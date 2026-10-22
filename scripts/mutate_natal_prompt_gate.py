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


# ----------------------------------------------------------------------------
# Gate 7 mutation rows
# ----------------------------------------------------------------------------

# family letter -> spellings that must each turn the gate red. The first entry
# of each family is the literal that was actually found on a page.
GATE7_SAMPLES = {
    "A": ("Donate red lentils on Sundays", "red-lentil charity", "Red Lentils (masoor dal)",
          "masur dal", "masoor", "Red  Lentil", "मसूर की दाल का दान"),
    "B": ("Milk offering to Shiva on Mondays", "milk abhishek of Lord Shiva",
          "offer milk to Shivling", "pour milk over a Shivalinga", "offer white flowers or milk at Shiva temples",
          "water/milk offerings to Shiva", "milk (abhishek) to the Shivalinga",
          "Moon is a deep devotee of Shiva", "Moon (Chandra) Remedies: Shiva Puja", "Moon → Shiva",
          "Shiva abhishek every Monday with cow milk"),
    "C": ("Hanuman is the only deity classical texts say can intercede with Shani",
          "Saturn → Hanuman", "Hanuman Chalisa on Saturdays", "Bajrangbali for Sade Sati",
          "Hanuman is Shani's protector", "Daily Hanuman worship to ease Saturn",
          "Maruti worship, especially on Saturday", "हनुमान चालीसा का शनिवार को पाठ",
          # the first run's window stopped at a full stop and missed both of these
          "Hanuman Chalisa is a 40-verse hymn. Recited daily, especially Tuesdays and Saturdays.",
          "Any priest selling a Shani nivaran puja is selling anxiety. Mantras + Chalisa + Hanuman worship cost nothing.",
          "हनुमान चालीसा एक स्तोत्र है। इसे शनिवार को पढ़ें।"),
    "D": ("Donate blankets, sesame oil, or grey cloth", "sesame-oil lamp", "Sesame  Oil", "til oil",
          "teel-oil", "Til ka tel", "gingelly oil", "तिल का तेल"),
    "E": ("Serve outsiders", "service to outsiders", "serving the marginalised",
          "support the marginalized", "helping outsiders", "donate to lepers or the marginalised",
          "feed unusual/marginalised people", "monthly serving of marginalised communities",
          # The verbatim string this slice was filed about, which reinstated GREEN
          # under the old noun list -- QA round 2 pasted it back and the whole
          # sweep passed. The nouns, not the verbs, were the gap.
          "Offer to lepers, outcasts, or homeless on Saturday sunset.",
          "Donations to leper colonies are classical Saturn remedies",
          "serve the outcastes on a Saturday"),
    # F. Introduced by this slice while retiring family C: Vishnu is Saturn's
    # deity (Table 7.1) and that part is right, but a HYMN was then named as the
    # practice and RANKED, in nine reader-facing places. One sentence apart is
    # the boundary: the hymn may be named for the 10th house or for Mercury and
    # Jupiter, whose deity Vishnu genuinely is.
    "F": ("the Vishnu Sahasranama is the most universal Saturn practice",
          "Saturn's classical deity (with Brahma) - the Vishnu Sahasranama is a good daily practice",
          "the Vishnu Sahasranama is the universal practice for Shani",
          "Vishnu Sahasranama recitation eases Sade Sati",
          "Daily Sahasranama on Saturdays",
          "recite the Sahasranama through a hard Saturn period",
          # QA round 4: both of these escaped family F. "Sahasranam" without
          # the trailing -a is the commoner Indian spelling, and the Hindi
          # surface is the one with no native reader to catch a reinstatement.
          "Daily Sahasranam for Shani",
          "शनि के लिए विष्णु सहस्रनाम का पाठ"),
    # G. A reader-facing remedy line borrowing a source name -- and the wrong
    # one. The same construction survived on a second page after the first was
    # fixed, because nothing checked for it.
    "G": ("Mars's classical grain per BPHS remedial tradition",
          "Rahu's classical grain per BPHS remedial tradition",
          "Saturn's grain per Parashara remedial tradition",
          "the classical grain per Saravali",
          "Toor daal is Mars's classical grain per Rao's remedial tradition",
          # QA round 4: one article before the source name escaped the construction.
          "Mars's classical grain per the BPHS remedial tradition"),
    # H. Surya Namaskar (slice 4). The two literals the old Gate 5 row knew
    # ("Surya Namaskar", "Sun salutation") are the FIRST two; the rest are the
    # spellings it could not see, written before the pattern was, and the tree
    # held one of them already ("the classical Sun Namaskar"). #467.
    "H": ("Surya Namaskar at sunrise, twelve rounds facing east",
          "Practise Sun salutations daily", "the classical Sun Namaskar in the morning",
          "Suryanamaskar", "Surya-Namaskar", "SURYA NAMASKAR", "Surya  Namaskar", "Surya\nNamaskar",
          "Surya Namaskara", "Surya Namaskaar", "Surya Namaskaram", "Surya Namashkar",
          "Surya Namskar", "S\u016brya Namask\u0101ra", "Soorya Namaskar", "Sun Namaskar",
          "Aditya Namaskar", "Sun-salutation", "Sun Salutation sequence",
          "Namaskar to the rising Sun", "Namaskar of Surya", "a daily namaskar at sunrise",
          "Namaskar facing east, three rounds", "12 rounds daily", "twelve postures with a mantra each",
          "12-round sunrise practice", "a sun salute each morning", "Salute the rising Sun",
          "Suriya Namaskar", "12 Aditya rounds",
          "सूर्य नमस्कार", "सूर्यनमस्कार", "सूर्य-नमस्कार", "सुर्य नमस्कार", "सूरज नमस्कार",
          "रोज़ सूर्य नमस्कर करें"),
    # I. "(per Parashara's grid)": a rule lent a source's name. Every variant here
    # keeps the construction and moves the article, the possessive, the verb or
    # the noun, which is how the first G patterns were walked around.
    "I": ("natural friends (per Parashara's grid), full 5 points",
          "per the Parashara grid", "per Parashara", "as per Parashara's table",
          "according to Parashara", "according to Parashara's scoring", "as given by Parashara",
          "as laid down by Parashara", "per Parashari rules", "per Parasara's tables",
          "per Brihat Parashara Hora Shastra", "following Parashara's scheme",
          "using Parashara's grid", "Parashara's grid", "the Parashara grid", "per BPHS grid",
          "per the BPHS table", "per BPHS's grid", "BPHS grid", "the grid from Parashara",
          "as per the Parashar grid", "(per Parashara\u2019s grid)", "Parashara's friendship grid says",
          "Parashara-grid", "as per Sage Parashara", "according to Maharishi Parashara",
          "as per the classical Parashara",
          "पराशर के अनुसार पाँच अंक", "पराशर जी के अनुसार", "पाराशर ग्रिड के अनुसार"),
}

