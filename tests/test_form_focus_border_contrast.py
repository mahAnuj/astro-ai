"""The focused form-field border is >= 3:1 on the surface it sits on — #732.

Before: every text field's focus state was a 1px saffron border (#E4913C), 2.50:1
on white, under WCAG 1.4.11's 3:1. Nothing failed and nothing rendered wrong, and
`verify_contrast.py` had no focus check, so no gate could see it.

One rule in base.html repaints the border for the 59 utilities that carry it.
These tests assert it on the SERVED page (not the template source), so a rule
that is present but not reaching the browser is also caught, and drive the
verify_contrast gate so the two cannot disagree.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("verify_contrast", ROOT / "scripts" / "verify_contrast.py")
vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vc)

PAGES = ["/", "/kundli", "/matching", "/numerology"]
RULE = re.compile(
    r'input\[class\*="focus:border-bhagya-saffron"\]:focus,\s*'
    r'textarea\[class\*="focus:border-bhagya-saffron"\]:focus,\s*'
    r'select\[class\*="focus:border-bhagya-saffron"\]:not\(\[name="lang"\]\):focus\s*'
    r"\{\s*border-color:\s*#([0-9A-Fa-f]{6})\s*;\s*\}"
)


@pytest.mark.parametrize("path", PAGES)
def test_served_page_carries_a_focus_border_rule_that_passes_3_to_1(client, path):
    html = client.get(path).text
    m = RULE.search(html)
    assert m, f"{path}: no focus-border override in the served <style> (saffron 2.50:1 is back)"
    rgb = tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    for name, surface in (("white", (255, 255, 255)), ("cream", (250, 246, 239)), ("cream-2", (241, 231, 216))):
        ratio = vc.contrast_ratio(rgb, surface)
        assert ratio >= 3.0, f"{path}: focus border #{m.group(1)} on {name} is {ratio:.2f}:1, needs 3:1"


@pytest.mark.parametrize("path", ["/numerology", "/matching"])
def test_the_fields_the_issue_measured_still_carry_the_selector_hook(client, path):
    """The rule matches on the class substring; a field that loses it would fall back to nothing."""
    html = client.get(path).text
    assert re.search(r"<input\b[^>]*focus:border-bhagya-saffron", html), (
        f"{path}: no <input> carries focus:border-bhagya-saffron, so the override matches nothing here"
    )


def test_language_picker_keeps_its_saffron_border_on_the_night_nav(client):
    html = client.get("/numerology").text
    sel = re.search(r'<select\b[^>]*name="lang"[^>]*>', html)
    assert sel and "focus:border-bhagya-saffron" in sel.group(0), "lang picker changed shape"
    assert ':not([name="lang"])' in html, (
        "the override would repaint the night-nav language picker dark-on-dark"
    )


def test_gate_5_passes_on_the_tree():
    colours = vc.emitted_colours(vc.BUILT_CSS.read_text(encoding="utf-8"))
    for util, rgb in vc.config_bhagya_colours().items():
        colours.setdefault(util, rgb)
    assert vc.gate_5_focus_border(colours) == []


def test_gate_5_goes_red_when_the_border_is_saffron_again(monkeypatch):
    colours = {"bg-white": (255, 255, 255), "bg-bhagya-cream": (250, 246, 239),
               "bg-bhagya-cream-2": (241, 231, 216)}
    real = vc.focus_rule
    monkeypatch.setattr(vc, "focus_rule", lambda text: (real(text)[0], (228, 145, 60)))
    fails = vc.gate_5_focus_border(colours)
    assert any("2.50:1" in f for f in fails), fails


def test_gate_5_goes_red_when_the_rule_is_missing(monkeypatch):
    monkeypatch.setattr(vc, "focus_rule", lambda text: None)
    fails = vc.gate_5_focus_border({})
    assert fails and "no" in fails[0]
