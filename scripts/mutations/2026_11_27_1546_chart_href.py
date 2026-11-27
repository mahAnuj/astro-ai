"""#1546: footer, homepage cards and /learn `/ask` CTAs link /?needs_chart=<key>, not the four
303 URLs, for a visitor with no saved chart. tests/test_footer_cta_chart_gated_links.py."""

_D = "src/astro_ai/routes/deps.py"
_B = "src/astro_ai/templates/base.html"
_I = "src/astro_ai/templates/index.html"
_L = "src/astro_ai/templates/learn_article_base.html"
_A = "src/astro_ai/templates/learn/mars-remedies.html"

MUTATIONS = [
    ("#1546: chart_href returns the path unchanged for a no-chart visitor",
     _D, "    if key is not None and not _has_chart(request):\n", "    if False:\n",
     "test_chart_href_unit"),
    ("#1546: the footer's Today's Horoscope link goes back to /today",
     _B, "<li><a href=\"{{ chart_href(request, '/today') }}\"", '<li><a href="/today"',
     "test_no_chart_page_links_no_redirecting_url"),
    ("#1546: the footer's Monthly Horoscope link goes back to /monthly",
     _B, "<li><a href=\"{{ chart_href(request, '/monthly') }}\"", '<li><a href="/monthly"',
     "test_no_chart_page_links_no_redirecting_url"),
    ("#1546: the footer's yearly link goes back to /yearly",
     _B, "<li><a href=\"{{ chart_href(request, '/yearly') }}\"", '<li><a href="/yearly"',
     "test_no_chart_page_links_no_redirecting_url"),
    ("#1546: the homepage feature_card macro stops gating its href",
     _I, '<a href="{{ chart_href(request, href) }}"', '<a href="{{ href }}"',
     "test_no_chart_page_links_no_redirecting_url"),
    ("#1546: the /learn article CTA goes back to /ask",
     _L, "<a href=\"{{ chart_href(request, '/ask') }}\" class=\"flex-1", '<a href="/ask" class="flex-1',
     "test_no_chart_page_links_no_redirecting_url"),
    ("#1546: an article body's inline /ask link goes back to /ask",
     _A, "<a href=\"{{ chart_href(request, '/ask') }}\">Ask Shubh Bhagya", '<a href="/ask">Ask Shubh Bhagya',
     "test_no_chart_every_learn_article_links_no_redirecting_url"),
    ("#1546: a chart holder is rewritten too (the has_chart check is inverted)",
     _D, "    if key is not None and not _has_chart(request):\n",
     "    if key is not None and _has_chart(request):\n",
     "test_visitor_with_a_chart_keeps_the_direct_links"),
    ("#1546: _CHART_GATED gains a key whose route does not redirect",
     _D, '"/ask": "ask"}', '"/ask": "ask", "/rashifal": "rashifal"}',
     "test_chart_gated_keys_are_the_ones_the_routes_redirect_on"),
]
