# /admin/ops Overview gains PRs-shipped bars and four Key metrics rows, each with its own window

- **Date:** 2026-11-27
- **PR / issue:** #1133, slice 2b (`Refs #1133`, not `closes`); the arithmetic is `src/astro_ai/ops_trends.py` (step 1, fd79a71), the markup is this commit. Folds in #1490 (a refused delta prints no `was`) and #1491 (a size correction to the 2a record).

## Why, measured

The owner's mock-up for #1133 (2026-11-17) put a PRs-shipped bar chart and a Key metrics list
between Results and Goals. Two panels, `#prs-shipped` and `#key-metrics`, now sit there on the
Overview tab only. 0 LLM tokens, 0 new GCS reads, 0 new GitHub reads, 0 storage:
`ops_trends.build(ops, kpis, links)` reads only what `snapshot()` and `ops_kpis.build` already
hold.

**The seven bars add up to the PRs-merged card.** The bars are the same 7 complete IST days as
the Results cards, and each PR is counted once, on the first IST day it shipped in the window
(`ops_kpis._stats` `pr_day`). A PR worked on two days is therefore not two PRs, and
`test_the_seven_bars_add_up_to_the_prs_merged_card` reads both numbers off the rendered page.
A day with no `loop.json` rows says "no runs", never 0: the loop did not run, which is not the
same as running and shipping nothing. A day with runs and no PR is a measured 0. Rejected for
the bars: `_by_day()` (counts cycles, so it would disagree with the card), `pr_flow` (every
merged PR, by UTC day), and Mon-Sun calendar bars (a partial current week).

**A bar opens that day's PRs.** Each bar is a `g.dcol` with `data-drill="kpi-prs-day"`,
`data-day`, `data-prs`, `data-tip`, `tabindex="0"` and `role="button"`, so the existing hover
tooltip handler works unchanged (the `#dtip` is inside the chart's wrap). The new `TILES` entry
filters `kpiPrs()` by the PR numbers in `data-prs`; the handler hands the clicked element to
the entry and appends `data-day` to the sheet title. It is inserted before `kpi-cycles` because
2a's `kpi-cost` check spans from there to the end of `TILES` and rejects `filter`. The bars
deliberately do not use `.day-btn`: that class is the Runs tab's, and
`test_every_drill_down_that_a_tab_renders_has_its_data_on_that_tab` would then demand `cycles`
(365 KB) in Overview's blob.

**The four rows, each with its own window.** The windows differ on purpose, and each row prints
its own:
- *Results and the bars*: 7 complete IST days ending yesterday.
- *Organic search clicks* (`gsc-daily.json`): 7 days ending at the file's own newest row.
  Search Console trails the present by about 3 days, and `traffic.window` prefers GA4's window,
  so it would name a week the clicks do not cover. Nothing attributes a click to an agent; the
  row says "not attributed to any agent".
- *Issues closed* (`issues.json` `trend.days[].closed`): UTC days, the 7 complete days before the
  collector's partial last day (`scripts/issue_flow.py`: "today included (partial)"). The row is
  labelled "UTC days" in the template (`window_text` carries only the dates) and prints how
  many closures were `close-on-evidence`. It is "closed", not "resolved": the file counts a
  closure for any reason. This needs no collector: the 2026-11-17 table said `issues.json` had
  no closed-per-day series, and it now has.
- *Content published* and *Average cycle time*: not collected. Slice 2e adds the collectors. Each
  row prints the owner's definition (answer 5) and no number and no sparkline, because a 0 here
  would mean "unknown". "Average cycle time" cannot be minutes per cycle: the owner defines it as
  an issue opened to its fix merged.

**It does not agree with the Backlog tab's "Issue flow" on purpose.** Issue flow shows a
different 7-day closed count because it takes the last 7 entries of the same series including
today's partial day; this row leaves the partial day out. The IST Results window and the UTC
issue window are also different days. Each panel names its own.

**States.** A row that cannot be computed has class `st-unavailable`, says "unavailable: <why>"
and prints no number, no sparkline and no change pill. A window with a missing day shows no
value and no change, never a sum over the hole (`no data for 1 of 7 days`). A refused change
prints no `was N` (#1490: a previous window that starts before the data held a partial week,
and `was 0` read as a fact). A change is an arrow and a direction word in its own text; the
green and red on it are the second signal. If `ops_trends.build` fails, both panels render
unavailable with the section line naming it, and Results is untouched.

**Accessibility.** Every SVG has `role="img"` and an `aria-label` naming its window, its unit
and every value; each has a `.vh` (visually hidden) table with the same numbers, and each
sparkline point has a `<title>`. The bars' weekday label is hidden under 640 px, where two label
lines at the scaled font do not fit; the tooltip and the table still carry the weekday. A bar's
hit rect is widened to the whole day by a transparent stroke, not by padding.

**Size** (TestClient, live switches off, measured on this runner against the unchanged template
at the same moment; the architect's table, taken on another checkout, read 222,398 for
Overview, and these baselines drift by the hour with live agent data). Overview 213,925 B to
231,154 B (+17,229; cap baseline + 18,000 and at most 245,000). Every other tab gains only the
CSS (2,405 B, cap 2.5 KB) and the script (about 0.7 KB, cap 1 KB): +3,082 B on each of agents
(87,233 at that moment), workflows 92,038, runs 503,220, backlog 169,869, analytics 123,002 and
monitoring 109,963 (cap +3,500). The tests count the growth from the template's own parts
instead of pinning a baseline the committed measurement files move. Overview warm render about
38 ms (cap 300 ms). No new colour and no new token (`--brand`, `--ink`, `--ink-dim`,
`--ink-mute`, `--line-2`, `--panel` and the existing status tokens); no Tailwind class changed,
so `app.css` was not rebuilt.

## What a gate cannot see

The colours, the spacing, the hover tooltip and the click that opens the sheet are
browser-only. `tests/test_ops_trends_page.py` pins the rendered text, the structure and the
sizes; the script's PR filter is pinned as a string, which is weaker than running it. The look
at 375 px and 1280 px, light and dark, and a click on a bar (9 rows for a bar labelled 9), were
exercised once in headless Chromium and are not in a gate.

## What remains

2c loop ring, agent health, system health. 2d activity chips. 2e collectors for Content
published and Average cycle time (waits on #1480). `_traffic_view` raises on a garbage
`gsc-daily.json` row, so `/admin/ops` 500s before this code runs (the #1492 / #1542 class, in
`ops_data.py`, not folded in to keep that file untouched).

## Rejected

- **One chart macro or a metric registry for two charts.** About 60 lines of indirection for a
  count that is not growing.
- **Full-height hover bands per sparkline point.** About 2 KB each; circles with a `<title>`
  cost under 1 KB in all.
- **Putting the panels inside the Results section.** The 2a test scans that block for
  arithmetic and its CSS is measured from its marker to the end of the style block.
- **A `/learn` article count from git at request time.** There is no `.git` in the image.
- **A mid-height gridline on the bar chart.** The template may not do arithmetic and the
  backend sends tick values, not positions; each bar carries its own number, so the top and the
  baseline are enough.
- **A new blob key.** `kpi_rows` already carries what the bar's drill needs.
