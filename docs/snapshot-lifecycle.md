# Snapshot and event-log lifecycle (#1105)

`src/astro_ai/snapshots.py` says a bucket lifecycle rule deletes snapshots after
30 days and points here. This file is that pointer. It records the rule that is
intended and the command to apply it.

**STATUS: NOT APPLIED — needs someone with bucket access; this doc does not prove the rule is set.**

Nothing in the repository sets, reads back or checks the rule. `load()` in
`snapshots.py` hides a snapshot after `expires_at`, but that only stops it being
served: the blob stays in the bucket until something deletes it. Until the rule
below is applied, nothing does.

## Key prefixes (read from the code, 2026-11-17)

| What | Key | Defined in |
| --- | --- | --- |
| Share-link snapshot (birth details + reading text) | `snapshot/{id}.json` | `snapshots.py` (`_key_for`) |
| Daily event log | `events/YYYY-MM-DD.json` | `events.py` (`_key_for`) |
| Natal reading text (addresses the seeker by name) | `llm/natal/{lang}/{prompt_fp}/{chart_fp}.{name_fp}.txt` | `routes/kundli.py` (`_natal_cache_keys`) |

The `events.py` module docstring says `events/YYYY-MM-DD.jsonl`; the key the code
builds ends `.json`. The rule below matches on the prefix, so it covers both.

`events.py` retains 30 days on READ (`EVENT_RETENTION_DAYS = 30` clamps `recent()`);
it never deletes the blobs either.

## The rule

`lifecycle.json`:

```json
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 30, "matchesPrefix": ["snapshot/", "events/"]}
    }
  ]
}
```

Apply it (replaces the bucket's entire lifecycle configuration, so first read
the current one with `gcloud storage buckets describe` and merge any rule that is
already there):

```bash
gcloud storage buckets describe gs://$BHAGYA_STORAGE_BUCKET --format="default(lifecycle_config)"
gcloud storage buckets update gs://$BHAGYA_STORAGE_BUCKET --lifecycle-file=lifecycle.json
```

`age` counts days since the object was created. Snapshots are written once, so
that is 30 days from creation. A daily event blob is rewritten through the day,
and GCS treats each rewrite as a new object generation, so a day's blob is deleted
30 days after its LAST write.

## What it does not cover

- `users.json` and `subscribers.json` are single blobs, not prefixed objects. They
  are never expired; a signed-in user removes their own entries through
  `POST /account/delete`.
- Natal reading blobs, `llm/natal/{lang}/{prompt_fp}/{chart_fp}.{name_fp}.txt`.
  The reading addresses the seeker by name and the blob never expires. They are
  NOT in the lifecycle rule above. They are erased per chart, for both languages,
  by `POST /account/delete` and `POST /delete-chart` (`erase_natal_blobs` in
  `routes/kundli.py`, #1105), but only under the CURRENT prompt token: the token
  is part of the path, `storage.py` has no prefix listing, so a blob written under
  an earlier prompt version cannot be found and remains. So does a blob written
  under a name the chart no longer carries. Neither is claimed as erased.
- Adding `llm/natal/` to the 30-day rule would close that gap, and would also make
  every natal reading regenerate after 30 days: about 7.8k Groq tokens each,
  against the free-tier 8,000 TPM per-model and daily limits (CLAUDE.md, token
  budget). That is an OWNER DECISION and is not part of the rule as written.
- A snapshot someone shared stays public until it expires or someone deletes the
  blob by hand. There is no self-serve delete for snapshots.

## To verify once applied

```bash
gcloud storage buckets describe gs://$BHAGYA_STORAGE_BUCKET --format="json(lifecycle_config)"
```

Then replace the STATUS line above with the date, who applied it and that output.
