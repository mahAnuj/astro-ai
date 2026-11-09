"""The queue drops a PR's QA round on `qa-pass` only when a PASS names the head.

#823 / PR #812: `qa-pass` was given at d182529; two `Merge origin/main` commits
followed. agent-merge (since 2026-11-05) refuses a label whose PASS comment does
not name the head, and qa-on-green queued a round on the new head -- which the
queue then dropped as "already carries qa-pass". The PR was stranded: refused
by one workflow, ignored by the other, the one dispatch per commit spent."""

MUTATIONS = [
    ("queue: a bare qa-pass label drops the round again, whatever commit it was given on",
     "scripts/cycle_queue.py",
     "    if passed and head and _pass_names_head(pass_lines, repo, head):",
     "    if passed:",
     "test_a_qa_pass_bound_to_an_EARLIER_commit_does_not_drop_the_round"),
    ("queue: any author's PASS comment binds the head (agent-merge accepts claude[bot] or the owner)",
     "scripts/cycle_queue.py",
     "        if who in trusted and head in first:",
     "        if head in first:",
     "test_a_PASS_comment_from_a_stranger_does_not_count_as_binding"),
    ("queue: the owner's PASS no longer binds the head (a top-level session's verdict)",
     "scripts/cycle_queue.py",
     '    trusted = {"claude[bot]", repo.split("/")[0]}',
     '    trusted = {"claude[bot]"}',
     "test_a_PASS_comment_from_the_repo_owner_binds_the_head"),
]
