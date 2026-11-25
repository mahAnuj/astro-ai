"""#1355: the dark-half (Krishna paksha) label on the finder's good-tithi credit, and the
avoid_tithi status ruling. Rows target src/astro_ai/muhurat_factors.py; the tests are in
tests/test_muhurat_factor_registry.py. One area file, a literal list (test_mutation_tables.py
requires it)."""

_F = "src/astro_ai/muhurat_factors.py"
_RULING2 = "test_each_second_ruling_override_resolves_to_the_auditors_status_and_sentence"
_GATE = "test_every_good_tithi_of_every_event_carries_the_rulings_krishna_label"

MUTATIONS = [
    ("#1355: the half-wide @Krishna qualifier is tried before the tithi (Dwadashi loses its own entry)",
     _F, '                         _qual("good_tithi", event, tithi,\n'
         '                               "@Krishna" if paksha == "Krishna" else "")))',
     '                         _qual("good_tithi", event, "@Krishna" if paksha == "Krishna" else "",\n'
     '                               tithi)))',
     "test_a_tithi_specific_entry_beats_the_half_wide_one_on_a_krishna_row"),
    ("#1355: griha_pravesh's dark-half credit key is renamed (the credit reads as sourced again)",
     _F, '"griha_pravesh": {"@Krishna": _vr(C, "In the dark half this credit rests on one table, "',
     '"griha_pravesh": {"@Krishna_x": _vr(C, "In the dark half this credit rests on one table, "',
     _GATE),
    ("#1355: vidyarambh's half-wide dark-half credit is removed (only Dwadashi stays contested)",
     _F, '                           "@Krishna": _vr(C, "Rao\'s table names no half;',
     '                           "@Krishna_x": _vr(C, "Rao\'s table names no half;',
     _GATE),
    ("#1355: griha_pravesh's avoid_tithi list goes back to sourced (the ruling made it contested)",
     _F, '"griha_pravesh": _vr(C, "The Muhurtha tradition rejects the 4th, 8th, 14th, New Moon "',
     '"griha_pravesh": _vr(S, "The Muhurtha tradition rejects the 4th, 8th, 14th, New Moon "',
     _RULING2),
    ("#1355: business's avoid_tithi list goes back to sourced (the ruling made it contested)",
     _F, '"business": _vr(C, "The Muhurtha tradition rejects the 4th, 8th, 14th, New Moon "',
     '"business": _vr(S, "The Muhurtha tradition rejects the 4th, 8th, 14th, New Moon "',
     "test_the_avoid_tithi_cleared_item_is_contested_for_four_events_and_sourced_for_vidyarambh"),
]
