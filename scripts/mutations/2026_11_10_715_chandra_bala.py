"""#715: Chandra Bala grades the Moon's house in two grades from the held Gochara table
(knowledge/vedic_reference.md 2A), and the Vivah couple verdict passes only "strong"."""

_VERDICT = '    verdict = "strong" if house in _CHANDRA_BALA_STRONG else "weak"\n'

MUTATIONS = [
    ("#715: houses 2, 5 and 9 fall back to a third 'neutral' grade",
     "src/astro_ai/muhurat.py",
     _VERDICT,
     '    verdict = ("strong" if house in _CHANDRA_BALA_STRONG else\n'
     '               "weak" if house in {4, 8, 12} else "neutral")\n',
     "test_each_house_takes_its_verdict_from_the_gochara_table"),
    ("#715: the weak set shrinks back to {4, 8, 12} (import-time partition check goes red)",
     "src/astro_ai/muhurat.py",
     "_CHANDRA_BALA_WEAK   = {2, 4, 5, 8, 9, 12}\n",
     "_CHANDRA_BALA_WEAK   = {4, 8, 12}\n",
     "test_the_two_sets_cover_all_twelve_houses_exactly_once"),
    ("#715: a strong house is moved into the weak table, as in a table typo",
     "src/astro_ai/muhurat.py",
     _VERDICT,
     '    verdict = "strong" if house in (_CHANDRA_BALA_STRONG - {6}) else "weak"\n',
     "test_each_house_takes_its_verdict_from_the_gochara_table"),
    ("#715: the couple verdict lets a neutral bride grade pass again",
     "src/astro_ai/muhurat.py",
     '    b_chandra_ok = bride.chandra_bala == "strong"\n',
     '    b_chandra_ok = bride.chandra_bala in ("strong", "neutral")\n',
     "test_the_couple_verdict_does_not_read_a_neutral_grade_as_a_pass"),
    ("#715: the couple verdict lets a neutral groom grade pass again",
     "src/astro_ai/muhurat.py",
     '    g_chandra_ok = groom.chandra_bala == "strong"\n',
     '    g_chandra_ok = groom.chandra_bala in ("strong", "neutral")\n',
     "test_the_couple_verdict_does_not_read_a_neutral_grade_as_a_pass"),
    ("#715: the finder's Chandra Bala disclosure names no source again",
     "src/astro_ai/templates/muhurat_finder.html",
     "counted from the natal Moon using Raman's Gochara table",
     "counted from the natal Moon using classical tables",
     "test_the_finder_states_the_source_of_the_chandra_grade"),
    ("#715: the disclosure is shown only for personal matching, not for the couple view",
     "src/astro_ai/templates/muhurat_finder.html",
     "{% if personal_active or couple_active %}\n      {#- #715",
     "{% if personal_active %}\n      {#- #715",
     "test_the_finder_states_the_source_of_the_chandra_grade"),
]
