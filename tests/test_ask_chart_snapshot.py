"""#1167 slice 2 -- each `form_ask` event carries a compact chart summary, and never the birth details.

Owner's ruling, 2026-11-17: the event stores planet signs and houses, the lagna, the Moon
nakshatra and the current mahadasha and antardasha, and "never stores birth date, birth time or
birth place". The purpose is a later audit that grades "your Saturn is in the 7th" against the
chart the answer was written for.

SCOPE, STATED PLAINLY: no model is called. The route tests stub the generator, capture what
`events.record` was handed, and read it back as the JSON the event store would serialise. The
privacy tests are about what CANNOT be in the snapshot, so they build the sentinels from the
chart itself (every longitude, every dasha date) instead of typing a list that could drift.
"""
from __future__ import annotations

import dataclasses
import json
import re
import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient

from astro_ai import chart as chart_mod
from astro_ai.routes import ask as ask_route
from astro_ai.session import SavedChart

BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE = "1990-04-15", "07:30", "New Delhi"
SAVED = SavedChart(id="c1", name="Test", birth_date=BIRTH_DATE,
                   birth_time=BIRTH_TIME, birth_place=BIRTH_PLACE)

# The cache drops an `ask` answer under 100 chars as a bad entry, so a stub shorter
# than that would be regenerated on the second ask and the cache-hit test would
# be testing a miss.
_ANSWER = "SNAPSHOT-ANSWER-1167 " + "A steady, practical year for your work. " * 4

ALLOWED_KEYS = {"lagna", "planets", "moon_nakshatra", "mahadasha", "antardasha"}


def _natal():
    c = chart_mod.compute_chart(BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE)
    return c, chart_mod.compute_dasha_state(c)


def _birth_sentinels(c, d) -> list[str]:
    """Everything that, stored, would let someone recover the birth moment or place."""
    out = ["1990", BIRTH_DATE, BIRTH_TIME, BIRTH_PLACE, "Delhi", "Asia/Kolkata",
           str(c.birth_lat), str(c.birth_lon), c.birth_tz, str(c.birth_utc.year),
           c.birth_utc.isoformat(), str(c.lagna_longitude)]
    for p in c.planets:
        out += [str(p.longitude), f"{p.longitude:.2f}"]
    for per in (d.mahadasha, d.antardasha, d.next_mahadasha, *d.upcoming_antardashas):
        if per is not None:
            out += [per.start.isoformat(), per.end.isoformat(), str(per.years)]
    return out


# --------------------------------------------------------------------------
# the snapshot itself
# --------------------------------------------------------------------------


def test_the_snapshot_has_exactly_the_allow_listed_keys_and_values():
    c, d = _natal()
    snap = ask_route.chart_snapshot(c, d)
    assert set(snap) == ALLOWED_KEYS
    assert snap["lagna"] == c.lagna_rashi
    assert set(snap["planets"]) == {p.name for p in c.planets} and len(snap["planets"]) == 9
    for p in c.planets:
        assert snap["planets"][p.name] == {"rashi": p.rashi, "house": p.house}
    assert snap["moon_nakshatra"] == next(p for p in c.planets if p.name == "Moon").nakshatra
    assert snap["mahadasha"] == d.mahadasha.lord
    assert snap["antardasha"] == d.antardasha.lord


def test_the_snapshot_holds_no_birth_detail_in_any_form():
    c, d = _natal()
    text = json.dumps(ask_route.chart_snapshot(c, d))
    for needle in _birth_sentinels(c, d):
        assert needle not in text, needle
    # No number with a decimal point at all: a longitude or a dasha length would be one.
    assert not re.search(r"\d\.\d", text), text
    # ...and no 4-digit run, which is what a year or a timestamp would be.
    assert not re.search(r"\d{4}", text), text


def test_a_field_added_to_chart_later_does_not_leak_in():
    """The allow-list, not a blacklist: a new Chart or PlanetPosition field stays out."""
    c, d = _natal()
    Wide = dataclasses.make_dataclass(
        "WideChart", [("birth_note", str, "LEAK-CHART-FIELD")],
        bases=(chart_mod.Chart,), frozen=True)
    WidePlanet = dataclasses.make_dataclass(
        "WidePlanet", [("secret", str, "LEAK-PLANET-FIELD")],
        bases=(chart_mod.PlanetPosition,), frozen=True)
    planets = [WidePlanet(**dataclasses.asdict(p)) for p in c.planets]
    wide = Wide(**{**{f.name: getattr(c, f.name) for f in dataclasses.fields(c)},
                   "planets": planets})
    snap = ask_route.chart_snapshot(wide, d)
    assert snap == ask_route.chart_snapshot(c, d)
    assert "LEAK" not in json.dumps(snap)


