"""#1504: Shashti and Dwadashi are avoided for Griha Pravesh and Shashti for Vivah (Raman's general
avoid list, knowledge/vedic_reference.md 29.9 and 29.13). tests/test_muhurat_shashti_dwadashi_rules.py.
Each old string ends on the next comment line so it matches exactly once (the harness refuses an
anchor that BEGINS on a comment)."""

MUTATIONS = [
    ("#1504: Griha Pravesh stops avoiding Shashti (Sarvartha Siddhi lifts 2027-02-12 again)",
     "src/astro_ai/muhurat.py",
     '        "avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami", "Dwadashi",\n'
     '                          "Chaturdashi", "Amavasya", "Purnima"},\n'
     "        # Nakshatras (#1061)",
     '        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Dwadashi",\n'
     '                          "Chaturdashi", "Amavasya", "Purnima"},\n'
     "        # Nakshatras (#1061)",
     "test_griha_pravesh_is_avoid_with_the_flag_in_both_pakshas"),
    ("#1504: Griha Pravesh stops avoiding Dwadashi (2027-02-18 is good again)",
     "src/astro_ai/muhurat.py",
     '        "avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami", "Dwadashi",\n'
     '                          "Chaturdashi", "Amavasya", "Purnima"},\n'
     "        # Nakshatras (#1061)",
     '        "avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami",\n'
     '                          "Chaturdashi", "Amavasya", "Purnima"},\n'
     "        # Nakshatras (#1061)",
     "test_real_dates_flip_to_avoid"),
    ("#1504: Vivah stops avoiding Shashti (Sarvartha Siddhi lifts 2027-02-12 again)",
     "src/astro_ai/muhurat.py",
     '                         "Ekadashi", "Trayodashi"},\n'
     '        "avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami", "Chaturdashi",\n'
     '                          "Amavasya", "Purnima"},\n'
     "        # Krishna-paksha only (#1022)",
     '                         "Ekadashi", "Trayodashi"},\n'
     '        "avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Chaturdashi",\n'
     '                          "Amavasya", "Purnima"},\n'
     "        # Krishna-paksha only (#1022)",
     "test_a_booster_cannot_lift_the_new_avoid_tithis"),
    ("#1504: the Vivah page stops listing the 6th among the avoided tithis",
     "src/astro_ai/muhurat.py",
     "(avoid 4, 6, 8, 9, 14, Amavasya, Purnima); the 11th-13th",
     "(avoid 4, 8, 9, 14, Amavasya, Purnima); the 11th-13th",
     "test_vivah_rules_summary_line_lists_the_avoided_tithis_it_applies"),
    ("#1504: the vivah Dwadashi note is removed (the cleared list says nothing about the contested 12th)",
     "src/astro_ai/muhurat_factors.py",
     '            "vivah": {"Dwadashi": _vr(C, "The 12th is contested: the Vedic table lists it for a "\n',
     '            "vivah": {"Dwadashi_x": _vr(C, "The 12th is contested: the Vedic table lists it for a "\n',
     "test_vivah_shukla_dwadashi_row_carries_the_contested_note"),
    ("#1504: _cleared_qual returns no qualifier (the note is registered but never shown)",
     "src/astro_ai/muhurat_factors.py",
     '    return _qual(key, event, tithi) if key == "avoid_tithi" else ""\n',
     '    return ""\n',
     "test_vivah_shukla_dwadashi_row_carries_the_contested_note"),
]
