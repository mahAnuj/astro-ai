"""The per-area day ratings and the sourced remedy (#523).

WHY THIS EXISTS
---------------
It did not, and that is the whole point. The feature shipped with zero tests,
and QA then found FIVE defects in it across two rounds. Each of the five would
have been caught by ONE assertion here:

  1. `_AREA_KARAKAS` was harvested one markdown line at a time, so every graha
     sitting on a wrap continuation was silently dropped -- Saturn from Work,
     Mars from Relationships, Mercury from Health. 6 for 6, no counter-example.
  2. four of the nine good deeds were the exact clauses `remedies.md` §11.2
     flags as NOT Rao's, under a commit claiming "Rao's own wording".
  3. a duplicate `_GRAHA_GOOD_DEED_HI` shadowed the fix for (2), so the English
     was corrected and the rendered Hindi still said "serve the elderly".
  4. the remedy's tie-break was house NUMBER, so a Saturn Sade Sati phase was
     passed over on 3 of the 4 rashis that had one.
  5. `_HOUSE_ORDINAL_HI` was a derived rule (`f"{n}वें"`), wrong in 4 of 12
     houses, leaking "1वें" where Hindi wants पहले.

So these are not coverage for its own sake: they are the five specific
regressions, plus the structural claim the panel makes about itself (that it
and the prose are computed from one sky) which was false until the day moment
was pinned.

Every assertion drives the real function against the real corpus file. None
reimplements the rule, and none asserts a figure for today's sky -- those
change daily by design.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from astro_ai import chart as chart_mod
from astro_ai.chart import (
    RASHIFAL_REFERENCE_PLACE,
    area_ratings_for_rashi,
    compute_chart,
    compute_transit_snapshot,
    gochara_for_rashi,
    rashifal_day_moment,
    remedy_for_rashi,
)

KNOWLEDGE = Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "knowledge"
IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture(scope="module")
def natal():
    return compute_chart("2000-01-01", "12:00", RASHIFAL_REFERENCE_PLACE)


@pytest.fixture(scope="module")
def transit(natal):
    return compute_transit_snapshot(natal, when=rashifal_day_moment(date(2026, 10, 25)))


# ---------------------------------------------------------------------------
# 1. The karaka sets, against the whole field and not one line of it
# ---------------------------------------------------------------------------

#: area -> the houses whose karaka fields it counts, as `_AREA_KARAKAS` cites.
_AREA_HOUSES = {
    "Work": ("10th",),
    "Money": ("2nd", "11th"),
    "Relationships": ("7th",),
    "Health": ("6th", "1st"),
}

_GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
           "Rahu", "Ketu")


def _karaka_field(house_ordinal: str) -> str:
    """The FULL 'Karakas:' field for one house from houses.md, wraps included.

    Reading this by line is the defect (1) above: the field is a paragraph that
    markdown wraps mid-sentence, so `grep` for the heading returns a prefix of
    it. This walks to the next field instead, which is what a human reading the
    page sees.
    """
    text = (KNOWLEDGE / "houses.md").read_text(encoding="utf-8")
    # The house's own section, then the Karakas field inside it up to the next
    # field label or blank-line break.
    m = re.search(rf"^#+\s*{re.escape(house_ordinal)}\s+House.*?(?=^#+\s|\Z)",
                  text, re.M | re.S)
    assert m, f"no section for the {house_ordinal} house in houses.md"
    section = m.group(0)
    k = re.search(r"\*{0,2}Karakas?\*{0,2}\s*:?\s*(.+?)(?=\n\s*\n|\n\s*[-*]?\s*\*{2}\w)",
                  section, re.S)
    assert k, f"no Karakas field in the {house_ordinal} house section"
    return k.group(1)


@pytest.mark.parametrize("area", sorted(_AREA_HOUSES))
def test_every_graha_named_in_the_cited_karaka_fields_is_counted(area):
    """Defect (1). The set must be the union of the FULL fields, not a prefix.

    This is the assertion whose absence let Saturn, Mars and Mercury be dropped
    while the PR body called the omissions deliberate.
    """
    coded = {a: set(k) for a, k, _src in chart_mod._AREA_KARAKAS}[area]
    named: set[str] = set()
    for house in _AREA_HOUSES[area]:
        field = _karaka_field(house)
        named |= {g for g in _GRAHAS if re.search(rf"\b{g}\b", field)}
    missing = named - coded
    assert not missing, (
        f"{area}: {sorted(missing)} are named in the "
        f"{'/'.join(_AREA_HOUSES[area])} karaka field(s) of houses.md but are "
        f"not counted. This is the wrap-continuation defect: read the whole "
        f"field, not its first line."
    )


def test_no_area_counts_a_graha_its_houses_do_not_name():
    """The other direction: a count may not include an invented karaka."""
    for area, karakas, _src in chart_mod._AREA_KARAKAS:
        named: set[str] = set()
        for house in _AREA_HOUSES[area]:
            named |= {g for g in _GRAHAS if re.search(rf"\b{g}\b", _karaka_field(house))}
        extra = set(karakas) - named
        assert not extra, f"{area}: {sorted(extra)} appear in no cited field"


def test_a_rating_is_a_count_with_its_denominator_and_never_a_score(transit):
    """Raman gives no aggregation rule, so there is no single number to print."""
    for entry in area_ratings_for_rashi(0, transit):
        assert set(entry) >= {"area", "favourable", "total"}
        assert entry["total"] == len(
            dict((a, k) for a, k, _s in chart_mod._AREA_KARAKAS)[entry["area"]])
        assert 0 <= entry["favourable"] <= entry["total"]
        # No key may carry a rolled-up figure.
        assert not {"score", "stars", "rating", "percent"} & set(entry)


# ---------------------------------------------------------------------------
# 2 + 3. The deeds: sourced, single-defined, and Hindi that is actually Hindi
# ---------------------------------------------------------------------------

def _unsourced_clauses() -> list[str]:
    """The clauses remedies.md §11.2 flags as NOT the cited author's.

    §11.2 exists verbatim so "a reader can tell the two apart". Defect (2) was
    shipping exactly its contents under a commit claiming the source's
    authority, because the table above it was read and the warning below was
    not.
    """
    text = (KNOWLEDGE / "remedies.md").read_text(encoding="utf-8")
    m = re.search(r"^#+.*Unsourced additions already in this file.*?$(.*?)(?=^#+\s|\Z)",
                  text, re.M | re.S)
    assert m, "remedies.md no longer has the §11.2 'Unsourced additions' section"
    return [c.strip().lower() for c in re.findall(r'"([^"]{6,})"', m.group(1))]


def test_no_good_deed_is_a_clause_the_corpus_flags_as_unsourced():
    """Defect (2). The warning sits below the table; both must be read."""
    flagged = _unsourced_clauses()
    assert flagged, "parsed no flagged clauses -- the guard would be vacuous"
    for graha, deed in chart_mod._GRAHA_GOOD_DEED.items():
        for clause in flagged:
            assert clause not in deed.lower(), (
                f"{graha}: {deed!r} contains {clause!r}, which remedies.md "
                f"§11.2 explicitly flags as not the cited author's"
            )


def test_each_deed_table_is_defined_exactly_once():
    """Defect (3). A second definition silently shadows the first.

    Caught last time only because the rendered Hindi still said "serve the
    elderly" after the English had been fixed.
    """
    src = Path(chart_mod.__file__).read_text(encoding="utf-8")
    for name in ("_GRAHA_GOOD_DEED", "_GRAHA_GOOD_DEED_HI", "_GRAHA_HI",
                 "_HOUSE_ORDINAL", "_HOUSE_ORDINAL_HI", "_AREA_KARAKAS"):
        n = len(re.findall(rf"^{name}(?:\s*:\s*[^=]+)?\s*=", src, re.M))
        assert n == 1, f"{name} is defined {n} times in chart.py; a later one shadows"


def test_the_two_deed_tables_cover_the_same_grahas():
    assert set(chart_mod._GRAHA_GOOD_DEED) == set(chart_mod._GRAHA_GOOD_DEED_HI)
    assert set(chart_mod._GRAHA_GOOD_DEED) <= set(chart_mod._GRAHA_HI)


def test_no_deed_in_either_language_offers_a_gemstone():
    """remedies.md §1.4 is categorical: a gemstone needs the Ascendant.

    A Rashifal is written for a rashi and has none, and the wrong stone -- blue
    sapphire for Saturn above all -- WORSENS the affliction. So the §4.2 table
    must stay unreachable from this path.
    """
    banned = ("gem", "stone", "sapphire", "ruby", "pearl", "emerald", "diamond",
              "coral", "topaz", "quartz", "ratna", "रत्न",
              "नीलम", "माणिक",
              "मोती", "पन्ना",
              "हीरा", "मूंगा")
    for table in (chart_mod._GRAHA_GOOD_DEED, chart_mod._GRAHA_GOOD_DEED_HI):
        for graha, deed in table.items():
            low = deed.lower()
            for word in banned:
                assert word not in low, f"{graha}: {deed!r} names {word!r}"


# ---------------------------------------------------------------------------
# 4. The sourced ordering must beat the unsourced one
# ---------------------------------------------------------------------------

def test_an_adverse_saturn_in_a_named_phase_always_wins_the_remedy(natal):
    """Defect (4). Sade Sati (12/1/2) and Ashtama Shani (8) are SOURCED.

    The first version sorted on house number, so houses 4, 7 and 1 came before
    12, 8 and 2 and the phase was passed over on 3 of the 4 rashis that had
    one. Swept over a year so the assertion does not depend on today's sky.
    """
    checked = 0
    for n in range(0, 366, 7):
        snap = compute_transit_snapshot(
            natal, when=rashifal_day_moment(date(2026, 1, 1) + timedelta(days=n)))
        for rashi in range(12):
            adverse = [e for e in gochara_for_rashi(rashi, snap)
                       if e["verdict"] == "challenging"
                       and e["planet"] in chart_mod._GRAHA_GOOD_DEED]
            phase = [e for e in adverse
                     if e["planet"] == "Saturn" and e["house"] in (12, 1, 2, 8)]
            if not phase:
                continue
            checked += 1
            pick = remedy_for_rashi(rashi, snap)
            assert pick and pick["planet"] == "Saturn", (
                f"rashi {rashi} on day {n}: Saturn is in house "
                f"{phase[0]['house']} (a named phase) and adverse, but the "
                f"remedy named {pick and pick['planet']}"
            )
    assert checked > 50, f"only {checked} phase-days swept; the guard is weak"


def test_no_remedy_is_invented_when_nothing_transits_adversely(transit):
    """A day with no affliction needs none, and inventing one is the defect."""
    class _Empty:
        planets: list = []
    assert remedy_for_rashi(0, _Empty()) is None


# ---------------------------------------------------------------------------
# 5. The Hindi surface
# ---------------------------------------------------------------------------

_LATIN = re.compile(r"[A-Za-z]")


def test_the_hindi_ordinals_are_twelve_literals_not_a_derived_rule():
    """Defect (5). `f"{n}वें"` is wrong for 1, 2, 3 and 6.

    The English table three lines below says why it is spelled out: "'3th'
    shipped from a naive f'{h}th' in the first draft". The Hindi map WAS that
    rule.
    """
    H = chart_mod._HOUSE_ORDINAL_HI
    assert set(H) == set(range(1, 13))
    for n, word in H.items():
        assert not _LATIN.search(word), f"house {n}: {word!r} has a Latin letter"
        assert not word.startswith(str(n)), (
            f"house {n}: {word!r} is the derived f'{{n}}वें' form; Hindi "
            f"ordinals are irregular at 1, 2, 3 and 6"
        )


@pytest.mark.parametrize("rashi", range(12))
def test_the_hindi_remedy_line_has_no_latin_character(transit, rashi):
    """Every field the Hindi panel prints, not just the deed.

    `house_ord` was the leak QA found -- "(Jupiter 4th भाव)" -- and it was
    introduced by this feature, so a disclosure about the pre-existing planet
    names did not cover it.
    """
    pick = remedy_for_rashi(rashi, transit, "hi")
    if pick is None:
        pytest.skip("nothing adverse for this rashi on the pinned day")
    for field in ("deed", "planet_label", "house_ord"):
        assert not _LATIN.search(str(pick[field])), (
            f"rashi {rashi}: {field}={pick[field]!r} leaks English onto a "
            f"Hindi surface"
        )


# ---------------------------------------------------------------------------
# The structural claim: the panel and the prose are ONE computation
# ---------------------------------------------------------------------------

def test_the_day_detail_does_not_depend_on_the_hour_it_is_asked(natal):
    """What `_day_detail_today` claimed and could not deliver until pinning.

    The reading is generated once and cached for the day; the panel recomputed
    every 900 s from `datetime.now()`. QA measured the two disagreeing on 9 of
    90 days, with the area counts moving for 10 of 12 rashis on 2026-10-31.
    The nightly job (#515) makes it worse than occasional: it generates at
    ~03:30 IST for a page served all day.

    So: asked for the same DATE, the answer must not move with the clock.
    """
    def detail(snap):
        return [(tuple((a["area"], a["favourable"], a["total"])
                       for a in area_ratings_for_rashi(i, snap)),
                 (lambda r: r and (r["planet"], r["house"]))(remedy_for_rashi(i, snap)))
                for i in range(12)]

    unpinned_moves = 0
    for n in range(90):
        day = date(2026, 10, 25) + timedelta(days=n)
        pinned = detail(compute_transit_snapshot(natal, when=rashifal_day_moment(day)))
        # The pin is a pure function of the date: every hour agrees.
        for hour in (0, 6, 12, 18, 23):
            moment = datetime(day.year, day.month, day.day, hour, 30, tzinfo=IST)
            assert detail(compute_transit_snapshot(
                natal, when=rashifal_day_moment(day))) == pinned
            # And record how often the OLD behaviour would have diverged, so
            # this test fails loudly if someone re-introduces now().
            if detail(compute_transit_snapshot(natal, moment)) != pinned:
                unpinned_moves += 1
    assert unpinned_moves > 0, (
        "no day in 90 diverged under an unpinned clock, so this test is not "
        "actually guarding anything -- check the ephemeris, not the code"
    )


def test_the_pinned_moment_is_local_noon_and_cannot_slip_a_day():
    """Noon, not an hour near midnight, so no offset moves the calendar date."""
    for n in range(0, 365, 11):
        day = date(2026, 1, 1) + timedelta(days=n)
        moment = rashifal_day_moment(day)
        assert moment.hour == 12 and moment.minute == 0
        assert moment.date() == day
        assert moment.astimezone(ZoneInfo("UTC")).date() == day, (
            "noon at the reference place must stay on the same UTC date"
        )


# ---------------------------------------------------------------------------
# Inputs that must not produce a plausible wrong answer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [12, 13, 99, -1, -12])
def test_an_out_of_range_rashi_returns_nothing_rather_than_a_wrong_panel(transit, bad):
    """`((p - r) % 12) + 1` accepts any int, and 12 returned ALL ZEROS.

    All-zeros is the worst-looking day the panel can render and is
    indistinguishable from a real one, so silence is the only safe answer.
    """
    assert area_ratings_for_rashi(bad, transit) == []
    assert remedy_for_rashi(bad, transit) is None
    assert gochara_for_rashi(bad, transit) == []


@pytest.mark.parametrize("broken", [None, object()])
def test_a_malformed_transit_degrades_instead_of_raising(broken):
    """These feed a panel and a prompt; neither may 500 over a decoration."""
    assert area_ratings_for_rashi(0, broken) == []
    assert remedy_for_rashi(0, broken) is None
    assert gochara_for_rashi(0, broken) == []
