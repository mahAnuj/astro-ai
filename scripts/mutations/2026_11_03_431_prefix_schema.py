"""#431: the prefix-cache read gate and the write side share one known-shape rule.

The read gate used to test `_PREFIX_ZERO`, so adding any counter skipped every
stored row. It tests `_PREFIX_REQUIRED` now; these rows restore each way that
could silently come back."""

MUTATIONS = [
    ("#431: the read gate tests _PREFIX_ZERO again (a defaultable counter skips every stored row)",
     "src/astro_ai/llm_stats.py",
     "            if not _is_known_prefix_row(pc):",
     "            if not _PREFIX_ZERO.keys() <= pc.keys():",
     "test_a_v2_row_stays_readable_when_a_defaultable_key_is_added"),
    ("#431: record() upgrades an old-shaped row in place again (a v1 row's 76k cached tokens read as current)",
     "src/astro_ai/llm_stats.py",
     "            pc = rows[stat_key] = dict(_PREFIX_ZERO)",
     "            pc = rows.setdefault(stat_key, dict(_PREFIX_ZERO))",
     "test_a_v1_row_is_replaced_not_upgraded_by_the_next_calls"),
    ("#431: _PREFIX_REQUIRED shrunk until a v1 row (prompt_tokens, no denominators) is readable",
     "src/astro_ai/llm_stats.py",
     '_PREFIX_REQUIRED = frozenset({"calls", "measurable", "reported",\n'
     '                              "prompt_measurable", "prompt_reported", "cached_tokens",\n'
     '                              "cached_measurable", "reported_unmeasurable"})',
     '_PREFIX_REQUIRED = frozenset({"calls", "reported", "cached_tokens"})',
     "test_the_required_set_sits_between_the_v2_keys_and_what_record_writes"),
]
