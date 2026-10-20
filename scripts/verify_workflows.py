#!/usr/bin/env python3
"""Gate: static checks over every `.github/workflows/*.yml`.

WHY THIS EXISTS

On 2026-10-09 the nightly produced a correct, QA'd PR that could not merge.
Tracing it surfaced four defects in the agent loop's own plumbing, each there
since the code was written, and not one produced a red run anybody read (#313):

    defect                                                    caught by
    --------------------------------------------------------  -------------
    1. agent-merge read `steps.pr.outputs.sha` inside the     check 1 (here)
       step whose id is `pr` -- always empty, HTTP 422
    2. close-on-evidence lacked `pull-requests: read`, so     check 2 (here)
       its close step got HTTP 403 -- and its `if` had never
       passed, so the step had never run to show it
    3. pr-gates omitted `ready_for_review` from `types`, so   check 3 (here)
       a draft PR got no checks (#303)
    4. agent-merge fetched `isDraft` and never read it        NOT CAUGHT

Nothing read those files. `verify-production.yml` asserts against the deployed
site and `pr-gates.yml` runs the gates over the tree; neither looked at the
automation that decides what reaches either.

WHAT IT CHECKS

 1. self-reference   A step with `id: X` whose own `run` / `with` / `env` /
                     `if` contains `steps.X.outputs.` -- always empty at that
                     point. Shell comments are stripped from `run` first
                     (YAML does NOT strip them from a block scalar), because
                     agent-merge.yml now DISCUSSES that exact expression in
                     prose beside the fix. The strip is quote-aware: a `#`
                     inside quotes is text, not a comment.
 2. permissions      Every `gh` call in a `run:` block, cross-checked against
                     the job's effective `permissions` (job-level if present,
                     else workflow-level; write implies read; an omitted scope
                     is `none`). A missing scope is a FAIL, never a warning.
                     Only calls whose token IS the workflow token are judged:
                     `GH_TOKEN` is resolved step env -> job env -> workflow
                     env. Any other secret is SKIPPED and printed. No token at
                     all is a FAIL -- `gh` cannot authenticate. A `gh api`
                     path or a `gh` subcommand it cannot classify is PRINTED
                     as unclassified, never guessed at, and does not fail.
                     Text inside a claude-code-action `prompt:` or
                     `claude_args` is not inspected: that action authenticates
                     with its own App token, not GITHUB_TOKEN.
 3. trigger types    `pull_request` / `pull_request_target` must carry an
                     explicit `types:` list including `ready_for_review`. The
                     default set is [opened, synchronize, reopened]. PyYAML
                     parses the `on:` key as boolean True; handled.

Exit codes: 0 pass, 1 fail, 2 COULD NOT VERIFY (PyYAML missing, or no workflow
files at all). 2 is not a pass.

A file that does not parse is a FAILURE, not a skip -- a checker that silently
narrows its own scope and reports success is the failure this gate is for.
`EXPECTED_WORKFLOWS` is pinned so a deleted or renamed workflow cannot vanish
silently; raise it when adding one, never lower it to get green.

WHAT IT DOES NOT CATCH, stated plainly

 * Defect 4 (a value fetched and never read). Detecting "unused" needs data
   flow through shell; this is pattern matching. It would have caught nothing
   about `isDraft`.
 * Anything about EFFECT. A workflow can satisfy all three checks and still
   do nothing: a trigger that never fires, an `if` that is never true, a step
   that is `continue-on-error` and quietly fails. #313 part 2, a weekly
   outcome report, is the answer to that class; this gate is not.
 * Whether a permission is *sufficient* beyond the scope name -- repository
   settings (e.g. "allow Actions to create PRs") are invisible from the tree.
 * `gh` calls it cannot see: inside a script file, behind an alias, or in a
   multi-line quoted string whose line happens not to start at a command
   position. Heredocs containing apostrophes can desynchronise the quote
   tracker in the comment stripper.
 * A `${{ }}` expression read through `steps['x']` index syntax.

stdlib + PyYAML only (PyYAML is present transitively via uvicorn[standard]; it
is not declared in pyproject.toml). No network.

    uv run python scripts/verify_workflows.py [--dir .github/workflows]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environmental
    print("COULD NOT VERIFY (exit 2) - PyYAML is not importable. This is NOT a pass.\n"
          "  It is a transitive dependency of uvicorn[standard]; `uv sync` provides it.")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / ".github" / "workflows"

# Pinned so a workflow cannot be deleted or renamed out of the sweep silently.
# Raise it when adding one.
EXPECTED_WORKFLOWS = 15

# Triggers whose default `types` omit `ready_for_review`.
PR_TRIGGERS = ("pull_request", "pull_request_target")

# Triggers that give a job a WRITE token while the head of the pull request is
# chosen by someone who may not have write access to this repository (#358):
#
#   pull_request_target  runs the BASE repo's definition against a fork head
#   workflow_run         fires in the BASE repo after a `pull_request` run,
#                        with the base definition and a write token
#   issue_comment        body and author are arbitrary
#
# In a workflow carrying one of these, no `${{ }}` may appear inside a `run:`
# block. See check 5 for why that rule is "none" rather than a list of unsafe
# expressions.
PRIVILEGED_TRIGGERS = ("pull_request_target", "workflow_run", "issue_comment")

# (file, trigger) -> why it need not listen for `ready_for_review`. An entry
# here is a hole in check 3; each one must justify itself beside it.
# The `types:` value is part of what the exemption means, so it is stored and
# asserted. See the check below for what QA demonstrated when it was not.
TRIGGER_EXEMPT: dict[tuple[str, str], tuple[str, list[str]]] = {
    # agent-merge's `pull_request_target` leg exists to react to the `qa-pass`
    # LABEL, and `types: [labeled]` is that intent stated explicitly. Draft
    # state is not what it waits on: it un-drafts the PR itself, in the
    # "Take it out of draft" step, once gates are green and qa-pass is set.
    ("agent-merge.yml", "pull_request_target"):
        ("reacts to the qa-pass label; un-drafts the PR itself before merging",
         ["labeled"]),
}

LEVELS = {"none": 0, "read": 1, "write": 2}

# gh subcommand -> (scope, level). Unknown subcommands are reported as
# unclassified rather than guessed at.
PR_READ = {"view", "list", "diff", "checks", "status"}
PR_WRITE = {"edit", "merge", "comment", "ready", "create", "close", "review"}
ISSUE_READ = {"view", "list"}
ISSUE_WRITE = {"close", "comment", "edit", "create", "reopen"}
RUN_READ = {"download", "view", "list"}
RUN_WRITE = {"rerun", "cancel", "delete"}
WORKFLOW_READ = {"list", "view"}
WORKFLOW_WRITE = {"run", "enable", "disable"}

# `gh api` flags that consume the next token, so it is not mistaken for the path.
API_VALUE_FLAGS = {"-X", "--method", "-H", "--header", "-f", "--raw-field",
                   "-F", "--field", "-q", "--jq", "--input", "--hostname",
                   "-t", "--template", "--cache", "-p", "--preview"}
API_FIELD_FLAGS = {"-f", "--raw-field", "-F", "--field", "--input"}
WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def fail(self, file: str, line: int | None, where: str, rule: str, msg: str) -> None:
        loc = f"{file}:{line}" if line else file
        self.failures.append(f"FAIL  {loc}  {where}  [{rule}]  {msg}")

    def note(self, text: str) -> None:
        self.notes.append(text)


# --------------------------------------------------------------------------
# Shell text handling
# --------------------------------------------------------------------------

def strip_shell_comments(text: str) -> str:
    """Blank out `# ...` comments, preserving newlines (so line numbers hold).

    A `#` starts a comment only when it is unquoted AND at the start of a word
    (line start or after whitespace) -- so `$#`, `${#x}` and `"a # b"` survive.
    Quote state carries across lines, as the shell's does.
    """
    out: list[str] = []
    quote: str | None = None
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if quote == "'":
            if c == "'":
                quote = None
            out.append(c)
        elif quote == '"':
            if c == "\\" and i + 1 < n:
                out.append(c)
                i += 1
                out.append(text[i])
            else:
                if c == '"':
                    quote = None
                out.append(c)
        else:
            if c == "\\" and i + 1 < n:
                out.append(c)
                i += 1
                out.append(text[i])
            elif c in "'\"":
                quote = c
                out.append(c)
            elif c == "#" and (i == 0 or text[i - 1] in " \t\n"):
                while i < n and text[i] != "\n":
                    i += 1
                continue  # the newline itself is appended by the next pass
            else:
                out.append(c)
        i += 1
    return "".join(out)


def logical_lines(text: str) -> list[tuple[int, str]]:
    """(0-based first physical line, text) with backslash continuations joined."""
    result: list[tuple[int, str]] = []
    buf, start = "", 0
    for idx, raw in enumerate(text.split("\n")):
        if not buf:
            start = idx
        if raw.rstrip().endswith("\\"):
            buf += raw.rstrip()[:-1] + " "
            continue
        result.append((start, buf + raw))
        buf = ""
    if buf:
        result.append((start, buf))
    return result


GH_WORD = re.compile(r"(?<![\w./$-])gh\s+(?=\S)")
CONTROL_PREFIX = ("&&", "||", ";", "|", "(", "`", "!", "{", "$(")
CONTROL_WORD = re.compile(r"(?:^|\s)(?:then|do|else|if|elif|while|until)$")


def gh_calls(run_text: str) -> list[tuple[int, list[str]]]:
    """Every `gh` invoked at COMMAND position: (0-based line, argument tokens).

    Command position excludes prose mentions such as
    `echo "... by hand: gh workflow run ..."`, which is the shape agent-merge
    uses in its warning text.
    """
    calls: list[tuple[int, list[str]]] = []
    for lineno, line in logical_lines(strip_shell_comments(run_text)):
        for m in GH_WORD.finditer(line):
            prefix = line[: m.start()].rstrip()
            if not (prefix == "" or prefix.endswith(CONTROL_PREFIX)
                    or CONTROL_WORD.search(prefix)):
                continue
            rest = line[m.end():]
            toks: list[str] = []
            for t in re.findall(r"\"[^\"]*\"|'[^']*'|\S+", rest):
                if t.startswith(("&&", "||", ";", "|", ")")) or t in ("&", "2>&1"):
                    break
                toks.append(t)
            calls.append((lineno, toks))
    return calls


def unquote(tok: str) -> str:
    return tok[1:-1] if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "'\"" else tok


# --------------------------------------------------------------------------
# gh -> required permission
# --------------------------------------------------------------------------

def classify(toks: list[str]) -> tuple[str, str, str] | None:
    """(scope, level, description) or None when it cannot be classified."""
    words = [unquote(t) for t in toks if not t.startswith("-")]
    if not words:
        return None
    group = words[0]
    if group == "api":
        return classify_api(toks)
    verb = words[1] if len(words) > 1 else ""
    desc = f"gh {group} {verb}".strip()
    table = {
        "pr": ("pull-requests", PR_READ, PR_WRITE),
        "issue": ("issues", ISSUE_READ, ISSUE_WRITE),
        "run": ("actions", RUN_READ, RUN_WRITE),
        "workflow": ("actions", WORKFLOW_READ, WORKFLOW_WRITE),
    }.get(group)
    if table is None:
        return None
    scope, reads, writes = table
    if verb in writes:
        return scope, "write", desc
    if verb in reads:
        return scope, "read", desc
    return None


def classify_api(toks: list[str]) -> tuple[str, str, str] | None:
    path, method, has_fields = None, "GET", False
    i = 0
    toks = list(toks)
    # drop the `api` word itself
    while i < len(toks) and toks[i].startswith("-"):
        i += 1
    i += 1
    while i < len(toks):
        t = toks[i]
        flag = t.split("=", 1)[0]
        if t.startswith("-"):
            if flag in ("-X", "--method"):
                method = (unquote(toks[i + 1]) if "=" not in t and i + 1 < len(toks)
                          else t.split("=", 1)[-1]).upper()
            if flag in API_FIELD_FLAGS:
                has_fields = True
            i += 1 if "=" in t else (2 if flag in API_VALUE_FLAGS else 1)
            continue
        if path is None:
            path = unquote(t)
        i += 1
    if path is None:
        return None
    # gh switches to POST when fields are supplied without an explicit method.
    write = method in WRITE_METHODS or (has_fields and method == "GET")
    level = "write" if write else "read"
    desc = f"gh api {path}"
    if re.search(r"/pulls(?:[/?]|$)", path):
        return "pull-requests", level, desc
    if "/actions/" in path:
        return "actions", level, desc
    if re.search(r"/check-(?:runs|suites)(?:[/?]|$)", path):
        return "checks", level, desc
    return None


# --------------------------------------------------------------------------
# YAML structure
# --------------------------------------------------------------------------

def yaml_get(mapping: dict, key: str):
    """PyYAML (YAML 1.1) parses the bare key `on` as boolean True."""
    if key in mapping:
        return mapping[key]
    if key == "on" and True in mapping:
        return mapping[True]
    return None


def step_lines(text: str) -> dict[tuple[str, int], tuple[int, int]]:
    """(job, step index) -> (1-based line of the step, 1-based line of run body).

    safe_load throws line numbers away; compose keeps them, so a failure can
    point at file:line instead of making the author search.
    """
    out: dict[tuple[str, int], tuple[int, int]] = {}
    root = yaml.compose(text)
    if not isinstance(root, yaml.MappingNode):
        return out
    jobs = next((v for k, v in root.value if k.value == "jobs"), None)
    if not isinstance(jobs, yaml.MappingNode):
        return out
    for jk, jv in jobs.value:
        if not isinstance(jv, yaml.MappingNode):
            continue
        steps = next((v for k, v in jv.value if k.value == "steps"), None)
        if not isinstance(steps, yaml.SequenceNode):
            continue
        for idx, sv in enumerate(steps.value):
            run_line = sv.start_mark.line + 1
            if isinstance(sv, yaml.MappingNode):
                for k, v in sv.value:
                    if k.value == "run":
                        run_line = v.start_mark.line + (2 if v.style in ("|", ">") else 1)
            out[(jk.value, idx)] = (sv.start_mark.line + 1, run_line)
    return out


def leaves(obj) -> list[str]:
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in leaves(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in leaves(v)]
    return [] if obj is None else [str(obj)]


def effective_permissions(job: dict, doc: dict):
    """(perms dict or None when undeclared anywhere, where it came from)."""
    for src, container in (("job", job), ("workflow", doc)):
        if "permissions" in container:
            p = container["permissions"]
            if p is None:
                return {}, src
            if p == "read-all":
                return {"*": "read"}, src
            if p == "write-all":
                return {"*": "write"}, src
            if isinstance(p, dict):
                return p, src
            return {}, src
    return None, "nowhere"


def perm_level(perms: dict, scope: str) -> int:
    if scope in perms:
        return LEVELS.get(str(perms[scope]), 0)
    return LEVELS.get(str(perms.get("*", "none")), 0)


WORKFLOW_TOKEN = re.compile(r"\$\{\{\s*(?:github\.token|secrets\.GITHUB_TOKEN)\s*\}\}")


def resolve_token(step: dict, job: dict, doc: dict) -> str | None:
    for container in (step, job, doc):
        env = container.get("env")
        if isinstance(env, dict):
            for key in ("GH_TOKEN", "GITHUB_TOKEN"):
                if key in env:
                    return str(env[key])
    return None


# --------------------------------------------------------------------------
# The three checks
# --------------------------------------------------------------------------

def check_workflow_run_targets(name: str, doc: dict, known: set[str], rep: Report) -> None:
    """A `workflow_run` trigger must name a workflow some file declares.

    `workflows:` matches a workflow's `name:` FIELD, never its filename, and an
    unmatched entry is not an error GitHub reports — the trigger simply never
    fires. That is the most expensive failure shape in this repository: wiring
    that reads as present and does nothing.

    Measured 2026-10-20. `agent-steward.yml` was given

        workflow_run:
          workflows: ["agent-work"]

    while `agent-work.yml` declares `name: Agent work`. Nothing matched, so the
    trigger added to make the steward react to a finished cycle could never have
    fired — on top of the separate bot-actor defect #439 fixed in the same
    trigger. Two never-fires bugs stacked in six lines, both the same class as
    #421, and both inside the change written to end #421.

    A workflow with no `name:` is known by its path, which is what GitHub lists,
    so that spelling is accepted too.
    """
    on = yaml_get(doc, "on")
    if not isinstance(on, dict):
        return
    wr = on.get("workflow_run")
    if not isinstance(wr, dict):
        return
    targets = wr.get("workflows")
    if not isinstance(targets, list) or not targets:
        rep.fail(name, None, "(on: workflow_run)", "workflow-run-target",
                 "`workflow_run` with no `workflows:` list — it will fire for "
                 "every workflow in the repository, which is almost never meant")
        return
    for t in targets:
        if not isinstance(t, str) or t not in known:
            rep.fail(name, None, "(on: workflow_run)", "workflow-run-target",
                     f"`workflows: [{t!r}]` names no workflow in this repository. "
                     f"It matches a workflow's `name:` field, not its filename, so "
                     f"this trigger NEVER FIRES and says nothing about it. "
                     f"Declared names: {', '.join(sorted(known))}")


def check_triggers(name: str, doc: dict, rep: Report) -> None:
    on = yaml_get(doc, "on")
    if isinstance(on, str):
        on = {on: None}
    elif isinstance(on, list):
        on = {t: None for t in on}
    if not isinstance(on, dict):
        rep.fail(name, None, "(workflow)", "trigger-types", "no readable `on:` block")
        return
    for trig in PR_TRIGGERS:
        if trig not in on:
            continue
        cfg = on[trig]
        types = cfg.get("types") if isinstance(cfg, dict) else None
        if isinstance(types, str):
            types = [types]
        # Keyed on (file, trigger), the exemption used to survive ANY `types:`
        # value — including None. QA changed agent-merge's `types: [labeled]` to
        # `[opened]`, then deleted the line, and both stayed green while the gate
        # PRINTED the old justification as though still true:
        #     EXEMPT agent-merge.yml ... types=None -- reacts to the qa-pass label
        # The justification is specifically that `[labeled]` IS the intent; once
        # the value changes it no longer holds. An exemption that cannot notice
        # it has stopped applying is a place to hide the defect check 3 is for.
        if (name, trig) in TRIGGER_EXEMPT:
            why, exempt_types = TRIGGER_EXEMPT[(name, trig)]
            if sorted(types or []) != sorted(exempt_types):
                rep.fail(name, None, f"on.{trig}", "trigger-types",
                         f"`types: {types}` is exempt only as `types: {exempt_types}` "
                         f"({why}). The exemption was granted for that exact value; "
                         "with a different one it does not apply. Restore the value, "
                         "or remove the TRIGGER_EXEMPT entry and justify the new one.")
                continue
            rep.note(f"EXEMPT  {name}  `{trig}` types={types}  -- {why}")
            continue
        if not types:
            rep.fail(name, None, f"on.{trig}", "trigger-types",
                     "no explicit `types:` list. The default set is [opened, synchronize, "
                     "reopened] and omits `ready_for_review`, so a draft PR that is later "
                     "readied emits an event nothing listens to (#303). List the types, "
                     "including ready_for_review.")
        elif "ready_for_review" not in types:
            rep.fail(name, None, f"on.{trig}", "trigger-types",
                     f"`types: {types}` omits `ready_for_review` -- a draft PR that is "
                     "readied later gets no run (#303).")


def run_blocks(text: str) -> list[tuple[int, str]]:
    """(1-based line of each `run:` body line, that line) for every run: scalar.

    Hand-scanned rather than taken from `yaml.compose`, because the check below
    needs the RAW text: safe_load would already have resolved nothing (the
    expression is literal inside the scalar) but compose would hand back a
    single blob whose internal line numbers must then be recomputed anyway.
    A block ends at the first line indented no further than the `run:` key.
    """
    out: list[tuple[int, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)run:\s*[|>]", lines[i])
        if not m:
            i += 1
            continue
        ind = len(m.group(1))
        i += 1
        while i < len(lines):
            ln = lines[i]
            if ln.strip() and len(ln) - len(ln.lstrip()) <= ind:
                break
            out.append((i + 1, ln))
            i += 1
    return out


def check_interpolation(name: str, text: str, doc: dict, rep: Report) -> None:
    """Check 5: no `${{ }}` inside a `run:` block of a privileged workflow (#358).

    WHY THE RULE IS "NONE", NOT "NO UNSAFE ONES"
    --------------------------------------------
    `${{ }}` is textual substitution performed BEFORE bash parses the script.
    An interpolated value is not a shell string, it is shell source. So the
    question is never "is this quoted properly" -- there is no quoting that
    survives, because the quotes are part of the text being replaced.

    A gate that allowed "safe" expressions would have to decide which values an
    outsider can influence, and that judgment is exactly what went wrong:
    `agent-merge` interpolated a pull-request HEAD BRANCH NAME into
    `case "${{ steps.pr.outputs.branch }}" in` -- the agent-branch filter
    itself -- in a job holding contents+actions write, with no fork guard.
    `git check-ref-format` accepts `$ ( ) " ` ; & |` in a branch name and
    `${IFS}` stands in for the forbidden space, so the filter was the injection
    point and ran before it could reject anything.

    Values reach these jobs through `env:` instead, where bash never re-parses
    them, and are expanded quoted. That is mechanical, so this gate is too.

    Shell comments are stripped first: the fix is documented in comments that
    necessarily quote the construct they warn about, and a gate that could not
    tell a warning from an occurrence would punish explaining itself.
    """
    on = yaml_get(doc, "on")
    if isinstance(on, str):
        on = {on: None}
    elif isinstance(on, list):
        on = {trig: None for trig in on}
    if not isinstance(on, dict):
        return  # check_triggers already failed this file
    privileged = [trig for trig in PRIVILEGED_TRIGGERS if trig in on]
    if not privileged:
        return

    hits = 0
    for lineno, raw in run_blocks(text):
        if "${{" not in raw:
            continue
        # strip_shell_comments preserves line count, so index 0 is this line.
        if "${{" not in strip_shell_comments(raw):
            continue
        # DETECTION IS THE PRESENCE OF `${{`, NOT A MATCH ON THE WHOLE
        # EXPRESSION. The first draft of this check reported
        # `re.findall(r"\$\{\{[^}]*\}\}")` and exited 0 on
        # `${{ format('{0}', steps.pr.outputs.branch) }}` -- `[^}]*` stops at
        # the `}` inside `{0}`, so a real defect read as clean and the gate
        # even printed "ok". mutate_verify_workflows.py caught it, and check 1
        # above carries a comment about the identical trap, which is how a
        # second instance of one mistake ends up in one file.
        #
        # So: every `${{` is a failure, and the expression text is only ever
        # used to make the message readable.
        for idx in (m.start() for m in re.finditer(r"\$\{\{", raw)):
            end = raw.rfind("}}")
            expr = raw[idx:end + 2] if end > idx else raw[idx:]
            if len(expr) > 90:
                expr = expr[:87] + "..."
            hits += 1
            rep.fail(name, lineno, "(run:)", "interpolation",
                     f"`{expr.strip()}` is substituted into shell before bash parses it; "
                     f"this workflow is triggered by {'/'.join(privileged)}, so pass it "
                     "through `env:` and expand it quoted instead (#358)")
    if not hits:
        rep.note(f"ok    {name}  [interpolation]  privileged trigger "
                 f"({'/'.join(privileged)}); no `${{{{ }}}}` in any run: block")


def check_job(name: str, text_lines: dict, jid: str, job: dict, doc: dict, rep: Report) -> None:
    steps = job.get("steps")
    if not isinstance(steps, list):
        return
    perms, perms_src = effective_permissions(job, doc)
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        sline, rline = text_lines.get((jid, idx), (None, None))
        label = step.get("name") or step.get("id") or f"#{idx + 1}"
        where = f"job={jid} step={label!r}"
        run = step.get("run")
        run_clean = strip_shell_comments(run) if isinstance(run, str) else ""

        # 1. self-referencing step output ---------------------------------
        sid = step.get("id")
        if sid:
            # Must sit inside a `${{ ... }}` span. GitHub interpolates ONLY
            # there, so a bare `steps.<id>.outputs.x` in a shell string is inert
            # text and reporting it is a false positive — QA found it with
            #     echo "see steps.live.outputs.ok in the next step"   -> FAIL
            # which is exactly the kind of prose this repo writes beside a fix.
            #
            # The harness ENSHRINED that false positive: its mutation
            # "self-reference inside a QUOTED string is not a comment" planted an
            # uninterpolated mention and REQUIRED exit 1, so it would have passed
            # forever holding the wrong answer, and fixing the gate would have
            # read as a harness regression. That mutation now uses `${{ ... }}`,
            # which is a real defect, and a control pins the other side.
            #
            # EXTRACT the span, then search inside it. The first version of this
            # used a single pattern with `[^}]*` between `${{` and the
            # reference, reasoning that a character class could not run past its
            # own closing braces into a later expression. True, and it also
            # could not run past a `}` INSIDE the same expression — so any
            # `format()` placeholder hid the reference completely:
            #
            #   ${{ format('v{0}-{1}', github.run_number, steps.tag.outputs.sha) }}
            #
            # is defect 1 of #313 verbatim, and the `[^}]*` version exited 0 on
            # it while the version before THAT exited 1. A narrowed check that
            # misses a real defect is worse than the false positive it fixed.
            # Found by QA; reproduced here with old and new side by side before
            # changing anything. `MUTATIONS` now pins it.
            #
            # `.*?` is safe once the match is confined to one span: finditer
            # yields each `${{ ... }}` separately, so a reference cannot be
            # attributed to a span it does not sit in.
            span = re.compile(r"\$\{\{(.*?)\}\}", re.S)
            ref = re.compile(r"steps\." + re.escape(str(sid)) + r"\.outputs\b")
            sources = {"run": run_clean, "if": str(step.get("if", "")),
                       "with": "\n".join(leaves(step.get("with"))),
                       "env": "\n".join(leaves(step.get("env")))}
            for field, body in sources.items():
                hit = None
                for sp in span.finditer(body):
                    inner = ref.search(sp.group(1))
                    if inner:
                        # offset of the reference within `body`, so the reported
                        # line is the reference's own and not the span's start.
                        hit = sp.start(1) + inner.start()
                        break
                if hit is not None:
                    ln = sline
                    if field == "run" and rline:
                        ln = rline + body[:hit].count("\n")
                    rep.fail(name, ln, where, "self-reference",
                             f"step id `{sid}` reads its own `steps.{sid}.outputs.*` in `{field}`"
                             " -- empty at that point (defect 1 in #313: HTTP 422). Use the event "
                             "payload, or read it in a LATER step.")

        # 2. gh calls vs permissions --------------------------------------
        if not run_clean:
            continue
        calls = gh_calls(run)
        if not calls:
            continue
        token = resolve_token(step, job, doc)
        if token is None:
            rep.fail(name, sline, where, "permissions",
                     "calls `gh` but no GH_TOKEN/GITHUB_TOKEN is set in step, job or workflow "
                     "env -- gh cannot authenticate. Add `GH_TOKEN: ${{ github.token }}`.")
            continue
        if not WORKFLOW_TOKEN.search(token):
            rep.note(f"SKIPPED  {name}  {where}  {len(calls)} gh call(s) use a non-workflow "
                     f"token ({token.strip()[:40]}); permissions block does not apply")
            continue
        seen: set[tuple[str, str]] = set()
        for lineno, toks in calls:
            ln = (rline + lineno) if rline else sline
            cls = classify(toks)
            if cls is None:
                rep.note(f"UNCLASSIFIED  {name}:{ln}  {where}  `gh {' '.join(toks)[:70]}`"
                         " -- not in the rule table; not judged")
                continue
            scope, need, desc = cls
            if (scope, need) in seen:
                continue
            seen.add((scope, need))
            if perms is None:
                rep.fail(name, ln, where, "permissions",
                         f"`{desc}` needs `{scope}: {need}` but no `permissions:` block exists "
                         "at job or workflow level. Declare one -- an undeclared block inherits "
                         "whatever the repository default is, which is invisible from the tree.")
                continue
            have = perm_level(perms, scope)
            if have < LEVELS[need]:
                got = next((k for k, v in LEVELS.items() if v == have), "none")
                rep.fail(name, ln, where, "permissions",
                         f"`{desc}` needs `{scope}: {need}`; the {perms_src}-level block "
                         f"grants `{scope}: {got}` (an omitted scope is `none`) -- "
                         f"expect HTTP 403 at run time.")


def declared_names(files: list[Path]) -> set[str]:
    """Every name GitHub knows a workflow in this repo by.

    Its `name:` when it has one, and otherwise the repo-relative path, which is
    what the API lists (`agent-steward.yml` had no `name:` and appeared as
    `.github/workflows/agent-steward.yml` until 2026-10-20).
    """
    out: set[str] = set()
    for f in files:
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError):
            continue
        nm = doc.get("name") if isinstance(doc, dict) else None
        out.add(nm if isinstance(nm, str) and nm.strip() else f".github/workflows/{f.name}")
    return out


def check_file(path: Path, rep: Report, known: set[str] | None = None) -> None:
    name = path.name
    try:
        text = path.read_text(encoding="utf-8")
        doc = yaml.safe_load(text)
        lines = step_lines(text)
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        first = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        rep.fail(name, None, "(file)", "parse",
                 f"cannot parse -- a file this gate cannot read is a failure, not a skip: {first}")
        return
    if not isinstance(doc, dict) or not isinstance(doc.get("jobs"), dict):
        rep.fail(name, None, "(file)", "parse", "no top-level `jobs:` mapping")
        return
    check_triggers(name, doc, rep)
    if known is not None:
        check_workflow_run_targets(name, doc, known, rep)
    check_interpolation(name, text, doc, rep)
    for jid, job in doc["jobs"].items():
        if isinstance(job, dict):
            check_job(name, lines, str(jid), job, doc, rep)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=str(DEFAULT_DIR),
                    help="workflows directory (default .github/workflows)")
    args = ap.parse_args()
    wdir = Path(args.dir)

    files = sorted(list(wdir.glob("*.yml")) + list(wdir.glob("*.yaml")))
    if not files:
        print(f"COULD NOT VERIFY (exit 2) - no workflow files in {wdir}. This is NOT a pass.")
        return 2

    known = declared_names(files)
    rep = Report()
    if len(files) < EXPECTED_WORKFLOWS:
        rep.failures.append(
            f"FAIL  {wdir}  [count]  found {len(files)} workflow files, expected at least "
            f"{EXPECTED_WORKFLOWS} (EXPECTED_WORKFLOWS) -- one was deleted or renamed out of "
            "the sweep. If that was deliberate, lower the pin in the same commit and say why.")
    for f in files:
        check_file(f, rep, known)

    for n in rep.notes:
        print(n)
    for f in rep.failures:
        print(f)
    if rep.failures:
        print(f"\nFAIL - {len(rep.failures)} problem(s) across {len(files)} workflow files")
        return 1
    print(f"PASS - {len(files)} workflow files; workflow_run targets, self-reference, "
          f"gh-vs-permissions, "
          "pull_request types and run:-interpolation checks clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
