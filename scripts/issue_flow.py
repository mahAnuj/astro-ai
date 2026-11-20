#!/usr/bin/env python3
"""Issue flow: what opened, what closed, who did each, and what shipped but stayed open.

WHY THIS EXISTS
---------------
Owner, 2026-11-18: *"Many prs have been merged but I don't see issue count
reducing"*. Measured 2026-11-15..18: 96 PRs merged, 59 issues closed, 73 opened,
131 open. The open count alone cannot say which of two very different things is
happening -- findings arriving faster than fixes, or fixes shipping and their
issues never closing. This block says which, so the reading is a number rather
than an argument.

WHAT IT WRITES -- the `trend` block of measurements/issues.json
---------------------------------------------------------------
For the last WINDOW_DAYS UTC days, today included (partial):

  days[]           date, opened, closed, net, open_end, opened_by{}, closed_by{}
  opened_by        who filed it (SOURCES):
                     ops       an `[OPS]` title (scripts/file_ops_findings.py). Its
                               label is `chore`, which half the backlog also carries,
                               so the title is the only reliable mark.
                     loop      claude[bot] / github-actions[bot] / shubhagya-publisher[bot]
                     audit     the repository owner's account -- audits and sessions
                     outsider  anyone else
  closed_by        who closed it (CLOSERS), from the issue's timeline: the `closed`
                   event's actor, and the closer's own comment within CLOSE_COMMENT_S
                   of it (`gh issue close --comment` posts one just before closing).
                   NOT the issue's last comment: measured 2026-11-18, the analyst's
                   score and the agent-timer marker land AFTER the close on most
                   closed issues, so the last comment names the wrong hand.
                     close-on-evidence  "Closed on production evidence"
                     cannot-reproduce   `cannot-reproduce` label, or CANNOT-REPRODUCE
                                        in the closing comment (/agent-cycle step 0)
                     main-red-report    "Green again on `main`" -- the red-main
                                        sentinel closing itself; not a fix closing,
                                        so it is kept out of `other`, where it would
                                        be most of the bucket
                     prioritise         closed by claude[bot] (agent-prioritise is the
                                        loop's only other closer), or by the owner's
                                        account with a comment headed "Closing" --
                                        /prioritise run from a session
                     owner              the owner's account, by hand
                     other              anything else
                     unread             the timeline was not read (page cap)
  merged_open[]    OPEN issues a merged PR claimed more than MERGED_OPEN_HOURS ago --
                   "fix shipped, issue not closed". A claim is read exactly as
                   close-on-evidence.yml reads it: a closing keyword in the title or
                   body, else an `issue/<n>-` branch unless the body only `Refs` it.
  closed_rows[]    number, closed_at, closer -- carried forward on the next run so a
                   closer is read from the timeline once, not twice a day forever.
  truncated[]      endpoints a page cap cut short. Non-empty means the counts are
                   a floor, and the page says so.

`open_end` is walked BACKWARDS from the live open count: open at the end of day d
= open now - (opened - closed) over every later day. An issue reopened after a
close has no `closed_at`, so it reads as never closed -- consistent with "open
now", and the reason this is a walk-back rather than a sum from zero.

COST, REST ONLY (GraphQL is unavailable in some sessions)
--------------------------------------------------------
Measured 2026-11-18 over 28 days: 837 issues and PRs updated (9 pages), 237 issues
closed. So the first run reads 9 + 237 timelines + ~6 PR pages, about 250 requests,
and every later run reads only the issues closed since -- about 20 -- because the
closers already read are carried forward from the file it is about to overwrite.
GITHUB_TOKEN allows 1,000 an hour per repository.

NO USER DATA: issue numbers, titles (already public, already in `rows`), dates and
the category each falls into. Never a comment body, never a login.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outbox import LOOP_IDENTITIES  # noqa: E402

WINDOW_DAYS = 28
#: A merged PR's issue counts as "shipped, not closed" once the merge is this old.
#: close-on-evidence waits on a deploy and a verify-production run, which together
#: take well under a day; past that, something in the chain did not fire.
MERGED_OPEN_HOURS = 24
#: Page caps. 837 items over 28 days is 9 list pages; 30 leaves room for a busy month.
MAX_LIST_PAGES = 30
MAX_PR_PAGES = 15
MAX_TIMELINE_PAGES = 5
#: Timelines read per run. The first run needs ~240; a cap keeps a burst from
#: spending the job's whole API budget, and what it skips is counted `unread`.
MAX_TIMELINES = 300
#: How far from the `closed` event the closer's own comment may sit.
CLOSE_COMMENT_S = 300

SOURCES = ("audit", "loop", "ops", "outsider")
CLOSERS = ("close-on-evidence", "prioritise", "cannot-reproduce", "main-red-report",
           "owner", "other", "unread")

# close-on-evidence.yml's own patterns, so a claim here is a claim there.
_CLAIM = re.compile(r"(?:clos(?:e|es|ed)|fix(?:e[sd])?|resolv(?:e|es|ed))\s+#(\d+)", re.I)
_REFS = re.compile(r"refs?\s+#(\d+)", re.I)
_BRANCH = re.compile(r"^issue/(\d+)")

Runner = Callable[[list], str]


def run_gh(args: list) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {p.stderr.strip()[:200]}")
    return p.stdout


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _pages(gh: Runner, url: str, cap: int, cut: list | None,
           stop: Callable[[list], bool] | None = None) -> list[dict]:
    """REST pages until a short one, `stop(page)` says enough, or `cap`. Manual
    paging so the tests see exactly what is requested. A cap that cuts the read
    short appends the endpoint to `cut`."""
    out: list[dict] = []
    sep = "&" if "?" in url else "?"
    for page in range(1, cap + 1):
        rows = json.loads(gh(["api", f"{url}{sep}per_page=100&page={page}"]) or "[]")
        if not isinstance(rows, list):
            raise ValueError(f"{url}: not a list")
        out.extend(r for r in rows if isinstance(r, dict))
        if len(rows) < 100 or (stop and stop(rows)):
            break
    else:
        if cut is not None:
            cut.append(url.split("?", 1)[0])
    return out


def source_of(issue: dict, owner: str) -> str:
    """Who filed it. `[OPS]` first: ops findings are filed by a bot, and the point
    of the bucket is to separate them from the loop's other filings."""
    if (issue.get("title") or "").lstrip().upper().startswith("[OPS]"):
        return "ops"
    login = str((issue.get("user") or {}).get("login") or "")
    if login in LOOP_IDENTITIES:
        return "loop"
    if owner and login.lower() == owner.lower():
        return "audit"
    return "outsider"


