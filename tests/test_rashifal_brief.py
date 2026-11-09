"""The nightly brief sends exactly what the live path sends (2026-11-09).

`scripts/rashifal_brief.py` called `llm._rashifal_user_message`, which never
existed, and fell back to a hand-written copy from before #513/#523: no
TODAY'S GOCHARA block, no SHAPE FOR TODAY. Every nightly reading was written
blind to the counts and Chandra Bala printed beside it. Its docstring cited
this file as pinning the two together; the file did not exist until now.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

from astro_ai import llm

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rashifal_brief", ROOT / "scripts" / "rashifal_brief.py")
rb = importlib.util.module_from_spec(_spec)
sys.modules["rashifal_brief"] = rb
_spec.loader.exec_module(rb)

DAY = "2026-11-09"


def _section(brief: str, en: str) -> str:
    m = re.search(rf"### {en} / \w+\n\n```\n(.*?)\n```", brief, re.S)
    assert m, f"no section for {en}"
    return m.group(1)


def test_the_brief_message_is_the_live_message_for_every_rashi():
    _, brief = rb.build("en", DAY)
    from datetime import date
    from astro_ai import festivals
    from astro_ai.chart import compute_chart, compute_panchang, compute_transit_snapshot
    day = date.fromisoformat(DAY)
    natal = compute_chart(*rb._NEUTRAL)
    transit = compute_transit_snapshot(natal, when=rb.rashifal_day_moment(day))
    panchang = compute_panchang(natal, when=rb.rashifal_day_moment(day))
    sig = "\n".join(f"- {s}" for s in llm._build_rashifal_day_signals(
        transit, DAY, "en", panchang, festivals.festival_for_date(day)))
    tb = llm.format_transit_for_prompt(transit)
    for idx, anchor in enumerate(llm._RASHI_ANCHORS):
        live = llm._format_rashifal_message(
            anchor, sig, tb, llm._gochara_block(idx, transit),
            llm._RASHIFAL_SHAPES[llm._rotation_index(DAY, idx, len(llm._RASHIFAL_SHAPES))])
        assert _section(brief, anchor["en"]) == live, anchor["en"]


def test_the_brief_carries_the_gochara_and_the_shape():
    _, brief = rb.build("en", DAY, "aries")
    msg = _section(brief, "Aries")
    assert "TODAY'S GOCHARA FOR THIS RASHI" in msg
    assert "PER-AREA COUNTS SHOWN TO THE READER" in msg
    assert "THE SHAPE FOR TODAY" in msg


def test_the_brief_keeps_no_hand_written_copy_of_the_message():
    src = (ROOT / "scripts" / "rashifal_brief.py").read_text()
    assert "_inline_user_message" not in src and "hasattr(llm" not in src
