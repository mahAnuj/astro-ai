#!/usr/bin/env python3
"""Probe an issue's `repro:` steps against live production, several times.

WHY THIS EXISTS
---------------
An open issue is not evidence that the problem still exists. `BACKLOG.md` has
recorded 36 open against 50 actual, and `project-manager`'s own definition says
titles lie. Every "verified" in this repo has historically meant verified against
`origin/main`; the last mile was done by hand, or not at all.

#266 is why the sample count is not 1. It was asserted to be a total outage from
its OPEN state alone. One page load looked fine. Two probes with different birth
data returned a 200 and a 503, and a retry of the failing one succeeded 26
seconds later. A single request would have closed it falsely; a single page load
would have left it open and wrongly described. The fault is intermittent, which
is a different bug from a deterministic one, with a different cause and fix.

So: several samples, varied inputs, and INTERMITTENT reported as its own verdict.

WHAT IT DOES NOT DO
-------------------
It does not close, label or comment. It prints a verdict and exits. The caller
decides, and in this repo a human closes.

THE REPRO GRAMMAR
-----------------
One `repro:` line in the issue's Evidence Block. Two shapes:

    repro: GET /kundli -> 200 contains "Lagna"
    repro: POST /reading birth_date=1990-01-15 birth_time=10:30 birth_place=Delhi
           -> follow -> 200 contains "Lagna" absent "high demand"

`-> follow` carries cookies through the 303 to GET /kundli. The chart lives in a
cookie and the LLM runs on the redirect target, so a POST alone proves nothing.
"""

from __future__ import annotations

import argparse
import glob
import http.cookiejar
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://shubhagya.com"
TIMEOUT = 180
# Varied inputs so a probe cannot pass by hitting one lucky code path: #266
# failed on a 1975 Chennai chart and passed on a 1990 Delhi one in the same
# minute. Every sample must be DISTINCT, not a cycle through a fixed list —
# repeating a fixture hits the cache and never reaches the LLM, so samples 4 and
# 5 of a 3-fixture cycle came back byte-identical to 1 and 2 and proved nothing
# about the path that was failing.
_PLACES = ["Delhi", "Chennai", "Mumbai", "Kolkata", "Jaipur", "Pune", "Lucknow", "Kochi"]


def fixture(i: int) -> dict:
    """A distinct birth chart per sample index. Spread across years, times of
    day and longitudes, since the failing request is the large one and size
    varies with dasha depth and place."""
    return {
        "name": f"S{i + 1}",
        "birth_date": f"{1962 + (i * 7) % 48:04d}-{1 + (i * 5) % 12:02d}-{1 + (i * 11) % 28:02d}",
        "birth_time": f"{(i * 9) % 24:02d}:{(i * 17) % 60:02d}",
        "birth_place": _PLACES[i % len(_PLACES)],
    }


