#!/usr/bin/env python3
"""GA4 landing-page and funnel data -> JSON on stdout.

Needs the NUMERIC property id (GA4_PROPERTY_ID), not the G-XXXXXXXXXX
measurement id. Mixing those two up is the most common failure here; the
measurement id belongs to the tag on the page, the property id to the API.

--daily SWITCHES DIMENSION, IT DOES NOT ADD ONE
-----------------------------------------------
The default report is landing page x channel, which has no date dimension and
therefore no series: it answers "which pages" and cannot answer "what happened
on Tuesday". `/admin/ops` needed the second question and nothing in this repo
could answer it, which was read for a while as "GA4 has no history". It does --
`runReport` returns whatever dimensions you ask for, and a `date` dimension was
simply never asked for.

Measured 2026-10-14: the daily series returns 97 rows back to 2026-06-28, which
is when the property started collecting, not a retention limit. So this is a
query change, not a storage problem, and nothing has to be retained here for a
line chart to exist.

The two reports stay SEPARATE requests rather than one report dimensioned by
both. Asking for landing x channel x date multiplies the row count by the
window and would hit the 1000-row limit the main report already reports
truncation against -- and the page wants one number per day, not per day per
page.

--daily ALSO ASKS TWO OPTIONAL THINGS, EACH ITS OWN REQUEST (#1277, #1070)
------------------------------------------------------------------------
`returning_users` per day (`activeUsers` x `newVsReturning`, the `returning` value; NOT
`activeUsers - newUsers`, a different quantity) and `admin_sessions` per day (sessions
landing on /admin, which #735 stopped tagging on 2026-11-12, so a later nonzero day is
a leak). Each fails alone: an `ApiError` of any status voids only that field (null,
with a status naming the HTTP code) and the base series survives; the first request
stays fatal, as before. Returning counts are user-days, not people: someone active on
three days counts three times.

--events IS A THIRD SEPARATE REQUEST SET (#782)
-----------------------------------------------
`cta_click` (#570, emitted by static/analytics.js with `from_path` / `to_path`)
was unreadable here: no export asked for an event name, so every metric that
claimed a click was "undetermined", not zero. `--events` asks two things as two
requests, because they fail differently. The count of events by name needs
nothing from the property. The from/to split needs `from_path` and `to_path`
registered as custom dimensions in GA4 Admin > Custom definitions, and until
they are the Data API answers HTTP 400, not `(not set)` -- so the total must
survive that failure instead of dying with it. One request dimensioned by event x
two params would also multiply rows. Only a 400 on the split is read as
"unregistered"; a 403 or a 5xx still fails the run.

`--events` also carries `journey_events` (#1469): `{count, since, partial_history}` for
every name in JOURNEY_SINCE, from the rows it already fetched. agent-measure runs
`--events` but not `--journeys`, so a declared event GA4 returned no row for read as
absent; it now reads 0 with its since-date -- unless the property was empty or the
list truncated, where count is null with a reason.

--trend IS THE PREVIOUS WINDOW GA4 NEVER HAD (#1115)
----------------------------------------------------
The analyst reported "no GA4 previous-window export" in four reports running, so
a GSC impressions rise (+145%) could not be tied to sessions or users.
`--trend` asks the same question of two adjacent windows -- the current one and
one of the SAME LENGTH ending the day before it starts, as `fetch_gsc.py --trend`
does -- as four requests (site totals and by-channel, per window; no `date`
dimension). GA4 holds the history; it was never asked for.

`activeUsers` per channel do NOT add up to the site figure (one person can
arrive through two channels), so the by-channel users are never summed here and
`coverage_note` says so. A previous window with 0 sessions is stated as such:
the property may simply not have been collecting, which is not a collapse.

--journeys IS LANDING PAGE x EVENT, SPLIT BY PARAMETER (#1226, #1070)
--------------------------------------------------------------------
#1070's metric is a completion ratio (completed / submitted) per tool, and "which
landing pages lead to a tool being used". `--events` counts events site-wide and
cannot say which page the visitor arrived on; the default report has landings but no
events. `--journeys` asks four things as FOUR requests, because they fail
differently: (A) landing page x eventName with `sessions` and `eventCount`, which
needs nothing from the property; and (B, C, D) eventName x one of `customEvent:tool`,
`customEvent:event_type`, `customEvent:mode`, each of which needs that parameter
registered as a custom dimension (GA4 Admin > Custom definitions, an owner step on
#1070). An unregistered one answers HTTP 400, so each split is its own request and a
400 voids only that split (`status: "unregistered"`), as `--events` treats
`cta_click` (#782). Only a 400 means unregistered; a 403 or a 5xx fails the run.

Landings are folded to a path (query string, fragment and trailing slash dropped, as
the analyst definition requires) and rows that fold together are summed: a session has
one landing, so summing sessions over landings for ONE event is safe. `sessions` are
NOT additive across events -- one session that submits and then completes is in both
rows -- and `coverage_note` says so. Every truncation at LIMIT is reported.

`since` is the date an event began to exist; a zero before it is not a measurement.
`tool_submitted` has no date here because this file cannot know when #1226's client
change deployed: it stays null, and `partial_history` is then null (unknown), never
false, until someone records the deploy.

NOT WIRED INTO CI. Calling this from .github/workflows/agent-measure.yml is a
workflow edit the App token cannot push (#421); it is a separate owner or session
act, to bundle with #1205's step.

--cohorts SIZES THE AUTOMATED SHARE OF EACH CHANNEL (#1364)
----------------------------------------------------------
The analyst said "not measured" for the automated share of Direct three reports running:
the only browser / device / country breakdown is `--anomalies`, which covers the spike
days (7 of 28), not the window. `--cohorts` asks the WHOLE window as two requests: (1)
channel x browser x device x country with `sessions`, `engagedSessions` and
`userEngagementDuration`, and (2) by channel alone, which is the exact denominator -- the
cohort request can be truncated, the channel request cannot in practice. Either failing
fails the run, as the default report does. It filters nothing and changes no other export.

`zero_engagement` is a FLAG on a cohort, not a verdict: GA4 cannot prove automation, and
a real cohort can also read zero engagement. A cohort is flagged at 20 or more sessions
and zero engaged sessions. The threshold is a false-positive bound: Direct's engaged rate
is 19% (#1364), so a cohort of 20 genuine readers is all-zero with probability
0.81^20 ~= 1.5%; at 10 sessions it would be 12%. It is deliberately not `explain()`'s
`dead` test, which has no minimum and judges one day's top-10 tech rows as a hint (rates
rounded to 2 places), where this is a window-wide count meant to be quoted. Cohorts under
20 sessions are never counted, so the headline is a LOWER BOUND on the automated share
(`small_cohort_sessions` says how many sessions that leaves unjudged). `engaged_rate` is
recomputed from sums, never averaged over cohorts.

NOT WIRED INTO CI, like --journeys: `agent-measure.yml` does not call it, and that is a
workflow edit the App token cannot push (#421). Nor is it yet mentioned in
`.claude/agents/analyst.md` (that edit was denied by the harness); both are follow-ups on #1364,
so until then the analyst only has this export when someone runs it by hand.

--page-locations SIZES WHAT STILL REACHES GA4 WITH A QUERY STRING (#1237)
-------------------------------------------------------------------------
#1066 (city) and #1093 (email, token) fixed leaks into GA4's `page_location` by stripping
those parameters client-side (`static/analytics.js` PII_PARAMS), and each issue's check is
"does a `page_location` carrying the parameter still arrive". Nothing here could answer
that. `--page-locations` asks two requests: (A) `pageLocation` x `eventCount` filtered to
locations CONTAINING "?", with the TOTAL aggregation, and (B) the unfiltered `eventCount`
total as the denominator. Either failing fails the run, with no partial file: a silent zero
would read as "no leak". These are EVENTS, not pageviews -- a page_view, a scroll and a
cta_click on one URL are three.

THE RAW LOCATION NEVER LEAVES `fold_location`. Output goes to /tmp and may be posted into
a report, and a leaked value is exactly the defect being measured, so each location is
folded to a SHAPE -- (path, sorted parameter NAMES) -- and the shapes are summed. Values,
host, fragment and userinfo are dropped; a path segment that holds an `@` (or `%40`) or runs
over 40 characters is `<redacted>`, and a parameter name is emitted only if it is a plain
identifier, because `?a@b.com` is a parameter NAME with no value. `watch` and `by_param` count
EVERY shape; only `rows` is capped. `coverage_pct` is events in the fetched rows over
events carrying a query string, 100 unless truncated -- not over all events, which would
read ~1% and look like a failed fetch.

A zero proves the fix only when the window starts after the fix's deploy date (this file
does not know those dates), and GA4 can threshold low-volume rows, so a zero can understate.

NOT WIRED INTO CI, like --journeys and --cohorts: calling this from agent-measure.yml is a
workflow edit the App token cannot push (#421). Wiring it is a separate sub-issue of #1237.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from urllib.parse import unquote, unquote_plus, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gapi import ApiError, post, token, window  # noqa: E402

LIMIT = 1000
API = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"
CTA_EVENT = "cta_click"
NOT_SET = "(not set)"
# --daily admin landings (#1277): /admin, /admin/..., /admin?... but not /administer.
ADMIN_LANDING_RE = "/admin([/?].*)?"
# The event is emitted from PR #688, merged 2026-11-03 04:42Z; before that a zero is
# not a measurement of anything.
CTA_SINCE = "2026-11-03"

# --journeys (#1226). The event names this issue family declares, each with the date
# it began to exist (None = not established here; see the module docstring).
# tool_submitted: #1226 part 1, commit 9b9ee35; its deploy date is unknown to this file,
# so it stays None until recorded. The four completion events: PR #1218 (0416530),
# merged 2026-11-18T12:53:58Z (`git log -1 --format=%cI 0416530`). cta_click: CTA_SINCE.
# kundli_generated, ask_answered and subscribe_completed predate this work and no date
# is verified here, so None rather than a guess.
JOURNEY_SINCE = {
    "tool_submitted": None,
    "kundli_generated": None,
    "matching_completed": "2026-11-18",
    "numerology_completed": "2026-11-18",
    "muhurat_searched": "2026-11-18",
    "dosha_check_completed": "2026-11-18",
    "ask_answered": None,
    "subscribe_completed": None,
    "cta_click": CTA_SINCE,
}
JOURNEY_EVENTS = tuple(JOURNEY_SINCE)
# Each split is its own request (an unregistered custom dimension answers 400), filtered
# to the events that carry that parameter: tool on tool_submitted; event_type and mode
# on muhurat_searched (templates/muhurat_finder.html, #1217).
JOURNEY_SPLITS = (
    ("tool", "customEvent:tool", ("tool_submitted",)),
    ("event_type", "customEvent:event_type", ("muhurat_searched",)),
    ("mode", "customEvent:mode", ("muhurat_searched",)),
)


def daily(args, start: str, end: str, bearer: str) -> int:
    """One row per day: active users, sessions, new users, returning users, admin landings.

    `activeUsers` is the headline, not `sessions`: a single visitor reloading a
    kundli produces several sessions and one user, and the question this page
    asks is how many people came.

    GA4 returns the date as YYYYMMDD with no separators; it is normalised to
    ISO here so the page never has to parse two date formats. Days with no
    traffic are ABSENT from the response rather than zero -- they are filled in
    below, because a chart that skips a day silently draws a flat line through
    an outage.
    """
    data = post(API.format(pid=args.property), {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": "date"}],
        "metrics": [{"name": "activeUsers"}, {"name": "sessions"}, {"name": "newUsers"}],
        "orderBys": [{"dimension": {"dimensionName": "date"}}],
        "limit": 400,
    }, bearer)

    got = {}
    for r in data.get("rows", []):
        raw = r["dimensionValues"][0]["value"]
        iso = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 else raw
        got[iso] = {"date": iso,
                    "active_users": int(r["metricValues"][0]["value"]),
                    "sessions": int(r["metricValues"][1]["value"]),
                    "new_users": int(r["metricValues"][2]["value"])}

    def _iso(raw: str) -> str:
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 else raw

    # Extra requests: ApiError subclasses SystemExit, so `except Exception` would miss it.
    # Any status voids only its own field; network timeouts still propagate as for the
    # first request.
    returning, ret_status = {}, "ok"
    try:
        rdata = post(API.format(pid=args.property), {
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": "date"}, {"name": "newVsReturning"}],
            "metrics": [{"name": "activeUsers"}],
            "limit": 1200,
        }, bearer)
        for r in rdata.get("rows", []):
            if r["dimensionValues"][1]["value"] == "returning":
                returning[_iso(r["dimensionValues"][0]["value"])] = int(r["metricValues"][0]["value"])
    except ApiError as e:
        ret_status = f"unavailable (HTTP {e.status})"

    admin, admin_status = {}, "ok"
    try:
        adata = post(API.format(pid=args.property), {
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": "date"}],
            "metrics": [{"name": "sessions"}],
            "dimensionFilter": {"filter": {
                "fieldName": "landingPagePlusQueryString",
                "stringFilter": {"matchType": "FULL_REGEXP", "value": ADMIN_LANDING_RE}}},
            "limit": 400,
        }, bearer)
        for r in adata.get("rows", []):
            admin[_iso(r["dimensionValues"][0]["value"])] = int(r["metricValues"][0]["value"])
    except ApiError as e:
        admin_status = f"unavailable (HTTP {e.status})"

    # A day with no `returning` row is 0 only when the request succeeded; on failure it is
    # unknown, and 0 would read as "nobody came back".
    ok_ret, ok_admin = ret_status == "ok", admin_status == "ok"
    rows, d = [], datetime.strptime(start, "%Y-%m-%d").date()
    last = datetime.strptime(end, "%Y-%m-%d").date()
    while d <= last:
        iso = d.isoformat()
        row = dict(got.get(iso, {"date": iso, "active_users": 0,
                                 "sessions": 0, "new_users": 0, "no_data": True}))
        row["returning_users"] = returning.get(iso, 0) if ok_ret else None
        row["admin_sessions"] = admin.get(iso, 0) if ok_admin else None
        rows.append(row)
        d += timedelta(days=1)

    ret_days = sum(r["returning_users"] for r in rows) if ok_ret else None
    total_users = sum(r["active_users"] for r in rows)
    print(json.dumps({
        "source": "ga4", "property": args.property, "window": [start, end],
        "dimensions": ["date"],
        "note": "window excludes the last 3 days - GA4 standard reports lag 24-48h. "
                "A day absent from the API is emitted as 0 with no_data=true, so a "
                "gap in collection is visible rather than drawn as a flat line.",
        "days": len(rows),
        "days_with_traffic": sum(1 for r in rows if not r.get("no_data")),
        "returning": {
            "status": ret_status,
            "user_days": ret_days,
            "share_pct": (round(100 * ret_days / total_users, 1)
                          if ok_ret and total_users else None),
            "note": "User-days, not unique people: a person active on three days counts "
                    "three times, so the share is of daily active users who were "
                    "returning, not of visitors. Rows whose newVsReturning is "
                    "(not set) are excluded.",
        },
        "admin_status": admin_status,
        "admin_note": "admin_sessions counts sessions landing on /admin*. #735 stopped "
                      "analytics on /admin/* on 2026-11-12, so a nonzero day from then "
                      "on is internal traffic leaking into the property.",
        "rows": rows,
    }, indent=2))
    return 0


def spike_days(rows: list[dict], top: int = 3) -> list[dict]:
    """Days whose active users clear max(2 x median, median + 10) and 15 users.

    A rule simple enough to argue with. The 2026-11-06 spike (57 users against a
    median in the 20s) is exactly what it exists to catch: GA4's own insight
    card flagged it, the analyst could not explain it, and the owner had to go
    and ask. Returned most extreme first, at most `top`.
    """
    vals = sorted(r.get("active_users", 0) for r in rows if not r.get("no_data"))
    if len(vals) < 7:
        return []
    med = vals[len(vals) // 2]
    bar = max(2 * med, med + 10, 15)
    hits = [dict(r, median=med, threshold=bar) for r in rows
            if not r.get("no_data") and r.get("active_users", 0) >= bar]
    return sorted(hits, key=lambda r: -r["active_users"])[:top]


def watch_days(rows: list[dict], spikes: list[dict], top: int = 7) -> list[dict]:
    """Days at or above median + 10 that `spikes` did not take (#1236).

    The spike bar is max(2 x median, median + 10, 15): at a median of 22 it is 44, so
    on 2026-11-16 five of the seven days at 32+ users had no named source and the
    analyst reported "not determined" four runs running. This is the tier between.
    A day over the spike bar that `spike_days`' own cap of 3 cut falls here, not into
    a gap. The median is computed as in `spike_days` on purpose: that function is
    pinned by test_analyst_levers and a mutation row, so it is not refactored.
    Returned most extreme first, at most `top`.
    """
    vals = sorted(r.get("active_users", 0) for r in rows if not r.get("no_data"))
    if len(vals) < 7:
        return []
    med = vals[len(vals) // 2]
    taken = {s["date"] for s in spikes}
    hits = [dict(r, median=med, threshold=med + 10) for r in rows
            if not r.get("no_data") and r.get("active_users", 0) >= med + 10
            and r["date"] not in taken]
    return sorted(hits, key=lambda r: -r["active_users"])[:top]


def _breakdown(rows: list[dict], dims: list[str]) -> list[dict]:
    out = []
    for r in rows:
        mv = [float(m["value"]) for m in r["metricValues"]]
        sess, new, engaged, secs = (mv + [0, 0, 0, 0])[:4]
        out.append({**{d: r["dimensionValues"][i]["value"] for i, d in enumerate(dims)},
                    "sessions": int(sess), "new_users": int(new),
                    "engaged_rate": round(engaged / sess, 2) if sess else None,
                    "avg_engagement_seconds": round(secs / sess, 1) if sess else None})
    return out


def explain(by_source: list[dict], by_tech: list[dict]) -> str:
    """One line a reader can act on. A hint, never a verdict: say what to check."""
    if not by_source:
        return "no breakdown rows returned"
    top = by_source[0]
    sess = sum(r["sessions"] for r in by_source) or 1
    engaged = sum((r["engaged_rate"] or 0) * r["sessions"] for r in by_source) / sess
    secs = sum((r["avg_engagement_seconds"] or 0) * r["sessions"] for r in by_source) / sess
    src = top.get("sessionSourceMedium", "?")
    parts = [f"top source {src} ({top['sessions']} sessions) landing on "
             f"{top.get('landingPagePlusQueryString', '?')}"]
    # Judge per SEGMENT, not on the blend (2026-11-16): the 11-06 spike averaged
    # 37% engaged and was called "real readers", while its tech breakdown held 19
    # US desktop/mobile sessions -- browser "(not set)" among them -- with exactly
    # zero engagement. Averaging let the bots hide inside the readers.
    tech_total = sum(r["sessions"] for r in by_tech) or 0
    dead = [r for r in by_tech if not r["engaged_rate"] and not r["avg_engagement_seconds"]]
    dead_n = sum(r["sessions"] for r in dead)
    if engaged < 0.15 and secs < 3:
        parts.append(f"engaged rate {engaged:.0%} and {secs:.1f}s average engagement: "
                     "looks automated, not readers")
    elif tech_total and dead_n / tech_total >= 0.3:
        who = ", ".join(f"{r.get('browser', '?')}/{r.get('deviceCategory', '?')}/"
                        f"{r.get('country', '?')} {r['sessions']}" for r in dead[:3])
        parts.append(f"MIXED: {dead_n} of {tech_total} sessions had zero engagement ({who}) "
                     "and look automated; the rest look like real readers")
    else:
        parts.append(f"engaged rate {engaged:.0%}, {secs:.1f}s average: looks like real readers")
    if src.startswith("google / organic"):
        parts.append("google/organic with flat Search Console clicks usually means Google "
                     "Discover; compare gsc-discover.json for that date")
    if by_tech:
        t = by_tech[0]
        parts.append(f"mostly {t.get('browser', '?')} on {t.get('deviceCategory', '?')} in "
                     f"{t.get('country', '?')}")
    return "; ".join(parts)


def anomalies(args, start: str, end: str, bearer: str) -> int:
    """Find unusual days in the window and say where their visitors came from."""
    url = API.format(pid=args.property)
    data = post(url, {"dateRanges": [{"startDate": start, "endDate": end}],
                      "dimensions": [{"name": "date"}], "metrics": [{"name": "activeUsers"}],
                      "limit": 400}, bearer)
    rows = []
    for r in data.get("rows", []):
        raw = r["dimensionValues"][0]["value"]
        rows.append({"date": f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 else raw,
                     "active_users": int(r["metricValues"][0]["value"])})
    metrics = [{"name": m} for m in ("sessions", "newUsers", "engagedSessions",
                                     "userEngagementDuration")]
    spikes = spike_days(rows)
    watch = watch_days(rows, spikes)
    # Uncapped count, so a truncation is visible in the file rather than silent.
    watch_omitted = len(watch_days(rows, spikes, top=len(rows))) - len(watch)

    def day_breakdown(day: dict) -> tuple[list[dict], list[dict]]:
        rng = [{"startDate": day["date"], "endDate": day["date"]}]
        src_dims = ["sessionSourceMedium", "landingPagePlusQueryString"]
        tech_dims = ["browser", "deviceCategory", "country"]
        order = [{"metric": {"metricName": "sessions"}, "desc": True}]
        a = post(url, {"dateRanges": rng, "dimensions": [{"name": d} for d in src_dims],
                       "metrics": metrics, "orderBys": order, "limit": 15}, bearer)
        b = post(url, {"dateRanges": rng, "dimensions": [{"name": d} for d in tech_dims],
                       "metrics": metrics, "orderBys": order, "limit": 10}, bearer)
        return (_breakdown(a.get("rows", []), src_dims),
                _breakdown(b.get("rows", []), tech_dims))

    found = []
    for day in spikes:
        by_source, by_tech = day_breakdown(day)
        found.append({**day, "tier": "spike", "explanation": explain(by_source, by_tech),
                      "by_source": by_source, "by_tech": by_tech})
    watched = []
    for day in watch:
        # Only here: the workflow deletes the whole file on any failure, so an error on
        # this optional tier must not erase the spike breakdown above (#1236).
        try:
            by_source, by_tech = day_breakdown(day)
            why = explain(by_source, by_tech)
        except ApiError as e:
            by_source, by_tech = [], []
            why = f"breakdown failed (HTTP {e.status})"
        watched.append({**day, "tier": "watch", "explanation": why,
                        "by_source": by_source, "by_tech": by_tech})
    print(json.dumps({"source": "ga4", "property": args.property, "window": [start, end],
                      "rule": "active users >= max(2 x median, median + 10, 15)",
                      "watch_rule": "active users >= median + 10, not a spike",
                      "days_checked": len(rows), "spikes": found,
                      "watch": watched, "watch_omitted": watch_omitted}, indent=2))
    return 0


def events(args, start: str, end: str, bearer: str) -> int:
    """Event counts by name, plus the `cta_click` from/to split (#782).

    Two requests, not one (see the module docstring). A 400 on the split is the
    Data API refusing `customEvent:from_path` because it is not a registered custom
    dimension -- an owner-side GA4 setting the loop cannot make -- and is reported
    in `coverage_note` while the total still stands. Any other error propagates.
    `journey_events` gives {count, since, partial_history} for every declared event
    from the same rows (#1469); count is null, with a reason, when zero is unprovable.
    """
    url = API.format(pid=args.property)
    ranges = [{"startDate": start, "endDate": end}]
    data = post(url, {
        "dateRanges": ranges,
        "dimensions": [{"name": "eventName"}],
        "metrics": [{"name": "eventCount"}],
        "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
        "limit": LIMIT,
    }, bearer)
    rows = [{"event": r["dimensionValues"][0]["value"],
             "count": int(r["metricValues"][0]["value"])}
            for r in data.get("rows", [])]
    row_count = data.get("rowCount", len(rows))
    truncated = row_count > len(rows)
    events_total = sum(r["count"] for r in rows)
    cta_count = sum(r["count"] for r in rows if r["event"] == CTA_EVENT)

    unregistered = False
    split_raw, split_truncated = [], False
    try:
        split = post(url, {
            "dateRanges": ranges,
            "dimensions": [{"name": "eventName"},
                           {"name": "customEvent:from_path"},
                           {"name": "customEvent:to_path"}],
            "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {"filter": {
                "fieldName": "eventName",
                "stringFilter": {"matchType": "EXACT", "value": CTA_EVENT}}},
            "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
            "limit": LIMIT,
        }, bearer)
    except ApiError as e:
        if e.status != 400:
            raise
        unregistered = True
    else:
        split_raw = [{"from_path": r["dimensionValues"][1]["value"],
                      "to_path": r["dimensionValues"][2]["value"],
                      "count": int(r["metricValues"][0]["value"])}
                     for r in split.get("rows", [])]
        split_truncated = split.get("rowCount", len(split_raw)) > len(split_raw)
    all_not_set = bool(split_raw) and all(
        r["from_path"] == NOT_SET and r["to_path"] == NOT_SET for r in split_raw)
    split_rows = [] if (unregistered or all_not_set) else split_raw
    split_available = bool(split_rows)

    parts = []
    if not rows:
        parts.append("the property recorded no events at all in the window, so "
                     f"{CTA_EVENT} 0 says only that the window is empty")
    elif cta_count == 0:
        parts.append(f"{CTA_EVENT}: 0 events recorded in the window -- a measurement, "
                     "not an unreadable export")
    else:
        parts.append(f"{CTA_EVENT}: {cta_count} events recorded in the window")
    if unregistered:
        parts.append("the from/to split is NOT available: GA4 answered HTTP 400 for "
                     "customEvent:from_path / customEvent:to_path, i.e. they are not "
                     "registered as custom dimensions (GA4 Admin > Custom definitions), "
                     "an owner-side property setting the loop cannot make; the TOTAL "
                     "count above is still valid")
    elif all_not_set:
        parts.append("the from/to split is NOT available: every row reports "
                     f"{NOT_SET} for from_path and to_path, so the parameters are not "
                     "registered as custom dimensions (or were never collected); "
                     "the TOTAL count above is still valid")
    elif cta_count and not split_rows:
        parts.append("the from/to split returned no rows although the total is "
                     "non-zero; the TOTAL count is still valid")
    if split_truncated:
        parts.append("the from/to split was TRUNCATED at the row limit")
    if truncated:
        parts.append(f"TRUNCATED: {len(rows)} of {row_count} event names returned")
    parts.append(f"{CTA_EVENT} exists only from {CTA_SINCE} 04:42Z (PR #688), so a "
                 f"window starting before 2026-12-01 holds partial history")

    # #1469: a declared event GA4 did not return used to be no row at all, which the
    # analyst read as "absent". Same rows, no new request. A name missing from the
    # list is a measured zero ONLY when the list is complete and non-empty: an empty
    # property or a truncated list cannot tell "zero" from "not seen".
    by_name = {r["event"]: r["count"] for r in rows}
    journey_events = {}
    for name in JOURNEY_SINCE:
        if name in by_name:
            entry = {"count": by_name[name]}  # exact even when the list was truncated
        elif not rows:
            entry = {"count": None, "reason": "the property recorded no events in the "
                     "window, so zero is not a measurement"}
        elif truncated:
            entry = {"count": None, "reason": "the event list was truncated at the row "
                     "limit, so a name may be cut off"}
        else:
            entry = {"count": 0}
        journey_events[name] = {**entry, **_since_note(start, name)}
    unknown = sum(e["count"] is None for e in journey_events.values())
    parts.append("journey_events: a count of 0 is a measurement over the window; "
                 "partial_history true means the event began after the window start")
    if unknown:
        parts.append(f"journey_events: {unknown} of {len(journey_events)} unknown -- "
                     + next(e["reason"] for e in journey_events.values()
                            if e["count"] is None))

    print(json.dumps({
        "source": "ga4", "property": args.property, "window": [start, end],
        "dimensions": ["eventName"],
        "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
        "row_count": row_count, "truncated": truncated,
        "rows": rows, "events_total": events_total,
        "coverage_note": "; ".join(parts),
        CTA_EVENT: {"count": cta_count, "split_available": split_available,
                    "rows": split_rows},
        "journey_events": journey_events,
    }, indent=2))
    return 0


def fold_landing(landing: str) -> str:
    """A landing as a path: no query string, fragment or trailing slash.

    Unlike busiest_pages.fold this DROPS NOTHING: an unreadable landing such as
    "(not set)" stays visible as its own row, so the export's totals still add up.
    """
    path = landing.split("?", 1)[0].split("#", 1)[0]
    if path.startswith("/") and path != "/":
        path = path.rstrip("/") or "/"
    return path


def _in_list(names) -> dict:
    return {"filter": {"fieldName": "eventName",
                       "inListFilter": {"values": list(names)}}}


def _since_note(start: str, event: str) -> dict:
    since = JOURNEY_SINCE[event]
    # None, not False, when the date is unknown: "no partial history" would be a claim.
    return {"since": since,
            "partial_history": None if since is None else start < since}


def journeys(args, start: str, end: str, bearer: str) -> int:
    """Landing x event rows plus tool / event_type / mode splits (#1226).

    Four requests (see the module docstring). A 400 on a split marks that split
    `unregistered` and leaves request A and the other splits intact; any other
    error propagates and fails the run.
    """
    url = API.format(pid=args.property)
    ranges = [{"startDate": start, "endDate": end}]
    order = [{"metric": {"metricName": "eventCount"}, "desc": True}]
    data = post(url, {
        "dateRanges": ranges,
        "dimensions": [{"name": "landingPage"}, {"name": "eventName"}],
        "metrics": [{"name": "sessions"}, {"name": "eventCount"}],
        "dimensionFilter": _in_list(JOURNEY_EVENTS),
        "orderBys": order,
        "limit": LIMIT,
    }, bearer)
    folded: dict[tuple[str, str], dict] = {}
    raw_rows = data.get("rows", [])
    for r in raw_rows:
        key = (fold_landing(r["dimensionValues"][0]["value"]),
               r["dimensionValues"][1]["value"])
        cur = folded.setdefault(key, {"landing": key[0], "event": key[1],
                                      "sessions": 0, "event_count": 0})
        cur["sessions"] += int(r["metricValues"][0]["value"])
        cur["event_count"] += int(r["metricValues"][1]["value"])
    rows = sorted(folded.values(), key=lambda r: (-r["event_count"], r["landing"], r["event"]))
    row_count = data.get("rowCount", len(raw_rows))
    truncated = row_count > len(raw_rows)
    totals = dict.fromkeys(JOURNEY_EVENTS, 0)
    for r in rows:
        totals[r["event"]] = totals.get(r["event"], 0) + r["event_count"]

    splits, parts = {}, []
    for name, dim, names in JOURNEY_SPLITS:
        entry = {"dimension": dim, "events": list(names), "rows": [],
                 "row_count": 0, "truncated": False}
        try:
            got = post(url, {
                "dateRanges": ranges,
                "dimensions": [{"name": "eventName"}, {"name": dim}],
                "metrics": [{"name": "eventCount"}],
                "dimensionFilter": _in_list(names),
                "orderBys": order,
                "limit": LIMIT,
            }, bearer)
        except ApiError as e:
            if e.status != 400:
                raise
            entry["status"] = "unregistered"
            parts.append(f"split {name}: NOT available, GA4 answered HTTP 400 for {dim}, "
                         "i.e. it is not registered as a custom dimension (GA4 Admin > "
                         "Custom definitions, an owner step on #1070); the landing x event "
                         "rows are still valid")
        else:
            g_rows = got.get("rows", [])
            entry["rows"] = [{"event": r["dimensionValues"][0]["value"],
                              "value": r["dimensionValues"][1]["value"],
                              "count": int(r["metricValues"][0]["value"])}
                             for r in g_rows]
            entry["row_count"] = got.get("rowCount", len(g_rows))
            entry["truncated"] = entry["row_count"] > len(g_rows)
            if entry["rows"] and all(r["value"] == NOT_SET for r in entry["rows"]):
                # Same reading as --events: a registered-too-late or never-collected
                # parameter reports (not set), which is not a distribution.
                entry["status"] = "not_set"
                entry["rows"] = []
                parts.append(f"split {name}: every row reports {NOT_SET}, so {dim} was "
                             "never collected or is not registered; not emitted as data")
            else:
                entry["status"] = "ok"
            if entry["truncated"]:
                parts.append(f"split {name} TRUNCATED: {len(g_rows)} of "
                             f"{entry['row_count']} rows returned")
        splits[name] = entry

    parts.insert(0, "`sessions` per landing x event are NOT additive across events: one "
                    "session that submits and then completes is counted in both rows, so "
                    "never add sessions over different events (over landings, for one "
                    "event, they are additive: a session has one landing)")
    if truncated:
        parts.append(f"TRUNCATED: {len(raw_rows)} of {row_count} landing x event rows "
                     "returned")
    since_note = {e: _since_note(start, e) for e in JOURNEY_EVENTS}
    if any(v["partial_history"] for v in since_note.values()):
        parts.append("a zero for an event before its `since` is not a measurement; "
                     "partial_history marks the events whose window starts earlier")
    if any(v["since"] is None for v in since_note.values()):
        parts.append("events with since null have no verified start date here "
                     "(tool_submitted: from #1226's deploy, not recorded); a zero for "
                     "them is not yet a measurement")

    print(json.dumps({
        "source": "ga4", "property": args.property, "mode": "journeys",
        "window": [start, end],
        "dimensions": ["landingPage", "eventName"],
        "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
        "row_count": row_count, "truncated": truncated,
        "landing_count": len({r["landing"] for r in rows}),
        "event_totals": totals,
        "events": since_note,
        "rows": rows,
        "splits": splits,
        "coverage_note": "; ".join(parts),
    }, indent=2))
    return 0


TREND_METRICS = ("sessions", "activeUsers", "newUsers", "engagedSessions",
                 "userEngagementDuration")
TREND_KEYS = ("sessions", "active_users", "new_users", "engaged_sessions",
              "engagement_seconds")


def previous_window(start: str, end: str) -> tuple[str, str]:
    """The window of the SAME LENGTH ending the day before `start` (as fetch_gsc)."""
    s = datetime.strptime(start, "%Y-%m-%d")
    span = (datetime.strptime(end, "%Y-%m-%d") - s).days
    prev_end = s - timedelta(days=1)
    return ((prev_end - timedelta(days=span)).strftime("%Y-%m-%d"),
            prev_end.strftime("%Y-%m-%d"))


def _trend_values(mv: list) -> dict:
    return {k: int(float(m["value"])) for k, m in zip(TREND_KEYS, mv)}


def _delta(cur: dict, pre: dict) -> tuple[dict, dict]:
    """Per-metric change and percentage. None, not 0 and not infinity, when the
    previous value is 0: there is no percentage change from nothing."""
    delta = {k: cur[k] - pre[k] for k in TREND_KEYS}
    pct = {k: round(delta[k] / pre[k] * 100, 1) if pre[k] else None for k in TREND_KEYS}
    return delta, pct


def _trend_window(url: str, bearer: str, start: str, end: str) -> tuple[dict, dict, int]:
    """(site totals, {channel -> values}, channel rowCount) for one window. Two requests.

    GA4 sends no `rows` key for an empty window; that is zeros, not an error.
    """
    rng = [{"startDate": start, "endDate": end}]
    metrics = [{"name": m} for m in TREND_METRICS]
    tot = post(url, {"dateRanges": rng, "metrics": metrics}, bearer)
    t_rows = tot.get("rows") or []
    totals = _trend_values(t_rows[0]["metricValues"]) if t_rows else dict.fromkeys(TREND_KEYS, 0)
    ch = post(url, {"dateRanges": rng,
                    "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                    "metrics": metrics,
                    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
                    "limit": LIMIT}, bearer)
    c_rows = ch.get("rows") or []
    by = {r["dimensionValues"][0]["value"]: _trend_values(r["metricValues"]) for r in c_rows}
    return totals, by, ch.get("rowCount", len(c_rows))


def trend(args, start: str, end: str, bearer: str) -> int:
    """This window against the one immediately before it (#1115): totals and by channel."""
    url = API.format(pid=args.property)
    prev_start, prev_end = previous_window(start, end)
    cur_tot, cur_by, cur_n = _trend_window(url, bearer, start, end)
    pre_tot, pre_by, pre_n = _trend_window(url, bearer, prev_start, prev_end)

    zero = dict.fromkeys(TREND_KEYS, 0)
    rows = []
    for ch in set(cur_by) | set(pre_by):
        c, p = cur_by.get(ch), pre_by.get(ch)
        d, pct = _delta(c or zero, p or zero)
        rows.append({"channel": ch, "current": c or zero, "previous": p or zero,
                     "delta": d, "delta_pct": pct,
                     "is_new": p is None, "is_gone": c is None})
    # Absolute size of the movement, so the biggest fall is as visible as the biggest rise.
    rows.sort(key=lambda r: (-abs(r["delta"]["sessions"]), r["channel"]))
    delta, delta_pct = _delta(cur_tot, pre_tot)

    parts = ["activeUsers per channel do NOT sum to the site total (one person can "
             "appear in two channels): by_channel users must not be added up"]
    if pre_tot["sessions"] == 0:
        parts.append("previous window empty: property may not have been collecting, "
                     "so no change can be read from this comparison")
    for label, tot, by, n in (("current", cur_tot, cur_by, cur_n),
                              ("previous", pre_tot, pre_by, pre_n)):
        got = sum(v["sessions"] for v in by.values())
        if tot["sessions"] and got < tot["sessions"]:
            parts.append(f"{label} window: channel rows account for "
                         f"{round(got / tot['sessions'] * 100)}% of the site's "
                         f"{tot['sessions']} sessions")
        if n > len(by):
            parts.append(f"{label} window TRUNCATED: {len(by)} of {n} channel rows returned")

    print(json.dumps({
        "source": "ga4", "property": args.property, "mode": "trend",
        "window": [start, end], "window_prev": [prev_start, prev_end],
        "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
        "totals": {"current": cur_tot, "previous": pre_tot,
                   "delta": delta, "delta_pct": delta_pct},
        "channels_now": len(cur_by), "channels_prev": len(pre_by),
        "coverage_note": "; ".join(parts),
        "by_channel": rows,
    }, indent=2))
    return 0


COHORT_DIMS = ("sessionDefaultChannelGroup", "browser", "deviceCategory", "country")
COHORT_METRICS = ("sessions", "engagedSessions", "userEngagementDuration")
# 20 sessions: see the --cohorts section of the module docstring (0.81^20 ~= 1.5%).
MIN_COHORT_SESSIONS = 20
COHORT_ROWS_SHOWN = 50
# GA4 caps one runReport at 250000 rows; 10000 is far above the ~150 cohorts seen, and a
# truncation is reported in coverage_note rather than assumed away.
COHORT_LIMIT = 10000


def parse_cohorts(raw_rows: list[dict]) -> list[dict]:
    """GA4 cohort rows -> dicts. `(not set)` values stay: dropping them would hide the very
    browserless cohort #1364 is about and make the totals stop adding up."""
    out = []
    for r in raw_rows:
        d, m = r["dimensionValues"], r["metricValues"]
        out.append({"channel": d[0]["value"], "browser": d[1]["value"],
                    "device": d[2]["value"], "country": d[3]["value"],
                    "sessions": int(float(m[0]["value"])),
                    "engaged_sessions": int(float(m[1]["value"])),
                    "engagement_seconds": int(float(m[2]["value"]))})
    return out


def zero_engagement(row: dict, min_sessions: int = MIN_COHORT_SESSIONS) -> bool:
    """A flag, not a verdict: a cohort big enough that zero engaged sessions is not luck."""
    return row["sessions"] >= min_sessions and row["engaged_sessions"] == 0


def channel_summary(channel_totals: dict, rows: list[dict],
                    min_sessions: int = MIN_COHORT_SESSIONS) -> list[dict]:
    """Per channel: totals from the by-channel request, cohort counts from ALL fetched rows."""
    totals = {c: dict(v) for c, v in channel_totals.items()}
    for r in rows:
        # A channel the denominator request lacks (inconsistent response): fall back to rows.
        if r["channel"] not in channel_totals:
            t = totals.setdefault(r["channel"], {"sessions": 0, "engaged_sessions": 0})
            t["sessions"] += r["sessions"]
            t["engaged_sessions"] += r["engaged_sessions"]
    out = []
    for ch, t in totals.items():
        mine = [r for r in rows if r["channel"] == ch]
        zero = [r for r in mine if zero_engagement(r, min_sessions)]
        zero_sessions = sum(r["sessions"] for r in zero)
        small = sum(r["sessions"] for r in mine if r["sessions"] < min_sessions)
        n, eng = t["sessions"], t["engaged_sessions"]
        if n:
            statement = (f"{zero_sessions} of {n} {ch} sessions fall in {len(zero)} cohorts "
                         f"with >={min_sessions} sessions and 0% engagement; {small} more "
                         f"sit in cohorts under {min_sessions} sessions and are not judged")
        else:
            statement = f"no {ch} sessions in the window"
        out.append({"channel": ch, "sessions": n, "engaged_sessions": eng,
                    "engaged_rate": round(eng / n, 4) if n else None,
                    "zero_cohorts": len(zero), "zero_cohort_sessions": zero_sessions,
                    "zero_engagement_share": round(zero_sessions / n, 4) if n else None,
                    "small_cohort_sessions": small, "statement": statement})
    out.sort(key=lambda c: (-c["sessions"], c["channel"]))
    return out


def headline(summary: list[dict], channel: str = "Direct") -> str:
    """The sentence the analyst quotes. Says so when the channel has no sessions."""
    ch = next((c for c in summary if c["channel"] == channel), None)
    if ch is None or not ch["sessions"]:
        return f"no {channel} sessions in the window, so no automated share can be stated"
    return (f"{ch['zero_cohort_sessions']} of {ch['sessions']} {channel} sessions fall in "
            f"cohorts with >={MIN_COHORT_SESSIONS} sessions and 0% engagement")


def cohorts(args, start: str, end: str, bearer: str) -> int:
    """Channel x browser x device x country over the whole window (#1364). Two requests."""
    url = API.format(pid=args.property)
    ranges = [{"startDate": start, "endDate": end}]
    metrics = [{"name": m} for m in COHORT_METRICS]
    order = [{"metric": {"metricName": "sessions"}, "desc": True}]
    data = post(url, {"dateRanges": ranges,
                      "dimensions": [{"name": d} for d in COHORT_DIMS],
                      "metrics": metrics, "orderBys": order, "limit": COHORT_LIMIT}, bearer)
    by_ch = post(url, {"dateRanges": ranges,
                       "dimensions": [{"name": COHORT_DIMS[0]}],
                       "metrics": metrics, "orderBys": order, "limit": COHORT_LIMIT}, bearer)

    raw_rows = data.get("rows") or []
    rows = parse_cohorts(raw_rows)
    row_count = data.get("rowCount", len(raw_rows))
    truncated = len(raw_rows) < row_count
    channel_totals = {}
    for r in by_ch.get("rows") or []:
        m = r["metricValues"]
        channel_totals[r["dimensionValues"][0]["value"]] = {
            "sessions": int(float(m[0]["value"])), "engaged_sessions": int(float(m[1]["value"]))}
    total_sessions = sum(v["sessions"] for v in channel_totals.values())
    rows_sessions = sum(r["sessions"] for r in rows)
    coverage = round(rows_sessions / total_sessions * 100) if total_sessions else None
    summary = channel_summary(channel_totals, rows)

    rows.sort(key=lambda r: (-r["sessions"], r["channel"], r["browser"], r["device"],
                             r["country"]))
    shown = [{**{k: r[k] for k in ("channel", "browser", "device", "country", "sessions",
                                   "engaged_sessions")},
              "engaged_rate": round(r["engaged_sessions"] / r["sessions"], 4)
              if r["sessions"] else None,
              "engagement_seconds": r["engagement_seconds"],
              "avg_engagement_seconds": round(r["engagement_seconds"] / r["sessions"], 1)
              if r["sessions"] else None,
              "zero_engagement": zero_engagement(r)}
             for r in rows[:COHORT_ROWS_SHOWN]]

    parts = ["zero_engagement is a FLAG on a cohort, not a verdict: GA4 cannot prove "
             "automation, and the headline count is a lower bound because cohorts under "
             f"{MIN_COHORT_SESSIONS} sessions are not counted (see small_cohort_sessions)"]
    if coverage is not None and rows_sessions < total_sessions:
        parts.append(f"cohort rows account for {coverage}% of the property's "
                     f"{total_sessions} sessions")
    if row_count > len(raw_rows):
        parts.append(f"TRUNCATED: {len(raw_rows)} of {row_count} cohort rows returned")
    if len(rows) > COHORT_ROWS_SHOWN:
        parts.append(f"rows lists the top {COHORT_ROWS_SHOWN} cohorts of {len(rows)}; "
                     "channel summaries use all of them")

    print(json.dumps({
        "source": "ga4", "property": args.property, "mode": "cohorts",
        "window": [start, end], "dimensions": list(COHORT_DIMS),
        "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
        "min_cohort_sessions": MIN_COHORT_SESSIONS,
        "total_sessions": total_sessions, "rows_sessions": rows_sessions,
        "coverage_pct": coverage, "row_count": row_count, "truncated": truncated,
        "cohort_count": len(rows),
        "headline": headline(summary),
        "channels": summary,
        "rows": shown, "rows_omitted": max(len(rows) - COHORT_ROWS_SHOWN, 0),
        "coverage_note": "; ".join(parts),
    }, indent=2))
    return 0


PAGE_LOCATION_LIMIT = 10000
PAGE_LOCATION_ROWS_SHOWN = 50
# Duplicated from static/analytics.js `var PII_PARAMS`; tests/test_ga4_page_locations_export.py
# regex-parses that list and asserts equality, so the two cannot drift apart silently.
PII_PARAMS = ("q", "city", "email", "token")
REDACTED_SEGMENT = "<redacted>"
REDACTED_NAME = "(redacted-name)"
UNPARSEABLE = "(unparseable)"
# A parameter NAME is attacker-controlled (`?a@b.com` is a bare name), so it is emitted only
# when it is a plain identifier. #1450: a plain-looking identifier is still a leak when it IS a
# value sent without an `=` (`?Ujjain`, `?tok3nSECRET...`), so see `_plain_name` for the two
# extra refusals.
_SAFE_NAME = re.compile(r"[A-Za-z0-9_.\[\]-]{1,32}")
# `routes/kundli.py` serves a saved chart at /r/{short_id}: a capability URL, so the id is as
# good as a password for that chart. The export collapses it to this placeholder.
SNAPSHOT_ID = "<id>"
# A name this long that mixes digits and letters is an id or a token, never a parameter name.
# 20 is the floor of the issue's own wording; the longest real name on the site is far shorter.
_TOKEN_MIN = 20


def _plain_name(part: str, name: str) -> bool:
    """Is this query part's name a parameter NAME rather than a value that arrived as one?

    `part` is the RAW text (before decoding) and `name` its decoded name. A part with no `=` is
    a name only when it is one of the watched PII_PARAMS (`?token`, `?email` are the very
    signals the export counts); any other bare text -- a city, an address, a token -- is a
    value. The raw `=` is checked, not the decoded one, so `?email%3Dx` does not pass as a
    valued `email`. A name that is 20+ characters of digits and letters is token-shaped.
    """
    if "=" not in part and name not in PII_PARAMS:
        return False
    if len(name) >= _TOKEN_MIN and any(c.isdigit() for c in name) and any(c.isalpha() for c in name):
        return False
    return True


def _safe_segment(seg: str) -> str:
    # A double-encoded address (`%2540`) decodes to `%40` one layer later, so any `%25` is
    # refused rather than decoded to the depth an attacker chose.
    if "%25" in seg.lower():
        return REDACTED_SEGMENT
    if "@" in seg or "%40" in seg.lower() or len(seg) > 40:
        return REDACTED_SEGMENT
    return seg


def fold_location(raw: str) -> tuple[str, tuple[str, ...]]:
    """A page_location as (path, sorted parameter NAMES); nothing else survives.

    The raw string is never echoed -- not here, not in an exception. Host, scheme, userinfo,
    fragment and every parameter VALUE are dropped, so an address that reached GA4 in a
    value cannot reach the output. Also dropped: a bare query token that is really a value
    (`?Ujjain`), a token-shaped name, a path segment holding `%25` (a double-encoded address)
    and the id of a /r/<id> kundli snapshot, which becomes `/r/<id>`.
    """
    try:
        u = urlsplit(raw)
    except ValueError:
        return UNPARSEABLE, ()
    segs = u.path.split("/")
    # Top level only: segs[0] is the empty text before the leading slash.
    if len(segs) > 2 and segs[1] == "r" and segs[2]:
        segs[2] = SNAPSHOT_ID
    path = "/".join(_safe_segment(seg) for seg in segs)
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]
    names = set()
    for part in u.query.split("&"):
        name = unquote_plus(part.split("=", 1)[0])
        if not name:
            continue
        if not _plain_name(part, name):
            names.add(REDACTED_NAME)
            continue
        names.add(name if _SAFE_NAME.fullmatch(name) else REDACTED_NAME)
    return path, tuple(sorted(names))


def _watch(shapes: list[dict]) -> dict:
    """Per watched parameter: events, distinct shapes, top 3 paths -- over every shape."""
    out = {}
    for p in PII_PARAMS:
        mine = [s for s in shapes if p in s["params"]]
        by_path: dict[str, int] = {}
        for s in mine:
            by_path[s["path"]] = by_path.get(s["path"], 0) + s["events"]
        top = sorted(by_path.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        out[p] = {"events": sum(s["events"] for s in mine), "shapes": len(mine),
                  "top_paths": [{"path": k, "events": v} for k, v in top]}
    return out


def _by_param(shapes: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for s in shapes:
        for p in s["params"]:
            t = seen.setdefault(p, {"param": p, "events": 0, "shapes": 0})
            t["events"] += s["events"]
            t["shapes"] += 1
    return sorted(seen.values(), key=lambda t: (-t["events"], t["param"]))


def location_headline(total: int, with_query: int | None, rows_events: int,
                      share: float | None, watch: dict, has_rows: bool,
                      lower_bound: tuple[str, ...] = ()) -> str:
    """The sentence #1066 and #1093 quote. Says so when there is nothing to judge.

    `lower_bound` names why the counts may undercount (truncated, rows hidden in (other), rows
    covering less than the total). The sentence is quoted without coverage_note, so the caveat
    has to be in it: a watched count that is a floor must not read as a measured value (#1451).
    """
    # q last: it is the free-text one, the others name an identity.
    order = sorted(PII_PARAMS, key=lambda p: p == "q")
    named = ", ".join(f"{p}={watch[p]['events']}" for p in order)
    suffix = f" (lower bound: {'; '.join(lower_bound)})" if lower_bound else ""
    if not total and not has_rows:
        return "no events in the window; nothing can be said"
    if not has_rows and lower_bound:
        # An incomplete empty result proves nothing: "none reaches GA4" would be a false all-clear.
        return (f"no page_location rows with a query string returned out of {total} events, "
                f"but the result is incomplete ({'; '.join(lower_bound)}): the watched params "
                "may still reach GA4 in the window")
    if not has_rows:
        return (f"0 of {total} events carry a query string in page_location: none of the "
                f"watched params ({', '.join(order)}) reaches GA4 in the window")
    if with_query is None:
        if not total:
            return (f"GA4 returned no total for events with a query string or for all events; "
                    f"the fetched rows hold {rows_events} events (total unknown); watched "
                    f"params {named}{suffix}")
        return (f"GA4 returned no total for events with a query string; the fetched rows "
                f"hold {rows_events} of {total} events; watched params {named}{suffix}")
    if not total:
        return (f"{with_query} events carry a query string in page_location (total events "
                f"unknown); watched params {named}{suffix}")
    return (f"{with_query} of {total} events ({share}%) carry a query string in "
            f"page_location; watched params {named}{suffix}")


def page_locations(args, start: str, end: str, bearer: str) -> int:
    """Which page_location values still carry a query string, folded to shapes (#1237)."""
    url = API.format(pid=args.property)
    ranges = [{"startDate": start, "endDate": end}]
    data = post(url, {
        "dateRanges": ranges,
        "dimensions": [{"name": "pageLocation"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {"filter": {
            "fieldName": "pageLocation",
            "stringFilter": {"matchType": "CONTAINS", "value": "?"}}},
        "metricAggregations": ["TOTAL"],
        "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
        "limit": PAGE_LOCATION_LIMIT,
    }, bearer)
    # No dimensions = the property's event total, the figure query_share_pct is against.
    all_events = post(url, {"dateRanges": ranges, "metrics": [{"name": "eventCount"}]}, bearer)

    raw_rows = data.get("rows") or []
    row_count = data.get("rowCount", len(raw_rows))
    truncated = len(raw_rows) < row_count
    folded: dict[tuple, dict] = {}
    for r in raw_rows:
        key = fold_location(r["dimensionValues"][0]["value"])
        s = folded.setdefault(key, {"path": key[0], "params": list(key[1]),
                                    "events": 0, "locations": 0})
        s["events"] += int(float(r["metricValues"][0]["value"]))
        s["locations"] += 1
    shapes = sorted(folded.values(), key=lambda s: (-s["events"], s["path"], s["params"]))
    rows_events = sum(s["events"] for s in shapes)

    totals = data.get("totals") or []
    if totals:
        with_query = int(float(totals[0]["metricValues"][0]["value"]))
    else:
        # No rows means no event carried a query string; rows without a total are unknown.
        with_query = None if raw_rows else 0
    t_rows = all_events.get("rows") or []
    total_events = int(float(t_rows[0]["metricValues"][0]["value"])) if t_rows else 0
    share = round(with_query / total_events * 100, 1) if with_query is not None and total_events else None
    coverage = (min(round(rows_events / with_query * 100), 100)
                if with_query else None)
    data_loss = bool((data.get("metadata") or {}).get("dataLossFromOtherRow", False))

    lower_bound = []
    if truncated:
        lower_bound.append("truncated")
    if data_loss:
        lower_bound.append("rows hidden in (other)")
    # Only when neither flag already explains the shortfall; rows_events < with_query, not
    # coverage < 100, because coverage rounds 99.6 up to 100.
    if not lower_bound and with_query is not None and rows_events < with_query:
        lower_bound.append(f"fetched rows cover {coverage}% of the events with a query string")

    watch = _watch(shapes)
    parts = ["these are EVENTS, not pageviews: a page_view, a scroll and a click on one URL "
             "count three times"]
    if coverage is not None and rows_events < with_query:
        parts.append(f"fetched rows account for {coverage}% of the {with_query} events "
                     "that carry a query string")
    if truncated:
        parts.append(f"TRUNCATED: {len(raw_rows)} of {row_count} page_location rows returned")
    if data_loss:
        parts.append("GA4 reports dataLossFromOtherRow: some rows are hidden in (other)")
    if len(shapes) > PAGE_LOCATION_ROWS_SHOWN:
        parts.append(f"rows lists the top {PAGE_LOCATION_ROWS_SHOWN} shapes of {len(shapes)}; "
                     "watch and by_param use all of them")

    print(json.dumps({
        "source": "ga4", "property": args.property, "mode": "page-locations",
        "window": [start, end], "dimensions": ["pageLocation"],
        "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
        "events_with_query": with_query, "total_events": total_events,
        "query_share_pct": share, "rows_events": rows_events, "coverage_pct": coverage,
        "row_count": row_count, "truncated": truncated,
        "other_row_data_loss": data_loss, "shape_count": len(shapes),
        "headline": location_headline(total_events, with_query, rows_events, share,
                                      watch, bool(raw_rows), tuple(lower_bound)),
        "watch": watch,
        "watch_note": "events, not pageviews. A zero proves a fix only if the window starts "
                      "after that fix's deploy date, and GA4 can threshold low-volume rows, "
                      "so a zero can understate",
        "by_param": _by_param(shapes),
        "rows": shapes[:PAGE_LOCATION_ROWS_SHOWN],
        "rows_omitted": max(len(shapes) - PAGE_LOCATION_ROWS_SHOWN, 0),
        "coverage_note": "; ".join(parts),
    }, indent=2))
    return 0


def _engagement(mv: list) -> dict:
    """engaged_sessions and engagement_seconds (total userEngagementDuration),
    or nothing if the response carried only the first four metrics."""
    if len(mv) < 6:
        return {}
    return {"engaged_sessions": int(float(mv[4]["value"])),
            "engagement_seconds": int(float(mv[5]["value"]))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--property", default=os.environ.get("GA4_PROPERTY_ID", ""))
    ap.add_argument("--daily", action="store_true",
                    help="one row per DAY (users/sessions) instead of per landing x channel")
    ap.add_argument("--events", action="store_true",
                    help="event counts by name plus the cta_click from/to split "
                         "(mutually exclusive with --daily)")
    ap.add_argument("--anomalies", action="store_true",
                    help="find spike days in the window and break each down by source, "
                         "landing page, browser and engagement")
    ap.add_argument("--trend", action="store_true",
                    help="this window against the same-length window before it: site "
                         "totals and by channel (mutually exclusive with the other reports)")
    ap.add_argument("--journeys", action="store_true",
                    help="landing x event rows for the #1070 funnel events plus tool / "
                         "event_type / mode splits (mutually exclusive with the other reports)")
    ap.add_argument("--cohorts", action="store_true",
                    help="channel x browser x device x country over the window, flagging "
                         "zero-engagement cohorts (mutually exclusive with the other reports)")
    ap.add_argument("--page-locations", dest="page_locations", action="store_true",
                    help="page_location values that still carry a query string, folded to "
                         "path + parameter names, with the watched PII params counted "
                         "(mutually exclusive with the other reports)")
    args = ap.parse_args()
    if args.journeys and (args.daily or args.events or args.anomalies or args.trend
                          or args.page_locations):
        sys.exit("--journeys is a separate report from --daily, --events, --anomalies, "
                 "--trend and --page-locations; run them one at a time")
    if args.events and args.daily:
        sys.exit("--events and --daily are separate reports; run them one at a time")
    if args.trend and (args.daily or args.events or args.anomalies or args.page_locations):
        sys.exit("--trend is a separate report from --daily, --events, --anomalies and "
                 "--page-locations; run them one at a time")
    if args.cohorts and (args.daily or args.events or args.anomalies or args.trend
                         or args.journeys or args.page_locations):
        sys.exit("--cohorts is a separate report from --daily, --events, --anomalies, "
                 "--trend, --journeys and --page-locations; run them one at a time")
    if args.page_locations and (args.daily or args.events or args.anomalies or args.trend
                                or args.journeys or args.cohorts):
        sys.exit("--page-locations is a separate report from --daily, --events, --anomalies, "
                 "--trend, --journeys and --cohorts; run them one at a time")
    if not args.property.isdigit():
        sys.exit("GA4_PROPERTY_ID must be the numeric property id "
                 "(GA4 > Admin > Property Settings), not the G- measurement id")

    start, end = window(args.days)
    bearer = token()

    if args.daily:
        return daily(args, start, end, bearer)
    if args.events:
        return events(args, start, end, bearer)
    if args.anomalies:
        return anomalies(args, start, end, bearer)
    if args.journeys:
        return journeys(args, start, end, bearer)
    if args.trend:
        return trend(args, start, end, bearer)
    if args.cohorts:
        return cohorts(args, start, end, bearer)
    if args.page_locations:
        return page_locations(args, start, end, bearer)

    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": "landingPagePlusQueryString"},
                       {"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": "sessions"}, {"name": "bounceRate"},
                    {"name": "screenPageViewsPerSession"}, {"name": "activeUsers"},
                    # Appended, never reordered: rows below read metrics by index.
                    # The owner's "what are users spending time on" (2026-11-15)
                    # was unanswerable because no export carried engagement time.
                    {"name": "engagedSessions"}, {"name": "userEngagementDuration"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        # Each landing now splits into one row per channel group, so the old 100
        # would cover far fewer pages. Truncation is reported below, not assumed away.
        "limit": LIMIT,
    }
    url = API.format(pid=args.property)
    data = post(url, body, bearer)
    # No dimensions = property-level sessions, the figure coverage is measured against.
    total = post(url, {"dateRanges": body["dateRanges"], "metrics": [{"name": "sessions"}]}, bearer)
    t_rows = total.get("rows") or []
    total_sessions = int(t_rows[0]["metricValues"][0]["value"]) if t_rows else 0

    rows = [
        {"landing": r["dimensionValues"][0]["value"],
         "channel": r["dimensionValues"][1]["value"],
         "sessions": int(r["metricValues"][0]["value"]),
         "bounce_rate": round(float(r["metricValues"][1]["value"]), 4),
         "pages_per_session": round(float(r["metricValues"][2]["value"]), 2),
         "active_users": int(r["metricValues"][3]["value"]),
         **_engagement(r["metricValues"])}
        for r in data.get("rows", [])
    ]
    landing_count = len({r["landing"] for r in rows})
    row_sessions = sum(r["sessions"] for r in rows)
    row_count = data.get("rowCount", len(rows))
    truncated = row_count > len(rows)
    coverage = round(row_sessions / total_sessions * 100) if total_sessions else None
    if coverage is None:
        note = "property total sessions were 0 or unavailable; coverage not computable"
    else:
        note = f"rows account for {coverage}% of the property's {total_sessions} sessions"
    if truncated:
        note += f" — TRUNCATED: {len(rows)} of {row_count} landing x channel rows returned"
    print(json.dumps({"source": "ga4", "property": args.property, "window": [start, end],
                      "dimensions": ["landingPagePlusQueryString", "sessionDefaultChannelGroup"],
                      "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
                      "total_sessions": total_sessions, "rows_sessions": row_sessions,
                      "coverage_pct": coverage, "row_count": row_count,
                      "landing_count": landing_count,
                      "truncated": truncated, "coverage_note": note,
                      "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
