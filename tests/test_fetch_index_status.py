"""scripts/fetch_index_status.py (#1065): URL Inspection over the sitemap.

FIXTURES ARE DOC-DERIVED. The response shapes below (`inspectionResult.
indexStatusResult` with `verdict`, `coverageState`, `lastCrawlTime`, ...) come
from Google's URL Inspection documentation, not from an observed response: the
loop cannot reach the API. Until one real response is captured these tests prove
the collector's logic against the documented shape, not that Google answers in it.

Nothing here touches the network: `fis.post` and `fis.token` are replaced, and git
runs either through a fake `fis._git` or against a real repository built in
tmp_path (including a real `git clone --depth 1`).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _gapi import ApiError  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "fetch_index_status", ROOT / "scripts" / "fetch_index_status.py")
fis = importlib.util.module_from_spec(_spec)
sys.modules["fetch_index_status"] = fis
_spec.loader.exec_module(fis)

SITE = "sc-domain:shubhagya.com"
BASE = "https://shubhagya.com"

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://shubhagya.com/rashifal</loc>
    <lastmod>2026-11-18</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
    <xhtml:link rel="alternate" hreflang="hi" href="https://shubhagya.com/hi/rashifal"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://shubhagya.com/rashifal"/>
  </url>
  <url>
    <loc>https://shubhagya.com/hi/rashifal</loc>
    <priority>0.9</priority>
    <xhtml:link rel="alternate" hreflang="hi" href="https://shubhagya.com/hi/rashifal"/>
  </url>
  <url>
    <loc>https://shubhagya.com/learn/sade-sati/</loc>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://shubhagya.com/learn/sade-sati/</loc>
    <priority>0.7</priority>
  </url>
</urlset>
"""


def resp(verdict="PASS", crawl="2026-11-01T10:00:00Z", google=None, user=None,
         robots="ALLOWED", state="INDEXING_ALLOWED", coverage="Submitted and indexed"):
    s = {"verdict": verdict, "coverageState": coverage, "robotsTxtState": robots,
         "indexingState": state, "pageFetchState": "SUCCESSFUL"}
    if crawl:
        s["lastCrawlTime"] = crawl
    if google:
        s["googleCanonical"] = google
    if user:
        s["userCanonical"] = user
    return {"inspectionResult": {"indexStatusResult": s}}


def entries(*paths, prio=0.7):
    return [{"url": BASE + p, "priority": prio} for p in paths]


def fake_post(by_url):
    """post(url, body, bearer) -> by_url[inspectionUrl]; an Exception value is raised."""
    calls = []

    def _post(url, body, bearer):
        calls.append(body["inspectionUrl"])
        v = by_url[body["inspectionUrl"]]
        if isinstance(v, list):  # one outcome per attempt
            v = v.pop(0)
        if isinstance(v, BaseException):
            raise v
        return v
    _post.calls = calls
    return _post


# --- parse_sitemap -------------------------------------------------------------

def test_parse_sitemap_reads_loc_and_priority_and_ignores_hreflang_links():
    got = fis.parse_sitemap(SITEMAP)
    assert [e["url"] for e in got] == [
        "https://shubhagya.com/rashifal", "https://shubhagya.com/hi/rashifal",
        "https://shubhagya.com/learn/sade-sati/"]
    assert [e["priority"] for e in got] == [0.9, 0.9, 0.7]


def test_parse_sitemap_dedupes_and_survives_a_missing_or_bad_priority():
    xml = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           '<url><loc>https://a/x</loc></url><url><loc>https://a/x</loc></url>'
           '<url><loc>https://a/y</loc><priority>high</priority></url></urlset>')
    got = fis.parse_sitemap(xml)
    assert got == [{"url": "https://a/x", "priority": None},
                   {"url": "https://a/y", "priority": None}]


