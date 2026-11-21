# `compute_panchang` is cached on exact coordinates (4 dp), not a 0.5 degree cell

- **Date:** 2026-11-21
- **PR / issue:** #1338

## Why, measured

`muhurat.find_candidates('namkaran', 'Delhi', date(2026, 12, 1), 30)` depended on process
history. After `routes.muhurat._landing_upcoming('griha_pravesh', date(2026, 11, 21))` had run,
Rahu Kaal, Abhijit and choghadiya differed by one printed minute (of 30 dates: Rahu Kaal 4,
Abhijit 2, choghadiya 15). Two processes, same input: finder hash `81276ed5` cold, `5d5bf372` after the landing
call. After the fix both give `81276ed5`.

Cause: `_PANCHANG_CACHE` was keyed on `(date, round(lat*2)/2, round(lon*2)/2, tz)`, a ~55 km
cell, so the first caller in the cell decided the value for everyone. The landing page uses
"New Delhi, India" (28.6138954, 77.2090057), the finder's free-text "Delhi" is (28.6328027,
77.2197713): one cell, ~5 s apart at sunset, which the truncated `%H:%M` display turns into a
whole minute. Exact values for 2026-12-01 (swisseph `rise_trans`, independent of project
code): Delhi sunset 17:23:58, Rahu Kaal 14:46-16:05; New Delhi sunset 17:24:03, Rahu Kaal
14:47-16:05. Drik Panchang, New Delhi, same day: sunrise 06:56, sunset 17:24, Rahu Kalam
14:47-16:05 (fetched 2026-11-21).

**Decision.** Key on `round(lat, 4)`, `round(lon, 4)` (~11 m). `compute_moon_rise_set` already
computes at exact coordinates for the same reason (the printed calendar day flipped on the
grid) and is the precedent. The two nearby free-text cities no longer share an entry; one
compute is ~0.2 ms, so that sharing was worth nothing.

**Rejected.** Making the landing page ask for "Delhi" (hides the defect for one pair of
strings, leaves every other pair in a cell order-dependent). Removing the cache (the finder
calls it up to 90 times per search).

**Bound.** Free-text city input can mint keys, so the dict is cleared at 20,000 entries
(`_PANCHANG_CACHE_MAX`). A clear costs ~0.2 ms per refilled entry. LRU was rejected as more
code than a 0.2 ms recompute justifies.

Pinned by `tests/test_panchang_cache_order_independent.py`; four mutation rows in
`scripts/mutations/2026_11_21_1338_panchang_cache_exact_key.py`. Cost: LLM tokens 0, GCS ops 0.
