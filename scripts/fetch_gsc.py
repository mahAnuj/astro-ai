#!/usr/bin/env python3
"""Search Console page (default) or query data -> JSON on stdout.

Default dimension is `page`, not `query` (#272). Google withholds any query
searched by too few people, so the query dimension measured ~9% of the site's
impressions (747 of 8,579 for 2026-09-08..10-05; 769 of 8,097 in September); the
page dimension measured ~101%.
`--by query` stays for when the wording itself matters, but it is a PARTIAL view
and the export says so. Every export carries `coverage_pct` so a reader can see
how much of the property the rows represent — a conclusion drawn from 7% of the
data (the old export's share) looks identical to one drawn from all of it unless the file says otherwise.

The 6-20 position band is the quarter's objective (#267: "organic traction is
real and unpromoted"). Those queries are one or two places off page one and need
no new content, which is why they outrank publishing more.

Ranked by impressions x achievable CTR gain, not by impressions alone: a query
at position 11 with 2,000 impressions is worth more than one at position 4 with
5,000, because the second has already won.

TWO MODES BEYOND THE SNAPSHOT
-----------------------------
`--by date` returns one row per day. `--trend` returns the same dimension
measured over TWO adjacent windows with the delta between them.

Both exist because "trending" was believed to be impossible here: nothing in
this repo retains history, each run overwrites its JSON, so a trend looked like
it needed a history store first. It does not. Search Console keeps 16 months
and will return a `date` dimension or any window you ask for -- GSC IS the
history store, and the gap was that neither was ever requested.

Measured 2026-10-14, 28 days against the 28 before: /learn/rahu-mahadasha-ketu-
antardasha/ went 146 -> 1,589 impressions and /festivals went 1,598 -> 228.
Neither movement was visible anywhere in this repo before.

A `--trend --by query` carries the same ~9% coverage caveat as any query fetch,
and the emitted document repeats it, because a ranked list of risers looks
equally authoritative whether it saw all the data or a twelfth of it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gapi import post, token, window  # noqa: E402

API = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
# Rough CTR by position. Used only to RANK opportunities against each other,
# never reported as a prediction — real CTR varies hugely by query intent.
ROW_LIMIT = 25000
CTR_AT = {1: .27, 2: .15, 3: .11, 4: .08, 5: .06}


def fetch_dim(url: str, bearer: str, dim: str, start: str, end: str) -> dict:
    """{key -> row} for one dimension over one window. One request."""
    data = post(url, {"startDate": start, "endDate": end, "dimensions": [dim],
                      "rowLimit": ROW_LIMIT, "dataState": "final"}, bearer)
    return {r["keys"][0]: r for r in data.get("rows", [])}


def property_impressions(url: str, bearer: str, start: str, end: str) -> int:
    """The window's total, with no dimension. What coverage is measured against."""
    total = post(url, {"startDate": start, "endDate": end, "dataState": "final"}, bearer)
    return (total.get("rows") or [{}])[0].get("impressions", 0)


