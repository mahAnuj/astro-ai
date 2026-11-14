"""#1010: learn surfaces stop stating an unsourced 'well-placed lord' Neechabhanga rule as fact.

`knowledge/` holds exactly one cancellation condition: a planet debilitated in D-1 but exalted in D-9
(divisional_charts.md), plus 'Neechabhanga rules exist, see BPHS' (rashis.md). It holds no rule that the lord of
the debilitation sign being 'well-placed' or 'strong' cancels a debilitation, and it does not name a
'Neechabhanga Raja Yoga'. Eight learn pages (and the registry FAQs behind four of them) said the lord's strength
forms that yoga and 'flips the debilitation into strength', and one added 'many highly successful people'. #1006
did this for the kendra conditions and the Guru, Sun-career and Sun-in-10th pages; this is the remainder.

Every test reads the real rendered route or the registry entry the route renders. The scans are generic (a
'well-placed'/'strong' within the same sentence as 'neecha', the 'Neechabhanga Raja Yoga' name), so a
re-introduction in different words on these pages is still caught; the positive tests keep the sourced D-9 rule
from being deleted by the fix.
"""
from __future__ import annotations

import re

PAGES = (
    "surya-sun-in-vedic-astrology",
    "shukra-venus-in-vedic-astrology",
    "budha-mercury-in-vedic-astrology",
    "mangal-mars-in-vedic-astrology",
    "venus-remedies",
    "mercury-remedies",
    "saturn-in-10th-house-career",
    "10th-lord-in-6th-house-career",
)
# the pages whose registry FAQ carried the same claim
REGISTRY_PAGES = (
    "surya-sun-in-vedic-astrology",
    "shukra-venus-in-vedic-astrology",
    "mangal-mars-in-vedic-astrology",
    "saturn-in-10th-house-career",
)
# which planet the D-9 sentence must name on each page
PLANET = {
    "surya-sun-in-vedic-astrology": "the Sun",
    "shukra-venus-in-vedic-astrology": "Venus",
    "budha-mercury-in-vedic-astrology": "Mercury",
    "mangal-mars-in-vedic-astrology": "Mars",
    "venus-remedies": "Venus",
    "mercury-remedies": "Mercury",
    "saturn-in-10th-house-career": "Saturn",
}

# 'well-placed' / 'strong' in the same sentence as 'neecha', either order ('[^.]' stops at the sentence end)
_LORD_STRENGTH = re.compile(
    r"neecha[^.]{0,250}(well[- ]placed|\bstrong\b)|(well[- ]placed|\bstrong\b)[^.]{0,250}neecha", re.I
)
_RAJA_YOGA_NAME = re.compile(r"neecha[ -]?bhanga\s+raja\s*yoga", re.I)
_OUTCOME_PROMISE = re.compile(r"highly successful (people|writers)|flips? (a|the) (weak|debilitat)", re.I)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def _text(client, slug: str) -> str:
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    return _plain(r.text)


def _article(slug: str):
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == slug)


def _registry_fields(slug: str) -> list[str]:
    a = _article(slug)
    return [a.summary, a.llm_summary, a.seo_description] + [f["q"] + " " + f["a"] for f in a.faqs]


def _violations(text: str) -> list[str]:
    return [m.group(0)[:200] for rx in (_LORD_STRENGTH, _RAJA_YOGA_NAME, _OUTCOME_PROMISE) for m in rx.finditer(text)]


def test_no_page_states_a_well_placed_lord_neechabhanga_condition(client):
    for slug in PAGES:
        bad = _violations(_text(client, slug))
        assert not bad, f"{slug}: {bad}"


def test_no_registry_entry_states_a_well_placed_lord_neechabhanga_condition():
    for slug in REGISTRY_PAGES:
        for field in _registry_fields(slug):
            bad = _violations(field)
            assert not bad, f"{slug}: {bad} in {field[:120]}"


def test_pages_that_keep_a_neechabhanga_sentence_still_state_the_navamsha_test(client):
    for slug, planet in PLANET.items():
        t = _text(client, slug)
        assert "debilitated in the D-1 chart but exalted in the D-9 has the debilitation cancelled" in t, slug
        assert f"check whether {planet} is exalted in the D-9" in t, slug
        assert "a matter for a chart reading" in t, slug


def test_tenth_lord_in_sixth_names_the_d9_test_and_drops_the_wrong_jupiter_example(client):
    t = _text(client, "10th-lord-in-6th-house-career")
    assert "a planet debilitated in the D-1 chart but exalted in the D-9 has the debilitation cancelled" in t
    assert "a matter for a chart reading" in t
    # 'Requires Neechabhanga ... to produce classical results' was an unsourced necessity claim
    assert "Requires Neechabhanga" not in t
    # rashis.md: Jupiter is debilitated in Capricorn, so 'Jupiter debilitated in Scorpio ... benefit from checking
    # Neechabhanga' named a planet that is not debilitated there
    assert "Jupiter debilitated in Scorpio in the 6th (Gemini ascendant) or Mars" not in t
    assert "Mars debilitated in Cancer in the 6th (Aquarius ascendant)" in t


def test_registry_faqs_keep_the_navamsha_test_and_agree_with_the_pages():
    expect = {
        "surya-sun-in-vedic-astrology": "check whether the Sun is exalted in the D-9",
        "shukra-venus-in-vedic-astrology": "check whether Venus is exalted in the D-9",
        "mangal-mars-in-vedic-astrology": "check whether Mars is exalted in the D-9",
        "saturn-in-10th-house-career": "check whether Saturn is exalted in the D-9 chart",
    }
    for slug, phrase in expect.items():
        joined = " ".join(_registry_fields(slug))
        assert phrase in joined, slug
        assert "a matter for a chart reading" in joined, slug


def test_registry_faq_text_is_what_the_page_renders_in_its_json_ld(client):
    """The FAQ JSON-LD must carry the corrected answer, not a stale copy."""
    for slug in REGISTRY_PAGES:
        raw = client.get(f"/learn/{slug}/").text
        assert "exalted in the D-9" in raw, slug
        assert "Neechabhanga Raja Yoga" not in raw, slug
