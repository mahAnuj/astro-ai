/* Shubh Bhagya analytics wrapper.
 *
 * Single source of truth for all tracking. Templates never touch gtag or
 * clarity directly — they call `Analytics.kundliGenerated({lang})` etc.
 * That way:
 *   1. Templates stay readable (no SDK plumbing inline).
 *   2. We can swap providers (e.g., add Posthog, drop Clarity) by editing
 *      this one file — call sites stay unchanged.
 *   3. Disabling analytics (env unset) is automatic — Analytics methods
 *      become no-ops, no `if (window.gtag)` guards in templates.
 *
 * Config comes from window.BHAGYA_ANALYTICS_CONFIG, which base.html
 * populates server-side from env vars:
 *   { ga4: 'G-XXXXXXXXXX', clarity: 'abc123def' }
 *
 * Both fields are optional — set zero, one, or both. Empty/missing →
 * that provider just isn't loaded.
 *
 * Public API (window.Analytics):
 *   .track(name, params)           — raw event, drops to all configured providers
 *   .kundliGenerated({lang})       — core conversion: someone read their chart
 *   .subscribeCompleted({lang,from_path}) — subscribed to daily Rashifal; from_path
 *                                    is the page's path only (#1229), never a query
 *   .languageSwitched({to_lang})   — picked English/Hindi in the nav (#1229); fired
 *                                    by the delegated change listener below, only
 *                                    for en|hi, beacon transport
 *   .pwaInstalled()                — accepted the PWA install prompt
 *   .feedbackSent({type})          — submitted the feedback form
 *   .pageView(path)                — manual pageview (use for SPA nav)
 *   .ctaClick({from_path,to_path}) — a /learn reader followed an in-article link
 *                                    to a tool; links in nav/header/footer never
 *                                    count (fired by the delegated listener
 *                                    below, not by templates — see TOOL_ROOTS)
 *   .toolSubmitted({tool})         — a visitor submitted a tool form (#1226); fired
 *                                    by the delegated submit listener below from
 *                                    `form[data-tool]`, never by a template
 *   .login({method})               — signed in; method 'google' only, beacon
 *                                    transport. Called by base.html's
 *                                    handleGoogleSignIn at event time, before the
 *                                    reload (#1229)
 *   .share({method,content_type})  — clicked a share control (#1229); fired by the
 *                                    delegated click listener below from
 *                                    `[data-share-method]` (+ data-share-content),
 *                                    both values from a fixed list
 *
 * Add a new event by adding a method here — keep templates dumb.
 *
 * Firing an event from a TEMPLATE (#1067) -- declare it, never call it:
 *   {% from "_analytics_event.html" import analytics_event %}
 *   {{ analytics_event('kundli_generated', {'lang': lang}) }}
 * renders `<div hidden data-analytics-event="kundli_generated"
 * data-analytics-params='{"lang":"en"}'>`, and this file fires it. Never put
 * `Analytics.*(` in an inline top-level <script>: this file loads with `defer`,
 * so the inline call runs first and throws "Analytics is not defined" on every
 * full page load (that is how kundli_generated, ask_answered and
 * dasha_deep_dive_viewed were lost). tests/test_analytics_declared_events.py
 * fails on such a call. Declared events are fired once each, on DOMContentLoaded
 * and after every htmx swap, then stamped `data-analytics-fired`. Params: only
 * fixed-vocabulary scalars (a language code, a planet name, a category), never
 * free text or anything a visitor typed -- see PII_PARAMS below.
 */
