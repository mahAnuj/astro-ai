"""#1554: one malformed row in the daily series, the movers tables or issues.json `trend.days`
degrades its own panel, never all 7 /admin/ops tabs. tests/test_ops_series_row_tolerance.py."""

_O = "src/astro_ai/ops_data.py"

MUTATIONS = [
    ("#1554: _dict_rows hands back the raw list, so a null row reaches `.get` again",
     _O, "    return [r for r in x if isinstance(r, dict)] if isinstance(x, list) else []\n",
     "    return x\n",
     "test_a_null_row_beside_good_rows_keeps_the_good_ones"),
    ("#1554: _num hands back the raw value, so a string count reaches sum/max again",
     _O, "    if isinstance(v, bool) or not isinstance(v, (int, float)):\n        return 0\n    return v if math.isfinite(v) else 0\n",
     "    return v\n",
     "test_a_non_numeric_count_is_zero"),
    ("#1554: the mover row keeps a non-numeric delta, which the up/down split compares",
     _O, '''if isinstance(r.get("delta"), (int, float)) and not isinstance(r.get("delta"), bool)
                and isinstance(r.get(dim), str)]''',
     '''if isinstance(r.get(dim), str)]''',
     "test_movers_drop_unreadable_rows_and_keep_the_good_one"),
    ("#1554: _clean_flow_days keeps a day whose counts are not integers",
     _O, 'or not all(_is_int(d.get(k)) for k in ("opened", "closed", "open_end", "net"))):',
     "):",
     "test_issue_flow_keeps_readable_days_and_counts_the_rest"),
    ("#1554: _clean_flow_days stops guarding opened_by/closed_by against a non-object",
     _O, "if isinstance(by, dict) else {})",
     "if True else {})",
     "test_a_bad_breakdown_is_ignored_not_fatal"),
]
