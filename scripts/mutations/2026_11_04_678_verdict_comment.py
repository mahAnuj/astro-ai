"""A repeat `qa-fail` round is dated from its verdict COMMENT, not the label event.

#678 / #502: GitHub emits no `labeled` event when `qa-fail` is already on the
PR, so every FAIL after round 1 was dated at round 1 and `qa-fail-refixed`
named commits a later round had already judged (PR #675, PR #498)."""

MUTATIONS = [
    ("detect_stalls: any commenter can move the verdict clock (author filter dropped)",
     "scripts/detect_stalls.py",
     '        if not isinstance(c, dict) or c.get("u") not in _VERDICT_AUTHORS:',
     '        if not isinstance(c, dict):',
     "test_a_look_alike_from_another_author_is_ignored"),
    ("detect_stalls: the label event dates the verdict even when a comment exists",
     "scripts/detect_stalls.py",
     "        if verdict:\n            return age_hours(verdict[0])\n",
     "        if False:\n            return age_hours(verdict[0])\n",
     "test_the_label_event_is_not_consulted_when_a_comment_exists"),
    ("detect_stalls: a verdict naming the current head is not recognised (sha check removed)",
     "scripts/detect_stalls.py",
     '            at_head = bool(vsha and (pr["headRefOid"] or "").startswith(vsha))',
     '            at_head = False',
     "test_a_round_2_fail_on_the_current_head_is_unaddressed_not_refixed"),
    ("detect_stalls: a comment-read failure falls back to the label event",
     "scripts/detect_stalls.py",
     "        verdict = _newest_verdict(pr)\n        if verdict:",
     "        try:\n            verdict = _newest_verdict(pr)\n        except RuntimeError:\n            verdict = None\n        if verdict:",
     "test_a_comment_fetch_failure_is_none_and_does_not_fall_back"),
]
