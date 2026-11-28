"""#1346 + #1354: an Abujha date is a BOOSTER inside `score_event`, applied after the hard
exclusions, never a branch that skips them.

Before this, `find_candidates` returned an `excellent` Abujha row without scoring the day at all,
so 2026-11-21 (Tulsi Vivah, Revati, a Panchak Moon, Dwadashi) was rated excellent for marriage
beside the Panchak rule Raman's Muhurtha records (knowledge/vedic_reference.md 2638-2648). The
astro-auditor's ruling (2026-11-21): the day is lifted with Sarvartha Siddhi semantics
(caution -> good, acceptable/good -> excellent, never lowers) only if it clears every exclusion;
a day that fails one stays in the list as `avoid`, with the exclusion's own flag and reason plus a
sentence saying the finder does not waive that exclusion for an Abujha date. Abujha itself is in
no book this site holds (knowledge/vedic_reference.md 29.14), so the row says "a regional almanac
custom" (#1354: it used to say "universally auspicious" beside a disclosure that said the opposite).

Premises are asserted, never assumed: the 2028-04-27 lift reads the date from `_abujha_days` and
checks the baseline rating the lift starts from. No network: geocoding is stubbed to New Delhi.
Mutation rows: scripts/mutations/2026_11_21_1346_abujha_booster.py.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from astro_ai import chart, muhurat as m

NEW_DELHI = (28.6139, 77.2090, "Asia/Kolkata")
TIER = {"avoid": 0, "caution": 1, "acceptable": 2, "good": 3, "excellent": 4}
PASS_PREFIX = "Abujha date, {name}: a regional almanac custom this finder includes; no book it holds names it"
AVOID_SUFFIX = ("{name} is listed as an Abujha date, a regional almanac custom; this finder does "
                "not waive this exclusion for it.")
SARVARTHA = ("Sarvartha Siddhi Yoga (universally auspicious)",)
AMRIT = ("Amrit Siddhi (Mars + Ashwini)",)


@pytest.fixture(autouse=True)
def _delhi(monkeypatch):
    # conftest resolves every place to Mumbai; the dates quoted in #1346 are New Delhi's.
    monkeypatch.setattr(chart, "geocode_place", lambda place: NEW_DELHI)


def _score(event, tithi, weekday, nakshatra, **kw):
    return m.score_event(event, m._MuhurtaInstant(tithi, "Shukla"), weekday, nakshatra,
                         False, False, "", "", {}, **kw)


# business, Shukla: each row is (tithi, weekday, nakshatra) -> the rating it holds with no booster.
SOFT_CASES = {
    "caution":    ("Pratipada", "Monday", "Hasta"),
    "acceptable": ("Dashami", "Saturday", "Anuradha"),
    "good":       ("Dashami", "Monday", "Anuradha"),
    "excellent":  ("Dashami", "Sunday", "Anuradha"),
}
LIFTED = {"caution": "good", "acceptable": "excellent", "good": "excellent", "excellent": "excellent"}


@pytest.mark.parametrize("baseline", list(SOFT_CASES))
def test_the_abujha_lift_has_sarvartha_semantics_and_never_lowers(baseline):
    tithi, weekday, nak = SOFT_CASES[baseline]
    base_rating, base_reason, base_flags = _score("business", tithi, weekday, nak)
    assert base_rating == baseline, "premise: the soft score this case starts from"
    rating, reason, flags = _score("business", tithi, weekday, nak, abujha_name="Akshaya Tritiya")
    assert rating == LIFTED[baseline], (baseline, rating)
    assert TIER[rating] >= TIER[base_rating]
    assert flags == base_flags + ("abujha_muhurat",)
    assert reason == PASS_PREFIX.format(name="Akshaya Tritiya") + "; " + base_reason


@pytest.mark.parametrize("baseline", ["caution", "acceptable", "good"])
def test_abujha_is_not_amrit_siddhi_it_does_not_always_lift_to_excellent(baseline):
    tithi, weekday, nak = SOFT_CASES[baseline]
    amrit, _r, _f = _score("business", tithi, weekday, nak, boosters=AMRIT)
    assert amrit == "excellent", "premise: Amrit Siddhi always lifts to excellent"
    assert _score("business", tithi, weekday, nak, abujha_name="Akshaya Tritiya")[0] == LIFTED[baseline]
    assert LIFTED["caution"] == "good"  # the case that tells the two apart


@pytest.mark.parametrize("baseline", ["caution", "acceptable", "good"])
def test_sarvartha_and_abujha_together_lift_once_not_twice(baseline):
    tithi, weekday, nak = SOFT_CASES[baseline]
    only_sarv = _score("business", tithi, weekday, nak, boosters=SARVARTHA)[0]
    both = _score("business", tithi, weekday, nak, boosters=SARVARTHA, abujha_name="Devuthani Ekadashi")
    assert both[0] == only_sarv == LIFTED[baseline], (baseline, both[0], only_sarv)
    assert "sarvartha_siddhi" in both[2] and "abujha_muhurat" in both[2]
    assert both[1].startswith(PASS_PREFIX.format(name="Devuthani Ekadashi") + "; Sarvartha Siddhi")


def test_an_abujha_name_never_reaches_past_an_exclusion_in_score_event():
    # A Panchak day, a Tuesday and an avoid tithi each stay `avoid` with the exclusion's own flag
    # and no Abujha flag: the flag is set only after the exclusions.
    P = m._MuhurtaInstant("Dashami", "Shukla")
    got = m.score_event("vivah", P, "Friday", "Revati", True, False, "", "", {},
                        abujha_name="Tulsi Vivah")
    assert got[0] == "avoid" and got[2] == ("panchak",), got
    got = m.score_event("business", P, "Tuesday", "Anuradha", False, False, "", "", {},
                        abujha_name="Akshaya Tritiya")
    assert got[0] == "avoid" and got[2] == ("avoid_weekday",), got


def _pairs():
    """Every (date, event) an Abujha rule names from the day #1346 was filed to 2033."""
    out = []
    for year in range(2026, 2034):
        for d, entries in sorted(m._abujha_days(year).items()):
            for _name, events in entries:
                for event in events:
                    if d >= date(2026, 11, 20) and (d, event) not in out:
                        out.append((d, event))
    return out


