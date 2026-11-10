# /admin/ops states the dates behind every figure and drops the hard-to-read display face

- **Date:** 2026-11-10
- **PR / issue:** this PR (owner request, 2026-11-10)

## Why, measured

**The owner's words.** "this data on ops dashboard is not showing for which duration is this
aggregated data for", and "a lot of data … is not readable properly, possibly bad font and
background".

**Measured on the page before the change:**
- **The window switch was invisible.** The selected chip (`.win.on`) set `color:var(--night)`, and
  `--night` is not defined on this page. The text inherited `--ink` on an `--ink` background and
  rendered as a blank box. The switch existed; nobody could see which window was on.
- **Only the panel header stated the window**, as "last 7 d". The tables below it stated nothing.
  "Last 7 d" is also not what the figures cover: `llm_stats` and `events` build N **calendar** days
  from the server's `date.today()` (UTC), with today still filling.
- **Marcellus draws old-style digits.** On the headline tiles, the objective and the panel labels,
  "109" read as "1O9" and "2026-11-06" as "2O26-II-O6".
- **Labels and secondary text were small and dim.** Micro-labels were 10–11px uppercase with .1em
  tracking. `--ink-mute` #838a97 on `--panel` was about 4.2:1.

**Decision:**
- `ops_data.window_range()` gives the exact dates. The Token budget and App health headers print
  them, for example "2026-11-04 → 2026-11-10 UTC, today still filling", and each token table and
  the error table carries the short form ("11-04 → 11-10").
- The chip uses a defined colour. A test now fails on any `var(--x)` the page never defines.
- One readability layer is appended last in the page's `<style>`, so the markup and every test that
  reads it are untouched:
  - Inter for text and JetBrains Mono for figures, both with lining tabular digits;
  - labels at 12px with less tracking;
  - brighter ink: `--ink-mute` 6.6:1 and `--ink-dim` 10.1:1 on `--panel`;
  - rounded cards with a header band, zebra rows and a hover on tables;
  - severity-coloured alerts with a solid left bar, and pill status chips with a live dot;
  - the accent fills the selected window chip.
- Checked at 1440px and at 375px, with no horizontal scroll.

**Not done here:**
- **A single-day filter (`?day=YYYY-MM-DD`).** It needs `events.error_breakdown` to take an end
  date, and `events.py` is in `TRUST_BOUNDARY`. That is its own change.
