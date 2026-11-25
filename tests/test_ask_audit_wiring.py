"""The weekly /ask answer audit never publishes a user's words (#1167).

Owner's decision on #1167, verbatim: "Yes and a for 1st question" -- run the
audit in CI, emails stripped, `show_full_output: "false"`, aggregates and
paraphrases only in public. The repo is public and so are its Actions logs, so
each property below is one way a user's question (or their email) would reach
a public page.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "agent-measure.yml"
NOW = datetime(2026, 11, 17, 21, 0, tzinfo=timezone.utc)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(mod)
    return mod


def _steps():
    return yaml.safe_load(WF.read_text())["jobs"]["measure"]["steps"]


def _index(pred) -> int:
    return next(i for i, s in enumerate(_steps()) if pred(s))


def _named(prefix: str) -> int:
    return _index(lambda s: (s.get("name") or "").startswith(prefix))


def _analyst() -> int:
    return _index(lambda s: "claude-code-action" in (s.get("uses") or "")
                  and "`analyst`" in str((s.get("with") or {}).get("prompt")))


def _audit() -> int:
    return _named("Audit the /ask answers")


# ---- wiring -------------------------------------------------------------------

def test_the_audit_steps_run_in_order_after_the_analyst():
    order = [_analyst(), _named("Is the /ask audit due"), _named("Collect the /ask sample"),
             _named("Remove the bucket credentials"), _audit(),
             _named("Refuse audit output that quotes a user"), _named("Delete the /ask sample")]
    assert order == sorted(order) and len(set(order)) == len(order), order
    # Before the artifact upload, or the audit's aggregates never reach measurements/.
    upload = _index(lambda s: "upload-artifact" in (s.get("uses") or ""))
    assert order[-1] < upload


def test_later_steps_are_gated_on_the_due_check():
    steps = _steps()
    assert steps[_named("Is the /ask audit due")]["id"] == "ask_due"
    for name in ("Collect the /ask sample", "Audit the /ask answers",
                 "Refuse audit output that quotes a user"):
        assert "steps.ask_due.outputs.due == 'true'" in steps[_named(name)]["if"], name


def test_the_audit_never_prints_its_tool_results():
    step = _steps()[_audit()]
    assert "claude-code-action" in step["uses"]
    assert step["with"]["show_full_output"] == "false"


def test_the_audit_has_no_web_tools():
    args = _steps()[_audit()]["with"]["claude_args"]
    allowed = re.search(r'--allowedTools\s+"([^"]*)"', args).group(1)
    assert "WebFetch" not in allowed and "WebSearch" not in allowed
    # Bash only for named commands: a bare `Bash` would allow curl.
    assert "Bash" not in [t.strip() for t in allowed.split(",")]
    assert re.search(r'--disallowedTools\s+"[^"]*WebFetch[^"]*WebSearch', args)


def _allowed() -> list[str]:
    args = _steps()[_audit()]["with"]["claude_args"]
    return [t.strip() for t in re.search(r'--allowedTools\s+"([^"]*)"', args).group(1).split(",")]


def test_the_audit_posts_only_through_the_post_script():
    """QA on PR #1169: raw `gh issue create|comment` took `--body-file <any
    path>`, so the guard ran only if the agent chose to run it."""
    allowed = _allowed()
    assert "Bash(python3 scripts/ask_audit_post.py:*)" in allowed
    for t in allowed:
        assert not re.match(r"Bash\(gh issue (create|comment|edit|close)", t), t
        assert not re.match(r"Bash\(gh (api|label create|pr)", t), t
    assert {"Bash(gh issue list:*)", "Bash(gh issue view:*)", "Bash(gh label list:*)"} <= set(allowed)


def test_no_allowed_command_can_print_the_environment():
    """`jq -n env`, `wc --files0-from=/proc/self/environ` and `date -f FILE`
    all echo what they read; Read of /proc/<pid>/environ or .git/config would
    hand the agent the OAuth token or the checkout's GITHUB_TOKEN."""
    step = _steps()[_audit()]
    allowed, args = _allowed(), step["with"]["claude_args"]
    for t in allowed:
        if t.startswith("Bash("):
            cmd = t[5:].split(":")[0].split()[0]
            assert cmd in {"gh", "python3", "date"}, t
    assert "Bash(date -u +%Y-%m-%dT%H:%M:%SZ)" in allowed
    assert not any(t.startswith("Bash(date") and t != "Bash(date -u +%Y-%m-%dT%H:%M:%SZ)" for t in allowed)
    # Writes are confined to the outputs: a bare Write could edit .claude/ settings.
    assert "Write" not in allowed and "Edit" not in allowed
    assert all(t.startswith("Edit(//tmp/") for t in allowed if t.startswith(("Edit", "Write")))
    denied = re.search(r'--disallowedTools\s+"([^"]*)"', args).group(1).split(",")
    for rule in ("Read(//proc/**)", "Read(//dev/**)", "Read(./.git/**)"):
        assert rule in denied, rule
    # v1 runs in auto mode by default, where a safety review can pass a call no
    # allow rule covers; this list is only a boundary in default mode.
    assert re.search(r"--permission-mode\s+default\b", args)
    assert step["env"]["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] == "1"
    assert step["with"]["display_report"] == "false"
    # The checkout's persisted token is removed before the agent can Read it.
    rm = _steps()[_named("Remove the bucket credentials")]["run"]
    assert "git config --local --unset-all http.https://github.com/.extraheader" in rm


def test_the_audit_uses_the_analysts_token_and_skips_an_empty_sample():
    steps = _steps()
    a, b = steps[_analyst()]["with"], steps[_audit()]["with"]
    assert a["claude_code_oauth_token"] == b["claude_code_oauth_token"]
    assert "steps.ask_sample.outputs.n != '0'" in steps[_audit()]["if"]
    assert "steps.ask_sample.outcome == 'success'" in steps[_audit()]["if"]


def test_the_audit_does_not_overwrite_the_analysts_report():
    prompt = _steps()[_audit()]["with"]["prompt"]
    assert "/tmp/ask-audit-report.md" in prompt
    assert "write /tmp/report.md" not in prompt.lower()


def test_bucket_credentials_are_removed_before_the_audit_agent():
    steps = _steps()
    auth = _index(lambda s: "google-github-actions/auth" in (s.get("uses") or ""))
    assert steps[auth]["id"] == "gcs"
    rm = _named("Remove the bucket credentials")
    assert steps[rm]["if"] == "always()"
    assert auth < _named("Collect the /ask sample") < rm < _audit()
    run = steps[rm]["run"]
    assert 'rm -f "$CREDS"' in run and "gha-creds-*.json" in run
    # The auth step EXPORTED the path to the job, so the variables must be
    # blanked for every later step, not only the file deleted.
    for var in ("GOOGLE_APPLICATION_CREDENTIALS", "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE",
                "GOOGLE_GHA_CREDS_PATH"):
        assert f'echo "{var}="' in run, var
    assert '>> "$GITHUB_ENV"' in run
    for s in steps[rm + 1:]:
        assert "credentials_file_path" not in json.dumps(s), s.get("name") or s.get("uses")
        assert "BHAGYA_STORAGE_BUCKET" not in json.dumps(s.get("env") or {}), s.get("name")


def test_the_sample_is_deleted_always_and_is_never_uploaded():
    steps = _steps()
    rm = steps[_named("Delete the /ask sample")]
    assert rm["if"] == "always()" and "/tmp/ask-sample.json" in rm["run"]
    collect = steps[_named("Collect the /ask sample")]["run"]
    assert "--out /tmp/ask-sample.json" in collect
    # /tmp/measure is uploaded as an artifact and committed to measurements/.
    assert "/tmp/measure/ask-sample.json" not in WF.read_text()


def test_no_new_job_and_the_measure_permissions_are_unchanged():
    doc = yaml.safe_load(WF.read_text())
    assert set(doc["jobs"]) == {"measure", "commit"}
    assert doc["jobs"]["measure"]["permissions"] == {
        "contents": "read", "issues": "write", "pull-requests": "read", "id-token": "write"}
    for s in _steps():
        assert "permissions" not in s


# ---- the collector's whitelist -------------------------------------------------

EVENTS = [
    {"ts": "2026-11-16T10:00:00+00:00", "type": "form_ask", "email": "seeker@example.com",
     "data": {"question": "Will my career change soon?", "category": "career", "lang": "en",
              "model": "groq120", "answer": "The chart suggests a supportive stretch ahead.",
              "context": "chart", "cache_hit": False,
              "partner_email": "other@example.com", "ip": "203.0.113.9"}},
    {"ts": "2026-11-15T09:00:00+00:00", "type": "form_ask", "email": "two@example.com",
     "data": {"question": "शादी कब होगी?", "category": "marriage", "lang": "hi",
              "model": "groq20", "answer": "उत्तर", "context": "chart", "cache_hit": True,
              "chart": {"lagna": "Leo"}}},
]


def _collect(tmp_path, events=EVENTS, probe=lambda: None):
    mod = _load("collect_ask_sample")
    out, meta = tmp_path / "s.json", tmp_path / "measure" / "meta.json"
    rc = mod.main(["x", "--out", str(out), "--meta", str(meta)],
                  read=lambda d, n: list(events), probe=probe, now=NOW)
    return mod, rc, out, meta


def test_the_sample_holds_only_whitelisted_fields_and_no_email(tmp_path):
    mod, rc, out, meta = _collect(tmp_path)
    assert rc == 0
    text = out.read_text()
    assert "@example.com" not in text and "email" not in text and "203.0.113.9" not in text
    doc = json.loads(text)
    assert doc["n"] == 2
    for row in doc["answers"]:
        assert set(row) <= set(mod.SAMPLE_FIELDS)
    assert set(doc["answers"][0]) == set(mod.SAMPLE_FIELDS) - {"chart"}
    assert doc["answers"][1]["chart"] == {"lagna": "Leo"}
    assert doc["answers"][0]["question"] == "Will my career change soon?"


def test_a_new_event_field_stays_out_unless_whitelisted(tmp_path):
    evt = json.loads(json.dumps(EVENTS[0]))
    evt["data"]["birth_place"] = "Somewhere"
    _, rc, out, _ = _collect(tmp_path, events=[evt])
    assert rc == 0 and "Somewhere" not in out.read_text()


def test_the_meta_file_holds_counts_and_no_text(tmp_path):
    _, rc, out, meta = _collect(tmp_path)
    m = json.loads(meta.read_text())
    assert m["total"] == 2 and m["fresh"] == 1 and m["cache_hits"] == 1 and m["with_chart"] == 1
    assert m["by_category"] == {"career": 1, "marriage": 1}
    assert m["by_lang"] == {"en": 1, "hi": 1}
    text = meta.read_text()
    for needle in ("career change", "शादी", "@example.com", "supportive", "Leo"):
        assert needle not in text, needle


def test_a_free_text_category_is_counted_as_other(tmp_path):
    evt = json.loads(json.dumps(EVENTS[0]))
    evt["data"]["category"] = "My Private Words"
    _, _, _, meta = _collect(tmp_path, events=[evt])
    assert json.loads(meta.read_text())["by_category"] == {"other": 1}


def test_zero_events_is_a_valid_empty_sample(tmp_path):
    _, rc, out, meta = _collect(tmp_path, events=[])
    assert rc == 0 and json.loads(out.read_text())["n"] == 0
    assert json.loads(meta.read_text())["total"] == 0


def test_unreadable_storage_exits_2_and_writes_nothing(tmp_path):
    _, rc, out, meta = _collect(tmp_path, probe=lambda: "Forbidden: 403")
    assert rc == 2 and not out.exists() and not meta.exists()


def test_the_sample_is_refused_under_measurements(tmp_path):
    mod = _load("collect_ask_sample")
    rc = mod.main(["x", "--out", str(tmp_path / "measurements" / "s.json"),
                   "--meta", str(tmp_path / "m.json")],
                  read=lambda d, n: list(EVENTS), probe=lambda: None, now=NOW)
    assert rc == 2


def test_the_real_events_reader_feeds_the_collector(tmp_path, monkeypatch):
    """Through astro_ai.events.recent, the reader /admin/activity uses, with
    the local fallback blob standing in for GCS."""
    from astro_ai import events
    today = datetime.now(timezone.utc).date()
    (tmp_path / f"{today.isoformat()}.json").write_text(json.dumps(
        {"date": today.isoformat(), "events": EVENTS[:1] + [
            {"ts": "x", "type": "form_kundli", "email": "k@example.com", "data": {}}]}))
    monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
    monkeypatch.setattr(events, "_LOCAL_FALLBACK_DIR", tmp_path)
    monkeypatch.setattr(events, "_read_day", events._fetch_day)
    mod = _load("collect_ask_sample")
    out, meta = tmp_path / "s.json", tmp_path / "m.json"
    assert mod.main(["x", "--out", str(out), "--meta", str(meta)], probe=lambda: None) == 0
    doc = json.loads(out.read_text())
    assert doc["n"] == 1 and "@example.com" not in out.read_text()


# ---- the weekly gate -------------------------------------------------------------

def test_due_when_the_audit_file_is_missing(tmp_path):
    assert _load("ask_audit_due").is_due(tmp_path / "ask-audit.json", NOW)[0] is True


def test_due_at_six_and_a_half_days_not_before(tmp_path):
    mod = _load("ask_audit_due")
    f = tmp_path / "ask-audit.json"
    for age, due in ((timedelta(days=6.4), False), (timedelta(days=6.5), True),
                     (timedelta(days=9), True), (timedelta(hours=1), False)):
        f.write_text(json.dumps({"generated_at": (NOW - age).strftime("%Y-%m-%dT%H:%M:%SZ")}))
        assert mod.is_due(f, NOW)[0] is due, age


def test_a_broken_audit_file_fails_open_to_due(tmp_path):
    mod = _load("ask_audit_due")
    f = tmp_path / "ask-audit.json"
    for body in ("not json", "{}", '{"generated_at": "yesterday"}', "[]"):
        f.write_text(body)
        assert mod.is_due(f, NOW)[0] is True, body


def test_due_writes_the_step_output(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    _load("ask_audit_due").main(["x", str(tmp_path / "missing.json")], now=NOW)
    assert out.read_text() == "due=true\n"


# ---- the leak guard ------------------------------------------------------------

SAMPLE = {"answers": [
    {"id": "abc123", "question": "Will I clear the bank exam in March next year?",
     "answer": "Your current period is supportive for steady study and focus, and the "
               "months ahead favour disciplined preparation over shortcuts of any kind."}]}


def _guard(tmp_path, *args):
    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps(SAMPLE))
    return _load("ask_audit_guard").main(["x", "--sample", str(sample), *args])


def test_the_guard_catches_a_quoted_question(tmp_path, capsys):
    f = tmp_path / "audit.json"
    f.write_text('{"note": "user asked: will i clear the bank exam in march"}')
    assert _guard(tmp_path, "leaks", "--delete", str(f)) == 1
    assert not f.exists()
    assert "bank exam" not in capsys.readouterr().out  # never echo the quote


def test_the_guard_catches_a_quoted_answer(tmp_path):
    f = tmp_path / "r.md"
    f.write_text("Example: focus, and the months ahead favour disciplined preparation over shortcuts of any kind.")
    assert _guard(tmp_path, "leaks", str(f)) == 1


def test_the_guard_passes_a_paraphrase(tmp_path):
    f = tmp_path / "r.md"
    f.write_text("An education answer gave a pass/fail verdict on a competitive exam (ask.txt:49).")
    assert _guard(tmp_path, "leaks", str(f)) == 0


def test_an_issue_body_needs_a_passing_evidence_block(tmp_path):
    body = tmp_path / "issue.md"
    body.write_text("<!-- ask-audit-class: exam-verdict -->\nAn answer gave a pass/fail verdict.\n")
    assert _guard(tmp_path, "issue-body", str(body), "--labels", "bug") == 1
    body.write_text(body.read_text() + (
        "## Evidence Block\n"
        "- **corpus:** n/a. The defect is a prompt-contract breach, ask.txt:49, no rule claimed.\n"
        "- **tokens:** 0 Groq, measured: the audit reads stored answers and makes no app LLM call.\n"
        "- **repro:** `jq '.defect_classes[0].count' measurements/ask-audit.json` -> `1`\n"
        "- **thesis:** tightening ask.txt:49 removes the verdicts.\n"
        "- **metric:** the class count is 0 on the next weekly audit.\n"))
    assert _guard(tmp_path, "issue-body", str(body), "--labels",
                  "astrology-correctness,bug,layer:prompt") == 0


def test_the_guard_without_a_sample_is_not_a_pass(tmp_path):
    f = tmp_path / "r.md"
    f.write_text("x")
    mod = _load("ask_audit_guard")
    assert mod.main(["x", "--sample", str(tmp_path / "none.json"), "leaks", str(f)]) == 2


def test_the_guard_names_the_file_not_the_sample_id(tmp_path, capsys):
    f = tmp_path / "audit.json"
    f.write_text("user asked: will i clear the bank exam in march")
    assert _guard(tmp_path, "leaks", str(f)) == 1
    out = capsys.readouterr().out
    assert f"a user quote was found in {f}" in out
    assert "abc123" not in out


# ---- the post-step file guard, EXECUTED (QA on PR #1169, D1 and D2) ----------------
#
# The step's own shell, lifted from the YAML and run under `bash -e` (the
# runner's default) with every /tmp/ path moved into a temp dir. Reading the
# YAML could not have caught either defect: both are about how bash expands it.

QUOTE = "user asked: will i clear the bank exam in march"


def _run_refuse_step(tmp_path, files: dict, report: str | None = None, sample=True):
    import os
    import subprocess
    import time
    run = _steps()[_named("Refuse audit output that quotes a user")]["run"]
    root = tmp_path / "t"
    (root / "measure").mkdir(parents=True)
    if sample:
        (root / "ask-sample.json").write_text(json.dumps(SAMPLE))
        old = time.time() - 60
        os.utime(root / "ask-sample.json", (old, old))
    for name, text in files.items():
        (root / "measure" / name).write_text(text)
    if report is not None:
        (root / "ask-audit-report.md").write_text(report)
    assert "/tmp/ask-sample.json" in run and "/tmp/measure" in run
    script = run.replace("/tmp/", f"{root}/")
    env = dict(os.environ, GITHUB_STEP_SUMMARY=str(root / "summary.md"))
    p = subprocess.run(["bash", "-e", "-c", script], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=60)
    return p, root


def test_executed_no_report_still_runs_the_guard_and_deletes_a_quote(tmp_path):
    """D1: `files=$(find ...; ls <report>)` took ls's exit 2 and the step died
    before the guard, leaving the quoting file to be uploaded."""
    p, root = _run_refuse_step(tmp_path, {"ask-audit.json": QUOTE})
    assert p.returncode == 0, p.stdout + p.stderr
    assert not (root / "measure" / "ask-audit.json").exists()
    assert "bank exam" not in p.stdout + p.stderr


def test_executed_quiet_week_is_green(tmp_path):
    """D1, the n == 0 week: no audit ran, no report, no new files."""
    p, root = _run_refuse_step(tmp_path, {})
    assert p.returncode == 0, p.stdout + p.stderr
    assert "no report written" in (root / "summary.md").read_text()


def test_executed_a_space_in_a_file_name_is_still_checked(tmp_path):
    """D2: an unquoted `$files` split `x y.json` into `x` and `y.json`."""
    p, root = _run_refuse_step(tmp_path, {"x y.json": QUOTE, "clean.json": '{"n": 3}'},
                               report="| rubric | pass |\n| grounded | 3 |\n")
    assert p.returncode == 0, p.stdout + p.stderr
    assert not (root / "measure" / "x y.json").exists()
    assert (root / "measure" / "clean.json").exists()
    assert "| grounded | 3 |" in (root / "summary.md").read_text()


def test_executed_a_quoting_report_is_deleted_and_never_summarised(tmp_path):
    p, root = _run_refuse_step(tmp_path, {}, report=f"Example: {QUOTE}\n")
    assert p.returncode == 0, p.stdout + p.stderr
    assert not (root / "ask-audit-report.md").exists()
    assert "bank exam" not in (root / "summary.md").read_text()


def test_executed_could_not_verify_deletes_unchecked_and_says_so(tmp_path):
    """Guard exit 2 is not a pass, and not a quote either."""
    p, root = _run_refuse_step(tmp_path, {"ask-audit.json": '{"n": 3}'},
                               report="aggregates", sample=False)
    assert p.returncode == 0, p.stdout + p.stderr
    assert not (root / "measure" / "ask-audit.json").exists()
    assert not (root / "ask-audit-report.md").exists()
    assert "could not verify" in p.stdout and "quote was found" not in p.stdout


# ---- ask_audit_post.py: the only way the audit posts --------------------------------

EVIDENCE = (
    "<!-- ask-audit-class: exam-verdict -->\nAn education answer gave a pass/fail verdict.\n"
    "## Evidence Block\n"
    "- **corpus:** n/a. The defect is a prompt-contract breach, ask.txt:49, no rule claimed.\n"
    "- **tokens:** 0 Groq, measured: the audit reads stored answers and makes no app LLM call.\n"
    "- **repro:** `jq '.defect_classes[0].count' measurements/ask-audit.json` -> `1`\n"
    "- **thesis:** tightening ask.txt:49 removes the verdicts.\n"
    "- **metric:** the class count is 0 on the next weekly audit.\n")


AUDIT_VIEW = {"author": {"login": "app/claude", "is_bot": True, "name": "claude"},
              "labels": [{"name": "bug"}, {"name": "provenance:outsider"}],
              "body": "<!-- ask-audit-class: exam-verdict -->\nbody\n"}


def _row(n, age_h=1.0, **over):
    """One `gh issue list` row for an audit issue made `age_h` hours ago."""
    made = datetime.now(timezone.utc) - timedelta(hours=age_h)
    row = dict(AUDIT_VIEW, number=n, createdAt=made.strftime("%Y-%m-%dT%H:%M:%SZ"))
    row.update(over)
    return row


class FakeGh:
    """`views` maps an issue number to the dict `gh issue view --json` would print;
    `listing` is what `gh issue list` prints. `bad` maps ("issue", "view"|"list") to
    raw stdout, for malformed answers. The default view is a valid audit issue."""

    def __init__(self, fail=(), views=None, listing=(), bad=None):
        self.calls, self.fail = [], set(fail)
        self.views, self.listing, self.bad = views, list(listing), bad or {}

    def __call__(self, args):
        self.calls.append(list(args))
        key = tuple(args[:2])
        rc = 1 if key in self.fail else 0
        out = ""
        if args[:2] == ["issue", "create"]:
            out = "https://github.com/o/r/issues/9\n"
        # Valid stdout even when rc is 1: a gh that fails but prints a plausible answer
        # must still be refused on its exit code, not on a parse error.
        elif key == ("issue", "view"):
            out = self.bad.get(key) or json.dumps(
                (self.views or {}).get(int(args[2]), AUDIT_VIEW))
        elif key == ("issue", "list"):
            out = self.bad.get(key) or json.dumps(self.listing)
        return self.mod.Result(rc, out)

    def posts(self):
        return [c for c in self.calls if c[:2] in (["issue", "create"], ["issue", "comment"])]

    def writes(self):
        """Every call that changes GitHub: label create, edit, create, comment."""
        return [c for c in self.calls if c[:2] in (["label", "create"], ["issue", "edit"],
                                                    ["issue", "create"], ["issue", "comment"])]


def _post(tmp_path, monkeypatch, body, *args, gh=None, where="work"):
    mod = _load("ask_audit_post")
    work = tmp_path / "ask-work"
    work.mkdir(exist_ok=True)
    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps(SAMPLE))
    monkeypatch.setattr(mod, "WORK_DIR", work)
    monkeypatch.setattr(mod, "SAMPLE", sample)
    f = (work if where == "work" else tmp_path) / "issue-exam-verdict.md"
    f.write_text(body)
    gh = gh or FakeGh()
    gh.mod = mod
    return mod.main(["x", "--body-file", str(f), *args], gh=gh), gh


LABELS = ("--labels", "astrology-correctness,bug,layer:prompt")


def test_post_refuses_a_quoting_body_and_posts_nothing(tmp_path, monkeypatch, capsys):
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE + f"\nExample: {QUOTE}\n",
                   "--title", "Exam verdicts", *LABELS)
    assert rc == 1 and gh.calls == []
    assert "bank exam" not in capsys.readouterr().out


def test_post_refuses_a_quoting_title(tmp_path, monkeypatch):
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE,
                   "--title", "Will I clear the bank exam in March", *LABELS)
    assert rc == 1 and gh.calls == []


def test_post_refuses_a_failing_evidence_block(tmp_path, monkeypatch):
    rc, gh = _post(tmp_path, monkeypatch, "An answer gave a verdict.\n", "--title", "t", *LABELS)
    assert rc == 1 and gh.calls == []


def test_post_files_a_clean_body_with_the_outsider_label(tmp_path, monkeypatch):
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE, "--title", "Exam verdicts", *LABELS)
    assert rc == 0
    [create] = [c for c in gh.calls if c[:2] == ["issue", "create"]]
    labels = [create[i + 1] for i, x in enumerate(create) if x == "--label"]
    assert "provenance:outsider" in labels and "astrology-correctness" in labels
    # The cap read comes first (#1291); the label is the first WRITE.
    assert gh.writes()[0][:3] == ["label", "create", "provenance:outsider"]


def test_post_comment_labels_the_issue_before_commenting(tmp_path, monkeypatch):
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE, *LABELS, "--issue", "42")
    assert rc == 0
    edit = gh.calls.index(["issue", "edit", "42", "--add-label", "provenance:outsider"])
    comment = next(i for i, c in enumerate(gh.calls) if c[:3] == ["issue", "comment", "42"])
    assert edit < comment


def test_post_comment_is_not_posted_when_the_label_fails(tmp_path, monkeypatch):
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE, *LABELS, "--issue", "42",
                   gh=FakeGh(fail={("issue", "edit")}))
    assert rc == 2 and gh.posts() == []


# ---- #1291: --issue and the cap are bound by gh, not by the prompt -------------------

def _comment(tmp_path, monkeypatch, view, **kw):
    return _post(tmp_path, monkeypatch, EVIDENCE, *LABELS, "--issue", "42",
                 gh=FakeGh(views={42: view}, **kw))


def _refused_without_a_write(rc, gh, want):
    assert rc == want and gh.writes() == [], gh.calls
    assert not any(c[:2] == ["label", "create"] for c in gh.calls)


def test_a_comment_on_a_human_filed_issue_is_refused(tmp_path, monkeypatch):
    human = dict(AUDIT_VIEW, author={"login": "someone", "is_bot": False, "name": "S"},
                 labels=[{"name": "bug"}])
    _refused_without_a_write(*_comment(tmp_path, monkeypatch, human), 1)


def test_a_comment_on_an_outsider_issue_copying_the_marker_and_label_is_refused(tmp_path, monkeypatch):
    """Forgery: label and marker are text anyone can write; the author is not."""
    forged = dict(AUDIT_VIEW, author={"login": "mallory", "is_bot": False, "name": "M"})
    _refused_without_a_write(*_comment(tmp_path, monkeypatch, forged), 1)
    # A non-self bot is no better.
    other = dict(AUDIT_VIEW, author={"login": "app/dependabot", "is_bot": True, "name": "d"})
    _refused_without_a_write(*_comment(tmp_path, monkeypatch, other), 1)


def test_a_comment_on_a_loop_issue_without_the_marker_or_the_label_is_refused(tmp_path, monkeypatch):
    """The loop's own issues (#1291 itself): self-app author, neither marker nor label."""
    no_marker = dict(AUDIT_VIEW, body="An ordinary loop issue.\n")
    no_label = dict(AUDIT_VIEW, labels=[{"name": "provenance:trusted"}])
    inline = dict(AUDIT_VIEW, body="see <!-- ask-audit-class: x --> inline, not on its own line")
    for view in (no_marker, no_label, inline):
        _refused_without_a_write(*_comment(tmp_path, monkeypatch, view), 1)


def test_a_comment_on_an_audit_issue_is_allowed_label_first(tmp_path, monkeypatch):
    rc, gh = _comment(tmp_path, monkeypatch, AUDIT_VIEW)
    assert rc == 0
    names = [c[:2] for c in gh.calls]
    assert names.index(["issue", "view"]) < names.index(["label", "create"]) \
        < names.index(["issue", "edit"]) < names.index(["issue", "comment"])
    assert not any(c[:2] == ["issue", "list"] for c in gh.calls)   # the cap is for new issues
    assert gh.calls[0] == ["issue", "view", "42", "--json", "author,labels,body"]


def test_a_comment_also_accepts_the_bot_suffix_rendering(tmp_path, monkeypatch):
    view = dict(AUDIT_VIEW, author={"login": "github-actions[bot]", "is_bot": True, "name": "g"})
    assert _comment(tmp_path, monkeypatch, view)[0] == 0


def test_a_comment_fails_closed_on_a_gh_answer_it_cannot_trust(tmp_path, monkeypatch):
    stringy = dict(AUDIT_VIEW, author={"login": "app/claude", "is_bot": "false", "name": "c"})
    bad_login = dict(AUDIT_VIEW, author={"login": "x y;rm", "is_bot": True, "name": "c"})
    for view in (stringy, bad_login, {"labels": [], "body": ""}, [], dict(AUDIT_VIEW, labels="bug"),
                 dict(AUDIT_VIEW, body=None)):
        rc, gh = _comment(tmp_path, monkeypatch, view)
        assert rc == 2 and gh.writes() == [], view
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE, *LABELS, "--issue", "42",
                   gh=FakeGh(fail={("issue", "view")}))
    assert rc == 2 and gh.writes() == []
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE, *LABELS, "--issue", "42",
                   gh=FakeGh(bad={("issue", "view"): "not json"}))
    assert rc == 2 and gh.writes() == []


def _new(tmp_path, monkeypatch, body=EVIDENCE, **kw):
    return _post(tmp_path, monkeypatch, body, "--title", "Exam verdicts", *LABELS, gh=FakeGh(**kw))


def test_a_sixth_new_issue_in_the_window_is_refused(tmp_path, monkeypatch):
    rc, gh = _new(tmp_path, monkeypatch, listing=[_row(n, age_h=n) for n in range(1, 6)])
    _refused_without_a_write(rc, gh, 1)
    assert not any(c[:2] == ["issue", "create"] for c in gh.calls)


def test_a_fifth_new_issue_in_the_window_is_allowed(tmp_path, monkeypatch):
    rc, gh = _new(tmp_path, monkeypatch, listing=[_row(n, age_h=n) for n in range(1, 5)])
    assert rc == 0
    [lst] = [c for c in gh.calls if c[:2] == ["issue", "list"]]
    assert "--search" not in lst and lst[lst.index("--state") + 1] == "all"
    assert [c[:2] for c in gh.calls].index(["issue", "list"]) < [c[:2] for c in gh.calls].index(["label", "create"])


def test_the_cap_counts_only_audit_issues_inside_the_window(tmp_path, monkeypatch):
    noise = [_row(10, age_h=25),                                        # outside the window
             _row(11, author={"login": "mallory", "is_bot": False, "name": "m"}),   # human + marker
             _row(12, body="no marker here"),                           # bot, no marker
             _row(13, labels=[{"name": "bug"}])]                        # no outsider label
    rc, gh = _new(tmp_path, monkeypatch, listing=noise + [_row(n) for n in range(1, 5)])
    assert rc == 0, gh.calls


def test_the_cap_is_counted_by_the_author_test(tmp_path, monkeypatch):
    """Five outsider-authored issues copying marker and label must not lock the audit out."""
    forged = [_row(n, author={"login": "mallory", "is_bot": False, "name": "m"}) for n in range(1, 8)]
    assert _new(tmp_path, monkeypatch, listing=forged)[0] == 0


def test_the_cap_fails_closed_when_it_cannot_be_counted(tmp_path, monkeypatch):
    for kw in (dict(fail={("issue", "list")}),
               dict(bad={("issue", "list"): "not json"}),
               dict(bad={("issue", "list"): '{"a": 1}'}),
               dict(listing=[_row(1, createdAt="yesterday")]),
               dict(listing=[_row(1, author={"login": "claude", "is_bot": "true", "name": "c"})]),
               # a full page that never leaves the window: older rows may still count
               dict(listing=[_row(n, age_h=0.1, body="x") for n in range(1, 101)])):
        rc, gh = _new(tmp_path, monkeypatch, **kw)
        assert rc == 2 and gh.writes() == [], (kw, gh.calls)


def test_a_full_page_that_reaches_outside_the_window_is_countable(tmp_path, monkeypatch):
    rows = [_row(n, age_h=0.1, body="x") for n in range(1, 100)] + [_row(100, age_h=30, body="x")]
    assert _new(tmp_path, monkeypatch, listing=rows)[0] == 0


def test_a_new_issue_without_the_class_line_is_refused(tmp_path, monkeypatch):
    rc, gh = _new(tmp_path, monkeypatch, body=EVIDENCE.replace("<!-- ask-audit-class: exam-verdict -->\n", ""))
    _refused_without_a_write(rc, gh, 1)
    assert gh.calls == []   # not even a read: the body alone decides


def test_post_refuses_a_body_outside_the_work_dir(tmp_path, monkeypatch):
    """Else it is a way to post any readable file, /proc/<pid>/environ included."""
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE, "--title", "t", *LABELS, where="outside")
    assert rc == 2 and gh.calls == []


def test_post_refuses_a_label_off_the_list(tmp_path, monkeypatch):
    rc, gh = _post(tmp_path, monkeypatch, EVIDENCE, "--title", "t",
                   "--labels", "bug,provenance:trusted")
    assert rc == 2 and gh.calls == []


def test_post_without_a_sample_posts_nothing(tmp_path, monkeypatch):
    mod = _load("ask_audit_post")
    work = tmp_path / "ask-work"
    work.mkdir()
    (work / "b.md").write_text(EVIDENCE)
    monkeypatch.setattr(mod, "WORK_DIR", work)
    monkeypatch.setattr(mod, "SAMPLE", tmp_path / "none.json")
    gh = FakeGh()
    gh.mod = mod
    assert mod.main(["x", "--body-file", str(work / "b.md"), "--title", "t", *LABELS], gh=gh) == 2
    assert gh.calls == []


def test_the_audit_runs_only_if_the_credentials_were_actually_removed():
    """QA FAIL on #1169: a failed removal (exit 1) did not stop the audit agent."""
    import yaml as _y
    from pathlib import Path as _P
    doc = _y.safe_load((_P(__file__).resolve().parents[1] / ".github/workflows/agent-measure.yml").read_text())
    steps = doc["jobs"]["measure"]["steps"]
    rm = next(s for s in steps if s.get("name") == "Remove the bucket credentials before the audit agent runs")
    audit = next(s for s in steps if s.get("name") == "Audit the /ask answers")
    assert rm.get("id") == "ask_creds_gone"
    assert "steps.ask_creds_gone.outcome == 'success'" in audit["if"]