def closer_of(actor: str, comment: str, labels: list[str], owner: str) -> str:
    """Which hand closed it, from the closer's login and its closing comment.
    Order matters: the specific markers before the identity fallbacks."""
    head = re.sub(r"[*_`\s]+", " ", comment).strip()
    if "cannot-reproduce" in labels or "CANNOT-REPRODUCE" in comment:
        return "cannot-reproduce"
    if head.startswith("Closed on production evidence"):
        return "close-on-evidence"
    if head.startswith("Green again on main"):
        return "main-red-report"
    if actor == "claude[bot]":
        return "prioritise"
    if owner and actor.lower() == owner.lower():
        return "prioritise" if re.match(r"closing\b", head, re.I) else "owner"
    return "other"


def read_closer(gh: Runner, repo: str, issue: dict, owner: str) -> str:
    """One issue's closer, from its timeline (usually one request)."""
    events = _pages(gh, f"repos/{repo}/issues/{issue['number']}/timeline",
                    MAX_TIMELINE_PAGES, None)
    closes = [e for e in events if e.get("event") == "closed"]
    if not closes:
        return "unread"
    last = closes[-1]
    actor = str((last.get("actor") or {}).get("login") or "")
    at = _ts(last.get("created_at"))
    comment = ""
    if at is not None:
        near = [e for e in events if e.get("event") == "commented"
                and str((e.get("actor") or e.get("user") or {}).get("login") or "") == actor
                and (t := _ts(e.get("created_at"))) is not None
                and abs((t - at).total_seconds()) <= CLOSE_COMMENT_S]
        if near:
            comment = near[-1].get("body") or ""
    labels = [lab.get("name", "") for lab in issue.get("labels") or []]
    return closer_of(actor, comment, labels, owner)


def claims(pr: dict) -> set[int]:
    """Issues a PR claims, exactly as close-on-evidence.yml reads them."""
    text = f"{pr.get('title') or ''}\n{pr.get('body') or ''}"
    found = {int(n) for n in _CLAIM.findall(text)}
    if found:
        return found
    m = _BRANCH.match(str((pr.get("head") or {}).get("ref") or ""))
    if not m:
        return set()
    n = int(m.group(1))
    return set() if n in {int(r) for r in _REFS.findall(text)} else {n}


