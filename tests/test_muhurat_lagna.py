"""#1026: Vivah lagna windows (Rao's guideline) in the muhurat finder, step 1: the maths.

What is pinned here, and why each is written out rather than derived from the module:
the benefic-owned lagna signs, the Moon-waxing rule for Cancer, the Mercury "joined by a malefic"
rule for Gemini/Virgo, the clean-7th rule (all nine bodies, nodes included), the window edges
against an independent 1-minute scan, the splitting at a lagna change, inward rounding, the gate
(Vivah, a row the page calls auspicious, ordinary daylight), the Rahu Kaal note, that the day
rating cannot move, the cache key, the wording the astro-auditor ruled, and a cost tripwire.

The sets below come from the auditor's ruling (knowledge/grahas.md section 2 and 12.5,
vedic_reference.md section 4.7), never from `muhurat_lagna`: a test that read the module's own
table would pass forever. No network (the place is stubbed), no LLM.
Mutation rows: scripts/mutations/2026_11_24_1026_muhurat_lagna.py.
"""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
import time
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
import swisseph as swe

from astro_ai import chart, muhurat
from astro_ai import muhurat_lagna as ml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "astro_ai"
DELHI = (28.61, 77.21, "Asia/Kolkata")
TROMSO = (69.6492, 18.9553, "Europe/Oslo")
IST = ZoneInfo("Asia/Kolkata")
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NINE = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


@pytest.fixture(autouse=True)
def _delhi(monkeypatch):
    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)


def _sky(**over) -> dict[str, int]:
    """A quiet sky: Mercury alone in Capricorn, nobody in Taurus's or Gemini's 7th."""
    s = dict(Sun=0, Moon=0, Mars=0, Mercury=9, Jupiter=4, Venus=4, Saturn=10, Rahu=10, Ketu=4)
    s.update(over)
    return s


def _row(d: date, rating: str = "good", sunrise: str = "07:00", rahu_kaal: str = "") -> SimpleNamespace:
    return SimpleNamespace(d=d, rating=rating, sunrise=sunrise, rahu_kaal=rahu_kaal)


# --- 1-3: which lagna signs are benefic-owned -------------------------------------------------

def test_exactly_taurus_libra_sagittarius_pisces_are_always_benefic():
    always = {"Taurus", "Libra", "Sagittarius", "Pisces"}
    for i, name in enumerate(SIGNS):
        if name in always:
            # waning Moon, Mercury sitting with every malefic: still benefic-owned
            assert ml.is_benefic_lagna(i, _sky(Mercury=0), 200.0), name
    for name in ("Aries", "Leo", "Scorpio", "Capricorn", "Aquarius"):
        assert not ml.is_benefic_lagna(SIGNS.index(name), _sky(), 90.0), name


@pytest.mark.parametrize("elongation, ok", [(10, True), (90, True), (179.9, True),
                                            (180, False), (200, False), (359, False)])
def test_cancer_needs_the_moon_waxing_at_that_moment(elongation, ok):
    assert ml.is_benefic_lagna(SIGNS.index("Cancer"), _sky(), elongation) is ok


@pytest.mark.parametrize("lagna", ["Gemini", "Virgo"])
def test_mercury_ruled_signs_need_mercury_unjoined_by_a_malefic(lagna):
    i = SIGNS.index(lagna)
    assert ml.is_benefic_lagna(i, _sky(), 90.0)                       # alone
    assert ml.is_benefic_lagna(i, _sky(Venus=9), 90.0)                # with Venus
    assert ml.is_benefic_lagna(i, _sky(Jupiter=9), 90.0)              # with Jupiter
    assert ml.is_benefic_lagna(i, _sky(Moon=9), 90.0)                 # with the waxing Moon
    for malefic in ("Sun", "Mars", "Saturn", "Rahu", "Ketu"):
        assert not ml.is_benefic_lagna(i, _sky(**{malefic: 9}), 90.0), malefic
        # the same malefic in the NEXT sign does not matter
        assert ml.is_benefic_lagna(i, _sky(**{malefic: 10}), 90.0), malefic
    assert not ml.is_benefic_lagna(i, _sky(Moon=9), 200.0)            # with the waning Moon
    assert ml.is_benefic_lagna(i, _sky(Moon=10), 200.0)               # waning Moon elsewhere


