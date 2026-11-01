"""`chief-cleared` must release the trust-boundary hold, and only on THIS head (#610).

THE DEFECT THIS CLOSES. `chief.md` told chief it could clear a boundary hold by
adding `chief-cleared`, and said "the existing sweep then merges it". Nothing in
`agent-merge.yml` read that label. So a cleared PR left `detect_stalls.py`'s
report — which does read it — while this step went on holding it: the PR
disappeared from the one surface that would have said it was stuck, and stayed
stuck. Worse than either half alone.

THE SHA BINDING IS THE OTHER HALF, and it is not decoration. A label cannot say
which commit it is about. Unbound labels have cost this repo twice in one week:
#609 merged on a `qa-pass` left over from an earlier commit, and #564 sat held
by a stale `qa-fail` after the defect was fixed. So the release requires a
ruling COMMENT containing `chief-cleared at <full head sha>`, and
`test_a_ruling_on_a_DIFFERENT_commit_does_not_release` runs the step's own `jq`
expression against real comment JSON rather than stubbing the count — the
binding is what is under test, so faking its answer would prove nothing.

THESE TESTS DRIVE THE REAL `run:` BLOCK, lifted from the YAML by step id. The
block is a shell string nothing type-checks, inside a workflow that cannot be
exercised before merge: `claude-code-action` refuses to run when the workflow
differs from the default branch, so every `agent-*.yml` change in this repo
lands unproven unless a test lifts it out. The failure mode is also the worst
one available — the PR merges.

THE FAKE `gh` DISPATCHES ON ARGUMENTS, because this step makes three different
calls (`api .../files`, `pr view --json labels`, `pr view --json comments`) and
a fake that answered them all the same way would let a wrong call site pass. It
exits 9 on anything it does not recognise, so a new call added to the step
breaks these tests loudly instead of being silently stubbed.

`/tmp/pr-files.txt` AND FRIENDS ARE THE SHIPPED PATHS, not a fixture choice.
The step writes them literally and the point here is to run the step as it
ships; the suite has no xdist, so serial runs cannot collide.

NOTHING HERE SKIPS. `scripts/verify_behaviour.py` fails the suite on any skip or
xfail, by design, so a case that cannot assert must not exist.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MERGE = ROOT / ".github" / "workflows" / "agent-merge.yml"

HEAD = "bf2b17d4e7c1a09d3f6b5e8a2c4d1f0e9b8a7c6d"
OTHER = "0123456789abcdef0123456789abcdef01234567"

_DOC = yaml.safe_load(MERGE.read_text())
_JOB = _DOC["jobs"]["merge"]


def _boundary_step() -> dict:
    return next(s for s in _JOB["steps"] if s.get("id") == "boundary")


def _real_boundary() -> str:
    """The job's own TRUST_BOUNDARY, so the table under test is the shipped one.

    Hard-coding the paths here would let the two drift and this file would go
    on passing against a boundary the workflow no longer has.
    """
    return _JOB["env"]["TRUST_BOUNDARY"]


FAKE_GH = r"""#!/bin/sh
case "$1" in
  api)
    printf '%s' "$FAKE_FILES"
    ;;
  pr)
    case "$*" in
      *"--json labels"*)
        printf '%s\n' "$FAKE_LABELS" ;;
      *"--json comments"*)
        # Run the step's OWN --jq expression over the fake comment payload, so
        # the SHA match is exercised rather than stubbed. The expression is the
        # argument after --jq.
        expr=""; want=0
        for a in "$@"; do
          if [ "$want" = 1 ]; then expr="$a"; want=0; fi
          if [ "$a" = "--jq" ]; then want=1; fi
        done
        printf '%s' "$FAKE_COMMENTS" | jq -r "$expr" ;;
      *"pr comment"*|*"--add-label"*)
        echo "gh $*" >> "$GH_CALLS" ;;
      *)
        echo "UNEXPECTED gh pr call: $*" >&2; exit 9 ;;
    esac
    ;;
  *)
    echo "UNEXPECTED gh call: $*" >&2; exit 9 ;;
