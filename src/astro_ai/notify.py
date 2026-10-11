"""Telegram notifications for owner monitoring.

Fires a Telegram message to the site owner's private bot chat whenever
users do something interesting: generate a Kundli, do Kundli matching,
ask a Q&A, sign in, or subscribe. Meant as a real-time pulse — analytics
show aggregates eventually, but this shows *what actually happened* in
the last few seconds.

Setup:
    1. Create a bot via @BotFather on Telegram → get bot token.
    2. Start a chat with the bot ("Hi!") so it can message you.
    3. Fetch your chat_id: curl https://api.telegram.org/bot<TOKEN>/getUpdates
       — look for "chat":{"id":123456789}.
    4. Set env vars:
         BHAGYA_TELEGRAM_BOT_TOKEN=<bot token from BotFather>
         BHAGYA_TELEGRAM_OWNER_CHAT_ID=<your chat_id>

Silent no-op when either env var is unset — safe for local dev, safe for
preview envs. Zero-config to disable.

Fire-and-forget: every notify() call spawns an asyncio task and returns
immediately. Never blocks the user request. Errors log-and-swallow.

Privacy (#255): the four birth-data alerts -- `kundli_generated`,
`matching_done`, `dosha_checked`, `numerology_computed` -- carry NO PII. They
send a diagnostic (rashi names, model, tokens, latency, cache state) and an
8-hex `identity.short_key`, which lets the owner find the matching event
without the alert saying whose it is. Name, birth date/time/place and email
are never passed to them.

These formatters STILL carry PII, and templates/privacy.html discloses it:
  - ask_submitted      question text + signed-in email
  - new_signin         email + name
  - subscribed         email
  - feedback_submitted message text + email
  - error_seen         exception message + traceback (+ email); a ChartError,
                       whose message embeds the birth place, is redacted
                       upstream in routes/llm_support._fire_error_alert
  - muhurat_computed   city + signed-in email
This is the site owner's private bot chat, not a public group; the bot token
grants send-only permission.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

import httpx

log = logging.getLogger(__name__)

_TG_TOKEN_ENV = "BHAGYA_TELEGRAM_BOT_TOKEN"
_TG_CHAT_ENV = "BHAGYA_TELEGRAM_OWNER_CHAT_ID"

# In-memory dedup — same event key within the window is suppressed.
# Guards against double-submit from users tapping the button twice AND
# rapid re-fires from browser prefetch, HTMX secondary swap, etc.
#
# CAVEAT: Cloud Run auto-scales to N instances during load — each
# instance has its OWN in-memory _LAST_FIRED dict, so the same event
# routed to different pods within the same window can still fire N
# times. Fix that at the CALL SITE by skipping notify on cache hits
# (see main.py _render_natal_for et al.) — that eliminates the vast
# majority of duplicates. The in-memory dedup here is a per-instance
# safety net, not a distributed guarantee.
_LAST_FIRED: dict[str, float] = {}
_DEDUP_WINDOW_SEC = 300.0   # 5 min — covers refresh, back-nav, prefetch, retry


def _config() -> Optional[tuple[str, str]]:
    """(token, chat_id) if both env vars set, else None (no-op)."""
    token = os.environ.get(_TG_TOKEN_ENV, "").strip()
    chat_id = os.environ.get(_TG_CHAT_ENV, "").strip()
    if not token or not chat_id:
        return None
    return token, chat_id


def _dedup_ok(dedup_key: str) -> bool:
    """True if this event key hasn't fired in the last 3 seconds."""
    now = time.time()
    last = _LAST_FIRED.get(dedup_key, 0.0)
    if now - last < _DEDUP_WINDOW_SEC:
        return False
    _LAST_FIRED[dedup_key] = now
    # Opportunistic housekeeping — trim entries older than 5 minutes so
    # the dict doesn't grow forever.
    cutoff = now - 300
    stale = [k for k, t in _LAST_FIRED.items() if t < cutoff]
    for k in stale:
        _LAST_FIRED.pop(k, None)
    return True


