"""#1079: /learn/gochar-2026-planetary-transits/ states ingress dates the sky agrees with, and
reads each Moon sign through the Gochara table instead of against it.

Three defects shipped on the page, each in hand-written prose that no gate read:

* Dates. "Mars in Taurus (Feb-Sep)" was about six weeks (21 June to 2 August), Mars has no
  retrograde in 2026, "late July" was when Mercury's second retrograde ENDS, and Rahu's move to
  Capricorn was put in "mid-December" (true node 25 November, mean node 5 December). Dates here are
  therefore recomputed from the ephemeris through `chart._sid_calc_ut` -- the same Lahiri frame
  the site's own charts use -- and compared to the page, so a date cannot rot again, which is how
  #141 and #146 went wrong (a constant nobody re-derived).
* Readings. Six per-rashi sentences gave a benefit where `knowledge/vedic_reference.md` section
  2A (Raman's Gochara table, counted from the natal Moon) gives the opposite verdict: Jupiter
  in the 4th, 3rd, 1st, 10th and 6th from the Moon is unfavourable (table: Jupiter favourable
  in 2, 5, 7, 9, 11) and Rahu in the 10th/9th is unfavourable (favourable only in 3, 6, 11).
* An unsourced superlative: "one of the most benevolent single transits possible". Nothing in
  `knowledge/` scores a transit by the transiting planet's dignity; section 2A scores it by house.

The favourable sets below are typed from that table, NOT imported from `chart.py`: reading the
code's own constant back would pass for any value of it (tests/test_chandra_bala_gochara_table.py
says the same). One test then compares the typed sets to the code's, so page, table and code
cannot drift apart.

What this does NOT catch: the phrase tests catch the wording they name, not every possible
rewording; the house-verdict test reads the word "unfavourable" in the sentence that names the
house, so it cannot judge whether the surrounding interpretation is wise. The Saturn, Mars, Mercury
and Rahu ingress dates are pinned to +-1 day, because an ingress near midnight differs by a day
between an ephemeris and a Panchang.
"""
from __future__ import annotations

import functools
import json
import re
from datetime import datetime, timedelta, timezone

import swisseph as swe

SLUG = "gochar-2026-planetary-transits"
IST = timezone(timedelta(hours=5, minutes=30))

# Typed from knowledge/vedic_reference.md section 2A (Raman, Ch. XII), Jupiter and Rahu/Ketu rows.
JUPITER_FAVOURABLE = {2, 5, 7, 9, 11}
RAHU_FAVOURABLE = {3, 6, 11}

# Zodiac order, typed here so the house arithmetic does not borrow chart.RASHIS.
ZODIAC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
CANCER, CAPRICORN, AQUARIUS = 3, 9, 10

_STALE = [
    "Mid-February 2026",
    "Feb–Sep",
    "eight months",
    "almost 8",
    "Mid-December 2026",
    "around 1 November",
    "around 14 December",
    "around mid-April",
    "30 March 2025",
    "21 October 2027",
    "24 February 2028",
    "most benevolent",
    "benevolent transit",
    "approx — verify",
]

# The removed inverted readings (each said Jupiter or Rahu helps in a house the table marks unfavourable).
_INVERTED = [
    "one of the best transits you'll ever get",
    "blesses home and mother",
    "activates courage and communication",
    "career recognition, promotions",
    "very good year for professional visibility",
    "helps overcome enemies",
    "sudden career opportunities possible",
    "foreign travel or spiritual guru appears",
    "all favoured",
]

_SATURN_STALE = ["30 March 2025", "21 October 2027", "24 February 2028"]


# --------------------------------------------------------------------------- ephemeris

def _lon_speed(jd: float, body: int) -> tuple[float, float]:
    from astro_ai.chart import _sid_calc_ut

    pos = _sid_calc_ut(jd, body, swe.FLG_SPEED)[0]
    return pos[0], pos[3]


