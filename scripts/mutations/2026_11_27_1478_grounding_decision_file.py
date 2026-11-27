"""2026-11-27 (#1478): check_grounding_proxy also accepts a citation in an ADDED line of the
change's own docs/decisions/*.md (a squash merge drops commit-message `corpus:` lines, so
6906d32 failed with knowledge/grahas.md cited in its decision file). Each row re-breaks one
way that route could pass wrongly or stop passing, and names the test that must go red.
tests/test_pre_qa_check.py."""

MUTATIONS = [
    ("grounding/decision-file: a decision file that cites nothing passes the proxy",
     "scripts/pre_qa_check.py",
     "if any(_CITES.search(line)",
     "if any(True or _CITES.search(line)",
     "test_a_decision_file_that_cites_nothing_still_fails_grounding"),

    ("grounding/decision-file: a citation in README.md or a non-decision file passes the proxy",
     "scripts/pre_qa_check.py",
     "for p in ctx.changed if _DECISION.match(p)",
     "for p in ctx.changed",
     "test_a_citation_outside_an_added_decision_line_does_not_pass_grounding"),

    ("grounding/decision-file: a citation only in REMOVED decision lines passes, an added one does not",
     "scripts/pre_qa_check.py",
     "for line in ctx.added.get(p, ())):",
     "for line in ctx.removed.get(p, ())):",
     "test_a_citation_in_an_added_decision_file_line_passes_grounding"),
]
