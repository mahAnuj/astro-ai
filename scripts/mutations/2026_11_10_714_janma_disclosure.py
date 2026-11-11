"""#714: the finder discloses how Janma (Tara position 1) is graded, cites no text for it,
and the grade itself is pinned so a change is a deliberate, sourced act."""

_NOTE = '<strong>Tara Bala, Janma:</strong> on a day when'

MUTATIONS = [
    ("#714: the Janma disclosure paragraph is deleted",
     "src/astro_ai/templates/muhurat_finder.html",
     _NOTE,
     '<strong>Tara Bala, Janma (removed):</strong> on a day when',
     "test_the_finder_discloses_how_janma_is_graded"),
    ("#714: the disclosure is reworded to cite Raman for a rule no held text carries",
     "src/astro_ai/templates/muhurat_finder.html",
     "are not sourced to a text this site holds.</p>",
     "follow Raman's Muhurtha, which treats Janma as variable.</p>",
     "test_the_janma_note_claims_nothing_about_what_any_text_says"),
    ("#714: Janma is quietly flipped to 'avoid' while the page still says 'ok'",
     "src/astro_ai/muhurat.py",
     '    1: ("Janma",     "ok"),',
     '    1: ("Janma",     "avoid"),',
     "test_janma_is_still_graded_ok"),
    ("#714: the couple verdict stops passing 'ok', so a Janma day silently demotes",
     "src/astro_ai/muhurat.py",
     '    g_tara_ok = groom.tara_bala in ("excellent", "good", "ok")\n',
     '    g_tara_ok = groom.tara_bala in ("excellent", "good")\n',
     "test_a_groom_on_his_own_janma_still_passes_the_couple_verdict"),
    ("#714: the disclosure shows when no Tara grade is displayed",
     "src/astro_ai/templates/muhurat_finder.html",
     "shown as strong.</p>\n      {#- #714",
     "shown as strong.</p>\n      {% endif %}{% if true %}\n      {#- #714",
     "test_the_janma_note_is_absent_when_no_tara_grade_is_shown"),
]
