"""The triage script and the resolver agree on one contract, exercised through a REAL subprocess.

`test_triage_outsider_issues.py` drives `classify_provenance` with an in-process fake. That is
how #377 DEF-1 survived review: the fake returned a bare exit code, so it could not express the
one case that mattered -- a resolver that exits 1 because it CRASHED, which is the same code
OUTSIDER uses. These tests run `run_resolver` for real, with no network, so the parse is proved
against process behaviour rather than against a stand-in that was weaker than the script.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts" / "resolve_provenance.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "triage_outsider_issues", ROOT / "scripts" / "triage_outsider_issues.py")
    mod = importlib.util.module_from_spec(spec)
    # dataclasses resolve annotations through sys.modules, so register before executing.
    sys.modules["triage_outsider_issues"] = mod
    spec.loader.exec_module(mod)
    return mod


t = _load()


def _stub(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "stub_resolver.py"
    p.write_text(body)
    return p


def _classify(monkeypatch, script: Path, number: int, repo: str = "owner/name"):
    """classify_provenance over a real `python <script> <number>` call."""
    monkeypatch.setattr(t, "RESOLVER", script)
    return t.classify_provenance(lambda n: t.run_resolver(n, repo), number)


def test_the_real_resolver_prints_a_line_the_triage_can_parse():
    """Guards the coupling itself: if the resolver's output line is reworded, this fails here
    rather than silently turning every verdict into an error in production."""
    src = RESOLVER.read_text()
    assert 'print(f"#{args.issue}  {v.verdict} -- {v.reason}")' in src, (
        "resolve_provenance's verdict line changed; _RESOLVER_VERDICT in "
        "triage_outsider_issues.py must change with it")
    for word in ("TRUSTED", "OUTSIDER", "UNRESOLVED"):
        assert t._RESOLVER_VERDICT.match(f"#12  {word} -- because"), word


def test_a_traceback_exiting_1_is_an_error_not_an_outsider(tmp_path, monkeypatch):
    """The defect. An uncaught exception exits 1 and prints nothing to stdout."""
    script = _stub(tmp_path, "import sys\nraise RuntimeError('gh went missing')\n")
    kind, cause = _classify(monkeypatch, script, 5)
    assert kind == "error", f"a crash was read as {kind}"
    assert "without printing a verdict" in cause
    assert "RuntimeError" in cause or "gh went missing" in cause


def test_a_printed_outsider_verdict_exiting_1_is_an_outsider(tmp_path, monkeypatch):
    script = _stub(tmp_path, "print('#5  OUTSIDER -- author has read access')\nraise SystemExit(1)\n")
    assert _classify(monkeypatch, script, 5) == ("outsider", "")


def test_a_printed_trusted_verdict_exiting_0_is_trusted(tmp_path, monkeypatch):
    script = _stub(tmp_path, "print('#5  TRUSTED -- author has write access')\nraise SystemExit(0)\n")
    assert _classify(monkeypatch, script, 5) == ("trusted", "")


def test_unresolved_stays_an_error_and_keeps_its_reason(tmp_path, monkeypatch):
    script = _stub(tmp_path, "import sys\nprint('#5  UNRESOLVED -- a 403 from the API')\n"
                             "print('boom', file=sys.stderr)\nraise SystemExit(2)\n")
    kind, cause = _classify(monkeypatch, script, 5)
    assert kind == "error" and "resolver reported UNRESOLVED" in cause


def test_a_verdict_printed_for_a_different_issue_is_not_borrowed(tmp_path, monkeypatch):
    script = _stub(tmp_path, "print('#99  OUTSIDER -- about another issue')\nraise SystemExit(1)\n")
    kind, _ = _classify(monkeypatch, script, 5)
    assert kind == "error"


def test_a_resolver_that_cannot_be_executed_is_an_error(tmp_path, monkeypatch):
    kind, cause = _classify(monkeypatch, tmp_path / "does_not_exist.py", 5)
    assert kind == "error"
    assert "without printing a verdict" in cause or "could not be executed" in cause


def test_the_real_resolver_refuses_a_bad_repo_without_a_verdict(monkeypatch):
    """End to end over the shipped script, no network: a usage error must not read as a verdict."""
    monkeypatch.setattr(t, "RESOLVER", RESOLVER)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    kind, cause = t.classify_provenance(lambda n: t.run_resolver(n, "not-a-repo"), 5)
    assert kind == "error", f"a usage error was read as {kind}"
    assert "without printing a verdict" in cause