def test_every_url_the_real_sitemap_lists_maps_to_files_that_exist(client):
    """The routing table is data, and data rots silently (#141/#146): a new
    /learn article, route or template rename that this table does not know would
    make that page's staleness permanently null."""
    entries_ = fis.parse_sitemap(client.get("/sitemap.xml").content)
    assert len(entries_) > 100, "the sitemap read as near-empty; the loop below would be vacuous"
    unmapped, missing = [], []
    for e in entries_:
        path = fis.urllib.parse.urlsplit(e["url"]).path or "/"
        files = fis.route_files(path)
        if not files:
            unmapped.append(path)
        missing += [f for f in files if not (ROOT / f).exists()]
    assert not unmapped, f"sitemap URLs with no source file: {unmapped}"
    assert not missing, f"mapped files that do not exist: {sorted(set(missing))}"


def test_route_files_strips_the_hindi_prefix_and_refuses_traversal():
    assert fis.route_files("/hi/rashifal/mesha") == fis.route_files("/rashifal/mesha")
    assert fis.route_files("/learn/sade-sati/") == [
        "src/astro_ai/templates/learn/sade-sati.html"]
    assert fis.route_files("/learn/../../etc/passwd") == []
    assert fis.route_files("/nonsense") == []


# --- classify ------------------------------------------------------------------

@pytest.mark.parametrize("verdict,expected", [
    ("FAIL", True), ("NEUTRAL", True), ("PASS", False), ("PARTIAL", False),
    ("VERDICT_UNSPECIFIED", None), (None, None)])
def test_not_indexed_follows_the_documented_verdict(verdict, expected):
    assert fis.classify(resp(verdict=verdict))["not_indexed"] is expected


def test_canonical_mismatch_is_an_exact_compare_and_null_when_either_is_absent():
    a, b = BASE + "/learn/x/", BASE + "/learn/x"
    assert fis.classify(resp(google=a, user=b))["canonical_mismatch"] is True
    assert fis.classify(resp(google=a, user=a))["canonical_mismatch"] is False
    assert fis.classify(resp(google=a))["canonical_mismatch"] is None
    assert fis.classify(resp())["canonical_mismatch"] is None


def test_blocked_reads_robots_and_indexing_state():
    assert fis.classify(resp(robots="DISALLOWED"))["blocked"] is True
    assert fis.classify(resp(state="BLOCKED_BY_META_TAG"))["blocked"] is True
    assert fis.classify(resp())["blocked"] is False


# --- stale ---------------------------------------------------------------------

def test_a_change_after_the_last_crawl_is_stale_and_one_before_it_is_not():
    assert fis.stale("2026-11-10T00:00:00+00:00", "2026-11-01T10:00:00Z", False) == (True, None)
    assert fis.stale("2026-10-01T00:00:00+00:00", "2026-11-01T10:00:00Z", False) == (False, None)


def test_stale_compares_instants_not_strings():
    # 04:00+05:30 is 22:30Z the day BEFORE the crawl at 23:00Z, so not stale; as
    # strings "2026-11-02T04:00..." sorts after "2026-11-01T23:00...", which says stale.
    assert fis.stale("2026-11-02T04:00:00+05:30", "2026-11-01T23:00:00Z", False) == (False, None)
    # nanosecond fraction as Google emits it
    assert fis.stale("2026-11-02T00:00:00+00:00", "2026-11-01T23:00:00.123456789Z", False) == (True, None)


def test_stale_is_null_with_a_reason_when_it_cannot_be_computed():
    assert fis.stale("2026-11-10T00:00:00+00:00", "2026-11-01T10:00:00Z", True) == (None, "shallow-checkout")
    assert fis.stale(None, "2026-11-01T10:00:00Z", False) == (None, "no-source-file")
    assert fis.stale("2026-11-10T00:00:00+00:00", None, False) == (None, "never-crawled")


# --- git -----------------------------------------------------------------------

def test_last_change_is_one_git_call_whatever_the_file_count(monkeypatch):
    seen = []

    def git(args, root):
        seen.append(args)
        return 0, "2026-11-10T12:00:00+05:30\tabc123\n"
    monkeypatch.setattr(fis, "_git", git)
    assert fis.last_change(["a.html", "b.py"], ROOT) == ("2026-11-10T12:00:00+05:30", "abc123")
    assert len(seen) == 1
    assert seen[0][:3] == ["log", "-1", "--format=%cI%x09%H"] and seen[0][-2:] == ["a.html", "b.py"]
    assert fis.last_change([], ROOT) is None and len(seen) == 1


