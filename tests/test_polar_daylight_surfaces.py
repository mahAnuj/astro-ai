"""No surface may print a daylight window on a date with no daylight span.

Rahu Kaal is a weekday-indexed eighth of the sunrise-to-sunset period and
Abhijit a fifteenth of it (`knowledge/vedic_reference.md` §28); Choghadiya cuts
the same span into eight. `compute_panchang` sets
`DailyPanchang.daylight_ordinary = False` on a date that holds no such span
(#227) — but it still POPULATES the four derived fields, deliberately, because
`llm.py` formats them unconditionally and a None there would crash the email
path. So the flag only helps a surface that reads it, and after #227 exactly
one did. These are the other five (#228).

WHY THE SUB-ARCTIC CASE IS THE ONE PINNED HERE. Gate 6 of
`scripts/verify_panchang_angas.py` already censuses Tromso (69.65N), where the
failure is loud enough to spot: 2026-05-17 produced "Rahu Kaal 00:14–00:06",
a window ending before it starts. Reykjavik is the case nothing catches. It is
a mainstream capital at 64.15N — SOUTH of the Arctic Circle — with 15 such
dates in 2026, and not one of them raises, so the route never degrades and
nothing is logged. On 2026-06-24 it produced **"Rahu Kaal 13:30–16:08"**: a
perfectly ordinary-looking afternoon window, computed as an eighth of a
21-hour "day" that ends at 00:04 the FOLLOWING date. No reader could tell.
Scope a guard to "polar" or to 66.56N and this is exactly what it misses.

Both directions are asserted, on the same weekday and the same date, because a
guard that hides windows from a shipping locale is as broken as one that shows
them at Reykjavik. The assertion is on the CONSEQUENCE — does this rendered
surface contain these clock times — not on the flag's own definition, which
would be a tautology that passes forever.

Hermetic: `geocode_place` is stubbed per city, everything else is really
computed by the Swiss Ephemeris.
"""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

# 2026-06-24, a WEDNESDAY, picked against three constraints that are all
# load-bearing and none obvious:
#   * NOT a Sunday. Rahu Kaal is then the 8th eighth of daylight and ENDS at
#     sunset — and sunset is legitimately still shown on every surface below,
#     so the absence assertion would fail on a string the page is right to
#     print. (Both #227's Tromso date and the midsummer solstice are Sundays.)
#   * Reykjavik must be flagged on it and Mumbai must not, so one date drives
#     both directions.
#   * `find_candidates("business", ...)` must rate it something other than
#     "avoid" at BOTH cities, because `muhurat_finder.html` re-splits the list
#     itself and an "avoid" row never reaches the Windows cell. An earlier
#     draft of this file used a date rated "avoid" and both finder cases
#     passed while rendering no window markup at all — a test that could not
#     fail. `_render_muhurat_finder` now asserts the cell was reached.
DAY = date(2026, 6, 24)

# (lat, lon, tz). Reykjavik 64.1466N/21.9426W and Mumbai 19.0760N/72.8777E.
POLAR = ("Reykjavik", 64.1466, -21.9426, "Atlantic/Reykjavik")
ORDINARY = ("Mumbai", 19.0760, 72.8777, "Asia/Kolkata")


def _panchang(monkeypatch, city_spec):
    """Real chart + real panchang for `city_spec` on DAY, no network."""
    from astro_ai import chart

    name, lat, lon, tz = city_spec
    monkeypatch.setattr(chart, "geocode_place", lambda place: (lat, lon, tz))
    natal = chart.compute_chart("2000-01-01", "12:00", name)
    when = datetime.combine(DAY, datetime.min.time().replace(hour=12), tzinfo=ZoneInfo(tz))
    return chart.compute_panchang(natal, when)


def _window_clock_strings(p) -> set[str]:
    """Every rendering of the four daylight-derived instants, in the formats the
    surfaces actually use — minus anything that is also a sunrise or sunset
    time, which the surfaces are entitled to keep showing.

    Deliberately derived from `p`, not typed out: a literal table here would
    stop failing the day the ephemeris moved a minute, which is the quiet way a
    gate stops being one.
    """
    fmts = ("%H:%M", "%I:%M %p", "%I:%M")
    keep = {d.strftime(f) for d in (p.sunrise, p.sunset) for f in fmts}
    keep |= {s.lstrip("0") for s in keep}
    out = {
        d.strftime(f)
        for d in (p.rahu_kaal_start, p.rahu_kaal_end, p.abhijit_start, p.abhijit_end)
        for f in fmts
    }
    out |= {s.lstrip("0") for s in out}
    return out - keep


