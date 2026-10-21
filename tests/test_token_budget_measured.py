"""The /admin/ops token columns are measured, not invented (#473).

WHAT WAS WRONG
--------------
`routes/subscribe.py` and `routes/llm_support.py` both recorded

    in_tok  = cache.estimate_tokens(text) * 2
    out_tok = cache.estimate_tokens(text)

where `text` is the model's OUTPUT. So input was *defined* as twice an estimate
of the output -- a fixed 2:1 for every route forever -- and the provider's real
`usage`, which `providers.py` already parses for the prefix-cache counters, was
thrown away.

Two errors compounded. The ratio was fabricated, and the UNIT was wrong: a
cache-layer "call" is a cached DOCUMENT, and `generate_rashifal` fans one out to
twelve provider calls. The panel reported 7,692 input tokens for a rashifal job
that measures ~38,500 -- about 5x -- and read `144% of one bucket`, a figure
that was right only by accident.

WHAT THESE TESTS HOLD
---------------------
That the measured pair reaches the store, that a SILENCE is never booked as a
zero, that the measured figure divides by provider calls rather than documents,
and that a new provider route cannot arrive unmapped and lose its tokens
quietly -- the last being the only one of the four that no reader would ever
notice going wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from astro_ai import llm_stats, ops_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def day(monkeypatch, tmp_path):
    """An isolated per-day stats file, so record() writes somewhere we can read."""
    monkeypatch.setattr(llm_stats, "_LOCAL_FALLBACK_DIR", tmp_path)
    monkeypatch.setattr(llm_stats.storage, "update_json", lambda *a, **k: None)
    return tmp_path


def _blob(day_dir: Path) -> dict:
    import json
    files = list(day_dir.glob("*.json"))
    assert files, "record() wrote nothing"
    return json.loads(files[0].read_text())


# --------------------------------------------------------------------------- #
# the store
# --------------------------------------------------------------------------- #

def test_the_measured_pair_is_stored_per_route(day):
    llm_stats.record(provider="groq120", model="openai/gpt-oss-120b",
                     route="rashifal_single", prompt_tokens=3210, completion_tokens=1923)
    llm_stats.record(provider="groq120", model="openai/gpt-oss-120b",
                     route="rashifal_single", prompt_tokens=3200, completion_tokens=1900)
    mb = _blob(day)["measured_by_route"]["rashifal_single"]
    assert mb == {"calls": 2, "measured": 2,
                  "input_tokens": 6410, "output_tokens": 3823}


def test_a_silence_is_not_a_zero(day):
    """The rule this module already keeps for the prefix cache, kept here too.

    A provider that reports no usage must add to `calls` and to nothing else.
    Booking it as a measured zero would drag every mean down with nothing on the
    page to explain it -- the exact defect QA round 4 found in the prefix-cache
    counters, and the reason `measured` is a separate denominator from `calls`.
    """
    llm_stats.record(provider="x", model="m", route="natal",
                     prompt_tokens=4000, completion_tokens=1000)
    llm_stats.record(provider="x", model="m", route="natal")               # silent
    llm_stats.record(provider="x", model="m", route="natal", prompt_tokens=4000)  # half
    mb = _blob(day)["measured_by_route"]["natal"]
    assert mb["calls"] == 3, "every call counts"
    assert mb["measured"] == 1, "only the fully-reported one is a measurement"
    assert mb["input_tokens"] == 4000 and mb["output_tokens"] == 1000
    # and the mean is the honest one, not diluted by the two it could not size
    assert mb["input_tokens"] / mb["measured"] == 4000


# --------------------------------------------------------------------------- #
# the panel
# --------------------------------------------------------------------------- #

def _rows(by_route, measured_by_route):
    """Drive ops_data's row builder with a pinned usage summary."""
    usage = {"total_calls": 0, "cache_hits": 0, "cache_misses": 0,
             "by_route": by_route, "measured_by_route": measured_by_route}
    return {r["route"]: r for r in ops_data._route_rows(usage)}


