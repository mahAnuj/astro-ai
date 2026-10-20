"""Shared helpers, template globals and dependencies for the route modules.

Extracted verbatim from ``main.py`` (issue #154). Nothing here is new logic —
every block is a byte-identical slice of the pre-split ``main.py``.

**The statement order in this module is load-bearing.** Two constraints:

1. The bulk ``from astro_ai import ...`` below must stay ABOVE ``load_dotenv``.
   Those modules evaluate ``os.environ.get(...)`` constants (SQLite paths, GCS
   fallback dirs) at import time, and ``load_dotenv(override=True)`` overrides
   real environment variables. Importing them after it would silently change
   the production DB path. This mirrors pre-split ``main.py`` exactly.
2. ``_ARTICLE_TITLE_BY_SLUG`` must be defined before ``_linkify_learn``, and
   ``load_dotenv`` before ``_site_url()`` / the ga4 / clarity / google_client_id
   globals, which are *evaluated* at import and read the environment.

Import rule for this package: absolute imports only (``from astro_ai import X``).
Sibling route modules shadow the names of real top-level modules
(``routes/festivals.py`` vs ``astro_ai/festivals.py``), so a relative import
self-imports and fails as a baffling AttributeError instead of an ImportError.
Nothing in this package may import ``astro_ai.main``.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time as _time
from datetime import date
from pathlib import Path

import jinja2
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from astro_ai.chart import compute_chart, compute_panchang, compute_transit_snapshot
from astro_ai.i18n import translate as _i18n_translate

# Deliberately copied UNPRUNED from main.py: several of these names are unused
# *here*, but importing the same set in the same position preserves the
# module-import order the app has always had (see constraint 1 above). Pruning
# it would move load_dotenv earlier in the import graph for whichever module
# got dropped.
from astro_ai import cache, daily_cache, email_sender, events, feedback, festivals, learn_registry, notify, shloks, snapshots, storage, subscribers, trivia, trust_bar, users


from astro_ai.session import (
    SUPPORTED_LANGS,
    ChartCollection,
    SavedMatching,
    SessionUser,
    clear_collection,
    clear_user,
    load_ask_usage,
    load_collection,
    load_lang,
    load_last_matching,
    load_user,
    save_ask_usage,
    save_collection,
    save_lang,
    save_last_matching,
    save_session_atomic,
    save_user,
)


# override=True so .env edits actually take effect when uvicorn reloads —
# otherwise the first-loaded values stick for the lifetime of the process
# and editing .env feels silently broken.
# Load order: .env (committed defaults) → .env.local (git-ignored local
# overrides, e.g. dev secrets that shouldn't live in .env). .env.local wins
# on any key it defines.
load_dotenv(override=True)
load_dotenv(".env.local", override=True)


# Project layout: src/astro_ai/main.py → templates and production prompts live
# alongside the code. The sibling `evals/` folder is the prompt-evaluation
# sub-project (separate concern, not a runtime dependency).
# NOTE (#154): this module lives one level deeper than the pre-split main.py,
# so it needs .parent.parent to land on src/astro_ai/ and not src/astro_ai/routes/.
HERE = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = HERE / "templates"
PROMPTS_DIR = HERE / "prompts"
STATIC_DIR = HERE / "static"
PROMPT_PATH = PROMPTS_DIR / "natal.txt"
DAILY_PROMPT_PATH = PROMPTS_DIR / "daily.txt"
MONTHLY_PROMPT_PATH = PROMPTS_DIR / "monthly.txt"
YEARLY_PROMPT_PATH = PROMPTS_DIR / "yearly.txt"
MATCHING_PROMPT_PATH = PROMPTS_DIR / "matching.txt"
RASHIFAL_PROMPT_PATH = PROMPTS_DIR / "rashifal_single.txt"
DASHA_DEEP_DIVE_PROMPT_PATH = PROMPTS_DIR / "dasha_deep_dive.txt"
ASK_PROMPT_PATH = PROMPTS_DIR / "ask.txt"

# Per-context OVERLAYS for /ask, appended to ask.txt rather than replacing it.
#
# Overlay, not replacement, on purpose. ask.txt is ~80 lines and nearly all of
# it — voice, plain-language, honesty, safety, the cross-link rule — applies to
# every ask regardless of where the seeker came from. Three standalone prompts
# would triplicate those rules, and the next safety fix would land in one file
# and silently not the other two. That is the guidance-drift failure CLAUDE.md
# calls out by name, so the shared rules stay in exactly one place.
#
# Selected by `_ask_overlay_path`, which the cache key and the generation call
# BOTH go through. If those two ever disagree about which overlay is in force,
# the answer is generated under one prompt and cached under another's
# fingerprint — the #181 failure class.
ASK_OVERLAY_PATHS = {
    # Two matching overlays, selected by whether the seeker is one of the pair.
    # A single file carried both shapes and asked the model to pick; QA's point
    # was that the code sent the right blocks but the guard was prose. Two files
    # make it mechanical, and give the shapes distinct prompt fingerprints.
    "matching": PROMPTS_DIR / "ask_matching.txt",
    "matching_third_party": PROMPTS_DIR / "ask_matching_third_party.txt",
    "numerology": PROMPTS_DIR / "ask_numerology.txt",
}


def _seeker_role(saved, last) -> str:
    """Which of the matched pair the seeker is: "groom", "bride" or "other".

    Cheap — string comparison only, no chart and no geocode — so BOTH handlers
    can call it. That matters twice over: POST uses it to pick whose chart is
    the partner's, and both use it as a cache-key component, so it must be
    derivable without the expensive work POST does.

    Identity is by DATE OF BIRTH first. Two differing birth dates identify the
    pair on their own, which is the ordinary case, and /matching labels both
    name fields "(optional)" — requiring a name there silently dropped the
    partner's chart for anyone who left them blank or spelled them differently
    from their saved chart. Names are consulted ONLY when both parties share a
    birth date, where the DOB genuinely cannot disambiguate; if the names are
    missing there too, neither matches and the seeker is treated as a third
    party, which is the safe outcome.
    """
    if last is None:
        return "other"
    same_dob = last.groom_birth_date == last.bride_birth_date

    def _is(name, dob) -> bool:
        if saved.birth_date != dob:
            return False
        if not same_dob:
            return True
        # str() because a drifted session schema can hand us a non-string name
        # and .strip() on an int raises. `saved.name` is left as-is: a
        # non-string there already 500s the page in display_name() long before
        # this runs, so coercing it here would only hide a louder bug.
        n = (str(name) if name else "").strip().lower()
        mine = (saved.name or "").strip().lower()
        return bool(n) and bool(mine) and n == mine

    if _is(last.groom_name, last.groom_birth_date):
        return "groom"
    if _is(last.bride_name, last.bride_birth_date):
        return "bride"
    return "other"


def _asset_fingerprint(rel_path: str) -> str:
    """Short content hash for a file under static/, or "0" if unreadable.

    Why this exists (#253). `static/sw.js` used to serve everything under
    /static/ cache-first with no revalidation, its only eviction path a manual
    bump of CACHE_VERSION (it is now stale-while-revalidate for un-fingerprinted
    URLs; a `?v=` URL is still cache-first, which is why this hash matters). `app.css` was linked at a fixed URL, so a rebuilt
    stylesheet was never re-fetched: two rebuilds (1e07122, e06c4e7) shipped
    after the service worker landed and neither bumped the constant, so
    returning visitors were still being served the 348ab01 CSS. One of those
    rebuilds was itself a fix ("the dosha strips have been shipping without
    their tints") that therefore never arrived.

    Hashing the CONTENT rather than stamping the mtime is deliberate: a
    rebuild that changes nothing keeps the same URL, so a redeploy does not
    needlessly evict every client's cached stylesheet.

    Computed once at import. The file cannot change under a running container
    — the image is immutable — so there is nothing to invalidate.
    """
    try:
        return hashlib.sha256((STATIC_DIR / rel_path).read_bytes()).hexdigest()[:8]
    except OSError:
        # Never let a missing asset break rendering; an unfingerprinted URL
        # is a stale-cache risk, not an outage.
        log.warning("asset fingerprint: could not read static/%s", rel_path)
        return "0"


# Autoescape is PINNED here, not inherited (#409). Starlette's own default for
# `directory=` happens to be `jinja2.select_autoescape()` — escape .html/.htm/.xml
# — and that default is the only thing between a visitor's `<script>` in a
# feedback `message`/`page`/`ua` and the owner's browser at /admin/feedback.
# Nothing asserted it; a dependency bump or an `autoescape=False` would have
# kept every gate green. tests/test_autoescape_pinned.py asserts it now.
#
# The extension list is spelled out to reproduce the inherited behaviour
# byte-for-byte, NOT to widen it: `.svg` is deliberately absent because
# cosmic_card.svg has always rendered unescaped (select_autoescape() does not
# list it) and changing that would alter shipped output. See ARCHITECTURE.md.
templates = Jinja2Templates(env=jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(
        enabled_extensions=("html", "htm", "xml"),
        default_for_string=True,
        default=False,
    ),
))
# Expose i18n to every template as `t(key, **kwargs)`. Templates pass the
# current `lang` (also injected per-request) into the call.
templates.env.globals["t"] = _i18n_translate
# Cache-busting fingerprints for service-worker-cached static assets (#253).
templates.env.globals["asset_v"] = _asset_fingerprint
# current_year used by nav labels like "Horoscope 2026" — auto-updates yearly.
templates.env.globals["current_year"] = lambda: date.today().year
# Astrology-term Devanagari lookups — templates call e.g.
# {{ planet_name(p.name, lang) }} to render "गुरु" for Hindi users
# and "Jupiter" for English. See i18n.py for the lookup tables.
from astro_ai.i18n import planet_name as _p_name, yoga_name as _y_name, kaal_sarp_variant_name as _ks_name
templates.env.globals["planet_name"] = _p_name
templates.env.globals["yoga_name"] = _y_name
templates.env.globals["kaal_sarp_variant_name"] = _ks_name


# slug → title lookup for the linkify filter (renders anchors with the
# article's proper title instead of the raw slug URL).
from astro_ai.learn_registry import ARTICLES as _ARTICLES
_ARTICLE_TITLE_BY_SLUG: dict[str, str] = {
    a.slug: (a.seo_title.strip() or a.title.strip()) for a in _ARTICLES
}

# Rendered in the homepage trust row (#188). Computed here rather than typed into
# the template because a hardcoded "75" is silently wrong the day article 76 ships
# and nothing breaks to tell you — the same shape of defect as the _FESTIVALS_2026
# dates. A plain int, not a lambda like `current_year`: ARTICLES is a tuple literal
# built at import and cannot change within a process, so there is nothing to
# re-evaluate. Cost is len() on an in-process tuple — no I/O, safe on the hot path.
templates.env.globals["learn_article_count"] = len(_ARTICLES)


def _linkify_learn(text: str) -> str:
    """Convert plain "/learn/<slug>/" occurrences in LLM output into <a href> tags.

    The natal / matching / ask LLM prompts instruct the model to emit cross-links
    as bare slug paths (e.g. "For more, see our Vimshottari Dasha guide →
    /learn/vimshottari-dasha-explained/"). This filter turns those into real
    clickable anchors when the reading is rendered.

    Anchor label is the article's title (via slug lookup) — much nicer to read
    than the raw URL. Unknown slugs fall back to the URL as label so nothing
    silently disappears.

    Escapes HTML first (defence-in-depth against LLM injecting tags), then
    substitutes the /learn/<slug>/ pattern with an anchor. Returns Markup so
    Jinja does not re-escape the anchor.
    """
    import html as _html
    import re as _re
    from markupsafe import Markup

    escaped = _html.escape(text or "")
    # Only match well-formed slugs (lowercase letters, digits, hyphens).
    pattern = _re.compile(r"/learn/([a-z0-9][a-z0-9-]*[a-z0-9])/")

    def _replace(match):
        slug = match.group(1)
        title = _ARTICLE_TITLE_BY_SLUG.get(slug, f"/learn/{slug}/")
        return (
            f'<a href="/learn/{slug}/" '
            # Built in Python, so Tailwind's scanner never sees it — these
            # utilities are emitted only because templates use them too. This
            # is `_linkify_learn`, which rewrites every /learn/<slug>/ mention
            # inside LLM prose across the whole site, so a stale colour here
            # shows up in the body of readings on every migrated screen at once.
            f'class="text-bhagya-sindoor hover:text-bhagya-ink underline underline-offset-2">'
            f'{_html.escape(title)}</a>'
        )

    return Markup(pattern.sub(_replace, escaped))


templates.env.filters["linkify_learn"] = _linkify_learn


def _site_url() -> str:
    """Canonical site URL for SEO meta + email links.

    Returned by the Jinja global `site_url` and used by sitemap.xml etc.
    Defaults to the production custom domain; override per-environment with
    BHAGYA_SITE_URL when running on a staging/preview deploy.
    """
    return os.environ.get("BHAGYA_SITE_URL", "").rstrip("/") or "https://shubhagya.com"


# Expose site_url to every template so canonical/OG/JSON-LD tags can build
# absolute URLs without each handler passing it in.
templates.env.globals["site_url"] = _site_url()
# GA4 measurement ID — base.html conditionally loads gtag.js when set.
# Leave unset in local dev / preview so analytics don't pollute the prod
# property with junk events.
templates.env.globals["ga4_measurement_id"] = os.environ.get("GA4_MEASUREMENT_ID", "").strip()
# Microsoft Clarity project ID — for session recordings + heatmaps. Free,
# complements GA4. Loaded only when set (skip on dev / preview).
templates.env.globals["clarity_project_id"] = os.environ.get("CLARITY_PROJECT_ID", "").strip()
# Google Identity Services client ID — templates use this to render the
# Sign-In button. Safe to expose publicly (it's the OAuth client ID, not the
# secret). Empty in dev if unset; sign-in button hides itself in that case.
templates.env.globals["google_client_id"] = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
# Request-scoped current user helper — templates call {{ load_current_user(request) }}
# at the top of _nav.html / _account_menu.html to decide what to render.
# Fast: just deserialises the cookie.
templates.env.globals["load_current_user"] = load_user


def _is_subscribed(email: str | None) -> bool:
    """Template helper — does this email have an active Rashifal subscription?

    Used by the daily-Rashifal CTA on the homepage so signed-in subscribers
    see a "you're subscribed" state instead of being nudged to subscribe
    again. Empty/None email returns False.
    """
    if not email:
        return False
    return subscribers.find_by_email(email.strip().lower()) is not None


templates.env.globals["is_subscribed"] = _is_subscribed


def _user_age_bucket(request: Request) -> str:
    """Derive the seeker's age bucket from their saved chart's birthdate.

    Returns one of: 'under-18', '18-24', '25-34', '35-44', '45-54', '55+',
    or '' when there's no saved chart yet. Sent to GA4 as a user property
    so we can slice every event by age cohort — answers questions like
    "do 25-34 users subscribe to daily Rashifal more often than 45-54?".

    Privacy: we NEVER expose the raw birthdate to analytics — only the
    bucket. The chart cookie itself is HMAC-signed and HttpOnly, the bucket
    is computed server-side and the value sent is one of 6 broad ranges.
    """
    collection = load_collection(request)
    if not collection.active:
        return ""
    try:
        birth_year = int(collection.active.birth_date[:4])
        age = date.today().year - birth_year
    except (ValueError, TypeError):
        return ""
    if age < 18:  return "under-18"
    if age < 25:  return "18-24"
    if age < 35:  return "25-34"
    if age < 45:  return "35-44"
    if age < 55:  return "45-54"
    return "55+"


# Expose as a template function: {{ user_age_bucket(request) }} in any
# template (Jinja's TemplateResponse provides `request` to all templates).
templates.env.globals["user_age_bucket"] = _user_age_bucket


def _lang(request: Request) -> str:
    """Resolve reading language. Precedence: /hi path prefix → `?lang=` → cookie.

    Every language-aware page in the app reads its language through this one
    function (58 call sites across 19 modules), so the `/hi/{path}` prefix is
    implemented here rather than 58 times: the `/hi` router sets
    `request.state.forced_lang = "hi"` and awaits the existing English handler.

    The prefix deliberately does NOT rewrite `scope["path"]`. A path-stripping
    middleware was built and rejected: mutating the path makes
    `request.url.path` return the English path inside the handler, so
    `base.html`'s canonical would point /hi/rashifal at /rashifal — the exact
    cross-language canonical #124 exists to remove. Reproduced by execution.

    `?lang=hi` used to be a silent no-op everywhere (QA finding on /festivals) —
    this function only read the __session cookie, so a shared or bookmarked
    Hindi link rendered in English. Honouring the param is still safe, but only
    two of the three original reasons survive:

    - Nothing that calls _lang declares `lang` as a query parameter, so nothing
      is shadowed. (`/lang` takes it as a Form field, and POST bodies are
      untouched. `POST /admin/warm-rashifal` DOES take `lang` as a query param —
      verified in the OpenAPI schema 2026-09-20, it is the only one — but it
      reads the param directly and never calls _lang, so there is no conflict.
      The earlier absolute "no route declares it" was simply wrong.) The `/hi`
      routes declare `rashi` and a catch-all, never `lang`.
    - No CDN-cached HTML route depends on _lang, and this is now load-bearing
      rather than incidental: it is what stops a cookie-`hi` render being
      snapshotted by a shared cache and served to a cookieless visitor sitting
      at an English URL. `routes/kundli_card.py:127` (the cosmic-card SVG) is
      still the ONLY `public, max-age` response in the app and it still does not
      call _lang; /panchang, /rashifal and /festivals are all `_no_cdn_cache`.
      Edge caches key on the full URL including query string anyway, so
      `?lang=hi` and the bare path cannot collide. Keep it true.
    - INVALIDATED — `base.html` emits `<link rel=canonical>` from
      `request.url.path` only, which used to mean `?lang=` variants
      self-canonicalise and add no duplicate-content surface. That reasoning
      dies the moment a path has a published Hindi twin: `/rashifal?lang=hi`
      renders Hindi prose while its canonical claims `/rashifal`, i.e. the
      cross-language canonical the issue forbids. S8 fixes it by 301-ing
      `?lang=hi` → `/hi/{path}` for paths in `hindi_pages.HINDI_PUBLISHED` ONLY.
      Unpublished paths have no Hindi URL to redirect to, so `?lang=hi` keeps
      working there exactly as it does today.

    Cookie vs URL: the cookie still wins on English URLs (status quo), and
    `/hi/*` forces Hindi regardless of cookie. "URL wins over cookie" — i.e.
    an English URL forcing English over a `hi` cookie — was considered and
    deliberately NOT built: `email/daily_rashifal.html:233,249` and
    `email/welcome.html:140` deep-link Hindi subscribers to `/rashifal#{slug}`,
    and templates carry 5 bare `href="/rashifal"` links plus `/rashifal#…` and
    `/rashifal/{slug}` variants (counted 2026-09-20), so that change would land
    every Hindi subscriber's daily email on an English page. Its only benefit
    accrues to crawlers, which carry no cookie and so never hit the case.

    Deliberately request-scoped: it does NOT write the cookie. `POST /lang` is
    still the only thing that changes a stored preference, so a shared link
    can't silently flip the recipient's saved language. An unsupported value —
    in `forced_lang` or in `?lang=` — falls through to the next source rather
    than forcing English.
    """
    # Set by the /hi router (routes/hindi.py), never by a client. Membership
    # test, not a truthiness check: a junk forced_lang must fall through to the
    # query param and cookie, not pin the page to a language that has no strings.
    forced = getattr(request.state, "forced_lang", None)
    if forced in SUPPORTED_LANGS:
        return forced
    requested = request.query_params.get("lang")
    if requested in SUPPORTED_LANGS:
        return requested
    return load_lang(request)


# The /hi allow-list, exposed to templates. Module-scope import is safe in both
# directions: hindi_pages holds no astro_ai imports at module scope, and its
# hreflang_alternates() pulls _site_url from THIS module lazily, inside the
# function body, precisely so deps.py can import it here.
#   - hreflang_alternates(path) → base.html's <link rel=alternate> tags (S6)
#   - hindi_url(path) → /hi twin, or None when unpublished (S7 nav toggle;
#     None is also the toggle's "hide me" signal)
#   - english_url(path) → the way back from a /hi page (S7)
# is_hindi_published() is deliberately NOT exposed: it is exactly
# `hindi_url(path) is not None`, and one predicate is one fewer thing that can
# disagree with the other.
from astro_ai import hindi_pages


def _lang_prefix(lang: str, path: str) -> str:
    """"/hi" when this page is being served as Hindi at a /hi URL, else "".

    For building a page's own links — the rashi tiles' hx-get, the JSON-LD
    @id, breadcrumbs, the WhatsApp share URL. Those all used to hardcode
    /rashifal/{slug}, which on a Hindi page meant the tiles fetched English
    readings and the structured data asserted the English URL as this page's
    identity (QA 2026-10-04).

    Conditioned on the PATH as well as the language, not language alone: with
    a `hi` cookie, /rashifal (no prefix) renders Hindi and must keep linking
    to unprefixed URLs, because that is the URL it is published at. Keying on
    `lang == "hi"` alone would have rewritten those links to /hi/..., which
    is a different published URL, from a page that is not it.

    Returns "" for a Hindi page that has no /hi twin, since there is nothing
    to prefix to — `hindi_url()` is the single source of that truth, so this
    cannot drift from the allow-list or the hreflang tags.
    """
    if lang != "hi":
        return ""
    return "/hi" if path.startswith("/hi/") or path == "/hi" else ""


templates.env.globals["lang_prefix_for"] = _lang_prefix
templates.env.globals["hreflang_alternates"] = hindi_pages.hreflang_alternates
templates.env.globals["hindi_url"] = hindi_pages.hindi_url
templates.env.globals["english_url"] = hindi_pages.english_url
# Non-normalising, for round-tripping the URL a reader is standing on —
# see strip_hi_prefix's docstring for why english_url is wrong there.
templates.env.globals["strip_hi_prefix"] = hindi_pages.strip_hi_prefix


def _save_collection_synced(response: Response, collection: ChartCollection, request: Request) -> None:
    """Save a ChartCollection to the cookie AND (if signed in) to users.json.

    Wrapper around session.save_collection that ensures signed-in users'
    chart state stays in sync across their devices. Anonymous users get
    exactly the previous behaviour (cookie-only). Silent failure on
    users.json write — cookie remains the source of truth for THIS
    session either way.
    """
    save_collection(response, collection, request)
    user = load_user(request)
    if user is not None:
        try:
            users.save_charts(user.sub, collection)
        except Exception as err:
            import logging
            logging.getLogger(__name__).warning(
                "chart sync to users.json failed for %s: %s", user.email, err
            )


_basic_auth = HTTPBasic(realm="Bhagya admin")
_ADMIN_DEV_FALLBACK = "bhagya-dev-only-CHANGE-ME"


def require_admin(creds: HTTPBasicCredentials = Depends(_basic_auth)) -> None:
    """HTTP Basic Auth gate for admin routes.

    Username must be 'admin'; password comes from the ADMIN_PASSWORD env var.
    If unset, falls back to a clearly-flagged dev placeholder so local
    development still works — but the var MUST be set before any deploy.
    `secrets.compare_digest` is used on both sides to dodge timing attacks.
    """
    expected_password = os.environ.get("ADMIN_PASSWORD", _ADMIN_DEV_FALLBACK)
    ok_user = secrets.compare_digest(creds.username, "admin")
    ok_pass = secrets.compare_digest(creds.password, expected_password)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": 'Basic realm="Bhagya admin"'},
        )


# Hindi month names for _pretty_date() — English strftime gives us "July"
# etc. natively but there's no locale-friendly way to get "जुलाई" without
# pulling in a full ICU dependency, so we spell it out. Month order is
# Jan=1 .. Dec=12; index 0 is a placeholder to keep month numbers 1-indexed.
_HINDI_MONTHS: tuple[str, ...] = (
    "", "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून",
    "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर",
)


# Hindi weekday names — same reasoning as _HINDI_MONTHS above: strftime("%A")
# gives us "Monday" natively and there is no locale-friendly way to get
# "सोमवार" without an ICU dependency. Indexed by date.weekday(), so
# Monday=0 .. Sunday=6.
_HINDI_WEEKDAYS: tuple[str, ...] = (
    "सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार",
)


def _pretty_weekday(d: date, lang: str = "en") -> str:
    """Weekday name for visible page chrome. English → "Monday", Hindi → "सोमवार".

    Companion to _pretty_date(): anywhere a date is localised, its weekday has
    to be too, or ?lang=hi renders "17 अगस्त 2026 · Monday".
    """
    if lang == "hi":
        return _HINDI_WEEKDAYS[d.weekday()]
    return d.strftime("%A")


def _pretty_date(iso_date: str, lang: str = "en") -> str:
    """Format an ISO date as human-friendly text for user-facing titles.

    ISO dates ('2026-07-31') in page titles kill click-through — external
    SEO audit flagged this specifically. Use this helper anywhere a date
    lands in a `<title>`, `<h1>`, or visible page chrome. Keep the raw ISO
    form for machine-readable slots (`<time datetime="...">`, sitemap
    lastmod, JSON-LD datePublished).

    English → "31 July 2026" (drops weekday — daily-content pages don't need
    the extra length; the current-day framing is already implied).
    Hindi   → "31 जुलाई 2026" (Devanagari digits look wrong here — most Indian
    UIs use Arabic numerals even in Hindi, matching AstroSage / mPanchang).
    """
    from datetime import date as _date
    try:
        d = _date.fromisoformat(iso_date)
    except (TypeError, ValueError):
        return iso_date  # last-resort — bad input should not break rendering
    if lang == "hi":
        return f"{d.day} {_HINDI_MONTHS[d.month]} {d.year}"
    return d.strftime("%-d %B %Y")


def _safe_redirect_target(candidate: str) -> str:
    """Allow only same-origin paths in `next=` redirects (open-redirect guard)."""
    return candidate if candidate.startswith("/") and not candidate.startswith("//") else "/"


def _is_localhost(request: Request) -> bool:
    """True when the request is from the developer's own machine.

    Used to bypass the /ask daily quota during local development so the dev
    can exercise the feature freely without exhausting the production limit.
    Covers IPv4 loopback, IPv6 loopback, and the "localhost" hostname.
    """
    client = request.client
    if client is None:
        return False
    return client.host in {"127.0.0.1", "localhost", "::1"}


def _no_cdn_cache(resp: Response) -> Response:
    """Stamp response with headers that stop CDN edge caches from
    snapshotting the page across deploys.

    External re-audit caught /rashifal being served from a stale Fastly
    snapshot even though the site had been deployed with fixes. Root
    cause: Cloud Run sends `cache-control: private` by default which
    SHOULD prevent shared-cache storage, but Fastly's default config
    snapshots aggressively on non-cookie'd anonymous fetches. Stronger
    directives fix that.

    Applied only to pages whose content changes daily (Rashifal,
    Panchang) — for evergreen /learn/ articles or static tool pages,
    the default cache-control is fine and desirable.
    """
    resp.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    # CDN-specific opt-out signals (Fastly / Cloudflare / GCP CDN all
    # honour at least one of these — belt-and-braces is cheap here).
    resp.headers["CDN-Cache-Control"] = "no-store"
    resp.headers["Surrogate-Control"] = "no-store"
    return resp


# Daily per-cookie quota. Tight at 3/day while we're on free LLM tiers —
# one motivated user can't drain Groq/Cerebras's daily quota for everyone.
# Bump this when we have paid LLM capacity or revenue covering the cost.
_ASK_DAILY_LIMIT = 3

# Exposed to templates so marketing copy quotes the real number (#242's trust
# strip does). Same reasoning as learn_article_count above: a hardcoded "3" in
# a template is silently wrong the day this constant moves, and nothing breaks
# to say so. index.html still carries two prose "3 free" strings in sentences
# that would need rewording anyway — those are not covered by this.
templates.env.globals["ask_daily_limit"] = _ASK_DAILY_LIMIT


def _ask_quota_remaining(request: Request) -> int:
    """Read today's remaining ask count from the session cookie.

    Localhost bypasses the quota entirely — returns a large sentinel so
    the UI shows plenty of remaining questions during local development.
    """
    if _is_localhost(request):
        return 9999
    stored_date, used = load_ask_usage(request)
    today = date.today().isoformat()
    if stored_date != today:
        return _ASK_DAILY_LIMIT
    return max(0, _ASK_DAILY_LIMIT - used)


def _ask_quota_bump(request: Request, response: Response) -> None:
    """Increment today's count on the response cookie.

    Localhost skips the increment so local dev exercises the feature
    without touching production-shaped state.
    """
    if _is_localhost(request):
        return
    stored_date, used = load_ask_usage(request)
    today = date.today().isoformat()
    new_count = (used + 1) if stored_date == today else 1
    save_ask_usage(response, request, today, new_count)


def _ask_cta_ctx(request: Request, hint: str = "about your chart") -> dict:
    """Build the context dict for the shared _ask_cta.html partial.

    Any result page that wants to show the 'Ask 3 free questions' CTA
    just merges this into its TemplateResponse context. Handles:
      - Detecting a saved chart (has_saved_chart)
      - Reading today's remaining quota
      - Passing the per-page phrasing hint ('about your chart' vs
        'about your numerology' vs 'about your Kundli match')
    """
    try:
        has_saved_chart = load_collection(request).active is not None
    except Exception:
        has_saved_chart = False
    return {
        "has_saved_chart": has_saved_chart,
        "ask_remaining": _ask_quota_remaining(request),
        "ask_context_hint": hint,
    }


# In-process daily cache for the Panchang strip. Keyed by
# (today_iso, city_lower). First homepage load for a given (date, city)
# pair runs the full compute chain (geocode + chart + panchang + transit
# snapshot ≈ 200ms cold on first hit); every subsequent same-day load
# on the same instance is a dict lookup.
_PANCHANG_STRIP_CACHE: dict[tuple, tuple] = {}


def panchang_strip_ctx(request) -> dict:
    """Template context for the Panchang strip, resolved for THIS seeker.

    The strip's whole point on a rashifal page is that Rahu Kaal and Abhijit
    are location-dependent: across Indian cities they shift by up to 79
    minutes, and Kolkata's Abhijit window does not overlap Mumbai's at all.
    The shared reading therefore names those windows without ever clocking
    them (see chart.format_day_windows_for_rashifal); this is what puts the
    reader's OWN times on the page beside the words.

    Falls back to Mumbai when there is no saved chart — the same default the
    homepage uses, and the same one the reading itself was generated against.
    """
    city = "Mumbai, India"
    try:
        collection = load_collection(request)
        if collection.active and collection.active.birth_place:
            city = collection.active.birth_place
    except Exception:
        pass
    panchang, moon, display = panchang_strip_for_city(city)
    return {
        "panchang_strip": panchang,
        "panchang_moon": moon,
        "panchang_city": display,
    }


log = logging.getLogger(__name__)


_FALLBACK_TTL_S = 60.0
"""Seconds a fallback-derived (default-city) strip is served before re-solving.

The two failure cases genuinely want different windows, and collapsing them
into one was the mistake. If the fallback SUCCEEDED we have something correct
and honestly labelled to show, so the only question is how soon to retry the
reader's real city — a minute. If BOTH legs failed there is nothing to show,
so retrying soon buys nothing and costs a blocking 10s geocode; that case
takes the long window below.
"""

_TOTAL_FAILURE_TTL_S = 600.0
"""Seconds a TOTAL geocode failure (both legs) is remembered before retrying.

Ten minutes, not sixty seconds and not the whole day. Geocoding blocks for 10s
(`chart.py` timeout) and `/rashifal` is an `async def` calling it inline, so a
short TTL re-arms an event-loop stall every minute: roughly a 16% duty cycle at
60s against ~1.7% at 600s. The old day-long cache had no duty cycle at all but
cost a full day of missing strips for a five-minute outage. Ten minutes buys
most of the first and keeps self-healing.
"""

_fallback_cache: dict[tuple, tuple] = {}
"""key -> (result, monotonic_at). Holds BOTH degraded cases; the TTL applied on
read depends on whether the result is usable."""


def _remember_degraded(key: tuple, result: tuple) -> None:
    """Record a degraded lookup, bounded like the two sibling caches."""
    _fallback_cache[key] = (result, _time.monotonic())
    if len(_fallback_cache) > _STRIP_CACHE_MAX:
        _fallback_cache.clear()
        _fallback_cache[key] = (result, _time.monotonic())

_STRIP_CACHE_MAX = 100
"""Entries kept in the strip day-cache before the oldest are evicted."""

_STRIP_DEFAULT_CITY = "Mumbai, India"
"""Fallback location for the Panchang strip.

Also the location the shared rashifal is generated against, which is why it
is the right fallback rather than an arbitrary one: a reader who lands on it
sees the same city the reading was written for, labelled as such.
"""


def panchang_strip_for_city(city: str) -> tuple:
    """Return (panchang, moon_info, city_display) — cached per day/city.

    Lives HERE, not in home.py, because it now has more than one consumer:
    the homepage strip and the rashifal pages both need the reader's own
    Rahu Kaal / Abhijit. It is the single place those windows are obtained
    for a page — nothing may recompute sunrise, Rahu Kaal or Abhijit for
    itself. compute_panchang has its own (date, coarse lat/lon, tz) cache
    underneath, so two cities in the same 55km bucket also share one solve.

    Uses date.today() implicitly so a new day naturally busts the cache.
    Cache is per-process (Cloud Run instances rebuild once each per day).

    That last sentence used to end "which is fine — the compute is <200ms so
    cold-start latency is negligible". Measured 2026-09-04, it is not: the
    FIRST call in a process takes **1.09s**, a second call for a DIFFERENT
    city 0.048s, and a repeat 0.000s. The gap is one-time global init the
    strip merely happens to trigger first — TimezoneFinder() at 0.551s and a
    live Nominatim geocode at 0.422s — not the panchang solve, which is
    indeed ~50ms. `main._warm_process_globals` now pays it during startup;
    the numbers and the rejected alternative are recorded there.
    """
    today = date.today().isoformat()
    resolved_city = (city or "").strip() or _STRIP_DEFAULT_CITY
    # Key on the RESOLVED city, so "", "  " and None share the Mumbai entry
    # instead of each opening a duplicate slot for identical data (#214).
    key = (today, resolved_city.lower())
    if key in _PANCHANG_STRIP_CACHE:
        return _PANCHANG_STRIP_CACHE[key]

    def _solve(place: str) -> tuple:
        chart_for_loc = compute_chart("2000-01-01", "12:00", place)
        pan = compute_panchang(chart_for_loc)
        transit = compute_transit_snapshot(chart_for_loc)
        moon = next((pl for pl in transit.planets if pl.name == "Moon"), None)
        moon_info = {"rashi": moon.rashi, "nakshatra": moon.nakshatra} if moon else None
        return (pan, moon_info, place.split(",")[0])

    # Fallback-derived result from a recent failure: SERVE IT, don't re-solve.
    # An earlier version marked the key and served nothing, which blanked the
    # strip for 60s — the #213 defect the fallback exists to prevent, made
    # intermittent instead of all-day. The reader keeps the Mumbai-labelled
    # times until the window lets us retry their real city.
    hit = _fallback_cache.get(key)
    if hit is not None:
        cached_result, at = hit
        # TTL depends on WHICH failure this was, which is the whole point of
        # the split: a usable fallback is retried soon, a total failure is not.
        ttl = _FALLBACK_TTL_S if cached_result[0] is not None else _TOTAL_FAILURE_TTL_S
        if _time.monotonic() - at < ttl:
            return cached_result
        # .pop(key, None), NOT del. Nothing holds a lock between the .get()
        # above and this line, so two threads reading the same expired entry
        # both reach it and the loser raises KeyError — which escapes to the
        # route and 500s / and /rashifal. Worse, the TTL boundary is exactly
        # when a herd converges on this key (there is no single-flight around
        # the re-solve), so the race window coincides with peak concurrency.
        # Reproduced at 1 escape in 16,000 calls under forced switching.
        # The eviction 90 lines below already uses .pop for this reason.
        _fallback_cache.pop(key, None)

    degraded = False
    try:
        result = _solve(resolved_city)
    except Exception:
        degraded = True
        # FALL BACK TO THE DEFAULT CITY, do not return None (#213).
        #
        # This used to yield (None, None, ""), and `_panchang_strip.html`
        # opens with `{% if panchang_strip %}` — so the whole strip vanished.
        # That was survivable while the strip was decoration. It stopped being
        # survivable when the rashifal reading was changed to never state a
        # clock time and to point at "the Abhijit window" instead: with the
        # strip gone, the page tells the reader to act in a window and offers
        # no way on Earth to know when it is.
        #
        # Mumbai is the honest fallback rather than a guess — it is the
        # reference location the shared reading was generated against, and
        # `panchang_city` displays it, so the reader sees WHICH city's times
        # they are looking at rather than being told nothing.
        #
        # Geocoding is a live Nominatim call with a 10s timeout, so a
        # transient upstream blip is enough to land here.
        log.warning("panchang strip: %r did not resolve — falling back to %s",
                    resolved_city, _STRIP_DEFAULT_CITY)
        try:
            if resolved_city == _STRIP_DEFAULT_CITY:
                # The failing input WAS the default. Re-solving it calls the
                # same geocode with the same argument and waits the same 10s
                # to fail the same way — 20s per request on the signed-out
                # homepage, i.e. every visitor without a saved chart.
                raise
            result = _solve(_STRIP_DEFAULT_CITY)
        except Exception:
            # Default failed too: something is properly broken. Return the
            # empty tuple rather than raising — a missing strip must never
            # take the page down — but do NOT cache it for the day, so the
            # next request retries instead of the page staying broken until
            # midnight.
            log.exception("panchang strip: default city failed too; strip suppressed")
            # Bounded negative cache. "Never cache" looked safer and was much
            # worse: geocode_place's lru_cache does not memoise a raising call
            # either, so NOTHING memoised and every request paid the timeout
            # again. Baseline paid 10s once a day; this paid 20s forever. And
            # index() is a sync def on the threadpool, so it saturates workers
            # — the #144 shape (a 13s homepage) reintroduced under a failure
            # mode rather than on a hot path.
            # BOTH legs failed, so there is nothing to serve and nothing to
            # gain from retrying soon — the reader gets no strip either way.
            # This gets the LONG window, because retrying it is pure cost:
            # geocode blocks for 10s (chart.py:386) and /rashifal is an async
            # def calling it inline, so a short TTL re-arms an event-loop
            # stall every minute. Measured duty cycle at 60s: ~16% of wall
            # clock with workers held. At 600s: ~1.7%, and it still self-heals
            # within ten minutes rather than at midnight, which is what the
            # old day-long cache cost.
            _remember_degraded(key, (None, None, ""))
            return (None, None, "")
    if degraded:
        # Fallback-derived: right for the DEFAULT city, not the one asked for.
        # Day-caching it would pin that reader to Mumbai after a single blip —
        # a Guwahati reader would see an Abhijit 76 min off, not overlapping
        # their real ~51-minute window at all. So it goes in a SHORT-TTL cache:
        # served for the window (so the strip never blanks), then re-solved.
        _remember_degraded(key, result)
        return result
    _PANCHANG_STRIP_CACHE[key] = result
    # Bound growth if many cities are queried across a day (#214).
    #
    # This used to clear() the whole dict, which threw away the DEFAULT-city
    # entry — the one backing every signed-out `/` and `/rashifal` — along
    # with the long tail that tripped the limit. Measured: clear() fired at
    # entry 101 and left exactly 1 — the key being written. (Inserting all 106
    # sequentially ends at 6, because five more arrive after the clear; the
    # original note said "106 in, 1 out", which a reader reproduces as 6 and
    # reasonably concludes the comment is wrong. State the mechanism, not a
    # figure whose harness you did not describe.) It also trips sooner than it used to, because the rashifal pages
    # now feed signed-in cities into the same dict.
    #
    # Drop oldest-inserted instead (dicts preserve insertion order), and never
    # evict the default: it is the hottest key in the process and the most
    # expensive to lose.
    if len(_PANCHANG_STRIP_CACHE) > _STRIP_CACHE_MAX:
        default_key = (today, _STRIP_DEFAULT_CITY.lower())
        # tuple(dict) snapshots in ONE C-level call that cannot be preempted.
        # A plain comprehension iterates the live dict from Python and raises
        # "dictionary changed size during iteration" under concurrency —
        # the plain comprehension raised in EVERY configuration tried, and
        # tuple(d) raised in NONE — that is the load-bearing claim and it
        # reproduces. The error COUNT does not travel: it depends on
        # sys.setswitchinterval and on the reader-thread count, and
        # independent runs have landed anywhere from 3 (CPython default) to
        # ~33,000 (forced switching, 64 readers). An earlier version of this
        # comment quoted a bare "20,013", which a reader reproduces as
        # something else entirely and reasonably concludes is invented. Quote
        # the mechanism, not a number whose harness you did not state.
        # Surfaces as a
        # 500 on / and /rashifal. The clear() this replaced was a single C
        # call and could not raise, so this was a NEW failure mode.
        for stale in [k for k in tuple(_PANCHANG_STRIP_CACHE)
                      if k not in (key, default_key)][:len(_PANCHANG_STRIP_CACHE) - _STRIP_CACHE_MAX]:
            _PANCHANG_STRIP_CACHE.pop(stale, None)
    return result
