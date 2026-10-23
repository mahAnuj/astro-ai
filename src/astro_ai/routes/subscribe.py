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
from astro_ai.rashifal_derive import combined_keys, sections_by_rashi
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
    (e.g. Rashifal — today only).

    This used to say per-chart routes gain nothing from GCS "because the
    SQLite key is unique per user anyway", and that sentence is why the natal
    reading was regenerated at ~7,800 input tokens a time on every cold start
    until 2026-08-30. How long that lasted is not recorded anywhere in this
    tree and is not stated here — an earlier draft of this paragraph guessed
    at it, which is the same fabricate-then-cite defect the sentence it
    replaces is an example of.
    GCS's value to a per-chart route is not sharing between users — it is
    SURVIVING THE CONTAINER. SQLite lives on `/tmp` tmpfs with min-instances 0,
    so a per-user key that never expires is still lost on every cold start and
    every deploy. `_cached(..., durable_key=...)` is the per-chart form.

    The two are deliberately NOT merged. This one reads GCS FIRST, which is
    right for content one warm job wrote for everybody: the local copy is the
    outlier and the bucket is the source of truth. Natal must read SQLITE
    FIRST, because its key is immutable and content-addressed, so a
    cross-continent round-trip on a warm instance is pure loss. Collapsing
    them into one function would force one of those two orders to be wrong.

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
    # INPUT IS NOT KNOWABLE HERE, so it is not guessed (#473).
    #
    # This read `cache.estimate_tokens(text) * 2  # input ~= 2x output` until
    # 2026-10-21 -- `text` is the model's OUTPUT, so input was DEFINED as twice
    # an estimate of it. Every route on /admin/ops therefore reported a flawless
    # 2:1 ratio that no traffic could disturb, and rashifal read 7,692 input
    # tokens against a job that measures ~38,500.
    #
    # Two things were wrong and only one was the arithmetic. This function sees
    # a cached DOCUMENT; `generate_rashifal` fans one out to twelve provider
    # calls, so even a perfect number here would be the wrong unit. The real
    # pair is recorded where it is known -- `providers.chat` ->
    # `llm_stats.record` -- keyed by provider route.
    #
    # Zero means UNKNOWN. ops_data renders it as a dash, never as a measured
    # zero, and never divides by it.
    in_tok = 0
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
    started = _time.time()
    try:
        neutral_chart = compute_chart("2000-01-01", "12:00", "Mumbai, India")
    except ChartError as err:
        return JSONResponse({"ok": False, "error": f"Couldn't compute reference chart: {err}"}, status_code=500)
    transit = compute_transit_snapshot(neutral_chart)
    # A batch job: nobody is waiting, so the bucket may make a call wait up to the
    # job budget -- but never past this deadline (#475). One language fits today;
    # the deadline is the guarantee, not the arithmetic.
    pace_deadline = llm_providers.pace_deadline()

    cache_key, storage_key = combined_keys(lang, today_iso)
    try:
        text = _daily_rashifal_text(
            lang=lang,
            today_iso=today_iso,
            cache_key=cache_key,
            storage_key=storage_key,
            call_fn=lambda: generate_rashifal(
                transit=transit, today_iso=today_iso,
                prompt_path=RASHIFAL_PROMPT_PATH, lang=lang,
                panchang=compute_panchang(neutral_chart),
                festival=festivals.festival_for_date(date.today()),
                pace_deadline=pace_deadline,
            ),
        )
    except AllProvidersExhausted as err:
        _fire_error_alert(request, err, f"rashifal:warm:{lang}")
        return JSONResponse({"ok": False, "lang": lang, "error": str(err)}, status_code=503)

    sections = parse_sectioned_reading(text)
    elapsed = round(_time.time() - started, 1)
    # single_pages is the number /rashifal/{rashi} needs (#268): how many of the
    # 12 pages can be cut from this text and pass the single route's own gate.
    # Counted on a cache hit too — the text is what matters, not who wrote it.
    by_rashi = sections_by_rashi(text)
    single_pages = sum(
        1 for i in range(12)
        if i in by_rashi and llm_providers.passes_quality(by_rashi[i], "rashifal_single")[0]
    )
    log.info("warm-rashifal lang=%s sections=%d single_pages=%d elapsed=%.1fs",
             lang, len(sections), single_pages, elapsed)
    if single_pages < 12:
        # Status stays 200: Cloud Scheduler judges the status and a retry would
        # not change what the model wrote. The alert is the signal, and this is
        # the detector #268 asked for — a heading format we do not recognise.
        _fire_error_alert(
            request,
            RuntimeError(f"warm {lang}: only {single_pages}/12 single pages derivable"),
            f"rashifal:warm:{lang}",
        )
    # sections is the number the blast needs; anything under 12 means the blast
    # will email a partial list, so surface it rather than reporting a bare ok.
    return JSONResponse({
        "ok": len(sections) == 12 and single_pages == 12,
        "lang": lang,
        "sections": len(sections),
        "single_pages": single_pages,
        "chars": len(text),
        "elapsed_s": elapsed,
    })


