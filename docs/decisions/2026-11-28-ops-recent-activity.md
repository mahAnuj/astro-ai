# /admin/ops Overview gains Recent activity with All, Agents, Workflows and Issues chips, and one Overview byte ceiling

- **Date:** 2026-11-28
- **PR / issue:** #1133, slice 2d (`Refs #1133`, not `closes`), and #1562 (the Overview byte cap). The data is `src/astro_ai/ops_activity.py` (step 1, 732e158 and 99e1924); the markup, CSS and page tests are step 2.

## Why, measured

The owner's mock-up for #1133 (2026-11-17) puts a Recent activity feed with filter chips on
Overview. It now sits after Key metrics and before Goals and agent decisions, on the Overview
tab only. 0 LLM tokens, 0 new GCS reads, 0 new GitHub reads, 0 storage, no script, no
Tailwind class (so `app.css` is not rebuilt): `ops_activity.build(ops, links, active)` reads
only what `snapshot()` already holds.

**The chips are server links, not JS.** `All / Agents / Workflows / Issues` are plain
`<a class="win" href="?tab=overview&window=7&activity=<key>#recent-activity">`, the Token
budget window selector's own pattern (`.winsel`, `.win`, `aria-current="true"`), so they
needed no CSS rule. The base is the rail's own Overview href, so a picked `?day=` and the
window survive a click, and the filter is in the URL (bookmarkable, shareable, works with
JS off). A link renders only the chosen view's 8 rows (about 4.4 KB); a JS filter would put
every view's rows in the DOM (3 x 8 rows plus All, about 14 KB), plus a script and a script
test, on a page at its cap. The cost of a click is one full re-render (about 40 ms server on a
quiet machine, 250 KB on the wire) landing on the `#recent-activity` anchor; acceptable for an
admin page. The `activity` value is membership-tested by `ops_activity.pick_filter` and never
echoed; an unknown value falls back to All, never a 422.

**What each type chip reads** (all already in `snapshot()`):