def test_the_serialised_size_is_small():
    """~533 B measured for a nine-planet chart; the 5000/day events cap makes this ~2.7 MB."""
    c, d = _natal()
    size = len(json.dumps(ask_route.chart_snapshot(c, d), separators=(",", ":")).encode())
    assert size < 700, size


# --------------------------------------------------------------------------
# the route
# --------------------------------------------------------------------------


def _client(monkeypatch):
    from astro_ai.main import app

    monkeypatch.setattr(ask_route, "load_collection",
                        lambda request: SimpleNamespace(active=SAVED))
    monkeypatch.setattr(ask_route.notify, "ask_submitted", lambda **k: None)
    recorded: list[dict] = []
    monkeypatch.setattr(ask_route.events, "record", lambda **k: recorded.append(k))
    generated: list[int] = []

    def fake_generate(**kw):
        generated.append(1)
        return _ANSWER

    monkeypatch.setattr(ask_route, "generate_ask_answer", fake_generate)
    return TestClient(app), recorded, generated


def _question() -> str:
    # Letters only: the whole event is scanned for birth sentinels, and a hex ref
    # would contain "1990" or a time by chance and fail one run in ten thousand.
    ref = "".join("ghijklmnopqrstuv"[int(ch, 16)] for ch in uuid.uuid4().hex[:12])
    return f"Will my work go well this year? ref {ref}"


def _ask_events(recorded):
    return [e for e in recorded if e["type"] == "form_ask"]


def test_a_fresh_generation_records_the_snapshot_and_no_birth_detail(monkeypatch):
    client, recorded, generated = _client(monkeypatch)
    r = client.post("/ask", data={"question": _question(), "category": "career"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text[:200]
    (ev,) = _ask_events(recorded)
    assert ev["data"]["cache_hit"] is False and generated == [1]
    c, d = _natal()
    assert ev["data"]["chart"] == ask_route.chart_snapshot(c, d)
    wire = json.dumps(ev, default=str)
    for needle in _birth_sentinels(c, d):
        assert needle not in wire, needle


def test_a_cache_hit_records_the_snapshot_too(monkeypatch):
    client, recorded, generated = _client(monkeypatch)
    q = _question()
    for _ in range(2):
        r = client.post("/ask", data={"question": q, "category": "career"},
                        follow_redirects=False)
        assert r.status_code == 303, r.text[:200]
    first, second = _ask_events(recorded)
    assert (first["data"]["cache_hit"], second["data"]["cache_hit"]) == (False, True)
    assert generated == [1], "the second ask must be served from cache"
    c, d = _natal()
    expected = ask_route.chart_snapshot(c, d)
    assert first["data"]["chart"] == expected
    assert second["data"]["chart"] == expected
    wire = json.dumps(second, default=str)
    for needle in _birth_sentinels(c, d):
        assert needle not in wire, needle


def test_a_snapshot_failure_still_answers_and_records_without_a_chart_key(monkeypatch):
    client, recorded, _ = _client(monkeypatch)

    def boom(chart, dasha):
        raise RuntimeError("snapshot exploded")

    monkeypatch.setattr(ask_route, "chart_snapshot", boom)
    r = client.post("/ask", data={"question": _question(), "category": "career"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text[:200]
    (ev,) = _ask_events(recorded)
    assert "chart" not in ev["data"]
    assert ev["data"]["answer"] == _ANSWER


def test_matching_context_records_the_seekers_own_chart_not_the_partners(monkeypatch):
    """`chart` is the saved chart; the partner is a separate object that never reaches the event."""
    seeker_c, seeker_d = _natal()
    partner = chart_mod.compute_chart("1993-11-02", "22:10", "Mumbai")
    assert ask_route.chart_snapshot(partner, seeker_d) != ask_route.chart_snapshot(
        seeker_c, seeker_d), "fixture needs two different charts"
    client, recorded, _ = _client(monkeypatch)
    # No matching record exists, so the route downgrades to chart context: the
    # snapshot must still be the seeker's, and `context` says what happened.
    r = client.post("/ask", data={"question": _question(), "category": "marriage",
                                  "context": "matching"}, follow_redirects=False)
    assert r.status_code == 303, r.text[:200]
    (ev,) = _ask_events(recorded)
    assert ev["data"]["chart"] == ask_route.chart_snapshot(seeker_c, seeker_d)
