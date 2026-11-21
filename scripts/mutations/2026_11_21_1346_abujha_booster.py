"""#1346 + #1354: an Abujha date is a booster inside `score_event`, applied after the hard
exclusions, with Sarvartha lift semantics; a day that fails an exclusion stays `avoid` with the
exclusion's own flag and reason plus a disclosure sentence. tests/test_muhurat_abujha_booster.py.
One area file, a literal list (test_mutation_tables.py requires it)."""

_M = "src/astro_ai/muhurat.py"

MUTATIONS = [
    ("#1346: the Abujha lift is dropped (flag and reason prefix stay, the rating never rises)",
     _M,
     "        elif rating in (\"caution\", \"acceptable\", \"good\"):\n            # Lift only if not already excellent",
     "        elif boosters and rating in (\"caution\", \"acceptable\", \"good\"):\n            # Lift only if not already excellent",
     "test_the_abujha_lift_has_sarvartha_semantics_and_never_lowers"),
    ("#1346: the Abujha flag is set before the exclusions (an avoid row claims the custom lifted it)",
     _M,
     "    flags: list[str] = []\n    reasons: list[str] = []\n",
     "    flags: list[str] = [\"abujha_muhurat\"] if abujha_name else []\n    reasons: list[str] = []\n",
     "test_every_abujha_day_event_pair_is_a_booster_after_the_exclusions"),
    ("#1346: the pass prefix is dropped (a lifted row no longer says no book names Abujha)",
     _M,
     "            reasons.insert(0, _ABUJHA_PASS_REASON.format(name=abujha_name))\n",
     "            pass\n",
     "test_the_real_lift_akshaya_tritiya_2028_business_acceptable_to_excellent"),
    ("#1346: the avoid suffix is dropped (an Abujha row that failed an exclusion hides the Abujha name)",
     _M,
     "            reason = reason.rstrip(\" .\") + \". \" + _ABUJHA_AVOID_SUFFIX.format(name=abujha_name)\n",
     "            pass\n",
     "test_the_1346_metric_no_panchak_row_is_excellent_and_2026_11_21_is_avoid"),
    ("#1346: Abujha is given Amrit Siddhi semantics (always excellent, even from caution)",
     _M,
     "        if any(b.startswith(\"Amrit Siddhi\") for b in boosters):\n            rating = \"excellent\"\n            reasons.insert(0, booster_names)\n",
     "        if abujha_name or any(b.startswith(\"Amrit Siddhi\") for b in boosters):\n            rating = \"excellent\"\n            reasons.insert(0, booster_names)\n",
     "test_abujha_is_not_amrit_siddhi_it_does_not_always_lift_to_excellent"),
    ("#1346: find_candidates does not pass abujha_name into score_event (the booster never runs)",
     _M,
     "            boosters=boosters, moon_pada=moon_pada,\n            abujha_name=abujha_name,\n        )\n",
     "            boosters=boosters, moon_pada=moon_pada,\n        )\n",
     "test_every_abujha_day_event_pair_is_a_booster_after_the_exclusions"),
]
