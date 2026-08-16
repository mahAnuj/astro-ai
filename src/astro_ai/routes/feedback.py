"""Feedback widget — the single submit endpoint behind the floating modal (issue #154).

Owns:
    POST /feedback  persist one entry to GCS, then Telegram + email the owner

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only. Note this module SHADOWS the top-level ``astro_ai.feedback``
store within the ``astro_ai.routes`` package, so the store must always be reached
by its absolute name; a relative import here would self-import and fail obscurely.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse

from astro_ai import email_sender, feedback, notify

router = APIRouter()


@router.post("/feedback")
async def submit_feedback(
    request: Request,
    type: str = Form("other"),
    message: str = Form(""),
    email: str = Form(""),
    page: str = Form(""),
) -> JSONResponse:
    """Persist a feedback entry to GCS + notify admin via email.

    Called from the floating feedback widget via fetch(). Returns JSON
    `{ok: true}` on success or `{ok: false, error: ...}` for inline
    error display in the modal.
    """
    user_agent = request.headers.get("user-agent", "")
    ok, msg, entry = feedback.add(
        type=type, message=message, email=email,
        page=page, user_agent=user_agent,
    )
    if not ok:
        return JSONResponse({"ok": False, "error": msg}, status_code=400)

    # Telegram alert for the owner — feedback should never sit unread.
    try:
        notify.feedback_submitted(
            type=entry["type"] if entry else type,
            message=entry["message"] if entry else message,
            page=entry.get("page", "") if entry else page,
            email=entry.get("email", "") if entry else email,
        )
    except Exception as err:  # noqa: BLE001
        # Log, do not swallow (#183). Still best-effort — the feedback is
        # already saved and the user's submit must not fail because a notify
        # channel is down. But a bare `pass` made a broken Telegram channel
        # completely invisible: feedback would keep arriving in GCS with
        # nobody being told, and the first symptom would be noticing months
        # later that nothing had been read. The email block immediately below
        # already logs its own failure; this now matches it.
        logging.getLogger(__name__).warning(
            "feedback Telegram notify failed (feedback itself was saved): %s", err
        )

    # Notify admin via email so feedback doesn't sit unread in a GCS file.
    # Best-effort — failure to email shouldn't fail the user's submit.
    try:
        admin_to = os.environ.get("BHAGYA_EMAIL_FROM", "").strip()
        if admin_to and entry:
            label = {"problem": "🐛 Problem", "feature": "✨ Feature request",
                     "other": "💬 Feedback"}.get(entry["type"], "Feedback")
            html = (
                f"<p><strong>{label}</strong> via {entry['page'] or 'unknown page'}</p>"
                f"<blockquote style='border-left:3px solid #6b21a8;padding:8px 12px;"
                f"margin:8px 0;background:#faf7f2;'>{entry['message']}</blockquote>"
                f"<p style='font-size:12px;color:#78716c;'>"
                f"From: {entry['email'] or '(anonymous)'}<br>"
                f"At: {entry['ts']}<br>"
                f"ID: <code>{entry['id']}</code></p>"
            )
            email_sender.send(admin_to, subject=f"[Shubh Bhagya feedback] {label}", html=html)
    except Exception as err:
        import logging
        logging.getLogger(__name__).warning("admin feedback notification failed: %s", err)

    return JSONResponse({"ok": True})