# --- 4: the 7th house is clean only if all nine bodies are elsewhere ---------------------------

@pytest.mark.parametrize("body", NINE)
def test_any_one_of_the_nine_in_the_7th_sign_makes_it_not_clean(body):
    for lagna in range(12):
        away = (lagna + 3) % 12
        crowd = {b: away for b in NINE}
        assert ml.seventh_clean(lagna, crowd), (lagna, "empty 7th")
        crowd[body] = (lagna + 6) % 12
        assert not ml.seventh_clean(lagna, crowd), (body, lagna)
        # the 6th and 8th signs are not the 7th
        for near in ((lagna + 5) % 12, (lagna + 7) % 12):
            crowd[body] = near
            assert ml.seventh_clean(lagna, crowd), (body, lagna, near)


def test_ketu_is_exactly_opposite_rahu_and_rahu_is_the_true_node():
    assert ml._BODIES["Rahu"] == swe.TRUE_NODE
    # 2461370.5: the true node is at 299.93 and the mean node at 300.51, a sign apart, so a
    # swap to the mean node changes the answer, not just a decimal.
    jd = 2461370.5
    signs, _ = ml._sky(jd)
    true_lon = chart._sid_calc_ut(jd, swe.TRUE_NODE)[0][0]
    assert signs["Rahu"] == int(true_lon // 30) == 9
    for j in (jd, jd + 100.25, jd + 777.5):
        s, _ = ml._sky(j)
        assert s["Ketu"] == (s["Rahu"] + 6) % 12


# --- 5: window edges against an independent 1-minute scan ------------------------------------

def _truth(jd: float, lat: float, lon: float) -> int | None:
    """The ruling, written out a second time: the qualifying lagna sign at an instant, else None."""
    lagna = int(chart._sid_houses(jd, lat, lon)[1][0] // 30) % 12
    longs = {n: chart._sid_calc_ut(jd, i)[0][0] % 360 for n, i in chart.PLANETS}
    longs["Ketu"] = (longs["Rahu"] + 180) % 360
    sign = {n: int(v // 30) for n, v in longs.items()}
    waxing = (longs["Moon"] - longs["Sun"]) % 360 < 180
    name = SIGNS[lagna]
    if name in ("Taurus", "Libra", "Sagittarius", "Pisces"):
        ok = True
    elif name == "Cancer":
        ok = waxing
    elif name in ("Gemini", "Virgo"):
        malefics = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"} | (set() if waxing else {"Moon"})
        ok = not any(sign[m] == sign["Mercury"] for m in malefics)
    else:
        ok = False
    if ok and any(s == (lagna + 6) % 12 for s in sign.values()):
        ok = False
    return lagna if ok else None


# 2026-11-25 two windows; 2027-01-26 none; 2027-01-28 Gemini; 2027-06-03 Virgo; 2027-10-20 Libra;
# 2027-04-05, 2027-05-20 and 2027-09-16: a body changes sign INSIDE a benefic lagna sign, so the
# slow edge (not the lagna edge) ends or starts the window.
ORACLE_DATES = [date(2026, 11, 25), date(2027, 1, 26), date(2027, 1, 28), date(2027, 6, 3),
                date(2027, 10, 20), date(2027, 4, 5), date(2027, 5, 20), date(2027, 9, 16)]


@pytest.mark.parametrize("day", ORACLE_DATES)
def test_windows_agree_with_a_one_minute_scan_at_every_edge(day):
    lat, lon, tz_name = DELHI
    wins = ml._windows_for(day, lat, lon, tz_name)
    sr, ss = chart._sunrise_sunset(day, lat, lon, IST)
    first = sr.replace(second=0, microsecond=0) + timedelta(minutes=1)
    scan: dict[datetime, int | None] = {}
    m = first
    while m <= ss:
        scan[m] = _truth(chart.julian_day_utc(m), lat, lon)
        m += timedelta(minutes=1)
    one = timedelta(minutes=1)
    covered: set[datetime] = set()
    for w in wins:
        assert w.start < w.end
        m = w.start
        while m <= w.end:
            assert scan[m] == w.sign, (day, "minute inside a window does not qualify", m)
            covered.add(m)
            m += one
        for outside in (w.start - one, w.end + one):
            if outside in scan:
                assert scan[outside] != w.sign, (day, "minute beyond an edge still qualifies", outside)
    for m, sign in scan.items():
        if sign is not None and m not in covered:
            # only a span too short to hold two whole minutes may go unreported
            assert scan.get(m - one) != sign and scan.get(m + one) != sign, (day, m)


def test_the_oracle_dates_cover_a_window_a_none_and_a_slow_edge():
    lat, lon, tz_name = DELHI
    by_day = {d: ml._windows_for(d, lat, lon, tz_name) for d in ORACLE_DATES}
    assert len(by_day[date(2026, 11, 25)]) == 2
    assert by_day[date(2027, 1, 26)] == ()
    signs = {w.sign for ws in by_day.values() for w in ws}
    assert {SIGNS.index("Gemini"), SIGNS.index("Virgo"), SIGNS.index("Libra")} <= signs


# --- 6: a lagna change splits a window; rounding is inward -------------------------------------

def _fake_lagna(monkeypatch, day: date, spans: list[tuple[float, float, int]]):
    """Replace the ascendant with scripted signs: (seconds after sunrise, until, sign), else Aries.
    The sky is the quiet one, so only the lagna decides."""
    sr, _ = chart._sunrise_sunset(day, *DELHI[:2], IST)
    jd0 = chart.julian_day_utc(sr.astimezone(timezone.utc))

    def lagna(jd, lat, lon):
        t = (jd - jd0) * 86400.0
        for a, b, sign in spans:
            if a <= t < b:
                return sign
        return 0

    monkeypatch.setattr(ml, "_lagna_sign", lagna)
    monkeypatch.setattr(ml, "_sky", lambda jd: (_sky(), 90.0))
    return sr


def test_two_adjacent_qualifying_signs_are_two_windows(monkeypatch):
    day = date(2026, 11, 25)
    sr = _fake_lagna(monkeypatch, day, [(3600.0, 7200.0, 1), (7200.0, 10800.0, 2)])
    wins = ml._windows_for.__wrapped__(day, *DELHI)
    assert [(w.sign, w.start, w.end) for w in wins] == [
        (1, _ceil(sr + timedelta(hours=1)), _floor(sr + timedelta(hours=2))),
        (2, _ceil(sr + timedelta(hours=2)), _floor(sr + timedelta(hours=3)))]


def _ceil(dt: datetime) -> datetime:
    f = dt.replace(second=0, microsecond=0)
    return f if f == dt else f + timedelta(minutes=1)


def _floor(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def test_rounding_is_inward_to_the_whole_minute(monkeypatch):
    day = date(2026, 11, 25)
    sr, _ = chart._sunrise_sunset(day, *DELHI[:2], IST)
    m0 = _ceil(sr + timedelta(hours=1))
    m1 = m0 + timedelta(hours=2)
    a = (m0 + timedelta(seconds=20) - sr).total_seconds()     # starts 20 s after a minute mark
    b = (m1 + timedelta(seconds=40) - sr).total_seconds()     # ends 40 s after a minute mark
    _fake_lagna(monkeypatch, day, [(a, b, 1)])
    (w,) = ml._windows_for.__wrapped__(day, *DELHI)
    assert w.start == m0 + timedelta(minutes=1)
    assert w.end == m1
    # a span with no whole minute inside it vanishes rather than rounding outward
    c = (m0 + timedelta(seconds=10) - sr).total_seconds()
    _fake_lagna(monkeypatch, day, [(c, c + 30.0, 1)])
    assert ml._windows_for.__wrapped__(day, *DELHI) == ()


# --- 7: the gate -------------------------------------------------------------------------------

@pytest.mark.parametrize("event", ["griha_pravesh", "namkaran", "business", "vidyarambh"])
def test_other_events_get_no_view(event):
    assert ml.lagna_view(_row(date(2026, 11, 25)), event, "Delhi") is None


@pytest.mark.parametrize("rating", ["caution", "avoid"])
def test_caution_and_avoid_rows_get_no_view(rating):
    assert ml.lagna_view(_row(date(2026, 11, 25), rating=rating), "vivah", "Delhi") is None


@pytest.mark.parametrize("rating", ["excellent", "good", "acceptable"])
def test_auspicious_rated_rows_get_a_view(rating):
    v = ml.lagna_view(_row(date(2026, 11, 25), rating=rating), "vivah", "Delhi")
    assert v is not None and v.windows


def test_no_sunrise_no_view():
    assert ml.lagna_view(_row(date(2026, 11, 25), sunrise=""), "vivah", "Delhi") is None


def test_tromso_on_the_227_date_renders_nothing_not_a_none_met_claim(monkeypatch):
    monkeypatch.setattr(chart, "geocode_place", lambda place: TROMSO)
    # 2026-05-17: sunset <= sunrise at Tromso (#227). A non-empty sunrise gets past the gate on
    # purpose, so this is the computation's own refusal, not the gate's.
    assert ml.lagna_view(_row(date(2026, 5, 17), sunrise="01:14"), "vivah", "Tromso") is None


def test_unknown_city_and_any_computation_failure_render_nothing_not_an_empty_list(monkeypatch):
    def boom(place):
        raise chart.ChartError("no such place")
    monkeypatch.setattr(chart, "geocode_place", boom)
    assert ml.lagna_view(_row(date(2026, 11, 25)), "vivah", "Nowhereville") is None

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)

    def explode(*a, **k):
        raise RuntimeError("ephemeris went away")
    monkeypatch.setattr(ml, "_windows_for", explode)
    assert ml.lagna_view(_row(date(2026, 11, 25)), "vivah", "Delhi") is None


def test_a_date_with_no_window_says_so_with_an_empty_tuple_and_the_ruled_sentence():
    v = ml.lagna_view(_row(date(2027, 1, 26)), "vivah", "Delhi")
    assert v is not None and v.windows == ()
    assert v.none_text == ("No lagna window met this guideline on this day. This does not make "
                           "the day unsuitable; the day rating is unchanged.")


def test_legend_needs_a_vivah_page_with_at_least_one_eligible_row():
    rows = [_row(date(2026, 11, 25)), _row(date(2026, 11, 26), rating="avoid")]
    assert ml.legend(rows, "vivah") is not None
    assert ml.legend(rows, "griha_pravesh") is None
    assert ml.legend([rows[1]], "vivah") is None
    assert ml.legend([], "vivah") is None


# --- 8: Rahu Kaal is a note, never a filter ----------------------------------------------------

def test_a_window_overlapping_rahu_kaal_carries_a_note_with_the_rows_own_minutes():
    # 2026-11-26 Delhi: Pisces window 13:44-15:08; the row printed Rahu Kaal 13:27-14:46.
    day = date(2026, 11, 26)
    with_rk = ml.lagna_view(_row(day, rahu_kaal="13:27-14:46"), "vivah", "Delhi")
    without = ml.lagna_view(_row(day, rahu_kaal=""), "vivah", "Delhi")
    assert [w.rahu_note for w in with_rk.windows] == ["overlaps Rahu Kaal 13:27-14:46"]
    assert [w.rahu_note for w in without.windows] == [""]
    # the window itself is the same with and without: a note, not a filter or a rank
    assert [replace(w, rahu_note="") for w in with_rk.windows] == list(without.windows)
    # the en dash the dataclass comment mentions reads the same
    dashed = ml.lagna_view(_row(day, rahu_kaal="13:27–14:46"), "vivah", "Delhi")
    assert dashed.windows == with_rk.windows


def test_a_window_that_only_touches_rahu_kaal_at_a_minute_mark_gets_no_note():
    day = date(2026, 11, 26)
    (w,) = ml.lagna_view(_row(day), "vivah", "Delhi").windows
    assert w.end == "15:08" and w.start == "13:44"
    after = ml.lagna_view(_row(day, rahu_kaal="15:08-16:30"), "vivah", "Delhi")
    before = ml.lagna_view(_row(day, rahu_kaal="12:00-13:44"), "vivah", "Delhi")
    assert after.windows[0].rahu_note == "" and before.windows[0].rahu_note == ""


@pytest.mark.parametrize("junk", ["", "garbage", "13:27", "25:99 to 26:00", None])
def test_an_unparseable_rahu_kaal_gives_no_note_and_no_exception(junk):
    v = ml.lagna_view(_row(date(2026, 11, 26), rahu_kaal=junk), "vivah", "Delhi")
    assert v is not None and len(v.windows) == 1 and v.windows[0].rahu_note == ""


def test_window_strings_name_the_sign_and_its_qualifier():
    v = ml.lagna_view(_row(date(2026, 11, 25)), "vivah", "Delhi")
    assert [(w.start, w.end, w.sign, w.qualifier) for w in v.windows] == [
        ("08:35", "10:38", "Sagittarius", ""), ("13:48", "15:12", "Pisces", "")]
    gem = ml.lagna_view(_row(date(2027, 1, 28)), "vivah", "Delhi")
    assert {(w.sign, w.qualifier) for w in gem.windows} >= {("Gemini", "Mercury not joined by a malefic")}
    assert ml._QUALIFIER == {3: "Moon waxing", 2: "Mercury not joined by a malefic",
                             5: "Mercury not joined by a malefic"}


# --- 9: the day rating cannot move -------------------------------------------------------------

def test_the_day_rating_is_unchanged_by_asking_for_windows():
    def snap():
        return [(c.d, c.rating, c.reason, c.flags, c.rahu_kaal, c.sunrise)
                for c in muhurat.find_candidates("vivah", "Delhi", date(2026, 11, 24), 45)]
    before = snap()
    rows = muhurat.find_candidates("vivah", "Delhi", date(2026, 11, 24), 45)
    shown = [c for c in rows if c.rating in muhurat.AUSPICIOUS_RATINGS]
    assert shown
    for c in rows:
        ml.lagna_view(c, "vivah", "Delhi")
    ml.legend(rows, "vivah")
    assert snap() == before


@pytest.mark.parametrize("name", ["muhurat.py", "muhurat_factors.py"])
def test_the_scorer_does_not_import_the_lagna_module(name):
    tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                else [node.module or ""] + [a.name for a in node.names]
                if isinstance(node, ast.ImportFrom) else [])
        assert not any("muhurat_lagna" in m for m in mods), (name, node.lineno)


# --- 10: the cache -----------------------------------------------------------------------------

def test_windows_are_memoised_on_date_and_place_and_a_new_longitude_is_a_miss(monkeypatch):
    ml._windows_for.cache_clear()
    row = _row(date(2026, 11, 25))
    a = ml.lagna_view(row, "vivah", "Delhi")
    assert ml._windows_for.cache_info().misses == 1
    assert ml.lagna_view(row, "vivah", "Delhi") == a
    info = ml._windows_for.cache_info()
    assert (info.hits, info.misses) == (1, 1)
    monkeypatch.setattr(chart, "geocode_place", lambda place: (28.61, 72.0, "Asia/Kolkata"))
    b = ml.lagna_view(row, "vivah", "Elsewhere")
    assert ml._windows_for.cache_info().misses == 2
    assert b.windows != a.windows        # 5 degrees of longitude is about 20 minutes of lagna


# --- 11: the wording ---------------------------------------------------------------------------

def test_the_ruled_wording_is_verbatim():
    assert ml.HEADING == "Lagna windows (Rao's guideline)"
    assert ml.CAVEAT == ("These are guidelines, not final recommendations. Planetary strength "
                         "matters more than following these thumb-rules.")
    assert ml.UNCHANGED == "The day rating is unchanged."
    assert ml.NONE_TEXT == ("No lagna window met this guideline on this day. This does not make "
                            "the day unsuitable; the day rating is unchanged.")
    assert ml.BENEFIC_DISCLOSURE == ("Benefic follows Rao's natural benefics: Jupiter, Venus, the "
                                     "waxing Moon, and Mercury unless joined by malefics.")
    v = ml.lagna_view(_row(date(2026, 11, 25)), "vivah", "Delhi")
    lg = ml.legend([_row(date(2026, 11, 25))], "vivah")
    assert (v.heading, v.caveat, v.unchanged) == (ml.HEADING, ml.CAVEAT, ml.UNCHANGED)
    assert (lg.disclosure, lg.caveat, lg.unchanged) == (ml.BENEFIC_DISCLOSURE, ml.CAVEAT, ml.UNCHANGED)


def test_the_legend_states_our_reading_of_clean_and_that_aspects_are_not_considered():
    text = " ".join(ml.legend([_row(date(2026, 11, 25))], "vivah").notes)
    assert "none of the nine grahas, Rahu and Ketu included, is in that sign" in text
    assert "That is our reading" in text
    assert "aspects are not considered" in text and "do not say" in text
    assert "true node" in text and "same sign" in text and "Lahiri" in text


_PROSE = [ml.HEADING, ml.CAVEAT, ml.UNCHANGED, ml.NONE_TEXT, ml.BENEFIC_DISCLOSURE,
          *ml.LEGEND_NOTES, *ml._QUALIFIER.values()]


@pytest.mark.parametrize("text", _PROSE)
def test_user_prose_has_no_claim_word_and_no_book_or_table_reference(text):
    for banned in (r"\bauspicious\b", r"\bsafe\b", r"\brecommended\b", r"\bVivah muhurat\b"):
        assert not re.search(banned, text, re.I), (banned, text)
    for token in ("Table", "Chapter", "§", "Brihat", "Chintamani", "BPHS", "Parashara"):
        assert token not in text, (token, text)


def test_the_module_and_its_partials_name_no_book_the_repo_does_not_hold():
    # verify_rule_citations scans only muhurat.py for these names, so this is what covers the
    # new files. The partials are step 2: scanned once they exist.
    spec = importlib.util.spec_from_file_location(
        "verify_rule_citations", ROOT / "scripts" / "verify_rule_citations.py")
    vrc = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "scripts"))
    spec.loader.exec_module(vrc)
    files = [SRC / "muhurat_lagna.py", *sorted((SRC / "templates").glob("_muhurat_lagna*.html"))]
    assert files[0].exists()
    for f in files:
        text = f.read_text(encoding="utf-8")
        for label, pattern in vrc._MUHURAT_UNHELD:
            assert not re.search(pattern, text, re.I), (f.name, label)


# --- 12: cost tripwire -------------------------------------------------------------------------

def test_cold_windows_stay_cheap():
    # Measured 2026-11-24 at Delhi: about 4 ms a day cold. 50 ms is a tripwire for a regression
    # to a fine-grid scan (26 ms a day measured), not a benchmark.
    lat, lon, tz_name = DELHI
    for day in ORACLE_DATES[:5]:
        ml._windows_for.cache_clear()
        t = time.perf_counter()
        ml._windows_for(day, lat, lon, tz_name)
        assert (time.perf_counter() - t) < 0.05, day
