#!/usr/bin/env python3
"""A durable queue in front of `agent-work`, so a dispatch is never dropped.

WHY THIS EXISTS
---------------
`agent-work` runs one cycle at a time PER LANE (`agent-work` / `agent-work-qa`), and
GitHub keeps at most ONE pending run per group: a third dispatch while one is
running and one is waiting CANCELS the waiting one, silently. So
`scripts/dispatch_cycle.sh` refused to dispatch while a cycle was in flight and
said the ruling "waits for the next run" -- but nothing ever came back for it.
For `qa-on-green` it was worse: its one-dispatch-per-commit marker was already
written, so that commit could never be dispatched again (#560). Measured on
PR #649: two green heads in one day, both deferred, neither ever reviewed.

So a deferred dispatch is now QUEUED, and the queue is drained when the slot
actually frees.

WHERE THE QUEUE LIVES
---------------------
As hidden marker comments, one per entry:

    <!-- agent-work-queue: kind=pr target=642 by=qa-on-green -->

on an issue or PR the writer can already comment on -- the target itself, or,
for `qa-on-green` (which may write PRs but not issues), the PR it is handling.
No new store, no label, and no permission any caller lacks. In particular no
LABEL: `qa-on-green` is barred from writing labels so it can never hand itself
`qa-pass`, and a queue that needed one would reopen that.

ONLY `github-actions[bot]` ENTRIES COUNT. Every writer uses `github.token`. An
entry anyone else wrote -- an outsider pasting the marker into a comment -- is
ignored, or it would aim a ~50-minute cycle at a target nobody ruled on.

HOW IT DRAINS
-------------
SINCE 2026-11-17 EVERY DISPATCH IS QUEUED, not just a busy one (#1185, design
#1184). A handler -- qa-on-green, red_gates, pr_fix_after_qa, the steward,
chief -- hands its ruling to `scripts/dispatch_cycle.sh`, which appends an entry
here and wakes `agent-queue.yml`. It starts nothing itself. The event used to
live INSIDE the handler's workflow run when the lane was idle, so a run GitHub
cancelled (one pending run per concurrency group) took the event with it:
qa-on-green runs 44059296498 and 44059273106 were cancelled on 2026-11-17 and
#1165, then #1171, got no QA round. An entry written first survives any run.

`drain` is the ONLY code that starts an `agent-work` cycle (tests pin it). It
runs when an `agent-work` run COMPLETES, when a handler wakes it, and hourly
(the backstop, #1186), so the slot is genuinely free and a cancelled or
duplicated drain loses nothing: the next one re-reads every entry. Since
2026-11-03 there are two lanes (build, QA) and `drain` starts at most one
entry PER FREE LANE -- up to two per run -- plus at most one `measure` run.

ENTRIES ARE KEYED (kind, target, head) where a head exists, and a timer's
entry by (timer key, due) -- `scripts/timers.py`. A key appended twice is one
entry: the second append sees the first and adds nothing.

FOLD. When `drain` starts an entry, every other pending entry for the SAME
TARGET is marked `folded into run <id>`. Same target means the same PR (a
`pr`/`fix_pr` entry, or an `issue` entry qa-on-green or red_gates wrote ON
that PR), or the same issue. Within a target a FIX outranks a QA request: a
`fix_pr` or `issue` cycle pushes, the push is a new head, and a new head earns
its own QA round from qa-on-green -- whereas a round on the pre-fix head
judges code that is about to change. So the fix is started and the round is
folded into it, never the reverse. Equal rank goes oldest first.

An entry is consumed by editing its marker, never by deleting the comment, so
the record of what was queued, by whom, and what became of it stays readable:

    agent-work-queue-claimed: ...        this drain is starting it
    agent-work-queue-taken: run=<id>     dispatched, run verified alive
    agent-work-queue-folded: ...         covered by another entry's run
    agent-work-queue-dropped: <reason>   the carrier refused it (closed, a PR
                                         that already carries qa-pass, ...)

A `claimed` entry whose drain died (cancelled, timed out) is recovered by the
next drain once it is CLAIM_TTL old: taken if a matching run appeared, else
returned to pending.

Dispatching itself is NOT reimplemented here: `drain` hands the ruling to
`scripts/dispatch_cycle.sh` in drain mode (`CYCLE_CARRIER=drain`), the one
carrier every dispatcher shares. `measure` entries (a scoring run, fired by an
analyst timer) are the exception: they start `agent-measure.yml`, see
`drain_measure`.

EXIT CODES
----------
  0  done (queued, already queued, drained one, or nothing to drain)
  1  could not do what was asked (an API write failed)
  2  bad arguments
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

MARK = "agent-work-queue"
WRITER = "github-actions[bot]"
#: How far back an entry is still worth starting. A queued round older than
#: this is about a head that has almost certainly moved on.
MAX_AGE_DAYS = 7
KINDS = ("issue", "pr", "fix_pr", "measure")
#: `head=` and `key=` are optional so entries written before 2026-11-17 parse.
_FIELDS = (r"kind=(issue|pr|fix_pr|measure) target=([0-9]+) by=([A-Za-z0-9_.-]+)"
           r"(?: head=([0-9a-f]{40}))?(?: key=([A-Za-z0-9_.:-]+))? -->")
ENTRY = re.compile(r"<!-- agent-work-queue: " + _FIELDS)
#: Any state: pending (bare marker) or a suffixed one.
ANY_ENTRY = re.compile(r"<!-- agent-work-queue(?:-(claimed|taken|dropped|folded))?: " + _FIELDS)
_KEY = re.compile(r"[A-Za-z0-9_.:-]+")
_HEAD = re.compile(r"[0-9a-f]{40}")
#: A claim older than this belongs to a drain that died: the job's own
#: timeout is 30 minutes (15 before the 2026-11-20 heartbeat doze), so a live
#: drain never holds a claim this long.
CLAIM_TTL = timedelta(minutes=31)
_BY = re.compile(r"[^A-Za-z0-9_.-]+")
CARRIER = Path(__file__).resolve().parent / "dispatch_cycle.sh"
#: The carrier's two rc=1 messages that mean "the ruling was fine, the RUN
#: failed" -- retry, never drop. Every other rc=1 is a refusal of the ruling.
TRANSIENT = ("created no new agent-work run", "it did not run a cycle",
             # the carrier found a cycle running after all and could not write
             # the re-queue entry: the ruling is fine, the write failed.
             "could NOT be queued")
#: Times a ruling whose RUN died goes back in the queue before it is dropped.
#: Without a bound it never ends (#675 QA round 2): the dead `agent-work` run
#: COMPLETES, which fires `agent-queue` again, which dispatches the same entry
#: again -- #421's shape lasted three days. Counted from the entry's own
#: `**Pending:**` notes, so it needs no new state, label or store.
MAX_RETRIES = 2

Runner = Callable[[list[str]], str]


def run_gh(args: list[str]) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}... failed: {p.stderr.strip()[:300]}")
    return p.stdout


@dataclass(frozen=True)
class Entry:
    comment_id: int
    kind: str
    target: int
    by: str
    created_at: str
    body: str
    state: str = "pending"
    head: str = ""
    key: str = ""
    #: The issue or PR the entry is written on (from the comment's issue_url);
    #: 0 when unknown. qa-on-green writes an `issue=` entry on its PR.
    on: int = 0
    updated_at: str = ""


def entries(gh: Runner, repo: str, now: datetime | None = None) -> list[Entry]:
    """Every entry in every state from the last MAX_AGE_DAYS, oldest first. ONE
    paginated call covers every issue and PR in the repo, which is why the
    queue can live on whichever item its writer may comment on."""
    since = ((now or datetime.now(timezone.utc)) - timedelta(days=MAX_AGE_DAYS)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = gh(["api", "--paginate",
              f"repos/{repo}/issues/comments?since={since}&sort=created&direction=asc&per_page=100",
              "--jq", '.[] | {id, body, created_at, updated_at, issue_url, login: .user.login}'])
    out: list[Entry] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        if c.get("login") != WRITER:
            continue
        m = ANY_ENTRY.search(c.get("body") or "")
        if not m:
            continue
        on = re.search(r"/issues/([0-9]+)$", c.get("issue_url") or "")
        out.append(Entry(int(c["id"]), m.group(2), int(m.group(3)), m.group(4),
                         c.get("created_at") or "", c.get("body") or "",
                         state=m.group(1) or "pending", head=m.group(5) or "",
                         key=m.group(6) or "", on=int(on.group(1)) if on else 0,
                         updated_at=c.get("updated_at") or c.get("created_at") or ""))
    out.sort(key=lambda e: (e.created_at, e.comment_id))
    return out


def pending(gh: Runner, repo: str, now: datetime | None = None) -> list[Entry]:
    """Untaken entries, oldest first."""
    return [e for e in entries(gh, repo, now) if e.state == "pending"]


def _duplicate(e: Entry, kind: str, target: int, head: str, key: str) -> bool:
    """Is `e` the same event as the one being appended?

    A TIMER entry (`key`) is one event for ever: a double fire of the same
    (timer, due) must add nothing even after the first entry ran or was
    dropped. A `claimed` entry is skipped so the carrier's race re-queue
    (drain mode, a cycle appeared after the claim) can still write its fresh
    entry. Anything else is the same event only while it is still PENDING --
    a later re-ruling of a target whose round has run is new information --
    and two different heads are two events (the fold merges them at drain)."""
    if (e.kind, e.target) == (kind, target):
        if key or e.key:
            return e.key == key and e.state != "claimed"
        return e.state == "pending" and (not head or not e.head or e.head == head)
    return False


def enqueue(gh: Runner, repo: str, kind: str, target: int, by: str, on: int,
            head: str = "", key: str = "") -> int:
    by = _BY.sub("-", by).strip("-") or "unknown"
    if head and not _HEAD.fullmatch(head):
        print(f"::warning::ignoring a head that is not a 40-hex sha: {head[:60]!r}")
        head = ""
    if key and not _KEY.fullmatch(key):
        print(f"::error::refusing an unparseable key {key[:60]!r} for {kind}={target}")
        return 2
    try:
        queued = entries(gh, repo)
    except (RuntimeError, ValueError) as exc:
        print(f"::error::could not read the queue before adding {kind}={target}: {exc}")
        return 1
    for e in queued:
        if _duplicate(e, kind, target, head, key):
            print(f"already queued: {kind}={target} (by {e.by}, comment {e.comment_id}, "
                  f"{e.state}). Not adding a second entry.")
            return 0
    fields = f"kind={kind} target={target} by={by}"
    if head:
        fields += f" head={head}"
    if key:
        fields += f" key={key}"
    body = (f"<!-- {MARK}: {fields} -->\n"
            f"**Queued for `agent-queue`:** `{kind}={target}`, ruled by `{by}`"
            + (f" at `{head[:7]}`" if head else "") + ".\n\n"
            f"Every dispatch is written here first (#1185), so a cancelled Actions run "
            f"cannot lose it. `agent-queue` is the only worker: it starts this entry when "
            f"its lane is free -- within the hour at worst, on its hourly backstop -- and "
            f"edits this comment when it does.")
    try:
        gh(["api", "-X", "POST", f"repos/{repo}/issues/{on}/comments", "-f", f"body={body}"])
    except RuntimeError as exc:
        print(f"::error::could not queue {kind}={target}: {exc}")
        return 1
    print(f"::notice::queued {kind}={target} (ruled by {by}) on #{on}")
    return 0


#: TWO LANES since 2026-11-03 (owner's request). A judge-only QA round
#: (`pr=`) never pushes, so it cannot conflict with a build cycle and need not
#: wait 45 minutes behind one. agent-work.yml puts `pr=` runs in the
#: `agent-work-qa` concurrency group and names them "QA round: PR #<n>"
#: (`run-name:`), because `gh run list` cannot show a run's inputs. A run
#: started before that change is titled "Agent work" and counts as build.
QA_TITLE = "QA round"
LANES = ("build", "qa")


def lane_of(kind: str) -> str:
    return "qa" if kind == "pr" else "build"


def lane_jq(lane: str) -> str:
    """The jq that counts running agent-work runs in ONE lane. dispatch_cycle.sh
    carries the same two selects; tests/test_cycle_queue.py pins they agree."""
    title = f'(.displayTitle | startswith("{QA_TITLE}"))'
    pick = title if lane == "qa" else f"({title} | not)"
    return f'[.[] | select(.status != "completed") | select({pick})] | length'


def busy(gh: Runner, repo: str, lane: str = "build") -> bool:
    """Is a cycle running in THIS lane? Unreadable counts as busy, as in the carrier."""
    try:
        n = gh(["run", "list", "--repo", repo, "--workflow", "agent-work.yml", "--limit", "20",
                "--json", "status,displayTitle", "--jq", lane_jq(lane)])
    except RuntimeError:
        return True
    return n.strip() != "0"


def _marker(state: str) -> str:
    return f"<!-- {MARK}: " if state == "pending" else f"<!-- {MARK}-{state}: "


def restate(gh: Runner, repo: str, cid: int, body: str, frm: str, to: str,
            note: str = "") -> str:
    """Move one entry from state `frm` to `to` by editing its marker; return the
    new body. `pending` is the bare marker; every other state is a suffix, so a
    non-pending entry never matches ENTRY and is never started again."""
    new = body.replace(_marker(frm), _marker(to), 1)
    if note:
        new += f"\n\n**{to.capitalize()}:** {note}"
    gh(["api", "-X", "PATCH", f"repos/{repo}/issues/comments/{cid}", "-f", f"body={new}"])
    return new


def mark(gh: Runner, repo: str, e: Entry, state: str, note: str) -> None:
    restate(gh, repo, e.comment_id, e.body, "pending", state, note)


#: The branch shapes that carry an owning issue -- the same three qa-on-green
#: reads (`issue/<n>-`, `partial/<n>-`, `fix/<n>-`).
_OWNED_BRANCH = re.compile(r"^(?:issue|partial|fix)/(\d+)-")


#: The workflows whose runs decide `blocked`: `pr-gates` (check `gates`) and
#: `verify-build` (check `build-gates`) are BOTH required, so a PR is waiting only
#: when neither is red. tests/test_cycle_queue.py pins both names to `name:` in
#: their workflow files and the pair to scripts/collect_gate_failures.py's
#: `GATE_WORKFLOWS`, because a rename would make every PR read as "no gates run"
#: and quietly restore the drain-into-a-stand-down loop. Neither workflow is
#: path-filtered (verify-build's `on:` has no `paths:`; a measurements-only diff
#: still runs the job and concludes success), so a MISSING run is uncertainty,
#: not "nothing to wait for".
GATES_WORKFLOW = "PR gates"
BUILD_WORKFLOW = "verify-build"
GATE_WORKFLOWS = (GATES_WORKFLOW, BUILD_WORKFLOW)
_SHA = re.compile(r"[0-9a-f]{40}")
#: Conclusions of a COMPLETED gates run that leave the PR nothing to wait for.
_RED = ("failure", "timed_out", "startup_failure", "cancelled")


def _gates_red(gh: Runner, repo: str, sha: str) -> bool | None:
    """Are the required gates on `sha` red? Reads the LATEST run of each workflow
    in GATE_WORKFLOWS. True: either is finished and red, so a cycle has a fix to
    make. False: both are present and each is running/queued or green, so
    `blocked` is only GitHub waiting for the merge. None: a run is missing, one
    ended some other way (skipped), or the answer is unreadable. The caller
    treats ONLY False as waiting.

    Read through the Actions API, as scripts/collect_gate_failures.py does --
    not `commits/<sha>/check-runs`, which needs a `checks` scope `agent-queue`
    does not hold. `event=pull_request` keeps a push-triggered run of the same
    name off the answer. The newest run is picked by `[created_at, id]`: two runs
    created in the same second tie on the first key, and `last` would otherwise
    take whichever the API listed first."""
    if not _SHA.fullmatch(sha or ""):
        return None
    jq = ('.workflow_runs | group_by(.name)[] | sort_by([.created_at, .id]) | last '
          '| "\\(.status) \\(.conclusion) \\(.name)"')
    try:
        raw = gh(["api", f"repos/{repo}/actions/runs?head_sha={sha}&event=pull_request&per_page=50",
                  "--jq", jq])
    except RuntimeError:
        return None
    latest: dict[str, tuple[str, str]] = {}
    for line in raw.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            latest[parts[2]] = (parts[0], parts[1])
    verdicts: list[bool | None] = []
    for workflow in GATE_WORKFLOWS:
        if workflow not in latest:
            verdicts.append(None)
            continue
        status, conclusion = latest[workflow]
        if status != "completed" or conclusion == "success":
            verdicts.append(False)
        else:
            verdicts.append(True if conclusion in _RED else None)
    if True in verdicts:
        return True
    return None if None in verdicts else False


def _mergeable_passed_pr(gh: Runner, repo: str, issue: int) -> int | None:
    """An open PR for `issue` that carries `qa-pass`, whose `QA: PASS` names its
    CURRENT head, and that GitHub reports `mergeable: true` -- or is `blocked`
    only while a `gates` run is still going or has passed (#1207) -- or None.
    Any read failure answers None (start the cycle).

    The head check is 2026-11-15: PR #1058 held `qa-pass` from 274e42f while its
    head was 98f14fb with `gates` red. red_gates.py queued `issue=1027` to fix
    it, and this function dropped the entry twice as "waiting to merge" --
    agent-merge refuses a stale pass (#823), so nothing was waiting and the red
    PR had no remaining route to green."""
    try:
        raw = gh(["api", f"repos/{repo}/pulls?state=open&per_page=100",
                  "--jq", ".[] | {number, ref: .head.ref, sha: .head.sha, labels: [.labels[].name]}"])
    except RuntimeError:
        return None
    for line in raw.splitlines():
        try:
            pr = json.loads(line)
        except json.JSONDecodeError:
            continue
        m = _OWNED_BRANCH.match(pr.get("ref") or "")
        if not m or int(m.group(1)) != issue or "qa-pass" not in pr.get("labels", []):
            continue
        try:
            # mergeable_state, not mergeable (2026-11-17): `mergeable: true` means
            # only "no conflict" and ignores checks. #1121, #1127, #1136 and #1138
            # each had a QA PASS on their head, then went red on that SAME head,
            # and their red-gates fix was dropped as "waiting to merge" while
            # GitHub reported them `blocked`. Only `clean` (or `has_hooks`) is
            # actually waiting to merge; anything else starts the cycle.
            state = gh(["api", f"repos/{repo}/pulls/{pr['number']}", "--jq", ".mergeable_state"]).strip()
            mergeable = "true" if state in ("clean", "has_hooks") else state
            # `blocked` is not one thing (#1207). It is red gates -- a cycle has a
            # fix to make -- but also a required check still RUNNING, which is a PR
            # waiting to merge. Only when BOTH required workflows' latest runs are
            # running or green does it count as waiting; a red one (either), a
            # missing one or an unreadable answer starts the cycle.
            if state == "blocked" and _gates_red(gh, repo, pr.get("sha") or "") is False:
                mergeable = "true"
        except RuntimeError:
            continue
        if mergeable == "true":
            try:
                pass_lines = gh(["api", "--paginate", f"repos/{repo}/issues/{pr['number']}/comments?per_page=100",
                                 "--jq", '.[] | select(.body | startswith("QA: PASS")) '
                                         '| "\\(.user.login)\\t\\(.body | split("\\n")[0])"'])
            except RuntimeError:
                continue
            if pr.get("sha") and _pass_names_head(pass_lines, repo, pr["sha"]):
                return pr["number"]
    return None


def _pass_names_head(lines: str, repo: str, head: str) -> bool:
    """True when a `QA: PASS` verdict from `claude[bot]` or the repo owner names
    `head` on its first line -- the same test agent-merge's `QA verdict` step
    applies before it will merge."""
    trusted = {"claude[bot]", repo.split("/")[0]}
    for line in lines.splitlines():
        who, _, first = line.partition("\t")
        if who in trusted and head in first:
            return True
    return False


def stale_reason(gh: Runner, repo: str, e: Entry) -> str | None:
    """A reason NOT to start this entry that the carrier would not catch. The
    carrier already refuses a closed target; a PR that has since been given
    `qa-pass` is open and would pass, and a round on it is ~50 minutes spent
    re-deciding a decided question.

    An ISSUE entry is dropped only when an open PR for that issue holds
    `qa-pass` AND GitHub reports it mergeable -- i.e. it really is waiting to
    merge. Measured 2026-11-03 18:52Z: an `issue=431` entry was drained twice
    while PR #694 held `qa-pass`; each cycle stood down in ~35s, the carrier
    read that as died-on-arrival, retried, and turned `agent-queue` red twice.

    The issue's OWN `qa-pass` label is only a prefilter, never the reason
    (QA round 1 on #704). `qa_verdict.sh` writes the verdict to the issue too,
    so the label survives two states where a cycle IS the next step: a
    `qa-pass` PR that has gone CONFLICTING (the #608 case -- the steward queues
    `issue=<n>` to run merge_main_into_branch.py, and agent-merge skips a
    conflicting PR by design, #403), and a `partial/` PR that merged with work
    still open. An unknown `mergeable` (GitHub still computing) also starts
    the cycle: a wasted stand-down costs ~35s, a wrongly dropped entry is
    permanent.

    Measured 2026-11-18 (#1207): PR #1227 for #1226 held `qa-pass` and was
    `blocked` while a second `gates` run was in progress; the entry was drained
    anyway, the cycle stood down in under 90s and the carrier read that as a
    dead run. PR #1199 (#1163) merged 14 minutes after its drain, and
    `agent-queue` had gone red three times in between."""
    try:
        labels = gh(["api", f"repos/{repo}/issues/{e.target}", "--jq", "[.labels[].name] | join(\",\")"])
    except RuntimeError:
        return None
    passed = "qa-pass" in labels.strip().split(",")
    if e.kind == "fix_pr":
        # A FIX for a session PR (2026-11-13). Drop it only when the PR has
        # since passed QA on its current head: then there is nothing to fix.
        # Anything unreadable starts it; the fix run re-reads the verdict.
        if not passed:
            return None
        try:
            head = gh(["api", f"repos/{repo}/pulls/{e.target}", "--jq", ".head.sha"]).strip()
            pass_lines = gh(["api", "--paginate", f"repos/{repo}/issues/{e.target}/comments?per_page=100",
                             "--jq", '.[] | select(.body | startswith("QA: PASS")) '
                                     '| "\\(.user.login)\\t\\(.body | split("\\n")[0])"'])
        except RuntimeError:
            return None
        if head and _pass_names_head(pass_lines, repo, head):
            return (f"PR #{e.target} passed QA at its head `{head[:7]}` since this fix was "
                    f"queued; there is nothing left to fix.")
        return None
    if e.kind != "pr":
        pr = _mergeable_passed_pr(gh, repo, e.target) if passed else None
        if pr is None:
            return None
        return (f"issue #{e.target}'s PR #{pr} carries `qa-pass` and is mergeable (or "
                f"blocked only on required gates that are not red); it is waiting to merge, "
                f"and a cycle would re-decide passed work.")
    # A round that has ALREADY ruled on the current head since this entry was
    # queued. The case QA round 1 on #675 exposed: once a busy loop is no
    # reason to hold back, the steward can queue a round for the very PR the
    # running cycle is reviewing, and draining it would be a second ~50-minute
    # round on the same commit. `qa_verdict.sh`'s comment names the SHA.
    try:
        head = gh(["api", f"repos/{repo}/pulls/{e.target}", "--jq", ".head.sha"]).strip()
        ruled = gh(["api", "--paginate", f"repos/{repo}/issues/{e.target}/comments?per_page=100",
                    "--jq", '.[] | select(.body | test("^QA: (PASS|FAIL)")) '
                            '| "\\(.created_at) \\(.body | split("\\n")[0])"'])
        # `qa-pass` decides the PR only for the commit it was given on (#823).
        # A label cannot say which commit it is about and survives a push, so
        # agent-merge also needs a `QA: PASS` comment naming the head, and
        # qa-on-green treats a stale label as no verdict and queues a round on
        # the new head. Dropping that round on the bare label stranded PR #812:
        # refused by agent-merge, ignored by every dispatcher, and the one
        # dispatch qa-on-green gets per commit already spent.
        pass_lines = gh(["api", "--paginate", f"repos/{repo}/issues/{e.target}/comments?per_page=100",
                         "--jq", '.[] | select(.body | startswith("QA: PASS")) '
                                 '| "\\(.user.login)\\t\\(.body | split("\\n")[0])"']) if passed else ""
    except RuntimeError:
        return None
    if passed and head and _pass_names_head(pass_lines, repo, head):
        return (f"PR #{e.target} already carries `qa-pass` for its head `{head[:7]}`; "
                f"a round would re-decide it.")
    for line in ruled.splitlines():
        when, _, first = line.partition(" ")
        if head and when > e.created_at and f"`{head}`" in first:
            return (f"a QA round already ruled on PR #{e.target} at `{head[:7]}` after "
                    f"this was queued; a second round on the same commit is waste.")
    return None


Carrier = Callable[..., tuple[int, dict[str, str], str]]


def run_carrier(ruling: str, who: str, entry: Entry | None = None) -> tuple[int, dict[str, str], str]:
    """Hand ONE ruling to dispatch_cycle.sh IN DRAIN MODE; return (rc, exported
    env, output). `CYCLE_CARRIER=drain` is what lets the carrier start a run:
    without it the carrier only appends to this queue (#1185), so this function
    is the single place a cycle can be started from. The entry's head, key and
    location ride along so a race re-queue writes the same event back."""
    with tempfile.TemporaryDirectory() as d:
        rf, envf = Path(d) / "ruling.txt", Path(d) / "env"
        rf.write_text(ruling + "\n")
        envf.touch()
        env = dict(os.environ, GITHUB_ENV=str(envf), CYCLE_CARRIER="drain")
        if entry is not None:
            env.update(QUEUE_HEAD=entry.head, QUEUE_KEY=entry.key,
                       QUEUE_ON=str(entry.on or entry.target))
        p = subprocess.run(["bash", str(CARRIER), str(rf), who],
                           capture_output=True, text=True, env=env, timeout=600)
        exported = dict(l.split("=", 1) for l in envf.read_text().splitlines() if "=" in l)
        return p.returncode, exported, p.stdout + p.stderr


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def group_of(e: Entry) -> tuple:
    """The TARGET an entry is about, for folding. An `issue` entry written on a
    different number was written on its PR (qa-on-green and red_gates queue on
    the PR they handle), so it belongs to that PR. An `issue` entry written on
    the issue itself stays apart: guessing its PR would fold on a guess."""
    if e.kind == "measure":
        return ("measure",)
    if e.kind in ("pr", "fix_pr"):
        return ("pr", e.target)
    if e.on and e.on != e.target:
        return ("pr", e.on)
    return ("issue", e.target)


#: FOLD PRECEDENCE within one target: a fix outranks a QA request. The fix
#: pushes; the push is a new head; qa-on-green gives the new head its own round.
#: A round on the pre-fix head would judge code about to change.
RANK = {"fix_pr": 2, "issue": 2, "pr": 1}


def _order(es: list[Entry]) -> list[Entry]:
    """Targets oldest first (by their oldest entry); within a target, the
    highest RANK first, then the oldest."""
    first: dict[tuple, tuple] = {}
    for e in sorted(es, key=lambda e: (e.created_at, e.comment_id)):
        first.setdefault(group_of(e), (e.created_at, e.comment_id))
    return sorted(es, key=lambda e: (first[group_of(e)], -RANK.get(e.kind, 0),
                                     e.created_at, e.comment_id))


def _fold(gh: Runner, repo: str, taken: Entry, run_id: str, es: list[Entry],
          handled: set[int]) -> None:
    g = group_of(taken)
    for o in es:
        if o.comment_id in handled or group_of(o) != g:
            continue
        handled.add(o.comment_id)
        try:
            restate(gh, repo, o.comment_id, o.body, "pending", "folded",
                    f"folded into run `{run_id}` (`{taken.kind}={taken.target}`, entry "
                    f"{taken.comment_id}). One run per target: a fix outranks a QA request, "
                    f"because the fix's push earns its own round.")
            print(f"folded {o.kind}={o.target} into run {run_id}")
        except RuntimeError as exc:
            # Left pending: the next drain sees it and folds or starts it. A
            # second run on one target is waste, never a lost event.
            print(f"::warning::could not fold {o.kind}={o.target} into run {run_id}: {exc}")


def _claim_run(e: Entry, runs: list[dict]) -> str | None:
    """The agent-work run a dead drain started for `e`, if one appeared within
    five minutes of the claim. Titles carry the target for `pr` and `fix_pr`;
    an `issue` run is titled "Agent work" and is matched by time alone."""
    want = {"pr": f"{QA_TITLE}: PR #{e.target}", "fix_pr": f"Agent work: fix PR #{e.target}",
            "issue": "Agent work"}.get(e.kind)
    try:
        claimed = _ts(e.updated_at or e.created_at)
    except ValueError:
        return None
    for r in runs:
        try:
            t = _ts(r.get("createdAt") or "")
        except ValueError:
            continue
        if (r.get("displayTitle") == want
                and claimed - timedelta(minutes=1) <= t <= claimed + timedelta(minutes=5)):
            return str(r.get("databaseId"))
    return None


def recover_claims(gh: Runner, repo: str, es: list[Entry], now: datetime) -> int:
    """A CANCELLED OR DEAD DRAIN IS HARMLESS. A drain killed between its claim
    and its `taken` edit left an entry `claimed`, where no drain looked again.
    Once a claim is CLAIM_TTL old its drain is gone: the entry is `taken` if a
    matching run appeared, else returned to the queue. Unreadable runs leave it
    for the next drain rather than risk a second cycle."""
    stale = []
    for e in es:
        if e.state != "claimed":
            continue
        try:
            if now - _ts(e.updated_at or e.created_at) > CLAIM_TTL:
                stale.append(e)
        except ValueError:
            continue
    if not stale:
        return 0
    try:
        runs = json.loads(gh(["run", "list", "--repo", repo, "--workflow", "agent-work.yml",
                              "--limit", "50", "--json", "databaseId,createdAt,displayTitle"]))
    except (RuntimeError, ValueError):
        print(f"::warning::{len(stale)} claimed entr(ies) from a dead drain; agent-work runs "
              f"unreadable, so they wait for the next drain.")
        return 0
    for e in stale:
        run = _claim_run(e, runs) if e.kind != "measure" else None
        if run:
            restate(gh, repo, e.comment_id, e.body, "claimed", "taken",
                    f"agent-work run `{run}` started at `{e.kind}={e.target}`; the drain that "
                    f"claimed this died before recording it.")
            print(f"recovered {e.kind}={e.target}: taken by run {run}")
        else:
            restate(gh, repo, e.comment_id, e.body, "claimed", "pending",
                    "the drain that claimed this died before dispatching it; returned to the queue.")
            print(f"recovered {e.kind}={e.target}: back to pending")
    return len(stale)


#: A `measure` entry from a timer waits this long past its due time for the
#: analyst's own daily slot (`0 21 * * *`, delivered 00:09-01:20Z over
#: 2026-11-05..09, measure_due.py) before the drain spends a run on it.
MEASURE_GRACE = timedelta(hours=4)
_TIMER_DUE = re.compile(r"\.(\d{8}T\d{4}Z)$")


def _cover_since(e: Entry) -> datetime:
    """An analyst run that STARTED at or after this scores the issue: a timer's
    due time (its key ends `.<YYYYMMDDTHHMMZ>`), else when the entry was written."""
    m = _TIMER_DUE.search(e.key)
    if m:
        return datetime.strptime(m.group(1), "%Y%m%dT%H%MZ").replace(tzinfo=timezone.utc)
    return _ts(e.created_at)


def analyst_runs(gh: Runner, repo: str, since: datetime) -> tuple[list[tuple[str, datetime]], bool]:
    """(completed runs whose `measure` job -- the analyst -- succeeded, with
    their start; whether an agent-measure run is still in flight). Only
    `schedule` and `workflow_dispatch` runs can carry the analyst."""
    raw = json.loads(gh(["api", f"repos/{repo}/actions/workflows/agent-measure.yml/runs"
                                f"?per_page=50&created=>={since:%Y-%m-%d}"]))
    done, inflight = [], False
    for r in raw.get("workflow_runs") or []:
        if r.get("status") != "completed":
            inflight = True
            continue
        if r.get("event") not in ("schedule", "workflow_dispatch"):
            continue
        jobs = json.loads(gh(["api", f"repos/{repo}/actions/runs/{r['id']}/jobs"])).get("jobs") or []
        if any(j.get("name") == "measure" and j.get("conclusion") == "success" for j in jobs):
            done.append((str(r["id"]), _ts(r.get("run_started_at") or r["created_at"])))
    return done, inflight


Starter = Callable[[Runner, str], "str | None"]


def start_measure(gh: Runner, repo: str) -> str | None:
    """Dispatch agent-measure (the analyst) and return the new run's id once it
    appears, or None. `gh workflow run` exits 0 on a run that never appears."""
    url = f"repos/{repo}/actions/workflows/agent-measure.yml/runs?per_page=1&event=workflow_dispatch"
    jq = ".workflow_runs[0].id // 0"
    before = gh(["api", url, "--jq", jq]).strip()
    gh(["workflow", "run", "agent-measure.yml", "--repo", repo])
    for _ in range(12):
        time.sleep(5)
        cand = gh(["api", url, "--jq", jq]).strip()
        if cand not in ("", "0", before):
            return cand
    return None


def drain_measure(gh: Runner, repo: str, ms: list[Entry], now: datetime,
                  starter: Starter = start_measure) -> bool:
    """Serve `measure` entries -- a scoring run an analyst timer asked for.
    ONE analyst run scores every issue, so every ripe entry folds into one
    run, and none is started when the daily slot already ran after the due
    time (the usual case: the timer then costs no Claude at all). Returns
    True when a dispatch failed (the drain goes red)."""
    if not ms:
        return False
    try:
        done, inflight = analyst_runs(gh, repo, min(_cover_since(e) for e in ms))
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"::warning::agent-measure runs unreadable ({exc}); {len(ms)} measure entr(ies) wait.")
        return False
    ripe = []
    for e in ms:
        cover = _cover_since(e)
        run = next((rid for rid, started in done if started >= cover), None)
        if run:
            mark(gh, repo, e, "taken", f"covered by analyst run `{run}`, which started after "
                                       f"{cover:%Y-%m-%dT%H:%MZ}; no extra run needed.")
            print(f"measure={e.target} covered by run {run}")
        elif now >= cover + (MEASURE_GRACE if _TIMER_DUE.search(e.key) else timedelta(0)):
            ripe.append(e)
    if not ripe:
        return False
    if inflight:
        print(f"an agent-measure run is in flight; {len(ripe)} measure entr(ies) wait for it.")
        return False
    first, rest = ripe[0], ripe[1:]
    body = restate(gh, repo, first.comment_id, first.body, "pending", "claimed")
    try:
        run_id = starter(gh, repo)
    except RuntimeError as exc:
        run_id = None
        print(f"::error::could not dispatch agent-measure: {exc}")
    if not run_id:
        restate(gh, repo, first.comment_id, body, "claimed", "pending",
                "the agent-measure dispatch did not produce a run; it stays queued.")
        print(f"::error::measure={first.target}: agent-measure did not start; returned to the queue.")
        return True
    restate(gh, repo, first.comment_id, body, "claimed", "taken",
            f"agent-measure run `{run_id}` started to score from the queue.")
    print(f"started measure={first.target} as agent-measure run {run_id}")
    _fold(gh, repo, first, run_id, rest, {first.comment_id})
    return False


def drain(gh: Runner, repo: str, carrier: Carrier = run_carrier, now: datetime | None = None,
          starter: Starter = start_measure) -> int:
    now = now or datetime.now(timezone.utc)
    allq = entries(gh, repo, now)
    if recover_claims(gh, repo, allq, now):
        allq = entries(gh, repo, now)
    failed = drain_measure(gh, repo, [e for e in allq if e.state == "pending" and e.kind == "measure"],
                           now, starter)
    # ONE ENTRY PER FREE LANE, oldest target first. A lane that starts
    # (or fails to start) a cycle is busy for the rest of this run.
    busy_lanes = {lane for lane in LANES if busy(gh, repo, lane)}
    if busy_lanes == set(LANES):
        print("a cycle is running in every lane (or the check failed); the queue waits.")
        return 1 if failed else 0
    queue = [e for e in allq if e.state == "pending" and e.kind != "measure"]
    if not queue:
        print("queue empty.")
        return 1 if failed else 0
    print(f"{len(queue)} queued; oldest target first, a fix before a QA request.")
    # One decision per TARGET. A target whose best entry's lane is busy waits
    # whole -- its QA request is not started beside a fix it is folded into.
    # A drop or a refusal hands the target's next entry its turn.
    settled: set[tuple] = set()
    handled: set[int] = set()
    for e in _order(queue):
        g = group_of(e)
        if g in settled or e.comment_id in handled:
            continue
        settled.add(g)
        lane = lane_of(e.kind)
        if lane in busy_lanes:
            continue
        reason = stale_reason(gh, repo, e)
        if reason:
            mark(gh, repo, e, "dropped", reason)
            print(f"dropped {e.kind}={e.target}: {reason}")
            handled.add(e.comment_id)
            settled.discard(g)
            continue
        # CLAIM BEFORE DISPATCH (QA round 1 on #675). Marking an entry only
        # AFTER a successful dispatch meant a failed PATCH left it pending, and
        # the next drain started the same cycle again (~50 Actions minutes a
        # turn). A claimed entry is no longer pending, so a failure from here on
        # can cost a ruling at worst, never a duplicate cycle.
        body = restate(gh, repo, e.comment_id, e.body, "pending", "claimed")
        handled.add(e.comment_id)
        retries = e.body.count("**Pending:**")
        try:
            rc, exported, out = carrier(f"{e.kind}={e.target}", f"queue({e.by})", entry=e)
        except (OSError, subprocess.TimeoutExpired) as exc:
            # The carrier itself could not run. Nothing is known about the
            # ruling, so it goes back -- counted, like any other retry -- rather
            # than being stranded in `claimed` where nothing would ever see it.
            restate(gh, repo, e.comment_id, body, "claimed", "pending",
                    f"the dispatch carrier could not run ({exc.__class__.__name__}); "
                    f"retry {retries + 1} of {MAX_RETRIES}.")
            print(f"::error::{e.kind}={e.target}: carrier failed to run: {exc}")
            failed = True
            busy_lanes.add(lane)
            continue
        print(out.rstrip())
        run_id = exported.get("DISPATCHED_RUN")
        if rc == 0 and run_id:
            restate(gh, repo, e.comment_id, body, "claimed", "taken",
                    f"agent-work run `{run_id}` started at `{e.kind}={e.target}` from the queue.")
            print(f"started {e.kind}={e.target} as run {run_id} ({lane} lane)")
            busy_lanes.add(lane)
            _fold(gh, repo, e, run_id, queue, handled)
            continue
        if rc == 1 and any(t in out for t in TRANSIENT) and "concluded 'success'" in out:
            # The run SUCCEEDED and left no trace on the target (#1207): the cycle
            # found nothing to do and stood down. A retry is the same cycle on the
            # same state, so it repeats itself -- measured 2026-11-17, three cycles
            # on #1163. A `failure` is a dead run and keeps its two retries below.
            restate(gh, repo, e.comment_id, body, "claimed", "dropped",
                    "the run succeeded and left no trace on the target; not retried, because "
                    "a green run that wrote nothing repeats itself.")
            print(f"::error::{e.kind}={e.target}: the dispatched run concluded 'success' and "
                  f"left no trace on the target. Dropped, not retried; see the carrier output above.")
            failed = True
            busy_lanes.add(lane)
            settled.discard(g)
            continue
        if rc == 1 and any(t in out for t in TRANSIENT) and retries < MAX_RETRIES:
            # The carrier ACCEPTED the ruling and the run did not survive -- the
            # #421 shape. That says nothing about the ruling, so it goes back in
            # the queue, and this run goes RED so the failure is seen rather
            # than reported as a green run that quietly dropped work. BOUNDED:
            # the third failure falls through to the drop below.
            restate(gh, repo, e.comment_id, body, "claimed", "pending",
                    f"the dispatched run did not start or died on arrival; "
                    f"retry {retries + 1} of {MAX_RETRIES}.")
            print(f"::error::{e.kind}={e.target}: the dispatched run did not start or died "
                  f"on arrival. Returned to the queue (retry {retries + 1} of {MAX_RETRIES}); "
                  f"see the carrier output above.")
            failed = True
            busy_lanes.add(lane)
            continue
        if rc == 1:
            restate(gh, repo, e.comment_id, body, "claimed", "dropped",
                    f"the dispatch carrier refused the ruling itself, or its run failed "
                    f"{MAX_RETRIES + 1} times (closed target, an issue number that is a PR, "
                    f"unparseable, or a run that never started) -- see the `agent-queue` log.")
            print(f"::error::{e.kind}={e.target} dropped; see the carrier output above.")
            # Retries ran out: the run kept dying, which is a failure someone
            # must see -- a red drain, not a green one with an annotation. A
            # plain refusal (closed target) is a legitimate outcome and stays green.
            if any(t in out for t in TRANSIENT):
                failed = True
            settled.discard(g)
            continue
        # rc 0 with no run: the carrier found a cycle in flight after all (a
        # race with a cron cycle or the chain step, the only other starters).
        # It could not see THIS entry -- it is
        # claimed, not pending -- so it has already written a fresh one for the
        # same target. Restoring this one would leave two (#675 QA round 2,
        # N2), so this one is closed and the carrier's entry is the live one.
        restate(gh, repo, e.comment_id, body, "claimed", "dropped",
                "a cycle appeared after the claim; the carrier queued a fresh entry for "
                "the same target, which replaces this one.")
        print(f"{e.kind}={e.target} not started (a cycle appeared); the carrier re-queued it.")
        busy_lanes.add(lane)
    return 1 if failed else 0


def main(argv: list[str], gh: Runner = run_gh) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("enqueue")
    q.add_argument("--kind", required=True, choices=KINDS)
    q.add_argument("--target", required=True, type=int)
    q.add_argument("--by", required=True)
    q.add_argument("--on", type=int, help="issue/PR to write the entry on (default: target)")
    q.add_argument("--head", default="", help="the PR head sha the event is about, if any")
    q.add_argument("--key", default="", help="a dedupe key (timers: timer.<key>.<due>)")
    sub.add_parser("drain")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::cycle_queue.py needs GH_REPO=owner/name")
        return 2
    if a.cmd == "enqueue":
        return enqueue(gh, repo, a.kind, a.target, a.by, a.on or a.target, a.head, a.key)
    try:
        return drain(gh, repo)
    except RuntimeError as exc:
        print(f"::error::drain failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