@pytest.mark.parametrize("out,rc,expected", [
    ("false\n", 0, False), ("true\n", 0, True), ("", 0, True), ("unknown\n", 0, True),
    ("false\n", 128, True)])
def test_is_shallow_trusts_only_an_exact_false(monkeypatch, out, rc, expected):
    monkeypatch.setattr(fis, "_git", lambda args, root: (rc, out))
    assert fis.is_shallow(ROOT) is expected


def _commit(repo: Path, msg: str, when: str):
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=repo, check=True, env=env)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    tpl = r / "src/astro_ai/templates/learn"
    tpl.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(r)], check=True)
    (tpl / "sade-sati.html").write_text("v1")
    (r / "src/astro_ai/templates/rashifal_grid.html").write_text("g1")
    _commit(r, "one", "2026-10-01T10:00:00+00:00")
    (tpl / "sade-sati.html").write_text("v2")
    _commit(r, "two", "2026-11-10T10:00:00+00:00")
    return r


def test_last_change_reads_the_newest_commit_touching_the_files_in_a_real_repo(repo):
    when, sha = fis.last_change(["src/astro_ai/templates/learn/sade-sati.html"], repo)
    assert when.startswith("2026-11-10T10:00:00") and len(sha) == 40
    # a file only the first commit touched keeps the first commit's date
    when2, _ = fis.last_change(["src/astro_ai/templates/rashifal_grid.html"], repo)
    assert when2.startswith("2026-10-01T10:00:00")
    assert fis.is_shallow(repo) is False


def test_a_shallow_clone_gives_null_staleness_not_a_flagged_page(repo, tmp_path):
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(clone)], check=True)
    assert fis.is_shallow(clone) is True
    page = BASE + "/learn/sade-sati/"
    fis.post = fake_post({page: resp(crawl="2026-11-12T00:00:00Z")})
    result = fis.run(entries("/learn/sade-sati/"), SITE, "tok", clone, None)
    row = result["rows"][0]
    assert result["shallow"] is True
    assert (row["stale_in_index"], row["stale_reason"]) == (None, "shallow-checkout")
    assert row["changed_at"] is None


# --- run -----------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _restore_post():
    orig = fis.post
    yield
    fis.post = orig


def test_run_flags_a_page_changed_after_its_crawl_and_a_canonical_mismatch(repo):
    sade, grid = BASE + "/learn/sade-sati/", BASE + "/rashifal"
    fis.post = fake_post({
        sade: resp(crawl="2026-11-01T00:00:00Z"),           # changed 2026-11-10 -> stale
        grid: resp(crawl="2026-11-12T00:00:00Z",            # changed 2026-10-01 -> fresh
                   google=BASE + "/rashifal/", user=BASE + "/rashifal")})
    rows = {r["path"]: r for r in fis.run(entries("/learn/sade-sati/", "/rashifal"),
                                           SITE, "tok", repo, None)["rows"]}
    assert rows["/learn/sade-sati/"]["stale_in_index"] is True
    assert rows["/rashifal"]["stale_in_index"] is False
    assert rows["/rashifal"]["canonical_mismatch"] is True
    assert rows["/learn/sade-sati/"]["changed_sha"]


def test_a_429_stops_the_run_partial_and_unreached_pages_are_never_indexed(repo):
    paths = ["/learn/sade-sati/", "/rashifal", "/privacy"]
    post = fake_post({BASE + paths[0]: resp(),
                      BASE + paths[1]: ApiError("HTTP 429 from searchconsole.googleapis.com", 429),
                      BASE + paths[2]: resp()})
    fis.post = post
    result = fis.run(entries(*paths), SITE, "tok", repo, None)
    assert result["partial"] is True and "429" in result["partial_reason"]
    assert post.calls == [BASE + paths[0], BASE + paths[1]], "the run kept calling after a 429"
    for r in result["rows"][1:]:
        assert r["status"] == "not_inspected"
        assert all(r[k] is None for k in ("verdict", "not_indexed", "stale_in_index",
                                          "canonical_mismatch", "lastCrawlTime"))
    c = fis.counts(result["rows"])
    assert (c["indexed"], c["not_inspected"], c["total"]) == (1, 2, 3)


