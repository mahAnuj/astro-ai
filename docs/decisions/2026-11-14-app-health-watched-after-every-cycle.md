# The live app's health is filed as issues after every cycle, from the steward

- **Date:** 2026-11-14
- **PR / issue:** this PR (owner request, 2026-11-14)

## Why, measured

**The owner's words.** On seeing "10.19% of LLM calls are erroring" on /admin/ops: "was this
reported by the agent monitoring the ops dashboard". Then: "the ops dashboard monitoring should be
more realtime vs nightly run".

**It was not reported.**
- `detect_ops_regressions.py` runs from a plain checkout, so its `NOT_COVERED` list names the LLM
  error rate, provider exhaustion, RequestTooLarge (413s) and the fallback rate: all of them live
  in the GCS event and usage logs.
- The only job that read the bucket was `agent-measure`'s analyst, once a day, and it collects
  tokens and cache figures, not errors.

**Decision.**
- `agent-steward` already holds `id-token: write` and `issues: write`, and already files the
  detector's findings. It runs after every `agent-work` completion and twice a day on a clock: 22
  runs over 11-12..11-14.
- Before filing, it now authenticates with the analyst's read-only identity, and
  `scripts/watch_app_health.py` computes `ops_data._app_view`, the dashboard's own function.
- It then applies `ops_data._app_alerts`: the dashboard's product rules, split out of `_alerts` so
  the two can never disagree.
- The findings (`app-errors`, `app-exhausted`, `app-too-large`, `app-fallbacks`, `app-token-peak`)
  go through the existing filer: one issue per kind, commented on change, a single note when it
  clears.
- **`app-idle` and `app-unreadable` are deliberately not filed**, though the dashboard shows
  both. Zero LLM calls read cannot be told apart from a bucket this job could not read, because
  `storage.get()` swallows a 403 and returns None. So the watcher reports zero calls as
  `ok: false`, never as an idle app, and `evaluate()` drops both kinds.

**The window.** Today so far. If today has fewer than 30 calls, the 7-day window is used instead,
so one failed request at 00:30 UTC does not read as a 100% error rate. The finding's title names
the window either way.

**Safety:**
- The auth step does not export credentials to the job. Only the watch step receives the file,
  and an `always()` step deletes it before the steward or chief agent runs. Those agents get no
  bucket access.
- If the bucket cannot be read, the app-* issues are left untouched, never marked cleared. That
  includes a partly readable bucket: before evaluating, the watcher reads yesterday's blob under
  every prefix the view reads (`llm_stats/` and `events/`), and if any read fails it reports
  `ok: false` with that key in the reason. Before this, `llm_stats/` readable with `events/`
  returning 403 read as 0 errors and cleared the open `app-errors` issue (QA on this PR).
- No `permissions:` change.

**Limits, stated:**
- "After every cycle" is about every 2–3h, not seconds.
- While `LOOP_PAUSED` is true the steward job is skipped, so this watch pauses with it.
- The app's own error alert email or Telegram (`_fire_error_alert`) remains the instant channel
  for a human.
