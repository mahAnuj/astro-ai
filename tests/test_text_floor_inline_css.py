"""#924: the 12px mobile text floor also covers `font-size` inside a template's own `<style>`.

#921 declared 14 templates floor-clean on the strength of a gate that read only `text-[Npx]`
utility classes. Two inline rules sat under 12px the whole time: `.callout-label` in
learn_article_base.html (0.7rem = 11.2px, on every /learn article) and the muhurat card labels
in muhurat_finder.html (10px, below 1024px). Hermetic: reads files, no network, no route.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "src" / "astro_ai" / "templates"

_spec = importlib.util.spec_from_file_location(
    "verify_redesign_tokens_924", ROOT / "scripts" / "verify_redesign_tokens.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gate
_spec.loader.exec_module(gate)


def _rule_font_px(template: str, selector_fragment: str) -> float:
    """Computed px of the `font-size` declared in the rule whose selector contains the fragment."""
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    m = re.search(re.escape(selector_fragment) + r"[^{]*\{([^}]*)\}", text)
    assert m, f"rule {selector_fragment!r} not found in {template}"
    d = re.search(r"font-size\s*:\s*([\d.]+)(px|rem)", m.group(1))
    assert d, f"no px/rem font-size in {selector_fragment!r} of {template}"
    return float(d.group(1)) * (16 if d.group(2) == "rem" else 1)


def test_real_tree_passes_the_text_floor_gate_including_inline_css():
    assert gate.gate_3_text_floor() == []


def test_inline_scan_flags_px_and_rem_under_the_floor_inside_style():
    text = ("<div>\n<style>\n"
            "  .a { font-size: 10px; }\n"
            "  .b { font-size: 0.7rem; }\n"
            "</style>\n")
    hits = gate.inline_css_sub_floor(text)
    assert [(n, decl) for n, decl, _px, _line in hits] == [
        (3, "font-size: 10px"), (4, "font-size: 0.7rem")]
    assert [round(px, 1) for _n, _d, px, _l in hits] == [10.0, 11.2]


def test_inline_scan_passes_the_floor_and_ignores_text_outside_style():
    text = ("<p style=\"font-size: 9px\">x</p>\n<style>\n"
            "  .a { font-size: 12px; }\n"
            "  .b { font-size: 0.75rem; }\n"
            "  .c { font-size: 1.25rem; }\n"
            "</style>\n<p class=\"x\">font-size: 8px in prose</p>\n")
    assert gate.inline_css_sub_floor(text) == []


def test_gate_fails_and_names_file_and_line_for_an_inline_regression(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "t.html"
    bad.write_text("<style>\n.x { font-size: 0.7rem; }\n</style>\n", encoding="utf-8")
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "TEXT_FLOOR_CLEAN", ("t.html",))
    failures = gate.gate_3_text_floor()
    assert len(failures) == 1 and "t.html:2" in failures[0] and "0.7rem" in failures[0]


def test_callout_label_is_at_least_12px():
    assert _rule_font_px("learn_article_base.html", ".article-prose .callout-label") >= 12


def test_muhurat_card_label_is_at_least_12px():
    assert _rule_font_px("muhurat_finder.html", ".mu-cards tbody td[data-label]::before") >= 12
