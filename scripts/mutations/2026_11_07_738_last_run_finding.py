"""Mutation rows for #738 -- a red last run reaches the ops-findings carrier (2026-11-07).

One file per area, loaded by `scripts/mutate_behaviour_suite.py`. Each row
re-opens one way the carrier could go silent about a loop whose last run failed,
or the alert could once more say "not due again yet" under verdict `ok`.

DATA ONLY. `MUTATIONS` must stay a literal list: `verify_no_relaxation.py`
counts it by parsing.
"""

MUTATIONS = [
    ("ops: the detector never emits the red-last-run finding",
     "scripts/detect_ops_regressions.py",
     "        if failed:\n            add(\"loop-last-run-failed\"",
     "        if False:\n            add(\"loop-last-run-failed\"",
     "test_a_red_last_run_under_a_quiet_verdict_is_a_finding"),
    ("ops: the red-last-run finding is raised per loop-already-alerted too",
     "scripts/detect_ops_regressions.py",
     "if _last_run_failed(r) and r.get(\"workflow\") not in flagged)",
     "if _last_run_failed(r))",
     "test_a_loop_already_in_alerts_is_not_announced_twice"),
    ("ops: the alert says 'not due again yet' under every verdict again",
     "src/astro_ai/ops_data.py",
     "if lp.get(\"verdict\") == \"not-due-yet\" else",
     "if True else",
     "test_the_not_due_again_clause_appears_only_under_not_due_yet"),
]
