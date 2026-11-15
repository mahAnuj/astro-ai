"""#1006: learn surfaces stop stating an unsourced kendra-based Neechabhanga rule as fact.

`knowledge/` holds exactly one cancellation condition: a planet debilitated in D-1 but exalted in D-9
(divisional_charts.md), plus 'Neechabhanga rules exist, see BPHS' (rashis.md). It holds no kendra rule and no
'lord of the debilitation sign is well-placed' rule. /learn/debilitated-sun-career listed three kendra conditions as
'the four most commonly cited', /learn/sun-in-10th-house-career repeated them and said 'many Capricorn ascendants'
have them active, and /learn/guru-jupiter-in-vedic-astrology said Saturn 'if well-placed' triggers the yoga; the
registry FAQs and LLM summaries carried the same text. #1004 did this for the Jupiter-in-10th page.

Every test reads the real rendered route or the registry entry the route renders. The scan is generic (any kendra
within a window of 'neecha', any 'lord of the debilitation sign' phrasing), so a re-introduction in different words
on these pages is still caught; the positive tests keep the sourced D-9 rule from being deleted by the fix.
"""
from __future__ import annotations

import re

SUN = "debilitated-sun-career"
SUN10 = "sun-in-10th-house-career"
GURU = "guru-jupiter-in-vedic-astrology"
SLUGS = (SUN, SUN10, GURU)

_NEECHA_KENDRA = re.compile(r"neecha.{0,250}kendra|kendra.{0,250}neecha", re.I | re.S)
_UNSOURCED_RULES = re.compile(
    r"lord of the (debilitation|exaltation) sign|if well-placed|is well-placed,? Neechabhanga"
    r"|Saturn[^.]{0,40}exalted in Libra|Venus[^.]{0,30}lord of Libra|many Capricorn ascendants|prime ministers",
    re.I,
)


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


def test_no_page_states_a_kendra_neechabhanga_condition(client):
    for slug in SLUGS:
        t = _text(client, slug)
        assert not _NEECHA_KENDRA.search(t), f"{slug}: {_NEECHA_KENDRA.search(t).group(0)[:200]}"
        assert not _UNSOURCED_RULES.search(t), f"{slug}: {_UNSOURCED_RULES.search(t).group(0)}"


def test_no_registry_entry_states_a_kendra_neechabhanga_condition():
    for slug in SLUGS:
        for field in _registry_fields(slug):
            assert not _NEECHA_KENDRA.search(field), f"{slug}: {field[:160]}"
            assert not _UNSOURCED_RULES.search(field), f"{slug}: {field[:160]}"


def test_sun_career_guide_keeps_the_navamsha_rule_and_says_the_rest_is_for_a_chart_reading(client):
    t = _text(client, SUN)
    assert "The one Neecha Bhanga condition we can state from the classical sources we hold is the navamsha test" in t
    assert "A planet debilitated in the D-1 but exalted in the D-9 gets Neechabhanga" in t
    assert "The fuller set of cancellation conditions is a matter for a chart reading, not a checklist we can give here" in t
    assert "The four most commonly cited" not in t and "four conditions" not in t
    assert "three kendra rules" not in t
    # The Kundli call to action must still point at something the chart does show: the D-9 chart.
    assert "draws the navamsha (D-9) chart" in t
    # exactly one numbered condition remains in the Neecha Bhanga list
    raw = client.get(f"/learn/{SUN}/").text
    section = raw[raw.index("Neecha Bhanga — the cancellation rules people miss"):]
    ol = section[section.index("<ol>"):section.index("</ol>")]
    assert ol.count("<li>") == 1 and "D-9" in ol


def test_sun_in_10th_guide_keeps_the_navamsha_rule(client):
    t = _text(client, SUN10)
    assert "a Sun debilitated in D-1 but exalted in the D-9 chart has the debilitation cancelled, so check D-9" in t
    assert "The fuller set of cancellation conditions is a matter for a chart reading" in t
    assert "Do not read this as a fixed sentence" in t
    assert "check the navamsha (D-9) test for Neecha Bhanga" in t


def test_guru_guide_keeps_only_the_navamsha_rule(client):
    t = _text(client, GURU)
    assert "a planet debilitated in the D-1 chart but exalted in the D-9 has the debilitation cancelled" in t
    assert "check whether Jupiter is exalted in the D-9 chart" in t
    assert "not a checklist we can give here" in t


def test_registry_faqs_agree_with_the_pages():
    sun = " ".join(_registry_fields(SUN))
    assert "the navamsha test: a planet debilitated in the D-1 chart but exalted in the D-9 has its debilitation cancelled" in sun
    assert "for Sun in Libra, check whether the Sun is exalted in the navamsha (D-9) chart" in sun
    assert "a matter for a chart reading, not a checklist we can give here" in sun
    assert "four most commonly cited" not in sun
    assert "chief justice" not in sun.lower() and "chief-justice" not in sun.lower()
    assert "exalted in the D-9" in " ".join(_registry_fields(GURU))
    s10 = " ".join(_registry_fields(SUN10))
    assert "check whether the Sun is exalted in the D-9 navamsha chart" in s10
    assert "chief justice" not in s10.lower()


def test_registry_faq_text_is_what_the_page_renders_in_its_json_ld(client):
    """The FAQ JSON-LD must carry the corrected answer, not a stale copy."""
    raw = client.get(f"/learn/{SUN}/").text
    assert "the navamsha test: a planet debilitated in the D-1 chart but exalted in the D-9" in raw
    assert "Venus (the lord of Libra)" not in raw
