"""#759: a chief clearance starts one agent-merge sweep, and only a real clearance does."""

MUTATIONS = [
    ("chief clear: the sweep dispatch is dropped, so a cleared PR waits for the cron",
     "scripts/chief_clear.py",
     "    if cleared:\n        dispatch_sweep(gh, repo)",
     "    if False:\n        dispatch_sweep(gh, repo)",
     "test_a_clearance_dispatches_one_agent_merge_sweep"),
    ("chief clear: a sweep is dispatched even when every clearance was refused",
     "scripts/chief_clear.py",
     "    if cleared:\n        dispatch_sweep(gh, repo)",
     "    if True:\n        dispatch_sweep(gh, repo)",
     "test_a_refused_clearance_dispatches_nothing"),
    ("chief clear: a failed dispatch aborts the run instead of warning",
     "scripts/chief_clear.py",
     "    except RuntimeError as exc:\n        print(f\"::warning::cleared, but could not dispatch",
     "    except KeyError as exc:\n        print(f\"::warning::cleared, but could not dispatch",
     "test_a_failed_dispatch_keeps_the_clearance_and_only_warns"),
]
