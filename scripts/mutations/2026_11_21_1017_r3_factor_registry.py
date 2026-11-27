"""#1017 R3: the factor and exclusion registry behind the finder's "Why this date" lists.

Rows target src/astro_ai/muhurat_factors.py and templates/muhurat_finder.html. The registry tests
(tests/test_muhurat_factor_registry.py), the parity test and the page tests
(tests/test_muhurat_factor_page.py) read the real scorer source, the real knowledge files and the
rendered page. The second block of rows pins the astro-auditor's second review: a sentence going
back to the shared wording, or a status drifting, is a defect the auditor already found once.
One area file, a literal list (test_mutation_tables.py requires it)."""

_F = "src/astro_ai/muhurat_factors.py"
_T = "src/astro_ai/templates/muhurat_finder.html"
_RULING2 = "test_each_second_ruling_override_resolves_to_the_auditors_status_and_sentence"

MUTATIONS = [
    ("#1017 R3: the dagdha entry leaves REGISTRY (a scorer flag with no entry)",
     _F, '    "dagdha": {\n        "label": "Not a Dagdha tithi-weekday pair",',
     '    "dagdha_x": {\n        "label": "Not a Dagdha tithi-weekday pair",',
     "test_every_flag_the_scorer_can_emit_has_a_registry_entry"),
    ("#1017 R3: check_dagdha is dropped from the applied exclusions (a dropped cleared item)",
     _F, '"dagdha": rules.get("check_dagdha"),',
     '"dagdha": False,',
     "test_the_cleared_list_equals_the_auditors_table_for_every_event"),
    ("#1017 R3: the Abujha override refills the cleared list (claims checks that never ran)",
     _F, '        return Explanation(scored=(_item("abujha_muhurat", event_type),), cleared=(),',
     '        return Explanation(scored=(_item("abujha_muhurat", event_type),),\n'
     '                           cleared=tuple(_item(k, event_type) for k in\n'
     '                                         _applied_hard(rules, candidate.nakshatra)),',
     "test_an_abujha_row_scores_only_itself_clears_nothing_and_has_no_boosters"),
    ("#1017 R3: the flag-to-key split swaps Tuesday and Saturday (hard and soft weekday)",
     _F, 'if flag == "avoid_weekday" and weekday not in _HARD_AVOID_WEEKDAYS:',
     'if flag == "avoid_weekday" and weekday in _HARD_AVOID_WEEKDAYS:',
     "test_the_hard_tuesday_and_the_soft_weekday_penalty_are_distinct_keys"),
    ("#1017 R3: a named heading no longer exists in the knowledge file",
     _F, '"### 29.13 ", "### 29.6 "',
     '"### 29.13 ", "### 29.60 "',
     "test_every_named_heading_exists_as_a_line_prefix_in_its_knowledge_file"),
    ("#1017 R3: the site_convention status is spelled differently (every convention item unknown)",
     _F, 'S, C, SC = "sourced", "contested", "site_convention"',
     'S, C, SC = "sourced", "contested", "convention"',
     "test_every_entry_is_sourced_contested_or_a_sentenced_site_convention"),
    ("#1017 R3: the business tithi list is marked sourced instead of site convention",
     _F, '"business": _vr(SC, _BIZ_LIST.format(what="tithi"), _BIZ),',
     '"business": _vr(S, _BIZ_LIST.format(what="tithi"), _BIZ),',
     "test_a_site_convention_item_says_so_and_a_contested_one_says_traditions_differ"),
    ("#1017 R3: the pada guard loses its nakshatra check (a pada item on a row with no star)",
     _F, '"avoid_nakshatra_pada": bool(rules.get("avoid_nakshatra_padas")) and bool(nakshatra),',
     '"avoid_nakshatra_pada": bool(rules.get("avoid_nakshatra_padas")),',
     "test_a_row_with_no_nakshatra_drops_every_nakshatra_based_check"),
    ("#1017 R3: the Amrit Siddhi sentence claims the grade was raised",
     _F, '"Whether and how this finder lifts a grade for it is its own "',
     '"Raising the grade for it is this finder\'s own "',
     "test_the_amrit_siddhi_sentence_never_claims_the_grade_rose"),
    ("#1017 R3: the cleared heading drops its local-noon qualifier",
     _F, 'CLEARED_HEADING = "Checked and not excluded at local noon"',
     'CLEARED_HEADING = "Checked and not excluded"',
     "test_the_cleared_heading_is_qualified_at_local_noon_and_never_all_day"),
    ("#1017 R3: the finder no longer includes the legend partial",
     _T, '{% include "_muhurat_why_legend.html" %}', "",
     "test_the_legend_appears_exactly_once_and_after_the_last_table"),
    ("#1017 R3: the finder no longer includes the per-row partial",
     _T, '{% include "_muhurat_why.html" %}', "",
     "test_every_auspicious_row_has_why_this_date_with_both_headings"),
    # --- the astro-auditor's second review ----------------------------------------------------
    ("#1017 R3 pass 2: Vidyarambh Rohini goes back to 'listed by one tradition, not both'",
     _F, '"Rohini": _vr(C, "The Muhurtha tradition holds this star neutral, not favourable, "',
     '"Rohini": _vr(C, "Listed by one tradition, not both; the Muhurtha tradition holds this '
     'star neutral, not favourable, "',
     _RULING2),
    ("#1017 R3 pass 2: Vidyarambh Pushya claims the Vedic tables list it too",
     _F, '"Pushya": _vr(S, "This star is on the favourable list in B.V. Raman\'s Muhurtha "',
     '"Pushya": _vr(S, "This star is on the favourable list in B.V. Raman\'s Muhurtha and the '
     'Vedic tables "',
     _RULING2),
    ("#1017 R3 pass 2: Vidyarambh Pushya loses its own qualifier (back to the shared credit)",
     _F, '"Pushya": _vr(S,', '"PushyaX": _vr(S,',
     "test_the_qualifiers_reach_the_item_they_belong_to"),
    ("#1017 R3 pass 2: Namkaran Chitra is sourced again (the Muhurtha list leaves it out)",
     _F, '"Chitra": _vr(C,', '"Chitra": _vr(S,',
     "test_second_ruling_overrides_reach_the_row_for_their_own_event_only"),
    ("#1017 R3 pass 2: Namkaran good tithi claims both traditions list it",
     _F, '"This tithi is on the Vedic table\'s list for naming a child, and "',
     '"This tithi is one the Muhurtha tradition and the Vedic tables list as favourable '
     'for naming a child, and "',
     _RULING2),
    ("#1017 R3 pass 2: Vidyarambh good weekday claims the Muhurtha tradition favours it",
     _F, '"This weekday is on the Vedic table\'s list for {event}; the "',
     '"This weekday is favoured for {event} in the Muhurtha tradition; the "',
     _RULING2),
    ("#1017 R3 pass 2: Griha Pravesh Saturday goes back to Vivah's 'another calls it middling'",
     _F, '"Traditions differ on Saturday: the Muhurtha tradition says "',
     '"Traditions differ on Saturday: another calls it middling, and the Muhurtha tradition '
     'says "',
     _RULING2),
    ("#1017 R3 pass 2: Vivah Purnima reads 'is the exception' again (can read as allowed)",
     _F, '"tradition, including the 6th for a wedding. Purnima is contested: "',
     '"tradition, including the 6th for a wedding. Purnima is the exception: "',
     _RULING2),
    ("#1017 R3 pass 2: the business convention opener goes back to lowercase",
     _F, '_BIZ_LIST = "Site convention, not sourced:',
     '_BIZ_LIST = "site convention, not sourced:',
     _RULING2),
    ("#1017 R3 pass 2: Vivah's Guru and Shukra veto loses 'The two wedding lists ... do not ask'",
     _F, '_VIVAH_NO_ASK = " The two wedding lists the books give do not ask for it."',
     '_VIVAH_NO_ASK = ""',
     _RULING2),
    ("#1017 R3 pass 2: the business Saturday sentence says 'the books we hold' again",
     _F, '"This finder deducts a point for Saturday; the Muhurtha tradition "',
     '"This finder deducts a point for Saturday; the books we hold "',
     _RULING2),
]