def test_a_403_that_says_quota_stops_the_run_but_another_403_is_one_row(repo):
    quota = ApiError('HTTP 403 from x\n{"error":{"message":"Quota exceeded for quota metric"}}', 403)
    fis.post = fake_post({BASE + "/learn/sade-sati/": resp(), BASE + "/rashifal": quota,
                          BASE + "/privacy": resp()})
    assert fis.run(entries("/learn/sade-sati/", "/rashifal", "/privacy"),
                   SITE, "tok", repo, None)["partial"] is True

    denied = ApiError("HTTP 403 from x\nUser does not own this property", 403)
    fis.post = fake_post({BASE + "/learn/sade-sati/": resp(), BASE + "/rashifal": denied,
                          BASE + "/privacy": resp()})
    result = fis.run(entries("/learn/sade-sati/", "/rashifal", "/privacy"), SITE, "tok", repo, None)
    assert result["partial"] is False
    assert [r["status"] for r in result["rows"]] == ["inspected", "error", "inspected"]


def test_a_refused_first_call_raises_so_nothing_is_written(repo):
    for status in (400, 401, 403):
        fis.post = fake_post({BASE + "/rashifal": ApiError(f"HTTP {status} from x", status)})
        with pytest.raises(fis.FirstCallError):
            fis.run(entries("/rashifal"), SITE, "tok", repo, None)


def test_a_transient_failure_is_retried_once_then_recorded_as_an_error(repo):
    ok = BASE + "/rashifal"
    fis.post = fake_post({ok: [ApiError("HTTP 503 from x", 503), resp()]})
    r = fis.run(entries("/rashifal"), SITE, "tok", repo, None)
    assert r["rows"][0]["status"] == "inspected" and r["calls"] == 2

    fis.post = fake_post({ok: [TimeoutError("slow"), OSError("reset")]})
    r = fis.run(entries("/rashifal"), SITE, "tok", repo, None)
    assert r["rows"][0]["status"] == "error" and r["calls"] == 2 and r["partial"] is False


# --- ranking and counts --------------------------------------------------------

def _row(url, imp, prio=0.7, stale=None, not_indexed=None, mismatch=None, blocked=False,
         status="inspected"):
    return {"url": url, "status": status, "impressions": imp, "sitemap_priority": prio,
            "stale_in_index": stale, "not_indexed": not_indexed, "canonical_mismatch": mismatch,
            "blocked": blocked, "verdict": "PASS" if not_indexed is False else None,
            "coverageState": "Crawled - currently not indexed", "changed_at": "c",
            "lastCrawlTime": "l"}


def test_request_indexing_ranks_by_impressions_then_priority_then_url_and_caps_at_ten():
    rows = [_row(f"u{i:02d}", i, stale=True) for i in range(15)]
    rows += [_row("a-low", 5, prio=0.5, stale=True), _row("b-high", 5, prio=0.9, stale=True)]
    got = fis.rank_requests(rows)
    assert len(got) == 10
    assert [g["url"] for g in got[:3]] == ["u14", "u13", "u12"]
    ranked_fives = [g["url"] for g in fis.rank_requests(rows, limit=99) if g["impressions"] == 5]
    assert ranked_fives == ["b-high", "u05", "a-low"]
    assert set(got[0]) == {"url", "reasons", "impressions", "changed_at", "lastCrawlTime"}


def test_request_indexing_leaves_out_what_requesting_cannot_fix():
    rows = [_row("ok-stale", 9, stale=True),
            _row("mismatch", 99, stale=True, mismatch=True),
            _row("blocked", 98, not_indexed=True, blocked=True),
            _row("unreached", 97, stale=True, status="not_inspected"),
            _row("fresh", 96, stale=False, not_indexed=False),
            _row("unknown", 95)]
    got = fis.rank_requests(rows)
    assert [g["url"] for g in got] == ["ok-stale"]
    assert got[0]["reasons"] == ["changed after Google's last crawl"]
    assert fis.rank_requests([_row("n", 1, not_indexed=True)])[0]["reasons"] == [
        "not indexed: Crawled - currently not indexed"]


