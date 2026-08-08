#!/usr/bin/env python3
r"""Verify there is exactly ONE Manglik answer, everywhere, for every chart.

WHY THIS EXISTS
---------------
"Is this chart Manglik?" is one question. This codebase shipped three
different answers to it at once, on three different surfaces, and none of
them could see the others. Issues #176, #165 and #166 are the three heads of
that one bug; this script is the thing that stops them growing back.

  * **#176 — two engines.** `chart.compute_vedic_flags()` carried its own
    inline Manglik test: TWO axes (Lagna, Moon) and NO cancellation
    catalogue. `chart.compute_manglik_details()` carried the real one: THREE
    axes (Lagna, Moon, Venus per knowledge/vedic_reference.md §1.1) plus the
    §1.3 cancellation/mitigation rules. The first fed the LLM prompt and the
    subscriber emails; the second fed `/manglik-check` and `/matching`. So a
    seeker could read "you are Manglik" in their reading and "not Manglik" on
    the check page, on the same chart, on the same day. Measured over the
    248,832-chart census below, the two disagreed on **31,104 charts —
    12.5%**. `compute_vedic_flags` now derives from `compute_manglik_details`
    and carries it whole on `VedicFlags.manglik_details`.

  * **#165 — badge versus prose.** `/matching` decided the red/green Mangal
    Dosh badge from one definition of "effectively Manglik" and wrote the
    explanatory note from another. A `mitigated` pair could therefore render
    a red "Needs review" badge sitting directly above prose reading "the
    dosha cancels through matching". One function, `matching.
    mangal_dosh_verdict()`, now returns the badge and the note together, so
    they cannot be computed apart.

  * **#166 — cancellation across a severity gap.** The classical
    mutual-Manglik cancellation (§1.3 table E rule 20) was applied whenever
    both partners were Manglik, ignoring severity entirely — so a `low`
    Manglik was told the dosha cancelled against a `high` one. It is now
    gated by `matching._severity_comparable()`: equal or adjacent grades are
    comparable, `low` versus `high` is not.

Also verified here: `cache.PROMPT_LOGIC_VERSION` is actually folded into
`cache.fingerprint_prompt()`. That fingerprint hashes the prompt TEMPLATE
FILE, so a fix that rewrites the assembled user message in Python moves
nothing — and natal entries are written with `ttl_days=None`. Without the
version token this whole bundle would have shipped and kept serving the old,
wrong readings from cache forever.

None of these is visible in a diff, and none is visible from inside any one
of the modules involved. So: one command, zero judgment, PASS/FAIL, exit 0 or
1. Deliberately shaped like `scripts/verify_panchang_angas.py` and
`scripts/verify_email_templates.py`.

  Gate 1 - one engine.  Over a synthetic census of all 248,832 charts
      (12 lagnas x 12 Mars signs x 12 Moon signs x 12 Venus signs x 12
      Jupiter signs), `compute_vedic_flags(c, WHEN).manglik` must equal
      `compute_manglik_details(c).is_manglik` on EVERY chart — zero
      disagreement, not "few". `flags.manglik_details` must be carried (not
      None) and `flags.manglik_reasons` must BE `manglik_details.axis_reasons`,
      because a second copy of the reasons is how the second engine grew last
      time. The gate also asserts observed coverage: all four
      `effective_status` values and all four `severity` values must actually
      occur in the census, otherwise the other assertions are being made over
      a domain the census never reached.

      Those checks alone are NOT sufficient, and the reason is worth stating
      plainly because it is easy to get wrong. Now that #176 is fixed,
      `compute_vedic_flags()` DELEGATES to `compute_manglik_details()` — so
      "the two engines agree" is true by construction and cannot fail while
      the delegation stands. It catches a re-introduced second engine, which
      is what #176 was, and nothing else: break the shared engine itself and
      both sides move together, still agreeing, still green. (Verified, not
      assumed — replacing the Venus-axis house set with the empty set changes
      31,104 verdicts and every agreement check above stays green.)

      So this gate carries a THIRD, INDEPENDENT derivation of the three axes,
      `_corpus_manglik()`, written here from vedic_reference.md §1.1 and
      computed from the census's raw sign INDICES — it imports nothing from
      chart.py and owes it nothing. `compute_manglik_details()` must match it
      on is_manglik, the qualifying house set, the axis count, the
      Venus-axis-only flag and the severity grade. Same reason
      `verify_panchang_angas.py` Gate 2 re-derives the karana rule instead of
      importing it: if these two are ever "shared" to remove the duplication,
      this gate stops testing anything at all.

      That covers §1.1, the AXES. The §1.3 CANCELLATION CATALOGUE gets no
      independent derivation — it is fifteen rules from four classical texts,
      and re-typing them here would be a transcription rather than a check. It
      is pinned by FINGERPRINT instead: exact-equality assertions on the
      `effective_status` and `severity` distributions over the fixed census, on
      the number of charts each `ManglikRule.slug` fires on, and on each slug's
      cancels/mitigates tag. Before those existed, corrupting a RULE was
      completely silent — flipping one `effect` from "cancels" to "mitigates",
      or deleting the combustion branch, left every other assertion in this
      file green, because the only catalogue assertion was that the four
      statuses were non-zero and they stayed non-zero. The per-slug halves are
      the sharp ones: they name the rule instead of only reporting that the
      distribution moved, and the fire counts alone catch a predicate change
      that happens not to move any status. The totals are asserted first and
      separately, so a change to the census size reports as itself rather than
      as four unrelated-looking histogram failures. A deliberate rule change is
      EXPECTED to move these numbers; see the constants block for what to do
      then, and for how to regenerate them.

  Gate 2 - exactly one assertion in the prompt.  `MANGLIK_ASSERTION_PREFIX`
      (imported, never re-typed) may appear exactly ONCE in the assembled
      message. `format_flags_for_prompt()` emits it; `format_manglik_for_prompt()`
      must supply evidence and phrasing guidance only. Checked on all 248,832
      charts, then again on a deterministic 500-chart subsample assembled
      through the REAL assemblers — the whole message the model actually
      receives, with real life chapters, a real dasha state, real transits and
      a real Panchang, not a hand-rolled approximation of it.

      ALL FOUR assemblers, not one. The flags block reaches a seeker through
      four different user messages, each built by its own function in its own
      block order: `llm._format_seeker_message()` (/kundli),
      `_format_outlook_message()` (/monthly, /yearly), `_format_daily_message()`
      (/today), and the block assembled inside `generate_ask_answer()` (/ask).
      This gate used to assemble only the first, which says nothing whatsoever
      about the other three — any of them can grow a second verdict on its own.
      The /ask message is not returned by any function, so the gate calls the
      REAL `generate_ask_answer()` and intercepts `providers.chat`, the network
      hop and only the network hop, to read the message the real code built;
      nothing about the assembly is stubbed. Every path is asserted on all four
      `effective_status` values (16 cells), and each path's line reports whether
      it carries the `format_manglik_for_prompt()` evidence block — only the
      natal path does, so only the natal path can double-assert by adding one
      evidence line, and the other three can only do it by emitting the flags
      block twice.

      Four arbitrations live in this gate, because the naive form of each
      check fails on CORRECT code, and a gate that fails on correct code is a
      gate someone disables:

        - The `cancelled` and `mitigated` wordings deliberately contain the
          word "Angshik", inside prohibitions aimed at the model (`Do not use
          the term "Angshik Manglik"`), because §1.2 / §1.3 F ban it as a
          colloquialism. So this does NOT assert "Angshik never appears" — it
          strips the two known prohibition sentences and asserts "Angshik" is
          absent from everything that remains. Both prohibition sentences must
          themselves be observed at least once, so a reworded prohibition
          cannot silently turn the exemption into a blanket hole.
        - The `mitigated` wording contains `Do NOT say it is cancelled or
          absent.` So this does NOT assert "the word cancelled appears iff the
          status is cancelled" — it asserts on the STATUS TOKEN: the literal
          `PRESENT BUT CANCELLED` appears iff `effective_status == "cancelled"`.
        - `Kuja-Shukra` is Mars and Venus under their Sanskrit names, and
          prompts/natal.txt forbids the reading from naming planets. But
          `format_flags_for_prompt()` legitimately uses it once, to explain why
          a Venus-axis-only chart was reduced with no classical rule behind it.
          Same shape as the "Angshik" exemption — strip the known explanatory
          sentence, assert the term is absent from the rest, and assert the
          sentence is OBSERVED — plus a placement check that owes the prose
          nothing: `_kuja_shukra_expected()` reads the CHART (mitigated +
          venus_axis_only + no §1.3 mitigation rule) and allows the term on
          exactly those charts, so copying it into another status's wording
          fails even with the original sentence untouched.
        - `Mathematical:` and `Effective status:` were the removed
          double-assertion lines; they must never come back. And no clause may
          dangle — no `Softened by: .`, no `Cancelled by: .`, and no `:\s*\.`
          anywhere. That last pattern caught a real defect on 51 charts during
          development (a Venus-axis-only chart reaching "mitigated" with no
          rule behind it, emitting "Softened by: .").

  Gate 3 - the badge and the note can never contradict.  Builds
      `ManglikDetails` DIRECTLY over the full cross-product of 4
      `effective_status` values x 3 `severity` values for both partners = 144
      combinations, deliberately including physically-impossible pairs like
      ("none", "high"). `mangal_dosh_verdict()` is a total function over its
      declared domain, not merely over the states the engine happens to
      produce today, and #165 was exactly a state nobody thought reachable.
      For each: `compatible` must equal `_BRANCH_COMPATIBLE[branch]`; `branch`
      must be re-derivable from `is_effectively_manglik()` plus
      `_severity_comparable()`; and the note is checked LEXICALLY — an
      incompatible verdict may not say "the dosha cancels" or "No Mangal Dosh
      concerns", and a compatible one may not say "careful evaluation",
      "extra remediation" or "not comparable". The lexical half is what
      catches a future prose edit that a structural check sails straight past.
      Branch tallies are asserted exactly: neither 36, one_sided 72,
      both_comparable 28, both_incomparable 8.

  Gate 4 - no cancellation across a low/high gap.  Over the same 144: when
      the two severities are {low, high} and both partners are effectively
      Manglik, the verdict must be incompatible, must take the
      `both_incomparable` branch, and must not claim the dosha cancels. It
      must ALSO disclose the convention — the note has to contain the word
      "comparable" — so CLAUDE.md's "state which convention a page uses"
      requirement cannot be dropped in a prose cleanup. The band is a Bhagya
      construct on a Bhagya severity ladder; §1.3 rule 20 says "comparable
      severity" and defines nothing, so the user has to be told where we drew
      the line.

  Gate 5 - the cache key actually moved.  `cache.fingerprint_prompt(p)` must
      NOT equal the bare `sha256(p.read_bytes()).hexdigest()[:8]`, and must
      start with `cache.PROMPT_LOGIC_VERSION`. This is the gate that bites
      when someone later "cleans up" the version token as redundant, which
      would silently re-pin every natal reading to its pre-fix text.

WHAT THIS DOES NOT DO
---------------------
It does not import `astro_ai.main`. That module builds the FastAPI app, reads
environment variables and touches GCS at import time, and it is edited
constantly — a gate that fails because an unrelated route was mid-edit is a
gate people learn to ignore.

The census charts are SYNTHETIC: `_chart()` builds `Chart` / `PlanetPosition`
objects directly, so there is no geocoding, no network and no ephemeris
lookup for the natal positions. That is what makes an exhaustive 248,832-chart
sweep possible at all. Every planet sits at 15.0 degrees of its sign, so
combustion is a clean same-sign toggle rather than a fuzzy one, and houses are
Whole Sign: ((sign_idx - lagna_idx) % 12) + 1.

`WHEN` is FIXED. `compute_vedic_flags()` reads a live Saturn transit for Sade
Sati, and a census anchored on "today" is a gate that changes its own inputs
every morning — i.e. a time bomb. Nothing about Manglik depends on the date;
pinning it costs nothing and removes the flake.

Usage:  uv run python scripts/verify_manglik_coherence.py
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import itertools
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import cache, llm  # noqa: E402
from astro_ai.chart import (  # noqa: E402
    MANGLIK_ASSERTION_PREFIX,
    RASHIS,
    Chart,
    ManglikDetails,
    PlanetPosition,
    compute_dasha_state,
    compute_gochar_impacts,
    compute_life_chapters,
    compute_manglik_details,
    compute_panchang,
    compute_transit_events,
    compute_transit_snapshot,
    compute_vedic_flags,
    format_flags_for_prompt,
    format_manglik_for_prompt,
    is_effectively_manglik,
)
from astro_ai.matching import (  # noqa: E402
    _BRANCH_COMPATIBLE,
    _COMPARABILITY_BAND_SENTENCE,
    _severity_comparable,
    mangal_dosh_verdict,
)

# ---------------------------------------------------------------------------
# Census harness — synthetic charts, no geocoding, no network
# ---------------------------------------------------------------------------

# Fixed transit moment. compute_vedic_flags() computes Sade Sati from the
# Saturn transit at `when`, so leaving this as "now" would make the census
# depend on today's sky. Manglik does not, but the gate would still start
# failing or passing for reasons nobody changed.
WHEN = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

# Birth moment for the synthetic charts. Only reached by the Vimshottari dasha
# code on the Gate 2 subsample (life chapters + dasha state are computed from
# birth_utc and the Moon), never by anything Manglik.
BIRTH_UTC = datetime(1990, 6, 15, 6, 30, tzinfo=timezone.utc)

# New Delhi. Never used for a computation here — `Chart` requires the fields
# and `format_for_prompt()` prints them.
BIRTH_LAT, BIRTH_LON, BIRTH_TZ = 28.6139, 77.2090, "Asia/Kolkata"

# Every planet at the midpoint of its sign. Deliberate: the combustion rule in
# _manglik_cancellations() measures Mars-Sun separation on ABSOLUTE sidereal
# longitude, so at a uniform 15.0 the separation is 0 when Sun and Mars share a
# sign and >= 30 otherwise. Combustion becomes a clean same-sign switch this
# gate can steer, instead of a threshold it has to sneak up on.
DEGREE_IN_SIGN = 15.0

CENSUS_AXES = ("lagna", "Mars", "Moon", "Venus", "Jupiter")
CENSUS_SIZE = 12 ** len(CENSUS_AXES)   # 248,832

STATUSES: tuple[str, ...] = ("none", "cancelled", "mitigated", "present")
SEVERITIES: tuple[str, ...] = ("low", "moderate", "high")
# severity carries a fourth value, "none", but only on non-Manglik charts —
# it is never paired with a status in Gate 3's cross-product, and it IS
# asserted as observed in Gate 1's coverage check.
CENSUS_SEVERITIES: tuple[str, ...] = SEVERITIES + ("none",)

# ---------------------------------------------------------------------------
# The §1.3 catalogue fingerprint
#
# WHY THESE NUMBERS EXIST. Everything else in Gate 1 re-derives §1.1 — the
# three AXES — from raw sign indices, so an axis bug bites. The §1.3
# CANCELLATION CATALOGUE has no independent derivation and cannot cheaply get
# one: it is fifteen classical rules from four different texts, and a second
# hand-written copy of them here would be a transcription, not a check. So it
# is pinned by FINGERPRINT instead. The census and WHEN are both fixed and
# fully deterministic, so the distributions below are constants; any change to
# a rule's predicate, its `effect`, or the set of rules moves at least one of
# them.
#
# Without these, corrupting a RULE was silent. Flipping one `effect` from
# "cancels" to "mitigates", or deleting the combustion branch, left every other
# assertion in this file green — the coverage checks below only asserted the
# four statuses were non-zero, and they stayed non-zero. That matters because
# `effective_status` is what every consumer keys off: the /matching badge, the
# explanatory note, the four prompt wordings in §1.4, and the mutual-
# cancellation branch. A silent catalogue change re-answers the question on all
# of them at once.
#
# A DELIBERATE RULE CHANGE IS EXPECTED TO MOVE THESE. That is the point — it
# makes the blast radius visible in the diff. Source the change against
# knowledge/vedic_reference.md §1.3, then regenerate and update the constants
# IN THE SAME COMMIT, from the repo root:
#
#   uv run python - <<'EOF'
#   import sys
#   from collections import Counter
#   sys.path[:0] = ["scripts", "src"]
#   import verify_manglik_coherence as v
#   from astro_ai.chart import compute_manglik_details
#   st, sv, fires, effects = Counter(), Counter(), Counter(), {}
#   for _params, chart in v.census():
#       d = compute_manglik_details(chart)
#       st[d.effective_status] += 1
#       sv[d.severity] += 1
#       for r in d.cancellations:
#           fires[r.slug] += 1
#           effects.setdefault(r.slug, set()).add(r.effect)
#   print(dict(st)); print(dict(sv))
#   print(dict(sorted(fires.items())))
#   print({k: sorted(v_) for k, v_ in sorted(effects.items())})
#   EOF
# ---------------------------------------------------------------------------

# Distribution of `effective_status` over the census. Sums to CENSUS_SIZE.
EXPECTED_STATUS_COUNTS: dict[str, int] = {
    "none": 31_104,
    "cancelled": 193_005,
    "mitigated": 13_983,
    "present": 10_740,
}

# Distribution of `severity` over the census. Sums to CENSUS_SIZE. "none" here
# is exactly the non-Manglik charts, so it necessarily equals the "none" status
# count above; the other three move with the Venus-axis-only downgrade.
EXPECTED_SEVERITY_COUNTS: dict[str, int] = {
    "low": 33_840,
    "moderate": 89_424,
    "high": 94_464,
    "none": 31_104,
}

# Charts on which each individual rule fires, by `ManglikRule.slug`. This is
# the sharp version of the two histograms above: it localises a broken rule to
# its NAME instead of only reporting that the distribution moved, and it is the
# only assertion here that catches a rule whose predicate changed WITHOUT
# changing any status (e.g. one more sign added to a `cancels` rule on charts
# some other `cancels` rule already covered). Counted over the 217,728
# Manglik-qualifying charts only — compute_manglik_details() returns early with
# cancellations=() for the other 31,104, so the catalogue never runs on them.
# A rule deleted, renamed or newly added shows up here as a missing or
# unexpected KEY, which is a clearer failure than a shifted number.
EXPECTED_RULE_FIRE_COUNTS: dict[str, int] = {
    "cancer_lagna_yogakaraka": 18_144,
    "jupiter_aspects_7h": 37_152,
    "jupiter_aspects_7l": 20_916,
    "jupiter_aspects_mars": 54_432,
    "leo_lagna_yogakaraka": 18_144,
    "mars_combust": 72_576,
    "mars_debilitated": 18_144,
    "mars_exalted": 18_144,
    "mars_in_jupiters_sign": 36_288,
    "mars_in_venus_sign": 18_144,
    "mars_jupiter_conjunct": 18_144,
    "mars_libra_movable": 18_144,
    "mars_own_sign": 36_288,
    "venus_aspects_mars": 20_736,
    "venus_with_mars": 20_736,
}

# Each slug's `effect`, which §1.3 requires to be a property of the RULE and
# not of the chart — so exactly one value per slug, everywhere in the census.
# This is what names the rule when someone flips a "cancels" to a "mitigates":
# the fire counts above do not move at all under that edit (the rule still
# fires on the same charts), only the status histogram and this map do.
EXPECTED_RULE_EFFECTS: dict[str, str] = {
    "cancer_lagna_yogakaraka": "cancels",
    "jupiter_aspects_7h": "cancels",
    "jupiter_aspects_7l": "cancels",
    "jupiter_aspects_mars": "cancels",
    "leo_lagna_yogakaraka": "cancels",
    "mars_combust": "cancels",
    "mars_debilitated": "cancels",
    "mars_exalted": "cancels",
    "mars_in_jupiters_sign": "mitigates",
    "mars_in_venus_sign": "mitigates",
    "mars_jupiter_conjunct": "cancels",
    "mars_libra_movable": "cancels",
    "mars_own_sign": "cancels",
    "venus_aspects_mars": "cancels",
    "venus_with_mars": "mitigates",
}

# Prepended to every fingerprint failure. The two cases a reader faces look
# identical in the output — a moved number — and only they know which one they
# are in, so the message must not read as "just update the constant".
FINGERPRINT_VERDICT = (
    "This is a change to the §1.3 cancellation catalogue in "
    "chart._manglik_cancellations(). There are exactly two possibilities and "
    "they are NOT interchangeable. (a) You changed a cancellation rule "
    "DELIBERATELY: source it against knowledge/vedic_reference.md §1.3, then "
    "update the constant in THIS file in the SAME commit, so the diff shows "
    "how many seekers the change re-answers. (b) You did not: this is a "
    "regression, and every consumer of effective_status just moved with it — "
    "the /matching badge, the explanatory note, the four §1.4 prompt wordings "
    "and the mutual-cancellation branch. Do not adjust the computation to "
    "silence a gate, and do not update the constant to make a red gate green."
)

EXPECTED_BRANCH_TALLY: dict[str, int] = {
    # Verified independently by two engineers before this file existed, and
    # re-derivable: 2 of the 4 statuses are effectively Manglik, so each
    # partner is "present" in 2*3 = 6 of their 12 (status, severity) states
    # and "clear" in the other 6.  neither = 6*6.  one_sided = 2*6*6.
    # both = 6*6 = 36, of which the incomparable ones are the 2 severity pairs
    # {low,high}/{high,low} across 2*2 status choices = 8; 36 - 8 = 28.
    "neither": 36,
    "one_sided": 72,
    "both_comparable": 28,
    "both_incomparable": 8,
}
COMBO_COUNT = len(STATUSES) * len(SEVERITIES) * len(STATUSES) * len(SEVERITIES)  # 144


def _chart(lagna_idx: int, positions: dict[str, int]) -> Chart:
    """A synthetic Chart with the given lagna and sign index per planet.

    Whole Sign houses throughout: house = ((sign_idx - lagna_idx) % 12) + 1,
    which is exactly what compute_chart() does for a real chart.
    """
    return Chart(
        lagna_rashi=RASHIS[lagna_idx],
        lagna_longitude=DEGREE_IN_SIGN,
        planets=[
            PlanetPosition(
                name=name,
                rashi=RASHIS[sign_idx],
                house=((sign_idx - lagna_idx) % 12) + 1,
                longitude=DEGREE_IN_SIGN,
                nakshatra="Ashwini",
                retrograde=False,
            )
            for name, sign_idx in positions.items()
        ],
        birth_lat=BIRTH_LAT,
        birth_lon=BIRTH_LON,
        birth_tz=BIRTH_TZ,
        birth_utc=BIRTH_UTC,
    )


def _build(lagna: int, mars: int, moon: int, venus: int, jupiter: int) -> Chart:
    """One census chart from the five free axes.

    Sun, Mercury and Saturn are placed DETERMINISTICALLY from the free axes so
    that every branch of `_manglik_cancellations()` is exercised somewhere in
    the census rather than sitting as dead code the gate never reaches:

      * Sun — the combustion branch. Sun shares Mars's sign (separation 0, so
        combust) on one Jupiter position in three, and sits 4 signs away
        (separation 120 degrees, never combust) otherwise. A fixed offset
        would have pinned combustion permanently on or permanently off.
      * Mercury — one sign ahead of the Sun, which is both astronomically
        honest (Mercury never strays far from the Sun) and enough to make the
        "Jupiter aspects the 7th lord" branch live for the four lagnas whose
        7th lord is Mercury.
      * Saturn — 7 signs from Mars, so the same 7th-lord branch is live for
        the two lagnas ruled by Saturn.

    Jupiter's own aspect branches (conjunct Mars / aspects Mars / aspects the
    7th house) and the Venus branches (conjunct Mars / opposite Mars) need no
    help: Jupiter and Venus are free axes and sweep all 12 signs.
    """
    sun = mars if jupiter % 3 == 0 else (mars + 4) % 12
    return _chart(lagna, {
        "Sun": sun,
        "Moon": moon,
        "Mars": mars,
        "Mercury": (sun + 1) % 12,
        "Jupiter": jupiter,
        "Venus": venus,
        "Saturn": (mars + 7) % 12,
        "Rahu": (moon + 3) % 12,
        "Ketu": (moon + 9) % 12,
    })


def census() -> Iterator[tuple[tuple[int, int, int, int, int], Chart]]:
    """All 248,832 charts, as (params, chart). A generator, not a list.

    Materialising a quarter of a million Chart objects (nine PlanetPosition
    each) costs hundreds of MB for no benefit — each gate walks this fresh.
    """
    for lagna in range(12):
        for mars in range(12):
            for moon in range(12):
                for venus in range(12):
                    for jupiter in range(12):
                        yield (
                            (lagna, mars, moon, venus, jupiter),
                            _build(lagna, mars, moon, venus, jupiter),
                        )


def _describe(params: tuple[int, int, int, int, int]) -> str:
    """A census chart's parameters, in words, for a failure message."""
    return ", ".join(
        f"{axis}={RASHIS[idx]}" for axis, idx in zip(CENSUS_AXES, params)
    )