def _mask_email(email: object) -> str:
    """``kartik@gmail.com`` → ``ka***@gmail.com``. Never returns a full address.

    Blast alerts get this, not the raw address (#222). ``_fire_error_alert``
    puts its message into the Telegram channel AND into ``events.record``'s
    ``error_message``, which ``/admin/activity`` renders and GCS retains for 30
    days — so a raw address there is a subscriber list in a chat channel and a
    month-long store. The alert's job is "how many failed"; enough of the
    address to recognise a repeat offender is all it needs. Identifying data
    stays in the app log, which is the right place for it.

    Total for anything the subscribers blob can hold: it cannot raise on a
    value that arrives through ``json.loads``. (Not total for *every* object —
    a ``str`` subclass overriding ``partition`` would raise — but the blob is
    parsed JSON, which cannot produce one.) It takes ``object``,
    not ``str``, because its argument comes from the subscribers blob via
    ``sub.get("email", "")`` — whatever is actually stored, not what the
    signature wishes were stored. A truthy non-string (``12345``, a list) used
    to reach ``.partition`` and raise AttributeError from the partial alert,
    which sits below the send loop and outside its handler: no alert fired and
    no outcome JSON returned. That is #220's harm exactly, so a masking helper
    on an error path must not be able to cause it. Non-strings mask to ``***``
    rather than ``str(email)`` — an unknown shape is not an address we can
    safely quote into a 30-day store.
    """
    if not isinstance(email, str):
        return "***"
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{local[:2]}***@{domain}"


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
    # ONE deadline for the whole job, computed before the first language: en and
    # hi share it (24 calls in this one 300 s request). Per language it would
    # grant each 12-call half its own allowance and the sum would pass the
    # timeout (#475, QA round 2: 319-395 s simulated).
    pace_deadline = llm_providers.pace_deadline()
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
                    # Batch job (the 7 AM blast): see /admin/warm-rashifal.
                    pace_deadline=pace_deadline,
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
    # Capture the list ONCE. Calling list_subscribers() again for the count
    # made `total` a different population from the one we sent to: a signup
    # landing mid-run gave sent=0 with total=1, which read as "delivered to
    # nobody" and returned 500 plus a false zero_delivered alert into the
    # rashifal_cron_failures metric. The tell was sent=0 WITH failed=0, which
    # is impossible for a genuine total failure. Capturing once also removes a
    # second storage round-trip on this path and makes `total` in the JSON
    # mean what any monitor reading it assumes: sent + failed == total.
    subs = subscribers.list_subscribers()
    # `list_subscribers()` is `data.get("subscribers", [])` off a JSON blob, so
    # a corrupted one (`{"subscribers": null}`) hands back a non-list — and both
    # `for sub in subs` and `len(subs)` raise on that, outside every handler
    # here: HTML 500, no outcome JSON, no alert (#223). Reported below as
    # ok:false with its own alert rather than as an empty list, because
    # sent=0/failed=0/total=0 with ok:true is what a genuine quiet day looks
    # like, and an unreadable list must not be indistinguishable from one.
    unreadable_list = not isinstance(subs, list)
    if unreadable_list:
        log.error("daily rashifal: subscriber list is %s, not a list", type(subs).__name__)
        subs = []
    for sub in subs:
        send_err: Exception | None = None
        email = ""
        try:
            # Read `email` with .get() like every other field on these rows. It
            # was subscripted directly at four sites, so a row missing it raised
            # KeyError — and there was no handler nearer than the app-level one,
            # so that single bad row took the whole blast down (#220). The read
            # is INSIDE the guard because #220's fix protected a malformed FIELD
            # and not a malformed ROW: a row that is not a dict (a bare string
            # in the blob) raises AttributeError on `.get` itself, one frame
            # further out, with all of #220's harm (#223). Only reachable via a
            # corrupted or hand-edited blob — the signup writer always writes a
            # normalised dict — so it is counted as a failure like any other bad
            # row rather than given a shape of its own.
            email = sub.get("email", "")
            if not email:
                raise ValueError("subscriber row has no email")
            lang = sub.get("lang", "en")
            if lang not in sections_by_lang:
                lang = "en"

            ctx = _email_context(lang=lang, city=sub.get("city", ""),
                                 request_cache=panchang_cache)
            ctx["rashifal_sections"] = _filter_rashi_sections(
                sections_by_lang[lang], sub.get("rashi", "all")
            )
            ctx["unsubscribe_url"] = (
                f"{site_url}/unsubscribe?email={email}"
                f"&token={subscribers.unsubscribe_token(email)}"
            )
            html = template.render(**ctx)
            subject = "आज का राशिफल — Shubh Bhagya" if lang == "hi" else "Today's Rashifal — Shubh Bhagya"
            ok = email_sender.send(email, subject=subject, html=html)
        except Exception as exc:  # noqa: BLE001 — one bad row must not end the blast
            # A raise here escaped past BOTH alerts below and past the outcome
            # JSON, so the blast aborted mid-run and reported nothing at all —
            # unretryably, because Cloud Scheduler runs this job with
            # --max-retry-attempts=0 (retries were double-generating and
            # doubling spend). NOT email_sender.send, which already wraps its
            # HTTP call and returns False; the raise sources are the context,
            # token and render code around it. Counted exactly like a falsey
            # send so the partial alert below covers it.
            send_err = exc
            ok = False
        if ok:
            sent += 1
        else:
            failed += 1
            failures.append(email or "<no email>")
            # The app log is now the ONLY place the full address appears — the
            # partial alert below carries a count and a masked prefix (#222) —
            # so log every failure, not just the raising ones. `exc_info` is
            # the traceback on the raising path and None on a falsey send.
            log.warning("daily rashifal: not delivered to %s",
                        email or "<no email>", exc_info=send_err)

    # `ok` must mean "subscribers got their email", not "the handler reached
    # its last line". It used to be the literal True, so a blast that failed
    # to deliver to EVERY subscriber still reported success — and this is the
    # endpoint that silently failed for 21 consecutive days (2026-08-01 to
    # 08-21) without anyone noticing. Cloud Run 504s never reach this code at
    # all, so an external monitor is still needed for that case; this covers
    # everything that DOES get here.
    total = len(subs)
    delivered_none = total > 0 and sent == 0
    ok = not unreadable_list and not delivered_none and failed == 0

    # Every alert below sits outside the per-subscriber handler, so anything
    # that raises while BUILDING or firing one kills the response the loop
    # just worked to protect: no alert, no outcome JSON, an HTML 500. That is
    # #220's own harm relocated one block down, and it was reached — a truthy
    # non-string `email` in the subscribers blob raised inside `_mask_email`.
    # `_mask_email` is total now; these guards are the part that generalises,
    # because the lesson of #220 is that the blast must not die silently and
    # an alert that raises does precisely that. Guarded separately so one
    # failing alert does not suppress the other.
    try:
        if unreadable_list:
            _fire_error_alert(
                request,
                RuntimeError("daily rashifal: subscriber list unreadable"
                             " (not a list) — nobody was attempted"),
                "rashifal:blast:unreadable_list",
            )
        elif delivered_none:
            _fire_error_alert(
                request,
                RuntimeError(f"daily rashifal reached 0 of {total} subscribers"),
                "rashifal:blast:zero_delivered",
            )
        elif failed:
            # Count plus ONE masked prefix — this message reaches the Telegram
            # channel and events.record's error_message, which /admin/activity
            # renders and GCS keeps for 30 days. It used to interpolate
            # `failures[:5]` raw, which put up to five subscriber addresses into
            # both (#222). Full addresses stay in the app log, logged per failure
            # in the loop above.
            _fire_error_alert(
                request,
                RuntimeError(f"daily rashifal failed for {failed} of {total}"
                             f" (first: {_mask_email(failures[0])})"),
                "rashifal:blast:partial",
            )
    except Exception:  # noqa: BLE001 — alerting must never cost the outcome JSON
        log.exception("daily rashifal: delivery alert failed; outcome still reported")

    # A short language is worth knowing about even when every send succeeded:
    # subscribers on that language quietly receive fewer than 12 rashis.
    short = {lang: len(secs) for lang, secs in sections_by_lang.items() if len(secs) != 12}
    if short:
        try:
            _fire_error_alert(
                request,
                RuntimeError(f"daily rashifal sections incomplete: {short} (expected 12 each)"),
                "rashifal:blast:short_sections",
            )
        except Exception:  # noqa: BLE001 — same: the outcome JSON outranks the alert
            log.exception("daily rashifal: short-sections alert failed; outcome still reported")

    log.info("daily rashifal: sent=%d failed=%d of %d subscribers, sections=%s",
             sent, failed, total, {k: len(v) for k, v in sections_by_lang.items()})
    return JSONResponse({
        "ok": ok,
        "date": today_iso,
        "total_subscribers": total,
        "sent": sent,
        "failed": failed,
        "sections": {lang: len(secs) for lang, secs in sections_by_lang.items()},
        # Capped so we don't return MB-sized lists, and coerced because
        # `failures` holds whatever the blob held: `bytes` is not JSON
        # serializable, so the encoder raised HERE — below the loop, outside
        # its handler, so no outcome JSON and an HTML 500, which is #220's harm
        # again (#225). Coerced at this site and not at `failures.append` on
        # purpose: `_mask_email` must keep receiving the raw value, or its
        # non-string branch becomes unreachable from this route and the
        # mutation row guarding it stops failing.
        "failed_emails": [str(e) for e in failures[:20]],
    }, status_code=200 if ok else 500)