# Text that must stay green. Hanuman as a MARS deity, the correct per-planet
# tables, Shiva as the Sun's deity, and the Kaal Sarp practices (a different,
# out-of-slice practice - not Moon -> Shiva) are all legal.
GATE7_LEGAL = (
    "Mars deities: Hanuman, Rudra, Kartikeya", "Hanuman Chalisa daily, especially on Tuesdays",
    "Sun → Shiva or Rama; Moon → Devi; Mars → Hanuman or Kartikeya; Saturn → Vishnu or Brahma",
    "Sun → Shiva, Moon → Devi, Mars → Hanuman, Saturn → Vishnu",
    "Moon → Devi, Sun → Shiva", "Shiva is the Sun's deity, not the Moon's.",
    "Nag Panchami (fast + serpent milk offering), Monday Shiva worship + milk abhishek",
    "Shiva holds the crescent Moon on his forehead.",
    "Saturn rules: discipline, the elderly, the marginalised, hard-won wisdom.",
    "Mars → Hanuman or Kartikeya, Saturn → Vishnu or Brahma, Rahu → Durga.",
    "Hanuman Chalisa is a 40-verse hymn. Recited daily, especially on Tuesdays.",
    "Donate toor daal (dark yellow lentil) on Tuesdays; wheat on Sundays; rice on Mondays.",
    "Donate black sesame, mustard oil and iron to the elderly on Saturdays.",
    # F must not fire on the hymn where Vishnu IS the deity, nor across a
    # sentence boundary. Both of these are live in the tree and correct.
    "For Saturn delays: Shani chalisa, Saturday oil-lamp, service to elderly/poor. "
    "For general 10th house strengthening: Vishnu Sahasranama, worship of your ishta devata.",
    "Because Vishnu is one of Mercury's ruling deities, the Vishnu Sahasranama is a "
    "safe universal Mercury remedy.",
    "For deeper practice, add the Guru Chalisa or Vishnu Sahasranama (Vishnu being "
    "Jupiter's ruling deity).",
    # E must not fire on an ancestral rite, which is not Rahu's family at all --
    # the first draft of the widened nouns did, on pitru-dosh-remedies.html.
    "Feed one Brahmin or one homeless person",
    # ...nor on Saturn's own sourced deed, which names the people it serves.
    # This is the sentence AS SHIPPED. It ended "and serve the elderly" until
    # bb4ccd2: remedies.md 11.2 records that clause as a product addition, not
    # Rao's, so a fixture carrying it would pin the overclaim this slice removed
    # as legal, under a comment calling it sourced. Keep it matching the tree.
    "Saturn's classical good deed is labour itself: perform some physical labour, "
    "help people who live on manual labour.",
    # G is a construction, not a ban on source names: these must stay green.
    "Cheiro's Book of Numbers gives 4 to Rahu.",
    "Rao's Table 78 maps Saturn to Vishnu and Brahma.",
    "Per Johari, the reduction differs.",
    # H and I are constructions, not bans on a word. "Guru Namaskar" is a different
    # practice this slice did not retire (numerology.py, Jupiter's puja); a Hindi
    # greeting and the Sun's own shloka are not the retired practice; and a
    # Sunday sunrise offering is Arghya, which is still on the pages.
    "Guru Namaskar; offer yellow flowers + jaggery to Vishnu", "Namaskar! Welcome to Shubh Bhagya.",
    "नमस्कार, आपका स्वागत है।", "Om Suryaya Namah - I bow to the Sun.",
    "Salutations to Surya, the source of all life and clarity.",
    "Offer arghya (water with red flowers) at sunrise; recite the Aditya Hridaya Stotra on Sunday.",
    "Visit a temple, donate to one, or help with its running (the Sun's classical good deed).",
    "Parashara is the author of Brihat Parashara Hora Shastra.",
    "Per Johari, the grid differs from the one Cheiro published.",
    "The friendship grid scores the two Moon-sign lords.",
    "A 12-month plan, in 3 rounds of review.",
)

