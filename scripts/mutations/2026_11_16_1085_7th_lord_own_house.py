"""#1085: the 7th-lord guide stops calling own-house the strongest placement.

Own sign is not the top of the dignity ladder (grahas.md 8.1 ranks exaltation as peak expression), and
no knowledge/*.md line says the 7th lord is strongest in the 7th. The claim lived in two copies (the
template and the registry FAQ that renders into the JSON-LD), so each gets a row.
Each row restores one removed claim and names the test that must go red."""

_T = "src/astro_ai/templates/learn/7th-lord-placement-marriage-guide.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#1085: the template intro again calls 7th-lord-in-7th 'the strongest possible placement'",
     _T,
     "is a strong placement, because own sign and a kendra (the 7th is one) both read as strength, and it is one of the most commonly praised marriage signatures in practice (the praise is practitioners' habit, not a rule the sources we hold state):</p>",
     "is the strongest possible placement for the 7th lord and one of the most commonly praised marriage signatures:</p>",
     "test_page_says_a_strong_placement_not_the_strongest_or_full_dignity"),
    ("#1085: the template 'Own house strength' bullet again says 'operates at full dignity'",
     _T,
     "<strong>Own sign, in a kendra.</strong> A planet in its own sign is at home: comfortable, natural and functional (exaltation sits above it, as peak positive expression). The 7th is also a kendra, a house where planets get power. The 7th lord in the 7th means marriage functions as a central life anchor with steady support.",
     "<strong>Own house strength.</strong> A planet in its own house operates at full dignity. The 7th lord in the 7th means marriage functions as a central life anchor with full karmic support.",
     "test_page_says_a_strong_placement_not_the_strongest_or_full_dignity"),
    ("#1085: the registry FAQ (JSON-LD) again says 'the strongest possible placement for the 7th lord'",
     _R,
     "is a strong placement, because own sign and a kendra (the 7th is one) both read as strength; exaltation, elsewhere in the chart, ranks above own sign. It is one of the most commonly praised marriage signatures in practice, though that praise is practitioners' habit, not a rule the sources we hold state. Marriage",
     "is the strongest possible placement for the 7th lord and one of the most commonly praised marriage signatures. Marriage",
     "test_registry_faq_says_a_strong_placement_not_the_strongest_or_full_dignity"),
]
