"""Festival calendar hub (issue #154).

Owns:
    GET /festivals   the next six months of named festivals plus computed
                     lunar observances, rendered inline on one page

Moved verbatim from ``main.py``; only the decorator prefix changed
(``@app.`` → ``@router.``).

NOTE on imports: this module is ``astro_ai.routes.festivals`` and shadows the
real ``astro_ai.festivals``. Every import here — including the function-local
``from astro_ai import festival_registry`` and
``from astro_ai.lunar_observances import ...`` — must therefore stay ABSOLUTE.
A relative import would resolve to this module and fail as a confusing
AttributeError rather than an ImportError. Nothing here may import
``astro_ai.main``.
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from astro_ai.routes.deps import (
    _HINDI_MONTHS,
    _lang,
    _no_cdn_cache,
    _pretty_date,
    _pretty_weekday,
    templates,
)

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/festivals", response_class=HTMLResponse)
async def festivals_page(request: Request) -> HTMLResponse:
    """Hindu festival calendar — the next six months, all on one page.

    Everything renders inline (date, tithi rule, significance, observance)
    rather than linking out to per-festival stubs: /learn already owns the
    long-form festival articles, and a parallel page type would cannibalise
    them. Only festivals that already have such an article get a link.

    The "in N days" copy is date-derived, so this page must not sit in a CDN
    cache overnight — same reason /panchang uses _no_cdn_cache.
    """
    from astro_ai import festival_registry as _fest_reg

    lang = _lang(request)
    today = date.today()
    today_iso = today.isoformat()
    # One window for the whole page: the cards, the grid and the lunar
    # observances below are all cut to [today, _window_end], which ends on the
    # last day of the sixth month ahead. Read it once here rather than letting
    # each consumer recompute it.
    _window_end = _fest_reg.window_end(today)
    entries = _fest_reg.upcoming(today)

    festivals_ctx: list[dict] = []
    for fest_date, fest in entries:
        # One malformed registry row should cost us that row, not the page —
        # but it gets logged, never silently dropped.
        try:
            article = _fest_reg.learn_article_for(fest)
            days_away = (fest_date - today).days
            festivals_ctx.append({
                "slug": fest.slug,
                "name_en": fest.name_en,
                "name_hi": fest.name_hi,
                # "major" (the named festivals) vs "recurring" (Purnima /
                # Amavasya / Ekadashi). getattr-with-default because the field
                # is landing in the registry separately — this must render
                # correctly both before and after it arrives.
                "tier": getattr(fest, "tier", "major"),
                "date_iso": fest_date.isoformat(),
                "pretty_date": _pretty_date(fest_date.isoformat(), lang),
                "weekday": _pretty_weekday(fest_date, lang),
                "days_away": days_away,
                "is_today": days_away == 0,
                # The registry carries note_hi for every festival and the daily
                # email has been using it for months; the hub was passing only
                # note_en, so ?lang=hi silently dropped Hindi copy that already
                # existed (QA BUG-2). Resolved here rather than in the template
                # so the template has one `note` to render, not a lang branch.
                #
                # significance and observance have NO Hindi in the registry at
                # all, so they stay English on purpose. The page says so under
                # the festival heading rather than mixing the two silently.
                "note": fest.note_hi if lang == "hi" else fest.note_en,
                "significance": fest.significance,
                "observance": fest.observance,
                "rule": fest.rule,
                "observance_window": fest.observance_window,
                "learn_url": f"/learn/{article.slug}/" if article else None,
                "learn_title": article.title if article else None,
            })
        except Exception as err:
            log.warning("festivals: skipping registry entry %r: %s", getattr(fest, "slug", "?"), err)

    # Month-grid calendar shown above the cards. Fed the rows that actually
    # made it into `festivals_ctx`, not the raw registry rows, so a skipped
    # entry above can never leave a marked day with no card to link to.
    _rendered = {f["slug"] for f in festivals_ctx}
    calendar_months = _fest_reg.month_grid(
        today, [(d, fest) for d, fest in entries if fest.slug in _rendered]
    )
    _tier_by_slug = {f["slug"]: f["tier"] for f in festivals_ctx}
    for _block in calendar_months:
        _block["label"] = (
            f"{_HINDI_MONTHS[_block['month']]} {_block['year']}"
            if lang == "hi" else _block["label_en"]
        )
        # month_grid deliberately returns only slug/name for each marked day.
        # Carry the tier across so the grid can render the ~20 named festivals
        # more strongly than the ~80 recurring lunar days that will join them.
        for _week in _block["weeks"]:
            for _cell in _week:
                if not _cell:
                    continue
                for _fx in _cell["festivals"]:
                    _fx["tier"] = _tier_by_slug.get(_fx["slug"], "major")

    # The header sentence counts the *named* festivals. The count is read here,
    # before the computed lunar days are merged in below, so adding ~28
    # Purnimas and Ekadashis cannot inflate "the N festivals in our verified
    # calendar" — those are computed, not hand-verified.
    #
    # The dates it spans are the WINDOW's, not the first and last festival's.
    # The window is what the calendar above draws and what every mark on it was
    # selected by; quoting the festival dates instead made the header claim a
    # narrower span than the page rendered (it stopped at 15 January while
    # February was on screen). It states a search range, not coverage — some
    # months inside it carry no named festival, and the grid says so.
    festival_count = len(festivals_ctx)
    first_iso = today_iso
    last_iso = _window_end.isoformat()

    # Computed monthly lunar days (Purnima / Amavasya / Ekadashi) merged into
    # the same two structures the named festivals use: one row in the card list
    # and one entry on the matching grid cell. Both appends happen together so
    # a failure part-way can never leave a marked day whose #slug anchor has no
    # target. The whole thing is guarded — an ephemeris failure must degrade
    # this page to festivals-only, never to a 500.
    #
    # Window is `_window_end`, the same one `upcoming()` and `month_grid()`
    # use, so the final month is marked to its end rather than trailing off
    # mid-month a few days into a block the grid has already drawn whole.
    try:
        from astro_ai.lunar_observances import observances_between as _obs_between

        _cells_by_iso = {
            _cell["date_iso"]: _cell
            for _block in calendar_months
            for _week in _block["weeks"]
            for _cell in _week
            if _cell and not _cell["is_past"]
        }
        for _obs_date, _obs in _obs_between(today, _window_end):
            _cell = _cells_by_iso.get(_obs_date.isoformat())
            if _cell is None:
                continue
            # slug is f"{kind}-{iso}" — the kind drives which glyph the grid
            # draws (hollow moon / filled moon / fast mark).
            _kind = _obs.slug.split("-", 1)[0]
            _days_away = (_obs_date - today).days
            _row = {
                "slug": _obs.slug,
                "name_en": _obs.name_en,
                "name_hi": _obs.name_hi,
                "tier": _obs.tier,
                "kind": _kind,
                "date_iso": _obs_date.isoformat(),
                "pretty_date": _pretty_date(_obs_date.isoformat(), lang),
                "weekday": _pretty_weekday(_obs_date, lang),
                "days_away": _days_away,
                "is_today": _days_away == 0,
                "rule": _obs.rule,
            }
            # Appended, not prepended: on a day that is both a named festival
            # and a lunar observance the festival must stay first, because the
            # cell's href points at festivals[0] and that link has to reach the
            # festival card.
            _cell["festivals"].append({
                "slug": _obs.slug,
                "name_en": _obs.name_en,
                "name_hi": _obs.name_hi,
                "tier": _obs.tier,
                "kind": _kind,
            })
            festivals_ctx.append(_row)
        festivals_ctx.sort(key=lambda f: f["date_iso"])
    except Exception as err:  # pragma: no cover - degrade to festivals-only
        log.warning("festivals: lunar observances unavailable: %s", err)

    # Source link for the reckoning block — current year where we have it,
    # otherwise any year we do, so a rollover past DATA_YEARS degrades to a
    # stale-but-valid citation instead of a broken link.
    source_url = _fest_reg.SOURCE_URL_BY_YEAR.get(today.year) or next(
        iter(_fest_reg.SOURCE_URL_BY_YEAR.values()), ""
    )

    return _no_cdn_cache(templates.TemplateResponse(
        request, "festivals_index.html",
        {
            "festivals": festivals_ctx,
            "festival_count": festival_count,
            "calendar_months": calendar_months,
            "window_start_pretty": _pretty_date(first_iso, lang),
            "window_end_pretty": _pretty_date(last_iso, lang),
            "today_iso": today_iso,
            "source_name": _fest_reg.SOURCE_NAME,
            "source_url": source_url,
            "data_years": list(_fest_reg.DATA_YEARS),
            "verified_through": max(_fest_reg.DATA_YEARS),
            "lang": lang,
        },
    ))