def trend(args, start: str, end: str, url: str, bearer: str) -> int:
    """This window against the one immediately before it, same dimension.

    The previous window is the SAME LENGTH and ends the day before this one
    starts, so the two are comparable without weighting. A 28-day window
    compared against 14 days would make every page look like it was collapsing.

    A key present now and absent before is a row with `prev=0` and
    `is_new=True`, not a row omitted: a page that went from nothing to 800
    impressions is the single most interesting thing this report can find, and
    an inner join would drop it.

    Rows are ordered by the absolute size of the movement, so the biggest fall
    is as visible as the biggest rise. A report sorted by `delta` descending
    buries every regression at the bottom, which is where /festivals losing
    1,370 impressions had been sitting unseen.
    """
    span = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days
    prev_end = (datetime.strptime(start, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_start = (datetime.strptime(prev_end, "%Y-%m-%d") - timedelta(days=span)).strftime("%Y-%m-%d")

    cur = fetch_dim(url, bearer, args.by, start, end)
    pre = fetch_dim(url, bearer, args.by, prev_start, prev_end)

    rows = []
    for key in set(cur) | set(pre):
        c, p = cur.get(key), pre.get(key)
        c_imp = c["impressions"] if c else 0
        p_imp = p["impressions"] if p else 0
        rows.append({
            args.by: key,
            "impressions": c_imp, "impressions_prev": p_imp,
            "delta": c_imp - p_imp,
            # None, not 0 and not infinity: a page with no previous impressions
            # has no percentage change, and 100% would be a different claim.
            "delta_pct": round((c_imp - p_imp) / p_imp * 100, 1) if p_imp else None,
            "clicks": c["clicks"] if c else 0,
            "clicks_prev": p["clicks"] if p else 0,
            "position": round(c["position"], 1) if c else None,
            "position_prev": round(p["position"], 1) if p else None,
            "is_new": p is None,
            "is_gone": c is None,
        })
    rows.sort(key=lambda r: -abs(r["delta"]))

    cur_total = property_impressions(url, bearer, start, end)
    cov = round(sum(r["impressions"] for r in rows) / cur_total * 100) if cur_total else None
    note = (f"rows account for {cov}% of the property's {cur_total} impressions "
            f"in the current window") if cov is not None else \
           "property total impressions were 0 or unavailable; coverage not computable"
    if args.by == "query":
        note += (" — the query dimension is a PARTIAL view: Google withholds queries "
                 "searched by too few people, so risers and fallers below describe only "
                 "the measured share, not the site")

    print(json.dumps({
        "source": "gsc", "site": args.site, "mode": "trend", "dimension": args.by,
        "window": [start, end], "window_prev": [prev_start, prev_end],
        "total_impressions": cur_total, "coverage_pct": cov, "coverage_note": note,
        "keys_now": len(cur), "keys_prev": len(pre),
        "rows": rows,
    }, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    # A DOMAIN property, not the URL-prefix form. shubhagya is verified as
    # sc-domain:shubhagya.com, and passing "https://shubhagya.com/" returns a 403
    # that reads like a permissions failure rather than a wrong identifier.
    ap.add_argument("--site", default=os.environ.get("GSC_SITE_URL", "sc-domain:shubhagya.com"))
    ap.add_argument("--band", action="store_true", help="only the 6-20 position band")
    ap.add_argument("--by", choices=("page", "query", "date"), default="page",
                    help="dimension; query is a PARTIAL view (anonymised queries are withheld)")
    ap.add_argument("--trend", action="store_true",
                    help="compare this window with the one before it and emit deltas")
    args = ap.parse_args()
    if args.trend and args.by == "date":
        sys.exit("--trend compares two windows on one dimension; "
                 "--by date is already a series, so the two are redundant")

    start, end = window(args.days)
    url = API.format(site=urllib.parse.quote(args.site, safe=""))
    bearer = token()

    if args.trend:
        return trend(args, start, end, url, bearer)
    # 25000 is the API maximum per request. The site has ~133 pages with impressions, so no
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
        # The band is an opportunity on a page or a query. A DAY has an average
        # position too, but "move 2026-10-09 into the top 5" is not a task, so
        # the field is omitted rather than computed into nonsense.
        if args.by != "date" and 6 <= pos <= 20:
            # Gain if it reached position 5 — the conservative target.
            row["band_opportunity"] = round(imp * (CTR_AT[5] - r["ctr"]), 1)
        rows.append(row)

    if args.band and args.by == "date":
        sys.exit("--band selects the 6-20 position band on pages or queries; "
                 "a date has no band")
    if args.band:
        rows = [r for r in rows if "band_opportunity" in r]
        rows.sort(key=lambda r: -r["band_opportunity"])
    elif args.by == "date":
        # Chronological, because this one is a series and a series read out of
        # order is not a series.
        rows.sort(key=lambda r: r["date"])
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
    if args.band and emitted_cov is not None:
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
