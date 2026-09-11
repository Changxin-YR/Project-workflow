"""Deterministic, conservative Git Delivery operations for Project Factory."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

try:
    from project_factory import GitError, inspect_repository, load_state, run_git, save_state
except ModuleNotFoundError:  # package import via `python -m scripts...`
    from .project_factory import GitError, inspect_repository, load_state, run_git, save_state


READY = "READY"
PASS = "PASS"
BLOCKED = "BLOCKED"
WAITING_FOR_REPOSITORY = "WAITING_FOR_REPOSITORY"
WAITING_FOR_GIT_REMOTE = "WAITING_FOR_GIT_REMOTE"
WAITING_FOR_GIT_AUTH = "WAITING_FOR_GIT_AUTH"
PUSH_FAILED = "PUSH_FAILED"
FAILED_VALIDATION = "FAILED_VALIDATION"
NEEDS_HUMAN_DECISION = "NEEDS_HUMAN_DECISION"

SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials.json",
    "service-account.json",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
GENERATED_DIRS = {"node_modules", "venv", ".venv", "dist", "build", ".cache", "coverage", "logs"}
SECRET_MARKERS = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|"
    r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_+/=-]{8,}",
    re.IGNORECASE,
)
PLACEHOLDER_VALUES = {"do-not-print", "example", "example-key", "dummy", "test", "changeme"}


def _pass(value) -> bool:
    return value is True or (isinstance(value, str) and value.upper() in {"PASS", "PASSED", "TRUE"})


def prerequisites_passed(evidence: dict) -> bool:
    required = ("fullAcceptance", "build", "unit", "integration", "e2e")
    if not all(_pass(evidence.get(key)) for key in required):
        return False
    coverage = evidence.get("coreCoverage", evidence.get("coverage"))
    if isinstance(coverage, str):
        coverage = coverage.strip().rstrip("%")
    try:
        if float(coverage) != 100:
            return False
    except (TypeError, ValueError):
        return False
    blocking = evidence.get("blockingSecurity", False)
    blocking = blocking is True or (isinstance(blocking, str) and blocking.upper() in {"BLOCKED", "FAIL", "FAILED", "TRUE"})
    return evidence.get("p0Bugs", 0) == 0 and evidence.get("p1Bugs", 0) == 0 and not blocking


def final_test_gate(evidence: dict) -> bool:
    if evidence.get("finalTest") in {FAILED_VALIDATION, "FAIL", "FAILED"}:
        return False
    return all(_pass(evidence.get(key)) for key in ("build", "unit", "integration", "e2e"))


def classify_repository(repo: Path) -> str:
    facts = inspect_repository(repo)
    if not facts["repositoryDetected"]:
        return WAITING_FOR_REPOSITORY
    if not facts["remoteDetected"]:
        return WAITING_FOR_GIT_REMOTE
    return READY


def validate_remote(remotes: list[dict], target: str = "origin") -> dict:
    matches = [item for item in remotes if item["name"] == target]
    unique_urls = {item["url"] for item in matches}
    if len(unique_urls) != 1:
        return {"status": NEEDS_HUMAN_DECISION, "reason": f"expected exactly one {target} remote"}
    url = next(iter(unique_urls))
    if any(char.isspace() for char in url) or "@" in url.split("://", 1)[-1].split("/", 1)[0]:
        return {"status": NEEDS_HUMAN_DECISION, "reason": "remote URL is malformed or contains credentials"}
    if url.startswith("git@"):
        match = re.fullmatch(r"git@([^:]+):([^/]+)/(.+?)(?:\.git)?", url)
        if not match:
            return {"status": NEEDS_HUMAN_DECISION, "reason": "remote URL is malformed"}
        host, owner, name = match.groups()
    else:
        parsed = urlparse(url)
        if not parsed.scheme or (not parsed.netloc and parsed.scheme != "file") or not parsed.path.strip("/"):
            return {"status": NEEDS_HUMAN_DECISION, "reason": "remote URL is malformed"}
        host = parsed.hostname or ""
        parts = [part for part in parsed.path.split("/") if part]
        owner, name = (parts[-2], parts[-1]) if len(parts) >= 2 else (None, None)
    return {"status": PASS, "name": target, "url": url, "host": host, "owner": owner, "repository": name.removesuffix(".git") if name else None}


def _safe_relative(repo: Path, value: Path | str) -> Path:
    repo = Path(repo).resolve()
    candidate = (repo / Path(value)).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        relative = candidate.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"path outside repository: {value}") from exc
    return relative


def scan_paths(repo: Path, paths) -> dict:
    repo = Path(repo).resolve()
    findings = []
    seen = set()
    for raw in paths:
        relative = _safe_relative(repo, raw)
        absolute = repo / relative
        if not absolute.exists() or not absolute.is_file():
            continue
        name = absolute.name.lower()
        key = relative.as_posix()
        if name in SECRET_NAMES or (name.startswith(".env.") and name != ".env.example"):
            findings.append({"path": key, "rule": "environment-file"})
        if absolute.suffix.lower() in SECRET_SUFFIXES:
            findings.append({"path": key, "rule": "private-key-or-certificate"})
        try:
            content = absolute.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        marker = SECRET_MARKERS.search(content)
        if marker and marker.group(0).rsplit("=", 1)[-1].strip(" '\"").lower() not in PLACEHOLDER_VALUES:
            findings.append({"path": key, "rule": "credential-marker"})
    for finding in findings:
        marker = (finding["path"], finding["rule"])
        if marker not in seen:
            seen.add(marker)
    return {"passed": not findings, "findings": findings}


def scan_worktree(repo: Path) -> dict:
    repo = Path(repo).resolve()
    paths = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [name for name in dirs if name not in {".git", ".superpowers", "__pycache__"}]
        relative_root = Path(root).relative_to(repo)
        if any(part in GENERATED_DIRS for part in relative_root.parts):
            dirs[:] = []
            continue
        paths.extend(relative_root / name for name in files)
    return scan_paths(repo, paths)


_CATEGORY_MESSAGES = {
    "database": "feat(database): add persistence layer",
    "auth": "feat(auth): implement authentication and authorization",
    "core": "feat(core): implement core workflows",
    "api": "feat(api): implement application APIs",
    "ui": "feat(ui): implement application interface",
    "agent": "feat(agent): integrate AI capabilities",
    "tests": "test: add automated coverage",
    "docs": "docs: add project documentation",
    "infra": "chore: initialize project infrastructure",
}


def _category(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    for name in _CATEGORY_MESSAGES:
        if name in parts:
            return name
    suffix = path.suffix.lower()
    if suffix in {".md", ".rst", ".txt"}:
        return "docs"
    if "test" in path.name.lower() or path.name.lower().startswith("spec"):
        return "tests"
    return "core"


def build_commit_plan(repo: Path, files: list[Path], manifest: dict | None = None) -> list[dict]:
    groups = defaultdict(list)
    if manifest and manifest.get("groups"):
        for group in manifest["groups"]:
            groups[group["message"]].extend(Path(item).as_posix() for item in group.get("files", []))
    else:
        for raw in files:
            relative = _safe_relative(repo, raw)
            groups[_CATEGORY_MESSAGES[_category(relative)]].append(relative.as_posix())
    plan = []
    for index, (message, grouped) in enumerate(sorted(groups.items()), 1):
        category = _category(Path(grouped[0])) if grouped else "core"
        plan.append({
            "id": f"COMMIT-{index:02d}",
            "message": message,
            "purpose": f"Complete {category} changes as one logical capability.",
            "files": sorted(set(grouped)),
            "dependencies": [],
            "risk": "Medium" if category in {"auth", "database", "infra"} else "Low",
        })
    return plan


def write_commit_plan(path: Path, plan: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Git Commit Plan", ""]
    for group in plan:
        lines.extend([
            f"## {group['id']}",
            f"- Message: `{group['message']}`",
            f"- Purpose: {group['purpose']}",
            f"- Files: {', '.join(f'`{item}`' for item in group['files'])}",
            f"- Dependencies: {', '.join(group['dependencies']) or 'None'}",
            f"- Risk: {group['risk']}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def commit_group(repo: Path, group: dict, dry_run: bool = False) -> dict:
    files = [_safe_relative(repo, item).as_posix() for item in group.get("files", [])]
    if not files:
        return {"status": "NOOP", "files": []}
    scan = scan_paths(repo, files)
    if not scan["passed"]:
        return {"status": BLOCKED, "reason": "secret scan failed", "findings": scan["findings"]}
    commands = [f"git add -- {' '.join(files)}", f"git commit -m {group['message']!r}"]
    if dry_run:
        return {"status": "DRY_RUN", "commands": commands, "files": files}
    run_git(repo, "add", "--", *files)
    staged = run_git(repo, "diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return {"status": "NOOP", "files": files}
    run_git(repo, "commit", "-m", group["message"])
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    return {"status": PASS, "head": head, "files": files}


def verify_history(repo: Path) -> dict:
    facts = inspect_repository(repo)
    head = run_git(repo, "rev-parse", "HEAD", check=False)
    log = run_git(repo, "log", "--oneline", "--decorate", "-10", check=False)
    return {
        "passed": facts["repositoryDetected"] and not facts["status"],
        "status": facts["status"],
        "branch": facts["branch"],
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "log": log.stdout.splitlines(),
    }


def push(repo: Path, remote: str = "origin", branch: str | None = None, dry_run: bool = False) -> dict:
    facts = inspect_repository(repo)
    validation = validate_remote(facts["remotes"], remote)
    if validation["status"] != PASS:
        return validation
    branch = branch or facts["branch"]
    if not branch:
        return {"status": NEEDS_HUMAN_DECISION, "reason": "detached HEAD has no target branch"}
    upstream = run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    command = f"git push {'-u ' if upstream.returncode else ''}{remote} {branch}"
    if dry_run:
        return {"status": "DRY_RUN", "command": command, "remote": validation}
    result = run_git(repo, "push", *( ["-u"] if upstream.returncode else []), remote, branch, check=False)
    if result.returncode:
        error = result.stderr.lower()
        status = WAITING_FOR_GIT_AUTH if any(word in error for word in ("authentication", "permission denied", "could not read username", "access denied")) else PUSH_FAILED
        return {"status": status, "error": result.stderr[-500:]}
    remote_head = run_git(repo, "ls-remote", remote, branch, check=False)
    if remote_head.returncode:
        return {"status": PUSH_FAILED, "error": remote_head.stderr[-500:]}
    return {"status": PASS, "remote": validation, "branch": branch, "head": remote_head.stdout.split()[0] if remote_head.stdout.split() else None}


def resume_git_delivery(repo: Path, state: dict) -> dict:
    facts = inspect_repository(repo)
    nested = dict(state.get("gitDelivery") or {})
    nested.update({
        "repositoryDetected": facts["repositoryDetected"],
        "remoteDetected": facts["remoteDetected"],
        "branch": facts["branch"],
    })
    if facts["repositoryDetected"]:
        head = run_git(repo, "rev-parse", "HEAD", check=False)
        nested["head"] = head.stdout.strip() if head.returncode == 0 else None
    state["gitDelivery"] = nested
    if state.get("status") in {WAITING_FOR_REPOSITORY, WAITING_FOR_GIT_REMOTE, READY} or not state.get("status"):
        state["status"] = classify_repository(repo)
    return state


def _read_json(path: Path | None) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Project Factory Git Delivery Gate")
    parser.add_argument("command", choices=("inspect", "scan", "plan", "verify", "deliver"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--state", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    state_path = args.state or repo / "workflow" / "state.json"
    facts = inspect_repository(repo)
    if args.command == "inspect":
        print(json.dumps(facts, ensure_ascii=False, indent=2))
        return 0
    if args.command == "scan":
        result = scan_worktree(repo)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 2
    if args.command == "verify":
        result = verify_history(repo)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 2
    if args.command == "plan":
        files = [Path(item[3:]) for item in facts.get("status", "").splitlines() if len(item) > 3]
        plan = build_commit_plan(repo, files, _read_json(args.manifest) if args.manifest else None)
        write_commit_plan(repo / "workflow" / "git-commit-plan.md", plan)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    state = load_state(state_path)
    evidence = _read_json(args.evidence) if args.evidence else state.get("evidence", {})
    if not prerequisites_passed(evidence):
        state.update({"phase": "FULL_ACCEPTANCE", "status": BLOCKED, "failedGate": "FULL_ACCEPTANCE"})
        save_state(state_path, state)
        print(json.dumps({"status": BLOCKED, "reason": "full acceptance prerequisites failed"}, ensure_ascii=False))
        return 2
    classification = classify_repository(repo)
    if classification != READY:
        state.update({"phase": "GIT_DELIVERY", "status": classification})
        save_state(state_path, state)
        print(json.dumps({"status": classification}, ensure_ascii=False))
        return 3
    scan = scan_worktree(repo)
    if not scan["passed"]:
        state.update({"phase": "GIT_DELIVERY", "status": BLOCKED, "failedGate": "SECRET_SCAN"})
        save_state(state_path, state)
        print(json.dumps({"status": BLOCKED, "findings": scan["findings"]}, ensure_ascii=False))
        return 2
    files = [Path(item[3:]) for item in facts["status"].splitlines() if len(item) > 3]
    plan_path = repo / "workflow" / "git-commit-plan.md"
    plan = build_commit_plan(repo, files, _read_json(args.manifest) if args.manifest else None)
    write_commit_plan(plan_path, plan)
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN", "plan": plan, "push": push(repo, dry_run=True)}, ensure_ascii=False, indent=2))
        return 0
    commit_statuses = []
    for group in plan:
        result = commit_group(repo, group)
        if result["status"] not in {PASS, "NOOP"}:
            state.update({"phase": "GIT_DELIVERY", "status": result["status"], "failedGate": "COMMIT"})
            save_state(state_path, state)
            print(json.dumps(result, ensure_ascii=False))
            return 2
        commit_statuses.append(result["status"])
    if not final_test_gate(evidence):
        state.update({"phase": "GIT_DELIVERY", "status": FAILED_VALIDATION, "failedGate": "FINAL_TEST"})
        save_state(state_path, state)
        print(json.dumps({"status": FAILED_VALIDATION}, ensure_ascii=False))
        return 2
    result = push(repo)
    head = run_git(repo, "rev-parse", "HEAD", check=False)
    delivery = state.setdefault("gitDelivery", {})
    delivery.update({
        "securityScan": PASS,
        "commitPlan": PASS,
        "commitsCompleted": PASS in commit_statuses,
        "finalTest": PASS,
        "remoteVerify": PASS,
        "push": result["status"],
        "branch": result.get("branch"),
        "head": head.stdout.strip() if head.returncode == 0 else None,
    })
    if result["status"] == PASS:
        validation = result.get("remote") or {}
        if validation.get("url"):
            delivery["remoteUrl"] = validation["url"]
    state["phase"] = "FINAL_DELIVERY"
    state["status"] = result["status"]
    save_state(state_path, state)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == PASS else 4


if __name__ == "__main__":
    raise SystemExit(main())
