"""/admin/ops can show ONE past day (owner, 2026-11-10: "build date picker if
that can be done easily without increasing any storage").

It reads the per-day blobs llm_stats and events already keep -- no new blob,
no new write. These tests pin both halves: the day is honoured end to end, and
the only thing `end` changes is WHICH existing days are read.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest

from astro_ai import events, llm_stats, ops_data


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


TODAY = date.today()


# --- which days are read ------------------------------------------------------

def _spy(monkeypatch, mod):
    seen: list[date] = []
    real = mod._read_day

    def spy(d):
        seen.append(d)
        return real(d)
    monkeypatch.setattr(mod, "_read_day", spy)
    return seen


def test_llm_stats_reads_the_picked_day_and_nothing_else(monkeypatch):
    seen = _spy(monkeypatch, llm_stats)
    day = TODAY - timedelta(days=4)
    llm_stats.usage_summary(1, end=day)
    llm_stats.range_summary(1, end=day)
    assert set(seen) == {day}


def test_events_reads_the_picked_day_and_nothing_else(monkeypatch):
    seen = _spy(monkeypatch, events)
    day = TODAY - timedelta(days=4)
    events.error_breakdown(days=1, end=day)
    assert set(seen) == {day}


def test_no_end_still_means_today(monkeypatch):
    seen = _spy(monkeypatch, llm_stats)
    llm_stats.usage_summary(1)
    assert seen == [TODAY]


def test_picking_a_day_writes_nothing(monkeypatch):
    from astro_ai import storage

    def boom(*a, **k):
        raise AssertionError("the day picker must not write to storage")
    for name in ("put", "put_json", "update_json"):
        monkeypatch.setattr(storage, name, boom)
    ops_data.snapshot(app_day=(TODAY - timedelta(days=3)).isoformat())


# --- what the page accepts ----------------------------------------------------

@pytest.mark.parametrize("value", ["", "abc", "2026-13-01", "2026-11-10; drop",
                                   (TODAY + timedelta(days=1)).isoformat(),
                                   (TODAY - timedelta(days=ops_data.PICK_DAYS)).isoformat()])
def test_a_bad_or_out_of_range_day_is_refused_not_clamped(value):
    assert ops_data.pick_day(value) is None


def test_the_oldest_kept_day_and_today_are_accepted():
    oldest = TODAY - timedelta(days=ops_data.PICK_DAYS - 1)
    assert ops_data.pick_day(oldest.isoformat()) == oldest
    assert ops_data.pick_day(TODAY.isoformat()) == TODAY


def test_a_picked_day_is_one_day_with_its_own_label():
    day = TODAY - timedelta(days=4)
    app = ops_data.snapshot(app_day=day.isoformat())["app"]
    assert app["days"] == 1 and app["day"] == day.isoformat()
    assert app["range"]["label"] == f"{day.isoformat()} UTC, the whole day"


def test_a_refused_day_falls_back_to_the_window():
    app = ops_data.snapshot(app_days=30, app_day="2001-01-01")["app"]
    assert app["days"] == 30 and app["day"] == ""


def test_a_picked_day_and_the_1_day_window_do_not_share_a_cache_slot():
    a = ops_data._app_view(1)
    b = ops_data._app_view(1, TODAY - timedelta(days=2))
    assert a is not b and b["day"] == (TODAY - timedelta(days=2)).isoformat()


# --- the page -----------------------------------------------------------------

def _page(q: str):
    from fastapi.testclient import TestClient
    from astro_ai.main import app
    from astro_ai.routes import deps
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    return TestClient(app).get("/admin/ops" + q, auth=("admin", pw))


def test_the_page_renders_the_picker_bounded_to_kept_days():
    day = TODAY - timedelta(days=4)
    r = _page(f"?day={day.isoformat()}")
    assert r.status_code == 200
    html = r.text
    assert f'name="day" value="{day.isoformat()}"' in html
    assert f'min="{(TODAY - timedelta(days=ops_data.PICK_DAYS - 1)).isoformat()}"' in html
    assert f'max="{TODAY.isoformat()}"' in html
    assert 'class="win on"' not in html, "no window chip may claim the view when a day is picked"
    assert f"{day.isoformat()} UTC, the whole day" in html


def test_a_mistyped_day_shows_the_page_not_a_422():
    assert _page("?day=not-a-date").status_code == 200
