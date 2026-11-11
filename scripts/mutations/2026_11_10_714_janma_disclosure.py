"""#714: the finder discloses how Janma (Tara position 1) is graded, names only the one held
book it follows, and the grade itself is pinned so a change is a deliberate, sourced act.
The Vivah groom rows are in 2026_11_11_714_janma_vivah.py."""

_NOTE = '<strong>Tara Bala, Janma:</strong> on a day when'

MUTATIONS = [
    ("#714: the Janma disclosure paragraph is deleted",
     "src/astro_ai/templates/muhurat_finder.html",
     _NOTE,
     '<strong>Tara Bala, Janma (removed):</strong> on a day when',
     "test_the_finder_discloses_how_janma_is_graded"),
    ("#714: the disclosure is reworded to claim what 'classical tradition' says about Janma",
     "src/astro_ai/templates/muhurat_finder.html",
     "are not sourced to a text this site holds.</p>",
     "follow classical tradition.</p>",
     "test_the_janma_note_names_one_book_and_does_not_lean_on_the_nuptials_sentence"),
    ("#714: Janma is quietly flipped to 'avoid' while the page still says 'ok'",
     "src/astro_ai/muhurat.py",
     '    1: ("Janma",     "ok"),',
     '    1: ("Janma",     "avoid"),',
     "test_janma_is_still_graded_ok"),
    ("#714: the couple verdict stops passing 'ok' for the bride, so her Janma day silently demotes",
     "src/astro_ai/muhurat.py",
     '    b_tara_ok = bride.tara_bala in ("excellent", "good", "ok")\n',
     '    b_tara_ok = bride.tara_bala in ("excellent", "good")\n',
     "test_a_bride_on_her_own_janma_still_passes_the_couple_verdict"),
    ("#714: the disclosure shows when no Tara grade is displayed",
     "src/astro_ai/templates/muhurat_finder.html",
     "shown as strong.</p>\n      {#- #714",
     "shown as strong.</p>\n      {% endif %}{% if true %}\n      {#- #714",
     "test_the_janma_note_is_absent_when_no_tara_grade_is_shown"),
]
