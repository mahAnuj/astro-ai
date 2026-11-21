"""#1325: the muhurat landing pages list the next five auspicious dates for New Delhi,
computed by the finder, cached per IST day, and say where they came from.

Rows target routes/muhurat.py and templates/muhurat_landing.html, which
tests/test_muhurat_landing_dates.py exercises through the real route. One area file, a
literal list (test_mutation_tables.py requires it)."""

_R = "src/astro_ai/routes/muhurat.py"
_T = "src/astro_ai/templates/muhurat_landing.html"
_FILTER = "    upcoming = sorted((c for c in rows if c.rating in AUSPICIOUS_RATINGS), key=lambda c: c.d)"

MUTATIONS = [
    ("#1325: the list admits caution dates (filter widened to everything but avoid)",
     _R, _FILTER,
     "    upcoming = sorted((c for c in rows if c.rating != \"avoid\"), key=lambda c: c.d)",
     "test_landing_and_finder_share_one_auspicious_definition"),
    ("#1325: the cache key drops the IST day (yesterday's list served for ever)",
     _R, 'f"muhurat:landing:{event_key}:{today.isoformat()}", LANDING_TTL_S,',
     'f"muhurat:landing:{event_key}", LANDING_TTL_S,',
     "test_one_find_candidates_call_per_event_per_ist_day"),
    ("#1325: the landing reads the UTC day instead of the IST day (#794)",
     _R, "    today = reading_today()  # read once: the cache key and the window must name the same IST day",
     "    today = date.today()  # read once: the cache key and the window must name the same IST day",
     "test_one_find_candidates_call_per_event_per_ist_day"),
    ("#1325: tier order shown instead of the five earliest dates in date order",
     _R, _FILTER,
     "    upcoming = [c for c in rows if c.rating in AUSPICIOUS_RATINGS]",
     "test_landing_lists_exactly_the_five_earliest_auspicious_dates_per_event"),
    ("#1325: find_candidates runs on the event loop (the #144 failure shape)",
     _R, "            upcoming = await run_in_threadpool(\n                hot_cache.get_or_compute,\n",
     "            upcoming = (lambda f, *a: f(*a))(\n                hot_cache.get_or_compute,\n",
     "test_find_candidates_runs_through_the_threadpool_not_on_the_loop"),
    ("#1325: a failed computation 500s the page instead of omitting the section",
     _R, "        except Exception:\n            # A panel must never 500 the page.",
     "        except ZeroDivisionError:\n            # A panel must never 500 the page.",
     "test_failures_leave_the_page_rendering"),
    ("#1325: the landing keeps its own copy of the auspicious set (the drift #1322 fixed)",
     _R, "    from astro_ai.muhurat import AUSPICIOUS_RATINGS\n",
     "    AUSPICIOUS_RATINGS = (\"excellent\", \"good\", \"acceptable\")\n",
     "test_landing_and_finder_share_one_auspicious_definition"),
    ("#1325: the landing is served without the no-CDN-cache headers",
     _R, "    return _no_cdn_cache(templates.TemplateResponse(",
     "    return (lambda r: r)(templates.TemplateResponse(",
     "test_landing_response_is_not_cdn_cacheable"),
    ("#1325: an excluded day no longer shows the finder's stored reason",
     _T, "{% if not day.valid %}<span class=\"text-bhagya-muted\">The finder's note: {{ day.reason }}</span>{% endif %}",
     "{% if not day.valid %}{% endif %}",
     "test_today_tomorrow_line_agrees_with_find_candidates_for_both_dates"),
]
