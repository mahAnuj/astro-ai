#!/usr/bin/env python3
r"""Prove `scripts/verify_natal_prompt.py` can actually go red.

A gate written at the same time as the change it guards has only ever seen
one input, and a green run tells you nothing about whether it would catch the
loss it exists to catch. That is not hypothetical here: two behaviour tests in
this repo reimplemented their own logic inside the test body and would have
passed forever (see `scripts/mutate_behaviour_suite.py`).

`verify_natal_prompt.py` is a checklist of rules that must still be stated in
`prompts/natal.txt`. The failure it guards against is a compression pass
quietly folding away a rule. So the mutation is exactly that: delete the text
one anchor matches, and require the gate to name THAT rule.

Two things are asserted per mutation, and the second matters as much as the
first:

  1. the mutated prompt FAILS Gate 2, and
  2. the failure names the mutated rule — not some other rule that happened to
     share a word. An anchor that only ever fails alongside its neighbours is
     not testing anything of its own.

The mutation erases EVERY occurrence of an anchor, not the first. Erasing only
the first tests whether the anchor phrase is unique in the file, which is a
different and much weaker question — the first version of this script did
that and reported 43 "misses" for anchors like `Mahadasha` and `Sade Sati`
that legitimately appear several times.

A CONTROL run with the file untouched must report `OK (correctly missed)`. If
the control fails, every result below is noise.

The closing COVERAGE report answers the question that actually matters before
a compression pass: deleting which lines of the prompt would the gate NOT
notice? Those lines are unprotected. Most of them are unprotected on purpose —
they are elaboration, examples and rationale, which is exactly the material a
compression pass is supposed to be free to remove. It is a map of what is safe
to cut, not a list of defects, so it does not affect the exit code. Read it
before editing the prompt, and if a line you consider load-bearing shows up
there, that rule needs an anchor.

Runs in-process against the real prompt file; writes nothing.

    uv run python scripts/mutate_natal_prompt_gate.py
"""
from __future__ import annotations

import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_natal_prompt as gate  # noqa: E402


