/* Scroll-reveal helper — used sitewide via [data-reveal].
 *
 * Any element with `data-reveal` starts hidden (base CSS in base.html
 * gives it opacity:0 + translateY(8px)). When the element scrolls into
 * view, this script adds `.reveal-visible` and the CSS transitions the
 * element into place.
 *
 * Optional attributes:
 *   data-reveal-delay="120"   — ms of transition-delay for stagger
 *
 * HTMX + boost compatibility:
 *   The site uses hx-boost, which swaps <body> without re-running <head>
 *   scripts. We therefore listen to `htmx:load` (fires on initial page
 *   load AND after every boosted navigation) and re-scan for any
 *   [data-reveal] element we haven't observed yet. A `data-reveal-init`
 *   marker prevents double-observing.
 *
 * Safety net: after DOMContentLoaded + a short grace period, any
 * [data-reveal] element that is above the fold but hasn't been revealed
 * (e.g. IntersectionObserver never fired for some browser quirk) is
 * force-revealed. Prevents ghost-content bugs from ever reaching users.
 *
 * prefers-reduced-motion is handled in base.html CSS — the [data-reveal]
 * rule is overridden to opacity:1 / transform:none for those users, so
 * this script's behaviour becomes visually inert (content appears
 * instantly) but still marks elements visible for consistency.
 */
(function () {
  var observer = null;

  function ensureObserver() {
    if (observer) return observer;
    if (!('IntersectionObserver' in window)) return null;
    observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        var delay = parseInt(el.getAttribute('data-reveal-delay') || '0', 10);
        if (delay > 0) el.style.transitionDelay = delay + 'ms';
        // Double-rAF: guarantee the browser paints the initial hidden state
        // for at least one frame before we flip the class, so the CSS
        // transition actually plays. Without this, above-fold elements can
        // skip the animation and pop straight into place.
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            el.classList.add('reveal-visible');
          });
        });
        observer.unobserve(el);
      });
    }, {
      // Reveal a touch before the element hits the viewport bottom, so the
      // animation completes at roughly the moment it's fully readable.
      rootMargin: '0px 0px -40px 0px',
      threshold: 0.01,
    });
    return observer;
  }

  function scan() {
    var els = document.querySelectorAll('[data-reveal]:not([data-reveal-init])');
    if (!els.length) return;
    var obs = ensureObserver();
    els.forEach(function (el) {
      el.setAttribute('data-reveal-init', '1');
      if (!obs) {
        // Ancient browser without IO — just show everything.
        el.classList.add('reveal-visible');
        return;
      }
      obs.observe(el);
    });
  }

  // Safety net: after a short grace period, force-reveal any element that
  // is inside or above the viewport but somehow hasn't been revealed.
  // Guards against browser bugs, extensions blocking IO, or elements
  // observed during a body swap that missed the callback.
  function safetyNet() {
    var vh = window.innerHeight || document.documentElement.clientHeight;
    document.querySelectorAll('[data-reveal]:not(.reveal-visible)').forEach(function (el) {
      var rect = el.getBoundingClientRect();
      if (rect.top < vh) el.classList.add('reveal-visible');
    });
  }

  function init() {
    scan();
    // Two safety-net passes: one quick (catch immediate render), one after
    // fonts/images settle (catch layout shifts that moved elements into view).
    setTimeout(safetyNet, 250);
    setTimeout(safetyNet, 1200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // htmx:load fires on initial page load AND after every boosted swap.
  // Using it as the single source of truth for "new DOM is ready".
  document.body && document.body.addEventListener('htmx:load', init);
  // If body wasn't ready when we ran (extremely unlikely with defer), bind on DCL.
  if (!document.body) {
    document.addEventListener('DOMContentLoaded', function () {
      document.body.addEventListener('htmx:load', init);
    });
  }
})();
