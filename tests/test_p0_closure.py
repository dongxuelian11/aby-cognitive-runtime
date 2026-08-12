"""Closure contract tests: P0 acceptance status, Apache-2.0 license, CLI reporting.

These tests lock the repository-status and license behavior introduced by the
P0 formal acceptance closure. They do not test P1 implementation (none exists).
"""

from pathlib import Path

from aby import cli

REPO_ROOT = Path(__file__).resolve().parent.parent

# Canonical Apache-2.0 text (apache.org / choosealicense.com) has 201 lines.
CANONICAL_APACHE_2_0_LINES = 201


def test_license_is_canonical_apache_2_0():
    text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].strip() == "Apache License"
    assert "Version 2.0, January 2004" in text
    assert "http://www.apache.org/licenses/" in text
    assert "END OF TERMS AND CONDITIONS" in text
    assert len(lines) == CANONICAL_APACHE_2_0_LINES


def test_pyproject_license_metadata():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = "Apache-2.0"' in pyproject


def test_tracker_all_items_accepted():
    tracker = (REPO_ROOT / "docs/p0/P0_ACCEPTANCE_TRACKER.md").read_text(encoding="utf-8")
    assert tracker.count("| [x] |") == 15
    assert "| [ ] |" not in tracker
    assert "ACCEPTED" in tracker
    assert "e3eeae345e5e86cf5bcec6349991bd4c1fbb04ed" in tracker


def test_cli_status_reports_accepted_not_validated(capsys):
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "THEORY_FREEZE_ACCEPTED: yes" in out
    assert "SCIENTIFICALLY_VALIDATED: no" in out
    # P1.1 started after closure merge; status wording evolves but the
    # accepted-vs-validated distinction must remain.
    assert "P1 Experimental Harness: authorized" in out
