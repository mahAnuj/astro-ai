#!/usr/bin/env python3
"""Build the Research team's reading list from open issues, each run (#1030).

WHY THIS EXISTS
---------------
agent-research's prompt carried a hand-typed "standing queue" of issue numbers.
Measured 2026-11-15: it named #177..#230 and none of the muhurat sourcing issues
filed the day before (#1027-#1029), so the books would have arrived and the
agent would have mined them for last month's questions. Every new need for a
source meant a workflow edit, which the loop cannot author (#421).

Now the need is declared where it is found -- on the issue -- and this script
collects it. An open issue is queued when EITHER:

  * it carries the label `skill:knowledge-integrator` (an explicit request:
    "extract this from the books"), or
  * its Evidence Block's `corpus:` field says `[UNSOURCED]` -- the convention
    verify_issue_evidence.py already names as "routes to the corpus loop". It
    was routed nowhere until this script.

Order: priority:high, priority:medium, unlabelled, priority:low; an explicit
request before a bare [UNSOURCED]; then oldest first. Capped, because a
75-minute run that is handed 40 issues finishes none.

A manual dispatch may pin the list instead (`--only 1027,1029`).

No model, no write: it reads issues and prints markdown.
EXIT CODES: 0 written (the list may be empty)   2 could not read the issues
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str]], str]
LABEL = "skill:knowledge-integrator"
#: Only issues FILED by this repository's own identities reach the research
#: agent, which may Write knowledge/*.md and holds Bash and WebFetch. QA on
#: #1063: an outsider's issue saying `corpus: [UNSOURCED]` was queued as item 1
#: with its title verbatim -- the #361 shape. The same closed set as
#: AGENT_AUTHORS in agent-merge.yml (owner taken from the repo slug);
#: tests/test_research_queue.py pins the two together.
BOT_AUTHORS = ("claude[bot]", "github-actions[bot]", "shubhagya-publisher[bot]")


def trusted(issue: dict, repo: str) -> bool:
    login = (issue.get("user") or {}).get("login", "")
    return login in BOT_AUTHORS or login == repo.split("/")[0]
CAP = 8
_PRIORITY = {"priority:high": 0, "priority:medium": 1, "priority:low": 3}

_spec = importlib.util.spec_from_file_location(
    "verify_issue_evidence", Path(__file__).resolve().parent / "verify_issue_evidence.py")
_vie = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vie)


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def open_issues(gh: Runner, repo: str) -> list[dict]:
    issues: list[dict] = []
    for page in range(1, 11):
        batch = json.loads(gh(["api", f"repos/{repo}/issues?state=open&per_page=100&page={page}"]))
        issues += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            break
    return issues


def reason(issue: dict) -> str | None:
    labels = {lb["name"] for lb in issue.get("labels") or []}
    if LABEL in labels:
        return f"labelled {LABEL}"
    corpus = _vie.field(issue.get("body") or "", "corpus") or ""
    if re.search(r"\[UNSOURCED\]", corpus, re.I):
        return "corpus: [UNSOURCED]"
    return None


def rank(issue: dict, why: str) -> tuple:
    labels = {lb["name"] for lb in issue.get("labels") or []}
    pri = min((_PRIORITY[lb] for lb in labels if lb in _PRIORITY), default=2)
    return (pri, 0 if why.startswith("labelled") else 1, issue["number"])


def build(gh: Runner, repo: str, only: list[int] | None = None, cap: int = CAP) -> list[tuple[dict, str]]:
    issues = [i for i in open_issues(gh, repo) if trusted(i, repo)]
    if only:
        by_num = {i["number"]: i for i in issues}
        return [(by_num[n], "pinned by the dispatch") for n in only if n in by_num]
    picked = [(i, w) for i in issues if (w := reason(i))]
    picked.sort(key=lambda p: rank(*p))
    return picked[:cap]


VERIFY_FIRST = Path(__file__).resolve().parent.parent / "measurements" / "verify-first.json"


def verify_first_section(path: Path = VERIFY_FIRST, top: int = 5) -> str:
    """The busiest pages, from scripts/busiest_pages.py (2026-11-15). Owner: "look
    at what users are spending more time on and make sure that is absolutely
    working fine ... 100% correctness". Absent file -> nothing, never an error."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return ""
    rows = (doc.get("rows") or [])[:top]
    if not rows:
        return ""
    win = doc.get("window") or ["?", "?"]
    out = ["", f"## Verify first: the busiest pages ({win[0]}..{win[1]}, measurements/verify-first.json)", "",
           "After the queue above: audit every astrological claim and rule these pages",
           "show against knowledge/*.md, unless an issue from the last 30 days already",
           "covers that page (search issues for its path). File one issue per page with defects.", ""]
    for r in rows:
        out.append(f"- {r['path']}: {r.get('engaged_sessions')} engaged sessions, "
                   f"{r.get('gsc_impressions')} impressions; serves: {r.get('serves')}")
    return "\n".join(out) + "\n"


def render(picked: list[tuple[dict, str]], total_note: str = "") -> str:
    lines = ["## Research queue (built this run from open issues)", ""]
    if not picked:
        lines.append("Empty: no open issue is labelled `skill:knowledge-integrator` or says "
                     "`corpus: [UNSOURCED]`. Fall back to the standing queue.")
    for n, (i, why) in enumerate(picked, 1):
        lines.append(f"{n}. #{i['number']} — {i['title'][:140]}  ({why})")
    if total_note:
        lines += ["", total_note]
    return "\n".join(lines) + "\n"


def parse_only(raw: str) -> list[int] | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if not re.fullmatch(r"\d{1,6}(,\d{1,6}){0,19}", raw.replace(" ", "")):
        raise ValueError(f"--only takes comma-separated issue numbers, got {raw[:40]!r}")
    return [int(x) for x in raw.replace(" ", "").split(",")]


def main(argv: list[str] | None = None, gh: Runner = run_gh) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--cap", type=int, default=CAP)
    args = ap.parse_args(argv)
    try:
        only = parse_only(args.only)
    except ValueError as exc:
        print(f"::error::{exc}")
        return 2
    try:
        picked = build(gh, args.repo, only, args.cap)
    except (RuntimeError, ValueError) as exc:
        print(f"::error::could not read issues: {exc}")
        return 2
    sys.stdout.write(render(picked) + verify_first_section())
    return 0


if __name__ == "__main__":
    sys.exit(main())
