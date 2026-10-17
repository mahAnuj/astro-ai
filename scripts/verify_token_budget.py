#!/usr/bin/env python3
r"""Gate: the input-token size of every LLM prompt path stays inside a recorded budget.

WHY THIS EXISTS (#400)
----------------------
Two production incidents were request-size regressions that nothing measured
before merge:

  * #212  prompt input grew 18.5% per call on the path behind the 21-day
          outage. Every step was small; the trend was fatal.
  * #266  `/kundli` answered "high demand" for every chart: the natal request
          (18,095 B of `natal.txt` plus the chart payload) was bigger than
          Groq's whole 8,000 TPM bucket, so it 413'd and no retry could help.

The agent definitions tell engineers to "measure input tokens before and
after" and QA that "an unmeasured token claim is a FAIL". That was an honour
system. This gate is the mechanism.

WHAT IT MEASURES
----------------
The ELEVEN prompt paths, one per file in `src/astro_ai/prompts/*.txt`, composed
exactly as `llm._system_prompt` composes them:

  ask                      ask.txt alone
  ask+matching             ask.txt + ask_matching.txt            (overlay)
  ask+matching_third_party ask.txt + ask_matching_third_party.txt
  ask+numerology           ask.txt + ask_numerology.txt
  natal, daily, monthly, yearly, matching, rashifal_single, dasha_deep_dive

The three `ask_*` files are never sent alone: `ASK_OVERLAY_PATHS` appends each
to ask.txt. So each overlay is measured as ask.txt + overlay — the request that
actually goes out — and each of the eleven files has a ceiling by way of the
route that contains it. Path constants come from `routes/deps.py`, not from
hardcoded names, so a renamed constant is an import error rather than a quiet
drift. A TWELFTH `prompts/*.txt` that no route above covers FAILS the gate: a
new prompt cannot ship unbudgeted.

System prompt only, for every route except natal. Per-route payload fixtures
were deliberately not built (YAGNI): the system prompt is the part an engineer
edits and the part that is sent on every call. Natal additionally gets a
`natal+payload` row — its system prompt plus the user message for one golden
chart (`cancer-lagna-manglik-exempt`, the largest of the eight, unshed) — because
#266 was the SUM crossing the TPM line, not the prompt alone.

Each route is measured in `en` and in `hi`. `_LANG_SUFFIX["hi"]` is appended to
every system prompt and is not free (see the output); the ceiling is judged on
the larger of the two, the growth check on `en`.

THE TABLE, AND WHY THIS FILE NEVER WRITES TO IT
-----------------------------------------------
`BUDGET` below is committed: route -> (baseline_tokens, ceiling_tokens,
measured_on, reason). There is no `--update` flag and there never should be.
A gate that regenerates its own expectations passes on anything — that was the
rule PR #395's `--update` flag was right about. **Raising a number is an explicit
edit to this file, in a reviewed diff, with the reason beside it.** If this
gate is red because you grew a prompt on purpose, edit the row; do not look for
a flag.

Two independent failures, because they catch different things:

  ceiling  measured > ceiling                    the hard line (a 413 in waiting)
  growth   measured > baseline * (1 + pct/100)   #212: each step under any
                                                 ceiling, the trend fatal

`--max-growth-pct` defaults to 5. Shrinkage is reported, not failed, but a
stale-high baseline silently widens the growth allowance — lower it by hand.

NO LLM, NO API KEY, ZERO RUNTIME TOKENS
---------------------------------------
This tokenises text we already have. It makes no LLM call. Two honest
qualifications to "no network":

  * `tiktoken.get_encoding("o200k_base")` DOWNLOADS its 3.6 MB vocabulary on
    first use (openaipublic.blob.core.windows.net) and caches it under
    $TMPDIR/data-gym-cache. A CI runner is ephemeral, so every pr-gates run
    pays that download. If it cannot be fetched this gate exits 2 — not 0.
    Pre-seed `TIKTOKEN_CACHE_DIR` to run offline.
  * `compute_chart` geocodes through Nominatim. This gate does NOT: it
    replaces `chart.geocode_place` with a pinned Chennai coordinate, because a
    network call to a rate-limited third party has no business deciding whether
    a PR merges.

`o200k_base` is a proxy for the o200k_harmony encoding gpt-oss-120b uses —
within a percent or two, not exact (see `measure_natal_request.py`). It is
used consistently, which is what a ratchet needs.

Exit 0 pass / 1 fail / 2 could not run (tiktoken or its vocabulary missing, or
no ephemeris). **Exit 2 is NOT a pass.**

OVERRIDES (for proving the gate, not for passing it)
----------------------------------------------------
    --prompt natal=/path/to/old_natal.txt     one file, by stem
    --prompts-dir /path/to/dir                every file, by name, from DIR

They exist so the #266 regression can be reproduced from the pre-fix prompt and
so tests can inflate a copy. The table is NOT loosened, the banner is printed
at the top and the verdict line says "(OVERRIDDEN ...)": an overridden pass is
never reported as plain PASS, and a missing or empty override file is a failure
rather than a silent fall-back to the shipped one.

    uv run python scripts/verify_token_budget.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# route -> (baseline_tokens, ceiling_tokens, measured_on, reason)
#
# baseline  what this script printed on the date beside it, `en`, tiktoken
#           o200k_base. The growth check is made against it.
# ceiling   the hard line, judged on the LARGER of en and hi. For the eleven
#           prompt rows it is the measured `hi` figure + 10%, rounded up to the
#           next 50 — enough that a clarifying sentence does not force a table
#           edit, not enough that a section can arrive unremarked. It sits above
#           the 5% growth line on purpose: growth is the tripwire, the ceiling
#           is the backstop for a baseline someone has already raised.
#           `natal+payload` is the exception; see its reason.
#
# Re-measured 2026-10-17 on 16c6ea4 (the `hi` suffix adds 132 tok to every
# route): measured en/hi = ask 1251/1383, ask+matching 1964/2096,
# ask+matching_third_party 2090/2222, ask+numerology 1822/1954, natal 3111/3243,
# daily 743/875, monthly 732/864, yearly 819/951, matching 1265/1397,
# rashifal_single 2278/2410, dasha_deep_dive 944/1076, natal+payload 6798/6930.
#
# RAISING A NUMBER IS AN EXPLICIT EDIT TO THIS TABLE, IN A REVIEWED DIFF, WITH
# THE REASON BESIDE IT. The gate never rewrites it and has no flag that does
# (#400, and PR #395's `--update`: a gate that regenerates its own expectations
# passes on anything). Do not "fix" a red run by editing a number you did not
# mean to raise.
_D = "2026-10-17"
BUDGET: dict[str, tuple[int, int, str, str]] = {
    "ask":                      (1251, 1550, _D, "hi 1383 + 10%"),
    "ask+matching":             (1964, 2350, _D, "hi 2096 + 10%"),
    "ask+matching_third_party": (2090, 2450, _D, "hi 2222 + 10%"),
    "ask+numerology":           (1822, 2150, _D, "hi 1954 + 10%"),
    "natal":                    (3111, 3600, _D,
                                 "hi 3243 + 10%. natal.txt was 4,332 tok before the "
                                 "#266 compression (18,095 B -> 13,135 B)"),
    "daily":                    (743, 1000, _D, "hi 875 + 10%"),
    "monthly":                  (732, 1000, _D, "hi 864 + 10%"),
    "yearly":                   (819, 1050, _D, "hi 951 + 10%"),
    "matching":                 (1265, 1550, _D, "hi 1397 + 10%"),
    "rashifal_single":          (2278, 2700, _D,
                                 "hi 2410 + 10%; sent on a cache miss of "
                                 "/rashifal/{rashi}, a free-tier TPD path"),
    "dasha_deep_dive":          (944, 1200, _D, "hi 1076 + 10%"),
    # System prompt + the largest golden chart's user message, unshed. Not
    # derived from the prompt: derived from the BUCKET. Groq's TPM is 8,000 per
    # model; providers.REQUEST_TOKEN_CEILING (8,000) less REQUEST_TOKEN_MARGIN
    # (1,000, the unmeasurable chat-template and completion remainder) is the
    # budget the runtime guard sheds chart blocks down to, so this ceiling is
    # 7,000: crossing it means the biggest chart starts LOSING blocks, and the
    # 1,000-tok margin to the 8,000 bucket (12.5%) is what keeps #266 away.
    # Headroom at baseline is 202 tok en, 70 tok hi, deliberately thin: this is
    # the row that broke production, and an edit to natal.txt SHOULD come here.
    "natal+payload":            (6798, 7000, _D,
                                 "7,000 = 8,000 TPM less the runtime guard's 1,000 margin"),
}

GROWTH_PCT_DEFAULT = 5.0

# The one golden chart whose payload is measured. The largest of the eight
# (tests/test_natal_request_size.py::BIGGEST_CHART, measured 2026-09-05).
PAYLOAD_FIXTURE = "cancer-lagna-manglik-exempt"
FIXTURES = REPO_ROOT / "tests" / "kundali-qa-fixtures.json"

# Chennai, pinned. `compute_chart` otherwise geocodes over Nominatim, a rate-
# limited third party, and a PR gate must not depend on one. Same cut as
# tests/conftest.py::_offline_geocode: only the one outbound call is replaced,
# the ephemeris arithmetic is real.
_PINNED_PLACE = (13.0827, 80.2707, "Asia/Kolkata")
# Pinned so the payload is the same text on any date. life_chapters has no
# `when` parameter and still reads the clock; its drift is a few tokens and
# lives inside the ceiling's headroom.
_PINNED_WHEN = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


class CouldNotRun(Exception):
    """The measurement cannot be made — distinct from a measurement that failed.

    Exit 2, never 0. `verify_css_build.py` shipped `lg:col-span-3` missing for
    eleven days (#229) because "could not verify" was read as "fine".
    """


def load_encoding():
    """tiktoken's o200k_base, or CouldNotRun.

    Separate and module-level so a test can substitute a tokenizer without
    reaching the network. First use DOWNLOADS the vocabulary (see the header).
    """
    try:
        import tiktoken

        return tiktoken.get_encoding("o200k_base")
    except Exception as exc:  # noqa: BLE001 — ImportError, URLError, ValueError(hash)...
        raise CouldNotRun(f"tiktoken o200k_base unavailable: {type(exc).__name__}: {exc}") from exc


def route_files(deps) -> dict[str, tuple[Path, Path | None]]:
    """route -> (base prompt, overlay or None), from routes/deps.py's constants."""
    ov = deps.ASK_OVERLAY_PATHS
    ask = deps.ASK_PROMPT_PATH
    return {
        "ask": (ask, None),
        "ask+matching": (ask, ov["matching"]),
        "ask+matching_third_party": (ask, ov["matching_third_party"]),
        "ask+numerology": (ask, ov["numerology"]),
        "natal": (deps.PROMPT_PATH, None),
        "daily": (deps.DAILY_PROMPT_PATH, None),
        "monthly": (deps.MONTHLY_PROMPT_PATH, None),
        "yearly": (deps.YEARLY_PROMPT_PATH, None),
        "matching": (deps.MATCHING_PROMPT_PATH, None),
        "rashifal_single": (deps.RASHIFAL_PROMPT_PATH, None),
        "dasha_deep_dive": (deps.DASHA_DEEP_DIVE_PROMPT_PATH, None),
    }


def resolve(path: Path, prompts_dir: Path, overrides: dict[str, Path]) -> Path:
    """Apply the override flags. An override is by file STEM, wherever it is used."""
    if path.stem in overrides:
        return overrides[path.stem]
    return prompts_dir / path.name


def uncovered_prompts(routes, prompts_dir: Path) -> list[str]:
    """Prompt files on disk that no route composes. Each is an unbudgeted prompt."""
    used = set()
    for base, overlay in routes.values():
        used.add(base.name)
        if overlay is not None:
            used.add(overlay.name)
    return sorted(p.name for p in prompts_dir.glob("*.txt") if p.name not in used)


def evaluate(measured: dict[str, tuple[int, int]], budget: dict, max_growth_pct: float) -> list[str]:
    """Pure comparison: measured {route: (en, hi)} against the table. Returns failures.

    No I/O, so a test can drive it with invented numbers. This is also where the
    gate's whole claim lives — a mutation that neuters either comparison below
    must turn tests/test_token_budget_gate.py red.
    """
    failures: list[str] = []
    for route, (en, hi) in measured.items():
        if route not in budget:
            failures.append(
                f"{route}: no recorded ceiling. A new prompt path ships with a "
                f"row in BUDGET (baseline, ceiling, date, reason) or not at all."
            )
            continue
        baseline, ceiling, on, _why = budget[route]
        worst = max(en, hi)
        if worst > ceiling:
            failures.append(
                f"{route}: {worst:,} tok ({'hi' if hi >= en else 'en'}) exceeds the ceiling {ceiling:,} "
                f"(+{worst - ceiling:,}; baseline {baseline:,} measured {on}). "
                f"A deliberate increase is an edit to BUDGET with a reason."
            )
        limit = baseline * (1 + max_growth_pct / 100)
        if en > limit:
            failures.append(
                f"{route}: {en:,} tok is +{(en / baseline - 1) * 100:.1f}% on the "
                f"baseline {baseline:,} (measured {on}), over the {max_growth_pct:g}% "
                f"growth allowance ({limit:,.0f}); ceiling {ceiling:,}. "
                f"#212 grew 18.5% per call with every step under a ceiling."
            )
    for route in budget:
        if route not in measured:
            failures.append(
                f"{route}: in BUDGET but not measured. A row for a path that no "
                f"longer exists is stale; a path that went missing is worse."
            )
    return failures


def natal_payload(llm) -> str:
    """The user message for PAYLOAD_FIXTURE, as generate_reading builds it, unshed."""
    from astro_ai import chart
    from astro_ai.chart import (
        compute_chart, compute_dasha_state, compute_life_chapters, compute_vedic_flags,
    )

    try:
        fx = json.loads(FIXTURES.read_text())[PAYLOAD_FIXTURE]
    except (OSError, KeyError, ValueError) as exc:
        raise CouldNotRun(f"fixture {PAYLOAD_FIXTURE!r} unreadable: {exc}") from exc
    real = chart.geocode_place
    chart.geocode_place = lambda place: _PINNED_PLACE
    try:
        c = compute_chart(fx["birth_date"], fx["birth_time"], fx["birth_place"])
        details = llm.BirthDetails(
            fx.get("name", ""), fx["birth_date"], fx["birth_time"], fx["birth_place"]
        )
        return llm._format_seeker_message(
            details, c,
            compute_vedic_flags(c, _PINNED_WHEN),
            compute_life_chapters(c),
            compute_dasha_state(c, _PINNED_WHEN),
        )
    except Exception as exc:  # noqa: BLE001 — no ephemeris, bad fixture...
        raise CouldNotRun(f"natal payload could not be computed: {type(exc).__name__}: {exc}") from exc
    finally:
        chart.geocode_place = real


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Per-route input-token budget gate (#400).")
    ap.add_argument("--max-growth-pct", type=float, default=GROWTH_PCT_DEFAULT,
                    help="fail a route that grew more than this %% over its recorded "
                    f"baseline (default {GROWTH_PCT_DEFAULT:g})")
    ap.add_argument("--prompt", action="append", default=[], metavar="STEM=PATH",
                    help="measure PATH in place of prompts/STEM.txt (e.g. natal=old.txt). "
                    "The table is not loosened and the verdict says it was overridden.")
    ap.add_argument("--prompts-dir", type=Path, default=None,
                    help="read every prompt, by file name, from this directory instead")
    args = ap.parse_args(argv)

    overrides: dict[str, Path] = {}
    for item in args.prompt:
        stem, sep, raw = item.partition("=")
        if not sep or not stem or not raw:
            ap.error(f"--prompt wants STEM=PATH, got {item!r}")
        overrides[stem] = Path(raw)

    print("Token budget gate (#400) — input tokens per prompt path, tiktoken o200k_base")
    try:
        enc = load_encoding()
        from astro_ai import llm
        from astro_ai.routes import deps

        prompts_dir = args.prompts_dir or deps.PROMPTS_DIR
        declared = route_files(deps)
        routes = {
            r: (resolve(b, prompts_dir, overrides),
                None if o is None else resolve(o, prompts_dir, overrides))
            for r, (b, o) in declared.items()
        }
        unknown = sorted(s for s in overrides if not any(
            s in (b.stem, o.stem if o else None) for b, o in declared.values()))
        if unknown:
            ap.error(f"--prompt names no prompt file: {', '.join(unknown)}")

        def count(text: str) -> int:
            return len(enc.encode(text))

        failures: list[str] = []
        for stem, path in overrides.items():
            if not path.is_file() or path.stat().st_size == 0:
                failures.append(f"override {stem}={path} is missing or empty — "
                                f"refusing to fall back to the shipped file")
        if overrides or args.prompts_dir:
            shown = [f"{s}={p}" for s, p in overrides.items()]
            if args.prompts_dir:
                shown.append(f"prompts-dir={args.prompts_dir}")
            print(f"  *** OVERRIDE ACTIVE: {', '.join(shown)}")
            print("  *** measuring files that are NOT what ships; a pass here proves nothing")
            print("  *** about the tree. The table is unchanged.")

        # Coverage is judged on the DECLARED names, not the resolved paths: an
        # override renames the file being measured (natal_prefix.txt), and
        # judging that would report natal.txt as uncovered for the wrong reason.
        extra = uncovered_prompts(declared, prompts_dir)
        for name in extra:
            failures.append(
                f"{name}: a prompt file with no route in this gate. Every prompts/*.txt "
                f"needs a BUDGET row and an entry in route_files() — a prompt cannot "
                f"ship unbudgeted."
            )

        measured: dict[str, tuple[int, int]] = {}
        for route, (base, overlay) in routes.items():
            try:
                measured[route] = (
                    count(llm._system_prompt(base, "en", overlay)),
                    count(llm._system_prompt(base, "hi", overlay)),
                )
            except OSError as exc:
                failures.append(f"{route}: prompt unreadable: {exc}")
        if "natal" in measured:
            user = count(natal_payload(llm))
            n_en, n_hi = measured["natal"]
            measured["natal+payload"] = (n_en + user, n_hi + user)
    except CouldNotRun as exc:
        print(f"  COULD NOT VERIFY: {exc}")
        print("  -> SKIPPED (exit 2). This is NOT a pass — the check did not run.")
        return 2

    failures += evaluate(measured, BUDGET, args.max_growth_pct)

    print(f"\n  {'route':<26}{'baseline':>9}{'en':>7}{'  d%':>7}{'hi':>7}{'ceiling':>9}{'headroom':>10}")
    print("  " + "-" * 75)
    for route, (en, hi) in measured.items():
        row = BUDGET.get(route)
        if row is None:
            print(f"  {route:<26}{'-':>9}{en:>7,}{'':>7}{hi:>7,}{'-':>9}{'-':>10}  NO ROW")
            continue
        baseline, ceiling, _on, _why = row
        delta = (en / baseline - 1) * 100
        print(f"  {route:<26}{baseline:>9,}{en:>7,}{delta:>+6.1f}%{hi:>7,}{ceiling:>9,}"
              f"{ceiling - max(en, hi):>+10,}")
    hi_costs = {hi - en for en, hi in measured.values()}
    print(f"\n  Hindi suffix adds {', '.join(f'{c:,}' for c in sorted(hi_costs))} tok per route "
          f"(ceiling is judged on the larger of en/hi; growth on en).")
    print("  Scope: system prompt only, except natal+payload (system + one golden chart,\n"
          "  unshed). Zero LLM calls; zero runtime tokens.")
    shrunk = [r for r, (en, _hi) in measured.items()
              if r in BUDGET and en < BUDGET[r][0] * (1 - args.max_growth_pct / 100)]
    if shrunk:
        print(f"  NOTE: {', '.join(shrunk)} shrank by more than {args.max_growth_pct:g}%. "
              f"Not a failure, but the stale-high baseline now widens the growth\n"
              f"  allowance. Lower it by hand in BUDGET.")

    if failures:
        print(f"\nFAIL — {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    tail = " (OVERRIDDEN — not a statement about the tree)" if overrides or args.prompts_dir else ""
    print(f"\nPASS{tail} — {len(measured)} paths inside their recorded budget"
          f" (growth allowance {args.max_growth_pct:g}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
