"""#1207: the queue drops an entry for a PR that is `blocked` only while a gates
run is going or green, and does not retry a green run that wrote nothing.
tests/test_cycle_queue.py."""

MUTATIONS = [
    # `is False` -> `is not True` lets None (no run / unreadable) count as waiting.
    ("queue: an unreadable or missing gates run counts as waiting to merge",
     "scripts/cycle_queue.py",
     '_gates_red(gh, repo, pr.get("sha") or "") is False',
     '_gates_red(gh, repo, pr.get("sha") or "") is not True',
     "test_a_BLOCKED_PR_with_NO_gates_run_is_still_started"),

    ("queue: a failed gates run reads as not red, so a red-gates fix is dropped as waiting",
     "scripts/cycle_queue.py",
     '    return True if conclusion in _RED else None\n',
     '    return False if conclusion in _RED else None\n',
     "test_a_BLOCKED_PR_whose_latest_gates_run_is_RED_is_still_started"),

    ("queue: a green carrier run that left no trace is retried like a dead one",
     "scripts/cycle_queue.py",
     'any(t in out for t in TRANSIENT) and "concluded \'success\'" in out:',
     'any(t in out for t in TRANSIENT) and "concluded \'never\'" in out:',
     "test_a_run_that_SUCCEEDED_and_left_no_trace_is_dropped_not_retried"),

    ("queue: the gates filter matches any workflow, so another workflow's run decides",
     "scripts/cycle_queue.py",
     'select(.name == "{GATES_WORKFLOW}")',
     'select(.name != "{GATES_WORKFLOW}")',
     "test_a_failing_run_of_ANOTHER_workflow_is_ignored"),
]