async def _send_async(token: str, chat_id: str, text: str) -> None:
    """POST to Telegram sendMessage. Log-and-swallow on failure."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                log.warning("telegram: sendMessage returned %d: %s",
                            resp.status_code, resp.text[:200])
    except Exception as err:  # noqa: BLE001 — never fail the user request
        log.warning("telegram: send failed: %s", err)


def notify(text: str, *, dedup_key: str = "") -> None:
    """Fire-and-forget Telegram notification. Silent no-op when unconfigured.

    Call from any endpoint after the user's response has been prepared —
    it schedules the send as an asyncio task and returns immediately.
    """
    config = _config()
    if config is None:
        return
    if dedup_key and not _dedup_ok(dedup_key):
        return
    token, chat_id = config
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_send_async(token, chat_id, text))
    except RuntimeError:
        # No running loop — likely called outside async context. Skip.
        log.debug("telegram: no event loop; skipping notify")


# ─── Event formatters ────────────────────────────────────────────────
#
# Each format_X returns a Telegram-friendly Markdown string. Keep messages
# terse enough to be scannable in the phone notification preview.


def _escape_md(s: str) -> str:
    """Escape Telegram Markdown special chars in user-supplied strings."""
    if not s:
        return ""
    for ch in ("_", "*", "`", "["):
        s = s.replace(ch, "\\" + ch)
    return s


def chart_rashis(chart) -> tuple[str, str, str]:
    """(lagna, moon, sun) rashi names of a computed chart -- the one birth-derived
    fact the diagnostic alerts and the `form_kundli` event may carry."""
    def _rashi_of(name: str) -> str:
        return next((p.rashi for p in chart.planets if p.name == name), "")
    return chart.lagna_rashi, _rashi_of("Moon"), _rashi_of("Sun")


def _rashi_line(lagna: str, moon: str, sun: str) -> str:
    bits = [f"{k}={_escape_md(v)}" for k, v in
            (("lagna", lagna), ("moon", moon), ("sun", sun)) if v]
    return "📊 " + " · ".join(bits) if bits else ""


def _cost_line(lang: str, model: str, tokens: Optional[int],
               latency_s: Optional[float], cache: str) -> str:
    """lang · model · tokens · latency · cache. A field that is absent is
    omitted, never printed as None or guessed -- `tokens` is None whenever the
    provider returned no usage block."""
    bits = [lang] if lang else []
    if model:
        bits.append(f"🤖 {_escape_md(model)}")
    if tokens is not None:
        bits.append(f"{tokens:,} tok")
    if latency_s is not None:
        bits.append(f"{latency_s:.1f}s")
    if cache:
        bits.append(f"cache={cache}")
    return "🌐 " + " · ".join(bits) if bits else ""


def _compose(*lines: str) -> str:
    return "\n".join(line for line in lines if line)


def kundli_generated(
    *, lagna: str, moon: str, sun: str, lang: str, key: str,
    model: str = "", tokens: Optional[int] = None,
    latency_s: Optional[float] = None, cache: str = "miss",
) -> None:
    """/reading → new Kundli generated. A diagnostic, not an identity (#255).

    `key` is `identity.short_key(...)`. The dedup key is built from it, so no
    birth detail or email sits in the in-memory dict either.
    """
    notify(
        _compose("🕉  *Kundli generated*", _rashi_line(lagna, moon, sun),
                 _cost_line(lang, model, tokens, latency_s, cache),
                 f"🔖 {key}" if key else ""),
        dedup_key=f"kundli:{key}",
    )


def matching_done(
    *, groom_moon: str, bride_moon: str, total_score: str, lang: str,
    groom_key: str, bride_key: str, model: str = "",
    tokens: Optional[int] = None, latency_s: Optional[float] = None,
    cache: str = "miss",
) -> None:
    """/matching POST → Ashtakoot matching complete. No names or dates (#255)."""
    moons = " · ".join(
        f"{k}={_escape_md(v)}" for k, v in
        (("groom moon", groom_moon), ("bride moon", bride_moon)) if v)
    notify(
        _compose("💍  *Kundli matching*",
                 f"⭐ Ashtakoot: *{total_score}*",
                 f"📊 {moons}" if moons else "",
                 _cost_line(lang, model, tokens, latency_s, cache),
                 f"🔖 {groom_key} · {bride_key}"),
        dedup_key=f"matching:{groom_key}:{bride_key}",
    )


def ask_submitted(
    *, question: str, category: str, lang: str, user_email: str = "",
    model: str = "",
) -> None:
    """/ask POST → chart-based Q&A."""
    trimmed = question.strip().replace("\n", " ")
    if len(trimmed) > 240:
        trimmed = trimmed[:240] + "…"
    parts = [
        "❓  *Ask question*",
        f"📝 {_escape_md(trimmed)}",
        f"🏷 {category} · lang={lang}",
    ]
    if user_email:
        parts.append(f"✉️ {_escape_md(user_email)}")
    if model:
        parts.append(f"🤖 {_escape_md(model)}")
    dedup = f"ask:{user_email}:{trimmed[:80]}"
    notify("\n".join(parts), dedup_key=dedup)


def new_signin(*, email: str, name: str, first_time: bool) -> None:
    """/auth/google → user signed in."""
    parts = [
        "🔐  *" + ("New user signed up" if first_time else "User signed in") + "*",
        f"👤 {_escape_md(name) or '_(no name)_'}",
        f"✉️ {_escape_md(email)}",
    ]
    dedup = f"signin:{email}"
    notify("\n".join(parts), dedup_key=dedup)


def subscribed(*, email: str, source: str, lang: str) -> None:
    """/subscribe POST → email newsletter opt-in."""
    parts = [
        "📬  *Newsletter subscribe*",
        f"✉️ {_escape_md(email)}",
        f"📍 source={source} · lang={lang}",
    ]
    dedup = f"subscribe:{email}"
    notify("\n".join(parts), dedup_key=dedup)


def feedback_submitted(*, type: str, message: str, page: str = "", email: str = "") -> None:
    """/feedback POST → user submitted feedback via floating widget."""
    label = {"problem": "🐛 Problem", "feature": "✨ Feature request",
             "other": "💬 Feedback"}.get(type, "💬 Feedback")
    trimmed = (message or "").strip().replace("\n", " ")
    if len(trimmed) > 300:
        trimmed = trimmed[:300] + "…"
    parts = [
        f"{label}",
        f"📝 {_escape_md(trimmed) or '_(no message)_'}",
    ]
    if page:
        parts.append(f"📄 page={_escape_md(page)}")
    if email:
        parts.append(f"✉️ {_escape_md(email)}")
    dedup = f"feedback:{email or 'anon'}:{trimmed[:80]}"
    notify("\n".join(parts), dedup_key=dedup)


def dosha_checked(
    *, dosha_type: str, is_present: bool, key: str, lagna: str = "",
    moon: str = "", sun: str = "", extra: str = "",
) -> None:
    """/manglik-check | /sade-sati-check | /kaal-sarp-check completion.

    `dosha_type` = 'Manglik' | 'Sade Sati' | 'Kaal Sarp'. `extra` is a short
    detail string (severity, phase, type) -- keep it human-readable. No birth
    place, name or email (#255); `key` is `identity.short_key(...)`.
    """
    icon = {"Manglik": "🔥", "Sade Sati": "🪐", "Kaal Sarp": "🐍"}.get(dosha_type, "🔮")
    status = "*present*" if is_present else "clear"
    notify(
        _compose(f"{icon}  *{dosha_type} check*",
                 f"📊 {status}" + (f" · {_escape_md(extra)}" if extra else ""),
                 _rashi_line(lagna, moon, sun),
                 f"🔖 {key}" if key else ""),
        dedup_key=f"dosha:{dosha_type}:{key}",
    )


def muhurat_computed(
    *, event_type: str, city: str, days_range: int,
    good_count: int, user_email: str = "",
) -> None:
    """/muhurat POST → event-type muhurat search completed."""
    parts = [
        "📅  *Muhurat search*",
        f"🎯 {_escape_md(event_type)} in {_escape_md(city)}",
        f"📊 {good_count} auspicious of {days_range} days",
    ]
    if user_email:
        parts.append(f"✉️ {_escape_md(user_email)}")
    dedup = f"muhurat:{event_type}:{user_email or city}"
    notify("\n".join(parts), dedup_key=dedup)


def numerology_computed(*, system: str, life_path: int, key: str) -> None:
    """/numerology POST → numerology reading generated. No name or date (#255);
    `key` is `identity.short_key(identity_key(name, birth_date))`."""
    notify(
        _compose("🔢  *Numerology reading*",
                 f"🛤 life path *{life_path}* · system={_escape_md(system)}",
                 f"🔖 {key}" if key else ""),
        dedup_key=f"numerology:{key}",
    )


def error_seen(
    *,
    source: str,                 # short label — "natal", "today", "ask", "rashifal", ...
    error_type: str,             # exception class name — "AllProvidersExhausted", ...
    error_message: str,          # str(exception), possibly long — will be truncated
    path: str = "",              # request URL path, e.g. "/kundli"
    method: str = "",            # request method, e.g. "GET"
    user_email: str = "",        # signed-in user's email if any
    traceback_str: str = "",     # last ~1500 chars of the traceback
) -> None:
    """User-facing error → Telegram alert with full low-level details.

    Fired from LLM error handlers (rate limits, provider outages) AND from
    the global FastAPI exception handler (unhandled 500s). Includes enough
    detail to diagnose without opening the Cloud Run console.
    """
    # Trim overlong values so a single Telegram message fits (~4096 char cap).
    msg = error_message.strip().replace("\n", " ")
    if len(msg) > 500:
        msg = msg[:500] + "…"

    parts = [
        f"🚨  *Error: {_escape_md(source)}*",
        f"⚠️ `{error_type}`",
        f"💬 {_escape_md(msg)}",
    ]
    if method or path:
        parts.append(f"🌐 {method or '?'} {_escape_md(path)}")
    if user_email:
        parts.append(f"✉️ {_escape_md(user_email)}")
    if traceback_str:
        # Use a code block. Escape backticks so nesting doesn't break markdown.
        tb_trimmed = traceback_str.strip()
        if len(tb_trimmed) > 1500:
            tb_trimmed = "…" + tb_trimmed[-1500:]
        tb_trimmed = tb_trimmed.replace("`", "'")
        parts.append("```\n" + tb_trimmed + "\n```")

    # Dedup by (source, error type, path) within 3 seconds. If the same LLM
    # provider is 429-ing 20 users in a burst, you get ONE alert, not 20.
    dedup = f"error:{source}:{error_type}:{path}"
    notify("\n".join(parts), dedup_key=dedup)
