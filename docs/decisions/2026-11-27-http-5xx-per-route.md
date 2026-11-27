# Per-route HTTP 5xx is counted by an innermost ASGI middleware into its own coalesced day blob

- **Date:** 2026-11-27
- **PR / issue:** #1506

## Why, measured

The analyst reported "HTTP 5xx per route: no data" every week; nothing recorded a 5xx against the
route that served it. `events.record(type="error")` is a per-event row labelled by a hand-written
`source`, kept 30 days, and never sees an inline `status_code=503` page (the "every LLM provider is
exhausted" pages). The count is taken at the ASGI `send`, where every response passes.

Three things in the brief were wrong or missing, found by probe (`scope["route"]` on Starlette
1.3.1 / FastAPI 0.138.1) before building:

1. **`llm_stats` does not batch writes.** Every `record()` is its own `storage.update_json` CAS
   write, so there is no buffer to reuse; a naive counter would be one write per failed request,
   which is a CAS storm and a Class A burn exactly during an incident. `http_errors` has its own
   locked in-process dict, flushed at most once per 600 s per process and at shutdown.
2. **A middleware at the end of the stack cannot see the route in production.** The router sets
   `scope["route"]` on the scope dict it is handed; `_RewriteHostFromForwardedMiddleware` replaces it
   with a copy whenever `X-Forwarded-Host` is present, which Firebase always sets. Outside it the
   route reads `None` and every 5xx would be labelled `unmatched`. So the middleware is added before
   the rewrite (innermost); `tests/test_http_errors.py` pins the order and the forwarded-host case.
3. **An unhandled exception never reaches a user middleware as a response** (`ServerErrorMiddleware`,
   outermost, renders it). The middleware counts a 500 and re-raises; HTTPException 5xx and inline
   5xx are read from `http.response.start`.

Choices:

- **A separate blob (`http_errors/`), not a key in `llm_stats/`.** Failure isolation: a storm cannot
  starve `llm_stats.record()` of its CAS retries, and a bad write cannot corrupt the token-ceiling
  numbers. Cost: 7 extra reads once a week in the collector.
- **Label = `"<METHOD> <route template>"`**, capped at 100 labels a day (overflow folds into
  `"other"`); never the raw path, query, IP, header or cookie. 4xx is not counted (scanner 404s).
- **A boot marker (`boots`)** makes a day with any instance start have a blob, so the collector can
  say "no errors on N of 7 days" rather than treat a missing blob as zero (`storage.get` cannot tell
  missing from unavailable). `http_5xx_days_recorded` is exported beside the total; `null` is unknown,
  never 0.
- **The flush is awaited (3 s cap) after the response, not a background thread:** Cloud Run is
  request-billed and a thread can be CPU-throttled once the response is done.
- The collector reads it as its own failure domain: an unreadable record yields null keys, and the
  LLM snapshot still lands.

Rejected: a Cloud Run request-log read in the collector (needs a logging scope, i.e. a workflow or
credential change); a new workflow step; `events.py` (per-event rows, a trust-boundary file, no route
template, misses inline 503s); hooking only the two exception handlers (misses inline 5xx); a write
per 5xx; `hot_cache` (a read memo, not a write buffer); a raw-path label (unbounded keyspace).

Tokens: 0, no LLM call. Not measured: the cold-start rate that sizes the boot marker's Class A cost
(see ARCHITECTURE.md §4, "5xx recorder").
