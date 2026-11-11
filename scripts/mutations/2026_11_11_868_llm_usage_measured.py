"""#868: collect_llm_usage reads the provider-measured input tokens, not the zeroed field,
and says unknown rather than 0. Each row re-breaks one of those and the suite must go red."""

_C = "scripts/collect_llm_usage.py"

MUTATIONS = [
    ("#868: the collector reads by_route input_tokens (0 since #473) again",
     _C, '"input_tokens": int(m["input_tokens"]) if n else None,',
     '"input_tokens": int(r.get("input_tokens") or 0),',
     "test_input_tokens_come_from_the_measured_store_not_the_zeroed_field"),
    ("#868: provider routes are no longer folded onto their feature (rashifal_single stays apart)",
     _C, 'key = PROVIDER_ROUTE_FEATURE.get(m.get("route") or "", m.get("route") or "")',
     'key = m.get("route") or ""',
     "test_a_provider_route_is_folded_onto_the_feature_it_serves"),
    ("#868: an unmeasured window reports 0 input tokens instead of unknown",
     _C, 'for r in routes) if any_measured else None,',
     'for r in routes) if any_measured else 0,',
     "test_an_unmeasured_route_is_unknown_not_zero"),
    ("#868: the ceiling detector reads the output-only peak first again",
     "scripts/detect_ops_regressions.py",
     'peak, peak_day = llm.get("peak_day_measured_tokens"), llm.get("peak_day_measured")\n'
     '        if not isinstance(peak, (int, float)):',
     'peak, peak_day = llm.get("peak_day_tokens"), llm.get("peak_day")\n'
     '        if not isinstance(peak, (int, float)):',
     "test_token_ceiling_reads_the_measured_peak_not_the_output_only_one"),
    ("#868: the measured peak day drops the output side",
     "src/astro_ai/llm_stats.py",
     'day_meas += _as_int(r.get("input_tokens")) + _as_int(r.get("output_tokens"))',
     'day_meas += _as_int(r.get("input_tokens"))',
     "test_measured_peak_day_counts_provider_reported_input_and_is_none_when_absent"),
]
