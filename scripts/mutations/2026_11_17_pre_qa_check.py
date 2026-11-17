"""2026-11-17: the cycle runs pr-gates' cheap checks before dispatching QA
(run 44020807802, #1067: two of three rounds failed only on a stale count).
A pre-check that exits 0 on a failure, or on "could not run", waves the round
through and saves nothing. Each row re-breaks one exit code and names the test."""

MUTATIONS = [
    ("pre-QA: a failing gate exits 0, so QA is dispatched on a red tree",
     "scripts/pre_qa_check.py",
     "        return 1\n",
     "        return 0\n",
     "test_a_failing_gate_exits_non_zero_and_names_it"),
    ("pre-QA: a gate that could not run reads as a pass",
     "scripts/pre_qa_check.py",
     "        return 2\n",
     "        return 0\n",
     "test_a_gate_that_cannot_run_exits_two_never_zero"),
]
