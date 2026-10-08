#!/usr/bin/env python3
"""GA4 landing-page and funnel data -> JSON on stdout.

Needs the NUMERIC property id (GA4_PROPERTY_ID), not the G-XXXXXXXXXX
measurement id. Mixing those two up is the most common failure here; the
measurement id belongs to the tag on the page, the property id to the API.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gapi import post, token, window  # noqa: E402

LIMIT = 1000
API = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--property", default=os.environ.get("GA4_PROPERTY_ID", ""))
    args = ap.parse_args()
    if not args.property.isdigit():
        sys.exit("GA4_PROPERTY_ID must be the numeric property id "
                 "(GA4 > Admin > Property Settings), not the G- measurement id")

    start, end = window(args.days)
    bearer = token()
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
                      "truncated": truncated, "coverage_note": note,
                      "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
