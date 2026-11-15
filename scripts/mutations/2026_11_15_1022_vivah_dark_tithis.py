"""#1022: Vivah excludes the waning-half 11th-13th (Raman, Muhurtha, marriage chapter) and gives
the bright-half 12th no credit (Rao lists it, Raman rejects it). tests/test_muhurat_vivah_dark_tithis.py."""

MUTATIONS = [
    ("#1022: the Krishna-paksha exclusion block never fires",
     "src/astro_ai/muhurat.py",
     '    if (panchang.tithi_name in rules.get("avoid_krishna_tithis", ())\n',
     '    if (False and panchang.tithi_name in rules.get("avoid_krishna_tithis", ())\n',
     "test_the_issue_repro_dark_half_11th_to_13th_are_avoid_with_the_flag"),
    ("#1022: the Krishna-paksha exclusion block never fires (booster path)",
     "src/astro_ai/muhurat.py",
     '    if (panchang.tithi_name in rules.get("avoid_krishna_tithis", ())\n',
     '    if (False and panchang.tithi_name in rules.get("avoid_krishna_tithis", ())\n',
     "test_a_booster_cannot_lift_a_dark_half_tithi"),
    ("#1022: the Krishna-paksha set is emptied in the Vivah rules",
     "src/astro_ai/muhurat.py",
     '        "avoid_krishna_tithis": {"Ekadashi", "Dwadashi", "Trayodashi"},',
     '        "avoid_krishna_tithis": set(),',
     "test_no_dark_half_11th_to_13th_is_acceptable_or_better_for_vivah"),
    ("#1022: the exclusion ignores the paksha and hits the bright half too",
     "src/astro_ai/muhurat.py",
     '            and panchang.tithi_paksha == "Krishna"):\n',
     '            ):\n',
     "test_the_bright_half_namesakes_are_not_excluded_and_keep_the_credit"),
    ("#1022: Dwadashi is back in Vivah's good_tithis",
     "src/astro_ai/muhurat.py",
     '                         "Ekadashi", "Trayodashi"},\n'
     '        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",\n'
     '                          "Amavasya", "Purnima"},\n'
     '        # Krishna-paksha only (#1022)',
     '                         "Ekadashi", "Dwadashi", "Trayodashi"},\n'
     '        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",\n'
     '                          "Amavasya", "Purnima"},\n'
     '        # Krishna-paksha only (#1022)',
     "test_bright_half_dwadashi_is_neutral_not_credited_and_not_excluded"),
    ("#1022: the bright-half Dwadashi is made an avoid tithi instead of neutral",
     "src/astro_ai/muhurat.py",
     '        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",\n'
     '                          "Amavasya", "Purnima"},\n'
     '        # Krishna-paksha only (#1022)',
     '        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",\n'
     '                          "Amavasya", "Purnima", "Dwadashi"},\n'
     '        # Krishna-paksha only (#1022)',
     "test_bright_half_dwadashi_is_neutral_not_credited_and_not_excluded"),
    ("#1022: every event, not just Vivah, now excludes the dark-half 11th-13th",
     "src/astro_ai/muhurat.py",
     'rules.get("avoid_krishna_tithis", ())',
     'rules.get("avoid_krishna_tithis", {"Ekadashi", "Dwadashi", "Trayodashi"})',
     "test_other_events_are_not_excluded_on_a_dark_half_tithi"),
    ("#1022: the exclusion reason stops saying it is the dark half",
     "src/astro_ai/muhurat.py",
     'Krishna-paksha (dark half, waning Moon) {tithi}: B.V. Raman',
     '{tithi}: B.V. Raman',
     "test_the_issue_repro_dark_half_11th_to_13th_are_avoid_with_the_flag"),
    ("#1022: the Vivah page stops naming Raman for the waning-half exclusion",
     "src/astro_ai/muhurat.py",
     "following B.V. Raman's Muhurtha, which rejects the dark-half 11th through New Moon for marriage",
     "following tradition",
     "test_the_rules_summary_carries_both_disclosures_and_never_says_classical_there"),
    ("#1022: the Vivah page stops saying whose list the 12th is on",
     "src/astro_ai/muhurat.py",
     "Rao's wedding guideline table lists it, Raman's rejects it, so the finder",
     "the finder",
     "test_the_rules_summary_carries_both_disclosures_and_never_says_classical_there"),
    ("#1022: the favourable-tithi line claims the 12th again",
     "src/astro_ai/muhurat.py",
     '"Favourable tithi: 2, 3, 5, 7, 10, 11, 13 (avoid 4, 8, 9, 14, Amavasya, Purnima); the 11th-13th',
     '"Favourable tithi: 2, 3, 5, 7, 10, 11, 12, 13 (avoid 4, 8, 9, 14, Amavasya, Purnima); the 11th-13th',
     "test_the_favourable_tithi_line_no_longer_claims_the_12th"),
    ("#1022: the /learn Vivah guide drops the Raman disclosure",
     "src/astro_ai/templates/learn/vivah-muhurat-2027.html",
     "rejects the dark-half 11th through New Moon for marriage, so our finder",
     "may differ for marriage, so our finder",
     "test_the_real_route_renders_the_disclosure_and_the_learn_page_agrees"),
]
