#!/usr/bin/env python3
"""Search Console page (default) or query data -> JSON on stdout.

Default dimension is `page`, not `query` (#272). Google withholds any query
searched by too few people, so the query dimension measured ~9% of the site's
impressions in September 2026 (769 of 8,097); the page dimension measured ~101%.
`--by query` stays for when the wording itself matters, but it is a PARTIAL view
and the export says so. Every export carries `coverage_pct` so a reader can see
how much of the property the rows represent — a conclusion drawn from 7% of the
data looks identical to one drawn from all of it unless the file says otherwise.

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
ROW_LIMIT = 25000
CTR_AT = {1: .27, 2: .15, 3: .11, 4: .08, 5: .06}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    # A DOMAIN property, not the URL-prefix form. shubhagya is verified as
    # sc-domain:shubhagya.com, and passing "https://shubhagya.com/" returns a 403
    # that reads like a permissions failure rather than a wrong identifier.
    ap.add_argument("--site", default=os.environ.get("GSC_SITE_URL", "sc-domain:shubhagya.com"))
    ap.add_argument("--band", action="store_true", help="only the 6-20 position band")
    ap.add_argument("--by", choices=("page", "query"), default="page",
                    help="dimension; query is a PARTIAL view (anonymised queries are withheld)")
    args = ap.parse_args()

    start, end = window(args.days)
    url = API.format(site=urllib.parse.quote(args.site, safe=""))
    bearer = token()
    # 25000 is the API maximum per request. The site has ~142 pages, so no
    # startRow pagination; if rows ever reach the limit we say so below.
    data = post(url, {"startDate": start, "endDate": end, "dimensions": [args.by],
                      "rowLimit": ROW_LIMIT, "dataState": "final"}, bearer)
    # No dimensions = the property total, which is what coverage is measured against.
    total = post(url, {"startDate": start, "endDate": end, "dataState": "final"}, bearer)
    t = (total.get("rows") or [{}])[0]
    total_imp, total_clk = t.get("impressions", 0), t.get("clicks", 0)

    raw = data.get("rows", [])
    row_imp = sum(r["impressions"] for r in raw)
    # Can exceed 100, reported as measured and never clamped. What was measured
    # (2026-09-08..10-05): page rows summed to 8,636 impressions against a property
    # total of 8,579 (101%); the page response is labelled byPage and the property
    # total byProperty, so the two use different aggregation types. The exact cause
    # of the 57 surplus is UNCONFIRMED. (The query dimension undershoots, not
    # overshoots, so it is not the same effect.)
    coverage = round(row_imp / total_imp * 100) if total_imp else None

    rows = []
    for r in raw:
        pos, imp = r["position"], r["impressions"]
        row = {args.by: r["keys"][0], "impressions": imp, "clicks": r["clicks"],
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

    # Honest about what is printed: coverage_pct / rows_impressions describe the
    # whole fetch, but --band prints a filtered subset (100 rows summing to 90%
    # against a 101% fetch), so the emitted figures are computed from `rows` itself.
    emitted_imp = sum(r["impressions"] for r in rows)
    emitted_cov = round(emitted_imp / total_imp * 100) if total_imp else None

    if coverage is None:
        cov_note = "property total impressions were 0 or unavailable; coverage not computable"
    else:
        cov_note = f"rows account for {coverage}% of the property's {total_imp} impressions"
    if args.band:
        cov_note += (f" — coverage_pct/rows_impressions describe the whole fetch; --band "
                     f"printed {len(rows)} rows at position 6-20 covering {emitted_cov}% "
                     f"({emitted_imp} impressions): see emitted_coverage_pct/emitted_impressions")
    if args.by == "query":
        cov_note += (" — PARTIAL VIEW: Google withholds anonymised (low-volume) queries, "
                     "so the query dimension cannot reach the total; use --by page for totals")
    truncated = len(raw) >= ROW_LIMIT
    if truncated:
        cov_note += f" — TRUNCATED at rowLimit {ROW_LIMIT}"

    print(json.dumps({"source": "gsc", "site": args.site, "window": [start, end],
                      "dimension": args.by,
                      "note": "window excludes the last 3 days — GSC data is not final before that",
                      "total_impressions": total_imp, "total_clicks": total_clk,
                      "rows_impressions": row_imp, "coverage_pct": coverage,
                      "emitted_rows": len(rows), "emitted_impressions": emitted_imp,
                      "emitted_coverage_pct": emitted_cov, "truncated": truncated,
                      "coverage_note": cov_note,
                      "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
