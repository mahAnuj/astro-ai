# /admin/ops Overview gains the engineering-loop ring, Agent health and System health, each saying only what was checked

- **Date:** 2026-11-27
- **PR / issue:** #1133, slice 2c (`Refs #1133`, not `closes`); the data is `src/astro_ai/ops_loop_health.py` (step 1, b6f6ed2 and 048b2ea), the markup and CSS are this commit.

## Why, measured

The owner's mock-up for #1133 (2026-11-17) put a loop ring, an Agent health panel and a System
health panel at the top of Overview. They now sit between Results and PRs shipped, on the
Overview tab only, in that order: The engineering loop, Agent health, System health. 0 LLM
tokens, 0 new GCS reads, 0 new GitHub reads, 0 storage, no script and no Tailwind class (so
`app.css` is not rebuilt): `ops_loop_health.build(ops, agents_now, tabs_health, links)` reads
only what `snapshot()`, the cards the route already fetched for every tab and the rail's health
block already hold.

**The ring is seven steps, and a step's colour is the collector's, not ours.** Measure, Decide,
Build, Check, Merge, Ship & Verify, Score, in a ring with seven arrows. A step is the worst
`last_run_health` of its workflows in `agents.json`. `loop-outcomes` exits non-zero by contract
when it finds something, so its last conclusion is `failure` with health `amber`: the ring
paints it amber and says "last run amber", it does not paint a working report as a crash. A
workflow with no row is `unavailable`, never green. Nothing in the data says which step is
current, so no step is marked. The data is as of the last collection, and a running step says
"running at last collection".

**The state is never the colour alone.** In the SVG a node carries a glyph (a tick, `!`, a
cross, an ellipsis, `?`) next to its name; in the legend a dot (aria-hidden) sits beside the
state WORD. The ring is `role="img"` with an aria-label that lists all seven steps and their
states, and the legend `<ol>` under it is the keyboard and screen-reader path (the SVG's own
links are `tabindex="-1"`, children of `role="img"` not being exposed). Tab order checked in
headless Chromium: the seven legend links, then Agents, then Monitoring, Workflows,
verify-production on GitHub, Monitoring. Each step's link is one of the rail's own hrefs
(`ops_tabs.tab_links`): no value from agents.json reaches an href. A hidden `.vh` table
repeats step, name, last run and result.

**Agent health is the groups the snapshot carries**, four today (build, decide, measure,
operate; 15 cards: 14 agents and the `merge` workflow), not the five of the mock-up: the panel
renders what the data has, so a fifth group appears by data and a fake "on request" row is not
drawn. A group's state word reads `failed` and `blocked` only. An empty or garbage
`agent_status` says "unavailable: agent_status returned no agents", never "0 cards".

**System health is four rows** (LLM providers, GitHub Actions, Website, Monitoring & alerts),
each a state word, a detail line and a link. The Website row is the last `verify-production`
run and says it is not an uptime monitor (owner, 2026-11-17: uptime shows unavailable).

**Size.** Measured through `TestClient` with `OPS_LIVE_ISSUES=0 OPS_LIVE_TODAY=0`, before and
after, on this runner (baselines drift hourly with the committed measurement files):

| tab | before | after | change |
|---|---|---|---|
| overview | 235,073 | 249,551 | +14,478 (the three sections 11,790 + CSS 2,685) |
| workflows | 95,229 | 97,914 | +2,685 (CSS only) |
| runs | 511,870 | 514,555 | +2,685 |
| backlog | 172,623 | 175,308 | +2,685 |
| analytics | 126,226 | 128,911 | +2,685 |
| monitoring | 112,624 | 115,309 | +2,685 |

The agents tab moved by the same CSS plus the live card data (92,550 to 93,089 on the last
run), which is not stable between runs. Overview's warm TestClient median is 40.9 ms (39.2
before), against a cap of 300 ms. Caps: Overview baseline + 15,000 B and at most **250,000 B
absolute** (2b's 245,000 is spent; this raises it, the issue's hard ceiling stays 418,318),
the three sections at most 12,000 B, the new CSS at most 3,000 B, every other tab at most
+3,000 B. At 375px the document's `scrollWidth` is 375 and the ring's names set at 20 user
units are about 10.8px; under 640px the ring drops its cadence lines and the legend carries
them in text. Pinned in `tests/test_ops_loop_health_page.py`, whose size tests count growth
from the template's own parts, not a baseline.

corpus: n/a -- this is an operations page; it makes no astrological claim.

## Rejected

- **A "current step" fill as in the mock-up.** No data says which step is current; marking one
  would assert something unmeasured.
- **Per-node live run lookups.** One GitHub read each, against the 60/h budget the page shares.
- **Reading `lessons.json` for the Score step.** A new fetch, and this slice adds none.
- **Mapping a node by the conclusion string.** The collector's `last_run_health` is the
  authority; `loop-outcomes` would read red.
- **The ring's caption inside the circle.** "One change, from data to production and back" is
  about 215 units at 12px, wider than the 194 units free between the side nodes, so it is a
  `figcaption` under the ring.
- **A JS drill sheet for a node.** A link to the tab satisfies the criterion with 0 script bytes.
- **Putting the panels after Goals.** It would leave the 2a/2b span tests untouched but bury the
  ring below a long panel.
