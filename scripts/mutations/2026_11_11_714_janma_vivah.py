"""#714, last slice: in the Vivah couple verdict a GROOM on his own Janma day is a Tara avoid
(Raman, Muhurtha: the 1st star is in the avoid list and marriage is inauspicious on it), a BRIDE on
hers still passes ("quite favourable for a woman"), and the finder says so, with the caveat that
it reads whole-day nakshatra and so does not apply the book's urgent-case ghati exception. The
self-contradictory "nuptials ... favourable without exception" sentence is not used."""

_GROOM_RULE = ('    g_tara = "avoid" if groom.tara_bala_name == _JANMA_TARA_NAME else groom.tara_bala\n')
_CAVEAT = ("This finder reads the whole-day nakshatra, so it does not apply the exception Raman "
           "allows only in urgent cases, where just the opening ghatis of that star are avoided. ")

MUTATIONS = [
    ("#714: the groom-Janma downgrade is removed (his own star day reads good-for-both again)",
     "src/astro_ai/muhurat.py",
     _GROOM_RULE,
     "    g_tara = groom.tara_bala\n",
     "test_groom_janma_with_a_passing_bride_is_mixed_never_good_for_both"),
    ("#714: the downgrade is applied to the bride as well (her own star day stops passing)",
     "src/astro_ai/muhurat.py",
     '    b_tara_ok = bride.tara_bala in ("excellent", "good", "ok")\n',
     '    b_tara_ok = (bride.tara_bala_name != _JANMA_TARA_NAME\n'
     '                 and bride.tara_bala in ("excellent", "good", "ok"))\n',
     "test_bride_janma_with_a_good_groom_is_unchanged_good_for_both"),
    ("#714: groom Janma is avoid on its own, whatever the bride's day (the 'both avoid' rule is bypassed)",
     "src/astro_ai/muhurat.py",
     '    both_tara_avoid = (bride.tara_bala == "avoid" and g_tara == "avoid")\n',
     '    both_tara_avoid = (bride.tara_bala == "avoid" and g_tara == "avoid"\n'
     '                       ) or groom.tara_bala_name == _JANMA_TARA_NAME\n',
     "test_groom_janma_with_a_passing_bride_is_mixed_never_good_for_both"),
    ("#714: the downgrade moves into _tara_bala, so every Janma chip and the personal match turn avoid",
     "src/astro_ai/muhurat.py",
     "    name, verdict = _TARA_BALA_NAMES.get(position, (\"\", \"\"))\n    return position, name, verdict\n",
     "    name, verdict = _TARA_BALA_NAMES.get(position, (\"\", \"\"))\n"
     "    if name == _JANMA_TARA_NAME:\n        verdict = \"avoid\"\n    return position, name, verdict\n",
     "test_tara_bala_still_grades_own_star_ok"),
    ("#714: the partner factors lose the Tara NAME, so the groom rule can never fire in the real search",
     "src/astro_ai/muhurat.py",
     "        tara_bala=t_verdict, tara_bala_name=t_name,\n        chandra_bala=c_verdict,\n"
     "        manglik_status=manglik_status,",
     "        tara_bala=t_verdict, tara_bala_name=\"\",\n        chandra_bala=c_verdict,\n"
     "        manglik_status=manglik_status,",
     "test_the_real_search_marks_a_groom_janma_day_mixed_not_good_for_both"),
    ("#714: the finder drops the whole-day / urgent-case ghati caveat",
     "src/astro_ai/templates/muhurat_finder.html",
     _CAVEAT,
     "",
     "test_the_finder_paragraph_states_the_groom_bride_split_and_the_ghati_caveat"),
    ("#714: the finder cites the self-contradictory 'nuptials ... without exception' sentence",
     "src/astro_ai/templates/muhurat_finder.html",
     'The same passage is unclear on "nuptials", so that sentence is not used. ',
     "Raman also lists nuptials as favourable without exception. ",
     "test_the_janma_note_names_one_book_and_does_not_lean_on_the_nuptials_sentence"),
    ("#714: the knowledge section says the nuptials sentence CAN be cited for a wedding",
     "src/astro_ai/knowledge/vedic_reference.md",
     "**line 1083 cannot be cited for the Vivah (wedding) day**",
     "**line 1083 can be cited for the Vivah (wedding) day**",
     "test_the_knowledge_section_exists_and_quotes_what_the_book_says"),
    ("#714: the knowledge section's bride quote is altered (the contrast it carries is lost)",
     "src/astro_ai/knowledge/vedic_reference.md",
     '> "For a woman, Janma Nakshatra would be quite favourable for marriage."',
     '> "For a woman, Janma Nakshatra would be favourable for marriage."',
     "test_the_knowledge_section_exists_and_quotes_what_the_book_says"),
]
