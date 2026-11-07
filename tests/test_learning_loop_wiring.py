"""The feedback loop is wired end to end (owner, 2026-11-06): the ledger is
built, rivals are recorded, the planners read it, and /sync acts on it."""
from __future__ import annotations

from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _steps(wf):
    doc = yaml.safe_load((WF / f"{wf}.yml").read_text())
    return {j: job["steps"] for j, job in doc["jobs"].items()}


def _prompts(wf):
    return [s["with"]["prompt"] for steps in _steps(wf).values() for s in steps
            if "claude-code-action" in (s.get("uses") or "")]


def test_agent_measure_builds_the_ledger_and_snapshots_llm_usage():
    jobs = _steps("agent-measure")
    commit = " ".join(s.get("run") or "" for s in jobs["commit"])
    measure = jobs["measure"]
    assert "scripts/collect_lessons.py" in commit
    snap = next(s for s in measure if "collect_llm_usage.py" in (s.get("run") or ""))
    assert "/tmp/measure/llm-usage.json" in snap["run"], "the commit job copies /tmp/measure/*.json"
    assert snap.get("continue-on-error") is True
    names = [s.get("name") or s.get("uses") for s in measure]
    assert names.index(snap["name"]) > names.index("google-github-actions/auth@v2"), \
        "the snapshot needs the GCS credentials minted before it"


def test_the_planners_read_the_ledger():
    for wf in ("agent-work", "agent-prioritise", "agent-discover"):
        assert any("measurements/lessons.md" in p for p in _prompts(wf)), wf


def test_discover_records_rival_patterns_and_never_imports_a_claim():
    p = " ".join(_prompts("agent-discover"))
    assert "<!-- competitor-pattern -->" in p
    assert "never copy an astrological claim" in p


def test_sync_runs_the_learning_review():
    p = " ".join(_prompts("agent-sync"))
    assert "learning review" in p and "measurements/lessons.md" in p
