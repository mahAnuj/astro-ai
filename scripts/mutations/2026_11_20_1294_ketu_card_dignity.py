"""#1294: the 9-grahas overview's Ketu card follows the scheme the Rahu card and knowledge/ hold (Rao Table 6:
Ketu exalted in Sagittarius, debilitated in Gemini; some say Scorpio / Taurus), not Scorpio / Taurus as the bare
"(disputed)" pair it used to show.

Each row restores the removed claim verbatim (taken from the pre-fix text) and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

MUTATIONS = [
    (
        '#1294: the-9-grahas-overview Ketu card shows Scorpio / Taurus as "(disputed)" again',
        'src/astro_ai/templates/learn/the-9-grahas-overview.html',
        '<strong>Exalted in:</strong> Sagittarius (some say Scorpio) &middot; <strong>Debilitated in:</strong> Gemini (some say Taurus)<br>',
        '<strong>Exalted in:</strong> Scorpio (disputed) &middot; <strong>Debilitated in:</strong> Taurus (disputed)<br>',
        'test_ketu_card_matches_the_held_scheme_and_mirrors_rahu',
    ),
    (
        '#1294: the-9-grahas-overview Ketu card flips only the exaltation half back to Scorpio',
        'src/astro_ai/templates/learn/the-9-grahas-overview.html',
        '<strong>Exalted in:</strong> Sagittarius (some say Scorpio) &middot; <strong>Debilitated in:</strong> Gemini (some say Taurus)<br>',
        '<strong>Exalted in:</strong> Scorpio (some say Sagittarius) &middot; <strong>Debilitated in:</strong> Gemini (some say Taurus)<br>',
        'test_ketu_card_matches_the_held_scheme_and_mirrors_rahu',
    ),
    (
        '#1294: the-9-grahas-overview Ketu card flips only the debilitation half back to Taurus',
        'src/astro_ai/templates/learn/the-9-grahas-overview.html',
        '<strong>Exalted in:</strong> Sagittarius (some say Scorpio) &middot; <strong>Debilitated in:</strong> Gemini (some say Taurus)<br>',
        '<strong>Exalted in:</strong> Sagittarius (some say Scorpio) &middot; <strong>Debilitated in:</strong> Taurus (some say Gemini)<br>',
        'test_ketu_card_matches_the_held_scheme_and_mirrors_rahu',
    ),
]
