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
once, and SPLIT BY WHO SHIPPED IT -- `shipped_by_loop` for the unattended
agent loop, `shipped_by_session` for a session at a keyboard. The total alone
cannot distinguish "the team shipped three" from "the loop shipped nothing and
a human shipped three", which is the question this page exists to answer. The snapshot counts an agent-work *cycle* whose PR merged, and
`collect_loop_measurements.py`'s own header says to "count distinct `pr`
values" because two runs can share one PR -- so the PR, not the run, was
always the unit. A PR a human merged now counts too, which the cycle-shaped
number silently dropped.

`failed` here spans every loop leg, not just agent-work: see LOOP_WORKFLOWS.

`pr-gates` is deliberately NOT a loop leg. A red gate on a PR is the gate
doing its job; counting it as a loop failure would make every caught defect
look like an outage and would bury the failures that are real.

COST — RE-DERIVED AFTER THE PAGER, BECAUSE THE OLD NUMBER WENT STALE
--------------------------------------------------------------------
Two endpoints, both unauthenticated-safe (the repo is public). This paragraph
used to say "two requests ... 36/hour worst case", and that was true until
`MAX_PAGES` was added: `_pages` will spend up to `MAX_PAGES` requests per
endpoint, so the arithmetic is

    MAX_PAGES (3) x 2 endpoints      = 6 per cache miss here
    + issue_backlog.MAX_PAGES (4)    = 10 per render
      for `ops_data._live_issues`
    x 12 cache misses an hour (CACHE_TTL 300 s)
                                     = 120/hour

THE `+ 1` ON THAT THIRD LINE WAS WRONG and said 7/84 until 2026-10-20. It
treated the backlog read as ONE request because `issue_backlog`'s own comment
says "the backlog is 67, so the normal case is a single request" -- true of the
ORDINARY case, and this paragraph computes the WORST one.
`issue_backlog.fetch_live` loops `for page in range(1, MAX_PAGES + 1)` with
`MAX_PAGES = 4`, so the backlog contributes up to 4.

Measured deterministically on 2026-10-20 by stubbing the HTTP layer and varying
the page fill, because the count is a property of the pager, not of the network:

    saturated day (pages full, MAX_PAGES hit)  fetch_today 6 + backlog 4 = 10

THE ORDINARY CASE IS NOT 3, AND SAYING SO WAS THE SAME MISTAKE ONE LEVEL DOWN.
"Ordinary" was computed by stubbing SHORT pages -- a shape chosen to make the
pager stop, not a shape measured against the repo. Measured against the real
API on 2026-10-20, at this repo's actual volume:

    pulls          1 page  (short, pager stops)                     = 1
    actions/runs   2 pages (page 1 FULL, page 2 short)              = 2
    + issue_backlog 2 pages (104 open issues at 100 per page)       = 2
                                                 = 5 per cold render
    x 12 cache misses an hour (CACHE_TTL 300 s)  = 60/hour

So the ordinary case SITS EXACTLY ON the 60/hour ceiling and the worst case is
double it. Both terms that moved are volume, not code: the runs page filled, and
the backlog crossed 100 open issues. Neither is unusual and neither is an
incident, which is what "latent, not live" got wrong.

The live limit was observed at `remaining=0 / limit=60` the same morning, which
is CONSISTENT with this and does not attribute it: the budget is per egress IP
and shared with everything else running from it.

against a ceiling of **60/hour shared across every tenant on this egress IP**.
So the documented worst case now EXCEEDS the budget, and the failure it would
produce is a self-inflicted 403 that drops the page back into the 0/0/0
fallback this module exists to fix.

IT IS NOT LATENT. That sentence stood here until 2026-10-20 and claimed
"today's real volumes cost one request per endpoint and 3 per render (36/hour)".
Both halves were false at the time of writing: the runs read already needed two
pages, and the backlog already needed two. The measured ordinary render is 5,
i.e. 60/hour, which IS the ceiling — a reader holding refresh exhausts the
shared budget without any incident at all. The pathological shape on top of that
is a run storm filling every page, i.e. during an incident, which is exactly
when the budget is least affordable.

The lesson is the one this paragraph keeps re-learning: a request count measured
against a fixture is a property of the fixture. The worst case is derived from
`MAX_PAGES` and pinned; the ordinary case is a property of the repo's volume and
is therefore dated, attributed and re-measurable, never asserted as a standing
fact.

Two things keep it honest rather than a comment: `truncated` is surfaced on
every affected tile, so an over-long day reads as "at least N" instead of
spending more requests; and `OPS_GH_TOKEN` raises the ceiling to 5,000/hour.
`test_the_cost_paragraph_states_the_actual_worst_case` recomputes the two
integers above from `MAX_PAGES`, so raising the cap cannot leave this
paragraph behind the way the pager already did once.

Any failure raises, and the caller renders the committed snapshot and labels it.
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
    # Nightly content generation, not an agent loop leg (#515). Declared here
    # for a reason beyond taxonomy: a FAILED run of it is the designed
    # behaviour, not an incident. The job publishes all 24 readings or none,
    # because a partial document would be a cache hit that suppresses the Groq
    # fallback -- so a night it declines to publish exits non-zero, Groq
    # generates the day at 01:00 UTC, and nothing is wrong. Counting that as a
    # loop failure would turn the delivery tile red on correct behaviour, which
    # is how a signal stops being read. Its real health is its own panel, which
    # counts published readings (24/24) rather than exit codes.
    "rashifal-generate.yml",
)

