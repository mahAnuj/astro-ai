"""The §10 freeze date as the two rule documents publish it (2026-11-19).

`tests/test_decision_log_frozen.py` binds its FROZEN_AFTER constant to the date in `CLAUDE.md`
and in `docs/decisions/README.md`. The existing row in `2026_11_09_decision_files.py` moves the
constant; these two move each document's copy, so a document that drifts from the constant is
caught on its own. Added with PR #1259, which removed two obsolete rows and had to keep the
harness total from falling. One area file, a literal list (test_mutation_tables.py requires it).
"""

MUTATIONS = [
    ("decision files: CLAUDE.md states a different freeze date than the test enforces",
     "CLAUDE.md",
     "(frozen after 2026-11-09; format in",
     "(frozen after 2027-11-09; format in",
     "test_no_decision_row_is_added_to_the_frozen_table"),
    ("decision files: the decisions README states a different freeze date than the test enforces",
     "docs/decisions/README.md",
     "a row dated after 2026-11-09 is added to the",
     "a row dated after 2027-11-09 is added to the",
     "test_no_decision_row_is_added_to_the_frozen_table"),
]
