# Design audit — shubhagya.com, 2026-11-06

**Filed: 3 new issues (#731, #732, #733) and 3 re-verification comments (#379, #597, #382).** #733 is a process defect, deliberately *not* tagged `ui`. All three new issues and all three commented issues now pass `scripts/verify_issue_evidence.py`.

**Revision audited:** `/health` → `{"revision":"bhagya-00583-fzl","build_sha":"6ab25f95d564f7d52a4e56fb5cf5e1aca16e333b"}`. Local HEAD is `6ab25f9`, so **the live SHA equals `origin/main` HEAD** (exact tier, not "a revision changed").

**Method.** Live site only. System Chromium driven by `puppeteer-core` (installed in `/tmp/pp`, not the repo): 375×667 touch/DPR 2 first, then 1280×800. DOM geometry, hit-testing with `elementFromPoint`, layout-shift and LCP observers, contrast computed from the live computed styles, and a keyboard Tab-stop count. WebFetch for rivals. **Real devices were not available.** Headless Chromium fired `beforeinstallprompt` by itself, which real Android Chrome does only when its install heuristics are met, so install-banner findings describe what happens *if* the prompt fires.

**Skills.** `ui-auditor`, `mobile-flow-auditor` and `ui-designer` are **not registered in this runner**: they are not in the skill list, and `.claude/` holds only `agents/`, `commands/` and `settings.json`. I did their jobs by hand and did not claim a skill ran. The 2026-10-09, 10-22 and 10-29 audits recorded the same gap.

---

## Does it work? (checked before anything else)

| Check | Result |
|---|---|
| `/`, `/kundli`, `/matching`, `/numerology` | 200, 0.57–0.86 s, 135 / 140 / 135 / 128 KB |
| `/learn` | 307 → `/learn/` → 200, 278 KB. Recorded as by design in the 10-29 audit; I did not re-litigate it. |
| `/health` | 200, exact tier |
| **Stylesheet freshness (#253)** | All pages link `app.css?v=6e65b6ec`. The live file is 84,532 B with sha256 `6e65b6ec…` and is **byte-identical to the committed `src/astro_ai/static/css/app.css`**. Served `public, max-age=31536000, immutable`, safe because the URL is content-hashed. `sw.js` is `max-age=300`. **Not stale.** (The hash differs from 10-29's `ad4efc16`, so the CSS changed since; both audits matched the tree.) |
| Horizontal overflow, 5 pages × 2 viewports | None. |
| Console errors / failed requests | Only the Google Analytics collect call, which this sandbox blocks. Nothing from the site's own assets. |
| Layout shift / LCP at 375×667 | CLS **0.000** on all five pages; LCP 0.71–1.04 s. |
| Numerology flow (form → result) | Works. Result renders with "Life Path" in about 4.5 s; no 503 or "high demand" text seen on the rendered result. |
| **Kundli flow (`POST /reading` → result)** | **NOT verified this run.** My first `curl` POST returned `303 → /kundli`; the follow-up that returned 405 was my own mistake (`curl -X POST -L` re-POSTs). A cookie-jar retry and a browser-driven retry were both denied by the harness, and I did not route around that. So I have **no evidence either way** on the kundli result today. The 10-29 audit recorded a working flow (303, then a full reading in about 3 s, no 503). **#266's failure was not observed on any page I could load**, but treat the kundli POST as unchecked. |
| Matching flow (form → result) | Not run to a result this time (only the form page and its geometry). |

No Engineering-class outage was observed. One process defect was found (#733).

---

## `/` (home)

**Saw.**
- At 375×667 the whole form is in the fold: `#name` y 262–308, submit y 490–538, tab bar from 591. Panchang strip, Rahu Kaal and tithi render.
- **No `<main>` landmark in the raw HTML** (`curl … | grep -c '<main'` = 0). It is the only visitor-facing top-level template without one. Filed as #731.
- The install banner (desktop, bottom-left at 1280) overlaps the sample chart's lower corner. Already #310.
- The banner icon is **still visibly the retired purple** on both viewports. Already #381; I did not re-measure the manifest or icon pixel this run, only saw it in the screenshots.
- Desktop hero reads well: the CTA is above the fold with the form to its right.

**Filed.** **#731** (`ui` + `skill:ui-fixer`).

**Considered and rejected.**
- *Any change to the hero or CTA position.* The CTA is already in the fold, and `/` is the top landing (89 sessions in 2026-10-06 → 11-02; Organic bounce 12.5%, Direct 38%). There is no number to beat, and #242/#244 are the precedent against touching it blind.
- *The 11 px form labels ("BIRTH DATE", "(optional)").* 11 px uppercase labels are borderline but legible at the measured contrast; #307/#366 own the sub-12 px sweep and I would be splitting their evidence.
- *Placeholder text and the US `mm/dd/yyyy` date format.* That is the browser's locale, not our markup.

## `/kundli`

**Saw.**
- **#597 reproduces with identical numbers.** `#name` is at y 729–779, **138 px under the tab bar**; the submit button is at y 1095. The H1, a 5-line lead and a 2-line tagline come first. `/` keeps the same form in the fold.
- The install banner and feedback FAB sit over the bottom of the first screen on arrival.
- At 1280 the page is fine: heading, lead, then a centred form.
- Focus on inputs is a saffron 1px border (see #732).

**Filed.** Re-verification comment on **#597** carrying a full Evidence Block (it had none, so the cycle could not dispatch it). Honest limits recorded there: n = 25 sessions, and the Direct bounce of 92.3% on 13 sessions is as likely to be synthetic traffic (our own headless audits run the GA tag) as friction. The GA4 export has no event dimension, so the `/kundli` → `/reading` submit rate cannot be computed.

**Rivals (WebFetch, 2026-11-06).** This is **not** a place a rival does better.
- https://www.astrosage.com/kundli/ — per the fetched text: header, nav, wallet and sign-in links, a title and one description sentence, then **9 visible fields** (Name, Gender, Day, Month, Year, Hrs, Min, Sec, Place) and "Show Kundli". No social proof before the form and no install banner above it. Ours has 4 fields.
- https://www.clickastro.com/ — leads with a free-horoscope form and "No credit card or signup required", plus "Served over 110 MILLION satisfied customers", "Average rating: 4.8 ★ (306,949 Ratings)" and press logos, all self-reported. **That is something they do better than us**: we have no stateable trust number at about 500 sessions per 28 days and CLAUDE.md bars invented provenance, so I did not file it. Recorded for the product-manager.
- https://www.astrosage.com/kundli-matching/ returned **404** and https://www.astro-seek.com/birth-chart-horoscope-online returned **403**, so **no claim is made about either**. Prokerala returned 429 in the 10-29 run and was not retried.

**Considered and rejected.**
- *Shortening the lead paragraph.* It is keyword copy and trimming it is an SEO call with no number behind it; reordering with CSS `order` gets the same fold result.
- *A wizard or a sample chart beside the form.* No number to beat.

## `/matching`

**Saw.**
- Form top 217, first input `#g_name` at y 334–384 (in the fold); submit at 1242 on the stacked two-person form. The page is fine at both viewports.
- `/matching` landings: 13 in the window (Direct 10 at 90% bounce, AI Assistant 2 with 9.0 pages/session, Organic 1). Too few to read.

**Filed.** Nothing new on this page. #382 (modal over the result) is covered by the comment below.

**Considered and rejected.**
- *"Person 1 (typically Groom)" wording.* A cultural/product wording question, not a design defect.
- *Filing the modal again as new.* #309 and #382 carry it.

## `/numerology`

**Saw.**
- Tradition note, H1, a long multi-line lead, then the form: `#name` at y 611–661, **20 px under the tab bar**. Same shape as #597 and recorded there; not filed separately because the note is deliberate honesty copy, and reordering `/kundli` first is the test.
- **#382 reproduces.** Clean context: first view `bhagya_visit_count`=1, modal hidden; after submitting, count=2 and the modal is **shown over the result** (about 4.5 s later). The modal's own inputs are 14 px (iOS zooms on focus below 16 px; #596).
- The page's own inputs are 16 px.
- Desktop is clean.
- Rival, https://www.astrosage.com/numerology/ (fetched): per the extracted text it opens with explanatory content and a quote, shows a 5-input *Personalized Horoscope* form near the top (not a numerology calculator), and carries **no** tradition disclaimer. **We are ahead on honesty here**; I did not file anything against that.

**Filed.** Re-verification comment on **#382** carrying a full Evidence Block (it had none).

**Considered and rejected.**
- *Moving the form above the fold.* 20 px off, and no funnel number: 11 landings in the window.
- *38 text nodes under 12 px on the result.* #595 owns it; not re-measured this run.

## `/learn`

**Saw.**
- Hero, search, chips and cards render at 375 and 1280; no overflow, CLS 0.000, LCP 0.91 s.
- **77 images carry no `width`/`height`** (measured on `/learn/`). I considered that a CLS risk and **measured it: CLS is 0.000 at 375×667**, so I rejected it as a finding. It could differ on a throttled connection, which I did not test.
- The search input is 14 px (iOS focus zoom) and has no accessible name. Both are #596's.
- 1280: the install banner overlaps the first card (#310).

**Filed.** Nothing new on this page beyond #731 and #732, which apply to it.

**Considered and rejected.**
- *Redesigning the hub or an article's CTA.* `/learn` landings are the organic base (for example `rahu-mahadasha-ketu-antardasha` at about 3,000 impressions, position 6.8); #518 and #304 cover the route-to-tool question and there is no CTR number here to beat.
- *The 307 `/learn` → `/learn/`.* Noted as by design on 10-29. Engineering/SEO, not design.

---

## Cross-cutting

### Filed
- **#731 — no `<main>` on `/`; no skip link on any page** (`ui` + `skill:ui-fixer`). Measured: `<main` count 0,1,1,1,1 across the five pages; 12–14 Tab stops to the first form field at 1280. Cheapest change: one skip link plus `id="main-content"` on the existing `<main>`s and a `<main>` wrapper in `index.html`. Metric: `<main` on `/` 0 → 1; Tab stops on `/kundli` 13 → 2. Accessibility only; no engagement claim.
- **#732 — form focus indicator is a 1px saffron border at 2.50:1 on white** (`ui` + `design-proposal`). Measured on `/numerology` `#birth_date` after the 200 ms transition: focused border `rgb(228,145,60)` vs white 2.50:1, vs the unfocused border 1.70:1; the 3px ring is 16% alpha. Under WCAG 1.4.11's 3:1, and `verify_contrast.py` does not check focus. It appears 58 times across 15 templates. Cheapest test: change only the focused border colour to a token with at least 3:1 (`night` is 18.84:1, `muted` 5.97:1) in the existing "Form focus glow" CSS block and keep the saffron glow. A `design-proposal` because it touches every form and needs a human look. 2.4.7 (Focus Visible) *is* met; this is a 1.4.11 reading.
- **#733 — `agent-design.yml` never asks for an Evidence Block** (`chore` + `needs-human-review`, not `ui`). Measured with `verify_issue_evidence.py`: **#308, #309, #310, #379, #380, #381, #382, #595, #597 each FAIL with 6 problems**, and the cycle's own comments record the same for #594 and #596. That is **0 of 11 open design issues dispatchable**, and the cause is the prompt: `agent-design.yml:65-68` lists page / what / change / metric and never mentions the block that `discover.md:31` makes mandatory. **This is why #379, a one-class fix open since 2026-10-15, has had no cycle for 22 days.** The fix is in `.github/workflows/`, which the loop cannot author (#421) and which routes to `chief`. I applied `needs-human-review` for that reason. It is an addition I made, and `chief` can remove it.

### Re-verified, with Evidence Blocks added (3 comments)
- **#379** (install Install button under the tab bar): reproduces. `elementFromPoint` at the Install button's centre returns a node in `#mobile-tab-bar`; banner y 523–655 and tab bar top 591, both `z-40`, the nav later in the DOM. Dismiss is 20 px wide.
- **#597** (`/kundli` form under the tab bar): reproduces, 729–779 vs fold 591.
- **#382** (subscribe modal over the `/numerology` result): reproduces.

Six more issues fail the gate and were **not** touched: #308, #309, #310, #380, #381, #595. I did not re-measure them to the standard a block needs, and writing a block for something I only glanced at would be the "write the justification down, then treat the writing as the fact" pattern. They need their own re-measurement.

### Considered and rejected overall
- Proposing a new look for any page. No CTR or funnel number exists to beat (the five pages together are about 140 of 508 sessions (89 + 25 + 13 + 11 + 3); most are too small to read), and #244 is the cautionary precedent.
- A trust-number strip like ClickAstro's. We have no number we can state honestly.
- Tap-target size for inline body links (16–19 px high). WCAG 2.5.8 exempts inline links. The hero stat links on `/` (`76 explainers`, `Cited to classical sources`, 16 px high at 18 px pitch) and the 40 px-wide hamburger are borderline, and I did not file them because I have no evidence anyone mis-taps them.
- The Direct-channel bounce rates (`/matching` 90%, `/numerology` 100%, `/kundli` 92%). Samples of 9–13, and plausibly includes our own audits. Not evidence of friction.

---

## What I could not verify
- **The kundli result flow today** (see the table above). Denied twice; not worked around.
- **A real phone.** Headless Chromium's emulation covers geometry and hit-testing, not iOS Safari's dynamic toolbar or real Android install heuristics.
- **Whether install prompt taps, `/kundli` form starts or modal subscribes change anything.** The GA4 export has no event or device dimension, so every metric above that names an outcome is either deterministic (a hit-test, a contrast ratio, a count) or flagged as needing an event first.
- **Rivals matching and astro-seek** (404 and 403 respectively) and Prokerala (429 last run).
- **That this audit's own GA hits are excluded from the Direct numbers.** In this sandbox the GA collect call failed, but earlier headless audit runs may have registered.
