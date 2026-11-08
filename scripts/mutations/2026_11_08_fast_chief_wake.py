"""A held PR wakes chief the moment it is ready, once per head (2026-11-08)."""

MUTATIONS = [
    ("fast wake: a ready held PR is too young for the steward again",
     "scripts/detect_stalls.py",
     "        if age < hours and not young_held:\n",
     "        if age < hours:\n",
     "test_a_ready_held_pr_minutes_old_is_reported_for_chief"),
    ("fast wake: a young held PR with red gates is reported too",
     "scripts/detect_stalls.py",
     "        if young_held and not green:\n            continue\n",
     "",
     "test_a_young_held_pr_whose_gates_are_not_green_raises_no_stall_at_all"),
    ("fast wake: agent-merge never dispatches the steward",
     ".github/workflows/agent-merge.yml",
     "                 && gh workflow run agent-steward.yml --repo \"$GH_REPO\" --ref main; then\n",
     "                 && true; then\n",
     "test_the_first_hold_on_a_head_comments_first_then_wakes_the_steward"),
    ("fast wake: the per-head marker is ignored, so every run wakes chief",
     ".github/workflows/agent-merge.yml",
     "          case \"$woke\" in\n            0)\n",
     "          case \"0\" in\n            0)\n",
     "test_the_same_head_never_wakes_chief_twice"),
]
