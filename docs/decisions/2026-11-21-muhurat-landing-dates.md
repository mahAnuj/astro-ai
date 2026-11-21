# Muhurat landing pages list the five earliest auspicious dates for New Delhi, in date order, computed per IST day

- **Date:** 2026-11-21
- **PR / issue:** #1325 (slice 6 of #1017)

## Why, measured

`GET /muhurat/griha-pravesh` returned a form and no dates, while the page's visible queries
are date-shaped ("griha pravesh muhurat today", "tomorrow", "date"). The landing now renders
the next auspicious dates, computed by `muhurat.find_candidates` at render time and never
typed in. No rule changed: no line of `find_candidates` moved.

**Order: chronological, not the finder's tier order.** The issue's AC1 says "in the same order"
as `find_candidates`. That function returns best-tier-first, so read literally the page would
list the five best-RATED dates of the window, possibly 80 days out, under a heading that says
"Next". The page lists the five EARLIEST auspicious dates and prints them in date order, which
is the finder's own tie-break inside a tier. Measured premise (2026-11-21, griha_pravesh):
the finder-order first five differ from the earliest five, and
`tests/test_muhurat_landing_dates.py` asserts that so the decision cannot silently stop
mattering. Reversible by one line if the literal reading is wanted.

**One definition of "auspicious".** #1322 defined it only as a Jinja literal in the finder
template. `muhurat.AUSPICIOUS_RATINGS` now names it (excellent, good, acceptable; caution is
not), read by the landing in Python and by the finder template through the lazy global
`muhurat_auspicious_ratings`, following `muhurta_instant_hour`. The finder's POST output is
byte-identical before and after (diffed, 200,169 bytes).

**Scope.** An allow-list of four events whose rules #1058 sourced: griha_pravesh, vidyarambh,
namkaran, business. Not "everything except vivah", so a new event type is opt-in; vivah is
left unchanged until #1026. A window with no auspicious date shows no section.

**90-day window.** At 60 days `business` had exactly five auspicious dates with no slack. At
90 (2026-11-21): griha_pravesh 16, vidyarambh 21, namkaran 19, business 11; 0.14-0.15 s warm.

**Cache and threads.** `hot_cache.get_or_compute`, key `muhurat:landing:<event>:<IST date>`,
TTL 86400 s, run with `run_in_threadpool`. IST rollover is in the key (`reading_today()`,
never `date.today()`, #794). `get_or_refresh` was rejected: a cold key returns no list, so a
crawler or the first visitor would see the page this exists to improve. Calling
`find_candidates` on the event loop was rejected (ephemeris plus a 10 s Nominatim timeout,
the #144 shape). A startup warm-up was rejected: it adds Nominatim and four computes to every
cold start for pages most instances never serve. Per instance, so at most 20 computes a day
across five instances; no GCS, no LLM.

**Response headers.** The page now names today and tomorrow, so the landing is wrapped in
`_no_cdn_cache` like `/rashifal` and `/panchang`. This applies to every landing, vivah
included, whose pre-filled start date was already date-dependent.

**Failure.** Any exception (Nominatim down, compute error) omits the section, keeps HTTP 200
and logs a warning. Deliberately no `_fire_error_alert`: a public crawled page would page the
owner on every Nominatim hiccup; `hot_cache` already collapses repeats to one per 5 s.

**Not done, and still true.** `POST /muhurat` runs `find_candidates` synchronously inside an
`async def` and blocks the event loop; it is a follow-up, not copied here.
