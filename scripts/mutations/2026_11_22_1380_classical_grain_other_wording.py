"""#1380: three more wordings of "a modern textbook's grain/charity table is classical" retired.

Each row restores the old wording on one surface and names the test that must go red."""

_L = "src/astro_ai/templates/learn/"
_PAGE = "test_remedy_pages_use_the_ruled_grain_wording"

MUTATIONS = [
    ("#1380: sade-sati calls sesame seeds a classical Saturn grain again",
     _L + "sade-sati.html",
     "— the grain a modern textbook's table gives Saturn.</li>",
     "— a classical Saturn grain.</li>",
     _PAGE),
    ("#1380: career-during-sade-sati puts sesame seeds in the classical remedy tables again",
     _L + "career-during-sade-sati.html",
     "Sesame seeds are the grain a modern textbook's table gives Saturn; mustard oil",
     "Sesame seeds are Saturn's grain in the classical remedy tables; mustard oil",
     _PAGE),
    ("#1380: rahu-remedies calls its charity list classical again",
     _L + "rahu-remedies.html",
     "heaviness-planets). Charity items for Rahu:",
     "heaviness-planets). Classical charity items for Rahu:",
     _PAGE),
]
