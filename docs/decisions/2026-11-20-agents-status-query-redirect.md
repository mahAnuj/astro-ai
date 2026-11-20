# /api/agents/status 301s any query string to the bare path

- **Date:** 2026-11-20
- **PR / issue:** #1261

## Why, measured

`GET /api/agents/status` reads no parameter, but the CDN keys on the full URL. Against
production, `?x=$RANDOM` returned 200 with `x-cache: MISS` every time: each junk query is a
fresh cache entry and a fresh trip to the Cloud Run instance, all carrying the same document.

Decision: any non-empty query string gets a 301 to `/api/agents/status` (relative `Location`,
nothing echoed from the request), before `asyncio.to_thread`, so a junk query never costs a
worker thread. The 301 carries the same `Access-Control-Allow-Origin` and `Vary: Origin` as the
200 (one shared constant, so they cannot drift) because a browser on anujmahajan.com that
follows a redirect without ACAO fails the fetch. It carries `Cache-Control: public,
max-age=3600`.

What this does and does not buy, stated plainly:

- **Saves** instance CPU and the CDN filling with copies of one document.
- **Does not save GitHub reads or Groq tokens.** `agent_status.snapshot()` is already cached
  in-process (60s with a token, 300s without), so a query-string flood was never a read flood.
- **Firebase may not cache the 301.** Measured on `/kundli/?q=N`: a Cloud Run redirect without
  `Cache-Control` came back `cache-control: private`, `MISS`, so Firebase does not CDN-cache it
  by default. The explicit `public, max-age=3600` here is the attempt to change that; it is not
  yet measured on this route in production. If it still misses, each `?x=N` reaches the instance
  once and gets a few bytes back instead of the JSON path.
- **Not addressed:** capping the instance count (`gcloud run ... --max-instances`) is a separate
  sub-issue of #1261.

Rejected: ignoring the query and serving the 200 (leaves the cache pollution); a 308 (the
endpoint is GET-only, 301 matches `routes/hindi.py`).
