"""#1370: six surfaces stop calling a modern textbook's grain table "classical".

Each row restores the old wording on one surface and names the test that must go red."""

_L = "src/astro_ai/templates/learn/"
_PAGE = "test_remedy_pages_use_the_ruled_grain_wording"
_SCAN = "test_no_source_file_calls_a_grain_classical"

MUTATIONS = [
    ("#1370: mars-remedies calls toor daal Mars's classical grain again",
     _L + "mars-remedies.html",
     "</strong> — the grain a modern textbook's table gives Mars. Also red flowers",
     "</strong> — Mars's classical grain. Also red flowers",
     _PAGE),
    ("#1370: mangal-mars page calls toor daal Mars's classical grain again",
     _L + "mangal-mars-in-vedic-astrology.html",
     "</strong> is the grain a modern textbook's table gives Mars. Also red cloth",
     "</strong> is Mars's classical grain. Also red cloth",
     _PAGE),
    ("#1370: mercury-remedies calls moong daal Mercury's classical grain again",
     _L + "mercury-remedies.html",
     "— the grain a modern textbook's table gives Mercury)",
     "— Mercury's classical grain)",
     _PAGE),
    ("#1370: jupiter-remedies calls chick peas Jupiter's classical grain again",
     _L + "jupiter-remedies.html",
     "(the grain a modern textbook's table gives Jupiter)",
     "(Jupiter's classical grain)",
     _PAGE),
    ("#1370: rahu-remedies calls urad daal Rahu's classical grain again",
     _L + "rahu-remedies.html",
     "— the grain a modern textbook's table gives Rahu; often given",
     "— Rahu's classical grain; often given",
     _PAGE),
    ("#1370: numerology Mars fasting_day calls toor daal Mars's classical grain again",
     "src/astro_ai/numerology.py",
     "dark yellow lentil, the grain a modern textbook's table gives Mars)",
     "dark yellow lentil, Mars's classical grain)",
     "test_numerology_mars_fasting_day_uses_the_ruled_wording"),
]