esac
"""


def _drive(tmp_path: Path, *, files: list[str], labels: str = "",
           comments: list[str] | None = None, sha: str = HEAD) -> tuple[int, str, str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)

    out_file = tmp_path / "gh_output"
    out_file.write_text("")
    calls = tmp_path / "gh_calls"
    calls.write_text("")

    payload = {"comments": [{"body": b} for b in (comments or [])]}
    p = subprocess.run(
        ["bash", "-e", "-c", _boundary_step()["run"]],
        capture_output=True, text=True,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "FAKE_FILES": "".join(f"{f}\n" for f in files),
            "FAKE_LABELS": labels,
            "FAKE_COMMENTS": json.dumps(payload),
            "GH_CALLS": str(calls),
            "GITHUB_OUTPUT": str(out_file),
            "GH_REPO": "mahAnuj/astro-ai",
            "PR_NUMBER": "631",
            "PR_SHA": sha,
            "TRUST_BOUNDARY": _real_boundary(),
        },
    )
    return p.returncode, p.stdout + p.stderr, out_file.read_text(), calls.read_text()


RULING = f"Shape C ruling. Gates green, qa-pass + qa:independent on record.\n\nchief-cleared at {HEAD}\n"

# ------------------------------------------------------------------ controls

def test_a_pr_touching_no_boundary_path_passes_without_any_ruling(tmp_path):
    """The control. If this released via the chief block, every case below lies."""
    rc, log, out, _ = _drive(tmp_path, files=["src/astro_ai/chart.py", "tests/test_x.py"])
    assert rc == 0, log
    assert "ok=true" in out
    assert "no protected path touched" in log
    assert "chief" not in log


def test_a_boundary_pr_with_no_labels_is_still_held(tmp_path):
    rc, log, out, calls = _drive(tmp_path, files=[".github/workflows/agent-work.yml"])
    assert rc == 0, log
    assert "ok=true" not in out, "a boundary PR with no ruling was released"
    assert "holding PR #631 for chief to rule on" in log
    assert "--add-label" in calls and "needs-human-review" in calls


# ------------------------------------------------------- the grant, working

@pytest.mark.parametrize("path", [
    ".github/workflows/agent-merge.yml",
    "src/astro_ai/prompts/natal.txt",
    "src/astro_ai/notify.py",
    "src/astro_ai/email_sender.py",
    "src/astro_ai/storage.py",
    "src/astro_ai/events.py",
    "src/astro_ai/knowledge/ashtakoota.md",
])
def test_chief_releases_the_hold_on_EVERY_boundary_path(path, tmp_path):
    """The user widened Shape C to the whole boundary on 2026-11-01.

    Parametrised over all seven entries rather than one, because the previous
    grant covered `prompts/` and `knowledge/` only and the obvious regression
    is a release block that reproduces that narrower list.
    """
    rc, log, out, _ = _drive(tmp_path, files=[path],
                             labels="qa-pass,qa:independent,chief-cleared",
                             comments=[RULING])
    assert rc == 0, log
    assert "ok=true" in out, f"chief could not clear {path}:\n{log}"
    assert f"chief ruled on {HEAD}" in log


def test_the_release_reports_which_paths_it_cleared(tmp_path):
    """A release that does not say what it released is unauditable."""
    rc, log, out, _ = _drive(
        tmp_path,
        files=[".github/workflows/agent-work.yml", "src/astro_ai/notify.py", "README.md"],
        labels="chief-cleared", comments=[RULING])
    assert "ok=true" in out, log
    assert "cleared: .github/workflows/agent-work.yml" in log
    assert "cleared: src/astro_ai/notify.py" in log
    assert "cleared: README.md" not in log, "an unprotected path was reported as cleared"


def test_a_release_posts_no_comment_and_adds_no_label(tmp_path):
    """It exits before the hold's comment-and-label block.

    Otherwise a cleared PR would be told it is held, and re-labelled
    `needs-human-review` on the way out.
    """
    _, log, out, calls = _drive(tmp_path, files=["src/astro_ai/storage.py"],
                                labels="chief-cleared", comments=[RULING])
    assert "ok=true" in out, log
    assert calls == "", f"the release path still called gh: {calls!r}"


# ------------------------------------------------- the binding, holding firm

def test_the_label_ALONE_does_not_release(tmp_path):
    """`chief-cleared` with no ruling comment is the fabrication shape.

    This repo has twice had an agent write its own authorisation and then cite
    it; the comment-before-label order is what makes a ruling checkable.
    """
    rc, log, out, calls = _drive(tmp_path, files=[".github/workflows/agent-merge.yml"],
                                 labels="qa-pass,chief-cleared", comments=[])
    assert rc == 0, log
    assert "ok=true" not in out, "a bare chief-cleared label released the hold"
    assert "no ruling comment names" in log
    assert "--add-label" in calls


def test_a_ruling_on_a_DIFFERENT_commit_does_not_release(tmp_path):
    """A clearance does not survive a push. Measured through the real `jq`.

    The fake `gh` runs the step's own `--jq` expression over the comment
    payload, so what is under test is the expression's `contains` against
    `$PR_SHA` — not a stubbed count that would pass whatever the expression said.
    """
    rc, log, out, _ = _drive(tmp_path, files=[".github/workflows/agent-merge.yml"],
                             labels="chief-cleared",
                             comments=[f"chief-cleared at {OTHER}\n"], sha=HEAD)
    assert rc == 0, log
    assert "ok=true" not in out, "a ruling bound to another commit released this one"
    assert f"no ruling comment names" in log


def test_a_ruling_among_several_comments_is_found(tmp_path):
    """The real PR has gate chatter above and below the ruling."""
    rc, _, out, _ = _drive(
        tmp_path, files=["src/astro_ai/prompts/natal.txt"], labels="chief-cleared",
        comments=["qa-on-green: dispatched at " + OTHER, RULING, "verify-production: green"])
    assert "ok=true" in out


def test_a_truncated_file_list_is_held_even_with_no_protected_path(tmp_path):
    """The cap means the diff could not be fully read.

    `chief.md` answers this case directly — *"an unreadable diff is still yours
    to answer"*, and `insufficient-evidence` is the right ruling — so it must
    reach the chief block rather than passing as "nothing protected".
    """
    rc, log, out, _ = _drive(tmp_path, files=[f"src/f{i}.py" for i in range(3000)])
    assert rc == 0, log
    assert "ok=true" not in out, "a capped file list passed as clean"
    assert "holding PR #631" in log


def test_chief_can_rule_on_a_truncated_file_list(tmp_path):
    rc, log, out, _ = _drive(tmp_path, files=[f"src/f{i}.py" for i in range(3000)],
                             labels="chief-cleared", comments=[RULING])
    assert rc == 0, log
    assert "ok=true" in out, log


# --------------------------------------------------- failing toward the hold

@pytest.mark.parametrize("hiccup", ["", "null", "error: not found", "   ", "3 comments"])
def test_a_NON_NUMERIC_comment_count_keeps_the_hold(hiccup, tmp_path, monkeypatch):
    """An API hiccup must fall toward holding, not releasing.

    This is the defect class this session has been cataloguing: a guard whose
    input can be legitimately empty, failing silently toward permissive. Here
    `[ "$ruled" -gt 0 ]` on an empty string is a bash syntax error under `-e`,
    which would abort the step — and an aborted step with `ok` unset holds, but
    reports nothing. The `case` normalises first so the hold is deliberate.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        '#!/bin/sh\n'
        'case "$1" in\n'
        '  api) printf "%s" "$FAKE_FILES" ;;\n'
        '  pr) case "$*" in\n'
        '        *"--json labels"*) printf "%s\\n" "$FAKE_LABELS" ;;\n'
        '        *"--json comments"*) printf "%s\\n" "$HICCUP" ;;\n'
        '        *) echo "gh $*" >> "$GH_CALLS" ;;\n'
        '      esac ;;\n'
        '  *) exit 9 ;;\n'
        'esac\n')
    gh.chmod(0o755)
    out_file = tmp_path / "gh_output"
    out_file.write_text("")
    calls = tmp_path / "gh_calls"
    calls.write_text("")
    p = subprocess.run(
        ["bash", "-e", "-c", _boundary_step()["run"]],
        capture_output=True, text=True,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin",
             "FAKE_FILES": ".github/workflows/agent-merge.yml\n",
             "FAKE_LABELS": "chief-cleared",
             "HICCUP": hiccup,
             "GH_CALLS": str(calls),
             "GITHUB_OUTPUT": str(out_file),
             "GH_REPO": "mahAnuj/astro-ai", "PR_NUMBER": "631", "PR_SHA": HEAD,
             "TRUST_BOUNDARY": _real_boundary()},
    )
    assert "ok=true" not in out_file.read_text(), (
        f"a comment count of {hiccup!r} released the hold")
    assert p.returncode == 0, p.stdout + p.stderr


