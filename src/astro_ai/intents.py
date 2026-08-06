"""Question-intent classifier for /ask — deterministic keyword matching.

WHAT: maps a free-text question ("meri shaadi kab hogi") to one of 15 named
intents ("Marriage / timing") so analytics can report what people actually
come here to ask, without reading raw question text one by one.

Design:
- Deterministic. NO LLM call, NO network, NO new dependency. Same input
  always gives the same output, so historical events can be re-classified
  and the numbers stay comparable across runs.
- English + common Hinglish transliteration (ASCII/Latin only). Devanagari
  script is out of scope for this phase.
- Precision over recall: a question that matches nothing is reported as
  unclassified rather than guessed into a bucket.

STDLIB ONLY — DO NOT ADD IMPORTS.
This module imports nothing but the Python standard library: no
``astro_ai.*``, no third-party packages. Its unit test must run on a bare
interpreter with zero project dependencies installed, so importing (say)
``astro_ai.storage`` here would drag the whole app — and its deps — into a
test that is meant to be free.

PATTERN ORDER MATTERS — FIRST MATCH WINS.
``_PATTERNS`` is an ordered list, not a dict. ``classify()`` walks it top to
bottom and returns on the first hit. The order encodes the tie-breaks:
- ``property`` sits above ``legal_dispute`` and ``family_conflict`` so
  "property dispute" reads as property, not a lawsuit or a family fight.
- ``general_future`` is LAST because it is the broadest net ("life",
  "future"); anything more specific must get a chance first.

To add a new intent:
1. Add ``slug -> "Human label"`` to ``INTENTS``.
2. Add ``(slug, re.compile(r"...", re.IGNORECASE))`` to ``_PATTERNS`` at the
   position its specificity deserves — narrow intents high, broad ones low,
   and always above ``general_future``.
3. Word-boundary any short or ambiguous token (``\\bghar\\b``, ``\\bcase\\b``,
   ``\\bland\\b``) so it cannot match inside an unrelated word.
"""

from __future__ import annotations

import re


# ─── The 15 intents ───────────────────────────────────────────────────
# slug -> human label. The label is what surfaces in admin/analytics UI;
# the slug is the stable key. Never rename a slug — rename the label.
INTENTS: dict[str, str] = {
    "marriage_timing": "Marriage / timing",
    "love_relationship": "Love & relationships",
    "job_career": "Job / career change",
    "business": "Business & self-employment",
    "money_finance": "Money & finance",
    "children": "Children & fertility",
    "health": "Health",
    "education": "Education & exams",
    "travel_abroad": "Travel / going abroad",
    "property": "Property & home",
    "spiritual_path": "Spiritual path",
    "feeling_stuck": "Feeling stuck / directionless",
    "family_conflict": "Family conflict",
    "legal_dispute": "Legal disputes",
    "general_future": "General future outlook",
}

UNCLASSIFIED = "unclassified"

# Long inputs are truncated before scanning — bounded work per call, and a
# real /ask question is a sentence, not an essay.
_MAX_SCAN_CHARS = 2000


