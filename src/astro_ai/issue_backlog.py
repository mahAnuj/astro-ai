"""Derive the open-issue backlog the /admin/ops page shows (#335, #353).

WHY THIS IS IN `src/` AND NOT IN `scripts/`
-------------------------------------------
Both callers need the same derivation, and only one of them can see
`scripts/`:

    scripts/collect_issue_backlog.py   the nightly collector, commits issues.json
    src/astro_ai/ops_data.py           /admin/ops, which now fetches live (#353)

The Docker image copies `pyproject.toml uv.lock README.md` and `src/` and
nothing else, so a function the page needs cannot live under `scripts/`. It was
there first, when the committed file was the only reader.

Duplicating it instead would be worse than a move. `ops_data` states as an
invariant that "no number on this page is computed twice", and a second copy of
`derive_priority` is exactly how the live count and the committed snapshot it
falls back to would start disagreeing about the same issue -- with no way for a
reader to tell which of the two was wrong.

WHAT IS DERIVED, AND WHY IT IS DERIVED RATHER THAN READ
-------------------------------------------------------
#335 asked for "issues category wise count". There is no usable category label:
measured on 2026-10-14 across 66 open issues, `category:technical` appears 4
times, `category:content` once and `seo` once. Inventing a label taxonomy here
would be work this module has no authority to do, and back-filling 66 issues is
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

So `ask` comes off a ladder of heading synonyms. Two things it must NOT do, both
found by measuring rather than by reasoning:

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

Stdlib only, and no import of anything else in this package: the collector adds
`src/` to `sys.path` and imports this module alone, so a dependency here would
drag the whole app into a workflow that only wants to shape some JSON.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
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


def read_objective(path: str = "OBJECTIVE.md") -> str:
    """The one line every loop ranks against, from OBJECTIVE.md's blockquote.

    Called only by the collector -- OBJECTIVE.md is not in the container, which
    is precisely why the objective is committed into issues.json instead of
    being read by the page. It lives here so the collector imports one name
    from this module rather than reaching for a private helper, and the
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


def build(issues: list[dict], *, repo: str, objective: str = "",
          generated_at: str | None = None) -> dict:
    """Shape the document both callers hand to the page.

    Counts are derived from `rows`, so the page never has to trust a total that
    disagrees with the list under it.

    `objective` is passed in rather than read here. The collector reads it from
    OBJECTIVE.md; the live path cannot, because OBJECTIVE.md is not in the
    container -- it carries the objective over from the committed snapshot
    instead. Either way the page gets the field in the same place.
    """
    rows = sorted((row_for(i) for i in issues), key=lambda r: r["number"], reverse=True)
    return {
        "generated_at": generated_at or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo,
        "objective": objective,
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


#: GitHub's REST API. Used only by `fetch_live`; the collector shells out to
#: `gh`, which every workflow in this repo already has on PATH.
API_BASE = "https://api.github.com"

#: One page holds 100 issues and the backlog is 67, so the normal case is a
#: single request. The cap bounds the worst case: without it a backlog that
#: grew past 400 would turn one page render into five serial round trips.
MAX_PAGES = 4

#: GitHub rejects a request with no User-Agent.
_UA = "astro-ai-admin-ops"


def fetch_live(repo: str, *, timeout: float, token: str | None = None) -> list[dict]:
    """Open issues straight from the REST API, in the shape `gh` returns.

    Raises on any failure -- the caller decides what to show instead, and for
    /admin/ops that is the committed snapshot. Swallowing the error here would
    make an empty backlog indistinguishable from an unreachable API.

    PULL REQUESTS ARE ISSUES ON THIS ENDPOINT. `/repos/{repo}/issues` returns
    both, and every PR carries a `pull_request` key; `gh issue list` filters
    them out for you and the REST API does not. Without the filter the open
    backlog would be inflated by every open PR -- the single most likely way
    for this path to disagree with the committed file it falls back to.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": _UA,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    out: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        url = (f"{API_BASE}/repos/{repo}/issues"
               f"?state=open&per_page=100&page={page}")
        req = urllib.request.Request(url, headers=headers)  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            batch = json.loads(resp.read().decode("utf-8"))
        if not isinstance(batch, list):
            raise ValueError(f"{url} did not return a list")
        issues = [i for i in batch if "pull_request" not in i]
        out.extend({
            "number": i["number"],
            "title": i.get("title") or "",
            "body": i.get("body") or "",
            # snake_case on the REST API, camelCase from `gh`. Normalised here
            # so `row_for` stays one function with one input shape.
            "createdAt": i.get("created_at"),
            "updatedAt": i.get("updated_at"),
            "labels": [{"name": lab.get("name", "")} for lab in (i.get("labels") or [])],
        } for i in issues)
        if len(batch) < 100:
            break
    return out
