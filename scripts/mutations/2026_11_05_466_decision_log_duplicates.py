"""#466: a decision-log row revised across rounds must replace its older self."""

MUTATIONS = [
    ("#466: the duplicate decision-log check never fires (threshold 1 -> 99)",
     "scripts/verify_architecture_counts.py",
     "sorted(keys.items()) if n > 1]",
     "sorted(keys.items()) if n > 99]",
     "test_a_decision_log_row_kept_beside_its_older_draft_fails"),
    ("#466: the log key is the bold span only, so 33 plain-title rows are never compared",
     "scripts/verify_architecture_counts.py",
     'LOG_ROW = re.compile(r"^\\|\\s*(\\d{4}-\\d{2}-\\d{2})\\s*\\|\\s*((?:[^|\\\\]|\\\\.)+?)\\s*\\|")',
     'LOG_ROW = re.compile(r"^\\|\\s*(\\d{4}-\\d{2}-\\d{2})\\s*\\|\\s*(\\*\\*[^*]+\\*\\*)\\s*\\|")',
     "test_a_duplicate_plain_title_fails_too"),
    ("#466: an unparseable decision log reports PASS instead of failing",
     "scripts/verify_architecture_counts.py",
     "    if not keys:\n        return [f\"no dated rows parsed",
     "    if False:\n        return [f\"no dated rows parsed",
     "test_a_decision_log_with_no_parseable_rows_fails_rather_than_passing"),
]
