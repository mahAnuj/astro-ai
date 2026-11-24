"""The outbox's noise evals (#1188): the collector that writes measurements/outbox.json,
the `outbox-noise` finding, and the /admin/ops panel.

The evals are computed from EVERY comment the loop's identities wrote, through the
outbox or not -- a quiet number must mean the loop is quiet, not that the three
migrated scripts are. The panel is rendered through the real route in all three
states a reader can meet: data, an empty window, and no file yet."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from astro_ai import llm_stats, ops_data

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


co = _load("collect_outbox")
ob = sys.modules["outbox"]
det = _load("detect_ops_regressions")

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
REPO = "mahAnuj/astro-ai"
SECRET = "SENTINEL-private-words-91c"


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def comment(n, body, *, login="claude[bot]", ago_h=1, pr=True, updated_ago_h=None):
    kind = "pull" if pr else "issues"
    return {"issue_url": f"https://api.github.com/repos/{REPO}/issues/{n}",
            "html_url": f"https://github.com/{REPO}/{kind}/{n}#issuecomment-{n}{ago_h}",
            "user": {"login": login}, "body": body,
            "created_at": iso(NOW - timedelta(hours=ago_h)),
            "updated_at": iso(NOW - timedelta(hours=updated_ago_h if updated_ago_h is not None else ago_h))}


class FakeGh:
    def __init__(self, comments, issues=()):
        self.comments, self.issues, self.calls = comments, list(issues), []

    def __call__(self, args):
        self.calls.append(args)
        url = args[1]
        rows = self.comments if "/issues/comments" in url else self.issues
        page = int(url.rsplit("page=", 1)[1])
        return json.dumps(rows[(page - 1) * 100: page * 100])


def corpus():
    m = ob.marker("ops-finding", "a" * 16, {"deduped": 2, "capped": 1})
    return [
        # PR 10: the same QA note three times about different heads -> two duplicates.
        comment(10, f"{SECRET} gates red at `3f9c2ab`", ago_h=5),
        comment(10, f"{SECRET} gates red at `77aa01f`", ago_h=4),
        comment(10, f"{SECRET} gates red at `0b1c2d3`", ago_h=3),
        comment(10, "looks good", login="mahAnuj", ago_h=2),
        # PR 11: one loop comment, no owner.
        comment(11, "QA: PASS", ago_h=2),
        # Issue 20: an outbox message carrying tallies, edited inside the window.
        comment(20, "Now AMBER\n" + m, login="github-actions[bot]", pr=False, ago_h=200, updated_ago_h=3),
        comment(20, "Now RED\n" + ob.marker("ops-finding", "b" * 16), login="github-actions[bot]", pr=False, ago_h=6),
        # An outsider's copy of the marker counts for nothing.
        comment(20, "spoof " + ob.marker("ops-finding", "c" * 16, {"deduped": 50}), login="drive-by", pr=False, ago_h=1),
        # The previous window.
        comment(12, "an older note", ago_h=24 * 9),
    ]


def test_the_collector_counts_threads_duplicates_tallies_and_the_owner():
    doc = co.collect(FakeGh(corpus()), REPO, NOW)
    cur, prev = doc["current"], doc["previous"]
    assert cur["loop_comments"] == 5                       # 3 + 1 on PRs, 1 on the issue (the 200h one is older)
    assert (cur["on_prs"], cur["prs"], cur["comments_per_pr"]) == (4, 2, 2.0)
    assert (cur["on_issues"], cur["issues"], cur["comments_per_issue"]) == (1, 1, 1.0)
    assert cur["duplicates"] == 2 and cur["duplicate_rate_pct"] == 40.0
    assert cur["sent_by_kind"] == {"ops-finding": 1} and cur["via_outbox"] == 1
    assert cur["suppressed"] == {"deduped": 2, "capped": 1, "failed": 0}, "the outsider's 50 is ignored"
    assert cur["owner_touched"] == {"prs": 2, "owner_commented": 1, "pct": 50}
    assert prev["loop_comments"] == 2 and "suppressed" not in prev   # the 200h and the 9-day one
    assert cur["top_threads"][0] == {"on": "pr", "number": 10, "comments": 3}


def test_outbox_json_never_carries_comment_text_or_logins(tmp_path):
    out = tmp_path / "outbox.json"
    assert co.write(FakeGh(corpus()), REPO, out, NOW) == 0
    text = out.read_text()
    assert SECRET not in text and "gates red" not in text and "drive-by" not in text
    assert "mahAnuj" not in text


def test_an_unreadable_api_leaves_the_previous_file_standing(tmp_path):
    out = tmp_path / "outbox.json"
    out.write_text('{"old": true}')

    def broken(args):
        raise RuntimeError("gh api: HTTP 502")

    assert co.write(broken, REPO, out, NOW) == 1
    assert out.read_text() == '{"old": true}'


def test_collect_lessons_writes_outbox_json_before_running_the_detector(tmp_path):
    cl = _load("collect_lessons")
    order = []

    def gh(args):
        if "/issues/comments" in args[1] and not (tmp_path / "outbox.json").exists():
            order.append("outbox-read")
        return "{\"workflow_runs\": []}" if "/actions/" in args[1] else "[]"

    def ops():
        order.append("detector" + (" saw outbox.json" if (tmp_path / "outbox.json").exists() else ""))
        return []

    assert cl.main(["x", "--repo", REPO, "--out-dir", str(tmp_path)], gh=gh, now=NOW, ops=ops) == 0
    assert order[-1] == "detector saw outbox.json"


# ---- the detector ---------------------------------------------------------------------

def _window(loop=40, dup=2.0, per_pr=2.0, prs=10):
    return {"loop_comments": loop, "duplicate_rate_pct": dup, "comments_per_pr": per_pr, "prs": prs,
            "via_outbox": 3, "top_threads": [{"on": "pr", "number": 10, "comments": 9}]}


def _find(tmp_path, monkeypatch, doc):
    m = tmp_path / "measurements"
    m.mkdir(parents=True, exist_ok=True)
    if doc is not None:
        (m / "outbox.json").write_text(json.dumps(doc))
    monkeypatch.setattr(det, "ROOT", tmp_path)
    monkeypatch.setattr(det, "MEASUREMENTS", m)
    return det.find(now=NOW)


def _doc(cur, prev, generated=NOW):
    return {"generated_at": iso(generated), "window_days": 7, "current": cur, "previous": prev}


def test_a_duplicate_rate_rise_fires_outbox_noise(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _doc(_window(dup=6.0), _window(dup=2.0)))
    hit = next(x for x in f if x["kind"] == "outbox-noise")
    assert "duplicate rate 2.0% -> 6.0%" in hit["title"] and "#10 (9)" in hit["detail"]


def test_a_comments_per_pr_rise_fires_outbox_noise(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _doc(_window(per_pr=3.5), _window(per_pr=2.0)))
    assert "comments per PR 2.0 -> 3.5" in next(x for x in f if x["kind"] == "outbox-noise")["title"]


def test_a_rise_at_or_under_fifty_percent_clears(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _doc(_window(dup=3.0, per_pr=3.0), _window(dup=2.0, per_pr=2.0)))
    assert "outbox-noise" not in {x["kind"] for x in f}


def test_a_small_sample_never_fires(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _doc(_window(loop=10, dup=30.0, per_pr=9.0), _window(loop=10)))
    assert "outbox-noise" not in {x["kind"] for x in f}
    f, _ = _find(tmp_path / "b", monkeypatch, _doc(_window(per_pr=9.0, prs=3), _window(prs=3)))
    assert "outbox-noise" not in {x["kind"] for x in f}


def test_a_duplicate_rate_from_zero_fires_only_past_the_floor(tmp_path, monkeypatch):
    f, _ = _find(tmp_path, monkeypatch, _doc(_window(dup=2.0), _window(dup=0.0)))
    assert "outbox-noise" not in {x["kind"] for x in f}
    f, _ = _find(tmp_path / "b", monkeypatch, _doc(_window(dup=5.0), _window(dup=0.0)))
    assert "outbox-noise" in {x["kind"] for x in f}


def test_a_truncated_read_is_unreadable_never_a_rise(tmp_path, monkeypatch):
    doc = _doc(_window(dup=9.0), _window(dup=2.0))
    doc["truncated"] = ["repos/o/r/issues/comments"]
    f, unread = _find(tmp_path, monkeypatch, doc)
    assert "outbox-noise" not in {x["kind"] for x in f} and any("truncated" in u for u in unread)


def test_the_collector_flags_a_page_cap(monkeypatch):
    monkeypatch.setattr(co, "MAX_PAGES", 1)
    many = [comment(10, f"note {k}", ago_h=1) for k in range(100)]
    assert co.collect(FakeGh(many), REPO, NOW)["truncated"] == [f"repos/{REPO}/issues/comments"]
    assert co.collect(FakeGh(many[:5]), REPO, NOW)["truncated"] == []


def test_no_file_is_no_finding_and_a_stale_one_is_unreadable(tmp_path, monkeypatch):
    f, unread = _find(tmp_path, monkeypatch, None)
    assert "outbox-noise" not in {x["kind"] for x in f} and not any("outbox" in u for u in unread)
    f, unread = _find(tmp_path / "b", monkeypatch,
                      _doc(_window(dup=9.0), _window(), generated=NOW - timedelta(days=3)))
    assert "outbox-noise" not in {x["kind"] for x in f} and any("outbox.json" in u for u in unread)


# ---- the panel ------------------------------------------------------------------------

@pytest.fixture
def page(client, monkeypatch, tmp_path):
    def render(files: dict):
        d = tmp_path / "m"
        d.mkdir(exist_ok=True)
        for name, doc in files.items():
            (d / name).write_text(json.dumps(doc))
        monkeypatch.setenv("ADMIN_PASSWORD", "bhagya-dev")
        monkeypatch.delenv("BHAGYA_STORAGE_BUCKET", raising=False)
        monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path / "stats")
        monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
        monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
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
    i = html.index('id="outbox"')
    return html[i: html.index("</section>", i)]


def test_the_panel_renders_the_evals(page):
    doc = co.collect(FakeGh(corpus()), REPO, NOW)
    s = _section(page({"outbox.json": doc}))
    assert "Loop comment noise" in s
    assert "comments per PR" in s and "2.0" in s
    assert "duplicate rate" in s and "40.0%" in s
    assert "PRs the owner commented on" in s and "50%" in s
    assert "ops-finding 1" in s and "#10 (3)" in s
    assert SECRET not in s


def test_the_panel_says_so_when_the_window_is_empty(page):
    empty = {"generated_at": iso(datetime.now(timezone.utc)), "window_days": 7,
             "current": {"loop_comments": 0}, "previous": {}}
    s = _section(page({"outbox.json": empty}))
    assert "No comments by the loop" in s and "duplicate rate" not in s


def test_the_panel_says_so_when_the_file_is_missing(page):
    s = _section(page({}))
    assert "is not there yet" in s and "duplicate rate" not in s
