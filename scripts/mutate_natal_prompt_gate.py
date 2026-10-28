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
    # Jupiter, whose deity Vishnu genuinely is -- but NOT called universal,
    # classical, primary, powerful or safe (slice 5, #465: the first five
    # entries after the Saturn ones are the sentences actually found on the
    # Mercury and Jupiter pages, which the Saturn-only pattern let through).
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
          "शनि के लिए विष्णु सहस्रनाम का पाठ",
          "Vishnu Sahasranama is the classical universal Mercury remedy",
          "The universal safe mantra: Vishnu Sahasranama",
          "reciting the Vishnu Sahasranama is a powerful Jupiter remedy",
          "Vishnu is Mercury's ruling deity; his Sahasranama is a safe universal Mercury practice",
          "Weekly Vishnu Sahasranama recitation - Vishnu is Mercury's ruling deity; safe universal Mercury practice",
          "the Vishnu Sahasranama is one of the most powerful and universally accessible Mercury remedies",
          "Vishnu is the primary deity and the Sahasranama its primary practice",
          "Sahasranam is the classical Jupiter remedy",
          "the most reliable Mercury practice is the Vishnu Sahasranama",
          "The universal safe practice: Vishnu SAHASRANAMA",
          # PR #487 QA round 1: widening the Lalita exemption must not exempt the
          # VISHNU hymn sitting in the same sentence, or one with a hyphen.
          "The Lalita Sahasranama and the Vishnu Sahasranama are both classical practices",
          "Vishnu-Sahasranama is the universal practice",
          "the classical practice is the Lalitha Sahasranama, or failing that the Vishnu Sahasranama"),
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
    # J. A product-added remedy called classical, or ranked above ritual (#468).
    # The first three are the sentences as found; the rest move the planet, the
    # article, the hyphen and the noun, which is how earlier patterns were walked
    # around.
    "J": ("Classical Saturn-domain good deeds",
          "Saturn responds to elder-respect more than to most rituals",
          "Serving these groups is Ketu's most classically-cited karma-clearing practice.",
          "Classical Venus-domain good deeds", "Classical Mercury-domain good deeds",
          "Classical Jupiter-domain good deeds", "classical Mars-domain good deed",
          "CLASSICAL  Moon-domain  good  deeds",
          "Serving the elderly works more than most rituals",
          "Saturn rewards patience more than to most remedies",
          "it works more than most pujas",
          "Feeding crows is Saturn's most classically cited practice",
          "the most classically-cited deed for Mars",
          "his most classically cited mantra",
          # PR #487 QA round 1. The first is the sentence as found (shani-saturn);
          # the next two are saturn-remedies and the FAQ twin in learn_registry.
          "Doing right by elders pacifies Saturn faster than any temple visit.",
          "is more powerful than expensive rituals done without devotion.",
          "all four together are more effective than any expensive puja package.",
          "works faster than most rituals", "sooner than any puja", "Quicker than all remedies",
          "faster than any other temple visit", "faster than any expensive offering",
          "more potent than costly pujas", "More Powerful Than Most Expensive rituals",
          "more effective than costly remedies",
          # plural nouns, other dashes, a space instead of the dash
          "Classical Saturn\u2011domain good deeds", "Classical Saturn\u2013domain good deeds",
          "Classical Saturn domain good deeds", "Classical Saturn-domain practices",
          "classical Mars-domain remedies", "Classical Venus-domain deeds",
          "Classical  Jupiter \u2010 domain  good  deeds",
          "Ketu's most classically-cited practices", "the most classically\u2011cited deeds for Mars",
          "his most classically cited mantras"),
    # K. Graha Maitri collapsed to friend / neutral-partial / enemy-0 (slice 6). The
    # first is the sentence as found on kundali-matching-ashtakoot-guna-milan; the
    # rest move the verb, the arrow, the synonym for "partial" and for "enemies".
    "K": ("If the two Moon-sign lords are natural friends, full 5 points. If neutral, partial. If enemies, 0.",
          "If neutral, partial", "neutral: half", "Neutral \u2192 reduced", "neutral - middling",
          "NEUTRAL  medium", "neutral, in-between", "neutral = some points",
          "If enemies, 0 points", "if the lords are enemies, 0", "If they are enemies: zero",
          "When the two lords are enemy planets, nil", "if the lords are inimical then 0",
          "if hostile, 0", "If enemies \u2192 0", "If enemies = 0", "Where the lords are enemies, zero points",
          "should the lords be enemies, 0",
          "If enemies score nothing", "if enemies get no points", "If the lords are enemies they receive zero",
          "Friends 5, neutral partial, enemies 0",
          # Measured by the author's own probe of 21 rewrites before these were widened:
          # 12 of 21 escaped. Each of these was one of them.
          "Neutral lords give partial credit", "neutral gives half marks", "Enemies = 0, friends = 5",
          "enemies: 0", "If the lords are foes, 0", "If at enmity, 0", "if the lords are unfriendly, 0",
          "neutral lords: partial points", "neutral: partially", "Neutral (partial)",
          "If the lords are neutral, a partial score", "friends 5, neutrals 3, enemies 0",
          "\u092f\u0926\u093f \u0930\u093e\u0936\u0940\u0936 \u0936\u0924\u094d\u0930\u0941 \u0939\u094b\u0902 \u0924\u094b 0 \u0905\u0902\u0915"),
    # L. Rahu and Ketu "outside Parashara's grid" (slice 6). The first four are the
    # sentences as found (rahu, ketu, the-9-grahas, shani-saturn); the rest move the
    # source name, the noun, the negation and the history.
    "L": ("Not part of Parashara's natural-friendship grid",
          "Not part of the classical natural-friendship grid (Parashara's Naisargika Maitri predates "
          "Rahu's formal inclusion in the graha family)",
          "Rahu and Ketu aren't included in Parashara's natural-friendship grid because it predates their "
          "formal inclusion in the graha family. Modern practice uses ad-hoc rules for them.",
          "Rahu and Ketu are not in classical natural-friendship grids (Parashara's tables were built for "
          "the 7-planet model).",
          "Not part of BPHS's friendship table", "BPHS's natural friendship grid", "Parashara's friendship table",
          "Parasara's Naisargika Maitri", "Parashar's natural-friendship tables", "Parashari natural-friendship grid",
          "Ketu is not in the traditional natural-friendship chart",
          "Rahu isn't listed in the ancient friendship table", "Ketu was never part of the original friendship grid",
          "Rahu is excluded from the classical friendship table", "Ketu was left out of the classical grid",
          "Rahu is missing from Parashara's own table", "Rahu: outside the classical natural-friendship grid",
          "The table predates the formal inclusion of Rahu and Ketu", "it predates their inclusion in the navagraha",
          "predates their inclusion in the nine-graha system", "Rahu and Ketu came late and the table predates them",
          "Modern practice uses ad hoc rules for them", "ad-hoc assignments for Rahu", "Ketu follows ad hoc conventions",
          "Parashara's tables were built for the seven planet model", "designed for the seven-planet model",
          # 9 of 16 rewrites escaped the first version of this family; each of these was one.
          "Rahu and Ketu don't appear in the classical friendship table",
          "The grid was drawn up before Rahu and Ketu were counted",
          "Parashara's table has no Rahu or Ketu", "the classical grid does not include Rahu",
          "The table predates the nodes", "Rahu and Ketu were added later to the graha family",
          "this scheme only knew seven planets", "The original 7-planet friendship table",
          "\u092a\u0930\u093e\u0936\u0930 \u0915\u0940 \u092e\u0948\u0924\u094d\u0930\u0940 \u0924\u093e\u0932\u093f\u0915\u093e \u092e\u0947\u0902 \u0930\u093e\u0939\u0941 \u0928\u0939\u0940\u0902"),
    # M-Q: #398 slice 7. In each family the first entry is the sentence as found on a page;
    # the rest are the rewordings a copywriter reaches for (the #467 finding: a pattern
    # bound to one spelling goes green on the first rewrite).
    "M": ("Guru (Jupiter) \u2014 Mercury's natural enemy in the friendship grid",
          "Jupiter is Mercury's enemy", "Jupiter, Mercury's classical foe", "Mercury's enemy: Jupiter",
          "Mercury's sworn enemy is Jupiter", "Mercury and Jupiter are natural enemies",
          "Jupiter and Mercury are mutual foes", "Budha and Guru are natural enemies",
          "Mercury considers Jupiter an enemy", "Mercury regards Guru as hostile",
          "Brihaspati is Budha's natural enemy", "Jupiter is the natural enemy of Mercury's own friendship set: Mercury's enemy",
          "\u092c\u0941\u0927 \u0915\u093e \u0936\u0924\u094d\u0930\u0941 \u0917\u0941\u0930\u0941 \u0939\u0948 \u0936\u0924\u094d\u0930\u0941"),
    # N. The first is the heading found; the second the shipped FAQ list; the rest move the verb.
    "N": ("Vishnu worship for uncancelled Manglik",
          "If mismatch: soften with Hanuman practices + Vishnu worship + Kumbh Vivah before marriage.",
          "Classical tradition also recommends Vishnu worship for Mars", "Manglik remedy: Ekadashi vrat",
          "Mars is pacified by Satya Narayan Katha on Purnima", "Recite the Vishnu Sahasranama to soften Manglik",
          "For Manglik Dosh, Narayana puja every Ekadashi", "Kumbh Vivah and Vishnu worship",
          "Vishnu puja is a Mars remedy", "Manglik: observe the Ekadashi fast", "Vishnu worship, then Kumbh Vivah",
          "Mars Dosh \u2014 Vishnu mantra daily"),
    # O. Headings, openers and rank words for Monday Shiva as the Kaal Sarp remedy.
    "O": ("1. Shiva worship on Mondays",
          "Any KSD remedy begins with Shiva worship.",
          "weekly Monday Shiva visits are the most accessible starting point",
          "Monday Shiva worship is the first Kaal Sarp remedy", "Shiva puja on Mondays is the primary remedy",
          "Start with Shiva worship for Kaal Sarp", "Kaal Sarp remedies begin with Shiva puja",
          "The classical Monday Shiva remedy", "Shiva worship every Monday is essential",
          "(1) Monday Shiva worship + milk abhishek", "Shiva visits on Mondays are the foundation, the starting point",
          "Shiva is the master of serpents, so Monday Shiva puja must come first",
          "Real remedies are simple: Nag Panchami observance, Shiva worship on Mondays, silver serpent offering"),
    # P. A tradition, regional custom or count called classical.
    "P": ("Classical KSD remedy: obtain a small pair of silver serpents",
          "Nag Panchami is the classical annual serpent-worship day and KSD's peak remedial day",
          "The classical \"big remedy\" for full KSD is the Nagbali at Trimbakeshwar",
          "Every classically-valid remedy below can be done for under 2,000",
          "This guide walks the seven classically-cited remedies for Kaal Sarp Dosh",
          "Kaal Sarp Dosh = pattern\n\u2022 7 classical remedies: (1) Durga",
          "the classical Nag Panchami fast", "Trimbakeshwar is the classical answer",
          "the silver serpent pair is a classical remedy", "Nagbali is a classical practice",
          "KSD's peak remedial day is Nag Panchami", "the best Kaal Sarp remedy day",
          "Nag Panchami, a classical observance", "Nag Panchami is classical"),
    # Q. "Universal safe" claimed for a non-Venus remedy page.
    "Q": ("The universal safe fallback\n\nIf you're anxious about Saturn",
          "these universal Jupiter practices are safe for anyone", "these Mercury practices are safe for anyone",
          "these Mars practices are safe for anyone", "the safest universal practices are:",
          "Daily Hanuman Chalisa recitation \u2014 the most universally-recommended Mars-related practice",
          "Mars practice \u2014 the most universally recommended", "4. Deity propitiation (safe universal practice)",
          "Vishnu is Saturn's classical deity; safe for any chart, no consultation needed.",
          "None of these require chart consultation, none can backfire. Saturn practices",
          "Mars practices together are measurable and none can backfire",
          "The universal safe fallback for Mercury", "universal safe practice for Jupiter: ...",
          "Mars: the universal safe practice, as the pattern shows"),
    # R. A remedy page borrowing a chapter / book nobody here has checked. The first
    # four are the callouts as they stood (surya, ketu, rahu, chandra); the rest are
    # other spellings and the body-text twin ("the classically-cited ones from ...").
    "R": ("Brihat Parashara Hora Shastra (Surya adhyaya), Ramayana Yuddha Kanda (Aditya Hridaya Stotra), "
          "Surya Samhita. Sunday charity list per Muhurtha Chintamani.",
          "Brihat Parashara Hora Shastra (Ketu adhyaya), Ganesh Purana. Beej mantra from Grahashanti tradition.",
          "Brihat Parashara Hora Shastra (Rahu adhyaya), Ganesh Purana, Durga Saptashati.",
          "Brihat Parashara Hora Shastra (Chandra adhyaya), Shiva Purana (Somvar vrat)",
          "The remedies above are the classically-cited ones from Brihat Parashara Hora Shastra and Phaladeepika",
          "the practices in BPHS", "remedies from the BPHS",
          "BPHS (Mangal adhyay)", "Parasara Shani Adhyaya", "B.P.H.S. Guru adhyaya",
          "Chandra adhyaya", "Surya Samhita", "S\u016brya Sa\u1e43hit\u0101", "Surya  Samhita",
          "Sunday charity list per Muhurtha Chintamani", "the donation list from Muhurta Chintamani",
          "Muhurtha Chintamani's charity list",
          "Beej mantra from standard Grahashanti tradition", "Graha Shanti tradition", "Grahashaanti tradition",
          # The label is pinned only where it sits over folk / untraced material.
          "Classical sources cited\nModern folk tradition (KSD is post-classical).",
          "Classical sources cited\nGanesha as Ketu's deity follow the standard lists. The rest is devotional "
          "and family tradition that we have not traced to a classical text."),
    # S. The bija mantras lent BPHS's name (remedies.md 6.3: widely-accepted, no book).
    "S": ("Chant Ketu's beej mantra \u2014 the full classical form per BPHS is Om Sraam Sreem Sraum Sah Ketave Namah",
          "Chant Rahu's beej mantra \u2014 the full classical form per BPHS is Om Bhraam",
          "the bija mantra per BPHS", "Beej mantra according to Brihat Parashara Hora Shastra",
          "the Rahu seed mantra given in BPHS", "Bheej mantra as per Parasara",
          "per Parashara, the beeja mantra is", "the original version per B.P.H.S.",
          "the standard form from BPHS is", "according to the BPHS the seed mantra for Shani",
          "the full classical version in Brihat Parashara"),
    # T. Urad / black gram as a SATURN practice (Rao 34.3: Saturn = sesame, Rahu = urad).
    "T": ("Donate black sesame, iron, mustard oil, or black gram (urad dal) on Saturdays.",
          "Saturn: donate urad daal", "Shani ko urad dal ka daan", "black daal for Sade Sati",
          "Saturn rules black gram", "donate black daal / mustard oil", "Urad Dal and iron on Saturday",
          "kaali dal for Shani", "mustard oil and black gram on Saturdays", "urad  dal \u2014 Saturn's grain",
          "Sade Sati remedies: urad", "black lentils and iron for Saturn",
          "\u0936\u0928\u093f \u0915\u0947 \u0932\u093f\u090f \u0909\u0921\u093c\u0926 \u0915\u093e \u0926\u093e\u0928"),
    # U. Sesame as a RAHU practice.
    "U": ("For Rahu-related unstable wealth: Rahu mantra, donations of black sesame or blue cloth, worship of Bhairava.",
          "Rahu: offer sesame seeds", "Donate black gram daal (urad dal), black sesame, or blue cloth for Rahu",
          "Rahu Yantra worshipped with blue flowers and black til", "sesame seeds donated to appease Rahu",
          "Rahu remedy: black til on Saturdays", "black sesame for Rahu mahadasha", "Rahu  \u2014 teel daan",
          "til for Rahu", "Rahu-related unstable wealth: donating black sesame",
          "\u0930\u093e\u0939\u0941 \u0915\u0947 \u0932\u093f\u090f \u0924\u093f\u0932 \u0915\u093e \u0926\u093e\u0928",
          # The sentence exemptions are per sentence: an ancestor rite or a "Saturn rules sesame"
          # in the NEXT sentence must not launder this one (QA round 1, D2).
          "Water to ancestors on Pitru Paksha. Rahu: offer sesame seeds.",
          "Saturn rules sesame seeds. Donate sesame seeds to Rahu on Saturdays.",
          "Rahu: black til daan. Tarpan is a separate rite."),
    # V. Both nodes "in their friendly signs" as a Kaal Sarp cancellation (grahas.md 11.1).
    "V": ("Both Rahu and Ketu are in their friendly signs",
          "Rahu and Ketu in friendly signs",
          "Rahu & Ketu in their friendly rashis",
          "both Rahu/Ketu placed in friendly signs",
          "Cancellation: Rahu and Ketu are in its friendly sign and Jupiter is in a kendra"),
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
    "Because Vishnu is one of Mercury's ruling deities, many readers also recite the "
    "Vishnu Sahasranama on Wednesdays.",
    # Slice 5 INVERTED the legal sample that stood here. It read "the Vishnu
    # Sahasranama is a safe universal Mercury remedy", under a comment calling it
    # correct, and so pinned the very overclaim #465 removed as legal: it is now
    # sample F above. A fixture that outlives its refutation is the defect class
    # this repo keeps paying for.
    "Many keep the Vishnu Sahasranama as that practice; the choice of hymn is yours.",
    # The Lalita Sahasranama is remedies.md 8's own, so it may sit beside a
    # certifying word; and Rao's own labour deed keeps its "classical".
    "Sri Sukta or the Lalita Sahasranama is the classical daily practice before the Sri Yantra.",
    "Recite the Lalita Sahasranama or Durga Chalisa - Goddess worship is Venus's devotional path.",
    # PR #487 QA round 1: the hyphen, a double space and the other spellings of the
    # one hymn remedies.md 8 does name.
    "Sri Sukta or the Lalita-Sahasranama is the classical daily practice before the Sri Yantra.",
    "Sri Sukta or the Lalita  Sahasranama is the classical daily practice before the Sri Yantra.",
    "The classical daily practice is the Lalitha Sahasranam before the Sri Yantra.",
    "The universal Sri Yantra practice is the Lalita\u2011Sahasranama.",
    "सबसे शक्तिशाली powerful ललिता सहस्रनाम",
    "The classical good deeds for Rahu are a research donation or a pilgrimage.",
    "Good deeds in Saturn's domain",
    "Serving these groups is a widely-kept Ketu karma-clearing practice.",
    "Your health matters more than any ritual.",
    # Near misses the widened J must leave alone (all live in the tree or its register).
    "Moon orbits Earth moving faster than any other graha across the zodiac.",
    "Ketu releases the difficulty faster than most people process it.",
    "Weekly worship on the planet's day is more effective than sporadic elaborate rituals.",
    "A good match matters more than any single remedy.",
    "none of them needs an expensive puja package.",
    "Genuine puja for Saturn is inexpensive; expensive rituals done without devotion are not "
    "what the tradition asks for.",
    "Classical Saturn good deed: labour itself.",
    "This guide walks the six most classically-cited Rahu remedies with honest expectations.",
    "This guide walks the six most classically-cited Ketu remedies with realistic expectations.",
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
    # K is the three-rung SHAPE, not a ban on "enemies" or on 0: enemy+enemy IS 0
    # (matching.md vv.27-28) and the rest of the ladder is the correct text.
    "Mutual enemies score 0 points.", "0 only when both are enemies",
    "friend + enemy 2, neutral + enemy 1, enemy + enemy 0",
    "If both lords are enemies, 0.", "If the lords are mutual enemies, zero.",
    "If one lord is a friend and the other an enemy, 2 points.",
    "If one lord is neutral and the other an enemy, 1 point.", "If the lords are neutral, 3 points.",
    "5 points if the lords are friends or the same planet rules both Moon signs, 4 for a friend and a "
    "neutral, 3 for two neutrals, 2 for a friend and an enemy, 1 for a neutral and an enemy, and 0 only "
    "when both are enemies.",
    "Neutral planets: Mars, Jupiter, Venus, Saturn", "The Moon has no enemies.",
    "If both lords are enemies, 0.", "both enemies, 0", "two enemies: 0 points",
    # L is the Parashara/predates/ad-hoc history, not a ban on saying the standard table
    # covers seven planets. The first two are the sentences as shipped after slice 6.
    "Outside the standard natural-friendship table, which covers the seven visible planets; Rahu's "
    "friendships are assigned by tradition (commonly friendly with Venus and Saturn, hostile to the Sun, "
    "Moon and Mars) and vary between schools",
    "The standard table above covers the seven visible planets. Rahu and Ketu are given friendships by "
    "tradition and schools vary on this more than they do on the seven.",
    "Rahu and Ketu are not in the standard natural-friendship table.",
    "The friendship table excludes Rahu and Ketu.", "The table covers only the seven visible planets.",
    "The classical grid (Naisargika Maitri):", "Rahu is friendly with Venus and Saturn.",
    "The Vimshottari scheme was built for nine planets.", "Ketu's friendships vary between schools.",
    # M-Q must leave the true text alone.
    "Jupiter counts Mercury among its natural enemies, while Mercury treats Jupiter as neutral; the two "
    "together often produce brilliant minds.",
    "Mercury is Jupiter's natural enemy.", "Mercury's enemy is the Moon; Jupiter is neutral to it.",
    "Mercury: friends Sun, Venus; enemy Moon; neutral Mars, Jupiter, Saturn", "Jupiter and Mercury are friends in the chart of this native.",
    "Narasimha is an angry form of Vishnu, so if Vishnu is your family's deity, this is the route that stays within it.",
    "Mars: Hanuman, Rudra, Kartikeya (Subrahmanya), Narasimha \u2014 the man-lion form of Vishnu.",
    "Vishnu devotions your family already keeps (Ekadashi fasts, Satya Narayan Katha) are worth continuing as "
    "devotion in their own right. They are a devotional tradition, not one of the deities the classical table "
    "gives Mars.",
    "Ketu releases the difficulty; Ekadashi vrat is also kept for Ketu by tradition.",
    "Many families also keep Monday Shiva worship for Kaal Sarp, because Shiva's iconography shows Nagas "
    "wrapped around his neck. That is a popular devotional tradition rather than the deity either node is "
    "given in the table (the table pairs Shiva with the Sun), so treat it as devotion you may add, not as a "
    "required first step.",
    "Monday temple visit \u2014 offer milk, water, bilva leaves to Shivalinga",
    "Regular visits to the deity you chose in section 1 (weekly for a year); Monday Shiva visits if that is "
    "your family's tradition",
    "7 remedies; only (1) the deities of Rahu and Ketu and (4) the Beej mantras are classical, the rest is "
    "tradition: (1) Rahu: Durga or Narasimha, Ketu: Ganesha (Monday Shiva worship + Om Namah Shivaya 108x is "
    "a devotional tradition, not the deity of either node)",
    "Only the deity pairing in section 1 and the Rahu and Ketu Beej mantras are classical. Monday Shiva "
    "worship, Nag Panchami observance, the silver serpent offering and the Trimbakeshwar Nagbali are "
    "traditional and regional practice.",
    "Nag Panchami is the traditional annual serpent-worship day, widely kept for Kaal Sarp.",
    "A traditional practice, not a classical remedy: obtain a small pair of silver serpents (Nag-Nagini)",
    "KSY is not defined in the classical Sanskrit Jyotish texts. Remedies are Nag Panchami observance, Shiva puja on Mondays.",
    "Rahu's classical remedies number six; Rahu's seven classical remedies are listed in the guide.",
    "A simple place to start", "If you're anxious about Saturn, these are simple practices to start with:",
    "Hanuman is the first-listed of Mars's classical deities.",
    "Weekly Sri Sukta recitation before a Sri Yantra \u2014 the universal safe Venus / Lakshmi practice.",
    "The universal safe fallback\n\nIf you don't know your Ascendant, these Venus practices are safe for anyone:",
    "Four practices anyone can do: Sri Sukta before a Sri Yantra. Venus-domain themes and none can backfire.",
    "Good deeds in Mars's domain (safe for anyone)",
    "None of these needs an expensive puja package.",
    # Slice 8. Each is live in the tree or is the shipped replacement text, and must stay green.
    "Black gram (urad daal) \u2014 Rahu's classical grain; often given raw or cooked to those in need",
    "Some folk traditions substitute black til (sesame) \u2014 this is actually Saturn's grain, but works as a "
    "symbolic offering on shared Saturday since Rahu and Shani both share the day. If in doubt, use urad daal.",
    "Donate black sesame, iron, or mustard oil on Saturdays.",
    "(4) Saturday charity (black gram/urad daal, blue clothes, coconut), (5) Ganesha pre-invocation",
    "Hasta (Antya), Anuradha (Madhya), Shravana (Antya); complementary Jupiter\u2013Saturn temperaments",
    "Pushya, Anuradha, Saturn in the 7th: check the nakshatra of the lord",
    "Saturday \u2014 sunset-only meal; moong-urad khichdi with rock salt",
    "Rahu: Durga worship. Water with sesame to ancestors on Pitru Paksha.",
    "Rahu mantra, Durga worship, donation of black gram.",
    "Chant Ketu's beej mantra \u2014 the widely-accepted full form is Om Sraam Sreem Sraum Sah Ketave Namah.",
    "The Beej mantra in its widely-accepted seed form follows the standard planet-by-planet remedy lists of modern "
    "Vedic astrology.",
    "Parashara is the author of Brihat Parashara Hora Shastra; the Rahu Beej mantra is widely accepted.",
    "Pradosh/Nishita muhurat windows per Muhurtha Chintamani.",
    "Brihat Parashara Hora Shastra (Bhava Phala adhyaya), Phaladeepika Ch.11, Saravali Ch.28 (Labha bhava).",
    "Skanda Purana (Kartik Mahatmya), Bhavishya Purana (Karva Chauth Katha).",
    "Classical sources cited\nGarud Purana (Pitru shraddha vidhi). Gaya tri-pindi per Gayawal Brahmin tradition.",
    "Classical sources cited\nKumbh Vivah + Peepal Vivah \u2014 modern folk-remedial practice.",
    "Sources and traditions\nThe Somvar vrats and silver are devotional and family tradition that we have not "
    "traced to a classical text.",
    "The Aditya Hridaya Stotra is a hymn from the Ramayana (Yuddha Kanda).",
    # QA round 1 (D2): three correct sentences the first T and U patterns flagged.
    "Saturn rules sesame seeds, Rahu rules black gram daal.",
    "Pitru dosh with Rahu: tarpan with black sesame",
    "Rahu: black til is Saturn's grain",
    # V: the sourced wording, and a single node in a friendly sign (learn_registry's Rahu-dasha FAQ).
    "Both Rahu and Ketu are in signs ruled by their traditional friends, Venus and Saturn (traditions vary "
    "on the nodes' friendships)",
    "A well-placed Rahu (in the 3rd, 6th, 10th, or 11th house, in a friendly sign, aspected by benefics)",
    "Rahu and Ketu in signs ruled by their traditional friends (Venus, Saturn)",
    # D4: the callout wording that replaced "the standard planet-by-planet remedy lists".
    "The Beej mantra in its widely-accepted seed form follows one modern textbook's planet-by-planet "
    "remedy table.",
)

