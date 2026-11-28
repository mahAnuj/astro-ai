# Overview's Backlog tile ships the top 50 issues, not every open one

- **Date:** 2026-11-28
- **PR / issue:** #1562

## Why, measured

`uv run pytest tests/test_ops_trends_page.py tests/test_ops_loop_health_page.py` failed on
`main`: the Overview was 252,098 B (252,049 B in the issue's run) against `OVERVIEW_CAP =
250_000`. About 105 KB of the page is the `ops-data` JSON blob, and `issues` (167 open-issue
rows, ~64 KB) was the only term in it with no ceiling: every other key is a fixed or
windowed size, so the page grew with the backlog.

`ops_tabs.top_issues` now keeps the first `OVERVIEW_ISSUE_ROWS = 50` rows in the order the
Backlog drill-down's script sorts them (priority high, medium, low, unset; newest first
inside a band), and the Overview ships only those. The Backlog tab still ships every row,
and the tile's sheet title says "Highest priority first: 50 of N open (the Backlog tab lists
all)" when the list is cut. Measured with the issue's repro on the same data: 252,098 B to
207,020 B. Overview size is now flat in the backlog, apart from the server-rendered queue
(already capped at 14). 0 LLM calls.

`tests/test_ops_overview_issue_cap.py` pins the cap, the order (against the rank literal read
from the template) and the Backlog tab's full list.

## Rejected

- **Raise `OVERVIEW_CAP`.** A ratchet: the cap would be re-raised each time the backlog grew,
  and the unbounded term is the defect, not the number.
- **Slim each row.** Cheaper rows still grow linearly with the backlog.
- **A lazy endpoint for the full list.** A new route, auth and failure mode for a drill-down
  that the Backlog tab already serves; not needed (YAGNI).
- **Trim `kpi_rows`.** Already bounded by its 7-day window.
