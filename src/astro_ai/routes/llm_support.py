"""LLM plumbing shared by the route modules: caching + error presentation.

Extracted verbatim from ``main.py`` (issue #154). Deliberately independent of
``routes.deps`` — these two are leaf modules and neither imports the other, so
importing one never drags in the other's import-order constraints.
Nothing in this package may import ``astro_ai.main``.
"""

from __future__ import annotations

import logging
import time as _time

from astro_ai import cache, events, notify
from astro_ai import providers as llm_providers
from astro_ai.providers import AllProvidersExhausted
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
    """
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


def _cached(
    cache_key: str,
    *,
    route: str,
    lang: str,
    ttl_days: int | None,
    call_fn,
) -> str:
    """Cache-wrap an LLM call. Logs every attempt (hit or miss) for /admin/usage.

    `call_fn` is a zero-arg callable that returns the LLM text. We do the
    cache-check and the per-route logging here so every reading benefits from
    the same observability surface without duplicating boilerplate.

    Self-healing: if the cached text fails the same quality check that the
    provider chain uses (e.g. missing '## Heading' markers), we treat it as
    a miss and re-generate — silently cleaning up any garbage that snuck
    into the cache before quality-gating was live.
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
    started = _time.time()
    text = call_fn()
    latency_ms = int((_time.time() - started) * 1000)
    in_tok = cache.estimate_tokens(text) * 2  # input ≈ 2x output for our prompts (rough)
    out_tok = cache.estimate_tokens(text)
    cache.put(cache_key, text, route=route, ttl_days=ttl_days,
              input_tokens=in_tok, output_tokens=out_tok)
    cache.log_call(route, lang, cache_hit=False,
                   input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency_ms)
    return text
