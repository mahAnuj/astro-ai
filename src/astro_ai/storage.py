"""Generic GCS-backed key→file storage with graceful local fallback.

A thin wrapper around google-cloud-storage that lets callers persist any
string (LLM output, JSON, whatever) under any key. Used by features whose
output is genuinely shared across users — today that's just Rashifal, but
the API is intentionally not Rashifal-specific.

Region: US multi-region keeps the bucket inside GCS Always-Free
(5 GB / 5K writes / 50K reads / 100 GB egress per month). Adds ~100-200ms
vs a Mumbai bucket but the trade-off is $0 forever.

Setup:
    1. Create a GCS bucket in a US Always-Free region.
    2. Set BHAGYA_STORAGE_BUCKET=<bucket-name> in your env.
    3. On Cloud Run: the service account needs Storage Object Admin on the
       bucket. Locally: `gcloud auth application-default login`.

Graceful degradation: if the env var is unset, google-cloud-storage isn't
installed, or any GCS call fails, `get`/`put` return None/False. The caller
falls through to whatever local cache it has. Means local dev needs zero
GCS setup.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_BUCKET_ENV = "BHAGYA_STORAGE_BUCKET"


def _bucket_name() -> str | None:
    name = os.environ.get(_BUCKET_ENV)
    return name.strip() if name else None


def _client():
    """Lazy-import google-cloud-storage so it's truly optional at runtime."""
    try:
        from google.cloud import storage  # type: ignore[attr-defined]
        return storage.Client()
    except Exception as err:
        log.warning("storage: GCS unavailable (%s); falling back to local cache", err)
        return None


def _blob(key: str):
    """Resolve a bucket blob for `key`, or None if storage isn't configured."""
    bucket_name = _bucket_name()
    if not bucket_name:
        return None
    client = _client()
    if client is None:
        return None
    return client.bucket(bucket_name).blob(key)


def get(key: str) -> str | None:
    """Read the value at `key`. Returns None if absent or GCS unavailable."""
    blob = _blob(key)
    if blob is None:
        return None
    try:
        if not blob.exists():
            return None
        return blob.download_as_text()
    except Exception as err:
        log.warning("storage.get(%s) failed: %s", key, err)
        return None


def put(key: str, value: str, *, content_type: str = "text/plain; charset=utf-8") -> bool:
    """Write `value` at `key`. Returns True on success, False otherwise.

    Caller should treat False as best-effort failure — local caches still
    work, the write just won't survive process death.
    """
    blob = _blob(key)
    if blob is None:
        return False
    try:
        blob.upload_from_string(value, content_type=content_type)
        return True
    except Exception as err:
        log.warning("storage.put(%s) failed: %s", key, err)
        return False


def get_json(key: str) -> Any | None:
    """Read `key` and parse as JSON. None if missing or malformed."""
    raw = get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as err:
        log.warning("storage.get_json(%s): invalid JSON (%s)", key, err)
        return None


def put_json(key: str, value: Any) -> bool:
    """Serialize `value` as JSON and write to `key`."""
    return put(key, json.dumps(value, ensure_ascii=False), content_type="application/json")


def update_json(key: str, mutator, *, default: Any = None, max_retries: int = 5) -> Any | None:
    """Atomically read-modify-write a JSON value at `key`.

    Uses GCS object-generation matching for compare-and-swap, so two concurrent
    writers can't silently clobber each other (e.g. two subscriptions arriving
    in the same second). Returns the final value (post-mutation) on success,
    or None if the underlying storage is unavailable.

    `mutator(current_value) -> new_value` may freely mutate or return a new
    object; it should NOT have side effects beyond returning the next state
    because we'll re-invoke it on contention.

    `default` is what mutator receives when the key doesn't yet exist.
    """
    bucket_name = _bucket_name()
    if not bucket_name:
        log.warning("storage.update_json(%s): no bucket configured", key)
        return None
    client = _client()
    if client is None:
        return None

    import time as _t  # local: only used in this rare path
    blob = client.bucket(bucket_name).blob(key)

    for attempt in range(max_retries):
        try:
            blob.reload()  # populates blob.generation (None if missing)
            generation = blob.generation
            if generation is not None:
                current = json.loads(blob.download_as_text())
            else:
                current = default
        except Exception as err:
            # Most likely the blob doesn't exist yet (404). Treat as initial.
            log.debug("storage.update_json(%s) read-miss: %s", key, err)
            generation = 0  # 0 = "must not exist" precondition in GCS
            current = default

        new_value = mutator(current)
        body = json.dumps(new_value, ensure_ascii=False)

        try:
            # if_generation_match enforces CAS — write only if the blob's
            # generation hasn't changed since our read. 0 means "blob must
            # not exist", a positive number means "must be this exact gen".
            blob.upload_from_string(
                body,
                content_type="application/json",
                if_generation_match=generation if generation is not None else 0,
            )
            return new_value
        except Exception as err:
            # 412 Precondition Failed → another writer beat us. Retry the
            # read-modify-write loop with the latest generation.
            log.info("storage.update_json(%s) CAS miss on attempt %d: %s",
                     key, attempt + 1, err)
            _t.sleep(0.05 * (2 ** attempt))  # exponential backoff

    log.error("storage.update_json(%s) gave up after %d retries", key, max_retries)
    return None
