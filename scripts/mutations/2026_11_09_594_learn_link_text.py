"""Mutation rows for #594 -- a learn article closing on a raw URL path as link text (2026-11-09).

One file per area, loaded and appended by `scripts/mutate_behaviour_suite.py`.

DATA ONLY. `MUTATIONS` must stay a literal list: `verify_no_relaxation.py`
counts it by parsing, and a list built by a call or concatenation cannot be
counted and would read as rows deleted.
"""

MUTATIONS = [
    ("learn: the rahu-ketu article's Dasha link text is the raw path again",
     "src/astro_ai/templates/learn/rahu-mahadasha-ketu-antardasha.html",
     '<a href="/dasha">The Dasha calculator</a>',
     '<a href="/dasha">/dasha</a>',
     "test_the_rahu_ketu_article_links_dasha_with_words"),
]
