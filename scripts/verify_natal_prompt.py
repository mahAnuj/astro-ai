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

Exit 0 = PASS, 1 = FAIL. No network, no API key, no ephemeris — it reads one
file, so it runs anywhere and belongs in the `verify_*` sweep.

Mutation-tested (2026-09-05): deleting any single rule's sentence from
`natal.txt` turns Gate 2 red for that rule and only that rule; the unmutated
CONTROL passes. A gate that has only ever passed is not evidence.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
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
FORBIDDEN = (
    (r"red[- ]lentil|masoor", "Sun's grain is wheat; red lentil is in no book we hold"),
    (r"Surya Namaskar", "proved absent from all 14 books"),
    (r"milk offering", "Shiva is the Sun's deity, not the Moon's (Table 78)"),
    (r"Hanuman intercession", "Saturn -> Vishnu, Brahma; Hanuman only via Mars with Saturnine influence"),
    (r"serve outsiders", "unsourced; Rao's Rahu deed is a donation to research or a pilgrimage"),
    (r"sesame[- ]oil", "unsourced; sesame is Saturn's and Rao gives Ketu no grain or oil"),
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
    ]
    print()
    if all(results):
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
