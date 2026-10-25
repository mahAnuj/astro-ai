"""The "Cached-token accounting" table on /admin/ops (#475 Phase 1b).

Every sentence on this panel is asserted here, and a sentence no test can make
fail was deleted rather than reworded. That is not decoration: the Phase 0 panels
shipped false sentences through seven QA rounds ("0 of 0 waited", a column count
that was never counted, a justification that outlived its refutation).

Three states a cell can be in, and they must not look alike:
  * a dash          -- the probe recorded nothing for the model in this window
  * 0 / a number    -- it ran; a model with no warm sample reads 0, not a dash
  * "no header ..." -- every classified call arrived without usable headers

The verdict printed is `ratelimit_probe.verdict()` applied to the window; the
decision recorded in ARCHITECTURE.md is a separate act and is PENDING.
"""
from __future__ import annotations

import html as html_lib
import os
import re

import pytest

from astro_ai import events, llm_stats, ops_data
from astro_ai import ratelimit_probe as rp

K120, K20, KOAI = "groq120|openai/gpt-oss-120b", "groq20|openai/gpt-oss-20b", "openai|gpt-4o-mini"


def probe(**kw):
    return {**dict.fromkeys(rp.FIELDS, 0), **kw}


def urow(key, ratelimit=None, calls=10):
    prov, _, model = key.partition("|")
    return {"key": key, "provider": prov, "model": model, "calls": calls, "measured": calls,
            "input_tokens": 9000, "output_tokens": 4000, "peak_tpm": 6000,
            "peak_minute": "2026-10-22T14:03+00:00", "reserved": None, "waits": None,
            "wait_ms": None, "skips": None, "forced": None, "ratelimit": ratelimit}


def usage(rows, days_rec=3, rl_days=2, days=7):
    return {"days": days, "model_days_recorded": days_rec, "paced_days": 0,
            "ratelimit_days": rl_days, "measured_by_model": rows}


#: 24 warm samples kept of 30 warm calls; 6 isolated colds of 8 cold calls. Groq's header
#: sits ~1,100 above the prediction on average, with 3 samples individually voting discounted.
POPULATED = probe(warm_seen=30, warm_n=24, warm_rem=24 * 5000, warm_exp=24 * 3900,
                  warm_cached=24 * 2304, warm_disc=3, cold_seen=8, cold_n=6, cold_rem=6 * 4000,
                  cold_exp=6 * 4000 + 75, cold_abs=75, skip_noanchor=3, skip_overlap=2,
                  skip_nohdr=1, skip_clamp=2, last_limit=8000)


# --------------------------------------------------------------------------- #
# the rows
# --------------------------------------------------------------------------- #

def test_rows_turn_sums_into_means_and_keep_the_skip_breakdown():
    (r,) = ops_data._ratelimit_rows(usage([urow(K120, POPULATED)]), [K120])
    assert (r["warm_n"], r["warm_seen"], r["cold_n"], r["cold_seen"]) == (24, 30, 6, 8)
    assert (r["mean_rem"], r["mean_exp"], r["mean_cached"]) == (5000, 3900, 2304)
    assert r["skips"] == {"noanchor": 3, "overlap": 2, "nohdr": 1, "clamp": 2}
    assert r["disc"] == 3 and r["cold_mean_abs"] == 12.5 and r["last_limit"] == 8000
    assert r["f"] == pytest.approx((5000 - 3900) / 2304)
    assert r["verdict"] == rp.verdict(POPULATED)["verdict"] == "PARTIAL"
    assert r["no_header"] is False


def test_a_model_with_no_probe_row_is_none_and_one_that_ran_with_no_samples_is_zero():
    rows = {r["key"]: r for r in ops_data._ratelimit_rows(usage([
        urow(K120, probe(warm_seen=0, cold_seen=3, skip_noanchor=1, cold_n=2)),
        urow(K20)]), [K120, K20, KOAI])}
    assert rows[K20]["probe"] is None and rows[KOAI]["probe"] is None
    assert rows[K120]["probe"] is not None and rows[K120]["warm_n"] == 0
    assert rows[K120]["mean_rem"] is None, "no warm sample means no mean, not a mean of zero"


def test_every_call_without_a_header_is_the_no_header_state_and_a_mixed_one_is_not():
    only = probe(warm_seen=4, cold_seen=2, skip_nohdr=6)
    mixed = probe(warm_seen=4, cold_seen=2, skip_nohdr=5, skip_noanchor=1)
    rows = {r["key"]: r for r in ops_data._ratelimit_rows(
        usage([urow(K120, only), urow(K20, mixed)]), [K120, K20])}
    assert rows[K120]["no_header"] is True and rows[K120]["no_header_calls"] == 6
    assert rows[K20]["no_header"] is False
    assert ops_data._ratelimit_rows({"days": 7}, [K120])[0]["probe"] is None


# --------------------------------------------------------------------------- #
# the page
# --------------------------------------------------------------------------- #