# ─── Ordered patterns — FIRST MATCH WINS, order is load-bearing ───────
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "marriage_timing",
        re.compile(
            r"marriage|marry|married|marria|wedding|sha+di|vivah|shaadi"
            r"|\bspouse\b|life\s*partner|rishta|engagement|\bdulha\b|\bdulhan\b"
            r"|get\s*hitched|\bnikah\b",
            re.IGNORECASE,
        ),
    ),
    (
        "job_career",
        re.compile(
            r"\bjobs?\b|career|naukri|nokri|naukari|promotion|appraisal"
            r"|\bswitch\b|resign|interview|\boffice\b|employer|\bboss\b"
            r"|new\s*company|placement|\bhike\b",
            re.IGNORECASE,
        ),
    ),
    (
        "children",
        re.compile(
            r"\bchild\b|children|\bbaby\b|\bbabies\b|bachch?a|bachch?e|bacha+\b"
            r"|santa+n|pregnan|conceive|conception|fertil|\bivf\b|\bkid\b|\bkids\b"
            r"|\baulad\b|\bputra\b",
            re.IGNORECASE,
        ),
    ),
    (
        "money_finance",
        re.compile(
            r"\bmoney\b|paisa|paise|\bdhan\b|salary|income|\bdebts?\b|\bloans?\b"
            r"|karz|wealth|financ|savings|\bemi\b|\bcash\b|\brich\b|prosperity"
            r"|\bdhanvan\b",
            re.IGNORECASE,
        ),
    ),
    (
        "spiritual_path",
        re.compile(
            r"spiritual|moksha|\bguru\b|meditat|sadhana|\bpuja\b|\bpooja\b"
            r"|mantra|bhakti|dharma|enlighten|\btemple\b|\bdeity\b|\bishta\b"
            r"|\bjaap\b|\bjapa\b",
            re.IGNORECASE,
        ),
    ),
    (
        "feeling_stuck",
        re.compile(
            r"\bstuck\b|\blost\b|no\s*direction|nothing\s*is\s*working"
            r"|kuch\s*nahi\s*ho\s*raha|confused\s*about\s*life|\bphas(a|i|e)\b"
            r"|struggl|\bdirectionless\b|feel\s*empty|\bhopeless\b"
            r"|nothing\s*works",
            re.IGNORECASE,
        ),
    ),
    (
        "health",
        re.compile(
            r"health|illness|\bill\b|disease|bimari|beemari|sehat|tabiyat"
            r"|surgery|operation|recovery|hospital|\bmedical\b|\bcure\b"
            r"|\bdiagnos",
            re.IGNORECASE,
        ),
    ),
    (
        "travel_abroad",
        re.compile(
            r"abroad|videsh|foreign|\bvisas?\b|immigrat|migrat|overseas"
            r"|travel|pravas|canada|australia|\bnri\b|settle\s*outside"
            r"|\brelocat",
            re.IGNORECASE,
        ),
    ),
    (
        "education",
        re.compile(
            r"stud(y|ies|ying)|\bexams?\b|padhai|padhayi|college|admission"
            r"|\bdegree\b|\bupsc\b|\bneet\b|\bjee\b|scholarship"
            r"|university|\bschool\b|entrance|\bmba\b|competitive",
            re.IGNORECASE,
        ),
    ),
    # property ABOVE legal_dispute and family_conflict on purpose:
    # "property dispute" / "ghar ka jhagda" are property questions.
    (
        "property",
        re.compile(
            r"propert|\bhouses?\b|\bhomes?\b|\bghar\b|makan|\bplots?\b"
            r"|\blands?\b|jam?een|zameen|\bflats?\b|real\s*estate|\bmakaan\b"
            r"|\bmortgage\b|own\s*a\s*house",
            re.IGNORECASE,
        ),
    ),
    (
        "business",
        re.compile(
            r"business|start\s*up|startup|vyapa+r|vyavsay|dhanda|partnership"
            r"|venture|\bshop\b|self\s*employ|entrepreneur|apna\s*kaam",
            re.IGNORECASE,
        ),
    ),
    (
        "legal_dispute",
        re.compile(
            r"\bcourts?\b|\bcases?\b|mukad(a)?ma|lawsuit|legal|litigat"
            r"|dispute|\bvakil\b|\blawyer\b|\bfir\b|\bbail\b",
            re.IGNORECASE,
        ),
    ),
    (
        "family_conflict",
        re.compile(
            r"family\s*(problem|issue|tension|matter|trouble)|\bparents\b"
            r"|in\s*-?\s*laws|sasural|jhag(da|ra)|fight\s*at\s*home"
            r"|\bbrothers?\b|\bsisters?\b|\bbhai\b|\bbehen\b|ghar\s*me\s*kalesh"
            r"|\bsaas\b",
            re.IGNORECASE,
        ),
    ),
    (
        "love_relationship",
        re.compile(
            r"\blove\b|\bpyar\b|\bpyaar\b|\bprem\b|girl\s*friend|girlfriend"
            r"|boy\s*friend|boyfriend|break\s*up|breakup|relationship"
            r"|\bcrush\b|affair|\bdating\b|\bex\b|one\s*sided",
            re.IGNORECASE,
        ),
    ),
    # LAST — broadest net. Everything specific gets first refusal.
    (
        "general_future",
        re.compile(
            r"future|bhavish|\blife\b|kaisa\s*rahega|kaisi\s*rahegi"
            r"|what\s*will\s*happen|forecast|\bahead\b|coming\s*years?"
            r"|\bdestiny\b|kya\s*hoga",
            re.IGNORECASE,
        ),
    ),
]


def classify(question: str, fallback_category: str = "") -> tuple[str, bool]:
    """Classify a free-text question into a human intent label.

    Returns ``(label, matched)``:
    - a pattern hit  -> (human label from INTENTS, True)
    - no hit, fallback_category given -> ("<category> (category)", False)
    - no hit, no fallback -> ("unclassified", False)

    Never raises. None, empty, whitespace-only, pure punctuation and very
    long strings all fall through to the unclassified path.
    """
    if question is None:
        return (UNCLASSIFIED, False)

    try:
        text = str(question).strip()
    except Exception:
        return (UNCLASSIFIED, False)

    if text:
        text = text[:_MAX_SCAN_CHARS]
        for slug, pattern in _PATTERNS:
            if pattern.search(text):
                return (INTENTS[slug], True)

    try:
        fallback = str(fallback_category or "").strip()
    except Exception:
        fallback = ""

    if fallback:
        return (f"{fallback} (category)", False)
    return (UNCLASSIFIED, False)
