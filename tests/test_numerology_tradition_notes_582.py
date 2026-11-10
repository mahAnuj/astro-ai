"""#582: the same numeral is read by two traditions on /numerology, and the page says so.

WHAT WAS WRONG
--------------
The Karmic Debt banner (Kumar's category, knowledge/numerology.md §12.5) and the
master-number readings (kept as a product call, §8) sat on the same page as the
compound-number row (§14.3), which reads 13/14/16/19 and 11/22/33 on its own terms:
Suman's 19 is a Karmic Debt and "fortunate and extremely favourable" at once.

chief's Standing ruling 3: declare which school a reading follows. So the page now
carries a tradition note, and no computation, meaning text or score moves. These
tests pin both halves: the notes appear where the numerals overlap, and the numbers
are exactly what they were.
"""

from __future__ import annotations

import pytest

from astro_ai import numerology as n

BIRTH = "1990-05-12"

BANNER = "This is a different tradition from the compound-number reading further down this page"
KARMIC_NOTE = 'data-tradition-note="karmic-debt"'
MASTER_NOTE = 'data-tradition-note="master-number"'


def _post(client, name):
    r = client.post("/numerology", data={"name": name, "birth_date": BIRTH})
    assert r.status_code == 200
    return r.text


# (name, karmic numbers, compound, bhagya score) -- measured before the template change
PROBES = [
    ("Suman", (19,), 19, 57),
    ("Kiran", (), 11, 58),
    ("Mohan", (14,), 22, 50),
    ("Ankit", (13,), 13, 48),
]


@pytest.mark.parametrize("name, karmic, compound, score", PROBES)
def test_numbers_are_unchanged_by_the_note(name, karmic, compound, score):
    r = n.compute(name, BIRTH)
    assert r.karmic_debt_numbers == karmic
    assert r.name_compound == compound
    assert n.compute_numerology_bhagya_score(r).value == score


def test_karmic_banner_declares_the_other_tradition(client):
    for name in ("Suman", "Mohan", "Ankit"):
        assert BANNER in _post(client, name), name


def test_suman_and_ankit_get_the_karmic_overlap_note(client):
    # compound 19 and 13 are also Karmic Debt numbers
    for name in ("Suman", "Ankit"):
        html = _post(client, name)
        assert KARMIC_NOTE in html, name
        assert MASTER_NOTE not in html, name


def test_kiran_and_mohan_get_the_master_number_note(client):
    # compound 11 and 22 are master numbers
    for name in ("Kiran", "Mohan"):
        html = _post(client, name)
        assert MASTER_NOTE in html, name
        assert KARMIC_NOTE not in html, name  # Kiran has no debt; Mohan's is 14, compound 22


def test_every_probe_page_carries_a_tradition_note(client):
    """The metric: 4 of 4 contradicting pages had no note; now each has one."""
    for name, *_ in PROBES:
        html = _post(client, name)
        assert KARMIC_NOTE in html or MASTER_NOTE in html or BANNER in html, name


def test_no_overlap_shows_neither_conditional_note(client):
    # Baldwin: compound 22 (master) -- so use a name measured to have neither overlap
    r = n.compute("Amit Sharma", BIRTH)
    assert r.name_compound not in r.karmic_debt_numbers
    assert r.name_compound not in (11, 22, 33)
    html = _post(client, "Amit Sharma")
    assert KARMIC_NOTE not in html
    assert MASTER_NOTE not in html
    # the existing compound caption is untouched and still there
    assert "The two are read together, not one instead of the other" in html


def test_no_debt_means_no_banner_note(client):
    r = n.compute("Amit Sharma", BIRTH)
    if not r.karmic_debt_numbers:
        assert BANNER not in _post(client, "Amit Sharma")
