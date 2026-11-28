"""#1492 (2026-11-27): one malformed row in measurements/loop.json 500ed /admin/ops on every
tab. `_loop_view` now drops rows it cannot read and counts them; the Overview footer reports the
count. Exercised by tests/test_ops_loop_row_tolerance.py.
One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("ops-loop-row: a row that is not a dict is read as one",
     "src/astro_ai/ops_data.py",
     "        if not isinstance(r, dict) or not isinstance(r.get(\"outcome\"), str):\n            skipped_rows += 1",
     "        if not isinstance(r.get(\"outcome\"), str):\n            skipped_rows += 1",
     "test_the_view_keeps_only_readable_rows_and_counts_what_it_dropped"),
    ("ops-loop-row: a row whose outcome is not a string is kept",
     "src/astro_ai/ops_data.py",
     "        if not isinstance(r, dict) or not isinstance(r.get(\"outcome\"), str):\n            skipped_rows += 1",
     "        if not isinstance(r, dict):\n            skipped_rows += 1",
     "test_the_view_keeps_only_readable_rows_and_counts_what_it_dropped"),
    ("ops-loop-row: the rows the view dropped never reach the Overview footer",
     "src/astro_ai/ops_kpis.py",
     "    skipped += int(loop.get(\"skipped_rows\") or 0)\n",
     "",
     "test_the_overview_footer_counts_every_row_left_out_and_good_rows_still_feed_the_cards"),
    ("ops-loop-row: a non-string started timestamp raises again",
     "src/astro_ai/ops_data.py",
     "    except (ValueError, TypeError):\n        return None\n\n\ndef next_cycle_ist",
     "    except ValueError:\n        return None\n\n\ndef next_cycle_ist",
     "test_a_non_string_ts_is_not_a_timestamp"),
]
