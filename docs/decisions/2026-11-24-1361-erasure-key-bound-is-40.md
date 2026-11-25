# The natal-erasure key bound is 40, not 20

- **Date:** 2026-11-24
- **PR / issue:** #1361 (corrects the arithmetic in `2026-11-21-natal-erasure-evicts-sqlite.md`, #1293)

## Why, measured

`2026-11-21-natal-erasure-evicts-sqlite.md` and its code comments said "up to 20" sequential
deletes and "at most ~20 keys". That counted one chart list (`MAX_CHARTS=10` x 2 languages).
`/account/delete` passes `[*cookie charts, *record charts]`, each list capped at
`MAX_CHARTS=10` (`session.py`), so the ceiling is 2 x 10 x 2 = **40** blob deletes and 40
SQLite keys. It is a ceiling, not the typical case: the lists can overlap and
`erase_natal_blobs` builds sets. `/delete-chart` passes one chart, so 2 keys.

The decision itself is unchanged: still no chunking, because 40 is far under SQLite's
bound-variable limit (999 on builds before 3.32, 32766 from 3.32), and the deletes still run
in a threadpool. Re-check the bound if `MAX_CHARTS` is raised. The comments in `cache.py`
(`delete_many`) and `routes/kundli.py` (`erase_natal_blobs`), and `ARCHITECTURE.md`, now say 40.

Rejected: a test asserting `2 * 2 * MAX_CHARTS <= 999`. It would guard a number 25x under the
limit; `MAX_CHARTS` would have to reach about 250 before it bound. 0 LLM tokens.
