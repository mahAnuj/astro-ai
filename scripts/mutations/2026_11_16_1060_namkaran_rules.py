"""#1060: Namkaran tithi and nakshatra sets follow the two held muhurta books (knowledge/vedic_reference.md 29.13).
Each row restores one removed defect and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_M = "src/astro_ai/muhurat.py"

MUTATIONS = [
    ("#1060: Namkaran credits Dwadashi again (Raman rejects the 12th, Rao's row omits it)",
     _M,
     '''"Ekadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami", "Dwadashi",
                          "Chaturdashi", "Amavasya", "Purnima"},''',
     '''"Ekadashi", "Dwadashi", "Trayodashi"},
        "avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami",
                          "Chaturdashi", "Amavasya", "Purnima"},''',
     "test_good_tithis_are_exactly_raos_row"),
    ("#1060: Namkaran stops avoiding Purnima and Shashti again (both on Raman's avoid list)",
     _M,
     '''"avoid_tithis": {"Chaturthi", "Shashti", "Ashtami", "Navami", "Dwadashi",
                          "Chaturdashi", "Amavasya", "Purnima"},''',
     '''"avoid_tithis": {"Chaturthi", "Ashtami", "Navami", "Dwadashi",
                          "Chaturdashi", "Amavasya"},''',
     "test_dwadashi_purnima_shashti_are_hard_avoid_not_credited"),
    ("#1060: Namkaran drops Dhanishta and Shatabhisha again (on Raman's list and Rao's row)",
     _M,
     '''"Anuradha", "Shravana", "Dhanishta", "Shatabhisha",
                             "Uttara Phalguni", "Uttara Ashadha",
                             "Uttara Bhadrapada", "Revati"},''',
     '''"Anuradha", "Shravana",
                             "Uttara Phalguni", "Uttara Ashadha",
                             "Uttara Bhadrapada", "Revati"},''',
     "test_dhanishta_and_shatabhisha_are_credited_in_scoring"),
    ("#1060: Namkaran landing copy says the 11th day again instead of Raman's 10th, 12th or 16th",
     _M,
     '''"hero_subtitle": "Raman's 10th, 12th or 16th day after birth + auspicious nakshatra and tithi selection for a newborn.",''',
     '''"hero_subtitle": "Traditional 11th-day timing + auspicious nakshatra and tithi selection for a newborn.",''',
     "test_page_copy_gives_ramans_days_and_not_the_unsourced_eleventh"),
    ("#1060: Namkaran rules_summary lists the 12th as favourable again",
     _M,
     '''"Favourable tithi (2, 3, 5, 7, 10, 11, 13); the 4th''',
     '''"Favourable tithi (2, 3, 5, 7, 10, 11, 12, 13); the 4th''',
     "test_rules_summary_tithi_line_matches_the_set"),
]
