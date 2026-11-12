# Clarity session replay is masked by default; only public-content paths are exempt

- **Date:** 2026-11-12
- **PR / issue:** #908

## Why, measured

`base.html` loads Microsoft Clarity on every page when `CLARITY_PROJECT_ID` is set, and
`grep data-clarity` over the templates returned nothing, so a replay captured `/kundli`,
`/ask`, `/matching` and `/numerology` as on-screen text: the birth details and the question.
`/privacy` said nothing about session replay.

**Chosen: default MASK, allowlist the exceptions.** `<body>` carries `data-clarity-mask="True"`
unless the path is `/learn`, `/about`, `/privacy`, `/terms` or `/festivals` (or beneath one,
matched as a segment so `/learnx` stays masked). Rejected: a mask LIST of the personal routes.
It fails open, so the next route someone adds is recorded until they remember, which is the
shape this repo keeps paying for. The allowlist fails closed. The cost is replay of those five
public trees stays readable, which is the point of keeping it.

**The signed-in chip is masked separately.** `_nav.html` renders the visitor's first name (and
their email in a `title`) on every page, `/learn` included, so the allowlist alone would have let
a replay read it. Rejected: masking the whole body on any signed-in request, which would blank
the public pages for exactly the visitors whose behaviour on them is worth seeing. One attribute
on the chip is the smaller correct change. The `title` attribute is not shown to be masked; see
`ARCHITECTURE.md` section 11.

`/hi/...` reaches the template with the prefix intact (`routes/hindi.py` awaits the English
handler and leaves `request.url.path` alone), so Hindi rashifal is masked and every other
`/hi/` path 301s to an allowlisted English URL.

**Two disclosures, one log fix.** `privacy.html` states the session replay (only when Clarity is
configured) and that the request log holds `/ask?q=...`: `POST /ask` answers with a 303 to
`/ask?q=<question>&c=...`, so every question is in the URL of its answer page, not only a
hand-typed one. And the panchang strip's failure warning logged the saved birth place, which
`verify_pii_egress` never reached; it now logs the length, the chained traceback is cut, and a
sweep scenario (`strip-place-unresolved`) fails on either line. With no log path left that holds
a birth place, the "place name" clause came off the page rather than being narrowed.

Tokens: 0. No LLM path, prompt or cache key touched.
