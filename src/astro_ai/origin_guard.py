"""Refuse a cross-site POST to `/auth/google` (#1106, sign-in CSRF).

Without this, any page can make a visitor's browser post an attacker's Google
credential, signing the victim in AS THE ATTACKER, so the victim's charts and
readings are saved to the attacker's account.

WHY NOT `g_csrf_token` double-submit, which is what the issue first asked for:
`base.html` runs Google Identity Services in CALLBACK mode (`data-callback`, no
`data-login_uri`) and the fetch posts only `credential`. Google sets the
`g_csrf_token` cookie in redirect mode only, and Firebase Hosting strips every
cookie but `__session`, so the check would 403 every real sign-in.

So the check is on where the request came from, which a browser states itself and
a page cannot forge:
  1. `Sec-Fetch-Site` is decisive when present: only `same-origin` passes.
     `same-site` is refused too, since a sibling subdomain is not this site.
  2. Else `Origin`: it must match the request's Host, or the public site host.
     `Origin: null` has an empty netloc and fails.
  3. Neither header: allowed. That is a non-browser client, and a CSRF attacker
     needs a browser, which always sends at least `Origin` on a cross-site POST.

main.py rewrites `Host` from `X-Forwarded-Host`, so behind Firebase the Host
header is already the public one.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

from astro_ai.routes.deps import _site_url

_FORBIDDEN = "Cross-site sign-in is not allowed."


def _allowed_hosts(request: Request) -> set[str]:
    hosts = {"shubhagya.com", "www.shubhagya.com"}
    site = urlsplit(_site_url()).netloc.lower()
    if site:
        hosts.add(site)
    host = request.headers.get("host", "").strip().lower()
    if host:
        hosts.add(host)
    return hosts


def is_same_origin(request: Request) -> bool:
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None:
        return fetch_site.strip().lower() == "same-origin"
    origin = request.headers.get("origin")
    if origin is not None:
        netloc = urlsplit(origin.strip()).netloc.lower()
        return bool(netloc) and netloc in _allowed_hosts(request)
    return True


def same_origin_or_403(request: Request) -> JSONResponse | None:
    """None when the request may proceed, else the 403 to return. JSON, not an
    HTTPException: the sign-in modal calls `r.json()` on every response."""
    if is_same_origin(request):
        return None
    return JSONResponse({"ok": False, "error": _FORBIDDEN}, status_code=403)
