"""#1062: the Namkaran first-letter table cites Raman's printed one, the finder page no longer
credits Muhurta Chintamani, and a Shravana child is shown both circulating sets.
tests/test_namkaran_letter_table.py.

No row for the muhurat.py "no book carries this table" comment: the harness refuses an anchor on a
comment line (it changes no behaviour), so that text is guarded by the test alone."""

_M = "src/astro_ai/muhurat.py"
_R = "src/astro_ai/routes/muhurat.py"
_F = "src/astro_ai/templates/muhurat_finder.html"
_V = "src/astro_ai/knowledge/vedic_reference.md"

MUTATIONS = [
    ("#1062: the finder page credits the syllable to Muhurta Chintamani again",
     _F, "This finder's list gives <strong>{{ child_first_letter }}</strong> for that pada.",
     "Per Muhurta Chintamani, that pada's assigned syllable is <strong>{{ child_first_letter }}</strong>.",
     "test_the_template_no_longer_credits_muhurta_chintamani"),
    ("#1062: the route stops passing the alternate set, so Shravana shows one set again",
     _R, "child_alternate_letters = _muhurat._namkaran_alternate_letters(child_nakshatra)",
     "child_alternate_letters = ()",
     "test_a_shravana_child_is_shown_both_sets_and_the_convention"),
    ("#1062: every nakshatra gets an alternate set, not only Shravana",
     _M, '    "Shravana": ("Ju", "Je", "Jo", "Gha"),\n}',
     '    "Shravana": ("Ju", "Je", "Jo", "Gha"),\n    "Bharani": ("Li", "Lu", "Le", "Lo"),\n}',
     "test_only_shravana_has_an_alternate_set"),
    ("#1062: the alternate paragraph renders for every child, with an empty set",
     _F, "{% if child_alternate_letters %}", "{% if child_nakshatra %}",
     "test_a_child_in_another_nakshatra_is_not_shown_an_alternate_set"),
    ("#1062: the alternate Shravana set carries Raman's raw 'Jay' instead of our 'Je'",
     _M, '"Shravana": ("Ju", "Je", "Jo", "Gha"),', '"Shravana": ("Ju", "Jay", "Jo", "Gha"),',
     "test_shravana_is_a_different_set_not_a_different_spelling"),
    ("#1062: the reference section's agreeing-row count drifts from the pinned verdicts",
     _V, "Purva Bhadrapada, Revati (18 of 27).", "Purva Bhadrapada, Revati (17 of 27).",
     "test_the_verdict_counts_are_the_ones_the_reference_section_states"),
]
