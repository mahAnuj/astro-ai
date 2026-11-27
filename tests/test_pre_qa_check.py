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
import os
import re
import subprocess
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
    monkeypatch.setattr(pqc, "diff_context", lambda changed: pqc.DiffContext(list(changed)))
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


# --------------------------------------------------------------- theme checks (#1255)
#
# The three themes QA fails on most (measurements/lessons.json, 2026-11-25: regression 31,
# grounding 30, tests 26). Each check is driven over a hand-built DiffContext in a temp ROOT.
# The pin below deliberately does NOT read lessons.json -- it is regenerated daily, and a
# test that follows it would go red on data drift rather than on a defect.

D = pqc.DiffContext


def test_theme_checks_cover_regression_grounding_and_tests():
    assert set(pqc.THEME_CHECKS) == {"regression", "grounding", "tests"}
    for theme, checks in pqc.THEME_CHECKS.items():
        assert len(checks) >= 1 and all(callable(c) for c in checks), theme


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(pqc, "ROOT", tmp_path)

    def put(rel: str, text: str) -> str:
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        return rel
    return put


def test_new_code_with_no_test_in_the_diff_fails_the_tests_theme():
    ctx = D(["scripts/new.py"], added={"scripts/new.py": ["import os", "def helper():", "    pass"]})
    [problem] = pqc.check_tests_accompany_code(ctx)
    assert "scripts/new.py" in problem and "tests/" in problem


def test_a_test_in_the_diff_clears_it_and_mutation_tables_and_non_code_are_exempt():
    with_test = D(["scripts/new.py", "tests/test_new.py"], added={"scripts/new.py": ["def helper():"]})
    assert pqc.check_tests_accompany_code(with_test) == []
    exempt = D(["scripts/mutations/m.py", "docs/x.md", "src/astro_ai/t.py"],
               added={"scripts/mutations/m.py": ["def f():"], "docs/x.md": ["def f():"],
                      "src/astro_ai/t.py": ["X = 1", "    # def commented", "y = 2"]})
    assert pqc.check_tests_accompany_code(exempt) == []


def _rows_file(tree, rows: str) -> str:
    return tree("scripts/mutations/m.py", f"MUTATIONS = [{rows}]\n")


def test_a_mutation_row_whose_anchor_is_missing_or_ambiguous_or_whose_test_is_absent_fails(tree):
    tree("src/t.py", "a = 1\nb = 2\nb = 2\n")
    tree("tests/test_t.py", "def test_real():\n    pass\n")
    row = lambda old, test: f'("lbl", "src/t.py", {old!r}, "x", {test!r}),'
    ok = _rows_file(tree, row("a = 1", "test_real"))
    assert pqc.check_mutation_rows_live(D([ok])) == []
    for old, test, word in (("zzz", "test_real", "0x"), ("b = 2", "test_real", "2x"),
                            ("a = 1", "test_gone", "test_gone")):
        _rows_file(tree, row(old, test))
        [problem] = pqc.check_mutation_rows_live(D(["scripts/mutations/m.py"]))
        assert word in problem, problem


def test_a_malformed_mutation_row_or_a_non_literal_table_cannot_pass(tree):
    _rows_file(tree, '("only", "three", "fields"),')
    assert "5-tuple" in pqc.check_mutation_rows_live(D(["scripts/mutations/m.py"]))[0]
    tree("scripts/mutations/m.py", "MUTATIONS = [make_row() for _ in range(3)]\n")
    with pytest.raises(pqc.CannotCompute):
        pqc.check_mutation_rows_live(D(["scripts/mutations/m.py"]))


def test_a_mutation_table_built_from_a_module_constant_is_read_not_refused(tree):
    # QA FAIL on #1475: `_GA = "..."` prefixes are common; literal_eval could not read them.
    tree("scripts/target.py", "ANCHOR = 1\n")
    tree("tests/test_t.py", "def test_x():\n    pass\n")
    tree("scripts/mutations/m.py",
         '_T = "scripts/target.py"\nMUTATIONS = [("lbl", _T, "ANCHOR", "OTHER", "test_x")]\n')
    assert pqc.check_mutation_rows_live(D(["scripts/mutations/m.py"])) == []


def test_a_mutation_file_that_cannot_be_loaded_cannot_compute_not_traceback(tree):
    tree("scripts/mutations/m.py", "MUTATIONS = [\n")
    with pytest.raises(pqc.CannotCompute):
        pqc.check_mutation_rows_live(D(["scripts/mutations/m.py"]))


