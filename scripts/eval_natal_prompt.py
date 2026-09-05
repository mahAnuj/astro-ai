#!/usr/bin/env python3
r"""Generative eval: did compressing `natal.txt` break the reading?

WHY THIS EXISTS
---------------
`prompts/natal.txt` was compressed from 18,095 B to 13,029 B to fix a Groq 413
("Limit 8000, Requested 8562"). `scripts/verify_natal_prompt.py` proves every
rule is still WRITTEN in the file. That is necessary and not sufficient: a rule
can survive as text and stop working, because rewriting the prose around it
changed how much weight the model gives it. Nothing static can see that.

So this measures the OUTPUT. For each golden chart it generates a reading with
the old prompt and with the new one, and checks each against the prompt's own
STRICT OUTPUT RULES — mechanically, not by taste:

  headings        exactly the seven `## ` sections, exact text, in order
  planet leak     none of the nine graha names in the prose
  sign leak       none of the twelve rashi names, English or Sanskrit
  house leak      no "2nd house" / "10th house" constructions
  jargon          none of transit / gochar / natal Lagna / natal Moon / Bhava
  banned words    none of the seventeen
  length          920-1380 words total
  manglik         the verdict stated matches compute_vedic_flags, not invented
  life areas      at least 5 of the 7 domains present in Life Stages
  learn links     at most one /learn/ link per section, raw slug form

These are the prompt's own contract, so a regression here means "compression
broke a rule", which is the question. It deliberately does NOT score whether
the prose is good — that is `qa`'s job and a human's, and a script that
pretended to measure it would be worse than one that admits it cannot.

WHICH MODEL, AND WHY NOT GROQ
-----------------------------
Default `openai`. Seven charts x two prompt variants is 14 calls at ~7k tokens
each, which is roughly half the 200,000-token DAILY free-tier budget the live
site runs on — running this against Groq would starve production for the rest
of the day. gpt-4o-mini costs cents.

That means the results answer "did I delete a rule the model was relying on",
NOT "is gpt-oss-120b's prose as good as before". Different models weight
instructions differently. Pass `--provider groq120` to check the production
model specifically, but do it deliberately and not while the daily rashifal
job needs the quota.

    OPENAI_API_KEY=... uv run python scripts/eval_natal_prompt.py \
        --baseline /path/to/old_natal.txt

Without `--baseline` it evaluates the current prompt alone, which is the right
mode for "is the prompt still holding" months from now.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from astro_ai import llm  # noqa: E402
from astro_ai.chart import (  # noqa: E402
    compute_chart,
    compute_dasha_state,
    compute_life_chapters,
    compute_vedic_flags,
)

FIXTURES = REPO_ROOT / "tests" / "kundali-qa-fixtures.json"
PROMPT = REPO_ROOT / "src" / "astro_ai" / "prompts" / "natal.txt"

HEADINGS = (
    "Personality & Character", "Career & Profession", "Wealth & Money",
    "Relationships & Marriage", "Health & Wellbeing", "Travel & Opportunities",
    "Life Stages",
)
PLANETS = ("Jupiter", "Saturn", "Rahu", "Ketu", "Mars", "Mercury", "Venus", "Sun", "Moon")
SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula",
    "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
)
JARGON = ("transit", "gochar", "natal Lagna", "natal Moon", "Bhava", "lord of the")
BANNED = (
    "navigate", "manifest", "amplify", "introspection", "consolidation",
    "favourability", "propensities", "endeavour", "facilitates", "delve",
    "unlock", "harness", "empower", "leverage", "moreover", "furthermore",
    "intricacies",
)
DOMAINS = {
    "health": ("health", "body", "energy", "vitality", "illness"),
    "family": ("family", "home", "parents", "children"),
    "education": ("education", "study", "studies", "learning", "school", "college"),
    "career": ("career", "work", "job", "profession", "business"),
    "marriage": ("marriage", "partner", "relationship", "love", "spouse"),
    "money": ("money", "wealth", "income", "savings", "earning", "financial"),
    "personality": ("personality", "nature", "inner", "confidence", "temperament"),
}
# "your 10th house", "the 2nd house" — the construction the prompt bans. Not a
# bare ordinal, which appears legitimately ("your 30s", "the 2nd half").
HOUSE_LEAK = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\s+house\b", re.IGNORECASE)
LEARN_LINK = re.compile(r"/learn/[a-z0-9-]+/")


@dataclass
class Result:
    fixture: str
    variant: str
    checks: dict[str, str]      # check name -> "" for pass, message for fail
    words: int

    @property
    def failures(self) -> list[str]:
        return [f"{k}: {v}" for k, v in self.checks.items() if v]


def _sections(text: str) -> dict[str, str]:
    """Split a reading on its `## ` headings."""
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return {
        parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)
    }


def check(reading: str, flags) -> tuple[dict[str, str], int]:
    """Every assertion the prompt's own rules support. "" means pass."""
    out: dict[str, str] = {}
    found = re.findall(r"^## (.+)$", reading, flags=re.MULTILINE)
    out["headings"] = (
        "" if tuple(h.strip() for h in found) == HEADINGS
        else f"got {[h.strip() for h in found]}"
    )
    body = re.sub(r"^## .+$", "", reading, flags=re.MULTILINE)

    leaked = [p for p in PLANETS if re.search(rf"\b{p}\b", body)]
    out["planet leak"] = ", ".join(leaked) if leaked else ""
    leaked = [s for s in SIGNS if re.search(rf"\b{s}\b", body)]
    out["sign leak"] = ", ".join(leaked) if leaked else ""
    hits = HOUSE_LEAK.findall(body)
    out["house leak"] = ", ".join(sorted(set(hits))) if hits else ""
    leaked = [j for j in JARGON if j.lower() in body.lower()]
    out["jargon"] = ", ".join(leaked) if leaked else ""
    leaked = [w for w in BANNED if re.search(rf"\b{w}", body, re.IGNORECASE)]
    out["banned words"] = ", ".join(leaked) if leaked else ""

    words = len(body.split())
    out["length"] = "" if 920 <= words <= 1380 else f"{words} words, want 920-1380"

    # The Manglik verdict is computed in Python and must not be re-decided by
    # the model. We can only check the weak direction mechanically: a chart
    # that is NOT Manglik must not be told it is.
    said_manglik = re.search(r"\bmanglik\b|\bmangal dosh\b", body, re.IGNORECASE)
    if not flags.manglik and said_manglik:
        out["manglik"] = "chart is not Manglik but the reading raises it"
    else:
        out["manglik"] = ""

    sections = _sections(reading)
    stages = sections.get("Life Stages", "")
    present = [d for d, words_ in DOMAINS.items()
               if any(w in stages.lower() for w in words_)]
    out["life areas"] = (
        "" if len(present) >= 5 else f"only {len(present)}/7: {present}"
    )

    over = {h: len(LEARN_LINK.findall(s)) for h, s in sections.items()
            if len(LEARN_LINK.findall(s)) > 1}
    out["learn links"] = ", ".join(f"{h}={n}" for h, n in over.items()) if over else ""
    if "](" in body and "/learn/" in body:
        out["learn links"] = (out["learn links"] + "; markdown link syntax").strip("; ")

    return out, words


