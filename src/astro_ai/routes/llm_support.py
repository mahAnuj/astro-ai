"""LLM plumbing shared by the route modules: caching + error presentation.

Extracted verbatim from ``main.py`` (issue #154). Deliberately independent of
``routes.deps`` — these two are leaf modules and neither imports the other, so
importing one never drags in the other's import-order constraints.
Nothing in this package may import ``astro_ai.main``.
"""

from __future__ import annotations

import logging
import time as _time

from astro_ai import cache, events, notify, storage
from astro_ai import providers as llm_providers
from astro_ai.providers import AllProvidersExhausted, RequestTooLarge
from astro_ai.session import load_user

log = logging.getLogger(__name__)


def _fire_error_alert(request, err: Exception, source: str) -> None:
    """Send a Telegram alert with the low-level error details. Best-effort.

    Called from every LLM error path so we get pinged the moment a user
    hits a provider outage / rate limit / crash. Never raises — Telegram
    alerts must not add failure modes to already-failed request paths.
    """
    try:
        import traceback as _tb
        _u = load_user(request) if request is not None else None
        _user_email = _u.email if _u else ""
        _path = request.url.path if request is not None else ""
        _method = request.method if request is not None else ""
        _tb_str = _tb.format_exc()
        notify.error_seen(
            source=source,
            error_type=type(err).__name__,
            error_message=str(err) or repr(err),
            path=_path, method=_method,
            user_email=_user_email,
            traceback_str=_tb_str,
        )
        # Persistent record so /admin/activity can show error history.
        events.record(
            type="error",
            email=_user_email,
            data={
                "source": source,
                "error_type": type(err).__name__,
                "error_message": (str(err) or repr(err))[:500],
                "path": _path, "method": _method,
                # Keep last ~1500 chars of traceback for post-hoc diagnosis.
                "traceback": _tb_str[-1500:] if _tb_str else "",
            },
        )
    except Exception:  # noqa: BLE001 — alert must never mask original error
        log.debug("notify.error_seen fire failed (swallowed)", exc_info=True)


def _llm_error_friendly(err: Exception) -> tuple[str, str]:
    """Translate an internal LLM error into a user-friendly (title, message).

    Rate-limit / high-demand errors get a distinct, retry-encouraging copy.
    Any other error gets a generic apology — the raw exception class name and
    message are NEVER exposed to the user (they leak internals and confuse
    non-technical seekers). Full details are logged server-side for debugging.

    `RequestTooLarge` is checked FIRST because it subclasses
    AllProvidersExhausted and would otherwise inherit the high-demand copy —
    which tells the seeker to try again in a couple of minutes, advice that can
    never work for them. A 413 means this particular chart assembled a request
    bigger than the model's per-request ceiling; re-submitting it produces the
    same request and the same refusal, at 3am as much as at peak. The change
    that introduced this class argues a 413 and a 429 "need OPPOSITE
    responses", and the user-facing layer is where that has to land or the
    distinction stops at the log file. QA caught it stopping there.

    The copy deliberately does not say "too large" — the seeker did nothing
    wrong and there is no input for them to shorten. It should be rare: the
    pre-flight guard in `llm._shed_to_fit` sheds optional blocks precisely so
    this page is not reached.
    """
    if isinstance(err, RequestTooLarge):
        return (
            "We couldn't prepare this chart",
            "🙏 Something in this particular chart made the reading too big for "
            "us to generate just now. This is on our side, not yours, and "
            "re-submitting will not change it — we have been alerted and are "
            "looking at it. Please do try again later today.",
        )
    if isinstance(err, AllProvidersExhausted):
        return (
            "High demand right now",
            "🙏 Many seekers are asking questions at the same time. "
            "Please try again in a couple of minutes — your input is safe "
            "to re-submit exactly as you typed it.",
        )
    return (
        "Something went wrong",
        "We couldn't complete the reading this time. Please try again in "
        "a moment — your input is safe to re-submit exactly as you typed it.",
    )