# The one honest Hanuman-Saturn sentence a page may keep: it must say popular/folk
# AND name Mars. Each half, removed, must turn the gate red.
_HONEST = ("Many people recite the Hanuman Chalisa on Saturdays through a hard Saturn period; "
           "that is a popular tradition, not a classical Saturn assignment. The classical road "
           "to Hanuman runs through Mars carrying Saturnine influence.")


def gate8_mutations() -> tuple[int, int]:
    """#430: re-break each Sade Sati phase-name surface and require Gate 8 red."""
    caught = missed = 0
    lines = gate.sade_sati_prompt_lines()
    titles = gate.sade_sati_panel_titles()
    ref = gate.sade_sati_reference()

    def run(**kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ok = gate.gate_8_sade_sati_phase_names(**kw)
        return ok

    def expect(label: str, ok: bool, want_green: bool):
        nonlocal caught, missed
        if ok == want_green:
            caught += 1
        else:
            missed += 1
            print(f"  MISSED  sade-sati-names  {label}: expected "
                  f"{'green' if want_green else 'red'}, went {'green' if ok else 'red'}")

    expect("CONTROL (real tree)", run(), True)
    for label, old, new in (
        ("prompt rising (arohini)", "rising phase", "rising phase (arohini)"),
        ("prompt setting (avarohini)", "setting phase", "setting phase (Avarohini)"),
        ("prompt invented label", "peak phase (madhya)", "peak phase (shikhara)"),
    ):
        expect(label, run(prompt_lines=[ln.replace(old, new) for ln in lines]), False)
    for key, new in (
        ("en:sade_sati_rising_title", "Rising Phase (Arohini)"),
        ("en:sade_sati_setting_title", "Setting Phase (Avarohini)"),
        ("hi:sade_sati_rising_title", "आरोही चरण (आरोहिणी)"),
        ("hi:sade_sati_setting_title", "अवरोही चरण (अवरोहिणी)"),
        ("en:sade_sati_peak_title", "Peak Phase (Shikhara)"),
    ):
        expect(f"panel {key}", run(panel_titles=[(k, new if k == key else t) for k, t in titles]), False)
    # Unchanged legal text stays green, and a gate with nothing to scan fails.
    expect("peak (madhya) is written in the reference", run(reference=ref), True)
    expect("empty reference", run(reference=""), False)
    expect("no prompt lines", run(prompt_lines=[]), False)
    expect("no panel titles", run(panel_titles=[]), False)
    return caught, missed


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

    real_fields = gate.numerology_remedy_fields()

    def run(units, fields=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ok = gate.gate_7_no_retired_claims_on_reader_surfaces(
                units, real_fields if fields is None else fields)
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

    # W. The numerology remedy rows carry no planet word in their strings, so the gate reads the
    # structure (QA round 1, D1: sesame put back into the Rahu yantra and charity strings stayed
    # green). Mutate the first offering field of each planet's row and require the gate to name it.
    def row_of(planet: str):
        return next(i for i, (_, pl, _t) in enumerate(real_fields) if pl == planet)

    for planet, extra, want_green in (
        ("Rahu", ", sesame seeds", False), ("Rahu", " with blue flowers and black sesame.", False),
        ("Rahu", " Til daan.", False), ("Saturn", ", urad daal", False), ("Saturn", " and black gram.", False),
        ("Rahu", " Donate black gram (urad daal).", True), ("Saturn", ", sesame seeds, iron nails.", True),
    ):
        i = row_of(planet)
        fields = list(real_fields)
        w, pl, t = fields[i]
        fields[i] = (w, pl, t + extra)
        ok, out = run(real, fields)
        if ok == want_green and (want_green or f"{w}" in out):
            caught += 1
        else:
            missed += 1
            print(f"  MISSED  reader-claim W  {planet} remedy + {extra!r}: expected "
                  f"{'green' if want_green else 'red naming ' + w}, went {'green' if ok else 'red'}")
    for label, fields in (("no rows", []), ("no Rahu row", [f for f in real_fields if f[1] != "Rahu"]),
                          ("no Saturn row", [f for f in real_fields if f[1] != "Saturn"])):
        if not run(real, fields)[0]:
            caught += 1
        else:
            missed += 1
            print(f"  MISSED  reader-claim W  a stub ({label}) with nothing to scan PASSED")

    # A gate that checks nothing must fail: no units, a lone surface, a tree with
    # no files, and a tree whose files exist but hold no text.
    import tempfile

    stubs = {"no units": [], "templates only": [u for u in real if u[0].startswith("templates/")],
             # slice 5: festival_registry.py is a required surface, so dropping it must fail
             "no festival_registry": [u for u in real if not u[0].startswith("festival_registry.py")]}
    with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as hollow:
        stubs["empty tree"] = gate.reader_surface_units(Path(empty))
        (Path(hollow) / "templates" / "learn").mkdir(parents=True)
        (Path(hollow) / "templates" / "learn" / "x.html").write_text("")
        for name in ("i18n.py", "numerology.py", "learn_registry.py", "festival_registry.py"):
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
        # Slice 6. The first row of each is the sentence the summary actually carried.
        gate.HYMN_CERTIFIED: (("jupiter-remedies", "Jupiter safe universal practices (any chart): Thursday fasting, Vishnu Sahasranama chanting"),
                              ("mercury-remedies", "Mercury safe universal practices: Wednesday fasting, Vishnu Sahasranama"),
                              ("manglik-remedies", "7 classical remedies: (1) Hanuman worship, (2) Vishnu Sahasranama + Ekadashi vrat"),
                              (None, "Vishnu Sahasranam is the classical Jupiter remedy"),
                              (None, "the most reliable Mercury practice is the Vishnu Sahasranama"),
                              (None, "विष्णु सहस्रनाम सबसे शक्तिशाली powerful उपाय")),
        gate.GRAHA_MAITRI_MISSTATED: (("kundali-matching-ashtakoot-guna-milan", "Graha Maitri: friends 5, if neutral, partial, if enemies, 0"),
                                      (None, "Friends full 5 points. Neutral: half."),
                                      (None, "if hostile, zero")),
        gate.RAHU_KETU_GRID: (("rahu-in-vedic-astrology", "Not part of Parashara's natural-friendship grid"),
                              (None, "Rahu and Ketu aren't in classical natural-friendship grids"),
                              (None, "the table predates Rahu's formal inclusion"),
                              (None, "Modern practice uses ad-hoc rules for them")),
        # Slice 7. The first row of each is the claim as it stood in (or would reach) the summary.
        gate.MERCURY_JUPITER_ENEMY: (("budha-mercury-in-vedic-astrology", "Jupiter is Mercury's natural enemy"),
                                     (None, "Mercury and Jupiter are natural enemies"),
                                     (None, "Mercury regards Guru as hostile")),
        gate.VISHNU_FOR_MANGLIK: (("manglik-remedies", "7 remedies: (1) Hanuman worship, (2) Vishnu worship (a mantra, or a hymn your own tradition keeps) + Ekadashi vrat, (3) Mars Beej mantra"),
                                  (None, "If mismatch: soften with Hanuman practices + Vishnu worship + Kumbh Vivah"),
                                  (None, "Manglik remedy: Satya Narayan Katha monthly")),
        gate.KSD_SHIVA_FIRST: (("kaal-sarp-dosh-remedies", "7 classical remedies: (1) Monday Shiva worship + milk abhishek"),
                               (None, "Any KSD remedy begins with Shiva worship"),
                               (None, "weekly Monday Shiva visits are the most accessible starting point")),
        gate.KSD_TRADITION_AS_CLASSICAL: (("kaal-sarp-dosh-remedies", "7 classical remedies: (1) Durga"),
                                          (None, "Nag Panchami is the classical annual serpent-worship day"),
                                          (None, "KSD's peak remedial day is Nag Panchami")),
        # Slice 8. The T and U first rows are the claims as they stood in a summary / FAQ.
        gate.BIJA_PER_BPHS: (("rahu-in-vedic-astrology", "Chant Rahu's beej mantra - the full classical form per BPHS"),
                             (None, "Ketu bija mantra from Brihat Parashara"),
                             (None, "the seed mantra given in BPHS")),
        gate.URAD_AS_SATURN: (("sade-sati", "\u2022 Safe remedies: Vishnu worship, serve elderly, donate black daal / mustard oil"),
                              ("saturn-remedies", "Saturn: donate urad daal"),
                              (None, "Shani charity: black gram"),
                              (None, "Saturday iron and urad dal for Sade Sati")),
        gate.SESAME_AS_RAHU: (("financial-struggles", "For Rahu-related unstable wealth: Rahu mantra, donating black sesame"),
                              ("rahu-remedies", "Rahu: offer sesame seeds"),
                              (None, "black til for Rahu")),
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
        # Slice 6: the Lalita hymn is remedies.md 8's own; mutual enemies ARE 0; the seven-planet table.
        ("venus-remedies", "Venus safe universal practices: Friday fasting, Sri Lalita Sahasranama, Devi/Lakshmi worship"),
        ("kundali-matching-ashtakoot-guna-milan", "friend+enemy 2, neutral+enemy 1, enemy+enemy 0; mutual enemies score 0"),
        ("rahu-in-vedic-astrology", "Outside the standard natural-friendship table, which covers the seven visible planets"),
        ("jupiter-remedies", "Vishnu worship (a mantra, or a hymn your own tradition keeps), many recite the Vishnu Sahasranama"),
        # Slice 8: Rahu's own grain, Saturn's own grain, and a nakshatra that contains the letters "urad".
        ("rahu-remedies", "Saturday charity (black gram/urad daal, blue clothes, coconut)"),
        ("saturn-remedies", "Saturn charity: sesame/iron/mustard-oil, Shani Beej mantra"),
        ("kundali-matching-ashtakoot-guna-milan", "Hasta (Antya), Anuradha (Madhya), Saturn-Jupiter temperaments"),
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

    c8, m8 = gate8_mutations()
    caught += c8
    missed += m8

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
