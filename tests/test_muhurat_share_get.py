"""#1336 (slice 5 of #1017): a finder result has a URL, and a search with no auspicious date
names the next one.

R7: `GET /muhurat?event=&city=&start=&days=` is the basic-mode POST, reached by a link. It
renders the same date rows, answers a bad event or date with the same 400, clamps `days` the
same way, is noindex with a canonical on the event landing, and never carries personal, couple
or Namkaran input (neither in, nor out). The page offers a "Share these dates" link only for a
basic search.

R8: a search whose rows hold no excellent/good/acceptable date scans forward, 60 days a call,
from the day after the window and up to 365 days past its end, and names the EARLIEST
auspicious date it finds (the finder returns rows best-tier-first, so `[0]` would be wrong).

A GET fires no `notify.muhurat_computed` and no `muhurat_searched` event, and a bad city on a
GET does not page the owner. All blocking work goes through `run_in_threadpool`.

No network (geocoding is stubbed) and no LLM. Mutation rows:
scripts/mutations/2026_11_21_1336_muhurat_share_get.py.
"""
from __future__ import annotations

import dataclasses
import html as htmllib
import inspect
import re
import threading
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

CITY = "Delhi, India"
DELHI = (28.61, 77.21, "Asia/Kolkata")
TODAY = date(2026, 11, 21)
START = date(2026, 11, 22)
# A window wholly inside Kharmas: no auspicious date for these events (checked by
# `_zero_window_premise` in each test that uses it, not assumed).
KHARMAS = date(2026, 12, 20)
EVENTS = ["vivah", "griha_pravesh", "vidyarambh", "namkaran", "business"]


@pytest.fixture(autouse=True)
def _pinned(monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)
    monkeypatch.setattr(route, "reading_today", lambda: TODAY)


@pytest.fixture
def calls(monkeypatch):
    """Record every find_candidates call as a normalised (event, city, start, days); the real
    function still runs. Also notes whether it ran on the thread that served the request."""
    from astro_ai import muhurat

    real = muhurat.find_candidates
    sig = inspect.signature(real)
    seen: list[dict] = []

    def recording(*a, **k):
        b = sig.bind(*a, **k)
        b.apply_defaults()
        seen.append({"event": b.arguments["event_type"], "city": b.arguments["city"],
                     "start": b.arguments["start"], "days": b.arguments["days"],
                     "thread": threading.get_ident()})
        return real(*a, **k)

    monkeypatch.setattr(muhurat, "find_candidates", recording)
    return seen


