"""#1051: residue of #1049 -- the Jupiter-in-10th registry text (summary, FAQ, llm_summary) and the Guru Chandala bullet
label their outcome claims as practitioner reading. Held (knowledge/vedic_reference.md 4.1): only the Hamsa rule and its
effects; nothing on a debilitated-Jupiter stall, reduced benefits, or a reputation-fragile Guru Chandala career.

Each row restores one removed unlabelled claim and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_R = "src/astro_ai/learn_registry.py"
_J = "src/astro_ai/templates/learn/jupiter-in-10th-house-career.html"

MUTATIONS = [
    ("#1051: llm_summary states 'institutional recognition stalls' flat again (injected into every natal prompt)",
     _R,
     "practitioners read slower recognition (a reading, not a held rule); check Neechabhanga",
     "capable but institutional recognition stalls; check Neechabhanga",
     "test_registry_fields_state_none_of_the_flat_claims"),
    ("#1051: FAQ says the benefits 'diminish significantly' flat again",
     _R,
     "practitioners read the placement's benefits as reduced; that is a reading, not a rule the texts state.",
     "the placement's benefits diminish significantly.",
     "test_registry_fields_state_none_of_the_flat_claims"),
    ("#1051: registry summary says 'the karma-dharma path stalls' flat again",
     _R,
     "Practitioners read a debilitated or afflicted Jupiter here as a slower road; that is a reading, not a rule the texts state.",
     "When debilitated in Capricorn or afflicted, the karma-dharma path stalls.",
     "test_registry_fields_state_none_of_the_flat_claims"),
    ("#1051: Guru Chandala bullet states 'spectacular but reputation-fragile' and guru-figures flat again",
     _J,
     "Practitioners read these careers as potentially spectacular yet fragile in reputation, and the pairing as yielding guru-figures whose teachings turn out to be more complicated than they first appeared; that is a reading, not a rule the texts state.",
     "Careers can be spectacular but reputation-fragile. Many charts with this pairing produce guru-figures whose teachings turn out to be more complicated than they first appeared.",
     "test_page_and_its_faq_json_ld_state_none_of_the_flat_claims"),
    ("#1051: Guru Chandala bullet keeps the practitioner lead but drops the 'not a rule the texts state' label",
     _J,
     "turn out to be more complicated than they first appeared; that is a reading, not a rule the texts state.",
     "turn out to be more complicated than they first appeared.",
     "test_guru_chandala_bullet_is_labelled_practitioner_reading"),
    ("#1051: page intro states the compromised-Jupiter path as flatly more difficult again",
     _J,
     "practitioners read the karma-dharma path as more difficult:",
     "the karma-dharma path becomes more difficult:",
     "test_page_and_its_faq_json_ld_state_none_of_the_flat_claims"),
]
