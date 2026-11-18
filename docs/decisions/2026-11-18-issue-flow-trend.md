# /admin/ops shows issue flow: opened against closed, who did each, and merged-but-open

- **Date:** 2026-11-18
- **PR / issue:** none yet (owner request, 2026-11-18)

## Why, measured

The owner: *"Many prs have been merged but I don't see issue count reducing"*. Measured
2026-11-15..18: 96 PRs merged, 59 issues closed, 73 opened, 131 open. The open count alone
cannot tell findings arriving faster from fixes not closing, so the page now shows both
flows and the gap between them. The owner said "Yes" to building it the same day.

What was decided, and what was rejected:

- **The trend is a `trend` block in `measurements/issues.json`, written by
  `collect_issue_backlog.py` through `scripts/issue_flow.py`.** A sibling file would need a
  new step in `agent-measure.yml`. This way the workflow does not change, and the page
  already fetches that file. The page always reads the trend from the committed snapshot,
  even when the backlog itself is live. The first run reads about 250 timelines, which is
  far too many for a request.
- **The closer comes from the issue timeline, never from the last comment.** I sampled 40
  closes on 2026-11-18. On most of them a later comment comes after the close: the
  analyst's "not scoreable" note or an agent-timer marker. The last comment would credit
  those to the wrong closer. The timeline gives the `closed` event's actor and the closer's
  own comment within 5 minutes of it, in one request per issue. Closers already read are
  carried forward by `(number, closed_at)`, so later runs read only new closes (about 20).
- **The red-main sentinel gets its own closer bucket (`main-red-report`).** Without it,
  those closes would be most of `other`, and none of them is a fix closing.
- **`[OPS]` findings are identified by title only.** `file_ops_findings.py` labels them
  `chore`, a label much of the backlog also carries.
- **A claim on an issue is read exactly as `close-on-evidence.yml` reads it**: a closing
  keyword in the title or body, else an `issue/<n>-` branch unless the body only `Refs` it.
  Merged-but-open counts open issues claimed by a PR merged more than 24 h ago.
  `detect_ops_regressions.py` raises `fixes-not-closing` (amber) at 3 or more, from the
  same constant as the page (`ops_data.FIXES_NOT_CLOSING_MIN`).

First reading on real data (2026-11-18, read-only, 250 requests, 169 s): last 7 days 131
opened (57 audit/session, 70 loop, 4 ops), 104 closed (77 close-on-evidence, 14 owner,
7 red-main sentinel, 6 /prioritise). 8 issues were merged-but-open: #310, #838, #856,
#889, #908, #970, #1056 and #1080, each claimed by a PR with `closes #N`, merged 49 to
191 h earlier.
