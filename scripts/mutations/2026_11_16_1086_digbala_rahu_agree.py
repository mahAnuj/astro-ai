"""#1086: knowledge/ agrees with itself on Saturn's digbala (7th house, Rao Integrated Approach 3.2.15) and Rahu's
exaltation (Gemini first, CONTESTED), and no page repeats the losing side.

Each row restores one removed claim verbatim (taken from the pre-fix text) and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

MUTATIONS = [
    (
        '#1086: houses.md calls Saturn in the 10th his Digbala again',
        'src/astro_ai/knowledge/houses.md',
        '- **Saturn in 10th = long career',
        '- **Saturn in 10th (Digbala) = long career',
        'test_grahas_and_houses_both_put_saturns_digbala_in_the_7th',
    ),
    (
        "#1086: houses.md drops the note that the 10th is not Saturn's Digbala",
        'src/astro_ai/knowledge/houses.md',
        "Saturn's Digbala: Saturn is strong in the 7th",
        "Saturn's strength: Saturn is strong in the 7th",
        'test_houses_tenth_house_note_says_it_is_not_saturns_digbala',
    ),
    (
        "#1086: rashis.md leads Rahu's exaltation with Taurus again",
        'src/astro_ai/knowledge/rashis.md',
        '| Rahu | Gemini (CONTESTED: some say Taurus) | Sagittarius (CONTESTED: some say Scorpio) |',
        '| Rahu | Taurus (some say Gemini) | Scorpio (some say Sagittarius) |',
        'test_rahu_and_ketu_exaltation_rows_agree_across_grahas_and_rashis',
    ),
    (
        "#1086: grahas.md drops the CONTESTED mark from Rahu's dignity row",
        'src/astro_ai/knowledge/grahas.md',
        '| Rahu | Aquarius | Gemini (CONTESTED: some say Taurus) | Sagittarius (CONTESTED: some say Scorpio) | Virgo |',
        '| Rahu | Aquarius | Gemini (some say Taurus) | Sagittarius (some say Scorpio) | Virgo |',
        'test_rahu_and_ketu_exaltation_rows_agree_across_grahas_and_rashis',
    ),
    (
        "#1086: grahas.md drops Raman's Taurus 20 / Scorpio 20 reckoning and calls the Taurus side unsourced again",
        'src/astro_ai/knowledge/grahas.md',
        'respectively" and puts debilitation 180° opposite',
        'respectively" and not a sourced one; debilitation 180° opposite',
        'test_grahas_records_that_two_held_books_disagree_on_rahu_and_ketu',
    ),
    (
        "#1086: saturn-in-10th intro calls the 10th Saturn's digbala again",
        'src/astro_ai/templates/learn/saturn-in-10th-house-career.html',
        "But <strong>the sources we hold do not put Saturn's <em>digbala</em> (directional strength) in the 10th</strong>: they give it to the 7th house, so this page does not call the 10th his strong house. Practitioners commonly read Saturn in the 10th as delay-then-elevation rather than permanent blockage — a reading from practice, not a rule those sources state.",
        'But <strong>Saturn in the 10th is also his <em>digbala</em> — his directional strength</strong> — and classical Vedic tradition places this among the most enduring career placements. The pattern is delay-then-elevation, not permanent blockage.',
        'test_no_learn_template_ties_saturn_digbala_to_the_10th',
    ),
    (
        '#1086: saturn-in-10th body says classical teaching gives Saturn digbala in the 10th again',
        'src/astro_ai/templates/learn/saturn-in-10th-house-career.html',
        "A note on directional strength, because it is often misstated: the sources we hold place Saturn's <em>digbala</em> (directional strength) in the 7th house (the west), and give the 10th to the Sun and Mars.",
        'Classical Vedic teaching gives Saturn <em>digbala</em> (directional strength) specifically in the 10th house.',
        'test_no_learn_template_ties_saturn_digbala_to_the_10th',
    ),
    (
        '#1086: career-not-progressing calls Saturn in the 10th (Digbala) again',
        'src/astro_ai/templates/learn/career-not-progressing.html',
        "Saturn in the 10th is commonly read as good for career in the long run — durable, structured, often institutional careers that build over decades (a reading from practice; Saturn's own directional strength, digbala, is in the 7th house, not the 10th).",
        'Saturn in the 10th (Digbala) is actually good for career — it gives durable, structured, often institutional careers that build over decades.',
        'test_no_learn_template_ties_saturn_digbala_to_the_10th',
    ),
    (
        '#1086: registry career FAQ calls Saturn in the 10th (Digbala) again',
        'src/astro_ai/learn_registry.py',
        "Saturn in the 10th house is commonly read as good for career in the long run — durable, structured, institutional careers that build over decades (a reading from practice; Saturn's directional strength, digbala, is in the 7th house, not the 10th).",
        'Saturn in the 10th house (Digbala) is actually good for career — it gives durable, structured, institutional careers that build over decades.',
        'test_no_registry_field_ties_saturn_digbala_to_the_10th',
    ),
    (
        '#1086: registry saturn-in-10th summary calls it his digbala again',
        'src/astro_ai/learn_registry.py',
        'It is not his digbala house (the sources we hold give Saturn that strength in the 7th)',
        'It is his digbala — his strongest directional placement',
        'test_saturn_10th_registry_entry_states_the_digbala_is_in_the_7th',
    ),
    (
        "#1086: registry saturn-in-10th FAQ says it is Saturn's digbala again",
        'src/astro_ai/learn_registry.py',
        "It is not Saturn's digbala house, though: the sources we hold give Saturn his directional strength in the 7th",
        "It is Saturn's digbala (directional strength)",
        'test_no_registry_field_ties_saturn_digbala_to_the_10th',
    ),
    (
        '#1086: registry saturn-in-10th llm_summary says the strongest classical placement again',
        'src/astro_ai/learn_registry.py',
        "• Saturn in 10th = NOT his digbala house (Saturn's directional strength is in the 7th); commonly read as delay-then-elevation, a reading from practice rather than a classical rule\\n",
        "• Saturn in 10th = Saturn's digbala (directional strength) — one of the STRONGEST classical career placements\\n",
        'test_saturn_10th_registry_entry_states_the_digbala_is_in_the_7th',
    ),
    (
        "#1086: the-9-grahas-overview leads Rahu's exaltation with Taurus again",
        'src/astro_ai/templates/learn/the-9-grahas-overview.html',
        '<strong>Exalted in:</strong> Gemini (some say Taurus) &middot; <strong>Debilitated in:</strong> Sagittarius (some say Scorpio)',
        '<strong>Exalted in:</strong> Taurus (some say Gemini) &middot; <strong>Debilitated in:</strong> Scorpio (some say Sagittarius)',
        'test_rahu_pages_lead_with_gemini_and_say_the_texts_disagree',
    ),
    (
        '#1086: kaal-sarp-dosh calls Gemini the exaltation sign and Taurus an extra again',
        'src/astro_ai/templates/learn/kaal-sarp-dosh.html',
        'Gemini, its exaltation sign on the reckoning we follow, though some texts say Taurus)',
        'Gemini, its exaltation sign, or Taurus on some reckonings)',
        'test_rahu_pages_lead_with_gemini_and_say_the_texts_disagree',
    ),
    (
        '#1086 QA: a learn page says Rahu is exalted in Taurus with no hedge again',
        'src/astro_ai/templates/learn/rahu-mahadasha-career-problems.html',
        'His exaltation is Gemini (some say Taurus) — the texts disagree on this, so treat it as contested.',
        'Rahu is exalted in Taurus.',
        'test_no_page_or_registry_field_states_rahu_exalted_in_taurus_unhedged',
    ),
]