(function () {
  var cfg = window.BHAGYA_ANALYTICS_CONFIG || {};
  // The last page_location this file `set` on GA4, or null while GA4's own
  // default (the real URL) is in force.
  var gaSet = null;

  // Query parameters that carry personal text and so must never reach GA4 in a
  // URL: `q` is the visitor's whole /ask question (#528); `city` is the Panchang
  // place box, which /panchang pre-fills with the SAVED BIRTH PLACE, so pressing
  // Update navigates to /panchang?city=<birth place> (#1066); `email` and `token`
  // are the unsubscribe link every email footer carries, /unsubscribe?email=<address>
  // &token=<hmac> (#1093) -- the address, and a token that unsubscribes it. Add a
  // name here when a new GET form or shareable URL carries free text.
  var PII_PARAMS = ['q', 'city', 'email', 'token'];

  // `url` with every PII_PARAMS parameter removed. Everything else -- path, `c`,
  // utm_* -- is kept, so reports still split by them. Returns `url` unchanged
  // when none is present.
  function stripQ(url) {
    try {
      var u = new URL(url, location.href);
      var found = false;
      PII_PARAMS.forEach(function (k) {
        if (u.searchParams.has(k)) { u.searchParams.delete(k); found = true; }
      });
      return found ? u.toString() : url;
    } catch (err) { return url; }
  }
  function gaLocation() { return stripQ(location.href); }

  // Keep GA4's page_location `q`-free, and put it back when we leave. Called
  // before EVERY event and after every hx-boost history push, because a boosted
  // submit of the /ask form lands on /ask?q=<question> without re-running this
  // file: the config call below never sees that URL, and an event such as
  // `ask_answered` would carry GA4's default, document.location.href, i.e. the
  // question (QA round 1 on #528). Sends nothing unless the value changes.
  function syncLocation() {
    if (!window.gtag) return;
    var loc = gaLocation(), dirty = loc !== location.href;
    if (dirty && loc !== gaSet) {
      window.gtag('set', { page_location: loc });
      gaSet = loc;
    } else if (!dirty && gaSet !== null) {
      window.gtag('set', { page_location: location.href });
      gaSet = null;
    }
  }

  // ── GA4 bootstrap ────────────────────────────────────────────────────
  if (cfg.ga4) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + cfg.ga4;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    // anonymize_ip — required for GDPR/DPDP compliance in IN/EU markets.
    var gaCfg = { anonymize_ip: true };
    // #528: POST /ask answers with a 303 to /ask?q=<the visitor's whole question>
    // (a deliberate, shareable URL -- routes/ask.py), and GA4 records the full
    // URL as the page. `anonymize_ip` covers the address, not the page, so a
    // sentence about someone's marriage prospects sat in the property as a
    // landing page. Override `page_location` ONLY when the URL carries `q`: on
    // every other page the default is left alone, because a config parameter
    // sticks to later events and a blanket override would mis-attribute them.
    var cleanLoc = gaLocation();
    if (cleanLoc !== location.href) {
      gaCfg.page_location = cleanLoc;
      gaSet = cleanLoc;
    }
    // A full reload FROM /ask?q=... (a non-boosted link, the language switch)
    // makes document.referrer the question URL; send it without `q` as well.
    if (document.referrer) {
      var cleanRef = stripQ(document.referrer);
      if (cleanRef !== document.referrer) gaCfg.page_referrer = cleanRef;
    }
    window.gtag('config', cfg.ga4, gaCfg);
    // hx-boost swaps pages without reloading this script.
    document.addEventListener('htmx:pushedIntoHistory', syncLocation);
  }

  // ── Microsoft Clarity bootstrap ──────────────────────────────────────
  if (cfg.clarity) {
    (function (c, l, a, r, i) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      var t = l.createElement(r); t.async = 1;
      t.src = 'https://www.clarity.ms/tag/' + i;
      var y = l.getElementsByTagName(r)[0];
      y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', cfg.clarity);
  }

  // ── Internal: send an event to every configured provider ─────────────
  function track(name, params) {
    params = params || {};
    syncLocation();
    if (window.gtag) window.gtag('event', name, params);
    // Clarity has its own custom-event API — gives us tagged session
    // recordings filterable by event name in the Clarity dashboard.
    if (window.clarity) window.clarity('event', name);
  }

  // ── cta_click: a /learn reader follows an in-article link to a tool (#570) ──
  // #276/#329/#521/#518 each claim these links get used; the only proxy was
  // pages/session, which cannot resolve at ~500 sessions/28d. One delegated
  // listener on `document` rather than an attribute per link: templates stay
  // free of gtag, no article has to be edited (#311's window is open), and it
  // survives hx-boost body swaps because `document` is never swapped.
  //
  // TOOL_ROOTS is matched on the FIRST path SEGMENT, never as a substring, so
  // /muhurat/vivah, /numerology/compatibility and /dasha/deep-dive count as the
  // tool they belong to and /kundlifoo does not count as /kundli. That also
  // admits /kundli/card (an SVG, linked from no article) -- deliberate: a
  // sub-page of a tool is still the tool. Derived 2026-11-03 from every
  // distinct non-/learn/ href in templates/learn/*.html and
  // learn_article_base.html; tests/test_learn_tool_routes.py::
  // test_every_learn_internal_href_is_classified fails when a new one appears
  // unclassified, so a new tool link cannot be silently ignored.
  var TOOL_ROOTS = [
    '/kundli', '/dasha', '/matching', '/ask', '/manglik-check',
    '/sade-sati-check', '/kaal-sarp-check', '/numerology', '/muhurat',
    // #518 slice 5: karva-chauth-2026's tip routes to the Panchang (Moonrise tile).
    '/panchang'
  ];
  // SITE CHROME NEVER COUNTS, for any path. QA round 1 measured the rendered
  // /learn/sade-sati/: ~21 tool anchors sit in the desktop nav, the mobile tab
  // bar and the footer against ~6 genuine in-article links (~3:1), and no param
  // separates them -- so a chrome click is a navigation click, and counting it
  // makes the event measure the menu rather than "an in-article tool CTA".
  // Every real CTA (in-prose links, the end-of-article card, the sticky mobile
  // CTA `#learn-sticky-cta`, a <div>) sits outside <nav>, <header> and <footer>,
  // so none is lost. The test is on position because the path cannot say.
  //
  // "/" is the extra hard case: it is BOTH the Kundli form (72 in-article
  // "Generate your free Kundli" links, the end-of-article CTA, the sticky mobile
  // CTA) and the site's Home link, so it is a tool only outside chrome -- which
  // the rule above already guarantees, hence no special case beyond listing it.
  var CHROME_SELECTOR = 'nav, header, footer';

  function isToolPath(path) {
    if (path === '/') return true;
    for (var i = 0; i < TOOL_ROOTS.length; i++) {
      var r = TOOL_ROOTS[i];
      if (path === r || path.indexOf(r + '/') === 0) return true;
    }
    return false;
  }

  // PATHS ONLY: `location.pathname` and the link's `pathname`. Never the query
  // string, hash, link text or anything a visitor typed. Modified clicks
  // (ctrl/meta/shift) ARE counted -- the `click` event still fires for them and
  // a new-tab open is a follow; a middle click fires `auxclick`, not `click`,
  // and is not counted. Never preventDefault/stopPropagation: this observes.
  function ctaClickHandler(e) {
    try {
      if (location.pathname.indexOf('/learn/') !== 0) return;
      var el = e.target;
      if (el && !el.closest && el.parentElement) el = el.parentElement;  // text node
      if (!el || !el.closest) return;
      var a = el.closest('a[href]');
      if (!a) return;
      if (a.closest(CHROME_SELECTOR)) return;
      var url = new URL(a.href, location.href);
      if (url.origin !== location.origin) return;
      if (!isToolPath(url.pathname)) return;
      window.Analytics.ctaClick({ from_path: location.pathname, to_path: url.pathname });
    } catch (err) { /* analytics must never break a click */ }
  }
  // Registered once, below, together with shareClickHandler (#1229): this file
  // keeps ONE delegated click listener (tests/test_cta_click_event.py pins it).

  // ── tool_submitted: a visitor submitted a tool's form (#1226, #1070 row 1) ──
  // The denominator for slice 1's completion events (matching_completed,
  // numerology_completed, muhurat_searched, dosha_check_completed): "completed /
  // submitted" per tool. GA4's enhanced-measurement `form_submit` cannot stand in
  // for it -- body is hx-boost, so submits are AJAX and it counted 1 in 28 days.
  //
  // ONE delegated listener on `document`, not a handler bound to each form: a
  // boosted page swap replaces <body>'s children but never `document`, so this
  // keeps working on every page a visitor reaches without a reload, exactly as
  // the cta_click listener above does. `submit` bubbles, and the browser raises
  // it only for a form that passed validation, so an incomplete form is not
  // counted as a submission.
  //
  // The tool comes from the form's own `data-tool` attribute, a fixed vocabulary
  // that templates set in markup; nothing the visitor typed is read. A missing or
  // unknown value sends nothing (TOOL_NAMES is the whole list). The only param is
  // `tool`. tests/test_analytics_tool_submitted.py pins every value here against
  // the templates that carry it. Never preventDefault/stopPropagation: observe.
  var TOOL_NAMES = ['kundli', 'matching', 'numerology', 'numerology_compat',
                    'muhurat', 'manglik', 'sade_sati', 'kaal_sarp', 'ask'];

  document.addEventListener('submit', function (e) {
    try {
      var el = e.target;
      if (el && !el.closest && el.parentElement) el = el.parentElement;  // text node
      if (!el || !el.closest) return;
      var form = el.closest('form[data-tool]');
      if (!form) return;
      window.Analytics.toolSubmitted({ tool: form.getAttribute('data-tool') });
    } catch (err) { /* analytics must never break a submit */ }
  });

  // ── language_switched: the nav language <select> (#1229, #1070 row 10) ──────
  // _lang_picker.html's <select name="lang"> carries `onchange="this.form.submit()"`.
  // HTMLFormElement.submit() does NOT raise a `submit` event (only a click on a
  // submit button or requestSubmit() does), so a `submit` listener on
  // form[action="/lang"] would never fire for the one path a visitor actually
  // uses; the observable event is the select's `change`, which bubbles to
  // `document` after the inline handler has started the navigation. Hence a
  // delegated `change` listener, not the `submit` one the issue named.
  // tests/test_analytics_share_login_lang.py pins that the template still uses
  // `.submit()` so this reasoning is rechecked if the markup changes.
  //
  // Only `to_lang` is sent, and only en|hi (LANG_CODES is the whole list): a
  // value outside it sends nothing. Beacon transport: the submit is a full page
  // navigation, which can cancel a plain gtag request. Never preventDefault or
  // stopPropagation: this observes and the form must still post.
  var LANG_CODES = ['en', 'hi'];

  document.addEventListener('change', function (e) {
    try {
      var el = e.target;
      if (el && !el.closest && el.parentElement) el = el.parentElement;  // text node
      if (!el || !el.closest || !el.closest('form[action="/lang"]')) return;
      if (el.getAttribute('name') !== 'lang') return;
      window.Analytics.languageSwitched({ to_lang: el.value });
    } catch (err) { /* analytics must never break a language switch */ }
  });

  // ── share: a visitor clicks a share control (#1229, #1070 row 11) ───────────
  // The control declares itself in markup: data-share-method (SHARE_METHODS) and
  // data-share-content (SHARE_CONTENT), set on the wa.me anchors in
  // learn_article_base / rashifal_single / _rashifal_card_content, on result.html's
  // WhatsApp controls and Cosmic Card link, and on _pdf_download_button.html when
  // its including page names a content type. Nothing is read from an href, the
  // URL or the link text -- a wa.me href carries the article title or a name.
  // One delegated click listener on `document` (hx-boost safe, no per-link
  // handler); a click on an icon inside the control bubbles to it via closest().
  // Either value missing or outside its list sends nothing. Never
  // preventDefault/stopPropagation: result.html's own handler must still run.
  var SHARE_METHODS = ['whatsapp', 'snapshot', 'pdf'];
  var SHARE_CONTENT = ['kundli', 'rashifal', 'learn'];

  function shareClickHandler(e) {
    try {
      var el = e.target;
      if (el && !el.closest && el.parentElement) el = el.parentElement;  // text node
      if (!el || !el.closest) return;
      var ctl = el.closest('[data-share-method]');
      if (!ctl) return;
      window.Analytics.share({
        method: ctl.getAttribute('data-share-method'),
        content_type: ctl.getAttribute('data-share-content')
      });
    } catch (err) { /* analytics must never break a click */ }
  }

  // The one delegated click listener: cta_click, then share. Each handler has its
  // own try/catch, so a throw in one never skips the other.
  document.addEventListener('click', function (e) {
    ctaClickHandler(e);
    shareClickHandler(e);
  });

  // ── Declared events: <div hidden data-analytics-event=... data-analytics-params=...> ──
  // Templates cannot call `Analytics.*` inline (this file is deferred, so the call
  // runs first and throws), so a template declares an event as inert markup and
  // this scan fires it. An element is stamped BEFORE it is tracked: a track() that
  // throws must not leave it unfired to be retried by every later swap, and a
  // payload that cannot be parsed must not block the next element. Nothing here
  // may throw into page code.
  //
  // Params: JSON.parse, then only string/number/boolean members are kept, so a
  // nested object or array a template slips in never reaches GA4. A malformed
  // payload fires the event WITHOUT params: the conversion still counts, and
  // nothing unparsed leaves the page.
  function fireDeclared(el) {
    try {
      el.setAttribute('data-analytics-fired', '');
      var name = el.getAttribute('data-analytics-event');
      if (!name) return;
      var params = {};
      try {
        var parsed = JSON.parse(el.getAttribute('data-analytics-params') || '{}');
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
          Object.keys(parsed).forEach(function (k) {
            var t = typeof parsed[k];
            if (t === 'string' || t === 'number' || t === 'boolean') params[k] = parsed[k];
          });
        }
      } catch (err) { params = {}; }
      track(name, params);
    } catch (err) { /* analytics must never break the page */ }
  }

  function scanDeclared() {
    try {
      var nodes = document.querySelectorAll('[data-analytics-event]:not([data-analytics-fired])');
      for (var i = 0; i < nodes.length; i++) fireDeclared(nodes[i]);
    } catch (err) { /* analytics must never break the page */ }
  }

  // A deferred script runs with readyState 'interactive', after the parser has
  // finished, so the declared elements exist already: scan now. The
  // DOMContentLoaded listener covers a script that runs earlier, and
  // htmx:afterSettle covers hx-boost swaps, which replace <body>'s children
  // without reloading this file.
  document.addEventListener('DOMContentLoaded', scanDeclared);
  document.addEventListener('htmx:afterSettle', scanDeclared);
  if (document.readyState !== 'loading') scanDeclared();

  // ── Public surface ───────────────────────────────────────────────────
  window.Analytics = {
    track: track,
    kundliGenerated:    function (p) { track('kundli_generated',     p); },
    // #1229: params rebuilt from the two named fields. from_path is a PATH:
    // anything from the first `?` or `#` on is cut, so a caller that hands over
    // location.href or a search string still cannot put a query on the wire.
    subscribeCompleted: function (p) {
      p = p || {};
      var params = { lang: p.lang };
      if (typeof p.from_path === 'string') {
        params.from_path = p.from_path.split('?')[0].split('#')[0];
      }
      track('subscribe_completed', params);
    },
    pwaInstalled:       function ( ) { track('pwa_installed');           },
    feedbackSent:       function (p) { track('feedback_sent',        p); },

    // Identify the user with anonymous demographic / preference signals.
    // Called once per page with whatever the server knows: age bucket
    // (derived from their saved chart's birthdate, NEVER the raw date),
    // language preference, has-saved-chart, etc. GA4 stores these as
    // user properties so every subsequent event is sliceable by them.
    userIdentified: function (props) {
      props = props || {};
      if (window.gtag) {
        window.gtag('set', 'user_properties', props);
      }
      // Also track as an event so the property appears immediately in
      // realtime view (user_properties alone can take ~24h to surface).
      track('user_identified', props);
    },

    // Record that a feature page was viewed — derived automatically from
    // location.pathname by the auto-instrument in base.html. Lets us
    // build clean GA4 funnels like /kundli → /dasha → /matching without
    // wading through every URL variation.
    featureView: function (feature) {
      if (!feature) return;
      track('feature_view', { feature: feature });
    },

    // transport_type 'beacon': the click navigates away, and without it gtag's
    // XHR can be cancelled by the unload and the event lost. It is a
    // transport option gtag consumes on event calls, not a reported dimension.
    // Params are rebuilt from the two named fields so nothing else a caller
    // passes can reach GA4.
    ctaClick: function (p) {
      p = p || {};
      track('cta_click', {
        from_path: p.from_path,
        to_path: p.to_path,
        transport_type: 'beacon'
      });
    },

    // Params are rebuilt from the one named field, and only a value in
    // TOOL_NAMES is sent, so neither a stray attribute nor a caller can put
    // anything else on the wire.
    toolSubmitted: function (p) {
      var tool = p && p.tool;
      if (TOOL_NAMES.indexOf(tool) === -1) return;
      track('tool_submitted', { tool: tool });
    },

    // #1229. transport_type 'beacon' as ctaClick: the submit that follows is a
    // full navigation. Params rebuilt from the one named field; only en|hi sent.
    languageSwitched: function (p) {
      var to = p && p.to_lang;
      if (LANG_CODES.indexOf(to) === -1) return;
      track('language_switched', { to_lang: to, transport_type: 'beacon' });
    },

    // #1229. `login` is GA4's recommended event name. method is 'google' (the only
    // sign-in there is). Beacon transport: base.html reloads the page right after.
    login: function (p) {
      var method = p && p.method;
      if (method !== 'google') return;
      track('login', { method: method, transport_type: 'beacon' });
    },

    // #1229. `share` is GA4's recommended event name. Params rebuilt from the two
    // named fields and each checked against its list, so neither a stray
    // attribute nor a caller can put anything else on the wire.
    share: function (p) {
      var method = p && p.method, content = p && p.content_type;
      if (SHARE_METHODS.indexOf(method) === -1) return;
      if (SHARE_CONTENT.indexOf(content) === -1) return;
      track('share', { method: method, content_type: content });
    },

    // Manual pageview helper. GA4's auto-config sends the initial pageview;
    // call this on SPA-style nav (hx-boost swap) so subsequent pages also
    // register. Path defaults to the current URL.
    pageView: function (path) {
      if (window.gtag) {
        window.gtag('event', 'page_view', {
          page_path: path || location.pathname,
          page_location: gaLocation()
        });
      }
    },
  };
})();
