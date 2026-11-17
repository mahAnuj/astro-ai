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
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "agent-measure.yml"
NOW = datetime(2026, 11, 17, 21, 0, tzinfo=timezone.utc)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
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
