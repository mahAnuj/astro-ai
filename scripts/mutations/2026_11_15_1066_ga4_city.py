"""#1066: the saved birth place must not reach GA4 as /panchang?city=<place>.

Rows target static/analytics.js, which tests/test_analytics_ask_location.py runs
under Node. One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("#1066: `city` is dropped from the strip-list, so the saved birth place reaches GA4",
     "src/astro_ai/static/analytics.js",
     "  var PII_PARAMS = ['q', 'city'];\n",
     "  var PII_PARAMS = ['q'];\n",
     "test_panchang_city_never_reaches_gtag_config"),
    ("#1066: the sanitiser stops after the first parameter it finds, so q and city are not both removed",
     "src/astro_ai/static/analytics.js",
     "      PII_PARAMS.forEach(function (k) {\n",
     "      PII_PARAMS.slice(0, found ? 0 : 1).forEach(function (k) {\n",
     "test_city_and_q_are_both_removed_from_one_url"),
    ("#1066: the sanitiser drops every query parameter, not only the PII ones",
     "src/astro_ai/static/analytics.js",
     "      return found ? u.toString() : url;\n",
     "      if (found) u.search = '';\n      return found ? u.toString() : url;\n",
     "test_city_is_stripped_but_other_params_survive"),
]
