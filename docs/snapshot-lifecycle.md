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
- Natal reading cache blobs keyed by a name fingerprint (`cache.py`) are shared by
  everyone with the same name and birth data and cannot be listed per user
  (`storage.py` has no prefix listing), so account deletion does not remove them.
- A snapshot someone shared stays public until it expires or someone deletes the
  blob by hand. There is no self-serve delete for snapshots.

## To verify once applied

```bash
gcloud storage buckets describe gs://$BHAGYA_STORAGE_BUCKET --format="json(lifecycle_config)"
```

Then replace the STATUS line above with the date, who applied it and that output.
