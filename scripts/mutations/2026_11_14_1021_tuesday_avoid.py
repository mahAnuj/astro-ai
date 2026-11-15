"""#1021: Tuesday is a hard exclusion for every event (Raman, Muhurtha), Saturday stays a
one-point penalty, Sunday is not a 'good weekday' for Vivah. tests/test_muhurat_tuesday.py."""

MUTATIONS = [
    ("#1021: the hard-avoid weekday set is emptied (Tuesday falls back to -1)",
     "src/astro_ai/muhurat.py",
     '_HARD_AVOID_WEEKDAYS = frozenset({"Tuesday"})',
     "_HARD_AVOID_WEEKDAYS = frozenset()",
     "test_the_issue_repro_tuesdays_are_avoid_with_the_flag"),
    ("#1021: the emptied set also lets Tuesday through the five-event sweep",
     "src/astro_ai/muhurat.py",
     '_HARD_AVOID_WEEKDAYS = frozenset({"Tuesday"})',
     "_HARD_AVOID_WEEKDAYS = frozenset()",
     "test_no_tuesday_is_acceptable_or_better_for_any_event"),
    ("#1021: Saturday is made a hard exclusion too (it is contested, one point only)",
     "src/astro_ai/muhurat.py",
     '_HARD_AVOID_WEEKDAYS = frozenset({"Tuesday"})',
     '_HARD_AVOID_WEEKDAYS = frozenset({"Tuesday", "Saturday"})',
     "test_saturday_is_still_only_a_one_point_penalty"),
    ("#1021: Sunday is back in Vivah's good_days",
     "src/astro_ai/muhurat.py",
     '        "good_days":  {"Monday", "Wednesday", "Thursday", "Friday"},\n'
     '        "avoid_days": {"Tuesday", "Saturday"},\n'
     '        "check_panchak": True,\n'
     '        "check_chaturmas": True,\n'
     '        "check_kharmas":   True,          # Dhanurmas',
     '        "good_days":  {"Monday", "Wednesday", "Thursday", "Friday", "Sunday"},\n'
     '        "avoid_days": {"Tuesday", "Saturday"},\n'
     '        "check_panchak": True,\n'
     '        "check_chaturmas": True,\n'
     '        "check_kharmas":   True,          # Dhanurmas',
     "test_sunday_is_not_a_good_weekday_for_vivah"),
    ("#1021: the Tuesday exclusion is skipped whenever a booster is present",
     "src/astro_ai/muhurat.py",
     "    if weekday_name in _HARD_AVOID_WEEKDAYS:\n",
     "    if weekday_name in _HARD_AVOID_WEEKDAYS and not boosters:\n",
     "test_a_booster_cannot_lift_a_tuesday"),
    ("#1021: the Tuesday exclusion is removed from score_event entirely",
     "src/astro_ai/muhurat.py",
     "    if weekday_name in _HARD_AVOID_WEEKDAYS:\n",
     "    if False and weekday_name in _HARD_AVOID_WEEKDAYS:\n",
     "test_a_booster_cannot_lift_a_tuesday"),
    ("#1021: Namkaran stops disclosing Raman's 10th/12th/16th day exception",
     "src/astro_ai/muhurat.py",
     '        if event_type == "namkaran":\n            reason += _NAMKARAN_TUESDAY_EXCEPTION\n',
     '        if False:\n            reason += _NAMKARAN_TUESDAY_EXCEPTION\n',
     "test_namkaran_discloses_ramans_child_day_exception"),
    ("#1021: every event carries the Namkaran exception",
     "src/astro_ai/muhurat.py",
     '        if event_type == "namkaran":\n            reason += _NAMKARAN_TUESDAY_EXCEPTION\n',
     '        if True:\n            reason += _NAMKARAN_TUESDAY_EXCEPTION\n',
     "test_other_events_do_not_carry_the_namkaran_exception"),
    ("#1021: the reason stops saying Amrit Siddhi does not override the exclusion",
     "src/astro_ai/muhurat.py",
     "Amrit Siddhi's Tuesday + Ashwini pairing does \"\n    \"not override this in this finder;",
     "Amrit Siddhi's Tuesday + Ashwini pairing may \"\n    \"override this in this finder;",
     "test_a_booster_cannot_lift_a_tuesday"),
]
