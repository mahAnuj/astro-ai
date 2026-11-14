"""#1014: the Jupiter-in-10th guide stops outrunning (or contradicting) the held sources.

Held, in `knowledge/`: Hamsa Yoga = Jupiter in Sg/Pi/Cn in a kendra, effects "wisdom, respect, dharma, scholarly
fame" (vedic_reference.md section 4.1, yogas.md); Guru Chandala is a real, named classical yoga and is not rated
difficult (vedic_reference.md); retrograde planets are read as STRONGER, a retrograde benefic as an excess of its
positive themes, e.g. retrograde Jupiter -> deep learning, expansion of meaning (grahas.md section 13). The page said
Hamsa natives are 'long-lived' and 'dignified in appearance' in 'unusually consistent' texts, called Guru Chandala
'classically difficult', and listed retrograde Jupiter with the weak and difficult ones while its own retrograde
paragraph said 'not weaker'. The registry FAQs repeated three of those claims.

Every test reads the real rendered route or the registry entry the route renders. The retrograde scan is generic (any
sentence naming retrograde together with a weak/difficult word), so the same claim in other words is still caught; the
positive tests keep the sourced rules from being deleted by the fix.
"""
from __future__ import annotations

import re

SLUG = "jupiter-in-10th-house-career"

# phrases the held sources do not support; matched case-insensitively on tag-stripped text
UNSOURCED = (
    "long-lived",
    "classically difficult",
    "unusually consistent",
    "dignified in appearance",
    "neither straightforwardly beneficial nor harmful",
    "one of the great scholarly and dharmic",
    "different classical outcomes",
    "classical outcomes tend to arrive",
    "classically produce the outcomes",
    # #1016: residue after #1014
    "fullest classical",
    "classical hamsa yoga native",
    "scandal-prone",
    "hamsa yoga at maximum power",
    "full hamsa yoga",
)

_WEAK_WORD = re.compile(r"\b(weak|weaker|weakened|difficult|afflicted|compromised|malefic)\b", re.I)


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return _plain(r.text)


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _registry_fields() -> list[str]:
    a = _article()
    return [a.summary, a.llm_summary, a.seo_description] + [f["q"] + " " + f["a"] for f in a.faqs]


def _retrograde_as_weak(text: str) -> list[str]:
    """Sentences that name retrograde and a weak/difficult word. 'not weaker' is the held rule, so it is removed."""
    out = []
    for sentence in re.split(r"(?<=[.!?;:])\s+", text):
        if not re.search(r"retrograde", sentence, re.I):
            continue
        if _WEAK_WORD.search(re.sub(r"\bnot weaker\b", "", sentence, flags=re.I)):
            out.append(sentence[:200])
    return out


def _violations(text: str) -> list[str]:
    low = text.lower()
    return [p for p in UNSOURCED if p in low] + _retrograde_as_weak(text)


def test_page_states_none_of_the_unsourced_claims(client):
    bad = _violations(_text(client))
    assert not bad, bad


def test_registry_entry_states_none_of_the_unsourced_claims():
    for field in _registry_fields():
        bad = _violations(_plain(field))
        assert not bad, f"{bad} in {field[:120]}"


def test_retrograde_scan_catches_the_listings_it_exists_for():
    # the scan must be red on the two original shapes, or it is a test that passes forever
    assert _retrograde_as_weak("A weak, retrograde, combust, or malefic-conjunct Jupiter struggles.")
    assert _retrograde_as_weak("reading a difficult Jupiter (debilitated, combust, retrograde, or with Rahu) as failure.")
    assert not _retrograde_as_weak("Retrograde planets are stronger, not weaker, in Vedic astrology.")


def test_page_keeps_the_sourced_rules(client):
    t = _text(client)
    # Hamsa: the rule and the held effects
    assert "Sagittarius, Pisces, or Cancer" in t and "kendra" in t
    assert "wisdom, respect, dharma, and scholarly fame" in t
    assert "ether" in t
    # Guru Chandala stays, as a named classical yoga
    assert "Guru Chandala" in t and "real, named classical yoga" in t
    # grahas.md section 13: retrograde is stronger, retrograde Jupiter -> deep learning, expansion of meaning
    assert "retrograde planets as stronger, not weaker" in t
    assert "deep learning and an expansion of meaning" in t
    # the Libra-ascendant line names what is held instead of a classical verdict
    assert "This forms Hamsa Yoga, which the sources we hold list with wisdom, respect, dharma, and scholarly fame" in t


def test_registry_keeps_the_sourced_rules():
    joined = _plain(" ".join(_registry_fields()))
    assert "Hamsa Yoga" in joined and "Panch Mahapurush" in joined
    assert "kendra" in joined
    assert "wisdom, respect, dharma, and scholarly fame" in joined
    assert "retrograde planets as stronger, not weaker" in joined
    assert "Guru Chandala" in joined


def test_registry_faq_text_is_what_the_page_renders_in_its_json_ld(client):
    """The FAQ JSON-LD must carry the corrected answers, not a stale copy."""
    raw = client.get(f"/learn/{SLUG}/").text
    assert "long-lived" not in raw
    assert "stronger, not weaker" in raw


def test_registry_llm_summary_reaching_the_natal_prompt_names_guru_chandala_without_scandal():
    """chart.py injects llm_summary into the natal prompt, so 'scandal-prone' there is a claim made to every reading."""
    summary = _article().llm_summary
    assert "Guru Chandala" in summary
    assert "scandal-prone" not in summary.lower()


def test_page_labels_the_hamsa_career_roles_as_a_reading_not_a_rule(client):
    t = _text(client)
    assert "practitioner's reading of those themes, not a rule the texts state" in t
    assert t.count("This forms Hamsa Yoga, which the sources we hold list") == 1
    assert "Hamsa Yoga formed at full strength" not in t