# ---------------------------------------------------------------------------
# The classical rule, re-derived here so Gate 1 is a THIRD derivation
# ---------------------------------------------------------------------------

# knowledge/vedic_reference.md §1.1: Mars in the 1st, 2nd, 4th, 7th, 8th or
# 12th house makes the chart Manglik. Deliberately NOT imported from chart.py —
# a gate whose expected values come from the implementation it is testing
# proves only that the implementation is self-consistent, and #176 was a
# self-consistent implementation that happened to be a second one.
CORPUS_MANGLIK_HOUSES = frozenset({1, 2, 4, 7, 8, 12})

# §1.1 counts the dosha from three reference points, in this order.
CORPUS_AXES: tuple[str, ...] = ("Lagna", "Moon", "Venus")


def _corpus_manglik(
    params: tuple[int, int, int, int, int]
) -> tuple[bool, tuple[int, ...], int, bool, str]:
    """The §1.1 three-axis Manglik test, re-derived from raw sign indices.

    Takes the census parameters — plain integers 0..11 — and uses nothing from
    astro_ai at all. Whole Sign houses, so "Mars's house counted from X" is
    just ((mars - x) % 12) + 1 for each of the Lagna, the Moon and Venus.

    Returns (is_manglik, qualifying houses, number of axes that fired,
    venus_axis_only, severity).

    The severity ladder and the Venus-axis-only downgrade are NOT corpus —
    they are Bhagya conventions (the same ones matching.py discloses to the
    user in _SEVERITY_GRADING_SENTENCE): 7th or 8th high, 1st/4th/12th
    moderate, 2nd alone low, then one grade lower, never below low, when only
    the Venus axis qualified. They are re-derived here anyway because #166
    lived entirely in the severity grade, so a silent regrade has to be a
    failure and not a shrug.
    """
    lagna, mars, moon, venus, _jupiter = params
    per_axis = {
        "Lagna": ((mars - lagna) % 12) + 1,
        "Moon":  ((mars - moon) % 12) + 1,
        "Venus": ((mars - venus) % 12) + 1,
    }
    fired = {axis: house for axis, house in per_axis.items()
             if house in CORPUS_MANGLIK_HOUSES}
    qualifying = frozenset(fired.values())
    if not qualifying:
        return False, (), 0, False, "none"

    venus_only = set(fired) == {"Venus"}
    if {7, 8} & qualifying:
        severity = "high"
    elif {1, 4, 12} & qualifying:
        severity = "moderate"
    else:
        severity = "low"
    if venus_only:
        severity = {"high": "moderate", "moderate": "low"}.get(severity, severity)
    return True, tuple(sorted(qualifying)), len(fired), venus_only, severity


