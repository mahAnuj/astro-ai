"""#1071: /learn/gochar-2027-planetary-transits/ states only dates the ephemeris gives, and reads each
Moon sign through the Gochara table.

This is the sibling of tests/test_gochar_2026_claims.py (#1079/#1100), written before the page so the
two defects that page shipped cannot be repeated on the new one:

* Dates written from memory. Every ingress and station the page, its FAQs and its Key-dates list
  state is recomputed here through `chart._sid_calc_ut` (the Lahiri frame the site's own charts use)
  and compared, so a date cannot rot the way #141 and #146 did (a constant nobody re-derived).
* Verdicts that contradict the table. Each Moon sign's section names the house a planet falls in and
  the table's verdict for it; both are recomputed here.

PROVENANCE OF THE DATES (issue #1071 AC2). Nothing was copied from a website or recalled. The table
below is the output of the command

    uv run python tests/test_gochar_2027_claims.py

which runs `_computed_2027()` below: a 1-hour scan of `_sid_calc_ut(jd, body, FLG_SPEED)` from
1 Jan 2026 to 1 Jan 2029 with a 50-step bisection on every sign change (ingress) and every change in
the sign of the longitude speed (station), shown in IST. Output as run on 2026-11-17:

    Jupiter retrograde station   2026-12-13 06:00 IST (Leo)
    Jupiter enters Cancer        2027-01-25 01:31 IST
    Jupiter direct station       2027-04-13 08:12 IST (Cancer)
    Jupiter enters Leo           2027-06-26 05:18 IST
    Jupiter enters Virgo         2027-11-26 18:45 IST
    Saturn direct station        2026-12-11 05:59 IST (Pisces)
    Saturn enters Aries          2027-06-03 05:28 IST
    Saturn retrograde station    2027-08-09 22:54 IST (Aries)
    Saturn enters Pisces         2027-10-20 07:12 IST
    Saturn direct station        2027-12-24 09:04 IST (Pisces)
    Saturn enters Aries (2028)   2028-02-23 19:24 IST
    Rahu (true) enters Capricorn 2026-11-25 19:15 IST (Ketu enters Cancer); no ingress at all in 2027
    Rahu (true) enters Sagittarius 2028-05-24 15:11 IST (Ketu enters Gemini)
    Rahu (mean) enters Capricorn 2026-12-05 22:32 IST; Sagittarius 2028-06-24 01:29 IST
    Mars retrograde station      2027-01-10 18:24 IST (Leo)
    Mars enters Cancer           2027-03-10 00:13 IST
    Mars direct station          2027-04-01 19:41 IST (Cancer)
    Mars enters Leo              2027-04-26 11:47 IST
    Mercury retrograde stations  2027-02-09 23:06, 2027-06-10 23:44, 2027-10-07 20:06 IST
    Mercury direct stations      2027-03-03 18:02, 2027-07-05 01:10, 2027-10-28 19:40 IST

The true node also makes many short retrograde/direct stations inside Capricorn through 2027 (it
wobbles about the mean node); none is a sign change, and the page says only that it does not cross
into another sign.

The favourable sets are typed from knowledge/vedic_reference.md section 2A (Raman, Ch. XII), NOT
imported from `chart.py`: reading the code's own constant back would pass for any value of it. One
test parses the table out of the knowledge file and one compares with the code, so the page, the
table and the code cannot drift apart.

What this does NOT catch: the phrase tests catch the wording they name, not every possible
rewording; the verdict tests read the word "favourable"/"unfavourable" next to the named house, so
they cannot judge whether the surrounding interpretation is wise. Ingress dates are pinned to +-1 day
because an ingress near midnight differs by a day between an ephemeris and a Panchang (every Jupiter
and Saturn date the page states is in fact the computed IST calendar day).
"""
from __future__ import annotations

import functools
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import swisseph as swe

SLUG = "gochar-2027-planetary-transits"
SLUG_2026 = "gochar-2026-planetary-transits"
IST = timezone(timedelta(hours=5, minutes=30))
KNOWLEDGE = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "knowledge"

# Typed from knowledge/vedic_reference.md section 2A, Jupiter, Saturn and Rahu/Ketu rows.
JUPITER_FAVOURABLE = {2, 5, 7, 9, 11}
SATURN_FAVOURABLE = {3, 6, 11}
RAHU_FAVOURABLE = {3, 6, 11}  # Rahu and Ketu share one row

# Zodiac order, typed here so the house arithmetic does not borrow chart.RASHIS.
ZODIAC = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
          "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ARIES, CANCER, LEO, VIRGO, SAGITTARIUS, CAPRICORN, PISCES = 0, 3, 4, 5, 8, 9, 11

# Typed from the headings of knowledge/houses.md ("4th House — Sukha Bhava (Mother / Home / ...)").
# test_house_themes_are_in_the_knowledge_file reads the file and checks each word is in its heading.
HOUSE_THEMES = {
    1: "self, body", 2: "wealth, family, speech", 3: "siblings, courage, communication",
    4: "mother, home, vehicles", 5: "children, higher intellect", 6: "enemies, illness, debts, service",
    7: "spouse, partnerships", 8: "longevity, transformation, occult", 9: "fortune, father, higher learning",
    10: "profession, status", 11: "gains, elder siblings, aspirations", 12: "expenditure, foreign, moksha",
}

