"""Feedback widget — the single submit endpoint behind the floating modal (issue #154).

Owns:
    POST /feedback  persist one entry to GCS, then Telegram + email the owner

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only. Note this module SHADOWS the top-level ``astro_ai.feedback``
store within the ``astro_ai.routes`` package, so the store must always be reached
by its absolute name; a relative import here would self-import and fail obscurely.
"""

from __future__ import annotations

import html as _html
import logging
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
        #
        # `logging` is imported at MODULE scope on purpose (#408). It used to be
        # imported inside the email `except` below, which made it function-local
        # for the whole of this handler, so THIS line raised UnboundLocalError
        # and a saved submission came back as a 500.
        logging.getLogger(__name__).warning(
            "feedback Telegram notify failed (feedback itself was saved): %s", err
        )

    # Notify admin via email so feedback doesn't sit unread in a GCS file.
    # Best-effort — failure to email shouldn't fail the user's submit.
    #
    # The hexes below are redesign tokens (#239): sindoor #9E2B25 rule, cream
    # #FAF6EF fill, muted #6B6259 meta. Moved with the three email templates
    # rather than with the shell, which is where #238's commit message put it:
    # this is an EMAIL body, not browser chrome, so the "half-migrated chrome a
    # user would see" reasoning that deferred meta theme-color and the
    # webmanifest does not apply to it. Migrating it alongside the other four
    # emails is what keeps them consistent. Tailwind never sees this string, so
    # nothing will flag it if the tokens move — grep here too.
    try:
        admin_to = os.environ.get("BHAGYA_EMAIL_FROM", "").strip()
        if admin_to and entry:
            label = {"problem": "🐛 Problem", "feature": "✨ Feature request",
                     "other": "💬 Feedback"}.get(entry["type"], "Feedback")
            # ESCAPED, because all three of these are typed by an anonymous
            # visitor (#373). `POST /feedback` needs no auth, `feedback.add`
            # caps the message at 2,000 characters and sanitises nothing, and
            # this body is delivered to the owner's inbox FROM THE SITE'S OWN
            # Brevo sender domain -- so it passes SPF and DKIM and renders as a
            # genuine Shubh Bhagya notification. Mail clients strip <script>,
            # but <a href>, a remote <img> and a styled block all render, which
            # is enough to spoof one.
            #
            # Escaped HERE rather than in `feedback.add`: storage keeps what the
            # visitor actually typed, which is what /admin/feedback needs to
            # show and what makes the record honest. Escaping belongs where the
            # markup is built, and any future consumer must do its own.
            #
            # DO NOT read this as "the Telegram path is safe". An earlier version of
            # this comment said `notify._escape_md` already escapes all three fields;
            # QA disproved it. `_escape_md` does not escape its own escape character
            # (`'\\' in ('_','*','`','[')` is False) and `notify.py:105` sends
            # `parse_mode: "Markdown"`, so a payload can still break out there. That is
            # #387, deliberately out of this diff's scope -- it is a different sink with
            # a different mechanism, and widening a security diff hurts review. This
            # change makes the EMAIL body safe and claims nothing about Telegram.
            msg = _html.escape(entry["message"] or "")
            page = _html.escape(entry["page"] or "") or "unknown page"
            frm = _html.escape(entry["email"] or "") or "(anonymous)"
            html = (
                f"<p><strong>{label}</strong> via {page}</p>"
                f"<blockquote style='border-left:3px solid #9E2B25;padding:8px 12px;"
                f"margin:8px 0;background:#FAF6EF;'>{msg}</blockquote>"
                f"<p style='font-size:12px;color:#6B6259;'>"
                f"From: {frm}<br>"
                f"At: {_html.escape(str(entry['ts']))}<br>"
                f"ID: <code>{_html.escape(str(entry['id']))}</code></p>"
            )
            email_sender.send(admin_to, subject=f"[Shubh Bhagya feedback] {label}", html=html)
    except Exception as err:
        logging.getLogger(__name__).warning("admin feedback notification failed: %s", err)

    return JSONResponse({"ok": True})
