"""A red `main` must reach a person, and the reporter must survive a killed job.

#461 round 1 put the reporter INSIDE `pr-gates`' `gates` job, guarded by
`if: failure() && ...`. Independent QA failed it on three findings, all three
verified here rather than described:

  1. `failure()` is FALSE when a job is killed rather than failing -- a job over
     `timeout-minutes`, or one cancelled by hand or by concurrency, ends
     `cancelled`. Those are the likeliest shapes of a red `main`, and the
     reporter did not run for any of them. A reporter inside the job it reports
     on is also reporting on its own executioner.
  2. The sentinel was found with `gh issue list --search '"[main-red]" in:title'`.
     GitHub's search tokenizer strips `[`, `]` and `-`, so that degrades to the
     words `main red` and matched #461 ITSELF -- the issue the work closes. The
     first red `main` would have commented there and never filed a sentinel.
  3. The file header 57 lines above still read "Pull requests ONLY".

Findings 1 and 2 are behavioural and are driven here against the REAL shell
extracted from the workflow, with a fake `gh`. Reading the YAML and agreeing
with it is what let finding 2 ship: the quoting in that `--search` call looks
exact, and nothing at the call site hints that GitHub rewrites it.
"""

import json
import os
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

WF_DIR = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows"
REPORTER = WF_DIR / "main-red-report.yml"
GATES = WF_DIR / "pr-gates.yml"

#: #461's real title, as `gh issue view 461 --json title` returned it on
#: 2026-10-28. It is the exact string the broken `--search` matched, so it is
#: the only honest fixture for finding 2.
ISSUE_461_TITLE = (
    "pr-gates never runs on main, so a red main is invisible — two "
    "independently-green PRs made main red for a day and nothing reported it"
)


