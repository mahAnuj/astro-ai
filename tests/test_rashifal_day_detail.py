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
    """Defect (4). Sade Sati (Saturn 12th/1st/2nd) is SOURCED; the 8th is not.

    The first version sorted on house number, so houses 4, 7 and 1 came before
    12 and 2 and the phase was passed over on 3 of the 4 rashis that had one.
    Swept over a year so the assertion does not depend on today's sky.

    The set is (12, 1, 2) and NOT (12, 1, 2, 8): vedic_reference.md §2.7.1
    sources the three Sade Sati signs to Rao, and marks §2.4 Ashtama Shani
    UNSOURCED (`ashtama shani` = 0 across 14 books). See the next test for the
    8th.
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
                     if e["planet"] == "Saturn" and e["house"] in (12, 1, 2)]
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


def _entry(planet: str, house: int) -> dict:
    return {"planet": planet, "house": house, "verdict": "challenging", "weighty": True}


def test_saturn_in_the_eighth_is_not_special_cased_by_the_remedy(natal, monkeypatch):
    """Ashtama Shani is UNSOURCED (vedic_reference.md §2.4, audited at §2.7.3).

    It was once in the Saturn tier via `(12, 1, 2, 8)` under a comment saying
    every tier was sourced. So an adverse Saturn in the 8th must rank as an
    ordinary slow mover -- behind a lower-numbered Jupiter -- while Saturn in
    the 12th, 1st or 2nd, which Rao sources, still outranks that same Jupiter.
    Driven through `remedy_for_rashi` with the Gochara entries fixed, so the
    ranking is the only thing varying.
    """
    def pick(saturn_house: int):
        monkeypatch.setattr(chart_mod, "gochara_for_rashi",
                            lambda r, t: [_entry("Jupiter", 4), _entry("Saturn", saturn_house)])
        got = remedy_for_rashi(0, object())
        return got and got["planet"]

    assert pick(8) == "Jupiter", "Saturn in the 8th outranked Jupiter: Ashtama is back in the sourced tier"
    for house in (12, 1, 2):
        assert pick(house) == "Saturn", f"Sade Sati house {house} lost the Saturn tier"


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


def test_every_hindi_table_the_remedy_can_print_is_free_of_latin_letters():
    """All nine deeds, all nine graha names, all twelve ordinals -- not the one
    the pinned day happens to pick.

    The per-rashi test below only inspects whichever graha `remedy_for_rashi`
    selects on one date, so a Latin word put into the Ketu deed -- a graha that
    day never picks -- left the suite green. The tables are the surface; walk
    them.
    """
    for name in ("_GRAHA_GOOD_DEED_HI", "_GRAHA_HI", "_HOUSE_ORDINAL_HI"):
        table = getattr(chart_mod, name)
        assert table, f"{name} is empty -- the guard would be vacuous"
        for key, text in table.items():
            assert not _LATIN.search(str(text)), (
                f"{name}[{key!r}] = {text!r} has a Latin letter on a Hindi surface")
    assert len(chart_mod._GRAHA_GOOD_DEED_HI) == 9, "expected all nine grahas' deeds"


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
# The pin must reach EVERY call site -- the helper being pure is not enough
# ---------------------------------------------------------------------------
#
# The test above compares `rashifal_day_moment` with itself, so it guards the
# helper and nothing else. QA reverted the `when=` at each of five call sites
# and the suite stayed green every time (1229 passed): a comment in chart.py
# said "this file asserts no Rashifal path forgets it" and nothing did.
#
# Each test below drives the REAL path in-process with `compute_transit_snapshot`
# (and `compute_panchang` where the path pins it) wrapped by a spy patched where
# that module LOOKS IT UP -- `from astro_ai.chart import compute_transit_snapshot`
# binds a second name, so patching `chart` rebinds nothing. The spy records the
# `when` it receives and delegates to the real function, so the path still runs.
# No LLM (`providers.chat` / `_daily_rashifal_text` stubbed), no mail, no GCS.

def _spy(monkeypatch, module, name):
    """Wrap `module.<name>`; return the list of `when` values it was called with.

    A missing `when` is recorded as None, so "forgot the pin" and "passed the
    wrong moment" both fail the same assertion.
    """
    seen: list = []
    real = getattr(module, name)

    def spy(*args, **kwargs):
        seen.append(kwargs["when"] if "when" in kwargs
                    else (args[1] if len(args) > 1 else None))
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, spy)
    return seen


def _assert_all_pinned(seen: list, day: date, what: str) -> None:
    assert seen, f"{what}: the spy was never reached -- the test is not driving the path"
    want = rashifal_day_moment(day)
    assert seen == [want] * len(seen), (
        f"{what}: expected every call to be pinned to {want!r}, got {seen!r}. "
        f"A None here is a call site that forgot `when=` and so reads now()."
    )


@pytest.fixture
def _empty_hot_cache():
    from astro_ai import hot_cache

    hot_cache.clear()
    yield
    hot_cache.clear()


@pytest.mark.parametrize("helper,args", [
    ("_day_detail_today", (0,)),
    ("_gochara_today", (0,)),
    ("_chandra_bala_today", ("aries",)),
])
def test_the_panel_helpers_compute_from_the_pinned_moment(
        monkeypatch, _empty_hot_cache, helper, args):
    """routes/rashifal.py: the three panel helpers beside the reading."""
    from astro_ai.routes import rashifal

    seen = _spy(monkeypatch, rashifal, "compute_transit_snapshot")
    getattr(rashifal, helper)(*args)
    _assert_all_pinned(seen, date.today(), f"rashifal.{helper}")


def test_the_reading_path_pins_both_the_transit_and_the_panchang(
        client, stub_llm, rashi_body, today_iso, monkeypatch):
    """routes/rashifal.py `rashifal_single`: the sky the LLM is shown.

    This is the call whose pin makes the PROSE agree with the panel. Driven
    through the real route with the provider stubbed (`providers.chat`), so the
    live-generation branch -- the only one that computes a transit -- runs.
    """
    from astro_ai import daily_cache
    from astro_ai.routes import rashifal

    stub_llm(lambda _n: rashi_body(heading="Aries / Mesha"))
    daily_cache.put("rashifal_single", "aries-en", {"body": ""}, today_iso)
    transits = _spy(monkeypatch, rashifal, "compute_transit_snapshot")
    panchangs = _spy(monkeypatch, rashifal, "compute_panchang")

    r = client.get("/rashifal/aries")

    assert r.status_code == 200, r.status_code
    _assert_all_pinned(transits, date.today(), "rashifal_single transit")
    _assert_all_pinned(panchangs, date.today(), "rashifal_single panchang")


def _disarm_mail_and_generation(monkeypatch):
    """Stub generation and sending so the subscribe paths touch no LLM, mail or GCS."""
    from astro_ai.routes import subscribe

    sections = "\n\n".join(
        f"## {r}\n" + "A steady day for measured work. " * 40
        for r in ("Aries / Mesha", "Taurus / Vrishabha"))
    monkeypatch.setattr(subscribe, "_daily_rashifal_text", lambda **k: sections)
    monkeypatch.setattr(subscribe.email_sender, "send", lambda *a, **k: True)
    monkeypatch.setattr(subscribe.subscribers, "list_subscribers", lambda: [])
    return subscribe


@pytest.fixture
def _admin():
    from astro_ai.main import app
    from astro_ai.routes.deps import require_admin

    app.dependency_overrides[require_admin] = lambda: None
    yield
    app.dependency_overrides.pop(require_admin, None)


def test_the_morning_blast_pins_the_transit(client, _admin, monkeypatch):
    """routes/subscribe.py `send_daily_rashifal` (the 7 AM email)."""
    subscribe = _disarm_mail_and_generation(monkeypatch)
    seen = _spy(monkeypatch, subscribe, "compute_transit_snapshot")

    r = client.post("/admin/send-daily-rashifal")

    assert r.status_code == 200, r.text
    _assert_all_pinned(seen, date.today(), "send_daily_rashifal")


def test_the_warm_job_pins_the_transit(client, _admin, monkeypatch):
    """routes/subscribe.py `warm_rashifal` (the cache the blast and pages read)."""
    subscribe = _disarm_mail_and_generation(monkeypatch)
    seen = _spy(monkeypatch, subscribe, "compute_transit_snapshot")

    client.post("/admin/warm-rashifal?lang=en")

    _assert_all_pinned(seen, date.today(), "warm_rashifal")


def test_the_welcome_email_pins_every_transit_it_computes(monkeypatch):
    """routes/subscribe.py `_send_welcome_email`: TWO call sites in one function.

    The first feeds the generated reading; the second feeds the Chandra Bala,
    Gochara and per-area context. email/welcome.html does not render that
    context today (only email/daily_rashifal.html does), so this guards the
    next template to adopt it, not a difference a reader sees now: left on
    now() it would be a panel and a reading from different skies.
    """
    subscribe = _disarm_mail_and_generation(monkeypatch)
    seen = _spy(monkeypatch, subscribe, "compute_transit_snapshot")

    assert subscribe._send_welcome_email("a@example.test", "en") is True

    assert len(seen) == 2, f"expected the reading's and the panel's transit, got {len(seen)}"
    _assert_all_pinned(seen, date.today(), "_send_welcome_email")


def test_the_nightly_brief_pins_the_day_it_was_asked_for(monkeypatch):
    """scripts/rashifal_brief.py `build`: pinned to the IST day it is given.

    Driven by calling `build` directly -- it composes the prompt from the same
    builders as the app and makes no provider call, so nothing needs stubbing
    beyond the autouse offline geocode. A date that is NOT today, so a pin that
    silently fell back to now() cannot pass by coincidence.
    """
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "scripts" / "rashifal_brief.py"
    spec = importlib.util.spec_from_file_location("rashifal_brief_under_test", path)
    brief = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(brief)

    transits = _spy(monkeypatch, brief, "compute_transit_snapshot")
    panchangs = _spy(monkeypatch, brief, "compute_panchang")
    day = date(2026, 3, 4)

    brief.build("en", day.isoformat(), "aries")

    _assert_all_pinned(transits, day, "rashifal_brief transit")
    _assert_all_pinned(panchangs, day, "rashifal_brief panchang")


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