# Wording that reads as a harm: a clause the table calls FAVOURABLE must carry none of it.
_HARM_STEMS = ("bad", "harm", "hurt", "damag", "ruin", "worst", "poor", "difficult", "trouble",
               "adverse", "inauspicious", "unlucky", "misfortune", "obstacle", "suffer", "weaken")
# Wording that reads as a promise or a superlative: a clause the table calls UNFAVOURABLE must carry none.
_PROMISE_STEMS = ("excellent", "best", "strongest", "bless", "windfall", "lucky", "auspicious", "boon")

_UNSOURCED_PHRASES = [
    "most benevolent", "benevolent transit", "one of the best", "one of the strongest",
    "excellent for", "once every", "rare year", "approx — verify", "guaranteed", "Health improves",
    "dusthana", "Your Lagna lord", "impacts you more than average",
]


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


def _entered(body: int, sign: int, after: datetime, y0: int = 2026, y1: int = 2029) -> datetime:
    """First ingress of `body` into `sign` on or after `after` (IST)."""
    hits = [t for t, s in _ingresses(body, y0, y1) if s == sign and t >= after]
    assert hits, f"no ingress of body {body} into sign {sign} after {after}"
    return hits[0]


def _station(body: int, kind: str, after: datetime, y0: int = 2026, y1: int = 2029) -> datetime:
    hits = [t for t, k in _stations(body, y0, y1) if k == kind and t >= after]
    assert hits, f"no {kind} station of body {body} after {after}"
    return hits[0]


def _d(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=IST)


@functools.cache
def _computed_2027() -> dict:
    """Every dated event the page may state, from the ephemeris (see the provenance block above)."""
    jup, sat, mars, merc = swe.JUPITER, swe.SATURN, swe.MARS, swe.MERCURY
    y26, y27 = _d(2026, 6, 1), _d(2027, 1, 1)
    mercury_retro = [t for t, k in _stations(merc, 2027, 2028) if k == "retro"]
    mercury_direct = [t for t, k in _stations(merc, 2027, 2028) if k == "direct"]
    return {
        "jupiter_retro_2026": _station(jup, "retro", y26),
        "jupiter_cancer": _entered(jup, CANCER, y27),
        "jupiter_direct": _station(jup, "direct", y27),
        "jupiter_leo": _entered(jup, LEO, _entered(jup, CANCER, y27)),
        "jupiter_virgo": _entered(jup, VIRGO, y27),
        "saturn_pisces_2025": _entered(sat, PISCES, _d(2025, 1, 1), 2025, 2029),
        "saturn_aries": _entered(sat, ARIES, y27),
        "saturn_retro": _station(sat, "retro", y27),
        "saturn_pisces": _entered(sat, PISCES, _entered(sat, ARIES, y27)),
        "saturn_direct": _station(sat, "direct", _entered(sat, PISCES, _entered(sat, ARIES, y27))),
        "saturn_aries_2028": _entered(sat, ARIES, _entered(sat, PISCES, _entered(sat, ARIES, y27))),
        "mars_retro": _station(mars, "retro", y27),
        "mars_cancer": _entered(mars, CANCER, y27),
        "mars_direct": _station(mars, "direct", y27),
        "mars_leo": _entered(mars, LEO, _entered(mars, CANCER, y27)),
        "mercury_retro": mercury_retro,
        "mercury_direct": mercury_direct,
        # The site's engine is TRUE_NODE (chart.py); Ketu is exactly opposite, so one ingress serves both.
        "rahu_capricorn_2026": _entered(swe.TRUE_NODE, CAPRICORN, y26),
        "rahu_sagittarius": _entered(swe.TRUE_NODE, SAGITTARIUS, y27),
        "mean_capricorn_2026": _entered(swe.MEAN_NODE, CAPRICORN, y26),
        "mean_sagittarius": _entered(swe.MEAN_NODE, SAGITTARIUS, y27),
    }


def _main() -> None:
    ev = _computed_2027()
    for key, val in ev.items():
        vals = val if isinstance(val, list) else [val]
        print(f"{key:22} " + ", ".join(f"{v:%Y-%m-%d %H:%M} IST" for v in vals))


# --------------------------------------------------------------------------- page helpers

def _html(client, path: str) -> str:
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    return r.text


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _page(client, slug: str = SLUG) -> str:
    """The <article> element only: the surrounding chrome carries inline scripts and nav text that
    are not claims (a bare 'guaranteed' lives in the analytics snippet)."""
    html = _html(client, f"/learn/{slug}/")
    start = html.index("<article")
    return html[start: html.index("</article>", start)]


def _article(slug: str = SLUG):
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == slug)


def _registry_text(slug: str = SLUG) -> str:
    a = _article(slug)
    return " ".join([a.summary, a.seo_title, a.seo_description, a.llm_summary]
                    + [f["q"] + " " + f["a"] for f in a.faqs])


def _within_a_day(page_date: datetime, computed: datetime) -> bool:
    return abs((page_date.date() - computed.date()).days) <= 1


def _parse(day_month_year: str) -> datetime:
    return datetime.strptime(day_month_year, "%d %B %Y").replace(tzinfo=IST)


