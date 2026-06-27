"""Subscriber list for the daily Rashifal email.

Storage: a single JSON file in the same GCS bucket we use for caching
(gs://$BHAGYA_STORAGE_BUCKET/subscribers.json). Cheap, easy to inspect,
and good enough for the MVP scale (low-hundreds of subscribers).

Concurrency: subscribes go through storage.update_json which uses GCS
object-generation matching, so two POSTs landing in the same instant
can't lose each other.

When this grows past ~10k subscribers or we need real queries, migrate
to Firestore — the API surface here (subscribe / unsubscribe / list)
stays the same; only the backend swaps.
"""

from __future__ import annotations

import hmac
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Iterable

from astro_ai import storage

log = logging.getLogger(__name__)

SUBSCRIBERS_KEY = "subscribers.json"

# Relaxed RFC-5321ish email regex — good enough to catch obvious typos
# without rejecting legitimate addresses. Brevo will validate properly
# on actual delivery.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _normalize(email: str) -> str:
    return email.strip().lower()


def _unsubscribe_secret() -> bytes:
    """HMAC key for tamper-proof unsubscribe links.

    Reuses the cookie secret so we don't have to manage another env var.
    If the secret is unset, fall back to a clearly-flagged dev string —
    same convention as ADMIN_PASSWORD in main.py.
    """
    return os.environ.get("ASTRO_AI_COOKIE_SECRET", "bhagya-dev-only-CHANGE-ME").encode()


def unsubscribe_token(email: str) -> str:
    """Generate a stable per-email HMAC token for one-click unsubscribe."""
    return hmac.new(_unsubscribe_secret(), _normalize(email).encode(), hashlib.sha256).hexdigest()[:24]


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Constant-time check that `token` matches `email`."""
    return hmac.compare_digest(unsubscribe_token(email), token)


def subscribe(email: str, lang: str = "en", city: str = "") -> tuple[bool, bool, str]:
    """Add a subscriber. Returns (ok, is_new, message).

    `is_new` is True only when this email wasn't in the list before; callers
    use it to decide whether to send the welcome email (we don't want to
    re-welcome someone who re-subscribed by accident).

    `city` is optional — when set, the daily email computes Panchang for
    that location. Blank/missing falls back to a sensible default at send
    time.

    Idempotent: re-subscribing the same email keeps the original timestamp
    but updates `lang` and `city` if the user changed either.
    """
    email = _normalize(email)
    if not _EMAIL_RE.match(email):
        return False, False, "Please enter a valid email address."
    if lang not in {"en", "hi"}:
        lang = "en"
    city = (city or "").strip()[:80]  # cap length to keep cookies/payloads sane

    state = {"was_new": True}

    def _add(current):
        data = current or {"subscribers": []}
        for existing in data["subscribers"]:
            if existing["email"] == email:
                existing["lang"] = lang
                if city:
                    existing["city"] = city
                state["was_new"] = False
                return data
        entry = {
            "email": email,
            "lang": lang,
            "subscribed_at": _now_iso(),
        }
        if city:
            entry["city"] = city
        data["subscribers"].append(entry)
        return data

    result = storage.update_json(SUBSCRIBERS_KEY, _add, default={"subscribers": []})
    if result is None:
        return False, False, "Couldn't save your subscription right now. Please try again later."
    return True, state["was_new"], "Subscribed."


def unsubscribe(email: str) -> tuple[bool, str]:
    """Remove a subscriber. Idempotent."""
    email = _normalize(email)

    def _remove(current):
        data = current or {"subscribers": []}
        data["subscribers"] = [s for s in data["subscribers"] if s["email"] != email]
        return data

    result = storage.update_json(SUBSCRIBERS_KEY, _remove, default={"subscribers": []})
    if result is None:
        return False, "Couldn't update your subscription right now."
    return True, "Unsubscribed."


def list_subscribers() -> list[dict]:
    """All current subscribers. Empty list if storage unavailable or empty."""
    data = storage.get_json(SUBSCRIBERS_KEY)
    if not data:
        return []
    return data.get("subscribers", [])


def count() -> int:
    """Quick subscriber count for the admin dashboard."""
    return len(list_subscribers())
