"""Prompt evaluation on every prompt change (scripts/eval_prompts.py, 2026-11-13:
"ensuring every prompt change is properly evaluated")."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ep", ROOT / "scripts" / "eval_prompts.py")
ep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep)


@pytest.fixture(autouse=True)
def _no_real_prompteval_dir(monkeypatch, tmp_path):
    """evaluate() deletes stale run files; never let a test reach the repo's own."""
    monkeypatch.setattr(ep, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(ep, "JUDGEMENTS", tmp_path / "judgements")


def test_an_ask_change_re_evaluates_every_overlay_that_sits_on_it(monkeypatch):
    monkeypatch.setattr(ep, "git", lambda *a: "src/astro_ai/prompts/ask.txt\n")
    assert ep.changed_prompts("b") == sorted(["ask", *ep.OVERLAYS])


def test_an_overlay_is_evaluated_as_production_sends_it_under_ask(monkeypatch):
    files = {"ask": "BASE RULES", "ask_matching": "PAIR RULES", "natal": "NATAL"}
    monkeypatch.setattr(ep, "prompt_at", lambda ref, name: files.get(name))
    assert ep.system_at(None, "ask_matching") == "BASE RULES\nPAIR RULES"
    assert ep.system_at(None, "natal") == "NATAL"


def test_the_gate_fails_only_on_a_measurably_worse_prompt():
    """`bound` mode fails any eval too small to rule a drop out -- at 8 charts,
    every eval -- so it would block every prompt change and mean nothing."""
    assert ep.GATE == ["--fail-on", "quality-5%", "--gate-mode", "significant"]


def test_new_removed_and_unchanged_prompts_are_reported_not_judged(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(ep, "run", lambda cmd, env: calls.append(cmd) or (0, ""))
    for base, head, word in ((None, "x", "New"), ("x", None, "Removed"), ("x", "x", "unchanged")):
        monkeypatch.setattr(ep, "system_at", lambda ref, n, b=base, h=head: b if ref else h)
        text, rc = ep.evaluate("natal", "base", tmp_path, "judge")
        assert rc == ep.OK and word in text
    assert calls == []


# --- What a real prompteval run leaves behind ---------------------------------
# tests/fixtures/prompteval/ holds files written by the PINNED prompteval-delta
# 0.3.0 itself (2026-11-15), driven through scripts/eval_prompts.py with a stub
# `claude` on PATH -- no network, no tokens. Only `input`, `output` and
# `prompt_text` were trimmed for size; every key and the `error` values are as
# prompteval wrote them. In that run `prompteval run` printed
# "errors 6 of 8 examples failed" and EXITED 0, and the unfixed script reported
# "no prompt got worse" and exited 0 (QA FAIL on PR #1000).
FIX = ROOT / "tests" / "fixtures" / "prompteval"
CLEAN_RUN = FIX / "natal-base-clean.json"
PARTIAL_RUN = FIX / "natal-head-6-of-8-errored.json"
FULL_JUDGEMENT = FIX / "judgement-full.json"
UNREADABLE_JUDGEMENT = FIX / "judgement-16-unreadable.json"
GATE_BREACH_OUT = ("Quality verdict:  significant regression on pairwise_preference\n\n"
                   "GATE FAILED:\n  - quality: pairwise_preference dropped\n")


def _prompteval(monkeypatch, tmp_path, base_run=CLEAN_RUN, head_run=CLEAN_RUN, compare=(0, ""),
                judgement=FULL_JUDGEMENT):
    """Stand in for the prompteval CLI the way it really behaves: `run` exits 0
    whatever happened to the examples and leaves .prompteval/runs/<tag>.json;
    `compare` leaves the judgement file and returns `compare`."""
    runs, judgements = tmp_path / "runs", tmp_path / "judgements"
    runs.mkdir(exist_ok=True)
    judgements.mkdir(exist_ok=True)
    monkeypatch.setattr(ep, "RUNS", runs)
    monkeypatch.setattr(ep, "JUDGEMENTS", judgements)
    monkeypatch.setattr(ep, "system_at", lambda ref, n: "old" if ref else "new")
    seen = []

    def fake(cmd, env):
        seen.append(cmd[1])
        if cmd[1] == "run":
            tag = cmd[cmd.index("--tag") + 1]
            src = base_run if tag.endswith("-base") else head_run
            if src is not None:
                (runs / f"{tag}.json").write_text(src.read_text())
            return 0, "errors                      6 of 8 examples failed\n"
        if judgement is not None:
            (judgements / f"{cmd[2]}__vs__{cmd[3]}.json").write_text(judgement.read_text())
        return compare

    monkeypatch.setattr(ep, "run", fake)
    return seen


def test_the_fixtures_are_the_shapes_they_claim():
    head = json.loads(PARTIAL_RUN.read_text())["examples"]
    assert len(head) == 8 and sum(e["error"] is not None for e in head) == 6
    assert all(e["error"] is None for e in json.loads(CLEAN_RUN.read_text())["examples"])


def test_a_run_whose_charts_errored_fails_closed_though_prompteval_exited_0(monkeypatch, tmp_path):
    seen = _prompteval(monkeypatch, tmp_path, head_run=PARTIAL_RUN)
    text, status = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert status == ep.NOT_EVALUATED, text
    assert "Could not evaluate" in text and "6 of 8 charts errored" in text and "429" in text
    assert "Worse" not in text, "an infra failure must not be reported as a measured regression"
    assert seen == ["run", "run"], "a partial run must not go on to be judged on its survivors"


def test_a_run_missing_charts_fails_closed(monkeypatch, tmp_path):
    short = tmp_path / "short.json"
    d = json.loads(CLEAN_RUN.read_text())
    d["examples"] = d["examples"][:6]
    short.write_text(json.dumps(d))
    _prompteval(monkeypatch, tmp_path, head_run=short)
    text, status = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert status == ep.NOT_EVALUATED and "6 charts recorded, the dataset has 8" in text


def test_a_run_that_left_no_run_file_fails_closed(monkeypatch, tmp_path):
    _prompteval(monkeypatch, tmp_path, head_run=None)
    text, status = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert status == ep.NOT_EVALUATED and "no readable run file" in text


def test_a_run_that_cannot_complete_fails_closed(monkeypatch, tmp_path):
    """`prompteval run` does exit non-zero on a ClickException (unknown model,
    missing criteria) -- that path is real too, just not the one errors take."""
    monkeypatch.setattr(ep, "system_at", lambda ref, n: "old" if ref else "new")
    monkeypatch.setattr(ep, "run", lambda cmd, env: (1, "Error: unknown model"))
    text, status = ep.evaluate("natal", "base", tmp_path, "judge")
    assert status == ep.NOT_EVALUATED and "Could not evaluate" in text and "Worse" not in text
    assert "`prompteval run` for `natal-base` exited 1" in text


def test_a_compare_that_crashes_is_could_not_evaluate_not_worse(monkeypatch, tmp_path):
    """compare exits 1 on a ClickException or a crash as well as on a gate breach;
    only its `GATE FAILED:` line is a measured regression. A full judgement file
    can exist even so: compare saves it BEFORE compute_comparison, whose
    ValueError (e.g. "only 1 paired examples") is a ClickException, exit 1."""
    _prompteval(monkeypatch, tmp_path,
                compare=(1, "Error: Cannot compare 'natal-base' vs 'natal-head': only 1 paired examples\n"))
    text, status = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert status == ep.NOT_EVALUATED, text
    assert "Could not evaluate" in text and "Worse" not in text


def test_an_unreadable_judge_reply_fails_closed(monkeypatch, tmp_path):
    """prompteval counts a reply that is not A, B or TIE as a tie, and ties pull
    the verdict towards 'not worse'."""
    _prompteval(monkeypatch, tmp_path, judgement=UNREADABLE_JUDGEMENT)
    text, status = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert status == ep.NOT_EVALUATED and "16 judge replies were not A, B or TIE" in text


def test_a_complete_run_with_no_regression_passes(monkeypatch, tmp_path):
    seen = _prompteval(monkeypatch, tmp_path, compare=(0, "Quality verdict:  holds\n"))
    text, status = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert status == ep.OK and "Not measurably worse" in text
    assert seen == ["run", "run", "compare"]


def test_a_stale_run_file_is_never_read_as_this_runs_result(monkeypatch, tmp_path):
    seen = _prompteval(monkeypatch, tmp_path, head_run=None)
    (tmp_path / "runs" / "natal-head.json").write_text(CLEAN_RUN.read_text())  # left by an earlier run
    text, status = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert status == ep.NOT_EVALUATED and seen == ["run", "run"]


def test_a_worse_verdict_fails_and_says_so(monkeypatch, tmp_path):
    seen = []
    _prompteval(monkeypatch, tmp_path, compare=(1, GATE_BREACH_OUT))
    fake = ep.run
    monkeypatch.setattr(ep, "run", lambda cmd, env: seen.append((cmd[1], env["EVAL_PROMPT"])) or fake(cmd, env))
    text, rc = ep.evaluate("natal", "base", tmp_path / "w", "judge")
    assert rc == ep.WORSE and "Worse" in text and "Could not evaluate" not in text
    assert seen == [("run", "natal"), ("run", "natal"), ("compare", "natal")]


def test_the_judge_reads_the_BASE_prompt_as_the_rules(monkeypatch, tmp_path):
    """Measured: judged against the head prompt, a prompt replaced by one vague
    line WON 0.88-0.50 because the real readings 'broke' its new rule."""
    _prompteval(monkeypatch, tmp_path)
    cmds = []
    fake = ep.run
    monkeypatch.setattr(ep, "run", lambda cmd, env: cmds.append(cmd) or fake(cmd, env))
    ep.evaluate("natal", "base", tmp_path / "w", "judge")
    compare = next(c for c in cmds if c[1] == "compare")
    ctx = compare[compare.index("--judge-context") + 1]
    assert ctx.endswith("base.txt") and Path(ctx).read_text() == "old"


def test_no_prompt_change_evaluates_nothing_and_passes(monkeypatch, tmp_path):
    monkeypatch.setattr(ep, "git", lambda *a: "abc123\n" if a[0] == "merge-base" else "")
    out = tmp_path / "r.md"
    assert ep.main(["x", "--out", str(out)]) == 0
    assert "No prompt changed" in out.read_text()


def test_every_prompt_has_a_captured_dataset():
    """evals/capture_datasets.py fails when a prompt has no route call; this
    keeps the committed datasets in step with the prompt files."""
    prompts = {p.stem for p in (ROOT / "src" / "astro_ai" / "prompts").glob("*.txt")}
    datasets = {p.stem for p in (ROOT / "evals" / "datasets").glob("*.jsonl")}
    assert prompts <= datasets, f"no dataset for {sorted(prompts - datasets)}"
    for name in prompts:
        rows = [json.loads(l) for l in (ROOT / "evals" / "datasets" / f"{name}.jsonl").read_text().splitlines()]
        assert len(rows) >= 8 and all(r["input"].strip() for r in rows), name


def test_the_job_fails_when_any_prompt_got_worse(monkeypatch, tmp_path):
    monkeypatch.setattr(ep, "git", lambda *a: "abc123\n")
    monkeypatch.setattr(ep, "changed_prompts", lambda base: ["daily", "natal"])
    monkeypatch.setattr(ep, "evaluate", lambda n, *a: (f"## {n}\n", 1 if n == "natal" else 0))
    out = tmp_path / "r.md"
    assert ep.main(["x", "--out", str(out)]) == 1
    assert "worse on natal" in out.read_text()


def test_could_not_evaluate_blocks_the_job_and_is_not_called_worse(monkeypatch, tmp_path):
    monkeypatch.setattr(ep, "git", lambda *a: "abc123\n")
    monkeypatch.setattr(ep, "changed_prompts", lambda base: ["daily", "natal"])
    monkeypatch.setattr(ep, "evaluate", lambda n, *a: (f"## {n}\n", ep.NOT_EVALUATED if n == "natal" else ep.OK))
    out = tmp_path / "r.md"
    assert ep.main(["x", "--out", str(out)]) == 1
    head = out.read_text().splitlines()[0]
    assert "could not evaluate natal (blocked, failing closed)" in head and "worse" not in head, head


# --- The eval must run on a dispatched pr-gates run too (QA FAIL on PR #1000) ---
# agent-work's rescue net (#322) dispatches pr-gates on the BRANCH for a PR opened
# with GITHUB_TOKEN. agent-merge reads the latest `gates` check per head SHA, of
# any event, so a dispatch that skips the eval and goes green lets a prompt
# change merge unevaluated. These run the workflow's own shell, not a copy of it.
WF = ROOT / ".github" / "workflows" / "pr-gates.yml"


def _step(name: str) -> dict:
    steps = yaml.safe_load(WF.read_text())["jobs"]["gates"]["steps"]
    return next(s for s in steps if s.get("name") == name)


def _holds(cond: str, ctx: dict[str, str]) -> bool:
    """Evaluate a step's `if:` for the expressions these steps use. Anything not
    in `ctx` is left as a bare name and raises, so a new clause cannot slip by."""
    expr = cond
    for key, value in ctx.items():
        expr = expr.replace(key, repr(value))
    return eval(expr.replace("&&", " and ").replace("||", " or "), {"__builtins__": {}}, {})


def _bash(script: str, cwd: Path, env: dict[str, str]) -> dict[str, str]:
    out = cwd / "gh_output"
    out.write_text("")
    script = re.sub(r"\$\{\{[^}]*\}\}", "", script)  # a dispatch has no pull_request payload
    subprocess.run(["bash", "-e", "-c", script], cwd=cwd, check=True, capture_output=True, text=True,
                   env={"PATH": "/usr/bin:/bin", "GITHUB_OUTPUT": str(out), **env})
    return dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo,
                   check=True, capture_output=True)


def _branch_with_prompt_change_then_docs_commit(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    prompts = repo / "src" / "astro_ai" / "prompts"
    prompts.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (prompts / "natal.txt").write_text("rules\n")
    (repo / "README.md").write_text("readme\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-qb", "feat")
    (prompts / "natal.txt").write_text("rules\none more\n")
    _git(repo, "commit", "-qam", "prompt change")
    (repo / "README.md").write_text("readme, edited\n")
    _git(repo, "commit", "-qam", "docs only")  # HEAD~1 is docs-only: the scope step's dispatch blind spot
    return repo


def test_a_dispatched_run_evaluates_a_changed_prompt(tmp_path):
    repo = _branch_with_prompt_change_then_docs_commit(tmp_path)
    env = {"EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/feat"}
    scope = _bash(_step("Does this touch code?")["run"], repo, env)
    assert scope.get("code") == "true", (
        "a dispatched run on a branch whose prompt differs from main read code=false, "
        f"so the prompt evaluation hanging off it is skipped and gates go green: {scope}")
    prompts = _step("Prompts changed?")
    ctx = {"steps.scope.outputs.code": scope["code"], "github.event_name": "workflow_dispatch"}
    assert _holds(prompts["if"], ctx), (
        f"`Prompts changed?` does not run on workflow_dispatch (if: {prompts['if']}), so a "
        "#322 rescue-net run of pr-gates skips the eval and reports green")
    assert _bash(prompts["run"], repo, env).get("changed") == "true"
    for name in ("Install Claude Code and prompteval", "Capture the eval datasets at this commit",
                 "Evaluate the changed prompts"):
        assert _holds(_step(name)["if"], {"steps.prompts.outputs.changed": "true"}), name
