"""#1469 -- `fetch_ga4.py --events` `journey_events`: a declared event GA4 returned no row
for reads as a measured zero with its since-date, and as unknown (null) where zero is
unprovable (empty property, truncated list).

Each row re-breaks one guard and names the test (tests/test_ga4_events_export.py) that
must go red. None touches GA4: they prove the arithmetic over the rows already fetched."""

_GA = "scripts/fetch_ga4.py"

MUTATIONS = [
    ("#1469: an empty property reports every declared event as a measured zero",
     _GA,
     '        elif not rows:\n'
     '            entry = {"count": None, "reason": "the property recorded no events in the "\n'
     '                     "window, so zero is not a measurement"}\n'
     '        elif truncated:\n',
     '        elif truncated:\n',
     "test_journey_events_on_an_empty_property_are_unknown_not_zero"),
    ("#1469: a truncated event list reports a name it cut off as a measured zero",
     _GA,
     '        elif truncated:\n'
     '            entry = {"count": None, "reason": "the event list was truncated at the row "\n'
     '                     "limit, so a name may be cut off"}\n'
     '        else:\n',
     '        else:\n',
     "test_journey_events_when_truncated_a_missing_name_is_unknown"),
    ("#1469: only events GA4 returned get an entry (the declared-but-absent ones vanish again)",
     _GA,
     "    for name in JOURNEY_SINCE:\n        if name in by_name:",
     "    for name in [n for n in JOURNEY_SINCE if n in by_name]:\n        if name in by_name:",
     "test_journey_events_declared_but_not_returned_reads_zero_with_since"),
    ("#1469: partial_history is hardcoded false instead of read from the since-date",
     _GA,
     "        journey_events[name] = {**entry, **_since_note(start, name)}",
     '        journey_events[name] = {**entry, "since": JOURNEY_SINCE[name],\n'
     '                                "partial_history": False}',
     "test_journey_events_declared_but_not_returned_reads_zero_with_since"),
    ("#1469: an event GA4 did return reports 0 instead of its count",
     _GA,
     '            entry = {"count": by_name[name]}',
     '            entry = {"count": 0}',
     "test_journey_events_returned_names_carry_their_count"),
    ("#1469: journey_events is folded into the cta_click key (its shape changes)",
     _GA,
     '                    "rows": split_rows},\n        "journey_events": journey_events,\n',
     '                    "rows": split_rows, "journey_events": journey_events},\n',
     "test_journey_events_add_no_request_and_keep_the_cta_click_shape"),
]