def test_a_changed_python_file_that_does_not_parse_fails_regression(tree):
    tree("src/ok.py", "x = 1\n")
    tree("src/bad.py", "def f(:\n")
    [problem] = pqc.check_python_parses(D(["src/ok.py", "src/bad.py"]))
    assert problem.startswith("src/bad.py:1")


def test_a_changed_template_that_does_not_parse_fails_regression(tree):
    tree("src/astro_ai/templates/ok.html", "{% if a %}x{% endif %}")
    tree("src/astro_ai/templates/bad.html", "{% if a %}x")
    [problem] = pqc.check_templates_parse(D(["src/astro_ai/templates/ok.html", "src/astro_ai/templates/bad.html"]))
    assert problem.startswith("src/astro_ai/templates/bad.html")


def test_a_removed_name_that_code_still_uses_fails_regression(tree):
    tree("src/astro_ai/gone.py", "X = 1\n")
    tree("src/astro_ai/user.py", "from astro_ai.gone import helper\nprint(MAX_ROWS, gone.OLD)\n")
    ctx = D(["src/astro_ai/gone.py"], removed={"src/astro_ai/gone.py": [
        "def helper():", "MAX_ROWS = 5", "OLD = 1", "class Unused:"]})
    problems = pqc.check_removed_names_unreferenced(ctx)
    assert sorted(p.split("`")[1] for p in problems) == ["MAX_ROWS", "OLD", "helper"]
    assert all("src/astro_ai/user.py:" in p for p in problems)


def test_a_removed_name_that_was_re_added_or_only_named_in_a_string_passes(tree):
    tree("src/astro_ai/user.py", 'print(helper())\nS = "see helper and MAX_ROWS"\nobj.MAX_ROWS\n')
    moved = D(["a.py", "b.py"], removed={"a.py": ["def helper():"]}, added={"b.py": ["def helper():"]})
    assert pqc.check_removed_names_unreferenced(moved) == []
    string_only = D(["a.py"], removed={"a.py": ["MAX_ROWS = 5"]})
    assert pqc.check_removed_names_unreferenced(string_only) == []


def test_a_claim_bearing_file_without_a_corpus_line_fails_grounding():
    for path in ("src/astro_ai/knowledge/remedies.md", "src/astro_ai/prompts/natal.txt",
                 "src/astro_ai/templates/learn/x.html", "src/astro_ai/chart.py",
                 "src/astro_ai/muhurat_lagna.py", "src/astro_ai/matching.py"):
        got = pqc.check_grounding_proxy(D([path], commits=["fix a thing\n\nCloses #1"]))
        # a knowledge/*.md change IS the source, so only that one is exempt
        assert (got == []) == path.endswith(".md"), path


def test_a_corpus_line_or_a_knowledge_change_or_an_unrelated_diff_passes_grounding():
    msg = "retune the table\n\ncorpus: n/a -- no astrological rule changed"
    assert pqc.check_grounding_proxy(D(["src/astro_ai/chart.py"], commits=["x", msg])) == []
    assert pqc.check_grounding_proxy(D(["src/astro_ai/chart.py", "src/astro_ai/knowledge/a.md"])) == []
    assert pqc.check_grounding_proxy(D(["src/astro_ai/main.py", "scripts/x.py"])) == []


CHART = "src/astro_ai/chart.py"


def test_a_citation_in_an_added_decision_file_line_passes_grounding():
    # 6906d32 (#1478): the decision file cited knowledge/grahas.md, no commit had `corpus:`
    cites = {"docs/decisions/x.md": ["source: knowledge/grahas.md section 12.5"]}
    assert pqc.check_grounding_proxy(D([CHART, "docs/decisions/x.md"], added=cites, commits=["x"])) == []
    na = {"docs/decisions/x.md": ["corpus: n/a -- no astrological rule changed"]}
    assert pqc.check_grounding_proxy(D([CHART, "docs/decisions/x.md"], added=na, commits=["x"])) == []


def test_a_decision_file_that_cites_nothing_still_fails_grounding():
    ctx = D([CHART, "docs/decisions/x.md"], commits=["x"],
            added={"docs/decisions/x.md": ["# a decision", "Why: it was slow"]})
    assert len(pqc.check_grounding_proxy(ctx)) == 1
    assert len(pqc.check_grounding_proxy(D([CHART, "docs/decisions/x.md"], commits=["x"]))) == 1


