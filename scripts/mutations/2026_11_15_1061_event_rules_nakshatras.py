"""#1061 / #1059: Griha Pravesh and Vidyarambh nakshatra and tithi sets follow the two held muhurta books
(knowledge/vedic_reference.md 29.13). Each row restores one removed defect and names the test that must go red.
The Thursday-peak comment label is pinned by a test but has no row: the harness refuses comment anchors.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_M = "src/astro_ai/muhurat.py"

MUTATIONS = [
    ("#1061: Griha Pravesh credits Hasta again (in neither Raman's nor Rao's house-entry list)",
     _M,
     '''"good_nakshatras": {"Rohini", "Mrigashira", "Uttara Phalguni",
                             "Chitra", "Anuradha",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"},''',
     '''"good_nakshatras": {"Rohini", "Mrigashira", "Uttara Phalguni",
                             "Hasta", "Chitra", "Anuradha",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"},''',
     "test_griha_pravesh_hasta_is_not_credited_and_uttara_bhadrapada_is"),
    ("#1061: Griha Pravesh drops Uttara Bhadrapada again (named among the best by Raman, on Rao's row)",
     _M,
     '''"Chitra", "Anuradha",
                             "Uttara Ashadha", "Uttara Bhadrapada", "Revati"},''',
     '''"Chitra", "Anuradha",
                             "Uttara Ashadha", "Revati"},''',
     "test_griha_pravesh_hasta_is_not_credited_and_uttara_bhadrapada_is"),
    ("#1059: Vidyarambh avoids Ardra again (both books call it beneficial for starting education)",
     _M,
     '''"avoid_nakshatras": {"Bharani", "Krittika", "Ashlesha",
                              "Magha", "Jyeshtha", "Mula"},
        "good_days":  {"Wednesday", "Thursday", "Friday", "Monday"},''',
     '''"avoid_nakshatras": {"Bharani", "Krittika", "Ardra", "Ashlesha",
                              "Magha", "Jyeshtha", "Mula"},
        "good_days":  {"Wednesday", "Thursday", "Friday", "Monday"},''',
     "test_vidyarambh_ardra_is_good_not_avoided"),
    ("#1059: Vidyarambh stops crediting Dhanishta and Satabhisha again (Raman's best list, Rao's bracket)",
     _M,
     '''"Anuradha", "Shravana", "Dhanishta", "Shatabhisha",
                             "Revati"},''',
     '''"Anuradha", "Shravana", "Revati"},''',
     "test_vidyarambh_ardra_is_good_not_avoided"),
    ("#1059: Vidyarambh stops avoiding Purnima again (Raman: New and Full Moon days should be avoided)",
     _M,
     '''"Amavasya", "Purnima"},
        # Nakshatras (#1059)''',
     '''"Amavasya"},
        # Nakshatras (#1059)''',
     "test_vidyarambh_purnima_is_avoided_like_amavasya"),
]
