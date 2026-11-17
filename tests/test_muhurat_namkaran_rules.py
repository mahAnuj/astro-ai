"""#1060: the Namkaran tithi and nakshatra sets and the day claim follow the two held muhurta books.

Source: knowledge/vedic_reference.md 29.13. Raman, *Muhurtha* (1948), Ch. VIII (Namakarana) gives the
10th, 12th or 16th day after birth, an auspicious-nakshatra list that includes Dhanishta and Satabhisha, and
an avoid list of the 4th, 6th, 8th, 12th, 14th lunar days, Full Moon and New Moon. Rao's Table 79 row
"Naming a child" is tithis 2, 3, 5, 7, 10, 11, 13 and lists Dhanishtha and Satabhisha.

Contested rows are pinned UNCHANGED on purpose (Magha avoided, Chitra credited, Navami avoided, the weekday
sets): the books disagree or one is silent, and changing them here would be a choice the issue did not make.

`data/` is absent on the runner, so these tests pin the code to that section, not to the books.
"""
from __future__ import annotations

from types import SimpleNamespace

from astro_ai import muhurat as m

NO_COMBUST = {"jupiter": False, "venus": False, "mercury": False}
RULES = m.EVENT_RULES["namkaran"]
LANDING = m.EVENT_LANDING["namkaran"]


def _score(tithi="Panchami", nakshatra="Rohini", weekday="Monday"):
    panchang = SimpleNamespace(tithi_name=tithi, tithi_paksha="Shukla")
    return m.score_event("namkaran", panchang, weekday, nakshatra, False, False, "", "", NO_COMBUST)


def test_issue_repro_now_prints_the_book_reading():
    assert "Dwadashi" not in RULES["good_tithis"]
    assert "Purnima" in RULES["avoid_tithis"]
    assert "Dhanishta" in RULES["good_nakshatras"]


def test_good_tithis_are_exactly_raos_row():
    assert RULES["good_tithis"] == {"Dwitiya", "Tritiya", "Panchami", "Saptami", "Dashami",
                                    "Ekadashi", "Trayodashi"}


def test_every_tithi_raman_rejects_is_avoided():
    # 4th, 6th, 8th, 12th, 14th, Full Moon, New Moon; Navami is kept (contested reading of an OCR-damaged figure).
    assert {"Chaturthi", "Shashti", "Ashtami", "Dwadashi", "Chaturdashi", "Purnima", "Amavasya"} <= RULES["avoid_tithis"]
    assert "Navami" in RULES["avoid_tithis"]
    assert not (RULES["good_tithis"] & RULES["avoid_tithis"])


def test_dwadashi_purnima_shashti_are_hard_avoid_not_credited():
    for tithi in ("Dwadashi", "Purnima", "Shashti"):
        rating, reason, _ = _score(tithi=tithi)
        assert rating == "avoid", (tithi, rating, reason)


def test_dhanishta_and_shatabhisha_are_credited_in_scoring():
    for nak in ("Dhanishta", "Shatabhisha"):
        assert nak in RULES["good_nakshatras"]
        assert nak not in RULES["avoid_nakshatras"]
        _, reason, _ = _score(nakshatra=nak)
        assert f"good nakshatra ({nak})" in reason


def test_contested_rows_are_unchanged():
    assert "Magha" in RULES["avoid_nakshatras"]
    assert "Chitra" in RULES["good_nakshatras"]
    assert RULES["good_days"] == {"Monday", "Wednesday", "Thursday", "Friday"}
    assert not (RULES["good_nakshatras"] & RULES["avoid_nakshatras"])


def _copy():
    return " ".join([LANDING["hero_subtitle"], *LANDING["intro_paragraphs"], *LANDING["rules_summary"]])


def test_page_copy_gives_ramans_days_and_not_the_unsourced_eleventh():
    text = _copy()
    assert "10th, 12th or 16th day" in text
    assert "11th day" not in text and "11th-day" not in text
    assert "Grihya" not in text


def test_rules_summary_tithi_line_matches_the_set():
    line = next(s for s in LANDING["rules_summary"] if s.startswith("Favourable tithi"))
    assert line.startswith("Favourable tithi (2, 3, 5, 7, 10, 11, 13)")
    assert "12" not in line.split(";")[0]
    assert "12th" in line.split(";")[1]


def test_intro_nakshatra_list_is_exactly_the_credited_set():
    para = next(p for p in LANDING["intro_paragraphs"] if p.startswith("What we do check"))
    listed = para.split("auspicious nakshatras (")[1].split(")")[0]
    assert {n.strip() for n in listed.split(",")} == RULES["good_nakshatras"]


def test_code_comment_no_longer_calls_the_eleventh_day_classical():
    src = open(m.__file__, encoding="utf-8").read()
    i = src.index('"namkaran": {\n        "label"')
    block = src[i:i + 1800]
    assert "classically done on the 11th" not in block
    assert "10th, 12th or 16th" in block