#: A run that ended in one of these DID its job. Everything else is a failure.
#:
#: AN ALLOW-LIST OF FAILURES WAS THE WRONG WAY ROUND, and this module already
#: knew that: `LOOP_WORKFLOWS` above is defined as "every workflow except the PR
#: gates ... so the list grows by default rather than by remembering", with a
#: declared complement and an exhaustiveness test. The identical reasoning
#: applies to conclusions and was not carried across.
#:
#: What it cost: `FAILED_CONCLUSIONS = ("failure", "timed_out", "cancelled")`
#: omitted `startup_failure` -- invalid workflow YAML, a missing secret, a runner
#: that could not start -- which is a leg that produced NOTHING. So a bad `on:`
#: block landing in `agent-steward.yml` would kill the loop for days while this
#: tile read `0 Failed today, live` and raised no alert: the 2026-10-18 screen
#: this module exists to prevent, reached through the one conclusion value
#: nobody wrote down. `action_required` and `stale` were missing too.
#:
#: `cancelled` counting as failure is the case that made the direction obvious:
#: it is what `timeout-minutes` reports, and a job killed by the clock did not
#: fail -- it never finished, which is worse.
#:
#: `None` is a run still in flight and is excluded by the caller, not here.
SUCCEEDED_CONCLUSIONS = ("success", "skipped", "neutral")

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
#: measured busiest day. Hitting it sets `truncated`, which the page renders
#: as an "at least" on every affected tile and in the alert --
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
            # WHO SHIPPED IT: the unattended loop, or a session at a keyboard.
            #
            # Read from the PR's AUTHOR TYPE, not its branch name. `issue/*` is
            # the obvious-looking discriminator and it is wrong: PR #471 is an
            # `issue/*` branch opened by a human session, and #445, #443 and
            # the rest of that week are `fix/*` and `feat/*` from the same
            # hands. The branch says what the work was about; only the author
            # says who did it.
            #
            # `user.type == "Bot"` rather than a login allow-list, because the
            # App's login has already changed once in this repo's history and a
            # stale allow-list would silently reclassify every loop PR as human
            # work -- which reads as the loop having stopped shipping.
            "by": "loop" if (p.get("user") or {}).get("type") == "Bot" else "session",
        }

    # Distinct by run id, for the reason stated on `shipped` above and for one
    # more that is specific to the pager. The reasoning was written down for
    # the PR list and not carried to this one, which is the asymmetry: one
    # list enforced its unit and its sibling assumed it.
    #
    # REPRODUCED DETERMINISTICALLY 2026-10-20: `/actions/runs` is newest-first
    # and paged, so a run created BETWEEN the page-1 and page-2 fetches shifts
    # every row one place later. With 150 failed runs and one run starting in
    # that window, page 2 re-serves the last row of page 1 -- 151 rows, 150
    # distinct ids, the boundary run counted twice on the tile and listed
    # twice in the drill-down. Low probability per render; certain eventually,
    # the window is widest during the run storm that makes paging happen at
    # all.
    failed: dict = {}
    for r in runs:
        path = (r.get("path") or "").rsplit("/", 1)[-1]
        if path not in LOOP_WORKFLOWS:
            continue
        concl = r.get("conclusion")
        # In flight: not a failure, and not an outcome yet. A run with no
        # conclusion is excluded here rather than in the set, because "has not
        # finished" is a different kind of thing from "finished badly".
        if concl is None or concl in SUCCEEDED_CONCLUSIONS:
            continue
        if (r.get("created_at") or "") < since:
            continue
        rid = r.get("id")
        # A row with no id cannot be deduped. Keyed uniquely rather than
        # collapsed: silently dropping all but one of them would be a bigger
        # error than counting one twice, which is the error being fixed.
        failed[rid if rid is not None else ("no-id", len(failed))] = {
            "run": rid,
            "workflow": r.get("name") or path,
            "conclusion": r.get("conclusion"),
            "started": r.get("created_at"),
            "url": r.get("html_url") or "",
        }

    return {
        "since": since,
        # True when a page cap was reached with rows still inside the day, so
        # the counts below are a floor. The page says "at least" rather than
        # printing a number it cannot stand behind.
        # PER ENDPOINT, not one flag for both. A single OR marked the Shipped
        # tile as a floor when only the RUNS read was capped -- rendering
        # "≥0 PRs merged" off a pulls read that was complete, which is a new
        # wrong statement in place of the old missing one. `truncated` stays as
        # the OR for any caller that only wants "was anything capped".
        "truncated": pr_more or runs_more,
        "shipped_truncated": pr_more,
        "failed_truncated": runs_more,
        "shipped": sorted(shipped.values(), key=lambda s: s["merged_at"], reverse=True),
        # The split, so "3 shipped" can be read as what it is. The autonomous
        # loop shipping nothing while a session ships three is a very different
        # day from the loop shipping three, and the single total cannot tell
        # them apart -- which is the whole question this repo's dashboards
        # exist to answer about the agent team.
        "shipped_by_loop": sum(1 for v in shipped.values() if v["by"] == "loop"),
        "shipped_by_session": sum(1 for v in shipped.values() if v["by"] == "session"),
        "failed": sorted(failed.values(), key=lambda f: f["started"] or "", reverse=True),
    }
