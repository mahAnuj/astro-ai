"""scripts/outbox.py -- the one posting path for the loop's comments and issues (#1188).

#311, #276 and #329 each collected 20+ near-identical comments, and every anti-noise
rule in this repo was written per script after its incident. These cases drive the
outbox against an in-memory GitHub so each of its promises is proven by behaviour:
dedupe (with SHAs, timestamps and run ids normalised), the daily cap and quiet start,
retry on 5xx and never on a 422, a ledger that carries no message text, and the three
migrated posters actually going through it. The last case keeps it that way: a script
under scripts/ that posts without the outbox turns this file red."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ob = _load("outbox")
REPO = "o/r"
NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
SECRET = "SENTINEL-user-text-a7f3 ghp_notarealtoken"


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeGh:
    """Comments per issue, each {body, viewerDidAuthor, createdAt, url}. `fail` is a
    list of exceptions raised by successive post attempts before one succeeds."""

    def __init__(self, comments=None, fail=(), read_fails=False, issues=None):
        self.comments = {k: list(v) for k, v in (comments or {}).items()}
        self.fail = list(fail)
        self.read_fails = read_fails
        self.issues = list(issues or [])
        self.calls: list = []
        self.next_id = 9000
        self.land_on_fail = False

    def _new(self, n, body):
        self.next_id += 1
        self.comments.setdefault(n, []).append(
            {"body": body, "viewerDidAuthor": True, "createdAt": iso(NOW),
             "url": f"https://github.com/{REPO}/issues/{n}#issuecomment-{self.next_id}"})
        return self.next_id

    def __call__(self, args):
        self.calls.append(list(args))
        if args[1] == "view" and args[0] in ("issue", "pr"):
            if self.read_fails:
                raise ob.GhError("gh: Bad Gateway (HTTP 502)")
            return json.dumps({"comments": self.comments.get(int(args[2]), [])})
        if args[1] == "comment" and args[0] in ("issue", "pr"):
            n, body = int(args[2]), args[args.index("--body") + 1]
            if self.fail:
                exc = self.fail.pop(0)
                if self.land_on_fail:
                    self._new(n, body)
                raise exc
            cid = self._new(n, body)
            return f"https://github.com/{REPO}/issues/{n}#issuecomment-{cid}\n"
        if args[:3] == ["api", "-X", "PATCH"]:
            cid = int(args[3].rsplit("/", 1)[1])
            for cs in self.comments.values():
                for c in cs:
                    if c["url"].endswith(f"-{cid}"):
                        c["body"] = args[5][len("body="):]
            return "{}"
        if args[:2] == ["api", "--paginate"] and "/issues?" in args[2]:
            return "\n".join(json.dumps(i) for i in self.issues)
        if args[:3] == ["api", "-X", "POST"] and args[3].endswith("/issues"):
            if self.fail:
                raise self.fail.pop(0)
            self.issues.append({"number": 100 + len(self.issues), "state": "open",
                                "created_at": iso(NOW), "user": {"login": "github-actions[bot]"},
                                "body": args[7][len("body="):]})
            return "{}"
        raise AssertionError(args)

    def posts(self):
        return [c for c in self.calls if c[1:2] == ["comment"]]


def box(gh, **kw):
    sleeps = kw.pop("sleeps", [])
    return ob.Outbox(gh, REPO, now=lambda: NOW, sleep=sleeps.append, ledger_path=kw.pop("ledger", ""),
                     log=kw.pop("log", sys.stderr), **kw)


def own(body, at=NOW, author=True, cid=1):
    return {"body": body, "viewerDidAuthor": author, "createdAt": iso(at),
            "url": f"https://github.com/{REPO}/issues/5#issuecomment-{cid}"}


# ---- dedupe and normalisation ---------------------------------------------------------

def test_volatile_parts_normalise_to_the_same_key():
    a = "QA round on `3f9c2ab1d4e5` at 2026-11-17T10:22:31Z, run 19876543210 (actions/runs/19876543210)"
    b = "QA round on `a0b1c2d3e4f5a6b7` at 2026-11-18T04:01:00Z, run 19900000001 (actions/runs/19900000001)"
    assert ob.normalise(a) == ob.normalise(b)
    assert ob.key_for("k", a) == ob.key_for("k", b)


def test_bare_run_ids_and_run_numbers_normalise_too():
    assert ob.normalise("retry of 19876543210 failed") == ob.normalise("retry of 19900000001 failed")
    assert ob.normalise("agent-work run #4821 stood down") == ob.normalise("agent-work run #4822 stood down")


def test_a_changed_number_in_the_prose_is_a_different_message():
    assert ob.key_for("k", "idle 90% of the week") != ob.key_for("k", "idle 40% of the week")
    assert ob.key_for("k", "13174859 tokens per PR") != ob.key_for("k", "20410000 tokens per PR"), \
        "an 8-digit count is not a SHA"
    assert ob.key_for("k", "the page was defaced") != ob.key_for("k", "the page was effaced")
    assert ob.key_for("k", "same text") != ob.key_for("other", "same text"), "the kind is in the key"


def test_the_marker_itself_is_not_part_of_the_key():
    body = "hello"
    marked = body + "\n\n" + ob.marker("k", ob.key_for("k", body), {"deduped": 3})
    assert ob.key_for("k", marked) == ob.key_for("k", body)


def test_a_repeat_of_our_own_marked_comment_is_a_logged_no_op():
    body = "Gates red on 3f9c2ab at 2026-11-17T10:00Z"
    gh = FakeGh({5: [own(body + "\n" + ob.marker("triage-stage1", ob.key_for("triage-stage1", body)))]})
    o = box(gh).post(5, "triage-stage1", "Gates red on 77aa01f at 2026-11-17T22:00Z")
    assert o.outcome == "deduped" and gh.posts() == []


def test_a_copied_marker_in_someone_elses_comment_does_not_silence_us():
    body = "a stop"
    m = ob.marker("provenance-unresolved", ob.key_for("provenance-unresolved", body))
    gh = FakeGh({5: [own(body + m, author=False)]})
    assert box(gh).post(5, "provenance-unresolved", body).outcome == "sent"


def test_an_unmarked_comment_from_before_the_outbox_still_dedupes_by_text():
    gh = FakeGh({5: [own("Provenance could not be resolved at 2026-11-01T00:00:00Z")]})
    o = box(gh).post(5, "provenance-unresolved", "Provenance could not be resolved at 2026-11-17T00:00:00Z")
    assert o.outcome == "deduped"


def test_a_repeat_outside_the_window_is_sent():
    body = "the same words"
    old = NOW - timedelta(days=8)
    gh = FakeGh({5: [own(body + ob.marker("provenance-unresolved", ob.key_for("provenance-unresolved", body)), at=old)]})
    assert box(gh).post(5, "provenance-unresolved", body).outcome == "sent"


def test_last_mode_says_A_again_after_cleared():
    """ops-finding is a state carrier: A, cleared, A must be three comments."""
    gh = FakeGh()
    b = box(gh)
    old = NOW - timedelta(days=2)
    for text in ("Now AMBER: x", "cleared", "Now AMBER: x"):
        gh.comments.setdefault(5, [])
        assert b.post(5, "ops-finding", text).outcome == "sent", text
        for c in gh.comments[5]:
            c["createdAt"] = iso(old)            # keep the cap out of this case
    assert b.post(5, "ops-finding", "Now AMBER: x").outcome == "deduped", "but not twice in a row"


def test_two_identical_posts_in_one_run_see_each_other_through_the_ledger():
    gh = FakeGh(read_fails=True)                 # no reads at all: the run ledger alone
    b = box(gh)
    assert b.post(5, "triage-stage1", "x").outcome == "sent"
    assert b.post(5, "triage-stage1", "x").outcome == "deduped"


def test_a_failed_read_is_fail_open_and_says_so():
    rows = []
    gh = FakeGh(read_fails=True)
    b = box(gh)
    o = b.post(5, "provenance-unresolved", "the stop")
    assert o.outcome == "sent" and b.rows[-1]["checked"] is False


# ---- cap and quiet start ----------------------------------------------------------------

def test_the_daily_cap_binds_per_target_and_kind():
    gh = FakeGh({5: [own("one" + ob.marker("ops-finding", "1" * 16), cid=1),
                     own("two" + ob.marker("ops-finding", "2" * 16), cid=2)]})
    assert box(gh).post(5, "ops-finding", "three").outcome == "capped"
    assert box(gh).post(6, "ops-finding", "three").outcome == "sent", "another target has its own cap"


def test_the_cap_is_a_rolling_day():
    yesterday = NOW - timedelta(hours=25)
    gh = FakeGh({5: [own("one" + ob.marker("ops-finding", "1" * 16), at=yesterday, cid=1),
                     own("two" + ob.marker("ops-finding", "2" * 16), at=yesterday, cid=2)]})
    assert box(gh).post(5, "ops-finding", "three").outcome == "sent"


def test_a_kind_never_seen_before_starts_quiet():
    assert "brand-new-kind" not in ob.KINDS
    assert ob.policy("brand-new-kind")["cap"] == ob.QUIET_CAP == 1
    gh = FakeGh()
    b = box(gh)
    assert b.post(5, "brand-new-kind", "first").outcome == "sent"
    assert b.post(5, "brand-new-kind", "second, different").outcome == "capped"


def test_the_kinds_config_is_valid_and_every_migrated_kind_is_in_it():
    assert ob.validate_kinds() == []
    assert ob.validate_kinds({"x": {"cap": 0}}), "a cap of 0 is refused"
    assert {"ops-finding", "ops-finding-issue", "triage-stage1", "provenance-unresolved"} <= set(ob.KINDS)


# ---- retry ------------------------------------------------------------------------------

def test_a_5xx_is_retried_with_backoff_then_sent():
    sleeps = []
    gh = FakeGh(fail=[ob.GhError("gh: Bad Gateway (HTTP 502)"), ob.GhError("HTTP 503: Service Unavailable")])
    o = box(gh, sleeps=sleeps).post(5, "triage-stage1", "x")
    assert o.outcome == "sent" and o.attempts == 3 and sleeps == list(ob.RETRY_DELAYS)


def test_a_422_is_never_retried():
    sleeps = []
    gh = FakeGh(fail=[ob.GhError("gh: Validation Failed (HTTP 422)")] * 3)
    o = box(gh, sleeps=sleeps).post(5, "triage-stage1", "x")
    assert o.outcome == "failed" and o.attempts == 1 and o.status == 422 and sleeps == []
    assert len(gh.posts()) == 1


def test_a_plain_403_is_final_but_a_secondary_rate_limit_is_retried():
    assert ob.classify(ob.GhError("gh: Resource not accessible by integration (HTTP 403)")) == (403, False)
    assert ob.classify(ob.GhError("gh: You have exceeded a secondary rate limit (HTTP 403)")) == (403, True)
    assert ob.classify(ob.GhError("HTTP 429: Too Many Requests")) == (429, True)
    assert ob.classify(ob.GhError("gh exit 1: some unknown failure")) == (None, False)
    assert ob.classify(ob.GhError("gh timed out")) == (None, True)


def test_retries_give_up_after_the_last_delay():
    sleeps = []
    gh = FakeGh(fail=[ob.GhError("HTTP 502")] * 5)
    o = box(gh, sleeps=sleeps).post(5, "triage-stage1", "x")
    assert o.outcome == "failed" and o.attempts == len(ob.RETRY_DELAYS) + 1


def test_a_502_that_landed_anyway_is_not_sent_twice():
    gh = FakeGh(fail=[ob.GhError("HTTP 502")])
    gh.land_on_fail = True
    o = box(gh).post(5, "triage-stage1", "x")
    assert o.outcome == "sent" and len(gh.posts()) == 1 and len(gh.comments[5]) == 1


# ---- the ledger --------------------------------------------------------------------------

def test_the_ledger_carries_no_message_text(tmp_path, capsys):
    led = tmp_path / "ledger.jsonl"
    gh = FakeGh()
    b = box(gh, ledger=str(led))
    b.post(5, "triage-stage1", SECRET)
    b.post(5, "triage-stage1", SECRET)                 # deduped
    gh.fail = [ob.GhError("gh: Validation Failed (HTTP 422) " + SECRET)]
    b.post(6, "triage-stage1", SECRET + " other")      # failed: the error text echoes the body
    b.create_issue("ops-finding-issue", SECRET, SECRET)
    text = led.read_text() + capsys.readouterr().err
    assert "SENTINEL" not in text and "ghp_" not in text
    rows = [json.loads(line) for line in led.read_text().splitlines()]
    assert [r["outcome"] for r in rows] == ["sent", "deduped", "failed", "sent"]
    allowed = {"at", "kind", "target", "key", "outcome", "attempts", "status", "checked", "comment_id"}
    assert all(set(r) <= allowed for r in rows)


def test_a_refused_attempt_is_tallied_on_our_own_marker():
    body = "the same"
    m = ob.marker("provenance-unresolved", ob.key_for("provenance-unresolved", body))
    gh = FakeGh({5: [own(body + "\n" + m, cid=77)]})
    box(gh).post(5, "provenance-unresolved", body)
    box(gh).post(5, "provenance-unresolved", body)
    assert ob.parse_marker(gh.comments[5][0]["body"])["deduped"] == 2
    assert gh.comments[5][0]["body"].startswith(body), "only the marker is rewritten"


def test_tally_false_writes_nothing_back():
    body = "the same"
    m = ob.marker("triage-stage1", ob.key_for("triage-stage1", body))
    gh = FakeGh({5: [own(body + m)]})
    box(gh, tally=False).post(5, "triage-stage1", body)
    assert not [c for c in gh.calls if c[0] == "api"]


# ---- issues --------------------------------------------------------------------------------

def _issue(body, state="open", login="github-actions[bot]", at=NOW):
    return {"number": 1, "state": state, "created_at": iso(at), "user": {"login": login}, "body": body}


def test_an_open_issue_with_the_same_key_is_not_filed_again():
    k = ob.key_for("ops-finding-issue", "T\nB")
    gh = FakeGh(issues=[_issue("B" + ob.marker("ops-finding-issue", k))])
    assert box(gh).create_issue("ops-finding-issue", "T", "B").outcome == "deduped"


def test_a_closed_issue_is_not_a_duplicate_and_an_outsiders_marker_is_ignored():
    k = ob.key_for("ops-finding-issue", "T\nB")
    gh = FakeGh(issues=[_issue("B" + ob.marker("ops-finding-issue", k), state="closed"),
                        _issue("B" + ob.marker("ops-finding-issue", k), login="drive-by")])
    o = box(gh).create_issue("ops-finding-issue", "T", "B", ["chore"])
    assert o.outcome == "sent"
    post = next(c for c in gh.calls if c[:3] == ["api", "-X", "POST"])
    assert "labels[]=chore" in post and ob.marker("ops-finding-issue", k) in post[7]


# ---- CLI -----------------------------------------------------------------------------------

def test_cli_post_and_exit_codes(tmp_path):
    f = tmp_path / "b.md"
    f.write_text("hello")
    assert ob.main(["post", "--repo", REPO, "--issue", "5", "--kind", "triage-stage1",
                    "--body-file", str(f)], gh=FakeGh()) == 0
    bad = FakeGh(fail=[ob.GhError("HTTP 422")])
    assert ob.main(["post", "--repo", REPO, "--pr", "5", "--kind", "triage-stage1",
                    "--body-file", str(f)], gh=bad) == 1
    assert bad.posts()[0][0] == "pr"
    assert ob.main(["post", "--repo", "nope", "--issue", "5", "--kind", "k", "--body-file", str(f)],
                   gh=FakeGh()) == 2


# ---- the migrated posters go through it -------------------------------------------------------

def test_file_ops_findings_files_and_comments_through_the_outbox():
    fo = _load("file_ops_findings")

    class G(FakeGh):
        def __call__(self, args):
            if args[:2] == ["api", "--paginate"] and "creator=" in args[2]:
                return "\n".join(json.dumps({"number": 100 + k, "body": i["body"]})
                                 for k, i in enumerate(self.issues))
            if args[:2] == ["api", "--paginate"] and "/comments" in args[2]:
                return "\n".join(c["body"] for c in self.comments.get(int(args[2].split("/issues/")[1].split("/")[0]), []))
            if args[:3] == ["api", "-X", "POST"] and "/labels" in args[3] or args[:3] == ["api", "-X", "DELETE"]:
                return "{}"
            return super().__call__(args)

    gh = G()
    F = lambda level="amber", title="Claude weekly quota 90% used": {  # noqa: E731
        "kind": "claude-quota", "level": level, "title": title, "detail": "d", "where": ""}
    fo.carry(gh, REPO, [F()], "2026-11-17T00:00Z", box=box(gh))
    assert "kind=ops-finding-issue" in gh.issues[0]["body"]
    fo.carry(gh, REPO, [F("red", "Claude weekly quota 97% used")], "t2", box=box(gh))
    assert "kind=ops-finding " in gh.comments[100][0]["body"]
    # Two comments already today: a third change in the same day is capped, counted, not lost.
    fo.carry(gh, REPO, [], "t3", box=box(gh))
    s = fo.carry(gh, REPO, [F()], "t4", box=box(gh))
    assert s["suppressed"] == 1 and len(gh.comments[100]) == 2


def test_triage_comments_through_the_outbox():
    t = _load("triage_outsider_issues")
    calls = []

    def gh(args):
        calls.append(args)
        return t.Result(0, "", "")

    i = {"number": 5, "title": "x", "body": "no block", "createdAt": "2026-11-01T00:00:00Z",
         "labels": [], "comments": []}
    assert t.apply_decision(gh, REPO, i, t.decide(i, [i])) == []
    (post,) = [c for c in calls if c[:2] == ["issue", "comment"]]
    assert "kind=triage-stage1" in post[-1]


def test_a_failed_ops_post_is_still_exit_1_and_a_capped_triage_comment_adds_no_label():
    fo = _load("file_ops_findings")

    class NoOpenFindings(FakeGh):
        def __call__(self, args):
            if args[:2] == ["api", "--paginate"] and "creator=" in args[2]:
                return ""
            return super().__call__(args)

    gh = NoOpenFindings(fail=[ob.GhError("gh: Validation Failed (HTTP 422)")])
    F ={"kind": "claude-quota", "level": "amber", "title": "t", "detail": "d", "where": ""}
    with pytest.raises(RuntimeError, match="422"):
        fo.carry(gh, REPO, [F], "t1", box=box(gh))

    t = _load("triage_outsider_issues")
    calls = []

    def tgh(args):
        calls.append(args)
        return t.Result(0, "", "")

    i = {"number": 5, "title": "x", "body": "no block", "createdAt": "2026-11-01T00:00:00Z", "labels": [],
         "comments": [{"body": "a" + ob.marker("triage-stage1", "1" * 16), "viewerDidAuthor": True,
                       "createdAt": iso(datetime.now(timezone.utc))},
                      {"body": "b" + ob.marker("triage-stage1", "2" * 16), "viewerDidAuthor": True,
                       "createdAt": iso(datetime.now(timezone.utc))}]}
    assert t.apply_decision(tgh, REPO, i, t.decide(i, [i])) == []
    assert calls == [], "capped: no comment and no label, so the next run retries both"


def test_resolve_provenance_comments_through_the_outbox():
    rp = _load("resolve_provenance")
    calls = []

    def gh(args):
        calls.append(args)
        return rp.Result(0, json.dumps({"comments": []}) if args[1] == "view" else "", "")

    v = rp.Verdict(rp.UNRESOLVED, [], "a 502")
    assert rp.apply_verdict(gh, REPO, 5, v, set()) == []
    (post,) = [c for c in calls if c[:2] == ["issue", "comment"]]
    assert "kind=provenance-unresolved" in post[-1] and rp.UNRESOLVED_MARKER in post[-1]


# ---- nothing under scripts/ posts around it -----------------------------------------------------

#: How a script posts a comment or files an issue, in every spelling found in this repo
#: on 2026-11-17: porcelain in a shell, porcelain as an argv list, REST through `gh api`
#: (explicit POST, or implicit -- gh switches to POST when a field is given), GraphQL.
POSTING = [
    re.compile(r"\bgh\s+issue\s+(?:comment|create)\b|\bgh\s+pr\s+comment\b"),
    re.compile(r"""["']issue["']\s*,\s*["'](?:comment|create)["']|["']pr["']\s*,\s*["']comment["']"""),
    re.compile(r"""POST["']?\s*,?\s*f?["']?repos/[^"'\s]*/(?:comments|issues)["'\s]"""),
    re.compile(r"""/comments["']?\s*,?\s*["']?-[fF]["']?\s*,?\s*f?["']?body="""),
    re.compile(r"\baddComment\b|\bcreateIssue\b"),
]