def rules_reported(text: str) -> set[str]:
    """Rule ids Gate 2 complains about for this text."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        gate.gate_2_rules(text)
    return set(re.findall(r"FAIL  ([a-z0-9-]+): missing", buf.getvalue()))


def anything_reported(text: str) -> set[str]:
    """Gate 1 and Gate 2 together — what the whole gate would complain about.

    The coverage sweep has to ask both. The `## ` heading lines are guarded by
    Gate 1 and by nothing in Gate 2, so a Gate-2-only sweep reports the seven
    most load-bearing lines in the file as unprotected.
    """
    buf = io.StringIO()
    with redirect_stdout(buf):
        headings_ok = gate.gate_1_headings(text)
    return rules_reported(text) | (set() if headings_ok else {"seven-headings"})


def main() -> int:
    original = gate.PROMPT.read_text(encoding="utf-8")

    print("CONTROL (unmutated prompt)")
    control = rules_reported(original)
    if control:
        print(f"  BLIND — gate already fails on the real file: {sorted(control)}")
        print("  Every result below is meaningless. Fix the gate first.")
        return 1
    print("  OK (correctly missed)\n")

    caught = missed = 0
    imprecise: list[str] = []
    for rule in gate.RULES:
        for anchor in rule.anchors:
            if not re.search(anchor, original):  # CONTROL already covers this
                continue
            mutated = re.sub(anchor, "", original)
            reported = rules_reported(mutated)
            if rule.rule_id not in reported:
                missed += 1
                print(f"  MISSED  {rule.rule_id}  erasing /{anchor}/ went unnoticed")
                continue
            caught += 1
            collateral = reported - {rule.rule_id}
            if collateral:
                imprecise.append(
                    f"{rule.rule_id} <- {anchor!r} also tripped {sorted(collateral)}"
                )
        for line_pat, tokens in rule.scoped:
            m = re.search(line_pat, original, flags=re.MULTILINE)
            if m is None:
                continue
            span = m.group(0)
            for token in tokens:
                # every occurrence WITHIN the span, so the mutation is "this
                # entry is gone from the list" and not "one of its mentions is"
                mutated = original.replace(span, span.replace(token, ""), 1)
                if rule.rule_id in rules_reported(mutated):
                    caught += 1
                else:
                    missed += 1
                    print(f"  MISSED  {rule.rule_id}  dropping {token!r} from the "
                          f"list went unnoticed")

    # Gate 5 is the opposite shape: it forbids text rather than requiring it, so
    # the mutation is INSERTION. Each retired claim, appended to the real
    # prompt, must turn Gate 5 red; the unmutated control must be green.
    # Several spellings per pattern: QA round 1 found "service to outsiders"
    # slipping past a literal "serve outsiders", so each pattern is tried with
    # the variants it exists to catch, not just one sample.
    samples = {  # literals each pattern must catch; default is the pattern itself
        r"red[- ]lentils?|masoor|masur": ("red-lentil", "red lentils", "masur dal", "masoor"),
        r"Surya[- ]?Namaskar|Sun[- ]salutation": ("Surya Namaskar", "Suryanamaskar", "Sun salutation"),
        r"sesame[- ]oil|(?:\btil|teel)[- ]oil": ("sesame-oil", "sesame oil", "til oil"),
        r"black[- ]sesame": ("black-sesame", "black sesame"),
        r"(?:serv(?:e|es|ing|ice)|support(?:ing)?|help(?:ing)?)(?:\s+to)?\s+(?:the\s+)?(?:outsiders|marginali[sz]ed)":
            ("serve outsiders", "service to outsiders", "serving the marginalised", "support outsiders"),
    }
    for pattern, _why in gate.FORBIDDEN:
        for sample in samples.get(pattern, (pattern,)):
            buf = io.StringIO()
            with redirect_stdout(buf):
                green = gate.gate_5_no_retired_claims(original)
                mutant_ok = gate.gate_5_no_retired_claims(original + "\n" + sample + "\n")
            if green and not mutant_ok:
                caught += 1
            else:
                missed += 1
                print(f"  MISSED  retired-claim  /{pattern}/ with {sample!r} (control "
                      f"green={green}, mutant went red={not mutant_ok})")

    # Gate 6 is the same insertion shape, applied to the topic summaries. The
    # mutation re-inserts a retired claim into ONE real summary and requires the
    # gate to go red AND to name that slug - a gate that fails without saying
    # where is a gate nobody can act on. Variant rows go into the very article
    # that shipped the variant (rahu-remedies, chandra-moon-remedies), because
    # that is where a regression would reappear.
    from astro_ai.learn_registry import ARTICLES

    real = [(a.slug, a.llm_summary) for a in ARTICLES if a.llm_summary]
    buf = io.StringIO()
    with redirect_stdout(buf):
        control6 = gate.gate_6_no_retired_claims_in_summaries(real)
    if not control6:
        print("  BLIND — Gate 6 already fails on the real registry:")
        print(buf.getvalue())
        return 1
    summary_samples = {  # (slug to inject into or None for the first, literal)
        r"red[- ]lentils?|masoor|masur": (("mars-remedies", "red-lentil Sunday charity"),
                                          (None, "red masur dal charity")),
        r"Surya[- ]?Namaskar|Sun[- ]salutation": (("surya-sun-remedies", "Surya Namaskar 12 rounds"),
                                                 (None, "Sun salutation at sunrise")),
        r"sesame[- ]oil|(?:\btil|teel)[- ]oil": (("ketu-remedies", "sesame oil, grey clothes"),
                                                 (None, "til oil charity")),
        r"black[- ]sesame": ((None, "black-sesame seeds"),),
        r"(?:serv(?:e|es|ing|ice)|support(?:ing)?|help(?:ing)?)(?:\s+to)?\s+(?:the\s+)?(?:outsiders|marginali[sz]ed)":
            (("rahu-remedies", "(2) service to outsiders/marginalised/animals"),
             (None, "serve outsiders"), (None, "support the marginalized")),
        gate.MILK_TO_SHIVA: (("chandra-moon-remedies", "Monday milk offering to Lord Shiva"),
                             (None, "milk offering to Shiva"), (None, "milk abhishek of Shiva"),
                             (None, "offer milk to Shivling")),
        r"(?:Hanuman|Bajrang\w*|Maruti|Anjaneya)[^\n]{0,60}(?:Shani|Saturn|Saturday|Sade[- ]Sati)"
        r"|(?:Shani|Saturn|Saturday|Sade[- ]Sati)[^\n]{0,60}(?:Hanuman|Bajrang\w*|Maruti|Anjaneya)":
            ((None, "Hanuman is the classical intercessor with Shani"),
             ("sade-sati", "Hanuman Chalisa Saturdays"), (None, "Bajrangbali for Sade Sati")),
        r"confirmation in D-?9|Raja Yoga confirmation":
            (("gajakesari-yoga", "Confirmation in D-9 Navamsha strengthens the effect"),),
    }
    first = real[0][0]
    for pattern, _why in gate.SUMMARY_FORBIDDEN:
        for target, sample in summary_samples.get(pattern, ((None, pattern),)):
            target = target or first
            mutated = [(slug, text + ("\n• " + sample if slug == target else ""))
                       for slug, text in real]
            buf = io.StringIO()
            with redirect_stdout(buf):
                mutant_ok = gate.gate_6_no_retired_claims_in_summaries(mutated)
            if not mutant_ok and f"{target}: /{pattern}/" in buf.getvalue():
                caught += 1
            else:
                missed += 1
                print(f"  MISSED  summary-claim  /{pattern}/ with {sample!r} in {target} "
                      f"(went red={not mutant_ok}, named {target}={f'{target}:' in buf.getvalue()})")

    # Legal text must stay legal, or the widened patterns are just a louder
    # false positive: Hanuman as a MARS deity (Table 78) and the Kaal Sarp
    # Nag Panchami serpent milk, which is not the retired Moon -> Shiva claim.
    for target, legal in (
        ("mars-remedies", "Mars deities: Hanuman, Rudra, Kartikeya"),
        ("kaal-sarp-dosh-remedies", "Nag Panchami (fast + serpent milk offering), Monday Shiva worship + milk abhishek"),
    ):
        mutated = [(slug, text + ("\n• " + legal if slug == target else "")) for slug, text in real]
        with redirect_stdout(io.StringIO()):
            still_green = gate.gate_6_no_retired_claims_in_summaries(mutated)
        if still_green:
            caught += 1
        else:
            missed += 1
            print(f"  MISSED  summary-claim  legal text wrongly forbidden: {legal!r}")

    lines = original.splitlines(keepends=True)
    unprotected = [
        i
        for i, line in enumerate(lines)
        if line.strip() and not anything_reported("".join(lines[:i] + lines[i + 1 :]))
    ]

    print(f"\n{caught} mutations caught, {missed} missed")
    print(f"\nCOVERAGE: {len(lines) - len(unprotected)}/{len(lines)} lines are anchored "
          f"— deleting any one of them turns the gate red.")
    if unprotected:
        print(f"{len(unprotected)} lines are NOT anchored (elaboration and examples, "
              f"free to compress):")
        for i in unprotected:
            print(f"  L{i + 1:>4}  {lines[i].strip()[:88]}")
    if imprecise:
        print("\nCollateral (a mutation that also tripped other rules — the gate still")
        print("named the right one, but the anchors overlap):")
        for line in imprecise:
            print(f"  {line}")
    if missed:
        print("\nFAIL — the gate cannot see some of the rules it claims to guard.")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
