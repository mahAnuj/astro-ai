#!/usr/bin/env python3
"""Resolve WHO an issue came from, before the loop acts on it. `/agent-cycle` step 0a
and `project-manager` call this. (#361)

WHY THIS EXISTS
---------------
The repo is public with issues enabled, and nothing in the loop checked who filed one.
The path was: anyone files an issue -> `project-manager` ranks it -> an agent works it ->
the loop's own `qa` reviews the result -> `agent-merge` merges it unattended. An outsider's
PULL REQUEST cannot reach that (#358's same-repository guard); an outsider's ISSUE reaches
an engineer. Measured 2026-10-15: `grep -rniE 'author_association|collaborator|permission'`
over agent-cycle.md and project-manager.md returned 0 and 0.

THE RULING THIS IMPLEMENTS (chief, #361, Standing ruling 4 clause 3 -- "an option that cannot
announce its own failure is not robust")
-------------------------------------------------------------------------------------------
Fail closed. There are three verdicts and the middle of the road is not one of them:

    TRUSTED     exit 0   the author is a human with admin/write on this repo, or a human
                         with admin/write applied `provenance:trusted` (see below)
    OUTSIDER    exit 1   anything else we could positively classify
    UNRESOLVED  exit 2   we could not tell. STOP. Never a default in either direction.

* Any author with `is_bot=true` is OUTSIDER, with ONE named exception: this repository's own
  delivery App (`SELF_APP`). Permission is still not consulted for a bot -- `claude[bot]`
  resolves to `none` and `app/github-actions` is a 404 -- so the exception is a login check
  and nothing more. Every other bot, present or installed later, stays OUTSIDER.

  WHY THE EXCEPTION EXISTS, measured 2026-11-01. 40 of the 130 open issues were filed by this
  App, and a cycle aimed at any of them stopped at `/agent-cycle` Step 0a without building
  anything. PR #642 was dispatched twice and died both times on #616, an issue the loop had
  filed itself. The loop could not work ~31% of its own backlog.

  WHAT THIS GIVES UP, stated because it is real and not small. The override rules below say a
  bot labelling its own issue is "the `USER AUTHORISED PUSH` failure in another costume", and
  this exception grants structurally the same thing: the loop trusting its own output. The
  laundering path is concrete -- a cycle reads an outsider's issue or a web page, files a NEW
  issue restating that content, and the next cycle reads it as trusted. Step 0a exists because
  an outsider's issue reaches an engineer, and that is not fixed by this, only narrowed to
  one hop.

  SO THE REMAINING PROTECTION IS NOT THIS GATE. It is that an issue BODY is data, never
  instructions, wherever it came from. `provenance:outsider` still marks what this App filed
  for a human to read; `qa` and `agent-merge` still gate the output. A trusted provenance says
  "this issue may be worked", never "do what it says".
* Permission comes from `collaborators/<login>/permission`, never from `author_association`
  (`CONTRIBUTOR` means "has had a PR merged", not "has write access").
    admin / write        -> trusted
    read / none / 404    -> outsider (a 404 is "not a user / not a collaborator")
    403, 5xx, timeout, empty output, any other value -> UNRESOLVED
  Separating those two is the point: collapsing "not a collaborator" and "could not ask" into
  one verdict is how a revoked token silently turns every issue into trusted or untrusted.
* `provenance:trusted` is an OVERRIDE honoured by WHO APPLIED IT, not by presence. The loop's
  own App and GITHUB_TOKEN can label issues, and a bot applying it to its own issue is the
  `USER AUTHORISED PUSH` failure in another costume. So: read the issue's event stream, take
  the LATEST `labeled` event for that label with no later `unlabeled`, and require the actor
  to be `type == "User"` (not Bot) AND admin/write by the same permission API. A label whose
  actor cannot be established is ignored, never trusted.

THE LOGIN IS ATTACKER-CONTROLLED TEXT
-------------------------------------
Everything here reaches `gh` as an argv LIST (never a shell), the login is validated against a
strict regex first, and a non-matching login is UNRESOLVED rather than sanitised and used.
It must also never appear in a `run:` block (#358); workflows pass it through `env:` or,
better, call this script with only the issue number.

READ-ONLY UNLESS --apply
------------------------
`--apply` records the verdict as a label (`provenance:outsider` / `provenance:trusted`) so every
later step reads one fact, and on UNRESOLVED posts one idempotent comment. Without it nothing
is written. The labels are a RECORD for humans and for a future `agent-merge` predicate; the
exit code of this script is what `/agent-cycle` obeys.

EXIT CODES
----------
0 trusted   1 outsider   2 unresolved (or could not apply the record -- NOT a pass)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable

TRUSTED, OUTSIDER, UNRESOLVED = "TRUSTED", "OUTSIDER", "UNRESOLVED"
EXIT = {TRUSTED: 0, OUTSIDER: 1, UNRESOLVED: 2}

# This repository's own delivery App, and the ONLY bot login that is not an
# outsider. A bare string, never a list: a collection here would invite a
# second entry, and the whole value of this exception is that it is one login
# wide. tests/test_resolve_provenance.py pins the type.
SELF_APP = "claude"


def is_self_app(login: str) -> bool:
    """Is `login` this repository's own delivery App?

    TWO RENDERINGS, and both are real. `gh issue view --json author` returns
    `app/claude`, which `normalise_login` reduces to `claude`; the REST API and
    AGENT_AUTHORS say `claude[bot]`, which it leaves intact because `[bot]` is
    a valid login character sequence. `qa-on-green.yml` carries the same note
    for the same reason. Only the first reaches this script today -- the second
    is handled because "today" is not a guarantee, and the failure would be a
    silent return to OUTSIDER for every issue the loop filed.

    CASE-INSENSITIVE because GitHub logins are. `Claude` and `claude` are the
    SAME ACCOUNT, so folding case is not a widening; comparing exactly would
    make the gate depend on how an API chose to capitalise today.
    """
    if not isinstance(login, str):
        return False
    # Fold case FIRST, then strip. The other order misses `CLAUDE[BOT]`, and a
    # case variant resolving to OUTSIDER would silently restore the stall this
    # exception exists to remove.
    folded = login.casefold()
    suffix = "[bot]"
    if folded.endswith(suffix):
        folded = folded[:-len(suffix)]
    return folded == SELF_APP.casefold()

LABEL_TRUSTED = "provenance:trusted"
LABEL_OUTSIDER = "provenance:outsider"
# Hidden marker so the UNRESOLVED comment is posted once, however often the loop retries.
UNRESOLVED_MARKER = "<!-- provenance-unresolved -->"

# GitHub logins: alphanumerics and single hyphens, 39 chars at most, plus the `[bot]` suffix
# an App account carries. A leading `app/` is gh's display form for an App and is stripped
# first. Anything else -- `x;id`, `$(...)`, a newline -- is not a login we will pass anywhere.
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

PERM_TRUSTED = {"admin", "write"}
PERM_OUTSIDER = {"read", "none"}


@dataclass
class Result:
    rc: int
    out: str = ""
    err: str = ""


# The seam. A runner takes the argv AFTER `gh` and returns a Result. Tests inject a fake, so
# nothing below needs a network; the real one is `run_gh`.
Gh = Callable[[list], Result]


def run_gh(args: list) -> Result:
    """Run `gh` with an argv list. Never a shell, so no login can be interpreted as syntax."""
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return Result(124, "", "timeout")
    except OSError as e:  # gh not installed / not executable
        return Result(127, "", f"{type(e).__name__}: {e}")
    return Result(p.returncode, p.stdout, p.stderr)


@dataclass
class Verdict:
    verdict: str
    evidence: list = field(default_factory=list)
    reason: str = ""            # one machine-ish phrase; safe to put in a comment
    override_valid: bool = False


def normalise_login(raw) -> str | None:
    """Strip gh's `app/` display prefix and validate. None means 'do not use this'."""
    if not isinstance(raw, str):
        return None
    login = raw[len("app/"):] if raw.startswith("app/") else raw
    # fullmatch, not match: `$` also matches just before a trailing newline, so `x\n` passed.
    return login if _LOGIN.fullmatch(login) else None


