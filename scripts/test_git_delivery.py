from pathlib import Path
import json
import subprocess
import tempfile

from git_delivery import (
    BLOCKED,
    FAILED_VALIDATION,
    NEEDS_HUMAN_DECISION,
    PASS,
    PUSH_FAILED,
    READY,
    WAITING_FOR_GIT_REMOTE,
    WAITING_FOR_REPOSITORY,
    build_commit_plan,
    classify_repository,
    commit_group,
    final_test_gate,
    inspect_repository,
    prerequisites_passed,
    push,
    resume_git_delivery,
    scan_worktree,
    validate_remote,
    write_commit_plan,
)
from project_factory import load_state, save_state, run_git


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True, text=True)


def init_repo():
    raw = tempfile.TemporaryDirectory()
    repo = Path(raw.name)
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Project Factory Test")
    return raw, repo


def test_three_repository_states():
    raw, path = init_repo()
    try:
        assert classify_repository(path) == WAITING_FOR_GIT_REMOTE
        git(path, "remote", "add", "origin", "https://github.com/example/project.git")
        assert classify_repository(path) == READY
    finally:
        raw.cleanup()
    with tempfile.TemporaryDirectory() as empty:
        assert classify_repository(Path(empty)) == WAITING_FOR_REPOSITORY


def test_prerequisites_and_final_gate():
    evidence = {
        "fullAcceptance": "PASS", "build": True, "unit": "PASS", "integration": "PASS",
        "e2e": "PASS", "coreCoverage": "100%", "p0Bugs": 0, "p1Bugs": 0,
        "blockingSecurity": False,
    }
    assert prerequisites_passed(evidence)
    assert final_test_gate({"build": True, "unit": "PASS", "integration": "PASS", "e2e": "PASS"})
    evidence["e2e"] = "FAIL"
    assert not prerequisites_passed(evidence)
    evidence["e2e"] = "PASS"
    evidence["blockingSecurity"] = "BLOCKED"
    assert not prerequisites_passed(evidence)
    assert final_test_gate({"finalTest": FAILED_VALIDATION}) is False


def test_secret_scan_redacts_values():
    raw, repo = init_repo()
    try:
        (repo / ".env").write_text("API_KEY=do-not-print\n", encoding="utf-8")
        (repo / "private.pem").write_text("-----BEGIN PRIVATE KEY-----\nsecret\n", encoding="utf-8")
        result = scan_worktree(repo)
        assert result["passed"] is False
        assert {item["path"] for item in result["findings"]} == {".env", "private.pem"}
        assert "do-not-print" not in json.dumps(result)
    finally:
        raw.cleanup()


def test_commit_plan_and_dry_run_are_logical():
    raw, repo = init_repo()
    try:
        (repo / "backend").mkdir()
        (repo / "backend" / "auth.py").write_text("auth\n", encoding="utf-8")
        (repo / "tests").mkdir()
        (repo / "tests" / "test_auth.py").write_text("test\n", encoding="utf-8")
        plan = build_commit_plan(repo, [Path("backend/auth.py"), Path("tests/test_auth.py")])
        assert len(plan) == 2
        target = repo / "workflow" / "git-commit-plan.md"
        write_commit_plan(target, plan)
        assert target.exists() and "Commit" in target.read_text(encoding="utf-8")
        result = commit_group(repo, {"message": "feat(auth): add authentication", "files": ["backend/auth.py"]}, dry_run=True)
        assert result["status"] == "DRY_RUN"
        assert "git add" in result["commands"][0]
        assert not (repo / ".git" / "index.lock").exists()
    finally:
        raw.cleanup()


def test_commit_is_idempotent_and_preserves_history():
    raw, repo = init_repo()
    try:
        file = repo / "README.md"
        file.write_text("one\n", encoding="utf-8")
        group = {"message": "docs: add readme", "files": ["README.md"]}
        first = commit_group(repo, group)
        assert first["status"] == PASS
        first_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        second = commit_group(repo, group)
        assert second["status"] == "NOOP"
        assert run_git(repo, "rev-parse", "HEAD").stdout.strip() == first_head
        file.write_text("two\n", encoding="utf-8")
        commit_group(repo, {"message": "docs: update readme", "files": ["README.md"]})
        assert run_git(repo, "rev-list", "--count", "HEAD").stdout.strip() == "2"
        assert run_git(repo, "show", "--format=%s", "-s", first_head).stdout.strip() == "docs: add readme"
    finally:
        raw.cleanup()


def test_remote_validation_and_push_failure_recovery():
    raw, repo = init_repo()
    try:
        assert validate_remote([], "origin")["status"] == NEEDS_HUMAN_DECISION
        assert validate_remote([{"name": "origin", "url": "not a url", "kind": "fetch"}], "origin")["status"] == NEEDS_HUMAN_DECISION
        git(repo, "remote", "add", "origin", "file:///missing/project.git")
        result = push(repo)
        assert result["status"] == PUSH_FAILED
        state = {"phase": "GIT_DELIVERY", "status": "PUSH_FAILED", "gitDelivery": {"push": "PUSH_FAILED"}}
        resumed = resume_git_delivery(repo, state)
        assert resumed["gitDelivery"]["repositoryDetected"] is True
    finally:
        raw.cleanup()


def test_state_waiting_recovery():
    raw, repo = init_repo()
    try:
        state = {"phase": "GIT_DELIVERY", "status": "WAITING_FOR_GIT_REMOTE", "gitDelivery": {}}
        resumed = resume_git_delivery(repo, state)
        assert resumed["status"] == WAITING_FOR_GIT_REMOTE
        git(repo, "remote", "add", "origin", "git@github.com:example/project.git")
        assert resume_git_delivery(repo, state)["status"] == READY
    finally:
        raw.cleanup()


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_"):
            value()
    print("test_git_delivery: PASS")
