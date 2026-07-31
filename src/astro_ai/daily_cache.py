"""File-based daily cache — one JSON file per (namespace, key, date).

Wraps expensive-once-per-day computations (LLM-generated rashifal, per-location
panchang) so a same-day request never triggers regeneration. The file is
overwritten on a new day and is human-readable for debugging — `cat` any file
in `data/daily_cache/` to see exactly what was served.

Design vs the 3-tier GCS+SQLite+LLM cache in main.py:
  - This layer sits IN FRONT of the 3-tier cache for rashifal — a same-instance
    same-day hit skips SQLite/GCS/LLM entirely (fastest path).
  - For panchang (pure-math, no LLM), this layer is the only cache we need.
  - Ephemeral disk on Cloud Run means cross-instance still relies on GCS for
    rashifal; panchang is cheap enough to just recompute per-instance.

The file naming carries `date_iso` in the filename so a new day naturally
supersedes the old file without needing a background purge job. A small
housekeeping helper `purge_older_than_days()` runs opportunistically on write
to keep the folder from growing forever.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")

# `data/` is already gitignored, works in both local dev and Cloud Run
# (writable /app/data on Cloud Run since we don't run as read-only fs).
_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "daily_cache"
_ROOT = Path(os.environ.get("BHAGYA_DAILY_CACHE_DIR", str(_DEFAULT_ROOT)))

_RETENTION_DAYS = 7


def _path_for(namespace: str, key: str, date_iso: str) -> Path:
    """Build the on-disk path for one cache entry. Ensures parent dir exists."""
    safe_key = key.replace("/", "_").replace(" ", "_").lower()
    subdir = _ROOT / namespace
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / f"{date_iso}-{safe_key}.json"


def get(namespace: str, key: str, date_iso: str | None = None) -> dict | None:
    """Return today's cached payload for (namespace, key), or None on miss.

    Silently returns None on any I/O or JSON error — cache is best-effort;
    caller should generate fresh on None.
    """
    d = date_iso or date.today().isoformat()
    p = _path_for(namespace, key, d)
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as err:  # noqa: BLE001
        log.warning("daily_cache read failed for %s: %s — treating as miss", p, err)
        return None


def put(namespace: str, key: str, payload: dict, date_iso: str | None = None) -> None:
    """Write today's payload atomically. Runs opportunistic housekeeping.

    Atomic write via NamedTemporaryFile + rename — a partially-written file
    could be read as garbage by a concurrent request.
    """
    d = date_iso or date.today().isoformat()
    p = _path_for(namespace, key, d)
    payload = {**payload, "_cached_at": datetime.utcnow().isoformat() + "Z", "_date": d}
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=p.parent, delete=False, suffix=".tmp", encoding="utf-8",
        ) as tf:
            json.dump(payload, tf, ensure_ascii=False, indent=2)
            tmp_path = tf.name
        os.replace(tmp_path, p)
    except Exception as err:  # noqa: BLE001
        log.warning("daily_cache write failed for %s: %s — carrying on", p, err)
        return
    try:
        _purge_older_than_days(namespace, _RETENTION_DAYS)
    except Exception:  # noqa: BLE001 — housekeeping never breaks the request
        log.debug("daily_cache purge failed", exc_info=True)


def get_or_compute(
    namespace: str,
    key: str,
    compute_fn: Callable[[], dict],
    date_iso: str | None = None,
) -> dict:
    """Common shape: return cached payload or generate + cache in one call.

    `compute_fn` must return a dict — that's what gets serialised. Wrap
    non-dict payloads at the call site (e.g. `{"text": llm_output}`).
    """
    hit = get(namespace, key, date_iso)
    if hit is not None:
        return hit
    payload = compute_fn()
    put(namespace, key, payload, date_iso)
    return payload


def _purge_older_than_days(namespace: str, retention_days: int) -> None:
    """Remove cache files with a date-prefix older than `retention_days` ago."""
    subdir = _ROOT / namespace
    if not subdir.exists():
        return
    cutoff = date.today() - timedelta(days=retention_days)
    for entry in subdir.iterdir():
        if not entry.is_file() or not entry.suffix == ".json":
            continue
        # Filename format is `{YYYY-MM-DD}-{key}.json` — parse the date prefix.
        stem = entry.stem
        if len(stem) < 10 or stem[4] != "-" or stem[7] != "-":
            continue
        try:
            entry_date = date.fromisoformat(stem[:10])
        except ValueError:
            continue
        if entry_date < cutoff:
            try:
                entry.unlink()
            except OSError:
                pass
