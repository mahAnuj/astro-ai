"""#595: /numerology holds the 12px mobile text floor (#43) and the gate keeps it there.

numerology.html carried nine `text-[9|10|11px]` utilities: the Bhagya-score labels, the Lo Shu
count chips, the 9px "Missing" tag, the arrow-digit chips, the italic subtitle and the
(planet) / count chips. It was the one file #921 left out of the sweep. Hermetic: reads files only.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL = "src/astro_ai/templates/numerology.html"
TEMPLATE = ROOT / REL

_spec = importlib.util.spec_from_file_location(
    "verify_redesign_tokens_595", ROOT / "scripts" / "verify_redesign_tokens.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gate
_spec.loader.exec_module(gate)


def test_numerology_has_no_utility_text_under_12px():
    text = TEMPLATE.read_text(encoding="utf-8")
    bad = [m.group(0) for m in re.finditer(r"text-\[(\d+(?:\.\d+)?)px\]", text)
           if float(m.group(1)) < 12]
    assert bad == []
    assert gate.inline_css_sub_floor(text) == []


def test_missing_tag_and_count_chips_are_text_xs():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r'class="text-xs mt-1 text-bhagya-muted-2 uppercase tracking-wider">Missing<', text)
    assert re.search(r'class="text-xs mt-1 px-1\.5 py-0\.5 rounded-full bg-bhagya-night', text)


def test_numerology_is_pinned_in_the_floor_clean_list():
    assert REL in gate.TEXT_FLOOR_CLEAN


def test_gate_passes_on_the_real_tree():
    assert gate.gate_3_text_floor() == []