def _sign(jd: float, body: int) -> int:
    return int(_lon_speed(jd, body)[0] // 30)


def _bisect(pred, a: float, b: float) -> float:
    fa = pred(a)
    for _ in range(50):
        m = (a + b) / 2
        if pred(m) == fa:
            a = m
        else:
            b = m
    return b


def _ist(jd: float) -> datetime:
    y, mo, d, h = swe.revjul(jd)
    return (datetime(y, mo, d, tzinfo=timezone.utc) + timedelta(hours=h)).astimezone(IST)


@functools.cache
def _ingresses(body: int, y0: int, y1: int) -> tuple:
    """((IST datetime, sign entered), ...) for `body` between 1 Jan y0 and 1 Jan y1."""
    a, b = swe.julday(y0, 1, 1, 0.0), swe.julday(y1, 1, 1, 0.0)
    out, jd, prev = [], a, _sign(a, body)
    step = 1 / 24
    while jd < b:
        n = jd + step
        s = _sign(n, body)
        if s != prev:
            out.append((_ist(_bisect(lambda x: _sign(x, body), jd, n)), s))
        jd, prev = n, s
    return tuple(out)


@functools.cache
def _stations(body: int, y0: int, y1: int) -> tuple:
    """((IST datetime, 'retro'|'direct'), ...) for `body` between 1 Jan y0 and 1 Jan y1."""
    a, b = swe.julday(y0, 1, 1, 0.0), swe.julday(y1, 1, 1, 0.0)
    out, jd, prev = [], a, _lon_speed(a, body)[1] > 0
    step = 1 / 24
    while jd < b:
        n = jd + step
        s = _lon_speed(n, body)[1] > 0
        if s != prev:
            t = _bisect(lambda x: _lon_speed(x, body)[1] > 0, jd, n)
            out.append((_ist(t), "direct" if s else "retro"))
        jd, prev = n, s
    return tuple(out)


def _entered(body: int, sign: int, after: datetime) -> datetime:
    """First ingress of `body` into `sign` on or after `after` (IST), within 2026-2027."""
    hits = [t for t, s in _ingresses(body, 2026, 2028) if s == sign and t >= after]
    assert hits, f"no ingress of body {body} into sign {sign} after {after}"
    return hits[0]


_START_2026 = datetime(2026, 1, 1, tzinfo=IST)


def _computed_2026() -> dict:
    """Every dated event the page's Key dates list must carry, from the ephemeris."""
    mars_tau = _entered(swe.MARS, 1, datetime(2026, 3, 1, tzinfo=IST))
    mercury_retro = [t for t, k in _stations(swe.MERCURY, 2026, 2027) if k == "retro"]
    jup_retro = [t for t, k in _stations(swe.JUPITER, 2026, 2027) if k == "retro"]
    return {
        "jupiter_cancer": _entered(swe.JUPITER, CANCER, _START_2026),
        "mars_taurus": mars_tau,
        "mars_gemini": _entered(swe.MARS, 2, mars_tau),
        "mars_cancer": _entered(swe.MARS, CANCER, mars_tau),
        "mars_leo": _entered(swe.MARS, 4, mars_tau),
        "mercury_retro": mercury_retro,
        "jupiter_leo": _entered(swe.JUPITER, 4, datetime(2026, 7, 1, tzinfo=IST)),
        "jupiter_retro": jup_retro[0],
        # The site's engine is TRUE_NODE (chart.py); Ketu is exactly opposite, so one ingress serves both.
        "rahu_capricorn": _entered(swe.TRUE_NODE, CAPRICORN, datetime(2026, 6, 1, tzinfo=IST)),
    }


# --------------------------------------------------------------------------- page helpers

def _html(client, path: str) -> str:
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    return r.text


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _page(client) -> str:
    return _html(client, f"/learn/{SLUG}/")


def _article(slug: str = SLUG):
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == slug)