# The one honest Hanuman-Saturn sentence a page may keep: it must say popular/folk
# AND name Mars. Each half, removed, must turn the gate red.
_HONEST = ("Many people recite the Hanuman Chalisa on Saturdays through a hard Saturn period; "
           "that is a popular tradition, not a classical Saturn assignment. The classical road "
           "to Hanuman runs through Mars carrying Saturnine influence.")


def gate7_mutations() -> tuple[int, int]:
    caught = missed = 0
    real = gate.reader_surface_units()
    with redirect_stdout(io.StringIO()):
        control = gate.gate_7_no_retired_claims_on_reader_surfaces(real)
    if not control:
        print("  BLIND — Gate 7 already fails on the real tree:")
        gate.gate_7_no_retired_claims_on_reader_surfaces(real)
        return 0, 1

    # Small, real baseline: the longest unit of each required surface. Running
    # the whole 5,000-unit tree once per mutation would take minutes.
    base: dict[str, tuple[str, str]] = {}
    for surface in gate._REQUIRED_SURFACES:
        cands = [(w, t) for w, t in real if w.startswith(surface)]
        base[surface] = max(cands, key=lambda wt: len(wt[1]))

    def run(units):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ok = gate.gate_7_no_retired_claims_on_reader_surfaces(units)
        return ok, buf.getvalue()

    def inject(surface: str, sample: str):
        units = []
        for s, (w, t) in base.items():
            units.append((w, t + ("\n" + sample + "\n" if s == surface else "")))
        return units, base[surface][0].rpartition(":")[0]

    # Hindi copies live in i18n.py (and a Devanagari sample in a template is
    # meaningless), so Devanagari samples are only injected into i18n.
    for family, samples in GATE7_SAMPLES.items():
        for sample in samples:
            for surface in gate._REQUIRED_SURFACES:
                if re.search("[ऀ-ॿ]", sample) and surface != "i18n.py":
                    continue
                units, fname = inject(surface, sample)
                ok, out = run(units)
                if (not ok) and f"{fname}:" in out:
                    caught += 1
                else:
                    missed += 1
                    print(f"  MISSED  reader-claim {family}  {sample!r} in {surface} "
                          f"(went red={not ok}, named {fname}={f'{fname}:' in out})")

    for legal in GATE7_LEGAL:
        for surface in gate._REQUIRED_SURFACES:
            units, _ = inject(surface, legal)
            if run(units)[0]:
                caught += 1
            else:
                missed += 1
                print(f"  MISSED  reader-claim  legal text wrongly forbidden in {surface}: {legal!r}")

    # The honest sentence stays green with both labels, red when either is cut.
    for label, sentence, want_green in (
        ("labelled", _HONEST, True),
        ("no 'popular'", _HONEST.replace("popular", "widespread"), False),
        ("no Mars", _HONEST.replace("Mars", "Venus"), False),
    ):
        units, _ = inject("templates/learn/", sentence)
        if run(units)[0] == want_green:
            caught += 1
        else:
            missed += 1
            print(f"  MISSED  reader-claim C  honest sentence ({label}) expected "
                  f"{'green' if want_green else 'red'}")

    # A gate that checks nothing must fail: no units, a lone surface, a tree with
    # no files, and a tree whose files exist but hold no text.
    import tempfile

    stubs = {"no units": [], "templates only": [u for u in real if u[0].startswith("templates/")]}
    with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as hollow:
        stubs["empty tree"] = gate.reader_surface_units(Path(empty))
        (Path(hollow) / "templates" / "learn").mkdir(parents=True)
        (Path(hollow) / "templates" / "learn" / "x.html").write_text("")
        for name in ("i18n.py", "numerology.py", "learn_registry.py"):
            (Path(hollow) / name).write_text("")
        stubs["hollow tree"] = gate.reader_surface_units(Path(hollow))
    for label, units in stubs.items():
        if not run(units)[0]:
            caught += 1
        else:
            missed += 1
            print(f"  MISSED  reader-claim  a stub ({label}) with nothing to scan PASSED")

    # Every family in the gate has samples here, so a sixth family cannot be added
    # to READER_FORBIDDEN without a row proving it.
    if len(gate.READER_FORBIDDEN) == len(GATE7_SAMPLES):
        caught += 1
    else:
        missed += 1
        print(f"  MISSED  reader-claim  {len(gate.READER_FORBIDDEN)} families in the gate, "
              f"{len(GATE7_SAMPLES)} with mutation samples")
    return caught, missed


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
        gate.SURYA_NAMASKAR: ("Surya Namaskar", "Suryanamaskar", "Sun salutation", "Sun Namaskar",
                              "Surya Namaskaram", "Soorya Namaskar", "12 rounds at sunrise",
                              "सूर्य नमस्कार"),
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
        gate.SURYA_NAMASKAR: (("surya-sun-remedies", "Surya Namaskar 12 rounds"),
                              (None, "Sun salutation at sunrise"), (None, "the classical Sun Namaskar"),
                              (None, "Suryanamaskaram daily"), (None, "सूर्य नमस्कार")),
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

    # Gate 7 scans the pages a reader opens directly. Same insertion shape: a
    # retired claim is injected into ONE real unit of each surface (a template,
    # the registry's FAQ/SEO strings, i18n, numerology) and the gate must go red
    # AND name that file - a gate that fails without saying where is a gate
    # nobody can act on. Several spellings per family, because QA found 17 of 38
    # variants slipping past the first Gate 5 patterns.
    c7, m7 = gate7_mutations()
    caught += c7
    missed += m7

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
