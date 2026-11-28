"""#1325 (slice 6 of #1017): the muhurat landing pages show the next auspicious dates for
New Delhi, computed by `muhurat.find_candidates` at render time and cached per IST day.

What is pinned here is what a visitor and a crawler get, not what the cache does inside:
the dates, their order, the provenance label, once-per-(event, IST day) computation, the
today/tomorrow line, vivah's disclosure (#1017 slice 8) and that no event filters an Abujha row
(#1346: Abujha is a booster after the exclusions, so the finder's verdict is shown as it is), and a
page that still renders when the computation or the geocode fails.

ORDER (the one judgement call): `find_candidates` returns best-tier-first, so the issue's
"same order" read literally would list the five best-RATED dates of the window, possibly
80 days out. The landing is headed "Next N", so it lists the five EARLIEST auspicious dates
in date order (date is only the last key of `muhurat.rank_key`, after tier, couple verdict
and score, so the sort is the landing's own and must stay). `test_landing_lists_exactly_the_
five_earliest...` pins that and asserts its own premise: that the two orders differ.

No network (geocoding is stubbed to New Delhi) and no LLM. Mutation rows:
scripts/mutations/2026_11_21_1325_landing_dates.py and
scripts/mutations/2026_11_21_1017_vivah_landing_dates.py.
"""
from __future__ import annotations

import dataclasses
import html as html_lib
import logging
import re
from datetime import date
from pathlib import Path

import pytest
from markupsafe import escape

DELHI = (28.61, 77.21, "Asia/Kolkata")
TODAY = date(2026, 11, 21)
CITY = "New Delhi, India"
EVENTS = [("griha-pravesh", "griha_pravesh"), ("vidyarambh", "vidyarambh"),
          ("namkaran", "namkaran"), ("business", "business")]
SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai"


@pytest.fixture(autouse=True)
def _delhi_and_pinned_day(monkeypatch):
    """Every place is Delhi and the IST day is 2026-11-21, unless a test says otherwise."""
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)
    monkeypatch.setattr(route, "reading_today", lambda: TODAY)


@pytest.fixture
def calls(monkeypatch):
    """Count find_candidates calls (the real function still runs)."""
    from astro_ai import muhurat

    real = muhurat.find_candidates
    seen: list[tuple] = []

    def counting(*a, **k):
        seen.append(a)
        return real(*a, **k)

    monkeypatch.setattr(muhurat, "find_candidates", counting)
    return seen


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _section(html: str) -> str:
    m = re.search(r'<section id="next-dates".*?</section>', html, flags=re.S)
    return m.group(0) if m else ""


def _listed(html: str) -> list[str]:
    """The dates in the <ol>, as printed (e.g. 'Nov 25, 2026'), in page order."""
    ol = re.search(r"<ol.*?</ol>", _section(html), flags=re.S)
    return re.findall(r"[A-Z][a-z]{2} \d\d, \d{4}", ol.group(0)) if ol else []


def _fmt(d: date) -> str:
    return d.strftime("%b %d, %Y")


def _rows(event: str, today: date = TODAY):
    from astro_ai import muhurat

    return muhurat.find_candidates(event, CITY, today, 90)


def _auspicious_earliest(rows, n: int = 5):
    from astro_ai.muhurat import AUSPICIOUS_RATINGS

    return sorted((c for c in rows if c.rating in AUSPICIOUS_RATINGS), key=lambda c: c.d)[:n]


@pytest.mark.parametrize("slug,event", EVENTS)
def test_landing_lists_exactly_the_five_earliest_auspicious_dates_per_event(client, slug, event):
    from astro_ai.muhurat import AUSPICIOUS_RATINGS

    rows = _rows(event)
    expected = [_fmt(c.d) for c in _auspicious_earliest(rows)]
    assert len(expected) == 5, "premise: the 90-day window holds five auspicious dates"

    r = client.get(f"/muhurat/{slug}")
    assert r.status_code == 200
    assert _listed(r.text) == expected

    block = re.search(r"<ol.*?</ol>", _section(r.text), flags=re.S).group(0)
    for c in rows:
        if c.rating not in AUSPICIOUS_RATINGS:
            assert _fmt(c.d) not in block, f"{c.rating} date {c.d} is listed as auspicious"

    if event == "griha_pravesh":
        assert any(c.rating == "caution" for c in rows), "premise: a caution row sits in the window"
        finder_order = [c.d for c in rows if c.rating in AUSPICIOUS_RATINGS][:5]
        assert finder_order != [c.d for c in _auspicious_earliest(rows)], (
            "premise: the finder's tier order and date order differ, or the order decision is untested")


