"""#1083: /learn/10th-lord-in-6th-house-career no longer says Jupiter is debilitated in Scorpio (it is debilitated
in Capricorn), and no longer credits unsourced profession lists and remedies to the classical texts.

Each row restores one removed false claim and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_T = "src/astro_ai/templates/learn/10th-lord-in-6th-house-career.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#1083: 'Jupiter debilitated in Scorpio' is back on the Gemini row",
     _T,
     "Jupiter in Scorpio is in the sign of Mars, a natural friend of Jupiter, so this is not a debilitation (Jupiter is debilitated in Capricorn).",
     "Jupiter debilitated in Scorpio in the 6th — one of the more challenging configurations.",
     "test_every_dignity_claim_matches_the_dignity_table"),
    ("#1083: the Gemini row loses its 'not a debilitation' correction",
     _T,
     "so this is not a debilitation (Jupiter is debilitated in Capricorn).",
     "so this is a strong placement.",
     "test_jupiter_in_scorpio_is_not_called_debilitated"),
    ("#1083: the Taurus row names the wrong 6th sign",
     _T,
     "Saturn (10th lord of Aquarius) in the 6th sign Libra.",
     "Saturn (10th lord of Aquarius) in the 6th sign Scorpio.",
     "test_each_row_names_the_right_10th_lord_and_6th_sign"),
    ("#1083: 'the classical successful doctor / litigator pattern' is back in the lede",
     _T,
     "the \"successful doctor / litigator / union leader / HR head\" pattern that practising astrologers often describe (a reading drawn from what the 6th house signifies, not a profession list from the classical texts).",
     "the classical \"successful doctor / litigator / union leader / HR head\" pattern.",
     "test_unsourced_classical_attributions_are_labelled_as_practice"),
    ("#1083: 'Classical texts consistently recommend' confronting conflicts is back",
     _T,
     "People with 6th-house difficulties are better served confronting their conflicts than avoiding them.",
     "Classical texts consistently recommend that people with 6th-house afflictions confront their conflicts rather than avoid them.",
     "test_unsourced_classical_attributions_are_labelled_as_practice"),
    ("#1083: 'classical Vedic remedy' for hospital donations is back",
     _T,
     "is a practical way to act on the 6th house's illness meaning. It is this site's suggestion, not a remedy the classical texts prescribe for a house.",
     "is classical Vedic remedy for 6th-house afflictions.",
     "test_unsourced_classical_attributions_are_labelled_as_practice"),
    ("#1083: the registry FAQ calls the remedies 'Safe universal classical practices' again",
     _R,
     "Safe universal practices (practical advice and devotional custom, not a house-by-house classical prescription): weekly worship",
     "Safe universal classical practices: weekly worship",
     "test_registry_no_longer_calls_the_remedies_classical"),
    ("#1083: the registry summary again promises 'honest classical remedies'",
     _R,
     "Dasha timing, and honest practical remedies.",
     "Dasha timing, and honest classical remedies.",
     "test_registry_no_longer_calls_the_remedies_classical"),
]
