"""#1075: the Rahu Mahadasha + Ketu Antardasha guide names the 'effects' and 'remedies' intents in headings.

Each row re-breaks one property of that change (the heading words, the practitioner-reading label, an effects line that
is no longer a sentence the page already makes, a bullet added without the page-level check, the remedies heading) and
names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list (see `verify_no_relaxation.py`)."""

_T = "src/astro_ai/templates/learn/rahu-mahadasha-ketu-antardasha.html"

MUTATIONS = [
    ("#1075: the effects heading no longer says 'effects'",
     _T,
     "<h2>Effects of Rahu Mahadasha + Ketu Antardasha: what happens, at a glance</h2>",
     "<h2>At a glance: Rahu Mahadasha + Ketu Antardasha</h2>",
     "test_an_effects_heading_names_the_intent_and_sits_near_the_top"),
    ("#1075: the effects block loses its practitioner-reading label",
     _T,
     "and all of it is how practitioners commonly describe the period, not something the sources we hold state:",
     "and all of it is established:",
     "test_effects_block_is_labelled_practitioner_reading_and_adds_no_source_claim"),
    ("#1075: an effects line is reworded into a claim the page does not make",
     _T,
     "relationships may end, and separation is part of the usual description.",
     "marriages will end within the first six months, and separation is certain.",
     "test_every_effects_line_restates_a_sentence_the_page_already_makes"),
    ("#1075: an effects line is dropped from the block",
     _T,
     "<li><strong>Place:</strong> foreign environments can turn unwelcoming, and sudden direction changes often follow.</li>\n",
     "",
     "test_effects_block_carries_exactly_the_seven_areas_and_no_other_bullet"),
    ("#1075: a new unsourced bullet is added to the effects block",
     _T,
     "  <li><strong>How long:</strong>",
     "  <li><strong>Health:</strong> the body weakens and surgery is likely.</li>\n  <li><strong>How long:</strong>",
     "test_effects_block_carries_exactly_the_seven_areas_and_no_other_bullet"),
    ("#1075: a remedy is smuggled into the effects block",
     _T,
     "Identities loosen.</li>",
     "Identities loosen. Wear a cat's eye to stop it.</li>",
     "test_effects_block_is_labelled_practitioner_reading_and_adds_no_source_claim"),
    ("#1075: the remedies heading is 'Remedies for surviving ...' again",
     _T,
     "<h2>Remedies for Rahu Mahadasha + Ketu Antardasha</h2>",
     "<h2>Remedies for surviving Rahu Mahadasha + Ketu Antardasha</h2>",
     "test_remedies_heading_uses_the_searchers_words_and_the_sourced_split_is_intact"),
    ("#1075: the effects block is moved above the sourced-versus-practice disclosure",
     _T,
     '<div class="callout callout-classic">\n  <div class="callout-label">What is sourced and what is practice</div>',
     '<h2>Effects of Rahu Mahadasha + Ketu Antardasha: what happens, at a glance</h2>\n<div class="callout callout-classic">\n  <div class="callout-label">What is sourced and what is practice</div>',
     "test_an_effects_heading_names_the_intent_and_sits_near_the_top"),
]
