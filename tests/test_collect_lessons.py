"""The lessons ledger the planners read (owner, 2026-11-06: "a continuous
feedback loop from their own actions and from researching other websites").

Every filter lives in Python, so these tests feed realistic REST payloads and
check what the loop will be told."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("collect_lessons", ROOT / "scripts" / "collect_lessons.py")
cl = importlib.util.module_from_spec(_spec)
sys.modules["collect_lessons"] = cl
_spec.loader.exec_module(cl)

NOW = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
REPO = "o/r"


def C(num, body, at="2026-11-05T10:00:00Z", user="claude[bot]"):
    return {"user": {"login": user}, "body": body, "created_at": at,
            "issue_url": f"https://api.github.com/repos/o/r/issues/{num}",
            "html_url": f"https://github.com/o/r/issues/{num}#c"}


class FakeGh:
    def __init__(self, comments=(), commits=(), runs=(), issues=()):
        self.data = {"comments": list(comments), "commits": list(commits),
                     "runs": list(runs), "issues": list(issues)}
        self.urls: list[str] = []

    def __call__(self, args):
        url = args[1]
        self.urls.append(url)
        page = int(url.rsplit("page=", 1)[1])
        if "/issues/comments" in url:
            rows = self.data["comments"]
        elif "/commits" in url:
            rows = self.data["commits"]
        elif "/actions/workflows/" in url:
            return json.dumps({"workflow_runs": self.data["runs"] if page == 1 else []})
        elif "/issues?" in url:
            rows = self.data["issues"]
        else:
            raise AssertionError(url)
        return json.dumps(rows if page == 1 else [])


def collect(gh, ops=()):
    return cl.collect(gh, REPO, NOW, list(ops))


def test_a_qa_fail_is_read_with_the_defect_from_the_verdict_beside_it():
    """The marker line qa_verdict.sh posts carries no detail; the full verdict
    sits beside it. One FAIL, its themes taken from the defect text."""
    gh = FakeGh(comments=[
        C(704, "QA: FAIL — verified at `abc`\nround 1", at="2026-11-04T07:38:00Z"),
        C(704, "## QA verdict: FAIL\nTests ran: 2295 passed. Token cost 0.\n"
               "DEFECT (regression): drops the conflicting PR's entry permanently.",
          at="2026-11-04T07:37:00Z"),
    ])
    doc = collect(gh)
    assert len(doc["errors"]["qa_fail"]) == 1
    assert doc["errors"]["qa_fail"][0]["themes"] == ["regression"]


def test_boilerplate_in_a_verdict_does_not_become_a_theme():
    """Every verdict states its test runs and a token cost. The first version
    tagged 40 of 43 FAILs 'tokens' and named nothing."""
    gh = FakeGh(comments=[C(1, "QA: FAIL — verified at `x`\nfull pytest 2268 pass; tokens 0.\n"
                               "BLOCKING: the Hindi page shows an untranslated card.")])
    assert collect(gh)["errors"]["qa_fail"][0]["themes"] == ["i18n"]


def test_a_theme_seen_twice_is_listed_as_repeated():
    gh = FakeGh(comments=[
        C(10, "QA: FAIL — at `a`\nBLOCKING: the rule is unsourced", at="2026-11-01T01:00:00Z"),
        C(11, "QA: FAIL — at `b`\nDEFECT: cites a section the book lacks", at="2026-11-02T01:00:00Z"),
        C(12, "QA: FAIL — at `c`\nBLOCKING: exploitable xss", at="2026-11-03T01:00:00Z"),
    ])
    doc = collect(gh)
    assert doc["repeated_themes"] == ["grounding"]
    assert "**grounding**" in cl.render(doc)


def test_comments_by_anyone_else_are_ignored():
    gh = FakeGh(comments=[C(1, "QA: FAIL — at `x`\nBLOCKING: unsourced", user="drive-by")])
    assert collect(gh)["errors"]["qa_fail"] == []


def test_the_analyst_verdict_is_the_word_after_verdict_latest_per_issue():
    """#311's comment said 'MISS so far' and mentioned an INCONCLUSIVE sibling;
    the first version read it as INCONCLUSIVE."""
    gh = FakeGh(comments=[
        C(311, "predicted 2.0, actual 0.4. verdict: HIT", at="2026-11-01T01:00:00Z"),
        C(311, "metric re-read. **Verdict: MISS so far.** #329 stays INCONCLUSIVE.",
          at="2026-11-05T01:00:00Z"),
        C(312, "a status line that says HIT and nothing else"),
    ])
    doc = collect(gh)
    assert doc["outcomes"] == [{"number": 311, "verdict": "MISS",
                                "at": "2026-11-05T01:00:00Z",
                                "url": "https://github.com/o/r/issues/311#c"}]


def test_comments_older_than_the_window_are_dropped():
    gh = FakeGh(comments=[C(1, "QA: FAIL — at `x`\nBLOCKING: unsourced", at="2026-09-01T00:00:00Z")])
    assert collect(gh)["errors"]["qa_fail"] == []


def test_the_newest_comments_are_requested_first():
    """Oldest-first with a page cap read only the start of the window: the first
    live run found 1 QA FAIL in 30 days."""
    gh = FakeGh()
    collect(gh)
    assert any("/issues/comments" in u and "direction=desc" in u for u in gh.urls)


def test_reverts_failed_verifies_and_competitor_patterns_are_collected():
    gh = FakeGh(
        commits=[{"sha": "a" * 40, "commit": {"message": "Revert \"x\"\n\nbody",
                                             "author": {"date": "2026-11-02T00:00:00Z"}}},
                 {"sha": "b" * 40, "commit": {"message": "Normal",
                                             "author": {"date": "2026-11-02T00:00:00Z"}}}],
        runs=[{"id": 9, "created_at": "2026-11-03T00:00:00Z", "head_sha": "c" * 40}],
        issues=[{"number": 50, "title": "Rival shows a dasha timeline", "state": "open",
                 "body": f"{cl.COMPETITOR_MARK}\nseen on example.com", "labels": []},
                {"number": 51, "title": "PR", "state": "open", "pull_request": {},
                 "body": cl.COMPETITOR_MARK, "labels": []},
                {"number": 52, "title": "plain issue", "state": "open", "body": "x", "labels": []}])
    doc = collect(gh, ops=[{"kind": "loop-idle", "level": "amber", "title": "idle"}])
    assert [r["sha"] for r in doc["errors"]["reverts"]] == ["aaaaaaa"]
    assert doc["errors"]["verify_production_failed"][0]["run"] == 9
    assert [c["number"] for c in doc["competitor_patterns"]] == [50]
    md = cl.render(doc)
    assert "Rival shows a dasha timeline" in md and "loop-idle" in md


def test_the_ledger_carries_the_grounding_rule():
    """A rival may suggest what to build, never what is astrologically true."""
    md = cl.render(collect(FakeGh()))
    assert "never imports an astrological claim" in md
    assert "knowledge/*.md" in md


def test_main_writes_both_files_and_a_failed_read_keeps_the_previous_ones(tmp_path):
    assert cl.main(["x", "--repo", REPO, "--out-dir", str(tmp_path)], gh=FakeGh(), now=NOW,
                   ops=lambda: []) == 0
    assert (tmp_path / "lessons.json").exists() and (tmp_path / "lessons.md").exists()
    (tmp_path / "lessons.md").write_text("previous")

    def broken(args):
        raise RuntimeError("gh: 502")
    assert cl.main(["x", "--repo", REPO, "--out-dir", str(tmp_path)], gh=broken, now=NOW,
                   ops=lambda: []) == 1
    assert (tmp_path / "lessons.md").read_text() == "previous"
