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
    assert r["skips"] == {"noanchor": 3, "overlap": 2, "nohdr": 1, "clamp": 2, "full": 0}
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
    # `bucket at ceiling` is counted apart from `clamped` (BUG-2 on PR #536): it
    # has two causes the counters cannot tell apart (calls spaced far apart, or a
    # request the size of the bucket), so it is shown, not interpreted, here.
    # `header-reported limit` renders here because ARCHITECTURE points at this
    # panel to settle whether the header is TPM, and it used to be computed and
    # then dropped (BUG-3).
    assert c[1] == ("24 of 30 warm calls · skipped, warm and cold: 3 no anchor · 2 overlapped · "
                    "1 no header · 2 clamped · 0 bucket at ceiling · "
                    "header-reported limit 8,000"), c[1]
    assert c[2] == "5,000 vs 3,900", c[2]
    assert c[3] == "2,304"
    assert c[4] == "0.48 3 of 24 samples individually discounted", c[4]
    assert c[5] == "6 isolated 8 cold calls excluded from the warm count · mean |error| 12.5", c[5]
    assert c[6] == "PARTIAL"
    assert "None" not in p


def test_a_tiny_negative_fraction_prints_as_zero_not_as_a_signed_zero(_ops, monkeypatch):
    """Rendered from a real run: f = -0.004 printed '-0.00', which reads as a measured sign."""
    near_zero = probe(warm_seen=30, warm_n=30, warm_rem=30 * 4000 - 300, warm_exp=30 * 4000,
                      warm_cached=30 * 2304, cold_seen=6, cold_n=6)
    c = cells(panel(page(monkeypatch, usage([urow(K120, near_zero)]))), "gpt-oss-120b")
    assert c[4].startswith("0.00 "), c[4]
    assert "-0.00" not in c[4]


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
    # (the threshold sentences themselves are pinned whole in test_the_threshold_sentences_...)
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


def test_the_dash_sentence_is_true_for_both_dash_situations(_ops, monkeypatch):
    """A dash is two different facts. QA found the fold calling both 'recorded nothing'."""
    seen_no_warm = probe(warm_seen=3, cold_seen=4, cold_n=2, cold_abs=4, skip_noanchor=3)
    html = page(monkeypatch, usage([urow(K120, seen_no_warm), urow(K20)]))
    p = panel(html)
    seen, unseen = cells(p, "gpt-oss-120b"), cells(p, "gpt-oss-20b")
    # situation 1: the model was never seen -> ONE dash spanning the row
    assert unseen[1:] == ["—"]
    # situation 2: seen, warm calls arrived, none kept -> the row is NOT 'nothing recorded'
    assert seen[1].startswith("0 of 3 warm calls"), seen
    assert seen[2:5] == ["—", "—", "—"], seen
    assert seen[6] == "INSUFFICIENT"
    text = flat(p)
    assert ("— means there is no figure to show: a row that is one dash means the probe recorded "
            "nothing for the model in this window, and a dash in the remaining-tokens, mean cached "
            "or discounted-fraction cell means the model was seen but no warm sample was kept to "
            "average") in text
    assert "0 means it ran and kept no sample" in text
    assert "means the probe recorded nothing for the model in this window;" not in text, \
        "the old sentence claimed that for EVERY dash"


def test_the_threshold_sentences_state_the_whole_rule_from_the_constants(_ops, monkeypatch):
    """The fold said 'DISCOUNTED at 0.75 or more'; verdict() also needs the vote."""
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    noise, vmax, vmin = (f"{rp.COLD_NOISE_FRACTION * 100:.0f}", f"{rp.VOTE_MAX * 100:.0f}",
                         f"{rp.VOTE_MIN * 100:.0f}")
    assert (f"It reads NOISY when the cold control’s mean absolute error exceeds {noise}% of the "
            f"mean cached count. Otherwise it reads FULL WEIGHT when the discounted fraction is "
            f"{rp.FULL_MAX_F:.2f} or less and at most {vmax}% of warm samples individually voted "
            f"discounted, DISCOUNTED when the fraction is {rp.DISCOUNT_MIN_F:.2f} or more and at "
            f"least {vmin}% did, and PARTIAL for everything else, including a fraction past a line "
            f"with too few votes. A warm sample votes discounted when Groq’s figure sits more than "
            f"{rp.VOTE_CACHED_FRACTION * 100:.0f}% of its cached count above the prediction.") in text
    # ... and each clause is what verdict() does, one side of each line at a time
    def v(**kw):
        return rp.verdict(counters(**kw))
    base = dict(warm_n=rp.MIN_WARM, cold_n=rp.MIN_COLD)
    assert v(**base, f=0.0, vote=rp.VOTE_MAX)["verdict"] == "FULL WEIGHT"
    assert v(**base, f=0.0, vote=0.35)["verdict"] == "PARTIAL", "fraction alone is not enough"
    assert v(**base, f=0.9, vote=rp.VOTE_MIN)["verdict"] == "DISCOUNTED"
    assert v(**base, f=0.9, vote=0.5)["verdict"] == "PARTIAL", "f past the line, too few votes"
    assert v(**base, f=0.9, vote=1.0, cold_mean_abs=0.3 * 2304)["verdict"] == "NOISY"
    # "mean absolute": a cold control whose errors cancel in sign still reads noisy
    assert rp.verdict({**counters(f=0.0), "cold_abs": 5 * 2304})["verdict"] == "NOISY"


