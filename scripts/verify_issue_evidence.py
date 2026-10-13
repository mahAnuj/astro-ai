#!/usr/bin/env python3
"""Validate an issue's Evidence Block. `/agent-cycle` step 1 calls this.

WHY THIS EXISTS
---------------
It did not. `.claude/commands/agent-cycle.md` has called
`scripts/verify_issue_evidence.py <n>` since the Evidence Block convention was
written, and the file was never created (#286). So step 1 — "No Evidence Block,
or a failing one -> label `needs-evidence` and move on. An agent must not reach
an engineer on a guess." — has never run.

That absence is not inert. Two measurable things grew in the gap:

  1. `project-manager` ranks issues with no Evidence Block at all, because
     nothing refuses them. The rule exists only as prose.
  2. The `repro:` field drifted into a SECOND DIALECT. `scripts/validate_issue.py`
     parses exactly one grammar -- `(GET|POST) <path> -> <status> contains "x"`
     -- while every `repro:` line now in the backlog is a shell command
     (`grep -c ...`, `git log ...`, `gh api ...`). Measured 2026-10-13 across
     the 66 open issues: 9 carry a `repro:`, and **0 of 66 are executable by
     validate_issue.py**. The probe `/agent-cycle` step 0 is built around has
     never had a single input it could run.

BOTH DIALECTS ARE CORRECT, AND THAT IS THE POINT
------------------------------------------------
This script does not pick a winner, because the two answer different questions
and agent-cycle's own step 0 already asks for both:

    "A claim about the code -> read it and quote the lines.
     A claim about content  -> count it (`grep -c`, the registry, the template)."

A repo grep cannot tell you production is fixed -- that is the whole premise of
validate_issue.py ("an open issue is not evidence that the problem still
exists"). And an HTTP probe cannot tell you a template still contains a line.
So: `http` repros are reported as executable by validate_issue.py, `shell`
repros as executable by the caller, and a `repro:` that is neither is a FAIL.

EXIT CODES
----------
0 pass (or exempt)   1 fail   2 could not run -- NOT a pass
Exit 2 matters: `pr-gates.yml` treats it as a failure precisely so a gate that
could not run cannot be mistaken for a gate that passed.

NO ARGUMENTS = SELF-TEST
------------------------
`pr-gates.yml` sweeps `for f in scripts/verify_*.py` and runs each with no
arguments, requiring exit 0. A gate that needs an issue number has nothing to
assert there -- but a parser with no test is how the `repro:` drift went
unnoticed for the life of the convention. So with no arguments this validates
its own parser against fixtures, including the three real formats found in the
backlog. It can go red, which is the only property that makes a gate worth
having.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

# Issues filed before the convention are EXEMPT. agent-cycle.md states why, and
# it is the difference between a gate and an outage:
#
#   "Every one of the 50 issues open on 2026-10-08 predates the convention;
#    enforcing it strictly would mean the loop can never work any of them, and
#    a gate that blocks the entire backlog is not a gate, it is an outage."
#
# A date, not a list, so the exemption shrinks by itself as the backlog turns
# over. Raising it to excuse a NEW issue would be relaxing a guardrail.
CONVENTION_DATE = "2026-10-08"

# `- **gsc:**`, `**gsc:**`, `gsc:` and `- gsc:` all appear in the backlog.
# agent-discover writes the bold form; the steward writes the bare one. A
# validator that accepted only one would reject its own team's output -- which
# is exactly how validate_issue.py came to be unable to read #329, #311 and #276.
def field(text: str, name: str) -> str | None:
    """Return the value of `name:` in any of the four spellings used in anger."""
    # The bold closes AFTER the colon -- agent-discover writes `- **corpus:**`,
    # not `- **corpus**:`. Getting that wrong left a literal "** " on the front
    # of every value, which only `corpus:` noticed, because it is the one field
    # matched at position 0; the others search for a digit anywhere and passed
    # regardless. The self-test below is what caught it.
    m = re.search(
        rf"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?{re.escape(name)}(?:\*\*)?:(?:\*\*)?[ \t]*"
        rf"(.+?)(?=\n[ \t]*(?:[-*][ \t]*)?(?:\*\*)?\w[\w -]*(?:\*\*)?:(?:\*\*)?|\n[ \t]*#|\Z)",
        text,
        re.M | re.S | re.I,
    )
    if not m:
        return None
    # Belt and braces: strip any stray emphasis the shapes above did not absorb.
    return " ".join(m.group(1).split()).lstrip("*").strip()


def classify_repro(value: str) -> tuple[str, str]:
    """('http'|'shell'|'bad', why).

    `http` is the subset scripts/validate_issue.py can execute. Its parser is
    `re.match(r"(GET|POST)\\s+(\\S+)")` plus a `-> <status>`; anything claiming
    to be an HTTP probe without a status line would parse and then assert
    nothing, so it is rejected here rather than silently passing there.
    """
    v = value.strip().strip("`")
    if re.match(r"(GET|POST)\s+\S+", v, re.I):
        if not re.search(r"->\s*(?:follow\s*->\s*)?\d{3}", v):
            return "bad", "looks like an HTTP probe but states no expected status, so validate_issue.py would assert nothing"
        return "http", "executable by scripts/validate_issue.py"
    # A shell probe must state an expectation, or it is a description. The
    # arrow, a "returns"/"expected", or an explicit count all qualify.
    if re.search(r"(->|=>|\breturns?\b|\bexpect(?:ed)?\b|\byields?\b)", v, re.I):
        return "shell", "executable by the caller; not by validate_issue.py"
    return "bad", "states a command but no expected result, so nothing can fail"


def check(body: str, labels: list[str], created: str) -> tuple[int, list[str]]:
    """Return (exit_code, lines). Pure: no network, so the self-test can use it."""
    out: list[str] = []
    if created and created[:10] < CONVENTION_DATE:
        return 0, [f"EXEMPT — filed {created[:10]}, before the convention ({CONVENTION_DATE}).",
                   "  The premise must still be established under step 0; this gate does not excuse that."]

    is_bug = "bug" in labels
    problems: list[str] = []

    # gsc:/ga4: -- one is mandatory, with a window. Bugs are exempt: a broken
    # feature needs no traffic thesis to justify fixing (agent-cycle.md).
    gsc, ga4 = field(body, "gsc"), field(body, "ga4")
    if is_bug:
        out.append("ok   gsc:/ga4: — exempt, labelled `bug`")
    elif not (gsc or ga4):
        problems.append("no `gsc:` or `ga4:` — a decision to build needs a measurement, not an opinion")
    else:
        got = gsc or ga4 or ""
        if not re.search(r"\d{4}-\d{2}-\d{2}", got):
            problems.append("`gsc:`/`ga4:` states no date window — without one the number cannot be scored later")
        else:
            out.append("ok   gsc:/ga4: — measurement with a date window")

    # competing: optional, but a rival claim that cannot be fetched is not evidence.
    comp = field(body, "competing")
    if comp and not re.search(r"https?://", comp):
        problems.append("`competing:` has no URL — a recollection about a rival is not evidence")
    elif comp:
        out.append("ok   competing: — carries a URL")

    # corpus: a file and a line range, or an explicit escape hatch.
    corpus = field(body, "corpus")
    if not corpus:
        problems.append("no `corpus:` — required even for bugs")
    elif re.search(r"\[UNSOURCED\]", corpus, re.I):
        out.append("ok   corpus: — [UNSOURCED], routes to the corpus loop and blocks delivery until sourced")
    elif re.match(r"n/?a\b", corpus, re.I):
        if len(corpus) < 12:
            problems.append("`corpus: n/a` with no reason — say why no source is needed")
        else:
            out.append("ok   corpus: — n/a with a stated reason")
    elif re.search(r"[Ll]\d+\s*[-–]\s*\d+|:\d+[-–]\d+|§", corpus):
        out.append("ok   corpus: — cites a line range or section")
    else:
        problems.append("`corpus:` names no line range, no §, and is not [UNSOURCED] or a justified n/a")

    # tokens: measured, not estimated.
    tokens = field(body, "tokens")
    if not tokens:
        problems.append("no `tokens:` — required even for bugs; the free Groq tier is the runtime budget")
    elif not re.search(r"\d", tokens):
        problems.append("`tokens:` states no number — an unmeasured token claim is a FAIL (qa.md)")
    elif re.search(r"\b(est|estimate[ds]?|approx|guess|~)\b", tokens, re.I) and not re.search(r"\bmeasured\b", tokens, re.I):
        problems.append("`tokens:` reads as an estimate — product-manager requires it measured")
    else:
        out.append("ok   tokens: — carries a number")

    for name, why in (("thesis", "what is expected to happen"), ("metric", "what would falsify it")):
        v = field(body, name)
        if not v:
            problems.append(f"no `{name}:` — {why}")
        elif name == "metric" and not re.search(r"\d", v):
            problems.append("`metric:` has no number — a thesis with no falsifiable metric is an opinion wearing a number")
        else:
            out.append(f"ok   {name}:")

    repro = field(body, "repro")
    if not repro:
        problems.append("no `repro:` — step 0 cannot establish the premise without one")
    else:
        kind, why = classify_repro(repro)
        if kind == "bad":
            problems.append(f"`repro:` {why}")
        else:
            out.append(f"ok   repro: — {kind}, {why}")

    for p in problems:
        out.append(f"FAIL {p}")
    out.append("")
    out.append(f"{'FAIL' if problems else 'PASS'} — {len(problems)} problem(s) in the Evidence Block")
    return (1 if problems else 0), out


GOOD = """
## Evidence Block
- **gsc:** window 2026-09-13 -> 2026-10-10 (28d). Row `/learn/manglik-dosh/`: 419 impressions, position 7.1.
- **competing:** (fetched 2026-10-13) https://dashaclub.com/mangal-dosha-calculator puts a button under the H1.
- **corpus:** n/a. It adds a link and one sentence of lead-in, no astrological claim.
- **tokens:** 0. Template-only change, measured; no LLM call (`routes/dosha.py:108-150`).
- **repro:** `grep -c "manglik-check" src/astro_ai/templates/learn/manglik-dosh.html` -> `0` today
- **thesis:** a reader who finds the tool one tap away will use it.
- **metric:** GA4 pages_per_session >= 1.30 on >= 10 sessions, 28 days after deploy.
"""

SELF_TESTS: list[tuple[str, str, list[str], str, int]] = [
    ("a real agent-discover block (bold fields, shell repro)", GOOD, [], "2026-10-13", 0),
    ("bare fields, http repro",
     'gsc: impressions=2410 window=2026-09-01..09-28\ncorpus: knowledge/a.md L22-46\n'
     'tokens: measured 2180 input/request\nrepro: GET /kundli -> 200 contains "Lagna"\n'
     'thesis: x\nmetric: 10 sessions\n', [], "2026-10-13", 0),
    ("pre-convention issue is exempt even when empty", "nothing here", [], "2026-10-07", 0),
    ("bug is exempt from gsc/ga4 but not from corpus/tokens",
     'corpus: n/a — workflow change, no astrological claim\ntokens: 0 measured\n'
     'repro: GET /health -> 200 contains "ok"\nthesis: x\nmetric: 1 run\n',
     ["bug"], "2026-10-13", 0),
    ("missing gsc on a non-bug fails", GOOD.replace("- **gsc:**", "- **noise:**"), [], "2026-10-13", 1),
    ("gsc with no date window fails",
     'gsc: impressions=2410\ncorpus: a.md L1-2\ntokens: 0 measured\nrepro: GET / -> 200\n'
     'thesis: x\nmetric: 1\n', [], "2026-10-13", 1),
    ("estimated tokens fails", GOOD.replace("- **tokens:** 0. Template-only change, measured;",
                                            "- **tokens:** ~approx 2000 est;"), [], "2026-10-13", 1),
    ("competing without a URL fails",
     GOOD.replace("https://dashaclub.com/mangal-dosha-calculator", "that rival calculator site"),
     [], "2026-10-13", 1),
    ("an HTTP repro with no expected status fails",
     GOOD.replace('`grep -c "manglik-check" src/astro_ai/templates/learn/manglik-dosh.html` -> `0` today',
                  "GET /kundli"), [], "2026-10-13", 1),
    ("a repro with no expectation at all fails",
     GOOD.replace('`grep -c "manglik-check" src/astro_ai/templates/learn/manglik-dosh.html` -> `0` today',
                  "`grep -c manglik-check template.html`"), [], "2026-10-13", 1),
    ("metric with no number fails", GOOD.replace("- **metric:** GA4 pages_per_session >= 1.30 on >= 10 sessions, 28 days after deploy.",
                                                 "- **metric:** it should get better."), [], "2026-10-13", 1),
    ("corpus naming no line range fails", GOOD.replace("- **corpus:** n/a. It adds a link and one sentence of lead-in, no astrological claim.",
                                                       "- **corpus:** the Rao book."), [], "2026-10-13", 1),
]


def self_test() -> int:
    print("verify_issue_evidence self-test — the parser, against the formats really in use\n")
    bad = 0
    for name, body, labels, created, want in SELF_TESTS:
        got, _ = check(body, labels, created)
        ok = got == want
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'} {name}  (want {want}, got {got})")
    # The drift this gate exists to catch: the real backlog's repro dialect.
    kind, _ = classify_repro('`git log --all --oneline -- data/x.pdf` -> 1 commit, 3c1b74b')
    if kind != "shell":
        print(f"  FAIL a real shell repro classified as {kind!r}, expected 'shell'"); bad += 1
    else:
        print("  ok   a real shell repro classifies as 'shell'")
    kind, _ = classify_repro('GET /kundli -> 200 contains "Lagna"')
    if kind != "http":
        print(f"  FAIL a real http repro classified as {kind!r}, expected 'http'"); bad += 1
    else:
        print("  ok   a real http repro classifies as 'http'")
    print()
    if bad:
        print(f"FAIL — {bad} self-test(s) failed")
        return 1
    print(f"PASS — {len(SELF_TESTS) + 2} self-tests; both repro dialects classify correctly")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("issue", nargs="?", type=int, help="issue number; omit to self-test the parser")
    args = ap.parse_args()
    if args.issue is None:
        return self_test()

    out = subprocess.run(
        ["gh", "issue", "view", str(args.issue), "--json", "body,labels,createdAt,title"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        # 2, not 1. A validator that could not read the issue has not judged it.
        print(f"COULD NOT VERIFY (exit 2) — gh issue view {args.issue} failed: "
              f"{out.stderr.strip()[:200]}\n  This is NOT a pass.")
        return 2
    d = json.loads(out.stdout)
    labels = [l["name"] for l in d.get("labels") or []]
    print(f"#{args.issue} {d.get('title', '')[:70]}")
    print(f"  labels: {', '.join(labels) or 'none'}\n")
    code, lines = check(d.get("body") or "", labels, d.get("createdAt") or "")
    for line in lines:
        print(f"  {line}" if line else "")
    if code:
        print("  -> label `needs-evidence` and move on. Do NOT dispatch an engineer.")
    return code


if __name__ == "__main__":
    sys.exit(main())