def _request(path: str = "/"):
    from starlette.requests import Request

    return Request({
        "type": "http", "method": "GET", "path": path, "raw_path": path.encode(),
        "root_path": "", "headers": [], "query_string": b"", "scheme": "http",
        "server": ("testserver", 80), "client": ("test", 1234), "app": None,
    })


# ─── the five surfaces, each rendered from the SAME DailyPanchang ────────


def _render_strip(p, city):
    from astro_ai.routes.deps import templates

    return templates.env.get_template("_panchang_strip.html").render(
        lang="en", panchang_strip=p, panchang_city=city,
        panchang_moon={"rashi": "Vrishabha Taurus", "nakshatra": "Rohini"},
    )


def _render_today(p, city):
    from astro_ai.routes.deps import templates

    planet = lambda n: SimpleNamespace(  # noqa: E731
        name=n, rashi="Vrishabha", house=3, nakshatra="Rohini", nakshatra_pada=2,
        degree=12.3, longitude=42.3, retrograde=False, sign_lord="Venus", dignity="",
    )
    return templates.env.get_template("today.html").render(
        lang="en", panchang=p, request=_request("/today"),
        transit=SimpleNamespace(planets=[planet("Moon"), planet("Sun")],
                                moment=datetime(2026, 6, 24, 12, 0)),
        natal=SimpleNamespace(lagna_rashi="Mesha", planets=[], birth_place=city),
        details=SimpleNamespace(name="", birth_place=city),
        flags=SimpleNamespace(sade_sati_phase="", sade_sati=False),
        today_pretty="Wednesday, 24 June 2026", today_date="2026-06-24",
        reading="", gochar=[],
    )


def _email(template: str, p, city):
    from astro_ai.routes.deps import templates

    return templates.env.get_template(template).render(
        lang="en", panchang=p, city=city, today_iso="2026-06-24",
        today_pretty="Wednesday, 24 June 2026",
        rashifal_sections=[("♈", "Mesha", "A steady day.", "A steady day, in full.")],
        shlok={"sanskrit": "ॐ", "translit": "om", "meaning": "the syllable",
               "graha": "Sun", "source": "Rig Veda"},
        festivals=[], trivia={"title": "Did you know", "body": "There are 27 nakshatras."},
        site_url="https://shubhagya.com",
        unsubscribe_url="https://shubhagya.com/unsubscribe?email=a@b.c&token=x",
    )


def _render_rashifal_email(p, city):
    return _email("email/daily_rashifal.html", p, city)


def _render_welcome_email(p, city):
    return _email("email/welcome.html", p, city)


def _render_muhurat_finder(p, city):
    """The finder renders `MuhuratCandidate`s, so this goes through
    `find_candidates` — the field values are the thing under test, not the
    panchang directly. `p` is accepted only to keep one signature."""
    from astro_ai import chart, muhurat
    from astro_ai.routes.deps import templates

    cands = muhurat.find_candidates("business", city, DAY, days=1)
    assert cands, "find_candidates returned nothing — the fixture is broken, not the code"
    assert chart  # the geocode stub is installed on this module; keep it imported
    # `avoid_candidates` is NOT passed: the template derives both lists from
    # `candidates` itself, and passing one shadowed nothing while looking as
    # though it did.
    html = templates.env.get_template("muhurat_finder.html").render(
        lang="en", candidates=cands, event_type="business",
        event_label="Business launch", city=city, start=DAY, days=1,
        personal_active=False, couple_active=False, personal_colors={},
        results=True, request=_request("/muhurat"),
    )
    assert 'data-label="Windows"' in html, (
        f"the Windows cell did not render for {city} on {DAY} — every assertion "
        f"about it would be vacuous. Rating was {cands[0].rating!r}; the main "
        "table skips 'avoid' rows, so pick another date or event."
    )
    return html


SURFACES = {
    "homepage strip": _render_strip,
    "/today panchang grid": _render_today,
    "daily rashifal email": _render_rashifal_email,
    "welcome email": _render_welcome_email,
    "muhurat finder": _render_muhurat_finder,
}


