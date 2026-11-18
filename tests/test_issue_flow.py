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
    def render(issues_doc):
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
            r = client.get("/admin/ops", auth=("admin", "bhagya-dev"))
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
