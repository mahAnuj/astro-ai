#!/usr/bin/env python3
r"""Prove `scripts/verify_workflows.py` can actually go red.

A gate that has only ever been run on a clean tree proves nothing about whether
it would catch the defects it exists for (#313). So: copy `.github/workflows`
to a temp dir, re-introduce one defect at a time, run the gate against the copy
with `--dir`, and require BOTH

  1. exit code 1, and
  2. a FAIL line that names the mutated file AND the rule AND the specific
     thing broken -- not some neighbour. A mutation that only turns the gate
     red because a different file was already failing proves nothing.

CONTROLS run first and matter as much as the mutations:

  * the untouched copy must exit 0, otherwise every result below is noise;
  * a copy where the self-reference expression appears ONLY in shell comments
    (a whole-line comment and a trailing one) must exit 0 -- the false
    positive #313 warns about, since agent-merge.yml discusses the expression
    in prose beside its fix;
  * the same text UNINTERPOLATED inside a quoted shell string must also exit 0.
    GitHub substitutes only inside `${{ }}`; bare text is inert. QA found the
    gate failing on `echo "see steps.live.outputs.ok in the next step"`, and
    found this harness REQUIRING that wrong answer;
  * the same text INTERPOLATED (`${{ ... }}`) inside a quoted string must exit 1
    -- substitution happens before the shell runs, so quoting is irrelevant.

Every mutation asserts that it actually changed the file. A mutation that
silently matched nothing would "pass" a gate that was never tested.

Never touches the real tree. Exit 0 = every control and mutation behaved.

    uv run python scripts/mutate_verify_workflows.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "scripts" / "verify_workflows.py"
REAL = ROOT / ".github" / "workflows"


def swap(old: str, new: str):
    def apply(text: str) -> str:
        if text.count(old) != 1:
            raise SystemExit(f"mutation anchor {old!r} matched {text.count(old)}x, need exactly 1 "
                             "-- the workflow changed; update this script, do not skip it")
        return text.replace(old, new)
    return apply


def run_gate(wdir: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(GATE), "--dir", str(wdir)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def fresh_copy(base: Path, label: str) -> Path:
    d = base / label
    shutil.copytree(REAL, d)
    return d


NUM_LINE = 'echo "number=$n" >> "$GITHUB_OUTPUT"'

# (name, file, transform, substrings that ONE FAIL line must all contain)
MUTATIONS = [
    ("defect 1: steps.pr.outputs.sha back inside the `pr` step", "agent-merge.yml",
     # The anchor is `$RUN_HEAD_SHA`, not the interpolated form: #358 moved
     # every event value in this workflow behind `env:`. The mutation plants the
     # interpolated self-reference back, so check 1 AND check 5 both fire on it
     # -- the assertion below still names the check-1 line specifically.
     swap("commits/$RUN_HEAD_SHA/pulls",
          "commits/${{ steps.pr.outputs.sha }}/pulls"),
     ["agent-merge.yml", "[self-reference]", "step id `pr`"]),
    # CORRECTED after QA. This previously planted an UNINTERPOLATED mention
    # inside the quotes and required exit 1 — enshrining a false positive, since
    # GitHub interpolates only inside `${{ }}` and a bare `steps.x.outputs.y` in
    # a shell string is inert text. The harness would have passed forever while
    # holding the wrong answer, and fixing the gate would have looked like a
    # regression here. That is the inverse of what this file exists to prevent.
    #
    # Interpolated inside a quoted string IS a defect: substitution happens
    # before the shell ever sees it, so the quoting is irrelevant.
    # Pins NEW-1. The `[^}]*` version of the check exited 0 on this while the
    # version before it exited 1 — a `format()` placeholder's `}` hid the
    # reference, so a real defect-1 instance walked straight through. No
    # mutation covered it, so the harness reported 18/18 regardless. QA found it
    # by diffing the two gates against the same tree.
    ("self-reference hidden behind a format() placeholder", "agent-merge.yml",
     swap(NUM_LINE,
          'echo "n=${{ format(\'v{0}\', steps.pr.outputs.sha) }}" >> "$GITHUB_OUTPUT"'),
     ["agent-merge.yml", "[self-reference]", "step id `pr`"]),
    ("self-reference interpolated inside a quoted string", "agent-merge.yml",
     swap(NUM_LINE, 'echo "number=${{ steps.pr.outputs.sha }}" >> "$GITHUB_OUTPUT"'),
     ["agent-merge.yml", "[self-reference]", "step id `pr`"]),
    ("defect 2: close-on-evidence loses pull-requests: read", "close-on-evidence.yml",
     swap("  pull-requests: read\n", ""),
     ["close-on-evidence.yml", "[permissions]", "pull-requests: read"]),
    ("defect 3: pr-gates drops ready_for_review", "pr-gates.yml",
     swap("types: [opened, synchronize, reopened, ready_for_review]",
          "types: [opened, synchronize, reopened]"),
     ["pr-gates.yml", "[trigger-types]", "ready_for_review"]),
    ("pr-gates drops `types:` entirely", "pr-gates.yml",
     swap("    types: [opened, synchronize, reopened, ready_for_review]\n", ""),
     ["pr-gates.yml", "[trigger-types]", "no explicit `types:`"]),
    ("issues: write -> read (gh issue close)", "close-on-evidence.yml",
     swap("  issues: write\n", "  issues: read\n"),
     ["close-on-evidence.yml", "[permissions]", "issues: write"]),
    ("actions: write -> read (gh workflow run)", "agent-merge.yml",
     swap("  actions: write\n", "  actions: read\n"),
     ["agent-merge.yml", "[permissions]", "actions: write"]),
    ("pull-requests: write -> read (gh pr create)", "agent-work.yml",
     swap("      pull-requests: write\n", "      pull-requests: read\n"),
     ["agent-work.yml", "[permissions]", "pull-requests: write"]),
    ("actions: read removed (gh run list/download)", "agent-prioritise.yml",
     swap("      actions: read\n", ""),
     ["agent-prioritise.yml", "[permissions]", "actions: read"]),
    ("checks: read removed (gh api .../check-runs)", "agent-merge.yml",
     swap("  checks: read\n", ""),
     ["agent-merge.yml", "[permissions]", "checks: read"]),
    ("gh with no GH_TOKEN anywhere", "close-on-evidence.yml",
     swap("      GH_TOKEN: ${{ github.token }}\n", ""),
     ["close-on-evidence.yml", "[permissions]", "cannot authenticate"]),
    ("malformed YAML is a failure, not a skip", "agent-sync.yml",
     lambda t: t + "\nbroken: [unclosed\n",
     ["agent-sync.yml", "[parse]"]),
    # Pins check 5 (#358). This is the real defect, restored verbatim: the
    # branch-name filter was `case "${{ steps.pr.outputs.branch }}" in`, so a
    # fork-chosen head ref was shell source inside the step meant to reject it.
    ("defect 5: the agent-branch filter interpolates the branch name again",
     "agent-merge.yml",
     swap('case "$PR_BRANCH" in', 'case "${{ steps.pr.outputs.branch }}" in'),
     ["agent-merge.yml", "[interpolation]", "steps.pr.outputs.branch"]),
    # The same rule on the other privileged workflow, and on an
    # `event`-derived value rather than a step output -- so the check is not
    # quietly only about `steps.*`.
    ("a workflow_run value interpolated into run: in close-on-evidence",
     "close-on-evidence.yml",
     swap("$run_link", "${{ github.event.workflow_run.html_url }}"),
     ["close-on-evidence.yml", "[interpolation]", "github.event.workflow_run.html_url"]),
    # The one the `[^}]*` form of the self-reference check already taught us
    # about: a `}` inside the expression must not end the match early.
    ("an interpolation hidden behind a format() placeholder in run:",
     "agent-merge.yml",
     swap('case "$PR_BRANCH" in',
          'case "${{ format(\'{0}\', steps.pr.outputs.branch) }}" in'),
     ["agent-merge.yml", "[interpolation]", "format("]),
    # ---- The run:-comment boundary, measured 2026-10-20 ---------------------
    # Inverted from controls. See the note in main() for what they cost.
    ("an interpolation in a WHOLE-LINE shell comment IS interpolated",
     "agent-merge.yml",
     swap('case "$PR_BRANCH" in',
          '# never write ${{ steps.pr.outputs.branch }} here\n          case "$PR_BRANCH" in'),
     ["agent-merge.yml", "[interpolation]", "steps.pr.outputs.branch"]),
    ("an interpolation in a TRAILING shell comment IS interpolated",
     "agent-merge.yml",
     swap('case "$PR_BRANCH" in',
          'case "$PR_BRANCH" in  # not ${{ steps.pr.outputs.branch }}'),
     ["agent-merge.yml", "[interpolation]", "steps.pr.outputs.branch"]),
    # The real defect, restored verbatim: the comment that explains the rule
    # used to spell an EMPTY expression, which is a syntax error, so GitHub
    # refused the file on every push for two days.
    ("an EMPTY expression in a run: block takes the whole file out of service",
     "agent-steward.yml",
     swap("so an expression in", "so a `${{ }}` in"),
     ["agent-steward.yml", "[empty-expression]"]),
    # Pins the #440 check. `workflow_run` matches a workflow's `name:`, never
    # its filename, and `workflows: ["agent-work"]` matched nothing for two
    # days while reading as wired.
    ("a workflow_run naming a workflow no file declares", "agent-steward.yml",
     swap('workflows: ["Agent work"]', 'workflows: ["agent-work"]'),
     ["agent-steward.yml", "[workflow-run-target]"]),
    # Pins the #441 check. GitHub refuses a duplicated key outright; measured on
    # a probe branch with an otherwise-valid minimal workflow, which failed.
    # `yaml.safe_load` keeps the last one silently, so nothing else here sees it.
    ("a duplicated top-level key", "agent-sync.yml",
     swap("name: Agent sync\n", "name: Agent sync\nname: Agent sync\n"),
     ["agent-sync.yml", "[duplicate-key]"]),
]


def main() -> int:
    if not REAL.is_dir() or not GATE.exists():
        print("COULD NOT RUN - gate or workflows directory missing")
        return 2
    bad: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mutate_wf_") as tmp:
        base = Path(tmp)

        print("CONTROLS")
        # Counted as they run. A literal goes stale the moment a control is
        # added — the same "one number, two places" defect #313 is about, and QA
        # found this file carrying `5 +` while six controls ran.
        n_controls = 0
        code, out = run_gate(fresh_copy(base, "control"))
        if code != 0:
            print(f"  BLIND - the untouched tree does not pass (exit {code}); results below are noise:")
            print("\n".join("    " + l for l in out.splitlines() if l.startswith("FAIL")))
            return 1
        print("  OK   untouched copy passes (exit 0)")
        n_controls += 1

        for label, new in (
            ("self-reference only in a WHOLE-LINE comment", "# steps.pr.outputs.sha\n          " + NUM_LINE),
            ("self-reference only in a TRAILING comment", NUM_LINE + "  # steps.pr.outputs.sha"),
            # Added after QA. The gate used to FAIL on this and the mutation
            # above used to REQUIRE that failure. It is a control precisely
            # because the matching mutation is the interpolated form: together
            # they pin the boundary from both sides.
            ("self-reference UNINTERPOLATED in a quoted string",
             'echo "see steps.pr.outputs.sha in a later step"\n          ' + NUM_LINE),
        ):
            d = fresh_copy(base, "ctl_" + str(abs(hash(label))))
            f = d / "agent-merge.yml"
            before = f.read_text()
            f.write_text(swap(NUM_LINE, new)(before))
            assert f.read_text() != before
            code, out = run_gate(d)
            n_controls += 1
            if code == 0:
                print(f"  OK   {label} passes (exit 0)")
            else:
                bad.append(f"control '{label}' exited {code}")
                print(f"  BAD  {label} exited {code} - false positive on prose")

        # THE TWO CONTROLS THAT USED TO LIVE HERE ARE NOW MUTATIONS, and the
        # reason is measured rather than argued. They required the gate to exit
        # 0 on `${{ ... }}` inside a shell comment in a run: block, on the
        # premise that "a gate that cannot tell a warning from an occurrence
        # would punish explaining itself". GitHub does not share that premise:
        # it substitutes into the whole run: string and has no concept of a
        # shell comment, so a commented expression is interpolated like any
        # other -- and an EMPTY one makes GitHub refuse the entire file.
        #
        # That is what took `agent-steward.yml` out of service from #438 to
        # 2026-10-20: six zero-job failed runs, the workflow listed by path
        # instead of name, no annotation on any API endpoint, and this gate
        # printing `ok ... no `${{ }}` in any run: block` throughout. These
        # controls are why it printed ok.
        #
        # So they are INVERTED, not deleted -- the same correction this file
        # already carries for check 1, which had enshrined the mirror-image
        # false positive. Three mutation rows below pin the boundary where the
        # measurement actually puts it.

        d = fresh_copy(base, "empty")
        for p in d.glob("*.yml"):
            p.unlink()
        code, _ = run_gate(d)
        # Counted because the control RAN, not because it passed. QA showed the
        # old placement shrank the denominator along with the numerator on a
        # failing run: 18 OK/BAD lines printed against a reported total of 17.
        n_controls += 1
        if code == 2:
            print("  OK   empty directory exits 2 (could not verify)")
        else:
            bad.append(f"empty dir exited {code}, expected 2")
            print(f"  BAD  empty directory exited {code}, expected 2")

        d = fresh_copy(base, "missing")
        (d / "agent-sync.yml").unlink()
        code, out = run_gate(d)
        n_controls += 1
        if code == 1 and "EXPECTED_WORKFLOWS" in out:
            print("  OK   a deleted workflow trips EXPECTED_WORKFLOWS (exit 1)")
        else:
            bad.append(f"deleted workflow: exit {code}")
            print(f"  BAD  deleted workflow exited {code}")

        print("\nMUTATIONS")
        for i, (name, fname, transform, needles) in enumerate(MUTATIONS):
            d = fresh_copy(base, f"m{i}")
            f = d / fname
            before = f.read_text()
            after = transform(before)
            if after == before:
                bad.append(f"{name}: mutation changed nothing")
                print(f"  BAD  {name}: mutation changed nothing")
                continue
            f.write_text(after)
            code, out = run_gate(d)
            hit = any(l.startswith("FAIL") and all(n in l for n in needles)
                      for l in out.splitlines())
            if code == 1 and hit:
                print(f"  OK   {name}")
            else:
                bad.append(name)
                print(f"  MISSED  {name}: exit {code}, expected exit 1 and a FAIL line "
                      f"containing {needles}")
                print("\n".join("      " + l for l in out.splitlines()[-6:]))

    total = n_controls + len(MUTATIONS)
    print(f"\n{total - len(bad)}/{total} controls+mutations behaved")
    if bad:
        print("FAIL - the gate cannot be trusted:")
        for b in bad:
            print(f"  - {b}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
