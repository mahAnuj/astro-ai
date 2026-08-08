#!/usr/bin/env python
"""Dump the full route table of the FastAPI app — issue #154 refactor guard.

Prints one stable, sorted line per route so `main.py`'s router split can be
proven behaviour-preserving by a plain `diff` of before/after output.

    uv run python scripts/route_inventory.py > /tmp/routes_before.txt

Each line is:  <METHODS>  <path>  name=<endpoint name>  resp=<response class>

The endpoint *name* is included deliberately: moving a handler into a router
must not rename it, because `url_for`/`url_path_for` in the Jinja templates
resolves by name.
"""

from __future__ import annotations

import sys

from astro_ai.main import app


def main() -> int:
    lines = []
    for r in app.routes:
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
    print(f"# total routes: {len(lines)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
