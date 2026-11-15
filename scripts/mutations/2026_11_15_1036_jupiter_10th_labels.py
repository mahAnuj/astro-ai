"""#1036: the Jupiter-in-10th guide labels career and marriage readings as practitioner reading instead of citing
'classical' or a bare superlative. Held (knowledge/vedic_reference.md 4.1): Hamsa = Jupiter in Sg/Pi/Cn in a kendra,
effects wisdom, respect, dharma, scholarly fame; nothing on marriage in a Jupiter Mahadasha or on career signatures.

Each row restores one removed unlabelled claim and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_J = "src/astro_ai/templates/learn/jupiter-in-10th-house-career.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#1036: page says Jupiter in the 10th is 'one of the classical configurations' again",
     _J,
     "is one of the four kendra placements that can form it.",
     "is one of the classical configurations that forms it.",
     "test_page_states_none_of_the_unsourced_claims"),
    ("#1036: page says '(classically) marriage' in the Jupiter Mahadasha again",
     _J,
     "and, in some practitioners' readings, marriage during this period if not already married (the sources we hold do not state this).",
     "and often (classically) marriage during this period if not already married.",
     "test_page_states_none_of_the_unsourced_claims"),
    ("#1036: page calls the Libra-ascendant careers 'common signatures' again",
     _J,
     "Practitioners read careers in judiciary, senior academia, international law, and dharmic institution-building as the usual expression; that is a reading of the yoga's themes, not a rule the texts state.",
     "Careers in judiciary, senior academia, international law, and dharmic institution-building are common signatures.",
     "test_page_states_none_of_the_unsourced_claims"),
    ("#1036: registry FAQ (and its JSON-LD) says 'most fortunate career placements' unlabelled again",
     _R,
     "Practitioners read Jupiter in the 10th as one of the most favourable career placements when Jupiter is dignified",
     "Jupiter in the 10th is one of the most fortunate career placements when Jupiter is dignified",
     "test_registry_entry_states_none_of_the_unsourced_claims"),
    ("#1036: registry Hamsa FAQ says the career fields 'are common signatures' again",
     _R,
     "Practitioners read the 10th house version as especially career-active, with teaching, judiciary, advisory, spiritual leadership, and publishing as the usual expression; that is a reading of the yoga's themes, not a rule the texts state.",
     "The 10th house version is especially career-active — teaching, judiciary, advisory, spiritual leadership, and publishing are common signatures.",
     "test_registry_entry_states_none_of_the_unsourced_claims"),
]