def test_measured_tokens_divide_by_provider_calls_not_by_documents():
    """The 12x half of the defect, which better arithmetic alone would not fix.

    One cached rashifal document, one miss, twelve provider calls. Dividing the
    measured sum by the single miss would report a 38,520-token "request" --
    arithmetically derived from real numbers and still wrong by 12x, because the
    thing a reader compares against an 8,000 TPM bucket is one CALL.
    """
    rows = _rows(
        by_route=[{"route": "rashifal", "calls": 2, "hits": 1,
                   "input_tokens": 15384, "output_tokens": 7692}],
        measured_by_route=[{"route": "rashifal_single", "calls": 12, "measured": 12,
                            "input_tokens": 38520, "output_tokens": 23076}],
    )
    r = rows["rashifal"]
    assert r["token_source"] == "measured"
    assert r["llm_calls"] == 12
    assert r["fan_out"] == 12.0
    # per CALL -- what the TPM bucket is charged, and the only figure the
    # `of one bucket` column may use. 38,520+23,076 over 12 calls.
    assert r["per_call_total"] == 5133
    assert r["tpm_pct"] == 64, "5,133/8,000 -- the old panel said 144%"
    # per REQUEST -- what one cached document costs, over 1 miss. This is the
    # daily-budget figure and it is 12x the per-call one, which is the whole
    # reason both exist.
    assert r["per_request"] == 38520
    assert r["per_request_total"] == 61596


def test_a_route_with_no_measurement_falls_back_and_says_so():
    """Every day recorded before #473 has no measured_by_route at all.

    Rendering those as zero would erase months of history; rendering them as
    measured would launder the estimate. The row keeps the old number and
    carries the label that says what it is.
    """
    rows = _rows(
        by_route=[{"route": "natal", "calls": 3, "hits": 1,
                   "input_tokens": 5460, "output_tokens": 2730}],
        measured_by_route=[],
    )
    r = rows["natal"]
    assert r["token_source"] == "estimated"
    assert r["per_request"] == 2730, "5,460 / 2 misses, the old denominator"
    assert r["llm_calls"] is None and r["fan_out"] is None


def test_a_measured_silence_does_not_promote_the_row():
    """`calls` without `measured` is not a measurement.

    A route whose provider never reported usage has rows in measured_by_route
    with measured=0 and zero tokens. Preferring those would print 0 tokens per
    request for a feature that is plainly spending some -- a confident zero,
    which this codebase treats as worse than a dash.
    """
    rows = _rows(
        by_route=[{"route": "ask", "calls": 4, "hits": 2,
                   "input_tokens": 2000, "output_tokens": 1000}],
        measured_by_route=[{"route": "ask", "calls": 4, "measured": 0,
                            "input_tokens": 0, "output_tokens": 0}],
    )
    r = rows["ask"]
    assert r["token_source"] == "estimated"
    assert r["per_request"] == 1000


# --------------------------------------------------------------------------- #
# the mapping, which is the one that fails silently
# --------------------------------------------------------------------------- #

def test_every_provider_route_maps_to_a_feature_or_is_one():
    """A new route must not arrive unmapped and lose its tokens quietly.

    `PROVIDER_ROUTE_FEATURE` only lists the rows where the provider name and the
    cached feature name differ. An unmapped new route does not crash and does
    not render wrong -- it renders as its own row with no cache figures, which
    looks like a feature nobody uses. Nothing else in the suite would notice.

    Both sides are scanned OUT OF THE SOURCE rather than listed here, because a
    hand-maintained list of routes is the thing that goes stale.
    """
    llm_src = (ROOT / "src" / "astro_ai" / "llm.py").read_text()
    provider_routes = set(re.findall(r'route="([a-z_0-9]+)"', llm_src))
    assert provider_routes, "the route= scan found nothing; this test is vacuous"

    cache_src = "\n".join(
        (ROOT / "src" / "astro_ai" / "routes" / f).read_text()
        for f in ("subscribe.py", "llm_support.py")
    ) + "\n".join(
        p.read_text() for p in (ROOT / "src" / "astro_ai" / "routes").glob("*.py")
    )
    features = set(re.findall(r'route="([a-z_0-9]+)"', cache_src))

    unmapped = {r for r in provider_routes
                if r not in features and r not in ops_data.PROVIDER_ROUTE_FEATURE}
    assert not unmapped, (
        f"provider routes with no feature: {sorted(unmapped)}. Add each to "
        f"ops_data.PROVIDER_ROUTE_FEATURE, or its tokens land on a row of their own."
    )


def test_the_mapping_only_contains_routes_that_actually_differ():
    """An entry for a route that needs none is dead weight that reads as fact."""
    for provider_route, feature in ops_data.PROVIDER_ROUTE_FEATURE.items():
        assert provider_route != feature, f"{provider_route} maps to itself"


