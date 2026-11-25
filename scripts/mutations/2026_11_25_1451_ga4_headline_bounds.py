"""#1451 -- the `--page-locations` headline is quoted without its coverage_note, so a count
that is only a floor (truncated, rows hidden in (other), rows short of the total) has to say
so in the headline itself, an empty-but-incomplete result must not read as "none reaches GA4",
and a missing total must not print "of 0" or "None%".

Each row re-breaks one of those and names the test (tests/test_ga4_page_locations_export.py)
that must go red. The first guards the encoded-name path #1451 also exercises end to end.
None touches GA4."""

_GA = "scripts/fetch_ga4.py"

MUTATIONS = [
    ("#1451: unquote_plus removed, an encoded watched name (e%6Dail) is no longer counted",
     _GA,
     '        name = unquote_plus(part.split("=", 1)[0])\n',
     '        name = part.split("=", 1)[0]\n',
     "test_watched_names_are_kept_with_a_value_bare_or_decoded"),
    ("#1451: truncated is dropped from the lower-bound reasons, the headline reads as exact",
     _GA,
     '    if truncated:\n        lower_bound.append("truncated")\n',
     '    if False:\n        lower_bound.append("truncated")\n',
     "test_truncation_is_in_the_headline_not_only_in_the_coverage_note"),
    ("#1451: data loss is dropped from the lower-bound reasons, hidden rows read as exact",
     _GA,
     '    if data_loss:\n        lower_bound.append("rows hidden in (other)")\n',
     '    if False:\n        lower_bound.append("rows hidden in (other)")\n',
     "test_data_loss_at_full_coverage_is_a_lower_bound_in_the_headline"),
    ("#1451: the incomplete-empty branch is removed, an unfinished fetch says none reaches GA4",
     _GA,
     "    if not has_rows and lower_bound:\n",
     "    if False and lower_bound:\n",
     "test_an_incomplete_empty_result_is_not_a_none_of_them_all_clear"),
    ("#1451: the unknown-total branch is removed, the headline prints 'of 0' and 'None%'",
     _GA,
     '    if not total:\n        return (f"{with_query} events carry',
     '    if False:\n        return (f"{with_query} events carry',
     "test_an_unknown_total_with_a_known_query_count_does_not_say_of_zero"),
    ("#1451: the both-totals-unknown branch is removed, the headline prints 'of 0'",
     _GA,
     '        if not total:\n            return (f"GA4 returned no total for events with a query string or',
     '        if False:\n            return (f"GA4 returned no total for events with a query string or',
     "test_both_totals_unknown_says_so_instead_of_of_zero"),
    ("#1451: the coverage-only reason is removed, rows short of the total read as exact",
     _GA,
     "    if not lower_bound and with_query is not None and rows_events < with_query:\n",
     "    if False:\n",
     "test_rows_covering_less_than_the_total_is_a_lower_bound_on_coverage_alone"),
]
