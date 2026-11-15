"""#1045: the Jupiter-in-10th guide's per-ascendant bullets label their career lists as practitioner reading, as the
Libra bullet already did (#1036). Held (knowledge/vedic_reference.md 4.1): Hamsa = Jupiter in Sg/Pi/Cn in a kendra,
effects wisdom, respect, dharma, scholarly fame; the held text carries no career lists per ascendant.

Each row restores one removed unlabelled career signature and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_J = "src/astro_ai/templates/learn/jupiter-in-10th-house-career.html"

MUTATIONS = [
    ("#1045: Pisces-ascendant careers stated flat ('are common') again",
     _J,
     "Practitioners read careers in teaching, philosophy, publishing, spiritual leadership, and religious scholarship as the usual expression; that is a reading of the yoga's themes, not a rule the texts state. In that reading, the Pisces intuition combined with the Sagittarius career expression gives a \"wise counsel\" figure.",
     "Careers in teaching, philosophy, publishing, spiritual leadership, and religious scholarship are common. The Pisces intuition combined with the Sagittarius career expression produces the classic \"wise counsel\" figure.",
     "test_page_states_none_of_the_unsourced_claims"),
    ("#1045: Gemini-ascendant careers stated flat ('often combine') again",
     _J,
     "Practitioners read careers here as combining communication with wisdom: teaching, editorial work, jurisprudence, and philosophical writing; that is a reading, not a rule the texts state.",
     "Careers here often combine communication with wisdom: teaching, editorial work, jurisprudence, and philosophical writing.",
     "test_page_states_none_of_the_unsourced_claims"),
    ("#1045: Aries-ascendant career stated flat ('often requires proving') again",
     _J,
     "Practitioners read this as a career that must prove its expertise repeatedly rather than being conferred authority; that is a reading, not a rule the texts state.",
     "Career often requires proving expertise repeatedly rather than being conferred authority.",
     "test_page_states_none_of_the_unsourced_claims"),
    ("#1045: Virgo/Sagittarius-ascendant careers stated flat ('often lean toward') again",
     _J,
     "Practitioners read careers here as leaning toward Mercury-Jupiter hybrid fields — technical writing, editorial work, financial advisory, or teaching in analytical fields; that is a reading, not a rule the texts state.",
     "Careers often lean toward Mercury-Jupiter hybrid fields — technical writing, editorial work, financial advisory, or teaching in analytical fields.",
     "test_page_states_none_of_the_unsourced_claims"),
    ("#1045: Cancer-ascendant careers stated flat (a phrase no scan lists) -- the label test must catch it",
     _J,
     "Practitioners read careers here as combining wisdom with visible leadership — teaching that becomes institutional headship, advisory that becomes formal authority; that is a reading, not a rule the texts state.",
     "Careers here combine wisdom with visible leadership — teaching that becomes institutional headship, advisory that becomes formal authority.",
     "test_1045_every_per_ascendant_bullet_that_names_careers_is_labelled_a_reading"),
]
