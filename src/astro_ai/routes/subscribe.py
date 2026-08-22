"""Daily-Rashifal subscriptions and the email blast (issue #154).

Owns:
    POST /subscribe/lookup            prefill the modal with existing prefs
    POST /subscribe                   subscribe + one-off welcome email
    GET  /unsubscribe                 HMAC-token one-click unsubscribe page
    POST /admin/send-daily-rashifal   the 7 AM IST Cloud Scheduler blast,
                                      basic-auth gated via require_admin

plus the email-building helpers only these routes use — ``_panchang_for_city``,
``_email_context``, ``_filter_rashi_sections``, ``_send_welcome_email`` — and
the three shared-content cache helpers moved out of ``main.py``'s header
region: ``_rashifal_teaser``, ``_daily_rashifal_text`` and the
``_shared_three_tier`` GCS → SQLite → LLM cache they sit on top of.

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``). Absolute imports only — nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
import time as _time
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from astro_ai import (
    cache,
    daily_cache,
    email_sender,
    festivals,
    notify,
    shloks,
    storage,
    subscribers,
    trivia,
)
from astro_ai import providers as llm_providers
from astro_ai.chart import (
    ChartError,
    compute_chart,
    compute_panchang,
    compute_transit_snapshot,
    symbol_for_rashi_label,
)
from astro_ai.llm import generate_rashifal, parse_sectioned_reading
from astro_ai.providers import AllProvidersExhausted
from astro_ai.routes.deps import (
    RASHIFAL_PROMPT_PATH,
    _site_url,
    require_admin,
    templates,
)
from astro_ai.routes.llm_support import _fire_error_alert, _llm_error_friendly

log = logging.getLogger(__name__)

router = APIRouter()


def _rashifal_teaser(body: str, sentences: int = 2) -> str:
    """Pull the first ~2 sentences of a rashi body for the scannable teaser.

    Used by both the web /rashifal accordion and the daily email <details>
    summary. Keeps the visible-by-default snippet short enough to scan all
    12 rashis in seconds; the rest reveals on click/tap.
    """
    import re as _re
    parts = _re.split(r"(?<=[.!?])\s+", (body or "").strip())
    teaser = " ".join(parts[:sentences]).strip()
    if len(parts) > sentences and not teaser.endswith(("...", "…")):
        # No ellipsis — the "Read full" button makes the truncation explicit.
        pass
    return teaser


def _daily_rashifal_text(
    *, lang: str, today_iso: str, cache_key: str, storage_key: str, call_fn,
) -> str:
    """Fetch today's Rashifal text with a Tier-0 daily JSON file in front.

    Read order:
      Tier 0  — data/daily_cache/rashifal/{date}-{lang}.json   (this instance, today)
      Tier 1  — GCS blob rashifal/{date}-{lang}-{promptfp}.txt (cross-instance)
      Tier 2  — SQLite key rashifal:{date}:{lang}:{promptfp}   (this instance)
      Tier 3  — LLM generation (12 per-rashi parallel calls)

    Every write propagates UP to fill the tier-0 file, so the FIRST request of
    the day pays the cold-generate cost and every subsequent same-day request
    on the same instance is a single-file read. The file is human-readable —
    `cat data/daily_cache/rashifal/{date}-{lang}.json` shows exactly what
    users are seeing today.
    """
    hit = daily_cache.get("rashifal", lang, today_iso)
    if hit is not None and isinstance(hit.get("text"), str) and hit["text"].strip():
        cache.log_call("rashifal", lang, cache_hit=True)
        return hit["text"]

    text = _shared_three_tier(
        route="rashifal",
        cache_key=cache_key,
        storage_key=storage_key,
        lang=lang,
        call_fn=call_fn,
    )
    # Write the tier-0 file so subsequent same-day/same-instance reads skip
    # everything below. Payload is intentionally verbose for humans debugging
    # why today's Rashifal looks a certain way.
    daily_cache.put("rashifal", lang, {
        "text": text,
        "lang": lang,
        "date_iso": today_iso,
    }, today_iso)
    return text


def _shared_three_tier(
    *, route: str, cache_key: str, storage_key: str, lang: str, call_fn,
) -> str:
    """3-tier cache for content that's identical across users: GCS → SQLite → LLM.

    Use this for routes where every visitor would get the same LLM output
    (e.g. Rashifal — today only). Per-chart routes should stick with
    `_cached`; GCS gives them nothing because the SQLite key is unique per
    user anyway.

    Cache writes propagate UP: a GCS hit also populates SQLite so the same
    instance skips the GCS round-trip next time; a fresh generation populates
    both layers.
    """
    # Tier 1: GCS — survives Cloud Run cold starts.
    persistent = storage.get(storage_key)
    if persistent is not None:
        ok, reason = llm_providers.passes_quality(persistent, route)
        if ok:
            cache.log_call(route, lang, cache_hit=True)
            cache.put(cache_key, persistent, route=route, ttl_days=1)  # warm SQLite
            return persistent
        log.warning("shared cache GCS: bad entry for route=%s (%s) — regenerating", route, reason)

    # Tier 2: SQLite — per-instance, alive while the container is.
    sqlite_hit = cache.get(cache_key)
    if sqlite_hit is not None:
        ok, reason = llm_providers.passes_quality(sqlite_hit, route)
        if ok:
            cache.log_call(route, lang, cache_hit=True)
            storage.put(storage_key, sqlite_hit)  # backfill GCS
            return sqlite_hit
        log.warning("shared cache SQLite: bad entry for route=%s (%s) — regenerating", route, reason)

    # Tier 3: LLM generation. Persist to both layers.
    started = _time.time()
    text = call_fn()
    latency_ms = int((_time.time() - started) * 1000)
    in_tok = cache.estimate_tokens(text) * 2
    out_tok = cache.estimate_tokens(text)
    cache.put(cache_key, text, route=route, ttl_days=1,
              input_tokens=in_tok, output_tokens=out_tok)
    cache.log_call(route, lang, cache_hit=False,
                   input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency_ms)
    storage.put(storage_key, text)
    return text


@router.post("/subscribe/lookup")
async def subscribe_lookup(email: str = Form(...)) -> JSONResponse:
    """Return the current preferences for a subscriber, or defaults if unknown.

    Called from the subscribe modal on email input (debounced) so the form
    prefills with the subscriber's existing lang / city / rashi choices. This
    prevents the silent reset that happens when a returning subscriber submits
    the form with default field values — the `subscribe()` upsert overwrites
    lang and rashi unconditionally.

    Same shape returned for subscribed and unsubscribed emails; the
    `subscribed` flag distinguishes them so the UI can show a "welcome back"
    hint. Not privacy-perfect (an attacker can enumerate) but proportional
    for a public astrology mailing list at this scale.
    """
    sub = subscribers.find_by_email(email)
    if sub is None:
        return JSONResponse({
            "ok": True, "subscribed": False,
            "lang": "en", "city": "", "rashi": "all",
        })
    return JSONResponse({
        "ok": True, "subscribed": True,
        "lang": sub.get("lang", "en"),
        "city": sub.get("city", ""),
        "rashi": sub.get("rashi", "all"),
    })


@router.post("/subscribe")
async def subscribe(request: Request,
                    email: str = Form(...),
                    lang: str = Form("en"),
                    city: str = Form(""),
                    rashi: str = Form("all")) -> JSONResponse:
    """Add an email to the daily-Rashifal subscriber list.

    Called from the modal in _subscribe_modal.html via fetch(). Returns JSON
    `{ok: true}` on success or `{ok: false, error: "..."}` so the frontend
    can show inline feedback without a full page reload.

    Side effect: sends a one-off welcome email to brand-new subscribers
    (skipped for re-subscribes). Welcome failure is logged but doesn't
    block the success response — the subscription itself already saved.
    """
    # `request` is declared on this handler so it can alert like its siblings
    # do — it previously went unused, which is why a storage failure here
    # returned 400 to the user and produced no signal at all (#183).
    try:
        ok, is_new, msg = subscribers.subscribe(email, lang, city, rashi)
    except Exception as err:  # noqa: BLE001
        # subscribe() is not documented to raise, so if it does, something
        # unmodelled broke and we want to hear about it rather than 500 silently.
        _fire_error_alert(request, err, "subscribe")
        return JSONResponse(
            {"ok": False, "error": subscribers.STORAGE_FAILURE_MSG}, status_code=400
        )
    if not ok:
        # A bad email is the user's to fix and must not page anyone; a storage
        # failure is ours and must. Compared against the named constant rather
        # than the wording, so rewording the message cannot silently switch
        # the alert off.
        if msg == subscribers.STORAGE_FAILURE_MSG:
            _fire_error_alert(
                request,
                RuntimeError(f"subscribers.subscribe could not persist: {msg}"),
                "subscribe",
            )
        return JSONResponse({"ok": False, "error": msg}, status_code=400)
    if is_new:
        try:
            _send_welcome_email(email, lang, city, rashi)
        except Exception as err:
            # Log and continue — the user is already subscribed; missing
            # welcome is a minor degradation, not a failure.
            import logging
            logging.getLogger(__name__).warning("welcome email failed for %s: %s", email, err)
        # Only notify on brand-new subscriptions, not re-subscribes.
        notify.subscribed(email=email, source=(city or "unknown"), lang=lang)
    return JSONResponse({"ok": True})


def _panchang_for_city(city: str | None, request_cache: dict | None = None):
    """Compute today's Panchang for a city. Returns None when no city given.

    Panchang (sunrise, Rahu Kaal, Abhijit Muhurta) is location-dependent —
    Delhi's times don't match Bangalore's. Rather than show wrong times,
    skip the Panchang section entirely when the subscriber hasn't told us
    where they are. Empty/blank/whitespace-only city all count as "no city".

    `request_cache` is keyed by city string and shared across the send loop
    so 200 Mumbai subscribers don't each trigger a Nominatim lookup.
    """
    resolved = (city or "").strip()
    if not resolved:
        return None
    if request_cache is not None and resolved in request_cache:
        return request_cache[resolved]
    try:
        # compute_chart's only job here is to geocode + give lat/lon/tz;
        # the date+time are throwaway. ~50-200ms incl. Nominatim lookup.
        chart_for_loc = compute_chart("2000-01-01", "12:00", resolved)
        p = compute_panchang(chart_for_loc)
    except Exception:
        # Couldn't geocode this city — degrade gracefully to no-Panchang
        # rather than guessing with a wrong location.
        p = None
    if request_cache is not None and p is not None:
        request_cache[resolved] = p
    return p


def _email_context(*, lang: str, city: str | None, request_cache: dict | None = None) -> dict:
    """Build the per-subscriber template context shared by daily + welcome emails.

    All the date/shlok/festival/trivia lookups are deterministic for a given
    date + lang, so they're computed once per (lang, date) and reused inside
    the same send call. Panchang is per-city.
    """
    today = date.today()
    panchang = _panchang_for_city(city, request_cache=request_cache)
    return {
        "lang": lang,
        "today_iso": today.isoformat(),
        "today_pretty": today.strftime("%A, %d %B %Y"),
        "panchang": panchang,
        "shlok": shloks.shlok_for_date(today),
        # ALL festivals, not the first. The email callout is a factual
        # "what day is it" block with room to repeat, so dropping the second
        # festival on a shared date (Makar Sankranti + Pongal, 2026-01-14) is
        # plain data loss to the subscriber. Both email templates loop over
        # this and render nothing when the list is empty.
        "festivals": festivals.festivals_for_date(today),
        "trivia": trivia.trivia_for_date(today),
        "site_url": _site_url(),
    }


def _filter_rashi_sections(sections: list, rashi: str) -> list:
    """If a subscriber chose a single rashi, return just that card. Otherwise
    return all 12. Matches by the English slug (first word of "Aries / Mesha")."""
    if not rashi or rashi == "all":
        return sections
    return [s for s in sections
            if s[1].split('/')[0].strip().lower() == rashi.lower()] or sections


def _send_welcome_email(email: str, lang: str, city: str = "", rashi: str = "all") -> bool:
    """Send the one-off welcome email to a newly-subscribed user.

    Embeds today's Rashifal + Panchang + shlok + trivia so the first email
    delivers immediate value, not just a "you're subscribed" confirmation.
    Reuses _shared_three_tier so the Rashifal piggybacks on the same daily
    generation the morning blast uses — zero extra LLM cost.
    """
    today_iso = date.today().isoformat()
    prompt_fp = cache.fingerprint_prompt(RASHIFAL_PROMPT_PATH)

    # Build today's Rashifal sections (may trigger generation if cold).
    try:
        neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
        transit = compute_transit_snapshot(neutral_chart)
        text = _daily_rashifal_text(
            lang=lang,
            today_iso=today_iso,
            cache_key=f"rashifal:{today_iso}:{lang}:{prompt_fp}",
            storage_key=f"rashifal/{today_iso}-{lang}-{prompt_fp}.txt",
            call_fn=lambda: generate_rashifal(
                transit=transit, today_iso=today_iso,
                prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                panchang=compute_panchang(neutral_chart),
                # Singular by design — the LLM prompt has one festival slot
                # (llm.py takes `dict | None`). The welcome email's own
                # festival CALLOUT does show all of them; this only shapes
                # the generated prose.
                festival=festivals.festival_for_date(date.today()),
            ),
        )
        sections = [
            (symbol_for_rashi_label(title) or "✦", title, _rashifal_teaser(body), body)
            for title, body in parse_sectioned_reading(text)
        ]
    except Exception:
        # If Rashifal generation fails entirely, send the rest of the
        # welcome anyway — better than blocking on a missed reading.
        sections = []

    ctx = _email_context(lang=lang, city=city)
    ctx["rashifal_sections"] = _filter_rashi_sections(sections, rashi)
    ctx["unsubscribe_url"] = (
        f"{ctx['site_url']}/unsubscribe?email={email}"
        f"&token={subscribers.unsubscribe_token(email)}"
    )

    html = templates.env.get_template("email/welcome.html").render(**ctx)
    subject = (
        "Shubh Bhagya में स्वागत है — कल से दैनिक राशिफल शुरू"
        if lang == "hi"
        else "Welcome to Shubh Bhagya — your daily Rashifal starts tomorrow"
    )
    return email_sender.send(email, subject=subject, html=html)


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(request: Request, email: str = "", token: str = "") -> HTMLResponse:
    """One-click unsubscribe landing page. Linked from every email's footer.

    Token is an HMAC of the email signed with our cookie secret, so we can't
    be tricked into removing arbitrary addresses by URL-tampering attackers.
    """
    if not email or not token or not subscribers.verify_unsubscribe_token(email, token):
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Invalid unsubscribe link",
             "message": "This link looks broken. Please reply to one of your Bhagya emails and we'll remove you manually."},
            status_code=400,
        )
    ok, _ = subscribers.unsubscribe(email)
    title = "You're unsubscribed" if ok else "Couldn't process right now"
    body = ("We've removed your email from Bhagya's daily Rashifal list. You can resubscribe anytime."
            if ok else "Please try again in a minute, or reply to one of our emails.")
    return templates.TemplateResponse(
        request, "error.html",
        {"title": title, "message": body},
        status_code=200 if ok else 503,
    )


@router.post("/admin/warm-rashifal", dependencies=[Depends(require_admin)])
async def warm_rashifal(request: Request, lang: str = "en") -> JSONResponse:
    """Generate and cache today's Rashifal for ONE language, ahead of the blast.

    Exists because /admin/send-daily-rashifal generates BOTH languages inline —
    24 LLM calls in a single HTTP request — and that stopped fitting in Cloud
    Run's request timeout. The daily email failed every day from 2026-08-01 to
    2026-08-21: twenty 504s at exactly 60.000s, then a 503 at 201.6s once the
    timeout was raised to 300s. A measured run of the full job took 399s.

    Splitting the work by language is what makes it fit: two warm requests of
    12 calls each, then a blast that only reads cache. Each piece is well under
    the timeout on its own, and none of it needs an always-on instance or a
    background worker — both of which cost money this project does not spend.

    Deliberately writes through the SAME cache keys the blast reads, so the
    blast needs no knowledge of this endpoint. If warming fails or never runs,
    the blast still generates inline exactly as before — this is an
    optimisation, not a dependency.
    """
    if lang not in ("en", "hi"):
        return JSONResponse({"ok": False, "error": f"unsupported lang: {lang}"}, status_code=400)

    today_iso = date.today().isoformat()
    prompt_fp = cache.fingerprint_prompt(RASHIFAL_PROMPT_PATH)
    started = _time.time()
    try:
        neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
    except ChartError as err:
        return JSONResponse({"ok": False, "error": f"Couldn't compute reference chart: {err}"}, status_code=500)
    transit = compute_transit_snapshot(neutral_chart)

    try:
        text = _daily_rashifal_text(
            lang=lang,
            today_iso=today_iso,
            cache_key=f"rashifal:{today_iso}:{lang}:{prompt_fp}",
            storage_key=f"rashifal/{today_iso}-{lang}-{prompt_fp}.txt",
            call_fn=lambda: generate_rashifal(
                transit=transit, today_iso=today_iso,
                prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                panchang=compute_panchang(neutral_chart),
                festival=festivals.festival_for_date(date.today()),
            ),
        )
    except AllProvidersExhausted as err:
        _fire_error_alert(request, err, f"rashifal:warm:{lang}")
        return JSONResponse({"ok": False, "lang": lang, "error": str(err)}, status_code=503)

    sections = parse_sectioned_reading(text)
    elapsed = round(_time.time() - started, 1)
    log.info("warm-rashifal lang=%s sections=%d elapsed=%.1fs", lang, len(sections), elapsed)
    # sections is the number the blast needs; anything under 12 means the blast
    # will email a partial list, so surface it rather than reporting a bare ok.
    return JSONResponse({
        "ok": len(sections) == 12,
        "lang": lang,
        "sections": len(sections),
        "chars": len(text),
        "elapsed_s": elapsed,
    })


@router.post("/admin/send-daily-rashifal", dependencies=[Depends(require_admin)])
async def send_daily_rashifal(request: Request) -> JSONResponse:
    """Send today's Rashifal email to every active subscriber.

    Triggered by Cloud Scheduler at 7 AM IST daily. Auth-gated by basic auth
    so a leaked URL can't drain Brevo quota. Reads (or generates if needed)
    today's Rashifal per language, then per-subscriber sends via Brevo.
    """
    today_iso = date.today().isoformat()
    today_pretty = date.today().strftime("%A, %d %B %Y")
    prompt_fp = cache.fingerprint_prompt(RASHIFAL_PROMPT_PATH)
    site_url = _site_url()

    # Build the Rashifal section list for each language we actually need.
    # We trigger generation via _shared_three_tier so cold-start days still
    # produce content rather than emailing empty bodies.
    try:
        neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
    except ChartError as err:
        return JSONResponse({"ok": False, "error": f"Couldn't compute reference chart: {err}"}, status_code=500)
    transit = compute_transit_snapshot(neutral_chart)

    sections_by_lang: dict[str, list] = {}
    for lang in ("en", "hi"):
        cache_key = f"rashifal:{today_iso}:{lang}:{prompt_fp}"
        storage_key = f"rashifal/{today_iso}-{lang}-{prompt_fp}.txt"
        try:
            text = _daily_rashifal_text(
                lang=lang,
                today_iso=today_iso,
                cache_key=cache_key,
                storage_key=storage_key,
                call_fn=lambda lang=lang: generate_rashifal(
                    transit=transit, today_iso=today_iso,
                    prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                    panchang=compute_panchang(neutral_chart),
                    # Singular by design — one festival slot in the prompt
                    # (llm.py takes `dict | None`), and this is the daily
                    # blast: a type error here fails the whole 7 AM send.
                    # The email's festival callout renders all of them.
                    festival=festivals.festival_for_date(date.today()),
                ),
            )
            sections_by_lang[lang] = [
                (symbol_for_rashi_label(title) or "✦", title, _rashifal_teaser(body), body)
                for title, body in parse_sectioned_reading(text)
            ]
        except Exception as err:
            log.exception("rashifal (per-rashi API) LLM generation failed")
            _fire_error_alert(request, err, "rashifal_api")
            _title, _msg = _llm_error_friendly(err)
            return JSONResponse(
                {"ok": False, "error": _msg},
                status_code=503 if isinstance(err, AllProvidersExhausted) else 502,
            )

    # Render + send per subscriber. Panchang is per-city, cached across
    # the send so subscribers sharing a city only trigger one geocode.
    template = templates.env.get_template("email/daily_rashifal.html")
    panchang_cache: dict = {}
    sent = failed = 0
    failures: list[str] = []
    for sub in subscribers.list_subscribers():
        lang = sub.get("lang", "en")
        if lang not in sections_by_lang:
            lang = "en"

        ctx = _email_context(lang=lang, city=sub.get("city", ""),
                             request_cache=panchang_cache)
        ctx["rashifal_sections"] = _filter_rashi_sections(
            sections_by_lang[lang], sub.get("rashi", "all")
        )
        ctx["unsubscribe_url"] = (
            f"{site_url}/unsubscribe?email={sub['email']}"
            f"&token={subscribers.unsubscribe_token(sub['email'])}"
        )
        html = template.render(**ctx)
        subject = "आज का राशिफल — Shubh Bhagya" if lang == "hi" else "Today's Rashifal — Shubh Bhagya"
        ok = email_sender.send(sub["email"], subject=subject, html=html)
        if ok:
            sent += 1
        else:
            failed += 1
            failures.append(sub["email"])

    # `ok` must mean "subscribers got their email", not "the handler reached
    # its last line". It used to be the literal True, so a blast that failed
    # to deliver to EVERY subscriber still reported success — and this is the
    # endpoint that silently failed for 21 consecutive days (2026-08-01 to
    # 08-21) without anyone noticing. Cloud Run 504s never reach this code at
    # all, so an external monitor is still needed for that case; this covers
    # everything that DOES get here.
    total = len(subscribers.list_subscribers())
    delivered_none = total > 0 and sent == 0
    ok = not delivered_none and failed == 0

    if delivered_none:
        _fire_error_alert(
            request,
            RuntimeError(f"daily rashifal reached 0 of {total} subscribers"),
            "rashifal:blast:zero_delivered",
        )
    elif failed:
        _fire_error_alert(
            request,
            RuntimeError(f"daily rashifal failed for {failed} of {total}: {failures[:5]}"),
            "rashifal:blast:partial",
        )
    # A short language is worth knowing about even when every send succeeded:
    # subscribers on that language quietly receive fewer than 12 rashis.
    short = {lang: len(secs) for lang, secs in sections_by_lang.items() if len(secs) != 12}
    if short:
        _fire_error_alert(
            request,
            RuntimeError(f"daily rashifal sections incomplete: {short} (expected 12 each)"),
            "rashifal:blast:short_sections",
        )

    log.info("daily rashifal: sent=%d failed=%d of %d subscribers, sections=%s",
             sent, failed, total, {k: len(v) for k, v in sections_by_lang.items()})
    return JSONResponse({
        "ok": ok,
        "date": today_iso,
        "total_subscribers": total,
        "sent": sent,
        "failed": failed,
        "sections": {lang: len(secs) for lang, secs in sections_by_lang.items()},
        "failed_emails": failures[:20],  # cap so we don't return MB-sized lists
    }, status_code=200 if ok else 500)
