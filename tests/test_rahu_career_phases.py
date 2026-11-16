"""#1084: /learn/rahu-mahadasha-career-problems states phase lengths that add up to its own antardasha figures,
and no longer calls Rahu combust or Sagittarius an exaltation.

Antardasha length = Mahadasha years x antardasha planet years / 120 (knowledge/vedic_reference.md 5.1 holds the
nine durations). For Rahu (18): Rahu 2.70, Jupiter 2.40 | Saturn 2.85, Mercury 2.55, Ketu 1.05, Venus 3.00 |
Sun 0.90, Moon 1.50, Mars 1.05, i.e. 5.10 + 9.45 + 3.45 = 18. The page said 'the middle 8 years' and 'the final 5
years'. Rao (Lessons Vol. I, via knowledge/grahas.md) excludes Rahu/Ketu from combustion; grahas.md gives
Sagittarius as Rahu's debilitation and Gemini (some say Taurus) as exaltation.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
SLUG = "rahu-mahadasha-career-problems"
ORDER = ["Rahu", "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun", "Moon", "Mars"]


def _years() -> dict[str, int]:
    md = (ROOT / "knowledge" / "vedic_reference.md").read_text()
    sec = md[md.index("### 5.1 Sequence and durations"):md.index("### 5.2")]
    d = {k: int(v) for k, v in re.findall(r"(Ketu|Venus|Sun|Moon|Mars|Rahu|Jupiter|Saturn|Mercury)\s+(\d+)y", sec)}
    assert len(d) == 9
    return d


def _months(planets: list[str]) -> float:
    y = _years()
    return sum(y["Rahu"] * y[p] / 120 * 12 for p in planets)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def _page(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return _plain(r.text)


def _span(txt: str) -> float:
    m = re.fullmatch(r"(\d+) years?(?: (\d+) months?)?", txt.strip())
    assert m, txt
    return int(m.group(1)) * 12 + int(m.group(2) or 0)


def test_phase_headings_equal_the_sum_of_their_antardashas(client):
    t = _page(client)
    for planets, label in [
        (ORDER[2:6], "Phase 2: The middle"),
        (ORDER[6:], "Phase 3: The final"),
    ]:
        m = re.search(label + r" (\d+ years? \d+ months?) \(", t)
        assert m, f"heading for {label!r} not found"
        stated = _span(m.group(1))
        assert abs(stated - _months(planets)) <= 1.0, (label, stated, _months(planets))
    # the three phases cover the whole Mahadasha
    assert abs(_months(ORDER[:2]) + _months(ORDER[2:6]) + _months(ORDER[6:]) - 18 * 12) < 1e-9


def test_the_old_wrong_phase_lengths_are_gone(client):
    t = _page(client)
    assert "middle 8 years" not in t and "final 5 years" not in t


def test_rahu_is_never_called_combust_and_sagittarius_is_not_an_exaltation(client):
    from astro_ai.learn_registry import ARTICLES

    art = next(a for a in ARTICLES if a.slug == SLUG)
    blob = _page(client) + " " + " ".join(f["a"] for f in art.faqs) + " " + art.llm_summary
    for m in re.finditer(r"[^.]*\bcombust\b[^.]*\.", blob):
        s = m.group(0).lower()
        assert re.search(r"\b(not|never|no)\b", s), f"Rahu combust claim: {m.group(0)}"
    assert not re.search(r"Sagittarius as exaltation|exalted in Sagittarius", blob)
    assert "Sagittarius (some texts say Scorpio)" in blob


def test_unsourced_classical_attributions_are_labelled_as_practice(client):
    t = _page(client)
    assert "not a rule found in the classical texts" in t
    assert "not a classical rule" in t
    assert "the classical career-launch placement" not in t
    assert "upachaya" in t  # the 3/6/10/11 rule is houses.md's natal upachaya rule, not the Moon-counted Gochara table


def test_registry_has_no_unsourced_best_subperiods_and_no_blue_cloth():
    from astro_ai.learn_registry import ARTICLES

    art = next(a for a in ARTICLES if a.slug == SLUG)
    blob = art.llm_summary + " " + " ".join(f["a"] for f in art.faqs)
    assert "Best sub-periods for major decisions" not in blob
    assert "blue cloth" not in blob
    assert "3rd, 6th, 10th or 11th house — the upachaya houses where a malefic becomes useful with time" in blob
