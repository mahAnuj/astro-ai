# Clarity session replay is masked on every page, unconditionally

- **Date:** 2026-11-12
- **PR / issue:** #908

## Why, measured

`base.html` loads Microsoft Clarity on every page when `CLARITY_PROJECT_ID` is set, and
`grep data-clarity` over the templates returned nothing, so a replay captured `/kundli`,
`/ask`, `/matching` and `/numerology` as on-screen text: the birth details and the question.
`/privacy` said nothing about session replay.

**Chosen: `<body data-clarity-mask="True">` on every page, a constant, no allowlist.**

The first version masked by default and exempted `/learn`, `/about`, `/privacy`, `/terms` and
`/festivals`. QA round 1 failed it on a defect the server cannot see: `<body hx-boost="true">`
means htmx swaps the body's CHILDREN and discards the response's `<body>` attributes (htmx 2.0.4
`makeFragment` / `takeChildrenFor`). A visitor who lands on a `/learn` article (the SEO entry
point, so the common first page) arrives with an UNMASKED body, clicks through to `/kundli` or
`/ask`, and the live body keeps the attribute it was loaded with: the birth details were recorded
as text. Demonstrated in jsdom against htmx 2.0.4 (`/learn/` -> boosted click -> `/kundli` left the
body attribute null while `curl /kundli` rendered `True`). An attribute that varies by path is
stale across exactly the navigation the site is built around.

A constant cannot go stale: every full page load of any path sets the same value, so whichever
page the visitor entered on, the live body carries it. That is why the allowlist is dropped
instead of patched (for example by re-applying the attribute on `htmx:afterSwap`, which is new JS
whose failure is silent and leaks personal text).

**The cost, stated plainly.** Session replay of the public `/learn` pages now shows layout, clicks
and scroll but no text. Heatmaps and click and scroll data are unaffected, because masking blanks
text and not events. Whoever wants readable replay on public pages gets it back by re-introducing
an allowlist, and that change needs a BROWSER-level test of the boost path (load `/learn/`, click a
boosted link to a personal page, read the live `document.body` attribute), the way
`scripts/verify_lang_switch_browser.py` handles the same stale-outer-attribute class for
`<html lang>` (`ARCHITECTURE.md` decision-log row 2026-10-05, the language control). `TestClient`
cannot run htmx, so a server-side test cannot see it; the first version had all of its tests green.

**The signed-in chip's own mask came off.** `_nav.html` rendered the first name under its own
`data-clarity-mask`. A body-wide mask covers that element identically (it is a descendant), so the
second attribute only added a place for the two to drift apart. The chip's `title` attribute (the
signed-in email) is not shown to be masked by either; see `ARCHITECTURE.md` section 11.

**Two disclosures, one log fix.** `privacy.html` states the session replay (only when Clarity is
configured: text is masked on every page; clicks, scrolling and layout may still be recorded) and
what the request log holds. The access log records page addresses, so it holds: `/ask?q=<question>`
(`POST /ask` answers with a 303 to `/ask?q=<question>&c=...`, so every question is in the URL of
its answer page, not only a hand-typed one), and `/panchang?city=<city>` (and
`/panchang/<date>?city=`), because the Panchang page's place box is a `method="get"` form
pre-filled with the saved birth place (`routes/panchang.py`), so submitting it, unedited or not,
puts that place in the URL. Enumerated by grep: `method="get"` forms in the templates are the
Panchang place box and an admin day picker (no personal data); every other place field
(`/kundli`, `/matching`, `/muhurat`, `/dosha`, `/subscribe`) is a POST form. Not verified: that the
production host's request log is retained as long as the page says.

The panchang strip's failure warning logged the saved birth place into the APPLICATION log, which
`verify_pii_egress` never reached; it now logs the length, the chained traceback is cut, and a
sweep scenario (`strip-place-unresolved`) fails on either line. So the claim is exactly this: no
`astro_ai` logger line holds a birth place, while the request log still holds a typed or pre-filled
city on `/panchang`, and the privacy page says so. (An earlier draft of this note said "no log path
holds a birth place"; that was false for the request log.)

Tokens: 0. No LLM path, prompt or cache key touched.
