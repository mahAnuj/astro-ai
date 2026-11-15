"""#1093: the unsubscribe link's address and token must not reach GA4 as
/unsubscribe?email=<address>&token=<hmac>.

Rows target static/analytics.js, which tests/test_analytics_ask_location.py runs
under Node. One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("#1093: `email` is dropped from the strip-list, so the subscriber's address reaches GA4",
     "src/astro_ai/static/analytics.js",
     "  var PII_PARAMS = ['q', 'city', 'email', 'token'];\n",
     "  var PII_PARAMS = ['q', 'city', 'token'];\n",
     "test_unsubscribe_email_and_token_never_reach_gtag_config"),
    ("#1093: `token` is dropped from the strip-list, so the unsubscribe token reaches GA4",
     "src/astro_ai/static/analytics.js",
     "  var PII_PARAMS = ['q', 'city', 'email', 'token'];\n",
     "  var PII_PARAMS = ['q', 'city', 'email'];\n",
     "test_unsubscribe_email_and_token_never_reach_gtag_config"),
]
