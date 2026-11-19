"""scripts/pre_qa_check.py -- the cheap half of pr-gates, run before every QA dispatch.

Run 44020807802 (#1067 / PR #1150) spent two of its three QA rounds on a stale
ARCHITECTURE.md count that `verify_architecture_counts.py` reports in seconds.
These tests pin the four properties that make the pre-check worth running:

  * a failing gate exits non-zero, and exit 2 ("could not run") is never a pass;
  * its gate list is pinned to pr-gates' sweep, so it cannot drift from it;
  * nothing slow (the full suite, a server, a browser, a live LLM) is on it;
  * agent-cycle.md runs it before every QA dispatch.

`main()` is driven over fake gate scripts in a temp ROOT, so nothing here runs
the real gates or the real suite.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("pre_qa_check", ROOT / "scripts" / "pre_qa_check.py")
pqc = importlib.util.module_from_spec(_spec)
sys.modules["pre_qa_check"] = pqc
_spec.loader.exec_module(pqc)

PR_GATES = (ROOT / ".github" / "workflows" / "pr-gates.yml").read_text(encoding="utf-8")
# /agent-cycle is two files since #1254: the entry (0c, 0d, 0a, the shared verdict section, 3.5)
# and build.md (0, 1, 2, 2.5, 3, 3.6, 4, 4.5). Read both, entry first.
CYCLE_BUILD = (ROOT / ".claude" / "commands" / "agent-cycle" / "build.md").read_text(encoding="utf-8")
AGENT_CYCLE = (ROOT / ".claude" / "commands" / "agent-cycle.md").read_text(encoding="utf-8") + "\n" + CYCLE_BUILD


def _pr_gates_list(var: str) -> set[str]:
    m = re.search(rf'^\s*{var}="([^"]*)"', PR_GATES, re.M)
    assert m, f"pr-gates.yml no longer defines {var}= -- re-read how its sweep is built"
    return set(m.group(1).split())


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    """A ROOT holding gate scripts that exit with a chosen code, and no diff."""
    (tmp_path / "scripts").mkdir()

    def make(name: str, code: int, msg: str = "") -> str:
        (tmp_path / "scripts" / f"{name}.py").write_text(
            f"import sys\nprint({msg!r})\nsys.exit({code})\n", encoding="utf-8")
        return name

    monkeypatch.setattr(pqc, "ROOT", tmp_path)
    monkeypatch.setattr(pqc, "changed_files", lambda: [])
    return make


def test_all_gates_passing_exits_zero(fake_root, capsys):
    gates = (fake_root("verify_a", 0), fake_root("verify_b", 0))
    assert pqc.main(gates) == 0
    assert "pre-QA check: PASS" in capsys.readouterr().out


def test_a_failing_gate_exits_non_zero_and_names_it(fake_root, capsys):
    gates = (fake_root("verify_a", 0), fake_root("verify_counts", 1, "template count 58 != 59"))
    assert pqc.main(gates) == 1
    out = capsys.readouterr().out
    assert "verify_counts" in out and "FAIL" in out
    assert "template count 58 != 59" in out, "the failing gate's tail must be printed"


def test_a_gate_that_cannot_run_exits_two_never_zero(fake_root, capsys):
    gates = (fake_root("verify_a", 0), fake_root("verify_needs_node", 2, "SKIPPED"))
    assert pqc.main(gates) == 2
    assert "NOT a pass" in capsys.readouterr().out


def test_a_missing_gate_script_exits_two(fake_root):
    assert pqc.main((fake_root("verify_a", 0), "verify_renamed_away")) == 2


def test_a_failure_outranks_a_could_not_run(fake_root):
    gates = (fake_root("verify_a", 1), fake_root("verify_b", 2))
    assert pqc.main(gates) == 1


def test_an_uncomputable_diff_exits_two(fake_root, monkeypatch):
    monkeypatch.setattr(pqc, "changed_files", lambda: None)
    assert pqc.main((fake_root("verify_a", 0),)) == 2


def test_a_failing_diff_test_exits_non_zero(fake_root, tmp_path, monkeypatch):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x():\n    assert False\n")
    monkeypatch.setattr(pqc, "changed_files", lambda: ["tests/test_x.py"])
    assert pqc.main((fake_root("verify_a", 0),)) == 1


def test_diff_tests_select_changed_tests_and_importers(fake_root, tmp_path):
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_chart.py").write_text("from astro_ai import chart\n")
    (t / "test_gate.py").write_text('p = ROOT / "scripts" / "red_gates.py"\n')
    (t / "test_other.py").write_text("import json\n")
    (t / "test_touched.py").write_text("\n")
    got = pqc.tests_for(["src/astro_ai/chart.py", "scripts/red_gates.py", "tests/test_touched.py"])
    assert got == ["tests/test_chart.py", "tests/test_gate.py", "tests/test_touched.py"]
    assert pqc.tests_for(["tests/conftest.py"]) == "ALL"
    assert pqc.tests_for(["README.md"]) == []


def test_every_verify_script_is_classified_exactly_once():
    on_disk = {p.stem for p in (ROOT / "scripts").glob("verify_*.py")}
    fast, slow, llm = set(pqc.FAST_GATES), set(pqc.SLOW_GATES), set(pqc.LIVE_LLM_GATES)
    assert not fast & slow, f"in both FAST and SLOW: {sorted(fast & slow)}"
    assert len(pqc.FAST_GATES) == len(fast), "a FAST gate is listed twice"
    unclassified = on_disk - fast - slow - llm
    assert not unclassified, (
        f"new pr-gates gate(s) {sorted(unclassified)}: classify each as FAST or SLOW "
        "in scripts/pre_qa_check.py")
    stale = (fast | slow | llm) - on_disk
    assert not stale, f"listed but no such script: {sorted(stale)}"
    assert all(reason.strip() for reason in pqc.SLOW_GATES.values())


def test_the_fast_list_is_in_pr_gates_sweep_and_nothing_slow():
    live_llm = _pr_gates_list("NEEDS_LIVE_LLM")
    needs_server = _pr_gates_list("NEEDS_SERVER")
    assert "for f in scripts/verify_*.py" in PR_GATES, "pr-gates' sweep glob moved"
    assert set(pqc.LIVE_LLM_GATES) == live_llm
    fast = set(pqc.FAST_GATES)
    assert not fast & live_llm, "a live-LLM gate is not in pr-gates' sweep at all"
    assert not fast & needs_server, "a server/browser gate is not cheap"
    # verify_behaviour IS the full suite, and verify_css_build needs node.
    assert "verify_behaviour" not in fast
    assert "verify_conflict_markers" in fast and "verify_architecture_counts" in fast
    assert "verify_test_floor" in fast


def test_the_script_is_not_named_like_a_gate():
    # pr-gates runs every scripts/verify_*.py with no arguments (PR #1063 went red that way).
    assert not Path(pqc.__file__).name.startswith("verify_")


def test_agent_cycle_runs_it_before_every_qa_dispatch():
    # Step 0d quotes this heading, so slice it from build.md alone.
    step3 = CYCLE_BUILD[CYCLE_BUILD.index("## Step 3 — build it"):CYCLE_BUILD.index("## Step 3.6")]
    qa_bullet = step3.index("**`qa` as a separate dispatch, always.**")
    check = step3.index("uv run python scripts/pre_qa_check.py")
    assert qa_bullet < check < step3.index("### Dispatch in the FOREGROUND")
    assert "Dispatch `qa` only on PASS." in step3
    assert "a re-QA after a fix included" in step3

    # The two re-QA paths after a FAIL (Step 2.5's, now in the shared section of the entry file).
    s25 = AGENT_CYCLE[AGENT_CYCLE.index("If that verdict is a FAIL"):
                      AGENT_CYCLE.index("**Dispatch the QA round with the verdict")]
    assert "Then\n    `scripts/pre_qa_check.py` (Step 3), and QA only on its PASS." in s25
    assert "Go straight to `scripts/pre_qa_check.py` (Step 3)" in s25
    assert "Go straight to QA." not in s25

    # Step 0d: the push is what earns the next round.
    s0d = AGENT_CYCLE[AGENT_CYCLE.index("## Step 0d"):AGENT_CYCLE.index("## Step 0a")]
    assert s0d.index("scripts/pre_qa_check.py") < s0d.index("**Push to the PR's branch**")
