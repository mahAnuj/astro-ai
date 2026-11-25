"""#1237 -- `fetch_ga4.py --page-locations`, the export that checks #1066 and #1093 did stop
the leaks into GA4's page_location.

Each row re-breaks one guard and names the test (tests/test_ga4_page_locations_export.py)
that must go red. The first three re-open the leak the export exists to find; the rest guard
the denominator, the truncation statement, the "zero is a finding" headline, the request
shape and the every-shape counting. None touches GA4."""

_GA = "scripts/fetch_ga4.py"
_NAMES = "        names.add(name if _SAFE_NAME.fullmatch(name) else REDACTED_NAME)\n"
_COVERAGE = ("    coverage = (min(round(rows_events / with_query * 100), 100)\n"
             "                if with_query else None)\n")

MUTATIONS = [
    ("#1237: redaction bypassed, the raw name=value text is emitted so values leak",
     _GA,
     _NAMES,
     "        names.add(part)\n",
     "test_no_canary_value_or_address_reaches_stdout"),
    ("#1237: a path segment holding an @ is no longer redacted",
     _GA,
     '    if "@" in seg or "%40" in seg.lower() or len(seg) > 40:\n',
     "    if len(seg) > 40:\n",
     "test_a_path_segment_with_an_at_sign_is_redacted"),
    ("#1237: the parameter-name safety regex is removed (a bare address passes as a name)",
     _GA,
     _NAMES,
     "        names.add(name)\n",
     "test_a_bare_address_as_a_parameter_name_is_redacted"),
    ("#1237: PII_PARAMS loses email, so the Python list drifts from analytics.js",
     _GA,
     'PII_PARAMS = ("q", "city", "email", "token")\n',
     'PII_PARAMS = ("q", "city", "token")\n',
     "test_pii_params_equal_the_list_in_analytics_js"),
    ("#1237: the CONTAINS '?' filter is emptied, so every location is fetched",
     _GA,
     '"stringFilter": {"matchType": "CONTAINS", "value": "?"}}},\n        "metricAggregations"',
     '"stringFilter": {"matchType": "CONTAINS", "value": ""}}},\n        "metricAggregations"',
     "test_two_requests_with_the_declared_dimension_metric_filter_and_window"),
    ("#1237: coverage_pct is divided by ALL events, so it reads ~0% and looks like a failed fetch",
     _GA,
     _COVERAGE,
     "    coverage = (min(round(rows_events / (total_events or 1) * 100), 100)\n"
     "                if with_query else None)\n",
     "test_coverage_is_100_unless_truncated_and_is_not_against_all_events"),
    ("#1237: the TRUNCATED statement is never written",
     _GA,
     '    if truncated:\n        parts.append(f"TRUNCATED: {len(raw_rows)} of {row_count} page_location',
     '    if False:\n        parts.append(f"TRUNCATED: {len(raw_rows)} of {row_count} page_location',
     "test_truncation_lowers_coverage_and_says_so"),
    ("#1237: zero rows with events is reported as 'no data' instead of a measured zero",
     _GA,
     '    if not has_rows:\n        return (f"0 of {total} events carry',
     '    if not has_rows:\n        return "no data"\n    if False:\n        return (f"0 of {total} events carry',
     "test_zero_rows_with_events_says_none_of_the_watched_params_reaches_ga4"),
    ("#1237: --page-locations is no longer refused beside --daily, --events or --anomalies",
     _GA,
     "    if args.page_locations and (args.daily or args.events or args.anomalies or args.trend\n",
     "    if False and (args.daily or args.events or args.anomalies or args.trend\n",
     "test_page_locations_with_another_report_is_refused_before_any_request"),
    ("#1237: watch counts only the 50 rows shown, not every shape",
     _GA,
     "    watch = _watch(shapes)\n",
     "    watch = _watch(shapes[:PAGE_LOCATION_ROWS_SHOWN])\n",
     "test_rows_are_capped_at_fifty_but_watch_and_by_param_use_every_shape"),
    ("#1237: by_param counts only the 50 rows shown, not every shape",
     _GA,
     '        "by_param": _by_param(shapes),\n',
     '        "by_param": _by_param(shapes[:PAGE_LOCATION_ROWS_SHOWN]),\n',
     "test_rows_are_capped_at_fifty_but_watch_and_by_param_use_every_shape"),
]
