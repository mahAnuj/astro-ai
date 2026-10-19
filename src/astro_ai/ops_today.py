"""Today's delivery numbers, read from the GitHub API rather than a snapshot.

WHY THIS EXISTS, MEASURED
-------------------------
On 2026-10-18 /admin/ops read `0 shipped today`, `0 filed today` and
`0 failed today`. Two of the three were right by accident and the third was
wrong, and no reader could tell which was which:

    tile            page      truth        why
    Filed today        0          0        live already (#353), genuinely quiet
    Shipped today      0          0        snapshot was 3 days old and agreed
    Failed today       0          2        BOTH wrong, for two separate reasons

The first reason is staleness. `measurements/loop.json` is committed by
`agent-measure`, and that workflow had failed on every run since 2026-10-15
("GH006: Protected branch update failed for refs/heads/main"), so the newest
row on the page was dated the 15th. `_loop_view` buckets by
`date_ist == today_ist`, so with no row dated today every "today" tile reads
zero -- not "no data", *zero*, which is a claim.

The second reason survives any amount of freshness.
`collect_loop_measurements.py:109` is `WORKFLOW_NAME = "agent-work"`, so
`loop.json` holds agent-work cycles and nothing else. `agent-measure` is not an
agent-work run, so the two failures of 2026-10-18 could never have appeared on
that tile however recently the file had been written. A dashboard whose job is
to show the loop failing was structurally incapable of showing the loop
failing -- and the failure it could not show was the one keeping its own data
three days old.

WHAT THIS CHANGES, STATED RATHER THAN IMPLIED
---------------------------------------------
`shipped` here means **a pull request merged during the IST day**, counted
once. The snapshot counts an agent-work *cycle* whose PR merged, and
`collect_loop_measurements.py`'s own header says to "count distinct `pr`
values" because two runs can share one PR -- so the PR, not the run, was
always the unit. A PR a human merged now counts too, which the cycle-shaped
number silently dropped.

`failed` here spans every loop leg, not just agent-work: see LOOP_WORKFLOWS.

`pr-gates` is deliberately NOT a loop leg. A red gate on a PR is the gate
doing its job; counting it as a loop failure would make every caught defect
look like an outage and would bury the failures that are real.

COST
----
Two requests, both unauthenticated-safe (the repo is public). The budget is
60/hour shared across every tenant on this egress IP, and `ops_data` already
spends one on the live backlog. Cached for `CACHE_TTL` by the caller, so a
worst case of constant reloading is 36/hour; the realistic case is a handful a
day, because this is an admin page. `OPS_GH_TOKEN` raises the ceiling to
5,000/hour if that ever stops being true. Any failure raises, and the caller
renders the committed snapshot and labels it.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

API_BASE = "https://api.github.com"

#: GitHub rejects a request with no User-Agent.
_UA = "astro-ai-admin-ops"

#: The workflows that ARE the loop, by file name -- matched against a run's
#: `path`, not its display name, because a display name is a free-text field in
#: the workflow file and renaming one would silently empty this tile.
#:
#: This was "mirrors `report_loop_outcomes.WORKFLOW` minus `pr-gates.yml`", and
#: that was the defect: `report_loop_outcomes.WORKFLOW` is itself a partial list
#: (8 of 15 workflows), so mirroring it inherited six blind spots rather than
#: one. Measured 2026-10-18: `agent-steward.yml`, `agent-sync.yml`,
#: `agent-prioritise.yml`, `agent-infra.yml`, `agent-research.yml` and
#: `loop-outcomes.yml` were all missing, and six dead scheduled legs would have
#: left this tile reading 0.
#:
#: `agent-steward.yml` is the one that decides it. Its stated job is to notice
#: that the pipeline has stopped and route the repair -- so its own failure was
#: invisible on the tile built to show the pipeline stopping. That is the exact
#: circularity in the module docstring above, repeating one level up.
#:
#: Defined as "every workflow except the PR gates", so the list grows by
#: default rather than by remembering.
LOOP_WORKFLOWS = (
    "agent-work.yml",
    "agent-merge.yml",
    "agent-measure.yml",
    "agent-discover.yml",
    "agent-design.yml",
    "agent-steward.yml",
    "agent-sync.yml",
    "agent-prioritise.yml",
    "agent-infra.yml",
    "agent-research.yml",
    "loop-outcomes.yml",
    "close-on-evidence.yml",
    "verify-production.yml",
)

#: The workflows that are deliberately NOT loop legs, listed rather than
#: implied. Both gate a pull request, and a red gate is the gate working --
#: counting one as a loop failure would make every caught defect read as an
#: outage and bury the failures that are real.
#:
#: This exists so the two sets TOGETHER are exhaustive, which
#: `tests/test_ops_today_live.py` asserts against `.github/workflows/*.yml`.
#: A new workflow therefore fails a test instead of being silently invisible.
#: The app image does not ship `.github/`, so the check cannot live here.
NOT_LOOP_WORKFLOWS = (
    "pr-gates.yml",
    "verify-build.yml",
)

#: A run that ended in any of these did not do its job. `cancelled` is here
#: because that is what a job killed by `timeout-minutes` reports, and a gate
#: killed by the clock did not fail -- it never ran, which is worse and was
#: invisible for exactly as long as this tile ignored it.
FAILED_CONCLUSIONS = ("failure", "timed_out", "cancelled")

#: 100 rows a page, and MORE PAGES ONLY WHEN THE PAGE DID NOT REACH BACK PAST
#: THE DAY START. "One page is always enough" was close to false already:
#: measured 2026-10-18, page 1 of the runs query spanned 31 hours against a
#: `total_count` of 139, and 51 of its rows fell inside the IST day at
#: two-thirds through that day. Under 2x headroom on a count that is growing,
#: and the overflow mode is a SILENT UNDERCOUNT -- the same failure this module
#: exists to fix, one layer up.
#:
#: So the stop condition is evidence, not arithmetic: keep paging while the
#: oldest row fetched is still inside the day, because that is the only state
#: in which an unfetched row could still qualify. On an ordinary day that is
#: one request, exactly as before.
PER_PAGE = 100

#: A hard stop, because the budget is 60/hour on a shared egress IP and a
#: runaway loop here is worse than an undercount. 300 runs is ~3.7x the
#: measured busiest day. Hitting it sets `truncated`, which the page shows --
#: an admitted "at least N" beats a confident wrong number.
MAX_PAGES = 3


def _get(url: str, *, timeout: float, token: str | None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": _UA,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _pages(base: str, *, key: str | None, oldest, since: str,
           timeout: float, token: str | None):
    """Rows from `base`, paging only while the oldest row is still in the day.

    Returns `(rows, truncated)`. `truncated` is True when MAX_PAGES was spent
    and the last page was STILL inside the window -- i.e. a qualifying row may
    exist that we did not fetch. It is never True on an ordinary day.

    The results are newest-first on both endpoints this is used for, so the
    last row of a page is the oldest fetched so far. Once that is older than
    `since`, every remaining row is older still and cannot qualify.
    """
    rows: list = []
    for page in range(1, MAX_PAGES + 1):
        doc = _get(f"{base}&per_page={PER_PAGE}&page={page}",
                   timeout=timeout, token=token)
        batch = doc if key is None else (
            doc.get(key) if isinstance(doc, dict) else None)
        if not isinstance(batch, list):
            raise ValueError(f"{base.rsplit('/', 1)[-1]} did not return a list")
        rows.extend(batch)
        if len(batch) < PER_PAGE:
            return rows, False          # the endpoint ran out: nothing unseen
        if oldest(batch[-1]) < since:
            return rows, False          # paged back past the day start
    return rows, True


def fetch_today(repo: str, day_start: datetime, *,
                timeout: float, token: str | None = None) -> dict:
    """What shipped and what failed since `day_start` (an aware UTC datetime).

    Raises on any failure. Swallowing it here would make a quiet day and an
    unreachable API render identically, which is the whole defect this module
    exists to fix.
    """
    # Normalise to UTC here rather than trusting the caller. The caller does
    # convert, but a function whose correctness depends on an aware datetime
    # already being in the right zone silently returns a day's worth of wrong
    # rows when it is not -- and the whole bug class this module fixes is a
    # date computed in the wrong zone.
    day_start = day_start.astimezone(timezone.utc)
    since = day_start.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Filter the ACTIONS query by the UTC date of the IST day's start, not by
    # today's UTC date. The IST day opens at 18:30 UTC on the previous day, so
    # `created>=<today UTC>` would silently drop every run between 00:00 and
    # 05:30 IST -- which is precisely when the loop is scheduled to run
    # ("04:30 IST, after the rolling cap resets"). The exact cut is applied
    # below against `created_at`; this parameter only bounds the page.
    day = day_start.strftime("%Y-%m-%d")

    prs, pr_more = _pages(
        f"{API_BASE}/repos/{repo}/pulls"
        f"?state=closed&sort=updated&direction=desc",
        key=None, oldest=lambda r: r.get("updated_at") or "",
        since=since, timeout=timeout, token=token)

    runs, runs_more = _pages(
        f"{API_BASE}/repos/{repo}/actions/runs?created=%3E%3D{day}",
        key="workflow_runs", oldest=lambda r: r.get("created_at") or "",
        since=since, timeout=timeout, token=token)

    # Distinct by number: the endpoint cannot repeat a PR, but the unit being
    # the PR rather than the row is the point of the count, so it is enforced
    # here rather than assumed.
    shipped: dict[int, dict] = {}
    for p in prs:
        merged = p.get("merged_at")
        if not merged or merged < since:
            continue
        shipped[p["number"]] = {
            "pr": p["number"],
            "title": p.get("title") or "",
            "merged_at": merged,
            "url": p.get("html_url") or "",
        }

    failed = []
    for r in runs:
        path = (r.get("path") or "").rsplit("/", 1)[-1]
        if path not in LOOP_WORKFLOWS:
            continue
        if r.get("conclusion") not in FAILED_CONCLUSIONS:
            continue
        if (r.get("created_at") or "") < since:
            continue
        failed.append({
            "run": r.get("id"),
            "workflow": r.get("name") or path,
            "conclusion": r.get("conclusion"),
            "started": r.get("created_at"),
            "url": r.get("html_url") or "",
        })

    return {
        "since": since,
        # True when a page cap was reached with rows still inside the day, so
        # the counts below are a floor. The page says "at least" rather than
        # printing a number it cannot stand behind.
        "truncated": pr_more or runs_more,
        "shipped": sorted(shipped.values(), key=lambda s: s["merged_at"], reverse=True),
        "failed": sorted(failed, key=lambda f: f["started"] or "", reverse=True),
    }
