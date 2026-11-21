"""#1341: the muhurat finder's ranked top pick (R1 of #1017) and the Range select's searched days
(#1339).

Rows target muhurat.py (the score carried on MuhuratCandidate, `rank_key`, `top_pick`) and
routes/muhurat.py (the context handed to the template), which tests/test_muhurat_top_pick.py
exercises through the real finder and routes. One area file, a literal list
(test_mutation_tables.py requires it)."""

_M = "src/astro_ai/muhurat.py"
_R = "src/astro_ai/routes/muhurat.py"

MUTATIONS = [
    ("#1341: the sort drops the score, so the earliest excellent day wins whatever it scored",
     _M, "    return (_TIER_ORDER.get(c.rating, 99), -c.score, c.d)",
     "    return (_TIER_ORDER.get(c.rating, 99), 0, c.d)",
     "test_the_higher_scoring_excellent_day_is_the_pick_even_when_later"),
    ("#1341: a higher score sorts LAST inside a tier (the sign of the score flipped)",
     _M, "    return (_TIER_ORDER.get(c.rating, 99), -c.score, c.d)",
     "    return (_TIER_ORDER.get(c.rating, 99), c.score, c.d)",
     "test_a_real_window_has_a_later_higher_scoring_excellent_day_and_the_pick_is_it"),
    ("#1341: a booster-lifted day keeps its raw soft score, with no tier floor",
     _M, "            _RATING_MIN_SCORE.get(rating, 0))",
     "            0)",
     "test_sweep_the_rating_is_still_a_pure_function_of_the_points_unless_lifted"),
    ("#1341: the tier cut-off is strict (a score exactly on a floor no longer reaches the tier)",
     _M, "next((r for r, floor in _RATING_MIN_SCORE.items() if score >= floor), \"caution\")",
     "next((r for r, floor in _RATING_MIN_SCORE.items() if score > floor), \"caution\")",
     "test_sweep_the_rating_is_still_a_pure_function_of_the_points_unless_lifted"),
    ("#1341: top_pick skips the couple-avoid filter, so a day the pair's factors reject is the headline",
     _M, "                if c.rating in AUSPICIOUS_RATINGS\n"
         "                and not (c.couple and c.couple.combined_verdict == \"avoid\")]",
     "                if c.rating in AUSPICIOUS_RATINGS]",
     "test_a_couple_avoid_day_is_never_the_pick_but_stays_in_the_list"),
    ("#1341: top_pick accepts a caution day as the pick",
     _M, "                if c.rating in AUSPICIOUS_RATINGS\n"
         "                and not (c.couple",
     "                if c.rating != \"avoid\"\n"
         "                and not (c.couple",
     "test_caution_only_avoid_only_and_empty_give_no_pick"),
    ("#1341: top_pick counts a tie on rating alone, ignoring the score",
     _M, "if c is not best and (c.rating, c.score) == (best.rating, best.score))",
     "if c is not best and c.rating == best.rating)",
     "test_ties_pick_the_earliest_and_count_the_others"),
    ("#1341: an Abujha day scores 0 instead of the excellent floor",
     _M, "                score=_RATING_MIN_SCORE[\"excellent\"],", "                score=0,",
     "test_an_abujha_day_carries_the_excellent_floor"),
    ("#1341: the route hands the template no top pick",
     _R, "         \"top_pick\": pick, \"top_pick_ties\": pick_ties,",
     "         \"top_pick\": None, \"top_pick_ties\": pick_ties,",
     "test_the_route_hands_the_template_the_pick"),
    ("#1339: the Range select is handed the raw days, not the clamped value searched",
     _R, "         \"prefill_days\": len(candidates),", "         \"prefill_days\": int(days),",
     "test_prefill_days_is_the_clamped_value"),
    ("#1339: a failed search forgets the requested days",
     _R, "             \"via_get\": via_get, \"prefill_days\": days},\n            status_code=500,",
     "             \"via_get\": via_get},\n            status_code=500,",
     "test_a_failed_search_keeps_the_requested_days"),
    ("#1339: an invalid-date re-render forgets the requested days",
     _R, "             \"prefill_city\": city, \"prefill_start\": start_date,\n"
         "             \"event_types\": event_types, \"selected_event\": event_type,\n"
         "             \"has_saved_chart\": has_saved_chart, \"use_personal\": wants_personal,\n"
         "             \"via_get\": via_get, \"prefill_days\": days},\n"
         "            status_code=400,\n        )\n    # Before any geocode",
     "             \"prefill_city\": city, \"prefill_start\": start_date,\n"
         "             \"event_types\": event_types, \"selected_event\": event_type,\n"
         "             \"has_saved_chart\": has_saved_chart, \"use_personal\": wants_personal,\n"
         "             \"via_get\": via_get},\n"
         "            status_code=400,\n        )\n    # Before any geocode",
     "test_error_re_renders_keep_the_requested_days"),
]
