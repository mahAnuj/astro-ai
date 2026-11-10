"""#826 (2026-11-10): a dispatched agent-work run wakes agent-queue itself.

Measured 2026-11-08..10: agent-queue ran after 8 of 8 scheduled cycles and 0
of 26 dispatched ones (GitHub drops a fourth workflow_run level). Each row
re-breaks one piece of the wake path."""

MUTATIONS = [
    ("#826: the wake step fires on scheduled runs too, so a cron cycle chains twice",
     ".github/workflows/agent-work.yml",
     "        if: always() && github.event_name == 'workflow_dispatch'\n        continue-on-error: true\n",
     "        if: always()\n        continue-on-error: true\n",
     "test_a_dispatched_cycle_wakes_agent_queue_with_its_own_run_id"),
    ("#826: the wake step no longer passes its run id",
     ".github/workflows/agent-work.yml",
     '-f after_run="$RUN_ID"',
     '-f after_run=""',
     "test_a_dispatched_cycle_wakes_agent_queue_with_its_own_run_id"),
    ("#826: wait_for_run returns while the waker is still running (it would read as a busy lane)",
     "scripts/wait_for_run.py",
     '            if run.get("status") == "completed":\n',
     '            if True:\n',
     "test_it_waits_for_the_waker_to_complete_then_describes_it"),
    ("#826: wait_for_run accepts a run of any workflow",
     "scripts/wait_for_run.py",
     "            if path != WORKFLOW_PATH:\n",
     "            if False:\n",
     "test_a_run_of_any_other_workflow_is_refused"),
    ("#826: wait_for_run never gives up",
     "scripts/wait_for_run.py",
     "        if waited >= max_wait:\n",
     "        if False and waited >= max_wait:\n",
     "test_a_run_that_never_completes_times_out_rather_than_chaining"),
    ("#826: a woken run is never chained off",
     ".github/workflows/agent-queue.yml",
     "        if: always() && (github.event_name == 'workflow_run' || env.WAKE_NAME != '')\n",
     "        if: always() && github.event_name == 'workflow_run'\n",
     "test_agent_queue_waits_before_draining_and_chains_off_the_woken_run"),
    ("#826: AFTER_RUN is passed through unvalidated",
     "scripts/wait_for_run.py",
     '    if not re.fullmatch(r"\\d{1,20}", run_id):\n',
     '    if False:\n',
     "test_main_validates_its_input_and_writes_github_env"),
]