def test_provenance_label_names_function_city_zone_and_computation_date(client):
    text = _text(client.get("/muhurat/griha-pravesh").text)
    assert "Computed by this site's Muhurat Finder for New Delhi, India (Asia/Kolkata)" in text
    assert "on Nov 21, 2026" in text
    assert "enter your city" in text


def test_one_find_candidates_call_per_event_per_ist_day(client, calls, monkeypatch):
    from astro_ai.routes import muhurat as route

    for _ in range(3):
        assert client.get("/muhurat/griha-pravesh").status_code == 200
    assert len(calls) == 1
    client.get("/muhurat/namkaran")
    assert len(calls) == 2

    monkeypatch.setattr(route, "reading_today", lambda: date(2026, 11, 22))
    r = client.get("/muhurat/griha-pravesh")
    assert len(calls) == 3, "a new IST day did not recompute"
    assert "on Nov 22, 2026" in _text(r.text)

    monkeypatch.setattr(route, "reading_today", lambda: TODAY)
    client.get("/muhurat/griha-pravesh")
    assert len(calls) == 3, "the 2026-11-21 key was not still cached"


def test_find_candidates_runs_through_the_threadpool_not_on_the_loop(client, monkeypatch):
    from astro_ai import hot_cache
    from astro_ai.routes import muhurat as route

    real = route.run_in_threadpool
    awaited: list[tuple] = []

    async def spy(fn, *args, **kwargs):
        awaited.append((fn, args))
        return await real(fn, *args, **kwargs)

    monkeypatch.setattr(route, "run_in_threadpool", spy)
    r = client.get("/muhurat/griha-pravesh")
    assert len(awaited) == 1
    fn, args = awaited[0]
    assert fn is hot_cache.get_or_compute
    assert args[0] == "muhurat:landing:griha_pravesh:2026-11-21"
    assert len(_listed(r.text)) == 5


def test_today_tomorrow_line_agrees_with_find_candidates_for_both_dates(client, monkeypatch):
    from astro_ai.routes import muhurat as route

    def block(html: str) -> str:
        return _text(_section(html).split("Today and tomorrow")[1].split("Computed by")[0])

    # Both days are `avoid` at the pinned date: the stored reason is shown verbatim.
    rows = {c.d: c for c in _rows("griha_pravesh")}
    html = client.get("/muhurat/griha-pravesh").text
    text = block(html)
    for d in (TODAY, date(2026, 11, 22)):
        assert rows[d].rating == "avoid", "premise: the pinned days are excluded"
        assert _fmt(d) in text
        assert str(escape(rows[d].reason)) in _section(html), rows[d].reason
    assert text.count("not auspicious") == 2

    # An auspicious day says so and carries no reason line.
    good = date(2026, 11, 25)
    rows = {c.d: c for c in _rows("griha_pravesh", good)}
    assert rows[good].rating in ("excellent", "good", "acceptable")
    monkeypatch.setattr(route, "reading_today", lambda: good)
    html = client.get("/muhurat/griha-pravesh").text
    first = _text(_section(html).split("Today and tomorrow")[1]).split(_fmt(date(2026, 11, 26)))[0]
    assert _fmt(good) in first and "auspicious." in first and "not auspicious" not in first
    assert "The finder's note" not in first

    # A caution day says "use with caution" and shows the reason.
    caution = next(c for c in _rows("griha_pravesh") if c.rating == "caution")
    again = {c.d: c for c in _rows("griha_pravesh", caution.d)}
    assert again[caution.d].rating == "caution", "premise: a date's rating does not depend on the window start"
    monkeypatch.setattr(route, "reading_today", lambda: caution.d)
    html = client.get("/muhurat/griha-pravesh").text
    assert "use with caution" in _text(_section(html).split("Today and tomorrow")[1])
    assert str(escape(caution.reason)) in html


@pytest.mark.parametrize("slug", ["vidyarambh", "namkaran", "business", "vivah"])
def test_today_tomorrow_only_on_griha_pravesh(client, slug):
    r = client.get(f"/muhurat/{slug}")
    assert "Next 5 auspicious" in r.text
    assert "Today and tomorrow" not in r.text


def _disclosure(html: str) -> str:
    """The vivah caveat paragraph, unescaped, whitespace-collapsed ('' when absent)."""
    m = re.search(r"<p[^>]*>\s*It checks the day only.*?</p>", _section(html), flags=re.S)
    return html_lib.unescape(_text(m.group(0))).strip() if m else ""


