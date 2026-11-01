"""The /matching verdict bands are disclosed as Bhagya's own reading (#177).

`matching.py:_overall_verdict` maps the 36-point total to Uttam (>=30), Madhyam
(>=24), Avara (>=18) and "Not recommended". The 36-point engine is sourced; the
four bands are not — "uttam", "madhyam" and "avara" are absent from the corpus
and Muhurta Chintamani states no minimum-guna rule (astro-auditor, 2026-10-17).
The result page nonetheless showed "Good compatibility (Madhyam)" and a legend
`0 · 18 Avara · 24 Madhyam · 30 Uttam · 36` as if they were doctrine.

The fix is DISCLOSURE ONLY, same shape as the Manglik ladder (#429, #579, #626).
Two things are pinned, and kept apart on purpose:

  * the rendered page says the bands are not drawn from the classical texts we hold
    (a term-search absence over the held corpus -- NOT a claim that no tradition has
    ever graded the total), in English and in Hindi, next to the legend (so a template that stops printing the key, or a
    key that loses a language, goes red);
  * the grades themselves did not move — a provenance edit must not change a
    verdict. The owner decides the bands.

Driven through the real POST /matching route and template. `compute_guna_milan`
is wrapped so the total can be set exactly; everything downstream of it (verdict
mapping, palette, template) is the real code. The LLM provider is stubbed (#449).
"""
from __future__ import annotations

import dataclasses

import pytest

# Total -> (overall_verdict, English label) exactly as shipped before this change.
_GRADES = [
    (17.5, "Not recommended", "Below recommended threshold"),
    (18.0, "Avara", "Acceptable with caveats (Avara)"),
    (23.5, "Avara", "Acceptable with caveats (Avara)"),
    (24.0, "Madhyam", "Good compatibility (Madhyam)"),
    (29.5, "Madhyam", "Good compatibility (Madhyam)"),
    (30.0, "Uttam", "Excellent compatibility (Uttam)"),
]
_EN_MARK = "not drawn from the classical texts we hold"
_HI_MARK = "शास्त्रीय ग्रंथों से नहीं लिए गए हैं"


def _post(client, stub_llm, monkeypatch, total, lang="en"):
    import astro_ai.routes.matching as route
    from astro_ai.matching import _overall_verdict

    real = route.compute_guna_milan

    def _with_total(groom, bride):
        g = real(groom, bride)
        verdict, label = _overall_verdict(total)
        return dataclasses.replace(
            g, total_awarded=total, overall_verdict=verdict, overall_verdict_label=label
        )

    monkeypatch.setattr(route, "compute_guna_milan", _with_total)
    stub_llm("## Compatibility\n" + "A canned narrative body for the stub. " * 20)
    r = client.post(f"/matching?lang={lang}", data={
        "g_name": "A", "g_birth_date": "1990-01-01", "g_birth_time": "10:00",
        "g_birth_place": "Mumbai",
        "b_name": "B", "b_birth_date": "1990-01-04", "b_birth_time": "10:00",
        "b_birth_place": "Mumbai",
    })
    assert r.status_code == 200, r.status_code
    return r.text


@pytest.mark.parametrize("lang,mark", [("en", _EN_MARK), ("hi", _HI_MARK)])
def test_result_page_discloses_the_bands_are_not_classical(
        client, stub_llm, monkeypatch, lang, mark):
    html = _post(client, stub_llm, monkeypatch, 26.0, lang)
    assert mark in html, f"{lang}: the band disclosure is not rendered"
    # It sits with the legend, not somewhere else on the page.
    legend = html.index("Madhyam</span>")
    assert 0 < html.index(mark) - legend < 600, "disclosure is not beside the scale legend"


@pytest.mark.parametrize("total,verdict,label", _GRADES)
def test_the_disclosure_moves_no_grade(client, stub_llm, monkeypatch, total, verdict, label):
    from astro_ai.matching import _overall_verdict

    assert _overall_verdict(total) == (verdict, label)
    html = _post(client, stub_llm, monkeypatch, total)
    assert label in html, f"{total}: rendered verdict is not {label!r}"
    assert _EN_MARK in html


