#!/usr/bin/env python3
"""Post a /ask audit issue or comment -- only through the guard (#1167, QA on PR #1169).

The audit agent reads real users' questions and then writes to GitHub, which is
public. Until this script, its tool list allowed `gh issue create` and
`gh issue comment` directly, with `--body-file <any path>`, so the leak guard
ran only if the agent chose to run it: the control was the prompt, which the
decision record had already rejected for text an outsider wrote. This script
is now the agent's ONLY way to post, so every body passes the guard by
construction.

    ask_audit_post.py --body-file /tmp/ask-work/issue-<class>.md \\
        --title "..." --labels astrology-correctness,bug,layer:prompt [--issue N]

Without --issue it opens an issue; with it, it comments on issue N. Either way,
before anything is posted:

  1. the body file must sit under WORK_DIR (/tmp/ask-work). The agent's Bash
     reaches this script, so a free path would make it a way to post any
     readable file -- /proc/<pid>/environ, .git/config -- to a public issue;
  2. neither the body nor the title may quote the sample
     (`ask_audit_guard.quotes`, the same check the file guard runs);
  3. the body's Evidence Block must pass `verify_issue_evidence.check()`, the
     gate `/agent-cycle` step 1 applies to every issue it works -- for a
     comment too, so an update carries this week's count as a checkable repro;
  4. every label must be on ALLOWED_LABELS;
  5. the target is one of the audit's own issues (#1291). The agent reads
     untrusted questions, and a bare `--issue N` would let a prompt injection
     comment on and label `provenance:outsider` ANY issue, the loop's own
     included -- the label alone turns a trusted issue unworkable. So `--issue N`
     is accepted only when `gh issue view` shows ALL of: an author that is this
     repository's own App (`resolve_provenance.is_self_app`, `is_bot` a real
     bool), the `provenance:outsider` label, and the hidden
     `<!-- ask-audit-class: <class> -->` line in the body. The author is the part
     an outsider cannot forge; label and line are defence in depth that exclude
     issues the loop filed for itself. A new issue (no --issue) must carry the
     line, and is capped at ISSUE_CAP per WINDOW, COUNTED FROM `gh` on every call
     (no process memory, no search index: `gh issue list --state all`, which is
     read-your-writes). The cap covers new issues only, never comments.

And it ALWAYS adds `provenance:outsider` (to the new issue, or to issue N when
commenting). The text came from an outsider's question by way of an LLM
answer; the label is what makes `scripts/resolve_provenance.py` answer
OUTSIDER for an issue `claude[bot]` filed, so the loop never builds from it.

It never prints the body, the title or any matched text: its output lands in
the same public log as the guard's.

EXIT CODES: 0 posted   1 refused (a quote, a failing Evidence Block, an --issue
              that is not an audit issue, a new issue without the class line,
              or the cap reached)
            2 could not run (bad arguments, no sample, a path outside WORK_DIR,
              a gh failure, a gh answer that is malformed or cannot be trusted
              -- a truncated cap listing included) -- NOT a pass, and nothing
              was posted unless the message says so. Every gh READ in step 5
              happens before the first write, so a refusal writes nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ask_audit_guard  # noqa: E402
from resolve_provenance import is_self_app, normalise_login  # noqa: E402
from verify_issue_evidence import check  # noqa: E402

WORK_DIR = Path("/tmp/ask-work")
SAMPLE = ask_audit_guard.SAMPLE
LABEL_OUTSIDER = "provenance:outsider"
# Closed on purpose. `provenance:trusted` in particular must never be applied
# from here (the resolver ignores a bot's application of it anyway, but it is
# not this script's to try).
ALLOWED_LABELS = frozenset({"astrology-correctness", "bug", "layer:prompt", LABEL_OUTSIDER})
# #1291: the prompt said "at most five new issues"; a prompt is not a control for an
# agent that reads outsiders' text. 5 per rolling 24h, counted from gh each time.
ISSUE_CAP = 5
WINDOW = timedelta(hours=24)
LIST_LIMIT = 100          # `gh issue list --limit`; a full page cannot prove the count
MARKER_RE = re.compile(r"^<!-- ask-audit-class: [a-z0-9-]+ -->\r?$", re.MULTILINE)


@dataclass
class Result:
    rc: int
    out: str = ""
    err: str = ""


Gh = Callable[[list], Result]


def run_gh(args: list) -> Result:
    """`gh` with an argv list, never a shell: the title is agent-written text."""
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return Result(124, "", "timeout")
    except OSError as e:
        return Result(127, "", f"{type(e).__name__}: {e}")
    return Result(p.returncode, p.stdout, p.stderr)


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _is_audit_issue(view) -> bool | None:
    """Is this `gh issue view|list --json author,labels,body` row an audit issue?

    True/False when the shape is sound; None when it is not, which the caller turns
    into exit 2 -- "could not tell" is never a yes and never a quiet no. All three
    must hold: a self-app author (the unforgeable part: an outsider's issue is filed
    by the outsider), the outsider label, and the class line.
    """
    if not isinstance(view, dict):
        return None
    author, labels, body = view.get("author"), view.get("labels"), view.get("body")
    if not isinstance(author, dict) or not isinstance(labels, list) or not isinstance(body, str):
        return None
    # `is True` below: a string "false" is truthy, and gh's field is a JSON bool.
    if not isinstance(author.get("is_bot"), bool):
        return None
    login = normalise_login(author.get("login"))
    if login is None:
        return None
    names = []
    for lab in labels:
        if not isinstance(lab, dict) or not isinstance(lab.get("name"), str):
            return None
        names.append(lab["name"])
    return (author["is_bot"] is True and is_self_app(login)
            and LABEL_OUTSIDER in names and MARKER_RE.search(body) is not None)


def _gh_json(gh: Gh, args: list, what: str):
    """(value, None) or (None, message). Never raises on a bad gh answer."""
    r = gh(args)
    if r.rc != 0:
        return None, f"{what} failed (gh exit {r.rc})"
    try:
        return json.loads(r.out), None
    except ValueError:
        return None, f"{what} returned invalid JSON"


def _check_target(gh: Gh, issue: int) -> int | None:
    """None to proceed, else the exit code. Reads only."""
    view, err = _gh_json(gh, ["issue", "view", str(issue), "--json", "author,labels,body"],
                         f"reading #{issue}")
    if err:
        print(f"COULD NOT POST (exit 2) -- {err}. Nothing posted.")
        return 2
    ok = _is_audit_issue(view)
    if ok is None:
        print(f"COULD NOT POST (exit 2) -- #{issue} came back in a shape that cannot be trusted. Nothing posted.")
        return 2
    if not ok:
        print(f"REFUSED #{issue} is not an issue this audit filed (needs its own App as author, "
              f"{LABEL_OUTSIDER} and the class line). Nothing posted.")
        return 1
    return None


def _check_cap(gh: Gh, body: str) -> int | None:
    """None to proceed, else the exit code. Reads only; counts from gh, not memory."""
    if not MARKER_RE.search(body):
        print("REFUSED a new issue must carry the `<!-- ask-audit-class: <class> -->` line. Nothing posted.")
        return 1
    # No --search: the search index is eventually consistent, so an issue filed a
    # minute ago can be missing from it and the cap would undercount.
    rows, err = _gh_json(gh, ["issue", "list", "--state", "all", "--label", LABEL_OUTSIDER,
                              "--limit", str(LIST_LIMIT), "--json", "number,author,labels,createdAt,body"],
                         "listing recent audit issues")
    if err:
        print(f"COULD NOT POST (exit 2) -- {err}. Nothing posted.")
        return 2
    if not isinstance(rows, list):
        print("COULD NOT POST (exit 2) -- the issue listing is not a list. Nothing posted.")
        return 2
    cutoff = datetime.now(timezone.utc) - WINDOW
    count, oldest = 0, None
    for row in rows:
        ok = _is_audit_issue(row)
        try:
            made = datetime.fromisoformat(str(row["createdAt"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            made = None
        if ok is None or made is None or made.tzinfo is None:
            print("COULD NOT POST (exit 2) -- a listed issue is malformed; the count cannot be trusted. "
                  "Nothing posted.")
            return 2
        oldest = made if oldest is None else min(oldest, made)
        if ok and made >= cutoff:
            count += 1
    if count >= ISSUE_CAP:
        print(f"REFUSED cap reached: {count} audit issues in the last 24h (cap {ISSUE_CAP}); "
              "comment on one instead. Nothing posted.")
        return 1
    if len(rows) >= LIST_LIMIT and oldest >= cutoff:
        # A full page that never leaves the window: older-than-page rows may be inside it.
        print("COULD NOT POST (exit 2) -- the listing is full and still inside the window; "
              "the count cannot be trusted. Nothing posted.")
        return 2
    return None


def main(argv: list, gh: Gh = run_gh) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--labels", default="")
    ap.add_argument("--issue", type=int, default=None)
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2

    body_path = Path(a.body_file)
    if not _under(body_path, WORK_DIR) or not body_path.is_file():
        print(f"COULD NOT POST (exit 2) -- the body must be a file under {WORK_DIR}. Nothing posted.")
        return 2
    if a.issue is None and not a.title.strip():
        print("COULD NOT POST (exit 2) -- a new issue needs --title. Nothing posted.")
        return 2
    if a.issue is not None and a.issue < 1:
        print("COULD NOT POST (exit 2) -- --issue must be a positive number. Nothing posted.")
        return 2
    labels = [x.strip() for x in a.labels.split(",") if x.strip()]
    stray = sorted(set(labels) - ALLOWED_LABELS)
    if stray:
        print(f"COULD NOT POST (exit 2) -- labels not allowed here: {', '.join(stray)}. Nothing posted.")
        return 2
    if LABEL_OUTSIDER not in labels:
        labels.append(LABEL_OUTSIDER)

    sample = ask_audit_guard._load(SAMPLE)
    if sample is None:
        print(f"COULD NOT VERIFY (exit 2) -- no readable sample at {SAMPLE}. Nothing posted.")
        return 2
    body = body_path.read_text(errors="replace")
    if not body.strip():
        print(f"REFUSED {body_path}: empty. Nothing posted.")
        return 1
    if ask_audit_guard.quotes(body, sample) or ask_audit_guard.quotes(a.title, sample):
        print(f"REFUSED a user quote was found in {body_path} or its title. "
              "Paraphrase; never quote a user. Nothing posted.")
        return 1
    code, lines = check(body, labels, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    if code != 0:
        for line in lines:
            print(f"  {line}")
        print(f"REFUSED {body_path}: Evidence Block. Nothing posted.")
        return 1

    # Every gh READ before the first write (#1291): a refusal leaves nothing behind,
    # not even the label.
    refused = _check_target(gh, a.issue) if a.issue is not None else _check_cap(gh, body)
    if refused is not None:
        return refused

    # Idempotent: create, or refresh the description of the existing label.
    r = gh(["label", "create", LABEL_OUTSIDER, "--force", "--color", "d93f0b",
            "--description", "Issue provenance resolved by scripts/resolve_provenance.py (#361)"])
    if r.rc != 0:
        print(f"COULD NOT POST (exit 2) -- label create failed (gh exit {r.rc}). Nothing posted.")
        return 2
    if a.issue is None:
        args = ["issue", "create", "--title", a.title, "--body-file", str(body_path)]
        for lab in labels:
            args += ["--label", lab]
        r = gh(args)
        if r.rc != 0:
            print(f"COULD NOT POST (exit 2) -- gh issue create failed (gh exit {r.rc}). Nothing posted.")
            return 2
        print(f"posted {r.out.strip()} with {LABEL_OUTSIDER}")
        return 0
    # Label FIRST: a comment that landed on an issue whose label then failed
    # would be outsider-derived text on an issue the loop still trusts.
    r = gh(["issue", "edit", str(a.issue), "--add-label", LABEL_OUTSIDER])
    if r.rc != 0:
        print(f"COULD NOT POST (exit 2) -- labelling #{a.issue} failed (gh exit {r.rc}). Nothing posted.")
        return 2
    r = gh(["issue", "comment", str(a.issue), "--body-file", str(body_path)])
    if r.rc != 0:
        print(f"COULD NOT POST (exit 2) -- gh issue comment failed (gh exit {r.rc}); "
              f"#{a.issue} was labelled {LABEL_OUTSIDER}, no comment posted.")
        return 2
    print(f"commented on #{a.issue}, labelled {LABEL_OUTSIDER}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
