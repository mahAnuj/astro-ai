"""#1207: the queue drops an entry for a PR that is `blocked` only while the required
gates (PR gates, verify-build) are going or green, and does not retry a green run that wrote nothing.
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
     "            verdicts.append(True if conclusion in _RED else None)\n",
     "            verdicts.append(False if conclusion in _RED else None)\n",
     "test_a_BLOCKED_PR_whose_latest_gates_run_is_RED_is_still_started"),

    ("queue: a green carrier run that left no trace is retried like a dead one",
     "scripts/cycle_queue.py",
     'any(t in out for t in TRANSIENT) and "concluded \'success\'" in out:',
     'any(t in out for t in TRANSIENT) and "concluded \'never\'" in out:',
     "test_a_run_that_SUCCEEDED_and_left_no_trace_is_dropped_not_retried"),

    # QA on PR #1271: verify-build is a required workflow too.
    ("queue: only `PR gates` is read, so a red verify-build is dropped as waiting to merge",
     "scripts/cycle_queue.py",
     "GATE_WORKFLOWS = (GATES_WORKFLOW, BUILD_WORKFLOW)\n",
     "GATE_WORKFLOWS = (GATES_WORKFLOW,)\n",
     "test_PR_gates_green_but_verify_build_RED_is_still_started"),

    ("queue: a missing required gates run counts as not red, so the PR is dropped as waiting",
     "scripts/cycle_queue.py",
     "            verdicts.append(None)\n            continue\n",
     "            verdicts.append(False)\n            continue\n",
     "test_a_MISSING_verify_build_run_is_uncertainty_so_the_cycle_starts"),

    ("queue: the newest gates run is picked by created_at alone, so a same-second tie takes the older",
     "scripts/cycle_queue.py",
     "sort_by([.created_at, .id])",
     "sort_by(.created_at)",
     "test_two_runs_created_in_the_same_second_are_ordered_by_id"),
]