@pytest.fixture
def _ops(monkeypatch):
    monkeypatch.setattr(ops_data, "LIVE_ISSUES", False)
    monkeypatch.setattr(ops_data, "LIVE_TODAY", False)
    monkeypatch.setattr(events, "error_breakdown", lambda **k: {})
    ops_data._app_cache.clear()
    yield
    ops_data._app_cache.clear()


def page(monkeypatch, extra, chain=(K120, K20)):
    from fastapi.testclient import TestClient

    from astro_ai.main import app
    from astro_ai.routes import deps
    base = {"days": 7, "total_calls": 40, "cache_hits": 0, "cache_misses": 40,
            "hit_rate_pct": 0, "total_input_tokens": 0, "total_output_tokens": 0, "by_route": []}
    monkeypatch.setattr(llm_stats, "usage_summary", lambda d: {**base, "days": d, **extra})
    monkeypatch.setattr(llm_stats, "range_summary", lambda d: {
        "days": [], "aggregate": {"fallback_reasons": {}}})
    monkeypatch.setattr(ops_data, "_chain_keys", lambda: list(chain))
    ops_data._app_cache.clear()
    pw = os.environ.get("ADMIN_PASSWORD", deps._ADMIN_DEV_FALLBACK)
    r = TestClient(app).get("/admin/ops", auth=("admin", pw))
    assert r.status_code == 200, r.status_code
    return r.text


def panel(html: str) -> str:
    start = html.index("Cached-token accounting")
    return html[start:html.index("</section>", start)]


