# Footer and body CTAs link a no-chart visitor to /?needs_chart=<key> through one `chart_href` global; the navs keep their inline rewrite

- **Date:** 2026-11-27
- **PR / issue:** #1546 (residual of #1107 criterion 4; extends #1177)

## Why, measured

`/today`, `/monthly`, `/yearly` and `/ask` answer `303 -> /?needs_chart=<key>` for a visitor
with no saved chart. #1177 fixed `_nav.html` and `_tab_bar.html`; the footer Readings group,
the homepage feature cards and the `/ask` CTAs in /learn still linked the four URLs. Redirecting
internal hrefs on `/`, `/kundli`, `/panchang`, `/muhurat` and `/learn/sade-sati/` for a no-chart
request: 7+3+3+3+4 = 20 before, 0 after (parsed `<a href>` values, not substring counts).

`routes/deps.py` gains `_CHART_GATED` (path -> key) and `_chart_href(request, path)`, registered
as the `chart_href` template global. It reuses `_has_chart`, so there is no storage read and no
LLM call. Measured: 11 calls (the count on `/`) take about 41 us with no cookie and about 0.68 ms
with a valid session cookie (one signed-cookie decode per call). Both pages are
`Cache-Control: private`, so a per-visitor href cannot leak through a shared cache.

corpus: n/a -- link targets only; the twelve /learn article bodies change an `href` attribute and no prose, so no astrological claim is added or altered.

## Rejected

- **Refactoring `_nav.html` and `_tab_bar.html` onto the helper.** They already carry their own
  inline rewrite (#1177) with an active-tab derivation that reads the direct path; moving them
  widens a one-link-class fix into a nav rewrite with its own test (`tests/test_nav_nochart_no_redirect.py`).
  Left as is; a later change can fold them in.
- **Rewriting `/dasha` and `/card`.** Both also 303 with `needs_chart`, but the issue names four
  URLs and the footer links `/dasha` directly; that is a separate residual, not widened here.
- **A route-level fix (answer 200 at the four URLs).** Changes the product behaviour the
  redirects encode; this issue is only about what the links point at.
