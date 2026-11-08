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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--property", default=os.environ.get("GA4_PROPERTY_ID", ""))
    ap.add_argument("--daily", action="store_true",
                    help="one row per DAY (users/sessions) instead of per landing x channel")
    ap.add_argument("--events", action="store_true",
                    help="event counts by name plus the cta_click from/to split "
                         "(mutually exclusive with --daily)")
    args = ap.parse_args()
    if args.events and args.daily:
        sys.exit("--events and --daily are separate reports; run them one at a time")
    if not args.property.isdigit():
        sys.exit("GA4_PROPERTY_ID must be the numeric property id "
                 "(GA4 > Admin > Property Settings), not the G- measurement id")

    start, end = window(args.days)
    bearer = token()

    if args.daily:
        return daily(args, start, end, bearer)
    if args.events:
        return events(args, start, end, bearer)

    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": "landingPagePlusQueryString"},
                       {"name": "sessionDefaultChannelGroup"}],
        "metrics": [{"name": "sessions"}, {"name": "bounceRate"},
                    {"name": "screenPageViewsPerSession"}, {"name": "activeUsers"}],
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
         "active_users": int(r["metricValues"][3]["value"])}
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
