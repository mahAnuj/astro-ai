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
    # strip_hi_prefix, NOT english_url, for the else-branch. english_url runs
    # _normalise, which lowercases and strips the trailing slash — so
    # /hi/learn/karva-chauth-2026/ redirected to /learn/karva-chauth-2026,
    # which Starlette then 307'd back to the slashed form: two hops for all 77
    # /learn/ URLs. The same normalisation defect as the picker's `next`, one
    # layer over, and hindi_pages.strip_hi_prefix's own docstring forbids
    # exactly this use of english_url (QA round 6, B-2).
    #
    # The twin lookup above still goes through hindi_url/english_url, which is
    # correct: there the canonical form IS the point, and /hi/rashifal/ should
    # land on /hi/rashifal.
    #
    # Handing the path through unchanged means the ENGLISH route's own slash
    # convention decides, rather than this module guessing one. Measured, and
    # the conventions genuinely differ: /learn/ is canonical WITH the slash
    # (/learn 307s to /learn/) while /about is canonical WITHOUT it (/about/
    # 307s to /about). english_url normalised every path to the no-slash form,
    # which was right for /about and wrong for all 77 /learn/ URLs. A reader
    # who types a slash a route does not use now pays exactly the one extra
    # hop they would pay typing it on the English URL directly — pre-existing
    # Starlette redirect_slashes behaviour, not something this adds.
    target = twin if twin is not None else hindi_pages.strip_hi_prefix(requested)
    # SAME-ORIGIN GUARD — this is the fix for an open redirect, not a
    # belt-and-braces extra.
    #
    # `{path:path}` captures everything after /hi/, so /hi//evil.example.com
    # arrives as path="/evil.example.com". `english_url()` strips the "/hi"
    # prefix and returns "//evil.example.com" — and "//host" in a Location
    # header is a PROTOCOL-RELATIVE URL, so the browser fetches
    # http://evil.example.com. Verified: before this guard,
    # /hi//evil.example.com/pwn returned 301 -> //evil.example.com/pwn, and
    # on production that is a cacheable redirect off shubhagya.com to an
    # arbitrary host. Found by QA 2026-10-04; both paths 404 before this
    # branch, so the branch introduced it.
    #
    # Fixing it HERE and not in `_normalise`: that function collapses only
    # leading slashes, so it never saw this path's inner "//" — and making it
    # collapse them would quietly reclassify "//rashifal" as the published
    # "/rashifal". Measured both before choosing. The check belongs where the
    # user-controlled string meets the Location header.
    #
    # `deps._safe_redirect_target` is this same guard for `next=` params. It
    # is reimplemented rather than imported: importing `deps` would pull
    # FastAPI + dotenv (it calls `load_dotenv` at import) into a module that
    # `hindi_pages` is deliberately kept independent of.
    if not target.startswith("/") or target.startswith("//"):
        target = "/"
    return RedirectResponse(target, status_code=301)


class RedirectLangParamMiddleware:
    """301 `?lang=hi` to `/hi/{path}` where a Hindi URL exists — #124 S8.

    The last half of the original defect. `/hi/...` being self-canonical does
    not help while the SAME Hindi content is still reachable at
    `/rashifal?lang=hi`, which renders `html lang="hi"` under
    `canonical=/rashifal`. That is the cross-language canonical this issue
    exists to remove, and `?lang=hi` links are already in the wild — they were
    the only way to get Hindi before this branch.

    This is a middleware where the /hi prefix deliberately is not, and the
    distinction is load-bearing: this one only ever REDIRECTS. It never lets a
    handler render with a mutated path, so it cannot produce the wrong
    canonical — which is precisely why the path-stripping middleware was
    rejected (see the module docstring).

    Narrow on purpose:

    * GET only. `POST /lang` carries `lang` as a FORM field and
      `POST /admin/warm-rashifal` takes it as a query param it reads directly;
      redirecting either would drop the body or the admin's intent.
    * Published paths only. `/matching?lang=hi` keeps working exactly as it
      does today, because there is no `/hi/matching` to send it to — the
      allow-list is the single source of that truth.
    * Other query parameters are preserved. Dropping them would break
      `/panchang?date=…&lang=hi`-shaped links, and a redirect that silently
      loses state is worse than no redirect.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "GET":
            return await self.app(scope, receive, send)

        from urllib.parse import parse_qsl, urlencode

        raw = scope.get("query_string", b"").decode("latin-1")
        if "lang=hi" not in raw:
            return await self.app(scope, receive, send)

        params = parse_qsl(raw, keep_blank_values=True)
        if not any(k == "lang" and v == "hi" for k, v in params):
            return await self.app(scope, receive, send)

        twin = hindi_pages.hindi_url(scope.get("path", "/"))
        if twin is None:
            return await self.app(scope, receive, send)

        kept = urlencode([(k, v) for k, v in params if k != "lang"])
        target = f"{twin}?{kept}" if kept else twin
        response = RedirectResponse(target, status_code=301)
        return await response(scope, receive, send)
