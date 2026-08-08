"""Static content pages (issue #154).

Owns:
    GET /about     editorial principles, classical sources, team (E-E-A-T)
    GET /privacy   short-form privacy policy
    GET /terms     short-form terms of service

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from astro_ai.routes.deps import _lang, templates

router = APIRouter()


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request) -> HTMLResponse:
    """About page — editorial principles, classical sources, team.

    E-E-A-T signal for Google (SEO audit #125): named entity behind the
    content, cited classical sources, contact-visible. Linked from the
    footer of every page via _nav.html.
    """
    return templates.TemplateResponse(
        request, "about.html", {"lang": _lang(request)},
    )


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request) -> HTMLResponse:
    """Honest short-form Privacy Policy. Written by a person, not a
    boilerplate generator; reflects our actual data practices."""
    return templates.TemplateResponse(
        request, "privacy.html",
        {"lang": _lang(request), "contact_email": "contact@shubhagya.com"},
    )


@router.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request) -> HTMLResponse:
    """Honest short-form Terms of Service. Includes astrology-disclaimer +
    AI-generated-content disclaimer per Shyamasundara audit follow-up."""
    return templates.TemplateResponse(
        request, "terms.html",
        {"lang": _lang(request), "contact_email": "contact@shubhagya.com"},
    )


