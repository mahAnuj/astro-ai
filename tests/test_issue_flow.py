"""Issue flow (2026-11-18): the `trend` block of measurements/issues.json, the
"Issue flow" panel on /admin/ops, and the `fixes-not-closing` finding.

Owner: "Many prs have been merged but I don't see issue count reducing". The open
count cannot say whether findings are arriving faster or fixes are not closing;
these tests pin the arithmetic that says which -- every source and closer bucket,
the walk-back of the open count, and merged-but-open -- against an in-memory
GitHub, then render the panel through the real route in all three states."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import issue_backlog, llm_stats, ops_data

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


flow = _load("issue_flow")
cib = _load("collect_issue_backlog")
det = _load("detect_ops_regressions")

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
REPO = "mahAnuj/astro-ai"
SECRET = "SENTINEL-comment-text-7f3"


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def day(d, h=10):
    """An instant on 2026-11-<d> (or 2026-<m>-<d> for a tuple)."""
    m, d = d if isinstance(d, tuple) else (11, d)
    return datetime(2026, m, d, h, 0, tzinfo=timezone.utc)


def issue(n, *, by="claude[bot]", created, closed=None, title=None, labels=()):
    return {"number": n, "title": title or f"issue {n}", "user": {"login": by},
            "state": "closed" if closed else "open",
            "created_at": iso(created), "updated_at": iso(closed or created),
            "closed_at": iso(closed) if closed else None,
            "labels": [{"name": x} for x in labels]}


def closed_ev(actor, at):
    return {"event": "closed", "actor": {"login": actor}, "created_at": iso(at)}


def comment_ev(actor, at, body):
    return {"event": "commented", "actor": {"login": actor}, "user": {"login": actor},
            "created_at": iso(at), "body": body}


def pr(n, *, merged_ago_h, body="", ref="feat/x", title="a change"):
    merged = iso(NOW - timedelta(hours=merged_ago_h)) if merged_ago_h is not None else None
    return {"number": n, "title": title, "body": body, "head": {"ref": ref},
            "merged_at": merged, "updated_at": merged or iso(NOW - timedelta(hours=1))}


def corpus():
    """(items, timelines, prs, open_issues). Expected buckets are in the names."""
    c = day
    items = [
        issue(101, by="mahAnuj", created=c(18)),                              # audit, open
        issue(102, by="claude[bot]", created=c(17)),                          # loop, open
        issue(103, by="github-actions[bot]", created=c(17, 11), title="[OPS] cache low"),  # ops, open
        issue(104, by="drive-by", created=c(16), closed=c(17)),              # outsider; close-on-evidence
        issue(105, created=c((10, 1)), closed=c(17, 12)),                    # prioritise (claude[bot])
        issue(106, created=c((10, 1)), closed=c(16), labels=("cannot-reproduce",)),
        issue(107, by="github-actions[bot]", created=c((10, 1)), closed=c(16, 12)),  # main-red-report
        issue(108, created=c((10, 1)), closed=c(15)),                        # owner by hand
        issue(109, created=c((10, 1)), closed=c(15, 11)),                    # owner's "Closing:" = /prioritise
        issue(110, created=c((10, 1)), closed=c(15, 12)),                    # other
        issue(111, created=c((10, 1)), closed=c(15, 13)),                    # coe, analyst comments after
        issue(112, created=c((9, 1)), closed=c((9, 2))),                     # before the window
        {**issue(900, created=c(18)), "pull_request": {"url": "x"}},         # a PR: never counted
    ]
    at = {it["number"]: datetime.fromisoformat(it["closed_at"].replace("Z", "+00:00"))
          for it in items if it.get("closed_at")}
    s = timedelta(seconds=2)
    timelines = {
        104: [comment_ev("github-actions[bot]", at[104] - s, f"Closed on production evidence.\n\n{SECRET}"),
              closed_ev("github-actions[bot]", at[104])],
        105: [comment_ev("claude[bot]", at[105] - s, "**Closing: already fixed (measured at abc1234).**"),
              closed_ev("claude[bot]", at[105])],
        106: [comment_ev("claude[bot]", at[106] - s, "five samples, none reproduce"),
              closed_ev("claude[bot]", at[106])],
        107: [comment_ev("github-actions[bot]", at[107] - s, "Green again on `main` at `abc`\n\nClosing: gates passed"),
              closed_ev("github-actions[bot]", at[107])],
        # Owner closes by hand; the analyst's score lands LATER and must not decide it.
        108: [closed_ev("mahAnuj", at[108]),
              comment_ev("claude[bot]", at[108] + timedelta(hours=3), "**Closing: analyst score**")],
        109: [comment_ev("mahAnuj", at[109] - s, "Closing: duplicate of #5, which covers it."),
              closed_ev("mahAnuj", at[109])],
        110: [closed_ev("someone-else", at[110])],
        111: [comment_ev("github-actions[bot]", at[111] - s, "Closed on production evidence."),
              closed_ev("github-actions[bot]", at[111]),
              comment_ev("claude[bot]", at[111] + timedelta(hours=1), "analyst, not scoreable"),
              comment_ev("github-actions[bot]", at[111] + timedelta(hours=2), "<!-- agent-timer -->")],
    }
    prs = [
        pr(201, merged_ago_h=48, body="closes #101"),                         # merged-but-open
        pr(202, merged_ago_h=2, body="fixes #102"),                           # too recent
        pr(203, merged_ago_h=30, ref="issue/103-ops-cache"),                  # branch fallback
        pr(204, merged_ago_h=30, ref="issue/102-partial", body="Refs #102 -- part 1"),  # refs only
        pr(205, merged_ago_h=None, body="closes #103"),                       # never merged
        pr(206, merged_ago_h=50, body="resolves #104"),                       # its issue is closed
    ]
    open_issues = [{"number": n, "title": f"issue {n}"} for n in (101, 102, 103, 50, 51)]
    return items, timelines, prs, open_issues


class FakeGh:
    def __init__(self, items, timelines, prs):
        self.items, self.timelines, self.prs, self.calls = items, timelines, prs, []

    def __call__(self, args):
        url = args[1]
        self.calls.append(url)
        page = int(url.rsplit("page=", 1)[1])
        if "/timeline" in url:
            n = int(url.split("/issues/")[1].split("/")[0])
            rows = self.timelines.get(n, [])
        elif "/pulls" in url:
            rows = self.prs
        else:
            rows = self.items
        return json.dumps(rows[(page - 1) * 100: page * 100])


def _collect(prior=None, **over):
    items, tl, prs, open_issues = corpus()
    gh = FakeGh(items, tl, prs)
    return flow.collect(gh, REPO, NOW, open_issues=open_issues, prior=prior), gh


def _days(doc):
    return {d["date"]: d for d in doc["days"]}


# ---- the collector's arithmetic ------------------------------------------------------

def test_every_source_is_classified():
    d = _days(_collect()[0])
    assert d["2026-11-18"]["opened_by"] == {"audit": 1}
    assert d["2026-11-17"]["opened_by"] == {"loop": 1, "ops": 1}
    assert d["2026-11-16"]["opened_by"] == {"outsider": 1}


def test_every_closer_is_classified_from_the_closing_comment_not_the_last_one():
    d = _days(_collect()[0])
    assert d["2026-11-17"]["closed_by"] == {"close-on-evidence": 1, "prioritise": 1}
    assert d["2026-11-16"]["closed_by"] == {"cannot-reproduce": 1, "main-red-report": 1}
    assert d["2026-11-15"]["closed_by"] == {"close-on-evidence": 1, "prioritise": 1,
                                            "owner": 1, "other": 1}


def test_opened_closed_net_and_the_open_count_walked_back_from_now():
    doc = _collect()[0]
    d = _days(doc)
    assert len(doc["days"]) == 28 and doc["days"][-1]["date"] == "2026-11-18"
    assert doc["days"][0]["date"] == "2026-10-22"
    assert doc["open_now"] == 5
    row = lambda k: (d[k]["opened"], d[k]["closed"], d[k]["net"], d[k]["open_end"])  # noqa: E731
    assert row("2026-11-18") == (1, 0, 1, 5)
    assert row("2026-11-17") == (2, 2, 0, 4)
    assert row("2026-11-16") == (1, 2, -1, 4)
    assert row("2026-11-15") == (0, 4, -4, 5)
    assert row("2026-11-14") == (0, 0, 0, 9)
    assert sum(x["opened"] for x in doc["days"]) == 4, "the PR item and older issues never count"
    assert sum(x["closed"] for x in doc["days"]) == 8, "#112 closed before the window"


def test_merged_but_open_reads_claims_as_close_on_evidence_does():
    mo = _collect()[0]["merged_open"]
    assert [(r["number"], r["pr"]) for r in mo] == [(101, 201), (103, 203)]
    assert mo[0]["hours"] == 48 and mo[0]["title"] == "issue 101"


def test_claims_keyword_branch_and_refs():
    assert flow.claims({"title": "x", "body": "Fixes #7 and closes #8", "head": {"ref": "issue/9-z"}}) == {7, 8}
    assert flow.claims({"title": "x", "body": "", "head": {"ref": "issue/9-z"}}) == {9}
    assert flow.claims({"title": "x", "body": "Refs #9", "head": {"ref": "issue/9-z"}}) == set()
    assert flow.claims({"title": "x (#9)", "body": "", "head": {"ref": "feat/9"}}) == set()


def test_closers_already_read_are_carried_forward_not_refetched():
    first, gh1 = _collect()
    assert sum("/timeline" in c for c in gh1.calls) == 8
    second, gh2 = _collect(prior=first)
    assert sum("/timeline" in c for c in gh2.calls) == 0
    assert second["days"] == first["days"]
    # A closed_at that moved (closed, reopened, closed again) is read again.
    moved = {**first, "closed_rows": [dict(r, closed_at="2026-01-01T00:00:00Z")
                                      if r["number"] == 104 else r for r in first["closed_rows"]]}
    _, gh3 = _collect(prior=moved)
    assert [c for c in gh3.calls if "/timeline" in c] == [f"repos/{REPO}/issues/104/timeline?per_page=100&page=1"]


def test_a_page_cap_marks_the_block_truncated(monkeypatch):
    monkeypatch.setattr(flow, "MAX_LIST_PAGES", 1)
    many = [issue(1000 + k, created=day(18)) for k in range(100)]
    doc = flow.collect(FakeGh(many, {}, []), REPO, NOW, open_issues=[])
    assert f"repos/{REPO}/issues" in doc["truncated"]
    assert _collect()[0]["truncated"] == []


def test_a_timeline_cap_counts_the_rest_unread(monkeypatch):
    monkeypatch.setattr(flow, "MAX_TIMELINES", 2)
    doc = _collect()[0]
    assert "timelines" in doc["truncated"] and doc["timelines_read"] == 2
    unread = sum(x["closed_by"].get("unread", 0) for x in doc["days"])
    assert unread == 6


def test_the_block_carries_no_comment_text_and_no_login():
    text = json.dumps(_collect()[0])
    assert SECRET not in text and "Closed on production" not in text
    for login in ("drive-by", "someone-else", "mahAnuj", "claude[bot]"):
        assert login not in text


def test_the_backlog_is_written_even_when_the_trend_cannot_be(tmp_path, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("gh api: HTTP 502")
    monkeypatch.setattr(cib.issue_flow, "collect", broken)
    out = tmp_path / "issues.json"
    t = cib.trend(REPO, [], out)
    assert t == {"error": "RuntimeError: gh api: HTTP 502"}


def test_the_collector_wires_the_trend_and_from_json_skips_it(tmp_path, monkeypatch):
    src = (ROOT / "scripts" / "collect_issue_backlog.py").read_text()
    assert 'doc["trend"] = trend(args.repo, issues, out)' in src
    raw = tmp_path / "raw.json"
    raw.write_text("[]")
    out = tmp_path / "issues.json"
    monkeypatch.chdir(tmp_path)
    assert cib.main(["--from-json", str(raw), "--out", str(out)]) == 0
    assert "trend" not in json.loads(out.read_text())


# ---- the detector --------------------------------------------------------------------

def _find(tmp_path, monkeypatch, trend):
    m = tmp_path / "measurements"
    m.mkdir(parents=True, exist_ok=True)
    doc = issue_backlog.build([], repo=REPO, generated_at=iso(NOW))
    if trend is not None:
        doc["trend"] = trend
    (m / "issues.json").write_text(json.dumps(doc))
    monkeypatch.setattr(det, "ROOT", tmp_path)
    monkeypatch.setattr(det, "MEASUREMENTS", m)
    return det.find(now=NOW)


def _mo(k):
    return {"merged_open_hours": 24,
            "merged_open": [{"number": 300 + i, "title": "t", "pr": 400 + i,
                             "merged_at": iso(NOW - timedelta(hours=30)), "hours": 30}
                            for i in range(k)]}


def test_three_merged_but_open_fires_fixes_not_closing(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _mo(3))
    hit = next(x for x in f if x["kind"] == "fixes-not-closing")
    assert hit["level"] == "amber" and hit["title"].startswith("3 issues")
    assert "#300 (PR #400, 30h)" in hit["detail"] and "#302" in hit["detail"]
    assert "close-on-evidence" in hit["detail"] and "verify-production" in hit["detail"]


def test_two_or_none_clears_it(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _mo(2))
    assert "fixes-not-closing" not in {x["kind"] for x in f}
    f, _ = _find(tmp_path / "b", monkeypatch, None)
    assert "fixes-not-closing" not in {x["kind"] for x in f}


def test_the_detector_and_the_page_share_one_threshold():
    assert det.FIXES_NOT_CLOSING_MIN is ops_data.FIXES_NOT_CLOSING_MIN == 3


# ---- the panel -----------------------------------------------------------------------

@pytest.fixture
def page(client, monkeypatch, tmp_path):
    def render(issues_doc, tab="backlog"):
        d = tmp_path / "m"
        d.mkdir(exist_ok=True)
        if issues_doc is not None:
            (d / "issues.json").write_text(json.dumps(issues_doc))
        monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
        monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
        monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "stats")
        monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
        monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
        monkeypatch.setattr(ops_data, "RAW_BASE", "http://127.0.0.1:9/none")
        monkeypatch.setenv("OPS_MEASUREMENTS_DIR", str(d))
        ops_data._cache.clear()
        ops_data._app_cache.clear()
        try:
            r = client.get(f"/admin/ops?tab={tab}", auth=("admin", "bhagya-dev"))
        finally:
            ops_data._cache.clear()
            ops_data._app_cache.clear()
        assert r.status_code == 200, r.text[:500]
        return r.text
    return render


def _section(html):
    i = html.index('id="issue-flow"')
    return html[i: html.index("</section>", i)]


def _backlog(trend):
    doc = issue_backlog.build([], repo=REPO, generated_at=iso(datetime.now(timezone.utc)))
    if trend is not None:
        doc["trend"] = trend
    return doc


def test_the_panel_renders_the_chart_breakdowns_merged_open_and_reading(page):
    s = _section(page(_backlog(_collect()[0])))
    # Week ending 11-18: 4 opened, 8 closed; open 9 at the end of 11-11 -> 5 now.
    assert ("Open count fell 4 in the last 7 days: 4 opened (1 audit / session (owner)), "
            "8 closed (2 close-on-evidence).") in s
    assert "Issues are closing at least as fast" in s
    assert "<polyline" in s and s.count('class="f-opened"') >= 4 and s.count('class="f-closed"') >= 3
    assert "red-main sentinel cleared" in s and "CANNOT-REPRODUCE" in s and "owner, by hand" in s
    assert "[OPS] findings" in s and "outsiders" in s
    assert 'href="https://github.com/mahAnuj/astro-ai/issues/101"' in s and "PR #201 merged 48h ago" in s
    assert "Merged but still open · 2" in s
    assert SECRET not in s


def test_the_reading_names_fixes_not_closing_at_the_threshold(page):
    t = _collect()[0]
    t["merged_open"] = _mo(3)["merged_open"]
    s = _section(page(_backlog(t)))
    assert "3 issues are still open more than 24h after a merged PR claimed them" in s
    assert 'class="hot"' in s


def test_the_panel_says_so_when_the_window_is_empty(page):
    items, tl, prs, _ = corpus()
    empty = flow.collect(FakeGh([], {}, []), REPO, NOW, open_issues=[])
    s = _section(page(_backlog(empty)))
    assert "No issues opened or closed in the last 28 days" in s and "<polyline" not in s


def test_the_panel_says_so_when_the_trend_or_the_file_is_missing(page):
    s = _section(page(_backlog(None)))
    assert "not in <code>measurements/issues.json</code> yet" in s and "<polyline" not in s
    s = _section(page(None))
    assert "not in <code>measurements/issues.json</code> yet" in s


def test_the_panel_shows_a_recorded_collector_error(page):
    s = _section(page(_backlog({"error": "RuntimeError: gh api: HTTP 502"})))
    assert "could not be collected" in s and "HTTP 502" in s and "<polyline" not in s


# ---- PR merge time (owner, 2026-11-19: "track the max time a PR took to merge") ----------

PR_NOW = datetime(2026, 11, 20, 6, 0, tzinfo=timezone.utc)


def _merged(n, created, merged, title="fix: thing", ref="issue/1-x"):
    return {"number": n, "title": title, "user": {"login": "claude[bot]"},
            "created_at": created, "merged_at": merged, "head": {"ref": ref}}


def test_pr_flow_reports_median_p90_and_the_max_and_names_the_slowest():
    merged = [_merged(1, "2026-11-19T00:00:00Z", "2026-11-19T00:30:00Z"),
              _merged(2, "2026-11-18T00:00:00Z", "2026-11-18T02:00:00Z"),
              _merged(3, "2026-11-16T00:00:00Z", "2026-11-18T00:00:00Z"),   # 48h, the slowest
              _merged(4, "2026-11-01T00:00:00Z", "2026-11-03T00:00:00Z")]   # outside 7d, inside 28d
    w = flow.pr_flow(merged, [], PR_NOW)["windows"]
    assert w["7d"]["merged"] == 3 and w["7d"]["max_h"] == 48.0 and w["7d"]["median_h"] == 2.0
    assert w["7d"]["slowest"][0]["number"] == 3
    assert w["28d"]["merged"] == 4


def test_pr_flow_excludes_the_automated_measurement_prs():
    merged = [_merged(1, "2026-11-19T00:00:00Z", "2026-11-19T00:01:00Z", ref="measurements/9-1"),
              _merged(2, "2026-11-19T00:00:00Z", "2026-11-19T00:01:00Z", title="sync report 2026-11-19"),
              _merged(3, "2026-11-19T00:00:00Z", "2026-11-19T05:00:00Z")]
    w = flow.pr_flow(merged, [], PR_NOW)["windows"]["7d"]
    assert w["merged"] == 1 and w["median_h"] == 5.0


def test_open_prs_are_listed_oldest_first_with_what_they_wait_on():
    op = [{"number": 7, "title": "a", "created_at": "2026-11-19T18:00:00Z", "head": {"ref": "x"},
           "labels": [{"name": "qa-fail"}]},
          {"number": 8, "title": "b", "created_at": "2026-11-18T06:00:00Z", "head": {"ref": "y"},
           "labels": [{"name": "needs-human-review"}, {"name": "qa-pass"}]}]
    o = flow.pr_flow([], op, PR_NOW)["open"]
    assert [r["number"] for r in o] == [8, 7] and o[0]["age_h"] == 48.0
    assert o[0]["waiting_on"] == "chief (trust boundary)" and o[1]["waiting_on"] == "a fix after QA failed"


def test_the_ops_page_shows_merge_time_and_the_slowest(page):
    t = _collect()[0]
    t["pr_flow"] = flow.pr_flow([_merged(3, "2026-11-16T00:00:00Z", "2026-11-18T00:00:00Z", title="slow one")],
                                [], PR_NOW)
    t["pr_flow"]["windows"]["7d"]["slowest"][0]["why"] = {"reason": "45.5h gates red", "primary": "gates_red"}
    t["pr_flow"]["windows"]["7d"]["top_reasons"] = flow.top_reasons(t["pr_flow"]["windows"]["7d"]["slowest"])
    html = page(_backlog(t), tab="runs")  # PR merge time lives on the Runs & Traces tab
    i = html.index('id="pr-merge-time"')
    s = html[i: html.index("</section>", i)]
    assert "48.0h" in s and "slow one" in s and "Slowest" in s and "pr-median" in s
    assert "45.5h gates red" in s and "Top delay reasons" in s and "1 PR" in s


def test_the_ops_page_survives_a_malformed_pr_flow(page):
    t = _collect()[0]
    t["pr_flow"] = {"windows": "x"}
    assert "Not collected yet" in page(_backlog(t), tab="runs")
    # Past the shape check, broken inside: a day whose date is not a string.
    t["pr_flow"] = {"windows": {}, "days": [{"date": 20261119, "merged": 1, "max_h": 2.0, "median_h": 1.0}]}
    assert "Not collected yet" in page(_backlog(t), tab="runs")


# ---- why a PR was slow: each PR's own timeline, replayed (owner: "this should be dynamic") ----

T0 = datetime(2026, 11, 18, 0, 0, tzinfo=timezone.utc)


def _at(h):
    return iso(T0 + timedelta(hours=h))


def _run(h0, h1, conclusion, name="gates"):
    return {"name": name, "started_at": _at(h0), "completed_at": _at(h1), "conclusion": conclusion}


def _verdict(h, ok):
    return {"created_at": _at(h), "body": ("QA: PASS" if ok else "QA: FAIL") + " — verified at x"}


def _why(end_h, commits, checks, comments=(), events=()):
    return flow.delay_reason(T0, T0 + timedelta(hours=end_h), commits, checks, list(comments), list(events))


def test_red_gates_that_sat_unfixed_are_named():
    """#1121: 45h with gates red after its push."""
    w = _why(46, [{"sha": "a", "at": _at(0)}], {"a": [_run(0.1, 0.5, "failure")]})
    assert w["primary"] == "gates_red" and w["reason"].startswith("45.5h gates red")