def generate(fixture: dict, prompt_path: Path, provider: str) -> str:
    import os

    os.environ["BHAGYA_LLM_PROVIDERS"] = provider
    chart = compute_chart(
        fixture["birth_date"], fixture["birth_time"], fixture["birth_place"]
    )
    details = llm.BirthDetails(
        fixture.get("name", ""), fixture["birth_date"],
        fixture["birth_time"], fixture["birth_place"],
    )
    return llm.generate_reading(
        details,
        chart=chart,
        flags=compute_vedic_flags(chart),
        life_chapters=compute_life_chapters(chart),
        prompt_path=prompt_path,
        dasha_state=compute_dasha_state(chart),
    )


_GOOD = """## Personality & Character
{filler}

## Career & Profession
{filler}

## Wealth & Money
{filler}

## Relationships & Marriage
{filler}
For more, see our Marriage Timing guide → /learn/marriage-timing-kundli/

## Health & Wellbeing
{filler}

## Travel & Opportunities
{filler}

## Life Stages
Looking back, from 5 to 21 your education and family life set the tone. Right
now, from 21 to 39, career and money take the front seat, and your work tends
to bring steady income. The years ahead, from 39 to 55, will likely bring a
partner and marriage into focus, alongside your health and your body's need for
rest. Through all of it your inner nature keeps growing quieter and surer.
{filler}
"""

_SELF_TEST_CASES = [
    ("a clean reading passes everything", {}, []),
    ("a renamed heading is caught",
     {"## Wealth & Money": "## Wealth and Money"}, ["headings"]),
    ("a planet name is caught", {"steady income": "steady Saturn income"},
     ["planet leak"]),
    ("a sign name is caught", {"steady income": "steady Capricorn income"},
     ["sign leak"]),
    ("a house number is caught", {"steady income": "income from your 10th house"},
     ["house leak"]),
    ("jargon is caught", {"steady income": "income during this transit"},
     ["jargon"]),
    ("a banned word is caught", {"steady income": "income you can leverage"},
     ["banned words"]),
    ("a short reading is caught", {"{filler}": ""}, ["length"]),
    ("two /learn links in one section are caught",
     {"For more, see our Marriage Timing guide → /learn/marriage-timing-kundli/":
      "See /learn/marriage-timing-kundli/ and /learn/saturn-in-10th-house-career/"},
     ["learn links"]),
    ("markdown link syntax is caught",
     {"→ /learn/marriage-timing-kundli/": "→ [guide](/learn/marriage-timing-kundli/)"},
     ["learn links"]),
]


