"""#209: /kundli advertises nakshatra padas, so the result's planet table shows them."""

MUTATIONS = [
    ("#209: the result planet table stops rendering each planet's pada",
     "src/astro_ai/templates/result.html",
     "{% if p.pada %} <span class=\"text-bhagya-muted-2\">&middot;</span> <span data-pada>",
     "{% if false %} <span class=\"text-bhagya-muted-2\">&middot;</span> <span data-pada>",
     "test_result_planet_table_shows_each_planets_pada"),
    ("#209: the pada label loses its Hindi translation and renders the English word",
     "src/astro_ai/i18n.py",
     '"pada_label":          "पाद {n}",',
     '"pada_label":          "Pada {n}",',
     "test_result_planet_table_shows_each_planets_pada"),
    ("#209: the landing goes back to calling padas a 27-nakshatra granularity",
     "src/astro_ai/templates/kundli_landing.html",
     "each of the 27 nakshatras split into its four padas, 108 divisions in all.",
     "the 27-nakshatra granularity that classical texts actually use.",
     "test_landing_still_advertises_padas"),
]
