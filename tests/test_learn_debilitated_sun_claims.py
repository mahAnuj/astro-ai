"""#1080: /learn/debilitated-sun-career stops calling the Sun in the 10th "the most classically difficult placement"
and stops attributing unsourced remedies to the classical tradition.

knowledge/grahas.md L244-252 and houses.md L299-300 give the Sun its digbala (directional strength) in the 10th house,
so the page cannot call that house the worst one for the Sun; no source we hold says which of debilitation and digbala
prevails, so the page states the two pulls and claims no outcome. Of the remedy list only wheat, the temple good deed,
the 6,000 bija count, honouring the father (Sun karaka) and the Aditya Hridayam as a stotra to learn from a teacher
(remedies.md L183, L200, L261, L280, L289-291) are sourced; arghya, jaggery/red cloth/copper, the Rama/Ravana story, the
12/108 count and a Sunday fast are common practice. 'Many senior judges carry this placement' had no data behind it.

Every test reads the rendered route or the registry entry the route renders (summary, every FAQ, llm_summary), so the
JSON-LD FAQ and the page cannot disagree. The positive tests keep the sourced sentences from being deleted by the fix.
"""
from __future__ import annotations

import re

SLUG = "debilitated-sun-career"

# each phrase was in the page or the registry before the fix; none is sourced in knowledge/
BANNED = (
    "most classically difficult",
    "classical daily practice",
    "safest single remedy",
    "classical Vedic tradition prescribes",
    "Safe universal classical practices",
    "Rama received",
    "Ravana",
    "Sun temples",
    "classically recommended",
    "classically strengthening",
    "classically produces",
    "Many senior judges",
    "Both amplify the debilitated pattern",
    "Classical remedies for debilitated Sun",
    "classical remedies that genuinely help",
    "honest classical remedies",
)
# a 'classical'/'classically' in the same sentence as an unsourced remedy word, in any phrasing
_CLASSICAL_REMEDY = re.compile(
    r"classical(ly)?[^.]{0,120}\b(arghya|jaggery|red cloth|copper|fast\b|safest)"
    r"|\b(arghya|jaggery|red cloth|copper|fast\b|safest)[^.]{0,120}classical(ly)?(?! remedies tables)",
    re.I,
)


def _plain(s: str) -> str:
    # tags dropped, not spaced: the page wraps 'Common practice' in <em>, and a space would split the phrase
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s))


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return _plain(r.text)


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _registry_fields() -> list[str]:
    a = _article()
    return [a.summary, a.seo_description, a.llm_summary] + [f["q"] + " " + f["a"] for f in a.faqs]


def _faq(q_start: str) -> str:
    return next(f["a"] for f in _article().faqs if f["q"].startswith(q_start))


def test_page_carries_none_of_the_unsourced_classical_attributions(client):
    t = _text(client)
    for phrase in BANNED:
        assert phrase not in t, phrase
    m = _CLASSICAL_REMEDY.search(t)
    assert not m, m.group(0)


def test_registry_entry_carries_none_of_the_unsourced_classical_attributions():
    for field in _registry_fields():
        for phrase in BANNED:
            assert phrase not in field, f"{phrase!r} in {field[:120]}"
        m = _CLASSICAL_REMEDY.search(field)
        assert not m, f"{m.group(0)} in {field[:120]}"


def test_tenth_house_states_the_two_opposing_pulls_and_claims_no_outcome(client):
    t = _text(client)
    assert "Debilitation in Libra weakens the Sun, while the 10th is the house where the Sun gains directional strength (digbala)" in t
    assert "They do not say which of the two prevails, so this page does not claim an outcome" in t
    # the placement's internal link survives the rewrite
    assert 'href="/learn/career-not-progressing/"' in client.get(f"/learn/{SLUG}/").text
    ten = t[t.index("Debilitated Sun in the 10th house"):]
    ten = ten[: ten.index("Debilitated Sun in the 11th house")]
    # the page's own advice is labelled as such, not as classical
    assert "Our own reading, not a classical rule" in ten


def test_llm_summary_states_digbala_and_the_sourced_versus_practice_split():
    s = _article().llm_summary
    assert "digbala" in s and "do not say which prevails" in s
    assert "Common practice, not in the sources" in s


def test_remedy_list_splits_sourced_items_from_common_practice(client):
    t = _text(client)
    assert "Items marked sourced appear in the classical remedies tables we hold" in t
    assert "We do not present the second kind as classical" in t
    # sourced items stay, and say they are sourced
    assert "Sourced: wheat, donated particularly on the Sun's weekday" in t
    assert "a count of 6,000 repetitions total" in t
    assert "Sourced in part: the sources we hold name the Aditya Hridayam as a Sun stotra" in t
    # unsourced items stay but are labelled
    assert "Common practice, not in the classical sources we hold" in t
    assert "Jaggery, red cloth and copper vessels are common practice" in t
    # the fast: remedies.md 5.2 gives the rajyapada-lord weekday, not a Sunday fast for a weak Sun
    assert "the sources we hold do not prescribe a Sunday fast for a weak Sun" in t
    assert "weekday ruled by the rajyapada lord (the 10th house pattern)" in t
    # the ruby caution is a sourced sentence the edit must not touch
    assert "gemstone remedies — particularly ruby" in t


def test_faq_how_to_strengthen_carries_the_same_split_as_the_page():
    a = _faq("How to strengthen")
    assert a.startswith("Sourced in the classical remedies tables we hold")
    assert "Common practice, not in those sources: offer arghya" in a
    assert "for which the tables give a count of 6,000 repetitions" in a
    assert "rajyapada lord (the 10th house pattern)" in a
    assert "Never wear a ruby" in a


def test_government_faq_and_judiciary_bullet_assert_no_unmeasured_prevalence(client):
    assert "carry this placement" not in _faq("Does Sun in Libra mean no government job")
    assert "civil servants carry this placement" not in _text(client)
    assert "Judges rule by weighing arguments, not by force." in _text(client)  # the page's reasoning stays


def test_sourced_sentences_survive_the_fix(client):
    t = _text(client)
    assert "most deeply at 10° Libra, and exalted in Aries (Mesha) at 10°" in t
    assert "exalted in the navamsha (D-9) chart" in t
    assert "Sun Mahadasha (6 years)" in t
    assert "For a functional malefic Sun, a ruby can amplify difficulty" in t


def test_json_ld_faq_carries_the_corrected_answers(client):
    raw = client.get(f"/learn/{SLUG}/").text
    assert "Sourced in the classical remedies tables we hold" in raw
    assert "Safe universal classical practices" not in raw
    assert "Many senior judges" not in raw
