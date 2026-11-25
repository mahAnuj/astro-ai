"""#1341: the muhurat finder's ranked top pick (R1 of #1017) and the Range select's searched days
(#1339).

Rows target muhurat.py (the score carried on MuhuratCandidate, `rank_key`, `top_pick`) and
routes/muhurat.py (the context handed to the template), which tests/test_muhurat_top_pick.py
exercises through the real finder and routes. One area file, a literal list
(test_mutation_tables.py requires it)."""

_M = "src/astro_ai/muhurat.py"
_R = "src/astro_ai/routes/muhurat.py"
_T = "src/astro_ai/templates/muhurat_finder.html"

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
    ("#1339: the Range select hard-codes 60 as the selected option again",
     _T, "{% if o == sel %} selected{% endif %}", "{% if o == 60 %} selected{% endif %}",
     "test_the_range_select_shows_the_days_searched"),
    ("#1339: a searched value that is already a standard option is listed twice",
     _T, "([] if sel in [30, 60, 90, 180] else [sel])", "[sel]",
     "test_the_range_select_shows_the_days_searched"),
    ("#1339: an out-of-range value on an error re-render is offered as an option",
     _T, "{% if sel < 1 or sel > 365 %}{% set sel = 60 %}{% endif %}", "",
     "test_a_bad_request_re_render_keeps_the_searched_days_selected"),
    ("#1341: the Top pick card drops the astro-auditor's disclosure",
     _T, "Among dates of the same grade, this card goes first", "Among dates of the same tier, this card goes first",
     "test_the_disclosure_is_always_in_the_card"),
    ("#1341: the Top pick card is headed with a superlative",
     _T, 'mb-1">Top pick</h3>', 'mb-1">Best pick</h3>',
     "test_the_card_never_prints_the_score_and_never_says_best"),
    ("#1341: the card hides that the pick won on order alone",
     _T, "{% if tp_ties > 0 %}", "{% if false %}",
     "test_a_pick_that_won_on_order_alone_says_so"),
    ("#1341: the card is shown for a window with no auspicious date",
     _T, "{% if top_pick %}\n    {% set tp = top_pick %}",
     "{% if top_pick or candidates %}\n    {% set tp = top_pick %}",
     "test_no_card_for_a_window_with_no_auspicious_date"),
    ("#1341: the couple card drops the not-an-endorsement line",
     _T, " It is not a classical endorsement for your two charts.", "",
     "test_a_couple_search_shows_the_verdict_and_the_not_an_endorsement_line"),
    ("#1341: an all-couple-avoid window shows no explanation",
     _T, "{% elif auspicious_candidates and couple_active %}", "{% elif false %}",
     "test_every_date_couple_avoid_says_so_and_shows_no_card"),
]
