"""Live agent status as JSON, for anujmahajan.com's /agent-cycle page.

Owns:
    GET /api/agents/status   the "Agents right now" cards (agent_status.py)

Public on purpose: everything in it is already public on GitHub (the
repository is public) and it carries no visitor data. It costs GitHub reads,
not Groq tokens, and those are capped by agent_status.CACHE_TTL whatever the
request rate: at most 3 reads per TTL however many callers there are.

CORS allows anujmahajan.com only, the one page that reads it from a browser;
the site's own server-side proxy needs no CORS at all.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from astro_ai import agent_status

router = APIRouter()

ALLOWED_ORIGIN = "https://anujmahajan.com"


@router.get("/api/agents/status", include_in_schema=False)
async def agents_status() -> JSONResponse:
    # Off the event loop: a cold refresh is three blocking urllib reads.
    doc = await asyncio.to_thread(agent_status.snapshot)
    return JSONResponse(doc, headers={
        "Cache-Control": "public, max-age=60",
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Vary": "Origin",
    })
