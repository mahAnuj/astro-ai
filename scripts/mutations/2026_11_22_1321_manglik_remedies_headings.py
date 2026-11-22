"""#1321: the manglik-remedies headings and the Manglik-Manglik FAQ stop claiming a classical ranking.

Each row restores the old wording on one surface and names the test that must go red."""

_T = "src/astro_ai/templates/learn/manglik-remedies.html"

MUTATIONS = [
    ("#1321: manglik-remedies h2 1 calls Hanuman Mars's presiding deity again",
     _T,
     "<h2>1. Hanuman worship — first of Mars's deities in a modern table</h2>",
     "<h2>1. Hanuman worship — Mars's presiding deity</h2>",
     "test_headings_do_not_claim_a_classical_ranking"),
    ("#1321: manglik-remedies toor daal item calls it Mars's classical grain again",
     _T,
     "— the grain a modern textbook's table gives Mars</li>",
     "— Mars's classical grain</li>",
     "test_headings_do_not_claim_a_classical_ranking"),
    ("#1321: manglik-remedies h2 6 calls matching the truest remedy again",
     _T,
     "<h2>6. Marriage matching — the one remedy a held source states</h2>",
     "<h2>6. Marriage matching — the truest Manglik remedy</h2>",
     "test_headings_do_not_claim_a_classical_ranking"),
    ("#1321: manglik-remedies section 6 attributes the comparable threshold to tradition again",
     _T,
     'Many retellings say "comparable" and leave the threshold open; we have not found that condition in a book we hold, so we set one and name it as ours:',
     'Tradition also says "comparable" and leaves the threshold open, so we set one and name it as ours:',
     "test_section_6_does_not_attribute_the_threshold_to_tradition"),
    ("#1321: manglik-remedies FAQ 4 attributes the severity condition to the held list again",
     "src/astro_ai/learn_registry.py",
     "One held antidote list says that when both partners are Manglik the dosha is cancelled; it names no severity condition.",
     "One held antidote list says Manglik-Manglik matching cancels the dosha, with one condition that most retellings drop: the two doshas must be of comparable severity.",
     "test_faq4_does_not_attribute_the_severity_condition_to_the_held_list"),
]
