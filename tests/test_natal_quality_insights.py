"""#972 -- the natal verdict as a weekly pass rate on /admin/insights (#327, #967 item 3).

`routes/kundli.py` writes `q_ok` / `q_banned` on each fresh `form_kundli` event and
nothing read them. These tests pin what the rate is allowed to count: a Hindi reading
is never rated (its bans are Latin words, so it would read better than it is), an event
without `q_ok` is `unchecked` rather than a pass or a fail, and nothing but counts and
kind names can reach the block -- the event carries no prose, and a planted term in
`q_banned` must not be rendered as one.
"""
from __future__ import annotations

import base64

from astro_ai import profiling

# 2026-11-09 is a Monday (ISO week 46); 2026-11-02 is week 45.
W46, W45 = "2026-11-10T08:00:00+00:00", "2026-11-03T08:00:00+00:00"


def _ev(ts, ok, *, model="gpt-oss-120b", lang="en", banned=None, **extra):
    data = {"lang": lang, "model": model, **extra}
    if ok is not None:
        data.update({"q_ok": ok, "q_sections": 7, "q_banned": banned or {}, "q_words": 1000})
    return {"type": "form_kundli", "ts": ts, "data": data}


def test_pass_rate_is_per_week_and_per_model():
    out = profiling.natal_quality([
        _ev(W46, True), _ev(W46, True), _ev(W46, False, banned={"planet": 2}),
        _ev(W46, True, model="other"), _ev(W45, False, banned={"sign": 1, "planet": 1}),
    ])
    rows = {(r["week"], r["model"]): (r["passed"], r["checked"], r["pass_pct"])
            for r in out["rows"]}
    assert rows == {
        ("2026-W46", "gpt-oss-120b"): (2, 3, 66.7),
        ("2026-W46", "other"): (1, 1, 100.0),
        ("2026-W45", "gpt-oss-120b"): (0, 1, 0.0),
    }
    assert (out["passed"], out["checked"], out["pass_pct"]) == (3, 5, 60.0)
    assert out["banned_kinds"] == [("planet", 3), ("sign", 1)]
    assert [r["week"] for r in out["rows"]][0] == "2026-W46", "newest week first"


def test_hindi_is_excluded_from_every_rate_and_counted_aside():
    out = profiling.natal_quality([_ev(W46, True), _ev(W46, True, lang="hi"),
                                   _ev(W46, False, lang="hi", banned={"planet": 9})])
    assert (out["checked"], out["hindi_excluded"]) == (1, 2)
    assert out["banned_kinds"] == [], "a Hindi event's bans must not enter the English tally"


def test_an_event_with_no_verdict_is_unchecked_not_a_pass_or_a_fail():
    out = profiling.natal_quality([_ev(W46, None), _ev(W46, None), _ev(W46, True)])
    assert (out["checked"], out["passed"], out["unchecked"]) == (1, 1, 2)


def test_only_a_literal_true_is_a_pass():
    out = profiling.natal_quality([_ev(W46, "yes"), _ev(W46, 1), _ev(W46, True)])
    assert (out["passed"], out["checked"]) == (1, 3)


def test_missing_model_and_unreadable_ts_degrade_instead_of_raising():
    out = profiling.natal_quality([
        {"type": "form_kundli", "ts": "garbage", "data": {"q_ok": True, "lang": "en"}},
        {"type": "form_kundli", "data": {"q_ok": True, "q_banned": {"planet": "x"}}},
    ])
    assert [(r["week"], r["model"]) for r in out["rows"]] == [("unknown", "unknown")]
    assert out["banned_kinds"] == [], "a non-integer count is ignored, not summed"


def test_an_unreadable_week_sorts_last_not_first():
    out = profiling.natal_quality([
        {"type": "form_kundli", "ts": "garbage", "data": {"q_ok": True}},
        _ev(W45, True), _ev(W46, True)])
    assert [r["week"] for r in out["rows"]] == ["2026-W46", "2026-W45", "unknown"]


def test_a_malformed_q_banned_is_ignored_and_never_raises():
    out = profiling.natal_quality([
        _ev(W46, False, banned=["planet"]), _ev(W46, False, banned={"sign": True}),
        _ev(W46, False, banned={"sign": -3, "planet": 2})])
    assert out["checked"] == 3 and out["banned_kinds"] == [("planet", 2)]


def test_no_events_gives_zero_rate_not_a_division_error():
    out = profiling.natal_quality([])
    assert out["rows"] == [] and out["pass_pct"] == 0.0


def test_audience_summary_carries_the_block(monkeypatch):
    monkeypatch.setattr(profiling.storage, "get_json", lambda k: None)
    monkeypatch.setattr(profiling.storage, "put_json", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(
        profiling.events, "recent",
        lambda types, days, limit: [_ev(W46, True)] if types == ["form_kundli"] else [])
    out = profiling.audience_summary(days=30, force_refresh=True)
    assert out["natal_quality"]["checked"] == 1


# ─── the rendered page ────────────────────────────────────────────────────


def _admin(client_):
    token = base64.b64encode(b"admin:bhagya-dev-only-CHANGE-ME").decode()
    return {"Authorization": f"Basic {token}"}


def _page(client, monkeypatch, summary_extra):
    base = {
        "generated_at": "2026-11-13T00:00:00+00:00", "days": 30,
        "totals": {"form_kundli": 0, "form_ask": 0, "form_matching": 0, "all": 0},
        "age_bands": [], "top_cities": [], "languages": [], "ask_categories": [],
        "ask_contexts": [], "ask_cache_hit_pct": 0.0,
        "funnel": {"unique_emails": 0, "kundli_only": 0, "kundli_plus_ask": 0,
                   "kundli_plus_matching": 0, "power_users": 0},
    }
    monkeypatch.setattr(profiling, "audience_summary", lambda **k: {**base, **summary_extra})
    r = client.get("/admin/insights", headers=_admin(client))
    assert r.status_code == 200, r.status_code
    return r.text


def test_page_renders_the_rate_the_exclusions_and_the_kinds(client, monkeypatch):
    nq = profiling.natal_quality([
        _ev(W46, True), _ev(W46, False, banned={"planet": 2}),
        _ev(W46, True, lang="hi"), _ev(W46, None)])
    html = _page(client, monkeypatch, {"natal_quality": nq})
    assert "Natal reading quality" in html
    assert "2026-W46" in html and "1 of 2" in html and "50.0%" in html
    assert "planet 2" in html
    assert "1 Hindi readings" in html and "1 Kundli events with no verdict" in html


def test_page_survives_a_summary_cached_before_this_block_existed(client, monkeypatch):
    html = _page(client, monkeypatch, {})
    assert "Natal reading quality" in html
    assert "No checked natal readings in this window" in html


def test_page_survives_an_empty_block(client, monkeypatch):
    html = _page(client, monkeypatch, {"natal_quality": profiling.natal_quality([])})
    assert "No checked natal readings in this window" in html
