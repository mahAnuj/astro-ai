"""#490: scripts/fetch_gsc.py --page-daily is a page x date series, in order, and
a watchlist entry that matched nothing is reported rather than dropped."""

MUTATIONS = [
    ("#490: --page-daily asks GSC for the page dimension only (no per-day series)",
     "scripts/fetch_gsc.py",
     '"dimensions": ["page", "date"],',
     '"dimensions": ["page"],',
     "test_main_requests_page_and_date_dimensions"),
    ("#490: a page's days come back in API order, not chronological order",
     "scripts/fetch_gsc.py",
     '        days.sort(key=lambda d: d["date"])\n',
     '        pass\n',
     "test_rows_group_per_page_in_chronological_order"),
    ("#490: a watchlist entry that matched no page is silently dropped",
     "scripts/fetch_gsc.py",
     '"unmatched_pages": [w for w in (pages or []) if w not in matched],',
     '"unmatched_pages": [],',
     "test_watchlist_keeps_only_matching_pages_and_reports_the_rest"),
]
