"""#713: Panchak opens at the third quarter of Dhanishta, not at the nakshatra
(Raman, Muhurtha ch. III, Nakshatra Panchaka -- per the issue; not re-read)."""

MUTATIONS = [
    ("#713: all of Dhanishta is Panchak again (pada 1-2 flagged, the original defect)",
     "src/astro_ai/muhurat.py",
     "        return pada >= _PANCHAK_FIRST_DHANISHTA_PADA\n",
     "        return True\n",
     "test_dhanishta_first_half_is_not_panchak_and_second_half_is"),
    ("#713: Revati dropped from the Panchak span (the end of the window lost)",
     "src/astro_ai/muhurat.py",
     '''_PANCHAK_WHOLE_NAKSHATRAS = {"Shatabhisha", "Purva Bhadrapada",
                             "Uttara Bhadrapada", "Revati"}''',
     '''_PANCHAK_WHOLE_NAKSHATRAS = {"Shatabhisha", "Purva Bhadrapada",
                             "Uttara Bhadrapada"}''',
     "test_the_finder_flags_panchak_only_from_dhanishta_pada_3"),
    ("#713: the Moon's pada never reaches the rule (finder passes a constant 4)",
     "src/astro_ai/muhurat.py",
     "    return (moon.nakshatra, moon.pada) if moon else (\"\", 0)\n",
     "    return (moon.nakshatra, 4) if moon else (\"\", 0)\n",
     "test_the_moon_pada_reaches_the_rule_from_the_chart_field"),
]
