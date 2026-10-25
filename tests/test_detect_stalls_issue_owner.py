"""`detect_stalls` must name the owning issue for every branch a cycle produces.

WHY THIS IS A TEST, given the charter in conftest.py.

Every routed action in `steward.md`'s table is some form of "**dispatch a cycle
at the owning issue**". So a `None` in this field is not a cosmetic gap -- it is
a stall the steward can SEE and cannot ACT on, and the loop has no other way to
get a QA round onto an open PR.

Measured 2026-10-25, which is why this file exists. PRs #521 and #524 both had
green gates and neither `qa-pass` nor `qa-fail`, so both correctly fired
`no-qa-verdict`. The steward ran at least three times against each over 21
hours, cleared neither, and `steward-ineffective` escalated both to chief --
which would have ruled the same un-dispatchable answer on every subsequent run.
Nothing was holding those PRs back by any judgment: their branches were named
`partial/` and the regex here was `^issue/(\\d+)`, so the field came back
`null`.

That is the third place the same branch-name coupling was found in one day
(`agent-merge`'s eligibility gate and `agent-work`'s push net were the others),
and it is the one that produced a visible 21-hour stall while every component
reported success.

THE OPPOSITE ERROR IS ALSO PINNED. `^[a-z]+/(\\d+)` would be the obvious
widening and it is wrong: it reads `measurements/40140256532-1` as issue
40140256532. Those branches appear ~8 times a day (CLAUDE.md), and one open
long enough to be judged stalled would route a dispatch at an issue that does
not exist. Only `issue/`, `partial/` and `fix/` carry an issue number by
construction -- agent-cycle.md Step 4 -- so the namespaces are enumerated.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SCRIPT = (Path(__file__).resolve().parent.parent
          / "scripts" / "detect_stalls.py")


def _owner_pattern() -> re.Pattern[str]:
    """The real regex out of `detect_stalls.py`, not a copy of it.

    Lifted by source match rather than by importing the module: the import is
    cheap here, but a test that reimplements the pattern passes forever while
    the script ships something else, which is the defect this whole file is
    about.
    """
    src = SCRIPT.read_text(encoding="utf-8")
    m = re.search(r'''re\.match\(r"(\^[^"]+)",\s*pr\["headRefName"\]''', src)
    assert m, "the owning-issue regex is no longer recognisable in detect_stalls.py"
    return re.compile(m.group(1))


PATTERN = _owner_pattern()


def owner(branch: str) -> int | None:
    m = PATTERN.match(branch)
    return int(m.group(1)) if m else None


# --- 1. every namespace a cycle produces resolves ---------------------------

@pytest.mark.parametrize("branch,issue", [
    ("issue/523-per-area-day-ratings", 523),
    ("partial/523-per-area-day-ratings", 523),
    ("partial/518-route-the-top-five-articles", 518),
    ("partial/398-bphs-attributions-and-grain-cross-assignments", 398),
    ("fix/515-claude-cannot-write-to-tmp", 515),
])
def test_the_owning_issue_resolves_for_every_cycle_namespace(branch, issue):
    assert owner(branch) == issue


def test_the_three_live_stalls_of_2026_10_25_all_resolve():
    """The exact branches that stalled, by name.

    #521 -> #518, #524 -> #523, #530 -> #398. Each sat with a routed action the
    steward could not carry out because this field was null.
    """
    assert owner("partial/518-route-the-top-five-articles") == 518
    assert owner("partial/523-per-area-day-ratings") == 523
    assert owner("partial/398-bphs-attributions-and-grain-cross-assignments") == 398


# --- 2. the widening that must NOT happen -----------------------------------

def test_a_measurement_branch_never_yields_an_issue():
    """`^[a-z]+/(\\d+)` would read the run id as an issue number.

    ~8 of these a day. A dispatch at issue 40140256532 fails in a way that
    looks like the steward malfunctioning rather than like a bad branch parse.
    """
    assert owner("measurements/40140256532-1") is None
    assert owner("measurements/39867786023-1") is None


@pytest.mark.parametrize("branch", [
    "chore/hand-edit",
    "feat/124-hindi-url-prefix",   # a long-lived human branch, not a cycle's
    "main",
    "",
])
def test_a_branch_outside_the_cycle_namespaces_yields_no_issue(branch):
    assert owner(branch) is None


def test_the_pattern_enumerates_its_namespaces_rather_than_matching_any_word():
    """Guards the shape, so the next widening cannot be the lazy one."""
    src = PATTERN.pattern
    assert "issue" in src and "partial" in src and "fix" in src, src
    assert "[a-z]+/" not in src and "[a-z]*/" not in src, (
        f"{src} matches any namespace, including measurements/<run-id>"
    )
