"""#150 slice 2: Gate 8 gets almanac rows for Saturday, Tuesday and Wednesday."""

MUTATIONS = [
    ("#150: Gate 8's almanac row for Saturday is shifted an hour",
     "scripts/verify_panchang_angas.py",
     "(\"2026-11-07\", \"Sat\", \"06:37\", \"17:32\", \"06:37\", \"07:59\"),",
     "(\"2026-11-07\", \"Sat\", \"06:37\", \"17:32\", \"07:37\", \"08:59\"),",
     "test_the_almanac_gate_is_green_and_can_go_red"),

    ("#150: Gate 8's almanac row for Tuesday carries Rahu Kalam's window, not Gulikai's",
     "scripts/verify_panchang_angas.py",
     "(\"2026-11-10\", \"Tue\", \"06:40\", \"17:30\", \"12:05\", \"13:26\"),",
     "(\"2026-11-10\", \"Tue\", \"06:40\", \"17:30\", \"14:47\", \"16:09\"),",
     "test_the_almanac_gate_is_green_and_can_go_red"),

    ("#150: Gate 8 no longer fails when a weekday has no almanac row",
     "scripts/verify_panchang_angas.py",
     "    if missing:\n        failures.append(",
     "    if False:\n        failures.append(",
     "test_the_almanac_gate_needs_a_row_for_every_weekday"),
]
