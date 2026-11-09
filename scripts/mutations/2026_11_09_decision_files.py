"""New decisions go in docs/decisions/, the §10 table is frozen (2026-11-09)."""

MUTATIONS = [
    ("decision files: the freeze moves a year later, so new rows pass again",
     "tests/test_decision_log_frozen.py",
     'FROZEN_AFTER = "2026-11-09"\n',
     'FROZEN_AFTER = "2027-11-09"\n',
     "test_no_decision_row_is_added_to_the_frozen_table"),
    ("decision files: a decision file loses its date line",
     "docs/decisions/2026-11-09-decision-log-one-file-per-decision.md",
     "- **Date:** 2026-11-09\n",
     "- When: today\n",
     "test_every_decision_file_is_named_and_shaped_as_the_readme_says"),
]
