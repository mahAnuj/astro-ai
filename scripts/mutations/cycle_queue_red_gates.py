"""2026-11-17: the queue must not drop a fix for a PR whose gates are red on a
QA-passed head (mergeable_state blocked). tests/test_cycle_queue.py."""

MUTATIONS = [
    ("queue: a blocked (red-gates) PR counts as waiting to merge",
     "scripts/cycle_queue.py",
     'mergeable = "true" if state in ("clean", "has_hooks") else state',
     'mergeable = "true" if state not in ("dirty", "unknown") else state',
     "test_an_ISSUE_entry_whose_PR_passed_QA_but_went_RED_on_the_same_head_is_still_started"),
]
