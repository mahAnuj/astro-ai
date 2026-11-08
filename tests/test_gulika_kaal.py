"""Gulika Kaal on `/panchang` — Saturn's part of the eight (#150, slice 1).

The window is `sunrise + (n-1)/8 .. sunrise + n/8` of daylight, where `n` is the
part ruled by Saturn counting Rao's daytime cycle from the weekday lord
(`knowledge/vedic_reference.md` §28.1-28.2, Table 10). The defects this guards
are the ones a wrong table, a dropped guard or a stale template would ship
quietly on a page that claims authority:

  * **A wrong ordinal** — every weekday still prints a plausible window, one
    eighth (~81 min) off, and nothing about it looks broken.
  * **A window on a date with no daylight** — Rahu Kaal printed
    "00:14 — 00:06" at Tromso for exactly this reason (#227). Gulika is the same
    arithmetic on the same span, so it needs the same guard.
  * **Copy that outlives its refutation** — the explainer used to say
    "Yamaganda / Gulikai ... not shown above, deferred to a next release".

The expected ordinals here are re-derived in this file from Rao's 8-slot cycle,
not imported from `chart.py`: a table asserted against itself proves nothing.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]

DELHI = ("New Delhi, India", 28.6139, 77.2090, "Asia/Kolkata")
TROMSO = ("Tromso", 69.6492, 18.9553, "Europe/Oslo")

# Rao Table 10: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, (lord-less),
# entered at the weekday lord. datetime.weekday() order, Monday = 0.
_CYCLE = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", None)
_LORD = ("Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun")


def _saturn_part(weekday: int) -> int:
    return 1 + (_CYCLE.index("Saturn") - _CYCLE.index(_LORD[weekday])) % 8


# One frozen date per weekday, Monday 2026-11-02 .. Sunday 2026-11-08.
WEEK = [f"2026-11-{d:02d}" for d in range(2, 9)]


def _panchang(monkeypatch, city, iso):
    from astro_ai import chart

    name, lat, lon, tz = city
    monkeypatch.setattr(chart, "geocode_place", lambda place: (lat, lon, tz))
    natal = chart.compute_chart("2000-01-01", "12:00", name)
    y, m, d = (int(x) for x in iso.split("-"))
    return chart.compute_panchang(natal, when=datetime(y, m, d, 12, 0, tzinfo=ZoneInfo(tz)))


def _page(client, monkeypatch, city, iso) -> str:
    from astro_ai import chart

    name, lat, lon, tz = city
    monkeypatch.setattr(chart, "geocode_place", lambda place: (lat, lon, tz))
    resp = client.get(f"/panchang/{iso}", params={"city": name})
    assert resp.status_code == 200, f"{name} {iso} returned {resp.status_code}"
    return resp.text


def test_rao_table_10_gives_the_ordinals_the_page_documents():
    """The re-derivation itself, pinned to the table printed in §28.2 so the
    helper above cannot drift: Sun 7, Mon 6, Tue 5, Wed 4, Thu 3, Fri 2, Sat 1."""
    assert [_saturn_part(w) for w in range(7)] == [6, 5, 4, 3, 2, 1, 7]


@pytest.mark.parametrize("iso", WEEK)
def test_gulika_window_is_saturns_part_of_the_table_10_cycle(monkeypatch, iso):
    """Every weekday, at New Delhi: the window is exactly the n-th eighth of
    sunrise-to-sunset, n from Rao's cycle — not from `_GULIKA_SEGMENT`."""
    p = _panchang(monkeypatch, DELHI, iso)
    assert p.daylight_ordinary is True
    n = _saturn_part(datetime.fromisoformat(iso).weekday())
    eighth = (p.sunset - p.sunrise).total_seconds() / 8.0
    got_start = (p.gulika_start - p.sunrise).total_seconds()
    got_end = (p.gulika_end - p.sunrise).total_seconds()
    assert got_start == pytest.approx((n - 1) * eighth, abs=1.0), (
        f"{iso} {p.weekday}: Gulika starts {got_start / 60:.1f} min after sunrise, "
        f"Saturn's part {n} starts {(n - 1) * eighth / 60:.1f}"
    )
    assert got_end == pytest.approx(n * eighth, abs=1.0)
    assert p.sunrise <= p.gulika_start < p.gulika_end <= p.sunset


def test_gulika_never_coincides_with_rahu_kaal():
    """Both are eighths of the same daylight; if the two tables ever agreed on a
    weekday the page would print two cards for one window."""
    from astro_ai.chart import _GULIKA_SEGMENT, _RAHU_KAAL_SEGMENT

    clash = [d for d in range(7) if _GULIKA_SEGMENT[d] == _RAHU_KAAL_SEGMENT[d]]
    assert not clash, f"Gulika and Rahu Kaal share a part on weekdays {clash}"