# ---------------------------------------------------------------------------
# Gate 1 - one engine
# ---------------------------------------------------------------------------

def _fingerprint_deltas(
    got: dict[str, int], want: dict[str, int]
) -> list[str]:
    """Every key where two count maps differ, as readable one-liners.

    Reports missing and unexpected keys separately from moved counts, because
    those mean different things: a missing key is a rule that was deleted or
    renamed, an unexpected key is a rule that was added, and a moved count is a
    rule whose predicate changed.
    """
    deltas: list[str] = []
    for key in sorted(set(want) - set(got)):
        deltas.append(f"{key}: MISSING (expected {want[key]:,}) — rule deleted, "
                      "renamed, or its predicate now never fires")
    for key in sorted(set(got) - set(want)):
        deltas.append(f"{key}: UNEXPECTED, fired on {got[key]:,} chart(s) — a rule "
                      "this gate has never seen")
    for key in sorted(set(got) & set(want)):
        if got[key] != want[key]:
            deltas.append(f"{key}: {got[key]:,}, expected {want[key]:,} "
                          f"({got[key] - want[key]:+,})")
    return deltas


def gate_1_one_engine() -> list[str]:
    failures: list[str] = []
    n = 0
    disagreements = 0
    missing_details = 0
    reason_mismatch = 0
    corpus_mismatch: Counter[str] = Counter()
    corpus_samples: list[str] = []
    samples: list[str] = []
    status_seen: Counter[str] = Counter()
    severity_seen: Counter[str] = Counter()
    rule_fires: Counter[str] = Counter()
    rule_effects: dict[str, set[str]] = {}

    for params, chart in census():
        n += 1
        flags = compute_vedic_flags(chart, WHEN)
        details = compute_manglik_details(chart)
        status_seen[details.effective_status] += 1
        severity_seen[details.severity] += 1
        for rule in details.cancellations:
            rule_fires[rule.slug] += 1
            rule_effects.setdefault(rule.slug, set()).add(rule.effect)

        # The third derivation — §1.1 re-computed from raw sign indices.
        want_manglik, want_houses, want_axes, want_venus_only, want_severity = (
            _corpus_manglik(params)
        )
        deltas: list[str] = []
        if details.is_manglik != want_manglik:
            corpus_mismatch["is_manglik"] += 1
            deltas.append(f"is_manglik {details.is_manglik} != §1.1 {want_manglik}")
        if details.houses != want_houses:
            corpus_mismatch["houses"] += 1
            deltas.append(f"houses {details.houses} != §1.1 {want_houses}")
        if len(details.axis_reasons) != want_axes:
            corpus_mismatch["axis_reasons"] += 1
            deltas.append(
                f"{len(details.axis_reasons)} axis reason(s) "
                f"{details.axis_reasons} != §1.1 {want_axes} axis/axes firing"
            )
        if details.venus_axis_only != want_venus_only:
            corpus_mismatch["venus_axis_only"] += 1
            deltas.append(
                f"venus_axis_only {details.venus_axis_only} != {want_venus_only}"
            )
        if details.severity != want_severity:
            corpus_mismatch["severity"] += 1
            deltas.append(f"severity {details.severity!r} != {want_severity!r}")
        if deltas and len(corpus_samples) < 3:
            corpus_samples.append(f"{_describe(params)} -> " + "; ".join(deltas))

        if flags.manglik != details.is_manglik:
            disagreements += 1
            if len(samples) < 3:
                samples.append(
                    f"{_describe(params)} -> compute_vedic_flags says "
                    f"manglik={flags.manglik}, compute_manglik_details says "
                    f"is_manglik={details.is_manglik} "
                    f"(status={details.effective_status}, axes={details.axis_reasons})"
                )
        if flags.manglik_details is None:
            missing_details += 1
            if len(samples) < 6:
                samples.append(
                    f"{_describe(params)} -> flags.manglik_details is None"
                )
        elif flags.manglik_reasons != flags.manglik_details.axis_reasons:
            reason_mismatch += 1
            if len(samples) < 6:
                samples.append(
                    f"{_describe(params)} -> flags.manglik_reasons="
                    f"{flags.manglik_reasons} but manglik_details.axis_reasons="
                    f"{flags.manglik_details.axis_reasons}"
                )

    print(f"  {'ok  ' if n == CENSUS_SIZE else 'FAIL'} census size {n:,} "
          f"(expected {CENSUS_SIZE:,} = 12^{len(CENSUS_AXES)}: "
          f"{' x '.join(CENSUS_AXES)})")
    print(f"  {'ok  ' if not disagreements else 'FAIL'} engine agreement "
          f"{n - disagreements:,}/{n:,} charts")
    print(f"  {'ok  ' if not missing_details else 'FAIL'} "
          f"flags.manglik_details carried on {n - missing_details:,}/{n:,} charts")
    print(f"  {'ok  ' if not reason_mismatch else 'FAIL'} "
          f"flags.manglik_reasons == manglik_details.axis_reasons on "
          f"{n - reason_mismatch:,}/{n:,} charts")
    for field in ("is_manglik", "houses", "axis_reasons", "venus_axis_only",
                  "severity"):
        bad = corpus_mismatch[field]
        print(f"  {'ok  ' if not bad else 'FAIL'} vs independent §1.1 derivation: "
              f"{field:<15} matches on {n - bad:,}/{n:,} charts")

    if n != CENSUS_SIZE:
        failures.append(
            f"census produced {n} charts, expected {CENSUS_SIZE}. The gate's domain "
            "is not what its docstring claims, so every count below is unreadable."
        )
    if n == 0:
        failures.append(
            "the census is EMPTY — this gate proved nothing rather than passing. "
            "An exhaustive sweep that sweeps nothing is the most dangerous shape a "
            "gate can take."
        )
    if disagreements:
        failures.append(
            f"{disagreements:,} of {n:,} charts ({disagreements / max(n, 1):.1%}) get a "
            "DIFFERENT Manglik answer from compute_vedic_flags() than from "
            "compute_manglik_details(). That is issue #176 back: the flags path feeds "
            "the LLM reading and the subscriber emails, the details path feeds "
            "/manglik-check and /matching, so the same seeker is told both things. "
            "compute_vedic_flags() must delegate to compute_manglik_details(), not "
            "re-derive."
        )
    if missing_details:
        failures.append(
            f"{missing_details:,} chart(s) produced VedicFlags with manglik_details=None. "
            "Every computed chart must carry the details object — it is the single "
            "carrier of status, severity and the cancellation rules, and "
            "format_flags_for_prompt() silently degrades to asserting \"NO\" without it."
        )
    if reason_mismatch:
        failures.append(
            f"{reason_mismatch:,} chart(s) have manglik_reasons that are not "
            "manglik_details.axis_reasons. A second, independently-built copy of the "
            "axis reasons is precisely how the second engine grew the first time."
        )
    if corpus_mismatch:
        failures.append(
            "compute_manglik_details() disagrees with the independent §1.1 derivation "
            f"in this file on: {dict(sorted(corpus_mismatch.items()))} (out of {n:,} "
            "charts). This is the assertion that actually bites — the two-engine check "
            "above cannot fail while compute_vedic_flags() delegates, so a bug INSIDE "
            "the shared engine only shows up here. Manglik is counted from all THREE "
            "reference points (Lagna, Moon, Venus) in houses "
            f"{sorted(CORPUS_MANGLIK_HOUSES)}; dropping or widening an axis silently "
            "re-answers the question for every seeker. Fix chart.py — do not edit "
            "_corpus_manglik() to agree with it."
        )
    for line in corpus_samples:
        failures.append(f"sample: {line}")
    for line in samples:
        failures.append(f"sample: {line}")

    missing_status = [s for s in STATUSES if not status_seen[s]]
    missing_severity = [s for s in CENSUS_SEVERITIES if not severity_seen[s]]
    print(f"  {'ok  ' if not missing_status else 'FAIL'} effective_status coverage  "
          + "  ".join(f"{s}={status_seen[s]:,}" for s in STATUSES))
    print(f"  {'ok  ' if not missing_severity else 'FAIL'} severity coverage         "
          + "  ".join(f"{s}={severity_seen[s]:,}" for s in CENSUS_SEVERITIES))
    if missing_status:
        failures.append(
            f"effective_status value(s) never produced by the census: {missing_status}. "
            "The assertions above are then being made over a domain the census never "
            "reached — widen the census (or the Sun/Mercury/Saturn placement in "
            "_build) rather than trusting a green result."
        )
    if missing_severity:
        failures.append(
            f"severity value(s) never produced by the census: {missing_severity}. Same "
            "problem: a severity nothing reaches is a severity nothing is testing, and "
            "issue #166 lived entirely in the severity comparison."
        )

    # --- the §1.3 catalogue fingerprint -----------------------------------
    # The coverage checks above only assert "non-zero", which a rule edit sails
    # straight past: flip one `effect` or delete one branch and all four values
    # stay non-zero while every seeker's verdict moves. These four assertions
    # are the ones that bite. See FINGERPRINT_VERDICT and the constants block.

    # Totals FIRST and separately, so a census-size change is reported as its
    # own failure instead of surfacing as four confusing histogram mismatches.
    status_total, severity_total = sum(status_seen.values()), sum(severity_seen.values())
    totals_ok = status_total == severity_total == CENSUS_SIZE
    print(f"  {'ok  ' if totals_ok else 'FAIL'} fingerprint totals            "
          f"status={status_total:,}  severity={severity_total:,}  "
          f"(both expected {CENSUS_SIZE:,})")
    if not totals_ok:
        failures.append(
            f"the fingerprint histograms total status={status_total:,} / "
            f"severity={severity_total:,}, expected {CENSUS_SIZE:,} each. Every chart "
            "must be counted exactly once in each. This is a CENSUS problem, not a "
            "catalogue problem — read it before the per-value mismatches below, which "
            "are all downstream of it and will look like four unrelated regressions."
        )

    status_deltas = _fingerprint_deltas(dict(status_seen), EXPECTED_STATUS_COUNTS)
    severity_deltas = _fingerprint_deltas(dict(severity_seen), EXPECTED_SEVERITY_COUNTS)
    fire_deltas = _fingerprint_deltas(dict(rule_fires), EXPECTED_RULE_FIRE_COUNTS)
    effect_deltas: list[str] = []
    for slug in sorted(set(rule_effects) | set(EXPECTED_RULE_EFFECTS)):
        got_effects = sorted(rule_effects.get(slug, set()))
        want_effect = EXPECTED_RULE_EFFECTS.get(slug)
        if len(got_effects) > 1:
            effect_deltas.append(
                f"{slug}: fires with effect {got_effects} — §1.3 tags each RULE "
                "cancels or mitigates; an effect that varies by chart means the "
                "catalogue is deciding the verdict twice"
            )
        elif got_effects and want_effect is None:
            effect_deltas.append(f"{slug}: new rule, effect {got_effects[0]!r}")
        elif got_effects and got_effects[0] != want_effect:
            effect_deltas.append(
                f"{slug}: effect {got_effects[0]!r}, expected {want_effect!r}"
            )
        elif not got_effects:
            effect_deltas.append(
                f"{slug}: never fired, expected effect {want_effect!r}"
            )

    print(f"  {'ok  ' if not status_deltas else 'FAIL'} §1.3 fingerprint: "
          "effective_status  "
          + "  ".join(f"{s}={status_seen[s]:,}" for s in STATUSES))
    print(f"  {'ok  ' if not severity_deltas else 'FAIL'} §1.3 fingerprint: "
          "severity          "
          + "  ".join(f"{s}={severity_seen[s]:,}" for s in CENSUS_SEVERITIES))
    print(f"  {'ok  ' if not fire_deltas else 'FAIL'} §1.3 fingerprint: per-rule "
          f"fire counts    {len(rule_fires)} slug(s), "
          f"expected {len(EXPECTED_RULE_FIRE_COUNTS)}")
    print(f"  {'ok  ' if not effect_deltas else 'FAIL'} §1.3 fingerprint: per-rule "
          "cancels/mitigates  "
          f"{len(rule_effects)} slug(s) each with one effect")

    if status_deltas:
        failures.append(
            "the effective_status distribution over the census has MOVED: "
            + "; ".join(status_deltas)
            + ". " + FINGERPRINT_VERDICT
        )
    if severity_deltas:
        failures.append(
            "the severity distribution over the census has MOVED: "
            + "; ".join(severity_deltas)
            + ". Severity is set by §1.1 house grading and the Venus-axis-only "
            "downgrade, not by the catalogue, so check the axis assertions above "
            "first — if they are green, this is a regrade, and issue #166 lived "
            "entirely in the severity grade. " + FINGERPRINT_VERDICT
        )
    if fire_deltas:
        failures.append(
            "the per-rule fire counts have MOVED, which names the rule(s) involved: "
            + "; ".join(fire_deltas)
            + ". " + FINGERPRINT_VERDICT
        )
    if effect_deltas:
        failures.append(
            "a rule's cancels/mitigates tag has CHANGED: " + "; ".join(effect_deltas)
            + ". Per vedic_reference.md §1.3, cancels means the dosha is fully "
            "nullified and mitigates means it is softened but still present — and "
            "is_effectively_manglik() counts mitigated as Manglik. So this single "
            "character flips whole populations of seekers between "
            "\"the dosha cancels\" and \"the dosha is present and reduced\". "
            + FINGERPRINT_VERDICT
        )
    return failures


