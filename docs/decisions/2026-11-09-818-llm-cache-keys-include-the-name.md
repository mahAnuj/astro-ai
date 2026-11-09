# The natal, outlook, today and matching cache keys include the visitor's name

- **Date:** 2026-11-09
- **PR / issue:** #818

## Why, measured

`cache.fingerprint_chart` hashes `birth_date|birth_time|birth_place` and nothing else, but
`llm.py` sends `Name: <name>` (natal, outlook, today) or `GROOM:` / `BRIDE:` (matching) and the
prompts let the model use it. Read in code at d55bf18 and then shown by test: with a fake provider
that echoes the requested name into its reply, two differently-named visitors with identical birth
data made **1** generation, not 2, and the second was shown the first's name on all four of
`/kundli`, `/monthly`, `/yearly`, `/today` (16 of the 26 cases in `tests/test_cache_name_isolation.py` are red on d55bf18 and all 26 are green after, including a
cold start that served the first visitor's name from the durable GCS blob and a pre-seeded old-shape row being served). Natal was
the worst case: that blob never expires and is shared across instances.

Now `cache.fingerprint_name` (NFC, strip, casefold, whitespace collapsed, sha256 truncated to 12
hex; `anon` when blank) is one key segment on each of those routes. Natal's SQLite key and GCS path
come from one helper, `kundli._natal_cache_keys`, used by the render path and the snapshot path, so
they cannot diverge. For matching each person's name hash is attached to that person's chart
fingerprint before the sort, so both names reach the key and swapping the two people still hits.

Rejected, with the architect's reasons on the issue: render-time substitution of a placeholder
(five `prompts/` edits, six consumers, still orphans every natal blob); putting the name in
`fingerprint_chart` (would split `/ask`, `/dasha` and matching's pair key, which do not carry it);
bumping `PROMPT_LOGIC_VERSION` (global: it would also regenerate rashifal and daily against the same
~200k tokens/day); a post-generation scrub (fails open on any variant of the name); `identity_key`
as the segment (its HMAC rotates with the cookie secret).

Cost: 0 added tokens per call, no prompt touched. Old natal blobs become unreachable and each
returning visitor regenerates once (worst-case fixture 6,748 input tokens per `verify_token_budget.py`).
The old blobs, some containing names, stay in the bucket; they cannot be listed and deleting them is
the owner's decision. Not fixed here: `/ask` with `context=numerology` has the same shape for
name-derived numbers.
