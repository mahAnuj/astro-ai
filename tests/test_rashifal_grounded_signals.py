"""The rashifal is told only what the corpus says, and its tone must match the
evidence (owner, 2026-11-09: "ensure nothing is cooked up but grounded in
astrology rules").

Found by auditing every signal against knowledge/*.md:
* the retrograde line said significations "feel internal/reflective/second-look",
  while grahas.md §13 says a retrograde planet is STRONGER (the "weakened" reading
  is Western) -- a direct contradiction of the corpus;
* the weekday table carried qualities the corpus never gives the planet
  ("rest" for the Moon, "competition, disputes" for Mars, ...);
* popular tithi characters ("quiet resets", "Ganesh energy") reached the prose.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import SimpleNamespace

from astro_ai import llm
from astro_ai.rashifal_quality import tone_conflicts

ROOT = pathlib.Path(__file__).resolve().parents[1]
GRAHAS = (ROOT / "src/astro_ai/knowledge/grahas.md").read_text()


def _signals(monkeypatch, retro=True, tithi_index=29):
    monkeypatch.setattr(llm, "format_day_windows_for_rashifal", lambda *a, **k: "windows")
    planets = [SimpleNamespace(name="Mercury", retrograde=retro, rashi="Libra", nakshatra="Swati"),
               SimpleNamespace(name="Moon", retrograde=False, rashi="Libra", nakshatra="Vishakha")]
    p = SimpleNamespace(weekday="Monday", day_lord="Moon", tithi_index=tithi_index,
                        tithi_paksha="Krishna", tithi_name="Amavasya", tithi_significance="POPULAR")
    return llm._build_rashifal_day_signals(SimpleNamespace(planets=planets), "2026-11-09", "en", p, None)


def test_retrograde_is_stated_as_the_corpus_states_it(monkeypatch):
    line = next(s for s in _signals(monkeypatch) if s.startswith("Planets currently retrograde"))
    assert "STRONGER" in line and "grahas.md §13" in line
    assert "internal/reflective" not in line


def test_every_day_lord_signification_is_the_grahas_md_line():
    for planet, sig in llm._DAY_LORD_SIGNIFIES.items():
        row = next(l for l in GRAHAS.splitlines() if l.startswith(f"| {planet} |"))
        assert row.split("|")[2].strip().lower() == sig.lower(), planet


def test_the_nakshatra_gets_no_invented_qualities(monkeypatch):
    line = next(s for s in _signals(monkeypatch) if s.startswith("Moon today"))
    assert "give it no qualities of its own" in line


def test_the_popular_tithi_character_never_reaches_the_reading(monkeypatch):
    # Both branches: a day on Raman's avoid-list (Amavasya) and one with no caution (the 5th).
    for idx in (29, 4):
        assert not any("POPULAR" in s for s in _signals(monkeypatch, tithi_index=idx)), idx


EV = {"Work": (1, 4), "Money": (1, 3), "Health": (0, 4), "Family": (2, 2),
      "Relationships": (1, 3), "Students": (1, 2)}


def test_a_line_with_no_support_may_not_sound_positive():
    assert tone_conflicts("Health: A great day for your energy.", EV)
    assert not tone_conflicts("Health: Your body needs rest today.", EV)


def test_a_line_with_full_support_may_not_warn():
    assert tone_conflicts("Family: Avoid talks at home today.", EV)
    assert not tone_conflicts("Family: Home feels warm and easy today.", EV)


def test_a_hard_day_may_not_be_called_good():
    body = "This is a good day for you.\n\nWork: Finish old work."
    assert tone_conflicts(body, EV, day_favourable=1)
    assert not tone_conflicts(body, EV, day_favourable=5)


def test_mixed_evidence_is_left_to_the_writer():
    assert not tone_conflicts("Work: Things go well, but avoid haste.", EV)


def test_the_publish_gate_applies_the_tone_check():
    spec = importlib.util.spec_from_file_location("publish_rashifal", ROOT / "scripts" / "publish_rashifal.py")
    pr = importlib.util.module_from_spec(spec); sys.modules["publish_rashifal"] = pr
    spec.loader.exec_module(pr)
    ev = pr._todays_evidence("2026-11-09")
    assert ev[0][0]["Health"] == (0, 4)            # Aries, measured that day
    from astro_ai.rashifal_quality import READER_LABELS
    lines = "\n".join(f"{l}: A plain line." for l in READER_LABELS["en"])
    prose = " ".join(["Finish the work you have already started today."] * 12)
    doc = "\n\n".join(f"## {a['en']} / {a['sa']}\n\n{prose}\n\n{lines}" for a in llm._RASHI_ANCHORS)
    bad = doc.replace("Health: A plain line.", "Health: A great day.", 1)   # Aries' section
    assert not [f for f in pr.validate(doc, "2026-11-09") if "supporting planet" in f]
    assert any("Aries: Health: says 'great'" in f for f in pr.validate(bad, "2026-11-09"))
