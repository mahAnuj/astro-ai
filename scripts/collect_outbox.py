#!/usr/bin/env python3
"""How noisy the loop is, from what it actually posted: measurements/outbox.json (#1188).

WHY THIS EXISTS
---------------
#311, #276 and #329 each collected 20+ near-identical comments and nothing measured
it; the owner saw it by reading the threads. The outbox (scripts/outbox.py) now
dedupes, caps and marks what goes through it -- but the measure has to cover what
does NOT go through it too (agents posting with `gh` directly, the posters still
being migrated), or a quiet number would only mean "the migrated scripts are quiet".

So the evals are computed from the COMMENTS THEMSELVES, every one written by
LOOP_IDENTITIES in the window, whichever path posted it:

  comments per PR / per issue   loop comments over the distinct threads they landed on
  duplicate rate                loop comments whose normalised text (outbox.normalise:
                                SHAs, timestamps and run ids replaced) already appeared
                                from the loop on the SAME thread earlier in the window
  sent by kind                  outbox markers, i.e. what went through the outbox
  deduped / capped / failed     the tallies the outbox writes onto its own markers
  owner touched                 of the PRs with any comment in the window, the share
                                where the repository owner commented

Two windows, current and previous, so `detect_ops_regressions.py` can say "rose".

WHERE IT RUNS
-------------
Called by `collect_lessons.py` inside agent-measure's commit job, before that script
runs the ops detector, so the detector judges this run's file. That job already holds
`issues: read`; this adds no permission, no step and no workflow edit. It is also a
CLI for a manual run.

WHAT IT NEVER WRITES: a comment body, a title, a login other than the counts' own
keys. Targets are thread numbers; kinds and keys come from markers.

EXIT CODES: 0 written, 1 nothing readable (the previous file is left standing), 2 bad args.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outbox  # noqa: E402

WINDOW_DAYS = 7
MAX_PAGES = 60          # measured 2026-11-17: 1,268 + 776 loop comments in 14 days, ~21 pages
TOP_THREADS = 5

Runner = Callable[[list], str]


def run_gh(args: list) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {p.stderr.strip()[:200]}")
    return p.stdout


def _pages(gh: Runner, url: str, cut: list | None = None) -> list[dict]:
    """REST pages until a short one. Manual paging, like collect_lessons.py: the
    tests need to see exactly what is requested. Appends `url` to `cut` when the
    page cap stopped it early -- NEWEST first, so what is lost is the previous
    window, and a trend against a truncated window would read as a rise."""
    out: list[dict] = []
    sep = "&" if "?" in url else "?"
    for page in range(1, MAX_PAGES + 1):
        rows = json.loads(gh(["api", f"{url}{sep}per_page=100&page={page}"]) or "[]")
        if not isinstance(rows, list):
            raise ValueError(f"{url}: not a list")
        out.extend(r for r in rows if isinstance(r, dict))
        if len(rows) < 100:
            break
    else:
        if cut is not None:
            cut.append(url.split("?", 1)[0])
    return out


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _thread(c: dict) -> tuple[str, int] | None:
    """("pr"|"issue", number) from a REST issue comment."""
    url = str(c.get("html_url") or "")
    try:
        n = int(str(c.get("issue_url") or "").rsplit("/", 1)[-1])
    except ValueError:
        return None
    return ("pr" if "/pull/" in url else "issue"), n


def summarise(comments: list[dict], issues: list[dict], start: datetime, end: datetime,
              owner: str, with_tallies: bool) -> dict:
    """The evals for one window [start, end). Counts only."""
    loop = []
    owner_prs: set[int] = set()
    any_prs: set[int] = set()
    for c in comments:
        when = _ts(c.get("created_at"))
        th = _thread(c)
        if when is None or th is None or not (start <= when < end):
            continue
        login = str((c.get("user") or {}).get("login") or "")
        if th[0] == "pr":
            any_prs.add(th[1])
            if owner and login.lower() == owner.lower():
                owner_prs.add(th[1])
        if login in outbox.LOOP_IDENTITIES:
            loop.append((when, th, c))
    loop.sort(key=lambda r: r[0])

    seen: dict[tuple, set] = defaultdict(set)
    dups = 0
    per_thread: Counter = Counter()
    sent: Counter = Counter()
    for _, th, c in loop:
        body = c.get("body") or ""
        h = outbox.key_for("-", body)
        if h in seen[th]:
            dups += 1
        seen[th].add(h)
        per_thread[th] += 1
        m = outbox.parse_marker(body)
        if m:
            sent[m["kind"]] += 1
    for i in issues:
        when = _ts(i.get("created_at"))
        if (i.get("pull_request") is None and when is not None and start <= when < end
                and str((i.get("user") or {}).get("login") or "") in outbox.LOOP_IDENTITIES):
            m = outbox.parse_marker(i.get("body") or "")
            if m:
                sent[m["kind"]] += 1

    on_prs = sum(v for (k, _), v in per_thread.items() if k == "pr")
    on_issues = sum(v for (k, _), v in per_thread.items() if k == "issue")
    prs = sum(1 for (k, _) in per_thread if k == "pr")
    iss = sum(1 for (k, _) in per_thread if k == "issue")
    doc = {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop_comments": len(loop),
        "on_prs": on_prs, "prs": prs,
        "on_issues": on_issues, "issues": iss,
        "comments_per_pr": round(on_prs / prs, 2) if prs else None,
        "comments_per_issue": round(on_issues / iss, 2) if iss else None,
        "duplicates": dups,
        "duplicate_rate_pct": round(dups / len(loop) * 100, 1) if loop else None,
        "sent_by_kind": dict(sorted(sent.items())),
        "via_outbox": sum(sent.values()),
        "top_threads": [{"on": k, "number": n, "comments": v}
                        for (k, n), v in per_thread.most_common(TOP_THREADS)],
        "owner_touched": {"prs": len(any_prs), "owner_commented": len(owner_prs & any_prs),
                          "pct": round(len(owner_prs & any_prs) / len(any_prs) * 100) if any_prs else None},
    }
    if with_tallies:
        # A tally is written when an attempt is refused, onto a marker that may be
        # older than the window, so it is read from comments UPDATED in the window.
        # A tally is cumulative per comment, so this is an upper bound for the window.
        t = Counter()
        for c in comments:
            up = _ts(c.get("updated_at"))
            if up is None or not (start <= up < end):
                continue
            if str((c.get("user") or {}).get("login") or "") not in outbox.LOOP_IDENTITIES:
                continue
            m = outbox.parse_marker(c.get("body") or "")
            if m:
                for k in outbox.TALLIED:
                    t[k] += m[k]
        doc["suppressed"] = {k: t[k] for k in outbox.TALLIED}
    return doc


def collect(gh: Runner, repo: str, now: datetime) -> dict:
    since = now - timedelta(days=2 * WINDOW_DAYS)
    iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    # `since` filters on updated_at, which is what the tallies need; the window
    # counts below filter on created_at themselves.
    cut: list[str] = []
    comments = _pages(gh, f"repos/{repo}/issues/comments?since={iso}&sort=created&direction=desc", cut)
    issues = _pages(gh, f"repos/{repo}/issues?state=all&since={iso}", cut)
    owner = repo.split("/", 1)[0]
    mid = now - timedelta(days=WINDOW_DAYS)
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": WINDOW_DAYS,
        # Non-empty = a page cap was hit and the PREVIOUS window is short. The
        # detector refuses to compare against it.
        "truncated": cut,
        "current": summarise(comments, issues, mid, now, owner, with_tallies=True),
        "previous": summarise(comments, issues, since, mid, owner, with_tallies=False),
        "kinds": {k: dict(v) for k, v in outbox.KINDS.items()},
        "quiet_cap": outbox.QUIET_CAP,
        "unavailable": {
            "failed_without_a_marker": "a failed post with no earlier comment of its kind on the "
                                       "target has nothing to tally onto; only that run's log has it",
            "suppressed_issue_creations": "issue bodies are not tallied; a refused create is in the "
                                          "run log only",
            "previous_suppressed": "tallies are cumulative per comment, so they are not split by window",
        },
    }


def write(gh: Runner, repo: str, out: Path, now: datetime | None = None) -> int:
    try:
        doc = collect(gh, repo, now or datetime.now(timezone.utc))
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"::warning::outbox.json not refreshed ({exc}); the previous file is left standing")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    c = doc["current"]
    print(f"outbox: {c['loop_comments']} loop comments in {WINDOW_DAYS}d, "
          f"{c['duplicate_rate_pct']}% duplicate, {c['comments_per_pr']} per PR, "
          f"{c['via_outbox']} via the outbox")
    return 0


def main(argv: list[str] | None = None, gh: Runner = run_gh) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=os.environ.get("GH_REPO", ""))
    ap.add_argument("--out", default="measurements/outbox.json")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    if "/" not in (a.repo or ""):
        print("usage: collect_outbox.py --repo OWNER/NAME [--out FILE]", file=sys.stderr)
        return 2
    return write(gh, a.repo, Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