def counters(*, warm_n=20, cold_n=5, f=0.0, cached=2304, vote=0.0, cold_mean_abs=0.0):
    """Same shape as test_ratelimit_probe.counters: counters that yield a chosen f, vote and cold error."""
    return {"warm_n": warm_n, "warm_cached": cached * warm_n,
            "warm_exp": 10000 * warm_n, "warm_rem": round((10000 + f * cached) * warm_n),
            "warm_disc": round(vote * warm_n),
            "cold_n": cold_n, "cold_abs": round(cold_mean_abs * cold_n)}


def test_the_live_verdict_is_not_the_recorded_decision_and_the_fold_says_so(_ops, monkeypatch):
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    assert ("The verdict column is a live reading of this window, not the recorded decision: the "
            f"row in ARCHITECTURE.md is written by a person after at least {rp.MIN_WARM} warm and "
            f"{rp.MIN_COLD} cold samples for the model.") in text


def _score(monkeypatch, remaining_after_warm):
    """One cold call anchors the bucket, then one isolated warm call whose header is chosen.

    The prediction is exactly 3,700 (anchor 7,000 minus 3,000 + 300), so a header of 3,700 is a
    full charge, below it is another consumer on the key, and +2,304 is cached tokens not charged.
    """
    rp.reset()
    monkeypatch.setattr(rp, "_clock", lambda: 0.0)
    key = "groq120|m"
    t = rp.begin(key)
    rp.finish(t, (8000, 7000), (3000, 0, False), 300)
    t = rp.begin(key)
    return rp.finish(t, (8000, remaining_after_warm), (3000, 2304, False), 300)


def test_the_other_caller_sentence_is_what_the_probe_does(_ops, monkeypatch):
    """Pins 'can only make cached tokens look fully charged, never discounted' to behaviour.

    QA flipped the sentence to 'look discounted, never fully charged' and every panel and probe
    test stayed green: the behaviour was tested in test_ratelimit_probe.py and the sentence in
    nothing. Here both are asserted by one test, so reversing either goes red.
    """
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    assert ("Another caller of the same key lowers Groq’s figure below the prediction, which can "
            "only make cached tokens look fully charged, never discounted") in text
    # the instrument CAN vote discounted: header 2,304 above the prediction
    assert _score(monkeypatch, 3700 + 2304)["warm_disc"] == 1
    assert _score(monkeypatch, 3700)["warm_disc"] == 0
    # ... and an extra consumer, at every size that leaves the arithmetic valid, never does
    totals = dict.fromkeys(("warm_n", "warm_rem", "warm_exp", "warm_cached", "warm_disc"), 0)
    for extra in (1, 300, 900, 1500, 2500, 3600):
        out = _score(monkeypatch, 3700 - extra)
        assert out["warm_exp"] - out["warm_rem"] == extra, "the extra consumer lowers the figure"
        assert out["warm_disc"] == 0, extra
        for k in totals:
            totals[k] += out[k]
    totals = {**totals, "warm_n": rp.MIN_WARM, "cold_n": rp.MIN_COLD, "cold_abs": 0}
    scale = rp.MIN_WARM / 6
    for k in ("warm_rem", "warm_exp", "warm_cached"):
        totals[k] = int(totals[k] * scale)
    v = rp.verdict(totals)
    assert v["f"] < 0 and v["verdict"] == "FULL WEIGHT", v


# --- the sentences added fixing the independent round's findings (PR #536) ----
#
# This file's rule is that every sentence on the panel is asserted here, and a
# sentence no test can make fail is deleted rather than reworded. The round
# found one that broke it: the fold promised a clamp was skipped when "the
# bucket was full or empty", the code checked only the empty end, and no test
# could tell. These pin the replacements.

