"""2026-11-11: a run dropped from the queue is not a failed loop run.

Each row re-breaks one piece and names the test that must go red."""

MUTATIONS = [
    ("ops-today: queue-dropped cancellations count as failures again",
     "src/astro_ai/ops_today.py",
     "        if superseded(r):\n            continue\n",
     "",
     "test_the_failed_tile_skips_queue_drops_and_keeps_real_failures"),
    ("ops-today: every cancellation reads as superseded, hiding timeouts",
     "src/astro_ai/ops_today.py",
     "    return (end - start).total_seconds() <= SUPERSEDED_WITHIN_S\n",
     "    return True\n",
     "test_a_cancel_at_a_timeout_still_counts_as_a_failure"),
    ("ops-today: a non-cancelled conclusion can read as superseded",
     "src/astro_ai/ops_today.py",
     '    if run.get("conclusion") != "cancelled":\n        return False\n',
     "",
     "test_only_cancelled_is_ever_read_as_superseded"),
]
