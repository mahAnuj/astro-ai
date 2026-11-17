"""#1175 (#1107 criteria 1-2): tool pages link specific articles; no article is an orphan.

One row removes a tool page's article links; one removes the last inbound edge of a
formerly orphaned article. Both are silent: the page renders and nothing errors."""

MUTATIONS = [
    ("#1175: /panchang loses its three article cards (renders fine, links nothing)",
     "src/astro_ai/templates/panchang.html",
     (
     '      <a href="/learn/vivah-muhurat-2027/" class="block p-4 bg-white border border-bhagya-line hover:border-bhagya-saffron transition-colors">\n'
     '        <div class="font-semibold text-bhagya-sindoor text-sm">Vivah Muhurat 2027 guide →</div>\n'
     '        <div class="text-xs text-bhagya-muted mt-1">The rules behind wedding dates, and where each comes from</div>\n'
     '      </a>\n'
     '      <a href="/learn/griha-pravesh-muhurat-2026-2027/" class="block p-4 bg-white border border-bhagya-line hover:border-bhagya-saffron transition-colors">\n'
     '        <div class="font-semibold text-bhagya-sindoor text-sm">Griha Pravesh Muhurat 2026-27 guide →</div>\n'
     '        <div class="text-xs text-bhagya-muted mt-1">House-warming dates and the criteria behind them</div>\n'
     '      </a>\n'
     '      <a href="/learn/diwali-muhurat-2026/" class="block p-4 bg-white border border-bhagya-line hover:border-bhagya-saffron transition-colors">\n'
     '        <div class="font-semibold text-bhagya-sindoor text-sm">Diwali Muhurat 2026 guide →</div>\n'
     '        <div class="text-xs text-bhagya-muted mt-1">The five days of Diwali and the puja window for each</div>\n'
     '      </a>\n'
     ),
     "",
     "test_each_tool_page_links_at_least_two_distinct_articles_in_its_body"),
    ("#1175: the dosha form's per-tool article map is keyed by a path no route uses",
     "src/astro_ai/templates/dosha_check_form.html",
     "'/sade-sati-check': [",
     "'/sade-sati-checker': [",
     "test_each_tool_page_links_at_least_two_distinct_articles_in_its_body"),
    ("#1175: mercury-remedies loses the only edge into it (orphan again)",
     "src/astro_ai/learn_registry.py",
     '"guru-jupiter-in-vedic-astrology", "mercury-remedies")',
     '"guru-jupiter-in-vedic-astrology")',
     "test_every_article_has_an_inbound_link_other_than_the_index"),
    ("#1175: /numerology's form view loses its Related reading block",
     "src/astro_ai/templates/numerology.html",
     '<a href="/learn/name-numerology-explained/"',
     '<a href="/numerology/compatibility"',
     "test_each_tool_page_links_at_least_two_distinct_articles_in_its_body"),
]
