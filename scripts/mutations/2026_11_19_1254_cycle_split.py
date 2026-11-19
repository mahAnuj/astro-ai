"""/agent-cycle split into an entry file and agent-cycle/build.md (#1254,
2026-11-19). Each row re-breaks one property that keeps the split from
degrading the loop: the route to the build file, QA rounds staying out of it,
and the shared verdict rules staying where every mode can read them."""

MUTATIONS = [
    ("cycle split: the entry no longer sends a build cycle to build.md",
     ".claude/commands/agent-cycle.md",
     "read\n  `.claude/commands/agent-cycle/build.md` in full now, before Step 0a.",
     "see\n  `.claude/commands/agent-cycle/build.md` if needed.",
     "test_a_build_cycle_is_sent_to_the_build_file_before_step_0a"),
    ("cycle split: QA rounds are no longer told to stay out of build.md",
     ".claude/commands/agent-cycle.md",
     "do not open the build file.",
     "open the build file if useful.",
     "test_a_qa_round_is_told_not_to_open_the_build_file"),
    ("cycle split: the FAIL-handling rule leaves the entry file QA and fix rounds read",
     ".claude/commands/agent-cycle.md",
     "  **If that verdict is a FAIL, fixing it is the cycle's whole job.",
     "  **When a verdict exists, fixing it is the cycle's whole job.",
     "test_the_shared_verdict_rules_are_in_the_entry_not_the_build_file"),
]
