"""#1208: llm-usage.json exports site-wide fallbacks, read from range_summary()'s
aggregate (usage_summary() has none), unknown as None, reasons bounded. Each row
re-breaks one of those and the suite must go red."""

_C = "scripts/collect_llm_usage.py"

MUTATIONS = [
    ("#1208: slim reads top-level usage.get('fallbacks') -- a permanent silent 0 in production",
     _C, 'agg = usage.get("aggregate")\n    if not isinstance(agg, dict) or not _is_count(agg.get("fallbacks")):',
     'agg = usage\n    if not isinstance(agg, dict) or not _is_count(agg.get("fallbacks")):',
     "test_fallbacks_and_reasons_are_carried_from_the_aggregate"),
    ("#1208: an absent aggregate reports 0 fallbacks instead of unknown",
     _C, '        return None, None\n    reasons: dict[str, int] = {}',
     '        return 0, {}\n    reasons: dict[str, int] = {}',
     "test_absent_fallbacks_are_unknown_not_zero"),
    ("#1208: the reason cap is removed",
     _C, '[:_REASON_MAX_ENTRIES]', '',
     "test_fallback_reasons_are_bounded_and_clean"),
    ("#1208: _summary no longer attaches the range aggregate",
     _C, 'usage["aggregate"] = llm_stats.range_summary(days)["aggregate"]', 'pass',
     "test_the_default_summary_attaches_the_range_aggregate"),
]
