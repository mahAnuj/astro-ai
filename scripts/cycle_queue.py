#!/usr/bin/env python3
"""A durable queue in front of `agent-work`, so a dispatch is never dropped.

WHY THIS EXISTS
---------------
`agent-work` runs one cycle at a time (`concurrency: group: agent-work`), and
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
`agent-queue.yml` runs `drain` when an `agent-work` run COMPLETES, so the slot
is genuinely free and nothing is dispatched into the cancellable pending slot.
It also runs when `agent-steward` completes (twice a day), a backstop for an
entry queued when no cycle was really running (an unreadable busy check counts
as busy) or a drain run that died. `drain` takes ONE entry per run, oldest
first, because one cycle at a time is the whole constraint.

An entry is consumed by editing its marker, never by deleting the comment, so
the record of what was queued, by whom, and what became of it stays readable:

    agent-work-queue-taken: run=<id>     dispatched, run verified alive
    agent-work-queue-dropped: <reason>   the carrier refused it (closed, a PR
                                         that already carries qa-pass, ...)

Dispatching itself is NOT reimplemented here: `drain` hands the ruling to
`scripts/dispatch_cycle.sh`, the one carrier every dispatcher shares.

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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

MARK = "agent-work-queue"
WRITER = "github-actions[bot]"
#: How far back an entry is still worth starting. A queued round older than
#: this is about a head that has almost certainly moved on.
MAX_AGE_DAYS = 7
ENTRY = re.compile(
    r"<!-- agent-work-queue: kind=(issue|pr) target=([0-9]+) by=([A-Za-z0-9_.-]+) -->")
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


def pending(gh: Runner, repo: str, now: datetime | None = None) -> list[Entry]:
    """Untaken entries, oldest first. ONE paginated call covers every issue and
    PR in the repo, which is why the queue can live on whichever item its
    writer may comment on."""
    since = ((now or datetime.now(timezone.utc)) - timedelta(days=MAX_AGE_DAYS)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = gh(["api", "--paginate",
              f"repos/{repo}/issues/comments?since={since}&sort=created&direction=asc&per_page=100",
              "--jq", '.[] | {id, body, created_at, login: .user.login}'])
    out: list[Entry] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        if c.get("login") != WRITER:
            continue
        m = ENTRY.search(c.get("body") or "")
        if not m:
            continue
        out.append(Entry(int(c["id"]), m.group(1), int(m.group(2)), m.group(3),
                         c.get("created_at") or "", c.get("body") or ""))
    out.sort(key=lambda e: (e.created_at, e.comment_id))
    return out


def enqueue(gh: Runner, repo: str, kind: str, target: int, by: str, on: int) -> int:
    by = _BY.sub("-", by).strip("-") or "unknown"
    try:
        queued = pending(gh, repo)
    except (RuntimeError, ValueError) as exc:
        print(f"::error::could not read the queue before adding {kind}={target}: {exc}")
        return 1
    for e in queued:
        if (e.kind, e.target) == (kind, target):
            print(f"already queued: {kind}={target} (by {e.by}, comment {e.comment_id}). "
                  f"Not adding a second entry.")
            return 0
    body = (f"<!-- {MARK}: kind={kind} target={target} by={by} -->\n"
            f"**Queued for `agent-work`:** `{kind}={target}`, ruled by `{by}`.\n\n"
            f"A cycle is already running, and `agent-work` runs one at a time. This "
            f"ruling is not dropped: `agent-queue` starts the oldest queued entry as "
            f"soon as the running cycle completes, and edits this comment when it does.")
    try:
        gh(["api", "-X", "POST", f"repos/{repo}/issues/{on}/comments", "-f", f"body={body}"])
    except RuntimeError as exc:
        print(f"::error::could not queue {kind}={target}: {exc}")
        return 1
    print(f"::notice::queued {kind}={target} (ruled by {by}) on #{on}")
    return 0


def busy(gh: Runner, repo: str) -> bool:
    """An unreadable answer counts as busy, exactly as in the carrier."""
    try:
        n = gh(["run", "list", "--repo", repo, "--workflow", "agent-work.yml", "--limit", "10",
                "--json", "status", "--jq", '[.[] | select(.status != "completed")] | length'])
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


def stale_reason(gh: Runner, repo: str, e: Entry) -> str | None:
    """A reason NOT to start this entry that the carrier would not catch. The
    carrier already refuses a closed target; a PR that has since been given
    `qa-pass` is open and would pass, and a round on it is ~50 minutes spent
    re-deciding a decided question."""
    if e.kind != "pr":
        return None
    try:
        labels = gh(["api", f"repos/{repo}/issues/{e.target}", "--jq", "[.labels[].name] | join(\",\")"])
    except RuntimeError:
        return None
    if "qa-pass" in labels.strip().split(","):
        return f"PR #{e.target} already carries `qa-pass`; a round would re-decide it."
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
    except RuntimeError:
        return None
    for line in ruled.splitlines():
        when, _, first = line.partition(" ")
        if head and when > e.created_at and f"`{head}`" in first:
            return (f"a QA round already ruled on PR #{e.target} at `{head[:7]}` after "
                    f"this was queued; a second round on the same commit is waste.")
    return None


Carrier = Callable[[str, str], tuple[int, dict[str, str], str]]


def run_carrier(ruling: str, who: str) -> tuple[int, dict[str, str], str]:
    """Hand ONE ruling to dispatch_cycle.sh; return (rc, exported env, output)."""
    with tempfile.TemporaryDirectory() as d:
        rf, envf = Path(d) / "ruling.txt", Path(d) / "env"
        rf.write_text(ruling + "\n")
        envf.touch()
        env = dict(os.environ, GITHUB_ENV=str(envf))
        p = subprocess.run(["bash", str(CARRIER), str(rf), who],
                           capture_output=True, text=True, env=env, timeout=600)
        exported = dict(l.split("=", 1) for l in envf.read_text().splitlines() if "=" in l)
        return p.returncode, exported, p.stdout + p.stderr


def drain(gh: Runner, repo: str, carrier: Carrier = run_carrier) -> int:
    if busy(gh, repo):
        print("a cycle is running (or the check failed); the queue waits for it to complete.")
        return 0
    entries = pending(gh, repo)
    if not entries:
        print("queue empty.")
        return 0
    print(f"{len(entries)} queued; oldest first.")
    failed = False
    for e in entries:
        reason = stale_reason(gh, repo, e)
        if reason:
            mark(gh, repo, e, "dropped", reason)
            print(f"dropped {e.kind}={e.target}: {reason}")
            continue
        # CLAIM BEFORE DISPATCH (QA round 1 on #675). Marking an entry only
        # AFTER a successful dispatch meant a failed PATCH left it pending, and
        # the next drain started the same cycle again (~50 Actions minutes a
        # turn). A claimed entry is no longer pending, so a failure from here on
        # can cost a ruling at worst, never a duplicate cycle.
        body = restate(gh, repo, e.comment_id, e.body, "pending", "claimed")
        retries = e.body.count("**Pending:**")
        try:
            rc, exported, out = carrier(f"{e.kind}={e.target}", f"queue({e.by})")
        except (OSError, subprocess.TimeoutExpired) as exc:
            # The carrier itself could not run. Nothing is known about the
            # ruling, so it goes back -- counted, like any other retry -- rather
            # than being stranded in `claimed` where nothing would ever see it.
            restate(gh, repo, e.comment_id, body, "claimed", "pending",
                    f"the dispatch carrier could not run ({exc.__class__.__name__}); "
                    f"retry {retries + 1} of {MAX_RETRIES}.")
            print(f"::error::{e.kind}={e.target}: carrier failed to run: {exc}")
            return 1
        print(out.rstrip())
        run_id = exported.get("DISPATCHED_RUN")
        if rc == 0 and run_id:
            restate(gh, repo, e.comment_id, body, "claimed", "taken",
                    f"agent-work run `{run_id}` started at `{e.kind}={e.target}` from the queue.")
            print(f"started {e.kind}={e.target} as run {run_id}")
            return 1 if failed else 0
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
            return 1
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
            continue
        # rc 0 with no run: the carrier found a cycle in flight after all (a
        # race with another dispatcher). It could not see THIS entry -- it is
        # claimed, not pending -- so it has already written a fresh one for the
        # same target. Restoring this one would leave two (#675 QA round 2,
        # N2), so this one is closed and the carrier's entry is the live one.
        restate(gh, repo, e.comment_id, body, "claimed", "dropped",
                "a cycle appeared after the claim; the carrier queued a fresh entry for "
                "the same target, which replaces this one.")
        print(f"{e.kind}={e.target} not started (a cycle appeared); the carrier re-queued it.")
        return 1 if failed else 0
    return 1 if failed else 0


def main(argv: list[str], gh: Runner = run_gh) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("enqueue")
    q.add_argument("--kind", required=True, choices=("issue", "pr"))
    q.add_argument("--target", required=True, type=int)
    q.add_argument("--by", required=True)
    q.add_argument("--on", type=int, help="issue/PR to write the entry on (default: target)")
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
        return enqueue(gh, repo, a.kind, a.target, a.by, a.on or a.target)
    try:
        return drain(gh, repo)
    except RuntimeError as exc:
        print(f"::error::drain failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