# ---------------------------------------------------------------------------
# Gate 2 - exactly one Manglik assertion in the assembled prompt
# ---------------------------------------------------------------------------

# The two sentences in format_flags_for_prompt() that legitimately contain the
# banned word "Angshik", because they are PROHIBITIONS aimed at the model:
# knowledge/vedic_reference.md §1.2 and §1.3 F ban "Angshik Manglik" as a
# colloquialism, so the prompt has to name it in order to forbid it. Stripped
# before the "Angshik" scan below — and each one must be OBSERVED in the census,
# so that rewording a prohibition cannot quietly widen the exemption into a hole.
ANGSHIK_PROHIBITIONS: tuple[str, ...] = (
    'Do not say it is uncancelled, partial, or "Angshik".',
    'Do not use the term "Angshik Manglik".',
)

# The status token, not the English word. "cancelled" appears in the MITIGATED
# wording too ("Do NOT say it is cancelled or absent"), which is correct
# instruction and would break a naive word test.
CANCELLED_TOKEN = "PRESENT BUT CANCELLED"

# The two double-assertion lines removed by #176. format_manglik_for_prompt()
# used to restate the verdict alongside format_flags_for_prompt()'s assertion,
# which is how the prompt ended up carrying two of them.
REMOVED_ASSERTION_LINES: tuple[str, ...] = ("Mathematical:", "Effective status:")

# A label followed by nothing. "Softened by: ." shipped on 51 census charts —
# a Venus-axis-only chart capped down to "mitigated" with no classical rule
# behind it, so the rules list was empty and the clause dangled.
DANGLING_CLAUSE = re.compile(r":\s*\.")
DANGLING_LITERALS: tuple[str, ...] = ("Softened by: .", "Cancelled by: .")

# "Kuja-Shukra" is Mars and Venus under their Sanskrit names, and
# prompts/natal.txt's STRICT OUTPUT RULES say "DO NOT name specific planets
# (Jupiter, Saturn, Rahu, Ketu, Mars, Mercury, Venus, Sun, Moon)". So the term
# is a planet name the model is being handed, and if it echoes it the reading
# breaks the rule in a way no other check here would see.
#
# It is not banned outright, and must not be: format_flags_for_prompt() uses it
# in ONE place for a real reason — a Venus-axis-only chart is capped to
# "mitigated" by no classical rule at all, so the prompt has to explain WHERE
# the reduction came from, and the classical name for that pattern is
# Kuja-Shukra. Same arbitration as ANGSHIK_PROHIBITIONS above, and the same
# shape: strip the known explanatory sentence, then assert the term is absent
# from everything that remains, and assert the sentence is OBSERVED so the
# exemption cannot quietly become a blanket hole.
#
# HONEST NOTE ON THE STRIPPING. ANGSHIK_PROHIBITIONS and this tuple are typed
# out here rather than imported, because chart.py has no constant for either —
# both sentences are inline f-string branches of format_flags_for_prompt(), and
# this file does not own chart.py. That is safe in ONE direction only, which is
# the direction that matters: if the wording drifts, the strip stops matching,
# the term survives into `stripped` and the gate goes RED, and the "never
# observed" assertion below names the sentence that moved. It cannot drift into
# a silent pass. (Gate 3 imports _COMPARABILITY_BAND_SENTENCE because
# matching.py exports it; if chart.py ever grows the equivalent constants,
# import them here and delete these.)
KUJA_SHUKRA_TERM = "Kuja-Shukra"
KUJA_SHUKRA_EXPLANATIONS: tuple[str, ...] = (
    "We treat a Venus-axis-only (Kuja-Shukra) chart as a supplementary, "
    "marriage-specific indicator rather than a full Mangal Dosha, so its "
    "weight is reduced.",
)

SUBSAMPLE_SIZE = 500


def _kuja_shukra_expected(details: ManglikDetails) -> int:
    """How many times "Kuja-Shukra" may legitimately appear, for this chart.

    Zero or one, derived from the chart's state rather than from the prose, so
    it holds whatever the sentence is reworded to. The term is permitted in
    exactly one situation: `compute_manglik_details()` capped a Venus-axis-only
    chart down to "mitigated" with NO §1.3 rule behind it, so
    format_flags_for_prompt() has to name the axis as the cause instead of a
    rule. Anywhere else it is a planet name handed to a prompt that forbids
    planet names, for no reason at all.
    """
    if details.effective_status != "mitigated" or not details.venus_axis_only:
        return 0
    if any(r.effect == "mitigates" for r in details.cancellations):
        return 0        # a real rule fired; the flags block cites the rule
    return 1


def _subsample_key(params: tuple[int, int, int, int, int], status: str) -> tuple:
    """(lagna, Mars house from lagna, effective_status) — the spanning key."""
    lagna, mars = params[0], params[1]
    return (lagna, ((mars - lagna) % 12) + 1, status)


