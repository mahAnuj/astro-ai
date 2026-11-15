"""#1051: residue of #1049 -- the Jupiter-in-10th guide's registry text and one page bullet still stated outcome claims flat.

Held, in `knowledge/vedic_reference.md` section 4.1: only the Hamsa / Pancha Mahapurusha rule and its effects (wisdom,
respect, dharma, scholarly fame). Nothing held states that a debilitated, combust or Rahu-conjunct Jupiter 'stalls' a
career or 'diminishes' the placement's benefits, or that Guru Chandala charts are 'reputation-fragile'. data/ was absent
when this was written, so no absence is asserted; the claim is only that these must not be presented as rules.

The registry fields (`summary`, FAQ answers, `llm_summary`) are the surface #1049 missed: `llm_summary` is injected into
every natal prompt, so a flat claim there is made to every reading. Own file so it cannot conflict with the #1045 /
#1049 suites.
"""
from __future__ import annotations

import re

SLUG = "jupiter-in-10th-house-career"

# the flat wording #1051 removed; matched case-insensitively on tag-stripped text
FLAT_PHRASES = (
    "institutional recognition stalls",
    "diminish significantly",
    "spectacular but reputation-fragile",
    "produce guru-figures",
    "the karma-dharma path stalls",
    "the karma-dharma path becomes more difficult",
    # QA round 1 on #1054: the page intro and the opening of the 'depends on dignity' section said the same thing flat
    "the karma path stalls",
    "moralistic advice-giving without institutional traction",
    "often struggles to convert that respect",
    "produces a person who is respected for wisdom",
)

LABEL = "not a rule the texts state"


def _plain(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _registry_fields() -> dict[str, str]:
    a = _article()
    out = {"summary": a.summary, "llm_summary": a.llm_summary}
    for f in a.faqs:
        out["faq: " + f["q"]] = f["a"]
    return out


def _page(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return r.text


def _sentences_with(text: str, needle: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if needle in s.lower()]


def test_registry_fields_state_none_of_the_flat_claims():
    for name, field in _registry_fields().items():
        low = _plain(field).lower()
        for phrase in FLAT_PHRASES:
            assert phrase not in low, f"{phrase!r} in {name}"


def test_page_and_its_faq_json_ld_state_none_of_the_flat_claims(client):
    low = _plain(_page(client)).lower()
    for phrase in FLAT_PHRASES:
        assert phrase not in low, phrase


def test_faq_benefits_reduced_sentence_is_labelled():
    ans = _plain(_registry_fields()["faq: Is Jupiter in the 10th house always good?"])
    hits = _sentences_with(ans, "benefits as reduced")
    assert len(hits) == 1, hits
    assert "practitioners read" in hits[0].lower()
    assert LABEL in ans.lower()


def test_summary_and_llm_summary_label_the_debilitated_outcome():
    fields = _registry_fields()
    assert "practitioners read a debilitated or afflicted jupiter" in _plain(fields["summary"]).lower()
    assert LABEL in _plain(fields["summary"]).lower()
    line = next(l for l in fields["llm_summary"].split("\n") if l.startswith("• Debilitated in Capricorn"))
    low = line.lower()
    assert "practitioners read" in low and "not a held rule" in low, line


def test_guru_chandala_bullet_is_labelled_practitioner_reading(client):
    html = _page(client)
    items = [_plain(m).strip() for m in re.findall(r"<li>(.*?)</li>", html, re.S)]
    matching = [i for i in items if i.startswith("Jupiter with Rahu")]
    assert len(matching) == 1, matching
    low = matching[0].lower()
    assert "practitioners read these careers" in low, matching[0][:160]
    assert LABEL in low, matching[0][-160:]
    # the named classical yoga stays stated as held, and is still not called difficult or scandal-prone
    assert "real, named classical yoga" in low
    assert "scandal" not in low


def test_every_page_sentence_naming_a_stall_or_struggle_is_labelled(client):
    """Catches a reworded flat claim: any rendered sentence about the weak/afflicted outcome carries the label.

    A sentence is 'about the outcome' if it says stall/struggle/harder/slower together with Jupiter's weakness words.
    The label may sit in the same sentence or in the one right after it ("...; that is a reading, ...").
    """
    text = _plain(_page(client))
    sents = re.split(r"(?<=[.!?])\s+", text)
    outcome = re.compile(r"\b(stalls?|struggles?|harder|slower|slow to)\b", re.I)
    weak = re.compile(r"\b(debilitated|afflicted|weak|combust|malefic-conjunct)\b", re.I)
    unlabelled = []
    for i, s in enumerate(sents):
        if outcome.search(s) and weak.search(s):
            window = (s + " " + (sents[i + 1] if i + 1 < len(sents) else "")).lower()
            if LABEL not in window and "practitioner" not in s.lower():
                unlabelled.append(s[:160])
    assert not unlabelled, unlabelled