def _doc(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _on(path: pathlib.Path) -> dict:
    """The `on:` block. YAML 1.1 reads the bare key `on` as the boolean True,
    which is why this is looked up by string rather than subscripted."""
    doc = _doc(path)
    key = next(k for k in doc if str(k) in ("on", "True"))
    return doc[key]


def _reporter_script() -> str:
    step = _doc(REPORTER)["jobs"]["report"]["steps"][0]
    return step["run"]


# --------------------------------------------------------------------------
# Finding 1 -- the reporter must not live inside the job it reports on
# --------------------------------------------------------------------------

def test_the_reporter_is_a_separate_workflow_run_listener():
    assert REPORTER.is_file(), (
        "main-red-report.yml is gone. A reporter step inside pr-gates cannot "
        "report pr-gates being killed, which is QA finding 1 on #461."
    )
    wr = _on(REPORTER).get("workflow_run")
    assert wr, "the reporter must trigger on `workflow_run`, not on `push`"
    assert "PR gates" in (wr.get("workflows") or []), (
        f"`workflows:` is {wr.get('workflows')!r}; it must name `PR gates`, the "
        "`name:` of pr-gates.yml, or the reporter never fires"
    )
    assert "completed" in (wr.get("types") or []), (
        f"`types:` is {wr.get('types')!r}; `completed` is the only type that "
        "fires for a run that ended `cancelled` or `timed_out`"
    )


def test_pr_gates_has_no_reporter_step_and_cannot_write_issues():
    text = GATES.read_text(encoding="utf-8")
    assert "Report a red main" not in text, (
        "the reporter step is back inside pr-gates. `failure()` is false when "
        "the job is cancelled or timed out, so it cannot report the two "
        "likeliest red shapes (QA finding 1 on #461)."
    )
    perms = _doc(GATES).get("permissions") or {}
    assert "issues" not in perms, (
        f"pr-gates permissions are {perms!r}. It no longer files anything, so "
        "`issues: write` is authority it does not need -- a gate's token should "
        "be the smallest that lets it assert."
    )


def test_the_reporter_fires_on_cancelled_and_timed_out_not_only_on_failure():
    cond = _doc(REPORTER)["jobs"]["report"]["if"]
    assert "conclusion != 'success'" in cond, (
        f"the `if:` is {cond!r}. It must exclude conclusions rather than name "
        "`failure`: a job over `timeout-minutes`, or cancelled by hand or by "
        "concurrency, ends `cancelled` and is still a red `main` (QA finding 1)."
    )
    assert "== 'failure'" not in cond, (
        f"the `if:` is {cond!r}, which tests for `failure` and so reports "
        "nothing for `cancelled` or `timed_out` -- the exact defect QA failed "
        "round 1 on."
    )
    # `skipped` is the one non-success conclusion that asserts nothing, so it is
    # the one documented exclusion. Anything else -- including a conclusion
    # GitHub has not shipped yet -- must report, because the bug class here is
    # silent non-reporting.
    assert "!= 'skipped'" in cond, (
        f"the `if:` is {cond!r}; `skipped` must be excluded explicitly, so that "
        "excluding it is a decision on the record rather than a side effect"
    )


# --------------------------------------------------------------------------
# Finding 2 -- the sentinel lookup, driven for real
# --------------------------------------------------------------------------

FAKE_GH = r'''#!/usr/bin/env python3
"""A `gh` that answers from $FIXTURE and appends every write to $ACTIONS.

IT EMULATES GITHUB'S TITLE SEARCH TOKENIZER, deliberately. The round-1 bug was
`--search '"[main-red]" in:title'` matching #461, and a fake that merely IGNORED
`--search` would "catch" a revert to it for the wrong reason: `$existing` would
be handed the whole JSON array, `int()` would raise, and the step would die of a
crash instead of being shown to comment on the wrong issue. That was measured --
the mutation row for this went CAUGHT with a `ValueError` and said nothing about
tokenization -- so the tokenizer is modelled here and the row is caught because
the reporter visibly comments on #461.

The model: GitHub splits a title on non-alphanumerics and requires every term in
the query to be present. `[`, `]` and `-` are therefore not matchable at all,
which is the whole defect.
"""
import json, os, re, sys

argv = sys.argv[1:]
fixture = json.load(open(os.environ["FIXTURE"]))
actions = os.environ["ACTIONS"]


def record(kind, **kw):
    with open(actions, "a") as fh:
        fh.write(json.dumps({"kind": kind, **kw}) + "\n")


def terms(s):
    return [t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t]


if argv[:2] == ["issue", "list"]:
    issues = fixture["open_issues"]
    if "--search" in argv:
        query = argv[argv.index("--search") + 1].replace("in:title", "")
        wanted = terms(query)
        issues = [i for i in issues
                  if all(w in terms(i["title"]) for w in wanted)]
        # The round-1 call paired `--search` with
        # `--json number --jq '.[0].number // empty'`, i.e. one bare number.
        print(issues[0]["number"] if issues else "")
        sys.exit(0)
    print(json.dumps(issues))
elif argv[:2] == ["issue", "view"]:
    number = int(argv[2])
    bodies = fixture.get("comments", {}).get(str(number), [])
    # The real call is `--json comments --jq '.comments[].body'`, which prints
    # one body per line.
    for b in bodies:
        print(b)
elif argv[:2] == ["issue", "comment"]:
    path = argv[argv.index("--body-file") + 1]
    record("comment", number=int(argv[2]), body=open(path).read())
elif argv[:2] == ["issue", "create"]:
    path = argv[argv.index("--body-file") + 1]
    title = argv[argv.index("--title") + 1]
    record("create", title=title, body=open(path).read())
else:
    sys.stderr.write("fake gh: unhandled %r\n" % (argv,))
    sys.exit(97)
'''


def _run_reporter(tmp_path, fixture: dict, sha: str):
    """Execute the workflow's own shell with a fake `gh` and real `jq`."""
    if shutil.which("jq") is None:                      # pragma: no cover
        pytest.skip("the reporter's sentinel filter is jq; no jq on this box")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(0o755)

    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    actions = tmp_path / "actions.jsonl"
    actions.touch()
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()

    script = tmp_path / "step.sh"
    script.write_text(_reporter_script(), encoding="utf-8")

    env = dict(os.environ)
    env.update(
        PATH=f"{bin_dir}:{env['PATH']}",
        FIXTURE=str(fixture_path),
        ACTIONS=str(actions),
        RUNNER_TEMP=str(runner_temp),
        GH_TOKEN="fake",
        GH_REPO="mahAnuj/astro-ai",
        SHA=sha,
        RUN_URL="https://example.invalid/run/1",
        CONCLUSION="cancelled",
    )
    proc = subprocess.run(
        ["bash", str(script)], env=env, capture_output=True, text=True, cwd=tmp_path
    )
    done = [json.loads(l) for l in actions.read_text().splitlines() if l.strip()]
    return proc, done


def test_the_sentinel_lookup_does_not_match_the_issue_it_closes(tmp_path):
    """THE round-1 defect. #461 is open, no sentinel exists -> file a sentinel.

    The broken `--search '"[main-red]" in:title'` returned #461 against the real
    repo on 2026-10-28, so round 1 would have commented on the issue it closes
    and never filed a sentinel at all.
    """
    proc, done = _run_reporter(
        tmp_path,
        {"open_issues": [{"number": 461, "title": ISSUE_461_TITLE}], "comments": {}},
        sha="deadbeefcafe",
    )
    assert proc.returncode == 0, proc.stderr
    assert [a["kind"] for a in done] == ["create"], (
        f"expected one new sentinel issue, got {done!r}. #461's title holds both "
        "'main' and 'red', which is all the stripped search ever matched on."
    )
    assert done[0]["title"].startswith("[main-red] ")
    assert "deadbee" in done[0]["body"]


def test_a_title_holding_main_and_red_is_not_mistaken_for_the_sentinel(tmp_path):
    """Generalises the above: only the literal `[main-red] ` prefix counts."""
    decoys = [
        {"number": 1, "title": "main is red again"},
        {"number": 2, "title": "red main: investigate"},
        {"number": 3, "title": "a main-red summary of the week"},
        {"number": 4, "title": "[main-red]no space after the prefix"},
    ]
    proc, done = _run_reporter(
        tmp_path, {"open_issues": decoys, "comments": {}}, sha="0123456789ab"
    )
    assert proc.returncode == 0, proc.stderr
    assert [a["kind"] for a in done] == ["create"], (
        f"a decoy title was taken for the sentinel: {done!r}"
    )


def test_an_existing_sentinel_is_commented_on_not_duplicated(tmp_path):
    proc, done = _run_reporter(
        tmp_path,
        {
            "open_issues": [
                {"number": 461, "title": ISSUE_461_TITLE},
                {"number": 900, "title": "[main-red] pr-gates did not pass on main at 1111111"},
            ],
            "comments": {"900": ["Still red on `main` at `1111111` — **failure**"]},
        },
        sha="2222222abcdef",
    )
    assert proc.returncode == 0, proc.stderr
    assert [a["kind"] for a in done] == ["comment"], f"{done!r}"
    assert done[0]["number"] == 900, (
        f"commented on #{done[0]['number']}; the sentinel is #900 and #461 is a decoy"
    )
    assert "2222222" in done[0]["body"]


def test_the_same_sha_is_not_reported_twice(tmp_path):
    """A re-run of the reporter must be idempotent: `main` red over six commits
    is one situation, not six, and the same commit is not two."""
    proc, done = _run_reporter(
        tmp_path,
        {
            "open_issues": [
                {"number": 900, "title": "[main-red] pr-gates did not pass on main at 1111111"}
            ],
            "comments": {"900": ["Still red on `main` at `2222222` — **cancelled**"]},
        },
        sha="2222222abcdef",
    )
    assert proc.returncode == 0, proc.stderr
    assert done == [], f"the same SHA was reported a second time: {done!r}"


def test_a_bare_hex_run_in_the_thread_does_not_suppress_a_report(tmp_path):
    """The dedup match includes the backticks. A seven-hex substring loose in
    some unrelated comment must not silence a real red commit."""
    proc, done = _run_reporter(
        tmp_path,
        {
            "open_issues": [
                {"number": 900, "title": "[main-red] pr-gates did not pass on main at 1111111"}
            ],
            "comments": {"900": ["unrelated prose mentioning 2222222 with no backticks"]},
        },
        sha="2222222abcdef",
    )
    assert proc.returncode == 0, proc.stderr
    assert [a["kind"] for a in done] == ["comment"], (
        f"a bare hex run suppressed a real report: {done!r}"
    )


def test_the_conclusion_reaches_the_reported_body(tmp_path):
    """`cancelled` vs `failure` is the distinction round 1 could not make, so
    the report has to name which one it was."""
    proc, done = _run_reporter(
        tmp_path, {"open_issues": [], "comments": {}}, sha="abcdef1234567"
    )
    assert proc.returncode == 0, proc.stderr
    assert "cancelled" in done[0]["body"], (
        f"the body does not say which conclusion it is reporting:\n{done[0]['body']}"
    )


def test_the_truncation_cap_announces_itself(tmp_path):
    """A truncated open-issue list would silently file a DUPLICATE sentinel, so
    the cap has to warn rather than degrade quietly."""
    many = [{"number": n, "title": f"filler {n}"} for n in range(500)]
    proc, done = _run_reporter(
        tmp_path, {"open_issues": many, "comments": {}}, sha="feedface1234"
    )
    assert proc.returncode == 0, proc.stderr
    assert "::warning::" in proc.stdout, (
        "the 500-issue cap was hit and said nothing; the next red commit would "
        f"file a second sentinel.\n{proc.stdout}"
    )


def test_no_interpolation_reaches_the_reporter_shell():
    """`workflow_run` is a privileged trigger: the base definition runs with a
    write token (#358). verify_workflows enforces this repo-wide; this pins it
    for the one file where a value from the triggering run is in scope."""
    assert not re.search(r"\$\{\{", _reporter_script()), (
        "a `${{ }}` appeared inside the reporter's run: block. Values must "
        "arrive as environment variables, which bash never re-parses as source."
    )
