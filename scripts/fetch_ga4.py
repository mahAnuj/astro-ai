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
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gapi import ApiError, post, token, window  # noqa: E402

LIMIT = 1000
API = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"
CTA_EVENT = "cta_click"
NOT_SET = "(not set)"
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
    """One row per day: active users, sessions, new users.

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

    rows, d = [], datetime.strptime(start, "%Y-%m-%d").date()
    last = datetime.strptime(end, "%Y-%m-%d").date()
    while d <= last:
        iso = d.isoformat()
        rows.append(got.get(iso, {"date": iso, "active_users": 0,
                                  "sessions": 0, "new_users": 0, "no_data": True}))
        d += timedelta(days=1)

    print(json.dumps({
        "source": "ga4", "property": args.property, "window": [start, end],
        "dimensions": ["date"],
        "note": "window excludes the last 3 days - GA4 standard reports lag 24-48h. "
                "A day absent from the API is emitted as 0 with no_data=true, so a "
                "gap in collection is visible rather than drawn as a flat line.",
        "days": len(rows),
        "days_with_traffic": sum(1 for r in rows if not r.get("no_data")),
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
    found = []
    for day in spike_days(rows):
        rng = [{"startDate": day["date"], "endDate": day["date"]}]
        src_dims = ["sessionSourceMedium", "landingPagePlusQueryString"]
        tech_dims = ["browser", "deviceCategory", "country"]
        order = [{"metric": {"metricName": "sessions"}, "desc": True}]
        a = post(url, {"dateRanges": rng, "dimensions": [{"name": d} for d in src_dims],
                       "metrics": metrics, "orderBys": order, "limit": 15}, bearer)
        b = post(url, {"dateRanges": rng, "dimensions": [{"name": d} for d in tech_dims],
                       "metrics": metrics, "orderBys": order, "limit": 10}, bearer)
        by_source = _breakdown(a.get("rows", []), src_dims)
        by_tech = _breakdown(b.get("rows", []), tech_dims)
        found.append({**day, "explanation": explain(by_source, by_tech),
                      "by_source": by_source, "by_tech": by_tech})
    print(json.dumps({"source": "ga4", "property": args.property, "window": [start, end],
                      "rule": "active users >= max(2 x median, median + 10, 15)",
                      "days_checked": len(rows), "spikes": found}, indent=2))
    return 0


def events(args, start: str, end: str, bearer: str) -> int:
    """Event counts by name, plus the `cta_click` from/to split (#782).

    Two requests, not one (see the module docstring). A 400 on the split is the
    Data API refusing `customEvent:from_path` because it is not a registered custom
    dimension -- an owner-side GA4 setting the loop cannot make -- and is reported
    in `coverage_note` while the total still stands. Any other error propagates.
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

    print(json.dumps({
        "source": "ga4", "property": args.property, "window": [start, end],
        "dimensions": ["eventName"],
        "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
        "row_count": row_count, "truncated": truncated,
        "rows": rows, "events_total": events_total,
        "coverage_note": "; ".join(parts),
        CTA_EVENT: {"count": cta_count, "split_available": split_available,
                    "rows": split_rows},
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
    args = ap.parse_args()
    if args.journeys and (args.daily or args.events or args.anomalies or args.trend):
        sys.exit("--journeys is a separate report from --daily, --events, --anomalies and "
                 "--trend; run them one at a time")
    if args.events and args.daily:
        sys.exit("--events and --daily are separate reports; run them one at a time")
    if args.trend and (args.daily or args.events or args.anomalies):
        sys.exit("--trend is a separate report from --daily, --events and --anomalies; "
                 "run them one at a time")
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
