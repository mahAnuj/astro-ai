"""#1553 (2026-11-27): /admin/ops?tab=analytics 500ed when gsc-daily.json was absent or `rows: []`
(a macro's arguments are evaluated before its body). Each chart call is now guarded on the
series' `ok`, with a "No data" note otherwise. Exercised by
tests/test_ops_traffic_series_degrade.py.
One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("ops-traffic-degrade: the search-impressions chart is called even when its series is empty",
     "src/astro_ai/templates/admin_ops.html",
     "{% if T.impressions.ok %}",
     "{% if true %}",
     "test_missing_search_series_still_renders_people"),
    ("ops-traffic-degrade: the people chart is called even when its series is empty",
     "src/astro_ai/templates/admin_ops.html",
     "{% if T.users.ok %}",
     "{% if true %}",
     "test_missing_people_series_still_renders_search"),
    ("ops-traffic-degrade: the missing-series note renders nothing",
     "src/astro_ai/templates/admin_ops.html",
     "No data: <code>measurements/{{ fname }}</code> is missing or has no rows.",
     "",
     "test_missing_search_series_still_renders_people"),
]
