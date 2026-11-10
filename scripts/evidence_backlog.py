#!/usr/bin/env python3
"""List the open issues the build loop refuses for a missing Evidence Block.

WHY THIS EXISTS
---------------
Measured 2026-11-10: 112 issues open, and `verify_issue_evidence.py` failed
**63** of them. The loop's Step 1 refuses those, on purpose -- an engineer must
not start on a guess -- and the cycle also refuses to write the missing block
itself, because that would be grading its own eligibility. `project-manager`
named "retrofit the Evidence Blocks" as its second item on every ranking and is
read-only inside a cycle. So nobody did it, and the 63 included every
wrong-in-front-of-users finding the auditors had filed (#581, #714-#716, #777).
The last two build cycles that day built nothing.

This is the deterministic half of the fix. It reads every open issue over REST
(body plus comments, since a comment may carry the block -- the checker reads
the LAST occurrence of each field), runs the same `check()` the loop runs, and
writes the failing ones in harm order: astrology-correctness first, then
priority:high, then bug, then the rest, oldest first within each. The agent
half is `agent-prioritise.yml` in `mode=evidence`, which retrofits or closes
from this list; `chain_cycle.py` dispatches it when 3 or more issues fail the gate.

Prints the markdown list (or writes it to --out). No arguments beyond that.

EXIT CODES: 0 listed (an empty list is still 0)   2 could not read the backlog
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str]], str]

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("verify_issue_evidence", _HERE / "verify_issue_evidence.py")
vie = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vie)


def run_gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip()[:200])
    return out.stdout


def harm_key(labels: list[str], number: int) -> tuple:
    s = set(labels)
    return (0 if "astrology-correctness" in s else 1,
            0 if "priority:high" in s else 1,
            0 if "bug" in s else 1,
            number)


def failing(gh: Runner, repo: str) -> list[dict]:
    issues: list[dict] = []
    for page in range(1, 6):
        batch = json.loads(gh(["api", f"repos/{repo}/issues?state=open&per_page=100&page={page}"]))
        issues += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            break
    out = []
    for i in issues:
        labels = [lb["name"] for lb in i.get("labels") or []]
        if "provenance:outsider" in labels:
            # An outsider's issue is triaged before it is built
            # (triage_outsider_issues.py); a retrofit would launder its claims.
            continue
        comments = json.loads(gh(["api", f"repos/{repo}/issues/{i['number']}/comments?per_page=100"])) \
            if i.get("comments") else []
        text = "\n".join([i.get("body") or ""] + [c.get("body") or "" for c in comments])
        code, lines = vie.check(text, labels, i.get("created_at") or "")
        if code != 0:
            out.append({"number": i["number"], "title": i["title"], "labels": labels,
                        "problems": [ln[5:] for ln in lines if ln.startswith("FAIL ")]})
    out.sort(key=lambda r: harm_key(r["labels"], r["number"]))
    return out


def render(rows: list[dict], total_open: int | None = None) -> str:
    head = f"# Issues failing the Evidence Block gate: {len(rows)}"
    if total_open is not None:
        head += f" of {total_open} open"
    lines = [head, "", "Harm order: astrology-correctness, priority:high, bug, then the rest.", ""]
    for r in rows:
        lines.append(f"- #{r['number']} [{', '.join(r['labels']) or 'no labels'}] {r['title']}")
        for p in r["problems"]:
            lines.append(f"    - {p}")
    return "\n".join(lines) + "\n"


def main(argv: list[str], gh: Runner = run_gh) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args(argv[1:])
    repo = os.environ.get("GH_REPO", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        print("::error::evidence_backlog.py needs GH_REPO=owner/name")
        return 2
    try:
        rows = failing(gh, repo)
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"::error::could not read the backlog ({exc.__class__.__name__}: {str(exc)[:120]})")
        return 2
    text = render(rows)
    if args.out:
        Path(args.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
