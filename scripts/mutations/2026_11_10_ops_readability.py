"""2026-11-10: /admin/ops names the days behind each figure and is legible.

Each row re-breaks one fix and names the test that must go red."""

MUTATIONS = [
    ("ops: the selected window chip goes back to an undefined colour (ink on ink)",
     "src/astro_ai/templates/admin_ops.html",
     ".win.on{color:var(--ground);background:var(--ink)}",
     ".win.on{color:var(--night);background:var(--ink)}",
     "test_no_style_uses_an_undefined_custom_property"),
    ("ops: a week window starts a day late (6 days labelled as 7)",
     "src/astro_ai/ops_data.py",
     "    start = end - timedelta(days=days - 1)\n",
     "    start = end - timedelta(days=days - 2)\n",
     "test_a_week_is_seven_calendar_days_ending_today"),
    ("ops: the per-model table loses its date range",
     "src/astro_ai/templates/admin_ops.html",
     'Tokens per minute, by model <span class="rng">· {{ ops.app.range.short }}</span></h3>',
     "Tokens per minute, by model</h3>",
     "test_every_token_table_names_its_dates"),
]
