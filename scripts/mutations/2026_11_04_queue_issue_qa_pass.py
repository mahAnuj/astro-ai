"""The queue drops an ISSUE entry whose issue already carries `qa-pass`.

2026-11-03 18:52Z: `issue=431` was drained twice while PR #694 held `qa-pass`;
each cycle stood down in ~35s and agent-queue went red twice on the retry."""

MUTATIONS = [
    ("queue: the qa-pass check skips issue entries again (done work re-dispatched)",
     "scripts/cycle_queue.py",
     '    try:\n        labels = gh(["api", f"repos/{repo}/issues/{e.target}"',
     '    if e.kind != "pr":\n        return None\n    try:\n        labels = gh(["api", f"repos/{repo}/issues/{e.target}"',
     "test_an_ISSUE_entry_whose_issue_already_carries_qa_pass_is_dropped"),
]
