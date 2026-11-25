"""#1364 -- `fetch_ga4.py --cohorts`, the window-wide cohort export.

Each row re-breaks one guard and names the test (tests/test_ga4_cohorts_export.py) that
must go red. They guard the boundary arithmetic, the honesty of the headline and the shape
of the request; none touches GA4."""

_GA = "scripts/fetch_ga4.py"
_FLAG = '    return row["sessions"] >= min_sessions and row["engaged_sessions"] == 0\n'

MUTATIONS = [
    ("#1364: a cohort of exactly 20 sessions is no longer counted (>= becomes >)",
     _GA,
     _FLAG,
     '    return row["sessions"] > min_sessions and row["engaged_sessions"] == 0\n',
     "test_headline_counts_only_cohorts_at_the_boundary_with_zero_engaged"),
    ("#1364: a cohort with one engaged session is flagged as zero engagement",
     _GA,
     _FLAG,
     '    return row["sessions"] >= min_sessions and row["engaged_sessions"] <= 1\n',
     "test_headline_counts_only_cohorts_at_the_boundary_with_zero_engaged"),
    ("#1364: (not set) cohorts are dropped from the rows",
     _GA,
     '        d, m = r["dimensionValues"], r["metricValues"]\n',
     '        d, m = r["dimensionValues"], r["metricValues"]\n'
     '        if d[1]["value"] == "(not set)":\n            continue\n',
     "test_not_set_cohorts_are_kept_as_rows_and_counted"),
    ("#1364: the cohort request gains a dimensionFilter",
     _GA,
     '"limit": COHORT_LIMIT}, bearer)\n    by_ch = post',
     '"limit": COHORT_LIMIT,\n                      "dimensionFilter": {"filter": {"fieldName": "browser", '
     '"stringFilter": {"value": "Chrome"}}}}, bearer)\n    by_ch = post',
     "test_two_requests_with_the_declared_dimensions_metrics_and_window"),
    ("#1364: a zero-session channel reports a share of 0, not null",
     _GA,
     '"zero_engagement_share": round(zero_sessions / n, 4) if n else None,',
     '"zero_engagement_share": round(zero_sessions / n, 4) if n else 0,',
     "test_a_channel_with_no_sessions_has_a_null_share_not_zero"),
    ("#1364: sessions in cohorts under the minimum are no longer accounted for",
     _GA,
     '        small = sum(r["sessions"] for r in mine if r["sessions"] < min_sessions)\n',
     '        small = 0\n',
     "test_every_channel_cohorts_add_up_to_its_sessions"),
    ("#1364: a truncated cohort fetch is no longer reported",
     _GA,
     '    if row_count > len(raw_rows):\n',
     '    if False:\n',
     "test_truncation_is_reported_in_the_coverage_note"),
    ("#1364: channel summaries are computed from the 50 rows shown, not every cohort",
     _GA,
     '    summary = channel_summary(channel_totals, rows)\n',
     '    summary = channel_summary(channel_totals, rows[:COHORT_ROWS_SHOWN])\n',
     "test_rows_are_capped_at_fifty_but_summaries_use_every_cohort"),
    ("#1364: --cohorts is no longer refused beside the other reports",
     _GA,
     '    if args.cohorts and (args.daily or args.events or args.anomalies or args.trend\n',
     '    if False and (args.daily or args.events or args.anomalies or args.trend\n',
     "test_cohorts_with_another_report_is_refused_before_any_request"),
    ("#1364: the headline quotes Organic Search instead of Direct",
     _GA,
     'def headline(summary: list[dict], channel: str = "Direct") -> str:',
     'def headline(summary: list[dict], channel: str = "Organic Search") -> str:',
     "test_headline_counts_only_cohorts_at_the_boundary_with_zero_engaged"),
]
