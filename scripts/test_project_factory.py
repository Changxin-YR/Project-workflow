from pathlib import Path
import json
import subprocess
import tempfile

from project_factory import DEFAULT_STATE, GitError, inspect_repository, load_state, save_state


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def test_state_round_trip_and_defaults():
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "workflow" / "state.json"
        state = load_state(path)
        assert state["phase"] == DEFAULT_STATE["phase"] == "INIT"
        state["phase"] = "GIT_DELIVERY"
        save_state(path, state)
        assert load_state(path)["phase"] == "GIT_DELIVERY"


def test_malformed_state_is_rejected():
    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "state.json"
        path.write_text("{", encoding="utf-8")
        try:
            load_state(path)
        except ValueError:
            return
        raise AssertionError("malformed state must raise ValueError")


def test_repository_and_origin_detection():
    with tempfile.TemporaryDirectory() as raw:
        repo = Path(raw)
        run("git", "init", cwd=repo)
        first = inspect_repository(repo)
        assert first["repositoryDetected"] is True
        assert first["remoteDetected"] is False
        run("git", "remote", "add", "origin", "https://github.com/example/project.git", cwd=repo)
        second = inspect_repository(repo)
        assert second["remoteDetected"] is True
        assert second["remotes"][0]["name"] == "origin"


def test_non_repository_detection():
    with tempfile.TemporaryDirectory() as raw:
        result = inspect_repository(Path(raw))
        assert result["repositoryDetected"] is False
        assert result["remoteDetected"] is False


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_"):
            value()
    print("test_project_factory: PASS")
