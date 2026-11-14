"""Five nitya yogas block a muhurat, not two (#1023).

Raman, Muhurtha (1948), Panchanga Suddhi lines 1343-1346, knowledge/vedic_reference.md
section 29.9: "the 16th (Atiganda) the 9th (Sula) 10th (Ganda) 17th (Vyathipatha) and
27th (Vaidhruti) have deleterious effects upon events which are started or commenced
under them" ("16th" is an OCR slip for 6th). `_BLOCKING_NITYA_YOGAS` held only the
last two, so a day under Atiganda or Ganda rated 'excellent'.

The dates below were read out of `find_candidates` on 2026-11-14 (New Delhi). Raman's
longer marriage-only list is deliberately not applied; see the constant's comment.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from astro_ai import muhurat as m
from astro_ai.chart import _NITYA_YOGA_NAMES

EVENTS = ("vivah", "griha_pravesh", "namkaran", "vidyarambh", "business")
OK_RATINGS = {"acceptable", "good", "excellent"}
# 1-based positions in Raman's list of 27 (his "Sula" is chart.py's "Shula").
FIVE = {6: "Atiganda", 9: "Shula", 10: "Ganda", 17: "Vyatipata", 27: "Vaidhriti"}


def test_the_blocking_set_is_exactly_ramans_five_by_position():
    assert m._BLOCKING_NITYA_YOGAS == set(FIVE.values())
    for pos, name in FIVE.items():
        assert _NITYA_YOGA_NAMES[pos - 1] == name, (pos, name)


def test_the_issue_repro_atiganda_and_ganda_days_are_avoid():
    cands = {c.d: c for c in m.find_candidates("griha_pravesh", "New Delhi", date(2027, 5, 8), 56)}
    for d, yoga in ((date(2027, 5, 8), "Atiganda"), (date(2027, 7, 2), "Ganda")):
        c = cands[d]
        assert c.nitya_yoga == yoga
        assert c.rating == "avoid", (d, c.rating, c.reason)
        assert "nitya_yoga_block" in c.flags
        assert yoga in c.reason and "Raman" in c.reason


def test_no_day_under_a_blocking_yoga_is_acceptable_or_better_for_any_event():
    seen = set()
    for event in EVENTS:
        for c in m.find_candidates(event, "New Delhi", date(2026, 11, 14), 365):
            if c.nitya_yoga in m._BLOCKING_NITYA_YOGAS:
                seen.add(c.nitya_yoga)
                assert c.rating not in OK_RATINGS, (event, c.d, c.nitya_yoga, c.rating)
    # the sweep really reached the three newly blocked yogas
    assert {"Atiganda", "Shula", "Ganda"} <= seen, seen


def test_a_booster_cannot_lift_a_blocked_yoga_day():
    rules = m.EVENT_RULES["vivah"]
    panchang = SimpleNamespace(tithi_name=sorted(rules["good_tithis"])[0])
    nak = sorted(rules["good_nakshatras"])[0]
    rating, reason, flags = m.score_event(
        "vivah", panchang, "Thursday", nak, False, False, "", "",
        {"jupiter": False, "venus": False, "mercury": False},
        nitya_yoga="Ganda", nitya_blocks=True,
        boosters=("Sarvartha Siddhi Yoga (universally auspicious)",))
    assert rating == "avoid" and flags == ("nitya_yoga_block",)
    assert "Ganda" in reason


@pytest.mark.parametrize("name", ["Priti", "Siddhi", "Shubha", "Sukarma"])
def test_ordinary_yogas_do_not_block(name):
    assert name not in m._BLOCKING_NITYA_YOGAS


def test_pages_no_longer_say_only_two_yogas_are_excluded():
    from pathlib import Path
    root = Path(m.__file__).parent / "templates"
    for rel in ("muhurat_finder.html", "panchang.html"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "Vaidhriti/Vyatipata days" not in text, rel
        assert "two most inauspicious yogas" not in text, rel
        assert "Atiganda" in text, rel
