"""#513 -- the daily rashifal email must not read as unchanged day to day.

#516 fixed the generation side (the shape and opening hint rotate by date). Two
pieces were left, and each is pinned here:

  * the SUBJECT carried no date: `Today's Rashifal -- Shubh Bhagya`, identical on
    every send, so a mail client threaded the series into one conversation;
  * nothing compared one day's opening with the last, so the defect could return
    unseen. `opening_repeats` is that comparison and `publish_rashifal` reports it.

Nothing here sends mail or reaches a network: the blast fixtures stub both.
"""
from __future__ import annotations

import importlib.util
import pathlib
from datetime import date, timedelta

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The two real Aries openings from the issue, 2026-10-22 and 10-23.
_DAY1 = ("You stride forward with a burst of confidence, as if ready to lift a "
         "heavy weight overhead. At work, the pace picks up.")
_DAY2 = ("You stride out of bed with a clenched fist, ready to set the day in "
         "motion. At work, the spark of initiative shows.")
_UNRELATED = "A quiet settling arrives with the morning. Work asks for patience."


def test_the_subject_names_the_day_in_both_languages():
    from astro_ai.routes.subscribe import daily_rashifal_subject
    d = date(2026, 11, 7)
    en, hi = daily_rashifal_subject("en", d), daily_rashifal_subject("hi", d)
    assert "Saturday, 7 November 2026" in en, en
    assert "शनिवार, 7 नवंबर 2026" in hi, hi
    assert en.startswith("Today's Rashifal") and hi.startswith("आज का राशिफल")


def test_seven_consecutive_sends_have_seven_distinct_subjects():
    """The issue's own metric: distinct subjects across 7 daily sends == 7."""
    from astro_ai.routes.subscribe import daily_rashifal_subject
    start = date(2026, 11, 1)
    for lang in ("en", "hi"):
        subjects = {daily_rashifal_subject(lang, start + timedelta(days=i)) for i in range(7)}
        assert len(subjects) == 7, (lang, subjects)


def test_the_blast_sends_the_dated_subject(client, monkeypatch):
    """The helper is inert unless the handler uses it."""
    from astro_ai.main import app
    from astro_ai.routes import subscribe
    from astro_ai.routes.deps import require_admin

    sections = "\n\n".join(f"## {r}\n" + "A steady day for measured work. " * 40
                           for r in ("Aries / Mesha", "Taurus / Vrishabha"))
    monkeypatch.setattr(subscribe, "_daily_rashifal_text", lambda **k: sections)
    monkeypatch.setattr(subscribe, "compute_chart", lambda *a, **k: {"stub": "chart"})
    monkeypatch.setattr(subscribe, "compute_transit_snapshot", lambda chart, when=None: {})
    subs = [{"email": "a@x.test", "lang": "en", "rashi": "all", "city": "Delhi"},
            {"email": "b@x.test", "lang": "hi", "rashi": "all", "city": "Delhi"}]
    monkeypatch.setattr(subscribe.subscribers, "list_subscribers", lambda: subs)
    got: dict[str, str] = {}
    monkeypatch.setattr(subscribe.email_sender, "send",
                        lambda email, subject, **k: got.setdefault(email, subject) and True)
    app.dependency_overrides[require_admin] = lambda: None
    try:
        r = client.post("/admin/send-daily-rashifal")
    finally:
        app.dependency_overrides.pop(require_admin, None)
    assert r.status_code == 200, r.text
    today = subscribe.reading_today()
    assert subscribe._pretty_date(today.isoformat(), "en") in got["a@x.test"], got
    assert subscribe._pretty_date(today.isoformat(), "hi") in got["b@x.test"], got


def test_consecutive_openings_that_share_a_content_word_are_reported():
    from astro_ai.rashifal_quality import opening_repeats
    assert opening_repeats(_DAY1, _DAY2) == ["ready", "stride"]


def test_unrelated_openings_report_nothing():
    from astro_ai.rashifal_quality import opening_repeats
    assert opening_repeats(_DAY1, _UNRELATED) == []


def test_only_the_first_sentence_counts():
    """`At work` opens the second sentence of both; the check is about the
    sentence the reader meets first, so that must not be reported."""
    from astro_ai.rashifal_quality import opening_repeats
    assert "work" not in opening_repeats(_DAY1, _DAY2)


def test_an_empty_reading_disables_the_check_rather_than_failing_it():
    from astro_ai.rashifal_quality import opening_repeats
    assert opening_repeats("", _DAY1) == [] == opening_repeats(_DAY1, "")


def _publish_module():
    spec = importlib.util.spec_from_file_location(
        "publish_rashifal_under_test", ROOT / "scripts/publish_rashifal.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _doc(aries: str, taurus: str) -> str:
    return f"## Aries / Mesha\n\n{aries}\n\n## Taurus / Vrishabha\n\n{taurus}\n"


def test_publish_names_the_rashi_whose_opening_repeated():
    notes = _publish_module().opening_notes(_doc(_DAY2, _UNRELATED), _doc(_DAY1, _DAY1))
    assert notes == ["aries: opening shares ready, stride with yesterday's"], notes


def test_publish_compares_a_rashi_with_its_own_yesterday_only():
    """Taurus today opens like Aries yesterday; that is a different rashi and
    is not a cross-day repeat."""
    notes = _publish_module().opening_notes(_doc(_UNRELATED, _DAY2), _doc(_DAY1, _UNRELATED))
    assert notes == [], notes


def test_publish_with_no_yesterday_reports_nothing():
    assert _publish_module().opening_notes(_doc(_DAY2, _DAY2), "") == []
