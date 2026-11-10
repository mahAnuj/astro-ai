"""/admin/ops says which days a figure covers, and its type is legible (owner, 2026-11-10).

"this data on ops dashboard is not showing for which duration is this
aggregated data for" and "a lot of data … is not readable properly, possibly
bad font and background". Measured before the change: the selected window chip
was ink on ink (`var(--night)` is not defined on the page), and Marcellus'
old-style digits rendered "109" as "1O9" on the headline tiles.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from astro_ai import ops_data

TPL = (Path(__file__).resolve().parents[1] / "src/astro_ai/templates/admin_ops.html").read_text()


def test_a_week_is_seven_calendar_days_ending_today():
    r = ops_data.window_range(7, today=date(2026, 11, 10))
    assert (r["start"], r["end"]) == ("2026-11-04", "2026-11-10")
    assert r["short"] == "11-04 → 11-10" and "today still filling" in r["label"]


def test_one_day_says_so_far_not_24_hours():
    r = ops_data.window_range(1, today=date(2026, 11, 10))
    assert r["start"] == r["end"] == "2026-11-10" and "so far" in r["label"]


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
