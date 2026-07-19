"""Persistent user store — signed-in Google users, keyed by Google `sub`.

Storage: a single JSON file in the same GCS bucket we use for other shared
state (gs://$BHAGYA_STORAGE_BUCKET/users.json). Same pattern as subscribers.py
— cheap, inspectable, and good enough for the MVP scale (low thousands of
users). When we outgrow flat-file JSON, migrate to Firestore; the API
surface here (upsert / find / count / list) stays the same, only the
storage backend swaps.

WHY GOOGLE `sub` AS PRIMARY KEY (not email):

The Google-issued `sub` (subject) is a stable, opaque unique identifier
that never changes — even if the user changes their Gmail address, links
a new backup email, or migrates their account. Email is a display value,
not an identity value. Using `sub` as the primary key keeps our records
correct across any Google-side account changes.

FIELDS:

At sign-in time we persist the minimum needed for Premium to work later:
- sub, email, name — identity
- created_at — first-ever sign-in (never changes)
- last_seen_at — updated every sign-in

Premium-related fields (premium_status, premium_expires_at,
razorpay_customer_id) will be added by the Premium build without needing
to change this module's API — upsert_user preserves any extra fields it
finds on an existing record.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from astro_ai import storage

log = logging.getLogger(__name__)

USERS_KEY = "users.json"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class User:
    """One persisted user — the shape returned by find_by_sub / find_by_email."""

    sub: str            # Google's stable unique ID — primary key
    email: str          # display value; may change over time
    name: str           # display name from Google; may be empty
    created_at: str     # ISO timestamp of very first sign-in
    last_seen_at: str   # ISO timestamp of most recent sign-in

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        """Best-effort parse — tolerate old records with missing fields."""
        return cls(
            sub=str(d.get("sub", "")),
            email=str(d.get("email", "")),
            name=str(d.get("name", "")),
            created_at=str(d.get("created_at", "")),
            last_seen_at=str(d.get("last_seen_at", "")),
        )


def upsert_user(sub: str, email: str, name: str) -> tuple[bool, bool]:
    """Create or refresh a user record. Returns (ok, is_new).

    Idempotent: called on every sign-in. If the user already exists,
    updates email + name (in case Google-side changed) + last_seen_at.
    If new, creates the record with created_at = last_seen_at = now.

    Preserves any extra fields on the existing record — this is what
    keeps Premium subscription state safe when we add it later. Do NOT
    replace records wholesale here.

    Silent failure: if storage isn't configured (no BHAGYA_STORAGE_BUCKET
    locally without a fallback), returns (False, False) and logs a
    warning. The auth flow itself still succeeds — persistence is best-
    effort, not a hard dependency.
    """
    email = email.strip().lower()
    if not sub or not email:
        return False, False

    state = {"was_new": True}
    now = _now_iso()

    def _add(current):
        data = current or {"users": []}
        for existing in data["users"]:
            if existing.get("sub") == sub:
                # Refresh mutable fields; preserve everything else (future
                # premium_* keys, referrals, etc.).
                existing["email"] = email
                if name:
                    existing["name"] = name
                existing["last_seen_at"] = now
                state["was_new"] = False
                return data
        # New user — full record.
        data["users"].append({
            "sub": sub,
            "email": email,
            "name": name,
            "created_at": now,
            "last_seen_at": now,
        })
        return data

    result = storage.update_json(USERS_KEY, _add, default={"users": []})
    if result is None:
        log.warning("users.upsert_user: storage unavailable — user not persisted")
        return False, False
    return True, state["was_new"]


def find_by_sub(sub: str) -> Optional[User]:
    """Look up a user by Google sub. Returns None if not found."""
    if not sub:
        return None
    data = storage.get_json(USERS_KEY)
    if not data:
        return None
    for row in data.get("users", []):
        if row.get("sub") == sub:
            return User.from_dict(row)
    return None


def find_by_email(email: str) -> Optional[User]:
    """Look up a user by email (case-insensitive). Returns None if not found.

    Prefer find_by_sub for identity lookups — email is a display value that
    can change; sub is the stable primary key. Use email lookups only for
    admin / support / migration flows.
    """
    if not email:
        return None
    email = email.strip().lower()
    data = storage.get_json(USERS_KEY)
    if not data:
        return None
    for row in data.get("users", []):
        if row.get("email", "").strip().lower() == email:
            return User.from_dict(row)
    return None


def list_users() -> list[dict]:
    """All persisted users as raw dicts. Empty list if storage empty."""
    data = storage.get_json(USERS_KEY)
    if not data:
        return []
    return data.get("users", [])


def count() -> int:
    """Total signed-up user count for the /admin/usage dashboard."""
    return len(list_users())
