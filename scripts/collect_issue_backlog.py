#!/usr/bin/env python3
"""Commit the open-issue backlog as the fallback /admin/ops reads (#335, #353).

WHERE THE DERIVATION LIVES
--------------------------
In `src/astro_ai/issue_backlog.py`, not here. /admin/ops now fetches the
backlog live (#353) and the Docker image does not copy `scripts/`, so the
derivation had to move somewhere both callers can import. This file is the
scheduled collector: it fetches with `gh`, reads OBJECTIVE.md, and writes the
file. Everything about what an `area`, a `type`, a `priority` or an `ask` IS
is documented in that module.

WHY THE COMMITTED FILE STILL EXISTS NOW THE PAGE IS LIVE
--------------------------------------------------------
Because the live path can fail, and on Cloud Run it will. An unauthenticated
GitHub API call is rate limited at 60/hour per egress IP, and that IP is shared
with every other tenant behind the same NAT -- so the budget can be gone for
reasons that have nothing to do with this app. A page that rendered a blank
backlog when that happened would be reporting "no issues" when it means "no
answer", which is the exact failure /admin/ops exists to catch.

So the page tries the API, falls back to this file, and SAYS WHICH -- "live"
or "as of 9h ago". This file is what makes the fallback a real answer instead
of an empty panel. It also carries the objective, which the container cannot
read from OBJECTIVE.md at all.

Writes measurements/issues.json. Stdlib plus the `gh` CLI, which every workflow
in this repo already has on PATH.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from astro_ai.issue_backlog import build, read_objective  # noqa: E402


def fetch(repo: str, state: str, limit: int) -> list[dict]:
    """`gh issue list` as JSON. Raises on a non-zero exit rather than guessing."""
    out = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", state,
         "--limit", str(limit), "--json",
         "number,title,labels,createdAt,updatedAt,body"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default="mahAnuj/astro-ai")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--out", default="measurements/issues.json")
    ap.add_argument("--from-json", help="read `gh issue list --json` output from this file instead of calling gh")
    args = ap.parse_args(argv)

    if args.from_json:
        issues = json.loads(Path(args.from_json).read_text())
    else:
        issues = fetch(args.repo, "open", args.limit)

    doc = build(issues, repo=args.repo, objective=read_objective())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"{out}: {doc['open']} open, {len(doc['by_area'])} areas, "
          f"{doc['by_priority'].get('unset', 0)} unprioritised, {doc['blocked']} blocked, "
          f"{doc['with_ask']} with a readable ask"
          + ("" if doc["objective"] else ", NO OBJECTIVE.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
