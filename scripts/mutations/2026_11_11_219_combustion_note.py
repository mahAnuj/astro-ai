"""#219: the finder states how it judges combustion; the sentence is pinned to the code."""

_NOTE = '<strong>Combustion (asta):</strong> this finder calls'
_T = "src/astro_ai/templates/muhurat_finder.html"

MUTATIONS = [
    ("#219: the combustion disclosure paragraph is deleted",
     _T, _NOTE, '<strong>Combustion (removed):</strong> this finder calls',
     "test_the_note_states_the_orbs_the_code_uses"),
    ("#219: the note's Guru orb drifts from chart.COMBUSTION_ORBS",
     _T, "Guru 11°, Shukra 10°", "Guru 12°, Shukra 10°",
     "test_the_note_states_the_orbs_the_code_uses"),
    ("#219: the note stops naming which events check which planet",
     _T, "Guru for Vivah, Griha Pravesh and Vidyarambh; Shukra for Vivah;",
     "Guru and Shukra for every event;",
     "test_the_note_names_exactly_the_events_that_check_each_planet"),
    ("#219: Namkaran starts checking Guru combustion while the page says it checks none",
     "src/astro_ai/muhurat.py",
     '        "check_jupiter_combust": False,\n        "check_venus_combust":   False,\n        "check_mercury_combust": False,\n    },\n    "vidyarambh": {',
     '        "check_jupiter_combust": True,\n        "check_venus_combust":   False,\n        "check_mercury_combust": False,\n    },\n    "vidyarambh": {',
     "test_namkaran_still_waives_every_combustion_check"),
    ("#219: the note is reworded to claim what another text's method is",
     _T, "and it knows only", "and, unlike Muhurta Chintamani's heliacal method, it knows only",
     "test_the_note_claims_nothing_about_any_other_texts_method"),
    ("#219: the 'own extension' admission for Business Mercury is dropped",
     _T, "that is this finder's own extension, not a rule we source.",
     "that is the standard rule.",
     "test_the_note_discloses_the_model_and_the_extension"),
]