def _safe(raw) -> str:
    """A form of attacker-controlled text that is safe to print: escaped and truncated."""
    return ascii(raw)[:60]


@dataclass
class Perm:
    kind: str                   # "value" | "absent" | "unresolved"
    value: str = ""
    detail: str = ""


def lookup_permission(gh: Gh, repo: str, login: str) -> Perm:
    """One `gh api` call; the login is URL-encoded into ONE argv element."""
    path = f"repos/{repo}/collaborators/{urllib.parse.quote(login, safe='')}/permission"
    r = gh(["api", path, "--jq", ".permission"])
    if r.rc != 0:
        if "HTTP 404" in r.err:
            return Perm("absent", detail="HTTP 404 (not a user / not a collaborator)")
        return Perm("unresolved", detail=f"gh exit {r.rc}: {r.err.strip()[:120]}")
    value = r.out.strip()
    if not value:
        return Perm("unresolved", detail="empty output")
    return Perm("value", value=value)


def classify_permission(p: Perm) -> str:
    if p.kind == "absent":
        return OUTSIDER
    if p.kind == "value" and p.value in PERM_TRUSTED:
        return TRUSTED
    if p.kind == "value" and p.value in PERM_OUTSIDER:
        return OUTSIDER
    return UNRESOLVED           # includes an unrecognised value: never guess


