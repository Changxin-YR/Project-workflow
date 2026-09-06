from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import os


ROOT = Path(__file__).resolve().parents[1]
NPM = "npm.cmd" if os.name == "nt" else "npm"


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


def test_npm_install():
    """Pack and install the package exactly as npm consumers do."""
    with tempfile.TemporaryDirectory(prefix="codex-project-factory-npm-") as temp:
        pack_dir = Path(temp) / "pack"
        install_dir = Path(temp) / "install"
        pack_dir.mkdir()
        install_dir.mkdir()
        packed = subprocess.run(
            [NPM, "pack", "--silent", "--pack-destination", str(pack_dir)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert packed.returncode == 0, packed.stdout + packed.stderr
        tarball = pack_dir / packed.stdout.strip().splitlines()[-1]
        assert tarball.is_file(), packed.stdout
        installed = subprocess.run(
            [NPM, "install", "--ignore-scripts", "--prefix", str(install_dir), str(tarball)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert installed.returncode == 0, installed.stdout + installed.stderr
        package_root = install_dir / "node_modules" / "codex-project-factory"
        assert (package_root / ".codex-plugin" / "plugin.json").is_file()
        assert (package_root / "skills" / "project-factory" / "SKILL.md").is_file()


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_"):
            value()
    print("test_package: PASS")
