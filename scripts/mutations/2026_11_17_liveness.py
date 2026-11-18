"""#1186 (2026-11-17): liveness findings. The replay rows re-open the shape the
owner found by hand on 2026-11-16/17: a QA PASS at the head, gates red on that
head, the fix marked dispatched and its queue entry dropped. tests/test_liveness.py."""

MUTATIONS = [
    ("liveness: a 'fix dispatched' marker counts as handled although its entry was dropped",
     "scripts/liveness.py",
     '            if any(f"qa-on-green: red gates noted at {head}" in (c.get("body") or "")',
     '            if any(f"qa-on-green: fix dispatched at {head}" in (c.get("body") or "")',
     "test_REPLAY_2026_11_17_pass_at_head_gates_red_fix_entry_dropped"),
    ("liveness: a dropped queue entry counts as live",
     "scripts/liveness.py",
     '    if e.state in ("pending", "claimed"):',
     '    if e.state in ("pending", "claimed", "dropped"):',
     "test_REPLAY_2026_11_17_pass_at_head_gates_red_fix_entry_dropped"),
    ("liveness: a held PR is reported ready before chief clears its head",
     "scripts/liveness.py",
     "            if when and (not held or cleared) and now - when > READY_STALE:",
     "            if when and now - when > READY_STALE:",
     "test_a_held_PR_is_ready_only_once_chief_cleared_ITS_head"),
    ("liveness: a head older than the shared runs page is invisible",
     "scripts/liveness.py",
     "        runs = gates.get(head) or gate_runs_for(gh, repo, head)",
     "        runs = gates.get(head) or {}",
     "test_a_PR_whose_gates_ran_before_the_shared_page_is_still_seen"),
    ("liveness: the hourly filer clears the steward's ops findings, and the steward clears these",
     "scripts/file_ops_findings.py",
     '    return (kind in LIVENESS_KINDS) == (scope == "liveness")',
     "    return True",
     "test_a_liveness_run_never_clears_the_stewards_kinds_and_vice_versa"),
]
