#!/usr/bin/env python3
"""Triage stage 1 for issues filed by outsiders: mechanical, no LLM, 0 Groq tokens. (#367)

WHY THIS EXISTS
---------------
The repo is public with issues enabled. #361 answers WHO filed an issue; this answers the
next question cheaply -- is it worth a human's or an agent's time yet -- using only checks a
script can make without reading the text as instructions:

  (a) Is the Evidence Block usable?   Reuses `verify_issue_evidence.check()`, imported, not
      reimplemented. A missing field is named exactly, with what a usable `repro:` looks like.
  (b) Does it duplicate an OLDER open issue?   Token-set Jaccard similarity over title+body,
      stdlib only, deterministic, threshold `DUP_THRESHOLD`. Only an older issue can be the
      candidate, so a pair is flagged once, on the newer one.

Outcomes, in this precedence (needs-detail first, then duplicate, else reviewed):

    triage:needs-detail        comment names the missing fields
    triage:possible-duplicate  comment links the candidate as #N and nothing else
    triage:reviewed            nothing is posted

THE OUTSIDER TEST HAS ONE SOURCE
--------------------------------
`scripts/resolve_provenance.py <issue>` (#361), run by argv list with the issue number only
and WITHOUT --apply. Exit 1 = outsider, proceed. Exit 0 = trusted, skip silently. Exit 2, any
other code, a timeout, or the file being absent = FAIL CLOSED: no label, no comment, this
script exits non-zero and names the cause on stderr. Labels and `author_association` are
deliberately not consulted -- a second predicate for one fact is how the two drift.

*** THE RESOLVER IS REAL NOW, AND THE CONTRACT IS READ FROM TWO SIGNALS. ***
`resolve_provenance.py` landed on `main` with #363, so the resolver-presence gate no longer
makes this script inert -- it clears that check and proceeds to `gh`. Inertness now rests
SOLELY on nothing invoking this script (no workflow, no command references it), which is a
thinner margin than the old "the file is missing" mechanism, so do not rely on it.

Provenance is read from the printed verdict line AND the exit status TOGETHER, never the
status alone: a crashing resolver exits 1, which is OUTSIDER's code, so the status by itself
cannot tell a verdict from a traceback (#377 DEF-1). `tests/test_triage_resolver_contract.py`
drives the real resolver through a real subprocess, offline, and pins that coupling.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
* AC3 (`triage:cannot-reproduce`) is NOT implemented. It needs `validate_issue.py`, which
  fetches whatever URL a `repro:` names (urllib follows redirects, off-host included) and whose
  `POST /reading` fixtures spend production Groq tokens on a stranger's say-so. There is no
  probe code here at all. (Chief's ruling on #367, constraint 5, option b.)
* No stage 2. `--cap N` bounds how many stage-2 candidates are EXAMINED per run; nothing
  is dispatched and no LLM is called.
* No close path. There is no `gh issue close`, `gh pr close`, `--state closed` or state-mutating
  `gh api` call anywhere in this file; a test scans for every one of them and
  `mutate_behaviour_suite.py` injects one to prove that test can go red.

THE ISSUE TEXT IS A STRANGER'S
------------------------------
It reaches `gh` only inside argv lists (never a shell). The comments this posts are built from
static templates plus integers: they never echo the title or the body, so an @mention, a link or
"ignore previous instructions" in an issue cannot be republished under the owner's name. The
Evidence Block problem lines come from `verify_issue_evidence`, which are fixed strings.

IDEMPOTENT
----------
One comment per issue per state, keyed by a hidden marker `<!-- triage-stage1:<state> -->`. The
state encodes the outcome plus the missing-field set or the candidate number, so a changed
state posts a new comment and an unchanged one posts nothing. A marker counts only in a comment
THIS token wrote (`viewerDidAuthor`), because the marker is public text. Superseded stage-1
labels (the three above, nothing else) are removed when the state changes.

READ-ONLY UNLESS --apply
------------------------
Without --apply nothing is written. EXIT: 0 clean, 2 anything that must not be mistaken for a
pass (resolver absent/failed, gh failed, a write failed).

    uv run python scripts/triage_outsider_issues.py                   # dry run
    uv run python scripts/triage_outsider_issues.py --apply --cap 5   # write
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
RESOLVER = ROOT / "scripts" / "resolve_provenance.py"
EVIDENCE = ROOT / "scripts" / "verify_issue_evidence.py"

LABEL_NEEDS_DETAIL = "triage:needs-detail"
LABEL_DUPLICATE = "triage:possible-duplicate"
LABEL_REVIEWED = "triage:reviewed"
# The only labels this script owns. It never touches any other `triage:*` label.
STAGE1_LABELS = (LABEL_NEEDS_DETAIL, LABEL_DUPLICATE, LABEL_REVIEWED)
LABEL_COLOUR = {LABEL_NEEDS_DETAIL: "fbca04", LABEL_DUPLICATE: "cfd3d7", LABEL_REVIEWED: "0e8a16"}
LABEL_DESC = "Outsider-issue triage stage 1 (scripts/triage_outsider_issues.py, #367)"

# Jaccard similarity of the two issues' token sets at or above which the newer one is flagged.
# Measured 2026-10-15 over the 74 open issues (2,701 comparable older/newer pairs, after `_STOP`
# strips the Evidence Block skeleton every agent-filed issue shares): median 0.058, maximum 0.275
# (#310 vs #308, two real but distinct [UI] issues on the same screen). 0.40 sits well above
# anything distinct and below a reworded duplicate (0.885 on the test's fixture; its distinct pair scores 0.256). There was
# no true duplicate in the backlog to calibrate against, so the upper side is a fixture, not data.
DUP_THRESHOLD = 0.40
# Below this many distinct tokens a similarity score is noise (two three-word issues are
# "identical"), so such an issue is never flagged and never used as a candidate.
MIN_TOKENS = 8

DEFAULT_LIMIT = 200
DEFAULT_CAP = 5
RESOLVER_TIMEOUT_S = 120

EXIT_OK, EXIT_FAIL = 0, 2

# The resolver's stdout contract, `#<n>  <VERDICT> -- <reason>`, and the exit code each
# verdict carries. Read TOGETHER, never separately: a crashing resolver exits 1, which is
# OUTSIDER's code, so the status alone cannot tell a verdict from a traceback.
_RESOLVER_VERDICT = re.compile(r"^#(\d+)\s+(TRUSTED|OUTSIDER|UNRESOLVED)\s+--", re.M)
_EXIT_VERDICT = {0: "TRUSTED", 1: "OUTSIDER", 2: "UNRESOLVED"}

# What a usable `repro:` looks like. Static text: it is the same for every issue.
REPRO_HELP = (
    "A usable `repro:` states a command or request AND what it should show, for example:\n"
    '- `repro: GET /kundli -> 200 contains "Lagna"`\n'
    "- `repro: grep -c some-text path/to/file.html -> 0`"
)

# Field names `verify_issue_evidence.check()` can report as a problem. The comment and the
# marker only ever carry names from this set -- never text taken from the issue.
KNOWN_FIELDS = ("gsc", "ga4", "competing", "corpus", "tokens", "thesis", "metric", "repro")


@dataclass
class Result:
    rc: int
    out: str = ""
    err: str = ""


# Two seams, both injected by the tests so nothing here needs a network or a subprocess.
Gh = Callable[[list], Result]          # argv AFTER `gh`
Resolver = Callable[[int], Result]     # issue number -> the resolver's exit code


def run_gh(args: list) -> Result:
    """Run `gh` with an argv list. Never a shell, so no issue text can become syntax."""
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return Result(124, "", "timeout")
    except OSError as e:
        return Result(127, "", f"{type(e).__name__}: {e}")
    return Result(p.returncode, p.stdout, p.stderr)


def run_resolver(number: int, repo: str = "") -> Result:
    """Call `resolve_provenance.py <number>` by argv. No --apply, no other argument.

    The repo reaches it through GH_REPO in the environment, which its own `--repo` default reads,
    so the argv stays "issue number only" as the ruling requires.
    """
    env = dict(os.environ)
    if repo:
        env["GH_REPO"] = repo
    try:
        p = subprocess.run([sys.executable, str(RESOLVER), str(int(number))], capture_output=True,
                           text=True, timeout=RESOLVER_TIMEOUT_S, check=False, env=env)
    except subprocess.TimeoutExpired:
        return Result(124, "", "timeout")
    except OSError as e:
        return Result(127, "", f"{type(e).__name__}: {e}")
    return Result(p.returncode, p.stdout, p.stderr)


# --------------------------------------------------------------------------------------
# Stage 1 (a): the Evidence Block. Imported from verify_issue_evidence, never reimplemented.
# --------------------------------------------------------------------------------------

_evidence_mod = None


def _load_evidence():
    global _evidence_mod
    if _evidence_mod is None:
        spec = importlib.util.spec_from_file_location("verify_issue_evidence", EVIDENCE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _evidence_mod = mod
    return _evidence_mod


def evidence_problems(body: str, labels: list, created: str) -> list:
    """The FAIL lines of `verify_issue_evidence.check()` for this body, or [] if it passes.

    The BODY ONLY. `verify_issue_evidence` also reads comments, which is right for a maintainer
    repairing an Evidence Block; here a comment is a stranger's text AND may be this script's own
    (it quotes an example `repro:`), so reading comments would let the script satisfy itself.
    """
    ev = _load_evidence()
    code, lines = ev.check(body or "", list(labels), created or "")
    if code == 0:
        return []
    # "FAIL <problem>" lines; the final summary line is "FAIL — N problem(s) ...".
    return [ln[len("FAIL "):].strip() for ln in lines
            if ln.startswith("FAIL ") and not re.match(r"FAIL\s+—\s+\d+ problem", ln)]


def missing_fields(problems: list) -> list:
    """Field names (from KNOWN_FIELDS) the problems are about, sorted, de-duplicated."""
    names = set()
    for p in problems:
        m = re.search(r"`(\w+):?`", p)
        names.add(m.group(1) if m and m.group(1) in KNOWN_FIELDS else None)
    # A problem we cannot attribute to a field still counts; it is keyed as "other" so the
    # state changes when it does, and the comment still prints the problem line itself.
    return sorted((n or "other") for n in names)


# --------------------------------------------------------------------------------------
# Stage 1 (b): duplicates. Cheap, deterministic, stdlib only.
# --------------------------------------------------------------------------------------

# Words that carry no signal, plus the Evidence Block skeleton every agent-filed issue shares.
# Without the second group two unrelated issues from the same filer score as near-duplicates.
_STOP = frozenset("""
a about above after again all also an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has
have having he her here hers him his how if in into is it its itself just more most my no nor
not now of off on once only or other our out over own same she should so some such than that
the their them then there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your
issue issues fix fixes add adds use uses used using make makes need needs should
evidence block gsc ga4 competing corpus tokens thesis metric repro measured window
impressions position clicks session sessions http https www com org html
""".split())
_TOKEN = re.compile(r"[a-z][a-z0-9_]{2,}")


def tokens_of(title: str, body: str) -> frozenset:
    text = f"{title or ''} {body or ''}".lower()
    return frozenset(t for t in _TOKEN.findall(text) if t not in _STOP)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_duplicate(issue: dict, others: list) -> tuple | None:
    """(number, score) of the best OLDER open issue at or above DUP_THRESHOLD, else None."""
    mine = tokens_of(issue.get("title"), issue.get("body"))
    if len(mine) < MIN_TOKENS:
        return None
    best: tuple | None = None
    for o in others:
        if o["number"] >= issue["number"]:
            continue                      # only an older issue can be the original
        theirs = tokens_of(o.get("title"), o.get("body"))
        if len(theirs) < MIN_TOKENS:
            continue
        score = jaccard(mine, theirs)
        if score < DUP_THRESHOLD:
            continue
        # Highest score wins; on a tie the OLDER (lower number) does, so the result is stable.
        if best is None or score > best[1] or (score == best[1] and o["number"] < best[0]):
            best = (o["number"], score)
    return best


# --------------------------------------------------------------------------------------
# The decision, and the words it is allowed to post.
# --------------------------------------------------------------------------------------

@dataclass
class Decision:
    label: str
    key: str                    # the part of the marker after `triage-stage1:`
    comment: str | None         # None = post nothing (triage:reviewed)
    problems: list = field(default_factory=list)


def marker_for(key: str) -> str:
    return f"<!-- triage-stage1:{key} -->"


def decide(issue: dict, others: list) -> Decision:
    labels = [lab["name"] for lab in issue.get("labels", [])]
    problems = evidence_problems(issue.get("body") or "", labels, issue.get("createdAt") or "")
    if problems:
        names = missing_fields(problems)
        key = "needs-detail:" + "+".join(names)
        lines = "\n".join(f"- {p}" for p in problems)
        comment = (
            f"{marker_for(key)}\n"
            "Thanks for the report. Before anyone can act on it, the Evidence Block needs more "
            f"detail. Missing or unusable: **{', '.join(names)}**.\n\n"
            f"{lines}\n\n{REPRO_HELP}\n\n"
            "Edit the issue description (not a comment) and this check will re-run. "
            "This was checked by a script; no one has judged the report yet."
        )
        return Decision(LABEL_NEEDS_DETAIL, key, comment, problems)
    dup = find_duplicate(issue, others)
    if dup:
        key = f"possible-duplicate:{int(dup[0])}"
        comment = (
            f"{marker_for(key)}\n"
            f"This looks similar to #{int(dup[0])}, which is older and still open. "
            "If it is the same problem, please add detail there. A script flagged this by word "
            "overlap only; it may be wrong, and no issue has been touched beyond this note."
        )
        return Decision(LABEL_DUPLICATE, key, comment)
    return Decision(LABEL_REVIEWED, "reviewed", None)


# --------------------------------------------------------------------------------------
# Reading the issue list, and writing.
# --------------------------------------------------------------------------------------

def list_open_issues(gh: Gh, repo: str, limit: int) -> tuple:
    """(issues, error). A list that cannot be read is an error, never an empty backlog."""
    r = gh(["issue", "list", "--repo", repo, "--state", "open", "--limit", str(limit), "--json",
            "number,title,body,labels,createdAt,comments"])
    if r.rc != 0:
        return None, f"gh issue list failed (exit {r.rc}): {r.err.strip()[:160]}"
    try:
        issues = json.loads(r.out)
        if not isinstance(issues, list):
            raise ValueError("not a list")
        for i in issues:
            int(i["number"])
    except (ValueError, KeyError, TypeError):
        return None, "gh issue list output is not the expected JSON"
    return sorted(issues, key=lambda i: int(i["number"])), None


def has_marker(issue: dict, key: str) -> bool:
    """A marker counts only in a comment THIS token wrote: it is public text, and an outsider
    who copies it into their own comment must not be able to silence the triage."""
    m = marker_for(key)
    return any(m in (c.get("body") or "") and c.get("viewerDidAuthor") is True
               for c in issue.get("comments") or [])


def already_done(issue: dict, d: Decision) -> bool:
    """The cheap skip: this exact state is already recorded, so there is nothing to do and the
    resolver need not be asked. (An outsider cannot apply these labels; it is a record, and the
    outsider decision itself is never read from a label.)"""
    have = {lab["name"] for lab in issue.get("labels", [])}
    if d.label not in have or (have & set(STAGE1_LABELS)) != {d.label}:
        return False
    return d.comment is None or has_marker(issue, d.key)


def verdict_printed(out: str, number: int) -> str | None:
    """The verdict the resolver PRINTED for `number`, or None if it printed none.

    The line is `#<n>  <VERDICT> -- <reason>` (resolve_provenance.main). Matched against
    the requested number so a reason that happens to quote another issue cannot be read
    as a second verdict.
    """
    for m in _RESOLVER_VERDICT.finditer(out or ""):
        if int(m.group(1)) == number:
            return m.group(2)
    return None


def stderr_gist(err: str) -> str:
    """The informative END of stderr, not its beginning.

    A traceback's first 100 characters are the banner and a temp path -- `Traceback (most
    recent call last):   File "/private/var/folders/...` -- while the line that names the
    failure is the LAST one. This string is what an operator reads in a FAIL line, so a
    cause that truncates before the exception announces nothing.
    """
    lines = [ln.strip() for ln in (err or "").splitlines() if ln.strip()]
    return lines[-1][:140] if lines else ""


def classify_provenance(resolver: Resolver, number: int) -> tuple:
    """('outsider'|'trusted'|'error', cause). Fail closed.

    THE EXIT CODE ALONE CANNOT BE TRUSTED. An uncaught exception in the resolver exits 1,
    which is OUTSIDER's code, so a crash and a finding are indistinguishable by status --
    and the crash direction is the expensive one: it routes a maintainer's issue into the
    outsider path and labels it. So the resolver's two statements must agree. It prints its
    verdict by contract (`#<n>  <VERDICT> -- <reason>`); a traceback carries no such line.
    Anything short of agreement is an error, never a verdict.
    """
    r = resolver(number)
    said = verdict_printed(r.out, number)
    expected = _EXIT_VERDICT.get(r.rc)
    detail = stderr_gist(r.err)

    if expected is not None and said == expected:
        if said == "TRUSTED":
            return "trusted", ""
        if said == "OUTSIDER":
            return "outsider", ""
        return "error", f"resolver reported UNRESOLVED: {detail}".rstrip(": ")

    if said is None:
        why = {124: "resolver timed out", 127: "resolver could not be executed"}.get(
            r.rc, f"resolver exited {r.rc} without printing a verdict "
                  "(a crash exits 1, the same code as OUTSIDER)")
    else:
        why = f"resolver printed {said} but exited {r.rc}"
    return "error", f"{why}: {detail}".rstrip(": ")


def apply_decision(gh: Gh, repo: str, issue: dict, d: Decision) -> list:
    """Write the decision. Returns failure strings; empty means it was recorded."""
    n, problems = str(int(issue["number"])), []
    have = {lab["name"] for lab in issue.get("labels", [])}

    def do(args: list, what: str) -> bool:
        r = gh(args)
        if r.rc != 0:
            problems.append(f"#{n}: {what} failed (gh exit {r.rc}): {r.err.strip()[:120]}")
        return r.rc == 0

    if d.comment is not None and not has_marker(issue, d.key):
        # Comment first: if it fails the label is not added, so the next run retries both.
        if not do(["issue", "comment", n, "--repo", repo, "--body", d.comment], "comment"):
            return problems
    if d.label not in have:
        do(["label", "create", d.label, "--repo", repo, "--force", "--color",
            LABEL_COLOUR[d.label], "--description", LABEL_DESC], f"create label {d.label}")
        do(["issue", "edit", n, "--repo", repo, "--add-label", d.label], f"add label {d.label}")
    for stale in STAGE1_LABELS:
        if stale != d.label and stale in have:
            do(["issue", "edit", n, "--repo", repo, "--remove-label", stale], f"remove label {stale}")
    return problems


def main(argv: list | None = None, gh: Gh = run_gh, resolver: Resolver | None = None,
         resolver_path: Path = RESOLVER) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--apply", action="store_true", help="write labels and comments (default: read-only)")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP,
                    help="at most this many stage-2 candidates are EXAMINED per run; the rest are deferred untouched for the next run, not dropped")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help="how many open issues to read (gh issue list --limit)")
    args = ap.parse_args(argv)

    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo or "") or args.cap < 0 or args.limit < 1:
        print("usage: triage_outsider_issues.py --repo OWNER/NAME (or GH_REPO) [--cap N>=0] "
              "[--limit N>=1] [--apply]", file=sys.stderr)
        return EXIT_FAIL

    # Fail closed BEFORE reading anything. Without the resolver there is no outsider test, and
    # "no resolver, therefore everyone is trusted/untrusted" is exactly what must not happen.
    if not resolver_path.is_file():
        print(f"FAIL: {resolver_path.name} is not present, so no issue can be classified as an "
              "outsider's. Nothing was labelled or commented. (#363 has not landed.)", file=sys.stderr)
        return EXIT_FAIL
    if resolver is None:
        resolver = lambda n: run_resolver(n, args.repo)  # noqa: E731

    issues, err = list_open_issues(gh, args.repo, args.limit)
    if err:
        print(f"FAIL: {err}", file=sys.stderr)
        return EXIT_FAIL
    if len(issues) >= args.limit:
        print(f"NOTE: read {len(issues)} issues, which is --limit; older issues may be unread "
              "(duplicate candidates are drawn from what was read).", file=sys.stderr)

    failures: list = []
    stage2: list = []
    deferred: list = []
    mode = "APPLIED" if args.apply else "WOULD"
    for issue in issues:
        n = int(issue["number"])
        d = decide(issue, issues)
        if already_done(issue, d):
            continue
        # THE CAP BOUNDS THE WORK, NOT THE PRINTOUT. Capping the `STAGE2:` line after the
        # loop had already labelled and commented on every candidate dropped the surplus
        # PERMANENTLY: the label is what `already_done` reads, so the next run skipped the
        # held-back issues before they could be listed, and `STAGE2:` came back empty. An
        # issue deferred here is left untouched -- no label, no comment, and the resolver is
        # not even asked -- which is exactly what makes the next run pick it up.
        if d.label == LABEL_REVIEWED and len(stage2) >= args.cap:
            deferred.append(n)
            continue
        kind, cause = classify_provenance(resolver, n)
        if kind == "trusted":
            continue                                        # silently, by ruling
        if kind == "error":
            failures.append(f"#{n}: provenance not resolved -- {cause}")
            continue
        print(f"{mode:<8} #{n}  {d.label}  ({d.key})  {'no comment' if d.comment is None else 'comment'}")
        if d.label == LABEL_REVIEWED:
            stage2.append(n)
        if args.apply:
            failures.extend(apply_decision(gh, args.repo, issue, d))
    print("STAGE2: " + " ".join(str(n) for n in stage2))
    if deferred:
        print(f"({len(deferred)} candidate(s) held back by --cap {args.cap}, unexamined and "
              f"unlabelled so the next run sees them: {' '.join('#' + str(n) for n in deferred)})")
    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    return EXIT_FAIL if failures else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
