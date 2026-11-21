"""Saved-chart management — switch, delete, reset (issue #154).

Owns:
    POST /switch        activate one saved chart, then redirect to `next`
    POST /delete-chart  drop a chart, clearing the cookie (and the signed-in
                        user's persisted charts) when nothing is left
    POST /reset         wipe the whole collection — the welcome-back panel's
                        fresh-start button

All three mutate the collection cookie and 303 back to a page; none renders a
template of its own.

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from astro_ai import users
from astro_ai.routes.deps import _safe_redirect_target, _save_collection_synced
from astro_ai.routes.kundli import erase_natal_blobs
from astro_ai.session import clear_collection, load_collection, load_user

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/switch")
async def switch(
    request: Request,
    chart_id: str = Form(...),
    # Python name avoids shadowing the builtin; the posted field stays `next`.
    next_url: str = Form(default="/", alias="next"),
) -> RedirectResponse:
    """Activate the named saved chart, then redirect to `next` (default home)."""
    collection = load_collection(request).set_active(chart_id)
    response = RedirectResponse(_safe_redirect_target(next_url), status_code=303)
    _save_collection_synced(response, collection, request)
    return response


@router.post("/delete-chart")
async def delete_chart(
    request: Request,
    chart_id: str = Form(...),
) -> RedirectResponse:
    """Remove a saved chart; if it was active, activate whatever remains first."""
    before = load_collection(request)
    collection = before.remove(chart_id)
    response = RedirectResponse("/", status_code=303)
    # The cached natal reading addresses the seeker by name and never expires
    # (#1105). Best-effort like the readings below. A twin chart (same name and
    # birth data) shares the blob; deleting a cache blob is harmless, the next
    # view regenerates it.
    try:
        await run_in_threadpool(erase_natal_blobs, [c for c in before.charts if c.id == chart_id])
    except Exception:
        log.warning("delete-chart: could not remove the cached natal reading")
    # A reading is personal data about that chart's birth details; removing
    # the chart must not leave its readings behind in users.json (#1105).
    # Best-effort: the redirect and cookie handling below never depend on it.
    signed_in = load_user(request)
    if signed_in is not None:
        try:
            users.delete_readings_for_chart(signed_in.sub, chart_id)
        except Exception:
            log.warning("delete-chart: could not remove readings for the chart")
    if not collection.charts:
        clear_collection(response)
        # Also clear the persisted charts for signed-in users so their
        # cross-device state stays consistent with what they see here.
        user = load_user(request)
        if user is not None:
            try:
                users.save_charts(user.sub, collection)  # empty collection
            except Exception:
                pass
    else:
        _save_collection_synced(response, collection, request)
    return response


@router.post("/reset")
async def reset() -> RedirectResponse:
    """Wipe all saved charts — fresh-start button on the welcome-back panel."""
    response = RedirectResponse("/", status_code=303)
    clear_collection(response)
    return response
