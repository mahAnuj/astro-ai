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
 * One shared IntersectionObserver handles every reveal on the page —
 * cheap regardless of how many revealable elements exist. Elements are
 * observed once, then unobserved after they've been revealed (no
 * reverse animation when scrolling back up — that would feel busy).
 *
 * Above-fold elements are revealed immediately on load (IntersectionObserver
 * fires synchronously on init for elements already in view), so users
 * with fast connections don't see a flash of hidden content.
 *
 * prefers-reduced-motion is handled in base.html CSS — the [data-reveal]
 * rule is overridden to opacity:1 / transform:none for those users, so
 * this script's behaviour becomes visually inert (content appears
 * instantly) but still marks elements visible for consistency.
 */
(function () {
  var els = document.querySelectorAll('[data-reveal]');
  if (!els.length) return;
  if (!('IntersectionObserver' in window)) {
    // Fallback for ancient browsers: just show everything.
    els.forEach(function (el) { el.classList.add('reveal-visible'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var el = entry.target;
      var delay = parseInt(el.getAttribute('data-reveal-delay') || '0', 10);
      if (delay > 0) {
        el.style.transitionDelay = delay + 'ms';
      }
      el.classList.add('reveal-visible');
      observer.unobserve(el);
    });
  }, {
    // Reveal a touch before the element hits the viewport bottom, so the
    // animation completes at roughly the moment it's fully readable.
    rootMargin: '0px 0px -40px 0px',
    threshold: 0.05,
  });

  els.forEach(function (el) { observer.observe(el); });
})();
