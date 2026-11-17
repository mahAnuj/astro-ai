"""#1072: /learn/vimshottari-dasha-explained/ answers "which mahadasha is best for career" in the question's
own words, with the sourced rule and no ranking.

`knowledge/vedic_reference.md` 5.2 holds the three-factor rule (lord's natal strength, houses it rules, house it
occupies) and 5.4 holds the per-dasha reading patterns. It holds no ranking of the nine dashas for career, so the
section says none is best for everyone and labels the Sun/Mercury/Saturn/Rahu patterns as practitioner reading.
The route renders the template and the registry FAQ (the FAQ lands in JSON-LD); `llm_summary` feeds the natal
prompt and must not change.
"""
from __future__ import annotations

import re

SLUG = "vimshottari-dasha-explained"
Q = "which mahadasha is best for career"


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text)).lower()


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _section(client) -> str:
    t = _text(client)
    start = t.index(Q)
    return t[start:start + 2200]


def test_page_asks_the_question_in_a_heading_and_in_the_faq(client):
    r = client.get(f"/learn/{SLUG}/")
    heads = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", r.text, flags=re.S | re.I)
    assert any(Q in re.sub(r"<[^>]+>", "", h).lower() for h in heads)
    assert any(f["q"].lower().rstrip("?") == Q for f in _article().faqs)


def test_answer_is_no_single_best_and_cites_the_three_factors(client):
    sec = _section(client)
    assert "no mahadasha is the best career period for everyone" in sec
    for factor in ("how strong the dasha lord is by birth", "which houses it rules", "which house it sits in"):
        assert factor in sec
    faq = next(f for f in _article().faqs if f["q"].lower().rstrip("?") == Q)["a"].lower()
    assert "none is best for everyone" in faq


def test_career_patterns_are_labelled_practice_and_nine_dashas_are_not_ranked(client):
    sec = _section(client)
    assert "reading habits and not guarantees" in sec
    assert "we do not rank the nine dashas for career" in sec
    assert "classical" not in sec


def test_section_links_to_the_dasha_tool(client):
    r = client.get(f"/learn/{SLUG}/")
    sec = r.text[r.text.lower().index(Q):]
    assert 'href="/dasha"' in sec[:3500]


def test_llm_summary_is_unchanged():
    # The natal prompt injects llm_summary for every chart; editing it changes runtime tokens (#1072 AC4).
    s = _article().llm_summary
    assert s.count("\n") == 5 and "Timing is probabilistic" in s
    assert "career" not in s.lower()
