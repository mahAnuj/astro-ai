"""Admin console — the owner-only dashboard and its deep-dive pages (issue #154).

Owns:
    GET /admin/feedback     every feedback entry, newest first
    GET /admin              landing dashboard: KPIs, LLM spend, community counts
    GET /admin/usage        301 to /admin (the old URL, merged 2026-08-06)
    GET /admin/activity     recent kundli / ask / matching submissions + errors
    GET /admin/insights     audience-shape aggregates (issue #140)
    GET /admin/ops          agent-loop control room (issue #335)
    GET /admin/subscribers  full Rashifal-email subscriber list

Auth is declared PER ROUTE, exactly as before: five of the six carry
``dependencies=[Depends(require_admin)]`` and ``/admin/usage`` deliberately does
NOT — it is an unauthenticated permanent redirect, so old bookmarks land on the
Basic-Auth prompt at /admin rather than hitting one on the redirect itself. The
gate must therefore never be hoisted onto the router.

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from astro_ai import cache, events, feedback, ops_data, subscribers, users
from astro_ai.routes.deps import _lang, require_admin, templates

router = APIRouter()


@router.get("/admin/feedback", response_class=HTMLResponse,
         dependencies=[Depends(require_admin)])
async def admin_feedback(request: Request) -> HTMLResponse:
    """List every feedback entry, most recent first. Auth-gated like /admin/usage."""
    return templates.TemplateResponse(
        request, "admin_feedback.html",
        {"lang": _lang(request), "entries": feedback.list_all()},
    )


@router.get("/admin", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_dashboard(request: Request, days: int = 1) -> HTMLResponse:
    """Admin landing dashboard — cross-cutting metrics from every subsystem.

    Sections:
      - Headline KPIs: Kundli / Ask / Matching / Errors counts for the window
      - LLM usage: token spend, cache hit rate, per-route/model/provider (formerly its own page)
      - Community: signed-in users, Rashifal subscribers, feedback count
      - Recent activity mini-feed with links to the per-type deep-dive pages

    Deep-dive pages: /admin/activity, /admin/subscribers, /admin/feedback.

    Protected by HTTP Basic Auth (username 'admin', password from
    ADMIN_PASSWORD env var). Browser shows the standard login prompt.
    """
    from astro_ai import llm_stats, feedback
    # Persistent (GCS) usage summary — survives Cloud Run cold starts and
    # deploys, unlike the SQLite version which lives in /tmp and resets on
    # every push. We supplement with cache_entries from SQLite (that count
    # IS instance-scoped but doesn't matter across restarts).
    summary = llm_stats.usage_summary(days=days)
    try:
        sqlite_summary = cache.usage_summary(days=days)
        summary["cache_entries"] = sqlite_summary.get("cache_entries", 0)
    except Exception:  # noqa: BLE001
        pass
    # Community counts. Users = Google sign-in persisted; subscribers = daily
    # Rashifal email opt-in; feedback = feedback widget submissions.
    user_count = users.count()
    subscriber_count = subscribers.count()
    feedback_count = feedback.count()
    # Per-model / per-route LLM call breakdown for the same window.
    llm_stats_summary = llm_stats.range_summary(days=days)
    # Event counts per type (form_kundli / form_ask / form_matching / error) —
    # backs the four headline KPI cards.
    event_totals = events.counts_by_type(days=days)
    # Recent-activity mini-feed: last N events across all types, newest first.
    recent_events = events.recent(days=days, limit=10)
    recent_errors = events.recent(types=["error"], days=days, limit=3)
    return templates.TemplateResponse(
        request, "admin_dashboard.html",
        {
            "lang": _lang(request),
            "summary": summary,
            "days": days,
            "user_count": user_count,
            "subscriber_count": subscriber_count,
            "feedback_count": feedback_count,
            "llm_stats": llm_stats_summary,
            "event_totals": event_totals,
            "recent_events": recent_events,
            "recent_errors": recent_errors,
        },
    )


@router.get("/admin/usage", include_in_schema=False)
async def admin_usage_redirect(days: int = 1) -> RedirectResponse:
    """Old URL — /admin/usage merged into the main /admin dashboard on
    2026-08-06. Permanent redirect so bookmarks and any linked-to URLs
    continue to work."""
    return RedirectResponse(f"/admin?days={days}", status_code=301)


@router.get("/admin/activity", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_activity(request: Request, days: int = 7, limit: int = 200) -> HTMLResponse:
    """Recent form submissions, Ask questions, and errors — auth-gated.

    Query params: days=1|7|30, limit=100|200|500.
    """
    kundlis = events.recent(types=["form_kundli"], days=days, limit=limit)
    matches = events.recent(types=["form_matching"], days=days, limit=limit)
    asks = events.recent(types=["form_ask"], days=days, limit=limit)
    errs = events.recent(types=["error"], days=days, limit=limit)
    totals = events.counts_by_type(days=days)
    return templates.TemplateResponse(
        request, "admin_activity.html",
        {
            "lang": _lang(request),
            "days": days, "limit": limit,
            "kundlis": kundlis, "matches": matches, "asks": asks, "errors": errs,
            "totals": totals,
        },
    )


@router.get("/admin/insights", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_insights(request: Request, days: int = 30,
                         refresh: int = 0) -> HTMLResponse:
    """Audience-shape aggregates — who's actually using the site.

    Runs `profiling.audience_summary(days)`, which reads from the existing
    GCS events log (no new collection). Cached per-day at the profiling
    layer, so repeated loads within an hour are cheap. `?refresh=1` forces
    a re-aggregate — useful right after new features change the substrate.

    See GitHub issue #140 for the dimension list and roadmap (Phase 1
    covers cheap dims; rashi + intent-NLP land in later phases).
    """
    from astro_ai import profiling
    summary = profiling.audience_summary(days=days, force_refresh=bool(refresh))
    return templates.TemplateResponse(
        request, "admin_insights.html",
        {"lang": _lang(request), "days": days, "summary": summary},
    )


@router.get("/admin/ops", response_class=HTMLResponse,
            dependencies=[Depends(require_admin)])
async def admin_ops(request: Request) -> HTMLResponse:
    """The agent team's control room — what the loop did, costs, and the backlog.

    Reads only the committed `measurements/*.json` files via `ops_data`, which
    returns None per file on failure rather than raising, so a missing file
    blanks one panel and the footer names it. Nothing here calls the GitHub API
    at request time: Cloud Run's egress IP is shared, and an unauthenticated
    API call would start failing at 60/hour for reasons invisible to the owner.

    The same snapshot is serialised into the page as JSON so the drill-downs
    filter data already rendered — a drill-down cannot disagree with the
    headline it was opened from.
    """
    ops = ops_data.snapshot()
    L, I = ops["loop"], ops["issues"]
    client = {
        "repo": "mahAnuj/astro-ai",
        "cycles": L["rows"],
        "issues": I["rows"],
        "today_shipped": L["today_shipped"],
        "today_failed": L["today_failed"],
        "filed_today": I["filed_today"],
        "by_priority": I.get("by_priority", {}),
        "by_area": I.get("by_area", {}),
        "by_type": I.get("by_type", {}),
    }
    return templates.TemplateResponse(
        request, "admin_ops.html",
        {
            "lang": _lang(request),
            "ops": ops,
            # </script> inside a JSON string would end the block early.
            "ops_json": json.dumps(client).replace("</", "<\\/"),
        },
    )


@router.get("/admin/subscribers", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_subscribers(request: Request) -> HTMLResponse:
    """Full Rashifal-email subscriber list — auth-gated."""
    subs = subscribers.list_subscribers()
    # Newest first — subscribers.list_subscribers order is insertion order.
    subs_sorted = sorted(subs, key=lambda s: s.get("subscribed_at", ""), reverse=True)
    return templates.TemplateResponse(
        request, "admin_subscribers.html",
        {
            "lang": _lang(request),
            "subscribers": subs_sorted,
            "total": len(subs_sorted),
        },
    )
