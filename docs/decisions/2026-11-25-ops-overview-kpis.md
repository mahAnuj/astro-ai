# /admin/ops Overview opens with four Results cards over a fixed 7-IST-day window

- **Date:** 2026-11-25
- **PR / issue:** #1133, slice 2a (`Refs #1133`, not `closes`); the cards' arithmetic is `src/astro_ai/ops_kpis.py` (step 1, a2f43c7), the markup is this commit

## Why, measured

The owner's answer 3 on #1133 (2026-11-17) named four cards: Cycles shipped, First-pass QA
rate, Cost per successful outcome, PRs merged, each with its delta, its sample size and its
source. They sit in a `Results` panel right after the objective and before Goals, on the
Overview tab only. 0 LLM tokens, 0 new GCS or GitHub reads, 0 storage: `ops_kpis.build` only
reads what `snapshot()` already holds.

**A fixed window, not the range picker's.** The cards cover the last 7 complete IST days
(`ops_kpis.WINDOW_DAYS`), ending yesterday, against the 7 before. Today is left out because a
half day reads as a fall next to a whole one. `?window` and `?day` drive Token budget and App
health and do not reach these cards; the panel's caption says so. `loop.json` starts on
2026-10-08, so no 30-day comparison exists yet, and the card refuses a delta whose previous
window starts before the data does. The global range picker is in no numbered slice; slice 2b
or later should take it.

**It does not agree with "Where the loop's time went", on purpose.** That panel is the
trailing 7x24 hours to the moment its file was collected (61 PRs shipped on 2026-11-25); the
cards are whole IST calendar days (64). A second sentence in the caption names the other panel
so a reader who sees both is told why they differ.

**Definitions** (the same sentences are printed on each card):
- *PRs merged* is the distinct PRs the loop shipped (`outcome == shipped`), the rule
  `collect_loop_measurements._window_tokens` uses ("count distinct `pr`, not rows"), and not
  every PR merged on the repository (76 against 61 over the same 7 days). That way the drill
  can list exactly the rows the headline counts. The card says "shipped by loop cycles".
- *Cycles shipped* is build cycles (every run except QA rounds) that shipped, out of all build
  cycles; two cycles on one PR are two cycles and one PR.
- *Cost per successful outcome* is list-price `cost_list_usd` summed over every measured run in
  the window, QA rounds and failures included, divided by the distinct shipped PRs. **List
  price, not spend**: the loop runs on a flat Claude subscription, so the card says "list price
  per PR, not spend". A window with an unmeasured run is shown as "a floor" and gets no delta.
- *First-pass QA rate* joins `agents.json` `qa.rounds_per_issue` (a PR number to its ordered
  verdicts, undated) to `loop.json` (PR number and date), because the verdict list has no date
  of its own. **It assumes the comments endpoint returns oldest first**, so index 0 is the
  first verdict; `test_first_pass_reads_the_first_verdict_not_the_last` pins the code to that,
  and a QA spot check of one PR against GitHub is the only thing that tests the assumption.
  Coverage on 2026-11-25: 64 of 64 PRs in the current window, 111 of 111 in the previous.
  When `agents.json` is absent the card says "unavailable: agents.json not read", never 0%.

**States.** Every card is one of ok, empty ("no runs", "no PRs"), unavailable ("unavailable:
<why>") or, if `build` itself failed, unavailable with the section line naming it. An
unavailable card prints no n and no number. A sample under 10 says "too few to read". A delta
is an arrow and a direction word in its own text; the green and red on it are the second
signal, never the only one.

**Drill-down.** Each card is a `button.tile.kpi` with `data-drill`, feeding the existing sheet.
Cycles lists the shipped build rows, PRs and QA list one row per distinct PR, cost lists every
row. The `cycle` renderer gained two bits: `first QA PASS|FAIL` (not on a QA-round row, where it
would read as that round's own verdict) and `$x list`. The rows are `kpi_rows` in Overview's
blob only (a whitelist of 12 keys, step 1).

**Size** (TestClient, live switches off). Overview 221,274 B to 229,793 B (ceiling 245,000; the
issue's hard cap is 418,318). Every other tab gains only the CSS (1,905 B) and the script
(1,286 B), about 3.1 KB (ceiling +4 KB): workflows 88,868 to 91,985, runs 479,188 to 482,305,
backlog 168,271 to 171,388, analytics 119,941 to 123,058, monitoring 106,169 to 109,266. The
Agents tab moves with live agent data between renders (87.8 to 89.0 KB across runs), so only its
+3.1 KB is attributable. No new colour, so Gate 6 of `verify_contrast.py` needed no new pair.
`.vh` is a global visually-hidden class, added for slice 2b's chart text tables.

## What a gate cannot see

The drill-down script runs in a browser. `tests/test_ops_overview_kpis_page.py` pins its shape
(each card's entry reads `KPI_ROWS`, the PR drill de-duplicates, the blob key is guarded) and
the template's rendered text; the click-through was exercised once in headless Chromium and is
not in a gate. Layout at 375 px and 1280 px, light and dark, is the same.

## What remains

2b: PRs-shipped bars and two sparklines. 2c: loop ring, agent health, system health. 2d: recent
activity. 2e: collectors for Average cycle time and Content published (waits on #1480). The
global range picker and a 30-day delta need `loop.json` to be older than they are.

## Rejected

- **The cards obeying `?window`.** Not one of the picker's windows is a clean week of IST days,
  and 24 h would compare a partial day.
- **`pr_flow` for PRs merged.** It counts every merged PR; the drill could not list what the
  headline counted.
- **A KPI registry or a generic card macro.** Four cards, one template block; a registry is
  indirection for a count that is not growing.
- **Shipping `cycles` (365 KB) in Overview's blob** to power the drill. `kpi_rows` is about 41 KB.
- **Estimating first-pass QA from `first_submission_fail_pct`.** It is a 30-day, undated figure
  and cannot be windowed.
- **Disabling an unavailable card's button.** `.tile[disabled]` is 55% opacity, which fails
  4.5:1 on its own text; the drill opens an empty sheet instead.
