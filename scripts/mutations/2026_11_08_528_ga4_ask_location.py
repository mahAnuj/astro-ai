"""#528: a visitor's /ask question must not reach GA4 as the page URL.

Rows target static/analytics.js, which tests/test_analytics_ask_location.py runs
under Node. One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("#528: gtag config no longer overrides page_location, so GA4 stores /ask?q=<question>",
     "src/astro_ai/static/analytics.js",
     "      gaCfg.page_location = cleanLoc;\n",
     "",
     "test_ask_question_never_reaches_gtag_config"),
    ("#528: the sanitiser keeps q (returns the URL unchanged)",
     "src/astro_ai/static/analytics.js",
     "      u.searchParams.delete('q');\n",
     "",
     "test_ask_question_never_reaches_gtag_config"),
    ("#528: page_location is overridden on every page, not only when q is present",
     "src/astro_ai/static/analytics.js",
     "    if (cleanLoc !== location.href) {\n",
     "    if (true) {\n",
     "test_urls_without_q_get_no_override"),
    ("#528: the override is never reset after an hx-boost navigation",
     "src/astro_ai/static/analytics.js",
     "      window.gtag('set', { page_location: loc });\n",
     "",
     "test_override_is_reset_once_after_a_boosted_navigation"),
    ("#528: the manual pageView sends the raw URL again",
     "src/astro_ai/static/analytics.js",
     "          page_location: gaLocation()\n",
     "          page_location: location.href\n",
     "test_manual_page_view_carries_the_sanitised_location"),
]