def test_reykjavik_midsummer_has_no_ordinary_daylight_span(monkeypatch):
    """The premise, measured rather than assumed — and below the Arctic Circle.

    Without this the five tests below could all pass against a panchang that
    was never flagged, asserting nothing.
    """
    p = _panchang(monkeypatch, POLAR)
    assert p.daylight_ordinary is False
    assert p.sunset.date() != DAY, (
        f"sunset {p.sunset} now falls inside {DAY} — if the ephemeris moved, "
        "re-pick the date rather than deleting the assertion"
    )
    assert POLAR[1] < 66.56, "Reykjavik must stay the SUB-Arctic case this file is about"


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_surface_hides_daylight_windows_when_there_is_no_daylight(monkeypatch, surface):
    p = _panchang(monkeypatch, POLAR)
    assert p.daylight_ordinary is False, "premise broken — see the test above"
    html = SURFACES[surface](p, POLAR[0])
    leaked = sorted(s for s in _window_clock_strings(p) if s in html)
    assert not leaked, (
        f"{surface} printed {leaked} for {POLAR[0]} on {DAY}, where sunrise "
        f"{p.sunrise:%d %b %H:%M} and sunset {p.sunset:%d %b %H:%M} bound no "
        "daylight period inside the date. Those are fractions of a span that "
        "does not exist (#228)."
    )


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_surface_still_shows_them_on_an_ordinary_day(monkeypatch, surface):
    """The other direction. Without it, `return ""` passes every test above."""
    p = _panchang(monkeypatch, ORDINARY)
    assert p.daylight_ordinary is True, "premise broken — Mumbai is an ordinary latitude"
    html = SURFACES[surface](p, ORDINARY[0])
    # EVERY one of the four instants, not merely one of them: a surface that
    # kept Rahu Kaal and dropped Abhijit would otherwise pass.
    fmts = ("%H:%M", "%I:%M %p", "%I:%M")
    missing = [
        f"{label} {d:%H:%M}"
        for label, d in (
            ("rahu_kaal_start", p.rahu_kaal_start), ("rahu_kaal_end", p.rahu_kaal_end),
            ("abhijit_start", p.abhijit_start), ("abhijit_end", p.abhijit_end),
        )
        if not any(d.strftime(f).lstrip("0") in html or d.strftime(f) in html for f in fmts)
    ]
    assert not missing, (
        f"{surface} did not show {missing} for {ORDINARY[0]} on {DAY} — the "
        "guard is withholding windows from a shipping locale (#228)"
    )


def test_muhurat_candidate_fields_are_empty_not_reversed(monkeypatch):
    """`find_candidates` is consumed by more than the finder template, so the
    fields themselves — not only the HTML — must be empty on such a date.

    `rating` is asserted to survive on purpose: tithi, nakshatra and yoga come
    from Sun and Moon longitudes, so the date is still a real candidate. Only
    the sub-day windows go.
    """
    from astro_ai import chart, muhurat

    monkeypatch.setattr(chart, "geocode_place", lambda place: POLAR[1:])
    polar = muhurat.find_candidates("business", POLAR[0], DAY, days=1)[0]
    assert polar.rahu_kaal == ""
    assert polar.abhijit_muhurta == ""
    assert polar.choghadiya == ()
    assert polar.rating, "the date must still be rated — only the windows are unavailable"
    assert polar.tithi, "tithi comes from Sun and Moon longitudes, not from daylength"

    monkeypatch.setattr(chart, "geocode_place", lambda place: ORDINARY[1:])
    plain = muhurat.find_candidates("business", ORDINARY[0], DAY, days=1)[0]
    assert plain.rahu_kaal and plain.abhijit_muhurta
    assert len(plain.choghadiya) == 8


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_surface_says_why_the_windows_are_missing(monkeypatch, surface):
    """Hiding the windows silently is its own wrong answer.

    A reader who has seen Rahu Kaal on this page every other day reads a gap as
    "nothing to avoid today", and on the two email surfaces there is no page to
    go back to and no way to refresh. Every surface must therefore name the
    sunrise-to-sunset period the missing windows are fractions of.

    Asserted as the phrase rather than the exact sentence so copy can be
    reworded — but it is asserted, because without it reverting
    `muhurat_finder.html` alone left the row rendering the label "✓ Abhijit"
    followed by nothing, which passes every absence check above and reads as a
    rendering bug.
    """
    p = _panchang(monkeypatch, POLAR)
    html = SURFACES[surface](p, POLAR[0])
    assert "sunrise-to-sunset" in html.lower(), (
        f"{surface} dropped the windows for {POLAR[0]} on {DAY} without saying "
        "why (#228)"
    )
    if surface == "muhurat finder":
        for label in ("Abhijit </div>", "Rahu Kaal </div>"):
            assert label not in html, (
                f"the finder rendered the bare label {label!r} — an empty value "
                "where a time used to be, with no explanation"
            )