def test_the_fan_out_mapping_is_what_folds_rashifal_onto_its_feature():
    """The join itself, end to end: provider rows land on the feature row."""
    rows = _rows(
        by_route=[{"route": "rashifal", "calls": 1, "hits": 0,
                   "input_tokens": 1, "output_tokens": 1},
                  {"route": "dasha_deep_dive", "calls": 1, "hits": 0,
                   "input_tokens": 1, "output_tokens": 1}],
        measured_by_route=[{"route": "rashifal_single", "calls": 12, "measured": 12,
                            "input_tokens": 1200, "output_tokens": 600},
                           {"route": "dasha", "calls": 1, "measured": 1,
                            "input_tokens": 900, "output_tokens": 300}],
    )
    assert rows["rashifal"]["per_call_total"] == 150, "(1200+600)/12 calls"
    assert rows["dasha_deep_dive"]["per_call_total"] == 1200, "(900+300)/1 call"
    assert "rashifal_single" not in rows and "dasha" not in rows


# --------------------------------------------------------------------------- #
# the source of the defect, so it cannot come back
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("mod", ["routes/subscribe.py", "routes/llm_support.py"])
def test_no_module_defines_input_tokens_as_a_multiple_of_the_output(mod):
    """`estimate_tokens(text) * 2` is the defect itself, in one line.

    It is still legal to ESTIMATE -- the cache layer has no usage block and the
    fallback above depends on it. What is not legal is deriving input from
    output by a constant, because the result is a ratio wearing the costume of a
    measurement and nothing on the page could tell the difference for months.
    """
    src = (ROOT / "src" / "astro_ai" / mod).read_text()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "estimate_tokens(text) * 2" not in code


def test_saved_by_cache_counts_whole_documents_not_single_calls():
    """A cache hit avoids all twelve calls, not one.

    Raised by the owner mid-change: "are we fixing the cache usage panel as
    well?" It was broken at that moment, by this very change. `saved` is
    `hits x cost-of-a-miss`, `hits` counts DOCUMENTS, and the first draft
    divided the measured sums by CALLS -- so one avoided rashifal document
    scored 3,210 tokens instead of ~38,520. A wrong number assembled out of two
    right ones, which is the hardest kind to see.
    """
    rows = _rows(
        by_route=[{"route": "rashifal", "calls": 2, "hits": 1,
                   "input_tokens": 0, "output_tokens": 0}],
        measured_by_route=[{"route": "rashifal_single", "calls": 12, "measured": 12,
                            "input_tokens": 38520, "output_tokens": 23076}],
    )
    r = rows["rashifal"]
    assert r["saved"] == 38520, "one hit avoids one document: 38,520 input tokens"
    assert r["saved"] != r["per_call_total"], "a hit does not avoid a single call"


def test_a_route_with_no_tokens_at_all_renders_unknown_not_zero():
    """Days recorded after #473 carry input_tokens=0 from the cache layer.

    A confident `0 tokens per request` for a feature that is plainly spending
    some is the same class of claim as the 2:1 ratio this change removed: it
    reads as a measurement and is not one. The row says `unknown` and every
    per-request figure stays None, so the template prints a dash.
    """
    rows = _rows(
        by_route=[{"route": "today", "calls": 5, "hits": 2,
                   "input_tokens": 0, "output_tokens": 0}],
        measured_by_route=[],
    )
    r = rows["today"]
    assert r["token_source"] == "unknown"
    assert r["per_request"] is None and r["per_request_total"] is None
    assert r["tpm_pct"] is None
    assert r["saved"] == 0


# --------------------------------------------------------------------------- #
# the Team panel's last-run light
# --------------------------------------------------------------------------- #

def _collector():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_cap", ROOT / "scripts" / "collect_agent_performance.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("conclusion,status,self_reporting,expected", [
    ("success", None, False, "green"),
    ("failure", None, False, "red"),
    ("timed_out", None, False, "red"),
    ("startup_failure", None, False, "red"),
    # `loop-outcomes` exits non-zero when it FINDS something. Painting that the
    # same red as a crash is what the collector's own header says teaches a
    # reader to ignore red.
    ("failure", None, True, "amber"),
    ("cancelled", None, False, "amber"),
    # A run still in flight carries no conclusion. The first version of this
    # column painted it green, which is a claim about a run that has not
    # finished.
    (None, "in_progress", False, "running"),
    (None, "queued", False, "running"),
    # Never a default of green: a loop that has never run has no health, and
    # saying otherwise is the silence this collector exists to break.
    (None, None, False, "unknown"),
    ("", None, False, "unknown"),
])
def test_last_run_health_colours(conclusion, status, self_reporting, expected):
    assert _collector()._health(conclusion, status, self_reporting) == expected


