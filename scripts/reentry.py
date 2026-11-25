#!/usr/bin/env python3
"""Stand an `issue` queue entry down when a cycle has already run on it and nothing
has happened since (#1255).

WHY THIS EXISTS
---------------
measurements/loop.json, 2026-11-12..19: 124 build cycles on 98 issues, 26 of them a
repeat on an issue that had already had one. Nine of the 26 lasted under ten minutes
(~12M tokens) -- they re-read the issue and PR, found nothing new, and stood down.
`cycle_queue.stale_reason` already drops an entry whose PR is waiting to merge
(#704, #1207); it did not drop one whose PR is simply where the last cycle left it.
#1207's own second repair named this rule ("do not drain an entry whose target
already has a claude[bot] cycle comment newer than the entry"); this is that rule,
stated so it can be tested.

THE RULE
--------
Stand down only when ALL of these were read successfully:

  1. a `claude[bot]` comment that is not a `QA:` comment (T_last -- the trace a
     cycle leaves) exists on the issue or its open PR and is NEWER than the entry:
     a cycle ran after the entry was queued, so whatever the entry was queued for
     has had its cycle;
  2. exactly one open PR is owned by the issue (`_OWNED_BRANCH`);
  3. that PR's head commit is no newer than T_last: the cycle left no new commit;
  4. no `QA: PASS|FAIL` verdict is newer than T_last: no new ruling to act on;
  5. the PR does not need `main` merged into it (`mergeable_state` not behind,
     dirty or unknown). "A new main merge" in the issue is read this way, not as
     "main moved": main moves most hours, which would make the rule vacuous.

ANYTHING ELSE, AND ANY READ ERROR, RE-ENTERS (returns None). A wasted stand-down
costs ~35s; a wrongly dropped entry is permanent -- the same asymmetry as
`stale_reason`. An entry queued AFTER the last cycle (red gates, a QA FAIL) is
newer than T_last, fails (1), and always runs.

Only `claude[bot]` writes the trace. Comment bodies and branch names are
untrusted input: nothing here reads a body beyond two regex booleans computed by
`jq`, and the only text taken from a branch name is the issue number
`_OWNED_BRANCH` matched. A verdict from ANY author blocks the stand-down (the
safe direction); only `claude[bot]` can be T_last.

KNOWN LIMIT: `claude[bot]` is also the login of the steward, chief and
project-manager, so their comments count as a "trace". `committer.date` is the
author's clock, not the push time, so a commit made before T_last and pushed after
it reads as old. Both err toward a wasted stand-down at worst, never toward
dropping a QA FAIL or red-gates entry (rule 1 and 4 still see those).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_queue  # noqa: E402  (cycle_queue imports THIS module lazily, inside stale_reason)

Runner = Callable[[list[str]], str]

TRACE_BOT = "claude[bot]"
#: PR needs `main` merged into it, or GitHub has not said yet.
NEEDS_MAIN = ("behind", "dirty", "unknown", "")

_PRS_JQ = ".[] | {number, ref: .head.ref, sha: .head.sha}"
_COMMENTS_JQ = ('.[] | "\\(.user.login)\\t\\(.created_at)\\t'
                '\\(.body | test("^QA: (PASS|FAIL)"))\\t\\(.body | startswith("QA:"))"')


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))


def parse_comments(raw: str) -> list[tuple[str, datetime, bool, bool]]:
    """(login, created_at, is_verdict, is_qa) per line; raises ValueError on a bad line."""
    out = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        login, when, verdict, qa = line.split("\t")
        out.append((login, _ts(when), verdict == "true", qa == "true"))
    return out


def decide(entry_created: datetime, comments: list[tuple[str, datetime, bool, bool]],
           head_date: datetime, state: str) -> tuple[str, datetime] | None:
    """The pure rule over facts already read: (why, T_last) to stand down, else None."""
    traces = [when for who, when, _v, qa in comments if who == TRACE_BOT and not qa]
    if not traces:
        return None
    t_last = max(traces)
    if t_last <= entry_created:
        return None
    if any(v and when > t_last for _who, when, v, _qa in comments):
        return None
    if head_date > t_last:
        return None
    if state in NEEDS_MAIN:
        return None
    return f"last cycle left its trace at {t_last:%Y-%m-%d %H:%M}Z", t_last


def nothing_new(gh: Runner, repo: str, e: "cycle_queue.Entry") -> str | None:
    """A reason to stand an `issue` entry down because nothing is new, else None."""
    if e.kind != "issue":
        return None
    try:
        reason = _nothing_new(gh, repo, e)
    except Exception:  # noqa: BLE001 -- fail OPEN: any read or parse problem re-enters
        return None
    if reason:
        _summary(reason)
    return reason


def _nothing_new(gh: Runner, repo: str, e: "cycle_queue.Entry") -> str | None:
    owned = []
    for line in gh(["api", f"repos/{repo}/pulls?state=open&per_page=100", "--jq", _PRS_JQ]).splitlines():
        if not line.strip():
            continue
        pr = json.loads(line)
        m = cycle_queue._OWNED_BRANCH.match(pr.get("ref") or "")
        if m and int(m.group(1)) == e.target:
            owned.append(pr)
    if len(owned) != 1 or not owned[0].get("sha"):
        return None
    pr = owned[0]
    comments: list[tuple[str, datetime, bool, bool]] = []
    for n in (e.target, pr["number"]):
        comments += parse_comments(gh(["api", "--paginate", f"repos/{repo}/issues/{n}/comments?per_page=100",
                                       "--jq", _COMMENTS_JQ]))
    head_date = _ts(gh(["api", f"repos/{repo}/commits/{pr['sha']}", "--jq", ".commit.committer.date"]))
    state = gh(["api", f"repos/{repo}/pulls/{pr['number']}", "--jq", ".mergeable_state"]).strip()
    got = decide(_ts(e.created_at), comments, head_date, state)
    if got is None:
        return None
    why, _t = got
    return (f"nothing new since the last cycle on issue #{e.target}: {why}, PR #{pr['number']} head "
            f"`{pr['sha'][:7]}` is no newer, no QA verdict has come since, and the PR does not "
            f"need main merged in (`{state}`). A cycle would re-read the same state.")


def _summary(reason: str) -> None:
    """Show the stand-down in the run summary, so the saving is countable."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"- re-entry stand-down (#1255): {reason}\n")
    except OSError:
        pass