def test_the_band_disclosure_credits_no_book():
    from astro_ai.i18n import translate as t

    for lang in ("en", "hi"):
        text = t(lang, "matching_bands_note")
        for book in ("Muhurta", "Muhurtha", "Chintamani", "Jataka", "Parashara"):
            assert book not in text, text


# --- the pages around it must not contradict the disclosure (#177, QA round 1) ---
#
# 28c70d5 disclosed the bands on the result page and left four other surfaces
# calling the same 18/24/30 cut-offs "classical": the /matching explainer, the
# learn article, marriage-delayed, and the registry FAQ that feeds JSON-LD. A
# sentence (or bullet) that names a cut-off or a band label must not also say
# "classical". The disclosure sentences carry no digits, so they stay legal. The
# eight koota weights and the 36 total ARE sourced and may still be called
# classical -- those sentences name no cut-off.
import re

_CUTOFF = re.compile(
    r"(?<![\d.])(?:18|24|30)(?:\s*/\s*36|\+\s+(?:is|=|acceptable|good|excellent|gunas?|points?)"
    r"|\s+to\s+\d\d|\s+gunas?\b)"
    r"|\b(?:above|below|under|over)\s+(?:18|24|30)\b"
    r"|\bUttam\b|\bMadhyam\b|\bAvara\b"
    r"|\b(?:18|24|30)\b[^.]{0,40}\b(?:acceptable|good|excellent|strong)\b",
    re.I,
)
_CLASSICAL = re.compile(r"classical|classically|शास्त्रीय|शास्त्रों", re.I)
_BLOCK_END = re.compile(r"</li>|</p>|</div>|<br\s*/?>|\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _offending(html: str) -> list[str]:
    html = re.sub(r"(?s)<(script|style)\b.*?</\1>|\{#.*?#\}|<!--.*?-->", " ", html)
    bad = []
    for chunk in _BLOCK_END.split(html):
        # A bullet is one claim even with two sentences ("Uttam (...). Classical texts
        # consider this an ideal match."); prose is judged one sentence at a time.
        parts = [chunk] if "<li" in chunk else _SENTENCE_END.split(re.sub(r"<[^>]+>", " ", chunk))
        for part in parts:
            text = re.sub(r"<[^>]+>", " ", part)
            text = re.sub(r"&mdash;|&middot;|&nbsp;", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if _CUTOFF.search(text) and _CLASSICAL.search(text):
                bad.append(text[:200])
    return bad


def test_checker_catches_the_old_wording():
    # The guard must be able to go red: the exact sentences 28c70d5 left behind.
    for old in (
        'A minimum threshold of <strong>18/36</strong> is the classical "acceptable" line.',
        "<li><strong>30 to 36 - Uttam</strong> (Excellent). Classical texts consider this an ideal match.</li>",
        "<li><strong>Below 18</strong> - Classical rule: not recommended.</li>",
        "<li>A score above 18/36 is classically considered acceptable for marriage.</li>",
        "The classical guidance: 18+ acceptable (Avara), 24+ good (Madhyam), 30+ excellent (Uttam).",
    ):
        assert _offending(old), f"checker is blind to: {old}"
    # ...and must leave koota-weight and age sentences alone.
    assert not _offending("Nadi (8) and Bhakoot (7) are classical Vedic practice, 15 of the 36 points.")
    assert not _offending("Classical astrology suggests marriage comes later, often 30+.")


@pytest.mark.parametrize("path", ["/matching", "/learn/kundali-matching-ashtakoot-guna-milan",
                                  "/learn/marriage-delayed"])
def test_no_page_calls_the_cutoffs_classical(client, path):
    r = client.get(path)
    assert r.status_code == 200, (path, r.status_code)
    assert "18" in r.text
    assert not _offending(r.text), (path, _offending(r.text))


def test_registry_faq_and_summary_do_not_call_the_cutoffs_classical():
    from astro_ai.learn_registry import ARTICLES

    art = next(a for a in ARTICLES if a.slug == "kundali-matching-ashtakoot-guna-milan")
    strings = [f["a"] for f in art.faqs] + [art.llm_summary, art.summary, art.seo_description]
    seen_cutoff = False
    for s in strings:
        seen_cutoff = seen_cutoff or bool(_CUTOFF.search(s))
        assert not _offending(s), _offending(s)
    assert seen_cutoff, "registry no longer states the cut-offs; the guard is vacuous"
