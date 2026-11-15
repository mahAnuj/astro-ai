"""2026-11-15: the queue must not drop a fix for a PR whose qa-pass is from an
older commit (PR #1058). tests/test_cycle_queue.py."""

_Q = "scripts/cycle_queue.py"

MUTATIONS = [
    ("queue: a mergeable qa-pass PR is 'waiting to merge' whatever commit the PASS names",
     _Q, 'if pr.get("sha") and _pass_names_head(pass_lines, repo, pr["sha"]):',
     "if True:",
     "test_an_ISSUE_entry_whose_PR_passed_an_OLDER_commit_is_still_started"),
]
