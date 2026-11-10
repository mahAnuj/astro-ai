"""2026-11-10: /admin/ops can show one past day, read from existing blobs.

Each row re-breaks one piece and names the test that must go red."""

MUTATIONS = [
    ("day picker: llm_stats ignores the picked day and reads today",
     "src/astro_ai/llm_stats.py",
     "    today = end or date.today()       # `end`: see usage_summary -- reads only\n",
     "    today = date.today()       # `end`: see usage_summary -- reads only\n",
     "test_llm_stats_reads_the_picked_day_and_nothing_else"),
    ("day picker: events ignores the picked day and reads today",
     "src/astro_ai/events.py",
     "    today = end or date.today()\n    wanted_days = [today - timedelta(days=i) for i in range(days)]\n",
     "    today = date.today()\n    wanted_days = [today - timedelta(days=i) for i in range(days)]\n",
     "test_events_reads_the_picked_day_and_nothing_else"),
    ("day picker: a day older than retention is accepted and renders deleted blobs as zeros",
     "src/astro_ai/ops_data.py",
     "    if not (t - timedelta(days=PICK_DAYS - 1) <= d <= t):\n",
     "    if not (d <= t):\n",
     "test_a_bad_or_out_of_range_day_is_refused_not_clamped"),
    ("day picker: a picked day shares the 1-day window's cache slot",
     "src/astro_ai/ops_data.py",
     "    key = (days, end)          # a picked day is its own cache entry\n",
     "    key = (days, None)          # a picked day is its own cache entry\n",
     "test_a_picked_day_and_the_1_day_window_do_not_share_a_cache_slot"),
    ("day picker: the 'day' chip still claims the view when a day is picked",
     "src/astro_ai/templates/admin_ops.html",
     "class=\"win{{ ' on' if d == ops.app_days and not ops.app.day }}\"",
     "class=\"win{{ ' on' if d == ops.app_days }}\"",
     "test_the_page_renders_the_picker_bounded_to_kept_days"),
]
