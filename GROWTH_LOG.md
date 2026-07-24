# Growth Log — Shubh Bhagya

The cadence journal for the growth-manager agent. Newest cycle at the top.

---

# Growth Cycle: 2026-07-24 — Baseline audit (first-ever cycle)

## Ran this cycle
- **seo-auditor** on 5 URLs (homepage + 4 top learn articles) → 9 GitHub issues created
- **keyword-researcher** on topic "career blockage astrology" → 5 content GitHub issues created

## Issues touched
- Created: 14 (well under 20-cap)
  - SEO: #5 (HIGH), #6, #7, #8, #9, #10, #11, #12, #13 (all MEDIUM)
  - Content: #14, #15, #16, #17, #18 (3 high-priority, 2 medium-priority)
- Closed: 0
- Top 3 to look at:
  - #5 — /learn/career-not-progressing title truncates in SERP (HIGH, most damaging to CTR)
  - #12 — Site-wide: zero outbound external links (E-E-A-T signal missing)
  - #13 — Site-wide: no visible "Last updated" date on articles (freshness signal)
- Open queue: 9 SEO, 5 content (14 total; label-taxonomy fresh — all labels created this cycle)

## Articles shipped this cycle
- None shipped by the growth-manager (this was an audit-only cycle)
- Note: 41 articles already exist in `src/astro_ai/templates/learn/`; many may not yet be deployed to prod per parent context

## Key observations

**What's working well (no action needed — worth preserving):**
- All 4 audited article pages carry rich JSON-LD: Article + BreadcrumbList + FAQPage + WebPage + Organization + WebSite + ImageObject. This is above-average structured-data coverage for the vertical.
- All pages have canonical links, single h1, viewport meta, OG + Twitter cards.
- Article word counts are strong: manglik-dosh 2207, sade-sati 2157, kundali-matching 2966, career-not-progressing 3314 — all comfortably in the 1500-3000 sweet spot.
- Heading hierarchy is clean (h1 → many h2s → h3s, no skips).
- Homepage schema includes Organization + WebSite + SearchAction (site-search structured data — nice).

**What's not working (turned into issues):**
- Titles are consistently 70-91 characters, well over Google's ~60-char SERP cap. This is the single highest-leverage fix — one template pass could improve CTR on all 42 articles.
- Meta descriptions run 173-296 characters — 50-140 chars past the ~160 SERP cap. Same story: template-level fix, sitewide payoff.
- No outbound external links anywhere. E-E-A-T signal is weaker than competitors'.
- No visible "Last updated" date in article prose (although JSON-LD carries datePublished — invisible to humans).
- Homepage h1 contains raw whitespace/newline that breaks preview extraction.

**Keyword research findings:**
- "Career blockage astrology" cluster has strong long-tail potential. The site already has a broad career-not-progressing pillar article — the 5 new content issues drill into specific configurations (Saturn-10, Rahu Mahadasha, debilitated Sun, 10th-lord-in-6th, career during sade sati) that our chart engine can uniquely surface.
- Every content issue includes cross-linking guidance to build a career topical cluster around the existing pillar.

## Suggested next cycle

- **Focus:** Audit-then-fix cycle (Week 1 of the rotation)
- **Rationale:** All 9 SEO issues are HIGH-leverage title/description template fixes plus 2 sitewide template changes. Doing another audit would produce redundant findings until these are cleared. Have content-drafter tackle the text rewrites (issues #5-#10 are all text-only, tagged `skill:content-drafter`); have human/manual tackle #11 (h1 template), #13 (last-updated template).
- **Deferred to a future research cycle:** competitor-scout run on top career-blockage queries before drafting the 5 new articles — helps set the outline benchmark.

## Blockers surfaced for human attention

1. **Deploy gap**: parent context notes "41 articles shipped to main, many not yet deployed to prod." The Cloud Run project `bhagya-500701` may be running older HTML. If any of the issues above touch content that's already been re-templated locally, verify against `main` before writing fixes.
2. **Label taxonomy created**: 16 new labels were created this cycle (`seo`, `content`, `severity:*`, `category:*`, `skill:*`, `priority:*`). Confirm these match your intent — if you want different names/colors, rename them once and future cycles will use the same set.
3. **Repo remote**: this repo (`mahAnuj/astro-ai`) has issue numbers starting at #5 for this cycle. #1-4 were consumed elsewhere (bot/label side-effects) and are not part of this cycle.

---