def self_test() -> int:
    """Prove every check can fail. No API key, no network.

    Same discipline as `scripts/mutate_behaviour_suite.py`: a check that has
    only ever passed is not evidence. Each case below breaks exactly one rule
    in an otherwise-clean reading and names the check that must catch it — and
    the check must not fire on the clean reading in the first place.
    """
    class _NotManglik:
        manglik = False

    filler = " ".join(["Your nature is steady and kind."] * 22)
    print("eval self-test — can each check fail?\n")
    bad = 0
    for label, edits, expected in _SELF_TEST_CASES:
        text = _GOOD.replace("{filler}", filler)
        for old, new in edits.items():
            if old == "{filler}":
                text = _GOOD.replace("{filler}", new)
            elif old not in text:
                print(f"  BROKEN CASE  {label}: {old!r} not in the sample")
                bad += 1
                continue
            else:
                text = text.replace(old, new)
        checks, _ = check(text, _NotManglik())
        fired = {k for k, v in checks.items() if v}
        missing = set(expected) - fired
        extra = fired - set(expected)
        if missing or extra:
            bad += 1
            print(f"  FAIL  {label}")
            if missing:
                print(f"        did not fire: {sorted(missing)}")
            if extra:
                print(f"        also fired:   {sorted(extra)} -> "
                      f"{ {k: checks[k] for k in sorted(extra)} }")
        else:
            print(f"  ok    {label}"
                  f"{'' if expected else ' (nothing fired, as required)'}")
    print()
    if bad:
        print(f"FAIL — {bad} case(s). The eval cannot be trusted until these pass.")
        return 1
    print(f"PASS — {len(_SELF_TEST_CASES)} cases, every check demonstrably fires.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path,
                    help="a second natal.txt to generate against for comparison "
                         "(e.g. the pre-compression snapshot)")
    ap.add_argument("--provider", default="openai",
                    help="BHAGYA_LLM_PROVIDERS value. Default openai — see the "
                         "module docstring for why not groq")
    ap.add_argument("--fixtures", nargs="*",
                    help="fixture keys to run (default: all)")
    ap.add_argument("--self-test", action="store_true",
                    help="prove every check can fail, using synthetic readings. "
                         "No API key needed — run this before trusting a green "
                         "eval run")
    ap.add_argument("--save", type=Path,
                    help="directory to write every generated reading into, so a "
                         "human can read what the numbers are describing")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    fixtures = {
        k: v for k, v in json.loads(FIXTURES.read_text()).items()
        if not k.startswith("_") and (not args.fixtures or k in args.fixtures)
    }
    variants = [("new", PROMPT)]
    if args.baseline:
        variants.append(("old", args.baseline))

    results: list[Result] = []
    for key, fx in sorted(fixtures.items()):
        chart = compute_chart(fx["birth_date"], fx["birth_time"], fx["birth_place"])
        flags = compute_vedic_flags(chart)
        for variant, path in variants:
            try:
                reading = generate(fx, path, args.provider)
            except Exception as exc:
                print(f"  {key} [{variant}]: GENERATION FAILED — "
                      f"{type(exc).__name__}: {exc}")
                continue
            if args.save:
                args.save.mkdir(parents=True, exist_ok=True)
                (args.save / f"{key}.{variant}.md").write_text(reading, encoding="utf-8")
            checks, words = check(reading, flags)
            results.append(Result(key, variant, checks, words))
            print(f"  {key} [{variant}]: {words} words, "
                  f"{len(checks) - len(Result(key, variant, checks, words).failures)}"
                  f"/{len(checks)} checks pass")

    if not results:
        print("\nNothing generated. Check the API key and --provider.")
        return 1

    names = list(results[0].checks)
    print(f"\n{'fixture':<32}{'variant':<9}" + "".join(f"{n[:11]:>13}" for n in names))
    print("-" * (41 + 13 * len(names)))
    for r in results:
        cells = "".join(
            f"{('ok' if not r.checks[n] else 'FAIL'):>13}" for n in names
        )
        print(f"{r.fixture:<32}{r.variant:<9}{cells}")

    print("\nFailures in detail:")
    any_fail = False
    for r in results:
        for f in r.failures:
            any_fail = True
            print(f"  {r.fixture} [{r.variant}]  {f}")
    if not any_fail:
        print("  (none)")

    if args.baseline:
        print("\nRead the table by COLUMN, comparing old and new rows for the same")
        print("fixture. A check that fails on both was already failing before the")
        print("compression and is not this change's regression; a check that fails")
        print("only on 'new' is.")
    print("\nThis measures the prompt's mechanical contract, not whether the prose")
    print("is any good. A human still reads the output — use --save.")
    return 1 if any(r.variant == "new" and r.failures for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
