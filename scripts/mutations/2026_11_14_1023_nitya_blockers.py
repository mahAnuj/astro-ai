"""#1023: five nitya yogas block a muhurat (Raman, Muhurtha lines 1343-1346).
tests/test_muhurat_nitya_blockers.py."""

_FIVE = '_BLOCKING_NITYA_YOGAS = {"Atiganda", "Shula", "Ganda", "Vyatipata", "Vaidhriti"}'

MUTATIONS = [
    ("#1023: the blocking set shrinks back to Vyatipata and Vaidhriti",
     "src/astro_ai/muhurat.py", _FIVE,
     '_BLOCKING_NITYA_YOGAS = {"Vyatipata", "Vaidhriti"}',
     "test_the_issue_repro_atiganda_and_ganda_days_are_avoid"),
    ("#1023: the shrunken set also lets blocked days through the five-event sweep",
     "src/astro_ai/muhurat.py", _FIVE,
     '_BLOCKING_NITYA_YOGAS = {"Vyatipata", "Vaidhriti"}',
     "test_no_day_under_a_blocking_yoga_is_acceptable_or_better_for_any_event"),
    ("#1023: Shula is spelled Sula (Raman's spelling, not chart.py's) so it never matches",
     "src/astro_ai/muhurat.py", _FIVE,
     '_BLOCKING_NITYA_YOGAS = {"Atiganda", "Sula", "Ganda", "Vyatipata", "Vaidhriti"}',
     "test_the_blocking_set_is_exactly_ramans_five_by_position"),
    ("#1023: an ordinary yoga (Siddhi) is added to the blockers",
     "src/astro_ai/muhurat.py", _FIVE,
     '_BLOCKING_NITYA_YOGAS = {"Atiganda", "Shula", "Ganda", "Vyatipata", "Vaidhriti", "Siddhi"}',
     "test_ordinary_yogas_do_not_block"),
    ("#1023: a booster skips the nitya-yoga block",
     "src/astro_ai/muhurat.py", "    if nitya_blocks:\n",
     "    if nitya_blocks and not boosters:\n",
     "test_a_booster_cannot_lift_a_blocked_yoga_day"),
    ("#1023: the finder page goes back to naming only two excluded yogas",
     "src/astro_ai/templates/muhurat_finder.html",
     "Days under Atiganda, Shula, Ganda, Vyatipata or Vaidhriti are excluded from this list.",
     "Vaidhriti/Vyatipata days are excluded from this list.",
     "test_pages_no_longer_say_only_two_yogas_are_excluded"),
    ("#1023: /panchang goes back to 'the two most inauspicious yogas'",
     "src/astro_ai/templates/panchang.html",
     "Atiganda, Shula, Ganda, Vyatipata and Vaidhriti are the five yogas Raman&rsquo;s <em>Muhurtha</em> says harm events started under them, so the Muhurat Finder excludes those days.",
     "Vaidhriti and Vyatipata are the two most inauspicious yogas and are traditionally avoided for muhurta.",
     "test_pages_no_longer_say_only_two_yogas_are_excluded"),
]