#: Scripts allowed to post WITHOUT the outbox, each with its reason. Keep it short.
ALLOWED = {
    # The outbox is the path.
    "scripts/outbox.py": "the posting path itself",
    # #1185-#1187 (inbox, liveness, timers) are being built in parallel by another
    # engineer on these files; migrating them here would make the two PRs conflict.
    # Remaining work, named in #1188's PR. Not checked for staleness: they may move.
    "scripts/cycle_queue.py": "#1185 in flight",
    "scripts/dispatch_cycle.sh": "#1185 in flight",
    "scripts/chain_cycle.py": "#1185 in flight",
    "scripts/red_gates.py": "#1185 in flight",
    "scripts/pr_fix_after_qa.py": "#1185 in flight",
    "scripts/timers.py": "#1187 in flight",
    "scripts/liveness.py": "#1186 in flight",
    # The QA verdict comment is SHA-BOUND and is agent-merge's merge trigger: the
    # outbox normalises SHAs, so it would dedupe a PASS at a new head against the PASS
    # at the old one and the PR would never merge. qa_verdict.sh stays the only writer.
    "scripts/qa_verdict.sh": "SHA-bound verdict, the merge trigger",
}
# scripts/mutations/ is not scanned: its rows carry posting CODE as text to inject
# into a sandbox copy, and post nothing themselves.
_IN_FLIGHT = {k for k, v in ALLOWED.items() if v.endswith("in flight")}


