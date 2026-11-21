"""#1346 + #1354: the Vivah and Griha Pravesh /learn articles say about Abujha dates what the finder
does (every one is `avoid` for New Delhi; Abujha is a regional custom no held book names).
tests/test_learn_abujha_claims.py. One area file, a literal list (test_mutation_tables.py requires it)."""

_V = "src/astro_ai/templates/learn/vivah-muhurat-2027.html"
_G = "src/astro_ai/templates/learn/griha-pravesh-muhurat-2026-2027.html"

MUTATIONS = [
    ("#1346: the Vivah Abujha section is 'universally auspicious days that override calculation' again",
     _V,
     "<h2>Abujha dates — a regional almanac custom, not a wedding rule</h2>",
     "<h2>Abujha Muhurats — universally auspicious days that override calculation</h2>",
     "test_neither_article_still_makes_the_retired_abujha_claims"),
    ("#1346: the Vivah lead says 'regardless of tithi' again",
     _V,
     "Some regional almanacs list \"swayam-siddha\" (self-perfected) days,",
     "Swayam-siddha days are auspicious for weddings regardless of tithi, and some regional almanacs list \"swayam-siddha\" (self-perfected) days,",
     "test_neither_article_still_makes_the_retired_abujha_claims"),
    ("#1346: the Vivah article stops saying the finder marks every 2027 Abujha date avoid",
     _V,
     "our finder marks all five 2027 Abujha dates",
     "our finder marks some 2027 Abujha dates",
     "test_the_vivah_article_calls_abujha_a_regional_custom_and_lists_no_panchak_day_as_a_wedding_date"),
    ("#1346: the Griha Pravesh mistakes list calls Devuthani the standing exception to Panchak again",
     _G,
     "and our finder does not waive it for any day, including Devuthani Ekadashi; if your family keeps a custom of entering during Panchak, ask your priest",
     "(an abujha day such as Devuthani Ekadashi is the standing exception)",
     "test_neither_article_still_makes_the_retired_abujha_claims"),
    ("#1346: the Griha Pravesh Devuthani note says Panchak does not cancel it again",
     _G,
     "and our finder does not waive Panchak for it.",
     "and it is auspicious without being cancelled by Panchak.",
     "test_neither_article_still_makes_the_retired_abujha_claims"),
    ("#1346: the Griha Pravesh Devuthani 2026 bullet is rated excellent again",
     _G,
     "and our finder rates it <strong>avoid</strong>; see the note below the list.",
     "and our finder rates it excellent; see the note below the list.",
     "test_the_griha_pravesh_article_says_devuthani_2026_is_avoid_and_panchak_is_not_waived"),
]
