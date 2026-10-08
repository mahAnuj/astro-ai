"""Serve `/rashifal/{rashi}` from the combined reading that already exists (#268).

`generate_rashifal` is 12 calls of the SAME per-rashi function, prompt and day
signals that `/rashifal/{rashi}` uses, so the combined text the 07:00 job caches
already contains every reading a single page needs. Before this module the single
route ignored it: the first reader of each (rashi, lang, date) paid a fresh
~3,330-token generation, and on 2026-10-08 — with the Groq daily budget spent
(198,298 of 200,000 TPD) — 21 of 24 pages were 503 while the reading they wanted
sat in the bucket.

Everything here is READ-ONLY and never reaches the LLM. Anything unexpected
returns None and the route generates live exactly as it did before, so this can
only ever turn a would-be generation into a cache hit, never a hit into a failure.
"""

from __future__ import annotations

import logging
import unicodedata

from astro_ai import cache, daily_cache
from astro_ai import providers as llm_providers
from astro_ai.chart import _RASHI_NAME_TOKENS
from astro_ai.llm import parse_sectioned_reading
from astro_ai.routes.deps import RASHIFAL_PROMPT_PATH
from astro_ai.routes.llm_support import _durable_get

log = logging.getLogger(__name__)

# Devanagari names a Hindi heading may carry, by rashi index. The first spelling
# of each is the one i18n.py's `rashi_name_*` keys use (knowledge/rashis.md);
# the rest are common variants — कुंभ/कुम्भ and वृष/वृषभ are the two this repo
# itself already spells both ways.
#
# ASSUMED, NOT MEASURED: which of these (if any) the model actually emits in a
# Hindi heading. rashifal_single.txt tells it to start with
# `## {English} / {Sanskrit}` and the Hindi suffix says "translate any section
# headings into Hindi" — those two instructions disagree, and no production Hindi
# combined text was available when this was written. An unrecognised heading
# fails CLOSED (no match -> live generation), and warm_rashifal's `single_pages`
# is what will show it.
_DEVANAGARI_NAMES: tuple[tuple[str, ...], ...] = (
    ("मेष",),
    ("वृषभ", "वृष"),
    ("मिथुन",),
    ("कर्क",),
    ("सिंह",),
    ("कन्या",),
    ("तुला",),
    ("वृश्चिक",),
    ("धनु",),
    ("मकर",),
    ("कुम्भ", "कुंभ"),
    ("मीन",),
)


def _norm(name: str) -> str:
    return unicodedata.normalize("NFC", name).strip().casefold()


# Whole-name EQUALITY against this table, never `in`. `chart._RASHI_NAME_TOKENS`
# is built for substring matching and carries "min" for Pisces, which is a
# substring of "Gemini / Mithuna" — a containment test would serve Gemini's
# reading on the Pisces page.
_ALLOWED: tuple[frozenset[str], ...] = tuple(
    frozenset(_norm(n) for n in latin + deva)
    for latin, deva in zip(_RASHI_NAME_TOKENS, _DEVANAGARI_NAMES)
)


def combined_keys(lang: str, today_iso: str) -> tuple[str, str]:
    """(SQLite cache key, GCS storage key) of the combined rashifal for a day.

    One definition for the writer (`warm_rashifal`) and this reader. Two copies
    of these f-strings is a derive path that silently reads a key nobody writes.
    """
    fp = cache.fingerprint_prompt(RASHIFAL_PROMPT_PATH)
    return f"rashifal:{today_iso}:{lang}:{fp}", f"rashifal/{today_iso}-{lang}-{fp}.txt"


def sections_by_rashi(text: str) -> dict[int, str]:
    """{rashi index: body} for every rashi that has EXACTLY ONE matching section.

    Matched by heading NAME, not by position: one call that emits an extra
    `## ` heading shifts every later section by one, and a positional split
    would serve Taurus's reading on the Gemini page without any error. A rashi
    with no section, or with two, is omitted — the caller generates live.
    """
    hits: dict[int, list[str]] = {}
    for title, body in parse_sectioned_reading(text or ""):
        segments = {_norm(seg) for seg in title.split("/")}
        matched = [i for i, names in enumerate(_ALLOWED) if segments & names]
        if len(matched) != 1:
            # Matches nothing (an extra heading, the "Reading" fallback) or
            # several rashis (not a heading we can attribute) — attribute to none.
            continue
        hits.setdefault(matched[0], []).append(body)
    return {i: bodies[0] for i, bodies in hits.items() if len(bodies) == 1}


def derive_single_reading(idx: int, lang: str, today_iso: str) -> str | None:
    """One rashi's reading cut from today's combined text, or None. Never raises.

    Read order: this instance's tier-0 file, then the GCS blob (negative misses
    bounded by `_durable_get`'s 30s dict). SQLite is skipped on purpose — it is
    per-instance /tmp and the warm job fills the other two.
    """
    try:
        text: str | None = None
        from_gcs = False
        hit = daily_cache.get("rashifal", lang, today_iso)
        if hit is not None and isinstance(hit.get("text"), str) and hit["text"].strip():
            text = hit["text"]
        else:
            text = _durable_get(combined_keys(lang, today_iso)[1])
            from_gcs = text is not None
        if not text:
            return None

        if from_gcs:
            # Gate BEFORE caching, and refuse to derive from a failing blob.
            # `_daily_rashifal_text` returns a tier-0 hit with no quality check,
            # so a corrupt blob written here would be emailed by the 07:00 blast.
            ok, reason = llm_providers.passes_quality(text, "rashifal")
            if not ok:
                log.warning("rashifal derive: GCS blob for %s fails the gate (%s)", lang, reason)
                return None
            daily_cache.put("rashifal", lang,
                            {"text": text, "lang": lang, "date_iso": today_iso}, today_iso)

        body = sections_by_rashi(text).get(idx)
        if body is None:
            return None
        # The single route's own read gate — a body it would discard must not be
        # stored, or it regenerates on every pageview (see rashifal_single).
        ok, reason = llm_providers.passes_quality(body, "rashifal_single")
        if not ok:
            log.warning("rashifal derive: section %d/%s fails the gate (%s)", idx, lang, reason)
            return None
        return body
    except Exception:  # noqa: BLE001 — a derive failure is a miss, never a 500
        log.warning("rashifal derive failed for idx=%s lang=%s (swallowed)", idx, lang, exc_info=True)
        return None
