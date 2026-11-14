"""#980: the second-marriage guide stops calling 7th lord in the 8th 'the strongest signature in classical texts'.

Each row restores one removed claim and names the test that must go red."""

_T = "src/astro_ai/templates/learn/second-marriage-yoga-kundli.html"
_R = "src/astro_ai/learn_registry.py"

MUTATIONS = [
    ("#980: 7th lord in the 8th is again 'the strongest second-marriage signature in classical texts'",
     _T,
     "commonly named by practitioners as one of the stronger second-marriage signatures. We cannot source that to the texts we hold, and we have not measured it.",
     "the strongest second-marriage signature in classical texts.",
     "test_7th_lord_in_8th_is_no_longer_the_strongest_signature_in_classical_texts"),
    ("#980: the 'we cannot source that' disclosure is dropped from the 7th-lord-in-8th bullet",
     _T,
     "We cannot source that to the texts we hold, and we have not measured it.",
     "It is widely observed.",
     "test_7th_lord_in_8th_says_it_is_practitioner_usage_we_cannot_source"),
    ("#980: the registry FAQ says '8th is the strongest single signature' again",
     _R,
     "practitioners most often single out the 8th, though we cannot source that ranking to the texts we hold;",
     "8th is the strongest single signature;",
     "test_registry_fields_do_not_carry_the_strongest_8th_claim"),
    ("#980: the llm_summary (natal prompt) says '8 strongest' again",
     _R,
     "(6/8/12; any ranking among them is unsourced)",
     "(6/8/12 — 8 strongest)",
     "test_registry_fields_do_not_carry_the_strongest_8th_claim"),
]