def _text(h: str) -> str:
    """Page text with tags removed and the space a tag leaves before punctuation closed up."""
    return re.sub(r" ([.,)])", r"\1", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


def _tables(h: str) -> list[str]:
    return re.findall(r"<table.*?</table>", h, flags=re.S)


def _hrefs(h: str) -> list[str]:
    return [htmllib.unescape(x) for x in re.findall(r'href="([^"]*)"', h)]


def _robots(h: str) -> str:
    return re.search(r'<meta name="robots" content="([^"]*)">', h).group(1)


def _canonicals(h: str) -> list[str]:
    return re.findall(r'<link rel="canonical" href="([^"]*)">', h)


def _share(h: str) -> str | None:
    m = re.search(r'<a href="([^"]*)"[^>]*>Share these dates</a>', h)
    return htmllib.unescape(m.group(1)) if m else None


def _site() -> str:
    from astro_ai.routes.deps import templates

    return templates.env.globals["site_url"]


def _get(client, event="griha_pravesh", city=CITY, start=START, days=60, **extra):
    q = {"event": event, "city": city, "start": start.isoformat(), "days": days, **extra}
    return client.get("/muhurat", params=q)


def _post(client, event="griha_pravesh", city=CITY, start=START, days=60, **extra):
    return client.post("/muhurat", data={"event_type": event, "city": city,
                                         "start_date": start.isoformat(), "days": str(days),
                                         **extra})


def _fmt(d: date) -> str:
    return d.strftime("%b %d, %Y")


def _auspicious(rows):
    from astro_ai.muhurat import AUSPICIOUS_RATINGS

    return [c for c in rows if c.rating in AUSPICIOUS_RATINGS]


def _zero_window(event="griha_pravesh", days=20):
    """A Kharmas window with no auspicious date, and the first auspicious date after it found
    by ONE independent 365-day call (the code under test scans in 60-day chunks)."""
    from astro_ai import muhurat

    rows = muhurat.find_candidates(event, CITY, KHARMAS, days)
    assert not _auspicious(rows), "premise: the window holds no auspicious date"
    after = KHARMAS + timedelta(days=len(rows))
    later = _auspicious(muhurat.find_candidates(event, CITY, after, 365))
    assert later, "premise: an auspicious date exists within 365 days"
    return min(c.d for c in later)


# --- R7: the GET is the POST -------------------------------------------------------------


@pytest.mark.parametrize("event", EVENTS)
def test_get_and_post_render_identical_date_rows(client, event):
    g, p = _get(client, event), _post(client, event)
    assert g.status_code == p.status_code == 200
    assert _tables(g.text) and _tables(g.text) == _tables(p.text)
    assert _text(_tables(g.text)[0]) == _text(_tables(p.text)[0])
    headline = r"\d+ auspicious dates? found in \d+-day search from [\d-]+"
    assert re.search(headline, _text(g.text)).group(0) == re.search(headline, _text(p.text)).group(0)


@pytest.mark.parametrize("event", EVENTS)
def test_a_get_result_is_noindex_with_a_canonical_on_the_event_landing(client, event):
    r = _get(client, event)
    assert _robots(r.text) == "noindex, follow"
    assert _canonicals(r.text) == [f"{_site()}/muhurat/{event.replace('_', '-')}"]


def test_bare_get_and_post_keep_index_follow_and_the_finder_canonical(client):
    for r in (client.get("/muhurat"), _post(client)):
        assert _robots(r.text) == "index, follow"
        assert _canonicals(r.text) == [f"{_site()}/muhurat"]


def test_an_invalid_event_canonicalises_to_the_finder_and_is_still_noindex(client):
    r = _get(client, "not_an_event")
    assert r.status_code == 400
    assert _robots(r.text) == "noindex, follow"
    assert _canonicals(r.text) == [f"{_site()}/muhurat"]


def test_get_without_city_and_start_is_todays_bare_form(client):
    bare = client.get("/muhurat")
    assert bare.status_code == 200 and "candidates for" not in bare.text
    for q in ({}, {"event": "griha_pravesh"}, {"city": CITY}, {"start": "2026-11-22"},
              {"city": "  ", "start": "2026-11-22"}, {"event": "griha_pravesh", "days": 30}):
        r = client.get("/muhurat", params=q)
        assert r.status_code == 200 and r.text == bare.text, q


@pytest.mark.parametrize("kwargs,message", [
    ({"event": "not_an_event"}, "Unknown event type: not_an_event"),
    ({"start": None}, "Invalid start date."),
])
def test_get_invalid_event_or_date_is_the_same_400_as_post(client, kwargs, message):
    if kwargs.get("start", 1) is None:
        g = client.get("/muhurat", params={"event": "griha_pravesh", "city": CITY,
                                           "start": "2026-13-45", "days": 60})
        p = client.post("/muhurat", data={"event_type": "griha_pravesh", "city": CITY,
                                          "start_date": "2026-13-45", "days": "60"})
    else:
        g, p = _get(client, **kwargs), _post(client, event=kwargs["event"])
    assert g.status_code == p.status_code == 400
    assert message in g.text and message in p.text
    assert _text(g.text.split("<main")[1].split("<form")[0]) == \
        _text(p.text.split("<main")[1].split("<form")[0])


@pytest.mark.parametrize("days,rows", [(9999, 365), (0, 1), (-5, 1), (400, 365), (60, 60)])
def test_days_is_clamped_exactly_as_post_clamps_it(client, calls, days, rows):
    g = _get(client, days=days)
    p = _post(client, days=days)
    assert g.status_code == p.status_code == 200
    assert f"{rows}-day search" in _text(g.text) and f"{rows}-day search" in _text(p.text)
    assert calls[0]["days"] == days  # the route passes it through; the finder clamps
    assert parse_qs(urlparse(_share(g.text)).query)["days"] == [str(rows)]
    assert _tables(g.text) == _tables(p.text)


def test_a_non_integer_days_is_refused_like_post(client):
    g = client.get("/muhurat", params={"event": "vivah", "city": CITY,
                                       "start": "2026-11-22", "days": "soon"})
    p = client.post("/muhurat", data={"event_type": "vivah", "city": CITY,
                                      "start_date": "2026-11-22", "days": "soon"})
    assert g.status_code == p.status_code == 422


def test_a_city_over_100_characters_is_a_400_and_never_geocodes(client, monkeypatch):
    from astro_ai import chart

    seen: list[str] = []
    monkeypatch.setattr(chart, "geocode_place", lambda place: seen.append(place) or DELHI)
    long_city = "x" * 101
    for r in (_get(client, city=long_city), _post(client, city=long_city)):
        assert r.status_code == 400
        assert "City is too long." in r.text
        assert long_city not in r.text, "the oversized string is echoed back"
    assert seen == []
    ok = _get(client, city="y" * 100)
    assert ok.status_code == 200 and seen, "100 characters is still accepted"


# --- the share link ----------------------------------------------------------------------


def test_the_share_link_is_the_exact_basic_get_url(client):
    r = _post(client, "business", days=45)
    href = _share(r.text)
    u = urlparse(href)
    assert f"{u.scheme}://{u.netloc}" == _site() and u.path == "/muhurat"
    assert parse_qs(u.query, keep_blank_values=True) == {
        "event": ["business"], "city": [CITY], "start": [START.isoformat()], "days": ["45"]}
    assert [k for k, _ in re.findall(r"([a-z_]+)=([^&]*)", u.query)] == ["event", "city", "start", "days"]
    # the link reproduces the page it came from
    path = href[len(_site()):]
    assert _tables(_get(client, "business", days=45).text) == _tables(client.get(path).text) \
        == _tables(r.text)


def test_extra_query_parameters_are_ignored_by_get(client):
    base = _get(client)
    r = _get(client, bride_name="Zzyzx", bride_dob="1990-01-01", child_dob="2020-02-02",
             groom_place="Pune", use_personal="1", child_time="10:00")
    assert r.status_code == 200
    assert _tables(r.text) == _tables(base.text)
    for needle in ("Zzyzx", "1990-01-01", "2020-02-02", "Pune"):
        assert needle not in r.text
    assert set(parse_qs(urlparse(_share(r.text)).query)) == {"event", "city", "start", "days"}


@pytest.mark.parametrize("city", ["Köln & Düsseldorf #1", "A+B C", "São Paulo, Brasil", "देहरादून", "a/b?c=d"])
def test_the_share_url_round_trips_awkward_city_names(client, city):
    r = _post(client, city=city)
    assert r.status_code == 200
    href = _share(r.text)
    assert parse_qs(urlparse(href).query)["city"] == [city]
    again = client.get(href[len(_site()):])
    assert again.status_code == 200
    assert _tables(again.text) == _tables(r.text)
    assert f"candidates for {htmllib.escape(city)}" in again.text


def _assert_no_link_and_no_private_input(r, private):
    assert r.status_code == 200
    assert _share(r.text) is None
    hrefs = _hrefs(r.text)
    assert not [h for h in hrefs if "/muhurat?" in h or "event=" in h], hrefs
    for h in hrefs:
        for needle in private:
            assert needle not in h, (needle, h)


def test_couple_namkaran_and_personal_searches_carry_no_share_link(client, saved_chart):
    couple = {"bride_name": "Sita Verma", "bride_dob": "1995-03-04", "bride_time": "06:30",
              "bride_place": "Jaipur, India", "groom_name": "Ram Verma", "groom_dob": "1993-07-19",
              "groom_time": "11:15", "groom_place": "Lucknow, India"}
    r = _post(client, "vivah", **couple)
    assert "Couple</th>" in r.text, "premise: couple mode was active"
    _assert_no_link_and_no_private_input(r, ["Sita", "Ram", "1995", "1993", "Jaipur", "Lucknow"])

    child = {"child_dob": "2026-10-01", "child_time": "08:10", "child_place": "Bhopal, India"}
    r = _post(client, "namkaran", **child)
    assert "Namkaran first-letter suggestion" in r.text, "premise: namkaran mode was active"
    _assert_no_link_and_no_private_input(r, ["2026-10-01", "Bhopal", "08:10"])

    saved = saved_chart(name="Priya Nair", birth_date="1991-05-06", birth_place="Kochi, India")
    r = _post(client, "griha_pravesh", use_personal="1")
    assert "personal chart matching active" in _text(r.text), "premise: personal mode was active"
    _assert_no_link_and_no_private_input(
        r, ["Priya", "Nair", saved["birth_date"], "Kochi", "1991"])
    # ...and the same saved chart, un-ticked, is a basic search with a link again
    assert _share(_post(client, "griha_pravesh").text) is not None


def test_a_get_never_uses_the_saved_chart(client, saved_chart, monkeypatch):
    from astro_ai.routes import muhurat as route

    saved_chart()
    real = route.compute_chart
    used: list[tuple] = []
    monkeypatch.setattr(route, "compute_chart", lambda *a, **k: used.append(a) or real(*a, **k))

    post = _post(client, use_personal="1")
    assert "personal chart matching active" in _text(post.text) and used, "premise"
    assert re.search(r"<th[^>]*>Personal</th>", post.text), "premise: POST renders the column"
    used.clear()

    r = _get(client, use_personal="1", bride_dob="1990-01-01", child_dob="2020-01-01")
    assert r.status_code == 200
    assert used == [], "a GET computed a chart"
    assert "personal chart matching active" not in _text(r.text)
    assert not re.findall(r"<th[^>]*>Personal</th>", r.text), "a personal column rendered"
    assert "Tara:" not in r.text, "a personal cell rendered"
    assert _tables(r.text) == _tables(_post(client).text)


# --- no search event from a GET ----------------------------------------------------------


def test_a_get_fires_no_notify_and_no_search_event_but_a_post_still_does(client, monkeypatch):
    from astro_ai import notify

    fired: list[dict] = []
    monkeypatch.setattr(notify, "muhurat_computed", lambda **k: fired.append(k))

    g = _get(client)
    assert g.status_code == 200 and _tables(g.text)
    assert fired == []
    assert "muhurat_searched" not in g.text

    p = _post(client)
    assert len(fired) == 1 and fired[0]["city"] == CITY
    assert "muhurat_searched" in p.text


def test_a_bad_city_on_get_does_not_page_the_owner_but_post_does(client, monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    def nowhere(place):
        raise chart.ChartError(f"Couldn't find the place {place!r}.")

    monkeypatch.setattr(chart, "geocode_place", nowhere)
    alerts: list[str] = []
    monkeypatch.setattr(route, "_fire_error_alert", lambda req, err, src: alerts.append(src))

    g = _get(client, city="Qwxzv")
    assert g.status_code == 500 and "Could not compute muhurats" in g.text
    assert alerts == []

    p = _post(client, city="Qwxzv")
    assert p.status_code == 500 and "Could not compute muhurats" in p.text
    assert alerts == ["muhurat:compute:griha_pravesh"]


def test_an_unexpected_failure_on_get_still_alerts(client, monkeypatch):
    from astro_ai import muhurat
    from astro_ai.routes import muhurat as route

    def boom(*a, **k):
        raise RuntimeError("ephemeris down")

    monkeypatch.setattr(muhurat, "find_candidates", boom)
    alerts: list[str] = []
    monkeypatch.setattr(route, "_fire_error_alert", lambda req, err, src: alerts.append(src))
    assert _get(client).status_code == 500
    assert alerts == ["muhurat:compute:griha_pravesh"]


# --- R8: the next auspicious date --------------------------------------------------------


@pytest.mark.parametrize("event", ["griha_pravesh", "business"])
def test_a_zero_result_search_names_the_first_auspicious_date_with_a_link(client, event):
    expected = _zero_window(event)
    for r in (_get(client, event, start=KHARMAS, days=20), _post(client, event, start=KHARMAS, days=20)):
        assert r.status_code == 200
        text = _text(r.text)
        assert "No auspicious dates found in this window" in text
        want = f"The next auspicious date after this range is {expected.strftime('%A')}, {_fmt(expected)}."
        assert want in text
        link = re.search(r'<a href="([^"]*)"[^>]*>' + re.escape(
            f"{expected.strftime('%A')}, {_fmt(expected)}") + "</a>", r.text)
        assert link, "the date is not a link"
        q = parse_qs(urlparse(htmllib.unescape(link.group(1))).query)
        assert q == {"event": [event], "city": [CITY], "start": [expected.isoformat()],
                     "days": ["20"]}
    # following the link lands on a page that lists that date as auspicious
    page = client.get(htmllib.unescape(link.group(1))[len(_site()):])
    assert page.status_code == 200 and "No auspicious dates found" not in page.text
    assert _fmt(expected) in _tables(page.text)[0]


def test_business_premise_the_best_rated_row_is_not_the_earliest(client):
    """Why the scan takes min(date) and not rows[0]: pinned with the real finder."""
    from astro_ai import muhurat

    after = KHARMAS + timedelta(days=20)
    hits = _auspicious(muhurat.find_candidates("business", CITY, after, 60))
    assert hits[0].d != min(c.d for c in hits), "premise: tier order differs from date order"
    r = _get(client, "business", start=KHARMAS, days=20)
    assert f"{min(c.d for c in hits).strftime('%A')}, {_fmt(min(c.d for c in hits))}" in _text(r.text)
    assert _fmt(hits[0].d) not in _text(r.text.split("The next auspicious date")[1].split("</span>")[0])


def test_a_search_with_an_auspicious_date_runs_no_scan_and_names_no_next_date(client, calls):
    r = _get(client)
    assert len(_auspicious_dates(r.text)) >= 1
    assert len(calls) == 1
    assert "The next auspicious date" not in r.text and "No auspicious date found" not in r.text
    calls.clear()
    _post(client)
    assert len(calls) == 1


def _auspicious_dates(h: str) -> list[str]:
    return re.findall(r"[A-Z][a-z]{2} \d\d, \d{4}", _tables(h)[0]) if _tables(h) else []


def _fake_finder(monkeypatch, auspicious: dict[date, str] | None = None):
    """find_candidates stand-in: every date is `avoid` unless listed. Rows come back
    best-tier-first like the real finder. Records (start, days)."""
    from astro_ai import muhurat

    base = muhurat.find_candidates("griha_pravesh", CITY, START, 1)[0]
    seen: list[tuple[date, int]] = []
    order = {"excellent": 0, "good": 1, "acceptable": 2, "caution": 3, "avoid": 4}

    def fake(event_type, city, start, days=90, **kw):
        days = max(1, min(days, 365))
        seen.append((start, days))
        rows = [dataclasses.replace(base, d=start + timedelta(days=i),
                                    rating=(auspicious or {}).get(start + timedelta(days=i), "avoid"))
                for i in range(days)]
        rows.sort(key=lambda c: (order[c.rating], c.d))
        return rows

    monkeypatch.setattr(muhurat, "find_candidates", fake)
    return seen


def test_no_auspicious_date_in_the_cap_says_so_and_scans_contiguously(client, monkeypatch):
    seen = _fake_finder(monkeypatch)
    r = _get(client, start=KHARMAS, days=30)
    assert r.status_code == 200
    window_last = KHARMAS + timedelta(days=29)
    scan = seen[1:]
    assert seen[0] == (KHARMAS, 30)
    assert scan[0][0] == KHARMAS + timedelta(days=30), "the scan must start the day after the window"
    for (s1, d1), (s2, _) in zip(scan, scan[1:]):
        assert s2 == s1 + timedelta(days=d1), "chunks overlap or leave a gap"
    last_start, last_days = scan[-1]
    assert last_start + timedelta(days=last_days - 1) == window_last + timedelta(days=365)
    assert sum(d for _, d in scan) == 365 and all(d <= 60 for _, d in scan)
    text = _text(r.text)
    assert (f"No auspicious date found in the following 365 days "
            f"(until {_fmt(window_last + timedelta(days=365))}).") in text
    assert "The next auspicious date" not in text


def test_the_scan_stops_at_the_first_chunk_with_a_date_and_names_the_earliest(client, monkeypatch):
    after = KHARMAS + timedelta(days=30)
    early, late = after + timedelta(days=130), after + timedelta(days=150)  # both in the 3rd chunk
    seen = _fake_finder(monkeypatch, {early: "acceptable", late: "excellent"})
    r = _get(client, start=KHARMAS, days=30)
    assert len(seen) == 1 + 3, seen
    text = _text(r.text)
    assert f"{early.strftime('%A')}, {_fmt(early)}" in text.split("The next auspicious date")[1]
    assert _fmt(late) not in text.split("The next auspicious date")[1]


def test_the_scan_includes_the_last_day_of_the_horizon(client, monkeypatch):
    window_last = KHARMAS + timedelta(days=29)
    edge = window_last + timedelta(days=365)
    _fake_finder(monkeypatch, {edge: "good"})
    text = _text(_get(client, start=KHARMAS, days=30).text)
    assert f"{edge.strftime('%A')}, {_fmt(edge)}" in text
    beyond = edge + timedelta(days=1)
    _fake_finder(monkeypatch, {beyond: "good"})
    text = _text(_get(client, start=KHARMAS, days=30).text)
    assert "No auspicious date found" in text and _fmt(beyond) not in text


def test_a_failed_scan_leaves_the_result_page_standing(client, monkeypatch):
    from astro_ai import muhurat

    real = muhurat.find_candidates
    n = {"c": 0}

    def flaky(*a, **k):
        n["c"] += 1
        if n["c"] > 1:
            raise RuntimeError("scan blew up")
        return real(*a, **k)

    monkeypatch.setattr(muhurat, "find_candidates", flaky)
    r = _get(client, start=KHARMAS, days=20)
    assert r.status_code == 200 and "No auspicious dates found in this window" in r.text
    assert "The next auspicious date" not in r.text and "No auspicious date found" not in r.text


def test_the_next_date_is_a_link_only_in_basic_mode(client, saved_chart):
    expected = _zero_window("vivah")
    want = f"{expected.strftime('%A')}, {_fmt(expected)}"
    couple = {"bride_dob": "1995-03-04", "bride_time": "06:30", "bride_place": "Jaipur, India",
              "groom_dob": "1993-07-19", "groom_time": "11:15", "groom_place": "Lucknow, India"}
    basic = _post(client, "vivah", start=KHARMAS, days=20)
    assert f">{want}</a>" in basic.text

    r = _post(client, "vivah", start=KHARMAS, days=20, **couple)
    assert "Couple</th>" in r.text or "couple" in r.text.lower()
    assert f"The next auspicious date after this range is {want}." in _text(r.text)
    assert f">{want}</a>" not in r.text
    assert not [h for h in _hrefs(r.text) if "/muhurat?" in h]

    saved_chart()
    r = _post(client, "vivah", start=KHARMAS, days=20, use_personal="1")
    assert "personal chart matching active" in _text(r.text), "premise"
    assert f"The next auspicious date after this range is {want}." in _text(r.text)
    assert f">{want}</a>" not in r.text
    assert not [h for h in _hrefs(r.text) if "/muhurat?" in h]


# --- threadpool, and one definition of "auspicious" ---------------------------------------


@pytest.fixture
def pool(monkeypatch):
    from astro_ai.routes import muhurat as route

    real = route.run_in_threadpool
    hops: list[tuple] = []

    async def spy(fn, *args, **kwargs):
        hops.append((fn, threading.get_ident()))
        return await real(fn, *args, **kwargs)

    monkeypatch.setattr(route, "run_in_threadpool", spy)
    return hops


@pytest.mark.parametrize("call,kwargs", [(_get, {}), (_post, {}),
                                         (_get, {"start": KHARMAS, "days": 20}),
                                         (_post, {"start": KHARMAS, "days": 20})])
def test_find_candidates_and_the_scan_run_in_one_threadpool_hop(client, calls, pool, call, kwargs):
    from astro_ai.routes import muhurat as route

    assert call(client, **kwargs).status_code == 200
    assert [fn for fn, _ in pool] == [route._search], "one hop, for the finder and the scan together"
    loop_thread = pool[0][1]
    assert calls and all(c["thread"] != loop_thread for c in calls), \
        "find_candidates ran on the event loop's thread"
    if kwargs:
        assert len(calls) >= 2, "premise: the zero path scanned"


def test_the_finder_and_the_scan_share_one_auspicious_definition(client, monkeypatch):
    from astro_ai import muhurat

    assert muhurat.AUSPICIOUS_RATINGS == ("excellent", "good", "acceptable")
    # Two acceptable dates, no excellent one: auspicious by the real definition.
    window = (date(2026, 12, 11), 2)
    rows = muhurat.find_candidates("griha_pravesh", CITY, *window)
    assert sorted(c.rating for c in rows) == ["acceptable", "acceptable"], "premise"
    real = _get(client, start=window[0], days=window[1])
    assert "The next auspicious date" not in real.text and "No auspicious dates found" not in real.text

    monkeypatch.setattr(muhurat, "AUSPICIOUS_RATINGS", ("excellent",))
    narrowed = _get(client, start=window[0], days=window[1])
    text = _text(narrowed.text)
    assert "No auspicious dates found in this window" in text, "the finder side kept its own copy"
    after = window[0] + timedelta(days=2)
    first = min(c.d for c in muhurat.find_candidates("griha_pravesh", CITY, after, 365)
                if c.rating == "excellent")
    assert f"The next auspicious date after this range is {first.strftime('%A')}, {_fmt(first)}" in text, \
        "the scan kept its own copy"
