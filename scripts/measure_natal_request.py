#!/usr/bin/env python3
r"""Measure the real token size of a `/kundli` natal request, per chart.

WHY THIS EXISTS
---------------
`/kundli` failed in production with a Groq 413:

    Request too large for model 'openai/gpt-oss-120b' ...
    tokens per minute (TPM): Limit 8000, Requested 8562

Everything downstream of that — how far the prompt has to be compressed, what
ceiling a runtime size guard should enforce, whether a chart needs blocks shed
before it can be sent at all — depends on a number nobody in this repo has
ever measured. `cache.estimate_tokens` exists but is a 4.0-chars-per-token
heuristic built for the `/admin/usage` counters, and CLAUDE.md is explicit
that an unmeasured token claim is a FAIL.

So this script assembles the ACTUAL request the route would send — the same
`_system_prompt` and `_format_seeker_message` calls `generate_reading` makes —
for every chart in `tests/kundali-qa-fixtures.json`, and counts it three ways:

  * **tiktoken `o200k_base`** — a real BPE tokenizer, and the closest publicly
    available encoding to the o200k_harmony one `gpt-oss-120b` uses. Not
    identical; treat it as accurate to a percent or two, not exact. It is the
    column to trust.
  * **`cache.estimate_tokens`** — what the codebase currently believes.
  * **chars / 3.6** — the constant `verify_natal_prompt.py` budgets with.

The point of printing all three is calibration. A size guard that UNDER-counts
is worse than no guard: it waves oversized requests through to the same 413 it
was added to prevent. If `estimate_tokens` reads low against tiktoken here,
the guard must not use it as-is.

Fixtures are the eight golden charts added 2026-07-24 for kundali-qa, which
until now nothing in the repo read. They were chosen for the scenarios that
make a request LARGE — an uncancelled Manglik pulls in the MANGLIK DETAIL
block, sade sati and gaja-kesari pull in topic summaries — so they are a fair
sample of the worst case, not of the median.

Needs the ephemeris (no network, no API key):

    uv run python scripts/measure_natal_request.py
    uv run python scripts/measure_natal_request.py --compare path/to/old_natal.txt

`--live` additionally answers the question this repo cannot answer statically:
**does Groq charge the reserved completion against the 8,000 TPM bucket?**

`providers.py` sets no `max_completion_tokens` today, and whether that is free
budget or a large hidden cost decides whether capping it is worth the
truncation risk that made `groq_qwen` unusable. The static evidence bounds it
but does not settle it: gpt-oss-120b's default completion limit is tens of
thousands of tokens, so if Groq reserved it in full against an 8,000 TPM
bucket then EVERY natal request would have 413'd from the day the chain was
configured, and they did not. That says the reservation is not the dominant
term. It does not say it is zero.

Settling it needs one real call, which needs a GROQ_API_KEY this container
does not have. So `--live` sends the same assembled request twice — once as
the code sends it today, once with an explicit `max_completion_tokens` — and
prints Groq's own `x-ratelimit-*` headers for each, which report what was
actually charged. Run it where a key exists:

    GROQ_API_KEY=... uv run python scripts/measure_natal_request.py --live

It sends exactly two requests to one fixture, so it costs about 16,000 tokens
of the 200,000 daily budget. Do not point it at the whole fixture set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import cache, llm  # noqa: E402
from astro_ai.chart import (  # noqa: E402
    compute_chart,
    compute_dasha_state,
    compute_life_chapters,
    compute_vedic_flags,
)

FIXTURES = REPO_ROOT / "tests" / "kundali-qa-fixtures.json"
PROMPT = REPO_ROOT / "src" / "astro_ai" / "prompts" / "natal.txt"

# Groq free tier, per model. Both chain entries (groq120, groq20) carry this
# same cap, which is why falling through the chain cannot fix a 413.
TPM_CEILING = 8_000

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("o200k_base")
except Exception as exc:  # pragma: no cover - reported, not raised
    _ENC = None
    _ENC_ERR = exc


def bpe(text: str) -> int | None:
    return None if _ENC is None else len(_ENC.encode(text))


def build(fixture: dict, lang: str = "en") -> tuple[str, str]:
    """The exact (system, user) pair `generate_reading` would send."""
    chart = compute_chart(
        fixture["birth_date"], fixture["birth_time"], fixture["birth_place"]
    )
    details = llm.BirthDetails(
        name=fixture.get("name", ""),
        birth_date=fixture["birth_date"],
        birth_time=fixture["birth_time"],
        birth_place=fixture["birth_place"],
    )
    return (
        llm._system_prompt(PROMPT, lang),
        llm._format_seeker_message(
            details,
            chart,
            compute_vedic_flags(chart),
            compute_life_chapters(chart),
            compute_dasha_state(chart),
        ),
    )


def live_completion_probe(fixture_key: str, cap: int) -> int:
    """Send the same request twice and print what Groq says it charged.

    Column to read is `x-ratelimit-remaining-tokens` before and after: the
    difference IS what the request cost against the 8,000 TPM bucket. If the
    two calls cost the same, the completion reservation is not being charged
    and capping it buys nothing. If the uncapped call costs materially more,
    it is, and a cap is worth its truncation risk.
    """
    import os

    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set — the live probe needs a real key.")
        print("Everything above is static and needs no key.")
        return 2

    from openai import OpenAI

    fixtures = json.loads(FIXTURES.read_text())
    system, user = build(fixtures[fixture_key])
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"]
    )
    print(f"\nlive completion-reservation probe on '{fixture_key}'")
    print("two calls to openai/gpt-oss-120b, ~8k tokens each\n")
    for label, extra in (
        ("as we send it today (no cap)", {}),
        (f"with max_completion_tokens={cap:,}", {"max_completion_tokens": cap}),
    ):
        try:
            resp = client.chat.completions.with_raw_response.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                reasoning_effort="low",
                **extra,
            )
        except Exception as exc:
            print(f"  {label}: FAILED — {type(exc).__name__}: {exc}")
            continue
        h = resp.headers
        parsed = resp.parse()
        usage = parsed.usage
        print(f"  {label}")
        print(f"    usage: prompt={usage.prompt_tokens:,} "
              f"completion={usage.completion_tokens:,} total={usage.total_tokens:,}")
        for key in ("x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                    "x-ratelimit-reset-tokens"):
            if key in h:
                print(f"    {key}: {h[key]}")
    print("\nCompare the remaining-tokens drop between the two calls. Equal drop =>")
    print("the reservation is not charged and a cap buys nothing; a materially")
    print("smaller drop on the capped call => it is, and a cap is worth considering.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--compare",
        type=Path,
        help="a second natal.txt (e.g. the pre-compression snapshot) to measure "
        "the same charts against, so the saving is a measurement not a claim",
    )
    ap.add_argument("--lang", default="en", help="en or hi (hi appends a suffix)")
    ap.add_argument(
        "--live",
        action="store_true",
        help="after the static table, send two real Groq calls to settle whether "
        "the completion reservation is charged against TPM. Needs GROQ_API_KEY "
        "and spends ~16k of the 200k daily budget.",
    )
    ap.add_argument("--live-fixture", default="manglik-uncancelled",
                    help="which fixture --live sends (default: the smallest)")
    ap.add_argument("--live-cap", type=int, default=2500,
                    help="max_completion_tokens for the capped call. 2,500 is "
                    "above the 1,380-word ceiling natal.txt sets, so a reading "
                    "that obeys the prompt cannot be truncated by it.")
    args = ap.parse_args()

    if _ENC is None:
        print(f"tiktoken unavailable ({_ENC_ERR}); the BPE column will be blank.")
        print("It is a dev dependency: uv sync --dev\n")

    fixtures = {
        k: v for k, v in json.loads(FIXTURES.read_text()).items() if not k.startswith("_")
    }
    old_prompt = args.compare.read_text(encoding="utf-8") if args.compare else None

    print(f"natal request size, lang={args.lang}, ceiling {TPM_CEILING:,} TPM per model")
    print(f"prompt: {PROMPT.relative_to(REPO_ROOT)}  {len(PROMPT.read_bytes()):,} B")
    if old_prompt is not None:
        print(f"vs    : {args.compare}  {len(old_prompt.encode()):,} B")
    print()
    head = f"{'fixture':<30}{'sys':>7}{'user':>7}{'total':>8}{'headroom':>10}"
    if old_prompt is not None:
        head += f"{'was':>8}{'saved':>8}"
    head += f"{'est_tok':>9}{'/3.6':>8}"
    print(head)
    print("-" * len(head))

    worst_user = 0
    rows = 0
    for key, fx in sorted(fixtures.items()):
        try:
            system, user = build(fx, args.lang)
        except Exception as exc:
            print(f"{key:<30}  SKIPPED: {type(exc).__name__}: {exc}")
            continue
        s_tok, u_tok = bpe(system), bpe(user)
        if s_tok is None:
            s_tok = round(len(system) / 3.6)
            u_tok = round(len(user) / 3.6)
        total = s_tok + u_tok
        worst_user = max(worst_user, u_tok)
        rows += 1
        line = (
            f"{key:<30}{s_tok:>7,}{u_tok:>7,}{total:>8,}"
            f"{TPM_CEILING - total:>10,}"
        )
        if old_prompt is not None:
            was_sys = bpe(old_prompt) or round(len(old_prompt) / 3.6)
            line += f"{was_sys + u_tok:>8,}{was_sys - s_tok:>8,}"
        line += (
            f"{cache.estimate_tokens(system + user):>9,}"
            f"{round(len(system + user) / 3.6):>8,}"
        )
        print(line)

    if not rows:
        print("\nno fixtures measured")
        return 1

    system, _ = build(next(iter(fixtures.values())), args.lang)
    s_tok = bpe(system) or round(len(system) / 3.6)
    print()
    print(f"System prompt is {s_tok:,} tok on every request — it does not vary by chart.")
    print(f"Largest chart payload measured: {worst_user:,} tok.")
    print(f"Worst case therefore {s_tok + worst_user:,} tok against a {TPM_CEILING:,} "
          f"ceiling ({TPM_CEILING - s_tok - worst_user:+,}).")
    print()
    print("Caveats, so the numbers are not over-read:")
    print("  * o200k_base is a PROXY for the o200k_harmony encoding gpt-oss-120b")
    print("    uses. Expect a percent or two of drift, not exactness.")
    print("  * This counts the two messages only. Groq's accounting also charges")
    print("    the chat-template scaffolding and whatever completion it reserves,")
    print("    so the real 'Requested' figure sits ABOVE the total column.")
    if args.live:
        return live_completion_probe(args.live_fixture, args.live_cap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