def test_a_fail_loop_counts_each_wait_for_a_fix_although_the_label_went_on_once():
    """#1212: `qa-fail` labelled once, five FAILs. Each FAIL starts a wait for a fix; each push
    ends it and the PR waits on gates and QA again."""
    commits = [{"sha": "a", "at": _at(0)}, {"sha": "b", "at": _at(10)}, {"sha": "c", "at": _at(20)}]
    checks = {"a": [_run(0.1, 0.5, "success")], "b": [_run(10.1, 10.5, "success")],
              "c": [_run(20.1, 20.5, "success")]}
    comments = [_verdict(1, False), _verdict(11, False), _verdict(21, True)]
    events = [{"event": "labeled", "created_at": _at(1), "label": {"name": "qa-fail"}}]
    w = _why(21.5, commits, checks, comments, events)
    assert w["hours"]["qa_fail"] == 18.0 and w["qa_fails"] == 2
    assert w["reason"].startswith("18.0h waiting for a fix after QA failed (2 QA FAILs)")


def test_a_held_pr_is_held_whatever_else_is_true():
    commits = [{"sha": "a", "at": _at(0)}]
    checks = {"a": [_run(0.1, 0.5, "success")]}
    events = [{"event": "labeled", "created_at": _at(1), "label": {"name": "needs-human-review"}}]
    w = _why(31, commits, checks, [_verdict(0.8, True)], events)
    assert w["primary"] == "held" and "30.0h held for chief" in w["reason"]


def test_a_quick_pr_has_no_dominant_wait():
    w = _why(0.3, [{"sha": "a", "at": _at(0)}], {"a": [_run(0.0, 0.2, "success")]}, [_verdict(0.25, True)])
    assert w["reason"] == "no single wait stood out"


def test_an_unreadable_pr_gets_no_reason_rather_than_a_guess():
    rows = [{"number": 5}]

    def down(args):
        raise RuntimeError("HTTP 502")
    flow.explain(down, "o/r", rows, PR_NOW)
    assert rows[0]["why"] is None