def _row(event, d):
    return m.find_candidates(event, "New Delhi, India", d, 1)[0]


def test_every_abujha_day_event_pair_is_a_booster_after_the_exclusions(monkeypatch):
    pairs = _pairs()
    assert len(pairs) >= 60, f"premise: the rule table names about 85 pairs to 2033, got {len(pairs)}"
    names = {(d, ev): m._abujha_for(d, ev) for d, ev in pairs}
    assert all(names.values())
    real = {(d, ev): _row(ev, d) for d, ev in pairs}
    monkeypatch.setattr(m, "_abujha_for", lambda d, event: "")
    base = {(d, ev): _row(ev, d) for d, ev in pairs}
    failed, passed = 0, 0
    for key in pairs:
        r, b, name = real[key], base[key], names[key]
        if b.rating == "avoid":
            failed += 1
            assert r.rating == "avoid", key
            assert r.flags == b.flags and "abujha_muhurat" not in r.flags, (key, r.flags, b.flags)
            assert r.reason == b.reason.rstrip(" .") + ". " + AVOID_SUFFIX.format(name=name), (key, r.reason)
            assert name in r.reason
        else:
            passed += 1
            assert TIER[r.rating] >= TIER[b.rating], key
            assert r.rating != "excellent" or b.rating in ("acceptable", "good", "excellent"), key
            assert r.flags == b.flags + ("abujha_muhurat",), (key, r.flags, b.flags)
            assert r.reason.startswith(PASS_PREFIX.format(name=name)), (key, r.reason)
        assert "universally auspicious" not in r.reason.replace("Sarvartha Siddhi Yoga (universally auspicious)", "")
    assert failed >= 20 and passed >= 1, (failed, passed)


def test_the_real_lift_akshaya_tritiya_2028_business_acceptable_to_excellent(monkeypatch):
    d = next(day for day, entries in m._abujha_days(2028).items()
             if any(n == "Akshaya Tritiya" and "business" in ev for n, ev in entries))
    # Observe the verdict the same inputs get WITHOUT the Abujha name, through the real scorer.
    seen = []
    real_score = m.score_event

    def observe(*a, **k):
        seen.append(real_score(*a, **{**k, "abujha_name": ""}))
        return real_score(*a, **k)

    monkeypatch.setattr(m, "score_event", observe)
    row = _row("business", d)
    assert [s[0] for s in seen] == ["acceptable"], "premise: the soft score the lift starts from"
    assert row.rating == "excellent", (d, row.rating, row.reason)
    assert row.flags == seen[0][2] + ("abujha_muhurat",)
    assert row.reason == PASS_PREFIX.format(name="Akshaya Tritiya") + "; " + seen[0][1]


def test_the_1346_metric_no_panchak_row_is_excellent_and_2026_11_21_is_avoid():
    rows = m.find_candidates("vivah", "New Delhi, India", date(2026, 11, 21), 90)
    today = next(c for c in rows if c.d == date(2026, 11, 21))
    assert (today.nakshatra, today.tithi) == ("Revati", "Dwadashi"), "premise: the issue's repro day"
    assert today.rating == "avoid" and today.flags == ("panchak",), (today.rating, today.flags)
    assert "Tulsi Vivah" in today.reason and today.reason.endswith(AVOID_SUFFIX.format(name="Tulsi Vivah"))
    assert [c.d for c in rows if "abujha_muhurat" in c.flags and m._is_panchak(c.nakshatra, 3)] == []
    assert [c.d for c in rows if c.rating == "excellent" and "panchak" in c.flags] == []


def test_the_1354_metric_the_abujha_label_no_longer_says_universally_auspicious():
    src = Path(m.__file__).read_text(encoding="utf-8")
    assert "Abujha Muhurat — {abujha_name} (universally auspicious)" not in src
    # the one remaining use of the phrase is the Sarvartha Siddhi booster's own name
    assert src.count("(universally auspicious)") == 1
    assert 'return "Sarvartha Siddhi Yoga (universally auspicious)"' in src
    for c in m.find_candidates("griha_pravesh", "New Delhi, India", date(2026, 11, 20), 2):
        assert "Abujha Muhurat —" not in c.reason and "universally" not in c.reason
