"""Public read-only snapshots of Kundli readings — WhatsApp-share support.

When a user wants to share their reading via WhatsApp (or any other
messenger), we can't attach a file to the wa.me URL scheme — the scheme
only accepts text. So we generate a **public read-only URL** the recipient
can open in a browser: `https://shubhagya.com/r/9AK2X7Q`.

Storage: single JSON blob per snapshot at `snapshot/{id}.json` in the
existing GCS bucket (falls back to local /tmp when unconfigured). Uses
the generic storage.py wrapper, same pattern as Rashifal + users.py.

Expiry: 30 days from creation. Enforced two ways:
  (1) `expires_at` field checked on every load() — expired snapshots
      return None as if they didn't exist.
  (2) Bucket-level GCS lifecycle rule auto-deletes objects with prefix
      `snapshot/` after 30 days. Set up once in GCS console; requires
      no code. See docs/snapshot-lifecycle.md for the exact rule.

IDs are unguessable — 4-byte URL-safe tokens (~6-7 chars, 2^32 space).
Not enumerable; someone would need to try ~2B URLs to hit one at random.

Privacy: snapshot stores birth details + reading text. Owner opts in at
creation time (by clicking "Share"). Deletion request → owner emails us
with the short URL → we delete the blob manually. Full DPDPA compliance
would need a self-serve delete endpoint; punted for MVP.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from astro_ai import storage

log = logging.getLogger(__name__)

# 30 days per user decision — long enough for casual recipients to
# revisit, short enough to keep PII from lingering indefinitely.
SNAPSHOT_TTL_DAYS = 30

# 4 bytes = ~6-7 URL-safe chars = 2^32 space. Collision-safe for our
# scale (thousands of snapshots per year, not billions).
_ID_BYTES = 4

# Local filesystem fallback for when GCS isn't configured (dev + preview
# environments). Prod always has BHAGYA_STORAGE_BUCKET set and never
# falls through to this path. On Cloud Run /tmp is the only writable dir
# and gets wiped on cold start — that's fine, snapshots are ephemeral.
_LOCAL_FALLBACK_DIR = Path(os.environ.get("BHAGYA_SNAPSHOT_FALLBACK_DIR", "/tmp/bhagya_snapshots"))


def _local_write(short_id: str, data: dict) -> bool:
    try:
        _LOCAL_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        (_LOCAL_FALLBACK_DIR / f"{short_id}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        return True
    except OSError as err:
        log.warning("snapshots local-fallback write failed: %s", err)
        return False


def _local_read(short_id: str) -> Optional[dict]:
    path = _LOCAL_FALLBACK_DIR / f"{short_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        log.warning("snapshots local-fallback read failed: %s", err)
        return None


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _parse_iso(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _blob_key(short_id: str) -> str:
    return f"snapshot/{short_id}.json"


@dataclass(frozen=True)
class Snapshot:
    """One shared reading — everything needed to re-render the /r/{id} page."""

    id: str
    created_at: str          # ISO timestamp
    expires_at: str          # ISO timestamp — enforced by load()
    lang: str                # 'en' or 'hi'
    birth_details: dict      # {name, birth_date, birth_time, birth_place}
    reading_text: str        # raw LLM output; snapshot page re-parses sections
    created_by_sub: str = "" # optional Google sub of creator, for future analytics

    @classmethod
    def from_dict(cls, d: dict) -> "Snapshot":
        return cls(
            id=str(d.get("id", "")),
            created_at=str(d.get("created_at", "")),
            expires_at=str(d.get("expires_at", "")),
            lang=str(d.get("lang", "en")),
            birth_details=dict(d.get("birth_details", {})),
            reading_text=str(d.get("reading_text", "")),
            created_by_sub=str(d.get("created_by_sub", "")),
        )

    def is_expired(self) -> bool:
        exp = _parse_iso(self.expires_at)
        if exp is None:
            return True   # unparseable expiry → treat as expired for safety
        return _now() >= exp


def create(
    *,
    birth_details: dict,
    reading_text: str,
    lang: str,
    created_by_sub: str = "",
) -> Optional[Snapshot]:
    """Persist a new snapshot and return it. None on storage failure."""
    now = _now()
    snap = Snapshot(
        id=secrets.token_urlsafe(_ID_BYTES),
        created_at=_iso(now),
        expires_at=_iso(now + timedelta(days=SNAPSHOT_TTL_DAYS)),
        lang=lang,
        birth_details=birth_details,
        reading_text=reading_text,
        created_by_sub=created_by_sub,
    )
    data = asdict(snap)
    if storage.put_json(_blob_key(snap.id), data):
        return snap
    # GCS unavailable → local fallback for dev / preview / cold-start Cloud Run.
    if _local_write(snap.id, data):
        log.info("snapshots.create: wrote to local fallback (GCS unavailable)")
        return snap
    log.warning("snapshots.create: both GCS and local fallback failed")
    return None


def load(short_id: str) -> Optional[Snapshot]:
    """Fetch a snapshot by id. Returns None if missing OR expired.

    Silently returns None for expired snapshots — the /r/{id} handler
    should render a friendly 'this link expired' page, not distinguish
    'expired' from 'never existed'.
    """
    # Basic sanity — reject anything that couldn't be a token_urlsafe output
    # to avoid probing GCS for weird keys.
    if not short_id or len(short_id) > 32 or not all(
        c.isalnum() or c in "-_" for c in short_id
    ):
        return None
    data = storage.get_json(_blob_key(short_id))
    if data is None:
        # GCS miss → try local fallback (dev / preview / same-instance write).
        data = _local_read(short_id)
        if data is None:
            return None
    snap = Snapshot.from_dict(data)
    if snap.is_expired():
        return None
    return snap
