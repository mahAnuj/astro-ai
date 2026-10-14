#!/usr/bin/env python3
"""Commit the open-issue backlog as data the /admin/ops page can read (#335).

WHY A FILE AND NOT THE GITHUB API AT REQUEST TIME
-------------------------------------------------
/admin/ops runs on Cloud Run, where an unauthenticated GitHub API call is rate
limited per egress IP and shared with every other tenant on that IP. A page
that renders the backlog by calling the API would go blank at 60 requests an
hour for reasons invisible to the owner. So the backlog is collected on a
schedule and committed, exactly like measurements/loop.json (#338).

THE TAXONOMY IS DERIVED, NOT DECLARED -- AND THAT IS THE FINDING
---------------------------------------------------------------
#335 asked for "issues category wise count". There is no usable category label:
measured on 2026-10-14 across 66 open issues, `category:technical` appears 4
times, `category:content` once and `seo` once. Inventing a label taxonomy here
would be work this script has no authority to do, and back-filling 66 issues is
not a reporting job.

So `area` is derived from the title, which the agents already structure:
  1. a bracket prefix, e.g. "[INFRA] ..."       -> INFRA
  2. "Redesign: ..."                            -> REDESIGN
  3. a lowercase word before the first colon    -> that word, e.g. "numerology:"
  4. nothing matched                            -> UNCLASSIFIED

`type` and `priority` come from labels, because those labels are real and
applied. A missing priority is recorded as "unset" rather than guessed: 43 of
the 66 open issues carry no priority label at all, and that number is the most
actionable thing on the page -- project-manager cannot rank what nobody ranked.

Writes measurements/issues.json. Stdlib plus the `gh` CLI, which every workflow
in this repo already has on PATH.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# A bracket prefix the agents write: "[INFRA]", "[CONVERSION]", "[SEO]".
_BRACKET = re.compile(r"^\s*\[([A-Za-z0-9 /&-]{2,20})\]")
# An informal area prefix: "numerology: ...", "rashifal: ...", "knowledge: ...".
# Deliberately narrow -- one lowercase word, then a colon, then a space. A
# sentence containing a colon further in does not match.
_WORD_PREFIX = re.compile(r"^([a-z][a-z0-9_-]{2,14}):\s")

# Label -> the type bucket shown on the page. Order matters: the FIRST match in
# this list wins, so a `bug` that is also an `enhancement` counts as a bug.
_TYPES = (
    ("bug", "bug"),
    ("astrology-correctness", "correctness"),
    ("design-proposal", "design"),
    ("ui", "ui"),
    ("chore", "chore"),
    ("enhancement", "enhancement"),
)


def derive_area(title: str) -> str:
    """Best-effort subject area for one issue title. See the module docstring."""
    m = _BRACKET.match(title)
    if m:
        return m.group(1).strip().upper()
    if title.strip().lower().startswith("redesign:"):
        return "REDESIGN"
    m = _WORD_PREFIX.match(title.strip())
    if m:
        return m.group(1).upper()
    return "UNCLASSIFIED"


def derive_type(labels: list[str]) -> str:
    """Type bucket from labels, first match in _TYPES order; else 'untyped'."""
    for label, bucket in _TYPES:
        if label in labels:
            return bucket
    return "untyped"


def derive_priority(labels: list[str]) -> str:
    """`priority:high` -> 'high'. No priority label -> 'unset', never a guess."""
    for label in labels:
        if label.startswith("priority:"):
            return label.split(":", 1)[1]
    return "unset"


def row_for(issue: dict) -> dict:
    """One backlog row. Keeps the fields a reader can act on, nothing more."""
    labels = [lab["name"] for lab in issue.get("labels", [])]
    return {
        "number": issue["number"],
        "title": issue["title"],
        "area": derive_area(issue["title"]),
        "type": derive_type(labels),
        "priority": derive_priority(labels),
        "labels": labels,
        "created": issue.get("createdAt"),
        "updated": issue.get("updatedAt"),
        # The two labels that mean "a human has to look at this" are surfaced
        # on their own, because they are why an issue is NOT in the loop's
        # queue -- project-manager skips both.
        "blocked": "needs-human-review" in labels,
        "needs_evidence": "needs-evidence" in labels,
    }


def fetch(repo: str, state: str, limit: int) -> list[dict]:
    """`gh issue list` as JSON. Raises on a non-zero exit rather than guessing."""
    out = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", state,
         "--limit", str(limit), "--json", "number,title,labels,createdAt,updatedAt"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def build(issues: list[dict], *, repo: str) -> dict:
    """Shape the committed document. Counts are derived from `rows`, so the
    page never has to trust a total that disagrees with the list under it."""
    rows = sorted((row_for(i) for i in issues), key=lambda r: r["number"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo,
        "open": len(rows),
        "by_area": dict(Counter(r["area"] for r in rows).most_common()),
        "by_type": dict(Counter(r["type"] for r in rows).most_common()),
        "by_priority": dict(Counter(r["priority"] for r in rows).most_common()),
        "blocked": sum(1 for r in rows if r["blocked"]),
        "rows": rows,
    }


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

    doc = build(issues, repo=args.repo)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"{out}: {doc['open']} open, {len(doc['by_area'])} areas, "
          f"{doc['by_priority'].get('unset', 0)} unprioritised, {doc['blocked']} blocked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
