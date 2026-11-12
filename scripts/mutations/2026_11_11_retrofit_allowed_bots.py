"""2026-11-11: the evidence retrofit accepts the bot that dispatches it.

Run 42933391630 failed with "Workflow initiated by non-human actor" before the
agent started; the step now names github-actions in allowed_bots."""

MUTATIONS = [
    ("retrofit: the bot-dispatched retrofit is refused again (allowed_bots removed)",
     ".github/workflows/agent-prioritise.yml",
     '          allowed_bots: "github-actions"\n',
     '',
     "test_the_retrofit_step_accepts_the_bot_that_dispatches_it"),
]
