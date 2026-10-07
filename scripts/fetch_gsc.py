#!/usr/bin/env python3
"""Search Console query data -> JSON on stdout.

The 6-20 position band is the quarter's objective (#267: "organic traction is
real and unpromoted"). Those queries are one or two places off page one and need
no new content, which is why they outrank publishing more.

Ranked by impressions x achievable CTR gain, not by impressions alone: a query
at position 11 with 2,000 impressions is worth more than one at position 4 with
5,000, because the second has already won.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gapi import post, token, window  # noqa: E402

API = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
# Rough CTR by position. Used only to RANK opportunities against each other,
# never reported as a prediction — real CTR varies hugely by query intent.
CTR_AT = {1: .27, 2: .15, 3: .11, 4: .08, 5: .06}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    # A DOMAIN property, not the URL-prefix form. shubhagya is verified as
    # sc-domain:shubhagya.com, and passing "https://shubhagya.com/" returns a 403
    # that reads like a permissions failure rather than a wrong identifier.
    ap.add_argument("--site", default=os.environ.get("GSC_SITE_URL", "sc-domain:shubhagya.com"))
    ap.add_argument("--band", action="store_true", help="only the 6-20 position band")
    args = ap.parse_args()

    start, end = window(args.days)
    data = post(
        API.format(site=urllib.parse.quote(args.site, safe="")),
        {"startDate": start, "endDate": end, "dimensions": ["query"],
         "rowLimit": 500, "dataState": "final"},
        token(),
    )

    rows = []
    for r in data.get("rows", []):
        pos, imp = r["position"], r["impressions"]
        row = {"query": r["keys"][0], "impressions": imp, "clicks": r["clicks"],
               "ctr": round(r["ctr"], 4), "position": round(pos, 1)}
        if 6 <= pos <= 20:
            # Gain if it reached position 5 — the conservative target.
            row["band_opportunity"] = round(imp * (CTR_AT[5] - r["ctr"]), 1)
        rows.append(row)

    if args.band:
        rows = [r for r in rows if "band_opportunity" in r]
        rows.sort(key=lambda r: -r["band_opportunity"])
    else:
        rows.sort(key=lambda r: -r["impressions"])

    print(json.dumps({"source": "gsc", "site": args.site, "window": [start, end],
                      "note": "window excludes the last 3 days — GSC data is not final before that",
                      "rows": rows[:100]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
