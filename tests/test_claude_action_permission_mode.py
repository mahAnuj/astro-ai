"""Every claude-code-action step runs with a strict tool list and a pinned action (#1172).

claude-code-action switched its default to AUTO mode on 2026-11-12 (its PR #2004,
"Run sessions in auto mode by default"). In auto mode a safety review may pass a
tool call that no --allowedTools rule covers, so every allow/deny list in the
loop became advisory -- including agent-research's Edit bans on the rule modules.
We used the floating `@v1` tag in all 13 references, so the change arrived with
no diff in this repo. Runs setting `allowed_bots` kept the old defaults; the
other seven workflows did not.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WFS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
STRICT = {"default", "acceptEdits"}
PINNED = re.compile(r"^anthropics/claude-code-action@[0-9a-f]{40}$")


def _claude_steps():
    for wf in WFS:
        doc = yaml.safe_load(wf.read_text())
        for job_name, job in (doc.get("jobs") or {}).items():
            for step in job.get("steps") or []:
                if "claude-code-action" in (step.get("uses") or ""):
                    yield wf.name, job_name, step


def test_there_are_claude_steps_to_check():
    assert len(list(_claude_steps())) >= 13


def test_every_claude_step_sets_a_strict_permission_mode():
    bad = []
    for wf, job, step in _claude_steps():
        args = (step.get("with") or {}).get("claude_args") or ""
        modes = re.findall(r"--permission-mode\s+(\S+)", args)
        if len(modes) != 1 or modes[0] not in STRICT:
            bad.append(f"{wf}:{job} -> {modes or 'none'}")
    assert not bad, "auto/bypass/missing permission mode: " + "; ".join(bad)


def test_every_claude_step_pins_the_action_to_a_commit():
    bad = [f"{wf}:{job} uses {step['uses']}" for wf, job, step in _claude_steps()
           if not PINNED.match(step["uses"].split()[0])]
    assert not bad, "a floating tag lets an upstream default change in silently: " + "; ".join(bad)