def issue_body(n: int) -> str:
    out = subprocess.run(
        ["gh", "issue", "view", str(n), "--json", "body,title,comments"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        sys.exit(f"gh issue view {n} failed: {out.stderr.strip()[:200]}")
    d = json.loads(out.stdout)
    # Comments matter: several in this repo carry corrections that invert the
    # original finding, and a repro added in a comment is the current one.
    parts = [d.get("body") or ""] + [c.get("body") or "" for c in d.get("comments", [])]
    return "\n".join(parts)


def last_repro_line(text: str) -> str | None:
    """The last `repro:` line, whatever dialect it is in.

    Dialect-agnostic on purpose. The previous version skipped any line that was
    not `GET`/`POST`, so an issue whose newest `repro:` was a shell command but
    which also carried an older http one silently probed the STALE line and
    reported a verdict on it (#543).
    """
    found = None
    # A LOOKAHEAD, not a consuming group. Consuming `\n<field>:` ate the next
    # `repro:` line's own prefix, so two adjacent `repro:` lines matched once
    # and "last wins" quietly returned the FIRST — a stale premise reported as
    # a current verdict, which is the whole failure #543 is about.
    for raw in re.findall(r"^\s*repro:\s*(.+?)(?=\n\s*\w+:|\Z)", text, re.M | re.S):
        found = " ".join(raw.split())
    return found


def parse_repro(text: str) -> dict | None:
    """The http dialect only. `None` means "not an http repro", not "no repro"."""
    for line in ([last_repro_line(text)] if last_repro_line(text) else []):
        m = re.match(r"(GET|POST)\s+(\S+)(.*)", line, re.I)
        if not m:
            continue
        method, path, rest = m.group(1).upper(), m.group(2), m.group(3)
        spec: dict = {"method": method, "path": path, "follow": "-> follow" in rest.lower()}
        spec["form"] = dict(
            kv.split("=", 1) for kv in re.findall(r"(\w+=[^\s]+)", rest.split("->")[0])
        )
        st = re.search(r"->\s*(?:follow\s*->\s*)?(\d{3})", rest)
        spec["status"] = int(st.group(1)) if st else 200
        spec["contains"] = re.findall(r'contains\s+"([^"]+)"', rest, re.I)
        spec["absent"] = re.findall(r'absent\s+"([^"]+)"', rest, re.I)
        return spec
    return None


def one_sample(spec: dict, fixture: dict) -> tuple[bool, str]:
    """Run the repro once with its own cookie jar. Returns (passed, detail)."""
    jar = http.cookiejar.CookieJar()
    # 303 -> GET is what urllib does by default, and it keeps the jar.
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    url = SITE + spec["path"] if spec["path"].startswith("/") else spec["path"]
    data = None
    if spec["method"] == "POST":
        form = {k: (fixture.get(k) or v) for k, v in (spec["form"] or {}).items()}
        for k, v in fixture.items():
            form.setdefault(k, v)
        data = urllib.parse.urlencode(form).encode()

    try:
        req = urllib.request.Request(url, data=data, method=spec["method"],
                                     headers={"User-Agent": "astro-ai-validate/1"})
        with opener.open(req, timeout=TIMEOUT) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", "replace") if e.fp else ""
    except Exception as e:  # noqa: BLE001 — a probe must never raise
        # ERRORED, not FAILED. A prober that cannot run is inconclusive; counting
        # it as a reproduction would send an engineer after a bug that does not
        # exist, which is strictly worse than reporting nothing. An earlier
        # revision of this file passed `context=` to opener.open(), crashed on
        # every sample, and confidently reported REPRODUCES — deterministic.
        return None, f"{type(e).__name__}: {e}"

    if status != spec["status"]:
        return False, f"HTTP {status} (wanted {spec['status']})"
    missing = [s for s in spec["contains"] if s.lower() not in body.lower()]
    present = [s for s in spec["absent"] if s.lower() in body.lower()]
    if missing:
        return False, f"HTTP {status}, missing {missing!r}"
    if present:
        return False, f"HTTP {status}, found forbidden {present!r}"
    return True, f"HTTP {status}, {len(body)}b"


# ---------------------------------------------------------------------------
# THE SHELL DIALECT (#543)
# ---------------------------------------------------------------------------
# `verify_issue_evidence.py` has classified `repro:` lines into two dialects
# since 2026-10-13 and deliberately refused to pick a winner:
#
#     "BOTH DIALECTS ARE CORRECT, AND THAT IS THE POINT ... `http` repros are
#      reported as executable by validate_issue.py, `shell` repros as
#      executable by the caller"
#
# That is right, and the gap it left is that "executable by the caller" had no
# caller. Measured 2026-10-26: 26 of 123 open issues carry a `repro:`, and
# 0 were executable here, so this probe had never had a single input.
#
# It lives in THIS file rather than a sibling script on purpose. The repo has
# recorded what copied logic does ("copied files diverge", five times in two
# days) and `close-on-evidence.yml` cites that as the reason it does not let
# `agent-merge` close issues itself. One implementation, two dialects, one
# verdict vocabulary -- so step 0 reads the same whichever dialect an issue
# happens to use.
#
# WHY THE POLARITY IS NOT INVERTED HERE, AND WHY THERE IS NO PASS/FAIL
# --------------------------------------------------------------------
# The two dialects state OPPOSITE things, and conflating them would invert
# every verdict:
#
#   http   `GET /kundli -> 200 contains "Lagna"`   states the HEALTHY state.
#          It passing means the bug is GONE -> CANNOT-REPRODUCE.
#   shell  `grep -c 'Requested' providers.py -> 16` states the state AS FOUND,
#          i.e. the defect. It matching means the premise STILL HOLDS.
#
# And the polarity is per-issue, not per-dialect: some shell repros record the
# broken count, others record what a fixed file should contain. Nothing in the
# grammar distinguishes them, so this does NOT guess. It reports whether the
# command still produces what the issue recorded, and leaves the reading to the
# caller:
#
#   MATCHES-STATED  the numbers/strings the issue recorded are still produced
#   DIFFERS         the command now produces something else -- look at it
#
# Inventing a polarity would have been the easy thing and would have made every
# verdict on a drifted premise exactly backwards.
_SHELL_TIMEOUT = 60

# An ALLOW-LIST, not a deny-list. A deny-list on a public repo is a promise to
# have thought of everything; #358 is the standing proof that nobody does.
_SHELL_ALLOW = {
    "grep": None,
    "rg": None,
    "sed": None,
    "wc": None,
    "cat": None,
    "head": None,
    "tail": None,
    "sort": None,
    "uniq": None,
    "ls": None,
    "diff": None,
    "jq": None,
    # Read-only subcommands only. `gh` reaches the network with the caller's
    # token, so a write verb here would let an issue body act as that user.
    "gh": {("issue", "view"), ("issue", "list"), ("pr", "view"), ("pr", "list"),
           ("pr", "diff"), ("pr", "checks"), ("run", "list"), ("run", "view"),
           ("label", "list"), ("search", "issues"), ("search", "prs"),
           ("api",)},
    # Read-only subcommands only, for the same reason.
    "git": {("log",), ("diff",), ("show",), ("status",), ("ls-files",),
            ("grep",), ("rev-parse",), ("cat-file",), ("describe",),
            ("ls-remote",), ("shortlog",)},
}

# Refused by name, with the reason stated, because they are arbitrary code by
# construction and no flag audit makes them safe:
#   python/python3/uv  -- `-c` is a program
#   bash/sh/zsh        -- same
#   gsutil/gcloud/aws  -- hold cloud credentials; `cp`/`rm` reach real buckets
#   curl/wget          -- egress, and `-o` writes files
_SHELL_ARBITRARY = {
    "python": "`-c` takes a program; no flag audit makes an interpreter safe",
    "python3": "`-c` takes a program; no flag audit makes an interpreter safe",
    "uv": "`uv run` executes arbitrary code",
    "uvx": "`uvx` executes arbitrary code",
    "bash": "a shell executes arbitrary code",
    "sh": "a shell executes arbitrary code",
    "zsh": "a shell executes arbitrary code",
    "node": "executes arbitrary code",
    "make": "runs whatever the Makefile says",
    "gsutil": "holds cloud credentials and reaches real buckets",
    "gcloud": "holds cloud credentials",
    "aws": "holds cloud credentials",
    "curl": "egress, and `-o` writes files",
    "wget": "egress, and `-O` writes files",
    "docker": "executes arbitrary code",
    "ssh": "egress with the caller's keys",
}

# Tokens that only exist to chain, redirect or substitute. After shlex.split a
# QUOTED pipe is one character inside one argument -- `grep -n 'a\|b' f` is a
# regex alternation and is fine. A BARE `|` is a real pipe, and since this runs
# with shell=False it would be passed to grep as a filename anyway; refusing it
# is how the caller learns why instead of reading a confusing grep error.
_SHELL_OPERATORS = {"|", "||", "&&", ";", "&", ">", ">>", "<", "<<", "2>",
                    "$(", "`", "|&"}

# `sed -i` edits the file. `find -exec`/`-delete` run and remove. A read-only
# allow-list that permits these is not read-only.
_SHELL_BANNED_FLAGS = {
    "sed": {"-i", "--in-place"},
    "jq": {"-f", "--from-file"},
    "gh": {"-X", "--method", "--input", "-F", "-f", "--field", "--raw-field"},
}

_ARROW = re.compile(r"->|=>|→|\bexpect(?:ed)?\b|\breturns?\b|\byields?\b",
                    re.I)


def split_shell_repro(line: str) -> tuple[str, str, int]:
    """('command', 'stated expectation', probes_on_this_line).

    The arrow separates command from expectation. The THIRD value exists
    because several `repro:` lines in this backlog paste two or three probes
    onto one line, and splitting on the first arrow alone pulls the NEXT
    command's numbers into the FIRST command's expectation.

    Measured on #423: `grep -c "verify_hindi_surface" ...verify-production.yml
    -> 0 grep -n "verify_hindi_surface" ...pr-gates.yml -> 234`. Taking
    everything after the first arrow gave the expectation `[0, 234]`, the
    command correctly reported 0, and the probe announced DIFFERS with
    "missing [234]" -- a false drift report on an issue whose premise was
    intact. So the expectation is truncated at the next command name, and the
    count is surfaced rather than hidden.
    """
    m = _ARROW.search(line)
    if not m:
        return line.strip(), "", 1
    cmd, rest = line[: m.start()].strip(), line[m.end():].strip()
    # Truncate the expectation where the next command starts.
    try:
        toks = shlex.split(rest)
    except ValueError:
        toks = rest.split()
    cut = None
    for i, t in enumerate(toks):
        bare = t.strip("`")
        if bare in _SHELL_ALLOW or bare in _SHELL_ARBITRARY:
            cut = i
            break
    probes = 1
    if cut is not None:
        probes = 1 + sum(1 for t in toks[cut:]
                         if t.strip("`") in _SHELL_ALLOW or t.strip("`") in _SHELL_ARBITRARY)
        rest = " ".join(toks[:cut])
    return cmd, rest.strip(), probes


def vet_shell(cmd_text: str) -> tuple[list[str] | None, str]:
    """(argv, reason). argv is None when the command must not be executed.

    Every refusal names what it refused and why, because #543's acceptance is
    "0 silently skipped" -- an unexplained skip is how the http dialect sat at
    0 of 123 for three weeks without anyone noticing.
    """
    text = cmd_text.strip().strip("`").strip()
    if not text:
        return None, "the `repro:` line states no command"
    try:
        argv = shlex.split(text)
    except ValueError as e:
        return None, f"cannot be tokenised ({e}) -- probably a heredoc or an unbalanced quote"
    if not argv:
        return None, "the `repro:` line states no command"

    ops = sorted({t for t in argv if t in _SHELL_OPERATORS})
    if ops:
        return None, ("contains the shell operator(s) " + ", ".join(f"`{o}`" for o in ops)
                      + " -- this runs with shell=False, so nothing interprets them. "
                        "Rewrite as a single command, or as an `http` repro.")

    exe = argv[0]
    if exe in _SHELL_ARBITRARY:
        return None, f"`{exe}` is refused: {_SHELL_ARBITRARY[exe]}"
    if exe not in _SHELL_ALLOW:
        return None, (f"`{exe}` is not on the allow-list. This is an allow-list, not a "
                      "deny-list: add it deliberately, with a read-only argument audit.")

    banned = _SHELL_BANNED_FLAGS.get(exe, set())
    hit = sorted(set(argv[1:]) & banned)
    if hit:
        return None, (f"`{exe}` with " + ", ".join(f"`{f}`" for f in hit)
                      + " is not read-only")
    if exe == "find" or "-exec" in argv or "-delete" in argv:
        return None, "`-exec`/`-delete` run or remove files"

    sub = _SHELL_ALLOW[exe]
    consumed: set[str] = set()
    if sub is not None:
        words = tuple(a for a in argv[1:] if not a.startswith("-"))
        matched = next((ok for ok in sub if words[: len(ok)] == ok), None)
        if matched is None:
            return None, (f"`{exe} {' '.join(words[:2])}` is not a read-only subcommand. "
                          f"Allowed: " + ", ".join(sorted(" ".join(s) for s in sub)))
        # The subcommand itself may BE an allow-listed executable name --
        # `git diff`, `git grep`, `git show`, `gh api`. Without this the
        # two-commands check below reads its own subcommand as a second
        # command and refuses every `git diff` in the backlog.
        consumed = set(matched)

    # A second allow-listed executable means two commands were pasted onto one
    # line (#468 is `sed -n ... file sed -n ... file`). Running that feeds the
    # second command's name to the first as a filename and reports a confusing
    # failure, so refuse and say which.
    extra = [a for a in argv[1:]
             if a not in consumed and (a in _SHELL_ALLOW or a in _SHELL_ARBITRARY)]
    if extra:
        return None, (f"two commands on one `repro:` line (found `{extra[0]}` after `{exe}`) "
                      "-- a probe must have one command with one expectation")
    return argv, f"`{exe}`, read-only"


def expand_globs(argv: list[str]) -> list[str]:
    """Expand `*`/`?` with glob, never with a shell.

    `grep -c x src/.../*.html` is 10 of the backlog's shape and is useless
    unexpanded. glob does it without giving the issue body a shell; an argument
    that matches nothing is left verbatim so the command reports its own
    not-found error rather than silently probing fewer files.
    """
    out: list[str] = []
    for a in argv:
        if a.startswith("-") or not any(c in a for c in "*?["):
            out.append(a)
            continue
        hits = sorted(glob.glob(a, root_dir=str(ROOT)))
        out.extend(hits or [a])
    return out


def one_shell_sample(argv: list[str]) -> tuple[int | None, str, str]:
    """(returncode, stdout, note). returncode None means it could not run."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, cwd=str(ROOT),
                           timeout=_SHELL_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return None, "", f"timed out after {_SHELL_TIMEOUT}s"
    except (OSError, ValueError) as e:
        return None, "", f"{type(e).__name__}: {e}"
    note = f"exit {p.returncode}, {len(p.stdout)}b"
    if p.returncode != 0 and p.stderr.strip():
        note += f", stderr: {p.stderr.strip()[:120]}"
    return p.returncode, p.stdout, note


# NO sign. An earlier version used `-?\d[\d,]*` and read the hyphens in
# `2026-10-08T06:57:17` as minus signs, so #461's stated expectation came out
# as [2026, -10, -8, 6, 57, 17] and #518's output as [10, -6, 4, ...]. Counts
# and positions in a `repro:` are never negative, and a date must tokenise the
# same way on both sides of the comparison or the comparison is noise.
_INT = re.compile(r"(?<![\w.])\d[\d,]*")


def _ints(text: str) -> list[int]:
    out = []
    for m in _INT.finditer(text):
        try:
            out.append(int(m.group().replace(",", "")))
        except ValueError:
            pass
    return out


def score_shell(stated: str, stdout: str) -> tuple[bool | None, str]:
    """(matches, detail). None when the expectation is not machine-comparable.

    Deliberately narrow. It compares the integers and the quoted strings the
    issue recorded, and when the expectation carries neither it says so instead
    of inventing a verdict -- `grep -c 'Requested' providers.py -> the string
    appears in a docstring` has nothing a script can check, and reporting that
    honestly is worth more than a confident coin flip.
    """
    want_contains = re.findall(r'contains\s+"([^"]+)"', stated, re.I)
    want_absent = re.findall(r'absent\s+"([^"]+)"', stated, re.I)
    if want_contains or want_absent:
        missing = [s for s in want_contains if s.lower() not in stdout.lower()]
        present = [s for s in want_absent if s.lower() in stdout.lower()]
        if missing or present:
            bits = []
            if missing:
                bits.append(f"missing {missing!r}")
            if present:
                bits.append(f"found forbidden {present!r}")
            return False, "; ".join(bits)
        return True, "every stated string still matches"

    want = _ints(stated)
    got = _ints(stdout)
    if not want:
        return None, ("the expectation states no number and no `contains \"...\"`, "
                      "so nothing can be compared mechanically")
    absent = [n for n in want if n not in got]
    if absent:
        return False, (f"stated {want} -- the command now reports {got[:12]}"
                       f"{' ...' if len(got) > 12 else ''}; missing {absent}")
    return True, f"stated {want}, all still present in the output"


def provenance_is_trusted(issue: int, repo: str) -> tuple[bool, str]:
    """Gate execution on WHO WROTE THE ISSUE (#361's resolver, #543 option C).

    A shell `repro:` is code supplied in an issue body, and this repo is public.
    Running it on a host that holds a `gh` token is letting an issue form act as
    that user, which is #358's shape with a different entry point. So: resolve
    the author, and execute only for admin/write.
    """
    if not repo:
        return False, "no --repo and no GH_REPO, so the author cannot be resolved"
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "resolve_provenance.py"),
         str(issue), "--repo", repo],
        capture_output=True, text=True, check=False,
    )
    first = (p.stdout.strip().splitlines() or [""])[0]
    if p.returncode == 0:
        return True, first or "trusted"
    # 1 outsider, 2 unresolved -- and UNRESOLVED must not execute either. A
    # resolver that cannot answer is not a yes; that is how a revoked token
    # turns every issue trusted.
    return False, first or f"resolve_provenance exited {p.returncode}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("issue", type=int)
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--repo", default=os.environ.get("GH_REPO", ""),
                    help="OWNER/NAME — required for a shell repro, which is gated "
                         "on the issue author's permission (#543)")
    ap.add_argument("--allow-untrusted-shell", action="store_true",
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    text = issue_body(args.issue)
    line = last_repro_line(text)
    if not line:
        print(f"#{args.issue}  NO-REPRO — no `repro:` line at all")
        print("  -> label needs-evidence; route back to discovery")
        return 3

    spec = parse_repro(text)
    if spec:
        return _run_http(args, spec)
    return _run_shell(args, line)


def _run_http(args, spec: dict) -> int:
    print(f"#{args.issue}  {spec['method']} {spec['path']}"
          f"{' -> follow' if spec['follow'] else ''}  x{args.samples}")
    results = []
    for i in range(args.samples):
        fx = fixture(i)
        ok, detail = one_sample(spec, fx)
        results.append(ok)
        mark = "pass" if ok else ("ERR " if ok is None else "FAIL")
        print(f"  {i + 1}/{args.samples}  {mark}  "
              f"[{fx['name']} {fx['birth_date']} {fx['birth_place']}]  {detail}")

    errored = sum(1 for r in results if r is None)
    ran = [r for r in results if r is not None]
    passed = sum(1 for r in ran if r)
    print()
    if errored:
        print(f"  {errored}/{args.samples} samples could not run — the probe is broken, "
              f"not necessarily the feature")
        if not ran:
            print("  INCONCLUSIVE — fix the probe before drawing any verdict")
            print("  -> do NOT label, do NOT close, do NOT queue work from this")
            return 4
        print(f"  verdict below rests on the {len(ran)} sample(s) that ran")
    if ran and passed == len(ran):
        print(f"  CANNOT-REPRODUCE — {passed}/{len(ran)} passed")
        print("  -> comment with these samples, label cannot-reproduce, DO NOT close")
        return 1
    if passed == 0:
        print(f"  REPRODUCES — 0/{len(ran)} passed, deterministic")
        return 0
    print(f"  INTERMITTENT — {passed}/{len(ran)} passed "
          f"({100 * passed // len(ran)}% hit rate)")
    print("  -> a different bug from a deterministic one; say so on the issue")
    return 0


def _run_shell(args, line: str) -> int:
    """The shell dialect. Verdicts are MATCHES-STATED / DIFFERS, never PASS."""
    cmd_text, stated, probes = split_shell_repro(line)
    print(f"#{args.issue}  shell repro")
    print(f"  command:  {cmd_text[:160]}")
    print(f"  stated:   {stated[:160] or '(nothing stated)'}")
    if probes > 1:
        print(f"  NOTE:     this `repro:` line states {probes} probes; only the first is")
        print(f"            scored. The rest are not checked by anything — split them")
        print(f"            onto their own issues or their own `repro:` lines (#543).")

    argv, why = vet_shell(cmd_text)
    if argv is None:
        print(f"\n  REFUSED — {why}")
        print("  -> not executed, and that is a verdict: record it on the issue so the")
        print("     `repro:` gets rewritten rather than skipped again (#543)")
        return 6

    # Provenance BEFORE execution. An unresolved author is not a yes.
    if args.allow_untrusted_shell:
        print("  provenance: SKIPPED by --allow-untrusted-shell (local use only)")
    else:
        trusted, detail = provenance_is_trusted(args.issue, args.repo)
        print(f"  provenance: {detail}")
        if not trusted:
            print("\n  REFUSED — the issue author is not admin/write on this repo, or "
                  "could not be resolved")
            print("  -> a shell `repro:` is code in an issue body; it is classified, "
                  "never executed, for an untrusted author (#543 option C)")
            return 6

    print(f"  vetted:   {why}")
    expanded = expand_globs(argv)
    if expanded != argv:
        print(f"  globbed:  {len(expanded)} args after expansion (no shell used)")

    # A shell repro reads the tree, so it is deterministic and five samples
    # would print the same thing five times. Two proves determinism and catches
    # a `gh`/network repro that is not.
    n = max(1, min(args.samples, 2))
    outs = []
    for i in range(n):
        rc, out, note = one_shell_sample(expanded)
        outs.append((rc, out))
        print(f"  {i + 1}/{n}  {'ERR ' if rc is None else 'ran '}  {note}")
    if any(rc is None for rc, _ in outs):
        print("\n  INCONCLUSIVE — the command could not run")
        print("  -> do NOT label, do NOT close, do NOT queue work from this")
        return 4
    if len({o for _, o in outs}) > 1:
        print("\n  NON-DETERMINISTIC — the same command gave different output")
        print("  -> treat like INTERMITTENT: say so on the issue, do not rank from it")
        return 5

    stdout = outs[0][1]
    head = [ln for ln in stdout.splitlines() if ln.strip()][:6]
    for ln in head:
        print(f"    | {ln[:150]}")
    if len(stdout.splitlines()) > 6:
        print(f"    | ... {len(stdout.splitlines()) - 6} more line(s)")

    matches, detail = score_shell(stated, stdout)
    print()
    if matches is None:
        print(f"  UNSCORED — {detail}")
        print("  -> the output above is the evidence; a human reads it. Rewrite the")
        print("     `repro:` with a number or a `contains \"...\"` to make it scorable")
        return 5
    if matches:
        print(f"  MATCHES-STATED — {detail}")
        print("  -> the premise still holds as the issue recorded it")
        return 0
    print(f"  DIFFERS — {detail}")
    print("  -> the premise has drifted. Read the output before ranking this issue;")
    print("     it may be fixed, or the finding may have moved (#543)")
    return 5


if __name__ == "__main__":
    sys.exit(main())
