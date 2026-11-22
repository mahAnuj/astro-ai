"""#1359: festival copy stops presenting "abujha" as a rule that removes the need for a muhurat.

The registry said Devuthani Ekadashi was "auspicious the whole day through", that Vasant Panchami, Akshaya
Tritiya, Ugadi/Gudi Padwa and Dussehra were each "one of the three and a half abujha muhurats" needing "no
further calculation", and (Dussehra's observance, no "abujha" in it) that a new undertaking "needs no further
muhurat check". The astro-auditor ruling on #1359: abujha is an UNSOURCED regional almanac custom (the four held
books record 0 hits for it, knowledge/vedic_reference.md section 29.14), so the copy may say the custom exists
and must send the reader to the tithi, star and Panchak. Devuthani is Panchak-flagged on 2026-11-20 and
2027-11-10, so "whole day auspicious" was also false on a date this registry prints. The "three and a half"
count is unsourced and contradicted by the registry itself (five days claim it). The Moon-in-Taurus reason for
Akshaya Tritiya holds in one year of three (Moon in Aries 29.7 deg in 2026, Gemini 1.8 deg in 2027, Taurus in
2028), so it is gone. "Classically ... Brahma began creation" is Puranic, not in knowledge/*.md.

A phrase test: it catches the wordings it names, not every possible rewording. The markers test is what holds
the line for new wording: any copy that says abujha must also say it is almanac custom and name Panchak.
"""
from __future__ import annotations

import re

import pytest

from astro_ai.festival_registry import FESTIVALS

# Case-insensitive. Each is a shape the shipped copy used to claim a day needs no muhurat check.
_FORBIDDEN_EN = (
    r"whole day",
    r"needs? no (further )?(muhurat|calculation)",
    r"no further (calculation|muhurat)",
    r"without (needing )?a calculated (window|muhurat)",
    r"calculated window",
    r"universally",
    r"auspicious throughout",
    r"three and a half",
    r"in their entirety",
    r"swayamsiddha",
    r"classically it is the day brahma",
)
_FORBIDDEN_HI = (r"पूरा दिन शुभ", r"पूरे दिन", r"साढ़े तीन")

# Slugs whose copy claimed abujha when #1359 was filed; the markers test must see them, or it is vacuous.
_ABUJHA_SLUGS = {"vasant-panchami", "ugadi-gudi-padwa", "akshaya-tritiya", "dussehra", "devuthani-ekadashi"}


def _fields(f) -> str:
    return " ".join([f.note_en, f.note_hi, f.significance, f.observance_window, f.observance])


def _by_slug(slug: str):
    return next(f for f in FESTIVALS if f.slug == slug)


@pytest.mark.parametrize("f", FESTIVALS, ids=lambda f: f.slug)
def test_no_festival_copy_says_a_day_needs_no_muhurat(f):
    text = _fields(f)
    for pat in _FORBIDDEN_EN:
        assert re.search(pat, text, re.I) is None, (f.slug, pat)
    for pat in _FORBIDDEN_HI:
        assert re.search(pat, text) is None, (f.slug, pat)


@pytest.mark.parametrize("f", FESTIVALS, ids=lambda f: f.slug)
def test_abujha_copy_names_the_almanac_custom_and_panchak(f):
    en = (f.note_en + " " + f.significance)
    if "abujha" in en.lower():
        assert "almanac custom" in en.lower(), f.slug
        assert "Panchak" in en, f.slug
    if "अबूझ" in f.note_hi:
        assert "पंचांग-प्रथा" in f.note_hi, f.slug
        assert "पंचक" in f.note_hi, f.slug


def test_the_abujha_markers_test_is_not_vacuous():
    carrying = {
        f.slug for f in FESTIVALS
        if "abujha" in (f.note_en + " " + f.significance).lower()
    }
    assert _ABUJHA_SLUGS <= carrying, _ABUJHA_SLUGS - carrying


def test_the_unsourced_astrology_stays_out_of_the_pinned_entries():
    assert "moon in taurus" not in _fields(_by_slug("akshaya-tritiya")).lower()
    devuthani = _fields(_by_slug("devuthani-ekadashi")).lower()
    assert re.search(r"(clear of|free of|outside) panchak", devuthani) is None
    assert "2026 and 2027" not in devuthani
    assert "classically" not in _fields(_by_slug("ugadi-gudi-padwa")).lower()
