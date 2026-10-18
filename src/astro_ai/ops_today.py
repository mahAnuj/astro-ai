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
#: Mirrors `report_loop_outcomes.WORKFLOW` minus `pr-gates.yml`, for the reason
#: in the module docstring.
LOOP_WORKFLOWS = (
    "agent-work.yml",
    "agent-merge.yml",
    "agent-measure.yml",
    "agent-discover.yml",
    "agent-design.yml",
    "close-on-evidence.yml",
    "verify-production.yml",
)

#: A run that ended in any of these did not do its job. `cancelled` is here
#: because that is what a job killed by `timeout-minutes` reports, and a gate
#: killed by the clock did not fail -- it never ran, which is worse and was
#: invisible for exactly as long as this tile ignored it.
FAILED_CONCLUSIONS = ("failure", "timed_out", "cancelled")

#: One page each. 100 closed PRs reaches back weeks on this repo and 100 runs
#: reaches back further than a day, so a second page would only ever fetch
#: rows this function is about to discard.
PER_PAGE = 100


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

    prs = _get(f"{API_BASE}/repos/{repo}/pulls"
               f"?state=closed&sort=updated&direction=desc&per_page={PER_PAGE}",
               timeout=timeout, token=token)
    if not isinstance(prs, list):
        raise ValueError("pulls did not return a list")

    runs_doc = _get(f"{API_BASE}/repos/{repo}/actions/runs"
                    f"?created=%3E%3D{day}&per_page={PER_PAGE}",
                    timeout=timeout, token=token)
    runs = runs_doc.get("workflow_runs") if isinstance(runs_doc, dict) else None
    if not isinstance(runs, list):
        raise ValueError("actions/runs did not return workflow_runs")

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
        "shipped": sorted(shipped.values(), key=lambda s: s["merged_at"], reverse=True),
        "failed": sorted(failed, key=lambda f: f["started"] or "", reverse=True),
    }
