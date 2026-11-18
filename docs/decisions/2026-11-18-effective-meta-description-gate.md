# The meta-description gate measures the EFFECTIVE description of every crawled page, and 54 over-length pages are shortened

- **Date:** 2026-11-18
- **PR / issue:** #1178 (follows #463)

## Why, measured

`scripts/verify_seo_copy.py` (#463) read `seo_description` only. `learn_article_base.html`
renders `{{ article.seo_description or article.summary }}`, so the 38 articles with an empty
`seo_description` served a 210-330 character `summary`, and every template block, `base.html`
default and route-built `page_meta` string was never measured at all.

Crawling `/sitemap.xml` in-process (TestClient, `/rashifal/*` skipped, `html.unescape` length)
on main @ 153821c: **54 of 202 pages over 160 decoded characters**. 38 /learn articles, `/` (309),
/muhurat (497), the five /muhurat/<event> landings (271-361), /kundli (255), /dasha (221),
/panchang and today's dated URL (236), /numerology (406), /numerology/compatibility (189),
/kaal-sarp-check (256), /about (194), /terms (168). After: 0 of 202, longest 160 or under, nearly
all 156 or under.

`rashifal_single_meta` is behind an LLM route, so the crawl never saw it: **EN 190, HI 172** at
its longest (12 rashis x 365 dates). Now **EN 157, HI 155**.

## What changed

- The 38 articles gain an explicit `seo_description` (the `summary` is untouched: cards use it).
- The page descriptions above are shortened, not rewritten: trailing and redundant words
  dropped, no claim added. `/muhurat`'s keeps the B.V. Raman attribution it already made and
  no longer mentions the conventions it labelled as its own (#1024) because it no longer lists
  those rules at all.
- The gate now has four parts: article ceiling on the effective value (floor still on a SET value
  only), the rendered `<meta>` of every sitemap page in-process, the Rashifal i18n key for EN and
  HI, and a refusal to pass vacuously (zero pages, non-200, no description meta, no dated Panchang).
- `tests/english_surface_baseline.json`: 12 `meta_description` entries edited in place. Not
  re-captured: `--capture` drops the file's hand-written `_hreflang_note` and `_coverage_note`.

## Rejected

- Raising the ceiling. 160 is what a SERP renders.
- Checking `seo_description` and `summary` separately in the registry only: it cannot see a
  template string, a `page_meta` built in a route, or `dated_description`.
- Rendering all 90 sitemap Panchang dates: each is an ephemeris run and all take the one
  `dated_description` path, so one future date is enough.

Tokens: 0. No LLM call, prompt or Groq budget is touched.
