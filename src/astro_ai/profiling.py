"""Audience-shape aggregation from the GCS events log.

Reads existing `form_kundli` / `form_ask` / `form_matching` events (via
`astro_ai.events`) and rolls them up into distributions the admin can
skim to answer "who actually uses the site". No new data collection —
this is a view on top of already-persisted events, so the DPDP posture
does not change.

Result is cached per (days, day) to GCS at `profiling/summary-{d}d-{iso}.json`
with a 1-hour TTL so repeated admin loads don't re-scan the events log.

Scope of this Phase 1 module (per GitHub issue #140):
  - Age-band histogram from Kundli events' `age_band` (legacy rows: birth_date)
  - Top-N cities from Kundli events' `city` (legacy rows: birth_place,
    best-effort free-text parse)
  - Language distribution (EN/HI) across all event types
  - Question-category distribution from Ask events
  - Ask-context split (chart / numerology / matching)
  - Cross-feature funnel by email: what % of Kundli users also do Ask/etc.
  - Cache-hit vs fresh split on Ask (added 2026-08-06)
  - Totals per event type

Deferred to later phases:
  - Ascendant / Moon / Sun rashi (requires compute_chart per event)
  - Question-intent NLP classifier (Phase 3, per issue #140)
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import date, datetime, timezone
from typing import Any

from astro_ai import events, storage

log = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 3600  # re-aggregate at most once per hour per (days, today)

# Sentinel cities the parser recognises — the free-text birth_place field
# has enormous variation ("Delhi", "New Delhi, India", "Delhi NCR",
# "delhi, india, 110001"). This dict maps normalised prefixes to a canonical
# city name so the histogram doesn't fragment across spelling variants.
# Extend as we see new patterns in the top-cities output.
_CITY_ALIASES = {
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "gurgaon": "Gurgaon",
    "gurugram": "Gurgaon",
    "bombay": "Mumbai",
    "bangalore": "Bengaluru",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "madras": "Chennai",
}


def _age_bucket_from_dob(dob: str) -> str:
    """Bucket a YYYY-MM-DD birth-date into one of the age bands.

    Mirrors the buckets used by main._user_age_bucket so the admin view
    and the GA4 user-property use the same labels.
    """
    try:
        birth_year = int(dob[:4])
    except (ValueError, TypeError):
        return "unknown"
    age = date.today().year - birth_year
    if age < 0 or age > 120:
        return "unknown"
    if age < 18:
        return "under-18"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    return "55+"


# Words that mark a fragment of a street address rather than a city. Any one of
# them in any comma token drops the city entirely (#255): a stored "Flat 4B" or
# "Rose Villa" is the identifying detail the coarse profile exists to avoid, and a
# missing histogram row costs far less than a retained address. Whole-word match
# on lower-cased letters, so "Ahmednagar" and "Stockholm" do not trip it.
_ADDRESS_WORDS = frozenset({
    "flat", "house", "plot", "street", "st", "road", "rd", "lane", "ln", "nagar",
    "apartment", "apartments", "apt", "building", "bldg", "tower", "towers",
    "villa", "society", "colony", "sector", "block", "floor", "wing", "marg",
    "chowk", "gali", "galli", "near", "opp", "opposite", "behind", "avenue",
    "ave", "drive", "residency", "bungalow", "enclave", "vihar", "layout",
    "phase", "po", "box", "residence", "niwas", "nivas", "bhavan", "bhawan",
    "kutir", "mandir",
})
# The same for Devanagari. Matras are not \w, so the whole-word split above cannot
# see these words; they are matched as substrings instead (Hindi is a supported
# language, so a Hindi address is a likely input, not a corner case).
_ADDRESS_SUBSTRINGS_DEVANAGARI = (
    "मकान", "गली", "निवास", "भवन", "विला", "नगर", "फ्लैट", "सोसाइटी", "सोसायटी",
    "कॉलोनी", "रोड", "मार्ग", "सेक्टर", "अपार्टमेंट",
)


def _city_from_place(place: str) -> str:
    """Best-effort COARSE city from a free-text birth_place, failing closed.

    Convention we see in the events log: "City, State, Country" or
    "City, Country" or bare "City". Take the first comma-separated
    token, lowercase, look up an alias if any, else title-case the
    original.

    The field is free text and users do type street addresses into it
    ("Flat 4B, Rose Villa, Andheri, Mumbai"), so the first token is not safe
    to store on trust. Returns "" — drops the city — when the input is empty,
    has more than the three tokens of "City, State, Country", carries a digit
    in any token (other than a bare trailing postal code, which is never
    stored), contains an address word anywhere, or the first token is longer
    than four words / 40 characters. Failing closed is deliberate (#255).
    """
    if not place:
        return ""
    tokens = [t.strip().lower() for t in place.split(",")]
    if len(tokens) > 3 or not tokens[0]:
        return ""
    for i, tok in enumerate(tokens):
        if "c/o" in tok or "@" in tok:
            return ""
        if any(w in tok for w in _ADDRESS_SUBSTRINGS_DEVANAGARI):
            return ""
        if re.search(r"\d", tok):
            # "Delhi, India, 110001": a bare postal code in the last slot is
            # harmless because only the first token is ever kept.
            if i == len(tokens) - 1 and i > 0 and re.fullmatch(r"[\d\s-]+", tok):
                continue
            return ""
        if _ADDRESS_WORDS.intersection(re.findall(r"[^\W\d_]+", tok)):
            return ""
    first = tokens[0]
    if len(first) > 40 or len(first.split()) > 4:
        return ""
    return _CITY_ALIASES.get(first, first.title())


def coarse_profile(birth_date: str, birth_place: str) -> dict[str, str]:
    """The only birth-derived fields an event may carry: an age band and a city.

    Keeps the /admin/insights panels alive without storing the raw date or
    place (#255). Either value is "" / "unknown" when it cannot be derived.
    """
    return {
        "age_band": _age_bucket_from_dob(str(birth_date or "")),
        "city": _city_from_place(str(birth_place or "")),
    }


def _bump(hist: Counter, key: str) -> None:
    """Increment a histogram counter, skipping empties."""
    if key:
        hist[key] += 1


def _pct(part: int, whole: int) -> float:
    """Percent with one decimal, safe for whole=0."""
    if whole <= 0:
        return 0.0
    return round(100.0 * part / whole, 1)


def _cache_key(days: int) -> str:
    return f"profiling/summary-{days}d-{date.today().isoformat()}.json"


def audience_summary(*, days: int = 30, force_refresh: bool = False) -> dict[str, Any]:
    """Aggregate the last `days` of events into an audience shape dict.

    Cheap path: return the cached blob if it's fresh (< 1h old).
    Miss path: scan events, roll them up, write cache, return.

    Result shape (all counts are non-empty subset; percentages are of the
    per-dimension total, not the day total):

        {
            "generated_at": iso8601,
            "days": int,
            "totals": {"form_kundli": int, "form_ask": int, ...},
            "age_bands": [{"label": "25-34", "count": int, "pct": float}, ...],
            "top_cities": [{"label": "Delhi", "count": int, "pct": float}, ...],
            "languages": [{"label": "en", "count": int, "pct": float}, ...],
            "ask_categories": [...],
            "ask_contexts": [...],
            "ask_cache_hit_pct": float,
            "funnel": {
                "unique_emails": int,
                "kundli_only": int, "kundli_plus_ask": int,
                "kundli_plus_matching": int, "power_users": int,
            },
        }
    """
    if not force_refresh:
        cached = storage.get_json(_cache_key(days))
        if cached is not None:
            # A defensive guard against a stale cache in case we ever
            # tweak the shape — always safe to fall through and recompute.
            if cached.get("days") == days:
                return cached

    # Pull the raw events. limit=very-high because we want ALL events in the
    # window, not a sample. events.recent respects the retention cap.
    kundlis = events.recent(types=["form_kundli"], days=days, limit=10_000)
    asks = events.recent(types=["form_ask"], days=days, limit=10_000)
    matches = events.recent(types=["form_matching"], days=days, limit=10_000)
    all_events = kundlis + asks + matches

    # ----- Kundli-derived: age + city -----
    age_hist: Counter[str] = Counter()
    city_hist: Counter[str] = Counter()
    for e in kundlis:
        d = e.get("data") or {}
        # New events carry the coarse bands only (see coarse_profile); events
        # written before #255 still hold raw birth_date/birth_place, and live
        # for up to EVENT_RETENTION_DAYS after the deploy, so fall back.
        _bump(age_hist, str(d.get("age_band") or "")
              or _age_bucket_from_dob(str(d.get("birth_date", ""))))
        _bump(city_hist, str(d.get("city") or "")
              or _city_from_place(str(d.get("birth_place", ""))))

    # ----- Language: every event carries lang in data. Some legacy events
    # may not, so we fall back to "unknown". -----
    lang_hist: Counter[str] = Counter()
    for e in all_events:
        _bump(lang_hist, str((e.get("data") or {}).get("lang", "")) or "unknown")

    # ----- Ask-only: category + context + cache-hit rate -----
    cat_hist: Counter[str] = Counter()
    ctx_hist: Counter[str] = Counter()
    ask_cache_hits = 0
    for e in asks:
        d = e.get("data") or {}
        _bump(cat_hist, str(d.get("category", "")) or "general")
        _bump(ctx_hist, str(d.get("context", "")) or "chart")
        if d.get("cache_hit"):
            ask_cache_hits += 1

    # ----- Cross-feature funnel by email -----
    # For each email, note which feature-set it touched. Anonymous events
    # (no email) are counted once as "anon" and don't participate in the
    # funnel — they'd need chart-fingerprint matching, which is out of
    # scope for Phase 1.
    per_email: dict[str, set[str]] = {}
    for e in all_events:
        email = str(e.get("email") or "").lower().strip()
        if not email:
            continue
        per_email.setdefault(email, set()).add(str(e.get("type", "")))
    unique_emails = len(per_email)
    kundli_only = sum(1 for feats in per_email.values() if feats == {"form_kundli"})
    kundli_plus_ask = sum(1 for feats in per_email.values()
                          if "form_kundli" in feats and "form_ask" in feats)
    kundli_plus_matching = sum(1 for feats in per_email.values()
                               if "form_kundli" in feats and "form_matching" in feats)
    power_users = sum(1 for feats in per_email.values()
                      if len(feats & {"form_kundli", "form_ask", "form_matching"}) == 3)

    def _to_list(hist: Counter[str], top_n: int | None = None) -> list[dict[str, Any]]:
        total = sum(hist.values())
        items = hist.most_common(top_n) if top_n else sorted(
            hist.items(), key=lambda kv: (-kv[1], kv[0])
        )
        return [{"label": k, "count": v, "pct": _pct(v, total)} for k, v in items]

    summary = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "days": days,
        "totals": {
            "form_kundli": len(kundlis),
            "form_ask": len(asks),
            "form_matching": len(matches),
            "all": len(all_events),
        },
        "age_bands": _to_list(age_hist),
        "top_cities": _to_list(city_hist, top_n=20),
        "languages": _to_list(lang_hist),
        "ask_categories": _to_list(cat_hist),
        "ask_contexts": _to_list(ctx_hist),
        "ask_cache_hit_pct": _pct(ask_cache_hits, len(asks)),
        "funnel": {
            "unique_emails": unique_emails,
            "kundli_only": kundli_only,
            "kundli_plus_ask": kundli_plus_ask,
            "kundli_plus_matching": kundli_plus_matching,
            "power_users": power_users,
        },
    }

    # Write-through cache; ignore failures (best-effort, next call will retry).
    try:
        storage.put_json(_cache_key(days), summary)
    except Exception:  # noqa: BLE001 — cache write is optional
        log.debug("profiling: cache put failed for days=%s", days)

    return summary
