#!/usr/bin/env python3
"""Turn `detect_ops_regressions.py`'s findings into issues the loop works.

WHY THIS EXISTS
---------------
The detector's own header says "a carrier workflow turns findings into issues"
-- and none did. Measured 2026-11-03: nothing in `.github/workflows/` ran the
detector; only `chief` read it, and only when an escalation woke it. The owner
then asked for exactly the missing half: "the agent monitoring the ops
dashboard should look at these data to take action and finetune".

So this is the carrier, deterministic and cheap, run from `agent-steward.yml`
twice a day. Every finding becomes ONE open issue per `kind`, which
`project-manager` ranks and `/agent-cycle` works like any other. Each finding's
detail names its lever ("stop dispatching ranked cycles that end in nothing",
"more cron slots", ...), so the issue is workable, not a status line.

THE RULES THAT KEEP IT FROM BECOMING NOISE
------------------------------------------
* One issue per kind, found by a hidden `<!-- ops-finding: <kind> -->` marker on
  an OPEN issue this workflow filed (`github-actions[bot]`). Never a second.
* An existing issue gets a comment only when the finding CHANGED (level or
  title); the same finding twice a day is silence.
* A finding that has gone gets ONE "cleared" comment and is left open. Closing
  is not this script's: CLAUDE.md names the three things that close issues, and
  a measurement dipping under a threshold for one run is not "fixed".
* `unreadable` sources are not filed: the detector already counts them, and an
  issue saying "could not read a file" is the stale-measurement finding's job.

Issues filed by `github-actions[bot]` are TRUSTED by `resolve_provenance.py`
(SELF_APPS, 2026-11-02), so a cycle can work them.

EXIT CODES: 0 done (including nothing to do), 1 an API write failed, 2 bad args.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Callable

WRITER = "github-actions[bot]"
MARK = "ops-finding"
_KIND = re.compile(r"<!-- ops-finding: ([a-z0-9-]+) -->")
_STATE = re.compile(r"<!-- ops-state: (.*?) -->")
CLEARED = "<!-- ops-cleared -->"

Runner = Callable[[list[str]], str]


def run_gh(args: list[str]) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {p.stderr.strip()[:200]}")
    return p.stdout


def _state(f: dict) -> str:
    """What a finding IS, for change detection: level and title. The detail
    carries live numbers that move every run and would make every run a change."""
    return f"{f['level']}|{f['title']}".replace("--", "-")


def _same(a: str | None, b: str) -> bool:
    """Whether two recorded states are the same FINDING. Numbers are ignored
    (2026-11-06): the title carries a live percentage, so #697 got four comments
    for "idle 90% -> 89% -> 88% -> 89%" while nothing about the finding changed.
    The level still counts, so amber -> red is always said."""
    norm = lambda s: re.sub(r"\d+(?:\.\d+)?", "#", s or "")
    return a is not None and norm(a) == norm(b)


#: Priority by severity (2026-11-06, owner: "such issues should also be
#: prioritised"). Both labels exist on the repository; project-manager ranks
#: on them. A red finding is a broken loop or a quota about to bind.
PRIORITY = {"red": "priority:high", "amber": "priority:medium"}


def _set_priority(gh: Runner, repo: str, number: int, level: str) -> None:
    want = PRIORITY.get(level)
    if not want:
        return
    gh(["api", "-X", "POST", f"repos/{repo}/issues/{number}/labels", "-f", f"labels[]={want}"])
    for other in set(PRIORITY.values()) - {want}:
        try:
            gh(["api", "-X", "DELETE", f"repos/{repo}/issues/{number}/labels/{other}"])
        except RuntimeError:
            pass            # 404: it was not there


def open_findings(gh: Runner, repo: str) -> dict[str, dict]:
    """kind -> {number, state, cleared} for every open ops-finding issue."""
    raw = gh(["api", "--paginate", f"repos/{repo}/issues?state=open&creator={WRITER}&per_page=100",
              "--jq", '.[] | select(.pull_request == null) | {number, body}'])
    out: dict[str, dict] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        i = json.loads(line)
        m = _KIND.search(i.get("body") or "")
        if m and m.group(1) not in out:
            s = _STATE.search(i.get("body") or "")
            out[m.group(1)] = {"number": i["number"], "state": s.group(1) if s else ""}
    return out


def last_comment_state(gh: Runner, repo: str, number: int) -> tuple[str | None, bool]:
    """(the newest ops-state recorded in a comment, whether the newest marker is CLEARED)."""
    raw = gh(["api", "--paginate", f"repos/{repo}/issues/{number}/comments?per_page=100",
              "--jq", f'.[] | select(.user.login == "{WRITER}") | .body'])
    state, cleared = None, False
    for body in raw.split("\x00") if "\x00" in raw else [raw]:
        for m in re.finditer(r"<!-- ops-state: (.*?) -->|" + re.escape(CLEARED), body):
            if m.group(0) == CLEARED:
                cleared = True
            else:
                state, cleared = m.group(1), False
    return state, cleared


#: Exempts the issue from the traffic fields of the evidence gate; the label
#: exists on the repository (checked 2026-11-03) -- `labels[]=` on a missing one
#: is dropped by the API without an error.
LABEL = "chore"

def body_for(f: dict, now: str) -> str:
    return (f"<!-- {MARK}: {f['kind']} -->\n<!-- ops-state: {_state(f)} -->\n"
            f"**{f['level'].upper()}: {f['title']}**\n\n{f['detail']}\n\n"
            # The loop's own intake gate (scripts/verify_issue_evidence.py) refuses an
            # issue with no Evidence Block: agent-cycle labels it needs-evidence and
            # project-manager never ranks it. QA round 2 on #691 measured exactly that
            # -- filed and never worked. `chore` (applied in carry()) exempts it from
            # gsc:/ga4:, and the shell repro yields NO-REPRO at validate_issue.py, so
            # step 0 can never close one on a probe.
            f"## Evidence Block\n"
            f"- corpus: n/a — operational measurement from measurements/*.json, no classical source involved\n"
            f"- tokens: 0 measured — no LLM path is touched; the lever is the loop's own schedule\n"
            f"- thesis: acting on the lever named above brings this reading back under its threshold\n"
            f"- metric: `{f['kind']}` fires 0 times in the next 7 days (thresholds in scripts/detect_ops_regressions.py)\n"
            f"- repro: `uv run python scripts/detect_ops_regressions.py --json` -> no finding of kind {f['kind']}\n\n"
            f"Filed by `agent-steward`'s ops carrier from `scripts/detect_ops_regressions.py` "
            f"at {now}. One issue per finding kind: it is commented on when the finding "
            f"changes and when it clears, never refiled. See `/admin/ops`.")


def carry(gh: Runner, repo: str, findings: list[dict], now: str) -> dict:
    stats = {"filed": 0, "updated": 0, "unchanged": 0, "cleared": 0}
    existing = open_findings(gh, repo)
    seen = set()
    for f in findings:
        kind = f["kind"]
        if kind in seen:            # one issue per kind even if the detector repeats one
            continue
        seen.add(kind)
        cur = existing.get(kind)
        if cur is None:
            args = ["api", "-X", "POST", f"repos/{repo}/issues",
                    "-f", f"title=[OPS] {f['title']}", "-f", f"body={body_for(f, now)}",
                    "-f", f"labels[]={LABEL}"]
            if PRIORITY.get(f["level"]):
                args += ["-f", f"labels[]={PRIORITY[f['level']]}"]
            gh(args)
            stats["filed"] += 1
            continue
        last, cleared = last_comment_state(gh, repo, cur["number"])
        prev = last or cur["state"]
        if _same(prev, _state(f)) and not cleared:
            stats["unchanged"] += 1
            continue
        if not prev or prev.split("|", 1)[0] != f["level"]:
            _set_priority(gh, repo, cur["number"], f["level"])
        gh(["api", "-X", "POST", f"repos/{repo}/issues/{cur['number']}/comments",
            "-f", f"body=<!-- ops-state: {_state(f)} -->\n**Now {f['level'].upper()}: "
                  f"{f['title']}** ({now})\n\n{f['detail']}"])
        stats["updated"] += 1
    for kind, cur in existing.items():
        if kind in seen:
            continue
        _, cleared = last_comment_state(gh, repo, cur["number"])
        if cleared:
            continue
        gh(["api", "-X", "POST", f"repos/{repo}/issues/{cur['number']}/comments",
            "-f", f"body={CLEARED}\nThe `{kind}` finding did not fire at {now}. Left open: one "
                  f"clean reading is not a fix, and closing belongs to the mechanisms CLAUDE.md "
                  f"names. It is commented on again if the finding returns."])
        stats["cleared"] += 1
    return stats


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--findings", required=True, help="detect_ops_regressions.py --json output file")
    try:
        a = ap.parse_args(argv[1:])
        doc = json.loads(open(a.findings).read())
    except (SystemExit, OSError, json.JSONDecodeError) as exc:
        print(f"::error::file_ops_findings.py: bad input ({exc})")
        return 2
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%MZ")
    try:
        stats = carry(gh, a.repo, doc.get("findings") or [], stamp)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"::error::ops findings could not be filed: {exc}")
        return 1
    print(f"ops findings: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
