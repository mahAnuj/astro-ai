"""The analyst reports the owner's growth levers every run, and the busiest pages
reach verification without anyone asking (owner, 2026-11-15)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vf = _load("verify_first")
rq = _load("research_queue")


def ga4(rows):
    return {"window": ["2026-10-16", "2026-11-12"], "rows": rows}


def row(landing, sessions, bounce=0.5, **kw):
    return {"landing": landing, "channel": "Organic Search", "sessions": sessions,
            "bounce_rate": bounce, **kw}


# --- verify_first.py ----------------------------------------------------------

def test_variants_of_one_page_are_folded_and_admin_is_dropped():
    out = vf.build(ga4([row("/learn/x/", 10), row("/learn/x?fbclid=1", 4),
                        row("/admin/ops", 50), row("(not set)", 30)]), {"rows": []})
    assert [r["path"] for r in out["rows"]] == ["/learn/x"]
    assert out["rows"][0]["sessions"] == 14


def test_ranked_by_engaged_sessions_not_raw_sessions():
    out = vf.build(ga4([row("/a", 100, bounce=0.9), row("/b", 30, bounce=0.1)]), {"rows": []})
    assert [r["path"] for r in out["rows"]] == ["/b", "/a"]
    assert out["basis"] == "sessions x (1 - bounce_rate)"


def test_ga4_engaged_sessions_and_time_win_when_present():
    out = vf.build(ga4([row("/a", 10, engaged_sessions=7, engagement_seconds=600)]), {"rows": []})
    r = out["rows"][0]
    assert (r["engaged_sessions"], r["avg_engagement_seconds"]) == (7.0, 60)
    assert out["basis"] == "GA4 engagedSessions"


def test_search_impressions_join_by_path_and_the_module_is_named():
    gsc = {"rows": [{"page": "https://shubhagya.com/learn/x/", "impressions": 300,
                     "clicks": 3, "position": 6.0}]}
    r = vf.build(ga4([row("/learn/x", 5)]), gsc)["rows"][0]
    assert (r["gsc_impressions"], r["gsc_position"]) == (300, 6.0)
    assert r["serves"] == "templates/learn/x.html"


def test_unreadable_input_exits_2(tmp_path):
    out = tmp_path / "o.json"
    assert vf.main(["--ga4", str(tmp_path / "nope.json"), "--gsc", "x", "--out", str(out)]) == 2
    assert not out.exists()


# --- fetch_ga4.py engagement fields ------------------------------------------

def test_engagement_metrics_are_read_by_index_and_optional():
    fg = _load("fetch_ga4")
    mv = [{"value": v} for v in ("10", "0.5", "2", "8", "6", "540.0")]
    assert fg._engagement(mv) == {"engaged_sessions": 6, "engagement_seconds": 540}
    assert fg._engagement(mv[:4]) == {}
    src = (ROOT / "scripts/fetch_ga4.py").read_text()
    assert src.index('"activeUsers"') < src.index('"engagedSessions"') < src.index('"userEngagementDuration"')


# --- research queue ----------------------------------------------------------

def test_the_research_queue_carries_the_busiest_pages(tmp_path):
    p = tmp_path / "vf.json"
    p.write_text(json.dumps({"window": ["a", "b"], "rows": [
        {"path": "/learn/x", "engaged_sessions": 9, "gsc_impressions": 100, "serves": "t"}]}))
    text = rq.verify_first_section(p)
    assert "/learn/x" in text and "knowledge/*.md" in text
    assert rq.verify_first_section(tmp_path / "absent.json") == ""


# --- wiring ------------------------------------------------------------------

def test_measure_ranks_pages_before_the_analyst_and_the_prompt_names_the_levers():
    doc = yaml.safe_load((ROOT / ".github/workflows/agent-measure.yml").read_text())
    steps = doc["jobs"]["measure"]["steps"]
    rank = next(i for i, s in enumerate(steps) if "verify_first.py" in (s.get("run") or ""))
    agent = next(i for i, s in enumerate(steps) if "claude-code-action" in (s.get("uses") or ""))
    assert rank < agent and steps[rank].get("continue-on-error") is True
    assert "/tmp/measure/verify-first.json" in steps[rank]["run"]
    prompt = steps[agent]["with"]["prompt"]
    for must in ("/tmp/verify-first.json", "Levers", "last three", "festivals.py"):
        assert must in prompt, must


def test_discover_treats_the_analysts_demand_sections_as_its_inbox():
    text = (ROOT / ".github/workflows/agent-discover.yml").read_text()
    assert '"Search demand"' in text and '"Content opportunities"' in text


def test_the_analyst_definition_carries_every_lever():
    md = (ROOT / ".claude/agents/analyst.md").read_text()
    for lever in ("**Growth**", "**Where time is spent**", "**Errors**", "**Search demand**",
                  "**Content opportunities**", "**Index status**", "**Measurement gaps**"):
        assert lever in md, lever


# --- spikes explained (2026-11-15) -------------------------------------------

def _days(vals):
    return [{"date": f"2026-11-{i + 1:02d}", "active_users": v} for i, v in enumerate(vals)]


def test_the_11_06_spike_is_found_and_ordinary_days_are_not():
    fg = _load("fetch_ga4")
    vals = [21, 29, 24, 22, 23, 32, 25, 28, 57, 22, 26]
    hits = fg.spike_days(_days(vals))
    assert [h["active_users"] for h in hits] == [57]
    assert fg.spike_days(_days([20, 22, 25, 21, 24, 23, 26])) == []
    assert fg.spike_days(_days([3, 1, 2])) == [], "too few days to call anything unusual"


def test_the_explanation_separates_readers_from_bots_and_points_at_discover():
    fg = _load("fetch_ga4")
    readers = [{"sessionSourceMedium": "google / organic", "landingPagePlusQueryString": "/learn/x",
                "sessions": 30, "new_users": 28, "engaged_rate": 0.6, "avg_engagement_seconds": 48.0}]
    bots = [{"sessionSourceMedium": "(direct) / (none)", "landingPagePlusQueryString": "/",
             "sessions": 40, "new_users": 40, "engaged_rate": 0.02, "avg_engagement_seconds": 0.4}]
    tech = [{"browser": "Safari", "deviceCategory": "mobile", "country": "India",
             "sessions": 30, "new_users": 28, "engaged_rate": 0.6, "avg_engagement_seconds": 48.0}]
    r = fg.explain(readers, tech)
    assert "real readers" in r and "Discover" in r and "Safari on mobile in India" in r
    assert "automated" in fg.explain(bots, [])


def test_measure_fetches_spikes_and_discover_and_hands_them_to_the_analyst():
    text = (ROOT / ".github/workflows/agent-measure.yml").read_text()
    assert "fetch_ga4.py --days 28 --anomalies > /tmp/ga4-anomalies.json" in text
    assert "fetch_gsc.py --days 28 --discover > /tmp/gsc-discover.json" in text
    assert "/tmp/ga4-anomalies.json /tmp/gsc-discover.json /tmp/measure/" in text
    assert "ga4-anomalies.json" in (ROOT / ".claude/agents/analyst.md").read_text()
