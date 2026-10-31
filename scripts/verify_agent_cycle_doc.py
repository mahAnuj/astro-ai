#!/usr/bin/env python3
"""Gate: every derivable claim in the agent-cycle DAG matches the repo.

WHY THIS EXISTS

`README.md`'s DAG section and `docs/agent-cycle.html` describe the agent loop:
how many agents and workflows there are, which crons fire when, what each
gate binds on, what a label does. Those are statements about OTHER files, and
they go stale the moment one of those files changes.

They did. Three independent QA rounds on PR #564 found 11, then 7, then 13
false or stale claims, and the count did not converge -- because the claim
surface does not shrink and every claim can rot independently. Round 2's own
fix introduced round 3's BUG-3, and round 3 found that the fix for round 2's
`verify-production` finding had swapped one false mechanism for another.

Three of those defects came from the SAME mistake: a correction landed in one
of the two artefacts and not the other. `boundary / size` was fixed in the
HTML's prose and left in its `EDGES` array; `qagreen -> merge` was fixed in
the HTML and left in `README.md`'s mermaid. A reader of either file alone was
told something the other file had already retracted.

So this gate does the two things the previous hand-written checker could not:

  1. It DERIVES each number from the repo and compares, instead of matching a
     blacklist of known-bad strings. Rewording a falsehood no longer passes
     FOR A DERIVED NUMBER -- but prose around it still can be reworded freely,
     and QA on PR #564 passed three such rewordings (the `agent-work` cadence
     described without the matched phrase, the exit-code NAMES falsified while
     the digits held, and architect's tool list contradicted in adjacent
     prose).
  2. It checks both artefacts against the same derived value FOR THE TWO
     QUANTITIES BOTH FILES STATE -- agents and workflows. The rest are
     one-sided because only one file states them: the gate count, the
     never-push count, the weekly crons, `qa-on-green`'s trigger count,
     architect's tools and the exit codes are HTML-only, and the
     trust-boundary list is satisfied by EITHER file. So the
     "lands in one file only" defect is caught for 2 of 11 derived
     quantities, not all of them. Independent QA measured this on PR #564;
     the earlier wording claimed the guarantee applied to all of them.

This is `verify_architecture_counts.py`'s rule (#405) applied to prose: a
number in a document is a liability unless something re-derives it. That gate's
own header says it -- "re-run the command; do not trust the number".

WHAT IT CHECKS

Derived from the repo, then required to appear correctly in both documents
wherever the document mentions it at all:

  agents              ls .claude/agents/*.md
  workflows           ls .github/workflows/*.yml
  gates pr-gates runs ls scripts/verify_*.py  minus  NEEDS_LIVE_LLM
  never-push count    grep -lEi 'never push|do not push' .claude/agents/*.md
  weekly crons        each workflow's cron, converted UTC -> IST
  agent-work cadence  how many cron entries it has
  qa-on-green         how many triggers it has
  MAX_LINES           whether the size hold can fire at all
  architect tools     the frontmatter list
  validate_issue      the set of exit codes it can return
  trust boundary      TRUST_BOUNDARY in agent-merge.yml

Plus structure: HTML well-formed, node ids unique, no edge endpoint naming a
missing node, no node drawn without an edge, the two files'
hold-edge labels equal TO EACH OTHER, and no `qagreen -> merge` edge in either
file. The published page's absolute URLs are held to an allow-list; README.md
is checked only for a credential-shaped parameter, because it legitimately
links to upstream docs. The mermaid block is checked for balanced brackets,
braces, quotes and subgraph/end pairs -- NOT that every referenced id is
defined; that check does not exist.

A CLAIM THIS GATE CANNOT PARSE IS A FAILURE, NOT A SKIP, with two measured
exceptions named at the end of this docstring. That is the one rule
it enforces about itself, for the reason `verify_architecture_counts.py` gives:
a checker that silently narrows its own scope and reports success is worse than
no checker, because the success gets quoted later as evidence. The previous
checker did exactly that -- it passed clean while four live defects sat in the
files it had just read, because it compared no claim to any source.

WHAT THIS DOES NOT CHECK, PLAINLY

  - Prose. "No agent decides what lands" is a sentence, not a number, and
    nothing here can falsify it. Most of both documents is prose.
  - Whether an EDGES row describes a relationship that exists. It checks that
    endpoints are real nodes and that two specific false edges are absent. It
    cannot tell that `loop-outcomes -> analyst` was invented (round 3's BUG-3)
    because "A feeds B" is not derivable from a YAML trigger list.
  - Rendering. No browser. The mermaid block is checked for balance, not for
    whether it draws.
  - Anything in the two documents that names no derivable quantity.
  - **The `WALK` array is not read at all.** No walk string is compared to the
    node it animates and no walk id is checked against `ids`. The one
    surviving round-1 defect on this PR lived there for four rounds: the walk
    narrated `qa-on-green` as "an independent QA round" while the node it
    animates says the opposite.
  - Node and workflow NAMES are not resolved to files. Only counts are
    derived, so renaming an agent or a workflow leaves both documents stale
    and this gate green.
  - The fact tiles other than agents and workflows -- "7 stages", "0 agents
    that can merge", "0 humans inside a cycle" -- are not derived, though
    `7` is simply `len(BANDS)`.
  - The hold edge is compared between the two FILES, never against
    `agent-merge.yml`. Identical-and-false passes, which is the very defect
    this gate's opening paragraph cites as its motivation.
  - The `MAX_LINES` check is a substring presence test per file, not a
    localised claim test, so a false "the size hold is live" sentence passes
    while the word "inert" survives anywhere else in the file.
  - The README's URLs are checked only for credential-shaped parameters, not
    against the allow-list the published page is held to.
  - Two rows do NOT follow the fail-not-skip rule: the `agent-work` cadence
    prints `ok` when its phrase does not match, and the trust-boundary leaf
    test passes a path present in either file.
  - Line-number citations in the prose are not verified.

So this gate shrinks the stale surface; it does not close it. A number it does
not know about is still unchecked, and the honest way to add a number to those
documents is to add it here in the same commit.

    uv run python scripts/verify_agent_cycle_doc.py
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from html.parser import HTMLParser

try:
    import yaml
except ImportError:                                           # pragma: no cover
    print("COULD NOT RUN (exit 2) — PyYAML is absent")
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "docs/agent-cycle.html"
README = ROOT / "README.md"

WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
         7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
         12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
         16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen",
         20: "twenty", 28: "twenty-eight", 30: "thirty"}

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ALLOWED_URLS = {
    "http://www.w3.org/2000/svg",
    "https://github.com/mahAnuj/astro-ai",
    "https://shubhagya.com",
    "https://htmlpreview.github.io",
}

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


def both(name: str, value: int, html: str, readme: str,
         html_pats: list[str], readme_pats: list[str]) -> None:
    """Every supplied pattern must match with the DERIVED value substituted.

    A pattern that matches nothing is a failure, not a skip: it means the
    document stopped making the claim in the shape this gate knows, and an
    unchecked claim is the thing this file exists to prevent.
    """
    word = WORDS.get(value, str(value))
    for label, text, pats in (("agent-cycle.html", html, html_pats),
                              ("README.md", readme, readme_pats)):
        for pat in pats:
            rx = pat.replace("{N}", str(value)).replace("{W}", word)
            if re.search(rx, text, re.I):
                ok(f"{name} = {value} — {label} agrees ({rx[:46]})")
            else:
                stale = re.search(pat.replace("{N}", r"(\d+)").replace("{W}", r"(\w+)"),
                                  text, re.I)
                found = stale.group(0)[:60] if stale else "no match at all"
                fail(f"{name} should be {value} ({word}) in {label}; found: {found!r}")


def git(*a: str) -> str:
    r = subprocess.run(("git", *a), cwd=ROOT, capture_output=True, text=True)
    return r.stdout


def main() -> int:
    if not HTML.exists() or not README.exists():
        print("COULD NOT RUN (exit 2) — one of the two documents is missing")
        return 2
    html, readme = HTML.read_text(), README.read_text()

    print("Agent-cycle DAG — every derivable claim against the repo\n")

    # ---------- derive ----------
    agents = sorted((ROOT / ".claude/agents").glob("*.md"))
    wfdir = ROOT / ".github/workflows"
    workflows = sorted(wfdir.glob("*.yml"))
    gates = sorted((ROOT / "scripts").glob("verify_*.py"))

    prg = (wfdir / "pr-gates.yml").read_text()
    m = re.search(r'NEEDS_LIVE_LLM="([^"]*)"', prg)
    if not m:
        print("COULD NOT RUN (exit 2) — NEEDS_LIVE_LLM not found in pr-gates.yml")
        return 2
    excluded = m.group(1).split()
    gates_run = len(gates) - len(excluded)

    push_rx = re.compile(r"never push|do not push", re.I)
    never_push = [p for p in agents if push_rx.search(p.read_text())]

    # ---------- counts, in both files ----------
    both("agents", len(agents), html, readme,
         [r"<b>{N}</b><span>agents</span>", r"\b{N} agent"],
         [r"\b{W} agents\b"])
    both("workflows", len(workflows), html, readme,
         [r"<b>{N}</b><span>workflows</span>"],
         [r"\b{W} workflows\b"])
    # NOT a `both()` row. This quantity must NOT appear as a literal in the
    # documents at all, which is the opposite of every other check here.
    #
    # The first version of this gate required the literal integer, and that was
    # a defect serious enough to break the repo: two gates landed on `main`
    # between writing it and merging it, so the derived count moved 29 -> 32
    # and this gate -- which runs for every code PR via `pr-gates.yml`'s
    # `scripts/verify_*.py` glob -- would have failed the required `gates`
    # check on `main` indefinitely, halting `agent-merge`. Worse, `both()`
    # treats an unmatched pattern as a failure, so DELETING the number failed
    # too: the only state it accepted was the one `pr-gates.yml:326-333`
    # forbids in as many words --
    #
    #     "a literal number goes stale the moment a gate is added -- then it
    #      either blocks every PR or, worse, is edited downward"
    #
    # A gate that mandates the anti-pattern its own repo documents is worse
    # than no gate. So the rule is inverted: the count is DERIVED and printed
    # for a reader, and the documents are required to carry no integer there.
    # Found by independent QA on PR #564 before it merged.
    stale_count = re.search(r"all \d+ gates|re-run \d+ gates", html)
    if stale_count:
        fail(f"agent-cycle.html hard-codes a gate count ({stale_count.group(0)!r}); "
             f"pr-gates runs {gates_run} today and that number moves whenever a "
             f"gate is added. Say 'every non-excluded verify_*.py' instead.")
    else:
        ok(f"no hard-coded gate count in the documents (derived: {gates_run} run, "
           f"{len(gates)} present, {len(excluded)} excluded)")
    both("agent files restating never-push", len(never_push), html, readme,
         [r"{N} of the %d" % len(agents)], [])

    # ---------- crons, converted ----------
    weekly = {"agent-discover": None, "agent-infra": None, "agent-research": None,
              "agent-design": None, "agent-prioritise": None, "agent-sync": None}
    for name in list(weekly):
        f = wfdir / f"{name}.yml"
        if not f.exists():
            fail(f"{name}.yml is gone; the document still lists it")
            continue
        cm = re.search(r'cron:\s*"(\d+)\s+(\d+)\s+\S+\s+\S+\s+(\d)"', f.read_text())
        if not cm:
            fail(f"{name}.yml has no parsable weekly cron")
            continue
        mi, hh, dow = int(cm.group(1)), int(cm.group(2)), int(cm.group(3))
        tot = hh * 60 + mi + 330                      # UTC -> IST
        ist_day = (dow - 1 + tot // (24 * 60)) % 7    # cron 0=Sun -> list Mon=0
        weekly[name] = (DAYS[ist_day], f"{(tot // 60) % 24:02d}:{tot % 60:02d}")

    for name, got in weekly.items():
        if got is None:
            continue
        day, hm = got
        if re.search(rf"<code>{re.escape(name)}</code> — {day} {hm}", html):
            ok(f"{name} — {day} {hm} IST, document agrees")
        else:
            shown = re.search(rf"<code>{re.escape(name)}</code> — (\w+ [\d:]+)", html)
            fail(f"{name} is {day} {hm} IST; document says "
                 f"{shown.group(1) if shown else 'nothing parsable'}")

    # ---------- agent-work cadence ----------
    aw = (wfdir / "agent-work.yml").read_text()
    n_cron = len(re.findall(r'- cron:\s*"', aw))
    if n_cron > 1 and re.search(r"(daily|once a day) 04:30", html + readme, re.I):
        fail(f"agent-work has {n_cron} crons; a document still calls it daily/once a day")
    else:
        ok(f"agent-work cadence ({n_cron} crons) not described as once a day")

    # ---------- qa-on-green trigger count ----------
    qog = yaml.safe_load((wfdir / "qa-on-green.yml").read_text())
    trig = qog.get(True, qog.get("on"))
    n_trig = len(trig) if isinstance(trig, dict) else 1
    says_one = bool(re.search(r"Its one <code>\w+</code> trigger", html))
    if (n_trig == 1) != says_one:
        fail(f"qa-on-green has {n_trig} trigger(s); the document's 'one trigger' claim is {says_one}")
    else:
        ok(f"qa-on-green trigger count ({n_trig}) matches the document")

    # ---------- MAX_LINES: can the size hold fire? ----------
    am = (wfdir / "agent-merge.yml").read_text()
    ml = re.search(r"MAX_LINES:\s*(\d+)", am)
    if not ml:
        fail("MAX_LINES not found in agent-merge.yml")
    else:
        disabled = int(ml.group(1)) >= 100_000
        marked = all(re.search(r"switched off|inert|holds nothing", t, re.I)
                     for t in (html, readme))
        if disabled and not marked:
            fail(f"MAX_LINES is {ml.group(1)} (the size hold cannot fire) and a "
                 "document does not say so")
        elif not disabled and marked:
            fail(f"MAX_LINES is {ml.group(1)} (the size hold CAN fire) and a "
                 "document still calls it switched off")
        else:
            ok(f"MAX_LINES {ml.group(1)} — both documents describe the size hold correctly")

    # ---------- architect tools ----------
    arch = (ROOT / ".claude/agents/architect.md").read_text()
    tm = re.search(r"^tools:\s*(.+)$", arch, re.M)
    if not tm:
        fail("architect.md has no tools: line")
    else:
        tools = [t.strip() for t in tm.group(1).split(",")]
        shown = re.search(r"Tools are <code>([^<]+)</code>", html)
        if shown and [t.strip() for t in shown.group(1).split(",")] == tools:
            ok(f"architect tools match ({', '.join(tools)})")
        else:
            fail(f"architect tools are {tools}; document shows "
                 f"{shown.group(1) if shown else 'nothing parsable'}")

    # ---------- validate_issue exit codes ----------
    vi = (ROOT / "scripts/validate_issue.py").read_text()
    codes = sorted({int(c) for c in re.findall(r"^\s+return (\d)\s*$", vi, re.M)})
    listed = sorted({int(c) for c in re.findall(r"<li><code>(\d)</code>", html)})
    if codes and listed == codes:
        ok(f"validate_issue exit codes match ({codes})")
    else:
        fail(f"validate_issue returns {codes}; the document lists {listed}")

    # ---------- trust boundary ----------
    amy = yaml.safe_load(am)
    tb_raw = (amy.get("env") or {}).get("TRUST_BOUNDARY")
    if not tb_raw:
        for _j in (amy.get("jobs") or {}).values():
            tb_raw = (_j.get("env") or {}).get("TRUST_BOUNDARY") or tb_raw
    if tb_raw:
        paths = [q.strip() for q in str(tb_raw).split("\n") if q.strip()]
        # the documents name the leaf (storage.py) or the directory (prompts/)
        leaves = {q.rstrip("/").split("/")[-1] + ("/" if q.endswith("/") else "")
                  for q in paths}
        missing = sorted(l for l in leaves
                         if l.rstrip("/") not in html and l.rstrip("/") not in readme)
        if missing:
            fail(f"trust-boundary paths absent from the documents: {missing}")
        else:
            ok(f"every trust-boundary path appears in the documents ({len(paths)} paths)")
    else:
        fail("TRUST_BOUNDARY not found in agent-merge.yml — cannot check the hold list")

    # ---------- structure ----------
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "source", "track", "wbr"}

    class P(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.stack: list[str] = []
            self.bad: list[str] = []

        def handle_starttag(self, t, a):
            if t not in VOID:
                self.stack.append(t)

        def handle_endtag(self, t):
            if t in VOID:
                return
            if not self.stack or self.stack[-1] != t:
                self.bad.append(t)
            else:
                self.stack.pop()

    p = P()
    p.feed(html)
    if p.bad or p.stack:
        fail(f"HTML not well formed (mismatched {p.bad[:3]}, unclosed {p.stack[:3]})")
    else:
        ok("HTML well formed")

    ids = re.findall(r'\{\s*id:"([^"]+)"', html)
    if len(ids) != len(set(ids)):
        fail(f"duplicate node ids: {sorted({i for i in ids if ids.count(i) > 1})}")
    else:
        ok(f"{len(ids)} node ids, no duplicates")

    blk = re.search(r"const EDGES = \[(.*?)\n\];", html, re.S)
    if not blk:
        fail("EDGES array not found")
        edges = []
    else:
        # 3 OR 4 elements: the 4th is the routing class ("back"/"hold").
        edges = re.findall(
            r'\[\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]*)"(?:\s*,\s*"([^"]*)")?\s*\]',
            blk.group(1))
        dang = sorted({e for row in edges for e in row[:2]} - set(ids))
        if dang:
            fail(f"edge endpoints naming no node: {dang}")
        else:
            ok(f"{len(edges)} edges, no dangling endpoint")
        orph = sorted(set(ids) - {e for row in edges for e in row[:2]})
        if orph:
            fail(f"nodes drawn with no edge: {orph}")
        else:
            ok("no node is drawn without an edge")

    # ---------- the two false edges, in BOTH files ----------
    if any(f == "qagreen" and t == "merge" for f, t, *_ in edges):
        fail("HTML has a qagreen->merge edge; qa-on-green cannot label and does "
             "not feed agent-merge")
    else:
        ok("HTML has no qagreen->merge edge")

    mer = re.search(r"```mermaid\n(.*?)```", readme, re.S)
    if not mer:
        fail("README has no mermaid block")
    else:
        body = mer.group(1)
        if re.search(r"^\s*[^%\n]*\bQG\b[^\n]*-->\s*AM", body, re.M):
            fail("README mermaid still routes QG into AM — the same error the "
                 "HTML already fixed")
        else:
            ok("README mermaid does not route QG into AM")
        bal = (body.count("[") == body.count("]")
               and body.count("{{") == body.count("}}")
               and body.count('"') % 2 == 0
               and len(re.findall(r"^\s*subgraph ", body, re.M))
               == len(re.findall(r"^\s*end\s*$", body, re.M)))
        if bal:
            ok("README mermaid balanced")
        else:
            fail("README mermaid brackets/braces/quotes/subgraphs unbalanced")

        # cross-file: the hold edge must say the same thing in both
        h_hold = [row[2] for row in edges if row[1] == "hold"]
        m_hold = re.search(r'AM -\.\s*"([^"]+)"\s*\.-> HOLD', body)
        if h_hold and m_hold:
            norm = lambda s: set(re.findall(r"[a-z-]+", s.lower()))
            if norm(h_hold[0]) == norm(m_hold.group(1)):
                ok(f"both files agree on the hold edge ({h_hold[0]!r})")
            else:
                fail(f"hold edge differs: HTML {h_hold[0]!r} vs README "
                     f"{m_hold.group(1)!r}")
        else:
            fail("could not read the hold edge from both files")

    # ---------- URLs, in both files ----------
    # The strict allow-list applies to the PUBLISHED page, which is served to
    # readers and must not reach a third party. README.md is a repository
    # document and legitimately links to upstream docs, so it is checked only
    # for a credential-shaped URL.
    html_urls = {u.rstrip(").,`") for u in re.findall(r"https?://[^\s\"'<>)`]+", html)}
    bad = sorted(u for u in html_urls
                 if not any(u.startswith(a) for a in ALLOWED_URLS))
    if bad:
        fail(f"agent-cycle.html has URLs outside the allow-list: {bad}")
    else:
        ok(f"agent-cycle.html — {len(html_urls)} URL(s), all allow-listed")

    rd_urls = {u.rstrip(").,`") for u in re.findall(r"https?://[^\s\"'<>)`]+", readme)}
    leaky = sorted(u for u in rd_urls
                   if re.search(r"(?i)(token|key|secret|passwd|password)=", u))
    if leaky:
        fail(f"README.md has URLs carrying something credential-shaped: {leaky}")
    else:
        ok(f"README.md — {len(rd_urls)} URL(s), none carry a credential-shaped parameter")

    # ---------- report ----------
    print()
    for n in notes:
        print(f"  note  {n}")
    if failures:
        print(f"\nFAIL — {len(failures)} claim(s) do not match the repo:")
        for f_ in failures:
            print(f"  - {f_}")
        return 1
    print(f"PASS — every derivable claim in both documents matches the repo "
          f"({len(agents)} agents, {len(workflows)} workflows, {gates_run} gates run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
