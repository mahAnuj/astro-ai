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

THE `trend` BLOCK (2026-11-18)
------------------------------
Opened against closed per day for 28 days, by source and by closer, and the open
issues a merged PR already claimed. Built by `scripts/issue_flow.py`, whose
docstring says what each bucket means and what it costs. It lives in this file,
written by this step, so no workflow changes: the page already reads issues.json.
A trend that cannot be read is recorded as `{"error": ...}` and the backlog is
written anyway -- the backlog is the older promise and must not depend on it.
`--no-trend`, and `--from-json`, skip it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from astro_ai.issue_backlog import build, read_objective  # noqa: E402

import issue_flow  # noqa: E402


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
    ap.add_argument("--no-trend", action="store_true", help="skip the opened/closed trend block")
    args = ap.parse_args(argv)

    if args.from_json:
        issues = json.loads(Path(args.from_json).read_text())
    else:
        issues = fetch(args.repo, "open", args.limit)

    doc = build(issues, repo=args.repo, objective=read_objective())
    out = Path(args.out)
    if not (args.from_json or args.no_trend):
        doc["trend"] = trend(args.repo, issues, out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"{out}: {doc['open']} open, {len(doc['by_area'])} areas, "
          f"{doc['by_priority'].get('unset', 0)} unprioritised, {doc['blocked']} blocked, "
          f"{doc['with_ask']} with a readable ask"
          + ("" if doc["objective"] else ", NO OBJECTIVE.md"))
    t = doc.get("trend") or {}
    if t.get("days"):
        week = t["days"][-7:]
        print(f"trend: last 7d {sum(d['opened'] for d in week)} opened, "
              f"{sum(d['closed'] for d in week)} closed, {len(t['merged_open'])} merged-but-open, "
              f"{t['timelines_read']} timelines read"
              + (f", TRUNCATED {t['truncated']}" if t["truncated"] else ""))
    elif t:
        print(f"trend: not collected -- {t.get('error')}")
    return 0


def trend(repo: str, issues: list[dict], out: Path) -> dict:
    """The trend block, or {"error": ...}. Never raises: see the docstring."""
    try:
        prior = json.loads(out.read_text()).get("trend") if out.is_file() else None
    except (OSError, ValueError, AttributeError):
        prior = None
    try:
        return issue_flow.collect(issue_flow.run_gh, repo, datetime.now(timezone.utc),
                                  open_issues=issues, prior=prior)
    except Exception as exc:  # noqa: BLE001 -- the backlog still gets written
        return {"error": f"{exc.__class__.__name__}: {str(exc)[:200]}"}


if __name__ == "__main__":
    sys.exit(main())
