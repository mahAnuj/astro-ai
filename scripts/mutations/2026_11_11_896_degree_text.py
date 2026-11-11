"""Mutation rows for #896 -- a one-decimal degree within a sign is 0.0..29.9 (2026-11-11).

One file per area, loaded and appended by `scripts/mutate_behaviour_suite.py`.
DATA ONLY: `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`).
"""

MUTATIONS = [
    ("chart: degree_text rounds again, so 29.95..29.999 prints as 30.0",
     "src/astro_ai/chart.py",
     "    tenths = min(299, max(0, int(longitude * 10 + 1e-9)))",
     "    tenths = max(0, int(round(longitude * 10)))",
     "test_degree_text_truncates_and_never_reaches_30"),
    ("chart: the prompt prose goes back to :.1f for planets",
     "src/astro_ai/chart.py",
     "{p.rashi} at {degree_text(p.longitude)}deg \"",
     "{p.rashi} at {p.longitude:.1f}deg \"",
     "test_prompt_and_templates_use_it"),
    ("result.html: the lagna tile goes back to \"%.1f\"|format",
     "src/astro_ai/templates/result.html",
     "chart.lagna_rashi, chart.lagna_longitude|degree_text ~ \"°\"",
     "chart.lagna_rashi, \"%.1f\"|format(chart.lagna_longitude) ~ \"°\"",
     "test_prompt_and_templates_use_it"),
]
