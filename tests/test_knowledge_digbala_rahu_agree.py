"""#1086: knowledge/ stops contradicting itself on Saturn's digbala and Rahu's exaltation, and no page repeats the
losing side.

Saturn's directional strength is in the 7th house (Rao, Integrated Approach §3.2.15: "Saturn is strong in the west
(7th house)"; grahas.md Directions and §9, houses.md 7th-house section). houses.md used to say "Saturn in 10th
(Digbala)" and five learn pages / registry fields repeated it (10th is the Sun's and Mars's). Rahu's exaltation is
Gemini in Rao's Table 6 and Taurus in Raman's Astrology for Beginners (two held books disagree); rashis.md said Taurus first, grahas.md Gemini first,
and two pages disagreed with each other. Both now lead with Gemini and mark the entry CONTESTED.

The page tests read the rendered route or the registry fields the route renders, so JSON-LD and page cannot disagree.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
KNOW = ROOT / "knowledge"
LEARN = ROOT / "templates" / "learn"

SATURN_PAGES = ("saturn-in-10th-house-career", "career-not-progressing")
RAHU_PAGES = ("the-9-grahas-overview", "kaal-sarp-dosh", "rahu-mahadasha-career-problems")


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s))


def _sentences(s: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+|\n", _plain(s))


_SATURN_10TH_DIGBALA = re.compile(
    r"saturn[^.]{0,160}(10th|tenth)[^.]{0,160}(dig ?bala|directional)"
    r"|saturn[^.]{0,160}(dig ?bala|directional)[^.]{0,160}(10th|tenth)"
    r"|(10th|tenth)[^.]{0,160}saturn[^.]{0,160}(dig ?bala|directional)",
    re.I,
)
_NEGATED = re.compile(r"\b(not|never|no)\b|NOT", re.I)


def _wrong_saturn_claims(text: str) -> list[str]:
    """Sentences tying Saturn, the 10th and digbala that do not negate the tie."""
    return [s for s in _sentences(text) if _SATURN_10TH_DIGBALA.search(s) and not _NEGATED.search(s)]


def _registry_text() -> str:
    from astro_ai.learn_registry import ARTICLES

    out = []
    for a in ARTICLES:
        out += [a.summary, a.seo_description or "", a.llm_summary or ""]
        out += [f["q"] + " " + f["a"] for f in a.faqs]
    return "\n".join(out)


def _row(md: str, planet: str, cells: int | None = None) -> str:
    """The dignity-table row: the first '| <planet> |' line that mentions a sign (other tables carry the name too)."""
    return next(
        l
        for l in md.splitlines()
        if l.startswith(f"| {planet} |") and re.search(r"Gemini|Taurus|Sagittarius|Scorpio", l)
    )


# ---- the two knowledge files agree -------------------------------------------------------------


def test_grahas_and_houses_both_put_saturns_digbala_in_the_7th():
    grahas = (KNOW / "grahas.md").read_text(encoding="utf-8")
    houses = (KNOW / "houses.md").read_text(encoding="utf-8")
    assert "Saturn west (7th)" in _plain(grahas)
    assert "Saturn in 7th (Digbala)" in _plain(houses)
    assert "Saturn in 10th (Digbala)" not in _plain(houses)
    assert _wrong_saturn_claims(houses) == []
    assert _wrong_saturn_claims(grahas) == []


def test_houses_tenth_house_note_says_it_is_not_saturns_digbala():
    houses = _plain((KNOW / "houses.md").read_text(encoding="utf-8"))
    assert "This is NOT Saturn's Digbala" in houses


def test_rahu_and_ketu_exaltation_rows_agree_across_grahas_and_rashis():
    g = (KNOW / "grahas.md").read_text(encoding="utf-8")
    r = (KNOW / "rashis.md").read_text(encoding="utf-8")
    # grahas: | Planet | Own | Exalted | Debilitated | Moolatrikona |   rashis: | Planet | Exalted | Debilitated |
    for planet in ("Rahu", "Ketu"):
        gc = [c.strip() for c in _row(g, planet).strip("|").split("|")]
        rc = [c.strip() for c in _row(r, planet).strip("|").split("|")]
        assert gc[2:4] == rc[1:3], (planet, gc, rc)
    rahu = _row(r, "Rahu")
    assert rahu.index("Gemini") < rahu.index("Sagittarius")
    assert "CONTESTED" in _row(r, "Rahu") and "CONTESTED" in _row(g, "Rahu")
    assert "CONTESTED" in _row(r, "Ketu") and "CONTESTED" in _row(g, "Ketu")


def test_grahas_records_the_rahu_and_ketu_disagreement_without_an_uncheckable_quotation():
    # chief's ruling on PR #1132 (2026-11-17): the CONTESTED note asserts Rao's Table 6 and says other
    # reckonings differ, but carries no direct quotation, degree or 180-degree claim attributed to a book
    # an independent QA round cannot open (Raman's Astrology for Beginners PDF is absent from the runner).
    g = _plain((KNOW / "grahas.md").read_text(encoding="utf-8"))
    assert "Rahu/Ketu dignity is CONTESTED between reckonings" in g
    assert "Rao's Table 6" in g and "states no alternative" in g
    assert "Taurus and Ketu's in Scorpio" in g  # the disagreement is still recorded
    assert "Taurus 20" not in g and "Scorpio 20" not in g  # no unverifiable degree quotation
    assert "180° opposite" not in g
    assert "not a sourced one" not in g  # the false 'no held book gives Taurus' claim stays retired


# ---- no page repeats the losing side ------------------------------------------------------------


def test_no_learn_template_ties_saturn_digbala_to_the_10th():
    bad = {}
    for p in sorted(LEARN.glob("*.html")):
        hits = _wrong_saturn_claims(p.read_text(encoding="utf-8"))
        if hits:
            bad[p.name] = hits[0][:160]
    assert bad == {}


def test_no_registry_field_ties_saturn_digbala_to_the_10th():
    assert _wrong_saturn_claims(_registry_text()) == []


def test_saturn_pages_state_that_the_digbala_is_in_the_7th(client):
    for slug in SATURN_PAGES:
        r = client.get(f"/learn/{slug}/")
        assert r.status_code == 200, slug
        t = _plain(r.text)
        assert re.search(r"digbala[^.]{0,80}7th house|7th house[^.]{0,80}digbala", t, re.I), slug


def test_saturn_10th_registry_entry_states_the_digbala_is_in_the_7th():
    from astro_ai.learn_registry import ARTICLES

    a = next(x for x in ARTICLES if x.slug == "saturn-in-10th-house-career")
    for field in (a.summary, a.llm_summary):
        assert "7th" in field and "digbala" in field.lower(), field[:120]
    assert any("7th" in f["a"] and "digbala" in f["a"].lower() for f in a.faqs)


def test_rahu_pages_lead_with_gemini_and_say_the_texts_disagree(client):
    t = _plain(client.get("/learn/the-9-grahas-overview/").text)
    assert "Exalted in: Gemini (some say Taurus)" in t
    assert "Debilitated in: Sagittarius (some say Scorpio)" in t
    assert "Exalted in: Taurus (some say Gemini)" not in t
    k = _plain(client.get("/learn/kaal-sarp-dosh/").text)
    assert "or Taurus on some reckonings" not in k
    assert "though some texts say Taurus" in k


# a flat 'Rahu is exalted in Taurus' (or Ketu in Scorpio/Taurus-reckoned) with no hedge in the same sentence
_FLAT_RAHU_TAURUS = re.compile(r"rahu[^.]{0,60}exalt[^.]{0,60}taurus|exalt[^.]{0,60}taurus[^.]{0,60}rahu", re.I)
_HEDGE = re.compile(r"some|contested|disagree|dispute|reckoning", re.I)


def _flat_rahu_taurus(text: str) -> list[str]:
    return [s for s in _sentences(text) if _FLAT_RAHU_TAURUS.search(s) and not _HEDGE.search(s)]


def test_no_page_or_registry_field_states_rahu_exalted_in_taurus_unhedged():
    bad = {p.name: _flat_rahu_taurus(p.read_text(encoding="utf-8")) for p in sorted(LEARN.glob("*.html"))}
    assert {k: v for k, v in bad.items() if v} == {}
    assert _flat_rahu_taurus(_registry_text()) == []


def test_no_learn_template_leads_rahu_exaltation_with_taurus():
    leading_taurus = re.compile(r"exalted in:?\s*(</strong>)?\s*Taurus \(some say Gemini\)", re.I)
    for p in sorted(LEARN.glob("*.html")):
        assert not leading_taurus.search(p.read_text(encoding="utf-8")), p.name
