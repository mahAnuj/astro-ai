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
 *   .subscribeCompleted({lang})    — subscribed to daily Rashifal
 *   .languageSwitched({lang})      — clicked English/Hindi
 *   .pwaInstalled()                — accepted the PWA install prompt
 *   .feedbackSent({type})          — submitted the feedback form
 *   .pageView(path)                — manual pageview (use for SPA nav)
 *   .ctaClick({from_path,to_path}) — a /learn reader followed an in-article link
 *                                    to a tool; links in nav/header/footer never
 *                                    count (fired by the delegated listener
 *                                    below, not by templates — see TOOL_ROOTS)
 *
 * Add a new event by adding a method here — keep templates dumb.
 */
(function () {
  var cfg = window.BHAGYA_ANALYTICS_CONFIG || {};

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
    window.gtag('config', cfg.ga4, { anonymize_ip: true });
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
    '/sade-sati-check', '/kaal-sarp-check', '/numerology', '/muhurat'
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
  document.addEventListener('click', function (e) {
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
  });

  // ── Public surface ───────────────────────────────────────────────────
  window.Analytics = {
    track: track,
    kundliGenerated:    function (p) { track('kundli_generated',     p); },
    subscribeCompleted: function (p) { track('subscribe_completed',  p); },
    languageSwitched:   function (p) { track('language_switched',    p); },
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

    // Manual pageview helper. GA4's auto-config sends the initial pageview;
    // call this on SPA-style nav (hx-boost swap) so subsequent pages also
    // register. Path defaults to the current URL.
    pageView: function (path) {
      if (window.gtag) {
        window.gtag('event', 'page_view', { page_path: path || location.pathname });
      }
    },
  };
})();
