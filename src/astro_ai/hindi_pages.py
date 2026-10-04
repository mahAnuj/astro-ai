"""Which pages are published in Hindi at ``/hi/{path}`` — and their hreflang.

WHAT: one hand-maintained allow-list (``HINDI_PUBLISHED``) plus three pure
functions that map between an English path, its ``/hi/`` twin, and the
hreflang annotations both of them must carry. Four consumers share it: the
``/hi`` router, a Jinja global in ``base.html``, the sitemap, and the nav
language toggle. They must agree, so they all read this module.

STDLIB ONLY AT MODULE SCOPE — DO NOT ADD IMPORTS.
Nothing from ``astro_ai.*`` is imported when this module is imported. The
canonical slugs come from ``astro_ai.llm`` and the site URL from
``astro_ai.routes.deps``, both fetched *inside* functions. Import-time
binding order is what left ``deps.py`` with 8 permanently-stuck re-exports
(#184 §4); this module is imported by ``base.html``'s environment and by the
sitemap, i.e. early, so it stays inert until called.

─── #124 is NOT "translate every URL" ────────────────────────────────────

The issue asks for all ~200 pages at ``/hi/{path}``. That premise is false:
the site's "Hindi" build is English prose wrapped in translated chrome.
Measured against production 2026-09-20 (Devanagari share of the letters in
the ``<main>`` block, and text similarity to the same page in English):

    /rashifal/mesha            74.3% Devanagari   similarity 0.240
    /numerology                36.7%              0.651
    /rashifal (hub)            24.8%              0.600
    /festivals                 11.0%              0.925
    /matching                   4.3%              0.956
    /panchang                   0.2%              0.998
    /muhurat, /muhurat/vivah, /manglik-check, /learn/,
    /learn/shukra-venus-…       0.0%              1.000

Publishing ``/hi/`` for all of them ships ~198 near-duplicate, mostly-English
pages under a Hindi locale — a plausible way to *harm* rankings rather than
help them. So the published set is 13 URLs, and this module is the single
switch that decides that.

─── The rule for adding a page ───────────────────────────────────────────

A page is Hindi-published iff, when rendered with ``lang="hi"`` and no
cookie:

1. ``<title>`` contains Devanagari, and
2. ``<meta name="description">`` contains Devanagari, and
3. ``<h1>`` contains Devanagari, and
4. the PRIMARY CONTENT BLOCK — what the reader came for, excluding nav,
   footer, panchang strip, CTAs and the subscribe modal — is Hindi: for a
   prose page, a clear majority of its letter characters are Devanagari;
   for a hub page, every heading and every link label in the primary list
   is Hindi; and
5. it is listed by hand in ``HINDI_PUBLISHED``, by a person who checked
   1–4, with the check date in a trailing comment.

─── Why the list is DECLARED and not derived ─────────────────────────────

The obvious design — derive the set from translation coverage — cannot
work, and the numbers say why. ``i18n._EN`` and ``i18n._HI`` both hold
**325 keys, 0 missing, 0 extra** (verified 2026-09-20). A coverage-derived
predicate would therefore report every page in the app as 100% Hindi,
including ``/numerology``, whose ``numerology.py`` is **120,272 characters
containing 0 Devanagari** (verified the same day). Coverage measures the
chrome, and the chrome is precisely the part that is already translated.

A page is published because a person read it, not because a ratio passed.

REJECTED CANDIDATES — do not re-propose without re-measuring:

- ``/numerology`` — 36.7% Devanagari in ``<main>``, and its entire content
  generator (``numerology.py``, 120,272 chars) has 0 Devanagari. The Hindi
  share it does show is chrome. Fails rule 4.
"""

from __future__ import annotations

from functools import lru_cache

# URL prefix for the Hindi locale. One segment, no trailing slash: paths are
# matched on a segment boundary so "/history" is never mistaken for Hindi.
_HI_PREFIX = "/hi"

# BCP-47 tags. "en-IN"/"hi-IN" rather than the issue text's lowercase
# "en-in" purely to match the existing og:locale "en_IN" at base.html:34 —
# Google treats region subtags case-insensitively, so this is cosmetic
# consistency, not a behaviour choice. Nothing to re-litigate here.
_EN_TAG = "en-IN"
_HI_TAG = "hi-IN"
_DEFAULT_TAG = "x-default"

# Declared at module scope for type checkers and for `from ... import
# HINDI_PUBLISHED`; RESOLVED LAZILY by __getattr__ below, because building it
# needs astro_ai.llm and this module must not import that at module scope.
HINDI_PUBLISHED: frozenset[str]


@lru_cache(maxsize=1)
def _published() -> frozenset[str]:
    """The 13 English paths that are genuinely Hindi (checked 2026-09-20).

    Built from ``llm.RASHI_CANONICAL_SLUGS`` rather than retyped, so the set
    cannot drift from the routes when a slug changes. The import is local and
    the result memoised: ``astro_ai.llm`` is pulled in on first *use*, never
    on import of this module.

    CANONICAL SLUGS ONLY. ``llm.RASHI_SLUG_TO_INDEX`` also accepts 21
    aliases (mesha, mesh, vrishab, …) and ``/rashifal/mesha`` renders 200
    with ``<link rel=canonical>`` pointing at itself (base.html:13 builds it
    from ``request.url.path``). That self-canonicalising duplicate is a
    PRE-EXISTING problem and is explicitly out of scope for #124 — a
    separate issue still needs filing for it. Until then, alias URLs get no
    hreflang from this module and appear in no sitemap, which is the safe
    side of the mistake: annotating 21 extra duplicates would spread the
    problem into the Hindi locale as well.
    """
    from astro_ai.llm import RASHI_CANONICAL_SLUGS

    return frozenset(
        # Hub: every heading and card label in the 12-sign grid is Hindi.
        ["/rashifal"]
        # Per-rashi readings: the LLM writes these in Hindi (74.3% Devanagari
        # in <main>; the remainder is the shared chrome and sign names).
        + [f"/rashifal/{slug}" for slug in RASHI_CANONICAL_SLUGS]
    )


