#!/usr/bin/env python3
"""Liveness: is every event reaching an end, and is every ready PR merging? (#1186)

WHY THIS EXISTS
---------------
Every stall the week of 2026-11-17 was silent and found by the owner: cancelled
dispatches, dropped queue entries, four PRs with a QA PASS on their head
sitting about a day (#1121, #1127, #1136, #1138), a cleared PR waiting on a
throttled cron (#1132). Nothing in the loop asked "did this event finish?".
`detect_ops_regressions.py` reads committed measurements only, so it cannot
see an inbox entry or a PR's head; this reads the API, with no model.

WHAT IT RAISES, each naming its targets and its lever
-----------------------------------------------------
  inbox-stale     a queue entry still pending or claimed, or taken/folded into
                  a run that has not completed, more than INBOX_STALE after it
                  was written.
  ready-unmerged  an open AGENT_AUTHORS PR with green gates on its head, a
                  `QA: PASS` naming that head, no `qa-fail`, and no hold (or a
                  `chief-cleared` label plus `chief-cleared at <head>`), still
                  open more than READY_STALE after the PASS.
  red-unhandled   the latest gate run on an AGENT_AUTHORS PR's head failed more
                  than RED_STALE ago, and nothing live is handling it: no queue
                  entry for that PR at that head that is pending, claimed, or
                  taken by a run still going. A `fix dispatched at <head>`
                  marker alone does NOT count -- 2026-11-16/17 had exactly that
                  marker while its queue entry was dropped as "waiting to
                  merge". A `red gates noted at <head>` comment does count:
                  red_gates.py has routed that head to a session, by design.

Findings are the shape `file_ops_findings.py` files (`kind`, `level`, `title`,
`detail`), filed from agent-queue's hourly job with `--scope liveness`, so
they get one issue per kind, a comment only when the finding changes, and one
"cleared" comment when it goes.

API cost per run, measured against the shape of the calls: one paginated read
of the last week's comments (~15 pages), the open PRs, one page each of
agent-work, agent-measure, PR gates and verify-build runs, one runs lookup per
agent PR whose head is older than those pages, and one comments read per PR
that is a ready or red candidate.

EXIT CODES: 0 nothing found   1 at least one finding   2 could not read (NOT a pass)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_queue  # noqa: E402

Runner = Callable[[list[str]], str]

KINDS = ("inbox-stale", "ready-unmerged", "red-unhandled")
INBOX_STALE = timedelta(hours=6)
READY_STALE = timedelta(hours=6)
RED_STALE = timedelta(hours=2)
#: The two workflows whose red runs red_gates.py handles (qa-on-green's
#: `workflow_run` list). Matched by `name:`, newest run per head.
GATE_WORKFLOWS = {"pr-gates.yml": "PR gates", "verify-build.yml": "verify-build"}
_RUN = re.compile(r"run `(\d+)`")
_BRANCH_ISSUE = re.compile(r"^(?:issue|partial|fix)/(\d+)-")


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _hours(d: timedelta) -> str:
    return f"{d.total_seconds() / 3600:.0f}h"


def _json(gh: Runner, path: str) -> dict | list:
    return json.loads(gh(["api", path]))


def run_status(gh: Runner, repo: str) -> dict[str, str]:
    """run id -> status for the recent agent-work and agent-measure runs."""
    out: dict[str, str] = {}
    for wf in ("agent-work.yml", "agent-measure.yml"):
        for r in _json(gh, f"repos/{repo}/actions/workflows/{wf}/runs?per_page=100").get("workflow_runs") or []:
            out[str(r["id"])] = r.get("status") or ""
    return out


def _live(e: cycle_queue.Entry, status: dict[str, str]) -> bool:
    """Is this entry still on its way? Pending and claimed are. A taken or
    folded entry is while its run has not completed. A run not among the
    recent ones is old enough to have completed (a cycle is capped at 120m)."""
    if e.state in ("pending", "claimed"):
        return True
    if e.state in ("taken", "folded"):
        ids = _RUN.findall(e.body)
        return bool(ids) and status.get(ids[-1], "completed") != "completed"
    return False


def inbox_stale(es: list[cycle_queue.Entry], status: dict[str, str], now: datetime) -> list[str]:
    stale = []
    for e in es:
        try:
            age = now - _ts(e.created_at)
        except ValueError:
            continue
        if age > INBOX_STALE and _live(e, status):
            where = f"#{e.on}" if e.on else f"#{e.target}"
            stale.append(f"`{e.kind}={e.target}` on {where} ({e.state}, written {_hours(age)} ago, "
                         f"comment {e.comment_id})")
    return stale


def gate_runs(gh: Runner, repo: str) -> dict[str, dict[str, dict]]:
    """head sha -> workflow name -> its newest run."""
    out: dict[str, dict[str, dict]] = {}
    for wf, name in GATE_WORKFLOWS.items():
        for r in _json(gh, f"repos/{repo}/actions/workflows/{wf}/runs?per_page=100").get("workflow_runs") or []:
            sha = r.get("head_sha") or ""
            cur = out.setdefault(sha, {}).get(name)
            if cur is None or (r.get("created_at") or "") > (cur.get("created_at") or ""):
                out[sha][name] = r
    return out


def gate_runs_for(gh: Runner, repo: str, sha: str) -> dict[str, dict]:
    """The newest gate run per workflow for ONE head, for a head older than the
    shared page. One page of `PR gates` runs covered ~16h on 2026-11-17, and a
    PR stranded longer than that is exactly the one this check exists for."""
    out: dict[str, dict] = {}
    raw = _json(gh, f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50")
    for r in raw.get("workflow_runs") or []:
        name = r.get("name")
        if name in GATE_WORKFLOWS.values():
            cur = out.get(name)
            if cur is None or (r.get("created_at") or "") > (cur.get("created_at") or ""):
                out[name] = r
    return out


def _comments(gh: Runner, repo: str, n: int) -> list[dict]:
    raw = gh(["api", "--paginate", f"repos/{repo}/issues/{n}/comments?per_page=100",
              "--jq", '.[] | {body, created_at, login: .user.login}'])
    return [json.loads(l) for l in raw.splitlines() if l.strip()]


def _pass_at(comments: list[dict], head: str, trusted: set[str]) -> datetime | None:
    """When a trusted `QA: PASS` first named `head` on its first line."""
    for c in comments:
        body = c.get("body") or ""
        if c.get("login") in trusted and body.startswith("QA: PASS") and head in body.split("\n")[0]:
            return _ts(c["created_at"])
    return None


def _handled(es: list[cycle_queue.Entry], pr: dict, status: dict[str, str]) -> bool:
    num, head = pr["number"], pr["head"]["sha"]
    m = _BRANCH_ISSUE.match(pr["head"].get("ref") or "")
    issue = int(m.group(1)) if m else None
    for e in es:
        about = (cycle_queue.group_of(e) == ("pr", num)
                 or (e.kind == "issue" and issue is not None and e.target == issue))
        if about and (not e.head or e.head == head) and _live(e, status):
            return True
    return False


def find(gh: Runner, repo: str, now: datetime, authors: set[str]) -> list[dict]:
    owner = repo.split("/")[0]
    trusted = {"claude[bot]", owner}
    es = cycle_queue.entries(gh, repo, now)
    status = run_status(gh, repo)
    findings: list[dict] = []

    stale = inbox_stale(es, status, now)
    if stale:
        findings.append({
            "kind": "inbox-stale", "level": "amber", "targets": stale,
            "title": f"{len(stale)} queue entr(ies) with no end after {_hours(INBOX_STALE)}",
            "detail": ("Entries that are still pending, claimed, or riding a run that has not "
                       "completed:\n\n" + "\n".join(f"- {s}" for s in stale) + "\n\n"
                       "**Lever:** agent-queue drains every free lane on each wake and hourly. An "
                       "entry this old means its lane stayed busy or the drain is failing: read "
                       "`gh run list --workflow agent-queue.yml`, then drop or re-rule an entry "
                       "whose target has moved on.")})

    prs = _json(gh, f"repos/{repo}/pulls?state=open&per_page=100")
    gates = gate_runs(gh, repo)
    ready, red = [], []
    for pr in prs:
        login = (pr.get("user") or {}).get("login") or ""
        ref = (pr.get("head") or {}).get("ref") or ""
        if login not in authors or ref.startswith("measurements/"):
            continue
        num, head = pr["number"], pr["head"]["sha"]
        labels = {l.get("name") for l in pr.get("labels") or []}
        runs = gates.get(head) or gate_runs_for(gh, repo, head)
        green = (runs.get("PR gates") or {}).get("conclusion") == "success" and all(
            r.get("conclusion") != "failure" for r in runs.values())
        failed = [r for r in runs.values() if r.get("status") == "completed"
                  and r.get("conclusion") == "failure"]
        if green and "qa-pass" in labels and "qa-fail" not in labels:
            comments = _comments(gh, repo, num)
            when = _pass_at(comments, head, trusted)
            held = "needs-human-review" in labels
            cleared = "chief-cleared" in labels and any(
                f"chief-cleared at {head}" in (c.get("body") or "") for c in comments
                if c.get("login") in trusted)
            if when and (not held or cleared) and now - when > READY_STALE:
                ready.append(f"PR #{num} at `{head[:7]}`: QA PASS {_hours(now - when)} ago, gates "
                             f"green{', chief-cleared' if held else ''}")
        elif failed:
            red_at = max(_ts(r.get("updated_at") or r["created_at"]) for r in failed)
            if now - red_at <= RED_STALE or _handled(es, pr, status):
                continue
            comments = _comments(gh, repo, num)
            if any(f"qa-on-green: red gates noted at {head}" in (c.get("body") or "")
                   for c in comments if c.get("login") == cycle_queue.WRITER):
                continue
            marked = any(f"qa-on-green: fix dispatched at {head}" in (c.get("body") or "")
                         for c in comments if c.get("login") == cycle_queue.WRITER)
            names = ", ".join(sorted(r.get("name") or "?" for r in failed))
            red.append(f"PR #{num} at `{head[:7]}`: {names} red {_hours(now - red_at)} ago"
                       + ("; a fix was marked dispatched but no live queue entry carries it"
                          if marked else "; no fix dispatched"))
    if ready:
        findings.append({
            "kind": "ready-unmerged", "level": "red", "targets": ready,
            "title": f"{len(ready)} PR(s) ready but unmerged after {_hours(READY_STALE)}",
            "detail": ("Gates green on the head, a trusted `QA: PASS` naming it, no `qa-fail`, "
                       "and no hold left:\n\n" + "\n".join(f"- {s}" for s in ready) + "\n\n"
                       "**Lever:** agent-merge should have merged these. Dispatch "
                       "`gh workflow run agent-merge.yml --ref main` and read why it refuses "
                       "(`gh run list --workflow agent-merge.yml`): size, a stale pass, or a "
                       "check it cannot see.")})
    if red:
        findings.append({
            "kind": "red-unhandled", "level": "amber", "targets": red,
            "title": f"{len(red)} red PR(s) with no live fix after {_hours(RED_STALE)}",
            "detail": ("The latest gate run on each head failed and nothing in the queue is "
                       "fixing it:\n\n" + "\n".join(f"- {s}" for s in red) + "\n\n"
                       "**Lever:** queue the fix -- `fix_pr=<n>`, or `issue=<n>` for a branch "
                       "naming its issue -- through the steward's carrier; read the dropped "
                       "entry's reason first, because the drop is usually the defect.")})
    return findings


def main(argv: list[str], gh: Runner = cycle_queue.run_gh, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="write the findings JSON here (default: stdout)")
    a = ap.parse_args(argv[1:])
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::liveness.py needs GH_REPO=owner/name")
        return 2
    authors = {a for a in os.environ.get("AGENT_AUTHORS", "").split(",") if a} or {
        "claude[bot]", "github-actions[bot]", "shubhagya-publisher[bot]", repo.split("/")[0]}
    now = now or datetime.now(timezone.utc)
    try:
        findings = find(gh, repo, now, authors)
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"::error::liveness could not read the API: {exc}")
        return 2
    doc = json.dumps({"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "findings": findings},
                     indent=2)
    if a.out:
        Path(a.out).write_text(doc + "\n")
    else:
        print(doc)
    for f in findings:
        print(f"{f['level'].upper()} {f['kind']}: {f['title']}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
