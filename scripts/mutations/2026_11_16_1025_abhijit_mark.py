"""#1025: the finder's Abhijit cell carries a tick only where it clears Rahu Kaal and Bhadra, and no
longer calls it "the most auspicious window". tests/test_muhurat_single_instant.py."""

_F = "src/astro_ai/templates/muhurat_finder.html"

MUTATIONS = [
    ("#1025: an overlapped Abhijit window carries the green tick again",
     _F,
     "{% if c.abhijit_overlaps %}<span class=\"text-amber-800\">~</span>{% else %}",
     "{% if False %}<span class=\"text-amber-800\">~</span>{% else %}",
     "test_abhijit_carries_a_tick_only_where_it_clears_rahu_kaal_and_bhadra"),
    ("#1025: a clear Abhijit window loses its tick",
     _F,
     "{% else %}<span class=\"text-emerald-800\">✓</span>{% endif %} Abhijit {{ c.abhijit_muhurta }}",
     "{% else %}<span class=\"text-amber-800\">~</span>{% endif %} Abhijit {{ c.abhijit_muhurta }}",
     "test_abhijit_carries_a_tick_only_where_it_clears_rahu_kaal_and_bhadra"),
    ("#1025: the legend calls Abhijit the most auspicious window again",
     _F,
     "The finder holds no source that calls Abhijit the most auspicious window or ranks it above either.",
     "Abhijit Muhurta = the most auspicious window, a fifteenth of daylight around solar noon.",
     "test_the_finder_no_longer_calls_abhijit_the_most_auspicious_window"),
]