def _json_documents(text: str) -> list:
    """`gh api --paginate` without --jq prints one JSON array per page, back to back."""
    dec, i, docs = json.JSONDecoder(), 0, []
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        doc, i = dec.raw_decode(text, i)
        docs.append(doc)
    return docs


def latest_label_event(events: list, label: str) -> dict | None:
    """The newest `labeled` event for `label` with no `unlabeled` after it, else None."""
    relevant = [e for e in events
                if isinstance(e, dict) and e.get("event") in ("labeled", "unlabeled")
                and isinstance(e.get("label"), dict) and e["label"].get("name") == label]
    relevant.sort(key=lambda e: (str(e.get("created_at", "")), e.get("id") or 0))
    if relevant and relevant[-1]["event"] == "labeled":
        return relevant[-1]
    return None


@dataclass
class Override:
    valid: bool = False
    unresolved: bool = False
    note: str = ""


def check_override(gh: Gh, repo: str, number: int) -> Override:
    r = gh(["api", f"repos/{repo}/issues/{number}/events", "--paginate"])
    if r.rc != 0:
        return Override(unresolved=True, note=f"events unreadable (gh exit {r.rc})")
    try:
        events = [e for page in _json_documents(r.out) for e in (page if isinstance(page, list) else [])]
    except ValueError:
        return Override(unresolved=True, note="events output is not JSON")
    ev = latest_label_event(events, LABEL_TRUSTED)
    if ev is None:
        return Override(note=f"{LABEL_TRUSTED} is present but no live `labeled` event found; ignored")
    actor = ev.get("actor")
    if not isinstance(actor, dict):
        return Override(note="labeled by an unidentifiable actor; ignored")
    if actor.get("type") != "User":
        return Override(note=f"labeled by a {_safe(actor.get('type'))} account; a bot's label is not evidence; ignored")
    login = normalise_login(actor.get("login"))
    if login is None:
        return Override(unresolved=True, note=f"labeler login {_safe(actor.get('login'))} is not a valid login")
    p = lookup_permission(gh, repo, login)
    verdict = classify_permission(p)
    shown = p.value or p.detail
    if verdict == TRUSTED:
        return Override(valid=True, note=f"labeled by human {login} ({shown})")
    if verdict == OUTSIDER:
        return Override(note=f"labeled by {login}, who has no write access ({shown}); ignored")
    return Override(unresolved=True, note=f"could not resolve labeler {login}'s permission ({shown})")


