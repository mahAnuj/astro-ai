"""#1322: the muhurat finder headline counts only excellent/good/acceptable, and the
results name the timezone and the sunrise the clock times are local to.

Rows target templates/muhurat_finder.html, muhurat.py and routes/muhurat.py, which
tests/test_muhurat_honest_count_and_zone.py exercises through the real route. One area
file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("#1322: the headline counts every non-avoid date again (caution counted as auspicious)",
     "src/astro_ai/templates/muhurat_finder.html",
     "{% set auspicious_candidates = candidates | selectattr('rating', 'in', muhurat_auspicious_ratings()) | list %}",
     "{% set auspicious_candidates = candidates | rejectattr('rating', 'equalto', 'avoid') | list %}",
     "test_headline_counts_only_excellent_good_acceptable"),
    ("#1322: muhurat.py names a sunrise on a date with no ordinary sunrise (polar guard dropped)",
     "src/astro_ai/muhurat.py",
     "                rk_str = ab_str = sunrise_str = \"\"\n",
     "                rk_str = ab_str = \"\"\n                sunrise_str = p.sunrise.strftime('%H:%M')\n",
     "test_polar_date_says_no_sunrise_instead_of_printing_one"),
    ("#1322: the results hard-code the timezone instead of the geocoded one",
     "src/astro_ai/routes/muhurat.py",
     "search_tz = _chart.geocode_place(city)[2]",
     "search_tz = \"Asia/Kolkata\"",
     "test_delhi_and_london_name_their_own_zone_and_sunrise"),
]