def test_the_almanac_gate_is_green_and_can_go_red(monkeypatch):
    """Gate 8 of `scripts/verify_panchang_angas.py` drives the seven Drik rows
    and Rao's table. It must pass on the shipped tree — and fail when a row is
    shifted by one eighth, which is what a wrong ordinal looks like. The second
    half is what stops the gate being a printout: it pins both the comparison
    and its 1-minute tolerance, because a widened tolerance passes the shifted
    row.
    """
    from astro_ai import chart

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI[1:])
    spec = importlib.util.spec_from_file_location(
        "verify_panchang_angas_under_test", ROOT / "scripts" / "verify_panchang_angas.py")
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)

    assert gate.gate_8_gulika() == []

    # One eighth of a ~654-minute day is ~82 minutes: move the printed window
    # by that much and BOTH the arithmetic and the app comparison must object.
    iso, abbr, sr, ss, gs, ge = gate.GULIKAI_ALMANAC[0]

    def shift(hhmm: str, minutes: int) -> str:
        total = int(hhmm[:2]) * 60 + int(hhmm[3:]) + minutes
        return f"{total // 60:02d}:{total % 60:02d}"

    monkeypatch.setattr(
        gate, "GULIKAI_ALMANAC", ((iso, abbr, sr, ss, shift(gs, 82), shift(ge, 82)),))
    failures = gate.gate_8_gulika()
    assert any("Saturn's part" in f for f in failures), failures
    assert any("compute_panchang()" in f for f in failures), failures

    # And a wrong table entry must fail Gate 8C on its own.
    monkeypatch.setattr(gate, "GULIKAI_ALMANAC", ())
    monkeypatch.setattr(gate, "_GULIKA_SEGMENT", {**chart._GULIKA_SEGMENT, 5: 2})
    assert any("Sat" in f and "Saturn in part 1" in f for f in gate.gate_8_gulika())


def test_the_page_shows_the_gulika_card_on_an_ordinary_day(client, monkeypatch):
    """2026-11-05 is a Thursday: Saturn's 3rd part of daylight at New Delhi."""
    iso = "2026-11-05"
    p = _panchang(monkeypatch, DELHI, iso)
    html = _page(client, monkeypatch, DELHI, iso)

    assert "Gulika Kaal (avoid)" in html
    window = f"{p.gulika_start:%H:%M} — {p.gulika_end:%H:%M}"
    assert window in html, f"the Gulika window {window} is not on the page"
    # The card sits beside Rahu Kaal's, not somewhere that survives the polar guard.
    assert html.index("Rahu Kaal (avoid)") < html.index("Gulika Kaal (avoid)") < html.index(
        "Abhijit Muhurat (best)")
    # The subtitle states the inference and attributes no prohibition to Rao.
    assert "inferred from Rao and confirmed against a published almanac" in html
    assert "some almanacs differ" not in html


def test_the_deferred_line_names_only_what_is_still_deferred(client, monkeypatch):
    """Defect this guards: the explainer kept saying Gulikai was "not shown
    above, deferred to a next release" after it was shown."""
    html = _page(client, monkeypatch, DELHI, "2026-11-05")
    assert "Yamaganda / Gulikai" not in html
    assert "deferred to a next release" not in html
    assert "<strong>Gulika Kaal</strong>" in html
    assert "<strong>Yamaganda and Brahma Muhurta</strong>" in html


def test_a_polar_day_has_no_gulika_card_and_no_inverted_window(client, monkeypatch):
    """Tromso 2026-05-17 (#227): sunset 00:06 precedes sunrise 01:14, so every
    eighth is negative and each window ends before it starts. The computed
    fields are still populated (llm.py reads them unconditionally), so the page
    is the only thing standing between that and a reader."""
    iso = "2026-05-17"
    p = _panchang(monkeypatch, TROMSO, iso)
    assert p.daylight_ordinary is False
    # Premise, so the absence assertions below cannot be vacuous.
    assert p.gulika_end < p.gulika_start, "Tromso 2026-05-17 no longer inverts; re-pick the date"

    html = _page(client, monkeypatch, TROMSO, iso)
    assert "Gulika Kaal (avoid)" not in html
    assert f"{p.gulika_start:%H:%M} — {p.gulika_end:%H:%M}" not in html
    assert "No ordinary sunrise-to-sunset day" in html
    # The disclosure must name Gulika among the windows it withholds.
    # (The explainer further down names Gulika regardless, so match the sentence.)
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert ("Rahu Kaal, Gulika Kaal, Abhijit Muhurat and Choghadiya are each a "
            "fixed fraction of the sunrise-to-sunset period") in flat


def test_gulika_adds_no_tokens_to_any_llm_prompt(monkeypatch):
    """This slice is page-only. `format_panchang_for_prompt` and the rashifal
    day-window block feed the Groq prompts, whose free-tier budget is the
    ceiling; a Gulika line there is a deliberate, measured decision, not a side
    effect of adding a field. Change this test in the same commit that does it,
    with the token numbers."""
    from astro_ai import chart

    p = _panchang(monkeypatch, DELHI, "2026-11-05")
    for text in (
        chart.format_panchang_for_prompt(p),
        chart.format_day_windows_for_rashifal(p, "en"),
        chart.format_day_windows_for_rashifal(p, "hi"),
    ):
        assert "gulik" not in text.lower()


def test_the_almanac_gate_needs_a_row_for_every_weekday(monkeypatch):
    """Fri/Sun/Mon/Thu shipped first; Sat/Tue/Wed were a stated gap that rested
    on Rao's table alone (#150). Every weekday now has a published-almanac row,
    and dropping any one must turn Gate 8 red rather than quietly reopen the gap.
    """
    from astro_ai import chart

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI[1:])
    spec = importlib.util.spec_from_file_location(
        "verify_panchang_angas_weekday_cover", ROOT / "scripts" / "verify_panchang_angas.py")
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)

    assert {r[1] for r in gate.GULIKAI_ALMANAC} == set(gate._WEEKDAY_ABBR)
    assert gate.gate_8_gulika() == []

    full = gate.GULIKAI_ALMANAC
    for dropped in ("Sat", "Tue", "Wed"):
        rows = tuple(r for r in full if r[1] != dropped)
        monkeypatch.setattr(gate, "GULIKAI_ALMANAC", rows)
        failures = gate.gate_8_gulika()
        assert any(f"no almanac row for {dropped}" in f for f in failures), failures
