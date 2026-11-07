#!/usr/bin/env python3
"""The test-count floor, DERIVED from the merge base instead of hand-edited.

WHY THIS EXISTS (#446, part 3 of #405)

`EXPECTED_TESTS` was a single integer on one line of `verify_behaviour.py` that
EVERY pull request had to edit, because every PR adds tests. So every pair of
concurrent PRs conflicted there, and on 2026-10-20 three of them did — #425,
#443 and #445 — with #443 resolving the same three files twice. One of those
hand resolutions silently concatenated two `ARCHITECTURE.md` decision rows, and
the script written to prevent exactly that had the same defect and could not run
at all. `ARCHITECTURE.md`'s own row for #405 predicted it: *"Until those land,
`verify_behaviour.py` and `mutate_behaviour_suite.py` still conflict."*

WHAT REPLACES IT, AND WHAT MUST NOT BE LOST

The floor's job was never the number. It was ONE property: coverage may not
vanish silently. It earned that job — a slice-based edit deleted six tests on
`feat/124-hindi-url-prefix`, two of them named guards for registered mutations,
and the floor is what caught it.

So the floor is now computed: count the tests at the MERGE BASE with
`origin/main`, count them at HEAD, and require HEAD not to be lower. Nothing is
stored, so nothing conflicts, and a stale constant drifts below the real count
and stops protecting anything, which is precisely what a hand-edited floor does
between bumps.

WHAT IT COMPARES, STATED PRECISELY (this paragraph used to say "strictly stronger
than a constant", which was false and was FAILED by independent QA on PR #448):
  * test NAMES, so a deleted or renamed-out-of-`test_*` function is named; and
  * the CASE COUNT of a function decorated with `pytest.mark.parametrize`, when
    its argvalues is a literal list/tuple (or a module-level name bound once to
    one). Names alone could not see a deleted case: QA removed one entry from the
    list in tests/test_dispatch_carrier.py and got `+9 added, 0 removed`, PASS.
    Stacked decorators multiply.
It does NOT see: a parametrize whose argvalues is computed (`sorted(X)`,
`range(n)`, a comprehension, a call) -- those are "unknown", and a literal at the
base that became computed at HEAD is reported as unverifiable and fails; it does
NOT see class-level parametrize, `pytest_generate_tests`, or fixture params; and
it is NOT pytest collection. Nor is it a replacement for the `EXPECTED_TESTS`
backstop, whose slack GROWS as PRs add tests (it is one integer, not re-derived),
so the backstop alone would let a few dozen tests vanish unnoticed.
`Test-Count-Drop:` in a commit message is a DECLARATION, not a licence: see
"A DELIBERATE DELETION" below for what must exist before it is honoured.

COUNTED BY PARSING, NOT BY COLLECTING. `ast` over `tests/**/*.py` needs only the
FILES, which `git show` hands over for any commit without a checkout, a venv or
an importable tree. Collection at an old commit would need all three. The two
counts are therefore measured the same way on both sides, which is the only
thing a comparison requires.

It also reports WHICH tests (and how many cases) disappeared. The old gate printed a number, so a
drop meant a manual hunt; both times it happened that hunt is what took the
time, not the discovery.

A DELIBERATE DELETION IS STILL POSSIBLE, but it is a REVIEWED act (#446 AC3).
`Test-Count-Drop: <reason>` in a commit message only DECLARES the deletion. It is
honoured when, and only when, a comment on the pull request by `claude[bot]` or
the repository owner contains the literal

    test-count-drop-ruled at <the full 40-character PR head sha>

Before this, the trailer alone passed the gate, and on the unattended path (the
loop merges on green gates) the author of a PR could lower the floor by typing
it: the declaration and the authorisation were the same person's same line. The
ruling is SHA-bound like `chief-cleared at <sha>`, so a push invalidates it, and
a short sha or a prefix does not count. The author is matched on `user.login`,
never `author_association`, as `chief_clear.py` does.

THE STATED LIMIT: `claude[bot]` is also the identity the loop's own author runs
as. This makes a drop a visible, SHA-bound, separately posted act, which a
reviewer or `chief` can be held to; it is not a cryptographic separation of the
author from the approver. The same limit applies to `chief-cleared`.

The comment is read from the GitHub API, and only when a drop is declared AND
something was actually removed, so the common path stays network-free. Posting a
comment does not trigger `pr-gates`: re-run the `gates` job afterwards. Anything
the gate cannot establish (no repo, no sha, no PR, an API error) is exit 2, never
a pass.

EXIT CODES
  0  the count did not fall (or a drop is declared AND ruled on, or there is no
     base to compare against — reported, never silent)
  1  tests or literal-parametrize cases disappeared and nothing declared it, or
     a drop is declared and no ruling comment names the head sha
  2  could not run: git failed, `tests/` is missing, or a declared drop could not
     be checked against GitHub. NOT a pass.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Mapping

ROOT = Path(__file__).resolve().parent.parent
TESTS = "tests"


def git(*args: str) -> str:
    out = subprocess.run(("git", "-C", str(ROOT), *args),
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> {out.stderr.strip()[:300]}")
    return out.stdout


# name -> literal parametrize case count (1 for an unparametrised test), or
# None when a parametrize argvalues is computed and so cannot be counted.
Counts = dict[str, "int | None"]


def _literal_len(node: ast.expr, bound: dict[str, ast.expr]) -> int | None:
    """Length of a literal list/tuple, following one module-level name."""
    if isinstance(node, ast.Name) and node.id in bound:
        node = bound[node.id]
    if isinstance(node, (ast.List, ast.Tuple)) and not any(
            isinstance(e, ast.Starred) for e in node.elts):
        return len(node.elts)
    return None


def _case_count(fn: ast.FunctionDef | ast.AsyncFunctionDef,
                bound: dict[str, ast.expr]) -> int | None:
    """Product of the literal argvalues lengths of every `parametrize` on `fn`."""
    total: int | None = 1
    for dec in fn.decorator_list:
        if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "parametrize"):
            continue
        vals = dec.args[1] if len(dec.args) > 1 else next(
            (k.value for k in dec.keywords if k.arg == "argvalues"), None)
        n = _literal_len(vals, bound) if vals is not None else None
        total = None if (n is None or total is None) else total * n
    return total


def _names_from_source(src: str, path: str) -> Counts:
    """`def test_*` at module level or inside a Test* class, as `path::name`.

    A SyntaxError is not zero tests — it is a file this cannot read, and
    returning an empty set would read as "every test here vanished". Raised so
    the caller exits 2 rather than 1.
    """
    tree = ast.parse(src, filename=path)
    # A name assigned exactly once at module level to a literal; anything
    # reassigned is ambiguous and is left out (so its parametrize is "unknown").
    seen: dict[str, int] = {}
    bound: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    seen[t.id] = seen.get(t.id, 0) + 1
                    bound[t.id] = node.value
    bound = {k: v for k, v in bound.items() if seen[k] == 1}
    found: Counts = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            found[f"{path}::{node.name}"] = _case_count(node, bound)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test"):
                    found[f"{path}::{node.name}::{sub.name}"] = _case_count(sub, bound)
    return found


def names_at(ref: str | None) -> Counts:
    """Every test name at `ref` (with case count), or the working tree if None."""
    out: Counts = {}
    if ref is None:
        for p in sorted((ROOT / TESTS).rglob("test_*.py")):
            rel = p.relative_to(ROOT).as_posix()
            out.update(_names_from_source(p.read_text(encoding="utf-8"), rel))
        return out
    listing = git("ls-tree", "-r", "--name-only", ref, "--", TESTS)
    for rel in listing.splitlines():
        name = rel.rsplit("/", 1)[-1]
        if not (name.startswith("test_") and rel.endswith(".py")):
            continue
        out.update(_names_from_source(git("show", f"{ref}:{rel}"), rel))
    return out


def case_drops(before: Counts, head: Counts) -> list[str]:
    """Tests present in both whose literal parametrize case count fell."""
    out: list[str] = []
    for name in sorted(set(before) & set(head)):
        if before[name] is not None and head[name] is None:
            out.append(f"{name}: {before[name]} cases at the base, now computed "
                       "-- cannot be counted")
        elif before[name] is not None and head[name] < before[name]:
            out.append(f"{name}: {before[name]} -> {head[name]} cases")
    return out


def base_ref() -> str | None:
    """The merge base with `origin/main`, or None when there is nothing to compare.

    None is a real answer, not an error: on `main` itself the merge base IS
    HEAD, and a shallow clone may not have the history. Both are reported.
    """
    # `origin/main` ONLY, never local `main`. CLAUDE.md records that this
    # repository's local `main` is PRE-REWRITE history (703/751 divergence), and
    # the first version of this function fell back to it: `merge-base HEAD main`
    # answered an ancient commit where `tests/` did not exist, so the base count
    # came back 0 and the floor passed `543 >= 0`. A floor that compares against
    # nothing reports PASS, which is the exact failure mode this file replaces.
    try:
        base = git("merge-base", "HEAD", "origin/main").strip()
    except RuntimeError:
        return None
    if base and base != git("rev-parse", "HEAD").strip():
        return base
    return None


def drop_declared() -> str | None:
    """`Test-Count-Drop: <reason>` in any commit not on the base."""
    base = base_ref()
    rng = f"{base}..HEAD" if base else "HEAD~1..HEAD"
    try:
        log = git("log", "--format=%B", rng)
    except RuntimeError:
        return None
    for line in log.splitlines():
        if line.strip().lower().startswith("test-count-drop:"):
            reason = line.split(":", 1)[1].strip()
            return reason or "(no reason given)"
    return None


# A ruling is `RULING_PHRASE` + the FULL head sha. The sha is captured as a whole
# hex token and compared for EQUALITY, so a short sha, a prefix, or a longer hex
# string that merely begins with the sha never matches.
RULING_PHRASE = "test-count-drop-ruled at"
_RULING = re.compile(re.escape(RULING_PHRASE) + r" ([0-9a-f]+)", re.IGNORECASE)
#: A ruling is the phrase STANDING ALONE ON ITS OWN LINE (2026-11-07). Matching it
#: anywhere read a quotation as a ruling: the author's note on #747 quoted the
#: phrase in backticks to say it was NOT ruling, the note posts as the owner, and
#: the gate went green on the author's own deletion -- the case #753 exists to
#: close (caught by independent QA at 03:05Z). A line inside a sentence, in
#: backticks, or behind a `>` quote is a mention, not an act.
_RULING_LINE = re.compile(re.escape(RULING_PHRASE) + r" ([0-9a-f]+)\.?", re.IGNORECASE)
_SHA = re.compile(r"[0-9a-f]{40}")
_API = "https://api.github.com"

# (repo, head sha, PR number or None) -> every comment on the PR; raises
# RuntimeError on any failure to read. Passed INTO main() rather than read from
# an env var or file: an override the gate reads at run time is a bypass.
Fetch = Callable[[str, str, "int | None"], list]


def _get(url: str) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "verify_test_floor"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RuntimeError(f"GET {url} -> {type(exc).__name__}: {exc}") from exc


def fetch_comments(repo: str, sha: str, pr: int | None) -> list:
    """Every issue comment on the PR holding `sha` (or on PR `pr`)."""
    if pr is not None:
        numbers = [pr]
    else:
        pulls = _get(f"{_API}/repos/{repo}/commits/{sha}/pulls")
        numbers = [p["number"] for p in pulls] if isinstance(pulls, list) else []
    if not numbers:
        raise RuntimeError(f"no pull request found for {sha[:9]}")
    out: list = []
    for n in numbers:
        for page in range(1, 21):
            batch = _get(f"{_API}/repos/{repo}/issues/{n}/comments?per_page=100&page={page}")
            if not isinstance(batch, list):
                raise RuntimeError(f"comments for #{n}: unexpected response")
            out.extend(batch)
            if len(batch) < 100:
                break
    return out


def pr_head(env: Mapping[str, str]) -> tuple[str, int | None]:
    """(sha the ruling must name, PR number if the event says).

    On a `pull_request` run HEAD is the `refs/pull/N/merge` commit, which nobody
    can name in advance, so the PR head comes from the event payload.
    """
    path = env.get("GITHUB_EVENT_PATH")
    if path:
        pr = json.loads(Path(path).read_text(encoding="utf-8")).get("pull_request")
        if isinstance(pr, dict) and isinstance(pr.get("head"), dict) and pr["head"].get("sha"):
            number = pr.get("number")
            return str(pr["head"]["sha"]).lower(), number if isinstance(number, int) else None
    return git("rev-parse", "HEAD").strip().lower(), None


def find_ruling(comments: list, sha: str, owner: str) -> dict | None:
    """The first comment by `claude[bot]` or the owner naming exactly `sha`."""
    allowed = {"claude[bot]", owner.lower()}
    for c in comments:
        user = c.get("user") if isinstance(c, dict) else None
        login = str(user.get("login", "")).lower() if isinstance(user, dict) else ""
        if login not in allowed:
            continue
        for line in str(c.get("body") or "").splitlines():
            m = _RULING_LINE.fullmatch(line.strip())
            if m and m.group(1).lower() == sha:
                return c
    return None


def check_ruling(reason: str, fetch: Fetch, env: Mapping[str, str]) -> int:
    """Exit code for a declared drop: 0 ruled, 1 declared but unruled, 2 unknown."""
    repo = env.get("GITHUB_REPOSITORY", "")
    try:
        sha, pr = pr_head(env)
    except (RuntimeError, OSError, ValueError, AttributeError) as exc:
        print(f"\nCOULD NOT RUN (exit 2) — head sha: {type(exc).__name__}: {exc}")
        print("A drop whose ruling cannot be looked up is NOT a pass.")
        return 2
    if "/" not in repo or not _SHA.fullmatch(sha):
        print("\nCOULD NOT RUN (exit 2) — a drop is declared, but the ruling cannot be looked up")
        print(f"       (repo={repo or 'unset'!r}, head={sha[:9]!r}; needs GITHUB_REPOSITORY and a 40-hex sha).")
        print("       This is NOT a pass. A declared drop needs a ruling comment on the pull request.")
        return 2
    try:
        comments = fetch(repo, sha, pr)
    except RuntimeError as exc:
        print(f"\nCOULD NOT RUN (exit 2) — reading the ruling comments: {exc}")
        print("A drop whose ruling cannot be read is NOT a pass.")
        return 2
    ruling = find_ruling(comments, sha, repo.split("/", 1)[0])
    if ruling:
        who = ruling["user"]["login"]
        print(f"\nPASS — removed tests declared and RULED: Test-Count-Drop: {reason}")
        print(f"       ruling by {who}, comment id {ruling.get('id')}, naming {sha[:9]}.")
        return 0
    print(f"\nFAIL — a drop is declared (Test-Count-Drop: {reason}) but no ruling names this head.")
    print("       Declaring is not authorising: the author's own line cannot lower the floor (#446 AC3).")
    print(f"       Post this on the pull request, as claude[bot] or {repo.split('/', 1)[0]}:")
    print(f"           {RULING_PHRASE} {sha}")
    print("       The FULL sha is required, and a push invalidates it. A comment does not trigger")
    print("       pr-gates, so re-run the `gates` job afterwards.")
    return 1


def main(fetch: Fetch = fetch_comments, env: Mapping[str, str] = os.environ) -> int:
    if not (ROOT / TESTS).is_dir():
        print(f"COULD NOT RUN (exit 2) — no {TESTS}/ directory. This is NOT a pass.")
        return 2
    try:
        head = names_at(None)
        base = base_ref()
    except (RuntimeError, SyntaxError, OSError) as exc:
        print(f"COULD NOT RUN (exit 2) — {type(exc).__name__}: {exc}")
        print("A floor this cannot compute is not a floor that passed.")
        return 2

    print(f"Test-count floor — derived, nothing stored (see #446)")
    # `def test_*`, NOT pytest's collected count: one parametrised function is
    # one name here and N cases there. Both sides are measured the same way, so
    # the comparison holds -- but the numbers differ from `verify_behaviour.py`'s
    # and that must not read as a regression.
    # Literal parametrize cases are compared per function (see `lost`), but this
    # is still not pytest's collected count.
    print(f"  HEAD: {len(head)} test functions (not pytest cases) in {TESTS}/")

    if base is None:
        print("  base: none — HEAD is the merge base (on main), or the history is")
        print("        shallow. Nothing to compare against, so nothing is asserted.")
        print("\nPASS (no base; reported rather than silently skipped)")
        return 0

    try:
        before = names_at(base)
    except (RuntimeError, SyntaxError, OSError) as exc:
        print(f"COULD NOT RUN (exit 2) — reading {base[:9]}: {type(exc).__name__}: {exc}")
        return 2

    print(f"  base: {len(before)} at {base[:9]}")
    # Names first (the original comparison), then per-function case counts.
    head_counts, before_counts = head, before
    head, before = set(head_counts), set(before_counts)
    gone = sorted(before - head) + case_drops(before_counts, head_counts)
    added = len(head - before)

    if not gone:
        print(f"  +{added} added, 0 removed (names, and literal parametrize case counts)")
        print(f"\nPASS ({len(head)} >= {len(before)})")
        return 0

    reason = drop_declared()
    print(f"  +{added} added, {len(gone)} REMOVED (tests or cases):")
    for name in gone[:25]:
        print(f"    - {name}")
    if len(gone) > 25:
        print(f"    ... and {len(gone) - 25} more")

    if reason:
        return check_ruling(reason, fetch, env)

    print(f"\nFAIL — {len(gone)} test(s) or parametrized case(s) at the merge base are gone at HEAD, and")
    print("       nothing declared it. Each test in this repo is a defect that")
    print("       shipped; deleting one removes the proof it cannot come back.")
    print("       If the deletion IS deliberate, say so where it can be reviewed:")
    print("       add `Test-Count-Drop: <reason>` to the commit message AND have")
    print(f"       `{RULING_PHRASE} <full head sha>` posted on the PR (see the docstring).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
