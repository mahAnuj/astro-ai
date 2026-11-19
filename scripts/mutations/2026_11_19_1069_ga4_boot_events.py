"""#1069: no feature_view / user_identified event; user properties are SET once.

Rows target static/analytics.js and templates/base.html, which
tests/test_analytics_boot_events.py checks statically, by rendering, and by running
the real analytics.js under Node. One area file, a literal list
(test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("#1069: the bootstrap no longer sets user properties (every later event loses age_bucket/lang/has_chart)",
     "src/astro_ai/static/analytics.js",
     "        window.gtag('set', 'user_properties', up);\n",
     "",
     "test_boot_sets_user_properties_once_and_sends_no_event"),
    ("#1069: user_identified is sent as an event again at boot",
     "src/astro_ai/static/analytics.js",
     "        window.gtag('set', 'user_properties', up);\n",
     "        window.gtag('set', 'user_properties', up);\n"
     "        window.gtag('event', 'user_identified', up);\n",
     "test_boot_sets_user_properties_once_and_sends_no_event"),
    ("#1069: user properties are set after config, so the first page_view misses them",
     "src/astro_ai/static/analytics.js",
     "    window.gtag('config', cfg.ga4, gaCfg);\n",
     "    window.gtag('config', cfg.ga4, gaCfg);\n"
     "    if (window.BHAGYA_USER_PROPS) window.gtag('set', 'user_properties', window.BHAGYA_USER_PROPS);\n",
     "test_boot_with_malformed_user_props_sends_no_set"),
    ("#1069: user properties are re-sent on every boosted swap (a set per navigation)",
     "src/astro_ai/static/analytics.js",
     "    document.addEventListener('htmx:pushedIntoHistory', syncLocation);\n",
     "    document.addEventListener('htmx:pushedIntoHistory', function () {\n"
     "      syncLocation();\n"
     "      if (window.BHAGYA_USER_PROPS) window.gtag('set', 'user_properties', window.BHAGYA_USER_PROPS);\n"
     "    });\n",
     "test_page_load_and_boosted_navigation_send_no_feature_view_or_user_identified"),
    ("#1069: a boosted swap fires feature_view again",
     "src/astro_ai/static/analytics.js",
     "  document.addEventListener('htmx:afterSettle', scanDeclared);\n",
     "  document.addEventListener('htmx:afterSettle', scanDeclared);\n"
     "  document.addEventListener('htmx:afterSettle', function () {\n"
     "    window.gtag && window.gtag('event', 'feature_view', { feature: location.pathname.split('/')[1] });\n"
     "  });\n",
     "test_page_load_and_boosted_navigation_send_no_feature_view_or_user_identified"),
    ("#1069: featureView is back on the public surface",
     "src/astro_ai/static/analytics.js",
     "    feedbackSent:       function (p) { track('feedback_sent',        p); },\n",
     "    feedbackSent:       function (p) { track('feedback_sent',        p); },\n"
     "    featureView: function (f) { if (f) track('feature_view', { feature: f }); },\n",
     "test_analytics_js_defines_none_of_the_removed_methods"),
    ("#1069: base.html calls into Analytics from an inline DOMContentLoaded script again",
     "src/astro_ai/templates/base.html",
     "<script src=\"/static/analytics.js?v={{ asset_v('analytics.js') }}\" defer></script>\n",
     "<script src=\"/static/analytics.js?v={{ asset_v('analytics.js') }}\" defer></script>\n"
     "<script>document.addEventListener('DOMContentLoaded', function () {"
     " if (window.Analytics) Analytics.userIdentified(window.BHAGYA_USER_PROPS); });</script>\n",
     "test_base_html_has_no_inline_domcontentloaded_analytics_script"),
    ("#1069: base.html drops BHAGYA_USER_PROPS, so analytics.js has nothing to set",
     "src/astro_ai/templates/base.html",
     "  window.BHAGYA_USER_PROPS = {\n",
     "  window.BHAGYA_USER_PROPS_X = {\n",
     "test_a_rendered_page_defines_user_props_and_calls_nothing_inline"),
    ("#1069: the user-properties set throws when GA4 is configured but the bag is not an object",
     "src/astro_ai/static/analytics.js",
     "      if (up && typeof up === 'object' && !Array.isArray(up)) {\n",
     "      if (true) {\n",
     "test_boot_with_malformed_user_props_sends_no_set"),
]
