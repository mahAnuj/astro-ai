# Templates declare analytics events as markup; analytics.js fires them

- **Date:** 2026-11-17
- **PR / issue:** #1067

## Why, measured

`analytics.js` loads with `defer` (`base.html`), so an inline top-level
`<script>Analytics.kundliGenerated(...)</script>` in a page body runs first and throws
`Analytics is not defined` on every full page load. `kundli_generated` (`result.html`),
`ask_answered` (`ask.html`) and `dasha_deep_dive_viewed` (`dasha_deep_dive.html`) all worked only
after an hx-boost swap. `dasha_deep_dive_viewed` was absent from all 16 event names in the
2026-10-16..2026-11-12 GA4 export; a lost event leaves no row, so the size of the loss for the
other two cannot be recovered.

Decision: a template calls the macro in `_analytics_event.html`, which renders
`<div hidden data-analytics-event=... data-analytics-params='...'>`; `analytics.js` scans for unfired
elements on DOMContentLoaded, on `htmx:afterSettle`, and once at load if the document is already past
`loading`, stamps each `data-analytics-fired` BEFORE tracking it, and keeps only scalar params.
Params go through `|tojson|forceescape`, never string interpolation into JS. A malformed payload
fires the event with no params (the conversion still counts, nothing unparsed leaves the page).

Rejected: wrapping each inline call in DOMContentLoaded (three more copies of the pattern, and an
inline `'{{ value }}'` in a JS string stays an injection shape); making `analytics.js` non-deferred
(blocks parsing for every page to fix three).

Guards: `tests/test_analytics_declared_events.py` fails on any template that calls `Analytics.*`
while the page parses; `scripts/verify_pii_egress.py` now reads declared events (the three events'
params would otherwise have left its `calls` surface unjudged). Tokens: 0, no LLM path.

Not fixed here: `base.html`'s own DOMContentLoaded calls on hx-boost (#1069) and re-fire on
revisit (#1068).
