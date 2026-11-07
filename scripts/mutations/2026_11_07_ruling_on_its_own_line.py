"""A test-count-drop ruling counts only as a line of its own (2026-11-07, #747's quoted phrase)."""

MUTATIONS = [
    ("ruling: the phrase anywhere in a comment counts again",
     "scripts/verify_test_floor.py",
     "            m = _RULING_LINE.fullmatch(line.strip())\n",
     "            m = _RULING_LINE.search(line)\n",
     "test_a_quoted_phrase_is_a_mention_not_a_ruling"),
]
