"""Deploy liveness marker for CI (issue #154 module layout).

Owns:
    GET /health    JSON {"ok", "revision", "build_sha"} — which revision is serving

Why this is its own module rather than a few lines in ``pages.py``: the value of
this endpoint is entirely in what it does NOT do. It must answer while the rest
of the app is unhealthy, and it is polled every 15s by
``.github/workflows/verify-production.yml`` while a deploy rolls out. A GCS read
here would pay the documented cross-continent round-trip (the bucket is US,
Cloud Run is asia-south1) on every poll, and a route that touches
``_PANCHANG_CACHE`` or an LLM path could report healthy-and-slow or fail for
reasons that have nothing to do with the deploy. Keeping it in a separate file
whose ONLY imports are ``os`` and FastAPI makes that guarantee checkable by
reading the import block, instead of a promise in a docstring.

Absolute imports only — nothing here may import ``astro_ai.main``. Note it also
does not import ``astro_ai.routes.deps``, deliberately: that module pulls in
templates, the panchang strip cache and storage.
"""

from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


# The path is /health and NOT /healthz. Do not "fix" this to match the
# kubernetes convention — /healthz is intercepted by Google infrastructure in
# front of Cloud Run and never reaches this app. Measured against production
# 2026-08-26; every path 404s, but look at WHO answers:
#
#   /healthz    Google's "Error 404 (Not Found)!!1", 1568 bytes, and crucially
#               NO `server: Google Frontend` and no `x-cloud-trace-context`
#   /health     the app's own 404 page, ~95 kB, `server: Google Frontend`
#   /livez  /readyz  /_ah/health  /healthcheck  /zzz-random-xyz
#               all the app's own 404 page
#
# So this is not a rewrite bug: firebase.json's catch-all ("source": "**" ->
# Cloud Run `bhagya`) delivers every other path, including nonsense ones.
# /healthz alone is swallowed upstream, where nothing in this repo can reach.
# It broke the first run of verify-production.yml (run 32957675512): the deploy
# gate polled a path that can never answer, timed out after ~12 min, and
# skipped all seven downstream assertion steps. Renaming the path is the fix.
@router.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    """Report which revision is answering, so CI can wait for a DEPLOY rather
    than for the site to merely return 200 (the old revision does that fine).

    ``revision`` comes from ``K_REVISION``, which Cloud Run injects into every
    container automatically — nothing GCP-side is needed for it. It changes on
    every deploy, which is what makes "poll until it changes" a real signal.
    Off Cloud Run (local dev, pytest) the variable is absent and we report the
    sentinel ``"local"``.

    ``build_sha`` is the exact marker and is ``null`` today: it needs the Cloud
    Build trigger to pass ``--set-env-vars=BUILD_SHA=$COMMIT_SHA``, which is
    configured GCP-side and is the repo owner's change, not this repo's. It is
    left null rather than falling back to a guess — an invented SHA would let a
    workflow claim "this commit is serving" on no evidence, which is worse than
    admitting we cannot tell.

    DISCLOSURE. This is public and unauthenticated, and it names the serving
    Cloud Run revision plus, once the trigger sets it, a commit SHA. Judged
    acceptable — but not for the reason it is tempting to write down: this
    repo is PRIVATE (`"private": true` from the GitHub API, checked
    2026-08-26), so "it is all readable on GitHub anyway" is false. The actual
    reason is that both values are opaque identifiers. A commit SHA is a hash;
    without repo access it fetches nothing, and it reveals only that a deploy
    happened. A revision name leaks the service name and a deploy counter, and
    the Cloud Run URL cannot be reconstructed from it. Nothing here is a
    credential, a path, or a hint about internals. If a secret ever needs to
    appear in this payload, that judgement has to be redone, not inherited.
    """
    return JSONResponse(
        {
            "ok": True,
            "revision": os.environ.get("K_REVISION") or "local",
            "build_sha": os.environ.get("BUILD_SHA") or None,
        },
        headers={
            # A cached /health would defeat the entire point: CI would poll a
            # stale revision string and time out through a perfectly good deploy.
            "Cache-Control": "no-store, max-age=0",
            # Not in sitemap.xml, and noindex for real. The site's usual
            # noindex mechanism is the `meta_robots` Jinja block in base.html,
            # which cannot apply to a JSON response with no template — the
            # header is the equivalent for non-HTML resources.
            "X-Robots-Tag": "noindex",
        },
    )
