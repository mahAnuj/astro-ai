"""#1049: the Jupiter-in-10th guide labels its debilitated / combust / Saturn outcome bullets as practitioner reading and
gives no age window. Held (knowledge/vedic_reference.md 4.1): only the Hamsa rule and its effects (wisdom, respect,
dharma, scholarly fame); nothing on these three outcomes or on an age.

Each row restores one removed unlabelled claim and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_J = "src/astro_ai/templates/learn/jupiter-in-10th-house-career.html"

MUTATIONS = [
    ("#1049: debilitated Jupiter bullet states the career stall flat again",
     _J,
     "practitioners read this as a person of real depth whose career is slow to be recognised — sound advice that institutions are slow to reward with title or income; that is a reading, not a rule the texts state.",
     "this can produce a person of genuine wisdom whose career keeps stalling — the advice is sound, but institutions do not confer the title, and the income never quite matches the depth.",
     "test_page_states_none_of_the_flat_difficult_placement_claims"),
    ("#1049: combust Jupiter bullet states the overshadowed-second-in-command pattern flat again",
     _J,
     "Practitioners read this as a wise person overshadowed by a more visible authority figure — a competent second-in-command whose ideas are used but not credited; that is a reading, not a rule the texts state.",
     "Careers under this configuration often show the pattern of a wise person overshadowed by a more visible authority figure — a competent second-in-command whose ideas are used but not credited.",
     "test_each_outcome_bullet_is_labelled_practitioner_reading"),
    ("#1049: Jupiter-with-Saturn bullet states the late bloom and the unsourced age 35-40 flat again",
     _J,
     "Practitioners read this pairing as a career that moves slowly early on (Saturn dominant) and later blooms into deep respected work (Jupiter's expansion catching up); that is a reading, not a rule the texts state, and we give no age for it.",
     "Careers under this pairing often move very slowly early on (Saturn dominant), then late-blooming into deep respected work (Jupiter's expansion finally catching up). The turning point is often around age 35-40.",
     "test_weak_block_gives_no_age_window"),
    ("#1049: age window returns inside an otherwise labelled Saturn bullet",
     _J,
     "that is a reading, not a rule the texts state, and we give no age for it.",
     "that is a reading, not a rule the texts state; the turning point is around age 35-40.",
     "test_weak_block_gives_no_age_window"),
]
