"""#1562: Overview ships only the top issues; the Backlog tab ships all of them."""

MUTATIONS = [
    ("#1562: Overview ships every open issue again (the cap is not applied)",
     "src/astro_ai/routes/admin.py",
     'full["issues"] = ops_tabs.top_issues(I["rows"], ops_tabs.OVERVIEW_ISSUE_ROWS)',
     'full["issues"] = I["rows"]',
     "test_overview_blob_ships_at_most_the_cap_in_the_scripts_order"),
    ("#1562: the cap keeps the oldest issues instead of the highest priority",
     "src/astro_ai/ops_tabs.py",
     "return sorted(rows or [], key=key)[:max(int(n), 0)]",
     "return list(rows or [])[:max(int(n), 0)]",
     "test_overview_blob_ships_at_most_the_cap_in_the_scripts_order"),
    ("#1562: the Python rank order drifts from the script's rank literal",
     "src/astro_ai/ops_tabs.py",
     '_ISSUE_RANK = {"high": 0, "medium": 1, "low": 2, "unset": 3}',
     '_ISSUE_RANK = {"high": 0, "medium": 2, "low": 1, "unset": 3}',
     "test_python_rank_order_equals_the_scripts_rank_literal"),
    ("#1562: the drill title claims every issue while showing a cut list",
     "src/astro_ai/templates/admin_ops.html",
     "of {{ I.open|int }} open (the Backlog tab lists all)",
     "open",
     "test_the_drill_title_says_when_it_is_cut"),
]
