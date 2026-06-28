"""User feedback collection — bugs, feature requests, general thoughts.

Storage shape (same pattern as subscribers.py):
    gs://$BHAGYA_STORAGE_BUCKET/feedback.json
    {
      "entries": [
        {
          "id": "abc12345",
          "type": "problem" | "feature" | "other",
          "message": "...",
          "email": "..." | "",        # optional
          "page": "/kundli",          # where the feedback was sent from
          "ua": "Mozilla/5.0...",     # user-agent, truncated
          "ts": "2026-06-28T07:42:00+00:00"
        },
        ...
      ]
    }

Concurrency-safe via storage.update_json's CAS retry loop — multiple
visitors submitting feedback in the same instant can't lose each other.

When this volume grows past a few hundred entries / month, migrate to a
real DB. For now JSON-in-GCS is dead simple and free.
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timezone

from astro_ai import storage

log = logging.getLogger(__name__)

FEEDBACK_KEY = "feedback.json"

# Same relaxed email check used by subscribers.py — Brevo validates harder
# on actual delivery. Empty email is allowed (anonymous feedback).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

VALID_TYPES = {"problem", "feature", "other"}
MAX_MESSAGE = 2000   # 2 KB ceiling so one prankster can't bloat the JSON
MAX_PAGE = 200
MAX_UA = 300


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def add(*, type: str, message: str, email: str = "",
        page: str = "", user_agent: str = "") -> tuple[bool, str, dict | None]:
    """Persist a feedback entry. Returns (ok, error_message, entry_or_none).

    The entry dict is returned on success so callers (admin notification
    email, analytics event) can reference its id / timestamp without
    re-reading from GCS.
    """
    # Validate inputs — fail loudly here rather than write garbage to GCS.
    if type not in VALID_TYPES:
        return False, f"type must be one of {sorted(VALID_TYPES)}", None
    message = (message or "").strip()
    if not message:
        return False, "Please write something in the message.", None
    if len(message) > MAX_MESSAGE:
        return False, f"Message is too long (max {MAX_MESSAGE} characters).", None
    email = (email or "").strip().lower()
    if email and not _EMAIL_RE.match(email):
        return False, "That email doesn't look right.", None

    entry = {
        "id": secrets.token_hex(4),
        "type": type,
        "message": message,
        "email": email,
        "page": (page or "")[:MAX_PAGE],
        "ua": (user_agent or "")[:MAX_UA],
        "ts": _now_iso(),
    }

    def _append(current):
        data = current or {"entries": []}
        data["entries"].append(entry)
        return data

    result = storage.update_json(FEEDBACK_KEY, _append, default={"entries": []})
    if result is None:
        return False, "Couldn't save right now. Please try again in a moment.", None
    return True, "Saved.", entry


def list_all() -> list[dict]:
    """Read every feedback entry. Most-recent-first, for the admin view."""
    data = storage.get_json(FEEDBACK_KEY)
    if not data:
        return []
    entries = data.get("entries", [])
    return list(reversed(entries))  # most recent first


def count() -> int:
    """Quick stat for the admin dashboard."""
    data = storage.get_json(FEEDBACK_KEY)
    return len(data.get("entries", [])) if data else 0