# ---------------------------------------------------------- the file's prose

def test_the_hold_comment_tells_the_reader_about_the_chief_route():
    """The hold text used to say only "merge by hand".

    Prose that names one route when two exist is how a repo keeps routing work
    to a person after the machine route was built — which is the whole of #610.
    """
    run = _boundary_step()["run"]
    # The chief route by name, FIRST and numbered. The mutation harness found
    # the earlier version of this test mis-pointed: its row's mutant replaced
    # `chief` with `Someone` in this very line and the test went on passing,
    # because it asserted the SHA phrasing and the human route and never the
    # one thing its name promises.
    assert "\\`chief\\` rules on it" in run, (
        "the hold comment no longer names chief as the first route")
    assert "chief-cleared at $PR_SHA" in run
    assert "A human reviews and merges by hand" in run
    assert "Removing \\`needs-human-review\\` on its own does not release anything" in run


def test_the_release_block_sits_AFTER_the_gate_chain_steps():
    """chief clears a hold, not a verdict.

    If the boundary step ever stopped depending on `size`, a ruling would be
    reachable without `gates` and `qa` having passed — which would make chief a
    hole in `pr-gates` rather than merge authority. `verify_no_relaxation.py`
    rule 5 guards the chain; this asserts THIS step is on it.
    """
    assert _boundary_step()["if"] == "steps.size.outputs.ok == 'true'"
