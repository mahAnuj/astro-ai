"""/agent-cycle is two files since #1254 (2026-11-19).

Every turn re-reads the whole command, and QA rounds (73 of 196 agent-work runs
in the week measured, `measurements/loop.json`) were re-reading about 6k tokens
of build steps they never use. So the entry file keeps what every mode needs and
the build steps moved to `agent-cycle/build.md`, which a build cycle reads first.

The split is only safe while three things hold, and each is a way it could
quietly degrade the loop:

1. every step exists exactly once across the two files (nothing lost, nothing
   duplicated to drift apart);
2. the entry file sends a build cycle to the build file, before Step 0a;
3. a QA round is told not to open the build file, or the saving is gone.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = (ROOT / ".claude" / "commands" / "agent-cycle.md").read_text(encoding="utf-8")
BUILD = (ROOT / ".claude" / "commands" / "agent-cycle" / "build.md").read_text(encoding="utf-8")

ENTRY_STEPS = ["0c", "0d", "0a", "3.5", "5"]
BUILD_STEPS = ["0", "1", "2", "2.5", "3", "3.6", "4", "4.5"]


def _steps(text: str) -> list[str]:
    return re.findall(r"^## Step ([0-9][0-9a-z.]*) ", text, re.M)


def test_every_step_is_in_exactly_one_file():
    entry, build = _steps(ENTRY), _steps(BUILD)
    assert entry == ENTRY_STEPS, f"entry file steps changed: {entry}"
    assert build == BUILD_STEPS, f"build file steps changed: {build}"
    assert not set(entry) & set(build), "a step is in both files and will drift"


def test_a_build_cycle_is_sent_to_the_build_file_before_step_0a():
    route = ENTRY.index("read\n  `.claude/commands/agent-cycle/build.md` in full now, before Step 0a.")
    assert route < ENTRY.index("## Step 0a"), "the build file is read too late to run Step 0"


def test_a_qa_round_is_told_not_to_open_the_build_file():
    assert "do not open the build file." in ENTRY


def test_the_shared_verdict_rules_are_in_the_entry_not_the_build_file():
    # QA rounds and fix rounds need these; they must not have to open build.md.
    for phrase in ("If that verdict is a FAIL", "### A JUDGE-ONLY round", "you cannot push to this branch"):
        assert phrase in ENTRY and phrase not in BUILD, phrase
