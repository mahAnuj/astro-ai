"""#1004: learn surfaces stop mis-ranking the Vimshottari Mahadasha lengths, and /learn/jupiter-in-10th-house-career/
stops stating a wrong Jupiter antardasha range and an unsourced Neechabhanga rule.

`knowledge/vedic_reference.md` 5.1 holds the nine durations: Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18,
Jupiter 16, Saturn 19, Mercury 17. Ranked: Venus 20 > Saturn 19 > Rahu 18 > Mercury 17 > Jupiter 16, so Rahu is
third-longest, Mercury fourth, Jupiter fifth, and Saturn (not Venus) is the second-longest. Pages said Rahu was
second-longest, Jupiter second- or third-longest, Mercury second-longest 'after Saturn and Venus' (which contradicts
itself), and Saturn 'the longest of all'. The Jupiter-in-10th page also said Jupiter's antardasha runs 2y4m to 2y10m
(it is 16/120 of the Mahadasha: 9.6 months in Sun to 2y8m in Venus) and listed 'Mars/Saturn in a kendra' as
Neechabhanga with invented reasoning; `knowledge/` holds only the D-9 rule (divisional_charts.md) and 'see BPHS'
(rashis.md).

Two kinds of test: phrase tests pin each corrected surface through the real route and the registry fields the
route renders; the derive-from-table tests read 5.1 and check EVERY '<planet> Mahadasha ... Nth-longest' claim in
the learn templates and registry against the rank computed from the table, so a new mis-ranking on another page is
caught too.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
J10 = "jupiter-in-10th-house-career"
_ORD = {"second": 2, "third": 3, "fourth": 4, "fifth": 5}


def _durations() -> dict[str, int]:
    """Parse vedic_reference.md 5.1 (the knowledge file is the source, not a copy in this test)."""
    md = (ROOT / "knowledge" / "vedic_reference.md").read_text()
    sec = md[md.index("### 5.1 Sequence and durations"):md.index("### 5.2")]
    pairs = re.findall(r"(Ketu|Venus|Sun|Moon|Mars|Rahu|Jupiter|Saturn|Mercury)\s+(\d+)y", sec)
    d = {k: int(v) for k, v in pairs}
    assert len(d) == 9 and sum(d.values()) == 120
    return d


def _rank(planet: str) -> int:
    d = _durations()
    return sorted(d.values(), reverse=True).index(d[planet]) + 1


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def _text(client, slug: str) -> str:
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    return _plain(r.text)


def _article(slug: str):
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == slug)


def _registry_text(slug: str) -> str:
    a = _article(slug)
    return " ".join([a.summary, a.llm_summary] + [f["q"] + " " + f["a"] for f in a.faqs])


def test_table_ranking_is_what_the_fix_assumes():
    assert [_rank(p) for p in ("Venus", "Saturn", "Rahu", "Mercury", "Jupiter")] == [1, 2, 3, 4, 5]
    assert _rank("Sun") == 9


def test_every_ordinal_longest_claim_matches_the_table():
    """Scan every learn template and the registry: a sentence naming exactly one planet's Mahadasha and an
    'Nth-longest' ordinal must use that planet's rank from 5.1."""
    d = _durations()
    sources = {p.name: p.read_text() for p in (ROOT / "templates" / "learn").glob("*.html")}
    sources["learn_registry.py"] = (ROOT / "learn_registry.py").read_text()
    checked = 0
    for name, raw in sources.items():
        for sent in re.split(r"(?<=[.!?])\s+|\\n|</p>|</li>", _plain(raw)):
            m = re.search(r"\b(second|third|fourth|fifth)[- ]longest", sent)
            if not m or "Mahadasha" not in sent:
                continue
            planets = [p for p in d if re.search(rf"\b{p} (Mahadasha|Maha)\b", sent)]
            if len(planets) != 1:
                continue
            checked += 1
            p = planets[0]
            assert _ORD[m.group(1)] == _rank(p), f"{name}: {p} is rank {_rank(p)}, page says {m.group(1)}-longest: {sent[:160]}"
    assert checked >= 8  # Rahu x4, Jupiter x3, Mercury, Saturn x3, so a scan that reads nothing cannot pass


def test_nothing_calls_a_non_venus_mahadasha_the_longest_of_all():
    for name, raw in [(p.name, p.read_text()) for p in (ROOT / "templates" / "learn").glob("*.html")] + [
        ("learn_registry.py", (ROOT / "learn_registry.py").read_text())
    ]:
        t = _plain(raw)
        for m in re.finditer(r"(Saturn|Rahu|Jupiter|Mercury)[^.]{0,80}((?<!second-)(?<!third-)longest of all|the longest first-Mahadasha(?!s)|longest first-Mahadasha of any)", t):
            raise AssertionError(f"{name}: {m.group(0)}")


def test_rahu_pages_say_third_longest(client):
    t = _text(client, "rahu-mahadasha-career-problems")
    assert "Rahu Mahadasha is 18 years long — the third-longest planetary period in the Vimshottari cycle, after Venus (20) and Saturn (19)" in t
    t = _text(client, "rahu-in-vedic-astrology")
    assert "Rahu Mahadasha is the third-longest at 18 years (Venus at 20 is longest, then Saturn at 19)" in t


