"""Mutation rows for #893 -- a degree within a sign is 0..29, never 30 (2026-11-11).

One file per area, loaded and appended by `scripts/mutate_behaviour_suite.py`.
DATA ONLY: `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`).
"""

MUTATIONS = [
    ("chart: the degree label rounds again, so 29.5..29.99 prints as 30",
     "src/astro_ai/chart.py",
     "    return min(29, max(0, int(longitude)))",
     "    return int(round(longitude))",
     "test_diamond_and_south_charts_print_29_not_30"),
    ("chart: the degree label loses its 29 clamp, so a longitude of 30.0 prints 30",
     "src/astro_ai/chart.py",
     "    return min(29, max(0, int(longitude)))",
     "    return max(0, int(longitude))",
     "test_degree_label_truncates_and_never_reaches_30"),
]
