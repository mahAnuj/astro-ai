# Design audit — shubhagya.com, 2026-10-29

**Filed: 5 new issues (#593–#597) and 4 re-verification comments (#379, #380, #381, #382).** One of the five (#593) is an Engineering bug, deliberately not tagged `ui`.

**Revision audited:** `/health` → `{"ok":true,"revision":"bhagya-00523-kjk","build_sha":"9a3739ee…"}`. Local HEAD is `eea0447` (measurements-only). The live SHA is not in this shallow clone, so I could not confirm live == `origin/main`. What I could confirm is the stylesheet (below).

**Method.** Live site only. `playwright-core` (installed in `/tmp/pw`, not the repo) driving the system Chromium: 375×667 touch/DPR 2 first, then 1366×900. DOM measurements, a contrast sweep that composites translucent backgrounds, and three real form flows with a synthetic person (kundli, matching, numerology). WebFetch for rivals. **Real devices were not available**, and headless Chromium is not Safari.

**Skills.** `ui-auditor`, `mobile-flow-auditor` and `ui-designer` are **not registered in this runner**: they are not in the skill list, and `.claude/` holds only `agents/` and `commands/`. I did their jobs by hand and did not claim a skill ran. The 2026-10-09 and 2026-10-22 audits recorded the same gap.

**Context.** The 2026-10-22 audit (`measurements/design/latest.md`) found four issues but could not file them (`gh issue create` was denied that run). **None of the four had been filed.** I re-verified each live before filing; all four reproduce today. They are #593 (draft A), #594 (draft B), #595 (draft C) and #597 (draft D).

---

## Does it work? (checked before anything else)

| Check | Result |
|---|---|
| `/`, `/kundli`, `/matching`, `/numerology` | 200, 0.55–0.97 s, 152 / 140 / 135 / 128 KB |
| `/learn` | 307 → `/learn/` → 200 (by design) |
| `/health` | 200, 0.43 s, exact tier (build_sha set) |
| **Stylesheet freshness (#253)** | All pages link `app.css?v=ad4efc16`. Live file is 85,596 B and **byte-identical to the committed `src/astro_ai/static/css/app.css`**. It is served `public, max-age=31536000, immutable`, which is safe because the URL is content-hashed. HTML is `no-store`. **Not stale.** |
| Horizontal overflow, 5 pages × 2 viewports | None. Only two `pointer-events-none -z-10` glows on `/` extend past the edge. |
| Console errors / failed requests | None on any of the 10 loads. |
| **Kundli flow** (`POST /reading`) | 303, then "Your reading" renders in ~3 s. Lagna/Moon/Sun/Mahadasha tiles, Bhagya score, Manglik panel, yogas and all topic sections (Personality, Career, Wealth, Relationships, Health, Travel, Life Stages) are present. **No 503 and no "high demand" text.** #266's failure was not observed. |
| **Matching flow** | Result renders in ~3 s with no 503. The email modal covers it (see #382 below). |
| **Numerology flow** | Result renders in ~4 s. Same modal. |

No Engineering-class outage (#266-shaped) was observed. The one Engineering-class defect found, a date mismatch, is filed as `bug` (#593).

### Closed UI issues, do they hold?
Not re-tested this run beyond what showed up incidentally. #306 (autofocus) held visibly: `/kundli` H1 is unclipped and the page loads at scrollY 0. #305 (rashi tile clipping): at 375px the Lagna, Moon and Sun tiles on the live result show full names ("Sagittarius (Dhanu)", "Taurus (Vrishabha)", "Cancer (Karka)"), so it holds for this input.

---

## `/` (home)

**Saw.**
- At 375×667 the whole form is inside the usable fold. The tab bar starts at 591, and the Name input is at y=262.
- The panchang strip reads "Friday in Mumbai … Tithi Krishna Panchami", which agrees with Drik Panchang (see #593).
- On first arrival in Chromium the PWA banner sits at y 523–655 just under the submit button (y 490–538). #379 re-verified: the Install button's centre hit-tests to the **tab bar**.
- Desktop: no contrast failures except decorative gold zodiac glyphs (2.20:1 on cream). They are `aria-hidden` ornaments, which CLAUDE.md allows. Rejected.

**Filed.** Nothing new on this page. Comments added to #379 and #381 (the install icon is still rgb(107,33,168) purple while the manifest says `#140F1C`).

**Considered and rejected.**
- *Any change to the hero or CTA position.* The CTA is already in the fold. GA4 (2026-09-29 → 10-26): `/` has 92 sessions, the top landing, with healthy engagement. There is no number to beat, and #242/#244 are the precedent against touching it blind.
- *Social-proof numbers like Astrotalk's.* We have none we can state honestly at 424 sessions per 28 days, and CLAUDE.md bars invented provenance.

## `/kundli`

**Saw.**
- The H1, a 7-line lead and a 2-line tagline come before the form. **The first input is at y=729**, which is 138 px under the tab bar (usable fold 591). `/` has the same form fully in the fold at y=262.
- The result page works (above).
- On the result, the feedback FAB (x 309–359, y 527–571) clips the bottom-right corner of the Mahadasha tile group. Cosmetic; already covered by #308.
- Chart SVG labels render at effective 7.5–8.5 px (63 nodes). #380 re-verified.

**Filed.** **#597**, `ui` + `design-proposal` + `page:kundli`. The cheapest test is CSS `order` at <640 px (form before the lead; DOM, H1 and copy untouched). The metric is a scripted first-input bottom ≤ 591 (today 779), plus the `/kundli` → `/reading` submit rate. I could not pull that rate (the GA4 export has no event dimension) and the issue says to pull it before changing anything. Honest limits: `/kundli` landed 22 sessions, 17 of them bounced (12 Direct at 100% may include non-human traffic). Directional only.

**Rivals** (WebFetch, 2026-10-29). This is **not** something they do better.
- https://www.astrosage.com/kundli/ has navigation, an image and an intro above a form of 10+ fields (Name, Gender, Day, Month, Year, Hrs, Min, Sec, Place, Settings).
- https://www.drikpanchang.com/jyotisha/kundali/kundali.html has a heading and chart tables above a 12-field form.
- https://www.prokerala.com/astrology/kundli/ returned **HTTP 429**, so **no claim about Prokerala**.
- Our four fields are the shortest of the three.

**Considered and rejected.**
- *Shortening the lead paragraph.* It is keyword copy and trimming it is an SEO call with no number behind it. Reordering gets the same fold result.
- *A sample chart beside the form, or a wizard.* No number to beat.

## `/matching`

**Saw.**
- Form top 217, first input 334 (in the fold). The page is two stacked person cards, and the sticky "Calculate Guna Milan" CTA sits above the tab bar.
- Result renders. **On the first completed use, the full-screen "Today's Rashifal in your inbox" modal covers the entire result** (`bhagya_visit_count` = 2). #382 re-verified with a comment.
- The modal's email, city and rashi controls have no accessible name (new, #596).

**Filed.** Comment on #382 only; nothing new.

**Considered and rejected.**
- *"Person 1 (typically Groom) / Person 2 (typically Bride)" labels.* A product/cultural wording question, not a design defect.
- *Shortening the two-person form.* It is two people's data.
- *Filing the modal as new.* #309 and #382 already carry it with a mechanism and a cheapest change; a third issue would split the evidence. #382 also has a conversion-lead aspect (whether the modal earns subscribers), which I did not take on.

## `/numerology`

**Saw.**
- A tradition-disclaimer note, H1, a 7-line lead, and the form at y=611 (20 px under the tab bar).
- The result renders. It carries **38 text nodes under 12 px: 6 at 9 px, 26 at 10 px, 6 at 11 px** (measured live, `Priya Sharma` / `1990-05-15`). This is identical to the 10-22 count.
- #366 (the sub-12px remainder) does not list this page.

**Filed.** **#595**, `ui` + `skill:ui-fixer`. The change is a class swap of the `text-[9|10|11px]` classes to `text-xs`, plus adding the file to `TEXT_FLOOR_CLEAN`. The metric is 38 → 0. It is legibility only, with no engagement claim (9 sessions).

**Considered and rejected.**
- *Moving the form above the fold.* It is 20 px off and the page is mostly a result page; no number to beat.
- *Folding this into #247 (the numerology redesign).* Kept separate on purpose: the class swap is independent and low-risk.
- Astrological correctness of the numerology rules (#581–#584) is not a design question.

## `/learn` (index and the top article)

**Saw.**
- Index: 76 cards, search and chips load, no overflow, and only 12 px+ text at 375 px.
- `/learn/` has no accessible name on its search input (`learn-search`; #596).
- The top landing article `/learn/rahu-mahadasha-ketu-antardasha/` (43 sessions) ends with `<a href="/dasha">/dasha</a>` as link text, confirmed live with curl.

**Filed.** **#594** (`ui` + `skill:ui-fixer`, a one-string text change; metric: raw-path anchors 1 → 0) and **#596** (`ui` + `skill:ui-fixer`, six placeholder-only controls across the subscribe modal, feedback widget and `/learn` search; `aria-label` on six tags; metric: empty-name controls 6 → 0).

**Considered and rejected.**
- *Redesigning the article page or moving its CTA.* It ranks (organic, position ~7); #276 and #304 already did the cheap work, and there is no CTR or funnel number to beat.
- *The mobile sticky CTA and FAB overlap on articles.* Covered by #304 (closed) and #308 (open).

## Cross-cutting: the Panchang date bug (Engineering, not Design)

**#593.** Between 00:00 and 05:30 IST, `/panchang` serves the previous day. Measured at 05:15 IST on Friday 30 Oct: `/panchang` says "29 October 2026", Thursday, Tithi Krishna Chaturthi; the home strip says Friday, Tithi Krishna Panchami. https://www.drikpanchang.com/ (fetched in the same minute) says **Friday, October 30, 2026, "Tithi: Panchami upto 07:24 PM"**. So the home strip is right and `/panchang` is a day behind. The likely cause is `date.today()` (UTC on Cloud Run) at `routes/panchang.py:171`, which is **read from the tree, not verified at runtime**. The issue says it may be an intended sunrise-day convention and leaves that to the astrology owners.

**What Drik Panchang does better.** Its tithi, nakshatra, yoga and karana each carry an end time ("Nakshatra: Mrigashira upto 09:04 AM", "Yoga: Shiva upto 08:41 PM"), and our `/panchang` shows names only. That is a computation feature, not a UI change; I did not file it (no tithi-end function in the engine to my knowledge, and no traffic number). Noted for the product-manager.

---

## What I could not verify

- **Live == `origin/main`.** The live build SHA is absent from this shallow clone. Only the stylesheet hash equality is confirmed.
- **Real devices.** How often the PWA install banner actually shows on a real Android or iOS first load. Headless Chromium fired it; Playwright's 2.5 s first load did not. #310/#379 carry this limit.
- **Hindi layouts** beyond what was measured in earlier audits. I ran no Hindi pass this run.
- **The LLM prose quality on the Kundli result.** The sections render; I did not read the reading for accuracy (that is `qa`'s job).
- **Desktop contrast over gradient/image backgrounds.** The sweep skips elements with a background image, and SVG text uses `fill`, which the sweep does not read. The two desktop hits were SVG chart digits (false positive) and the decorative glyph row (rejected).
- **Prokerala** (HTTP 429) and any rival's conversion.
- **Side effects on production.** Four `POST /reading` (my first scripts stopped at the loading overlay, so I re-ran), two completed `POST /matching`, one `POST /numerology`, all with synthetic people. Nothing subscribed, signed in or sent to `/feedback`. The extra reading calls cost Groq tokens (the Kundli page generates topic prose), and I did not measure that number.
- **No repo files were created or changed by this audit.** Scratch scripts and screenshots are in `/tmp/pw`, `/tmp/aud` and `/tmp/iss`.

## Issues

| # | Labels | Title |
|---|---|---|
| 593 | bug, category:technical, priority:low | /panchang shows yesterday's date, weekday and tithi from 00:00 to 05:30 IST |
| 594 | ui, skill:ui-fixer | Top /learn landing article uses the raw path "/dasha" as link text |
| 595 | ui, skill:ui-fixer | /numerology result: 38 text nodes under 12px |
| 596 | ui, skill:ui-fixer | Six form controls have a placeholder and no accessible name |
| 597 | ui, design-proposal, page:kundli, effort:s, risk:low | /kundli on mobile: first form field 138 px under the tab bar |
| comments | | #379, #380, #381, #382: re-verified live 2026-10-29 |
