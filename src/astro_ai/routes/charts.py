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

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from astro_ai import users
from astro_ai.routes.deps import _safe_redirect_target, _save_collection_synced
from astro_ai.session import clear_collection, load_collection, load_user

router = APIRouter()


@router.post("/switch")
async def switch(
    request: Request,
    chart_id: str = Form(...),
    next: str = Form(default="/"),
) -> RedirectResponse:
    """Activate the named saved chart, then redirect to `next` (default home)."""
    collection = load_collection(request).set_active(chart_id)
    response = RedirectResponse(_safe_redirect_target(next), status_code=303)
    _save_collection_synced(response, collection, request)
    return response


@router.post("/delete-chart")
async def delete_chart(
    request: Request,
    chart_id: str = Form(...),
) -> RedirectResponse:
    """Remove a saved chart; if it was active, activate whatever remains first."""
    collection = load_collection(request).remove(chart_id)
    response = RedirectResponse("/", status_code=303)
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
