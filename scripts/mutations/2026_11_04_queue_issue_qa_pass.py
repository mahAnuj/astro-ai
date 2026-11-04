"""The queue drops an ISSUE entry only when that issue's PR has passed QA and
is mergeable.

2026-11-03 18:52Z: `issue=431` was drained twice while PR #694 held `qa-pass`;
each cycle stood down in ~35s and agent-queue went red twice on the retry.
QA round 1 on #704: the issue's own label is not enough -- a conflicting
`qa-pass` PR (the #608 case) still needs the cycle."""

MUTATIONS = [
    ("queue: issue entries are never dropped again (done work re-dispatched)",
     "scripts/cycle_queue.py",
     "        pr = _mergeable_passed_pr(gh, repo, e.target) if passed else None",
     "        pr = None",
     "test_an_ISSUE_entry_whose_PR_has_passed_and_is_mergeable_is_dropped"),
    ("queue: an issue entry is dropped on the label alone, conflicting PR or not",
     "scripts/cycle_queue.py",
     '        if mergeable == "true":',
     '        if True:',
     "test_an_ISSUE_entry_whose_qa_pass_PR_is_CONFLICTING_is_still_started"),
    ("queue: another issue's PR counts (number prefix, #43 for #431)",
     "scripts/cycle_queue.py",
     "        if not m or int(m.group(1)) != issue or",
     "        if not m or not str(issue).startswith(m.group(1)) or",
     "test_an_ISSUE_entry_with_qa_pass_but_NO_open_PR_is_still_started"),
]
