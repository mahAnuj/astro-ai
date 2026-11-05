"""A trust-boundary hold must be an OBLIGED action so `chief` is woken (#709).

2026-11-04: PR #706 sat held seven hours, `OBLIGED_ACTIONS=0`, three green
steward runs. Rows: drop the kind from the set, and re-apply the push filter
that would exempt workflow-PR holds."""

MUTATIONS = [
    ("detect_stalls: boundary-hold-clearable not obliged (chief never woken, #706)",
     "scripts/detect_stalls.py",
     'OBLIGED_RULING_KINDS = frozenset({"boundary-hold-clearable"})',
     'OBLIGED_RULING_KINDS = frozenset()',
     "test_a_boundary_hold_is_reported_and_counts_as_an_obliged_action"),
    ("detect_stalls: boundary hold filtered by agent_pushable (workflow PRs unwoken)",
     "scripts/detect_stalls.py",
     '            if x["kind"] in OBLIGED_RULING_KINDS\n',
     '            if x["kind"] in OBLIGED_RULING_KINDS and x.get("agent_pushable", True)\n',
     "test_a_boundary_hold_on_a_workflow_pr_still_counts"),
]
