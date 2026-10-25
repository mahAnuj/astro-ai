#!/usr/bin/env python3
r"""Verify `prompts/natal.txt` still carries every rule it is supposed to, and
still fits inside the Groq free-tier request ceiling.

WHY THIS EXISTS
---------------
`/kundli` broke in production with a Groq **413**:

    Request too large for model 'openai/gpt-oss-120b' ...
    tokens per minute (TPM): Limit 8000, Requested 8562

That is a SIZE failure, not a rate failure. A single request larger than the
entire per-minute budget can never succeed, at any traffic level, on any of
the free-tier models — `groq120` and `groq20` share the same 8,000 TPM cap, so
falling through the chain just repeats the same 413. At the time of the
failure `natal.txt` was 18,095 B, roughly 5,000 tokens, **64% of the whole
request**; the chart data was the other 36%.

The fix was to compress the prompt. Compression is where prompts silently lose
rules: a paragraph gets folded into a neighbouring one, and six months later
nobody can tell whether "do not name the planet" was deliberately dropped or
accidentally deleted. Every rule in the table below was in the 18,095 B
version and is load-bearing — several were added by a specific issue after a
specific reading went wrong (#60 house lords, #61 dignity, #62 D-9, #64 D-10,
#65 remedies; the Manglik block is the residue of #165/#166/#176).

So this gate is a checklist taken from the pre-compression file. It does not
judge prose. It asserts that each rule is still *stated*, that the seven
section headings are exactly right, and that the file still fits the budget
the 413 taught us about.

  Gate 1 - the seven sections.  `## ` headings, exact text, exact order,
      exactly seven of them, each appearing exactly once. The route splits the
      reading on these headings to render the section cards; an eighth heading
      or a renamed one produces a card the template has no home for. This is
      the one part of the prompt whose text is a wire format.

  Gate 2 - the rules.  Every rule in RULES must still be findable. Each rule
      carries anchors (regexes that must all match) and an explanation of what
      breaks if it goes. Anchors are deliberately SHORT and semantic — the
      distinctive words a rule cannot be stated without — so the prompt can be
      rewritten freely as long as the rule survives. Where a rule is about a
      list (the nine planet names, the seventeen banned words) the whole list
      is checked, because dropping one entry from a list is exactly the kind
      of loss a prose-level check misses.

  Gate 3 - the budget.  The file must stay under MAX_BYTES, and the estimated
      system-prompt token count must leave room for the chart data. The
      numbers and their provenance are recorded beside the constants.

  Gate 4 - no stale size citations.  Prose that quotes the prompt's byte size
      must still match it.

  Gate 5 - no retired claims.  Strings #398 removed as wrong or unsourced
      (FORBIDDEN) must not reappear.

  Gate 6 - no retired claims in the topic summaries.  The natal user message
      carries RELEVANT TOPIC SUMMARIES, built from `Article.llm_summary` in
      `learn_registry.py` (`chart.format_topic_summaries_for_prompt` emits
      nothing else). Gate 5 cleaned the system prompt and the summaries
      kept saying red-lentil, Surya Namaskar, black sesame and "Hanuman is
      the intercessor with Shani" - so a reader was still told them, from
      the other half of the same request. This gate runs SUMMARY_FORBIDDEN
      over every llm_summary and names the offending slug. Only llm_summary
      is scanned: the /learn article bodies and FAQs are Gate 7's. Slice 6
      added three rows here: a hymn beside a certifying word (Jupiter's and
      Mercury's summaries said "safe universal practices ... Vishnu
      Sahasranama", and so did Manglik's "7 classical remedies"), and the
      Graha Maitri and Rahu/Ketu-grid shapes of Gate 7 families K and L.
      Slice 7 added four more (M Mercury-Jupiter enmity, N Vishnu rite for
      Manglik, O Monday Shiva as the Kaal Sarp remedy, P Kaal Sarp tradition
      called classical); the constants are shared with Gate 7. Slice 8 added
      three more: the bija mantras lent BPHS's name (S), urad given as a
      Saturn practice (T) and sesame as a Rahu one (U) - including a summary
      that said "donate black daal / mustard oil" under Sade Sati.

  Gate 7 - no retired claims on the reader-facing surfaces.  The same claims
      sat on the pages a reader opens directly: the /learn article bodies,
      the FAQ answers / SEO fields in `learn_registry.py`, `i18n.py` (both
      languages) and `numerology.py`. Gates 5 and 6 cleaned only what the LLM
      is shown. This gate scans those surfaces for the twenty-one families #398
      retired - Sun->red lentils, Moon->milk/Shiva, Saturn->Hanuman,
      Ketu->sesame oil, Rahu->serve outsiders, a named hymn as Saturn's
      practice or as ANY planet's universal/classical/safe one (slice 5),
      "per <source> remedial tradition", Surya Namaskar (slice 4),
      a rule lent Parashara's name, "(per Parashara's grid)" (slice 4), and
      three shapes by which a product-added remedy was called classical or
      ranked above ritual (slice 5, #468), the Graha Maitri ladder collapsed
      to friend / neutral-"partial" / enemy-0 (K, slice 6) and Rahu and Ketu
      placed outside "Parashara's" friendship grid (L, slice 6), and (slice 7)
      Jupiter as "Mercury's natural enemy" (M), a Vishnu rite as a Manglik
      remedy (N), Monday Shiva as the first/classical Kaal Sarp remedy (O),
      Kaal Sarp tradition called classical (P) and "universal safe" on the
      Saturn/Jupiter/Mercury/Mars pages (Q), and (slice 8) a remedy page citing
      a BPHS "<planet> adhyaya", a Surya Samhita or a Muhurtha Chintamani
      "charity list" or "Grahashanti tradition" (R), the bija mantras "per BPHS"
      (S), urad / black gram as a Saturn practice (T) and sesame as a Rahu one (U)
      (READER_FORBIDDEN) - and names file:line. It does NOT forbid the
      families still open on #398 ("black sesame", weekday fasting):
      forbidding them here would only make main red. A bare "per BPHS" is
      also not forbidden, for the same reason (family I's comment has the
      count). It must also see at least one unit from each
      surface (festival_registry.py included since slice 5), so a gate pointed
      at an empty tree fails instead of passing.

Exit 0 = PASS, 1 = FAIL. No network, no API key, no ephemeris — it reads one
file, so it runs anywhere and belongs in the `verify_*` sweep.

Mutation-tested (2026-09-05): deleting any single rule's sentence from
`natal.txt` turns Gate 2 red for that rule and only that rule; the unmutated
CONTROL passes. A gate that has only ever passed is not evidence.
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Gate 6 reads the registry. learn_registry.py imports only `dataclasses`, so
# this stays runnable with no API key and no ephemeris, like the other gates.
sys.path.insert(0, str(REPO_ROOT / "src"))
PROMPT = REPO_ROOT / "src" / "astro_ai" / "prompts" / "natal.txt"

# --- Gate 1 ------------------------------------------------------------------

# Exact, ordered. `routes/kundli.py` splits the reading on these.
HEADINGS = (
    "Personality & Character",
    "Career & Profession",
    "Wealth & Money",
    "Relationships & Marriage",
    "Health & Wellbeing",
    "Travel & Opportunities",
    "Life Stages",
)

# --- Gate 3 ------------------------------------------------------------------

# All four constants are MEASURED, by `scripts/measure_natal_request.py` over
# the eight golden charts in tests/kundali-qa-fixtures.json, 2026-09-05. They
# were guesses in the first version of this file and every one of them was
# wrong — the guessed chars-per-token over-counted the prompt by 16%.
#
#   * The system prompt is 3,111 tok at 13,135 B (13,013 B after #398) — 4.22 B/tok for instruction
#     prose. It is identical on every request; only the user message varies.
#   * The largest chart payload across the eight fixtures is 3,687 tok
#     (cancer-lagna-manglik-exempt: Manglik detail block plus topic summaries).
#   * On the PRE-compression 18,095 B prompt that same chart assembled to
#     8,019 tok — over the 8,000 ceiling before Groq adds anything of its own.
#     That is the 413, reproduced from a fixture rather than inferred.
#   * Production reported 8,562 for a chart we do not have. The 543 above our
#     highest fixture is some mix of a larger chart and Groq's own accounting
#     (chat-template scaffolding, plus whatever completion it reserves), and we
#     cannot yet split it — hence a deliberately generous margin below.
TPM_CEILING = 8_000
BYTES_PER_TOKEN = 4.23
MAX_BYTES = 13_200  # ~3,120 tok: a ratchet at today's size, not a target
LARGEST_CHART_PAYLOAD = 3_687

# What must be left over the worst measured chart once the prompt is counted.
# 1,000 tok (12.5%) covers Groq's unmeasured accounting and charts bigger than
# any fixture. It is the number to revisit once the completion reservation is
# measured against the live API.
MARGIN = 1_000

# --- Gate 2 ------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """One normative rule the prompt must still state.

    `anchors` are regexes, all of which must match somewhere in the file.
    `scoped` locates a single line and asserts a list of tokens all appear on
    it — used for the list-shaped rules, where the failure mode is losing one
    entry rather than the whole rule.
    """

    rule_id: str
    why: str
    anchors: tuple[str, ...] = ()
    scoped: tuple[tuple[str, tuple[str, ...]], ...] = field(default=())


PLANETS = ("Jupiter", "Saturn", "Rahu", "Ketu", "Mars", "Mercury", "Venus", "Sun", "Moon")

BANNED_WORDS = (
    "navigate", "manifest", "amplify", "introspection", "consolidation",
    "favourability", "propensities", "endeavour", "facilitates", "delve",
    "unlock", "harness", "empower", "leverage", "moreover", "furthermore",
    "intricacies",
)

LIFE_DOMAINS = ("Health", "Family", "Education", "Career", "marriage", "Money", "Personality")

RULES: tuple[Rule, ...] = (
    # --- what the reading is ---
    Rule(
        "chart-data-is-internal",
        "The whole premise: the seeker gets interpretation, not placements. "
        "Lose this and the model narrates the chart back at them.",
        anchors=(r"\bsilently\b", r"NOT on which planet sits where|not on placements"),
    ),
    Rule(
        "section-word-targets",
        "Six sections at 120-180 words and Life Stages at 250-350 are what make "
        "the seven cards render at comparable heights.",
        anchors=(r"120-180", r"250-350"),
    ),
    Rule(
        "total-word-target",
        "920-1380 total. Below it the page looks empty; above it the completion "
        "reservation eats into the same 8,000 TPM budget the 413 came from.",
        anchors=(r"920-1380",),
    ),
    # --- Manglik: the residue of #165 / #166 / #176 ---
    Rule(
        "manglik-verdict-is-given-not-chosen",
        "Three surfaces once gave three different Manglik answers for one chart "
        "(#176). The verdict is computed in Python and stated once in the user "
        "message; the model restates it and nothing else.",
        anchors=(r"VERDICT IS NOT YOURS", r"Manglik \(Mangal Dosh\):"),
    ),
    Rule(
        "manglik-no-invented-rules",
        "Without this the model supplies classical rules from training data that "
        "contradict the cancellation catalogue in knowledge/vedic_reference.md.",
        anchors=(r"[Dd]o NOT invent rules|only what the MANGLIK DETAIL block lists",),
    ),
    Rule(
        "manglik-never-predicts-marital-failure",
        "At any status, at any severity. This is the single most harmful thing "
        "the reading could say.",
        anchors=(r"NOT predict marital failure",),
    ),
    Rule(
        "manglik-mutual-remedy-is-conditional",
        "'Marry another Manglik' is never unconditional — and this reading sees "
        "ONE chart, so it cannot judge whether a partner's dosha would match "
        "(#166: a low Manglik was told it cancelled against a high one).",
        anchors=(r"NEVER unconditional", r"ONE chart"),
    ),
    Rule(
        "manglik-frame-disambiguation",
        "Mars sits in different houses counted from Lagna, Moon and Venus. A bare "
        "'Mars is in the 7th' is unfalsifiable and often reads as wrong.",
        anchors=(r"FRAME DISAMBIGUATION|which frame",),
        scoped=((r"^.*FRAME DISAMBIGUATION.*$", ("Lagna", "Moon", "Venus")),),
    ),
    Rule(
        "no-classical-text-names-in-prose",
        "The seeker does not know who Rao is. Book-and-chapter citations belong "
        "in the UI panel; CLAUDE.md states this as a content rule.",
        anchors=(r"BPHS", r"[Dd]o NOT (name|cite) classical|do NOT cite"),
        # SCOPE, not just presence. The old prompt stated this twice — once in
        # the Manglik block and once globally under the yogas allowance — and
        # the first compression left only the Manglik copy, moving a global ban
        # inside a conditionally-scoped bullet list. Both anchors above stayed
        # green throughout, because they only ask whether the words are in the
        # file. It now lives in STRICT OUTPUT RULES with the other global bans,
        # and this window asserts that is where it stays.
        scoped=((r"STRICT OUTPUT RULES(?:.|\n){0,900}", ("classical texts",)),),
    ),
    Rule(
        "sade-sati-named-with-phase",
        "Sade Sati is named on the page, so the prose must agree with the panel — "
        "including which of the three phases is running.",
        # "Sade Sati" and "phase" both also occur in the ALLOWED list further
        # down, so a whole-file search for them stays green even if the Health
        # section's instruction is deleted — the mutation harness reports that
        # line as unanchored and QA restated it. This third anchor is the
        # instruction's own distinctive words.
        anchors=(r"Sade Sati", r"phase", r"not as something scary"),
    ),
    # --- Life Stages: the section that is hardest to keep honest ---
    Rule(
        "life-stages-uses-real-dasha-ages",
        "Age windows must be the Mahadasha boundaries from the user message, not "
        "invented decades — otherwise the section is a generic horoscope.",
        anchors=(r"Mahadasha", r"start-age|exact age boundaries", r"generic decade"),
    ),
    Rule(
        "life-stages-whole-years",
        "The block gives whole years. A decimal age ('from 34.7') reads as a bug "
        "to the seeker and there is nothing behind the extra precision.",
        anchors=(r"whole years", r"decimals"),
    ),
    Rule(
        "life-stages-never-names-the-ruling-planet",
        "The chapter is a life period, not a planet. Naming the ruler leaks the "
        "mechanism the STRICT OUTPUT RULES exist to hide.",
        anchors=(r"NOT name the planet",),
    ),
    Rule(
        "life-stages-tense-tags",
        "[PAST]/[NOW]/[LATER] with EXACTLY ONE [NOW]. Describing a past chapter "
        "in the present tense makes the whole reading read as untethered.",
        anchors=(r"\[PAST\]", r"\[NOW\]", r"\[LATER\]", r"EXACTLY ONE \[NOW\]"),
    ),
    Rule(
        "life-stages-archetype-is-mandatory",
        "The archetype hint is what makes a chapter about THIS chart. Without the "
        "mandate every chapter collapses to 'you will grow'.",
        anchors=(r"ARCHETYPE|archetype", r"MANDATORY"),
    ),
    Rule(
        "life-stages-life-area-coverage",
        "At least 5 of the 7 domains, or the section becomes career-only.",
        anchors=(r"AT LEAST 5",),
        scoped=(),
    ),
    Rule(
        "life-stages-domain-list",
        "All seven domains must still be listed — losing one silently narrows "
        "every reading from then on. Scoped to the window right after the "
        "coverage instruction, because every one of these words also occurs "
        "elsewhere in the prompt and a whole-file search would pass on a list "
        "that had lost an entry.",
        scoped=((r"AT LEAST 5(?:.|\n){0,700}", LIFE_DOMAINS),),
    ),
    Rule(
        "life-stages-chapter-selection",
        "6-9 chapters out to age 80+; infancy gets a phrase, [NOW] and the next "
        "[LATER] get the detail, the final chapter gets a closing note.",
        anchors=(r"age 5", r"70\+|final chapter"),
    ),
    Rule(
        "life-stages-current-sub-window",
        "The sub-window is what makes the reading feel like it is about this "
        "month rather than this decade. One sentence, planet unnamed.",
        anchors=(r"CURRENT SUB-WINDOW", r"ONE final sentence|one final sentence"),
    ),
    Rule(
        "yoga-activation",
        "Every detected yoga must surface in at least one chapter it activates "
        "in — that mapping is the whole point of computing activators.",
        anchors=(r"activates in", r"AT LEAST ONE chapter"),
    ),
    Rule(
        "yoga-names-are-allowed",
        "Yoga names are the one Sanskrit vocabulary the reading may use; without "
        "the explicit allowance the model suppresses them with the planets.",
        anchors=(r"yoga names ARE allowed|[Yy]oga names are allowed",),
    ),
    Rule(
        "no-invented-yogas",
        "Only what the YOGAS DETECTED block lists. An invented yoga is an "
        "unsourced astrological claim shipped to a user.",
        anchors=(r"NOT invent yogas|only use what the block lists",),
    ),
    # --- the hard output bans ---
    Rule(
        "ban-planet-names",
        "All nine. Dropping one from the list is how 'Ketu' starts appearing in "
        "readings that ban the other eight.",
        anchors=(r"NOT name specific planets",),
        scoped=((r"^.*NOT name specific planets.*$", PLANETS),),
    ),
    Rule(
        "ban-sign-names",
        "Signs are the same leak as planets, in English or Sanskrit.",
        anchors=(r"NOT name specific signs",),
    ),
    Rule(
        "ban-house-numbers",
        "'Your 10th house' is the single most common way the mechanism leaks.",
        anchors=(r"NOT reference natal house numbers|NOT reference house numbers",),
    ),
    Rule(
        "ban-jargon-terms",
        "transit / gochar / natal Lagna / natal Moon / Bhava / lord of the — the "
        "vocabulary that makes a reading sound like a chart printout.",
        anchors=(r"\"transit\"", r"\"gochar\"", r"\"natal Lagna\"", r"\"natal Moon\"",
                 r"\"Bhava\"", r"\"lord of the\""),
    ),
    Rule(
        "no-explaining-why",
        "The seeker gets the conclusion. Explaining the reasoning re-introduces "
        "every banned term through the back door.",
        anchors=(r"NOT explain WHY",),
    ),
    # --- the conditional data blocks ---
    Rule(
        "topic-summaries-woven-in",
        "The summaries are per-chart classical rules; they belong inside the "
        "matching section, not in a list of their own.",
        anchors=(r"RELEVANT TOPIC SUMMARIES",),
    ),
    Rule(
        "learn-link-format",
        "Raw `/learn/<slug>/` path, at most one per section — the site linkifies "
        "it (routes/deps.py:_linkify_learn) and markdown syntax survives as text.",
        anchors=(r"/learn/<slug>/", r"raw slug path", r"one link per section"),
    ),
    Rule(
        "house-lord-placements",
        "#60. Career reads the 10th lord, Wealth the 2nd and 11th, Marriage the "
        "7th — in plain language, without naming the planet.",
        anchors=(r"HOUSE LORD PLACEMENTS", r"10th lord", r"7th lord",
                 r"2nd \+ 11th lord|2nd and 11th lord"),
    ),
    Rule(
        "d9-navamsha-scope",
        "#62. The D-9 is a lens for the marriage cross-check only (#398 removed "
        "the yoga-confirmation use: Rao puts manifestation in D-1 and D-10). "
        "Given any wider licence the model writes a Navamsha section.",
        anchors=(r"D-9", r"NAVAMSHA|Navamsha", r"[Mm]arriage"),
        # the substance, not just the block name: the 7th-house cross-check and
        # the kendra/trikona test are the rule. Without them "use the D-9 for
        # marriage" is an instruction with no method attached.
        # Anchored on the BLOCK DELIMITER, not on a bare "D-9" mention: the
        # umbrella rule above the bullets names both divisional charts, so a
        # first-match window opened on "D-9" starts in the wrong place and
        # never reaches the method. (Caught by this gate when the umbrella
        # was rewritten — which is the gate doing its job, brittly.)
        scoped=((r"--- D-9 NAVAMSHA ---(?:.|\n){0,900}", ("7th", "kendra")),),
    ),
    Rule(
        "d10-dashamsa-scope",
        "#64. The D-10 is a career cross-check only, and the check is whether "
        "the 10th of D-10 carries a benefic or its lord sits in a kendra.",
        anchors=(r"D-10", r"DASHAMSA|Dashamsa", r"Career section|career section"),
        scoped=((r"--- D-10 DASHAMSA ---(?:.|\n){0,700}", ("10th", "benefic")),),
    ),
    Rule(
        "divisional-charts-never-surface",
        "The factored rule the per-block handlers each used to restate: no "
        "separate section, no listing placements, never name the technique.",
        anchors=(r"separate\b[^\n]{0,24}\bsection",
                 r"list[^\n]{0,24}placements",
                 r"without naming Navamsha|technique by name|naming the technique"),
    ),
    Rule(
        "planet-dignity",
        "#61. Debilitation REVERSES a planet's meaning and combustion removes "
        "recognition without removing capacity. Ignoring the tag inverts the "
        "section it governs.",
        anchors=(r"PLANET DIGNITY", r"DEBILITATED", r"COMBUST", r"EXALTED"),
    ),
    Rule(
        "remedies-are-safe-and-brief",
        "#65. One line, universal practices only.",
        anchors=(r"REMEDIES", r"ONE brief|one brief"),
    ),
    Rule(
        "gemstone-caveat",
        "A wrongly-worn gemstone is the one remedy that can make things worse, "
        "and it is the one a reader will act on immediately.",
        anchors=(r"gemstone", r"consult a knowledgeable astrologer"),
    ),
    # --- language and format ---
    Rule(
        "banned-word-list",
        "All seventeen. This list is the difference between the house voice and "
        "generic LLM register; entries fall out of it one at a time.",
        anchors=tuple(rf'"{w}"' for w in BANNED_WORDS),
    ),
    Rule(
        "banned-words-are-hard",
        "Stated as a hard ban with a swap instruction — a soft 'prefer' is "
        "ignored roughly half the time.",
        anchors=(r"HARD BAN",),
    ),
    Rule(
        "short-sentences",
        "10-18 words, for a reader whose English is conversational.",
        anchors=(r"10-18 words",),
    ),
    Rule(
        "voice",
        "A kind elder, not a poet or a professor. The single most load-bearing "
        "line for the site's voice.",
        anchors=(r"kind elder",),
    ),
    Rule(
        "tentative-language",
        "'may bring', 'tends to' — astrological claims are not predictions.",
        anchors=(r"may bring", r"tends to"),
    ),
    Rule(
        "heading-marker-discipline",
        "Bare `##` markers between paragraphs break the section split as surely "
        "as a renamed heading does.",
        anchors=(r"bare `?##",),
    ),
    Rule(
        "format-prose-not-bullets",
        "Flowing prose inside each section; the cards are typeset for prose.",
        anchors=(r"[Nn]o bullets",),
    ),
    Rule(
        "address-by-name",
        "The seeker's name, used naturally — the one personalisation the reading "
        "is allowed outside the chart.",
        anchors=(r"by name",),
    ),
    Rule(
        "no-entertainment-disclaimer",
        "The site does not hedge that astrology is entertainment.",
        anchors=(r"[Nn]o disclaimers",),
    ),
)


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}")


def gate_1_headings(text: str) -> bool:
    print("Gate 1 - the seven sections")
    found = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    ok = True
    if tuple(found) != HEADINGS:
        ok = False
        _fail(f"heading list is {found!r}")
        _fail(f"                 expected {list(HEADINGS)!r}")
        _fail("routes/kundli.py splits the reading on these; a renamed or extra")
        _fail("heading produces a section card the template cannot place.")
    else:
        print(f"  ok    {len(found)} headings, exact text, in order")
    return ok


def gate_2_rules(text: str) -> bool:
    print("Gate 2 - the rules")
    failures: list[Rule] = []
    for rule in RULES:
        missing = [a for a in rule.anchors if not re.search(a, text)]
        for line_pat, tokens in rule.scoped:
            m = re.search(line_pat, text, flags=re.MULTILINE)
            if m is None:
                missing.append(f"(line matching {line_pat})")
                continue
            line = m.group(0)
            missing += [f"{t!r} on that line" for t in tokens if t not in line]
        if missing:
            failures.append(rule)
            _fail(f"{rule.rule_id}: missing {', '.join(map(str, missing))}")
            for line in rule.why.splitlines():
                print(f"          {line}")
    if not failures:
        print(f"  ok    {len(RULES)} rules present")
    return not failures


def gate_3_budget(text: str) -> bool:
    """The size check the 413 bought.

    Byte-based on purpose: it must run with no dependencies, in any checkout,
    as part of the `verify_*` sweep. `scripts/measure_natal_request.py` does
    the real BPE count over real charts; this is the cheap ratchet that keeps
    the prompt from drifting back up between measurements. If you change the
    prompt's size materially, re-run the measurement and re-derive the
    constants above rather than nudging MAX_BYTES.
    """
    print("Gate 3 - the budget")
    size = len(text.encode("utf-8"))
    tokens = round(size / BYTES_PER_TOKEN)
    worst = tokens + LARGEST_CHART_PAYLOAD
    print(f"  info  {size:,} B  ~{tokens:,} tok at {BYTES_PER_TOKEN} B/tok (measured)")
    print(f"  info  + largest measured chart payload {LARGEST_CHART_PAYLOAD:,} tok "
          f"= {worst:,} worst case")
    print(f"  info  ceiling {TPM_CEILING:,} TPM per model, margin {MARGIN:,}")
    ok = True
    if size > MAX_BYTES:
        ok = False
        _fail(f"{size:,} B exceeds MAX_BYTES={MAX_BYTES:,}")
        _fail("The 413 came from an 18,095 B prompt: 4,332 tok, 54% of the request.")
    if worst > TPM_CEILING - MARGIN:
        ok = False
        _fail(f"worst case {worst:,} tok leaves under {MARGIN:,} of margin under "
              f"the {TPM_CEILING:,} ceiling")
    if ok:
        print(f"  ok    {MAX_BYTES - size:,} B of headroom, "
              f"{TPM_CEILING - worst:,} tok under the ceiling")
    return ok


# Files that quote this prompt's size in prose, and must not drift from it.
# Gate 4 reads the byte figures out of them and compares against reality.
SIZE_CITERS = (
    Path("ARCHITECTURE.md"),
    Path("src") / "astro_ai" / "llm.py",
    Path("scripts") / "verify_natal_prompt.py",
    Path("scripts") / "eval_natal_prompt.py",
)
_SIZE_CITATION = re.compile(r"\b(\d{1,3},?\d{3}) B\b")
# A line only counts as citing THIS prompt if it says so. Without this the gate
# flags every unrelated byte figure in the same files — Marcellus at 14,552 B,
# the homepage at 13,151 B — which is how a gate gets switched off.
_ABOUT_THIS_PROMPT = ("natal.txt", "system prompt", "The system prompt")
# The size that caused the 413. Quoted in several places as history and
# deliberately frozen there.
PRE_COMPRESSION_BYTES = 18_095


def gate_4_no_stale_size_citations(text: str) -> bool:
    """Prose that quotes this file's size must still be telling the truth.

    This exists because the drift happened TWICE in one afternoon, both times
    in the same way: an edit changed the prompt's size, updated some of the
    numbers on the line it was already editing, and left a neighbour behind.
    The first left a token saving of 1,250 beside a byte figure it had just
    corrected; the second moved everything by 3 tokens by adding one word.
    Both were caught by a human reading carefully, which is not a mechanism.

    Only BYTE figures are checked, not token counts: bytes are free to compute
    anywhere, whereas an honest token count needs tiktoken, which is a dev
    dependency this gate must not require. In practice the two move together —
    every drift so far has moved both — so the cheap check catches the case.

    The pre-compression 18,095 B is deliberately outside the pattern's range:
    it is a historical measurement of a file that no longer exists, and it is
    supposed to stay exactly as it is.
    """
    print("Gate 4 - no stale size citations")
    actual = len(text.encode("utf-8"))
    ok, checked = True, 0
    for rel in SIZE_CITERS:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not any(marker in line for marker in _ABOUT_THIS_PROMPT):
                continue
            cited = [int(c.replace(",", "")) for c in _SIZE_CITATION.findall(line)]
            # The pre-compression size is a fixed historical fact about a file
            # that no longer exists, and several lines narrate it on purpose
            # ("natal.txt reached 18,095 B and took /kundli down"). Those must
            # not be dragged forward — a line citing ONLY history is correct.
            cited = [c for c in cited if c != PRE_COMPRESSION_BYTES]
            if not cited:
                continue
            checked += 1
            # At least one figure on the line must be the CURRENT size. A line
            # may legitimately carry historical sizes alongside it — "18,095 B
            # -> 13,135 B" is the whole point of the decision-log row — so the
            # test is that the line has not lost touch with the present, not
            # that every number on it is today's.
            if actual not in cited:
                ok = False
                _fail(f"{rel}:{n} cites {cited} B for this prompt, none of them "
                      f"the current {actual:,} B")
                _fail(f"        {line.strip()[:96]}")
    if not checked:
        ok = False
        _fail("no line in any of the SIZE_CITERS mentions this prompt's size, so "
              "this gate is checking nothing — the citations moved or the markers "
              "in _ABOUT_THIS_PROMPT went stale")
    elif ok:
        print(f"  ok    {checked} citation line(s), all current at {actual:,} B")
    return ok


# Claims #398 removed because they were measured against Rao Ch. 34 / §11 and
# found wrong, unsourced or cross-assigned (knowledge/remedies.md §12,
# divisional_charts.md). Gate 2 asks whether rules are still STATED; nothing
# else asked whether a corrected claim had crept back, and these came from
# training-data folk practice, which is exactly what a later edit reintroduces.
# Matching is case-insensitive and hyphen/space-agnostic.
#
# Surya Namaskar (#398 slice 4). remedies.md 12 row 2: 0 hits for any of 4
# spellings of "Surya Namaskar" and any of 3 of "namaskar" across all 94,019
# corpus lines. The first FORBIDDEN row for it was two literals --
# `Surya[- ]?Namaskar|Sun[- ]salutation` -- and the tree already held a THIRD
# spelling it missed ("the classical Sun Namaskar", learn_registry.py), which is
# the #467 shape: a pattern bound to the strings that happened to be found.
# So this is built from parts. A bare "Namaskar" is NOT forbidden (it is also a
# greeting, and "Guru Namaskar" in numerology.py is a different, un-retired
# practice); what is forbidden is a namaskar tied to the Sun by a name beside
# it or by a practice word in the same sentence, a Sun-salutation, or the
# "twelve rounds / postures" shape the retired text was made of.
_PARASH = (r"(?:Parashar\w*|Parasar\w*|Brihat\s+Parashar\w*|Brhat\s+Parashar\w*"
           r"|पाराशर\w*|पराशर\w*)")
_POSS = r"(?:['\u2019]s?)?"
_TITLE = r"(?:(?:classical|ancient|great|sage|rishi|maharishi|maharshi|saint)\s+)*"
_NAM = r"nam[\w\u0300-\u036f]{0,3}k[aā\u0300-\u036f]*r[\w\u0300-\u036f]*"
_SUNNAME = (r"(?:s[uū]ry[aā]?|s(?:oo|u)riy[aā]?|soory[aā]?|s[uū]r[aā]j|sun|aditya|ravi|bhaskar)")
_PRACTICE = r"(?:sun|surya|sunrise|dawn|east|rounds?|postures?|poses?|asanas?|yoga)"
_SEP = r"[\s\-_/.,:()*]"
SURYA_NAMASKAR = (
    rf"\b{_SUNNAME}{_SEP}{{0,4}}{_NAM}"
    rf"|{_NAM}{_SEP}{{0,3}}(?:(?:of|to|for)\s+)?(?:the\s+)?(?:rising\s+)?{_SUNNAME}\b"
    rf"|{_NAM}[^.;\n]{{0,60}}?\b{_PRACTICE}\b"
    rf"|\b{_PRACTICE}\b[^.;\n]{{0,60}}?{_NAM}"
    # "a sun salute each morning" and "salute the rising Sun" are the same practice
    # in other words; "Salutations to Surya" (the shloka's meaning) is not.
    r"|\bsun[\s\-_]*salut\w*|\bsalut(?:e|es|ed|ing)\s+(?:the\s+)?(?:rising\s+)?sun\b"
    r"|\b(?:12|twelve)[\s\-]+(?:\w+[\s\-]+)?(?:rounds?|postures?|poses?|asanas?)\b"
    # Devanagari (i18n.py carries the Hindi copy, with no native reader to catch a
    # reinstatement). The bare Hindi word for "greetings" is legal; only the
    # Sun-prefixed compound is the practice. [\u0900-\u097f] rather than \w,
    # because the virama and the vowel signs are not word characters.
    r"|(?:स[ूु]?र्य|स[ूु]रज)[\s\-_/.,]{0,3}नम[\u0900-\u097f]{1,4}क[\u0900-\u097f]{0,2}र"
)

FORBIDDEN = (
    (r"red[- ]lentils?|masoor|masur", "Sun's grain is wheat; red lentil is in no book we hold"),
    (SURYA_NAMASKAR, "proved absent from all 14 books (remedies.md 12 row 2)"),
    (r"milk offering", "Shiva is the Sun's deity, not the Moon's (Table 78)"),
    (r"Hanuman intercession", "Saturn -> Vishnu, Brahma; Hanuman only via Mars with Saturnine influence"),
    (r"(?:serv(?:e|es|ing|ice)|support(?:ing)?|help(?:ing)?)(?:\s+to)?\s+(?:the\s+)?(?:outsiders|marginali[sz]ed)",
     "unsourced (serve/serving/service to/support outsiders or the marginalised); Rao's Rahu deed is a donation to research or a pilgrimage"),
    (r"sesame[- ]oil|(?:\btil|teel)[- ]oil", "unsourced; sesame is Saturn's and Rao gives Ketu no grain or oil"),
    (r"black[- ]sesame", "'black' is ours; Rao says sesame"),
    (r"per Parashara", "misattributed: his rule is a ten-chart count, not a D-9 gate"),
    (r"fully manifested", "Rao §11.7.2 / §11.11 deny that any one factor settles a yoga"),
)


def gate_5_no_retired_claims(text: str) -> bool:
    print("Gate 5 - no retired claims")
    ok = True
    for pattern, why in FORBIDDEN:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            ok = False
            _fail(f"/{pattern}/ matched {m.group(0)!r} - {why}")
    if ok:
        print(f"  ok    {len(FORBIDDEN)} retired claims absent")
    return ok


# The hymn vocabulary Gate 6 (summaries) and Gate 7 family F share. Defined
# here, above SUMMARY_FORBIDDEN, because a summary said "Jupiter safe universal
# practices ... Vishnu Sahasranama" to the LLM for as long as the pages did, and the
# two gates must not be able to disagree about what counts as certifying it.
# "Sahasranam" without the trailing -a is the commoner Indian spelling, and
# the Hindi surface has no native reader, so both are the likeliest way the
# retired claim comes back. QA round 4 measured each escaping family F.
_HYMN = r"(?:Sahasranama?|सहस्रनाम)"
# "Sri Lalita Sahasranama" is remedies.md 8's own practice (Sri Yantra section).
# Python lookbehinds are fixed-width, so one per separator length: QA round 1
# measured "Lalita-Sahasranama" and "Lalita  Sahasranama" firing as the Vishnu
# hymn, and the Hindi/"Lalitha" spellings are the likeliest next ones.
_LALITA_SEP = r"[\s\-\u2010\u2011]"
_HYMN_NOT_LALITA = "".join(
    rf"(?<!{name}{_LALITA_SEP}{{{k}}})"
    for name in ("Lalita", "Lalitha", "ललिता") for k in (1, 2, 3)) + _HYMN
# Words that CERTIFY a practice rather than mention it. "safe for anyone to
# recite" is deliberately not here: it is the register slice 3 kept for the
# Saturn pages, and the tree carries it as plain description.
_HYMN_CERT = (r"(?:universal(?:ly)?|classical(?:ly)?|primary|powerful"
              r"|safe\s+(?:universal|foundation|practice|mantra|fallback)"
              r"|most\s+(?:classical\w*|cited|reliable|direct))")
HYMN_CERTIFIED = (rf"{_HYMN_NOT_LALITA}[^.\n]{{0,140}}{_HYMN_CERT}"
                  rf"|{_HYMN_CERT}[^.\n]{{0,140}}{_HYMN_NOT_LALITA}")

# K. The Graha Maitri ladder collapsed to three rungs (#398 slice 6). The
# koota is graded -- matching.md vv.27-28: friend+friend or one lord for both
# signs 5, friend+neutral 4, neutral+neutral 3, friend+enemy 2, neutral+enemy 1,
# enemy+enemy 0 (matching.py _graha_maitri_score) -- and the Ashtakoot article
# said "friends 5, neutral partial, enemies 0", which gives 0 to the 44 of 144
# rashi pairs that really score 1 or 2. "Enemies, 0" is NOT wrong on its own:
# enemy+enemy IS 0, so a bare "mutual enemies, 0" and the matrix row
# "enemy + enemy 0" stay legal. What is forbidden is the three-rung SHAPE:
#   (a) "neutral, partial" / "neutral -> half" -- the middle rung is one of
#       three numbers (4, 3, 1), never "partial";
#   (b) an "if ... enemies, 0" with no "both"/"mutual"/"each" in it, i.e. 0 for
#       any enemy at all, plus its "enemies get/score nothing" spellings.
_ARROW = r"[\s,:=\-\u2010-\u2015\u2192>(]*"
_ENEMY = r"(?:enem(?:y|ies)|inimical|hostile|foes?|unfriendly|enmity|adversar\w+|shatru\w*)(?:\s+(?:planets?|lords?|grahas?|signs?))?"
_ZERO = r"(?:0|zero|nil|nothing|no\s+points?)"
_NOT_BOTH = r"(?:(?!\bboth\b|\bmutual\w*|\beach\b|\bpair\b)[^.\n]){0,40}?"
GRAHA_MAITRI_MISSTATED = (
    rf"\bneutral(?:s|\s+(?:lords?|planets?|signs?|pair))?\b{_ARROW}(?:(?:gives?|gets?|scores?|earns?|receives?|yields?|is|are|means?)\s+)?"
    rf"(?:a\s+)?(?:partial|half|some|reduced|middling|medium|in[\s\-]between)\w*"
    # A bare plural "enemies, 0" opening a list item or table cell ("friends 5,
    # neutrals 3, enemies 0"). Anchored to a delimiter because "if both lords are
    # enemies, 0" is enemy+enemy and correct, and lookbehind cannot be variable.
    rf"|(?:^|(?<=[;,.(\n=:])|(?<=\band)|(?<=\bor))\s*\benemies\b{_ARROW}{_ZERO}\b"
    rf"|\b(?:if|when|where|should)\b{_NOT_BOTH}\b{_ENEMY}\b{_ARROW}(?:then\s+)?{_ZERO}\b"
    rf"|\b(?:if|when|where|should)\b{_NOT_BOTH}\b{_ENEMY}\b[^.\n]{{0,15}}?\b(?:score|scores|get|gets|receive|receives"
    rf"|earn|earns|give|gives|yield|yields)\s+{_ZERO}\b"
    # Hindi: no Graha Maitri copy exists in i18n.py today; "if the lords are
    # enemies, 0" is the only shape worth pinning without a native reader.
    r"|\u092f\u0926\u093f[^.\n\u0964]{0,40}?\u0936\u0924\u094d\u0930\u0941[\u0900-\u097f]*(?:\s+[\u0900-\u097f]+){0,2}[\s,:=\-]*(?:0|\u0966|\u0936\u0942\u0928\u094d\u092f)"
)

# L. Rahu and Ketu "outside Parashara's grid" (#398 slice 6). grahas.md 11.1
# gives the seven-planet table as the classical one AND gives Rahu/Ketu
# friendships (friendly with Venus and Saturn, enemies of Sun, Moon, Mars,
# neutral with the rest -- "traditions vary here more than for the classical 7").
# So the sourced statement is "the standard table covers seven planets; the
# two nodes' friendships come from tradition and vary". Four pages said instead
# that the grid is Parashara's, that it "predates their formal inclusion in the
# graha family", that it "was built for the 7-planet model", and that modern
# practice "uses ad-hoc rules" -- history grahas.md does not carry. Forbidden:
# the attribution of a friendship table to Parashara/BPHS, the "predates" and
# "7-planet model" history, "ad-hoc rules" for the nodes, and an absence from a
# CLASSICAL/Parashara/ancient/original grid ("Outside the standard
# natural-friendship table" is the sourced wording and stays legal).
_FGRID = r"(?:grid|table|chart|matrix|scheme)s?"
_GRID_WORD = r"(?:natural[\s\-]*|friendship[\s\-]*|maitri[\s\-]*|naisargika[\s\-]*)"
RAHU_KETU_GRID = (
    rf"\b(?:{_PARASH}|BPHS){_POSS}[\s\-]+(?:{_GRID_WORD}|classical[\s\-]+|own[\s\-]+){{1,4}}"
    rf"(?:{_FGRID}|maitri|friendships?)\b"
    rf"|(?:\bnot|n['\u2019]t|\bnever)\s+(?:be\s+)?(?:part\s+of|appear(?:ing)?|(?:included|listed|covered|found|present|given|shown)"
    rf"(?:\s+(?:in|on|by))?|in)\s+(?:the\s+|any\s+)?(?:\w+[\s\-]+){{0,2}}?"
    rf"(?:classical|{_PARASH}|BPHS|ancient|traditional|original|canonical)[\w'\u2019\s\-]{{0,40}}?{_FGRID}"
    rf"|\b(?:excluded|left\s+out|absent|missing|omitted|outside)(?:\s+(?:from|of))?\s+(?:the\s+|any\s+)?(?:\w+[\s\-]+){{0,2}}?"
    rf"(?:classical|{_PARASH}|BPHS|ancient|traditional|original|canonical)[\w'\u2019\s\-]{{0,40}}?{_FGRID}"
    # Hindi: "पराशर की मैत्री तालिका". i18n.py carries no such copy today.
    r"|(?:पाराशर|पराशर)\w*\s+(?:की|के|का)\s+(?:नैसर्गिक\s+)?(?:मैत्री|तालिका|ग्रिड)"
    # The reverse shape: the grid is the subject and the node is what it lacks.
    rf"|(?:classical|{_PARASH}|BPHS|ancient|traditional|original|canonical)[\w'\u2019\s\-]{{0,40}}?{_FGRID}\s+"
    rf"(?:(?:does\s+not|doesn['\u2019]t|did\s+not|didn['\u2019]t|never)\s+)?"
    rf"(?:include|cover|list|contain|mention|know|exclude|omit|has\s+no|have\s+no|lacks?)\w*\s+(?:both\s+)?(?:Rahu|Ketu)"
    # History the corpus does not carry, in the other words it can be put.
    r"|\bpredat\w+\s+(?:the\s+)?(?:nodes|lunar\s+nodes|shadow\s+planets)"
    r"|\b(?:original|older|earlier|early)\s+(?:7|seven)[\s\-]planet"
    r"|\bonly\s+knew\s+(?:of\s+)?(?:the\s+)?(?:7|seven)\b"
    r"|\b(?:added|included|admitted|counted)\s+(?:later|afterwards|subsequently)\b"
    r"|\bbefore\s+(?:Rahu|Ketu)[^.\n]{0,30}\bwere\s+(?:counted|added|included|recogni[sz]ed)"
    r"|\bpredat\w+[^.\n;]{0,60}?(?:formal\s+inclusion|inclusion|graha\s+family|nava?graha|nine[\s\-]graha)"
    r"|\b(?:Rahu|Ketu)\b[^.\n]{0,80}?\bpredat\w+"
    r"|\b(?:built|made|designed|drawn\s+up|written)\s+for\s+the\s+(?:7|seven)[\s\-]planet"
    r"|\bad[\s\-]?hoc\s+(?:rules?|assignments?|conventions?|friendships?|relationships?)\b"
)

# --- #398 slice 7 ------------------------------------------------------------
# Five more reader-facing defects, each checked against knowledge/*.md first.
# Written wider than the literals found (the #467 finding: a pattern bound to
# one spelling is a gate that goes green on the first rewording).

# M. Jupiter as "Mercury's natural enemy". grahas.md 11.1: Mercury's enemy is the
# Moon and Jupiter is NEUTRAL to it; Jupiter's enemies are Mercury and Venus. So
# the relation is one-way: "Jupiter counts Mercury among its enemies" and "Mercury
# is Jupiter's enemy" are true, "Jupiter is Mercury's enemy" and "Mercury and
# Jupiter are natural enemies" are not. The window refuses to cross a ';' or the
# word Moon/neutral, so a sentence that correctly names the Moon stays legal.
_MJ_NOT_MOON = r"(?:(?!Moon|Chandra|neutral)[^.\n;])"
_MJ = r"(?:Jupiter|Guru|Brihaspati|Brhaspati)"
_MERC = r"(?:Mercury|Budha)"
_ENEMY_N = r"(?:enem(?:y|ies)|foes?|inimical|hostile|adversar\w+)"
MERCURY_JUPITER_ENEMY = (
    rf"\b{_MJ}\b{_MJ_NOT_MOON}{{0,60}}?\b{_MERC}['’]?s?\s+(?:natural\s+|sworn\s+|classical\s+|own\s+)?{_ENEMY_N}"
    rf"|\b{_MERC}['’]?s\s+(?:natural\s+|sworn\s+|classical\s+|own\s+)?{_ENEMY_N}{_MJ_NOT_MOON}{{0,40}}?\b{_MJ}\b"
    rf"|\b{_MERC}\b{_MJ_NOT_MOON}{{0,30}}?\b(?:and|&|with|\+)\s+{_MJ}\b{_MJ_NOT_MOON}{{0,25}}?\b(?:are|being|as|remain)\s+(?:\w+\s+){{0,2}}?{_ENEMY_N}"
    rf"|\b{_MJ}\b{_MJ_NOT_MOON}{{0,30}}?\b(?:and|&|with|\+)\s+{_MERC}\b{_MJ_NOT_MOON}{{0,25}}?\b(?:are|being|as|remain)\s+(?:\w+\s+){{0,2}}?{_ENEMY_N}"
    rf"|\b{_MERC}\s+(?:considers?|treats?|sees?|regards?|counts?|views?)\s+{_MJ}\b{_MJ_NOT_MOON}{{0,30}}?{_ENEMY_N}"
    # Hindi: "बुध का शत्रु गुरु"
    r"|बुध[^.\n।]{0,30}(?:गुरु|बृहस्पति)[^.\n।]{0,30}शत्रु"
)

# N. Vishnu worship / Ekadashi vrat / Satya Narayan Katha as a MANGLIK (Mars)
# remedy. remedies.md 7.1 maps Mars to Hanuman, Rudra, Kartikeya (Subrahmanya)
# and Narasimha, and vedic_reference.md 1.5 lists matching, a Mars-deity text,
# Tuesday toor daal and (only after review) coral -- no Vishnu rite. Narasimha IS
# a form of Vishnu (remedies.md 7.2), so "Narasimha, the man-lion form of Vishnu"
# stays legal: what is forbidden is a Vishnu RITE beside Manglik/Mars in one
# sentence, or the shipped list "Hanuman practices + Vishnu worship + Kumbh Vivah".
_VISHNU_RITE = r"(?:Vishnu|Narayan\w*)\W+(?:\w+\W+){0,2}?(?:worship|puja|vrat|katha|mantra|stotra|sahasranama?)"
_RITE_ALONE = r"(?:Ekadashi\s+(?:vrat|fast\w*)|Satya[\s\-]*Narayan\w*(?:\s+(?:katha|puja|vrat))?)"
_MANGLIK_N = r"(?:Manglik|Mangal(?:ik)?\b|Kuja|Mars\b)"
_NEG = r"(?:(?!\bnot\b|n['’]t\b|\bnor\b|\bnone\b|\bnever\b)[^.\n;])"
VISHNU_FOR_MANGLIK = (
    rf"\b{_MANGLIK_N}{_NEG}{{0,80}}?\b(?:{_VISHNU_RITE}|{_RITE_ALONE})"
    rf"|\b(?:{_VISHNU_RITE}|{_RITE_ALONE}){_NEG}{{0,80}}?\b{_MANGLIK_N}"
    r"|\bsoften\w*\b[^.\n;]{0,60}?\bVishnu\s+worship"
    r"|\bVishnu\s+(?:worship|puja)\s*(?:\+|,|and|&|then|followed\s+by)\s*(?:then\s+)?Kumbh"
    r"|\bKumbh\s+Vivah\s*(?:\+|,|and|&)\s*Vishnu\s+(?:worship|puja)"
    r"|\bVishnu\s+worship\s+for\s+(?:an?\s+)?(?:uncancelled\s+|severe\s+)?Manglik"
)

# O. Monday Shiva worship as the first / classical / primary remedy for Kaal Sarp
# (kaal-sarp-dosh-remedies; learn_registry). remedies.md 7.1: Rahu -> Durga,
# Narasimha; Ketu -> Ganesha; Shiva is the SUN's deity (7.1, 7.2). vedic_reference.md
# 3.2/8.1 call KSD post-classical and name Trimbakeshwar puja a folk practice, and
# remedies.md 12 row 11 records weekday observance as unsourced as stated. So Monday
# Shiva may be described as a devotional tradition; it may not be ranked or called
# classical. The window is short (50) and a ';' ends it, because the summary line
# "...classical, the rest is tradition: (1) Rahu: Durga...(Monday Shiva worship..." is
# the correct text and sits ~70 characters from the word "classical".
# _GAP never crosses a full stop, ';' or a newline: "...are classical. Monday Shiva
# worship, Nag Panchami..." is two sentences and the correct text.
_GAP = r"[^\w.;\n!?]+"
_MON_SHIVA = (rf"(?:Mondays?{_GAP}(?:[\w+/]+{_GAP}){{0,4}}?Shiv\w*"
              rf"|Shiv\w*{_GAP}(?:[\w+/]+{_GAP}){{0,4}}?(?:on\s+|every\s+|each\s+)?Mondays?\b)")
_RANK = (r"(?:classical(?:ly)?|first|foremost|primary|essential|the\s+master|begins?\b"
         r"|most\s+(?:accessible|effective|important|reliable|powerful|direct)"
         r"|starting\s+point|real\s+remed\w+|must\b|peak)")
KSD_SHIVA_FIRST = (
    rf"{_MON_SHIVA}[^.;\n]{{0,50}}?\b{_RANK}"
    rf"|\b{_RANK}[^.;\n]{{0,50}}?{_MON_SHIVA}"
    r"|\b(?:begin|start)s?\s+with\s+(?:\w+\s+){0,2}?Shiv\w*"
    r"|\bShiv\w*\s+(?:worship|puja)\s+(?:is|as)\s+(?:the\s+)?(?:first|primary|foremost|starting|most)\b"
    r"|\b1[.)]?\s+(?:Shiv\w*\s+(?:worship|puja)\s+on\s+Mondays?|Monday\s+Shiv\w*)"
    r"|\(1\)\s+Monday\s+Shiv\w*"
)

# P. A tradition or a regional custom called classical, in the Kaal Sarp remedies.
# KSD is post-classical (vedic_reference.md 3.2) and Trimbakeshwar puja is "folk
# practice, never scripture" (vedic_reference.md 8.1); Nag Panchami and the silver
# serpent pair are not in remedies.md at all. Only the nodes' deities (7.1) and the
# bija mantras (6.3) are classical there.
_KSD_PRACTICE = (r"(?:Nag\s+Panchami|Trimbak\w*|Nagbali|silver\s+serpents?|Nag[\s\-]*Nagini"
                 r"|serpent[\s\-]worship|(?:Kaal\s*Sarp|KSD|Kalsarp)(?:['’]s)?\s+(?:remed\w+|peak))")
KSD_TRADITION_AS_CLASSICAL = (
    # "not a classical ..." is the correct text ("A traditional practice, not a classical remedy").
    rf"(?<!not\s)(?<!not\sa\s)(?<!not\sthe\s)\bclassical(?:ly)?{_GAP}(?:[\w'’\-]+{_GAP}){{0,3}}?{_KSD_PRACTICE}"
    rf"|{_KSD_PRACTICE}(?:{_GAP}(?!not\b|n['’]t\b)[\w'’\-]+){{0,2}}?{_GAP}(?:(?:is|are|as|a|an|the)\s+)+classical(?:ly)?\b"
    r"|\b(?:KSD|Kaal\s*Sarp|Kalsarp)(?:['’]s)?\s+(?:peak|best|ideal)\s+remed\w+"
    r"|\b(?:7|seven)\s+classical(?:ly[\s\-]cited)?\s+remed\w+[^.\n]{0,30}?\b(?:Kaal\s*Sarp|KSD|Kalsarp)\b"
    # A count of "classical" remedies, only where the same string is about Kaal Sarp:
    # Rahu's and the Sun's summaries say "7 classical remedies" about other things.
    r"|(?:Kaal\s*Sarp|KSD|Kalsarp)[\s\S]{0,700}?\b(?:7|seven)\s+classical(?:ly[\s\-]cited)?\s+remed\w+"
    r"|\bclassically[\s\-]valid\b"
    r"|\b(?:peak|best|ideal)\s+(?:KSD|Kaal\s*Sarp)[\s\-]+remed\w+"
    r"|\bclassical\W{0,3}big\s+remedy"
)

# Q. "Universal safe" claimed for the non-Venus remedy pages. remedies.md 8 and 10.7
# reserve "the universal safe fallback" for Sri Yantra + Sri Sukta (the Venus page's
# own heading is legitimate), and 5/6 describe good deeds and mantras as the safe
# options without extending that to a deity list. Scoped to the four pages' shapes:
# the heading followed by a non-Venus planet, "these <planet> practices are safe for
# anyone", "the safest universal practices", "none can backfire", the Mars ranking,
# and the Saturn deity heading. "(safe for anyone)" on a GOOD-DEEDS heading is
# remedies.md 10.2's own wording and is deliberately not forbidden.
_NON_VENUS = r"(?:Saturn|Shani|Jupiter|Guru|Mercury|Budha|Mars|Mangal)"
NON_VENUS_UNIVERSAL_SAFE = (
    rf"universal\s+safe\s+(?:fallback|practice|remed\w+|foundation)(?=\W+(?:[\w'’]+\W+){{0,25}}?\b{_NON_VENUS}\b)"
    rf"|\b(?:these|the|our)\s+(?:universal\s+)?{_NON_VENUS}\s+practices\s+are\s+(?:safe\s+for\s+(?:anyone|everyone|any\s+chart)|universal)"
    r"|\b(?:the\s+)?safest\s+universal\s+(?:practices?|remed\w+)"
    # "none can backfire" only where the same string also names a non-Venus planet: the
    # Venus page's list IS Sri Sukta and Sri Yantra, which remedies.md 8 does certify.
    rf"|\b{_NON_VENUS}\b[\s\S]{{0,500}}?\bnone\s+(?:of\s+(?:them|these)\s+)?(?:can|could|will)\s+(?:ever\s+)?backfire"
    rf"|\bnone\s+(?:of\s+(?:them|these)\s+)?(?:can|could|will)\s+(?:ever\s+)?backfire[^\n]{{0,60}}?\b{_NON_VENUS}\b"
    rf"|\b{_NON_VENUS}\b\W+(?:[\w'’]+\W+){{0,6}}?universal\s+safe\s+(?:fallback|practice|remed\w+)"
    r"|\bmost\s+universally[\s\-]+recommended"
    r"|\bDeity\s+propitiation\s*\(\s*safe\s+universal"
    r"|\bsafe\s+for\s+any\s+chart,?\s+no\s+consultation"
)

# --- #398 slice 8 ------------------------------------------------------------
# Four more reader-facing defects, each checked against knowledge/*.md first.
# Written wider than the literals found (#467): spelling, spacing, case, order.

# R. A remedy page borrowing authority from a chapter or book nobody on this
# project has checked. BPHS is not in data/ (chart.py's comment on the deleted
# "(per BPHS)" attribution says so) and remedies.md 5/6/7 attribute the planet ->
# deity table and the good-deed/grain list to Rao's Ch. 34, not to a Parashara
# "<planet> adhyaya"; "Surya Samhita" is in no book we hold; "Sunday charity list per
# Muhurtha Chintamani" is a claim nothing shows is true. The pages' "Classical sources
# cited" callouts carried all four. The label itself is pinned only where it still
# sits over folk material (the two tail alternatives), because manglik- and
# pitru-dosh-remedies keep it over a different, unreviewed attribution that is not this
# slice's to change. Muhurat pages say "per Muhurtha Chintamani" for windows; only the
# charity-list shape is forbidden.
_PLANET_ANY = (r"(?:S[uū]rya|Sun|Chandra|Moon|Mangal|Mars|Budh\w*|Mercury|Guru|Jupiter|Shukra|Venus"
               r"|Shani|Saturn|Rahu|Ketu)")
_ADHYAYA = r"adhy?[aā]y\w*"
BPHS_REMEDY_ATTRIBUTION = (
    rf"\b(?:BPHS|B\.P\.H\.S\.|{_PARASH})[^.;\n]{{0,50}}?\b{_PLANET_ANY}\s+{_ADHYAYA}"
    rf"|\b{_PLANET_ANY}\s+{_ADHYAYA}"
    r"|\bS[uū]rya\s+Sa[mṃ]hit[aā]"
    r"|\b(?:charity|donation|daan|dana)\s+(?:list|items?)\s+(?:per|from|in|according\s+to)\s+(?:the\s+)?Muhurt\w*\s+Chintamani"
    r"|\bMuhurt\w*\s+Chintamani[^.;\n]{0,30}\b(?:charity|donation)\s+(?:list|items?)"
    rf"|\b(?:ones|remedies|practices)\s+(?:from|in)\s+(?:the\s+)?(?:BPHS|B\.P\.H\.S\.|{_PARASH})"
    r"|\bGraha[\s\-]*sh?(?:a|ā)+nth?[iī]\w*\s+tradition"
    r"|\bClassical\s+sources\s+cited[\s\S]{0,900}?not\s+traced\s+to\s+a\s+classical"
    r"|\bClassical\s+sources\s+cited[\s\S]{0,60}?(?:modern\s+)?folk\s+tradition"
)

# S. The bija mantras lent BPHS's name. remedies.md 6.3 calls them "widely-accepted
# ... universally cited across classical sources" and attributes them to no book; the
# two Rahu/Ketu pages said "the full classical form per BPHS is ...". A bare
# "per BPHS" elsewhere is still not forbidden (family I's comment has the count).
_BIJA = r"(?:beej|beeja|bheej|bija|seed)\w*"
_BPHS_NAME = rf"(?:BPHS|B\.P\.H\.S\.|{_PARASH})"
BIJA_PER_BPHS = (
    rf"\b{_BIJA}[^.;\n]{{0,80}}?\b(?:per|according\s+to|from|in|by|given\s+in)\s+(?:the\s+)?{_BPHS_NAME}"
    rf"|\b(?:per|according\s+to)\s+(?:the\s+)?{_BPHS_NAME}[^.;\n]{{0,60}}?\b{_BIJA}"
    rf"|\b(?:full|classical|original|standard)\s+(?:classical\s+)?(?:form|version)\s+(?:is\s+)?(?:per|from|in|according\s+to)\s+(?:the\s+)?{_BPHS_NAME}"
)

# T/U. Grain cross-assignments against Rao 34.3 (remedies.md 5.1): Saturn rules
# SESAME, Rahu rules BLACK GRAM (urad) daal, Ketu none. T: urad/black gram given as a
# Saturn practice -- it names Saturn, or sits beside Saturn's own sesame / iron /
# mustard oil in one list (saturn-in-10th-house-career had "black sesame, iron, mustard
# oil, or black gram (urad dal)" with no planet word in the bullet at all, and the
# sade-sati summary "donate black daal / mustard oil"). U: sesame given as a Rahu
# practice. The window refuses to cross the OTHER planet's name, so "this is Saturn's
# grain" (rahu-remedies, which flags the substitution honestly) stays legal.
# The look-around keeps "Anuradha" (a nakshatra, on a dozen pages) from reading as "urad".
_URAD = (r"(?<![A-Za-z])(?:urad|urd|udad|maash|black[\s\-]+(?:gram|daal|dal|dhal|lentils?)"
         r"|kaali[\s\-]+(?:daal|dal)|उड़द|उरद)(?![A-Za-z])")
_NOT_RAHU = r"(?:(?!Rahu|राहु)[^.;\n])"
_SATURN_ONLY = r"(?:Saturn|Shani|Sade[\s\-]*Sati|शनि)"
_SATURN_ITEM = r"(?:sesame|til\b|tila\b|teel\b|iron|mustard[\s\-]+oil|तिल)"
URAD_AS_SATURN = (
    rf"{_URAD}\b{_NOT_RAHU}{{0,100}}?\b{_SATURN_ONLY}"
    rf"|\b{_SATURN_ONLY}{_NOT_RAHU}{{0,100}}?{_URAD}"
    rf"|{_URAD}\b[^.;\n]{{0,60}}?\b{_SATURN_ITEM}"
    rf"|\b{_SATURN_ITEM}[^.;\n]{{0,60}}?{_URAD}"
)
_SESAME = r"(?:\b(?:sesame|til|tila|teel)\b|तिल)"
_NOT_SATURN = r"(?:(?!Saturn|Shani|शनि)[^.;\n])"
SESAME_AS_RAHU = (
    rf"(?:\bRahu\b|राहु){_NOT_SATURN}{{0,100}}?{_SESAME}"
    rf"|{_SESAME}{_NOT_SATURN}{{0,100}}?(?:\bRahu\b|राहु)"
)

# What Gate 6 forbids inside an llm_summary: FORBIDDEN, except that the bare
# "milk offering" is replaced by MILK_TO_SHIVA (the claim #398 actually
# retired is Moon -> Shiva; kaal-sarp-dosh-remedies has a Nag Panchami serpent
# milk offering, a different practice, and a bare pattern would force a
# rewrite of it to satisfy a regex), plus two patterns the system prompt never
# carried but the summaries did. Round 1 of QA found `rahu-remedies` saying
# "service to outsiders" past a literal "serve outsiders" - hence the widened
# FORBIDDEN rows above.
# Moon -> Shiva by milk, in the spellings seen or likely: "milk offering to
# Shiva", "milk offering to Lord Shiva", "milk abhishek of Shiva", "offer milk
# to Shivling". Every alternative needs milk and Shiva ADJACENT through a
# preposition, which is what keeps kaal-sarp-dosh-remedies legal: its
# "Monday Shiva worship + milk abhishek" has no "to/of/for Shiva" after the
# milk, and its Nag Panchami "serpent milk offering" has no Shiva at all.
MILK_TO_SHIVA = (
    r"milk[\s-]+(?:offerings?|abhishek(?:a|am)?|bath)\s+(?:to|of|for)\s+(?:Lord\s+|Bhagwan\s+)?Shiv"
    r"|(?:offer|offering|pour|pouring)\s+(?:of\s+)?milk\s+(?:to|on|over)\s+(?:Lord\s+|Bhagwan\s+)?Shiv"
)

SUMMARY_FORBIDDEN = tuple(
    (p, w) for p, w in FORBIDDEN if p != r"milk offering"
) + (
    (MILK_TO_SHIVA, "Shiva is the Sun's deity, not the Moon's (Table 78)"),
    # Per LINE, because a summary is bulleted and the planets sit on one bullet.
    # Saturday is Saturn's day, so "Hanuman ... Saturday" is the same folk rule
    # reached by the weekday. Hanuman as a MARS deity (Table 78) is untouched.
    (r"(?:Hanuman|Bajrang\w*|Maruti|Anjaneya)[^\n]{0,60}(?:Shani|Saturn|Saturday|Sade[- ]Sati)"
     r"|(?:Shani|Saturn|Saturday|Sade[- ]Sati)[^\n]{0,60}(?:Hanuman|Bajrang\w*|Maruti|Anjaneya)",
     "Saturn -> Vishnu, Brahma; Hanuman only via Mars with Saturnine influence (Rao 19504-19506)"),
    # "D-9 confirmation" in a MARRIAGE bullet is a different, sourced use and
    # does not match: the pattern needs the confirmation to come first.
    (r"confirmation in D-?9|Raja Yoga confirmation",
     "yoga manifestation is D-1/D-10, not a D-9 gate (Rao 20217-20219; divisional_charts.md:107-113)"),
    # Slice 6. Jupiter's and Mercury's summaries said "safe universal practices"
    # and listed the Vishnu Sahasranama (remedies.md 8: the universal safe
    # practice is the Sri Yantra; the hymn is in no book we hold). Same pattern
    # as Gate 7 family F's certifying half, so the two cannot disagree.
    (HYMN_CERTIFIED,
     "no book we hold names the Vishnu Sahasranama as ANY planet's practice, let alone a "
     "universal/classical/safe one (remedies.md 8, 11.2)"),
    (GRAHA_MAITRI_MISSTATED,
     "Graha Maitri is a six-rung ladder 5/4/3/2/1/0 (matching.md vv.27-28), not friends/neutral/enemies"),
    (RAHU_KETU_GRID,
     "grahas.md 11.1 gives Rahu/Ketu friendships; the standard table covers seven planets and the "
     "'Parashara / predates / ad-hoc' history is unsourced"),
    # Slice 7.
    (MERCURY_JUPITER_ENEMY,
     "grahas.md 11.1: Mercury is NEUTRAL to Jupiter; only Jupiter counts Mercury an enemy"),
    (VISHNU_FOR_MANGLIK,
     "remedies.md 7.1: Mars -> Hanuman, Rudra, Kartikeya, Narasimha; no book we hold gives a Vishnu "
     "rite, Ekadashi vrat or Satya Narayan Katha as a Manglik remedy"),
    (KSD_SHIVA_FIRST,
     "remedies.md 7.1: Rahu -> Durga, Narasimha; Ketu -> Ganesha; Shiva is the Sun's. Monday Shiva "
     "is a devotional tradition, never the first or classical Kaal Sarp remedy"),
    (KSD_TRADITION_AS_CLASSICAL,
     "vedic_reference.md 3.2/8.1: Kaal Sarp is post-classical and Trimbakeshwar puja is folk practice; "
     "Nag Panchami and the silver pair are in no remedies.md row"),
    # Slice 8.
    (BIJA_PER_BPHS,
     "remedies.md 6.3: the bija mantras are 'widely-accepted', attributed to no book; BPHS is not in data/"),
    (URAD_AS_SATURN,
     "Rao 34.3 (remedies.md 5.1): Saturn rules sesame seeds, Rahu rules black gram (urad) daal"),
    (SESAME_AS_RAHU,
     "Rao 34.3 (remedies.md 5.1): sesame is Saturn's grain; Rahu's is black gram (urad) daal"),
)


def gate_6_no_retired_claims_in_summaries(summaries=None) -> bool:
    """`summaries` is an iterable of (slug, text); default is the real registry.

    The parameter exists so `mutate_natal_prompt_gate.py` can feed it a
    re-broken summary without editing learn_registry.py.
    """
    print("Gate 6 - no retired claims in topic summaries (Article.llm_summary)")
    if summaries is None:
        from astro_ai.learn_registry import ARTICLES

        summaries = [(a.slug, a.llm_summary) for a in ARTICLES]
    summaries = [(slug, text) for slug, text in summaries if text]
    ok = True
    for slug, text in summaries:
        for pattern, why in SUMMARY_FORBIDDEN:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                ok = False
                _fail(f"{slug}: /{pattern}/ matched {m.group(0)!r} - {why}")
    if not summaries:
        ok = False
        _fail("no Article carries an llm_summary, so this gate is checking nothing")
    elif ok:
        print(f"  ok    {len(summaries)} summaries x {len(SUMMARY_FORBIDDEN)} "
              f"retired claims: none present")
    return ok


# --- Gate 7 ------------------------------------------------------------------

SRC = REPO_ROOT / "src" / "astro_ai"

# The reader-facing counterpart of FORBIDDEN/SUMMARY_FORBIDDEN, but only for
# the families slices 3-7 of #398 fixed. Patterns are wider than the
# literals that were found (QA measured 17 of 38 spelling variants slipping
# past the first Gate 5 patterns): hyphen/space-agnostic, singular/plural,
# Devanagari where i18n.py carries a Hindi copy.
_HANU = r"(?:Hanuman|Bajrang\w*|Maruti|Anjaneya|हनुमान)"
_SATURN = r"(?:Shani|Saturn|Saturday|Sade[- ]Sati|शनि)"
# A window must not run across an arrow or a ';' - "Mars -> Hanuman; ...;
# Saturn -> Vishnu" is the correct table and must stay legal. Tags are blanked
# before matching, so the window is wide enough to cross "</strong>".
_NO_ARROW = r"(?:(?!→|->)[^.\n;])"
_HANUMAN_SATURN = (
    # ", Saturn -> Vishnu" after a Mars entry is the correct table, not the claim.
    rf"{_HANU}{_NO_ARROW}{{0,100}}?{_SATURN}(?!\w*\s*(?:→|->))"
    rf"|{_SATURN}{_NO_ARROW}{{0,100}}?{_HANU}"
    rf"|{_SATURN}\s*(?:→|->)\s*{_HANU}"
)
_DONOR_VERB = (
    r"(?:serv(?:e|es|ed|ing|ice|ices)|support(?:s|ing)?|help(?:s|ing)?"
    r"|donat(?:e|es|ed|ing|ion|ions)|feed(?:s|ing)?|offer(?:s|ed|ing|ings)?"
    r"|giv(?:e|es|ing)|gave)"
)
READER_FORBIDDEN = (
    (r"red[- ]*lentils?|masoor|masur|मसूर",
     "A: Sun's grain is wheat, Mars's is toor daal; red lentil is in no book we hold"),
    (MILK_TO_SHIVA
     + r"|milk\s*(?:\(abhishek\))?\s+(?:at|to|over|on)\s+(?:a\s+|the\s+)?(?:Lord\s+)?Shiv"
     + r"|Shiv\w*\s+(?:abhishek\w*|puja)[^.;\n]{0,40}\bmilk"
     + r"|\b(?:Moon|Chandra)\b(?:\s*(?:→|->)\s*|(?:(?!→|->)[^.\n;,]){0,40}?)\bShiv",
     "B: Moon -> Gauri, Lalita, Saraswati, Krishna; Shiva is the Sun's (Table 78)"),
    (_HANUMAN_SATURN,
     "C: Saturn -> Vishnu, Brahma; Hanuman only via Mars with Saturnine influence "
     "- unless the sentence labels it popular/folk tradition AND names the Mars route"),
    (r"sesame(?:[- ]+seeds?)?[- ]+oil|(?:\btil|\bteel|\btila|gingelly)[- ]+oil"
     r"|\btil(?:\s+ka)?\s+tel\b|oil\s+of\s+sesame|तिल\s*(?:का|के)\s*तेल"
     # The oil was the only literal, so the CROSS-ASSIGNMENT underneath it walked
     # through: QA pasted "sesame seeds and black lentils" and "offer sesame +
     # black lentils" back into two Ketu records and the whole sweep stayed green.
     # Sesame paired with BLACK LENTILS is the Ketu shape -- Saturn's own rows say
     # "urad daal", never "black lentils" -- so this pins it without needing the
     # planet, which a string in `numerology.py` does not carry.
     r"|sesame[^.;\n]{0,40}black\s+lentils|black\s+lentils[^.;\n]{0,40}sesame",
     "D: unsourced; sesame is Saturn's and Rao gives Ketu no grain or oil"),
    # The donor NOUNS were only `outsiders|marginalised`, so the verbatim string
    # this slice was filed about -- "Offer to lepers, outcasts, or homeless on
    # Saturday sunset" -- reinstated green. Widened to the whole family.
    (rf"{_DONOR_VERB}(?:\s+(?:to|of|for))?\s+(?:[\w'-]+[\s/,]+){{0,4}}?"
     rf"(?:outsiders?|marginali[sz]ed|lepers?|outcast\w*)",
     "E: unsourced; Rao's Rahu deed is a donation to a research organisation or a "
     "pilgrimage, and Saturn's is physical labour and manual labourers"),

    # F. The claim slice 3 introduced while retiring family C: it replaced
    # Hanuman with Vishnu (correct, Table 7.1) and then named a HYMN as the
    # practice and ranked it -- "the most universal Saturn practice" -- in nine
    # reader-facing places. `sahasranama` returns one hit in `knowledge/`, and it
    # is LALITA Sahasranama in the Sri Yantra section. Scoped to one sentence, so
    # "For Saturn delays: ... . For general 10th house strengthening: Vishnu
    # Sahasranama" stays legal: there the hymn is the 10th house's, not Saturn's.
    # Slice 5 (#465) widened it past Saturn: the same hymn was "the classical
    # universal Mercury remedy" and "the universal safe mantra" for Jupiter. The
    # deity link there IS sourced (Table 7.1), so a hymn beside a planet stays
    # legal; what is forbidden is the hymn beside a CERTIFYING word. The Lalita
    # Sahasranama is exempt because remedies.md 8 does name it, under Sri Sukta.
    (rf"{_SATURN}[^.;\n]{{0,140}}{_HYMN}|{_HYMN}[^.;\n]{{0,140}}{_SATURN}|{HYMN_CERTIFIED}",
     "F: the deity is sourced (Vishnu for Mercury, Jupiter and Saturn - Table 7.1); no book "
     "we hold names a hymn as ANY planet's practice, let alone calls one universal/classical/safe"),

    # G. A reader-facing remedy line borrowing authority from a source name. NOT a
    # blanket ban -- source names are deliberate and pervasive elsewhere (Cheiro,
    # Johari, Phaladeepika, Saravali) -- just this construction, which is how the
    # same wrong attribution survived on two pages: the grain tables are Rao's
    # (remedies.md 5.1/13.1), and BPHS is not where they come from.
    (r"\bper\s+(?:the\s+)?(?:BPHS|Brihat\s+Parashara\w*|Parashara\w*|Phaladeepika|Saravali"
     r"|Rao'?s?|Raman'?s?)\s+remedial\s+tradition"
     r"|classical\s+grain\s+per\s+\w+",
     "G: a remedy line must not borrow authority from a source name on a reader-facing "
     "page, and the grain tables are Rao's, not BPHS's"),

    # H. Surya Namaskar, retired by #398 slice 4. Same pattern Gates 5/6 use, so a
    # spelling cannot be legal on a page and illegal in the prompt.
    (SURYA_NAMASKAR,
     "H: Surya Namaskar / Sun salutation is in none of the 14 books (remedies.md 12 row 2); "
     "the Sun's sourced practices are a temple visit or gift, wheat, Shiva/Rama, and its mantra"),

    # I. "(per Parashara's grid)" -- a source name lent to a rule the corpus does not
    # attribute to him. The Graha Maitri scoring is Muhurta Chintamani's (matching.md
    # vv.27-28), not BPHS's, and BPHS is not in data/ at all. The owner's rule is that
    # no source appears in reader-facing text; this is the construction by which one
    # did. SCOPE, measured on the tree: Parashara-named "per/according to" is banned
    # outright (0 other hits), and BPHS-named only when it is followed by a grid-like
    # noun. "Parashara's natural-friendship grid" (rahu/ketu-in-vedic-astrology, the-9-grahas,
    # shani-saturn) was NOT banned here in slice 4 -- it is a different claim (grahas.md 11.1
    # gives Rahu/Ketu friendships, which those sentences denied) -- and is family L since
    # slice 6, which also fixed the four pages. A bare "per BPHS" is NOT banned: it sits on five pages (rahu/ketu beej
    # mantras, dhana yoga, matching.html Tara, about.html's own explanation of the
    # phrase) that are separate claims needing their own sourcing, and banning it here
    # would turn main red over work this slice does not do.
    (rf"\b(?:(?:as\s+)?per|according\s+to|as\s+(?:given|laid\s+down|set\s+out|prescribed|stated)\s+(?:by|in))"
     rf"\s+(?:the\s+)?{_TITLE}{_PARASH}"
     rf"|\b(?:(?:as\s+)?per|according\s+to|following|using|from|by|in|under)\s+(?:the\s+)?(?:{_PARASH}|BPHS|B\.P\.H\.S\.)"
     rf"{_POSS}\s+(?:own\s+|classical\s+|natural\s+)?(?:grid|matrix|table|scoring|scheme|scale)s?\b"
     rf"|\b(?:{_PARASH}|BPHS){_POSS}[\s\-]+(?:(?:own|classical|friendship|maitri)[\s\-]+)?(?:grid|matrix)\b"
     rf"|\b(?:grid|matrix)\s+(?:of|from|by|in)\s+(?:the\s+)?(?:{_PARASH}|BPHS)"
     # Hindi: "पराशर के अनुसार", "पराशर ग्रिड". No native reader checks this copy.
     r"|(?:पाराशर|पराशर)[\u0900-\u097f]*\s*(?:जी\s*)?(?:के\s+|की\s+|का\s+)?(?:अनुसार|मतानुसार|ग्रिड|तालिका)",
     "I: a rule must not borrow Parashara's name on a reader-facing page: the Graha Maitri "
     "grid is Muhurta Chintamani's (matching.md vv.27-28) and BPHS is not in data/"),

    # J. A product-added remedy presented as classical, or ranked. #468: the Saturn
    # good-deeds list was headed "Classical Saturn-domain good deeds" while its first
    # bullet was "serve the elderly", which remedies.md 11.2 records as ours (Rao's
    # Saturn deed is labour and manual labourers, remedies.md 5); shani-saturn said
    # elder-respect works "more than to most rituals"; ketu-remedies called serving
    # renunciates "Ketu's most classically-cited karma-clearing practice" when Rao's
    # Ketu deed is meditation. A forbidden LITERAL cannot express "a product addition
    # called classical" (that needs the claim compared against the sourcing table),
    # so this pins the shapes found (three in the first pass, four more after QA round 1
    # of PR #487). The wording that stays legal is
    # Rao's own: "Saturn's classical good deed is labour itself", "the classical good
    # deeds for Rahu" -- the heading shape is "Classical <Planet>-domain good deeds".
    (r"\bclassical\s+[A-Za-z]+[\s\-\u2010-\u2015]+domain\s+(?:good\s+)?(?:deeds?|practices?|remed(?:y|ies))"
     r"|\bmore\s+than\s+(?:to\s+)?most\s+(?:rituals?|remed(?:y|ies)|pujas?)"
     # QA round 1 (PR #487): the same ranking in the other words a copywriter
     # reaches for. "faster than any temple visit" and "more powerful than expensive
     # rituals" survived the first pass because J pinned three literals. These are
     # still narrow on purpose: "faster than most people" (Ketu), "more effective than
     # sporadic elaborate rituals" and "matters more than any ritual" are legal.
     r"|\b(?:faster|sooner|quicker)\s+than\s+(?:any|most|all)\s+(?:\w+\s+){0,2}?"
     r"(?:temple|ritual|puja|remed|rite|offering|mantra|visit)\w*"
     r"|\bmore\s+(?:powerful|effective|potent)\s+than\s+(?:any\s+|most\s+)?(?:expensive|costly)\b"
     # Plural nouns and any dash. NOT `remedies`: "the six most classically-cited Ketu
     # remedies" is a page's own count and is pinned legal.
     r"|\bmost[\s\-\u2010\u2011]+classically[\s\-\u2010\u2011]+cited[^.\n]{0,40}\b(?:practices?|remedy|deeds?|mantras?)\b",
     "J: remedies.md 11.2 lists 'serve the elderly' and 'support renunciates' as product "
     "additions, so no heading, superlative or comparison may present them as classical"),

    # K. Graha Maitri collapsed to friend / neutral-partial / enemy-0 (#398 slice 6;
    # kundali-matching-ashtakoot-guna-milan). See GRAHA_MAITRI_MISSTATED for what is
    # and is not forbidden: "mutual enemies, 0" is correct and stays legal.
    (GRAHA_MAITRI_MISSTATED,
     "K: Graha Maitri is a six-rung ladder 5/4/3/2/1/0 (matching.md vv.27-28; matching.py "
     "_graha_maitri_score): 0 only for enemy+enemy, 1 for neutral+enemy, 2 for friend+enemy"),

    # L. Rahu and Ketu "outside Parashara's grid" (#398 slice 6). See RAHU_KETU_GRID.
    (RAHU_KETU_GRID,
     "L: grahas.md 11.1 gives Rahu/Ketu friendships; say the standard table covers the seven "
     "planets and the nodes' friendships come from tradition and vary - no Parashara "
     "attribution, no 'predates' history, no 'ad-hoc rules'"),

    # M-Q: #398 slice 7. See the constants above for the sourcing of each.
    (MERCURY_JUPITER_ENEMY,
     "M: grahas.md 11.1: Mercury -> Jupiter is NEUTRAL, only Jupiter -> Mercury is enemy; "
     "'Jupiter counts Mercury an enemy' is true, 'Mercury's natural enemy' is not"),
    (VISHNU_FOR_MANGLIK,
     "N: remedies.md 7.1 gives Mars Hanuman, Rudra, Kartikeya and Narasimha; a Vishnu rite "
     "(Sahasranama, Ekadashi vrat, Satya Narayan Katha) is not a Manglik remedy in any book we hold"),
    (KSD_SHIVA_FIRST,
     "O: Rahu -> Durga, Narasimha and Ketu -> Ganesha (remedies.md 7.1); Monday Shiva worship is a "
     "devotional tradition and may not be called first, classical or the starting point"),
    (KSD_TRADITION_AS_CLASSICAL,
     "P: Kaal Sarp is post-classical (vedic_reference.md 3.2); Nag Panchami, the silver pair and "
     "Trimbakeshwar are tradition/geography, not classical remedies"),
    (NON_VENUS_UNIVERSAL_SAFE,
     "Q: remedies.md 8 reserves 'the universal safe fallback' for Sri Yantra + Sri Sukta (Venus); "
     "the Saturn/Jupiter/Mercury/Mars pages may say 'a simple place to start', not universal or safe"),

    # R-U: #398 slice 8. See the constants above for the sourcing of each.
    (BPHS_REMEDY_ATTRIBUTION,
     "R: BPHS is not in data/, and no book we hold shows a Parashara '<planet> adhyaya', a Surya Samhita "
     "or a Muhurtha Chintamani 'charity list'; state what remedies.md supports and label the rest "
     "devotional/folk tradition, under a heading that does not say 'Classical'"),
    (BIJA_PER_BPHS,
     "S: remedies.md 6.3 calls the bija mantras 'widely-accepted', attributed to no book; "
     "'the full classical form per BPHS' is a claim nothing we hold supports"),
    (URAD_AS_SATURN,
     "T: Rao 34.3 gives Saturn sesame seeds and Rahu black gram (urad) daal; urad is not a Saturn grain"),
    (SESAME_AS_RAHU,
     "U: Rao 34.3 gives Rahu black gram (urad) daal and Saturn sesame seeds; sesame is not a Rahu grain"),
)

# Pattern index in READER_FORBIDDEN whose hits a labelled sentence may keep.
_HANUMAN_ROW = 2
# The window above stops at a full stop, so "Hanuman Chalisa - a 40-verse hymn.
# Recited daily, especially Tuesdays and Saturdays." and "...a Shani nivaran
# puja is selling anxiety. ... mantras + Chalisa + Hanuman worship" both slipped
# past it on the first run. So family C is ALSO checked per line: Hanuman and a
# Saturn word on one line (one string, for the .py surfaces). Measured on the
# tree: only six lines carry both, four of them correct per-planet tables, which
# is why a per-line rule is affordable here. A "Saturn -> Vishnu or Brahma" table
# entry is blanked before the check, so the correct table stays legal.
_SATURN_TABLE_ENTRY = re.compile(
    rf"{_SATURN}\s*(?:→|->)\s*(?!{_HANU})\w+(?:\s+(?:or|and)\s+\w+)*", re.IGNORECASE)
_HONEST_LABEL = (r"popular|folk", r"\bMars\b")

# What a surface is: (path-relative-to-src, kind). Every group must contribute
# at least one unit, or the gate is looking at nothing.
_REQUIRED_SURFACES = ("templates/learn/", "i18n.py", "numerology.py", "learn_registry.py",
                      "festival_registry.py")


def _blank_tags(html: str) -> str:
    """Same-length blanking so offsets (and so line numbers) survive."""
    return re.sub(r"<[^>]*>", lambda m: re.sub(r"[^\n]", " ", m.group(0)), html)


def _py_string_units(path: Path):
    """(lineno, text) for every string constant, except `llm_summary=` values.

    The summaries are Gate 6's, with a stricter pattern set (it also forbids
    black sesame and so on), and are what the LLM is shown.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "llm_summary":
            skip.update(id(n) for n in ast.walk(node.value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in skip):
            yield node.lineno, node.value


def reader_surface_units(root: Path | None = None):
    """[(where, text)] for every reader-facing surface under `root` (src/astro_ai).

    `where` is `relpath:line`; for a template, `text` is the whole file with
    tags blanked, and `where` is the file with the line added when reported.
    """
    root = root or SRC
    units: list[tuple[str, str]] = []
    for path in sorted((root / "templates").glob("**/*.html")):
        units.append((f"{path.relative_to(root)}:1", _blank_tags(path.read_text(encoding="utf-8"))))
    for name in ("i18n.py", "numerology.py", "learn_registry.py", "festival_registry.py"):
        path = root / name
        if path.exists():
            for lineno, text in _py_string_units(path):
                units.append((f"{name}:{lineno}", text))
    return units


def _labelled_honestly(text: str, start: int, end: int) -> bool:
    """True if the line(s) holding the match call it popular/folk AND name Mars."""
    a = text.rfind("\n", 0, start) + 1
    b = text.find("\n", end)
    line = text[a: len(text) if b < 0 else b]
    return all(re.search(p, line, flags=re.IGNORECASE) for p in _HONEST_LABEL)


def _hanuman_saturn_same_line(text: str):
    """(start, end, snippet) for each line carrying both a Hanuman and a Saturn word."""
    pos = 0
    for line in text.split("\n"):
        blanked = _SATURN_TABLE_ENTRY.sub(lambda m: " " * len(m.group(0)), line)
        h = re.search(_HANU, blanked, flags=re.IGNORECASE)
        s = re.search(_SATURN, blanked, flags=re.IGNORECASE)
        if h and s:
            yield pos + h.start(), pos + max(h.end(), s.end()), h.group(0) + " .. " + s.group(0)
        pos += len(line) + 1


def gate_7_no_retired_claims_on_reader_surfaces(units=None) -> bool:
    """`units` is an iterable of (where, text); default is the real tree.

    The parameter exists so `mutate_natal_prompt_gate.py` can feed it a
    re-broken surface without editing a template or the registry.
    """
    print("Gate 7 - no retired claims on reader-facing surfaces "
          "(templates, learn_registry, festival_registry, i18n, numerology)")
    units = list(reader_surface_units() if units is None else units)
    ok = True
    missing = [s for s in _REQUIRED_SURFACES if not any(w.startswith(s) for w, _ in units)]
    if missing:
        ok = False
        _fail(f"no text scanned from {missing} - this gate is checking nothing "
              f"there (an empty or moved tree must fail, not pass)")
    hits = 0
    for where, text in units:
        path, _, base = where.rpartition(":")
        base = int(base)
        for row, (pattern, why) in enumerate(READER_FORBIDDEN):
            found = [(m.start(), m.end(), m.group(0))
                     for m in re.finditer(pattern, text, flags=re.IGNORECASE)]
            if row == _HANUMAN_ROW:
                found += list(_hanuman_saturn_same_line(text))
            for start, end, matched in found:
                if row == _HANUMAN_ROW and _labelled_honestly(text, start, end):
                    continue
                ok = False
                hits += 1
                line = base + text.count("\n", 0, start)
                _fail(f"{path}:{line} matched "
                      f"{' '.join(matched.split())[:60]!r} - {why}")
    if ok:
        print(f"  ok    {len(units)} text units x {len(READER_FORBIDDEN)} retired "
              f"claim families: none present")
    return ok


def main() -> int:
    if not PROMPT.exists():
        print(f"FAIL: {PROMPT} does not exist")
        return 1
    text = PROMPT.read_text(encoding="utf-8")
    print(f"natal prompt gate - {PROMPT.relative_to(REPO_ROOT)}\n")
    results = [
        gate_1_headings(text),
        gate_2_rules(text),
        gate_3_budget(text),
        gate_4_no_stale_size_citations(text),
        gate_5_no_retired_claims(text),
        gate_6_no_retired_claims_in_summaries(),
        gate_7_no_retired_claims_on_reader_surfaces(),
    ]
    print()
    if all(results):
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
