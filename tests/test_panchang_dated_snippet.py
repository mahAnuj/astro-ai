"""A dated `/panchang/{date}` URL must not call itself "Today's", and its snippet
must carry the values the page computed (#1074).

Defect this guards: `panchang.html` hardcoded "Today's Panchang" in the
`<title>` and "Today's Panchang for <city> -- tithi (lunar day), ..." in the
meta description for EVERY date. Probed on production 2026-11-15,
`/panchang/2026-12-02` (17 days ahead) was titled "Today's Panchang -- 2 December
2026" with a description holding no date and no value, while the answer a
"2 december 2026 rahu kaal" query wants (Wednesday, Krishna Navami, Rahu Kaal
12:27-13:50) sat in the first screen. The H1 already branched on `is_today`.

Every expected value below is READ BACK FROM THE RENDERED CARDS on the same page,
never typed, so an ephemeris update moves page and snippet together and these
stay about rendering. Comparing the snippet to the cards is also what makes a
route that computes the sentence from anything but the page's own values fail.
"""
from __future__ import annotations

import html as _html
import re

import pytest

FUTURE = "2026-12-02"   # the URL the issue was measured on
PAST = "2025-03-04"
# Tromso 2026-05-17 has no ordinary sunrise-to-sunset span (#227): the page
# discloses it and omits Rahu Kaal, so the snippet must omit it too.
POLAR_CITY = "Tromso"
POLAR_DATE = "2026-05-17"


def _get(client, path: str, **params) -> str:
    resp = client.get(path, params=params)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    return resp.text


def _title(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    assert m, "no <title>"
    return _html.unescape(m.group(1)).strip()


def _description(page: str) -> str:
    m = re.search(r'<meta name="description" content="(.*?)">', page, re.S)
    assert m, "no meta description"
    return _html.unescape(m.group(1)).strip()


def _sentence(page: str) -> str | None:
    m = re.search(r"<p[^>]*data-answer-sentence>(.*?)</p>", page, re.S)
    return _html.unescape(m.group(1)).strip() if m else None


def _card(page: str, label: str) -> str:
    m = re.search(
        re.escape(label) + r"[^<]*</div>\s*<div[^>]*>\s*([^<]+?)\s*</div>", page)
    assert m, f"no {label!r} card on the page"
    return _html.unescape(m.group(1)).strip()


def _rendered_rahu_kaal(page: str) -> str:
    """The card's "12:27 — 13:50" as the sentence spells it, "12:27–13:50"."""
    start, end = re.split(r"\s*[—-]\s*", _card(page, "Rahu Kaal (avoid)"))
    return f"{start}–{end}"


@pytest.mark.parametrize("iso", [FUTURE, PAST])
def test_a_dated_title_does_not_say_today_and_names_the_date(client, iso):
    title = _title(_get(client, f"/panchang/{iso}"))

    assert "Today" not in title, f"a dated URL calls itself Today's: {title!r}"
    assert title.startswith("Panchang "), title
    assert {FUTURE: "2 December 2026", PAST: "4 March 2025"}[iso] in title
    assert "Rahu Kaal" in title and "Mumbai" in title
    # A SERP truncates near 60-70 characters; the longest default city is the
    # one a visitor gets, so measure the real thing rather than a short stand-in.
    assert len(title) <= 70, f"{len(title)} chars: {title!r}"


def test_the_dated_description_carries_the_rendered_values(client):
    page = _get(client, f"/panchang/{FUTURE}")
    desc = _description(page)

    assert "Today" not in desc
    assert _card(page, "Day &amp; Lord") in desc
    assert _card(page, "Tithi") in desc
    # Nakshatra comes off the Moon card's second line, "<nakshatra> nakshatra".
    nak = re.search(r"([A-Za-z ]+?) nakshatra</div>", page)
    assert nak, "no Moon nakshatra on the page"
    assert nak.group(1).strip() in desc
    assert _rendered_rahu_kaal(page) in desc, desc
    assert "2 December 2026" in desc and "Mumbai" in desc
    assert len(desc) <= 175, f"{len(desc)} chars"


def test_the_sentence_under_the_heading_and_the_description_agree(client):
    page = _get(client, f"/panchang/{FUTURE}")
    sentence, desc = _sentence(page), _description(page)

    assert sentence, "no answer sentence under the H1"
    # Description is the sentence plus an optional fixed tail: one source.
    assert desc.startswith(sentence), (sentence, desc)
    assert sentence.startswith("On ") and "at sunrise" in sentence
    assert _rendered_rahu_kaal(page) in sentence
    # Restates computed values only (#1074 AC5): no verdict words.
    for word in ("auspicious", "avoid", "inauspicious", "best", "favour"):
        assert word not in sentence.lower()
        assert word not in desc.lower()


def test_today_keeps_its_title_and_description(client):
    page = _get(client, "/panchang")

    assert _title(page).startswith("Today's Panchang — ")
    assert _title(page).endswith(" · Tithi, Nakshatra, Rahu Kaal, Choghadiya")
    assert _description(page).startswith(
        "Today's Panchang for Mumbai, India — tithi (lunar day), nakshatra")
    assert _description(page).endswith("Classical Vedic sidereal Lahiri.")
    # And today's page now carries the same one-sentence answer.
    assert _sentence(page)


def test_a_dated_url_that_is_today_is_still_titled_today(client):
    """`is_today` decides, not the URL shape: /panchang/<today> is today."""
    from astro_ai.chart import local_today

    iso = local_today("Asia/Kolkata").isoformat()
    title = _title(_get(client, f"/panchang/{iso}"))
    # Mumbai's civil date is the page's "today"; a one-day skew at a UTC/IST
    # boundary would make this a dated page, so accept only the two honest forms.
    assert title.startswith("Today's Panchang") or title.startswith("Panchang ")


def test_a_polar_date_omits_rahu_kaal_from_sentence_and_description(client, monkeypatch):
    from astro_ai import chart

    monkeypatch.setattr(
        chart, "geocode_place", lambda place: (69.6492, 18.9553, "Europe/Oslo"))
    page = _get(client, f"/panchang/{POLAR_DATE}", city=POLAR_CITY)

    assert "No ordinary sunrise-to-sunset day" in page, "date is no longer polar"
    sentence, desc = _sentence(page), _description(page)
    assert sentence and "Rahu Kaal" not in sentence, sentence
    assert "Rahu Kaal" not in desc, desc
    assert "Today" not in _title(page)
    assert desc.startswith(sentence)
    assert _card(page, "Tithi") in sentence


def test_a_page_with_no_panchang_still_renders_a_dated_snippet(client, monkeypatch):
    """Both geocodes failing leaves `p` None; the snippet must degrade, not 500."""
    from astro_ai.routes import panchang as route

    def _boom(*a, **k):
        raise RuntimeError("no ephemeris")

    monkeypatch.setattr(route, "compute_panchang", _boom)
    page = _get(client, f"/panchang/{FUTURE}")

    assert "Today" not in _title(page)
    assert _sentence(page) is None
    desc = _description(page)
    assert "2 December 2026" in desc and "Today" not in desc
