#!/usr/bin/env python3
"""What the loop should learn from: its own errors, its own outcomes, and rivals.

WHY THIS EXISTS
---------------
Owner, 2026-11-06: "I want the agents to learn and improve, learn what they did
but not helped in improving, learn from other competitors and apply those
things" -- "there should be continuous feedback loop from their own actions and
as well as from researching other websites".

Every signal already existed, but each sat on a single issue or PR thread, and no
agent ever read the set. QA FAIL verdicts sat on PRs. The analyst's HIT/MISS
scores sat on closed issues. Rivals reached the loop only as one-off issues. So
the same mistake could recur and the same idea could be re-filed, and nothing
noticed. This collector, which is deterministic and calls no LLM, folds the last
WINDOW_DAYS of all three into one ledger the planners read and `/sync` reviews
weekly:

  measurements/lessons.json   machine-readable
  measurements/lessons.md     what an agent reads before planning

WHAT IT READS (GitHub REST, raw JSON; every filter is in Python so it is tested)
-------------------------------------------------------------------------------
* OUR ERRORS
  - QA FAIL verdicts: `claude[bot]` comments whose first line starts
    `QA: FAIL`, each tagged with error THEMES by keyword (grounding, tests,
    tokens, i18n, security, ...)
  - reverted commits on main
  - failed verify-production runs (production did not satisfy its invariants)
  - ops findings from scripts/detect_ops_regressions.py
* OUR OUTCOMES -- the analyst's post-ship verdicts on closed issues (HIT, MISS,
  INCONCLUSIVE, PENDING, UNSCOREABLE), latest per issue, by `claude[bot]`, read
  only from comments that also say `metric` or `predicted`
* RIVALS -- issues carrying the hidden `<!-- competitor-pattern -->` marker that
  the discover loop writes, one per pattern seen on a competing site

A theme that recurs at least REPEAT_AT times in the window is listed under
"Repeated", which is what `/sync` turns into a definition fix or an issue.

THE GROUNDING RULE IS PRINTED INTO THE LEDGER. A competitor pattern may suggest
what to BUILD: structure, tools, wording, speed. It never imports an astrological
claim. A rule seen on a rival site ships only once it traces to knowledge/*.md.

EXIT CODES
----------
  0 written   1 nothing readable (the previous files are left standing)   2 bad args
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

WINDOW_DAYS = 30
REPEAT_AT = 2
MAX_PAGES = 40     # ~600 comments a week here, so 30 days needs ~25 pages
BOT = "claude[bot]"
COMPETITOR_MARK = "<!-- competitor-pattern -->"

#: Error themes by keyword. Keywords are FAILURE language, not the boilerplate every
#: verdict carries: QA always states its test runs and a token cost, so the first
#: cut ("token", "tests") tagged 40 of 43 FAILs and named nothing. Only the defect part
#: of a verdict is scanned (see _defect_text). Lowercase.
THEMES: dict[str, tuple[str, ...]] = {
    "grounding":   ("unsourced", "no source", "not in the corpus", "not in the book",
                    "citation", "cites a section", "untraceable", "not classical"),
    "tokens":      ("over budget", "exceeds the budget", "ceiling", "429", "unmeasured token",
                    "token claim", "tpm bucket"),
    "tests":       ("survived", "did not catch", "passes on main", "reimplement", "no test",
                    "untested", "test is vacuous", "would pass with"),
    "i18n":        ("hindi", "i18n", "translation", "untranslated"),
    "security":    ("xss", "injection", "unescaped", "leak", "secret", "exploitable"),
    "copy":        ("overclaim", "false claim", "misleading", "stale prose", "says the opposite",
                    "contradicts", "wrong copy"),
    "performance": ("latency", "timeout", "slow", "gcs round", "hot path"),
    "regression":  ("regression", "breaks", "broke", "500", "502", "crash", "exception"),
}
_DEFECT = re.compile(r"\b(blocking|defect|regression|finding|fails? because|what broke)\b", re.I)


def _defect_text(text: str) -> str:
    """The part of a verdict that names what is wrong: from the first BLOCKING /
    DEFECT / FINDING onwards, or the whole text when there is no such marker."""
    m = _DEFECT.search(text)
    return text[m.start():] if m else text


VERDICTS = ("HIT", "MISS", "INCONCLUSIVE", "PENDING", "UNSCOREABLE")
_VERDICT = re.compile(r"\b(" + "|".join(VERDICTS) + r")\b")
#: Prefer the word right after "verdict": a comment that says "MISS so far" and later
#: mentions an INCONCLUSIVE sibling issue must read as MISS.
_AFTER_VERDICT = re.compile(r"verdict[^A-Za-z\n]{0,12}(?:\*\*)?\s*(" + "|".join(VERDICTS) + r")\b", re.I)
#: Both shapes QA writes: the marker line qa_verdict.sh posts, and the full verdict.
_FAIL = re.compile(r"^(?:#+\s*)?QA(?: verdict)?:\s*FAIL", re.I)

Runner = Callable[[list[str]], str]


def run_gh(args: list[str]) -> str:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {p.stderr.strip()[:200]}")
    return p.stdout


def _pages(gh: Runner, url: str, key: str | None = None) -> list[dict]:
    """REST pages until a short one. Manual paging: `--paginate` breaks behind
    some proxies, and the tests need to see exactly what is requested."""
    out: list[dict] = []
    sep = "&" if "?" in url else "?"
    for page in range(1, MAX_PAGES + 1):
        raw = gh(["api", f"{url}{sep}per_page=100&page={page}"])
        data = json.loads(raw or "[]")
        rows = data.get(key, []) if key else data
        out.extend(rows)
        if len(rows) < 100:
            break
    return out


def _ts(s: str | None) -> float:
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%dT%H:%M:%S").timestamp()
    except ValueError:
        return 0.0


def themes_of(text: str) -> list[str]:
    t = text.lower()
    return [name for name, kws in THEMES.items() if any(k in t for k in kws)]


def collect(gh: Runner, repo: str, now: datetime, ops_findings: list[dict]) -> dict:
    since = (now - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # NEWEST FIRST: oldest-first with a page cap silently reads only the start of
    # the window -- measured on the first run, 1 QA FAIL found in 30 days.
    comments = _pages(gh, f"repos/{repo}/issues/comments?since={since}&sort=created&direction=desc")
    comments = [c for c in comments if (c.get("created_at") or "") >= since]
    comments.sort(key=lambda c: c.get("created_at") or "")

    mine = [c for c in comments if (c.get("user") or {}).get("login") == BOT]
    by_thread: dict[int, list[dict]] = {}
    for c in mine:
        by_thread.setdefault(int(str(c.get("issue_url", "")).rsplit("/", 1)[-1] or 0), []).append(c)

    qa_fail, latest_verdict, seen_fail = [], {}, set()
    for num, thread in by_thread.items():
        for c in thread:
            body = c.get("body") or ""
            if _FAIL.match(body.split("\n", 1)[0].strip()):
                # The marker line carries no detail; the full verdict sits beside it. One
                # FAIL per thread per 10 minutes, its text merged from both comments.
                at = c.get("created_at") or ""
                key = (num, at[:15])            # YYYY-MM-DDTHH:M -> 10-minute bucket
                near = " ".join((d.get("body") or "") for d in thread
                                if abs(_ts(d.get("created_at")) - _ts(at)) <= 600)
                if key in seen_fail:
                    continue
                seen_fail.add(key)
                qa_fail.append({"number": num, "at": at, "url": c.get("html_url"),
                                "summary": body[:300].replace("\n", " "), "themes": themes_of(_defect_text(near))})
                continue
            low = body.lower()
            if "metric" in low or "predicted" in low:
                m = _AFTER_VERDICT.search(body) or _VERDICT.search(body)
                if m:
                    latest_verdict[num] = {"number": num, "verdict": m.group(1).upper(),
                                           "at": c.get("created_at"), "url": c.get("html_url")}

    reverts = [{"sha": c["sha"][:7], "message": c["commit"]["message"].split("\n", 1)[0],
                "at": c["commit"]["author"]["date"]}
               for c in _pages(gh, f"repos/{repo}/commits?sha=main&since={since}")
               if c.get("commit", {}).get("message", "").startswith("Revert")]

    vp_failed = [{"run": r["id"], "at": r["created_at"], "sha": r["head_sha"][:7]}
                 for r in _pages(gh, f"repos/{repo}/actions/workflows/verify-production.yml/runs"
                                     f"?status=failure&created=>={since[:10]}", key="workflow_runs")]

    competitors = []
    for i in _pages(gh, f"repos/{repo}/issues?state=all&since={since}"):
        if i.get("pull_request") is None and COMPETITOR_MARK in (i.get("body") or ""):
            competitors.append({"number": i["number"], "title": i["title"], "state": i["state"],
                                "url": i.get("html_url"),
                                "labels": [l["name"] for l in i.get("labels", [])]})

    theme_counts = Counter(t for f in qa_fail for t in f["themes"])
    outcome_counts = Counter(v["verdict"] for v in latest_verdict.values())
    repeated = sorted(t for t, n in theme_counts.items() if n >= REPEAT_AT)
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": WINDOW_DAYS,
        "errors": {"qa_fail": qa_fail, "reverts": reverts, "verify_production_failed": vp_failed,
                   "ops_findings": ops_findings},
        "error_themes": dict(theme_counts.most_common()),
        "repeated_themes": repeated,
        "outcomes": sorted(latest_verdict.values(), key=lambda v: v["number"]),
        "outcome_counts": dict(outcome_counts),
        "competitor_patterns": competitors,
    }


def render(doc: dict) -> str:
    e = doc["errors"]
    lines = [f"# Lessons — last {doc['window_days']} days (generated {doc['generated_at']})", "",
             "Read this before planning, specifying or ranking. It is the loop's memory of what",
             "failed, what moved nothing, and what rivals do. Built by `scripts/collect_lessons.py`;",
             "deterministic, no LLM.", "",
             "> **Grounding rule.** A competitor pattern may suggest what to BUILD (structure, tools,",
             "> wording, speed). It never imports an astrological claim: a rule seen on a rival site",
             "> ships only once it traces to `knowledge/*.md`.", ""]
    lines += ["## Repeated error themes: act on these", ""]
    if doc["repeated_themes"]:
        for t in doc["repeated_themes"]:
            nums = sorted({f["number"] for f in e["qa_fail"] if t in f["themes"]})
            lines.append(f"- **{t}** — {doc['error_themes'][t]} QA FAIL(s): "
                         + ", ".join(f"#{n}" for n in nums))
    else:
        lines.append("- none at or above the repeat threshold")
    lines += ["", "## Our errors", "",
              f"- QA FAIL verdicts: {len(e['qa_fail'])}",
              f"- reverted commits on main: {len(e['reverts'])}"
              + "".join(f"\n  - `{r['sha']}` {r['message']}" for r in e["reverts"][:10]),
              f"- failed verify-production runs: {len(e['verify_production_failed'])}",
              f"- ops findings now: {len(e['ops_findings'])}"
              + "".join(f"\n  - [{f.get('level','?')}] {f.get('kind','?')}: {f.get('title','')}"
                        for f in e["ops_findings"]), ""]
    lines += ["## Our outcomes (analyst verdicts, latest per issue)", ""]
    if doc["outcomes"]:
        lines.append("counts: " + ", ".join(f"{k} {v}" for k, v in sorted(doc["outcome_counts"].items())))
        lines += [f"- #{o['number']}: {o['verdict']}" for o in doc["outcomes"]]
        lines += ["", "A MISS is the most useful line here: before proposing work of the same kind, say why "
                  "this time differs, or do not propose it."]
    else:
        lines.append("- no scored verdicts in the window")
    lines += ["", "## Competitor patterns", ""]
    if doc["competitor_patterns"]:
        for c in sorted(doc["competitor_patterns"], key=lambda c: c["state"] != "open"):
            lines.append(f"- #{c['number']} [{c['state']}] {c['title']}")
    else:
        lines.append("- none recorded yet: discover writes one issue per pattern with "
                     f"`{COMPETITOR_MARK}`")
    return "\n".join(lines) + "\n"


def ops_from_detector() -> list[dict]:
    """The detector's current findings, or [] if it cannot run here."""
    try:
        p = subprocess.run([sys.executable, "scripts/detect_ops_regressions.py", "--json"],
                           capture_output=True, text=True, timeout=120)
        data = json.loads(p.stdout or "{}")
        return data.get("findings", []) if isinstance(data, dict) else []
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def main(argv: list[str], gh: Runner = run_gh, now: datetime | None = None,
         ops: Callable[[], list[dict]] = ops_from_detector) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out-dir", required=True)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    try:
        doc = collect(gh, a.repo, now or datetime.now(timezone.utc), ops())
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"::warning::lessons not refreshed ({exc}); the previous files are left standing")
        return 1
    out = Path(a.out_dir)
    (out / "lessons.json").write_text(json.dumps(doc, indent=1) + "\n")
    (out / "lessons.md").write_text(render(doc))
    print(f"lessons: {len(doc['errors']['qa_fail'])} QA FAILs, repeated themes "
          f"{doc['repeated_themes'] or 'none'}, {len(doc['outcomes'])} verdicts, "
          f"{len(doc['competitor_patterns'])} competitor patterns")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
