#!/usr/bin/env python3
"""Prove `scripts/verify_agent_cycle_doc.py` can fail. 15 rows plus a control.

WHY THIS EXISTS

The gate this harness tests replaced a hand-written checker that passed clean
while four live defects sat in the two files it had just read. QA round 3 on
PR #564 established that by mutation: it injected eight false claims and one
README/HTML divergence into a copy, and the old checker printed
`ALL CHECKS PASS`, exit 0.

So this gate does not get to be trusted on its own say-so. Every row below is
a falsehood the gate MUST turn red on, and the control is a no-op edit it must
stay green on -- because a harness that reports CAUGHT for everything is
measuring nothing. The rows are deliberately the same shapes round 3 used
against the old checker, so the comparison is direct.

NOT WIRED INTO CI, deliberately and with a reason. `pr-gates.yml` runs
`mutate_verify_workflows.py` as a named step, and adding a step for this one
would make the PR that introduces it touch `.github/workflows/` -- a
trust-boundary path, which holds the whole PR for a human merge. The same
choice was already made for `mutate_learn_article_dates.py` and
`mutate_natal_prompt_gate.py`, which also live here unwired. Run it by hand
after changing either document or the gate:

    uv run python scripts/mutate_agent_cycle_doc_gate.py

WHAT THIS DOES NOT PROVE: that the gate checks every claim in the two
documents. It checks the claims it knows about, and this harness checks that
those checks bite. A claim neither file knows about is still unguarded -- the
gate's own docstring says so under "WHAT THIS DOES NOT CHECK, PLAINLY".
"""
import pathlib, shutil, subprocess, sys, tempfile, os

ROOT = pathlib.Path(__file__).resolve().parent.parent
H, R = "docs/agent-cycle.html", "README.md"

# Derived so the rows below cannot go stale when a workflow is added.
_WORKFLOWS = len(list((ROOT / ".github" / "workflows").glob("*.yml")))
_WORD = {15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
         19: "nineteen", 20: "twenty"}

# (label, file, old, new)
ROWS = [
 ("agents count, HTML fact tile",      H, "<b>15</b><span>agents</span>", "<b>50</b><span>agents</span>"),
 ("agents count, README word form",    R, "Fifteen agents", "Fifty agents"),
 # DERIVED, not hardcoded. These two anchored on the literal "17"/"seventeen"
 # and went stale the moment #461 added an 18th workflow -- the harness then
 # reported NOT BEHAVING for rows whose subject was fine. A mutation anchor
 # that tracks the repo cannot rot that way, and the gate it tests derives the
 # same number.
 ("workflows count, HTML fact tile",   H,
  f"<b>{_WORKFLOWS}</b><span>workflows</span>", "<b>3</b><span>workflows</span>"),
 ("workflows count, README",           R,
  f"{_WORD[_WORKFLOWS]} workflows", "three workflows"),
 # INVERTED, and the only row of this shape. Every other row restores a
 # falsehood; this one restores a hard-coded NUMBER -- which is what
 # `pr-gates.yml:326-333` forbids ("a literal number goes stale the moment a
 # gate is added") and what the first version of this gate REQUIRED. Two gates
 # landed on `main` between writing that version and merging it, so it would
 # have failed the required `gates` check for every code PR and halted
 # `agent-merge`. Found by independent QA on #564 before it merged.
 ("a hard-coded gate count comes back", H,
  "re-run every non-excluded <code>verify_*.py</code>", "re-run all 29 gates"),
 ("never-push count",                  H, "9 of the 15", "15 of the 15"),
 ("qa-on-green trigger count",         H, "Its one <code>workflow_run</code> trigger", "Its two triggers"),
 ("a weekly cron's IST day",           H, "<code>agent-discover</code> — Tue 01:30", "<code>agent-discover</code> — Mon 01:30"),
 ("architect tools",                   H, "Tools are <code>Read, Grep, Glob, Bash, Write</code>", "Tools are <code>Read, Grep, Glob, Bash, WebFetch</code>"),
 ("validate_issue exit codes",         H, "<li><code>4</code> <strong>INCONCLUSIVE</strong>", "<li><code>5</code> <strong>INCONCLUSIVE</strong>"),
 ("the qagreen->merge edge returns",   H, '["qagreen","qa","dispatches a round","back"],', '["qagreen","merge","qa-pass"],'),
 ("README routes QG into AM again",    R, "    G1 & G2 --> AM", "    G1 & G2 & QG --> AM"),
 ("hold edge disagrees across files",  H, '["merge","hold","boundary / needs-human-review","hold"],', '["merge","hold","boundary / size","hold"],'),
 ("a node is orphaned",                H, '["measure","score","GA4 + GSC"], ', ''),
 ("a trust-boundary path vanishes",    "*", "storage.py", "datastore.py"),
 ("CONTROL: a no-op edit",             H, "<!-- control -->", "<!-- control -->"),
]

caught, missed = [], []
with tempfile.TemporaryDirectory() as td:
    work = pathlib.Path(td) / "w"
    shutil.copytree(ROOT, work, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "node_modules"))
    pristine = {f: (work / f).read_text() for f in (H, R)}
    # the CONTROL row needs its anchor to exist
    (work / H).write_text(pristine[H] + "\n<!-- control -->\n")
    pristine[H] = (work / H).read_text()

    for label, f, old, new in ROWS:
        for g, txt in pristine.items():
            (work / g).write_text(txt)
        if f == "*":
            # every occurrence, in BOTH documents: the gate asks whether the
            # path appears ANYWHERE, so one surviving mention keeps it green.
            hits = sum(pristine[g].count(old) for g in pristine)
            if hits == 0:
                print(f"  ANCHOR  {label}: no occurrence — row is stale")
                missed.append(label); continue
            for g in pristine:
                (work / g).write_text(pristine[g].replace(old, new))
        else:
            src = pristine[f]
            if src.count(old) != 1:
                print(f"  ANCHOR  {label}: matched {src.count(old)}x — row is stale")
                missed.append(label); continue
            (work / f).write_text(src.replace(old, new, 1))
        r = subprocess.run(("uv", "run", "python", "scripts/verify_agent_cycle_doc.py"),
                           cwd=work, capture_output=True, text=True)
        red = r.returncode == 1
        is_control = label.startswith("CONTROL")
        good = (not red) if is_control else red
        tag = "CAUGHT" if (red and not is_control) else ("MISSED" if not red and not is_control
               else ("ok (stayed green)" if is_control and not red else "CONTROL WENT RED"))
        print(f"  {tag:<18} {label}")
        if not good:
            missed.append(label)
            print("      " + (r.stdout.strip().splitlines() or ["<no output>"])[-1][:120])
        else:
            caught.append(label)

    for g, txt in pristine.items():
        (work / g).write_text(txt)

print(f"\n{len(caught)}/{len(ROWS)} behaved as required")
if missed:
    print("NOT BEHAVING: " + ", ".join(missed))
sys.exit(1 if missed else 0)
