"""Live agent status as JSON, for anujmahajan.com's /agent-cycle page.

Owns:
    GET /api/agents/status   the "Agents right now" cards (agent_status.py)

Public on purpose: everything in it is already public on GitHub (the
repository is public) and it carries no visitor data. It costs GitHub reads,
not Groq tokens, and those are capped by agent_status.CACHE_TTL whatever the
request rate: at most 3 reads per TTL however many callers there are.

CORS allows anujmahajan.com only, the one page that reads it from a browser;
the site's own server-side proxy needs no CORS at all.

A request carrying ANY query string is 301'd to the bare path (#1261). The
endpoint reads no parameter, so `?x=1`, `?x=2` ... are all the same document
under different cache keys: each one is a CDN miss that reaches the instance.
The redirect makes the bare URL the only one that is ever served a body. Be
honest about what that buys: it saves instance CPU and stops the CDN filling
with copies of one document. It does NOT save GitHub reads (snapshot() is
already cached in-process, so a query-string flood was never a read flood) and
it does not touch Groq. Firebase Hosting may not cache the 301 either, so each
`?x=N` can still reach the instance once; it just gets a few bytes back
instead of the JSON path. Capping the instance count is a separate issue.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from astro_ai import agent_status

router = APIRouter()

ALLOWED_ORIGIN = "https://anujmahajan.com"

# One place for the CORS pair, so the 200 and the 301 cannot drift: a browser
# on anujmahajan.com that follows a redirect without ACAO fails the fetch.
_CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Vary": "Origin",
}


@router.get("/api/agents/status", include_in_schema=False)
async def agents_status(request: Request) -> Response:
    # Before the thread hop, so a junk query never costs a worker thread.
    # Location is the bare path and echoes nothing from the request (cf.
    # routes/hindi.py), so there is no open-redirect surface.
    if request.url.query:
        return RedirectResponse(
            "/api/agents/status", status_code=301,
            headers={**_CORS_HEADERS, "Cache-Control": "public, max-age=3600"},
        )
    # Off the event loop: a cold refresh is three blocking urllib reads.
    doc = await asyncio.to_thread(agent_status.snapshot)
    return JSONResponse(doc, headers={
        **_CORS_HEADERS,
        "Cache-Control": "public, max-age=60",
    })
