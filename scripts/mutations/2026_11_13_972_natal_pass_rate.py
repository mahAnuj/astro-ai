"""#972: the weekly natal pass rate on /admin/insights counts only what reading_quality
may honestly rate -- English readings, a literal True, newest week first."""

MUTATIONS = [
    ("#972: a Hindi reading is rated (its Latin-word bans undercount, so the rate reads better than the output)",
     "src/astro_ai/profiling.py",
     '        if str(d.get("lang") or "en") != "en":\n',
     '        if False:\n',
     "test_hindi_is_excluded_from_every_rate_and_counted_aside"),
    ("#972: any truthy q_ok counts as a pass (a malformed event reads as a good reading)",
     "src/astro_ai/profiling.py",
     'row["passed"] += 1 if d["q_ok"] is True else 0',
     'row["passed"] += 1 if d["q_ok"] else 0',
     "test_only_a_literal_true_is_a_pass"),
    ("#972: the table lists the oldest week first, so the current week is at the bottom",
     "src/astro_ai/profiling.py",
     "                                       reverse=True)\n",
     "                                       reverse=False)\n",
     "test_pass_rate_is_per_week_and_per_model"),
]