def classify(gh: Gh, repo: str, number: int) -> Verdict:
    ev: list = []
    r = gh(["issue", "view", str(number), "--repo", repo, "--json", "author,labels"])
    if r.rc != 0:
        return Verdict(UNRESOLVED, [f"issue unreadable (gh exit {r.rc}): {r.err.strip()[:120]}"],
                       "the issue could not be read")
    try:
        view = json.loads(r.out)
        author = view["author"]
        is_bot = author["is_bot"]
        raw_login = author["login"]
        labels = {lab["name"] for lab in view.get("labels", [])}
    except (ValueError, KeyError, TypeError):
        return Verdict(UNRESOLVED, ["issue JSON lacks author.login / author.is_bot"],
                       "the issue author could not be read")
    if not isinstance(is_bot, bool):
        return Verdict(UNRESOLVED, [f"author.is_bot is {_safe(is_bot)}, not a boolean"],
                       "the issue author could not be read")
    login = normalise_login(raw_login)
    if login is None:
        return Verdict(UNRESOLVED, [f"author login {_safe(raw_login)} is not a valid GitHub login"],
                       "the author login is not a valid GitHub login")
    ev.append(f"author      : {login} (is_bot={str(is_bot).lower()})")

    if is_bot:
        # Permission is still not consulted for ANY bot: `claude[bot]` resolves
        # to `none` and `app/github-actions` is a 404, so asking would answer
        # "outsider" for the App that owns this repo's loop. The exception is a
        # login comparison and is deliberately exactly one login wide.
        if is_self_app(login):
            base = TRUSTED
            ev.append(f"permission  : not consulted -- author is this repo's own "
                      f"delivery App ({SELF_APP}), trusted by the 2026-11-01 ruling")
        else:
            base = OUTSIDER
            ev.append("permission  : not consulted -- a bot author is untrusted by rule "
                      "(the only exception is this repo's own App)")
    else:
        p = lookup_permission(gh, repo, login)
        base = classify_permission(p)
        ev.append(f"permission  : {p.value or p.detail}")
        if base == UNRESOLVED:
            return Verdict(UNRESOLVED, ev, "the author's repository permission could not be resolved")

    if base == TRUSTED:
        ev.append("override    : not consulted (author is trusted)")
        return Verdict(TRUSTED, ev,
                       f"author is this repo's own delivery App ({SELF_APP})" if is_bot
                       else "author has write access")

    why = "author is a bot (untrusted by rule)" if is_bot else "author is not a collaborator with write access"
    if LABEL_TRUSTED not in labels:
        ev.append(f"override    : none ({LABEL_TRUSTED} not present)")
        return Verdict(OUTSIDER, ev, why)
    o = check_override(gh, repo, number)
    ev.append(f"override    : {o.note}")
    if o.unresolved:
        return Verdict(UNRESOLVED, ev, "the provenance override could not be verified")
    if o.valid:
        return Verdict(TRUSTED, ev, "a maintainer applied the override", override_valid=True)
    return Verdict(OUTSIDER, ev, why)


# --------------------------------------------------------------------------------------
# --apply: record the verdict. Everything below only runs when asked.
# --------------------------------------------------------------------------------------

def _comment_exists(gh: Gh, repo: str, number: int) -> bool | None:
    r = gh(["issue", "view", str(number), "--repo", repo, "--json", "comments"])
    if r.rc != 0:
        return None
    try:
        # Only a comment THIS token wrote counts: the marker is public text, and anyone who copies
        # it into a comment must not be able to silence the stop. A different token (a rerun
        # under another identity) posts a visible duplicate, which is the safe direction.
        return any(UNRESOLVED_MARKER in (c.get("body") or "") and c.get("viewerDidAuthor") is True
                   for c in json.loads(r.out).get("comments", []))
    except (ValueError, AttributeError, TypeError):
        return None


