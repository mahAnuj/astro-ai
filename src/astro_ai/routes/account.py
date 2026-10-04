"""Language switch, Google Sign-In and the account page (issue #154).

Owns:
    POST /lang          switch reading language, persisted in __session
    POST /auth/google   verify a Google Identity Services ID token, start a
                        signed-in session and merge cross-device charts
    POST /auth/logout   clear the user portion of the session cookie
    GET  /account       signed-in profile page

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from astro_ai import notify, users
from astro_ai.routes.deps import _lang, _safe_redirect_target, templates
from astro_ai.routes.llm_support import _fire_error_alert
from astro_ai.session import (
    ChartCollection,
    SessionUser,
    clear_user,
    load_collection,
    load_user,
    save_lang,
    save_session_atomic,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/lang")
async def set_lang(
    request: Request,
    lang: str = Form(...),
    next: str = Form(default="/"),
) -> RedirectResponse:
    """Switch reading language; persisted in the combined __session cookie.

    `next` arrives as the ENGLISH url of the page the reader was on. When they
    chose Hindi and that page has a published Hindi twin, land them on the
    twin rather than on the English URL (#124).

    Both halves are needed and each was shipped alone and broken: writing the
    cookie without moving leaves the reader at a URL whose language it is not,
    and moving without writing gives them Hindi here and English on the next
    page. The twin lookup lives in `hindi_pages`, so the template does not
    have to carry a second copy of the URL mapping.
    """
    target = _safe_redirect_target(next)
    if lang == "hi":
        from astro_ai import hindi_pages

        target = hindi_pages.hindi_url(target) or target
    response = RedirectResponse(target, status_code=303)
    save_lang(response, lang, request)
    return response


# ─── Google Sign-In auth endpoints ──────────────────────────────────────────
# GIS flow: browser gets an ID token from Google, POSTs it here. We verify
# the token against Google's public keys (signature, expiry, audience) and
# persist the resulting user into the same __session cookie. No password
# management, no OAuth redirect dance.


@router.post("/auth/google")
async def auth_google(
    request: Request,
    credential: str = Form(...),
) -> JSONResponse:
    """Verify a Google Identity Services ID token and start a signed-in session.

    The `credential` is a JWT from the GIS button callback on the frontend.
    We validate it against Google's public keys with the expected audience
    (our GOOGLE_CLIENT_ID). On success we store {email, name, sub, since}
    in the session cookie. The client then reloads / navigates as needed.
    """
    from datetime import datetime, timezone
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        return JSONResponse(
            {"ok": False, "error": "Google Sign-In not configured on server."},
            status_code=503,
        )
    try:
        info = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            client_id,
            clock_skew_in_seconds=30,  # small tolerance for clock drift
        )
    except ValueError as err:
        # Bad signature, wrong audience, expired token — treat all as auth failure.
        return JSONResponse(
            {"ok": False, "error": f"Invalid Google credential: {err}"},
            status_code=401,
        )

    # Only email-verified accounts are accepted — otherwise anyone can
    # sign in with an arbitrary unverified email.
    if not info.get("email") or not info.get("email_verified"):
        return JSONResponse(
            {"ok": False, "error": "Google account email is not verified."},
            status_code=401,
        )

    user = SessionUser(
        email=str(info["email"]).lower(),
        name=str(info.get("name", "")),
        sub=str(info["sub"]),
        since=datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
    )
    # Persist to users.json — silent failure on storage error (auth still
    # succeeds; user just isn't in our persistent record). Cookie is the
    # source-of-truth for THIS session; users.json is for cross-device
    # continuity, Premium subscription tracking, and analytics.
    _is_new_user = False
    try:
        _ok, _is_new_user = users.upsert_user(sub=user.sub, email=user.email, name=user.name)
    except Exception as err:
        # Log and continue — never let a storage hiccup block sign-in.
        import logging
        logging.getLogger(__name__).warning(
            "users.upsert_user failed for %s: %s", user.email, err
        )
    notify.new_signin(email=user.email, name=user.name, first_time=_is_new_user)

    # Cross-device chart sync: merge (this device's charts) ∪ (user's
    # cross-device charts) and write the union back to BOTH the cookie
    # and users.json. Signed-in users' charts follow them across devices;
    # anonymous / storage-unavailable paths silently keep the cookie as-is.
    response = JSONResponse({"ok": True, "email": user.email, "name": user.name})
    merged: ChartCollection | None = None
    try:
        cookie_collection = load_collection(request)
        user_collection = users.load_charts(user.sub)
        merged = users.merge_collections(cookie=cookie_collection, user=user_collection)
        users.save_charts(user.sub, merged)  # silent no-op if storage unavailable
    except Exception as err:
        log.exception("chart sync on sign-in failed for %s", user.email)
        _fire_error_alert(request, err, "auth:chart_sync")
        merged = None  # leave existing cookie charts untouched on failure

    # SINGLE atomic cookie write — write user AND merged collection in one
    # go. Doing two consecutive save_xxx() calls (save_collection then
    # save_user) would result in the second overwriting the first because
    # both re-read the request cookie (which hasn't seen the first write).
    # See session.save_session_atomic docstring for the exact failure mode.
    save_session_atomic(response, request, user=user, collection=merged)
    return response


@router.post("/auth/logout")
async def auth_logout(request: Request) -> JSONResponse:
    """Sign the user out — clears the user portion of the session cookie."""
    response = JSONResponse({"ok": True})
    clear_user(response, request)
    return response


@router.get("/account", response_class=HTMLResponse)
async def account(request: Request) -> HTMLResponse:
    """Signed-in user profile page — email, saved charts, sign-out.

    Redirects home if not signed in (soft nudge: they can click the Sign In
    button in nav from wherever). Later this page will show Premium status
    and manage-subscription controls.
    """
    user = load_user(request)
    if user is None:
        return RedirectResponse("/", status_code=303)
    collection = load_collection(request)
    # Prefer persisted created_at from users.json — accurate "member since"
    # that survives sign-out / cookie clear. Falls back to the session
    # cookie's `since` (this-session-only) if the persistent record is
    # missing (e.g. storage was unavailable when they first signed in).
    persisted = users.find_by_sub(user.sub)
    member_since = (persisted.created_at if persisted else user.since) or user.since
    return templates.TemplateResponse(
        request, "account.html",
        {
            "current_user": user,
            "charts": collection.charts,
            "active_id": collection.active_id,
            "saved_charts_count": len(collection.charts),
            "member_since": member_since,
            "lang": _lang(request),
        },
    )
