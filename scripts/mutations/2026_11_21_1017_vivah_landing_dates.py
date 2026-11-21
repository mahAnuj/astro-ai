"""#1017 (slice 8): /muhurat/vivah lists the next five auspicious dates and carries the auditor's
R9 disclosure beside the list.

Rows target routes/muhurat.py and templates/muhurat_landing.html, which
tests/test_muhurat_landing_dates.py exercises through the real route. The vivah allow-list row
here replaces the one #1325 carried (its nominated test was deleted when vivah joined). The
`LANDING_EXCLUDE_FLAGS` rows (an interim vivah-only Abujha display filter) were deleted with the
filter when #1346 made Abujha a booster after the exclusions; one row now guards against a filter
coming back.
One area file, a literal list (test_mutation_tables.py requires it)."""

_R = "src/astro_ai/routes/muhurat.py"
_T = "src/astro_ai/templates/muhurat_landing.html"
_IF = "{% if event_key == 'vivah' %}"

MUTATIONS = [
    ("#1017: vivah drops out of the landing allow-list (no list, no disclosure)",
     _R, 'LANDING_DATES_EVENTS = frozenset({"griha_pravesh", "vidyarambh", "namkaran", "business", "vivah"})',
     'LANDING_DATES_EVENTS = frozenset({"griha_pravesh", "vidyarambh", "namkaran", "business"})',
     "test_vivah_landing_lists_the_earliest_five_auspicious_dates"),
    ("#1346: the landing drops Abujha-flagged rows again (a display filter hiding the finder's verdict)",
     _R, "    upcoming = sorted((c for c in rows if c.rating in AUSPICIOUS_RATINGS), key=lambda c: c.d)",
     '    upcoming = sorted((c for c in rows if c.rating in AUSPICIOUS_RATINGS\n'
     '                       and "abujha_muhurat" not in c.flags), key=lambda c: c.d)',
     "test_no_landing_event_filters_an_abujha_flagged_row"),
    ("#1017: the disclosure is never rendered",
     _T, _IF, "{% if false %}",
     "test_vivah_landing_carries_the_disclosure_beside_the_list"),
    ("#1017: the disclosure is rendered on every landing, not only vivah",
     _T, _IF, "{% if true %}",
     "test_the_disclosure_is_vivah_only"),
    ("#1017: the disclosure stops saying the finder does not read the lagna or the 7th house",
     _T, "the rising sign (lagna) or the state of the 7th house. Rao's",
     "Rao's",
     "test_vivah_landing_carries_the_disclosure_beside_the_list"),
    ("#1017: the Rao quote is reworded off the corpus",
     _T, '"These are merely guidelines and not final recommendations"',
     '"These are binding rules"',
     "test_vivah_landing_carries_the_disclosure_beside_the_list"),
    ("#1017: the disclosure calls the almanac conventions classical (test_muhurat_classical_copy's gate)",
     _T, "Sarvartha Siddhi) come from",
     "Sarvartha Siddhi) are not classical, they come from",
     "test_the_real_routes_render_the_disclosure"),
]
