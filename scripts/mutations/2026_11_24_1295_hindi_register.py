"""#1295: the Hindi suffix said "Use Sanskrit Vedic terms naturally" while rashifal_single.txt said
"not Sanskrit-heavy". tests/test_hindi_register_suffix.py."""

MUTATIONS = [
    ("#1295: the Hindi suffix licenses Sanskrit Vedic terms naturally again, against the rashifal prompt",
     "src/astro_ai/llm.py",
     "Use everyday spoken Hindi; keep common Vedic terms: ",
     "Use Sanskrit Vedic terms naturally: ",
     "test_hindi_rashifal_prompt_does_not_license_sanskrit_beside_its_own_ban"),
]
