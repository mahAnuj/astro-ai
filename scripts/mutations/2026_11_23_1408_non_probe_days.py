"""#1408: totals.non_probe_dates names the days totals.probe / totals.non_probe sum over."""

MUTATIONS = [
    ("#1408: non_probe_dates lists every known day, not only the days with a probe split",
     "scripts/collect_kundli_submissions.py",
     '[r["date"] for r in rows if r["non_probe"] is not None]',
     '[r["date"] for r in rows if r["fresh_generations"] is not None]',
     "test_non_probe_dates_skips_unmarked_empty_and_capped_days"),
    ("#1408: non_probe_dates is always empty, so the analyst cannot tell which days non_probe covers",
     "scripts/collect_kundli_submissions.py",
     '[r["date"] for r in rows if r["non_probe"] is not None]',
     '[]',
     "test_non_probe_dates_names_the_days_non_probe_sums_over"),
    ("#1408: the semantics stop telling the reader that probe/non_probe cover only non_probe_dates",
     "scripts/collect_kundli_submissions.py",
     '    "verify-production probes (X-Bhagya-Probe) unless `probe` is non-null. `totals.probe` and "\n'
     '    "`totals.non_probe` cover ONLY the days listed in `totals.non_probe_dates` (days whose "\n'
     '    "events all carry the probe marker); `totals.fresh_generations` covers every known day, "\n'
     '    "so never put one beside the other. Compare to GA4 `kundli_generated` only over days "\n'
     '    "inside `non_probe_dates`. Days are UTC. null = unknown, never 0 "\n',
     '    "verify-production probes (X-Bhagya-Probe) unless `probe` is non-null. "\n'
     '    "Days are UTC. null = unknown, never 0 "\n',
     "test_semantics_says_what_the_number_is_not"),
]