| chip | source | one row is | href, built from an int or a regex-checked filename, never a row string |
|---|---|---|---|
| Agent | `loop.json` rows, plus PRs merged today when `today_live` is true | one agent-work cycle, or one live merge | the PR, else the run |
| Workflow | `agents.json` loops (the ring's own state words), plus today's failed runs when live | the last run of one workflow | the workflow's page, or the run |
| Issue | `issues.json` open rows, newest filed first | one issue still open | the issue |

**Supersede rule for the two Workflow sources.** Keyed by the workflow's display name,
casefolded. A live failed run replaces that workflow's `agents.json` row only if its start is
strictly newer than the row's last run; an unmatched name is added. It fails open: a name
mismatch costs a second row, never a hidden failure. When today's GitHub read did not happen
the live lists are copies of rows already counted under Agent and are ignored.

**A state is a dot and a word.** The dot is `aria-hidden`; the state word (`shipped`,
`PR open`, `failed`, `running at last collection`, `blocked`, `still open`) is always text.
A source that cannot be read says `unavailable: <why>` and "Nothing is shown, not 'no
activity'"; a source that is readable with nothing in it says so in a `role="status"` line.
A half-empty All names the unreadable source in a note, so it is never read as a quiet system.

**Deployments is omitted.** The issue's own table says no per-deploy record is collected
(`collect_agents` would have to list `verify-production` runs with their `head_sha`). It
belongs to slice 4, and the page does not mention it (pinned: the word is not in the panel).

**Closed issues are not listed.** `issues.json` carries closed numbers and closers but no
titles, and `_issue_flow_view` does not pass them through; passing them needs an
`ops_data.py` edit, which would collide with #1564. The panel's closing line says so. An
issue filed and closed within a day never appears.

**"View all" is per chip.** All and Agents link the rail's Runs href; Workflows links the
Workflows tab and Issues the Backlog tab, because Runs & Traces lists agent cycles by day and
shows no workflow or issue rows. A judgement beyond the spec's single link; flagged for QA,
three lines to revert in `ops_activity._VIEW_ALL`.

**Size.** Measured through `TestClient` with `OPS_LIVE_ISSUES=0 OPS_LIVE_TODAY=0` on this
runner (baselines drift with the committed measurement files; "before" is the "after" less
the section and the CSS, since a clean-tree render was not taken):

| thing | measured | cap in test |
|---|---|---|
| Overview | 254,559 B (about 249,510 before) | `OVERVIEW_MAX_BYTES` 418,318 |
| the `id="recent-activity"` section, real data | 4,393 B (All), 4,214 (Agents), 4,398 (Workflows), 4,444 (Issues) | 6,500 |
| the new CSS block | 656 B | 1,500 |
| each other tab | +656 B (CSS only): agents 93,745, workflows 98,570, runs 515,211, backlog 175,964, analytics 129,567, monitoring 115,950 | CSS block <= 1,500 |
| blob keys | unchanged | equal to `ops_tabs.BLOB_KEYS["overview"]` |

The section's worst case is a constant, not a function of data: 8 rows per view, titles cut at
90 characters, subtitles at 110. On a fixture with every title at 90 characters and 30 rows per
source it stays under 6,500 B in every view (test). It is not bounded against a title made
of characters that HTML escapes to five bytes (`"`, `&`, `<`); real titles carry few.

## #1562: one Overview byte ceiling

The two page tests that carried their own `OVERVIEW_CAP` (245,000, then 250,000) failed for a
data reason, not a code reason: the number that moves is the open-issue count (104 on
2026-10-20, 165 on 2026-11-28), and it also moves down. Slice 2d alone adds about 5 KB, so a
250,000 cap fails on this very PR whatever else is done.

**Decision.** One named constant, `ops_tabs.OVERVIEW_MAX_BYTES = 418_318`, the issue's own
acceptance criterion for slice 2 (Overview no larger than the old whole page, measured
2026-11-17). The 2b and 2c page tests and the new 2d test import it, so they cannot disagree.

**Code growth is guarded by the data-independent tests, not by the page total**: 2c's
`test_overview_growth_is_the_sections_plus_the_css_and_at_most_15_kb`, 2b's
`grew <= 18_000`, and the bounded-section and CSS tests here, all on hand-written fixtures. The
real-data tests keep one assertion, the page ceiling. 2c's real-data `_sections <= 12,000`
line was dropped (11,798 B against 12,000 B: the longest alert title the LLM row can print
moves it with no code change); its fixture twin still pins it. **2b's real-data
`grew <= 18_000` (17,229 B, 771 B of headroom) is the next one to watch.**

**Trigger, not a trim now.** The only data-linear term in the blob is `issues`
(63,806 B for 165 open issues, about 387 B a row). Headroom is 418,318 - 254,559 = 163,759 B,
about 270 days at 600 B a day (a rate consistent with the open-issue count, not measured over
time). **When real Overview passes 380,000 B (about 90%), slim the `issues` rows that
`blob_for("overview", ...)` ships (drop `ask`, `labels`) in its own issue**, because that
changes the Backlog tile's drill rows and needs its own tests. To measure it:

```
OPS_LIVE_ISSUES=0 OPS_LIVE_TODAY=0 uv run python -c "
import os; from fastapi.testclient import TestClient
from astro_ai.main import app; from astro_ai.routes import deps
pw = os.environ.get('ADMIN_PASSWORD', deps._ADMIN_DEV_FALLBACK)
print(len(TestClient(app).get('/admin/ops?tab=overview', auth=('admin', pw)).content))"
```

corpus: n/a -- this is an operations page; it makes no astrological claim.

## What a gate cannot see

The colours (gold, amber and the status fills against light and dark), the 375px look (rows
wrap; the chip and time drop under the text), the focus ring on a chip and the click landing
on the panel are browser-only. They were looked at once in headless Chromium at 375px and
1280px, light and dark: `scrollWidth` 375 and 1280, no element past the viewport, the chip
group inside the panel, a 2px focus outline on a chip, a click on Workflows landing with that
chip `aria-current` and the panel at the top of the viewport. None of that is in a gate.
`scripts/verify_contrast.py` covers the tokens (`--ink-mute` time text), not the rendered
page.

## Rejected

- **A JS filter over rows already in the page.** It needs every view's rows in the DOM, a
  script and a script test, on a page at its cap; the link needs none and keeps the filter in
  the URL.
- **A Deployments chip with a stub.** Nothing is collected; a chip over no data would read as a
  quiet system.
- **Listing closed issues.** No title in the file; reading them live is a new GitHub read.
- **Raising the cap to 300,000.** Still a data ratchet, red again in about 70 days.
- **Keeping 250,000 and trimming `issues` now.** 2d alone needs about 5 KB, and trimming
  changes the Backlog drill, which has its own tests.
- **Deleting the real-data tests.** The ceiling is the owner's own criterion and the only check
  that sees real data.
- **A per-day ratchet file.** A second thing to keep in step with the data.
