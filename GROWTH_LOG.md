# Growth Log — Shubh Bhagya

The cadence journal for the growth-manager agent. Newest cycle at the top.

---

# Growth Cycle: 2026-07-24 — Cycle 2 (QA fixes + Life-Questions career cluster)

## Ran this cycle

**Phase A — QA fixes (3 issues cleared):**
- #19 sade-sati: Registry FAQ misnamed first phase as "Anu"; corrected to classical "Arambha" (ecae248)
- #21 career-not-progressing: Single 15° combustion orb (Saturn-only) replaced with planet-specific orbs Venus 10° / Jupiter 11° / Moon 12° / Mercury 14° / Saturn 15° / Mars 17° (699093e)
- #20 kundali-matching: Bhakoot rules were self-contradictory (5-9 in both favourable and dosha lists). Removed erroneous entry, added named classical dosha labels (Dwir-Dwadasha / Navama-Pancama / Shadashtaka) and Rashi-Rashish maitri cancellation note (2b06459)

**Phase B — Content articles (3 issues cleared, 3 new articles shipped):**
- #18 career-during-sade-sati (2443 words, 6 FAQs, 2a0dcae) — Life Questions article covering Sade Sati career arc across Arambha/Madhya/Uttara, when to change jobs, "just laid off" section, promotion-during-Sade-Sati honest treatment. All 8 article-qa checks: PASS.
- #16 debilitated-sun-career (2377 words, 6 FAQs, be6dfe4) — Sun in Libra career pattern: the negotiation-forward leader, house-by-house effects, the four classical Neecha Bhanga cancellation rules most explanations miss. All 8 checks: PASS.
- #17 10th-lord-in-6th-house-career (2740 words, 6 FAQs, 45db6dd) — Career-through-struggle placement with per-ascendant flavours for all 12 ascendants, Vipareeta Raja Yoga context, Dasha activation windows. All 8 checks: PASS. Slightly exceeds 2500-word target — the ascendant map justifies the length.

**Phase C — Systemic link fix (1 issue cleared):**
- #22 6 articles at zero inline /learn/ links → each now carries 3-5 contextual inline links added in natural anchor positions inside existing prose. Articles fixed: manglik-dosh (3), pitru-dosh (5), kaal-sarp-dosh (3), gajakesari-yoga (4), panch-mahapurush-yoga (5), jupiter-remedies (5). (b98e204)

**Phase D — E-E-A-T outbound links (#12):** Deferred to next cycle per plan.

## Issues touched

- **Closed: 7** (#19, #20, #21 QA-accuracy; #18, #16, #17 content; #22 systemic-links)
- **Created: 0** (all planned work delegated within existing backlog)
- **Open queue: 13** (1 SEO, 0 content, 12 QA including 3 unbriefed #23-25 and 9 newer #26-34)

Top 3 remaining to look at next cycle:
- #12 site-wide outbound external links (last SEO fix; deferred here)
- #23-34 the 12 medium-severity QA issues (bulk cluster — a dedicated QA-fixes cycle would clear most in one pass)
- New content: no content backlog; time for a keyword-researcher run on a fresh topic

## Articles shipped this cycle

- career-during-sade-sati
- debilitated-sun-career
- 10th-lord-in-6th-house-career

**Total article count now: 46 files under templates/learn/** (from 43 at start of cycle).

## Key observations

**What worked well:**
- The three career-cluster articles all landed comfortably in the 2400-2740 word range with clean cross-linking. The 12-ascendant map in the 10th-lord-in-6th article is a strong diagnostic engagement hook.
- Phase A fixes were small, factual, unambiguous — 3 issues cleared in ~5 minutes of edits. QA-accuracy fixes are excellent low-friction throughput.
- The Phase C link fix batch (6 articles) was high-ROI: single commit, cleared one HIGH-severity systemic issue, boosted topic-cluster internal linking sitewide.

**What didn't:**
- Push to origin/main is blocked by permissions in this environment — 7 commits are local. Closed issues manually with commit references and a "pending push" note. This blocks GitHub's auto-close-via-commit-message and leaves the paper trail on the close comment instead.
- Task tool for delegating to content-drafter/article-qa subagents is not available in this subagent context. Wrote both roles inline: content-drafter for the 3 articles, article-qa self-review with all 8 checks before commit. Results appear equivalent but harder to audit externally.
- The parent's brief listed 4 QA issues (#19-22). Post-cycle-1 the article-qa audit had actually surfaced 12 QA issues total (#23-34 all opened 2026-07-24 shortly after #19-22). Only the briefed 4 were addressed this cycle; the other 9 remain open as `qa` label backlog for next cycle.

**Backlog composition after Cycle 2:**
- SEO: 1 open (#12 outbound external links)
- Content: 0 open
- QA: 12 open (all severity:medium; heavy skill:content-drafter tag; cluster around voice/engagement/links checks)

## Suggested next cycle (Cycle 3)

- **Focus: QA-fixes volume cycle.** The 12 open QA issues are all medium-severity, all fixable via prose editing, and clustered enough to batch efficiently. A dedicated QA-fixes cycle can plausibly clear 6-10 of them.
- **Rationale:** Zero content backlog + 12 open QA + 1 SEO backlog. Doing another content-drafter run without clearing QA first would compound the QA debt. Clearing QA also protects the quality of the newly shipped articles.
- **Also this cycle:** run keyword-researcher on a fresh topic (children in astrology / muhurat / gochar effects were the parent-suggested rotation candidates) to refill the content pipeline before it goes empty.
- **Also this cycle:** #12 outbound external links — this is a template-level fix (add 2-3 authoritative external links per article), doable in a batch.

## Blockers surfaced for human attention

1. **7 commits pending push to origin/main.** Local commits: ecae248, 699093e, 2b06459, 2a0dcae, be6dfe4, 45db6dd, b98e204. All are on main. Push was blocked in this session; someone with push access needs to `git push origin main` for the articles to actually deploy and for GitHub's auto-close-via-commit-message to fire. Issues are already closed via manual `gh issue close` with commit references, so backlog state is accurate — but the site itself will not show the changes until push lands.
2. **Skill / Task tool unavailable in subagent context.** This subagent could not invoke the `content-drafter` or `article-qa` skills via the Skill tool (they were not in the available-skills list), and did not have Task tool access to spawn general-purpose subagents. All content-drafter and article-qa work was executed inline. If the parent wants true delegation with independent QA runs, that needs to happen from a context that has Task/Skill access to those specific skills.
3. **Article-qa audit created 12 QA issues (#23-34)** during or after the previous cycle. Only the briefed 4 were addressed here; the other 9 remain open. Recommend either explicitly scheduling a QA-fixes-only cycle or having article-qa self-limit issue creation per audit to a smaller batch.

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
