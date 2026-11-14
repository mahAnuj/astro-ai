"""Prompt evaluation on every prompt change (scripts/eval_prompts.py, 2026-11-13:
"ensuring every prompt change is properly evaluated")."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ep", ROOT / "scripts" / "eval_prompts.py")
ep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep)


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
    monkeypatch.setattr(ep, "run", lambda cmd, env: calls.append(cmd) or 0)
    for base, head, word in ((None, "x", "New"), ("x", None, "Removed"), ("x", "x", "unchanged")):
        monkeypatch.setattr(ep, "system_at", lambda ref, n, b=base, h=head: b if ref else h)
        text, rc = ep.evaluate("natal", "base", tmp_path, "judge")
        assert rc == 0 and word in text
    assert calls == []


def test_a_run_that_cannot_complete_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(ep, "system_at", lambda ref, n: "old" if ref else "new")
    monkeypatch.setattr(ep, "run", lambda cmd, env: 1)
    text, rc = ep.evaluate("natal", "base", tmp_path, "judge")
    assert rc == 1 and "failed" in text


def test_a_worse_verdict_fails_and_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(ep, "system_at", lambda ref, n: "old" if ref else "new")
    seen = []

    def fake(cmd, env):
        seen.append((cmd[1], env["EVAL_PROMPT"]))
        return 1 if cmd[1] == "compare" else 0

    monkeypatch.setattr(ep, "run", fake)
    text, rc = ep.evaluate("natal", "base", tmp_path, "judge")
    assert rc == 1 and "Worse" in text
    assert seen == [("run", "natal"), ("run", "natal"), ("compare", "natal")]


def test_the_judge_reads_the_BASE_prompt_as_the_rules(monkeypatch, tmp_path):
    """Measured: judged against the head prompt, a prompt replaced by one vague
    line WON 0.88-0.50 because the real readings 'broke' its new rule."""
    monkeypatch.setattr(ep, "system_at", lambda ref, n: "old" if ref else "new")
    cmds = []
    monkeypatch.setattr(ep, "run", lambda cmd, env: cmds.append(cmd) or 0)
    ep.evaluate("natal", "base", tmp_path, "judge")
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