def cells(p: str, model: str) -> list[str]:
    for tr in re.findall(r"<tr>.*?</tr>", p, flags=re.S):
        if model in tr:
            return [" ".join(re.sub(r"<[^>]+>", " ", td).split())
                    for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
    raise AssertionError(f"no row for {model}")


def test_a_model_the_probe_never_saw_prints_a_dash(_ops, monkeypatch):
    p = panel(page(monkeypatch, usage([urow(K120), urow(K20, POPULATED)])))
    assert cells(p, "gpt-oss-120b")[1:] == ["—"]
    assert "None" not in p


def test_a_probe_that_ran_and_kept_no_warm_sample_prints_zero_not_a_dash(_ops, monkeypatch):
    p = panel(page(monkeypatch, usage([urow(K120, probe(
        warm_seen=0, cold_seen=3, cold_n=2, cold_abs=4, skip_noanchor=1))])))
    c = cells(p, "gpt-oss-120b")
    assert c[1].startswith("0 of 0 warm calls"), c
    assert c[2] == "—" and c[3] == "—" and c[4] == "—", "no warm sample, no mean"
    assert c[5] == "2 isolated 3 cold calls excluded from the warm count · mean |error| 2.0", c
    assert c[6] == "INSUFFICIENT"
    assert "None" not in p


def test_a_populated_row_prints_every_figure_the_header_describes(_ops, monkeypatch):
    p = panel(page(monkeypatch, usage([urow(K120, POPULATED)])))
    c = cells(p, "gpt-oss-120b")
    assert len(c) == 7
    assert c[1] == ("24 of 30 warm calls · skipped, warm and cold: 3 no anchor · 2 overlapped · "
                    "1 no header · 2 clamped"), c[1]
    assert c[2] == "5,000 vs 3,900", c[2]
    assert c[3] == "2,304"
    assert c[4] == "0.48 3 of 24 samples individually discounted", c[4]
    assert c[5] == "6 isolated 8 cold calls excluded from the warm count · mean |error| 12.5", c[5]
    assert c[6] == "PARTIAL"
    assert "None" not in p


def test_cold_calls_are_never_folded_into_the_warm_sample_count(_ops, monkeypatch):
    only_cold = probe(cold_seen=40, cold_n=39, cold_rem=39 * 4000, cold_exp=39 * 4000,
                      skip_noanchor=1)
    c = cells(panel(page(monkeypatch, usage([urow(K120, only_cold)]))), "gpt-oss-120b")
    assert c[1].startswith("0 of 0 warm calls") and c[5].startswith("39 isolated 40 cold calls excluded")


def test_the_verdict_cell_is_the_probes_verdict(_ops, monkeypatch):
    full = probe(warm_seen=25, warm_n=25, warm_rem=25 * 4000, warm_exp=25 * 4000,
                 warm_cached=25 * 2304, cold_seen=6, cold_n=6, cold_rem=6 * 4000, cold_exp=6 * 4000)
    disc = {**full, "warm_rem": 25 * (4000 + 2304), "warm_disc": 25}
    p = panel(page(monkeypatch, usage([urow(K120, full), urow(K20, disc)])))
    assert cells(p, "gpt-oss-120b")[6] == "FULL WEIGHT"
    assert cells(p, "gpt-oss-20b")[6] == "DISCOUNTED"
    assert cells(p, "gpt-oss-20b")[4].startswith("1.00 25 of 25 samples individually discounted")


def test_every_call_without_a_header_prints_that_and_no_verdict(_ops, monkeypatch):
    p = panel(page(monkeypatch, usage([urow(K120, probe(warm_seen=9, cold_seen=3, skip_nohdr=12))])))
    c = cells(p, "gpt-oss-120b")
    assert c[1:] == ["no header received on 12 calls"], c
    assert "INSUFFICIENT" not in p.split("</table>")[0]


def test_the_table_has_seven_columns_and_the_empty_state_matches(_ops, monkeypatch):
    html = page(monkeypatch, usage([urow(K120, POPULATED)]))
    p = panel(html)
    assert len(re.findall(r"<th[ >]", p.split("</table>")[0])) == 7
    assert 'class="rt cols7"' in p
    assert ".rt.cols7{" in html, "the min-width rule must exist"
    empty = panel(page(monkeypatch, {}, chain=()))
    assert 'colspan="7"' in empty


def test_the_phase_0_table_still_ends_where_it_did(_ops, monkeypatch):
    """The new table sits UNDER the per-model table; it must not have changed its columns."""
    html = page(monkeypatch, usage([urow(K120, POPULATED)]))
    start = html.index("Tokens per minute, by model")
    phase0 = html[start:html.index("Cached-token accounting", start)]
    assert len(re.findall(r"<th[ >]", phase0.split("</table>")[0])) == 8


def flat(p: str) -> str:
    text = html_lib.unescape(" ".join(re.sub(r"<[^>]+>", " ", p).split()))
    return re.sub(r"\s+([,.;:])", r"\1", text)      # a tag boundary leaves "cold , is"


def test_the_fold_states_only_what_the_code_does(_ops, monkeypatch):
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    # measure-only: pinned for real by test_settle_is_unchanged in test_ratelimit_probe.py
    assert "Nothing here changes what the bucket charges" in text
    assert "a warm call is still settled at its full prompt + completion tokens" in text
    # the thresholds are printed FROM the constants the verdict applies
    assert (f"at least {rp.MIN_WARM} warm and {rp.MIN_COLD} cold samples") in text
    assert (f"exceeds {rp.COLD_NOISE_FRACTION * 100:.0f}% of the mean cached count") in text
    assert (f"FULL WEIGHT at a fraction of {rp.FULL_MAX_F:.2f} or less") in text
    assert (f"DISCOUNTED at {rp.DISCOUNT_MIN_F:.2f} or more") in text
    assert "A warm call is one whose provider reported cached_tokens above 0" in text
    assert "a call reporting 0 or nothing is cold, is never counted as a warm sample" in text
    assert "limit ÷ 60 per second" in text
    assert "Only requests that were served are counted" in text
    assert "This window has probe figures for 2 of 7 days" in text
    assert "Those thresholds are judgment, not measurement" in text


def test_the_phase_0_fold_points_at_the_table_that_now_exists(_ops, monkeypatch):
    """It used to say 'open, #396' -- a pointer to a closed issue. Now it names a table."""
    html = page(monkeypatch, usage([urow(K120, POPULATED)]))
    text = flat(html)
    assert ("whether Groq discounts them against TPM is being measured in the table below, "
            "#475 Phase 1b") in text
    assert "open, #396" not in text
    assert html.index("being measured in the table below") < html.index("Cached-token accounting")


def test_the_documented_thresholds_are_the_ones_the_verdict_applies():
    """The fold prints rules from constants; this pins that the constants are what verdict() reads."""
    c = {"warm_n": rp.MIN_WARM, "warm_cached": 2000 * rp.MIN_WARM, "warm_exp": 0,
         "warm_rem": 0, "warm_disc": 0, "cold_n": rp.MIN_COLD, "cold_abs": 0}
    assert rp.verdict(c)["verdict"] == "FULL WEIGHT"                      # f = 0
    c["warm_rem"] = int(rp.FULL_MAX_F * c["warm_cached"]) + 1000          # f just over the line
    assert rp.verdict(c)["verdict"] == "PARTIAL"
    c["warm_rem"] = int(rp.DISCOUNT_MIN_F * c["warm_cached"])
    c["warm_disc"] = c["warm_n"]
    assert rp.verdict(c)["verdict"] == "DISCOUNTED"
    c["cold_abs"] = int(rp.COLD_NOISE_FRACTION * 2000 * rp.MIN_COLD) + rp.MIN_COLD
    assert rp.verdict(c)["verdict"] == "NOISY"


def test_the_dash_and_zero_sentence_is_true(_ops, monkeypatch):
    html = page(monkeypatch, usage([urow(K120, probe(cold_seen=1, skip_noanchor=1)), urow(K20)]))
    text = flat(panel(html))
    assert "means the probe recorded nothing for the model in this window" in text
    assert "means it ran and kept no sample" in text
    assert cells(panel(html), "gpt-oss-120b")[1].startswith("0 of 0")
    assert cells(panel(html), "gpt-oss-20b")[1:] == ["—"]