# Keys we looked for in the bucket recently and did not find. A chart in
# neither tier would otherwise pay a Class B op and a cross-continent
# round-trip on EVERY render while the seeker refreshes waiting for a reading
# that has not been generated yet.
#
# Short TTL on purpose, per the 2026-08-23 decision-log rule: a permanent
# negative cache pins a reader to a wrong answer, and no negative cache pays
# the full round-trip every request. 30s is well under the ~10s a natal
# generation takes, so the blob a fresh generation writes is picked up by the
# next instance almost immediately; the entry is dropped outright on a
# successful write, so it never masks a reading this process just produced.
_DURABLE_MISS_TTL_S = 30.0
_DURABLE_MISSES: dict[str, float] = {}
_DURABLE_MISS_SWEEP_AT = 500


def _durable_get(durable_key: str) -> str | None:
    """`storage.get`, but a cache tier is never allowed to break a reading.

    `storage.get` already returns None when no bucket is configured and
    swallows GCS errors, so the try/except only covers the unexpected — a
    credential refresh raising, an import blowing up. Cheap insurance for a
    layer whose entire job is to be optional.

    Recent misses are remembered for `_DURABLE_MISS_TTL_S` and answered
    locally. Swept by AGE and only on write, the one place the dict grows
    (#182): dropping by size would evict live entries and re-admit the
    round-trips this exists to remove.
    """
    now = _time.time()
    missed_at = _DURABLE_MISSES.get(durable_key)
    if missed_at is not None and now - missed_at < _DURABLE_MISS_TTL_S:
        return None
    try:
        value = storage.get(durable_key)
    except Exception:  # noqa: BLE001 — a cache miss is always a valid answer
        log.warning("durable cache: get(%s) raised (swallowed)", durable_key, exc_info=True)
        value = None
    if value is None:
        if len(_DURABLE_MISSES) > _DURABLE_MISS_SWEEP_AT:
            cutoff = now - _DURABLE_MISS_TTL_S
            for key in list(_DURABLE_MISSES.keys()):
                seen = _DURABLE_MISSES.get(key)
                if seen is not None and seen < cutoff:
                    _DURABLE_MISSES.pop(key, None)
        _DURABLE_MISSES[durable_key] = now
    else:
        _DURABLE_MISSES.pop(durable_key, None)
    return value


def _durable_put(durable_key: str, text: str) -> None:
    """`storage.put`, best-effort. A failed write costs a regeneration, not a page."""
    try:
        ok = storage.put(durable_key, text)
    except Exception:  # noqa: BLE001 — see _durable_get
        log.warning("durable cache: put(%s) raised (swallowed)", durable_key, exc_info=True)
        return
    if ok:
        # The blob exists now, so the negative entry is stale the instant it
        # was written. Leaving it would make this process regenerate a reading
        # it had just persisted.
        _DURABLE_MISSES.pop(durable_key, None)