def _registry_text(slug: str = SLUG) -> str:
    a = _article(slug)
    return " ".join([a.summary, a.llm_summary] + [f["q"] + " " + f["a"] for f in a.faqs])


def _day(dt: datetime):
    return dt.date()


def _parse_dm(day_month: str, year: int = 2026) -> datetime:
    return datetime.strptime(f"{day_month} {year}", "%d %B %Y").replace(tzinfo=IST)


def _within_a_day(page_date: datetime, computed: datetime) -> bool:
    return abs((_day(page_date) - _day(computed)).days) <= 1


def _key_dates(page: str) -> list[tuple[datetime, str]]:
    section = page[page.index("Key 2026 dates to watch"):]
    section = section[: section.index("</ul>")]
    items = re.findall(r"<li><strong>(\d{1,2} \w+ \d{4})</strong> — (.*?)</li>", section, re.S)
    return [(datetime.strptime(d, "%d %B %Y").replace(tzinfo=IST), re.sub(r"<[^>]+>", "", desc))
            for d, desc in items]


def _rashi_sections(page: str) -> dict[str, str]:
    found = re.findall(r"<h3>(\w+) / \w+</h3>\s*<p>(.*?)</p>", page, re.S)
    assert [name for name, _ in found] == ZODIAC, [name for name, _ in found]
    return {name: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", body)) for name, body in found}


def _house_from(moon: str, planet_sign: int) -> int:
    return (planet_sign - ZODIAC.index(moon)) % 12 + 1


# --------------------------------------------------------------------------- dates

def test_every_key_date_matches_the_ephemeris_within_a_day(client):
    """Each Key-dates item is compared with the recomputed event; every expected event must be present."""
    got = _key_dates(_page(client))
    ev = _computed_2026()

    def pick(*words):
        return [(d, desc) for d, desc in got if all(w in desc for w in words)]

    singles = [
        ("Jupiter enters Cancer", ("Jupiter", "enters Cancer"), ev["jupiter_cancer"]),
        ("Mars enters Taurus", ("Mars", "enters Taurus"), ev["mars_taurus"]),
        ("Mars enters Cancer", ("Mars", "enters Cancer"), ev["mars_cancer"]),
        ("Jupiter moves into Leo", ("Jupiter", "into Leo"), ev["jupiter_leo"]),
        ("Jupiter turns retrograde", ("Jupiter", "turns retrograde"), ev["jupiter_retro"]),
        ("Rahu-Ketu axis shifts", ("Rahu-Ketu", "Capricorn-Cancer"), ev["rahu_capricorn"]),
    ]
    for label, words, computed in singles:
        hits = pick(*words)
        assert len(hits) == 1, f"Key dates must carry exactly one '{label}' item, found {len(hits)}"
        assert _within_a_day(hits[0][0], computed), (
            f"'{label}': page says {hits[0][0]:%d %B %Y}, ephemeris says {computed:%d %B %Y %H:%M} IST")

    mercury = sorted(d for d, _ in pick("Mercury", "turns retrograde"))
    # The Feb-Mar station falls before the second and third episodes the list names.
    expected = ev["mercury_retro"][1:]
    assert len(mercury) == len(expected) == 2, (
        f"Key dates must carry Mercury's 2nd and 3rd retrograde stations, found {len(mercury)}")
    for page_date, computed in zip(mercury, expected):
        assert _within_a_day(page_date, computed), (
            f"Mercury retrograde: page says {page_date:%d %B %Y}, ephemeris says {computed:%d %B %Y %H:%M} IST")


def test_key_dates_are_chronological_and_each_carries_a_full_date(client):
    page = _page(client)
    dates = [d for d, _ in _key_dates(page)]
    assert len(dates) == 8, f"expected 8 dated items, parsed {len(dates)}"
    assert dates == sorted(dates), "Key dates list is out of chronological order"
    section = page[page.index("Key 2026 dates to watch"):]
    section = section[: section.index("</ul>")]
    assert section.count("<li>") == len(dates), "a Key-dates item has no leading '<strong>D Month YYYY</strong>'"


def test_mars_in_taurus_is_about_six_weeks_between_the_two_computed_ingresses(client):
    page = _page(client)
    ev = _computed_2026()
    days = (ev["mars_gemini"] - ev["mars_taurus"]).days
    assert 38 <= days <= 48, f"Mars should spend about six weeks in Taurus, ephemeris gives {days} days"
    # Other-transits bullet and the Taurus paragraph both give the two dates.
    bullet = re.search(r"Mars in Taurus</strong> \((\d{1,2} \w+)[–-](\d{1,2} \w+) 2026\)", page)
    assert bullet, "Mars-in-Taurus bullet has no 'D Month-D Month 2026' range"
    para = re.search(r"Mars in your rashi from (\d{1,2} \w+) to (\d{1,2} \w+) —", page)
    assert para, "Taurus paragraph has no 'from D Month to D Month' range"
    for start, end in (bullet.groups(), para.groups()):
        assert _within_a_day(_parse_dm(start), ev["mars_taurus"]), (start, ev["mars_taurus"])
        assert _within_a_day(_parse_dm(end), ev["mars_gemini"]), (end, ev["mars_gemini"])
    assert "about six weeks" in _text(page)


def test_mars_does_not_turn_retrograde_in_2026_and_the_page_says_no_loop(client):
    assert not [s for s in _stations(swe.MARS, 2026, 2027)], (
        "Mars has a station in 2026 after all; the page's 'no retrograde' sentence is now wrong")
    text = _text(_page(client))
    assert "retrograde period" not in text
    assert "Mars does not turn retrograde in 2026" in text


def test_mars_in_cancer_gives_the_two_computed_dates(client):
    page = _page(client)
    ev = _computed_2026()
    m = re.search(r"Mars in Cancer</strong> \((\d{1,2} \w+)[–-](\d{1,2} \w+) 2026\)", page)
    assert m, "Mars-in-Cancer bullet has no exact range (it said 'Sep-Nov approx — verify')"
    assert _within_a_day(_parse_dm(m.group(1)), ev["mars_cancer"])
    assert _within_a_day(_parse_dm(m.group(2)), ev["mars_leo"])


def test_jupiter_station_and_ingress_dates_in_prose_match_the_ephemeris(client):
    text = _text(_page(client))
    ev = _computed_2026()
    # The first 'direct' station of 2026 (11 March) ends the PREVIOUS retrograde; take the one after ev's.
    retro_end = [t for t, k in _stations(swe.JUPITER, 2026, 2028)
                 if k == "direct" and t > ev["jupiter_retro"]][0]
    m = re.search(r"Jupiter retrograde \((\d{1,2} \w+ 2026) – (\d{1,2} \w+ 2027)\)", text)
    assert m, "Jupiter-retrograde bullet has no exact range"
    assert _within_a_day(datetime.strptime(m.group(1), "%d %B %Y").replace(tzinfo=IST), ev["jupiter_retro"])
    assert _within_a_day(datetime.strptime(m.group(2), "%d %B %Y").replace(tzinfo=IST), retro_end)
    m = re.search(r"Jupiter is in Cancer from (\d{1,2} \w+) to (\d{1,2} \w+ 2026), in Leo from", text)
    assert m, "Jupiter calendar sentence missing"
    assert _within_a_day(_parse_dm(m.group(1)), ev["jupiter_cancer"])
    assert _within_a_day(_parse_dm(m.group(2).replace(" 2026", "")), ev["jupiter_leo"])


def test_saturn_dates_on_the_page_match_the_ephemeris(client):
    text = _text(_page(client))
    ing = _ingresses(swe.SATURN, 2025, 2029)
    pisces_2025 = next(t for t, s in ing if s == 11)
    aries_2027 = next(t for t, s in ing if s == 0 and t.year == 2027)
    pisces_2027 = next(t for t, s in ing if s == 11 and t.year == 2027)
    aries_2028 = next(t for t, s in ing if s == 0 and t.year == 2028)
    m = re.search(r"arrived on (\d{1,2} \w+ 2025)\. .*? Aries on (\d{1,2} \w+ 2027), .*? Pisces on its "
                  r"retrograde path on (\d{1,2} \w+ 2027), and re-enters Aries on (\d{1,2} \w+ 2028)", text)
    assert m, "Saturn sentence not found in the expected shape"
    for got, want in zip(m.groups(), (pisces_2025, aries_2027, pisces_2027, aries_2028)):
        assert _within_a_day(datetime.strptime(got, "%d %B %Y").replace(tzinfo=IST), want), (got, want)


def test_rahu_ketu_shift_is_dated_to_the_true_node_and_names_the_mean_node(client):
    text = _text(_page(client))
    ev = _computed_2026()
    true_node = ev["rahu_capricorn"]
    assert _within_a_day(_parse_dm("25 November"), true_node), (
        f"the true-node ingress is now {true_node:%d %B %Y %H:%M} IST; update the page's 25 November")
    mean = _entered_mean_node()
    assert _within_a_day(_parse_dm("5 December"), mean), f"mean-node ingress is {mean}"
    assert "On 25 November 2026, the axis shifts" in text
    assert "almanacs that use the mean node give 5 December 2026" in text
    assert "true node" in text


def _entered_mean_node() -> datetime:
    hits = [t for t, s in _ingresses(swe.MEAN_NODE, 2026, 2028) if s == CAPRICORN]
    assert hits
    return hits[0]


def test_registry_dates_agree_with_the_ephemeris():
    ev = _computed_2026()
    faq = {f["q"]: f["a"] for f in _article().faqs}
    big = faq["Which is the biggest transit of 2026?"]
    m = re.search(r"entered Cancer on (\d{1,2} \w+ 2026), moves on to Leo on (\d{1,2} \w+ 2026)", big)
    assert m, "biggest-transit FAQ has no exact Cancer/Leo ingress dates"
    assert _within_a_day(datetime.strptime(m.group(1), "%d %B %Y").replace(tzinfo=IST), ev["jupiter_cancer"])
    assert _within_a_day(datetime.strptime(m.group(2), "%d %B %Y").replace(tzinfo=IST), ev["jupiter_leo"])
    rahu = faq["What happens to the Rahu-Ketu axis in late 2026?"]
    m = re.search(r"shifts on (\d{1,2} \w+ 2026)", rahu)
    assert m, "Rahu FAQ has no exact date"
    assert _within_a_day(datetime.strptime(m.group(1), "%d %B %Y").replace(tzinfo=IST), ev["rahu_capricorn"])
    assert "mean node give 5 December 2026" in rahu
    assert "2 June–31 October 2026" in _article().llm_summary


def test_saturn_faq_dates_match_the_ephemeris():
    ing = _ingresses(swe.SATURN, 2025, 2029)
    pisces_2025 = next(t for t, s in ing if s == 11)
    pisces_2027 = next(t for t, s in ing if s == 11 and t.year == 2027)
    aries_2028 = next(t for t, s in ing if s == 0 and t.year == 2028)
    faq = {f["q"]: f["a"] for f in _article().faqs}["How long is Saturn in Pisces?"]
    m = re.search(r"entered Pisces on (\d{1,2} \w+ 2025) .*? Pisces on (\d{1,2} \w+ 2027) .*? Aries on "
                  r"(\d{1,2} \w+ 2028)", faq)
    assert m, "Saturn FAQ not in the expected shape"
    for got, want in zip(m.groups(), (pisces_2025, pisces_2027, aries_2028)):
        assert _within_a_day(datetime.strptime(got, "%d %B %Y").replace(tzinfo=IST), want), (got, want)


# --------------------------------------------------------------------------- stale strings

def test_stale_dates_and_superlative_are_gone_from_the_rendered_page(client):
    text = _text(_page(client))
    for phrase in _STALE:
        assert phrase not in text, f"stale phrase back on the page: {phrase!r}"


def test_stale_dates_and_superlative_are_gone_from_the_registry():
    reg = _registry_text()
    for phrase in _STALE:
        assert phrase not in reg, f"stale phrase back in the registry (summary/faqs/llm_summary): {phrase!r}"


def test_the_corrected_faq_text_reaches_the_json_ld(client):
    html = _page(client)
    blocks = re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    answers = []
    for b in blocks:
        data = json.loads(b)
        for node in data if isinstance(data, list) else [data]:
            if node.get("@type") == "FAQPage":
                answers += [q["acceptedAnswer"]["text"] for q in node["mainEntity"]]
    assert answers, "no FAQPage JSON-LD on the page"
    joined = " ".join(answers)
    assert "25 November 2026" in joined
    assert "31 October 2026" in joined
    assert "benevolent" not in joined


def test_saturn_dates_are_corrected_on_sade_sati_too(client):
    """Ban only: #1081 owns the rest of that page and may reword the sentence."""
    text = _text(_html(client, "/learn/sade-sati/"))
    reg = _registry_text("sade-sati")
    for phrase in _SATURN_STALE:
        assert phrase not in text, f"sade-sati page: {phrase!r}"
        assert phrase not in reg, f"sade-sati registry: {phrase!r}"


def test_inverted_readings_are_gone(client):
    text = _text(_page(client)).lower()
    for phrase in _INVERTED:
        assert phrase not in text, f"inverted Gochara reading is back: {phrase!r}"
    assert "sudden career opportunities" not in _registry_text().lower()


# --------------------------------------------------------------------------- the Gochara invariant

def test_typed_favourable_sets_equal_the_codes_table():
    from astro_ai.chart import _GOCHARA_BENEFIC_FROM_MOON

    assert set(_GOCHARA_BENEFIC_FROM_MOON["Jupiter"]) == JUPITER_FAVOURABLE
    assert set(_GOCHARA_BENEFIC_FROM_MOON["Rahu"]) == RAHU_FAVOURABLE
    assert set(_GOCHARA_BENEFIC_FROM_MOON["Ketu"]) == RAHU_FAVOURABLE


def test_jupiter_is_in_cancer_in_the_months_the_page_discusses():
    # The house arithmetic below assumes Cancer is where Jupiter is; the ephemeris, not the test, says so.
    jd = swe.julday(2026, 8, 1, 0.0)
    assert _sign(jd, swe.JUPITER) == CANCER


def _jupiter_sentence(section: str) -> tuple[int, str]:
    m = re.search(r"[^.]*Jupiter (?:\([^)]*\) )?in Cancer \((\d+)(?:st|nd|rd|th) from you[,)][^.]*\.", section)
    assert m, f"no 'Jupiter in Cancer (Nth from you)' sentence in: {section[:80]}"
    return int(m.group(1)), m.group(0)


def test_each_rashi_section_names_the_right_house_for_jupiter_in_cancer(client):
    for moon, section in _rashi_sections(_page(client)).items():
        stated, _ = _jupiter_sentence(section)
        assert stated == _house_from(moon, CANCER), (
            f"{moon}: page says Jupiter in Cancer is the {stated}th from you, it is "
            f"the {_house_from(moon, CANCER)}th")


def test_each_rashi_section_gives_the_gochara_verdict_for_jupiter(client):
    """'unfavourable' appears in the Jupiter sentence iff the house is outside {2,5,7,9,11} (vedic_reference.md 2A)."""
    for moon, section in _rashi_sections(_page(client)).items():
        house, sentence = _jupiter_sentence(section)
        says_unfavourable = "unfavourable" in sentence
        assert says_unfavourable == (house not in JUPITER_FAVOURABLE), (
            f"{moon}: Jupiter in Cancer is the {house}th house from the Moon, which the Gochara table "
            f"counts as {'favourable' if house in JUPITER_FAVOURABLE else 'unfavourable'}; "
            f"the page says: {sentence!r}")


# Sections that name Rahu's house, with the sign Rahu is in at that point in the sentence.
_RAHU_SIGN_IN_SECTION = {
    "Aries": CAPRICORN, "Taurus": CAPRICORN, "Gemini": CAPRICORN, "Libra": CAPRICORN,
    "Scorpio": CAPRICORN, "Sagittarius": CAPRICORN, "Virgo": AQUARIUS,
}
# Sections whose Rahu sentence carries the table's verdict in words (the rest only name the house).
_RAHU_VERDICT_STATED = {"Aries", "Taurus", "Scorpio"}


def test_each_named_rahu_house_is_right_and_its_verdict_follows_the_table(client):
    sections = _rashi_sections(_page(client))
    for moon, rahu_sign in _RAHU_SIGN_IN_SECTION.items():
        m = re.search(r"[^.]*\bRahu\b[^.]*?\b(\d+)(?:st|nd|rd|th)\b[^.]*\.", sections[moon])
        assert m, f"{moon}: no sentence naming Rahu's house"
        stated, sentence = int(m.group(1)), m.group(0)
        house = _house_from(moon, rahu_sign)
        assert stated == house, f"{moon}: page says Rahu is in the {stated}th, it is the {house}th: {sentence!r}"
        says_unfavourable = "unfavourable" in sentence
        if moon in _RAHU_VERDICT_STATED:
            assert says_unfavourable == (house not in RAHU_FAVOURABLE), (
                f"{moon}: Rahu in the {house}th from the Moon is "
                f"{'favourable' if house in RAHU_FAVOURABLE else 'unfavourable'} on the Gochara table; "
                f"the page says: {sentence!r}")
        elif says_unfavourable:
            assert house not in RAHU_FAVOURABLE, f"{moon}: calls a favourable Rahu house unfavourable: {sentence!r}"


def test_taurus_and_aries_rahu_houses_are_the_ones_the_issue_named(client):
    # Pinned by number as well as by arithmetic: the two sections the issue singled out.
    assert _house_from("Aries", CAPRICORN) == 10 and 10 not in RAHU_FAVOURABLE
    assert _house_from("Taurus", CAPRICORN) == 9 and 9 not in RAHU_FAVOURABLE


def test_page_states_the_table_does_not_adjust_for_exaltation_and_is_a_first_approximation(client):
    text = _text(_page(client))
    assert "does not adjust for Jupiter's strength in Cancer" in text
    assert "first approximation" in text
    assert "weigh it with your dasha and natal chart" in text


def test_jupiter_amplifies_list_is_limited_to_the_favourable_moon_signs(client):
    text = _text(_page(client))
    favourable_moons = [m for m in ZODIAC if _house_from(m, CANCER) in JUPITER_FAVOURABLE]
    assert sorted(favourable_moons) == sorted(["Gemini", "Pisces", "Capricorn", "Scorpio", "Virgo"])
    m = re.search(r"What Jupiter in Cancer can amplify, for those whose Moon sign puts it in a favourable "
                  r"house \(the 2nd, 5th, 7th, 9th or 11th from the Moon: ([^)]*)\):", text)
    assert m, "the amplifies list lost its favourable-house qualifier"
    named = re.findall(r"[A-Z][a-z]+", m.group(1).replace("Moons", ""))
    assert sorted(w for w in named if w in ZODIAC) == sorted(favourable_moons)


def test_the_sourced_facts_stay(client):
    text = _text(_page(client))
    assert "its exaltation sign, Cancer" in text
    assert "Jupiter — Guru, the Great Benefic" in text
    assert "Mars is debilitated in Cancer" in text
