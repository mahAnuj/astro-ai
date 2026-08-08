#!/usr/bin/env python
"""Dump the full route table of the FastAPI app — issue #154 refactor guard.

Prints one stable, sorted line per route so `main.py`'s router split can be
proven behaviour-preserving by a plain `diff` of before/after output.

    uv run python scripts/route_inventory.py > /tmp/routes_before.txt

Each line is:  <METHODS>  <path>  name=<endpoint name>  resp=<response class>

The endpoint *name* is included deliberately: moving a handler into a router
must not rename it, because `url_for`/`url_path_for` resolves by name.

Why this does not just read `app.routes`
----------------------------------------
As of FastAPI 0.138, `include_router()` no longer copies the child routes into
the parent. It appends a single lazy `fastapi.routing._IncludedRouter` marker
and resolves the real routes at match time, so `app.routes` stops being the
flat route table — 62 handlers collapse into one opaque entry with no `.path`
and no `.name`.

`fastapi.routing.iter_route_contexts` is the supported way to walk the real
table on those versions. We use it when present and fall back to `app.routes`
otherwise, so this script reports the same thing before and after the split and
on either FastAPI generation.
"""

from __future__ import annotations

import sys

from astro_ai.main import app

try:  # FastAPI >= 0.138
    from fastapi.routing import iter_route_contexts
except ImportError:  # pragma: no cover - older FastAPI
    iter_route_contexts = None


def _routes():
    """Yield the real route objects, flattening any lazy include markers."""
    if iter_route_contexts is None:
        yield from app.routes
        return
    for ctx in iter_route_contexts(app.routes):
        # RouteContext wraps the route; older shapes are the route itself.
        yield getattr(ctx, "route", ctx)


def main() -> int:
    lines = []
    count = 0
    for r in _routes():
        count += 1
        methods = ",".join(sorted(getattr(r, "methods", None) or []))
        path = getattr(r, "path", "?")
        name = getattr(r, "name", "?")
        resp = getattr(r, "response_class", None)
        resp_name = getattr(resp, "__name__", None) or type(resp).__name__ if resp else "-"
        include = getattr(r, "include_in_schema", True)
        lines.append(
            f"{methods:<20} {path:<48} name={name:<40} resp={resp_name:<20} schema={include}"
        )
    for line in sorted(lines):
        print(line)
    print(f"# total routes: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
