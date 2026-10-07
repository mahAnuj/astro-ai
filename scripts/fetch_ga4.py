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
        "dimensions": [{"name": "landingPagePlusQueryString"}],
        "metrics": [{"name": "sessions"}, {"name": "bounceRate"},
                    {"name": "screenPageViewsPerSession"}, {"name": "activeUsers"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": 100,
    }
    data = post(API.format(pid=args.property), body, bearer)

    rows = [
        {"landing": r["dimensionValues"][0]["value"],
         "sessions": int(r["metricValues"][0]["value"]),
         "bounce_rate": round(float(r["metricValues"][1]["value"]), 4),
         "pages_per_session": round(float(r["metricValues"][2]["value"]), 2),
         "active_users": int(r["metricValues"][3]["value"])}
        for r in data.get("rows", [])
    ]
    print(json.dumps({"source": "ga4", "property": args.property, "window": [start, end],
                      "note": "window excludes the last 3 days — GA4 standard reports lag 24-48h",
                      "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