def test_vivah_landing_lists_the_earliest_five_auspicious_dates(client):
    """#1017 slice 8: vivah lists the five earliest auspicious dates the finder returns, with no
    display filter (#1346 removed the interim Abujha one: the finder no longer rates a Panchak day
    excellent, so there is nothing to hide)."""
    rows = _rows("vivah")
    expected = [_fmt(c.d) for c in _auspicious_earliest(rows)]
    assert len(expected) == 5, "premise: five auspicious dates in the window"

    r = client.get("/muhurat/vivah")
    assert r.status_code == 200
    assert _listed(r.text) == expected
    from astro_ai.muhurat import EVENT_LANDING, EVENT_RULES

    assert f"Next 5 auspicious {EVENT_RULES['vivah']['label']} dates" in _text(r.text)
    # Carried over from the deleted test_vivah_landing_unchanged_and_never_computes (chief's ruling
    # on PR #1348): the page's own hero and first criteria line must still render, and the form must
    # still post to /muhurat. Those were the only render-level checks of the vivah copy.
    landing = EVENT_LANDING["vivah"]
    assert str(escape(landing["hero_title"])) in r.text
    assert str(escape(landing["rules_summary"][0])) in r.text
    assert 'action="/muhurat"' in r.text


def test_vivah_landing_carries_the_disclosure_beside_the_list(client):
    """The auditor's R9 disclosure sits in the list's section, after the provenance line, in this
    order. The Rao quote is tied to its corpus source so it cannot be reworded off-corpus, and the
    paragraph never says 'classical' (test_muhurat_classical_copy.py would fail on it)."""
    html = client.get("/muhurat/vivah").text
    text = html_lib.unescape(_text(_section(html)))
    needles = [
        "Computed by this site's Muhurat Finder for New Delhi, India (Asia/Kolkata)",
        "on Nov 21, 2026",
        "It checks the day only",
        "does not read the rising sign (lagna) or the state of the 7th house",
        "merely guidelines and not final recommendations",
        "planetary strength matters more than the thumb-rules",
        "not from the texts this site is built on",
        "a starting point to take to a priest, not a confirmed muhurat",
    ]
    at = -1
    for needle in needles:
        nxt = text.find(needle, at + 1)
        assert nxt > at, f"{needle!r} missing or out of order"
        at = nxt
    ref = (SRC / "knowledge" / "vedic_reference.md").read_text()
    assert "merely guidelines and not final recommendations" in re.sub(r"\s+", " ", ref)
    para = _disclosure(html)
    assert para and "classical" not in para.lower()


def test_the_disclosure_is_vivah_only(client):
    """The other four events' rules were sourced in #1058; the vivah caveats are not theirs."""
    for slug, _event in EVENTS:
        assert "It checks the day only" not in client.get(f"/muhurat/{slug}").text, slug


def test_vivah_landing_failure_still_renders_200(client, monkeypatch):
    """A failed compute omits the section and the caveat with it (nothing to disclaim)."""
    from astro_ai import muhurat

    def boom(*a, **k):
        raise ValueError("compute failed")

    monkeypatch.setattr(muhurat, "find_candidates", boom)
    r = client.get("/muhurat/vivah")
    assert r.status_code == 200
    assert 'action="/muhurat"' in r.text and "Criteria checked" in r.text
    assert 'id="next-dates"' not in r.text and "<ol" not in r.text
    assert "It checks the day only" not in r.text


def test_vivah_computes_once_per_ist_day_in_the_threadpool(client, monkeypatch):
    """Three GETs make one find_candidates call, with the fixed city, the IST day and the 90-day
    window, and no chart: nothing personal can reach a public landing page."""
    from astro_ai import hot_cache, muhurat
    from astro_ai.routes import muhurat as route

    real = muhurat.find_candidates
    seen: list[tuple] = []

    def spy(*a, **k):
        seen.append((a, k))
        return real(*a, **k)

    monkeypatch.setattr(muhurat, "find_candidates", spy)
    awaited: list[tuple] = []
    real_pool = route.run_in_threadpool

    async def pool_spy(fn, *args, **kwargs):
        awaited.append((fn, args))
        return await real_pool(fn, *args, **kwargs)

    monkeypatch.setattr(route, "run_in_threadpool", pool_spy)
    for _ in range(3):
        assert client.get("/muhurat/vivah").status_code == 200
    assert seen == [(("vivah", CITY, TODAY, 90), {})]
    assert all(fn is hot_cache.get_or_compute for fn, _ in awaited)
    assert awaited[0][1][0] == "muhurat:landing:vivah:2026-11-21"


