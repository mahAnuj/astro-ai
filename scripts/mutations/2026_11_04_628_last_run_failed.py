"""Mutation rows for #628 defect 2 -- a weekly loop's red last run (2026-11-04).

One file per area, loaded and appended by `scripts/mutate_behaviour_suite.py`.
Each row re-opens one way the "last run failed" alert could go silent again:
the verdict set that decides which loops are checked, the alert branch itself,
and the Team panel header that used to claim every loop ran when due.

DATA ONLY. `MUTATIONS` must stay a literal list: `verify_no_relaxation.py`
counts it by parsing, and a list built by a call or concatenation cannot be
counted and would read as rows deleted.
"""

MUTATIONS = [
    ("ops: a weekly loop between slots is no longer checked for a red last run",
     "src/astro_ai/ops_data.py",
     '    return (lp.get("verdict") in ("not-due-yet", "ok")',
     '    return (lp.get("verdict") in ("ok",)',
     "test_a_failed_last_run_between_slots_raises_an_amber_alert"),
    ("ops: the last-run-failed alert branch never fires",
     "src/astro_ai/ops_data.py",
     "        elif _last_run_failed(lp):",
     "        elif False:",
     "test_a_failed_last_run_between_slots_raises_an_amber_alert"),
    ("ops: the Team header claims every loop ran when due over a red last run",
     "src/astro_ai/templates/admin_ops.html",
     "{% elif A.last_failed %}",
     "{% elif False %}",
     "test_the_team_header_no_longer_claims_every_loop_ran_when_one_failed"),
]