def test_request_indexing_asks_for_a_not_indexed_next_year_learn_page_before_stale_pages():
    rows = [_row(f"{BASE}/learn/stale-{i:02d}/", 500 + i, stale=True) for i in range(12)]
    g27 = f"{BASE}/learn/gochar-2027-planetary-transits/"
    rows += [_row(g27, 0, not_indexed=True),
             _row(f"{BASE}/hi/learn/vivah-muhurat-2027/", 0, not_indexed=True),   # /hi/ form counts
             _row(f"{BASE}/learn/gochar-2026-planetary-transits/", 0, not_indexed=True),  # this year
             _row(f"{BASE}/panchang/2027-01-05", 0, not_indexed=True),            # a date page, not a successor
             _row(f"{BASE}/learn/pad-12027-x/", 0, not_indexed=True),             # digit boundary
             _row(f"{BASE}/learn/griha-2027-blocked/", 0, not_indexed=True, blocked=True),
             _row(f"{BASE}/learn/griha-2027-unreached/", 0, not_indexed=True, status="not_inspected"),
             _row(f"{BASE}/learn/stale-2027-only/", 0, stale=True, not_indexed=False)]
    today = date(2026, 11, 28)
    got = fis.rank_requests(rows, today=today)
    urls = [g["url"] for g in got]
    assert set(urls[:2]) == {g27, f"{BASE}/hi/learn/vivah-muhurat-2027/"}   # tied on 0 imp: order is by URL
    assert all("names 2027: ask before it has impressions" in g["reasons"] and g["reasons"][0].startswith("not indexed") for g in got[:2])
    # exactly the two successors carry the reason: a decoy ranked third or lower would hide behind urls[:2]
    assert {g["url"] for g in got if any(r.startswith("names 2027") for r in g["reasons"])} == set(urls[:2])
    for decoy in ("gochar-2026", "panchang/2027", "pad-12027", "2027-blocked", "2027-unreached", "stale-2027-only"):
        assert not any(decoy in u for u in urls[:2])
    assert not any(("2027-blocked" in u or "2027-unreached" in u) for u in urls)
    # the cap: five ask-first rows leave five slots for stale pages
    many = [_row(f"{BASE}/learn/next-2027-{i}/", 0, not_indexed=True) for i in range(8)]
    got = fis.rank_requests(rows[:12] + many, today=today)
    assert sum("2027" in g["url"] for g in got) == 5 and len(got) == 10
    # the year follows the date: in 2027 the 2027 page is an ordinary 0-impression row, below the cap line
    assert g27 not in [g["url"] for g in fis.rank_requests(rows, today=date(2027, 3, 1))]
    # a shallow capture (stale unknown) still lists it
    assert fis.rank_requests([_row(g27, 0, not_indexed=True, stale=None)], today=today)[0]["url"] == g27


def test_counts_partition_the_rows_and_indexed_means_an_inspected_pass():
    rows = [_row("a", 1, not_indexed=False), _row("b", 1, not_indexed=True),
            _row("c", 1), _row("d", 1, status="not_inspected"), _row("e", 1, status="error")]
    c = fis.counts(rows)
    assert c["total"] == 5 and c["inspected"] + c["not_inspected"] == c["total"]
    assert (c["indexed"], c["not_indexed"], c["unknown"], c["errors"]) == (1, 1, 1, 1)


# --- main ----------------------------------------------------------------------

def _sitemap_file(tmp_path, paths):
    xml = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + "".join(f"<url><loc>{BASE}{p}</loc><priority>0.7</priority></url>" for p in paths)
           + "</urlset>")
    f = tmp_path / "sitemap.xml"
    f.write_text(xml)
    return f