def _pick_subsample(
    buckets: dict[tuple, list[tuple[int, int, int, int, int]]]
) -> list[tuple[int, int, int, int, int]]:
    """Exactly SUBSAMPLE_SIZE charts spanning every (lagna, Mars house, status).

    Round-robin over the sorted bucket keys, so the first pass takes one chart
    from every bucket before any bucket gets a second — coverage is a property
    of the selection order, not of luck. Fully deterministic.
    """
    keys = sorted(buckets)
    picked: list[tuple[int, int, int, int, int]] = []
    depth = 0
    while len(picked) < SUBSAMPLE_SIZE and any(len(buckets[k]) > depth for k in keys):
        for k in keys:
            if len(buckets[k]) > depth:
                picked.append(buckets[k][depth])
                if len(picked) == SUBSAMPLE_SIZE:
                    return picked
        depth += 1
    return picked


# ---------------------------------------------------------------------------
# The FOUR assemblers that carry the Manglik verdict to a seeker
#
# format_flags_for_prompt() emits the one assertion, and four different user
# messages embed it. Checking one of them proves nothing about the other three:
# each is assembled by its own function, in its own block order, and any of
# them can grow a second verdict on its own. Until this block existed the gate
# assembled only the natal one; the other three were hand-checked once, by a
# human, across all four effective_status values. A one-off human check is not
# a gate.
#
#   natal    /kundli             llm._format_seeker_message()
#   outlook  /monthly, /yearly   llm._format_outlook_message()
#   daily    /today              llm._format_daily_message()
#   ask      /ask                assembled INSIDE llm.generate_ask_answer()
#
# The first three are pure functions and are called directly with real
# arguments. The fourth is not callable: /ask builds its user message inline
# and hands it straight to providers.chat(), so there is no function that
# returns it. Rather than re-implement that assembly here — which would make
# the check test THIS file instead of llm.py — the gate calls the REAL
# generate_ask_answer() and intercepts providers.chat, the network hop and only
# the network hop, to read the message the real code actually built. Nothing
# about the message is stubbed. See _ask_message().
PATH_NATAL = "natal   /kundli"
PATH_OUTLOOK = "outlook /monthly,/yearly"
PATH_DAILY = "daily   /today"
PATH_ASK = "ask     /ask"
MESSAGE_PATHS: tuple[str, ...] = (PATH_NATAL, PATH_OUTLOOK, PATH_DAILY, PATH_ASK)

# The monthly window, taken from the real call site in routes/outlook.py
# (monthly: days=30, step_days=1; yearly: days=365, step_days=7). The two share
# _format_outlook_message() verbatim and differ only in the event list handed
# to it, which carries no Manglik text at all — so the monthly window is the
# whole path, and the yearly scan would cost 53 more ephemeris snapshots per
# chart to assert the identical thing.
OUTLOOK_EVENT_DAYS, OUTLOOK_EVENT_STEP_DAYS = 30, 1

# Real /ask inputs. "marriage" is one of routes/ask.py's _ASK_CATEGORIES, and
# the question is the one this bundle exists for — a seeker asking about the
# verdict is exactly when a second, contradicting assertion does the damage.
ASK_QUESTION = "Will Mangal Dosh affect my marriage?"
ASK_CATEGORY = "marriage"
ASK_PROMPT_PATH = REPO_ROOT / "src" / "astro_ai" / "prompts" / "ask.txt"


def _ask_message(chart: Chart, flags, dasha) -> str:
    """The REAL /ask user message, captured by intercepting the provider call.

    generate_ask_answer() assembles its message and passes it directly to
    providers.chat(). Swapping that one function out for the duration of the
    call is the only way to read the message without a network round-trip, an
    API key and a paid token spend per census chart — and it leaves every line
    of the assembly running as written. The original is restored in a finally,
    because `llm.providers` is the shared module object.
    """
    captured: list[str] = []

    def _capture(messages, route=None, **kwargs):
        captured.append(messages[-1]["content"])
        return "(no model was called; this gate never leaves the process)"

    real_chat = llm.providers.chat
    llm.providers.chat = _capture
    try:
        llm.generate_ask_answer(
            chart=chart,
            dasha=dasha,
            flags=flags,
            question=ASK_QUESTION,
            category=ASK_CATEGORY,
            prompt_path=ASK_PROMPT_PATH,
            lang="en",
        )
    finally:
        llm.providers.chat = real_chat

    if len(captured) != 1:
        raise AssertionError(
            f"generate_ask_answer() called providers.chat() {len(captured)} times, "
            "expected exactly 1. The interception above no longer identifies the "
            "user message, so this path is not being checked — fix the capture, do "
            "not delete the assertion."
        )
    return captured[0]


def _message_problems(message: str) -> dict[str, int]:
    """Every Gate 2 assertion, applied to one fully assembled user message.

    Returns counts, not booleans, so a failure can report how far off it is.
    `assertions` and `assertion_lines` are counted separately: the first
    catches the verdict being restated anywhere, the second that it is a LINE
    of its own, which is the shape format_flags_for_prompt() emits and the
    shape MANGLIK_ASSERTION_PREFIX documents.
    """
    stripped = message
    for sentence in ANGSHIK_PROHIBITIONS + KUJA_SHUKRA_EXPLANATIONS:
        stripped = stripped.replace(sentence, "")
    return {
        "assertions": message.count(MANGLIK_ASSERTION_PREFIX),
        "assertion_lines": sum(
            1 for line in message.splitlines()
            if line.startswith(MANGLIK_ASSERTION_PREFIX)
        ),
        # The DANGLING_LITERALS are a strict subset of this pattern, so the
        # regex alone is the whole check on a full message.
        "dangling": len(DANGLING_CLAUSE.findall(message)),
        "removed_lines": sum(message.count(line) for line in REMOVED_ASSERTION_LINES),
        "angshik": stripped.count("Angshik"),
        "kuja_shukra": stripped.count(KUJA_SHUKRA_TERM),
    }


# What the problem counters mean when they are non-zero, in the order they are
# reported. Kept next to _message_problems() so a new counter cannot be added
# without a sentence saying why it matters.
PROBLEM_EXPLANATIONS: dict[str, str] = {
    "assertions": (
        "the assembled message states the Manglik verdict a number of times "
        "other than once. Two is the prompt handing the model two verdicts and "
        "letting it choose; zero is a reading with no grounded verdict at all"
    ),
    "assertion_lines": (
        "the verdict is not exactly one LINE of its own starting with "
        "MANGLIK_ASSERTION_PREFIX — either it moved inside another line, or a "
        "second line now opens with it"
    ),
    "dangling": (
        "a label followed by nothing (/:\\s*\\./), e.g. \"Softened by: .\" — the "
        "prompt asserting a cause it does not have"
    ),
    "removed_lines": (
        "one of the double-assertion lines #176 removed is back in the message"
    ),
    "angshik": (
        '"Angshik" outside the known prohibition sentences — §1.2 / §1.3 F ban '
        "the term as a colloquialism, so it may appear only in a sentence "
        "forbidding it"
    ),
    "kuja_shukra": (
        '"Kuja-Shukra" outside the known Venus-axis explanation — it is Mars '
        "and Venus in Sanskrit, and prompts/natal.txt forbids naming planets"
    ),
}