def __getattr__(name: str) -> frozenset[str]:
    """Resolve ``HINDI_PUBLISHED`` on first access (PEP 562).

    Lets the module expose a constant without paying an ``astro_ai.llm``
    import at module scope.
    """
    if name == "HINDI_PUBLISHED":
        return _published()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _normalise(path: str) -> str:
    """Canonical form of a URL path: leading slash, no trailing slash, lower.

    Lowercased because the rashifal route itself lowercases the slug before
    lookup, so ``/rashifal/Aries`` is a live URL; it must resolve to the same
    published entry (and emit the lowercase canonical in its hreflang).
    """
    path = (path or "").strip()
    # Callers pass request.url.path, but a caller passing a full-ish URL
    # shouldn't silently get a wrong answer.
    for sep in ("?", "#"):
        path = path.split(sep, 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    path = path.lower()
    return path.rstrip("/") or "/"


def english_url(path: str) -> str:
    """Strip the ``/hi`` prefix. Idempotent — safe on an English path."""
    path = _normalise(path)
    if path == _HI_PREFIX:
        return "/"
    if path.startswith(_HI_PREFIX + "/"):
        return path[len(_HI_PREFIX):]
    return path


def strip_hi_prefix(path: str) -> str:
    """Remove a leading ``/hi``, changing NOTHING else.

    Deliberately not ``english_url()``, which runs ``_normalise`` and so also
    lowercases and strips the trailing slash. The language picker posts this
    as its ``next``, and using the normalising version turned
    ``/learn/karva-chauth-2026/`` into ``/learn/karva-chauth-2026`` — so every
    language switch on the 75 ``/learn/`` articles and ``/learn/`` itself took
    TWO redirect hops where ``main`` took one (QA 2026-10-04).

    ``english_url()`` is still correct for the allow-list lookups it was
    written for, where a canonical form is the point. It is wrong for
    round-tripping a URL the reader is standing on.
    """
    if path == _HI_PREFIX:
        return "/"
    if path.startswith(_HI_PREFIX + "/"):
        return path[len(_HI_PREFIX):]
    return path


def is_hindi_published(path: str) -> bool:
    """True if this page has a real Hindi version. Accepts either variant."""
    return english_url(path) in _published()


def hindi_url(path: str) -> str | None:
    """``/rashifal`` -> ``/hi/rashifal``; ``None`` when unpublished.

    ``None`` is the signal the nav toggle uses to hide the language switch:
    offering Hindi on a page that has no Hindi version just bounces the
    reader back to English prose under a Hindi URL.
    """
    english = english_url(path)
    if english not in _published():
        return None
    return _HI_PREFIX if english == "/" else _HI_PREFIX + english


def hreflang_alternates(path: str, base_url: str | None = None) -> list[tuple[str, str]]:
    """The three hreflang pairs for a page — or ``[]`` if it has no Hindi twin.

    Returns ``[(en-IN, …), (hi-IN, …), (x-default, …)]`` in that order, and
    BYTE-IDENTICAL for the English URL and its ``/hi/`` twin: reciprocity is
    the whole point of hreflang, and Google validates it by comparing the two
    pages' annotation sets. Both sides therefore render the same three tags.

    An unpublished path returns ``[]`` — deliberately NOT a lone en-IN +
    x-default pair. An ``hi-IN`` annotation pointing at a page that does not
    exist (or that does not point back) makes Google discard hreflang
    annotations SITE-WIDE, which would poison the 13 URLs we actually care
    about in order to decorate ~198 we do not. Emitting nothing on those
    pages is not a degradation; it is the correct answer.

    ``base_url`` defaults to ``routes.deps._site_url()``, imported lazily so
    this module stays free of ``routes.*`` at import time. Pass it explicitly
    from anything that must not drag FastAPI + dotenv in (gate scripts,
    tests) — ``deps`` calls ``load_dotenv(override=True)`` on import.
    """
    # A mixed-case or otherwise non-canonical URL is a 200 page (the rashifal
    # route lowercases its slug), and `_normalise` lowercases too — so
    # /rashifal/ARIES was treated as published and got the full triple, whose
    # three hrefs are all lowercase and therefore none of them is the URL
    # being served. That is a one-sided annotation on an indexable page, the
    # exact mechanism this docstring says makes Google discard hreflang
    # SITE-WIDE. Emitting nothing is right: the page still carries its own
    # canonical, and the lowercase pair keeps its honest annotations.
    # Found by QA 2026-10-04; `main` emits nothing there, so #124 introduced it.
    if path != _normalise(path):
        return []
    english = english_url(path)
    if english not in _published():
        return []
    if base_url is None:
        from astro_ai.routes.deps import _site_url

        base_url = _site_url()
    base = base_url.rstrip("/")
    en = f"{base}{english}"
    hi = f"{base}{_HI_PREFIX}{english}"
    return [
        (_EN_TAG, en),
        (_HI_TAG, hi),
        # x-default points at English: it is the fallback for readers whose
        # locale matches neither tag, and English is the wider-reach version.
        (_DEFAULT_TAG, en),
    ]