@pytest.mark.parametrize("slug,event", EVENTS + [("vivah", "vivah")])
def test_no_landing_event_filters_an_abujha_flagged_row(client, monkeypatch, slug, event):
    """The landing lists the finder's verdict as it is, for all five events (#1346). A row carrying
    the Abujha flag is listed like any other: the finder only sets that flag on a day that cleared
    every exclusion, so there is nothing for the page to drop."""
    from astro_ai import muhurat

    rows = _rows(event)
    first = _auspicious_earliest(rows, 1)[0]
    patched = [dataclasses.replace(c, flags=("abujha_muhurat",)) if c is first else c for c in rows]
    monkeypatch.setattr(muhurat, "find_candidates", lambda *a, **k: patched)
    assert _listed(client.get(f"/muhurat/{slug}").text)[0] == _fmt(first.d)


def test_no_auspicious_dates_in_window_shows_no_section(client, monkeypatch):
    from astro_ai import muhurat

    real = _rows("griha_pravesh")
    avoid = [c for c in real if c.rating == "avoid"]
    caution = [c for c in real if c.rating == "caution"]
    good = [c for c in real if c.rating in muhurat.AUSPICIOUS_RATINGS]
    assert avoid and caution and len(good) >= 3, "premise: the real window has every tier"

    def check(rows, event):
        monkeypatch.setattr(muhurat, "find_candidates", lambda *a, **k: rows)
        r = client.get(f"/muhurat/{event}")
        assert r.status_code == 200
        assert "Next " not in _text(r.text) and "<ol" not in r.text
        assert 'action="/muhurat"' in r.text and "Criteria checked" in r.text

    check(avoid, "griha-pravesh")
    check(caution, "vidyarambh")

    monkeypatch.setattr(muhurat, "find_candidates", lambda *a, **k: avoid + good[:3])
    r = client.get("/muhurat/namkaran")
    assert "Next 3 auspicious" in r.text
    assert len(_listed(r.text)) == 3


def test_failures_leave_the_page_rendering(client, monkeypatch, caplog):
    from astro_ai import chart, muhurat

    real = muhurat.find_candidates
    attempts: list[str] = []

    def boom(event, *a, **k):
        attempts.append(event)
        raise ValueError("compute failed")

    def page_ok(r):
        assert r.status_code == 200
        assert 'action="/muhurat"' in r.text and "Criteria checked" in r.text
        assert 'id="next-dates"' not in r.text and "<ol" not in r.text

    with caplog.at_level(logging.WARNING, logger="astro_ai.routes.muhurat"):
        monkeypatch.setattr(muhurat, "find_candidates", boom)
        page_ok(client.get("/muhurat/griha-pravesh"))
        assert any(rec.levelno == logging.WARNING and "griha_pravesh" in rec.getMessage()
                   for rec in caplog.records)
        # The failure is cached briefly (hot_cache.ERROR_TTL_S): no retry storm.
        page_ok(client.get("/muhurat/griha-pravesh"))
        assert attempts == ["griha_pravesh"]

        monkeypatch.setattr(muhurat, "find_candidates", real)

        def no_geocode(place):
            raise chart.ChartError("Geocoding failed")

        monkeypatch.setattr(chart, "geocode_place", no_geocode)
        page_ok(client.get("/muhurat/vidyarambh"))


def test_landing_and_finder_share_one_auspicious_definition(client, monkeypatch):
    from astro_ai import muhurat

    assert muhurat.AUSPICIOUS_RATINGS == ("excellent", "good", "acceptable")

    monkeypatch.setattr(muhurat, "AUSPICIOUS_RATINGS", ("excellent",))
    excellent = [c for c in _rows("griha_pravesh") if c.rating == "excellent"]
    assert excellent, "premise: the window holds an excellent date"
    landing = client.get("/muhurat/griha-pravesh").text
    assert _listed(landing) == [_fmt(c.d) for c in sorted(excellent, key=lambda c: c.d)[:5]]

    start = date(2026, 11, 14)
    finder_rows = muhurat.find_candidates("griha_pravesh", CITY, start, 60)
    r = client.post("/muhurat", data={"event_type": "griha_pravesh", "city": CITY,
                                      "start_date": start.isoformat(), "days": "60"})
    n = len([c for c in finder_rows if c.rating == "excellent"])
    assert re.search(rf"\b{n} auspicious dates?\b", _text(r.text))

    # No second copy of the set: the literal lives in muhurat.py only.
    for path in ("routes/muhurat.py", "templates/muhurat_landing.html"):
        assert not re.search(r"""['"]acceptable['"]""", (SRC / path).read_text()), path


def test_landing_response_is_not_cdn_cacheable(client):
    r = client.get("/muhurat/griha-pravesh")
    assert "no-store" in r.headers["cache-control"]