def gate_2_single_assertion() -> list[str]:
    failures: list[str] = []
    n = 0
    count_hist: Counter[int] = Counter()
    angshik_leaks = 0
    token_mismatch = 0
    removed_line_hits = 0
    dangling_hits = 0
    prohibition_seen = Counter()
    kuja_leaks = 0
    kuja_misplaced = 0
    kuja_charts = 0
    kuja_explanation_seen = Counter()
    samples: list[str] = []
    # Up to two charts per (lagna, Mars house, status) bucket — enough depth for
    # a 500-chart round-robin over the ~326 reachable buckets.
    buckets: dict[tuple, list[tuple[int, int, int, int, int]]] = {}

    for params, chart in census():
        n += 1
        flags = compute_vedic_flags(chart, WHEN)
        details = flags.manglik_details
        if details is None:                       # Gate 1 reports this properly
            continue
        text = format_flags_for_prompt(flags) + "\n" + format_manglik_for_prompt(details)

        key = _subsample_key(params, details.effective_status)
        slot = buckets.setdefault(key, [])
        if len(slot) < 2:
            slot.append(params)

        hits = text.count(MANGLIK_ASSERTION_PREFIX)
        count_hist[hits] += 1
        if hits != 1 and len(samples) < 3:
            samples.append(
                f"{_describe(params)} (status={details.effective_status}) -> "
                f"{hits} assertion line(s)"
            )

        stripped = text
        for sentence in ANGSHIK_PROHIBITIONS:
            if sentence in text:
                prohibition_seen[sentence] += 1
            stripped = stripped.replace(sentence, "")
        if "Angshik" in stripped:
            angshik_leaks += 1
            if len(samples) < 6:
                samples.append(
                    f"{_describe(params)} (status={details.effective_status}) -> "
                    '"Angshik" outside the known prohibition sentences'
                )

        # "Kuja-Shukra" — same exemption shape as "Angshik" above, plus a
        # placement check that owes the prose nothing: the term is allowed on
        # exactly the charts _kuja_shukra_expected() names and on no others, so
        # copying it into the "present" or "cancelled" wording fails here even
        # if the sentence it is copied from is left untouched.
        kuja_stripped = text
        for sentence in KUJA_SHUKRA_EXPLANATIONS:
            if sentence in text:
                kuja_explanation_seen[sentence] += 1
            kuja_stripped = kuja_stripped.replace(sentence, "")
        if KUJA_SHUKRA_TERM in kuja_stripped:
            kuja_leaks += 1
            if len(samples) < 6:
                samples.append(
                    f"{_describe(params)} (status={details.effective_status}, "
                    f"venus_axis_only={details.venus_axis_only}) -> "
                    f'"{KUJA_SHUKRA_TERM}" outside the known Venus-axis explanation'
                )
        want_kuja = _kuja_shukra_expected(details)
        kuja_charts += want_kuja
        if text.count(KUJA_SHUKRA_TERM) != want_kuja:
            kuja_misplaced += 1
            if len(samples) < 9:
                samples.append(
                    f"{_describe(params)} (status={details.effective_status}, "
                    f"venus_axis_only={details.venus_axis_only}) -> "
                    f'"{KUJA_SHUKRA_TERM}" appears {text.count(KUJA_SHUKRA_TERM)} '
                    f"time(s), expected {want_kuja}"
                )

        if (CANCELLED_TOKEN in text) != (details.effective_status == "cancelled"):
            token_mismatch += 1
            if len(samples) < 9:
                samples.append(
                    f"{_describe(params)} -> status={details.effective_status} but "
                    f"{CANCELLED_TOKEN!r} present={CANCELLED_TOKEN in text}"
                )

        if any(line in text for line in REMOVED_ASSERTION_LINES):
            removed_line_hits += 1
        dangle = DANGLING_CLAUSE.search(text)
        if dangle or any(lit in text for lit in DANGLING_LITERALS):
            dangling_hits += 1
            if len(samples) < 12:
                samples.append(
                    f"{_describe(params)} (status={details.effective_status}) -> "
                    f"dangling clause {dangle.group(0)!r}" if dangle else
                    f"{_describe(params)} -> dangling literal clause"
                )

    exactly_one = count_hist.get(1, 0)
    print(f"  {'ok  ' if exactly_one == n else 'FAIL'} exactly one "
          f"{MANGLIK_ASSERTION_PREFIX!r} line on {exactly_one:,}/{n:,} charts "
          f"(counts observed: {dict(sorted(count_hist.items()))})")
    print(f"  {'ok  ' if not angshik_leaks else 'FAIL'} \"Angshik\" appears only "
          f"inside the {len(ANGSHIK_PROHIBITIONS)} known prohibition sentence(s) "
          f"— {angshik_leaks:,} leak(s)")
    print(f"  {'ok  ' if not kuja_leaks else 'FAIL'} \"{KUJA_SHUKRA_TERM}\" appears only "
          f"inside the {len(KUJA_SHUKRA_EXPLANATIONS)} known Venus-axis explanation "
          f"— {kuja_leaks:,} leak(s)")
    print(f"  {'ok  ' if not kuja_misplaced else 'FAIL'} \"{KUJA_SHUKRA_TERM}\" appears "
          f"on exactly the {kuja_charts:,} rule-less Venus-axis-only chart(s) and no "
          f"others — {kuja_misplaced:,} mismatch(es)")
    print(f"  {'ok  ' if not token_mismatch else 'FAIL'} {CANCELLED_TOKEN!r} present "
          f"iff effective_status == 'cancelled' — {token_mismatch:,} mismatch(es)")
    print(f"  {'ok  ' if not removed_line_hits else 'FAIL'} removed double-assertion "
          f"lines {REMOVED_ASSERTION_LINES} absent — {removed_line_hits:,} hit(s)")
    print(f"  {'ok  ' if not dangling_hits else 'FAIL'} no dangling clause "
          f"(/{DANGLING_CLAUSE.pattern}/) — {dangling_hits:,} hit(s)")

    if exactly_one != n:
        failures.append(
            f"{n - exactly_one:,} of {n:,} charts carry {count_hist} occurrences of "
            f"{MANGLIK_ASSERTION_PREFIX!r} rather than exactly one. Two assertions is "
            "the prompt telling the model two different verdicts and letting it pick; "
            "zero is the reading having no grounded verdict at all. "
            "format_flags_for_prompt() emits the one assertion; "
            "format_manglik_for_prompt() must stay evidence-only."
        )
    if angshik_leaks:
        failures.append(
            f'{angshik_leaks:,} chart(s) contain "Angshik" outside the known '
            "prohibition sentences. §1.2 / §1.3 F ban the term as a colloquialism, so "
            "it may appear ONLY inside a sentence forbidding it."
        )
    for sentence in ANGSHIK_PROHIBITIONS:
        if not prohibition_seen[sentence]:
            failures.append(
                f"the prohibition sentence {sentence!r} never appeared in the census. "
                "Either it was reworded (update ANGSHIK_PROHIBITIONS in the same "
                "commit) or the prompt stopped forbidding \"Angshik\" — and until then "
                'this gate is stripping a string that does not exist, which makes the '
                '"Angshik" scan above weaker than it looks.'
            )
    if kuja_leaks:
        failures.append(
            f'{kuja_leaks:,} chart(s) contain "{KUJA_SHUKRA_TERM}" outside the known '
            "Venus-axis explanation. The term is Mars and Venus under their Sanskrit "
            "names, and prompts/natal.txt's STRICT OUTPUT RULES forbid naming planets "
            "in the reading — so every extra place it appears is another chance for it "
            "to reach the seeker's prose. It is permitted in ONE sentence, where it "
            "explains why a Venus-axis-only chart was reduced with no classical rule "
            "behind it."
        )
    if kuja_misplaced:
        failures.append(
            f'{kuja_misplaced:,} chart(s) carry "{KUJA_SHUKRA_TERM}" a number of times '
            "other than _kuja_shukra_expected() allows. That check reads the CHART "
            "(mitigated + venus_axis_only + no §1.3 mitigation rule), not the prose, so "
            "it fires whether the term was copied into another status's wording or the "
            "Venus-axis branch grew a second mention. If the copy is deliberate, argue "
            "it against prompts/natal.txt's ban on planet names first."
        )
    for sentence in KUJA_SHUKRA_EXPLANATIONS:
        if not kuja_explanation_seen[sentence]:
            failures.append(
                f"the Venus-axis explanation {sentence!r} never appeared in the census. "
                "Either it was reworded (update KUJA_SHUKRA_EXPLANATIONS in the same "
                "commit) or the prompt stopped explaining the Venus-axis reduction — "
                "and until then this gate is stripping a string that does not exist, "
                f'which makes the "{KUJA_SHUKRA_TERM}" scan above weaker than it looks.'
            )
    if token_mismatch:
        failures.append(
            f"{token_mismatch:,} chart(s) where the {CANCELLED_TOKEN!r} status token and "
            "effective_status disagree. The token IS the verdict the model reads; a "
            "chart whose dosha is cancelled must say so, and one whose dosha is not "
            "must never carry the token."
        )
    if removed_line_hits:
        failures.append(
            f"{removed_line_hits:,} chart(s) contain one of {REMOVED_ASSERTION_LINES}. "
            "Those were the second and third verdict statements #176 removed from "
            "format_manglik_for_prompt(); re-adding one restores the double assertion."
        )
    if dangling_hits:
        failures.append(
            f"{dangling_hits:,} chart(s) contain a dangling clause — a label followed by "
            "nothing, e.g. \"Softened by: .\". The prompt is asserting a cause it does "
            "not have, directly contradicting the evidence block below it, which "
            "correctly reports that no classical rule applies."
        )
    for line in samples:
        failures.append(f"sample: {line}")

    # --- the real assembled user messages, on a spanning 500-chart subsample ---
    # All FOUR assemblers, not just the natal one. See MESSAGE_PATHS above for
    # why one is not evidence about the other three.
    picked = _pick_subsample(buckets)
    details_line = llm.BirthDetails(
        name="Verification Seeker",
        birth_date=BIRTH_UTC.date().isoformat(),
        birth_time="12:00",
        birth_place="New Delhi, India",
    )
    sub_hist: Counter[int] = Counter()
    sub_lagnas: set[int] = set()
    sub_houses: set[int] = set()
    sub_statuses: set[str] = set()
    sub_samples: list[str] = []
    # Per-path tallies over the same subsample. `path_problems` sums the counts
    # from _message_problems(); `path_cells` records which (path, status) cells
    # were actually reached, because an assertion made over three statuses is
    # not the assertion this gate claims to make.
    path_seen: Counter[str] = Counter()
    path_problems: dict[str, Counter[str]] = {p: Counter() for p in MESSAGE_PATHS}
    path_evidence: Counter[str] = Counter()
    path_cells: set[tuple[str, str]] = set()
    path_samples: list[str] = []
    # The header of the evidence block, taken from the function that emits it
    # rather than re-typed, so "which paths carry the evidence block" is read
    # off chart.py and not off this file's memory of it.
    evidence_header = format_manglik_for_prompt(
        _details("present", "high")
    ).splitlines()[0]

    for params in picked:
        chart = _build(*params)
        flags = compute_vedic_flags(chart, WHEN)
        status = flags.manglik_details.effective_status if flags.manglik_details else "?"
        sub_lagnas.add(params[0])
        sub_houses.add(((params[1] - params[0]) % 12) + 1)
        sub_statuses.add(status)
        # Real ones. A gate that passes None here would be testing a message
        # shape no seeker ever receives.
        chapters = compute_life_chapters(chart)
        dasha = compute_dasha_state(chart, WHEN)
        try:
            message = llm._format_seeker_message(
                details_line, chart, flags, chapters, dasha,
            )
        except Exception as exc:
            failures.append(
                f"{_describe(params)}: llm._format_seeker_message() raised "
                f"{type(exc).__name__}: {exc}"
            )
            continue
        hits = message.count(MANGLIK_ASSERTION_PREFIX)
        sub_hist[hits] += 1
        if hits != 1 and len(sub_samples) < 3:
            sub_samples.append(f"{_describe(params)} (status={status}) -> {hits}")

        # The other three paths, each with genuine arguments computed from this
        # same chart — real transits, real gochar impacts, a real 30-day event
        # scan, a real Panchang. All local ephemeris; no network, no API key.
        transit = compute_transit_snapshot(chart, WHEN)
        messages: dict[str, str] = {PATH_NATAL: message}
        try:
            messages[PATH_OUTLOOK] = llm._format_outlook_message(
                details_line,
                chart,
                transit,
                flags,
                compute_gochar_impacts(chart, WHEN),
                compute_transit_events(
                    chart, start=WHEN, days=OUTLOOK_EVENT_DAYS,
                    step_days=OUTLOOK_EVENT_STEP_DAYS,
                ),
            )
            messages[PATH_DAILY] = llm._format_daily_message(
                details_line, chart, transit, flags, compute_panchang(chart, WHEN),
            )
            messages[PATH_ASK] = _ask_message(chart, flags, dasha)
        except Exception as exc:
            failures.append(
                f"{_describe(params)}: assembling the real user message raised "
                f"{type(exc).__name__}: {exc}. A path that cannot be assembled is a "
                "path that is not being checked."
            )
            continue

        for path, text_ in messages.items():
            path_seen[path] += 1
            path_cells.add((path, status))
            if evidence_header and evidence_header in text_:
                path_evidence[path] += 1
            problems = _message_problems(text_)
            for key, count in problems.items():
                want = 1 if key in ("assertions", "assertion_lines") else 0
                if count != want:
                    path_problems[path][key] += 1
                    if len(path_samples) < 8:
                        path_samples.append(
                            f"{path}: {_describe(params)} (status={status}) -> "
                            f"{key}={count}, expected {want}"
                        )

    sub_ok = sub_hist.get(1, 0) == len(picked) and len(picked) == SUBSAMPLE_SIZE
    print(f"  {'ok  ' if sub_ok else 'FAIL'} real llm._format_seeker_message(): "
          f"{sub_hist.get(1, 0):,}/{len(picked):,} messages carry exactly one "
          f"assertion  [spans {len(sub_lagnas)}/12 lagnas, {len(sub_houses)}/12 Mars "
          f"houses, {len(sub_statuses)}/{len(STATUSES)} statuses]")

    # Per-path results. Every path gets its own line whether it passed or not,
    # so the output records WHICH four things were checked — a gate that only
    # prints failures leaves a reader unable to tell coverage from silence.
    for path in MESSAGE_PATHS:
        problems = path_problems[path]
        seen = path_seen[path]
        ok = seen == len(picked) and not problems
        print(f"  {'ok  ' if ok else 'FAIL'} {path:<24} "
              f"{seen:,}/{len(picked):,} real messages assembled, "
              f"{'no' if not problems else dict(sorted(problems.items()))} problem(s)"
              f"  [evidence block: {'yes' if path_evidence[path] else 'no'}"
              f", {path_evidence[path]:,} msg(s)]")
        if seen != len(picked):
            failures.append(
                f"{path}: only {seen:,} of {len(picked):,} messages were assembled, so "
                "this path is checked over less than it claims."
            )
        for key, count in sorted(problems.items()):
            failures.append(
                f"{path}: {count:,} of {seen:,} assembled messages — "
                f"{PROBLEM_EXPLANATIONS[key]}. This is the fully assembled user "
                "message for this route, not a block of it, so the verdict the seeker "
                "gets on this surface is the one that just moved."
            )

    expected_cells = len(MESSAGE_PATHS) * len(STATUSES)
    print(f"  {'ok  ' if len(path_cells) == expected_cells else 'FAIL'} "
          f"path x effective_status coverage  {len(path_cells)}/{expected_cells} cell(s) "
          f"({len(MESSAGE_PATHS)} assemblers x {len(STATUSES)} statuses)")
    if len(path_cells) != expected_cells:
        missing = sorted(
            (p, s) for p in MESSAGE_PATHS for s in STATUSES if (p, s) not in path_cells
        )
        failures.append(
            f"only {len(path_cells)} of {expected_cells} (path, effective_status) cells "
            f"were exercised; missing {missing}. The four §1.4 wordings are chosen by "
            "status, so a path checked on three of them is a path with an unchecked "
            "wording."
        )
    for line in path_samples:
        failures.append(f"sample: {line}")

    if len(picked) != SUBSAMPLE_SIZE:
        failures.append(
            f"subsample is {len(picked)} charts, expected {SUBSAMPLE_SIZE} — the "
            "spanning selection did not fill, so the assembled-message check ran over "
            "less than it claims."
        )
    for label, got, want in (("lagnas", len(sub_lagnas), 12),
                             ("Mars houses", len(sub_houses), 12),
                             ("statuses", len(sub_statuses), len(STATUSES))):
        if got != want:
            failures.append(
                f"subsample spans only {got}/{want} {label}. The whole point of "
                "assembling the real user message is to catch a block that behaves "
                "differently for some chart shape, which needs the shapes present."
            )
    if sub_hist and set(sub_hist) != {1}:
        failures.append(
            f"the REAL assembled user message carries {dict(sorted(sub_hist.items()))} "
            f"occurrences of {MANGLIK_ASSERTION_PREFIX!r}. The block-level check above "
            "passed, so something else in _format_seeker_message() — another block, or "
            "the flags block being emitted twice — is adding a second verdict."
        )
    for line in sub_samples:
        failures.append(f"sample: {line}")
    return failures


