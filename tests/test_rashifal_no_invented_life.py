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


def test_no_shape_asks_for_a_fact_about_the_reader():
    hits = [t for t in llm._RASHIFAL_SHAPES if _INVENTING.search(t)]
    assert not hits, f"these tell the model to invent the reader's life: {hits}"


def test_no_fixed_opening_line_is_handed_to_the_model():
    # Owner, 2026-11-09: "Don't map any fixed lines for the opening."
    assert not hasattr(llm, "_OPENING_MOVES")
    assert not any("opening_style" in a for a in llm._RASHI_ANCHORS)
    msg = llm._format_rashifal_message(llm._RASHI_ANCHORS[0], "- sig", "tb", "", llm._RASHIFAL_SHAPES[0])
    assert "OPENING MOVE" not in msg and "OPENING STYLE" not in msg and "CHARACTER" not in msg


def test_the_prompt_asks_for_plain_everyday_language():
    text = RASHIFAL_PROMPT_PATH.read_text()
    assert "Class 8" in text and "No idioms, metaphors or poetic images" in text


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


# --- the eight reader lines (owner, 2026-11-09) ------------------------------

from datetime import datetime, timezone  # noqa: E402

from astro_ai import chart  # noqa: E402
from astro_ai.rashifal_quality import READER_LABELS, missing_reader_lines  # noqa: E402


def _transit():
    natal = chart.compute_chart("1990-01-01", "06:00", "Delhi, India")
    return chart.compute_transit_snapshot(natal, when=datetime(2026, 11, 9, 6, 30, tzinfo=timezone.utc))


def test_family_and_students_read_their_sourced_karakas():
    groups = {g["area"]: [k["planet"] for k in g["karakas"]]
              for g in chart.reader_groups_for_rashi(0, _transit())}
    assert groups == {"Family": ["Moon", "Venus"], "Students": ["Mercury", "Jupiter"]}


def test_the_message_carries_evidence_for_every_line():
    msg = llm._gochara_block(0, _transit())
    for label in ("Work:", "Money:", "Health:", "Family:", "Students:",
                  "In a relationship, Married, Single and looking to marry:"):
        assert f"  {label} supporting" in msg, label


def test_the_prompt_asks_for_the_eight_lines_in_both_languages():
    text = RASHIFAL_PROMPT_PATH.read_text()
    for lang in ("en", "hi"):
        for label in READER_LABELS[lang]:
            assert label in text, label
    assert "Never predict an exam result or a wedding" in text


def test_the_gate_finds_a_missing_line_in_either_language():
    en = "\n".join(f"{l}: A plain line." for l in READER_LABELS["en"])
    hi = "\n".join(f"{l}: एक सरल पंक्ति।" for l in READER_LABELS["hi"])
    assert missing_reader_lines("Some prose.\n\n" + en) == []
    assert missing_reader_lines("Some prose.\n\n" + hi) == []
    assert missing_reader_lines(en.replace("Students:", "Learners:")) == ["Students"]


def test_the_publish_gate_refuses_a_reading_without_its_lines():
    import importlib.util, pathlib, sys as _sys
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("publish_rashifal", root / "scripts" / "publish_rashifal.py")
    pr = importlib.util.module_from_spec(spec); _sys.modules["publish_rashifal"] = pr
    spec.loader.exec_module(pr)
    prose = " ".join(["Today is a quiet day and suits finishing work already started."] * 10)
    lines = "\n".join(f"{l}: A plain line for today." for l in READER_LABELS["en"])
    doc_ok = "\n\n".join(f"## {a['en']} / {a['sa']}\n\n{prose}\n\n{lines}" for a in llm._RASHI_ANCHORS)
    doc_bad = doc_ok.replace("Students: A plain line for today.", "", 1)
    assert not [f for f in pr.validate(doc_ok) if "missing the line" in f]
    assert any("missing the line(s) Students" in f for f in pr.validate(doc_bad))
