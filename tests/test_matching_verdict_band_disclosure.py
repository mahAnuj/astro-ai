"""The /matching verdict bands are disclosed as Bhagya's own reading (#177).

`matching.py:_overall_verdict` maps the 36-point total to Uttam (>=30), Madhyam
(>=24), Avara (>=18) and "Not recommended". The 36-point engine is sourced; the
four bands are not — "uttam", "madhyam" and "avara" are absent from the corpus
and Muhurta Chintamani states no minimum-guna rule (astro-auditor, 2026-10-17).
The result page nonetheless showed "Good compatibility (Madhyam)" and a legend
`0 · 18 Avara · 24 Madhyam · 30 Uttam · 36` as if they were doctrine.

The fix is DISCLOSURE ONLY, same shape as the Manglik ladder (#429, #579, #626).
Two things are pinned, and kept apart on purpose:

  * the rendered page says the bands are not a classical grading, in English and
    in Hindi, next to the legend (so a template that stops printing the key, or a
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
_EN_MARK = "not a classical grading"
_HI_MARK = "कोई शास्त्रीय श्रेणी नहीं"


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