# ---------------------------------------------------------------------------
# Gate 3 / Gate 4 - the 144 (status x severity)^2 combinations
# ---------------------------------------------------------------------------

def _details(status: str, severity: str) -> ManglikDetails:
    """A ManglikDetails built DIRECTLY, including impossible (status, severity) pairs.

    ("none", "high") cannot come out of compute_manglik_details() today.
    mangal_dosh_verdict() still has to be total over the domain it declares —
    #165 was a state everyone assumed unreachable, and the fix is worth nothing
    if the gate only checks the states the engine currently happens to emit.
    """
    return ManglikDetails(
        is_manglik=status != "none",
        houses=(7,),
        primary_house=7,
        severity=severity,
        cancellations=(),
        effective_status=status,
        axis_reasons=("Mars in 7th house from Lagna",),
    )


def _combinations() -> list[tuple[str, str, str, str]]:
    """All 144 (groom status, groom severity, bride status, bride severity)."""
    sides = list(itertools.product(STATUSES, SEVERITIES))
    return [(gs, gv, bs, bv) for gs, gv in sides for bs, bv in sides]


def _expected_branch(g_status: str, g_sev: str, b_status: str, b_sev: str) -> str:
    """The branch re-derived from the two published primitives, nothing else."""
    g_present = is_effectively_manglik(g_status)
    b_present = is_effectively_manglik(b_status)
    if not g_present and not b_present:
        return "neither"
    if g_present and b_present:
        return ("both_comparable" if _severity_comparable(g_sev, b_sev)
                else "both_incomparable")
    return "one_sided"


# Prose an INCOMPATIBLE verdict may never contain.
INCOMPATIBLE_BANNED: tuple[str, ...] = ("the dosha cancels", "No Mangal Dosh concerns")
# Prose a COMPATIBLE verdict may never contain.
COMPATIBLE_BANNED: tuple[str, ...] = ("careful evaluation", "extra remediation",
                                      "not comparable")


def gate_3_badge_and_note_agree(combos: list[tuple[str, str, str, str]]) -> list[str]:
    failures: list[str] = []
    tally: Counter[str] = Counter()
    bad_compatible = 0
    bad_branch = 0
    lexical_hits: list[str] = []

    for g_status, g_sev, b_status, b_sev in combos:
        v = mangal_dosh_verdict(_details(g_status, g_sev), _details(b_status, b_sev))
        tally[v.branch] += 1
        label = f"groom({g_status},{g_sev}) x bride({b_status},{b_sev})"

        if v.branch not in _BRANCH_COMPATIBLE:
            bad_branch += 1
            failures.append(
                f"{label}: branch {v.branch!r} is not in _BRANCH_COMPATIBLE. Every "
                "branch must have a declared badge polarity, or the badge is being "
                "decided somewhere other than this table."
            )
            continue
        if v.compatible != _BRANCH_COMPATIBLE[v.branch]:
            bad_compatible += 1
            failures.append(
                f"{label}: branch {v.branch!r} reports compatible={v.compatible} but "
                f"_BRANCH_COMPATIBLE says {_BRANCH_COMPATIBLE[v.branch]}. The badge and "
                "the branch have come apart — this is issue #165's exact shape."
            )
        want = _expected_branch(g_status, g_sev, b_status, b_sev)
        if v.branch != want:
            bad_branch += 1
            failures.append(
                f"{label}: branch is {v.branch!r}, but is_effectively_manglik() + "
                f"_severity_comparable() say {want!r}. The verdict is using some third "
                "definition of \"is this chart Manglik\" — which is the whole bug."
            )

        # Lexical half. ARBITRATION: _COMPARABILITY_BAND_SENTENCE is the
        # convention disclosure CLAUDE.md requires ("state which convention a
        # page uses"), and it necessarily ends with "... and a low-versus-high
        # pairing as not comparable". That phrase is banned prose in a
        # COMPATIBLE note, so the naive scan flags all 28 both_comparable
        # combinations on correct code. Same arbitration as the "Angshik"
        # prohibitions in Gate 2: strip the known disclosure sentence, then
        # scan what remains. The sentence is IMPORTED, never re-typed, so it
        # cannot drift away from the module. "careful evaluation" and "extra
        # remediation" do not occur in it, so only "not comparable" is
        # exempted, and only where the disclosure actually sits — a compatible
        # note that says "not comparable" in its substantive prose still fails.
        note = v.note
        scanned = note.replace(_COMPARABILITY_BAND_SENTENCE, "")
        banned = INCOMPATIBLE_BANNED if v.compatible is False else COMPATIBLE_BANNED
        for phrase in banned:
            if phrase in scanned:
                lexical_hits.append(
                    f"{label}: branch {v.branch!r}, compatible={v.compatible}, but the "
                    f"note contains {phrase!r}. The badge and the prose are saying "
                    "opposite things to the same couple — the structural checks above "
                    "cannot see this, only the words can."
                )

    for branch in sorted(EXPECTED_BRANCH_TALLY):
        got, want = tally.get(branch, 0), EXPECTED_BRANCH_TALLY[branch]
        print(f"  {'ok  ' if got == want else 'FAIL'} branch {branch:<18} "
              f"{got:>3} combination(s), expected {want}")
        if got != want:
            failures.append(
                f"branch {branch!r} fired on {got} of the {len(combos)} combinations, "
                f"expected {want}. A tally that has moved means the branch boundaries "
                "moved — either is_effectively_manglik() changed which statuses count, "
                "or _severity_comparable() changed the band. Both are user-visible "
                "verdict changes and neither may happen by accident."
            )
    unexpected = sorted(set(tally) - set(EXPECTED_BRANCH_TALLY))
    if unexpected:
        failures.append(
            f"branch(es) {unexpected} are new since this gate was written. Add the "
            "expected tally and the badge polarity deliberately — a new branch is a "
            "new verdict."
        )

    print(f"  {'ok  ' if not bad_compatible else 'FAIL'} compatible == "
          f"_BRANCH_COMPATIBLE[branch] on {len(combos) - bad_compatible}/"
          f"{len(combos)} combination(s)")
    print(f"  {'ok  ' if not bad_branch else 'FAIL'} branch re-derivable from "
          f"is_effectively_manglik() + _severity_comparable() on "
          f"{len(combos) - bad_branch}/{len(combos)} combination(s)")
    print(f"  {'ok  ' if not lexical_hits else 'FAIL'} note prose never contradicts "
          f"the badge on {len(combos) - len(lexical_hits)}/{len(combos)} "
          "combination(s)")
    failures.extend(lexical_hits)
    if len(combos) != COMBO_COUNT:
        failures.append(
            f"{len(combos)} combinations built, expected {COMBO_COUNT} "
            f"({len(STATUSES)} statuses x {len(SEVERITIES)} severities, both partners)"
        )
    return failures


# ---------------------------------------------------------------------------
# Gate 4 - no mutual cancellation across a low/high severity gap
# ---------------------------------------------------------------------------

# Phrases that would amount to claiming the dosha cancelled for this pair.
CANCELLATION_CLAIMS: tuple[str, ...] = (
    "the dosha cancels", "dosha cancels through matching", "cancels through matching",
)
# CLAUDE.md: "State which convention a page uses rather than implying a single
# universal answer." §1.3 rule 20 says "comparable severity" and defines no
# band; the low/high exclusion is a Bhagya convention on a Bhagya severity
# ladder, so the note must say so rather than presenting it as classical fact.
CONVENTION_DISCLOSURE = "comparable"


def gate_4_no_low_high_cancellation(combos: list[tuple[str, str, str, str]]) -> list[str]:
    failures: list[str] = []
    checked = 0

    for g_status, g_sev, b_status, b_sev in combos:
        if {g_sev, b_sev} != {"low", "high"}:
            continue
        if not (is_effectively_manglik(g_status) and is_effectively_manglik(b_status)):
            continue
        checked += 1
        v = mangal_dosh_verdict(_details(g_status, g_sev), _details(b_status, b_sev))
        label = f"groom({g_status},{g_sev}) x bride({b_status},{b_sev})"

        claims = [c for c in CANCELLATION_CLAIMS if c in v.note]
        discloses = CONVENTION_DISCLOSURE in v.note
        ok = (v.compatible is False and v.branch == "both_incomparable"
              and not claims and discloses)
        print(f"  {'ok  ' if ok else 'FAIL'} {label:<62} branch={v.branch:<18} "
              f"compatible={v.compatible}")

        if v.compatible is not False:
            failures.append(
                f"{label}: compatible={v.compatible}. Issue #166: the classical "
                "mutual-Manglik cancellation (§1.3 table E rule 20) requires "
                "\"comparable severity\", and a low against a high is the one pair "
                "unambiguously outside any reading of that word. Telling this couple "
                "the dosha cancels is the harmful direction of the error."
            )
        if v.branch != "both_incomparable":
            failures.append(
                f"{label}: branch is {v.branch!r}, expected 'both_incomparable'. A "
                "low/high pair reaching any other branch means _severity_comparable() "
                "is no longer gating the mutual-cancellation rule."
            )
        for claim in claims:
            failures.append(
                f"{label}: the note claims cancellation ({claim!r}) for a pair the "
                "verdict marks incompatible. Badge and prose contradicting each other "
                "is #165; doing it on a low/high pair is #165 and #166 at once."
            )
        if not discloses:
            failures.append(
                f"{label}: the note never uses the word {CONVENTION_DISCLOSURE!r}. The "
                "corpus says \"comparable severity\" and defines no band — where Bhagya "
                "draws it is our convention, and CLAUDE.md requires a page to state the "
                "convention it uses instead of implying a universal answer."
            )

    expected = EXPECTED_BRANCH_TALLY["both_incomparable"]
    print(f"  {'ok  ' if checked == expected else 'FAIL'} {checked} low/high "
          f"combination(s) checked, expected {expected}")
    if checked != expected:
        failures.append(
            f"{checked} low/high combination(s) reached this gate, expected {expected}. "
            "If it is 0 the gate asserted nothing at all, which is worse than failing."
        )
    return failures


# ---------------------------------------------------------------------------
# Gate 5 - the cache key actually moved
# ---------------------------------------------------------------------------

