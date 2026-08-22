"""Janma Kundli — the natal reading, its share snapshots and the email-it route.

Issue #154. Owns:
    POST /reading               form submit → save chart → 303 to GET /kundli
    GET  /reading               safety net for stale GETs → 303 to /kundli
    GET  /natal                 legacy URL → 301 to /kundli
    GET  /kundli                the reading (or the SEO landing page when no
                                chart is saved)
    POST /email/kundli-reading  email the signed-in user their saved reading
    POST /kundli/snapshot       create a public, 30-day share link
    GET  /r/{short_id}          public read-only render of a share snapshot

plus the shared ``_render_natal_for`` renderer and the two in-process
rate-limit dicts (``_EMAIL_KUNDLI_LAST_SENT``, ``_SNAPSHOT_CREATED_TODAY``)
that the email and snapshot routes own.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
import os
from datetime import date

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from astro_ai import cache, email_sender, events, notify, snapshots, users
from astro_ai import providers as llm_providers
from astro_ai.chart import (
    ChartError,
    compute_bhagya_score,
    compute_chart,
    compute_dasha_state,
    compute_dashamsa_chart,
    compute_life_chapters,
    compute_manglik_details,
    compute_navamsha_chart,
    compute_sade_sati_details,
    compute_vedic_flags,
    compute_yogas,
    symbol_for_rashi_label,
)
from astro_ai.llm import BirthDetails, generate_reading, parse_sectioned_reading
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import (
    PROMPT_PATH,
    _ask_cta_ctx,
    _lang,
    _save_collection_synced,
    _site_url,
    templates,
)
from astro_ai.routes.llm_support import _cached, _fire_error_alert, _llm_error_friendly
from astro_ai.session import load_collection, load_user

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/reading")
async def reading(
    request: Request,
    name: str = Form(default=""),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    birth_place: str = Form(...),
) -> Response:
    """Form submission → save chart to cookie → 303 redirect to GET /kundli.

    Post-Redirect-Get pattern. The actual reading renders at GET /kundli,
    not here. Benefits:
      - Browser URL bar shows `/kundli` after submission (bookmarkable,
        matches the term users actually search for).
      - Refreshing the result page doesn't re-submit the form.
      - The lang picker's `next` field captures `/kundli` (a valid GET
        route) instead of `/reading` (POST only — which used to return
        a JSON 405 when the lang form tried to redirect back to it).
      - Back button works correctly.
    """
    details = BirthDetails(
        name=name.strip(),
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place.strip(),
    )
    # Validate chart math + geocoding up-front so the user sees birth-date
    # / city errors immediately instead of after a redirect dance.
    try:
        compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:reading_form")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    # Cap check before saving so we don't accept a chart we can't store.
    try:
        collection = load_collection(request).add(details)
    except ValueError as err:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Chart limit reached", "message": str(err)},
            status_code=400,
        )
    response = RedirectResponse("/kundli", status_code=303)
    _save_collection_synced(response, collection, request)
    # notify.kundli_generated fires from _render_natal_for after the LLM
    # succeeds — that way the notification includes the model that actually
    # served the request. Firing here would fire on form submit, before the
    # LLM even runs (redirect target renders it).
    return response


@router.get("/reading")
async def reading_get() -> RedirectResponse:
    """Safety net for any stale GET to /reading (bookmarks, lang next=, etc.)."""
    return RedirectResponse("/kundli", status_code=303)


@router.get("/natal", include_in_schema=False)
async def natal_legacy_redirect() -> RedirectResponse:
    """Old URL — kept so existing bookmarks, SEO indexes, and any cached
    SW responses still work. Permanent redirect to the renamed canonical
    /kundli route."""
    return RedirectResponse("/kundli", status_code=301)


@router.get("/kundli", response_class=HTMLResponse)
async def kundli(request: Request) -> HTMLResponse:
    """Render the Janma Kundli reading for the currently active saved chart.

    When no chart is saved (typical for Googlebot + first-time visitors)
    we render an SEO landing page with the birth-details form inline instead
    of redirecting to home. Before this change (SEO audit #123) Googlebot
    was 303-redirected to '/' with a canonical pointing at '/', so /kundli
    had no indexable page of its own — competitors' /kundli URLs sat on
    2,000-word explainers while ours was invisible in search.
    """
    saved = load_collection(request).active
    if saved is None:
        return templates.TemplateResponse(
            request, "kundli_landing.html",
            {"lang": _lang(request)},
        )
    return await _render_natal_for(request, saved.to_birth_details(), chart_id=saved.id)


async def _render_natal_for(request: Request, details: BirthDetails,
                            chart_id: str = "") -> HTMLResponse:
    """Shared natal-reading renderer used by both GET /natal and POST /reading."""
    try:
        chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
    except ChartError as err:
        _fire_error_alert(request, err, "chart:natal_render")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't compute the chart", "message": str(err)},
            status_code=400,
        )
    if not os.environ.get("OPENAI_API_KEY"):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": "API key not configured",
                "message": (
                    "The server can't reach the LLM because OPENAI_API_KEY isn't set. "
                    "Add it to .env and reload."
                ),
            },
            status_code=503,
        )
    flags = compute_vedic_flags(chart)
    life_chapters = compute_life_chapters(chart)
    dasha_state = compute_dasha_state(chart)
    lang = _lang(request)
    chart_fp = cache.fingerprint_chart(details.birth_date, details.birth_time, details.birth_place)
    prompt_fp = cache.fingerprint_prompt(PROMPT_PATH)
    cache_key = f"natal:{chart_fp}:{lang}:{prompt_fp}"
    # Detect cache hit BEFORE _cached() so we know whether this render
    # counts as a fresh generation (worth notifying about) or a re-view
    # of an already-generated reading (silent — user is just refreshing
    # or navigating back to their chart). Cheap: one extra cache lookup.
    was_cached = cache.get(cache_key) is not None
    try:
        reading_text = _cached(
            cache_key, route="natal", lang=lang, ttl_days=None,
            call_fn=lambda: generate_reading(
                details, chart=chart, flags=flags, life_chapters=life_chapters,
                prompt_path=PROMPT_PATH, lang=lang, dasha_state=dasha_state,
            ),
        )
    except Exception as err:
        log.exception("natal LLM generation failed")
        _fire_error_alert(request, err, "natal")
        _title, _msg = _llm_error_friendly(err)
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "title": _title,
                "message": _msg,
            },
            status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
        )
    sections = parse_sectioned_reading(reading_text)
    sade_sati = compute_sade_sati_details(chart)

    # Fire owner-notification + activity event ONLY on fresh generation.
    # Every /kundli page render (refresh, back-nav, HTMX-boosted click)
    # used to re-fire these — annoying duplicate Telegram pings for the
    # same person + inflated activity counts. Cache-hit means the user
    # is re-viewing their already-generated reading, not a new event.
    _u_natal = load_user(request)
    if not was_cached:
        notify.kundli_generated(
            name=details.name, birth_date=details.birth_date,
            birth_time=details.birth_time, birth_place=details.birth_place,
            lang=lang, user_email=(_u_natal.email if _u_natal else ""),
            model=llm_providers.last_used_model(),
        )
        events.record(
            type="form_kundli",
            email=(_u_natal.email if _u_natal else ""),
            data={
                "name": details.name, "birth_date": details.birth_date,
                "birth_time": details.birth_time, "birth_place": details.birth_place,
                "lang": lang, "model": llm_providers.last_used_model(),
                "rashi_lagna": chart.lagna_rashi,
                "rashi_moon": next((p.rashi for p in chart.planets if p.name == "Moon"), ""),
                "rashi_sun": next((p.rashi for p in chart.planets if p.name == "Sun"), ""),
            },
        )

    # Persist to signed-in user's reading history so they can revisit it
    # from any device. Best-effort — never fails the render.
    _signed_in = load_user(request)
    if _signed_in and _signed_in.sub:
        _title = f"{details.name}'s Kundli reading" if details.name else "Kundli reading"
        try:
            users.save_reading(
                sub=_signed_in.sub,
                kind="natal",
                chart_id=chart_id,
                title=_title,
                body=reading_text,
                meta={"birth_date": details.birth_date,
                      "birth_place": details.birth_place},
            )
        except Exception:  # noqa: BLE001 — history is best-effort
            log.warning("save_reading(natal) failed for %s", _signed_in.sub)

    # Pre-compute SS progress for the template (Jinja can't do date arithmetic cleanly).
    ss_progress = 0
    ss_elapsed_years = 0.0
    ss_remaining_years = 0.0
    if sade_sati.is_active and sade_sati.overall_start and sade_sati.overall_end:
        today = date.today()
        total_days = (sade_sati.overall_end - sade_sati.overall_start).days
        elapsed_days = max(0, min(total_days, (today - sade_sati.overall_start).days))
        ss_progress = int(elapsed_days / total_days * 100) if total_days else 0
        ss_elapsed_years = round(elapsed_days / 365.25, 1)
        ss_remaining_years = round((total_days - elapsed_days) / 365.25, 1)

    # Zodiac glyphs for the three summary chips (Lagna, Moon, Sun).
    moon_plt = next(p for p in chart.planets if p.name == "Moon")
    sun_plt  = next(p for p in chart.planets if p.name == "Sun")
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "details": details,
            "reading": reading_text,
            "sections": sections,
            "chart": chart,
            "flags": flags,
            "lang": lang,
            "lagna_glyph": symbol_for_rashi_label(chart.lagna_rashi),
            "moon_glyph":  symbol_for_rashi_label(moon_plt.rashi),
            "sun_glyph":   symbol_for_rashi_label(sun_plt.rashi),
            **_ask_cta_ctx(request, hint="about your chart"),
            # Bhagya Score — 0-100 gamified 'current chapter weather' reading.
            # Aggregates yogas, doshas, dashas, dignities into one number
            # with 'why' drivers for transparency. Feature spec in
            # chart.py compute_bhagya_score.
            "bhagya_score": compute_bhagya_score(chart, lang=_lang(request)),
            # Structured insight panels — see chart.py for shape.
            "manglik":  compute_manglik_details(chart),
            "navamsha_chart": compute_navamsha_chart(chart),
            "dashamsa_chart": compute_dashamsa_chart(chart),
            "yogas":    compute_yogas(chart),
            "sade_sati": sade_sati,
            "dasha":    compute_dasha_state(chart),
            # Pre-computed SS timeline values for the panel.
            "sade_sati_progress": ss_progress,
            "sade_sati_elapsed_years": ss_elapsed_years,
            "sade_sati_remaining_years": ss_remaining_years,
        },
    )


_EMAIL_KUNDLI_LAST_SENT: dict[str, float] = {}
_EMAIL_KUNDLI_MIN_INTERVAL_SEC = 60.0  # user can email themselves at most once per minute

# Sweep threshold for the two rate-limit dicts below (#182). Both grew without
# bound for the lifetime of a Cloud Run instance; the snapshot one is keyed by
# user sub OR CLIENT IP, so every distinct anonymous visitor left a permanent
# entry. A slow leak, worst on exactly the long-lived warm instances we want.
#
# NOT the `clear()` that routes/deps.py uses for _PANCHANG_STRIP_CACHE.
# That is right for a cache — dropping a cached value costs a recompute — and
# WRONG for a rate limiter, where wiping the dict hands every currently
# limited caller an immediate reset. Someone at their daily snapshot cap would
# only need to wait for an unrelated visitor to push the dict past the
# threshold. These sweeps therefore drop entries by AGE, so live limits
# survive and only expired ones go.
_RATE_DICT_SWEEP_AT = 500


def _sweep_expired(store: dict, is_expired) -> None:
    """Drop expired keys from a module-level rate-limit dict.

    Materialises the key list before mutating: these dicts are shared across
    worker threads, and iterating one while another request writes to it
    raises "dictionary changed size during iteration". Individual dict
    operations are atomic under the GIL, so a snapshot of the keys plus
    per-key deletes is safe without a lock. A key written during the sweep
    is simply missed and swept next time — it is fresh, so that is correct.
    """
    for key in list(store.keys()):
        value = store.get(key)
        if value is not None and is_expired(value):
            store.pop(key, None)


@router.post("/email/kundli-reading")
async def email_kundli_reading(request: Request) -> JSONResponse:
    """Email the signed-in user their most-recent saved Kundli reading.

    Auth-gated (only signed-in users, sending to their own address) so
    there's no abuse vector — a caller can never target a third-party
    email. Rate-limited per-user in-memory to prevent hammering.
    """
    user = load_user(request)
    if not user or not user.sub or not user.email:
        return JSONResponse({"ok": False, "error": "sign_in_required"}, status_code=401)

    import time
    now = time.time()
    last = _EMAIL_KUNDLI_LAST_SENT.get(user.sub, 0.0)
    if now - last < _EMAIL_KUNDLI_MIN_INTERVAL_SEC:
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)

    readings = users.list_readings(user.sub, limit=5)
    kundli_reading = next((r for r in readings if r.kind == "natal"), None)
    if not kundli_reading:
        return JSONResponse({"ok": False, "error": "no_reading"}, status_code=404)

    lang = _lang(request)
    sections = parse_sectioned_reading(kundli_reading.body)

    saved_chart = load_collection(request).active
    chart_ctx = None
    birth_details_ctx = None
    if saved_chart is not None:
        details = saved_chart.to_birth_details()
        birth_details_ctx = {
            "name": details.name,
            "birth_date": details.birth_date,
            "birth_time": details.birth_time,
            "birth_place": details.birth_place,
        }
        try:
            chart_ctx = compute_chart(details.birth_date, details.birth_time, details.birth_place)
        except Exception:  # noqa: BLE001 — chart is best-effort for the email header
            chart_ctx = None

    ctx = {
        "lang": lang,
        "site_url": _site_url(),
        "user_name": user.name or "",
        "birth_details": birth_details_ctx,
        "chart": chart_ctx,
        "sections": sections,
        "unsubscribe_url": "",  # transactional — no subscription list to leave
    }
    html = templates.env.get_template("email/kundli_reading.html").render(**ctx)
    subject = (
        "आपकी कुंडली रीडिंग — Shubh Bhagya"
        if lang == "hi"
        else "Your Kundli Reading — Shubh Bhagya"
    )
    ok = email_sender.send(user.email, subject=subject, html=html)
    if ok:
        # An entry older than the interval can no longer rate-limit anyone —
        # the next check subtracts and passes regardless — so it is garbage
        # (#182). Swept on write, the only place this dict grows.
        if len(_EMAIL_KUNDLI_LAST_SENT) > _RATE_DICT_SWEEP_AT:
            cutoff = now - _EMAIL_KUNDLI_MIN_INTERVAL_SEC
            _sweep_expired(_EMAIL_KUNDLI_LAST_SENT, lambda ts: ts < cutoff)
        _EMAIL_KUNDLI_LAST_SENT[user.sub] = now
        return JSONResponse({"ok": True, "email": user.email})
    # Brevo failed — infra issue worth an alert (rate limit, key rotation,
    # network flake). Raise an exception object so _fire_error_alert has
    # something structured to report.
    _fire_error_alert(request, RuntimeError(f"Brevo send failed for {user.email}"), "email:kundli")
    return JSONResponse({"ok": False, "error": "send_failed"}, status_code=502)


# Per-user rate limit on snapshot creation — 5/day/user cap. Keeps casual
# WhatsApp-share behaviour cheap but prevents someone from generating a
# thousand snapshots and bloating the storage bucket.
_SNAPSHOT_CREATED_TODAY: dict[str, list[float]] = {}
_SNAPSHOT_DAILY_CAP = 5


def _snapshot_rate_ok(key: str) -> bool:
    """True if `key` (user sub or IP) hasn't exceeded today's snapshot cap."""
    import time as _t
    now = _t.time()
    day_ago = now - 86400
    # A key whose every hit is older than the 24h window can never affect a
    # decision again, so it is pure garbage (#182). Swept here rather than on
    # a timer because this is the only place the dict is written.
    if len(_SNAPSHOT_CREATED_TODAY) > _RATE_DICT_SWEEP_AT:
        _sweep_expired(
            _SNAPSHOT_CREATED_TODAY,
            lambda hits: not any(t > day_ago for t in hits),
        )
    hits = [t for t in _SNAPSHOT_CREATED_TODAY.get(key, []) if t > day_ago]
    if len(hits) >= _SNAPSHOT_DAILY_CAP:
        _SNAPSHOT_CREATED_TODAY[key] = hits
        return False
    hits.append(now)
    _SNAPSHOT_CREATED_TODAY[key] = hits
    return True


@router.post("/kundli/snapshot")
async def create_kundli_snapshot(request: Request) -> JSONResponse:
    """Create a public read-only snapshot of the caller's active Kundli reading.

    Returns a short URL the caller can paste into WhatsApp or any messenger;
    the URL renders a public, expiry-gated view of the exact reading. See
    snapshots.py for storage + expiry semantics (30-day TTL).

    Requires: an active chart in the session cookie AND (if signed in) a
    saved reading in the user's history; anonymous callers get the reading
    text from the fresh render path — no signed-in requirement for the
    happy path because most /kundli visitors are anonymous.
    """
    saved = load_collection(request).active
    if saved is None:
        return JSONResponse({"ok": False, "error": "no_chart"}, status_code=400)

    # Rate-limit by signed-in sub if available, else by client IP. Loose but
    # sufficient for MVP; a real abuse case would need per-IP + captcha.
    user = load_user(request)
    rate_key = user.sub if (user and user.sub) else (
        request.client.host if request.client else "unknown"
    )
    if not _snapshot_rate_ok(rate_key):
        return JSONResponse(
            {"ok": False, "error": "rate_limited",
             "message": "Too many share links created today. Try again tomorrow."},
            status_code=429,
        )

    # Get the reading text — prefer the persisted reading (signed-in users),
    # else regenerate from cache. Regeneration path is fast — cache hits
    # for the same chart+lang; only cold-cache visitors take the LLM hit.
    details = saved.to_birth_details()
    lang = _lang(request)

    reading_text = None
    if user and user.sub:
        readings = users.list_readings(user.sub, limit=10)
        for r in readings:
            if r.kind == "natal":
                reading_text = r.body
                break

    if reading_text is None:
        # Anonymous or no saved reading — synth from cache (or LLM if missed).
        try:
            chart = compute_chart(details.birth_date, details.birth_time, details.birth_place)
            flags = compute_vedic_flags(chart)
            life_chapters = compute_life_chapters(chart)
            dasha_state = compute_dasha_state(chart)
            chart_fp = cache.fingerprint_chart(details.birth_date, details.birth_time, details.birth_place)
            prompt_fp = cache.fingerprint_prompt(PROMPT_PATH)
            cache_key = f"natal:{chart_fp}:{lang}:{prompt_fp}"
            reading_text = _cached(
                cache_key, route="natal", lang=lang, ttl_days=None,
                call_fn=lambda: generate_reading(
                    details, chart=chart, flags=flags, life_chapters=life_chapters,
                    prompt_path=PROMPT_PATH, lang=lang, dasha_state=dasha_state,
                ),
            )
        except Exception as err:  # noqa: BLE001 — snapshot can't be built without a reading
            log.exception("snapshot: reading generation failed")
            _fire_error_alert(request, err, "snapshot:reading")
            return JSONResponse(
                {"ok": False, "error": "reading_unavailable"},
                status_code=502,
            )

    birth_details_dict = {
        "name": details.name or "",
        "birth_date": details.birth_date,
        "birth_time": details.birth_time,
        "birth_place": details.birth_place,
    }
    snap = snapshots.create(
        birth_details=birth_details_dict,
        reading_text=reading_text,
        lang=lang,
        created_by_sub=(user.sub if (user and user.sub) else ""),
    )
    if snap is None:
        # Storage unavailable (no GCS bucket configured OR write failed).
        # Fall back to a graceful error rather than a broken WhatsApp share.
        _fire_error_alert(
            request, RuntimeError("snapshots.create returned None (GCS + local fallback both failed)"),
            "snapshot:storage",
        )
        return JSONResponse(
            {"ok": False, "error": "storage_unavailable",
             "message": "Sharing is temporarily unavailable. Please try again later."},
            status_code=503,
        )
    return JSONResponse({
        "ok": True,
        "id": snap.id,
        "url": f"{_site_url()}/r/{snap.id}",
        "expires_at": snap.expires_at,
    })


@router.get("/r/{short_id}", response_class=HTMLResponse)
async def view_kundli_snapshot(request: Request, short_id: str) -> HTMLResponse:
    """Public read-only render of a shared Kundli snapshot.

    Renders the sender's reading (chart + LLM sections + flags) with a
    prominent 'Get your own free reading' CTA. No edit/regenerate paths;
    no session-state mutation. Expired snapshots 404.
    """
    snap = snapshots.load(short_id)
    if snap is None:
        return templates.TemplateResponse(
            request,
            "snapshot_expired.html",
            {"lang": _lang(request), "short_id": short_id},
            status_code=404,
        )

    # Re-compute chart deterministically from birth details — cheaper than
    # storing the full chart object in the snapshot, and always fresh with
    # any chart.py improvements shipped since the snapshot was created.
    try:
        chart = compute_chart(
            snap.birth_details.get("birth_date", ""),
            snap.birth_details.get("birth_time", ""),
            snap.birth_details.get("birth_place", ""),
        )
    except ChartError as err:
        _fire_error_alert(request, err, "snapshot:view")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Couldn't render shared reading", "message": str(err)},
            status_code=400,
        )

    sections = parse_sectioned_reading(snap.reading_text)
    sade_sati = compute_sade_sati_details(chart)
    moon_plt = next(p for p in chart.planets if p.name == "Moon")
    sun_plt = next(p for p in chart.planets if p.name == "Sun")

    ss_progress = 0
    ss_elapsed_years = 0.0
    ss_remaining_years = 0.0
    if sade_sati.is_active and sade_sati.overall_start and sade_sati.overall_end:
        today = date.today()
        total_days = (sade_sati.overall_end - sade_sati.overall_start).days
        elapsed_days = max(0, min(total_days, (today - sade_sati.overall_start).days))
        ss_progress = int(elapsed_days / total_days * 100) if total_days else 0
        ss_elapsed_years = round(elapsed_days / 365.25, 1)
        ss_remaining_years = round((total_days - elapsed_days) / 365.25, 1)

    # Rebuild BirthDetails so result.html can treat this like a normal render.
    details = BirthDetails(
        name=snap.birth_details.get("name", ""),
        birth_date=snap.birth_details.get("birth_date", ""),
        birth_time=snap.birth_details.get("birth_time", ""),
        birth_place=snap.birth_details.get("birth_place", ""),
    )
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "details": details,
            "reading": snap.reading_text,
            "sections": sections,
            "chart": chart,
            "flags": compute_vedic_flags(chart),
            "lang": snap.lang,
            "lagna_glyph": symbol_for_rashi_label(chart.lagna_rashi),
            "moon_glyph": symbol_for_rashi_label(moon_plt.rashi),
            "sun_glyph": symbol_for_rashi_label(sun_plt.rashi),
            "manglik": compute_manglik_details(chart),
            "navamsha_chart": compute_navamsha_chart(chart),
            "dashamsa_chart": compute_dashamsa_chart(chart),
            "yogas": compute_yogas(chart),
            "sade_sati": sade_sati,
            "dasha": compute_dasha_state(chart),
            "sade_sati_progress": ss_progress,
            "sade_sati_elapsed_years": ss_elapsed_years,
            "sade_sati_remaining_years": ss_remaining_years,
            # Snapshot-mode flag — result.html hides interactive controls
            # (bookmark/email/sign-in/return-triggers) when this is set.
            "is_snapshot": True,
            "snapshot": snap,
        },
    )


