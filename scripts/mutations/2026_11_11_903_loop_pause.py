"""#903 (2026-11-11): one repository variable pauses every Claude-spending loop job.

Each row re-breaks one piece and names the test that must go red."""

MUTATIONS = [
    ("#903: agent-work runs Claude while the loop is paused",
     ".github/workflows/agent-work.yml",
     "    if: vars.LOOP_PAUSED != 'true'\n",
     "    if: always()\n",
     "test_every_claude_spending_loop_job_honours_the_pause"),
    ("#903: the steward runs Claude while the loop is paused",
     ".github/workflows/agent-steward.yml",
     "    if: vars.LOOP_PAUSED != 'true'\n",
     "    if: always()\n",
     "test_every_claude_spending_loop_job_honours_the_pause"),
    ("#903: a dispatch while paused fires a run instead of queueing",
     "scripts/dispatch_cycle.sh",
     '  busy="paused"\n',
     '  :\n',
     "test_a_dispatch_while_paused_is_queued_not_dropped"),
    ("#903: the queue drains and chains while paused",
     ".github/workflows/agent-queue.yml",
     "    if: vars.LOOP_PAUSED != 'true'\n",
     "    if: always()\n",
     "test_the_queue_holds_still_while_paused"),
    ("#903: qa-on-green dispatches without knowing the loop is paused",
     ".github/workflows/qa-on-green.yml",
     "          LOOP_PAUSED: ${{ vars.LOOP_PAUSED }}   # #903: paused queues, never dispatches\n",
     "",
     "test_every_dispatch_call_is_told_whether_the_loop_is_paused"),
]
