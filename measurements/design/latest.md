# Design audit — shubhagya.com, 2026-10-09

**Revision audited:** `bhagya-00410-qxx`, `build_sha` 347473b0391a… (== `origin/main` HEAD, so the tree and the site agree).
**Method:** live site only. Headless Chrome 154 (puppeteer-core, installed outside the repo) at 375×667 touch/DPR 2 and 1280×800; screenshots plus DOM measurements. Real devices were **not** available.

**Skills.** `ui-auditor`, `mobile-flow-auditor` and `ui-designer` are not registered in this runner (not in the skill list, no `.claude/skills/`). I did their jobs by hand with the checks below rather than pretend a skill ran: overflow, tap targets, sub-12px text, computed contrast (colour composited on nearest opaque background), fixed-layer hit-testing, first-fold content, and a real form → result flow on mobile.

## Does it work? (checked first)

| Check | Result |
|---|---|
| `/`, `/kundli`, `/matching`, `/numerology` | 200, 0.5–0.9 s, 128–152 KB. `/learn` → 307 → `/learn/` (200), by design |
| `/health` | `{"ok":true,"revision":"bhagya-00410-qxx","build_sha":"347473b…"}` — **exact tier is live** |
| Stylesheet freshness (#253) | All five pages link `app.css?v=34ae1431`; live file is 85,460 B, **byte-identical** to the committed `app.css`; `cache-control: immutable` is safe because the URL is content-hashed. Not stale. |
| #266 (`/kundli` "high demand") | **Did not reproduce.** One POST `/reading` (Mumbai test chart): 200, 211 KB, 10.3 s cold, lagna/mahadasha present, no "high demand". A second run from a real mobile flow took 5.6 s. One sample; the issue is still OPEN with last activity 2026-09-05 — Engineering/infra should decide whether to close it, not Design. |
| `/numerology` POST, `/matching` POST | Both rendered full results at 375 px, no horizontal overflow, no ellipsis-clipped text |
| Horizontal overflow, all 5 pages × 2 viewports | None (`scrollWidth == viewport`) |
| JS page errors / 4xx on first-party requests | None. The only failed requests were Google Analytics beacons, blocked by the sandbox, not a site defect |

No Engineering-class bug found, so nothing was filed to the wrong team.

**Sample-size caveat that applies to every metric below.** `measurements/latest.md` (2026-09-08 → 2026-10-05): 254 GA4 sessions in 28 days, 620 GSC impressions, 9 clicks. `/kundli` and `/matching` had **1 landing session each**; 176 sessions (69%) land on `/learn/*`; `/` has 56 sessions at 14.3% bounce and 5.39 pages/session. No funnel or CTR experiment on these pages can reach significance in one window, so wherever I could, I defined the success metric as a **deterministic scripted check** and listed the outcome metric as directional only.

## `/` (home)

**Saw.** The mobile hero puts the four-field birth form before the H1 (form is fully in the first fold, submit button at y=490–538 of 667). Headline, sample chart, trust chips, fear-reframing cards, Gita quote all render cleanly. No overflow. Contrast: no failures found, but elements over the dark gradient hero were skipped by my script, so the hero is **unmeasured**. 26 text nodes under 12 px (Rahu Kaal strip labels at 10 px, stat labels at 11 px).
**Filed.**
- #310 (design-proposal) — install banner covers the lower half of the submit button on the first fold.
- #307 (ui-fixer) — sub-12px text, home is a contributor.
**Considered and rejected.**
- *Reorder hero so H1 precedes the form on mobile.* The page converts: 5.39 pages/session, 14.3% bounce on 56 sessions. A number to beat does not exist in the direction of "worse", and #242 is the redesign precedent for not touching it blind.
- *Autofocus on the Name field.* Present, but on `/` it causes no scroll (scrollY=0). Left alone; see `/kundli`.
- *"See your free Kundli →" link measured 168×30 px and the hero trust links 16 px tall.* Below 44 px but not clearly harmful; left out to avoid noise.

## `/kundli`

**Saw.** Landing at 375 px: the page opens already scrolled 44 px, so the first line of the H1 ("Free Vedic Janma Kundli…") is cut by the sticky header; the form starts at y=482 and its submit at y=1031 (1.5 screens down). The full flow works: form → "Casting your chart…" overlay → result in 5.6 s. On the result, the first screen shows Lagna / Moon / Sun tiles — and they clip.
**Filed.**
- #306 (ui-fixer) — autofocus scrolls the page 44 px and clips the H1. Confirmed by stripping `autofocus` from the live document: scrollY 44 → 0, h1.top 57 → 101 (header bottom 69). Notes that #67 added it deliberately and that its "keyboard opens" premise was unmeasured.
- #305 (ui-fixer) — **10 of 12 rashi names clip** in the Lagna tile at 375 px (`truncate` at `result.html:169,173`); the test chart shows "Cancer (Ka…", "Sagittarius …", "Taurus (Vri…". Hindi not measured.
- #309 / #310 — modal and install banner both stack over this page on repeat visits.
**Considered and rejected.**
- *Shrink the 7-line intro so the form is in the fold on mobile.* Probably right, but `/kundli` has 1 landing session in 28 days — there is no CTR or funnel to beat, and the intro is keyword text for the page title. Not filed. If `/kundli` starts to receive landings, revisit.
- *Add a sample chart beside the form.* Prokerala does this (below the form, see rivals). Same reason: no number to beat.

## `/matching`

**Saw.** Clean two-card form (groom/bride), correct focus ring, no overflow, no sub-44 px controls of note. Result at 375 px: score ring 27.0/36, verdict pill, dosha cards and cancellation lists all readable. The feedback FAB overlaps copy (see #308) and the right end of the verdict pill on first view. The long-ish PDF/info icon row fine.
**Filed.** #308 (FAB over text), #309 (modal on the second tool page), #310 (install banner covers the left of the "Calculate Guna Milan" button on desktop).
**Considered and rejected.**
- *Girl-first ordering, as Prokerala has it.* A cultural-default question for the astrologers, not a design finding.
- *Add a Kerala/Tamil "system" selector (Prokerala).* That is a product feature with its own correctness burden, route it to product-manager if wanted.

## `/numerology`

**Saw.** Honest tradition disclaimer in a yellow note directly under the nav, then H1 and a long lead paragraph; the form's CTA is at y=769 (below the fold). On a second tool page the subscribe modal appeared over the page within 2.5 s. The result page (Bhagya score 58/100 ring, Chaldean) renders well with no clipping.
**Filed.** #309 (modal over an empty form — reproduced here), #308.
**Considered and rejected.**
- *Add a worked example above the form (AstroSage's page leads with a Virat Kohli name-reduction example).* AstroSage's page is an article with a "Get Horoscope" form, not a calculator, and I could not see its layout or conversion. Our page already has the honest-tradition note they lack. No number to beat.

## `/learn` (index) and the article landing it feeds

**Saw.** Index: 76 cards, 34,644 px tall on mobile; search and category chips work; 234 text nodes under 12 px, chip counts at 4.21:1. The index itself is not a GA4 landing page. The **articles** are where traffic is, so I measured the top landing `/learn/rahu-mahadasha-ketu-antardasha/` on mobile: first `/kundli` link at y=6211 of 10124 px, and the sticky "Check your own chart" bar that should catch readers earlier is **hidden under the tab bar**: bar box 598–667 px, tab bar 592–667 px, `elementFromPoint` at the bar's centre returns a tab label. This is the highest-value finding of the run.
**Filed.**
- #304 (ui-fixer) — sticky Kundli CTA is invisible and untappable on mobile. Number to beat: 69% of sessions land on `/learn/*`, 71% of those sit in rows at exactly 1.00 pages/session, 1.38 session-weighted.
- #307 (ui-fixer) — sub-12px text and 4.21:1 chip counts.
- Comment on #276 (inline CTA position) cross-linking #304, since fixing the sticky bar is a prerequisite to reading any result from moving the inline CTA.
**Considered and rejected.**
- *Paginate or lazy-load the 76-card index on mobile.* The index is not a landing and has no CTR to beat. Not filed.
- *Redesign the article page.* Never proposed. #244's instinct again, and the article already ranks.

## Rivals (all fetched; what was and was not retrievable)

Fetched successfully: `https://www.prokerala.com/astrology/kundli/`, `https://www.prokerala.com/astrology/kundali-matching/`, `https://www.astrosage.com/numerology/`, `https://www.astrosage.com/free/`, `https://www.astrosage.com/`. Failed (404 — I guessed the URL, discard): `astrosage.com/free/kundli.asp`, `prokerala.com/astrology/numerology/`, `prokerala.com/astrology/numerology/…`. `costarastrology.com` returned only a page title, so **no claim about Co–Star is made**. WebFetch returns text, not rendering, so everything below is about structure and copy, not visual polish.

| What they do | Where | Do we do it better? |
|---|---|---|
| Kundli form: Name, Gender, **Year/Month/Day dropdowns**, **12-hour Hour/Minute/AM-PM dropdowns**, free-text place, language | prokerala.com/astrology/kundli/ | We are ahead: native date/time inputs, four fields, no gender, no language pick. |
| Static sample chart and a "Details in Kundli" 12-house list **below the form** | same | Their one structural advantage. Ours has no sample output on `/kundli` itself (the home has one). Considered, **not filed** (no number to beat on `/kundli`). |
| Matching: "Choose System" (Kerala / Tamil / Guna Milan), girl's details first, notes that results follow the ashta-kuta rules and are "not based on any published almanac" | prokerala.com/astrology/kundali-matching/ | A feature/content question (South Indian Porutham) → product, not design. Their no-almanac note is a similar honesty move to ours. |
| Home first screen puts a Kundli form **and** a Matching form, "Advanced Settings" (lat/long, time zone, DST, ayanamsa, chart style, KP horary number), ~24 paid AI-astrologer cards at ₹11–35/min, wallet in header, sign-in dialog, chat pop-ups | astrosage.com | We have one CTA, no wallet, no per-minute pricing. Advanced Settings is a power-user feature worth product-manager's attention, not a UI defect here. |
| `/free/` hub: ~20 tools in three **unlabelled groups** that each restart numbering at 1, mixed with paid upsells | astrosage.com/free/ | Ours is clearer. |
| Numerology: no calculator, an article with celebrity worked examples, **no stated limits of the practice**, paid upsells, "First Call/Chat FREE" popup | astrosage.com/numerology/ | Ours leads with the tradition caveat; better. |

**Honest summary:** on structure and honesty we are ahead of both fetched rivals; the sub-12px text, covered CTAs and clipped tiles above are where we lose to *ourselves*, not to a competitor. I cannot say anything about their mobile performance or conversion.

## Issues filed (7) and one comment

| # | Title | Labels | Page |
|---|---|---|---|
| 304 | `/learn` articles: sticky Kundli CTA renders under the tab bar | ui, skill:ui-fixer | `/learn/*` mobile |
| 305 | `/kundli` result: tiles clip 10 of 12 rashi names at 375px | ui, skill:ui-fixer | `/kundli` result |
| 306 | `/kundli`: autofocus scrolls 44 px and clips the H1 | ui, skill:ui-fixer | `/kundli` mobile |
| 307 | Sub-12px text: 10px tab-bar labels, 234 nodes on `/learn`, chip counts 4.21:1 | ui, skill:ui-fixer | every page / `/learn` |
| 308 | Mobile feedback FAB sits on reading text | ui, design-proposal | result and form pages |
| 309 | Subscribe modal fires over the empty form on the 2nd tool page | ui, design-proposal | `/numerology`, others |
| 310 | PWA install banner covers the primary CTA on the first fold | ui, design-proposal | all pages |
| comment on #276 | cross-link to #304 | — | `/learn` article |

## What I could not verify

- **Real-device behaviour.** All mobile measurements are Chrome 154 emulation. Whether `autofocus` opens the soft keyboard on Android/iOS (#306), and how often the install banner shows on a first load (#310), are unverified; the issues say so.
- **Contrast of text over gradient or image backgrounds** (home hero) — skipped by the script.
- **Hindi** layouts — not measured; Hindi rashi names are likely wider than English, so #305's 10/12 is a floor, not a ceiling.
- **Any baseline for feedback submissions, install rate, or subscribe-per-modal.** The event log was not queried; #308, #309, #310 each name the baseline to pull before changing anything.
- **#266.** One successful POST is one sample, not proof the Groq ceiling is gone.
- Side effects of this audit on production: three `POST /reading` for the same test chart (LLM-backed; the later two returned in ~5.6 s, probably cached), one `POST /numerology`, one `POST /matching`. Nothing was subscribed, signed in, or submitted to `/feedback`.
