"""Team restructure (2026-11-19): the agent board after conversion-lead and qa-lead were
removed. Exercised by tests/test_agent_status.py. One area file, a literal list
(test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("team: an unscheduled agent borrows a state instead of saying it has no schedule",
     "src/astro_ai/agent_status.py",
     '        cards[key] = {"state": "idle", "detail": "not on any schedule", "at": None}\n',
     '        cards[key] = {"state": "idle", "detail": "waits for the next build cycle", "at": None}\n',
     "test_on_request_agents_say_they_have_no_schedule"),
    ("team: a group's cards split, so its heading renders twice",
     "src/astro_ai/agent_status.py",
     '    ("infra-reviewer", "infra-reviewer", "operate",',
     '    ("infra-reviewer", "infra-reviewer", "measure",',
     "test_cards_of_one_group_are_contiguous_so_each_heading_renders_once"),
]
