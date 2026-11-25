"""#1344: in couple mode the combined verdict ranks inside a tier, so the Top pick is not a `mixed`
day while a `good-for-both` day of the same grade exists.

Rows target muhurat.py (`_VERDICT_ORDER`, `_verdict_rank`, `rank_key`, the tie count in `top_pick`)
and the couple disclosure in muhurat_finder.html, all exercised by tests/test_muhurat_top_pick.py.
One area file, a literal list (test_mutation_tables.py requires it)."""

_M = "src/astro_ai/muhurat.py"
_T = "src/astro_ai/templates/muhurat_finder.html"

MUTATIONS = [
    ("#1344: the verdict is dropped from the sort key, so a mixed day can head a tier again",
     _M, "    return (_TIER_ORDER.get(c.rating, 99), _verdict_rank(c), -c.score, c.d)",
     "    return (_TIER_ORDER.get(c.rating, 99), 0, -c.score, c.d)",
     "test_within_a_tier_good_for_both_ranks_before_mixed_even_when_later_and_lower_scoring"),
    ("#1344: the verdict order is flipped (mixed before good-for-both)",
     _M, '_VERDICT_ORDER = {"excellent-for-both": 0, "good-for-both": 1, "mixed": 2, "avoid": 3}',
     '_VERDICT_ORDER = {"excellent-for-both": 0, "good-for-both": 2, "mixed": 1, "avoid": 3}',
     "test_verdict_order_is_excellent_good_mixed_avoid"),
    ("#1344: the verdict is placed before the tier, so tier no longer dominates",
     _M, "    return (_TIER_ORDER.get(c.rating, 99), _verdict_rank(c), -c.score, c.d)",
     "    return (_verdict_rank(c), _TIER_ORDER.get(c.rating, 99), -c.score, c.d)",
     "test_tier_still_outranks_the_verdict"),
    ("#1344: the tie count ignores the verdict",
     _M, "if c is not best and (c.rating, _verdict_rank(c), c.score) == best_grade)",
     "if c is not best and (c.rating, c.score) == (best.rating, best.score))",
     "test_a_tie_counts_only_the_same_verdict"),
    ("#1344: an unknown verdict raises instead of ranking as mixed",
     _M, '_VERDICT_ORDER.get(c.couple.combined_verdict, _VERDICT_ORDER["mixed"])',
     "_VERDICT_ORDER[c.couple.combined_verdict]",
     "test_an_unknown_verdict_does_not_raise_and_ranks_as_mixed"),
    ("#1344: a row with no couple is ranked by a verdict, so non-couple order moves",
     _M, "    if c.couple is None:\n        return 0\n",
     "    if c.couple is None:\n        return 2\n    if False:\n        return 0\n",
     "test_non_couple_rows_rank_zero_for_the_verdict"),
    ("#1344: the couple card drops its verdict-first disclosure and shows the non-couple sentence",
     _T, "      {% if couple_active and tp.couple %}\n      <p class=\"text-xs text-bhagya-muted\">Among",
     "      {% if false %}\n      <p class=\"text-xs text-bhagya-muted\">Among",
     "test_a_couple_search_shows_the_verdict_and_the_not_an_endorsement_line"),
]