def _posters():
    out = {}
    for p in sorted(SCRIPTS.rglob("*")):
        if p.suffix not in (".py", ".sh") or "mutations" in p.relative_to(SCRIPTS).parts:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        hits = [rx.pattern[:30] for rx in POSTING if rx.search(text)]
        if hits:
            out[str(p.relative_to(ROOT))] = hits
    return out


def test_no_script_posts_a_comment_or_issue_without_the_outbox():
    rogue = {k: v for k, v in _posters().items() if k not in ALLOWED}
    assert rogue == {}, ("these scripts post without scripts/outbox.py (#1188) -- route them "
                         f"through Outbox.post / create_issue, or justify an ALLOWED entry: {rogue}")


def test_the_allow_list_is_not_stale():
    found = _posters()
    stale = [k for k in ALLOWED if k not in _IN_FLIGHT and k not in found]
    assert stale == [], f"no longer posts, so remove it from ALLOWED: {stale}"


def test_the_scanner_can_go_red():
    for snippet in ('gh issue comment "$N" --body x', 'gh(["issue", "comment", n])',
                    'gh(["api", "-X", "POST", f"repos/{repo}/issues/{n}/comments", "-f", "b"])',
                    'gh api "repos/$R/issues/$N/comments" -f body="x"',
                    'gh(["api", "-X", "POST", f"repos/{repo}/issues", "-f", "title=x"])'):
        assert any(rx.search(snippet) for rx in POSTING), snippet
    for benign in ('gh(["api", "-X", "POST", f"repos/{repo}/issues/{n}/labels"])', "gh pr create --fill",
                   'gh api "repos/$R/issues/$N/comments?since=$t"'):
        assert not any(rx.search(benign) for rx in POSTING), benign
