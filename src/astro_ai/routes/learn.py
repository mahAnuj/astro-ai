"""/learn — the SEO article hub and the per-article renderer (issue #154).

Owns:
    GET /learn/         hub page listing every registered article
    GET /learn/{slug}/  one hand-written article template plus its related links

The TRAILING SLASH on both paths is load-bearing: the canonical URLs indexed by
Search Console end in a slash, and dropping it would turn every hit into a 307.

Moved verbatim; only the decorator prefix changed (``@app.`` → ``@router.``).
Absolute imports only.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from astro_ai import learn_registry
from astro_ai.routes.deps import _lang, templates

router = APIRouter()


@router.get("/learn/", response_class=HTMLResponse)
async def learn_index(request: Request) -> HTMLResponse:
    """Hub page listing every learning article. Public, indexable, no auth."""
    return templates.TemplateResponse(
        request,
        "learn_index.html",
        {
            "lang": _lang(request),
            "articles": learn_registry.all_articles(),
        },
    )


@router.get("/learn/{slug}/", response_class=HTMLResponse)
async def learn_article(request: Request, slug: str) -> HTMLResponse:
    """Render one learning article. Each article is a hand-written Jinja
    template at templates/learn/<slug>.html that extends learn_article_base.
    Registry holds metadata (title, summary, FAQs, related links)."""
    article = learn_registry.get_article(slug)
    if article is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        f"learn/{slug}.html",
        {
            "lang": _lang(request),
            "article": article,
            "related": learn_registry.related_articles(slug),
        },
    )
