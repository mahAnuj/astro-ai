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

  // ── Public surface ───────────────────────────────────────────────────
  window.Analytics = {
    track: track,
    kundliGenerated:    function (p) { track('kundli_generated',     p); },
    subscribeCompleted: function (p) { track('subscribe_completed',  p); },
    languageSwitched:   function (p) { track('language_switched',    p); },
    pwaInstalled:       function ( ) { track('pwa_installed');           },
    feedbackSent:       function (p) { track('feedback_sent',        p); },
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