def summarise(items: list[dict], prs: list[dict], closers: dict[int, str], *,
              open_now: int, open_titles: dict[int, str], owner: str,
              now: datetime) -> dict:
    """The trend block from already-fetched data. Pure, so the tests drive it.

    `items` is the issues endpoint's output (PRs included; dropped here),
    `closers` maps an issue number to its closer, `open_titles` is every open
    issue (the live backlog) by number.
    """
    today = now.astimezone(timezone.utc).date()
    first = today - timedelta(days=WINDOW_DAYS - 1)
    days = {first + timedelta(days=i): {"opened": 0, "closed": 0,
                                        "opened_by": Counter(), "closed_by": Counter()}
            for i in range(WINDOW_DAYS)}
    closed_rows = []
    for it in items:
        if "pull_request" in it:
            continue
        c = _ts(it.get("created_at"))
        if c is not None and c.date() in days:
            d = days[c.date()]
            d["opened"] += 1
            d["opened_by"][source_of(it, owner)] += 1
        x = _ts(it.get("closed_at")) if it.get("state") == "closed" else None
        if x is not None and x.date() in days:
            who = closers.get(it["number"], "unread")
            d = days[x.date()]
            d["closed"] += 1
            d["closed_by"][who] += 1
            closed_rows.append({"number": it["number"], "closed_at": it["closed_at"],
                                "closer": who})

    out_days = []
    running = open_now
    for day in sorted(days, reverse=True):
        d = days[day]
        out_days.append({"date": day.isoformat(), "opened": d["opened"], "closed": d["closed"],
                         "net": d["opened"] - d["closed"], "open_end": running,
                         "opened_by": {k: d["opened_by"][k] for k in SOURCES if d["opened_by"][k]},
                         "closed_by": {k: d["closed_by"][k] for k in CLOSERS if d["closed_by"][k]}})
        running -= d["opened"] - d["closed"]
    out_days.reverse()

    merged_open: dict[int, dict] = {}
    cut = now - timedelta(hours=MERGED_OPEN_HOURS)
    for pr in prs:
        merged = _ts(pr.get("merged_at"))
        if merged is None or merged > cut:
            continue
        for n in claims(pr):
            if n in open_titles and (n not in merged_open
                                     or merged_open[n]["merged_at"] < pr["merged_at"]):
                merged_open[n] = {"number": n, "title": open_titles[n], "pr": pr["number"],
                                  "merged_at": pr["merged_at"],
                                  "hours": int((now - merged).total_seconds() // 3600)}

    return {"generated_at": _iso(now), "window_days": WINDOW_DAYS, "open_now": open_now,
            "merged_open_hours": MERGED_OPEN_HOURS, "days": out_days,
            "merged_open": sorted(merged_open.values(), key=lambda r: r["number"]),
            "closed_rows": sorted(closed_rows, key=lambda r: r["number"])}


# --------------------------------------------------------------- PR merge time

#: Owner, 2026-11-19: "i think we should also track the max time a PR took to merge, this
#: would help understand how the loop is performing". Measured that day over 125 PRs merged
#: since 2026-11-13: median 0.5h, p90 7.4h, max 46.6h (#1121). The tail is QA-fail loops and
#: trust-boundary holds; the median says nothing about it, so the block reports the max too.
#:
#: Counted: PRs merged in the window, open -> merge. Not counted: the automated measurement
#: and report PRs (`publish_measurements.sh`), which merge themselves in about a minute and
#: would drag every number toward zero.
PR_WINDOWS = (7, 28)
SLOWEST_SHOWN = 5
_AUTOMATED_TITLE = re.compile(r"^(measurement|sync report|infra report|discover report|"
                              r"prioritise report|design report)\b", re.I)


def _automated(pr: dict) -> bool:
    return ((pr.get("head") or {}).get("ref") or "").startswith("measurements/") or \
        bool(_AUTOMATED_TITLE.match(pr.get("title") or ""))


def _pct(sorted_hours: list[float], p: float) -> float | None:
    if not sorted_hours:
        return None
    return round(sorted_hours[min(len(sorted_hours) - 1, int(p * len(sorted_hours)))], 1)


def waiting_on(labels: list[str]) -> str:
    """What an open PR is waiting for, read from its labels."""
    if "qa-fail" in labels:
        return "a fix after QA failed"
    if "needs-human-review" in labels:
        return "chief (trust boundary)"
    if "qa-pass" in labels:
        return "merge"
    return "gates / QA"


def pr_flow(merged: list[dict], open_prs: list[dict], now: datetime) -> dict:
    """Merge-time stats from closed-PR and open-PR listings (REST `pulls` shape). Pure."""
    rows = []
    for pr in merged:
        c, m = _ts(pr.get("created_at")), _ts(pr.get("merged_at"))
        if c is None or m is None or _automated(pr):
            continue
        rows.append({"number": pr["number"], "title": (pr.get("title") or "")[:90],
                     "author": (pr.get("user") or {}).get("login"), "merged_at": pr["merged_at"],
                     "hours": round((m - c).total_seconds() / 3600, 1)})
    windows = {}
    for days in PR_WINDOWS:
        floor = now - timedelta(days=days)
        sel = sorted((r for r in rows if _ts(r["merged_at"]) >= floor), key=lambda r: r["hours"])
        hs = [r["hours"] for r in sel]
        windows[f"{days}d"] = {"merged": len(sel), "median_h": _pct(hs, 0.5), "p90_h": _pct(hs, 0.9),
                               "max_h": hs[-1] if hs else None,
                               "slowest": [dict(r) for r in sel[::-1][:SLOWEST_SHOWN]]}
    start = (now - timedelta(days=PR_WINDOWS[-1] - 1)).date()
    by_day = {(start + timedelta(days=i)).isoformat(): [] for i in range(PR_WINDOWS[-1])}
    for r in rows:
        d = r["merged_at"][:10]
        if d in by_day:
            by_day[d].append(r["hours"])
    days_out = [{"date": d, "merged": len(h), "median_h": _pct(sorted(h), 0.5),
                 "max_h": max(h) if h else None} for d, h in by_day.items()]
    open_rows = []
    for pr in open_prs:
        c = _ts(pr.get("created_at"))
        if c is None or _automated(pr):
            continue
        labels = [l.get("name") for l in pr.get("labels") or []]
        open_rows.append({"number": pr["number"], "title": (pr.get("title") or "")[:90],
                          "age_h": round((now - c).total_seconds() / 3600, 1),
                          "waiting_on": waiting_on(labels)})
    open_rows.sort(key=lambda r: -r["age_h"])
    return {"windows": windows, "days": days_out, "open": open_rows}


# --- why a PR was slow (owner, 2026-11-19: "also capture top one liner reasons, explaining why
# it is being delayed" -- "this should be dynamic"). Not a fixed list of causes: each PR's own
# record is replayed as a timeline -- every push, each gates run on each commit, each QA
# verdict, each label -- and the time between events is charged to the STATE the PR was in.
# The one-liner names whichever states actually dominated, so a fix loop, a stalled queue and
# a held PR read differently. For the slowest and the open PRs only (EXPLAIN_MAX), with at most
# CHECKED_COMMITS commits' check runs read each.
EXPLAIN_MAX = 10
CHECKED_COMMITS = 6
GATE_NAMES = ("gates", "build-gates")
#: state -> its phrase. Priority order when several hold at once: the first wins.
STATES = (
    ("held", "held for chief (trust boundary)"),
    ("qa_fail", "waiting for a fix after QA failed"),
    ("gates_red", "gates red"),
    ("gates_running", "gates running"),
    ("no_gates", "waiting for gates to start"),
    ("awaiting_qa", "waiting for a QA round"),
    ("awaiting_merge", "QA passed, waiting for the merge"),
)
_PHRASE = dict(STATES)


def _timeline(created: datetime, end: datetime, commits: list[dict], checks: dict,
              comments: list[dict], events: list[dict]) -> dict[str, float]:
    """Hours per state between `created` and `end`. Pure. `commits` [{sha, at}], `checks`
    sha -> [{name, started_at, completed_at, conclusion}], `comments` and `events` in the
    REST shape."""
    marks: list[tuple[datetime, str, object]] = []
    for c in commits:
        if _ts(c.get("at")):
            marks.append((_ts(c["at"]), "push", c["sha"]))
    for sha, runs in checks.items():
        for r in runs:
            if r.get("name") not in GATE_NAMES:
                continue
            if _ts(r.get("started_at")):
                marks.append((_ts(r["started_at"]), "run_start", (sha, r["name"])))
            if _ts(r.get("completed_at")):
                marks.append((_ts(r["completed_at"]), "run_end", (sha, r["name"], r.get("conclusion"))))
    for c in comments:
        body = c.get("body") or ""
        if body.startswith(("QA: PASS", "QA: FAIL")) and _ts(c.get("created_at")):
            marks.append((_ts(c["created_at"]), "verdict", body.startswith("QA: PASS")))
    for e in events:
        name = (e.get("label") or {}).get("name")
        if name in ("qa-fail", "needs-human-review") and e.get("event") in ("labeled", "unlabeled") \
                and _ts(e.get("created_at")):
            marks.append((_ts(e["created_at"]), e["event"], name))
    marks = sorted((m for m in marks if created <= m[0] <= end), key=lambda m: m[0])
    head, runs, labels, verdict = None, {}, set(), None    # runs: name -> running|green|red for head
    hours: dict[str, float] = {}

    def state() -> str:
        if "needs-human-review" in labels:
            return "held"
        if "qa-fail" in labels:
            return "qa_fail"
        if any(v == "red" for v in runs.values()):
            return "gates_red"
        if any(v == "running" for v in runs.values()):
            return "gates_running"
        if not runs:
            return "no_gates"
        return "awaiting_merge" if verdict else "awaiting_qa"

    t = created
    for at, kind, val in marks:
        st = state()
        hours[st] = hours.get(st, 0.0) + (at - t).total_seconds() / 3600
        t = at
        if kind == "push":
            # A push after a QA FAIL is the fix arriving: `qa-fail` stays on the PR until the next
            # QA round clears it, but from here the PR waits on gates and QA, not on a fix.
            head, runs, verdict = val, {}, None
            labels.discard("qa-fail")
        elif kind == "run_start" and val[0] == head:
            runs[val[1]] = "running"
        elif kind == "run_end" and val[0] == head:
            runs[val[1]] = "green" if val[2] == "success" else "red"
        elif kind == "verdict":
            # Each verdict sets the state itself: the `qa-fail` LABEL goes on once and stays
            # through later rounds (#1212: labelled once, five FAILs), so a FAIL starts a new
            # wait for a fix and a PASS ends it, whatever the label events say.
            verdict = val
            if val:
                labels.discard("qa-fail")
            else:
                labels.add("qa-fail")
        elif kind == "labeled":
            labels.add(val)
        elif kind == "unlabeled":
            labels.discard(val)
    st = state()
    hours[st] = hours.get(st, 0.0) + (end - t).total_seconds() / 3600
    return {k: round(v, 1) for k, v in hours.items() if v > 0}


def delay_reason(created: datetime, end: datetime, commits: list[dict], checks: dict,
                 comments: list[dict], events: list[dict]) -> dict:
    """The per-state hours and the one-liner for one PR. Pure."""
    hours = _timeline(created, end, commits, checks, comments, events)
    total = max(sum(hours.values()), 0.1)
    fails = sum((c.get("body") or "").startswith("QA: FAIL") for c in comments)
    top = [(k, v) for k, v in sorted(hours.items(), key=lambda kv: -kv[1]) if v >= 0.5 and v >= 0.1 * total][:2]
    parts = []
    for k, v in top:
        phrase = _PHRASE[k]
        if k == "qa_fail" and fails:
            phrase += f" ({fails} QA FAIL{'' if fails == 1 else 's'})"
        parts.append(f"{v}h {phrase}")
    extra = f"; {len(commits)} pushes" if len(commits) >= 4 else ""
    return {"reason": ("; ".join(parts) or "no single wait stood out") + extra,
            "primary": top[0][0] if top else "other", "hours": hours,
            "qa_fails": fails, "pushes": len(commits)}


def explain(gh: Runner, repo: str, prs: list[dict], now: datetime) -> None:
    """Add `why` to each row in place. A failed read gives `why: null`, never a guess."""
    for r in prs[:EXPLAIN_MAX]:
        try:
            n = r["number"]
            pr = json.loads(gh(["api", f"repos/{repo}/pulls/{n}"]))
            raw = json.loads(gh(["api", f"repos/{repo}/pulls/{n}/commits?per_page=100"]))
            commits = [{"sha": c["sha"], "at": (c.get("commit") or {}).get("committer", {}).get("date")}
                       for c in raw]
            checks = {}
            for c in commits[-CHECKED_COMMITS:]:
                checks[c["sha"]] = json.loads(gh(["api", f"repos/{repo}/commits/{c['sha']}/check-runs?per_page=100"])).get("check_runs") or []
            comments = json.loads(gh(["api", f"repos/{repo}/issues/{n}/comments?per_page=100"]))
            events = json.loads(gh(["api", f"repos/{repo}/issues/{n}/events?per_page=100"]))
            created, end = _ts(pr.get("created_at")), _ts(pr.get("merged_at")) or now
            r["why"] = delay_reason(created, end, commits, checks, comments, events)
        except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
            r["why"] = None


def top_reasons(rows: list[dict]) -> list[dict]:
    """How many of these PRs each state was the biggest wait for, most common first."""
    counts: dict[str, int] = {}
    for r in rows:
        k = (r.get("why") or {}).get("primary")
        if k:
            counts[k] = counts.get(k, 0) + 1
    return [{"reason": _PHRASE.get(k, "no single wait stood out"), "prs": v}
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]


def collect(gh: Runner, repo: str, now: datetime, *, open_issues: list[dict],
            prior: dict | None = None) -> dict:
    """Fetch and summarise. `open_issues` is the backlog the collector already
    read (`gh issue list` shape: number, title); `prior` is the trend block of
    the file about to be overwritten, whose closers are reused."""
    owner = repo.split("/", 1)[0]
    start = datetime.combine(now.astimezone(timezone.utc).date()
                             - timedelta(days=WINDOW_DAYS - 1), datetime.min.time(),
                             tzinfo=timezone.utc)
    truncated: list[str] = []
    items = _pages(gh, f"repos/{repo}/issues?state=all&since={_iso(start)}"
                       f"&sort=updated&direction=desc", MAX_LIST_PAGES, truncated)

    known = {(r.get("number"), r.get("closed_at")): r.get("closer")
             for r in ((prior or {}).get("closed_rows") or [])
             if isinstance(r, dict) and r.get("closer") not in (None, "unread")}
    closers: dict[int, str] = {}
    read = 0
    for it in items:
        x = _ts(it.get("closed_at"))
        if "pull_request" in it or it.get("state") != "closed" or x is None or x < start:
            continue
        hit = known.get((it["number"], it["closed_at"]))
        if hit:
            closers[it["number"]] = hit
        elif read < MAX_TIMELINES:
            read += 1
            closers[it["number"]] = read_closer(gh, repo, it, owner)
        elif "timelines" not in truncated:
            truncated.append("timelines")

    # Newest-updated first; stop once a whole page predates the window, since a
    # PR merged inside it was updated inside it.
    def old(page: list) -> bool:
        return all((_ts(p.get("updated_at")) or start) < start for p in page)
    prs = _pages(gh, f"repos/{repo}/pulls?state=closed&sort=updated&direction=desc",
                 MAX_PR_PAGES, truncated, stop=old)

    doc = summarise(items, prs, closers, open_now=len(open_issues),
                    open_titles={int(i["number"]): i.get("title") or "" for i in open_issues},
                    owner=owner, now=now)
    doc["timelines_read"] = read
    doc["truncated"] = truncated
    # One extra read: the open PRs, for their ages. A failure here leaves the rest of the block.
    try:
        open_prs = json.loads(gh(["api", f"repos/{repo}/pulls?state=open&per_page=100"]))
    except (RuntimeError, ValueError):
        open_prs = []
        truncated.append("open-prs")
    doc["pr_flow"] = pf = pr_flow(prs, open_prs if isinstance(open_prs, list) else [], now)
    # Why the slow ones were slow, and why the open ones are waiting: the 7-day slowest first,
    # then the 28-day slowest not already read, then the open PRs, up to EXPLAIN_MAX in all.
    seen, todo = set(), []
    for row in (pf["windows"]["7d"]["slowest"] + pf["windows"]["28d"]["slowest"] + pf["open"]):
        if row["number"] not in seen:
            seen.add(row["number"]); todo.append(row)
    explain(gh, repo, todo, now)
    whys = {r["number"]: r.get("why") for r in todo}
    for w in pf["windows"].values():
        for r in w["slowest"]:
            r["why"] = whys.get(r["number"])
        w["top_reasons"] = top_reasons(w["slowest"])
    for r in pf["open"]:
        r["why"] = whys.get(r["number"])
    return doc
