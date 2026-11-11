"""/admin/ops says which days a figure covers, and its type is legible (owner, 2026-11-10).

"this data on ops dashboard is not showing for which duration is this
aggregated data for" and "a lot of data … is not readable properly, possibly
bad font and background". Measured before the change: the selected window chip
was ink on ink (`var(--night)` is not defined on the page), and Marcellus'
old-style digits rendered "109" as "1O9" on the headline tiles.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from astro_ai import ops_data

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()


# window_range() decides "today still filling" by comparing `today` with the REAL
# date.today(), so these two must use the real date: a hard-coded 2026-11-10 passed
# on that day only and turned red at the next UTC midnight (found 2026-11-11, on
# main, while it was red for every PR's gates).
def test_a_week_is_seven_calendar_days_ending_today():
    today = date.today()
    first = today - timedelta(days=6)
    r = ops_data.window_range(7, today=today)
    assert (r["start"], r["end"]) == (first.isoformat(), today.isoformat())
    assert r["short"] == f"{first:%m-%d} → {today:%m-%d}" and "today still filling" in r["label"]


def test_a_finished_week_does_not_say_still_filling():
    r = ops_data.window_range(7, today=date.today() - timedelta(days=1))
    assert "today still filling" not in r["label"]


def test_one_day_says_so_far_not_24_hours():
    today = date.today()
    r = ops_data.window_range(1, today=today)
    assert r["start"] == r["end"] == today.isoformat() and "so far" in r["label"]
    past = ops_data.window_range(1, today=today - timedelta(days=1))
    assert "so far" not in past["label"] and "the whole day" in past["label"]


def test_every_token_table_names_its_dates():
    for h in ("Tokens per request, by feature", "Tokens per minute, by model", "Where the errors are"):
        assert re.search(re.escape(h) + r' <span class="rng">· \{\{ ops.app.range.short \}\}</span>', TPL), h
    assert "{{ ops.app.range.label }}" in TPL


def test_no_style_uses_an_undefined_custom_property():
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", TPL))
    used = set(re.findall(r"var\((--[a-z0-9-]+)", TPL))
    assert not used - defined, f"undefined: {sorted(used - defined)}"


def test_no_display_face_with_old_style_digits_is_loaded():
    assert "family=Marcellus" not in TPL
    assert "lining-nums" in TPL
