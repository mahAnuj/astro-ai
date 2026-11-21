"""#1017 (slice 8): /muhurat/vivah lists the next five auspicious dates with the finder's Abujha
rows dropped, and carries the auditor's R9 disclosure beside the list.

Rows target routes/muhurat.py and templates/muhurat_landing.html, which
tests/test_muhurat_landing_dates.py exercises through the real route. The vivah allow-list row
here replaces the one #1325 carried (its nominated test was deleted when vivah joined). The
`LANDING_EXCLUDE_FLAGS` rows go when the Abujha precedence bug (#1346) is fixed in muhurat.py.
One area file, a literal list (test_mutation_tables.py requires it)."""

_R = "src/astro_ai/routes/muhurat.py"
_T = "src/astro_ai/templates/muhurat_landing.html"
_IF = "{% if event_key == 'vivah' %}"

MUTATIONS = [
    ("#1017: vivah drops out of the landing allow-list (no list, no disclosure)",
     _R, 'LANDING_DATES_EVENTS = frozenset({"griha_pravesh", "vidyarambh", "namkaran", "business", "vivah"})',
     'LANDING_DATES_EVENTS = frozenset({"griha_pravesh", "vidyarambh", "namkaran", "business"})',
     "test_vivah_landing_lists_the_earliest_five_non_abujha_auspicious_dates"),
    ("#1017: the vivah Abujha exclusion is emptied (the finder's Abujha-override rows are listed)",
     _R, 'LANDING_EXCLUDE_FLAGS = {"vivah": frozenset({"abujha_muhurat"})}',
     'LANDING_EXCLUDE_FLAGS = {"vivah": frozenset()}',
     "test_vivah_landing_never_shows_an_abujha_row"),
    ("#1017: the Abujha exclusion applies to every event, not only vivah",
     _R, "    skip = LANDING_EXCLUDE_FLAGS.get(event_key, frozenset())",
     '    skip = LANDING_EXCLUDE_FLAGS["vivah"]',
     "test_the_abujha_exclusion_is_vivah_only"),
    ("#1017: the Abujha rows are dropped by a flag name that never matches (monkeypatched row survives)",
     _R, '"vivah": frozenset({"abujha_muhurat"})',
     '"vivah": frozenset({"abujha"})',
     "test_a_monkeypatched_abujha_row_is_dropped_from_the_vivah_list"),
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
