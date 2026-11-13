"""#944: /numerology's first input must clear the mobile tab bar at 375x667.

Measured 2026-11-13 (headless Chromium, b0e3cd8): the 7-line lede put `#name` at y 611-661,
entirely under the fixed tab bar (y 591-667). Below `sm` the lede is now one short line (input
at y 481-531); from `sm` up the full list is unchanged. Hermetic: reads the template only, so it
pins the structure that produced the measurement, not the pixels.
"""
from __future__ import annotations

import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "src/astro_ai/templates/numerology.html"
TEXT = TEMPLATE.read_text(encoding="utf-8")


def _ledes() -> list[str]:
    header = re.search(r"<header class=\"text-center\">(.*?)</header>", TEXT, re.S)
    assert header, "the form-state <header> is gone"
    return re.findall(r'<p class="([^"]*)">', header.group(1))


def test_long_lede_is_hidden_below_sm():
    classes = _ledes()
    long_ones = [c for c in classes if "hidden" in c.split() and "sm:block" in c.split()]
    assert len(long_ones) == 1, classes


def test_a_short_lede_shows_only_below_sm():
    classes = _ledes()
    short = [c for c in classes if "sm:hidden" in c.split()]
    assert len(short) == 1, classes
    assert "hidden" not in short[0].split(), "a bare `hidden` would hide it at every width"


def test_full_lede_text_survives_for_sm_and_up():
    assert "Chaldean and Lo Shu grid calculators" in TEXT
    assert "per-number remedies (gemstone, colour, deity, mantra)" in TEXT


def test_tradition_note_is_untouched_and_stays_visible():
    # The issue's one hard constraint: the grounding line is not trimmed or hidden.
    m = re.search(r"<details class=\"([^\"]*)\">.*?<strong>Note:</strong> (.*?) <span", TEXT, re.S)
    assert m
    assert "hidden" not in m.group(1).split()
    assert m.group(2) == "Numerology is a modern Western tradition, not classical Vedic Jyotish."
