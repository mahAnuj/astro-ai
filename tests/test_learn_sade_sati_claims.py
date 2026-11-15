"""#1081: /learn/sade-sati/ and its FAQ stop stating things the corpus does not hold.

The page shipped one wrong number and five unsourced attributions, all in hand-written prose:

* "first Sade Sati typically around ages 27-35" (and 56-64, 86-94). Sade Sati starts when Saturn
  reaches the 12th sign from the natal Moon; from any birth position that takes at most nine
  signs, so a first Sade Sati always begins before about age 23. Measured on the ephemeris
  (Lahiri, births 1850-2150, all twelve Moon signs): worst case 22.74 years, and the test below
  recomputes it, so the number on the page cannot rot the way a typed constant would.
* A *Phaladeepika* / *Brihat Jataka* attribution and "BPHS §Shani, and knowledge base §2.5".
  None of those books is held (knowledge/vedic_reference.md section 2.7), and the second names an
  internal file in user-facing prose.
* "strong Saturn (own sign, exalted, or in a kendra)". The held source (Rao, Lessons Vol. I, note
  29; vedic_reference.md section 2.7.2) is functional: Saturn as lagna lord or yogakaraka.
* "Classical remedies" listing a 108-count mantra, a lamp, footwear, a salt-free fast and colours
  that no knowledge/ file carries (remedies.md gives Saturn's japa as 19,000).
* "Common effects classical texts mention".

What this does NOT catch: phrase tests catch the wording they name, not every rewording, and the
remedy split is checked by position in the page, not by judging each item.
"""
from __future__ import annotations

import re

import pytest
import swisseph as swe

from astro_ai.learn_registry import get_article

SLUG = "sade-sati"


def _page(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return r.text


def _faq(question_fragment: str) -> str:
    art = get_article(SLUG)
    for f in art.faqs:
        if question_fragment in f["q"]:
            return f["a"]
    raise AssertionError(f"no FAQ containing {question_fragment!r}")


def _all_text(client) -> str:
    art = get_article(SLUG)
    faqs = " ".join(f["a"] for f in art.faqs)
    return _page(client) + " " + faqs + " " + art.llm_summary


def test_first_sade_sati_start_age_is_under_23_on_the_ephemeris():
    """The claim the page now makes, recomputed: no first Sade Sati starts at or after age 23."""
    from astro_ai.chart import _sid_calc_ut

    step = 4.0
    j0 = swe.julday(1850, 1, 1, 0)
    n = int((swe.julday(2150, 1, 1, 0) - j0) / step)
    signs = [int(_sid_calc_ut(j0 + i * step, swe.SATURN)[0][0] // 30) for i in range(n)]
    horizon = int(26 * 365.25 / step)
    worst = 0.0
    for i in range(0, n - horizon, 3):
        for moon in range(12):
            zone = {(moon - 1) % 12, moon, (moon + 1) % 12}
            if signs[i] in zone:
                continue
            k = i
            while signs[k] not in zone:
                k += 1
            worst = max(worst, (k - i) * step / 365.25)
    assert 20 < worst < 23, f"worst first-start age {worst:.2f} -- the page says about 23"


def test_no_27_35_age_window_anywhere(client):
    text = _all_text(client)
    for stale in ("27-35", "27–35", "56-64", "86-94"):
        assert stale not in text, f"{stale!r} still on the page or its FAQ"


def test_page_and_faq_state_the_first_start_is_by_about_age_23(client):
    assert "about age 23" in _page(client)
    assert "about age 23" in _faq("How many times")


@pytest.mark.parametrize("attribution", ["Phaladeepika", "Brihat Jataka", "BPHS", "knowledge base"])
def test_unheld_books_and_internal_files_are_not_cited(client, attribution):
    assert attribution not in _all_text(client), attribution


def test_strong_saturn_rule_is_the_functional_one(client):
    page = _page(client)
    faq = _faq("Is Sade Sati always bad")
    for text in (page, faq):
        assert "lagna lord" in text and "yogakaraka" in text
        assert "own sign, exalted" not in text
        assert "in a kendra" not in text
    # the computable set, from vedic_reference.md section 2.7.2
    assert "Capricorn or Aquarius" in faq and "Taurus or Libra" in faq


def test_remedies_are_not_all_labelled_classical(client):
    page = _page(client)
    assert "Classical remedies for Sade Sati" not in page
    m = re.search(r"<h2>Remedies for Sade Sati</h2>(.*?)<h2>", page, re.S)
    assert m, "remedies section missing"
    section = m.group(1)
    split = section.index("Common practice")
    sourced, practice = section[:split], section[split:]
    for item in ("Vishnu", "sesame seeds", "elderly", "Neelam"):
        assert item in sourced, f"{item} lost from the sourced list"
    for item in ("lamp", "Fast on Saturdays", "blue or black", "mustard oil", "footwear"):
        assert item in practice, f"{item} not in the common-practice list"
        assert item not in sourced, f"{item} presented as classical"
    assert "108" not in section  # remedies.md gives Saturn's japa as 19,000, not 108


def test_effects_are_not_attributed_to_classical_texts(client):
    page = _page(client)
    assert "Common effects classical texts mention" not in page
    assert "practitioners commonly describe" in page


def test_summary_does_not_recommend_mustard_oil(client):
    assert "mustard oil" not in get_article(SLUG).llm_summary
