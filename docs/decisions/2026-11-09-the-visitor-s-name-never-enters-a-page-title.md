# The visitor's name never enters a page `<title>`

- **Date:** 2026-11-09
- **PR / issue:** #817

## Why, measured

The #744 PII sweep found, on its first run, that the server-rendered `<title>` of eight
routes carried the visitor's name (`/kundli`, `/monthly`, `/yearly`, `/manglik-check`,
`/sade-sati-check`, `/kaal-sarp-check`, `/numerology`, `/numerology/compatibility`).
`static/analytics.js` sets no `page_title`, so gtag collects `document.title`, and
`privacy.html` says analytics carry no birth details. `base.html` also copies the title into
`og:title` and `twitter:title`.

`chief` ruled option B on #817: render the name-free title everywhere rather than override
`page_title` in `analytics.js`. Option B also keeps the name out of tab titles, bookmarks and
social cards, not only GA4. The three i18n pages use their existing `*_anon` keys (so `lang=hi`
is covered), the dosha pages a fixed English string, the numerology pages Life Path and score.
The numerology meta description / `og:description` carried the name too and was made name-free
in the same change. The visible h1 still names the visitor.

`KNOWN_GAPS` in `scripts/verify_pii_egress.py` is now empty; a reappearing leak fails.
0 LLM tokens. No Tailwind class changed.