def _key_dates(page: str) -> list[tuple[datetime, str]]:
    section = page[page.index("Key 2027 dates to watch"):]
    section = section[: section.index("</ul>")]
    items = re.findall(r"<li><strong>(\d{1,2} \w+ \d{4})</strong> — (.*?)</li>", section, re.S)
    return [(_parse(d), re.sub(r"<[^>]+>", "", desc)) for d, desc in items]


def _house_from(moon: str, planet_sign: int) -> int:
    return (planet_sign - ZODIAC.index(moon)) % 12 + 1


_ORD = re.compile(r"(\d+)(?:st|nd|rd|th)")


def _rashi_blocks(page: str) -> dict[str, tuple[str, dict[str, str]]]:
    """Moon sign -> (lead paragraph text, {'Saturn'|'Jupiter'|'Rahu and Ketu': bullet text})."""
    found = re.findall(r"<h3>(\w+) / \w+</h3>\s*<p>(.*?)</p>\s*<ul>(.*?)</ul>", page, re.S)
    assert [name for name, _, _ in found] == ZODIAC, [name for name, _, _ in found]
    out = {}
    for name, lead, ul in found:
        items = re.findall(r"<li><strong>([^<:]+):</strong> (.*?)</li>", ul, re.S)
        assert [k for k, _ in items] == ["Saturn", "Jupiter", "Rahu and Ketu"], (name, [k for k, _ in items])
        out[name] = (re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", lead)),
                     {k: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", v)) for k, v in items})
    return out


def _verdict_clauses(text: str, sign_names: tuple[str, ...]) -> list[tuple[str, str, int, str]]:
    """[(verdict, sign, stated house, whole clause)] for '<verdict> in <Sign> (<Nth> from you: ...)'."""
    pat = "|".join(sign_names)
    return [(m.group(1), m.group(2), int(m.group(3)), m.group(0))
            for m in re.finditer(rf"\b(favourable|unfavourable) in ({pat}) \((\d+)(?:st|nd|rd|th) from you[^)]*\)", text)]


# --------------------------------------------------------------------------- the ephemeris itself

def test_jupiter_and_saturn_sign_sequences_in_2027_are_what_the_page_assumes():
    """The house arithmetic below assumes these sign sequences; the ephemeris, not the test, says so."""
    jan1, dec31 = swe.julday(2027, 1, 1, 0.0), swe.julday(2027, 12, 31, 0.0)
    assert _sign(jan1, swe.JUPITER) == LEO and _sign(dec31, swe.JUPITER) == VIRGO
    assert [s for t, s in _ingresses(swe.JUPITER, 2027, 2028)] == [CANCER, LEO, VIRGO]
    assert _sign(jan1, swe.SATURN) == PISCES and _sign(dec31, swe.SATURN) == PISCES
    assert [s for t, s in _ingresses(swe.SATURN, 2027, 2028)] == [ARIES, PISCES]


def test_rahu_and_ketu_do_not_change_sign_in_2027_on_either_node():
    for node in (swe.TRUE_NODE, swe.MEAN_NODE):
        assert not _ingresses(node, 2027, 2028), f"node {node} changes sign in 2027 after all"
        assert _sign(swe.julday(2027, 6, 1, 0.0), node) == CAPRICORN
    ev = _computed_2027()
    assert ev["rahu_sagittarius"].year == 2028 and ev["mean_sagittarius"].year == 2028


def test_the_dates_the_2026_page_states_for_2027_are_the_computed_ones_to_the_day():
    """AC4: gochar-2026 and gochar-2027 agree, and both equal the ephemeris day exactly (#1071)."""
    ev = _computed_2027()
    def mmdd(dt: datetime) -> tuple[int, int, int]:
        return (dt.year, dt.month, dt.day)

    wanted = {
        "Jupiter enters Cancer": (ev["jupiter_cancer"], r"25 January 2027"),
        "Jupiter enters Leo": (ev["jupiter_leo"], r"26 June 2027"),
        "Saturn enters Aries": (ev["saturn_aries"], r"3 June 2027"),
        "Saturn enters Pisces": (ev["saturn_pisces"], r"20 October 2027"),
        "Jupiter direct": (ev["jupiter_direct"], r"13 April 2027"),
    }
    for label, (computed, literal) in wanted.items():
        assert mmdd(_parse(literal)) == mmdd(computed), (label, literal, computed)
        for slug in (SLUG_2026, SLUG):
            # The template text, never "template or registry": the 2026 FAQ also carries these dates,
            # so an either/or let a wrong date in the 2026 body pass (found by the row that did it).
            assert literal in _article_template(slug), f"{slug} body does not state {label} as {literal}"


def _article_template(slug: str) -> str:
    root = Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "templates" / "learn"
    return _text((root / f"{slug}.html").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- Key dates and prose dates

def test_every_key_date_matches_the_ephemeris_within_a_day(client):
    got = _key_dates(_page(client))
    ev = _computed_2027()

    def pick(*words):
        return [(d, desc) for d, desc in got if all(w in desc for w in words)]

    singles = [
        ("Jupiter turns retrograde in Leo", ("Jupiter", "turns retrograde"), ev["jupiter_retro_2026"]),
        ("Mars turns retrograde", ("Mars", "turns retrograde"), ev["mars_retro"]),
        ("Jupiter enters Cancer", ("Jupiter", "enters Cancer"), ev["jupiter_cancer"]),
        ("Mars moves back into Cancer", ("Mars", "back into Cancer"), ev["mars_cancer"]),
        ("Jupiter turns direct", ("Jupiter", "turns direct"), ev["jupiter_direct"]),
        ("Saturn enters Aries", ("Saturn enters Aries",), ev["saturn_aries"]),
        ("Jupiter enters Leo", ("Jupiter", "enters Leo"), ev["jupiter_leo"]),
        ("Saturn turns retrograde", ("Saturn", "turns retrograde"), ev["saturn_retro"]),
        ("Saturn slips back into Pisces", ("Saturn", "back into Pisces"), ev["saturn_pisces"]),
        ("Jupiter enters Virgo", ("Jupiter", "enters Virgo"), ev["jupiter_virgo"]),
        ("Saturn turns direct", ("Saturn", "turns direct"), ev["saturn_direct"]),
    ]
    for label, words, computed in singles:
        hits = pick(*words)
        assert len(hits) == 1, f"Key dates must carry exactly one '{label}' item, found {len(hits)}"
        assert _within_a_day(hits[0][0], computed), (
            f"'{label}': page says {hits[0][0]:%d %B %Y}, ephemeris says {computed:%d %B %Y %H:%M} IST")

    mercury = sorted(d for d, _ in pick("Mercury", "turns retrograde"))
    assert len(mercury) == len(ev["mercury_retro"]) == 3, f"Mercury has {len(ev['mercury_retro'])} stations in 2027"
    for page_date, computed in zip(mercury, ev["mercury_retro"]):
        assert _within_a_day(page_date, computed), (page_date, computed)


def test_key_dates_are_chronological_and_each_carries_a_full_date(client):
    page = _page(client)
    dates = [d for d, _ in _key_dates(page)]
    assert len(dates) == 14, f"expected 14 dated items, parsed {len(dates)}"
    assert dates == sorted(dates), "Key dates list is out of chronological order"
    section = page[page.index("Key 2027 dates to watch"):]
    section = section[: section.index("</ul>")]
    assert section.count("<li>") == len(dates), "a Key-dates item has no leading '<strong>D Month YYYY</strong>'"


def test_key_date_tails_name_the_following_station(client):
    """'direct again D Month' tails are the station after that retrograde, not a guess."""
    ev = _computed_2027()
    items = _key_dates(_page(client))

    def tail(desc: str) -> datetime | None:
        m = re.search(r"direct again (\d{1,2} \w+)( \d{4})?", desc)
        if not m:
            return None
        return _parse(f"{m.group(1)}{m.group(2) or ' 2027'}")

    directs = {
        "Mars": [t for t, k in _stations(swe.MARS, 2027, 2028) if k == "direct"],
        "Jupiter": [t for t, k in _stations(swe.JUPITER, 2026, 2029) if k == "direct"],
        "Mercury": ev["mercury_direct"],
    }
    seen = 0
    for d, desc in items:
        t = tail(desc)
        if t is None:
            continue
        planet = desc.split()[0]
        nxt = min(x for x in directs[planet] if x > d.replace(tzinfo=IST))
        assert _within_a_day(t, nxt), f"{planet}: tail says {t:%d %B %Y}, next direct station {nxt:%d %B %Y}"
        seen += 1
    assert seen == 5, f"expected 5 'direct again' tails (Jupiter, Mars, Mercury x3), found {seen}"


def test_mars_and_saturn_range_bullets_give_the_computed_dates(client):
    text = _text(_page(client))
    ev = _computed_2027()
    m = re.search(r"Mars retrograde \((\d{1,2} \w+)[–-](\d{1,2} \w+) 2027\)", text)
    assert m, "Mars retrograde bullet has no exact range"
    assert _within_a_day(_parse(f"{m.group(1)} 2027"), ev["mars_retro"])
    assert _within_a_day(_parse(f"{m.group(2)} 2027"), ev["mars_direct"])
    m = re.search(r"Mars in Cancer \((\d{1,2} \w+)[–-](\d{1,2} \w+) 2027\)", text)
    assert m, "Mars-in-Cancer bullet has no exact range"
    assert _within_a_day(_parse(f"{m.group(1)} 2027"), ev["mars_cancer"])
    assert _within_a_day(_parse(f"{m.group(2)} 2027"), ev["mars_leo"])
    m = re.search(r"Saturn retrograde \((\d{1,2} \w+)[–-](\d{1,2} \w+ 2027)\)", text)
    assert m, "Saturn retrograde bullet has no exact range"
    assert _within_a_day(_parse(f"{m.group(1)} 2027"), ev["saturn_retro"])
    assert _within_a_day(_parse(m.group(2)), ev["saturn_direct"])
    m = re.search(r"\(9 February[–-]3 March, 10 June[–-]5 July, 7 October[–-]28 October\)", text)
    assert m, "Mercury episode ranges missing"
    for d, mr in zip([_parse("9 February 2027"), _parse("10 June 2027"), _parse("7 October 2027")],
                     ev["mercury_retro"]):
        assert _within_a_day(d, mr)
    for d, md in zip([_parse("3 March 2027"), _parse("5 July 2027"), _parse("28 October 2027")],
                     ev["mercury_direct"]):
        assert _within_a_day(d, md)


def test_jupiter_and_saturn_sentences_in_the_body_match_the_ephemeris(client):
    text = _text(_page(client))
    ev = _computed_2027()
    m = re.search(r"it is in Leo until (\d{1,2} \w+), in Cancer from (\d{1,2} \w+) to (\d{1,2} \w+), in Leo again "
                  r"from (\d{1,2} \w+) to (\d{1,2} \w+), and in Virgo from (\d{1,2} \w+)\.", text)
    assert m, "Jupiter four-stretch sentence missing"
    want = [ev["jupiter_cancer"], ev["jupiter_cancer"], ev["jupiter_leo"], ev["jupiter_leo"],
            ev["jupiter_virgo"], ev["jupiter_virgo"]]
    for got, w in zip(m.groups(), want):
        assert _within_a_day(_parse(f"{got} 2027"), w), (got, w)
    m = re.search(r"Jupiter turns retrograde in Leo on (\d{1,2} \w+ 2026) and direct again in Cancer on "
                  r"(\d{1,2} \w+ 2027)", text)
    assert m, "Jupiter retrograde sentence missing"
    assert _within_a_day(_parse(m.group(1)), ev["jupiter_retro_2026"])
    assert _within_a_day(_parse(m.group(2)), ev["jupiter_direct"])
    m = re.search(r"in Pisces \(Meena\) since (\d{1,2} \w+ 2025)\. On (\d{1,2} \w+ 2027) it enters Aries \(Mesha\)\. "
                  r"It turns retrograde there on (\d{1,2} \w+), moves back into Pisces on (\d{1,2} \w+), turns "
                  r"direct in Pisces on (\d{1,2} \w+), and re-enters Aries on (\d{1,2} \w+ 2028)\.", text)
    assert m, "Saturn sentence not found in the expected shape"
    g = m.groups()
    assert _within_a_day(_parse(g[0]), ev["saturn_pisces_2025"])
    assert _within_a_day(_parse(g[1]), ev["saturn_aries"])
    assert _within_a_day(_parse(f"{g[2]} 2027"), ev["saturn_retro"])
    assert _within_a_day(_parse(f"{g[3]} 2027"), ev["saturn_pisces"])
    assert _within_a_day(_parse(f"{g[4]} 2027"), ev["saturn_direct"])
    assert _within_a_day(_parse(g[5]), ev["saturn_aries_2028"])


def test_rahu_ketu_dates_name_the_true_node_and_the_mean_node(client):
    text = _text(_page(client))
    ev = _computed_2027()
    assert _within_a_day(_parse("25 November 2026"), ev["rahu_capricorn_2026"])
    assert _within_a_day(_parse("24 May 2028"), ev["rahu_sagittarius"])
    assert _within_a_day(_parse("5 December 2026"), ev["mean_capricorn_2026"])
    assert _within_a_day(_parse("24 June 2028"), ev["mean_sagittarius"])
    assert "on 25 November 2026" in text and "Rahu into Sagittarius and Ketu into Gemini on 24 May 2028" in text
    assert "true node" in text and "mean node" in text
    assert "Rahu and Ketu do not change sign at all in 2027" in text


# --------------------------------------------------------------------------- #1100-style: every dated claim

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATE_RX = re.compile(rf"\b(\d{{1,2}}) ({_MONTHS})(?: (\d{{4}}))?")


@functools.cache
def _all_event_days() -> tuple:
    """Every ingress and station any date on the page may name, as IST dates."""
    events = []
    for body, y0, y1 in ((swe.JUPITER, 2026, 2029), (swe.SATURN, 2025, 2029), (swe.MARS, 2026, 2029),
                         (swe.TRUE_NODE, 2026, 2029), (swe.MEAN_NODE, 2026, 2029)):
        events += [t.date() for t, _ in _ingresses(body, y0, y1)]
    for body, y0, y1 in ((swe.MERCURY, 2026, 2029), (swe.JUPITER, 2026, 2029), (swe.SATURN, 2026, 2029),
                         (swe.MARS, 2026, 2029)):
        events += [t.date() for t, _ in _stations(body, y0, y1)]
    return tuple(events)


def _unmatched_dates(text: str) -> list[str]:
    """Dates in `text` that no ephemeris event falls within a day of; a year-less date is read in 2027."""
    events = _all_event_days()
    bad = []
    for m in _DATE_RX.finditer(text):
        day, month, year = int(m.group(1)), m.group(2), m.group(3)
        mo = datetime.strptime(month, "%B").month

        def close(ev):
            if year is not None:
                return abs((datetime(int(year), mo, day).date() - ev).days) <= 1
            return ev.year == 2027 and abs((datetime(2027, mo, day).date() - ev).days) <= 1

        if not any(close(ev) for ev in events):
            bad.append(m.group(0))
    return bad


def test_every_dated_claim_on_the_page_and_registry_is_an_ephemeris_event(client):
    """A date anywhere on the page, in its FAQs, summary or meta names a real ingress or station.

    The Key-dates and prose tests pin the dates they name; this one catches the rest (a per-rashi date,
    a FAQ tail) and is why the page reports no unattributable date (#1071 AC3).
    """
    for label, text in (("page", _text(_page(client))), ("registry", _registry_text())):
        assert len(_DATE_RX.findall(text)) >= (40 if label == "page" else 15), label
        assert not _unmatched_dates(text), f"{label}: dates no ephemeris event supports: {_unmatched_dates(text)}"


def test_the_date_check_itself_catches_a_moved_date():
    assert _unmatched_dates("Saturn moves into Aries on 5 June 2027") == ["5 June 2027"]
    assert _unmatched_dates("Saturn moves into Aries on 3 June 2027") == []
    assert _unmatched_dates("Jupiter enters Cancer on 25 February") == ["25 February"]
    assert _unmatched_dates("Jupiter enters Cancer on 25 January") == []


def test_every_rashi_section_date_is_a_known_slow_planet_date(client):
    allowed = {"3 June", "20 October", "25 January", "26 June", "26 November", "25 November 2026",
               "23 February 2028"}
    for moon, (lead, items) in _rashi_blocks(_page(client)).items():
        for text in [lead, *items.values()]:
            for m in _DATE_RX.finditer(text):
                assert m.group(0) in allowed, f"{moon}: unexpected date {m.group(0)!r} in {text[:70]!r}"


# --------------------------------------------------------------------------- the Gochara invariant

def test_typed_favourable_sets_equal_the_knowledge_table_and_the_code():
    from astro_ai.chart import _GOCHARA_BENEFIC_FROM_MOON

    text = (KNOWLEDGE / "vedic_reference.md").read_text(encoding="utf-8")
    section = text[text.index("## 2A. Gochara"):]
    rows = dict(re.findall(r"^\| (Jupiter|Saturn|Rahu / Ketu) \| ([\d, ]+) \|", section, re.M))
    parse = lambda s: {int(x) for x in s.split(",")}  # noqa: E731
    assert parse(rows["Jupiter"]) == JUPITER_FAVOURABLE
    assert parse(rows["Saturn"]) == SATURN_FAVOURABLE
    assert parse(rows["Rahu / Ketu"]) == RAHU_FAVOURABLE
    assert set(_GOCHARA_BENEFIC_FROM_MOON["Jupiter"]) == JUPITER_FAVOURABLE
    assert set(_GOCHARA_BENEFIC_FROM_MOON["Saturn"]) == SATURN_FAVOURABLE
    assert set(_GOCHARA_BENEFIC_FROM_MOON["Rahu"]) == RAHU_FAVOURABLE
    assert set(_GOCHARA_BENEFIC_FROM_MOON["Ketu"]) == RAHU_FAVOURABLE


def test_house_themes_are_in_the_knowledge_file():
    text = (KNOWLEDGE / "houses.md").read_text(encoding="utf-8")
    heads = {int(m.group(1)): m.group(0).lower() for m in re.finditer(r"^## (\d+)(?:st|nd|rd|th) House.*$", text, re.M)}
    assert sorted(heads) == list(range(1, 13)), sorted(heads)
    for house, themes in HOUSE_THEMES.items():
        for word in themes.split(", "):
            assert word in heads[house], f"house {house}: theme {word!r} is not in its houses.md heading"


def test_each_moon_sign_names_the_right_houses_and_the_tables_verdicts(client):
    """Saturn (Pisces, Aries), Jupiter (Cancer, Leo, Virgo), Rahu (Capricorn), Ketu (Cancer): house and verdict."""
    blocks = _rashi_blocks(_page(client))
    for moon, (_, items) in blocks.items():
        for planet, signs, fav in (("Saturn", ("Pisces", "Aries"), SATURN_FAVOURABLE),
                                   ("Jupiter", ("Cancer", "Leo", "Virgo"), JUPITER_FAVOURABLE)):
            clauses = _verdict_clauses(items[planet], signs)
            assert [c[1] for c in clauses] == list(signs), f"{moon} {planet}: signs {[c[1] for c in clauses]}"
            for verdict, sign, stated, clause in clauses:
                house = _house_from(moon, ZODIAC.index(sign))
                assert stated == house, f"{moon}: {planet} in {sign} is the {house}th, page says {stated}th"
                assert (verdict == "favourable") == (house in fav), (
                    f"{moon}: {planet} in {sign} ({house}th) is "
                    f"{'favourable' if house in fav else 'unfavourable'} on the table; page: {clause!r}")
                assert HOUSE_THEMES[house] in clause, f"{moon}: wrong theme for house {house}: {clause!r}"
        for planet, sign in (("Rahu", CAPRICORN), ("Ketu", CANCER)):
            m = re.search(rf"{planet} in {ZODIAC[sign]} \((\d+)(?:st|nd|rd|th) from you: ([^)]*)\)(?: is counted)? as "
                          rf"(favourable|unfavourable)", items["Rahu and Ketu"])
            assert m, f"{moon}: no verdict for {planet}"
            house = _house_from(moon, sign)
            assert int(m.group(1)) == house, f"{moon}: {planet} is the {house}th, page says {m.group(1)}th"
            assert (m.group(3) == "favourable") == (house in RAHU_FAVOURABLE), (moon, planet, house, m.group(3))
            assert m.group(2) == HOUSE_THEMES[house]
        assert "all year" in items["Rahu and Ketu"]


def test_a_favourable_clause_never_reads_as_a_harm_nor_an_unfavourable_one_as_a_promise(client):
    for moon, (_, items) in _rashi_blocks(_page(client)).items():
        for planet, signs in (("Saturn", ("Pisces", "Aries")), ("Jupiter", ("Cancer", "Leo", "Virgo"))):
            for verdict, sign, house, clause in _verdict_clauses(items[planet], signs):
                low = clause.lower()
                stems = _HARM_STEMS if verdict == "favourable" else _PROMISE_STEMS
                for stem in stems:
                    assert not re.search(rf"\b{stem}", low), f"{moon}: {verdict} clause carries {stem!r}: {clause!r}"


def test_the_page_states_the_table_does_not_adjust_for_dignity_and_is_a_first_approximation(client):
    text = _text(_page(client))
    assert "The classical Gochara table does not adjust for that" in text
    assert "judges the house from your Moon and not the sign's dignity" in text
    assert "first approximation" in text
    assert "weigh it with your dasha and natal chart" in text
    # No sentence about exaltation or debilitation may carry a promise: the table scores by house only.
    for sentence in re.split(r"(?<=[.!?]) ", text):
        if re.search(r"exalt|debilitat", sentence, re.I):
            for stem in ("bless", "auspicious", "windfall", "lucky", "fortunate", "promise", "boon", "gains", "good"):
                assert stem not in sentence.lower(), f"dignity sentence reads as a verdict: {sentence!r}"


# --------------------------------------------------------------------------- Saturn labels (Sade Sati, Kantaka, Ashtama)

_PHASE_BY_HOUSE = {12: "rising", 1: "peak", 2: "setting"}


def _saturn_houses(moon: str) -> dict[str, int]:
    return {"Pisces": _house_from(moon, PISCES), "Aries": _house_from(moon, ARIES)}


def test_sade_sati_kantaka_and_ashtama_labels_follow_saturns_house(client):
    """A label is on a Moon sign's section iff Saturn is in the matching house from it at some point in 2027."""
    for moon, (lead, items) in _rashi_blocks(_page(client)).items():
        houses = set(_saturn_houses(moon).values())
        section = lead + " " + " ".join(items.values())
        assert ("Sade Sati" in section) == bool(houses & set(_PHASE_BY_HOUSE)), (
            f"{moon}: Saturn houses {sorted(houses)}; Sade Sati label mismatch: {lead!r}")
        assert ("Kantaka" in section) == (4 in houses), f"{moon}: Kantaka label mismatch ({sorted(houses)})"
        assert ("Ashtama" in section) == (8 in houses), f"{moon}: Ashtama label mismatch ({sorted(houses)})"
        in_sade_sati = bool(houses & set(_PHASE_BY_HOUSE))
        assert ("Sade Sati" in lead.split(".")[0]) == in_sade_sati, (
            f"{moon}: Sade Sati must open the lead exactly when Saturn is in the 12th, 1st or 2nd: {lead!r}")
        phases = {_PHASE_BY_HOUSE[h] for h in houses if h in _PHASE_BY_HOUSE}
        said = set(re.findall(r"\b(rising|peak|setting) phase", lead))
        assert said == phases, f"{moon}: lead names phases {sorted(said)}, Saturn's houses give {sorted(phases)}"


def test_the_saturn_section_lists_who_is_in_sade_sati_in_each_stretch(client):
    text = _text(_page(client))
    for label, sat_sign, marker in (("first", PISCES, "Until 3 June \\(Saturn in Pisces\\):"),
                                    ("second", ARIES, "3 June to 20 October \\(Saturn in Aries\\):")):
        m = re.search(marker + r" (.*?)(?: 3 June to 20 October| From 20 October|$)", text)
        assert m, label
        said = {(moon, phase) for moon, phase in
                re.findall(r"(\w+) Moons (?:are in |enter |in )?the (rising|peak|setting) phase", m.group(1))}
        expected = {(moon, _PHASE_BY_HOUSE[_house_from(moon, sat_sign)]) for moon in ZODIAC
                    if _house_from(moon, sat_sign) in _PHASE_BY_HOUSE}
        # Aquarius leaves Sade Sati in the second stretch; it is named only as being outside it.
        assert said == expected, f"{label} stretch: page {sorted(said)} vs table {sorted(expected)}"
    outside = {m for m in ZODIAC if _house_from(m, ARIES) not in _PHASE_BY_HOUSE
               and _house_from(m, PISCES) in _PHASE_BY_HOUSE}
    assert outside == {"Aquarius"}, outside
    third = re.search(r"From 20 October \(Saturn back in Pisces\): (.*?)\.", text).group(1)
    in_pisces = {m for m in ZODIAC if _house_from(m, PISCES) in _PHASE_BY_HOUSE}
    for moon in in_pisces:
        assert moon in third, f"{moon} is in Sade Sati with Saturn in Pisces but the third stretch omits it"
    assert "Taurus Moons are outside it until Saturn re-enters Aries on 23 February 2028" in third
    assert _house_from("Taurus", PISCES) == 11


def test_kantaka_and_ashtama_moon_signs_named_in_the_saturn_section_are_right(client):
    text = _text(_page(client))
    m = re.search(r"Kantaka Shani \(Saturn 4th from your Moon: (.*?)\) and Ashtama Shani "
                  r"\(Saturn 8th from your Moon: (.*?)\)\.", text)
    assert m, "Kantaka/Ashtama sentence not found"
    for group, house in ((m.group(1), 4), (m.group(2), 8)):
        said = set(re.findall(r"(\w+) Moons in (Pisces|Aries)", group))
        expected = {(moon, sign) for moon in ZODIAC for sign in ("Pisces", "Aries")
                    if _house_from(moon, ZODIAC.index(sign)) == house}
        assert said == expected, (house, said, expected)
    assert "Those two names are modern usage, not classical terms" in text


# --------------------------------------------------------------------------- wording, registry, wiring

def test_page_and_registry_carry_no_unsourced_superlative_or_stale_phrase(client):
    text = _text(_page(client))
    reg = _registry_text()
    for phrase in _UNSOURCED_PHRASES:
        assert phrase not in text, f"unsourced wording on the page: {phrase!r}"
        assert phrase not in reg, f"unsourced wording in the registry: {phrase!r}"
    for word in ("best", "strongest", "excellent", "luckiest", "benevolent"):
        assert not re.search(rf"\b{word}\b", text, re.I), f"superlative on the page: {word!r}"
        assert not re.search(rf"\b{word}\b", reg, re.I), f"superlative in the registry: {word!r}"


def test_the_page_states_its_convention_and_the_registry_entry_is_wired(client):
    text = _text(_page(client))
    assert "Lahiri (sidereal)" in text and "Indian Standard Time" in text and "Swiss Ephemeris" in text
    assert "true node" in text
    a = _article()
    assert "2027" in a.title and a.last_updated == "2026-11"
    assert a.hero_image == f"/static/learn/{SLUG}/hero.svg" and a.faqs
    assert "In short" in text
    from astro_ai.learn_registry import ARTICLES

    slugs = {x.slug for x in ARTICLES}
    assert set(a.related) <= slugs, set(a.related) - slugs
    assert len(a.seo_title) <= 60, len(a.seo_title)
    assert len(a.seo_description) <= 160, len(a.seo_description)


def test_the_registry_faqs_are_the_computed_dates(client):
    ev = _computed_2027()
    faq = {f["q"]: f["a"] for f in _article().faqs}
    major = faq["What are the major planetary transits in 2027?"]
    m = re.search(r"Leo until (\d{1,2} \w+ 2027), in Cancer from \d{1,2} \w+ to (\d{1,2} \w+), in Leo again from "
                  r"\d{1,2} \w+ to (\d{1,2} \w+) and in Virgo from (\d{1,2} \w+)\. Saturn moves from Pisces into Aries "
                  r"on (\d{1,2} \w+ 2027) and back into Pisces on (\d{1,2} \w+)", major)
    assert m, "major-transits FAQ not in the expected shape"
    jc, jl, jv = ev["jupiter_cancer"], ev["jupiter_leo"], ev["jupiter_virgo"]
    for got, want in zip(m.groups(), (jc, jl, jv, jv, ev["saturn_aries"], ev["saturn_pisces"])):
        got = got if got[-4:].isdigit() else f"{got} 2027"
        assert _within_a_day(_parse(got), want), (got, want)
    saturn = faq["When does Saturn enter Aries in 2027?"]
    m = re.search(r"enters Aries on (\d{1,2} \w+ 2027), turns retrograde there on (\d{1,2} \w+), slips back into "
                  r"Pisces on (\d{1,2} \w+) and turns direct in Pisces on (\d{1,2} \w+)\. It re-enters Aries on "
                  r"(\d{1,2} \w+ 2028)", saturn)
    assert m, "Saturn FAQ not in the expected shape"
    for got, want in zip(m.groups(), (ev["saturn_aries"], ev["saturn_retro"], ev["saturn_pisces"],
                                      ev["saturn_direct"], ev["saturn_aries_2028"])):
        got = got if got[-4:].isdigit() else f"{got} 2027"
        assert _within_a_day(_parse(got), want), (got, want)
    jupiter = faq["Where is Jupiter in 2027?"]
    assert "from 25 January to 26 June" in jupiter and "turns direct in Cancer on 13 April" in jupiter
    rahu = faq["Do Rahu and Ketu change sign in 2027?"]
    assert rahu.startswith("No.") and "24 May 2028" in rahu and "5 December 2026" in rahu


def test_the_new_entry_stays_out_of_the_llm_path():
    """AC8: llm_summary is empty (the article is not exposed to the natal prompt) and chart.py never names it."""
    assert _article().llm_summary == ""
    root = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
    assert SLUG not in (root / "chart.py").read_text(encoding="utf-8")


def test_gochar_2026_links_to_the_2027_page_exactly_once(client):
    html = _page(client, SLUG_2026)
    assert html.count(f'href="/learn/{SLUG}/"') == 1, "AC7: exactly one contextual link from the 2026 page"


if __name__ == "__main__":
    _main()