def test_rahu_registry_fields_say_third_longest():
    from astro_ai.learn_registry import ARTICLES

    blob = " ".join(
        a.summary + " " + a.llm_summary + " " + " ".join(f["a"] for f in a.faqs) for a in ARTICLES
    )
    assert "Rahu Mahadasha runs 18 years — the third-longest of the nine, after Venus (20) and Saturn (19)" in blob
    assert "Rahu Mahadasha (18 years) — the third-longest, and most disruptive" in blob
    assert "the third-longest of the nine Vimshottari Mahadashas (only Venus at 20 years and Saturn at 19 are longer)" in blob


def test_jupiter_and_mercury_pages_rank_correctly(client):
    t = _text(client, "guru-jupiter-in-vedic-astrology")
    assert "Jupiter Mahadasha is the fifth-longest at 16 years" in t
    t = _text(client, "budha-mercury-in-vedic-astrology")
    assert "Mercury Mahadasha runs 17 years — the fourth-longest, after Venus (20), Saturn (19) and Rahu (18)" in t


def test_saturn_is_second_longest_not_longest_of_all(client):
    assert "Saturn Mahadasha is the second-longest of all Mahadashas at 19 years (only Venus at 20 is longer)" in _text(client, "saturn-remedies")
    t = _text(client, "pushya-nakshatra")
    assert "19 years long — the second-longest of all Mahadashas, after Venus at 20" in t
    assert "often one of the longest first-Mahadashas people experience" in t
    assert "the second-longest of all Mahadashas at 19 years" in (ROOT / "learn_registry.py").read_text()


def test_rahu_first_mahadasha_is_not_the_longest_first_mahadasha(client):
    assert "Rahu's 18 years is the third-longest Mahadasha (only Venus at 20 and Saturn at 19 are longer)" in _text(client, "ardra-nakshatra")
    assert "Rahu's 18 years is third-longest, after Venus and Saturn" in _text(client, "swati-nakshatra")
    assert "18 years, the third-longest Mahadasha after Venus and Saturn" in (ROOT / "learn_registry.py").read_text()


def test_venus_longest_claims_are_untouched(client):
    assert "Venus Mahadasha is the longest Vimshottari period at 20 years" in _text(client, "shukra-venus-in-vedic-astrology")
    assert "longest of the seven visible-planet dashas" in _text(client, "venus-remedies")


def test_jupiter_10th_mahadasha_rank_and_antardasha_range(client):
    t = _text(client, J10)
    assert "the fifth-longest of the nine Vimshottari Mahadashas (Venus 20, Saturn 19, Rahu 18 and Mercury 17 are longer)" in t
    assert "Jupiter takes 16/120 of whichever Mahadasha it sits in" in t
    assert "just under 10 months inside Sun Mahadasha and up to 2 years 8 months inside Venus Mahadasha" in t
    assert "2 years 4 months 24 days inside Rahu" in t
    assert "2 years 10 months" not in t and "2 years 4 months to" not in t
    a = _registry_text(J10)
    assert "the fifth-longest of the nine Vimshottari periods" in a
    assert "16/120 of the outer Mahadasha: just under 10 months inside Sun Mahadasha, up to 2 years 8 months inside Venus Mahadasha" in a
    assert "second-longest" not in a and "2 years 10 months" not in a


def test_antardasha_range_is_derived_from_the_table():
    d = _durations()
    months = lambda md_years: 16 * md_years / 120 * 12  # noqa: E731 - Jupiter's share of a Mahadasha
    assert round(months(d["Sun"]), 1) == 9.6  # 'just under 10 months'
    assert months(d["Venus"]) == 32  # 2 years 8 months
    assert round(months(d["Rahu"]), 1) == 28.8  # 2 years 4 months 24 days, as the Rahu guide already states
    assert min(months(v) for k, v in d.items() if k != "Jupiter") == months(d["Sun"])
    assert max(months(v) for v in d.values()) == months(d["Venus"])


def test_neechabhanga_keeps_only_the_sourced_navamsha_rule(client):
    t = _text(client, J10)
    for gone in (
        "Saturn in a kendra",
        "Mars in a kendra",
        "Mars is close friend",
        "ruled by Moon",
        "Saturn in kendra, Mars in kendra",
    ):
        assert gone not in t, gone
    assert "a planet debilitated in the D-1 chart but exalted in the D-9 has the debilitation cancelled" in t
    assert "The fuller set of cancellation conditions is a matter for a chart reading" in t
    assert "the fuller conditions are a matter for a chart reading" in t
    assert "do not read this placement as a fixed sentence" in t


def test_page_keeps_its_headings_and_title(client):
    r = client.get(f"/learn/{J10}/")
    for h in (
        "When Jupiter in the 10th is weak or afflicted",
        "Per-ascendant variations",
        "When Jupiter in the 10th activates: the timing question",
    ):
        assert f"<h2>{h}</h2>" in r.text, h
    assert _article(J10).title == "Jupiter in the 10th House: Career, Hamsa Yoga, and the Dharmic Path"
