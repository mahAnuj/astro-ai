"""#782 -- `fetch_ga4.py --events`, the only reader of `cta_click` (#570).

Each row re-breaks one guard and names the test (tests/test_ga4_events_export.py)
that must go red. They prove the export's failure handling is guarded; none of
them touches GA4, so they say nothing about whether the property has the custom
dimensions registered."""

_GA = "scripts/fetch_ga4.py"
_API = "scripts/_gapi.py"

MUTATIONS = [
    ("#782: every error on the split is swallowed as 'unregistered' (a 403 reads as a setting)",
     _GA,
     "        if e.status != 400:\n            raise\n        unregistered = True",
     "        unregistered = True",
     "test_any_other_error_on_the_split_still_fails_the_run"),
    ("#782: the split loses its EXACT cta_click filter (every event is split)",
     _GA,
     '"stringFilter": {"matchType": "EXACT", "value": CTA_EVENT}}},',
     '"stringFilter": {"matchType": "CONTAINS", "value": CTA_EVENT}}},',
     "test_the_requests_ask_for_event_name_and_the_exact_cta_click_split"),
    ("#782: all-(not set) split rows are printed as data",
     _GA,
     "    split_rows = [] if (unregistered or all_not_set) else split_raw",
     "    split_rows = [] if unregistered else split_raw",
     "test_all_not_set_rows_are_not_emitted_as_data"),
    ("#782: a zero count is reported as unreadable instead of a measurement",
     _GA,
     'parts.append(f"{CTA_EVENT}: 0 events recorded in the window -- a measurement, "\n                     "not an unreadable export")',
     'parts.append(f"{CTA_EVENT}: not available")',
     "test_no_cta_click_row_is_a_zero_measurement_not_an_unreadable_export"),
    ("#782: the 400 note stops naming the unregistered custom dimensions",
     _GA,
     '"registered as custom dimensions (GA4 Admin > Custom definitions), "',
     '"available (GA4 Admin > Custom definitions), "',
     "test_a_400_on_the_split_keeps_the_total_and_names_the_unregistered_dimensions"),
    ("#782: --events and --daily are no longer refused together",
     _GA,
     "    if args.events and args.daily:\n",
     "    if False:\n",
     "test_events_and_daily_together_are_refused"),
    ("#782: truncation of the event list is no longer reported",
     _GA,
     "    truncated = row_count > len(rows)\n    events_total",
     "    truncated = False\n    events_total",
     "test_truncation_is_reported"),
    ("#782: the API error loses its status (a 400 cannot be told from a 403)",
     _API,
     "        self.status = status\n",
     "        self.status = 400\n",
     "test_any_other_error_on_the_split_still_fails_the_run"),
]
