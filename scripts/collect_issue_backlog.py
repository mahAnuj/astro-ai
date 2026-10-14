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

THE ASK LINE IS EXTRACTED, AND HALF THE TIME IT CANNOT BE
---------------------------------------------------------
A title says what is WRONG; a reader ranking the queue needs what is REQUIRED.
The bodies carry it, but there is no shared structure to read it from: measured
2026-10-14 across the 65 open issues there are 40+ distinct section headings for
the same job -- Scope, Fix, Required, Proposed change, What to do, Proposed
work, Suggested fix, Design, Recommendation, Options, What it would take -- and
12 issues have no headings at all.

So `ask` comes off a ladder of heading synonyms, then the body preamble. Two
things it must NOT do, both found by measuring rather than by reasoning:

  * "scope" matches inside "Out of scope". #335's ask came out as "The public
    mirror on anujmahajan.com", lifted from its out-of-scope list -- a
    confident sentence saying the opposite of the truth. Hence _NEGATIVE.
  * a matched section often opens with something that is not a statement: a
    bare file path (#327), a config value (#266 -> "BHAGYA_LLM_PROVIDERS=..."),
    a colon lead-in (#263 -> "Not a design task. Roughly:"), or the redesign
    epic's shared preamble "Part of #233. Depends on #241." which 10 of the
    #242-#251 children emit identically. Hence _usable().

With both guards about half the backlog yields a real ask and half yields
nothing. `ask` is then "" and the page shows a blank, because an issue with no
readable statement of the work is a triage finding worth seeing -- filling the
row with boilerplate would hide exactly the issues that need rewriting. The
coverage number is printed on every run so the ratio itself is visible.

NO LLM ON THIS PATH. Every field here is a regex over text the agents already
wrote. The page must stay free to render.

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


# Headings that introduce WHAT TO DO, most explicit first. A ladder, not a key:
# see the module docstring for why there is no single heading to read.
_ASK_HEADINGS = (
    "proposed change", "proposed work", "proposed fix", "proposed move",
    "proposed check", "suggested fix", "suggested shape", "what to do",
    "what it needs", "what it would take", "what is required", "required",
    "scope", "fix", "work, in this order", "design", "two ways to close it",
    "recommendation", "immediate mitigation", "next step", "options",
)

# A heading containing any of these is about what NOT to do. Matching "scope"
# inside "Out of scope" gave #335 an ask lifted from its own exclusion list.
_NEGATIVE = (
    "out of scope", "not in scope", "explicitly out", "non-negotiable",
    "do not", "must not", "do no", "not claimed", "not done",
)

_HEADING = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.M)

# Cross-references the redesign epic's children all open with. Ten of #242-#251
# emit "Part of #233. Depends on #241." verbatim, which is provenance, not work.
_BOILERPLATE = re.compile(
    r"^(part of #\d+|depends on #\d+|fell out of|found by|surfaced by|"
    r"split out of|deferred decision|supersedes|tracking issue|housekeeping)",
    re.I,
)

# A line that is a path, a config assignment, or a verdict stamp rather than a
# sentence about work.
_PATHLIKE = re.compile(r"^[\w/.\-]*[/.](py|html|css|js|json|md|yml|yaml|pdf)\b|^/")
# `PROOF = "..."`, `BHAGYA_LLM_PROVIDERS=groq120`. The space before `=` is why
# an anchored `[A-Z0-9_]+=` missed #265.
_ASSIGNMENT = re.compile(r"^[A-Z0-9_]{4,}\s*=")
# A shell or YAML fragment pasted as the proposal: #341 gave `git log -1 ...`
# and #278 gave `run: sudo apt-get install ...`, both of which read as prose.
_CODELIKE = re.compile(
    r"^(git|gh|run|uv|npm|npx|curl|cd|sed|awk|grep|echo|sudo|python3?|docker|"
    r"gcloud|jq|cat|export|if|for|while)\b[\s:]", re.I,
)
# A machine verdict or counter line: "6 BROKEN, 2 UNKNOWN, 7 OK", "Verdict: ...".
_STATUSLINE = re.compile(r"^(verdict|status|result|page|pages)\b\s*:", re.I)
_COUNTERLINE = re.compile(r"^\d+\s+[A-Z]{2,}\b")
# A clause continuing an argument from the line above, so it cannot stand alone
# as the ask: #279's section opened "So the free route can take CI from 1/8 to 4/8."
_CONTINUATION = re.compile(
    r"^(so|then|therefore|however|but|and|also|thus|hence|besides|"
    r"note that|that said|which|because)\b", re.I,
)
# Two adjacent lowercase words -- the cheapest test for "this is prose".
_PROSE = re.compile(r"[a-z]{3}\s+[a-z]{3}")


def _sections(body: str) -> list[tuple[str, str]]:
    """[(heading, text)] for every `##`..`####` section, in document order."""
    out: list[tuple[str, str]] = []
    last: tuple[str, int] | None = None
    for m in _HEADING.finditer(body):
        if last:
            out.append((last[0], body[last[1]:m.start()]))
        last = (m.group(1).strip(), m.end())
    if last:
        out.append((last[0], body[last[1]:]))
    return out


def _strip_markup(line: str) -> str:
    """Bullet markers, code ticks, bold/italic and link syntax off one line."""
    s = re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", line.strip())
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", s)
    s = s.replace("**", "")      # an unclosed bold span, left by a line split
    s = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", s)
    # Markdown backslash-escapes, which an agent writes when a path would
    # otherwise be read as emphasis: #124's scope renders "\/\, \/rashifal\"
    # on the page unless they come off here.
    s = re.sub(r"\\([^A-Za-z0-9])", r"\1", s)
    return s.strip().rstrip("\\").strip()


def _usable(s: str) -> bool:
    """Is this line a statement of work, or one of the things measured to be
    noise? Each test below exists because a real issue produced that shape."""
    if len(s) < 25:
        return False
    if _BOILERPLATE.match(s):
        return False
    if s.endswith(":"):           # a lead-in to a list, not a statement
        return False
    if _ASSIGNMENT.match(s) or _PATHLIKE.match(s) or _CODELIKE.match(s):
        return False
    if _STATUSLINE.match(s) or _COUNTERLINE.match(s):
        return False
    if not s[:1].isalnum():       # an emoji or symbol stamp, e.g. #327's "WARN"
        return False
    if not (s[:1].isupper() or s[:1].isdigit()):
        return False              # mid-sentence fragment: #151's "the five angas"
    if _CONTINUATION.match(s):
        return False
    return bool(_PROSE.search(s))


def _first_claim(text: str, limit: int = 180) -> str:
    """The first usable sentence in `text`, trimmed to one sentence."""
    for raw in text.split("\n"):
        stripped = raw.strip()
        if not stripped or stripped.startswith(("```", "|", ">", "---", "#")):
            continue
        cleaned = _strip_markup(stripped)
        if not _usable(cleaned):
            continue
        m = re.match(r"^(.{14,%d}?[.!?])(\s|$)" % limit, cleaned)
        if m:
            return m.group(1)
        # No sentence end in range: cut on a word boundary, never mid-word, and
        # drop a dangling open bracket (#177 ended "(the section rashis.md:249").
        cut = cleaned[:limit].rsplit(" ", 1)[0] if len(cleaned) > limit else cleaned
        if cut.count("(") > cut.count(")"):
            cut = cut[:cut.rfind("(")].rstrip()
        return cut.rstrip(" ,;:-—")
    return ""


def derive_ask(body: str) -> str:
    """One plain line saying what the issue requires, or "" if none is readable.

    Tries the ask headings in order, then the preamble above the first heading.
    Never guesses: see the module docstring for why a blank is the right answer.
    """
    if not body:
        return ""
    secs = _sections(body)
    for want in _ASK_HEADINGS:
        for name, text in secs:
            low = name.lower()
            if any(neg in low for neg in _NEGATIVE):
                continue
            if low.startswith(want) or want in low:
                claim = _first_claim(text)
                if claim:
                    return claim
    # NO PREAMBLE FALLBACK. It was tried and measured: of 25 asks it produced,
    # 14 were context rather than work -- "Workflow files were deliberately not
    # touched in #272's PR" (#291), "6 BROKEN, 2 UNKNOWN, 7 OK" (#326), the
    # "Page: ..." field label the UI audits open with (#307-#310). A blank says
    # "nobody wrote down what this needs", which is true and useful. A confident
    # wrong line teaches the reader to distrust the whole column.
    return ""


def read_objective(path: str = "OBJECTIVE.md") -> str:
    """The one line every loop ranks against, from OBJECTIVE.md's blockquote.

    Committed into issues.json rather than read by the page: the Docker image
    copies only `src/`, so OBJECTIVE.md is absent from the container, and the
    backlog is the thing the objective is meant to rank. Returns "" if absent --
    chief owns that file and may not have written it yet.
    """
    p = Path(path)
    if not p.is_file():
        return ""
    for line in p.read_text().split("\n"):
        s = line.strip()
        if s.startswith(">"):
            return _strip_markup(s.lstrip("> ").strip())
    return ""


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
        # What the issue REQUIRES, not what is wrong with it. "" where no
        # statement of work could be read -- never boilerplate. See the docstring.
        "ask": derive_ask(issue.get("body") or ""),
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
         "--limit", str(limit), "--json",
         "number,title,labels,createdAt,updatedAt,body"],
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
        "objective": read_objective(),
        "open": len(rows),
        # Stated, not implied. Half the backlog has no readable ask, and a page
        # showing 30 summaries over 65 rows must say which number is which.
        "with_ask": sum(1 for r in rows if r["ask"]),
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
          f"{doc['by_priority'].get('unset', 0)} unprioritised, {doc['blocked']} blocked, "
          f"{doc['with_ask']} with a readable ask"
          + ("" if doc["objective"] else ", NO OBJECTIVE.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
