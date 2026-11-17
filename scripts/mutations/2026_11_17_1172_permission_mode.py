"""#1172: every claude-code-action step sets a strict --permission-mode and pins
the action to a commit. tests/test_claude_action_permission_mode.py."""

MUTATIONS = [
    ("#1172: rashifal-generate's claude step drops --permission-mode (auto mode again)",
     ".github/workflows/rashifal-generate.yml",
     "claude_args: --permission-mode default --max-turns 40",
     "claude_args: --max-turns 40",
     "test_every_claude_step_sets_a_strict_permission_mode"),
    ("#1172: agent-research goes back to the floating @v1 tag",
     ".github/workflows/agent-research.yml",
     "anthropics/claude-code-action@cc98b3ae241b0fcfb6a42a2690751afffecb4452  # v1.0.278",
     "anthropics/claude-code-action@v1",
     "test_every_claude_step_pins_the_action_to_a_commit"),
    ("#1172 QA: agent-research comments the mode out (the action strips it -> auto)",
     ".github/workflows/agent-research.yml",
     "            --permission-mode default",
     "            # --permission-mode default",
     "test_every_claude_step_sets_a_strict_permission_mode"),
]