def test_the_team_table_draws_the_last_run_and_not_only_its_date():
    """The column the owner asked for, pinned where it can be dropped.

    `last_conclusion` had been collected and committed into agents.json since
    #345 and the template printed only `last_run[0:10]` -- the date. So a loop
    between slots with a red most-recent run looked exactly like one resting,
    which is how `agent-measure` read healthy on this page through six days of
    failing every single run (#393).
    """
    tmpl = (ROOT / "src" / "astro_ai" / "templates" / "admin_ops.html").read_text()
    head = tmpl[tmpl.index("<thead><tr><th>Loop</th>"):]
    head = head[:head.index("</thead>")]
    assert "<th>Last run</th>" in head, "the Last run column is gone from the header"
    assert "r.last_conclusion" in tmpl, "the conclusion is collected but not drawn"
    # The colour must come from the collector, which is the only side that
    # knows SELF_REPORTING. A template mapping the conclusion string itself
    # would paint a working report as a crash.
    assert "r.last_run_health" in tmpl
    assert "'failure'" not in tmpl.split("<th>Last run</th>")[1][:1200], (
        "the template is deciding the colour from the conclusion string again")


def test_the_collector_emits_the_health_field_the_template_reads():
    """Two files, one contract: the field name is spelled the same on both sides.

    An absent key renders as the neutral chip -- no error, no blank, just every
    loop quietly grey. Nothing else in the suite would notice.
    """
    src = (ROOT / "scripts" / "collect_agent_performance.py").read_text()
    assert '"last_run_health"' in src
    assert "SELF_REPORTING" in src.split('"last_run_health"')[1][:400], (
        "last_run_health must be computed with the self-reporting flag")


# --------------------------------------------------------------------------- #
# shipped by the loop vs shipped by a session
# --------------------------------------------------------------------------- #

def _pr(number, *, bot, merged="2026-10-21T10:00:00Z", ref="issue/1-x"):
    return {"number": number, "title": "t", "merged_at": merged,
            "html_url": f"u/{number}", "head": {"ref": ref},
            "user": {"login": "claude[bot]" if bot else "mahAnuj",
                     "type": "Bot" if bot else "User"}}


def _shipped(prs, monkeypatch):
    from datetime import datetime, timezone
    from astro_ai import ops_today
    monkeypatch.setattr(ops_today, "_pages",
                        lambda url, **k: ((prs, False) if "pulls" in url else ([], False)))
    return ops_today.fetch_today(
        "r", datetime(2026, 10, 21, tzinfo=timezone.utc), timeout=1)


def test_shipped_splits_by_author_type(monkeypatch):
    got = _shipped([_pr(1, bot=True), _pr(2, bot=True), _pr(3, bot=False)], monkeypatch)
    assert got["shipped_by_loop"] == 2
    assert got["shipped_by_session"] == 1
    assert len(got["shipped"]) == 3, "the total is unchanged; this only labels it"
    assert got["shipped_by_loop"] + got["shipped_by_session"] == len(got["shipped"])


def test_the_branch_prefix_is_not_what_decides_it(monkeypatch):
    """`issue/*` is the obvious discriminator and it is wrong.

    PR #471 is an `issue/*` branch opened by a human session; #445, #443 and
    most of that week are `fix/*` and `feat/*` from the same hands, while #469
    is `issue/*` from the App. The branch says what the work was about. Only
    the author says who did it.
    """
    got = _shipped([_pr(1, bot=False, ref="issue/393-x"),    # human on issue/*
                    _pr(2, bot=True, ref="partial/398-y")],  # loop not on issue/*
                   monkeypatch)
    assert got["shipped_by_session"] == 1 and got["shipped_by_loop"] == 1
    by = {s["pr"]: s["by"] for s in got["shipped"]}
    assert by == {1: "session", 2: "loop"}


def test_an_unknown_author_counts_as_a_session_not_as_the_loop(monkeypatch):
    """The safe direction when the API answers something unexpected.

    Over-reporting loop output is the failure that matters here: this page
    exists to say whether the autonomous team is working, and a number that
    flatters it is worse than one that undersells it.
    """
    bare = {"number": 9, "title": "t", "merged_at": "2026-10-21T10:00:00Z",
            "html_url": "u", "head": {"ref": "x"}}          # no `user` at all
    got = _shipped([bare], monkeypatch)
    assert got["shipped_by_loop"] == 0
    assert got["shipped_by_session"] == 1
