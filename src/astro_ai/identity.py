"""Keyed identity hashes, so an event or an alert can say "same person" without saying who.

WHY KEYED. The input is name + birth date + time + place: a small, structured
space. An unsalted hash of it is a lookup table away from the plaintext (try
every plausible date and a list of cities), so hashing alone would be a
disguise. A per-row random salt would fix that but destroy the one property we
want, which is that the same chart produces the same key twice so a Telegram
alert can be matched to its event. A keyed HMAC gives both: stable for us,
unrecoverable without the secret.

`chart.fingerprint_chart` is NOT this and must not be reused for it. It is
unsalted and is used as a GCS path component, which makes it a stable public-ish
identifier; anything written to the events log or sent to Telegram uses
`identity_key` instead.

WHY THE COOKIE SECRET. `ASTRO_AI_COOKIE_SECRET` is already set on the deployed
service (high entropy), so reusing it needs no new environment variable and no
GCP step. A domain-separated subkey is derived from it, so the cookie signer
and this module never use the same key bytes directly.

ROTATION. Changing the secret changes every key. Acceptable: events are only
kept for EVENT_RETENTION_DAYS = 30, so the discontinuity is bounded by that
window, and nothing durable is keyed by it.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Final

_DOMAIN: Final[bytes] = b"bhagya/identity/v1"
_WS = re.compile(r"\s+")
_SEP: Final[str] = "\x1f"  # \s matches it, so _normalise removes it from every part
_SHORT_LEN: Final[int] = 8


def _subkey() -> bytes:
    # Imported here, not at module scope: session imports llm, and this module
    # is meant to be importable from anywhere (notify, events) without
    # risking an import cycle.
    from astro_ai.session import cookie_secret

    return hmac.new(cookie_secret().encode("utf-8"), _DOMAIN, hashlib.sha256).digest()


def _normalise(part: object) -> str:
    return _WS.sub(" ", str(part).casefold()).strip()


def identity_key(*parts: object) -> str:
    """Full hex HMAC-SHA256 over the normalised, unit-separator-joined parts.

    Parts are joined with a separator that cannot occur in user input, so
    ("a|b", "c") and ("a", "b|c") differ; case and runs of whitespace do not
    matter, so "Delhi " and "delhi" key the same.
    """
    joined = _SEP.join(_normalise(p) for p in parts)
    return hmac.new(_subkey(), joined.encode("utf-8"), hashlib.sha256).hexdigest()


def short_key(full: str) -> str:
    """First 8 hex chars: enough to look an event up from an alert, not to identify anyone."""
    return full[:_SHORT_LEN]