def test_the_fold_describes_both_ceiling_branches_the_code_implements(_ops, monkeypatch):
    """BUG-2b. The old sentence was false of the code and asserted nowhere."""
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    assert ("the bucket was full when the call started, or would have refilled past full "
            "before it finished") in text, (
        "the fold no longer describes the ceiling skip, which is a counted "
        "outcome the reader sees in the breakdown"
    )
    assert "bucket was full or empty" not in text, (
        "the sentence that promised both ends while the code checked one is back"
    )


#: The fold's whole skip passage, verbatim as a reader sees it. It is pinned in FULL on
#: purpose: round 3 of PR #536 found a closing sentence spliced into the middle of an older
#: one ("... at all. The arithmetic does not hold) -- and is never counted as agreement."),
#: and every test then asserted a substring that the splice left intact.
SKIP_PASSAGE = (
    "every other candidate is counted under skipped — no anchor (nothing usable before it), "
    "overlapped, no header, clamped (the prediction fell outside the bucket, or Groq reported "
    "zero remaining), or at its ceiling (the bucket was full when the call started, or would "
    "have refilled past full before it finished, so the refill term cannot hold). That last one "
    "has two causes these counters cannot tell apart: the model’s calls are spaced far enough "
    "apart that the bucket had refilled completely, or the request is about the size of the "
    "whole bucket (the natal estimate is 98–101% of 8,000, the estimator’s charge rather than "
    "billed tokens). A model showing ceiling skips rising while warm samples stay at zero "
    "therefore needs calls closer together or a smaller request, and nothing on this panel says "
    "which; closer calls cannot help a request the size of the bucket. A skipped call is never "
    "counted as agreement."
)


def test_the_fold_skip_passage_reads_exactly_as_written_and_is_not_spliced(_ops, monkeypatch):
    """D1 of QA round 3. The whole passage, so a splice anywhere in it fails."""
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    assert SKIP_PASSAGE in text, "the skip passage in the fold no longer reads as written"
    # the closing sentence on its own, and the shape of the defect that shipped
    assert text.count("A skipped call is never counted as agreement.") == 1
    assert "does not hold)" not in text
    fold = text[text.index("every other candidate"):text.index("discounted fraction is 0")]
    assert fold.count("(") == fold.count(")"), fold


def test_the_fold_does_not_say_a_ceiling_means_the_path_cannot_be_measured(_ops, monkeypatch):
    """D2 of QA round 3. `skip_full` with `warm_n` 0 is ALSO what a light request on sparse
    traffic produces (QA's fake-clock sweep: 640 of 723 cells at pred/limit 0.3), and natal
    does yield counted samples in a 50-57 s idle-gap window, so the counters support
    'spaced far apart OR bucket-sized' and nothing stronger."""
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    for overclaim in ("cannot be measured by this instrument", "measured at all",
                      "on every call", "not under-deployed"):
        assert overclaim not in text, overclaim
    assert "spaced far enough apart that the bucket had refilled completely" in text
    assert "or the request is about the size of the whole bucket" in text


def test_the_fold_says_what_the_empty_end_clamp_is(_ops, monkeypatch):
    """D3(c). Only the ceiling clause was asserted; this is the other half of the same sentence.
    The probe really does skip a header of zero remaining (test_ratelimit_probe)."""
    text = flat(panel(page(monkeypatch, usage([urow(K120, POPULATED)]))))
    assert ("clamped (the prediction fell outside the bucket, or Groq reported zero remaining)"
            in text)


def test_a_nonzero_ceiling_count_reaches_the_page(_ops, monkeypatch):
    """D3(a). `skip_full` is the counter the operator is told to watch, and the POPULATED
    fixture has it at 0, so replacing its read with a literal 0 changed nothing anywhere."""
    seen = probe(warm_seen=40, warm_n=0, skip_full=37, skip_noanchor=3, last_limit=8000)
    (r,) = ops_data._ratelimit_rows(usage([urow(K120, seen)]), [K120])
    assert r["skips"]["full"] == 37 and r["warm_n"] == 0
    p = panel(page(monkeypatch, usage([urow(K120, seen)])))
    assert "37 bucket at ceiling" in " ".join(cells(p, "gpt-oss-120b")[1].split()), (
        cells(p, "gpt-oss-120b")[1])


def test_the_header_reported_limit_reaches_the_page(_ops, monkeypatch):
    """BUG-3. ARCHITECTURE points at this panel to settle whether the header is
    TPM ("the panel prints `last_limit`; 8,000 would say so"). It was computed
    at ops_data.py:1163 and then dropped, so the stated route to answering that
    question led to a page that never printed it."""
    p = panel(page(monkeypatch, usage([urow(K120, POPULATED)])))
    assert "header-reported limit 8,000" in p, p