# Real prompt files, both on paths this bundle changed the assembled message for.
GATED_PROMPTS: tuple[str, ...] = ("natal.txt", "matching.txt")


def gate_5_cache_key_moved() -> list[str]:
    failures: list[str] = []
    version = cache.PROMPT_LOGIC_VERSION

    print(f"  {'ok  ' if version else 'FAIL'} cache.PROMPT_LOGIC_VERSION = {version!r}")
    if not version:
        failures.append(
            "cache.PROMPT_LOGIC_VERSION is empty. An empty token prefixes nothing, so "
            "the fingerprint collapses back to the bare file hash and every check "
            "below passes vacuously."
        )

    prompts_dir = REPO_ROOT / "src" / "astro_ai" / "prompts"
    for name in GATED_PROMPTS:
        path = prompts_dir / name
        if not path.exists():
            failures.append(
                f"{name}: prompt file not found at {path} — this gate needs a real "
                "prompt file, not a synthetic one"
            )
            print(f"  FAIL {name}  missing")
            continue
        got = cache.fingerprint_prompt(path)
        bare = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
        moved = got != bare
        prefixed = got.startswith(version) if version else False
        ok = moved and prefixed
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<14} fingerprint {got!r} vs bare "
              f"sha256[:8] {bare!r}")
        if not moved:
            failures.append(
                f"{name}: fingerprint_prompt() returns the bare file hash. "
                "PROMPT_LOGIC_VERSION is no longer folded in, so a change to the Python "
                "that assembles the user message moves no cache key — and natal entries "
                "are written with ttl_days=None. The #176/#165/#166 fixes would ship and "
                "the site would keep serving the pre-fix readings forever."
            )
        if not prefixed:
            failures.append(
                f"{name}: fingerprint {got!r} does not start with PROMPT_LOGIC_VERSION "
                f"{version!r}. Bumping the version must be able to invalidate every key "
                "built from this prompt; if the token is not the prefix, it cannot."
            )
    return failures


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Bite test (--self-test) — prove these gates can actually fail
# ---------------------------------------------------------------------------
#
# Five green gates are evidence only if red is reachable. Each corruption below
# patches one of the actually-shipped bugs back into the real module the
# production path resolves through, runs the gate meant to catch it, and
# requires a non-empty failure list. A corruption that leaves its gate green is
# itself a failure: it means the gate asserts nothing about that bug.
#
# The patch target is the module attribute the *production* code looks up at
# call time, never this script's own imported name:
#   - compute_vedic_flags()      resolves chart.compute_manglik_details
#   - mangal_dosh_verdict()      resolves matching._severity_comparable
#   - _format_seeker_message()   resolves llm.format_manglik_for_prompt
#     (llm.py imports that name into its own namespace, so patching chart.*
#      would leave the real prompt path untouched and the test would pass
#      vacuously — the exact failure mode this whole file exists to prevent)


@contextlib.contextmanager
def _venus_axis_dropped() -> Iterator[None]:
    """#176: the pre-fix 2-axis engine — Lagna and Moon only, Venus ignored."""
    from astro_ai import chart as chart_mod

    real = chart_mod.compute_manglik_details

    def patched(chart: Chart) -> ManglikDetails:
        details = real(chart)
        if details.venus_axis_only:
            return dataclasses.replace(
                details,
                is_manglik=False,
                houses=(),
                primary_house=0,
                severity="none",
                effective_status="none",
                axis_reasons=(),
                venus_axis_only=False,
            )
        return details

    chart_mod.compute_manglik_details = patched
    try:
        yield
    finally:
        chart_mod.compute_manglik_details = real


@contextlib.contextmanager
def _comparability_ignored() -> Iterator[None]:
    """#166: mutual cancellation with the comparable-severity check removed."""
    from astro_ai import matching as matching_mod

    real = matching_mod._severity_comparable
    matching_mod._severity_comparable = lambda a, b: True
    try:
        yield
    finally:
        matching_mod._severity_comparable = real


@contextlib.contextmanager
def _branch_table_flipped() -> Iterator[None]:
    """#165: the badge claims compatible where the note says it cannot cancel."""
    from astro_ai import matching as matching_mod

    real = dict(matching_mod._BRANCH_COMPATIBLE)
    matching_mod._BRANCH_COMPATIBLE["both_incomparable"] = True
    try:
        yield
    finally:
        matching_mod._BRANCH_COMPATIBLE.clear()
        matching_mod._BRANCH_COMPATIBLE.update(real)


@contextlib.contextmanager
def _double_assertion_restored() -> Iterator[None]:
    """#176: the pre-fix prompt carried a second, contradicting Manglik line."""
    from astro_ai import llm as llm_mod

    real = llm_mod.format_manglik_for_prompt

    def patched(details: ManglikDetails) -> str:
        return f"{real(details)}\n{MANGLIK_ASSERTION_PREFIX} Mathematical: yes."

    llm_mod.format_manglik_for_prompt = patched
    try:
        yield
    finally:
        llm_mod.format_manglik_for_prompt = real


@contextlib.contextmanager
def _cache_version_cleared() -> Iterator[None]:
    """The fix ships, every cached natal reading keeps serving the old answer."""
    real = cache.PROMPT_LOGIC_VERSION
    cache.PROMPT_LOGIC_VERSION = ""
    try:
        yield
    finally:
        cache.PROMPT_LOGIC_VERSION = real


# (label, corruption, gate-title prefixes that MUST redden)
_CORRUPTIONS: list[tuple[str, object, tuple[str, ...]]] = [
    ("#176  engine split — Venus axis dropped from compute_manglik_details",
     _venus_axis_dropped, ("Gate 1",)),
    ("#166  comparability ignored — _severity_comparable() always True",
     _comparability_ignored, ("Gate 4",)),
    ("#165  branch table flipped — both_incomparable marked compatible",
     _branch_table_flipped, ("Gate 4",)),
    ("#176  prompt regression — a second Manglik assertion line restored",
     _double_assertion_restored, ("Gate 2",)),
    ("cache  PROMPT_LOGIC_VERSION cleared — fix ships, cache serves the old read",
     _cache_version_cleared, ("Gate 5",)),
]


def _run_gates_quietly(
    gates: list[tuple[str, object]], only: tuple[str, ...] | None = None
) -> dict[str, int]:
    """Run gates with their output suppressed; return {title: failure count}."""
    out: dict[str, int] = {}
    sink = io.StringIO()
    for title, run in gates:
        if only and not any(title.startswith(p) for p in only):
            continue
        with contextlib.redirect_stdout(sink):
            try:
                failures = run()
            except Exception as err:
                failures = [f"gate raised {type(err).__name__}: {err}"]
        out[title] = len(failures)
    return out


def self_test() -> int:
    """Corrupt the code on purpose; require the gates to notice."""
    print("Manglik coherence — BITE TEST (--self-test)")
    print("  Each corruption puts a real, previously-shipped bug back into the")
    print("  module the production path resolves through, then requires the")
    print("  matching gate to FAIL. A gate that stays green is a broken gate.")
    print()

    gates = _build_gates(_combinations())

    print("Baseline — uncorrupted tree must be fully green")
    baseline = _run_gates_quietly(gates)
    dirty = {t: n for t, n in baseline.items() if n}
    if dirty:
        for title, n in dirty.items():
            print(f"  FAIL {title} — {n} problem(s) before any corruption")
        print()
        print("FAIL — the tree is already red, so no corruption below proves "
              "anything. Fix the gate failures first, then re-run --self-test.")
        return 1
    print(f"  ok   all {len(baseline)} gate(s) green")
    print()

    problems: list[str] = []
    for label, corruption, must_fail in _CORRUPTIONS:
        print(label)
        with corruption():  # type: ignore[operator]
            results = _run_gates_quietly(gates, only=must_fail)
        for title, n in sorted(results.items()):
            if n:
                print(f"  ok   {title} reddened ({n} problem(s))")
            else:
                print(f"  FAIL {title} stayed GREEN under this corruption")
                problems.append(f"{label}: {title} did not detect the bug")
        if not results:
            print("  FAIL no gate matched the required prefixes "
                  f"{must_fail!r} — the corruption ran against nothing")
            problems.append(f"{label}: matched no gate")
        print()

    print("Restoration — every patch must have been undone")
    restored = _run_gates_quietly(gates)
    leaked = {t: n for t, n in restored.items() if n}
    if leaked:
        for title, n in leaked.items():
            print(f"  FAIL {title} still red after restore ({n} problem(s))")
            problems.append(f"restore leaked into {title}")
    else:
        print(f"  ok   all {len(restored)} gate(s) green again")
    print()

    if problems:
        print(f"FAIL — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"PASS — {len(_CORRUPTIONS)} corruption(s), every one caught, "
          "every patch cleanly restored")
    return 0


def _build_gates(combos: list[tuple[str, str, str, str]]) -> list[tuple[str, object]]:
    """The gate roster, shared by the real run and the bite test."""
    return [
        ("Gate 1 - one Manglik engine (#176)", gate_1_one_engine),
        ("Gate 2 - exactly one Manglik assertion per prompt (#176)",
         gate_2_single_assertion),
        ("Gate 3 - badge and note never contradict (#165)",
         lambda: gate_3_badge_and_note_agree(combos)),
        ("Gate 4 - no cancellation across a low/high gap (#166)",
         lambda: gate_4_no_low_high_cancellation(combos)),
        ("Gate 5 - the prompt cache key actually moved", gate_5_cache_key_moved),
    ]


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    print("Manglik coherence verification — issues #176 + #165 + #166")
    print("  engines   : src/astro_ai/chart.py compute_vedic_flags() / "
          "compute_manglik_details()")
    print("  verdict   : src/astro_ai/matching.py mangal_dosh_verdict()")
    print("  corpus    : knowledge/vedic_reference.md §1.1 (three axes), "
          "§1.3 (cancellations, rule 20), §1.4 (prompt wordings)")
    print(f"  census    : {CENSUS_SIZE:,} synthetic charts "
          f"({' x '.join(f'12 {a}' for a in CENSUS_AXES)}), transit fixed at "
          f"{WHEN.isoformat()}")
    print(f"  combos    : {COMBO_COUNT} (status x severity)^2 pairs, built directly")
    print()

    combos = _combinations()

    gates = _build_gates(combos)

    all_failures: list[str] = []
    results: list[tuple[str, int]] = []
    for title, run in gates:
        print(title)
        try:
            failures = run()
        except Exception as err:  # a gate that crashes is a failing gate
            failures = [f"gate raised {type(err).__name__}: {err}"]
        for line in failures[:20]:
            print(f"  FAIL: {line}")
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        print(f"  -> {'PASS' if not failures else f'FAIL ({len(failures)} problem(s))'}")
        print()
        results.append((title, len(failures)))
        all_failures.extend(failures)

    print("Summary")
    for title, n in results:
        print(f"  {'PASS' if n == 0 else f'FAIL ({n})':<9} {title}")
    print()
    if all_failures:
        print(f"FAIL — {len(all_failures)} problem(s). Do not adjust the computation "
              "to silence a gate, and do not relax an assertion to fit a new answer.")
        print("  compute_vedic_flags() and compute_manglik_details() are ONE engine — "
              "the first delegates to the second and carries its result; every "
              "assertion above comes from knowledge/vedic_reference.md §1.1 (Manglik "
              "is read from the Lagna, the Moon AND Venus), §1.3 table E rule 20 "
              "(mutual cancellation needs comparable severity) and §1.4 (the three "
              "cancelled / mitigated / present wordings, and the ban on \"Angshik\").")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
