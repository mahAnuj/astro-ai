"""The rashifal may not invent the reader's life (2026-11-09).

The owner's Aries email opened "You left the kitchen conversation with your
sister hanging" -- a scene the reader never had -- and the live page that week
carried "your mother's kitchen", "Item four on your list" and invented dialogue.
Root cause: five of eleven opening moves and two shapes told the model to assert
something about the reader's own life, and the prompt asked for "concrete
images" with nothing forbidding invention.
"""
from __future__ import annotations

import re

from astro_ai import llm
from astro_ai.rashifal_quality import check_reading
from astro_ai.routes.deps import RASHIFAL_PROMPT_PATH

_INVENTING = re.compile(
    r"happened yesterday|have not replied|in the room with them|that matters to them"
    r"|deliberately not made|mid-situation|has been avoiding", re.I)


def test_no_opening_move_or_shape_asks_for_a_fact_about_the_reader():
    hits = [t for t in llm._OPENING_MOVES + llm._RASHIFAL_SHAPES if _INVENTING.search(t)]
    assert not hits, f"these tell the model to invent the reader's life: {hits}"


def test_the_rotation_pools_keep_their_sizes():
    # 7 x 11 = 77 pairings before a rashi repeats (llm.py's rotation comment).
    assert (len(llm._RASHIFAL_SHAPES), len(llm._OPENING_MOVES)) == (7, 11)


def test_the_prompt_forbids_inventing_the_readers_life():
    text = RASHIFAL_PROMPT_PATH.read_text()
    assert "NEVER INVENT THE READER'S LIFE" in text
    assert "Concrete images" not in text, "the instruction that invited the scenes is back"


def test_the_gate_refuses_a_named_relative_or_boss():
    for body in ("You left the kitchen conversation with your sister hanging.",
                 "The old tiffin box in your mother's kitchen.",
                 "Your manager may ask for the file."):
        assert any("invents the reader's people" in s for s in check_reading(body)["style"]), body


def test_the_gate_leaves_generic_people_alone():
    for body in ("Talk gently with your family tonight.",
                 "If a conversation has been left hanging, today suits finishing it.",
                 "Someone close to you may need a quieter word."):
        assert not any("invents" in s for s in check_reading(body)["style"]), body
