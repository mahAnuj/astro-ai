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
    assert "== 'failure'" not in cond, (
        f"the `if:` is {cond!r}, which tests for `failure` and so reports "
        "nothing for `cancelled` or `timed_out` -- the exact defect QA failed "
        "round 1 on."
    )
    # `skipped` is the ONE excluded conclusion: nothing ran, so nothing is
    # asserted. Everything else reaches the step, including a conclusion GitHub
    # has not shipped yet, because the bug class here is silent non-reporting.
    assert "!= 'skipped'" in cond, (
        f"the `if:` is {cond!r}; `skipped` must be excluded explicitly, so that "
        "excluding it is a decision on the record rather than a side effect"
    )
    # `success` must NOT be excluded -- the green path is what closes the
    # sentinel, and round 2 excluding it is why nothing kept the promise the
    # sentinel body makes.
    assert "!= 'success'" not in cond, (
        f"the `if:` is {cond!r}; excluding `success` means no green push ever "
        "closes the sentinel, so a stale one stays open and the next unrelated "
        "red `main` appends to it and conflates two incidents."
    )


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out",
                                        "action_required", "stale", "neutral"])
def test_every_non_green_conclusion_reports(tmp_path, conclusion):
    """Behavioural companion to the assertion above: the step itself must file
    for each of these, not merely be reachable."""
    proc, done = _run_reporter(
        tmp_path, {"open_issues": [], "comments": {}},
        sha="abcdef1234567", conclusion=conclusion,
    )
    assert proc.returncode == 0, proc.stderr
    assert [a["kind"] for a in done] == ["create"], f"{conclusion}: {done!r}"
    assert conclusion in done[0]["body"]


# --------------------------------------------------------------------------
# The green path -- the sentinel body promises this, so something must do it
# --------------------------------------------------------------------------

def test_a_green_main_closes_the_open_sentinel(tmp_path):
    """QA BUG-2: the body said "stays open until a push to `main` goes green"
    and nothing closed it, so a stale sentinel collected the NEXT, unrelated
    red `main` and conflated two incidents."""
    proc, done = _run_reporter(
        tmp_path,
        {"open_issues": [
            {"number": 900, "title": "[main-red] pr-gates did not pass on main at 1111111"},
            {"number": 461, "title": ISSUE_461_TITLE},
        ], "comments": {"900": ["Still red on `main` at `1111111`"]}},
        sha="9999999abcdef", conclusion="success",
    )
    assert proc.returncode == 0, proc.stderr
    assert [a["kind"] for a in done] == ["comment", "close"], f"{done!r}"
    assert all(a["number"] == 900 for a in done), (
        f"a green main touched something other than the sentinel: {done!r}"
    )


def test_every_open_sentinel_is_closed_not_just_the_first(tmp_path):
    """Two can exist if the 500-cap warning ever fires. Leaving one behind is
    the same stale-sentinel bug one level down."""
    proc, done = _run_reporter(
        tmp_path,
        {"open_issues": [
            {"number": 900, "title": "[main-red] pr-gates did not pass on main at 1111111"},
            {"number": 901, "title": "[main-red] pr-gates did not pass on main at 3333333"},
        ], "comments": {}},
        sha="9999999abcdef", conclusion="success",
    )
    assert proc.returncode == 0, proc.stderr
    assert sorted({a["number"] for a in done}) == [900, 901], f"{done!r}"
    assert sorted(a["kind"] for a in done) == ["close", "close", "comment", "comment"]