def test_a_citation_outside_an_added_decision_line_does_not_pass_grounding():
    line = ["source: knowledge/grahas.md section 12.5"]
    for path in ("docs/decisions/README.md", "docs/other.md", "knowledge/x.mdx",
                 "docs/decisions/sub/x.md"):
        ctx = D([CHART, path], added={path: line}, commits=["x"])
        assert len(pqc.check_grounding_proxy(ctx)) == 1, path
    removed = D([CHART, "docs/decisions/x.md"], removed={"docs/decisions/x.md": line}, commits=["x"])
    assert len(pqc.check_grounding_proxy(removed)) == 1


def test_the_grounding_failure_names_both_places_a_citation_can_go():
    [msg] = pqc.check_grounding_proxy(D([CHART], commits=["x"]))
    assert "docs/decisions" in msg and "`corpus:`" in msg


def test_main_prints_one_themes_line_and_a_failing_theme_exits_one(fake_root, monkeypatch, capsys):
    monkeypatch.setattr(pqc, "changed_files", lambda: ["src/astro_ai/chart.py"])
    monkeypatch.setattr(pqc, "tests_for", lambda changed: [])
    monkeypatch.setattr(pqc, "diff_context", lambda changed: D(list(changed), commits=["no corpus"]))
    assert pqc.main((fake_root("verify_a", 0),)) == 1
    out = capsys.readouterr().out
    assert "themes: regression PASS grounding FAIL tests PASS" in out
    assert "[grounding] src/astro_ai/chart.py" in out and "FAIL (theme:grounding)" in out


def test_all_themes_passing_prints_the_summary_line_and_exits_zero(fake_root, monkeypatch, capsys, tmp_path):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(pqc, "changed_files", lambda: ["docs/x.md"])
    assert pqc.main((fake_root("verify_a", 0),)) == 0
    assert "themes: regression PASS grounding PASS tests PASS" in capsys.readouterr().out
    assert "themes: regression PASS grounding PASS tests PASS" in summary.read_text()


def test_a_theme_that_cannot_compute_exits_two_never_zero(fake_root, monkeypatch, capsys):
    monkeypatch.setattr(pqc, "changed_files", lambda: ["docs/x.md"])
    monkeypatch.setattr(pqc, "tests_for", lambda changed: [])
    def boom(ctx):
        raise pqc.CannotCompute("no table")
    monkeypatch.setitem(pqc.THEME_CHECKS, "tests", (boom,))
    assert pqc.main((fake_root("verify_a", 0),)) == 2
    assert "tests COULD NOT RUN" in capsys.readouterr().out


def test_an_undiffable_tree_makes_the_themes_unrunnable_not_passing(fake_root, monkeypatch):
    monkeypatch.setattr(pqc, "changed_files", lambda: ["docs/x.md"])
    monkeypatch.setattr(pqc, "tests_for", lambda changed: [])
    monkeypatch.setattr(pqc, "diff_context", lambda changed: None)
    assert pqc.main((fake_root("verify_a", 0),)) == 2


def test_diff_context_reads_added_removed_untracked_and_commit_lines_from_real_git(tmp_path, monkeypatch):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True, env=env)
    git("init", "-q", "-b", "main")
    (tmp_path / "a.py").write_text("def old():\n    pass\n-- not a header\nKEEP = 1\n")
    git("add", "."); git("commit", "-qm", "base")
    git("checkout", "-qb", "work")
    (tmp_path / "a.py").write_text("def new():\n    pass\n-- not a header\nKEEP = 1\n")
    git("commit", "-qam", "rename\n\ncorpus: n/a -- test")
    (tmp_path / "b.py").write_text("def fresh():\n    pass\n")      # untracked
    monkeypatch.setattr(pqc, "ROOT", tmp_path)
    monkeypatch.setattr(pqc, "BASE_REF", "main")
    ctx = pqc.diff_context(["a.py", "b.py"])
    assert ctx.added == {"a.py": ["def new():"], "b.py": ["def fresh():", "    pass"]}
    assert ctx.removed == {"a.py": ["def old():"]}
    assert len(ctx.commits) == 1 and "corpus: n/a" in ctx.commits[0]
    assert pqc.check_grounding_proxy(D(["src/astro_ai/chart.py"], commits=ctx.commits)) == []
