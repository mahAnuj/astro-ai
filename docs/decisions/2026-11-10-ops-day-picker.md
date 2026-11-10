# /admin/ops can show one past day, from the per-day blobs that already exist

- **Date:** 2026-11-10
- **PR / issue:** this PR (owner request, 2026-11-10)

## Why, measured

**The owner's words.** "build date picker if that can be done easily without increasing any
storage".

**Why it needs no storage.** Every Token budget and App health figure already comes from per-day
blobs:
- `llm_stats.usage_summary`, `llm_stats.range_summary` and `events.error_breakdown` each walk
  `[today - i for i in range(days)]`.
- Both stores keep 30 days (`STATS_RETENTION_DAYS`, `EVENT_RETENTION_DAYS`).

A picked day is the same walk ending on a different day, so the three functions gained one
optional `end` argument (default today).

**What this adds and what it does not:**
- No new blob, no new write, and no new read pattern.
- `_read_day` is already memoised and pins an elapsed day for the process lifetime.
- A test patches every storage write to raise and renders a picked day.

**Decision:**
- `?day=YYYY-MM-DD` renders that one UTC day. Its label reads "…UTC, the whole day", or "so far"
  for today.
- `ops_data.pick_day()` **refuses, rather than clamps**, anything that is not a date, is in the
  future, or is older than the 30 kept days. An out-of-range day would read blobs retention has
  deleted and print zeros under that date. A refused value shows the normal window, never a 422.
- The control is a plain GET form with `<input type="date">` bounded to the kept days. It
  submits on change and has a no-JS button. The URL is shareable like `?window`.
- `end` is passed only when a day is picked, so the default call is unchanged for every existing
  caller and stub.

**Trust boundary.** `events.py` is in `TRUST_BOUNDARY`, so this PR is held for `chief`. The
change there is an optional read parameter, and nothing it writes or stores changes.
