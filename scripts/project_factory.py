"""Small, dependency-free primitives shared by Project Factory Skills."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile


DEFAULT_STATE = {
    "schemaVersion": 1,
    "phase": "INIT",
    "status": "READY",
    "requirementsVersion": "1.0",
    "requirementsFrozen": False,
    "currentModule": None,
    "completedModules": [],
    "failedGate": None,
    "retryCount": 0,
    "lastGoodCommit": None,
    "gitDelivery": {
        "repositoryDetected": None,
        "remoteDetected": None,
        "securityScan": "PENDING",
        "commitPlan": "PENDING",
        "commitsCompleted": False,
        "finalTest": "PENDING",
        "remoteVerify": "PENDING",
        "push": "PENDING",
        "branch": None,
        "head": None,
    },
}


class GitError(RuntimeError):
    """Raised when a Git fact cannot be read safely."""


def load_state(path: Path) -> dict:
    """Read state or return an independent default state."""
    path = Path(path)
    if not path.exists():
        return deepcopy(DEFAULT_STATE)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid workflow state: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("workflow state must be a JSON object")
    return value


def save_state(path: Path, state: dict) -> None:
    """Write JSON atomically so an interrupted session cannot truncate state."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def update_state(path: Path, **changes) -> dict:
    state = load_state(path)
    state.update(changes)
    state["updatedAt"] = datetime.now(timezone.utc).isoformat()
    save_state(path, state)
    return state


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    repo = Path(repo).resolve()
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and result.returncode:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result


def _parse_remotes(output: str) -> list[dict]:
    remotes = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] in {"(fetch)", "(push)"}:
            remotes.append({"name": parts[0], "url": parts[1], "kind": parts[2][1:-1]})
    return remotes


def inspect_repository(repo: Path) -> dict:
    """Collect read-only Git facts; non-repositories return a normal result."""
    repo = Path(repo)
    probe = run_git(repo, "rev-parse", "--is-inside-work-tree", check=False)
    if probe.returncode or probe.stdout.strip().lower() != "true":
        return {
            "repositoryDetected": False,
            "remoteDetected": False,
            "branch": None,
            "status": "",
            "remotes": [],
        }
    status = run_git(repo, "status", "--short").stdout
    branch = run_git(repo, "branch", "--show-current").stdout.strip() or None
    remotes = _parse_remotes(run_git(repo, "remote", "-v").stdout)
    return {
        "repositoryDetected": True,
        "remoteDetected": any(item["name"] == "origin" for item in remotes),
        "branch": branch,
        "status": status,
        "remotes": remotes,
    }
