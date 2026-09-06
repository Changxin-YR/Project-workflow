from pathlib import Path
import json
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_templates():
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "codex-project-factory"
    assert manifest["skills"] == "./skills/"
    state = json.loads((ROOT / "templates" / "project" / "workflow" / "state.json").read_text(encoding="utf-8"))
    assert state["phase"] == "INIT" and state["requirementsFrozen"] is False
    assert state["gitDelivery"]["push"] == "PENDING"
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["name"] == manifest["name"]
    assert "skills" in package["files"] and any(item.startswith("scripts/") for item in package["files"])
    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    entry = marketplace["plugins"][0]
    assert entry["name"] == manifest["name"]
    assert entry["source"]["path"] == "./"
    assert entry["policy"]["installation"] == "AVAILABLE"


def test_skill_inventory():
    expected = {
        "project-factory", "requirement-parser", "requirement-interviewer", "requirements-freeze",
        "github-reference-miner", "reference-synthesizer", "solution-architect", "plan-reviewer",
        "implementation-agent", "module-reviewer", "full-project-auditor", "release-manager", "git-delivery",
    }
    actual = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
    assert expected <= actual


def test_no_embedded_credentials():
    pattern = re.compile(r"(?i)(?:password|token|api[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]")
    for path in list((ROOT / "skills").rglob("*.md")) + [ROOT / "README.md", ROOT / "AGENTS.md"]:
        assert not pattern.search(path.read_text(encoding="utf-8")), path


def test_script_regressions():
    for name in ("test_project_factory.py", "test_git_delivery.py"):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_"):
            value()
    print("test_package: PASS")
