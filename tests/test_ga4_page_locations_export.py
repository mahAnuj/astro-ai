"""#1237 -- `scripts/fetch_ga4.py --page-locations`: which page_location values still reach GA4
with a query string, so #1066 (city) and #1093 (email, token) can be checked rather than
asserted. Hermetic: `post`, `token` and `window` are patched.

Each test is a way this export could ship wrong, and the worst is a leak: the export exists
to find an address in a URL, so printing one into a file that gets posted into a report
would reproduce the defect it measures. The canaries below are planted in values, in a bare
parameter NAME, in a path, in a long segment, as a bare token, double-encoded in a path and as
a /r/<id> kundli snapshot id (#1450), and must appear nowhere in stdout. The
others: a partial file after one request failed (a silent zero reads as "no leak"), coverage
measured against all events (it would read ~1% and look like a failed fetch), watch counts
taken from the 50 rows shown, the JS and Python PII lists drifting apart, or the flag
combining with another report."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("fetch_ga4", ROOT / "scripts" / "fetch_ga4.py")
ga = importlib.util.module_from_spec(_spec)
sys.modules["fetch_ga4"] = ga
_spec.loader.exec_module(ga)

WIN = ("2026-11-01", "2026-11-21")
HOST = "https://shubhagya.com"

CANARIES = ("victim@example.com", "tok3nSECRET", "Ujjain-Canary", "victim%40example.com",
            "LONGSEGMENTCANARY", "tok3nSECRETabcdefghijklmnop", "victim%2540example.com",
            "SNAPSHOTIDCANARY", "Ujjain")


def _loc_rows(rows, row_count=None, totals=None, loss=None):
    """rows: (page_location, events). `totals` is the events TOTAL; None omits the block."""
    out = {"rows": [{"dimensionValues": [{"value": loc}],
                     "metricValues": [{"value": str(n)}]} for loc, n in rows],
           "rowCount": len(rows) if row_count is None else row_count}
    if totals is not None:
        out["totals"] = [{"metricValues": [{"value": str(totals)}]}]
    if loss is not None:
        out["metadata"] = {"dataLossFromOtherRow": loss}
    return out


def _total(n):
    return {"rows": [{"metricValues": [{"value": str(n)}]}], "rowCount": 1}


class Fake:
    """Answers the filtered pageLocation request and the dimensionless total; records bodies."""

    def __init__(self, locations, total, fail_on=None):
        self.locations, self.total = locations, total
        self.fail_on = fail_on
        self.bodies = []

    def __call__(self, url, body, bearer):
        self.bodies.append(body)
        is_loc = "dimensions" in body
        if self.fail_on == ("loc" if is_loc else "total"):
            raise ga.ApiError(500, "boom")
        return self.locations if is_loc else self.total


def run(monkeypatch, capsys, fake, *flags):
    monkeypatch.setattr(ga, "post", fake)
    monkeypatch.setattr(ga, "token", lambda: "t")
    monkeypatch.setattr(ga, "window", lambda days: WIN)
    monkeypatch.setattr(sys, "argv", ["fetch_ga4.py", "--property", "123", *flags])
    rc = ga.main()
    raw = capsys.readouterr().out
    return rc, json.loads(raw), raw


def _go(monkeypatch, capsys, rows, total=1000, totals=None, **kw):
    t = sum(n for _, n in rows) if totals is None else totals
    fake = Fake(_loc_rows(rows, totals=t, **kw), _total(total))
    return run(monkeypatch, capsys, fake, "--page-locations"), fake


def test_two_requests_with_the_declared_dimension_metric_filter_and_window(monkeypatch, capsys):
    (rc, out, _), fake = _go(monkeypatch, capsys, [(f"{HOST}/panchang?city=Delhi", 5)])
    assert rc == 0 and len(fake.bodies) == 2
    loc, total = fake.bodies
    assert [d["name"] for d in loc["dimensions"]] == ["pageLocation"]
    assert [m["name"] for m in loc["metrics"]] == ["eventCount"]
    assert loc["dimensionFilter"] == {"filter": {
        "fieldName": "pageLocation",
        "stringFilter": {"matchType": "CONTAINS", "value": "?"}}}
    assert loc["metricAggregations"] == ["TOTAL"]
    assert loc["orderBys"] == [{"metric": {"metricName": "eventCount"}, "desc": True}]
    assert loc["limit"] == 10000
    assert [m["name"] for m in total["metrics"]] == ["eventCount"]
    assert "dimensions" not in total and "dimensionFilter" not in total
    for b in fake.bodies:
        assert b["dateRanges"] == [{"startDate": WIN[0], "endDate": WIN[1]}]
    assert out["mode"] == "page-locations" and out["window"] == list(WIN)
    assert out["dimensions"] == ["pageLocation"]


def test_no_canary_value_or_address_reaches_stdout(monkeypatch, capsys):
    rows = [
        (f"{HOST}/panchang?city=Ujjain-Canary&email=victim@example.com", 4),
        (f"{HOST}/unsubscribe?token=tok3nSECRET&email=victim%40example.com", 3),
        (f"{HOST}/ask?victim@example.com", 2),
        (f"{HOST}/u/victim@example.com/chart?utm_source=x#tok3nSECRET", 2),
        (f"https://victim@example.com:pw@shubhagya.com/x?q=tok3nSECRET", 1),
        (f"{HOST}/c/{'LONGSEGMENTCANARY' * 3}?utm=1", 1),
        (f"{HOST}/unsubscribe?tok3nSECRETabcdefghijklmnop", 1),
        (f"{HOST}/pre/victim%2540example.com?c=1", 1),
        (f"{HOST}/r/SNAPSHOTIDCANARY?utm_source=x", 1),
        (f"{HOST}/x?Ujjain", 1),
    ]
    (_, _, raw), _ = _go(monkeypatch, capsys, rows)
    for c in CANARIES:
        assert c not in raw
    assert "example.com" not in raw and "shubhagya.com" not in raw
    assert "/r/<id>" in raw and "/pre/<redacted>" in raw


def test_a_bare_address_as_a_parameter_name_is_redacted(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/ask?a@b.com", 3)])
    assert out["rows"][0]["params"] == ["(redacted-name)"]
    assert [b["param"] for b in out["by_param"]] == ["(redacted-name)"]
    # With an `=` the bare-name check does not apply, so the character whitelist must catch it.
    assert ga.fold_location(f"{HOST}/ask?a@b.com=1") == ("/ask", ("(redacted-name)",))


@pytest.mark.parametrize("name", ["a@b.com", "x" * 33, "a b", "a%40b", "\u00e9"])
def test_unsafe_parameter_names_are_redacted_and_safe_ones_kept(name):
    path, names = ga.fold_location(f"{HOST}/p?{name}&utm_source=x&filter[a].b-c_d=1")
    assert names == ("(redacted-name)", "filter[a].b-c_d", "utm_source")
    assert path == "/p"


TOKEN = "tok3nSECRETabcdefghijklmnop"
REDACTED = ("(redacted-name)",)


@pytest.mark.parametrize("q", [TOKEN, "Ujjain", "abc"])
def test_a_bare_query_token_as_a_name_is_redacted(q):
    assert ga.fold_location(f"{HOST}/x?{q}") == ("/x", REDACTED)


def test_a_token_shaped_name_with_a_value_is_redacted():
    assert ga.fold_location(f"{HOST}/x?{TOKEN}=1") == ("/x", REDACTED)


@pytest.mark.parametrize("enc", ["2540", "252540"])
def test_a_double_encoded_address_in_a_path_is_redacted(enc):
    path, names = ga.fold_location(f"{HOST}/pre/victim%{enc}example.com?c=1")
    assert path == "/pre/<redacted>" and names == ("c",)


def test_a_snapshot_id_is_collapsed():
    assert ga.fold_location(f"{HOST}/r/abc123?utm_source=x") == ("/r/<id>", ("utm_source",))
    assert ga.fold_location(f"{HOST}/r/abc123/?c=1")[0] == "/r/<id>"
    assert ga.fold_location(f"{HOST}/r/{'AbCdEfGhIjKlMnOpQrStUv'}?c=1")[0] == "/r/<id>"


@pytest.mark.parametrize("path,want", [("/r", "/r"), ("/r/", "/r"), ("/learn/r/x", "/learn/r/x")])
def test_only_a_top_level_r_with_an_id_is_collapsed(path, want):
    assert ga.fold_location(f"{HOST}{path}?c=1")[0] == want


def test_watched_names_are_kept_with_a_value_bare_or_decoded():
    assert ga.fold_location(f"{HOST}/x?q=1&city=x&email=a&token=t")[1] == (
        "city", "email", "q", "token")
    assert ga.fold_location(f"{HOST}/x?token&email")[1] == ("email", "token")
    assert ga.fold_location(f"{HOST}/x?e%6Dail=a")[1] == ("email",)
    # no raw `=`: the encoded one is not a separator, so this is a value sent as a name
    assert ga.fold_location(f"{HOST}/x?email%3Dx")[1] == REDACTED


def test_ordinary_names_and_slug_paths_are_kept():
    names = ("utm_source", "utm_campaign", "page", "lang", "rashi", "date", "needs_chart",
             "geoname-id", "filter[a].b-c_d")
    q = "&".join(f"{n}=1" for n in names)
    assert ga.fold_location(f"{HOST}/x?{q}")[1] == tuple(sorted(names))
    slug = "/learn/which-mahadasha-best-for-career/"
    assert ga.fold_location(f"{HOST}{slug}?lang=hi")[0] == slug.rstrip("/")


def test_the_token_shaped_name_threshold_is_exactly_twenty_mixed_characters():
    kept = ("a" * 20, "a1" * 9 + "b", "1" * 20)     # all letters, 19 mixed, all digits
    assert [len(k) for k in kept] == [20, 19, 20]
    for k in kept:
        assert ga.fold_location(f"{HOST}/x?{k}=1")[1] == (k,), k
    assert ga.fold_location(f"{HOST}/x?{'a1' * 10}=1")[1] == REDACTED          # 20 mixed


def test_a_path_segment_with_an_at_sign_is_redacted():
    path, _ = ga.fold_location(f"{HOST}/u/victim@example.com/chart?x=1")
    assert path == "/u/<redacted>/chart"
    path, _ = ga.fold_location(f"{HOST}/u/victim%40example.com/chart?x=1")
    assert path == "/u/<redacted>/chart"


def test_a_segment_over_forty_characters_is_redacted_and_forty_is_kept():
    assert ga.fold_location(f"{HOST}/{'a' * 41}?x=1")[0] == "/<redacted>"
    assert ga.fold_location(f"{HOST}/{'a' * 40}?x=1")[0] == "/" + "a" * 40


def test_values_host_fragment_and_userinfo_are_dropped_and_names_sorted():
    assert ga.fold_location(f"{HOST}/p/?utm=1&city=X&a=2#frag") == ("/p", ("a", "city", "utm"))
    assert ga.fold_location("https://u:p@h.example/p?b=1&b=2") == ("/p", ("b",))


def test_an_unparseable_location_folds_to_a_shape_and_is_never_echoed(monkeypatch, capsys):
    assert ga.fold_location("http://[victim@example.com?x=1") == ("(unparseable)", ())
    (_, out, raw), _ = _go(monkeypatch, capsys, [("http://[victim@example.com?x=1", 6)])
    assert out["rows"][0]["path"] == "(unparseable)" and out["rows"][0]["events"] == 6
    assert "victim" not in raw


def test_locations_fold_into_shapes_and_their_events_are_summed(monkeypatch, capsys):
    rows = [(f"{HOST}/panchang?city=X", 5), (f"{HOST}/panchang?city=Y", 3),
            (f"{HOST}/panchang?city=Z&utm=1", 2)]
    (_, out, _), _ = _go(monkeypatch, capsys, rows)
    assert out["shape_count"] == 2
    assert out["rows"] == [{"path": "/panchang", "params": ["city"], "events": 8, "locations": 2},
                           {"path": "/panchang", "params": ["city", "utm"], "events": 2,
                            "locations": 1}]
    assert out["rows_events"] == 10


def test_watch_counts_and_the_exact_headline(monkeypatch, capsys):
    rows = [(f"{HOST}/panchang?city=X", 5), (f"{HOST}/kundli?city=Y&email=a", 3),
            (f"{HOST}/unsubscribe?token=t", 2), (f"{HOST}/ask?q=hi", 1),
            (f"{HOST}/learn?utm=1", 4)]
    (_, out, _), _ = _go(monkeypatch, capsys, rows, total=1000)
    assert out["events_with_query"] == 15 and out["total_events"] == 1000
    assert out["query_share_pct"] == 1.5
    assert out["headline"] == ("15 of 1000 events (1.5%) carry a query string in "
                               "page_location; watched params city=8, email=3, token=2, q=1")
    w = out["watch"]
    assert (w["city"]["events"], w["city"]["shapes"]) == (8, 2)
    assert [p["path"] for p in w["city"]["top_paths"]] == ["/panchang", "/kundli"]
    assert (w["email"]["events"], w["token"]["events"], w["q"]["events"]) == (3, 2, 1)
    assert {b["param"]: b["events"] for b in out["by_param"]}["utm"] == 4


def test_zero_rows_with_events_says_none_of_the_watched_params_reaches_ga4(monkeypatch, capsys):
    fake = Fake(_loc_rows([]), _total(5000))
    _, out, _ = run(monkeypatch, capsys, fake, "--page-locations")
    assert out["events_with_query"] == 0 and out["rows"] == []
    assert out["headline"].startswith("0 of 5000 events carry a query string")
    assert "none of the watched params" in out["headline"] and "reaches GA4" in out["headline"]
    assert "no data" not in out["headline"]
    assert out["coverage_pct"] is None and out["query_share_pct"] == 0.0


def test_zero_events_at_all_says_nothing_can_be_said(monkeypatch, capsys):
    fake = Fake({}, {})
    _, out, _ = run(monkeypatch, capsys, fake, "--page-locations")
    assert out["headline"] == "no events in the window; nothing can be said"
    assert out["total_events"] == 0 and out["query_share_pct"] is None


def test_a_missing_total_is_none_not_a_guess(monkeypatch, capsys):
    fake = Fake(_loc_rows([(f"{HOST}/p?city=X", 4)]), _total(100))   # rows, no totals block
    _, out, _ = run(monkeypatch, capsys, fake, "--page-locations")
    assert out["events_with_query"] is None and out["coverage_pct"] is None
    assert out["query_share_pct"] is None


def test_coverage_is_100_unless_truncated_and_is_not_against_all_events(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?city=X", 10)], total=100000)
    assert out["coverage_pct"] == 100 and out["truncated"] is False
    assert "TRUNCATED" not in out["coverage_note"]
    assert "lower bound" not in out["headline"]


def test_truncation_lowers_coverage_and_says_so(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?city=X", 30)], totals=100,
                         row_count=77)
    assert out["truncated"] is True and out["row_count"] == 77
    assert out["coverage_pct"] == 30
    assert "TRUNCATED: 1 of 77 page_location rows returned" in out["coverage_note"]


_NAMED = "watched params city=0, email=0, token=0, q=20"


def test_truncation_is_in_the_headline_not_only_in_the_coverage_note(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?q=a", 20)], totals=200,
                         row_count=5, total=1000)
    assert out["headline"].startswith("200 of 1000 events (20.0%) carry a query string in "
                                      f"page_location; {_NAMED}")
    assert out["headline"].endswith(" (lower bound: truncated)")


def test_data_loss_at_full_coverage_is_a_lower_bound_in_the_headline(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?q=a", 20)], loss=True)
    assert out["coverage_pct"] == 100
    assert out["headline"].endswith(" (lower bound: rows hidden in (other))")


def test_both_flags_are_named_in_one_suffix(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?q=a", 20)], totals=200,
                         row_count=5, loss=True)
    assert out["headline"].endswith(" (lower bound: truncated; rows hidden in (other))")


def test_rows_covering_less_than_the_total_is_a_lower_bound_on_coverage_alone(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?q=a", 30)], totals=100)
    assert out["truncated"] is False and out["other_row_data_loss"] is False
    assert out["headline"].endswith(
        " (lower bound: fetched rows cover 30% of the events with a query string)")
    assert "truncated" not in out["headline"] and "(other)" not in out["headline"]


def test_an_unknown_total_with_a_known_query_count_does_not_say_of_zero(monkeypatch, capsys):
    fake = Fake(_loc_rows([(f"{HOST}/p?city=X", 4)], totals=4), {})
    _, out, _ = run(monkeypatch, capsys, fake, "--page-locations")
    assert out["headline"] == ("4 events carry a query string in page_location (total events "
                               "unknown); watched params city=4, email=0, token=0, q=0")
    assert "None" not in out["headline"] and " of 0 " not in out["headline"]
    assert out["query_share_pct"] is None


def test_both_totals_unknown_says_so_instead_of_of_zero(monkeypatch, capsys):
    fake = Fake(_loc_rows([(f"{HOST}/p?city=X", 4)]), {})
    _, out, _ = run(monkeypatch, capsys, fake, "--page-locations")
    assert "no total for events with a query string or for all events" in out["headline"]
    assert "(total unknown)" in out["headline"]
    assert "None" not in out["headline"] and " of 0 " not in out["headline"]


@pytest.mark.parametrize("kw,why", [({"loss": True}, "rows hidden in (other)"),
                                    ({"row_count": 3}, "truncated")])
def test_an_incomplete_empty_result_is_not_a_none_of_them_all_clear(monkeypatch, capsys, kw, why):
    fake = Fake(_loc_rows([], **kw), _total(5000))
    _, out, _ = run(monkeypatch, capsys, fake, "--page-locations")
    assert f"result is incomplete ({why})" in out["headline"]
    assert "may still reach GA4" in out["headline"]
    assert "none of the watched params" not in out["headline"]


def test_an_encoded_watched_name_is_counted_and_its_value_never_printed(monkeypatch, capsys):
    (_, out, raw), _ = _go(monkeypatch, capsys, [(f"{HOST}/x?e%6Dail=a@b.com", 3)])
    assert out["watch"]["email"]["events"] == 3
    assert "a@b.com" not in raw and "b.com" not in raw


def test_other_row_data_loss_is_surfaced_and_tolerated_when_absent(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?city=X", 3)], loss=True)
    assert out["other_row_data_loss"] is True and "dataLossFromOtherRow" in out["coverage_note"]
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?city=X", 3)])
    assert out["other_row_data_loss"] is False


def test_the_notes_say_events_not_pageviews(monkeypatch, capsys):
    (_, out, _), _ = _go(monkeypatch, capsys, [(f"{HOST}/p?city=X", 3)])
    assert "not pageviews" in out["coverage_note"] and "not pageviews" in out["watch_note"]
    assert "deploy date" in out["watch_note"] and "understate" in out["watch_note"]


@pytest.mark.parametrize("fail_on", ["loc", "total"])
def test_either_request_failing_is_fatal_with_no_partial_file(monkeypatch, capsys, fail_on):
    fake = Fake(_loc_rows([(f"{HOST}/p?city=X", 3)], totals=3), _total(10), fail_on=fail_on)
    with pytest.raises(ga.ApiError):
        run(monkeypatch, capsys, fake, "--page-locations")
    assert capsys.readouterr().out == ""


def test_rows_are_capped_at_fifty_but_watch_and_by_param_use_every_shape(monkeypatch, capsys):
    # 60 shapes of one event each on distinct paths; the last 10 are the only ones with email.
    rows = [(f"{HOST}/p{i:02d}?city=X", 10) for i in range(50)]
    rows += [(f"{HOST}/q{i:02d}?email=a", 1) for i in range(10)]
    (_, out, _), _ = _go(monkeypatch, capsys, rows)
    assert len(out["rows"]) == 50 and out["rows_omitted"] == 10 and out["shape_count"] == 60
    assert all("email" not in r["params"] for r in out["rows"])
    assert out["watch"]["email"] == {
        "events": 10, "shapes": 10,
        "top_paths": [{"path": f"/q0{i}", "events": 1} for i in range(3)]}
    assert {b["param"]: b["events"] for b in out["by_param"]} == {"city": 500, "email": 10}
    assert "top 50 shapes of 60" in out["coverage_note"]


def test_pii_params_equal_the_list_in_analytics_js():
    js = (ROOT / "src" / "astro_ai" / "static" / "analytics.js").read_text()
    m = re.search(r"var PII_PARAMS = \[([^\]]*)\]", js)
    assert m, "analytics.js no longer declares `var PII_PARAMS = [...]`"
    assert tuple(re.findall(r"'([^']+)'", m.group(1))) == ga.PII_PARAMS


@pytest.mark.parametrize("other", ["--daily", "--events", "--anomalies", "--trend",
                                   "--journeys", "--cohorts"])
def test_page_locations_with_another_report_is_refused_before_any_request(
        monkeypatch, capsys, other):
    fake = Fake({}, {})
    with pytest.raises(SystemExit) as e:
        run(monkeypatch, capsys, fake, "--page-locations", other)
    assert "--page-locations" in str(e.value) and other in str(e.value)
    assert fake.bodies == []


def test_page_locations_off_leaves_the_default_report_untouched(monkeypatch, capsys):
    calls = []

    def fake(url, body, bearer):
        calls.append(body)
        return {"rows": []}

    _, out, _ = run(monkeypatch, capsys, fake)
    assert "mode" not in out and len(calls) == 2
    assert "pageLocation" not in [d["name"] for d in calls[0]["dimensions"]]
