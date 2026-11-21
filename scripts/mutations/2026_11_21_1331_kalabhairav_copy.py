"""#1331: Kalabhairav Jayanti stops asserting an unsourced Ashtami window.

Each row re-breaks one property and names the test that must go red."""

MUTATIONS = [
    ("#1331: the significance gets its 'dusk to midnight' tithi claim back (2026-12-01 Ashtami ends 23:13)",
     "src/astro_ai/festival_registry.py",
     "The date given here is the day \"\n            \"on which Ashtami is running in the evening, after sunset, as the Drik Panchang \"\n            \"for New Delhi prints it. That is not always the day Ashtami is current at \"\n            \"sunrise, and in some years Ashtami ends before midnight, so a locality or \"\n            \"temple that keeps the midnight tithi may observe a day either side.\"",
     "Because Bhairava is a deity of \"\n            \"the night, the tithi that counts is the one running from dusk to midnight, \"\n            \"not the one at sunrise.\"",
     "test_the_copy_names_no_dusk_to_midnight_or_nishita_window"),
    ("#1331: the registry window is 'pradosh to nishita' again",
     "src/astro_ai/festival_registry.py",
     "observance_window=\"evening, Ashtami running after sunset\"",
     "observance_window=\"pradosh to nishita, Ashtami prevailing\"",
     "test_the_copy_names_no_dusk_to_midnight_or_nishita_window"),
    ("#1331: a reworded midnight window ('until midnight') slips past the named phrases",
     "src/astro_ai/festival_registry.py",
     "observance_window=\"evening, Ashtami running after sunset\"",
     "observance_window=\"dusk until midnight, Ashtami prevailing\"",
     "test_no_window_shaped_phrase_ties_the_date_to_midnight_or_nishita"),
    ("#1331: the expected table keeps the old window, so registry and table diverge",
     "tests/festival_dates_expected.json",
     "\"observance_window\": \"evening, Ashtami running after sunset\"",
     "\"observance_window\": \"pradosh to nishita, Ashtami prevailing\"",
     "test_each_observance_window_matches_the_expected_table"),
]
