"""Acceptance tests for the independent NEW_FOREX bootstrap."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "40820a9e1c631b8cd3e894a89d39fb66c63ddf68"


def test_bootstrap_documents_and_provenance_are_present() -> None:
    assert (ROOT / "docs" / "MASTER_PLAN.md").read_text() == (ROOT / "NEW_FOREX_MASTER_PLAN.md").read_text()
    assert (ROOT / "AGENTS.md").read_text() == (ROOT / "NEW_FOREX_AGENT_LOOP.md").read_text()
    provenance = (ROOT / "docs" / "PROVENANCE.md").read_text()
    assert "https://github.com/jpmartintech/SQX_CLAUDE_FOREX" in provenance
    assert SOURCE_SHA in provenance


def test_bootstrap_uses_new_forex_package_name() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'name = "new-forex"' in pyproject
    assert (ROOT / "src" / "new_forex" / "__init__.py").is_file()
    tracked = subprocess.run(
        ["git", "ls-files", "src/*.py", "scripts/*.py", "tests/*.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert tracked
    source_paths = [path for path in tracked if path != "tests/bootstrap/test_p00_bootstrap.py"]
    assert all("sqxf" not in (ROOT / path).read_text() for path in source_paths)


def test_bootstrap_excludes_local_data_and_secrets_from_git() -> None:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    assert not any(path.startswith(("data/", "runs/", ".venv/")) for path in tracked)
    assert ".env" not in tracked
    assert ".env.example" in tracked
