"""#889 -- /matching's positions line, and the South Indian chart's stack and caption.

Each row re-breaks one property and names the test that must go red."""

_MATCHING = "src/astro_ai/templates/matching_result.html"
_POS = "src/astro_ai/templates/_chart_positions.html"
_SOUTH = "src/astro_ai/templates/_south_indian_chart.html"
_DIAMOND = "src/astro_ai/templates/_diamond_labels.html"
_LINE_TEST = "test_each_chart_lists_every_planet_with_its_degree_and_retrograde_flag"
_SOUTH_TEST = "test_every_label_stays_inside_its_cell_and_nothing_overlaps"

MUTATIONS = [
    ("#889: /matching no longer prints the positions line under its charts",
     _MATCHING,
     "    {{ chart_positions(ch, t(lang, 'matching_positions_label')) }}\n",
     "",
     _LINE_TEST),

    ("#889: the positions line drops the retrograde flag",
     _POS,
     "&deg;{% if p[2] %}&nbsp;R{% endif %}</span>",
     "&deg;</span>",
     _LINE_TEST),

    ("#889: the positions line drops the degree (the thing the diamond dropped)",
     _POS,
     "{{ p[0] }}&nbsp;{{ p[1] }}&deg;{% if p[2] %}",
     "{{ p[0] }}{% if p[2] %}",
     _LINE_TEST),

    ("#889: the positions line drops to 10px (below the 12px floor)",
     _POS,
     'class="mt-2 text-xs text-bhagya-muted leading-relaxed" data-chart-positions',
     'class="mt-2 text-[10px] text-bhagya-muted leading-relaxed" data-chart-positions',
     "test_the_line_is_never_below_the_12px_floor"),

    ("#889: the Hindi label for the positions line is gone",
     "src/astro_ai/i18n.py",
     '    "matching_positions_label": "ग्रह स्थिति",\n',
     '    "matching_positions_label": "Positions",\n',
     "test_the_line_is_labelled_in_both_languages"),

    ("#889: the diamond header says the dropped degree is in a table /matching lacks",
     _DIAMOND,
     "dropped here is lost from the page, but WHERE it survives differs: /kundli has",
     "remain in the positions table under the chart. /kundli has",
     "test_the_false_sentence_about_the_positions_table_is_gone"),

    ("#889: LAGNA goes back to cy+92, in the planet stack's path",
     _SOUTH,
     '<text x="{{ cx + 46 }}" y="{{ cy + 16 }}" text-anchor="middle"',
     '<text x="{{ cx + 50 }}" y="{{ cy + 92 }}" text-anchor="middle"',
     _SOUTH_TEST),

    ("#889: the South Indian stack starts at cy+42 for every count (6 leave the cell)",
     _SOUTH,
     "{% set y0 = [42, 94 - 13 * (n - 1)]|min if n <= 6 else 42 %}",
     "{% set y0 = 42 %}",
     _SOUTH_TEST),

    ("#889: the South Indian chart never switches to two columns (8 leave the cell)",
     _SOUTH,
     "      {% if n <= 6 %}\n      <text x=\"{{ cx + 50 }}\"",
     "      {% if n <= 99 %}\n      <text x=\"{{ cx + 50 }}\"",
     _SOUTH_TEST),
]