def _cached(
    cache_key: str,
    *,
    route: str,
    lang: str,
    ttl_days: int | None,
    call_fn,
    durable_key: str | None = None,
) -> str:
    """Cache-wrap an LLM call. Logs every attempt (hit or miss) for /admin/usage.

    `call_fn` is a zero-arg callable that returns the LLM text. We do the
    cache-check and the per-route logging here so every reading benefits from
    the same observability surface without duplicating boilerplate.

    Self-healing: if the cached text fails the same quality check that the
    provider chain uses (e.g. missing '## Heading' markers), we treat it as
    a miss and re-generate — silently cleaning up any garbage that snuck
    into the cache before quality-gating was live.

    DURABLE TIER (`durable_key`), added for the natal reading:

        SQLite hit                              → return              0 GCS ops
        SQLite miss → GCS hit → warm SQLite     → return              1 GCS GET
        both miss   → generate → write both                           1 GCS PUT

    SQLite is checked FIRST and GCS only on a local miss, which is the whole
    point: the bucket is US multi-region and Cloud Run runs in asia-south1, so
    every round-trip is cross-continent and a warm instance must pay zero of
    them (#144 — ~30 sequential bucket round-trips per render was a 13-second
    homepage). That read order is also why this is not merged into
    `subscribe._shared_three_tier`, which correctly reads GCS first for content
    a warm job wrote once for everybody.

    Why it is needed at all: the natal cache is written `ttl_days=None`
    ("never expires") into SQLite on `/tmp` — tmpfs, per-instance, min-instances
    0, up to 5 instances. "Permanent" therefore meant regenerated once per
    instance, once per cold start and once per deploy, each costing a full
    natal call (~7,800 input tokens against an 8,000 TPM per-model bucket).
    This tier makes a reading generated once, ever. It removes WASTE; it does
    not raise the ceiling — a chart nobody has ever asked for still costs full
    price, and the site still serves on the order of 20-30 fresh readings a day.

    `durable_key` is explicit rather than inferred from `ttl_days is None`,
    because that sentinel would also sweep in `/ask`, whose cache key contains
    the seeker's free-text question — an unbounded keyspace writing one GCS
    object per unique question against a 5,000 Class A ops/month allowance.

    Blobs are content-addressed (the key carries `PROMPT_LOGIC_VERSION` via
    `fingerprint_prompt`), so a stale read is impossible by construction and a
    version bump orphans every existing blob. Orphans can never be listed or
    deleted — `storage.py` has no prefix listing — but a reading is small.
    `prompts/natal.txt` mandates 920-1380 words; at 5.51 UTF-8 bytes/word
    (measured on a real generated body, 661 B / 120 words) that is **5-7.6 KB
    in English**, and Hindi measures 2.39x English across 325 matched
    translation pairs in `i18n.py`, so **12-18 KB in Devanagari**. Take 15 KB:
    1,000 orphans is ~15 MB against a 5 GB free tier, 0.3%. Accepted.
    An English-only figure understates this by more than half, which is why
    both languages are stated — and both were derived, not measured on a real
    natal reading: there is none in the tree to measure and generating one
    costs a model-minute.
    """
    hit = cache.get(cache_key)
    if hit is not None:
        ok, reason = llm_providers.passes_quality(hit, route)
        if ok:
            cache.log_call(route, lang, cache_hit=True)
            return hit
        log.warning(
            "cache: dropping bad entry for route=%s (%s) — will regenerate",
            route, reason,
        )
        # Fall through to regeneration; the fresh call will overwrite.
    if durable_key:
        durable = _durable_get(durable_key)
        if durable is not None:
            ok, reason = llm_providers.passes_quality(durable, route)
            if ok:
                # A hit here made no LLM call, so it is a hit for token
                # accounting — logging it as a miss would attribute the
                # estimated tokens of a call that never happened to /admin/usage.
                cache.log_call(route, lang, cache_hit=True)
                cache.put(cache_key, durable, route=route, ttl_days=ttl_days)
                log.info("durable cache: hit for route=%s key=%s", route, durable_key)
                return durable
            log.warning(
                "durable cache: dropping bad blob for route=%s (%s) — will regenerate",
                route, reason,
            )
            # Fall through; the fresh generation overwrites the blob below.
        else:
            log.info("durable cache: miss for route=%s key=%s", route, durable_key)
    started = _time.time()
    text = call_fn()
    latency_ms = int((_time.time() - started) * 1000)
    in_tok = cache.estimate_tokens(text) * 2  # input ≈ 2x output for our prompts (rough)
    out_tok = cache.estimate_tokens(text)
    cache.put(cache_key, text, route=route, ttl_days=ttl_days,
              input_tokens=in_tok, output_tokens=out_tok)
    cache.log_call(route, lang, cache_hit=False,
                   input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency_ms)
    if durable_key:
        _durable_put(durable_key, text)
    return text
