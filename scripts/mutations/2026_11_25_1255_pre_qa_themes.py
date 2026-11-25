"""2026-11-25 (#1255): scripts/pre_qa_check.py runs THEME_CHECKS -- regression, grounding,
tests, the three themes QA fails on most (measurements/lessons.json: 31, 30, 26) -- before
the diff's pytest. A check that passes on a defect, or a theme that is dropped or reads
"could not compute" as PASS, spends the QA round it exists to save. Each row re-breaks one
of them and names the test that must go red. tests/test_pre_qa_check.py."""

MUTATIONS = [
    ("themes/tests: new code with no test passes because a test-free diff is read as having one",
     "scripts/pre_qa_check.py",
     '    if any(p.startswith("tests/") for p in ctx.changed):\n',
     '    if not any(p.startswith("tests/") for p in ctx.changed):\n',
     "test_new_code_with_no_test_in_the_diff_fails_the_tests_theme"),

    ("themes/tests: a mutation anchor that occurs twice is accepted",
     "scripts/pre_qa_check.py",
     "            if n != 1:\n",
     "            if n < 1:\n",
     "test_a_mutation_row_whose_anchor_is_missing_or_ambiguous_or_whose_test_is_absent_fails"),

    ("themes/tests: a mutation row naming a test that does not exist is accepted",
     "scripts/pre_qa_check.py",
     'if not re.search(rf"\\bdef {re.escape(name)}\\b", tests_text):',
     "if False:",
     "test_a_mutation_row_whose_anchor_is_missing_or_ambiguous_or_whose_test_is_absent_fails"),

    ("themes/regression: a changed .py that does not parse is not reported",
     "scripts/pre_qa_check.py",
     'problems.append(f"{p}:{e.lineno}: {e.msg}")',
     "pass",
     "test_a_changed_python_file_that_does_not_parse_fails_regression"),

    ("themes/regression: a changed template that does not parse is not reported",
     "scripts/pre_qa_check.py",
     'problems.append(f"{p}:{e.lineno}: {e.message}")',
     "pass",
     "test_a_changed_template_that_does_not_parse_fails_regression"),

    ("themes/regression: a removed name that code still uses is not reported",
     "scripts/pre_qa_check.py",
     "            if refs:\n",
     "            if False:\n",
     "test_a_removed_name_that_code_still_uses_fails_regression"),

    ("themes/regression: a name moved to another file is reported as removed",
     "scripts/pre_qa_check.py",
     "for name in sorted(_top_names(lines) - readded):",
     "for name in sorted(_top_names(lines)):",
     "test_a_removed_name_that_was_re_added_or_only_named_in_a_string_passes"),

    ("themes/grounding: a `corpus:` line in a commit no longer satisfies the proxy",
     "scripts/pre_qa_check.py",
     'for m in ctx.commits):\n        return []\n    return [f"{p} can carry',
     'for m in []):\n        return []\n    return [f"{p} can carry',
     "test_a_corpus_line_or_a_knowledge_change_or_an_unrelated_diff_passes_grounding"),

    ("themes/grounding: prompts/ is dropped from the claim-bearing paths",
     "scripts/pre_qa_check.py",
     '"src/astro_ai/knowledge/", "src/astro_ai/prompts/", "src/astro_ai/templates/learn/")',
     '"src/astro_ai/knowledge/", "src/astro_ai/templates/learn/")',
     "test_a_claim_bearing_file_without_a_corpus_line_fails_grounding"),

    ("themes: the grounding theme has no checks",
     "scripts/pre_qa_check.py",
     '    "grounding": (check_grounding_proxy,),\n',
     '    "grounding": (),\n',
     "test_theme_checks_cover_regression_grounding_and_tests"),

    ("themes: a failing theme does not fail the run",
     "scripts/pre_qa_check.py",
     '            failed.append(f"theme:{theme}")',
     "            pass",
     "test_main_prints_one_themes_line_and_a_failing_theme_exits_one"),

    ("themes: a theme that could not compute reads as a pass",
     "scripts/pre_qa_check.py",
     '            unrun.append(f"theme:{theme}")',
     "            pass",
     "test_a_theme_that_cannot_compute_exits_two_never_zero"),

    ("themes: an undiffable tree reads as a pass",
     "scripts/pre_qa_check.py",
     '        unrun.append("themes")\n',
     "        pass\n",
     "test_an_undiffable_tree_makes_the_themes_unrunnable_not_passing"),

    ("themes: main never runs the theme checks",
     "scripts/pre_qa_check.py",
     "        _themes_into(changed, failed, unrun)\n",
     "        pass\n",
     "test_main_prints_one_themes_line_and_a_failing_theme_exits_one"),
]
