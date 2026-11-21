"""#1332: single-sunrise Ekadashi with Dwadashi skipped takes D-1 (an unsourced-in-corpus Drik
convention), in BOTH copies of the pick; `shukla_tithi_date` collects every candidate month,
keeps the dates in the requested year and returns the earliest.
tests/test_lunar_ekadashi_drik.py."""

_LO = "src/astro_ai/lunar_observances.py"
_LD = "src/astro_ai/lunar_dates.py"
_TPL = "src/astro_ai/templates/_festival_reckoning.html"

_GUARD = "                idx in _VIDDHA_TITHIS\n                and 0 < i\n"
_PREV = "                and samples[i - 1][1] == idx - 1\n"
_NEXT = "                and (samples[i + 1][1] - idx) % 30 >= 2\n"

MUTATIONS = [
    ("#1332: lunar_observances drops the day-earlier rule (Gauna date again)",
     _LO, _GUARD, "                False\n                and 0 < i\n",
     "test_the_three_drik_dates_are_emitted_a_day_earlier"),
    ("#1332: lunar_dates._pick_day drops the day-earlier rule (the copy drifts)",
     _LD, _GUARD, "                False\n                and 0 < i\n",
     "test_lunar_dates_agrees_with_lunar_observances_on_devuthani_2025"),
    ("#1332: lunar_observances forgets the previous sunrise must be t-1",
     _LO, _PREV, "",
     "test_without_t_minus_1_at_the_previous_sunrise_it_stays"),
    ("#1332: lunar_observances forgets the next sunrise must be t+2 or later",
     _LO, _NEXT, "",
     "test_t_plus_1_at_the_next_sunrise_stays_on_the_sunrise_day"),
    ("#1332: lunar_dates._pick_day forgets the previous sunrise must be t-1",
     _LD, _PREV, "",
     "test_pick_day_keeps_the_sunrise_day_when_either_condition_fails"),
    ("#1332: lunar_dates._pick_day forgets the next sunrise must be t+2 or later",
     _LD, _NEXT, "",
     "test_pick_day_keeps_the_sunrise_day_when_either_condition_fails"),
    ("#1332: shukla_tithi_date returns a date outside the requested year (Pausha 2026)",
     _LD, "if (d := _shukla_pick(m, tithi, reckoning)) is not None and d.year == year",
     "if (d := _shukla_pick(m, tithi, reckoning)) is not None",
     "test_a_month_with_no_occurrence_in_the_year_is_none_not_the_neighbouring_year"),
    ("#1332: shukla_tithi_date returns the later of two in-year candidates",
     _LD, "return min(dates) if dates else None", "return max(dates) if dates else None",
     "test_two_in_year_candidates_return_the_earlier"),
    ("#1332: shukla_tithi_date looks only at the first candidate month (Margashirsha 2027 again)",
     _LD, "for m in _nija_months(year, month)\n        if (d := _shukla_pick",
     "for m in _nija_months(year, month)[:1]\n        if (d := _shukla_pick",
     "test_margashirsha_2027_is_the_2027_month_not_the_december_2026_one"),
    ("#1332: the /festivals note drops the Drik Dwadashi day-earlier sentence",
     _TPL, "There is a third pick: an Ekadashi\n    seen at a single sunrise whose Dwadashi has no sunrise of its own is listed on the day\n    before, as Drik Panchang prints it. ",
     "",
     "test_festivals_note_states_the_drik_dwadashi_day_earlier_pick"),
    ("#1332: the /festivals note reinstates the Dashami-piercing justification",
     _TPL, "following Drik Panchang&rsquo;s published practice.",
     "since a tithi that long is already pierced by the preceding Dashami at the first sunrise.",
     "test_festivals_note_no_longer_claims_the_dashami_piercing_mechanism"),
]
