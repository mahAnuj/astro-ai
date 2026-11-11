"""One switch pauses every Claude-spending loop job (#903, owner 2026-11-11:
"there should be a pause/resume button for loop. If I want to save the tokens
for claude").

The switch is the repository variable LOOP_PAUSED ("true" = paused). These
tests pin that every loop job running claude-code-action honours it, that a
paused parent does not leave its persist job running on nothing, that the queue
holds still, and that a dispatch made while paused is QUEUED, not lost.
"""
from __future__ import annotations

import glob
import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
PAUSE = "vars.LOOP_PAUSED != 'true'"
#: Deliberately NOT paused: pausing it hands the day's rashifal to Groq, which
#: is a separate decision from saving Claude tokens on the loop.
NOT_LOOP = {"rashifal-generate.yml"}

_spec = importlib.util.spec_from_file_location("dispatch_carrier", ROOT / "tests" / "test_dispatch_carrier.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _claude_jobs():
    for f in sorted(glob.glob(str(WF / "*.yml"))):
        name = Path(f).name
        doc = yaml.safe_load(open(f))
        for job, spec in (doc.get("jobs") or {}).items():
            if any("claude-code-action" in str(s.get("uses", "")) for s in spec.get("steps", [])):
                yield name, job, spec, doc


def test_every_claude_spending_loop_job_honours_the_pause():
    seen = []
    for name, job, spec, _ in _claude_jobs():
        if name in NOT_LOOP:
            continue
        seen.append(f"{name}:{job}")
        assert str(spec.get("if", "")).startswith(PAUSE), f"{name}:{job} runs Claude while paused"
    assert len(seen) >= 9, seen


def test_a_paused_parent_does_not_leave_its_persist_job_running():
    for name, job, _, doc in _claude_jobs():
        if name in NOT_LOOP:
            continue
        for other, spec in doc["jobs"].items():
            needs = spec.get("needs") or []
            needs = [needs] if isinstance(needs, str) else needs
            if job in needs and "always()" in str(spec.get("if", "")) and name != "agent-measure.yml":
                assert f"needs.{job}.result != 'skipped'" in spec["if"], f"{name}:{other}"


def test_the_measurement_collectors_keep_running_while_paused():
    # They spend no Claude tokens and keep the quota reading the owner pauses on fresh.
    commit = yaml.safe_load(open(WF / "agent-measure.yml"))["jobs"]["commit"]
    assert "LOOP_PAUSED" not in str(commit.get("if", ""))


def test_the_queue_holds_still_while_paused():
    drain = yaml.safe_load(open(WF / "agent-queue.yml"))["jobs"]["drain"]
    assert drain["if"] == PAUSE


def test_every_dispatch_call_is_told_whether_the_loop_is_paused():
    for f in glob.glob(str(WF / "*.yml")):
        doc = yaml.safe_load(open(f))
        for job in (doc.get("jobs") or {}).values():
            for step in job.get("steps", []):
                if "scripts/dispatch_cycle.sh" in str(step.get("run", "")):
                    assert step.get("env", {}).get("LOOP_PAUSED") == "${{ vars.LOOP_PAUSED }}", f


def test_a_dispatch_while_paused_is_queued_not_dropped(tmp_path, monkeypatch):
    monkeypatch.setenv("LOOP_PAUSED", "true")
    r = dc._run(tmp_path, "issue=409", busy=0)          # lane free, but paused
    assert r.returncode == 0, r.stdout + r.stderr
    assert "QUEUED, not dropped" in r.stdout and "would queue" in r.stdout
    assert "would dispatch" not in r.stdout


def test_an_unpaused_free_lane_still_dispatches(tmp_path, monkeypatch):
    monkeypatch.setenv("LOOP_PAUSED", "false")
    r = dc._run(tmp_path, "issue=409", busy=0)
    assert "would dispatch" in r.stdout


def test_the_dashboard_links_to_the_switch():
    html = (ROOT / "src/astro_ai/templates/admin_ops.html").read_text()
    assert "github.com/mahAnuj/astro-ai/settings/variables/actions" in html
    assert "Pause / resume the loop" in html
