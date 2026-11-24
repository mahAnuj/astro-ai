# Natal erasure evicts the SQLite rows after the GCS delete, off the event loop

- **Date:** 2026-11-21
- **PR / issue:** #1293

## Why, measured

After `/account/delete` or `/delete-chart` the GCS blobs went (#1105) but the serving
instance's SQLite cache (`llm_cache`, `ttl_days=None`) still held the same readings, so a
warm instance kept serving a deleted chart's natal reading, which addresses the seeker by
name. `cache.py` had no delete. Separately, up to 20 sequential `storage.delete` calls (2
languages x 10 charts; bucket in the US, service in asia-south1) ran inside `async def`
handlers and blocked the event loop for every other request on the instance.

Change: `cache.delete_many(keys)` (one statement, one lock, returns the row count);
`kundli.natal_sqlite_keys` beside `natal_blob_keys`, both from `_natal_cache_keys`;
`erase_natal_blobs` deletes the blobs, then evicts in a `finally`; both handlers call it
through `run_in_threadpool`. 0 LLM tokens, no prompt touched.

- **GCS first, SQLite last, always.** `_cached` backfills SQLite after a durable hit, so
  evicting first lets a concurrent view re-warm the row from the blob still in the bucket.
  The `finally` means a raising delete still evicts. An eviction error is logged (no keys:
  they hash birth data and the name) and does not change the return value.
- **Limit, stated plainly:** only the instance serving the delete is cleared. The other
  instances (up to 5, each its own `/tmp` SQLite) cannot be reached, and nothing in the app
  can reach them. A deleted reading can be served there until it is evicted or the instance
  recycles. Reaching them needs a shared channel (a tombstone checked on read, a pub/sub),
  which is a human decision.
- **Accepted residual race:** a generation already in flight on another request when the
  delete runs can write its row (and blob) after the erasure. The delete is idempotent; a
  retry clears it.

## Rejected

- **Evict first, then delete blobs:** the re-warm race above.
- **An executor inside `erase_natal_blobs`:** it would hide the blocking call from the
  caller; the function stays sync and the async handlers own the offloading.
- **An async wrapper function:** a second public entry to keep in step with the first, for
  one `run_in_threadpool` line at each of two call sites.
- **Bumping `PROMPT_LOGIC_VERSION`:** reaches every instance but regenerates every cached
  reading site-wide against the free-tier ceiling, to delete one user's data.
- **A tombstone blob checked on read:** a per-render GCS read on the hot path (#144).
- **A per-chart `LIKE` purge of SQLite** (all prompt versions): deferred. Keys embed the
  prompt token, so only the current token's rows are evicted, as for the blobs.
- **Cross-instance purge:** needs a shared channel; see the limit above.
