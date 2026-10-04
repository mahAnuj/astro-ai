"""The `/hi/{path}` URL surface — #124.

WHY A ROUTER AND NOT A MIDDLEWARE.

A path-stripping middleware was built first and rejected. Rewriting
`scope["path"]` makes `request.url.path` return the ENGLISH path inside the
handler, so `base.html`'s canonical tag renders `/rashifal` on a page served
at `/hi/rashifal` — a cross-language canonical, which is the precise defect
#124 exists to remove. Reproduced by execution before discarding the approach.

So the prefix is handled here instead, as ordinary routes that set
`request.state.forced_lang` and await the existing English handler. `_lang()`
reads that state first (`routes/deps.py:374`), which is why 58 call sites
across 19 modules need no edit: the handler resolves Hindi through the same
function it already called, and `request.url.path` stays `/hi/...` so the
canonical is self-referential.

WHY ONLY THIRTEEN PATHS.

`hindi_pages.HINDI_PUBLISHED` holds the pages whose PRIMARY CONTENT is really
Hindi — `/rashifal` and the 12 rashi pages, whose readings are generated in
Hindi. Measured on production, `/rashifal/aries?lang=hi` is 74.3% Devanagari
at 0.240 text similarity to its English twin.

Every other page is NOT in the set, and the measurement is why: with
`?lang=hi` the rest of the site is 83-98% textually identical to English,
because only the chrome is translated. `/learn/` is 0.978 similar and 1.8%
Devanagari — English prose under a Hindi navbar. Publishing ~200 such URLs
would be publishing ~200 near-duplicate pages, which is how a site gets its
hreflang annotations discarded and its thin content demoted. The allow-list
is not caution; it is the finding.

So an unpublished `/hi/...` path does not serve Hindi and does not 404 —
it 301s to its English URL. A 404 on a page that demonstrably exists is a
soft-404 risk and is user-hostile to anyone who hand-types or shares the
prefix; the redirect says the true thing, which is "this page exists, just
not in Hindi".
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import hindi_pages
from . import rashifal as _rashifal

router = APIRouter()


def _force_hindi(request: Request) -> None:
    """Pin this request to Hindi.

    Set on `request.state`, never read from a client: `_lang()` membership-tests
    the value against `SUPPORTED_LANGS`, so this cannot be used to request a
    language that has no strings.
    """
    request.state.forced_lang = "hi"


# Declared BEFORE the catch-all, and the order is load-bearing WITHIN this
# module only: FastAPI matches in registration order, but that order is
# per-router, so where main.py includes this router relative to the others
# does not matter (verified — no /hi path collides with an English route).
# What matters is that these two come before /hi/{path:path} below.
#
# Measured consequence of getting it wrong: the catch-all matches
# /hi/rashifal, hindi_url() returns /hi/rashifal because it IS published, and
# the route 301s to itself. Every Hindi URL becomes a redirect loop at once —
# not the English-at-a-Hindi-URL failure guessed at here first.
# tests/test_hindi_urls.py::test_hi_redirect_chains_terminate covers it.
@router.get("/hi/rashifal", response_class=HTMLResponse)
async def hindi_rashifal(request: Request) -> HTMLResponse:
    _force_hindi(request)
    return await _rashifal.rashifal(request)


@router.get("/hi/rashifal/{rashi}", response_class=HTMLResponse)
async def hindi_rashifal_single(request: Request, rashi: str) -> HTMLResponse:
    """Serves the 12 rashi pages. An unknown slug is NOT handled here —
    it falls through to the English handler's own 404, so `/hi/rashifal/foo`
    and `/rashifal/foo` fail identically rather than diverging."""
    _force_hindi(request)
    return await _rashifal.rashifal_single(request, rashi)


@router.get("/hi/{path:path}")
async def hindi_unpublished(request: Request, path: str) -> RedirectResponse:
    """301 anything else to its English URL — see the module docstring.

    301 and not 302: the absence of a Hindi version is a property of the page,
    not of today, so it is correct to let it be cached. If a page later gains
    real Hindi content it joins HINDI_PUBLISHED and gets a route above this
    one, at which point the redirect stops being reached at all.
    """
    requested = "/hi/" + path
    # A PUBLISHED path only reaches here in a non-canonical form — most often a
    # trailing slash, since the two routes above match exactly. Sending those
    # to English would silently drop the language: /hi/rashifal/ would serve
    # the English page, which is the defect this module exists to fix, just
    # reached via a slash. Redirect to the canonical /hi form instead.
    twin = hindi_pages.hindi_url(requested)
    if twin is not None:
        return RedirectResponse(twin, status_code=301)
    return RedirectResponse(hindi_pages.english_url(requested), status_code=301)