def test_main_writes_one_document_with_the_designed_keys(repo, tmp_path, capsys, monkeypatch):
    sade, grid = BASE + "/learn/sade-sati/", BASE + "/rashifal"
    fis.post = fake_post({sade: resp(crawl="2026-11-01T00:00:00Z"),
                          grid: resp(verdict="FAIL", crawl="2026-11-12T00:00:00Z",
                                     coverage="Crawled - currently not indexed")})
    monkeypatch.setattr(fis, "token", lambda: "tok")
    imp = tmp_path / "gsc.json"
    imp.write_text(json.dumps({"rows": [{"page": sade, "impressions": 40},
                                        {"page": BASE + "/learn/gone/", "impressions": 7}]}))
    rc = fis.main(["--sitemap-file", str(_sitemap_file(tmp_path, ["/learn/sade-sati/", "/rashifal"])),
                   "--impressions", str(imp), "--root", str(repo)])
    doc = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert set(doc) >= {"source", "site", "generated_at", "sitemap_url", "git_shallow", "partial",
                        "partial_reason", "quota", "impressions_source", "impressions_matched",
                        "note", "counts", "request_indexing", "rows"}
    assert doc["quota"] == {"calls": 2, "limit_per_day": 2000}
    assert doc["impressions_matched"] == {"matched": 1, "with_impressions": 2}
    assert doc["git_shallow"] is False and doc["partial"] is False
    assert [r["url"] for r in doc["request_indexing"]] == [sade, grid]
    for phrase in ("base.html", "i18n.py", "learn_registry.py", "/rashifal", "/panchang"):
        assert phrase in doc["note"]


def test_same_site_keeps_only_http_urls_on_the_sitemaps_own_host():
    entries = [{"url": u, "priority": None} for u in (
        "https://shubhagya.com/a", "https://SHUBHAGYA.com/b", "https://evil.example/x",
        "file:///etc/passwd", "ftp://shubhagya.com/c", "https://shubhagya.com.evil.example/d")]
    kept, dropped = fis.same_site(entries, "https://shubhagya.com/sitemap.xml")
    assert [e["url"] for e in kept] == ["https://shubhagya.com/a", "https://SHUBHAGYA.com/b"]
    assert dropped == 4


def test_main_never_sends_an_off_site_or_file_url_to_inspection(repo, tmp_path, capsys, monkeypatch):
    sent = []

    def post(url, body, bearer):
        sent.append(body["inspectionUrl"])
        return resp()

    fis.post = post
    monkeypatch.setattr(fis, "token", lambda: "tok")
    xml = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"<url><loc>{BASE}/rashifal</loc></url>"
           "<url><loc>https://evil.example/x</loc></url>"
           "<url><loc>file:///etc/passwd</loc></url></urlset>")
    f = tmp_path / "s.xml"
    f.write_text(xml)
    rc = fis.main(["--sitemap-file", str(f), "--root", str(repo),
                   "--impressions", str(tmp_path / "none.json")])
    doc = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert sent == [BASE + "/rashifal"]
    assert [r["url"] for r in doc["rows"]] == [BASE + "/rashifal"]


def test_main_prints_nothing_and_exits_1_when_the_file_would_be_noise(repo, tmp_path, capsys,
                                                                      monkeypatch):
    monkeypatch.setattr(fis, "token", lambda: "tok")
    ok = _sitemap_file(tmp_path, ["/rashifal"])
    argv = ["--root", str(repo), "--impressions", str(tmp_path / "none.json")]

    assert fis.main(["--sitemap-file", str(tmp_path / "missing.xml"), *argv]) == 1
    bad = tmp_path / "bad.xml"
    bad.write_text("<urlset")
    assert fis.main(["--sitemap-file", str(bad), *argv]) == 1
    empty = tmp_path / "empty.xml"
    empty.write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
    assert fis.main(["--sitemap-file", str(empty), *argv]) == 1

    fis.post = fake_post({BASE + "/rashifal": ApiError("HTTP 403 from x", 403)})
    assert fis.main(["--sitemap-file", str(ok), *argv]) == 1
    fis.post = fake_post({BASE + "/rashifal": ApiError("HTTP 429 from x", 429)})
    assert fis.main(["--sitemap-file", str(ok), *argv]) == 1
    assert capsys.readouterr().out == ""


def test_the_collector_makes_no_llm_call():
    src = (ROOT / "scripts" / "fetch_index_status.py").read_text()
    for needle in ("openai", "anthropic", "groq", "astro_ai"):
        assert f"import {needle}" not in src and f"from {needle}" not in src
