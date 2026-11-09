"""The rashifal may not invent the reader's life (2026-11-09)."""

MUTATIONS = [
    ("rashifal: an opening move asks for yesterday's unfinished business again",
     "src/astro_ai/llm.py",
     '    "Open on how the day starts compared with how it ends.",\n',
     '    "Open on something that happened yesterday and is not finished.",\n',
     "test_no_opening_move_or_shape_asks_for_a_fact_about_the_reader"),
    ("rashifal: the people shape names someone the reader has been avoiding",
     "src/astro_ai/llm.py",
     '    "conversations and the household, never who those people are -- then "\n',
     '    "conversations and someone the reader has been avoiding -- then "\n',
     "test_no_opening_move_or_shape_asks_for_a_fact_about_the_reader"),
    ("rashifal: the prompt loses its rule against inventing the reader's life",
     "src/astro_ai/prompts/rashifal_single.txt",
     "NEVER INVENT THE READER'S LIFE. ",
     "",
     "test_the_prompt_forbids_inventing_the_readers_life"),
    ("rashifal: the gate stops refusing a named relative",
     "src/astro_ai/rashifal_quality.py",
     '        r"\\byour (?:(?:older|younger|elder|little|big) )?(?:sister|brother|sibling|mother|"\n',
     '        r"\\byour (?:(?:older|younger|elder|little|big) )?(?:siblingx|"\n',
     "test_the_gate_refuses_a_named_relative_or_boss"),
]