def apply_verdict(gh: Gh, repo: str, number: int, v: Verdict, current_labels: set) -> list:
    """Return a list of failure strings; empty means the record was written."""
    problems: list = []
    n = str(number)

    def do(args: list, what: str) -> None:
        r = gh(args)
        if r.rc != 0:
            problems.append(f"{what} failed (gh exit {r.rc}): {r.err.strip()[:120]}")

    if v.verdict == UNRESOLVED:
        if _comment_exists(gh, repo, number):
            return problems
        # Posted even when the existence check failed: a visible duplicate is better than a
        # stop that announces nothing (the clause the ruling turned on).
        body = (f"{UNRESOLVED_MARKER}\n**Provenance could not be resolved** ({v.reason}), so the "
                "loop is not working this issue. This is not a finding that the author is "
                "untrusted -- the check could not complete (a 403, a 5xx, a timeout, an empty "
                "answer or an unreadable author all stop here by design). Re-run "
                "`scripts/resolve_provenance.py` once the cause is cleared.")
        do(["issue", "comment", n, "--repo", repo, "--body", body], "comment")
        return problems

    want, drop = (LABEL_TRUSTED, LABEL_OUTSIDER) if v.verdict == TRUSTED else (LABEL_OUTSIDER, LABEL_TRUSTED)
    color = "0e8a16" if v.verdict == TRUSTED else "d93f0b"
    if want not in current_labels:
        # --force: create, or update the description of an existing one. Exit 0 either way.
        do(["label", "create", want, "--repo", repo, "--force", "--color", color,
            "--description", "Issue provenance resolved by scripts/resolve_provenance.py (#361)"],
           f"create label {want}")
        do(["issue", "edit", n, "--repo", repo, "--add-label", want], f"add label {want}")
    # The opposite label goes. A VALID human override can never be removed here: it makes
    # the verdict TRUSTED, so `drop` is then the (stale) outsider label, and a verdict of
    # OUTSIDER only exists when the trusted label failed verification.
    if drop in current_labels:
        do(["issue", "edit", n, "--repo", repo, "--remove-label", drop], f"remove label {drop}")
    return problems


def current_labels_of(gh: Gh, repo: str, number: int) -> set:
    r = gh(["issue", "view", str(number), "--repo", repo, "--json", "labels"])
    if r.rc != 0:
        return set()
    try:
        return {lab["name"] for lab in json.loads(r.out).get("labels", [])}
    except (ValueError, KeyError, TypeError):
        return set()


def main(argv: list | None = None, gh: Gh = run_gh) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("issue", type=int)
    ap.add_argument("--repo", default=os.environ.get("GH_REPO", ""))
    ap.add_argument("--apply", action="store_true",
                    help="record the verdict as a label (and comment on UNRESOLVED)")
    args = ap.parse_args(argv)

    if args.issue < 1 or not _REPO.match(args.repo or ""):
        print("usage: resolve_provenance.py <issue> --repo OWNER/NAME (or set GH_REPO)", file=sys.stderr)
        return EXIT[UNRESOLVED]

    v = classify(gh, args.repo, args.issue)
    print(f"#{args.issue}  {v.verdict} -- {v.reason}")
    for line in v.evidence:
        print(f"  {line}")

    code = EXIT[v.verdict]
    if args.apply:
        problems = apply_verdict(gh, args.repo, args.issue, v, current_labels_of(gh, args.repo, args.issue))
        for p in problems:
            print(f"  APPLY FAILED: {p}", file=sys.stderr)
        if problems:
            # A record that was not written is not a pass: downstream reads the label.
            return EXIT[UNRESOLVED]
        print("  recorded: " + ("comment posted/already present" if v.verdict == UNRESOLVED
                                 else f"label provenance:{v.verdict.lower()}"))
    return code


if __name__ == "__main__":
    sys.exit(main())
