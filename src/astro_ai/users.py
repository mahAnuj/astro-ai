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
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from astro_ai import storage
from astro_ai.session import ChartCollection, MAX_CHARTS, SavedChart

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


# ─── Cross-device chart sync ────────────────────────────────────────────────
# Signed-in users get their SavedChart list synced to users.json — the cookie
# remains the fast local cache but users.json is the cross-device source of
# truth. On sign-in we merge (device charts) ∪ (cross-device charts) and
# write the union back to both places, so charts follow the user.


def _chart_dedup_key(chart: SavedChart) -> tuple[str, str, str]:
    """Charts are considered "the same" when birth details match.

    Case-insensitive place matching so "Delhi" and "delhi" don't dedupe as
    different charts. Time and date are compared as-is (both are stored
    from user input, so they're already in a consistent format).
    """
    return (chart.birth_date, chart.birth_time, chart.birth_place.strip().lower())


def load_charts(sub: str) -> ChartCollection:
    """Load a signed-in user's persisted ChartCollection. Empty if not found."""
    if not sub:
        return ChartCollection(charts=(), active_id=None)
    for row in list_users():
        if row.get("sub") == sub:
            raw = row.get("charts", [])
            try:
                charts = tuple(SavedChart(**c) for c in raw)
            except (TypeError, KeyError):
                charts = ()
            return ChartCollection(charts=charts, active_id=row.get("active_id"))
    return ChartCollection(charts=(), active_id=None)


def save_charts(sub: str, collection: ChartCollection) -> bool:
    """Persist a signed-in user's ChartCollection to users.json.

    Silent failure (returns False + logs) when storage isn't configured or
    when the user doesn't exist in users.json — this is best-effort sync,
    the cookie remains the source of truth for THIS session. The user
    record is expected to already exist (upsert_user runs before this on
    sign-in); if it doesn't, we skip rather than create a phantom record.
    """
    if not sub:
        return False

    def _add(current):
        data = current or {"users": []}
        for existing in data["users"]:
            if existing.get("sub") == sub:
                existing["charts"] = [asdict(c) for c in collection.charts]
                existing["active_id"] = collection.active_id
                return data
        # User not in users.json — skip. upsert_user creates the record;
        # sync should only happen after that. If we hit this, it's a race
        # or an anonymous user; either way, do nothing.
        return None

    result = storage.update_json(USERS_KEY, _add, default={"users": []})
    if result is None:
        log.warning("users.save_charts: storage unavailable or user %s not found", sub)
        return False
    return True


def merge_collections(cookie: ChartCollection, user: ChartCollection) -> ChartCollection:
    """Merge (device charts) ∪ (cross-device charts), dedup by birth details.

    Merge policy:
    - User (cross-device) charts come first — treated as authoritative for
      any dedup collisions (they carry the historical id, may have been
      renamed on another device).
    - Cookie charts NOT already in the user set get appended.
    - Cap at MAX_CHARTS: if total exceeds, drop the tail (least-recently-
      added cookie charts are lost; user's cross-device set is preserved).
    - active_id: prefer cookie's (that's what this device was just looking
      at). If cookie's active didn't survive dedup, fall back to user's
      active. If neither survives, first merged chart.
    """
    seen: set[tuple[str, str, str]] = set()
    merged: list[SavedChart] = []

    for chart in user.charts:
        key = _chart_dedup_key(chart)
        if key not in seen:
            seen.add(key)
            merged.append(chart)

    for chart in cookie.charts:
        key = _chart_dedup_key(chart)
        if key not in seen and len(merged) < MAX_CHARTS:
            seen.add(key)
            merged.append(chart)

    # Cap at MAX_CHARTS — trim from the tail (user's earliest cross-device
    # charts get priority over cookie additions).
    merged = merged[:MAX_CHARTS]

    # Resolve active_id — prefer cookie, then user, then first.
    merged_ids = {c.id for c in merged}
    active_id: Optional[str] = None
    if cookie.active_id and cookie.active_id in merged_ids:
        active_id = cookie.active_id
    elif user.active_id and user.active_id in merged_ids:
        active_id = user.active_id
    elif merged:
        active_id = merged[0].id
    # Also handle: cookie's active chart might have deduped away — find its
    # replacement in the user set by matching birth details.
    if active_id is None and cookie.active_id:
        for c in cookie.charts:
            if c.id == cookie.active_id:
                target_key = _chart_dedup_key(c)
                for m in merged:
                    if _chart_dedup_key(m) == target_key:
                        active_id = m.id
                        break
                break
        if active_id is None and merged:
            active_id = merged[0].id

    return ChartCollection(charts=tuple(merged), active_id=active_id)
