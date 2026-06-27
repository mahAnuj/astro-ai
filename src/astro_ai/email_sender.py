"""Thin wrapper around Brevo's transactional email API.

Why Brevo: free tier covers 300 emails/day with no card required, the API
is a single POST per email, and dashboard analytics are usable from day one.
SendGrid/Mailgun would also work; Brevo just wins on the free quota.

Configure with:
    BREVO_API_KEY=xkeysib-...        # from https://app.brevo.com/settings/keys/api
    BHAGYA_EMAIL_FROM=hello@bhagya.app   # must be a verified sender in Brevo

If unset, send() returns False without raising — same graceful-fallback
pattern as storage.py, so local dev works with zero email setup.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

import httpx

log = logging.getLogger(__name__)

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"
_DEFAULT_FROM_NAME = "Bhagya"


def _api_key() -> str | None:
    key = os.environ.get("BREVO_API_KEY")
    return key.strip() if key else None


def _from_address() -> tuple[str, str] | None:
    """Return (name, email) for the verified Brevo sender, or None if unset."""
    addr = os.environ.get("BHAGYA_EMAIL_FROM")
    if not addr:
        return None
    return (_DEFAULT_FROM_NAME, addr.strip())


def send(to_email: str, *, subject: str, html: str, text: str | None = None) -> bool:
    """Send one email via Brevo. Returns True on 2xx, False otherwise.

    Caller should treat False as best-effort failure and continue (don't
    blow up the daily-send loop because one bad email bounced).
    """
    api_key = _api_key()
    sender = _from_address()
    if not api_key or not sender:
        log.warning("email_sender.send: BREVO_API_KEY or BHAGYA_EMAIL_FROM unset; skipping send")
        return False

    payload = {
        "sender": {"name": sender[0], "email": sender[1]},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
    }
    if text:
        payload["textContent"] = text

    try:
        r = httpx.post(
            BREVO_ENDPOINT,
            headers={"api-key": api_key, "content-type": "application/json"},
            json=payload,
            timeout=15.0,
        )
        if r.status_code >= 400:
            log.warning("email_sender.send(%s): %s %s", to_email, r.status_code, r.text[:200])
            return False
        return True
    except Exception as err:
        log.warning("email_sender.send(%s): %s", to_email, err)
        return False


def send_bulk(messages: Iterable[dict]) -> tuple[int, int]:
    """Send many emails serially. Returns (sent, failed).

    Each `messages` item: {"to": "...", "subject": "...", "html": "...", "text": "..."}.
    We send one-at-a-time rather than using Brevo's batch endpoint because the
    transactional API caps batches at 1000 anyway and serial keeps the failure
    accounting simple. For a few hundred subscribers this completes in seconds.
    """
    sent = failed = 0
    for msg in messages:
        ok = send(msg["to"], subject=msg["subject"], html=msg["html"], text=msg.get("text"))
        if ok:
            sent += 1
        else:
            failed += 1
    return sent, failed
