"""#583: Life Path strong months follow Cheiro's table, and the cautious months say they are editorial.

WHAT WAS WRONG
--------------
`_PROFILES[n].strong_months` for 2, 4, 7, 8 and 9 disagreed with knowledge/numerology.md
§14.6 (Cheiro, "Strong periods"): 2 was a month late and credited to "Moon-in-Cancer's own
house", 4 and 7 were undated "ephemeris-dependent" placeholders, 8 ran a month late and 9
ended on Apr 28 where Cheiro says 19/26 Apr. Nothing in the held corpus supports the
planetary reasoning those strings carried.

Numbers 1 (Johari §4-sourced) and 3, 5, 6 (agree with §14.6 to about a day) are deliberately
untouched, so they are not pinned here.

`weak_months` for 2-9 has no held source at all (only number 1's, Johari §4:200). It is left
as written and the page labels it editorial; these tests pin the label, not the dates.
"""

from __future__ import annotations

import pytest

from astro_ai import numerology as n

# §14.6 rows, "20/27" uncertainty kept as Cheiro writes it.
CHEIRO = {
    2: ["Jun 20 – Jul 27"],
    4: ["Jun 21 – Jul 20/27", "Jul 22 – end of Aug"],
    7: ["Jun 21 – Jul 20/27, less strongly to end of Aug"],
    8: ["Dec 21 – Jan 20/27", "then to Feb 19/26"],
    9: ["Mar 21 – Apr 19/26", "Oct 21 – Nov 20/27"],
}

FORBIDDEN = ("Moon-in-Cancer", "ephemeris", "full-moon periods", "Ketu-friendly",
             "Rahu's own", "Mars's own sign", "Saturn's own signs", "Sun-in-Scorpio",
             "Sun-in-Aries", "Apr 28")

CAPTION = "Editorial guidance, not a dated rule from the classical text we follow."


@pytest.mark.parametrize("number, windows", sorted(CHEIRO.items()))
def test_strong_months_match_cheiro_14_6(number, windows):
    text = n._PROFILES[number].strong_months
    for w in windows:
        assert w in text, f"Life Path {number}: {w!r} missing from {text!r}"
    # The tradition, not the author, in user-facing copy (verify_numerology_copy,
    # #200); the author stays in numerology.py's comments and numerology.md §14.6.
    assert "the Chaldean tradition's strong period for this number" in text
    assert "Cheiro" not in text


def test_no_invented_reasoning_remains_in_the_rewritten_rows():
    for number in CHEIRO:
        text = n._PROFILES[number].strong_months
        for phrase in FORBIDDEN:
            assert phrase not in text, f"Life Path {number} still says {phrase!r}"


def test_no_profile_carries_an_ephemeris_placeholder():
    for number, prof in n._PROFILES.items():
        assert "ephemeris" not in prof.strong_months, number


def _numerology_page(client, birth_date):
    r = client.post("/numerology", data={"name": "Asha Rao", "birth_date": birth_date})
    assert r.status_code == 200, r.status_code
    assert "Cautious months" in r.text, "the reading did not render; the test proves nothing"
    return r.text


def _birth_date_for(life_path):
    """A date the real compute() maps to `life_path`, found rather than hard-coded."""
    for year in range(1960, 2010):
        for month in range(1, 13):
            for day in range(1, 29):
                bd = f"{year}-{month:02d}-{day:02d}"
                if n.compute("Asha Rao", bd, target_year=2026).life_path == life_path:
                    return bd
    raise AssertionError(f"no 1960-2009 birth date reaches life path {life_path}")


@pytest.mark.parametrize("life_path", [2, 8])
def test_page_renders_cheiro_window_and_editorial_caption(client, life_path):
    html = _numerology_page(client, _birth_date_for(life_path))
    assert CHEIRO[life_path][0] in html
    assert CAPTION in html


def test_life_path_1_has_no_editorial_caption(client):
    html = _numerology_page(client, _birth_date_for(1))
    assert n._PROFILES[1].weak_months.split(" (")[0] in html
    assert CAPTION not in html