def test_a_green_main_with_no_sentinel_does_nothing(tmp_path):
    """The common case: every merge fires this, and it must be a quiet no-op."""
    proc, done = _run_reporter(
        tmp_path,
        {"open_issues": [{"number": 461, "title": ISSUE_461_TITLE}], "comments": {}},
        sha="9999999abcdef", conclusion="success",
    )
    assert proc.returncode == 0, proc.stderr
    assert done == [], f"a green main with no sentinel acted: {done!r}"


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
import json, os, re, subprocess, sys

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
elif argv[0] == "api" and "/jobs" in argv[1]:
    # The reporter asks whether `pr-gates`' "GATES ASSERTED" step ran, because
    # a run conclusion of `success` does NOT mean the gates executed -- every
    # gate step is scope-gated, so a docs-only push skips them all and still
    # concludes success. The fixture decides what the step says; default
    # `success`, so every pre-existing test keeps its old meaning.
    state = fixture.get("asserted", "success")
    steps = [{"name": "Verification gates", "conclusion": "success"}]
    if state != "absent":
        steps.append({"name": "GATES ASSERTED", "conclusion": state})
    if "--jq" in argv:
        payload = {"jobs": [{"steps": steps}]}
        expr = argv[argv.index("--jq") + 1]
        r = subprocess.run(("jq", "-r", expr), input=json.dumps(payload),
                           capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        sys.exit(r.returncode)
    sys.exit(0)
elif argv[:2] == ["issue", "view"]:
    number = int(argv[2])
    # Honour the `--json` field list, because WHICH fields are asked for is
    # exactly what the dedup got wrong: the SHA of the commit that CREATED the
    # sentinel lives in `body`, never in `comments`. A fake that always served
    # both would hide the defect; a fake that always served only comments would
    # make the fix untestable.
    fields = argv[argv.index("--json") + 1].split(",") if "--json" in argv else []
    payload = {}
    if "body" in fields:
        payload["body"] = fixture.get("body", {}).get(str(number), "")
    if "comments" in fields:
        payload["comments"] = [{"body": b}
                               for b in fixture.get("comments", {}).get(str(number), [])]
    # HONOUR `--jq`, by shelling out to the real jq (#461 round 4, BUG-3).
    # The previous fake parsed `--json` and ignored `--jq`, so the tests pinned
    # WHICH fields were requested and nothing about what was done with them.
    # Mutating the jq expression alone -- `[.body] + [.comments[].body]` back to
    # `.comments[].body`, which is exactly round 3's defect -- left all 26 tests
    # green. The harness already requires jq, so there is nothing new to install.
    if "--jq" in argv:
        expr = argv[argv.index("--jq") + 1]
        r = subprocess.run(("jq", "-r", expr), input=json.dumps(payload),
                           capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        sys.exit(r.returncode)
    print(json.dumps(payload))
elif argv[:2] == ["issue", "comment"]:
    path = argv[argv.index("--body-file") + 1]
    record("comment", number=int(argv[2]), body=open(path).read())
elif argv[:2] == ["issue", "close"]:
    record("close", number=int(argv[2]))
elif argv[:2] == ["issue", "create"]:
    path = argv[argv.index("--body-file") + 1]
    title = argv[argv.index("--title") + 1]
    record("create", title=title, body=open(path).read())
else:
    sys.stderr.write("fake gh: unhandled %r\n" % (argv,))
    sys.exit(97)
'''


def _run_reporter(tmp_path, fixture: dict, sha: str, conclusion: str = "cancelled"):
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
        RUN_ID="1",
        CONCLUSION=conclusion,
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


def test_the_dedup_survives_a_large_comment_thread(tmp_path):
    """QA BUG-1, and the reason `test_the_same_sha_is_not_reported_twice` above
    was not enough on its own.

    The dedup was `gh issue view ... | grep -qF -- "\\`$short\\`"`. `grep -q`
    exits at the FIRST match; under `set -o pipefail` the upstream `gh` then
    dies of SIGPIPE and the PIPELINE reports 141, not 0 -- so the `if` took the
    false branch and posted a SECOND comment for a SHA already recorded.

    MEASURED, with no fake `gh` involved at all:

        { printf 'match-here\\n'; yes filler | head -60000; } > big.txt
        bash -c 'set -euo pipefail
                 if cat big.txt | grep -qF -- match-here; then echo OK
                 else echo "FAILED rc=$?"; fi'
        -> FAILED rc=141          # and rc=0 on a one-line file

    That is why the small-fixture test passed while the real thing would have
    broken on any thread carrying ~64 KB of comments after the match: roughly
    280 auto-comments, or one pasted CI log. The fixture here is deliberately
    ~200 KB so it crosses the pipe buffer.
    """
    filler = "x" * 100
    comments = ["Still red on `main` at `2222222` — **cancelled**"] + \
               [f"{filler} {n}" for n in range(2000)]
    proc, done = _run_reporter(
        tmp_path,
        {"open_issues": [
            {"number": 900, "title": "[main-red] pr-gates did not pass on main at 1111111"}
        ], "comments": {"900": comments}},
        sha="2222222abcdef",
    )
    assert proc.returncode == 0, proc.stderr
    assert done == [], (
        "the same SHA was reported twice on a large thread. `grep -q` + "
        f"`pipefail` makes the pipeline 141 at the first match: {done!r}"
    )


def test_the_sha_that_opened_the_sentinel_is_not_reported_twice(tmp_path):
    """QA round 3, BUG-3. The dedup read `--json comments` only.

    The FIRST red commit of a stretch has its SHA in the issue's TITLE and
    BODY — it was never a comment — so that one commit was invisible to the
    dedup, and a re-run of pr-gates for it appended a duplicate report of a SHA
    already on the issue. The script promises "a re-run of this workflow must
    not append the same SHA twice", and that promise was false for precisely
    the commit that opens every red stretch.

    `test_the_same_sha_is_not_reported_twice` and
    `test_the_dedup_survives_a_large_comment_thread` both seed the SHA as a
    COMMENT, which is the second-and-later case. Neither could see this.
    """
    proc, done = _run_reporter(
        tmp_path,
        {
            "open_issues": [
                {"number": 900,
                 "title": "[main-red] pr-gates did not pass on main at 2222222"}
            ],
            "body": {"900": "`main` is red. `pr-gates` runs on pushes to `main` "
                            "(#461) and did not pass at `2222222` — **cancelled**"},
            "comments": {"900": []},
        },
        sha="2222222abcdef",
    )
    assert proc.returncode == 0, proc.stderr
    assert done == [], (
        "the sentinel's own creating SHA was reported a second time; the dedup "
        f"must read the issue body, not comments alone: {done!r}"
    )


def test_no_pipeline_feeds_an_early_exiting_reader():
    """The class behind two separate defects on this PR, pinned structurally.

    Under `set -o pipefail`, a reader that exits before consuming its input
    (`grep -q`, `head`) makes the upstream die of SIGPIPE and the PIPELINE
    report 141. Round 2 found it on `gh issue view | grep -qF` (a duplicate
    comment); round 3 found it latent on `printf | head -n 1` (measured to fire
    at 20,000 lines, where it would kill the step and leave a red `main`
    unreported).

    Both were invisible to behavioural tests until the input crossed the 64 KB
    pipe buffer, so this asserts on the shape instead. Capture into a variable
    and use a herestring or parameter expansion.
    """
    # EVERY `run:` block in both workflows, not just the reporter's (#461
    # round 4, BUG-5). Scanning the reporter alone left `pr-gates.yml` --
    # which THIS PR newly runs on `main` -- unscanned, and it contains
    # `echo "$changed" | grep -qE ...` in the scope step. That one is not
    # reachable today (the largest `main` commit's file list measured 847
    # bytes against a 64 KB pipe buffer) but it is the same class, in a file
    # this change touches, invisible to the test that exists for the class.
    RX = re.compile(
        r"\|\s*(head\b|read\b|grep\b[^|]*?\s-[a-zA-Z]*(?:q|m\s*1)[a-zA-Z]*\b"
        r"|sed\b[^|]*\bq[;'\"]?)"
    )
    offenders = []
    for wf in ("main-red-report.yml", "pr-gates.yml"):
        doc = yaml.safe_load((WF_DIR / wf).read_text())
        for job_name, job in (doc.get("jobs") or {}).items():
            for step in job.get("steps") or []:
                for line in (step.get("run") or "").splitlines():
                    if line.lstrip().startswith("#"):
                        continue
                    if RX.search(line):
                        offenders.append(
                            f"{wf}  job={job_name}  step={step.get('name')!r}\n"
                            f"      {line.strip()}")
    assert offenders == [], (
        "a pipeline feeds a reader that exits early; under `pipefail` the "
        "upstream dies of SIGPIPE and the pipeline reports 141 — and it only "
        "manifests past the 64 KB pipe buffer, so a small-fixture test will "
        "not catch it:\n  " + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# #461 round 4, BUG-1: a run that asserted nothing must not be judged.
#
# Every gate step in `pr-gates.yml` is `if: steps.scope.outputs.code ==
# 'true'`, so a docs- or measurements-only push skips all of them and the job
# still concludes `success`. Measured 2026-10-31: 26 of the last 40 commits on
# `main` were that shape. The reporter used to CLOSE the sentinel on those and
# comment "`pr-gates` passed on the merge result", which is false.
# ---------------------------------------------------------------------------

def test_a_green_run_that_skipped_every_gate_does_not_close_the_sentinel(tmp_path):
    """The blocker. A docs-only push concludes `success` and asserts nothing."""
    fixture = {
        "open_issues": [{"number": 700, "title": "[main-red] main is red at deadbee"}],
        "body": {"700": "`deadbee` — **failure**"},
        "comments": {},
        "asserted": "skipped",          # the gates were scope-skipped
    }
    proc, done = _run_reporter(tmp_path, fixture, sha="cafebabe123", conclusion="success")
    assert proc.returncode == 0, proc.stderr
    assert done == [], (
        "a run that executed no gate closed the sentinel — the exact defect "
        f"round 4 found; actions taken: {done}"
    )
    assert "nothing was asserted" in proc.stdout


def test_a_red_run_reports_even_though_the_marker_reads_skipped(tmp_path):
    """THE INVERSION. This test previously asserted the bug.

    It paired `asserted="skipped"` with `conclusion="failure"` and demanded
    silence — but that pairing is exactly a real failing gates run, because an
    `if:` with no status-check function carries an implicit `success()` and so
    the marker is `skipped` whenever an earlier step failed. Measured on run
    41097631280: steps 14, 15 and 16 share the marker's `if:` and all read
    `skipped` on a `failure` run.

    So the suite was pinning "a red `main` reports nothing", which is the
    opposite of what this workflow is for.
    """
    fixture = {"open_issues": [], "comments": {}, "asserted": "skipped"}
    proc, done = _run_reporter(tmp_path, fixture, sha="cafebabe123", conclusion="failure")
    assert proc.returncode == 0, proc.stderr
    assert done, (
        "a red `main` filed nothing — the marker must gate only the GREEN "
        "path, because on a red run it always reads `skipped`"
    )
    assert done[0]["kind"] == "create"


@pytest.mark.parametrize(
    "conclusion,marker,want_action,why",
    [
        # A non-green conclusion IS the verdict. The marker is irrelevant to it
        # and, on a real red run, always reads `skipped` or `absent`.
        ("failure",   "skipped",    True,  "a failing gate must reach a person"),
        ("failure",   "absent",     True,  "a job that never started is still red"),
        ("failure",   "unreadable", True,  "an unreadable jobs API must not silence a red run"),
        ("cancelled", "skipped",    True,  "the killed-job case this file exists for"),
        ("cancelled", "absent",     True,  "pending-cancelled: the API returns steps: []"),
        ("timed_out", "skipped",    True,  "a timeout is the other half of that case"),
        # Green is the only path the marker disambiguates.
        ("success",   "success",    True,  "a real green closes the sentinel"),
        ("success",   "skipped",    False, "green but no gate ran: round 4's defect"),
        ("success",   "unreadable", False, "green and unverifiable: decline to close"),
    ],
)
def test_the_marker_gates_only_the_green_path(tmp_path, conclusion, marker, want_action, why):
    """A (conclusion x marker) MATRIX, because testing one axis at a time is
    precisely how the inversion above shipped: every single-axis test passed."""
    fixture = {
        "open_issues": [{"number": 700, "title": "[main-red] main is red at deadbee"}],
        "body": {"700": "`deadbee` — **failure**"},
        "comments": {},
        "asserted": marker,
    }
    proc, done = _run_reporter(tmp_path, fixture, sha="cafebabe123", conclusion=conclusion)
    assert proc.returncode == 0, f"{why}\n{proc.stdout}\n{proc.stderr}"
    assert bool(done) is want_action, (
        f"{conclusion} + marker {marker}: expected "
        f"{'an action' if want_action else 'silence'}, got {done}\n{why}"
    )


def test_a_green_run_with_a_missing_marker_fails_loudly(tmp_path):
    """Drift is fatal on the green path only — where the marker is the only
    thing standing between a scope-skipped run and a false close."""
    fixture = {"open_issues": [], "comments": {}, "asserted": "absent"}
    proc, done = _run_reporter(tmp_path, fixture, sha="cafebabe123", conclusion="success")
    assert proc.returncode == 1, f"drift was tolerated on a green run:\n{proc.stdout}"
    assert done == []
    assert "drifted apart" in proc.stdout


def test_a_run_whose_gates_really_ran_is_still_judged(tmp_path):
    """The control. Without this the test above passes on a reporter that does
    nothing at all, which would be a far worse bug than the one it pins."""
    fixture = {"open_issues": [], "comments": {}, "asserted": "success"}
    proc, done = _run_reporter(tmp_path, fixture, sha="cafebabe123", conclusion="failure")
    assert proc.returncode == 0, proc.stderr
    assert done, "a run whose gates DID execute was not reported at all"
    assert done[0]["kind"] == "create"


def test_pr_gates_carries_the_step_the_reporter_reads(tmp_path):
    """The other half of the coupling: the two files must agree on the name.

    The reporter failing loudly is only useful if someone notices; this fails
    at PR time instead.
    """
    import yaml
    wf = yaml.safe_load((WF_DIR / "pr-gates.yml").read_text())
    steps = wf["jobs"]["gates"]["steps"]
    marker = [s for s in steps if s.get("name") == "GATES ASSERTED"]
    assert len(marker) == 1, (
        "pr-gates.yml has no 'GATES ASSERTED' step; main-red-report.yml reads "
        "it by name to tell a real green from a scope-skipped one"
    )
    assert "steps.scope.outputs.code" in marker[0].get("if", ""), (
        "the marker must be gated on the same condition as the gates it "
        f"stands for; got: {marker[0].get('if')!r}"
    )


def test_the_reporter_is_serialised():
    """The sentinel lookup is read-then-write with no lock (#461 round 4).

    Two reporters that both read "no sentinel open" both file one. QA round 5
    deleted this block and all 65 tests stayed green, so it is pinned here:
    the fix was correct and unprotected.
    """
    doc = yaml.safe_load((WF_DIR / "main-red-report.yml").read_text())
    conc = doc.get("concurrency")
    assert conc, (
        "main-red-report.yml has no concurrency group; it is the only "
        "state-mutating workflow_run listener without one, and its sentinel "
        "lookup is read-then-write"
    )
    assert conc.get("cancel-in-progress") is False, (
        "cancel-in-progress must be false for agent-merge's reason: "
        f"cancelling the thing that reports a kill is the worst outcome; got {conc}"
    )
