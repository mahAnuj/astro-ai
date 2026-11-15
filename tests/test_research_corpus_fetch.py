"""Research runs fetch the books instead of holding none of them (#1030).

Measured 2026-11-14: agent-research only ever ran `fetch_corpus.py --list`, so a
CI research run held ~0 of 10 books and every muhurat sourcing issue (#1027-#1029)
could be worked only on the owner's machine. The repo is public, so the books
are never committed: free ones download, the rest come from the private bucket.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "agent-research.yml"


def _steps():
    return yaml.safe_load(WF.read_text())["jobs"]["research"]["steps"]


def _index(pred):
    return next(i for i, s in enumerate(_steps()) if pred(s))


def _agent():
    return _index(lambda s: "claude-code-action" in (s.get("uses") or ""))


def test_the_books_are_fetched_before_the_agent_reads_them():
    fetch = _index(lambda s: "fetch_corpus.py --fetch" in (s.get("run") or ""))
    bucket = _index(lambda s: "fetch_corpus.py --from-bucket" in (s.get("run") or ""))
    listing = _index(lambda s: s.get("name") == "Which books are present")
    assert fetch < bucket < listing < _agent()


def test_bucket_credentials_never_reach_the_agent():
    auth = _index(lambda s: "google-github-actions/auth" in (s.get("uses") or ""))
    step = _steps()[auth]
    assert step["with"]["export_environment_variables"] is False
    assert step.get("continue-on-error") is True, "a failed sign-in must not stop the audit"
    rm = _index(lambda s: (s.get("name") or "").startswith("Remove the bucket credentials"))
    assert _steps()[rm]["if"] == "always()"
    assert auth < rm < _agent()
    for i, s in enumerate(_steps()):
        if i != _index(lambda x: "--from-bucket" in (x.get("run") or "")):
            assert "credentials_file_path" not in str(s.get("env") or {}) or i == rm, s.get("name")


def test_no_book_is_ever_committed():
    assert "data/" in (ROOT / ".gitignore").read_text().splitlines() or \
        any(line.strip() in ("data", "data/", "/data/", "/data") for line in (ROOT / ".gitignore").read_text().splitlines())
    assert "git add data" not in WF.read_text()

