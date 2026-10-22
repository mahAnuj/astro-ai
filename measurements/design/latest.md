# Design audit — shubhagya.com, 2026-10-22

**Read this first: no GitHub issues were filed.** `gh issue create` was denied by the permission layer in this run (the call was refused, not errored). I did not route around it (`gh api`, a different invocation) because that would be the same action by another path. All four findings are written out in full under **"Issue drafts"** at the bottom, with labels, so a human or the next loop can file them verbatim. Two production `POST`s I tried to repeat were also denied (see "Does it work?"); I stopped there.

**Revision audited:** `/health` → `revision: bhagya-00493-9zh`, `build_sha: 380769fd1c6e7769db4e175d68310ac66b21c817`. Local `HEAD` is `0efd435` (`measurement 2026-10-22 (#488)`, measurements-only, which does not deploy). The live SHA is not in this shallow clone, so I **could not confirm the live build equals `origin/main`**; what I could confirm is that the stylesheet matches the tree (below).

**Method.** Live site only. Playwright (installed in `/tmp`, not the repo) driving system Chromium 155: 375×667 touch/DPR 2 first, then 1280×800. Screenshots, DOM measurements, a sampled-background contrast sweep, three real form flows, plus a GET of all 76 `/learn` articles. Real devices were **not** available.

**Skills.** `ui-auditor`, `mobile-flow-auditor` and `ui-designer` are not registered in this runner (not in the skill list; no `.claude/skills/`; `.claude/` holds only `agents/`, `commands/`, `settings.json`). I did their jobs by hand rather than claim a skill ran. The 2026-10-09 audit (`measurements/design/latest.md`) recorded the same gap; this run treats it as a baseline and mostly checks what changed since.

---

## Does it work? (checked before anything else)

| Check | Result |
|---|---|
| `/`, `/kundli`, `/matching`, `/numerology` | 200; 0.55–0.64 s; 152 / 140 / 135 / 128 KB |
| `/learn` | 307 → `/learn/` → 200 (by design, as in 10-09) |
| `/health` | `{"ok":true,"revision":"bhagya-00493-9zh","build_sha":"380769fd…"}` — exact tier live |
| **Stylesheet freshness (#253)** | All pages link `app.css?v=e8f61cc2`; live file 85,567 B, **md5 `032166e1…` identical to the committed `src/astro_ai/static/css/app.css`**; `cache-control: public, max-age=31536000, immutable`, safe because the URL is content-hashed. **Not stale.** `sw.js` is `max-age=300`. |
| Horizontal overflow, 5 pages × 2 viewports | None (`scrollWidth == viewport`). The only wide boxes are two `pointer-events-none -z-10` decorative glows on `/` |
| Console errors / 4xx / failed requests | None on any of the 10 loads |
| `POST /matching` (fresh context) | 200 in 8.7 s; result renders, no clipped text, no overflow |
| `POST /numerology` | Result in 2.6 s; no clipped text, no overflow |
| `POST /reading` (Kundli) | **Accepted: 303 in 0.4 s**, then the "Casting your chart…" overlay. **I did not wait for the result page**; my script read the URL too early, and a follow-up request to re-check it was denied by the permission layer. So **the Kundli result, the #305 tile clipping and #266 are unverified this run.** I saw no 503, but I also did not see a result. |
| `/learn` articles | 76/76 return 200, exactly one `<h1>`, every one links `/kundli`. 13 contain the word "None" — all ordinary prose ("None of the above…", "Manglik is: None — Mars is not…"); rejected as a defect |

No Engineering-class failure of the shape #266 describes (503 / "high demand") was observed. One Engineering-class **correctness** finding was found and is drafted as a `bug`, not a `ui` issue (draft A).

### Closed UI issues — do they hold on the live site?

| Issue | Live result 2026-10-22 |
|---|---|
| #306 `/kundli` autofocus scroll | **Holds.** `scrollY` 0 after load, no `[autofocus]` in the DOM, H1 top 101 px vs header bottom 69 px |
| #304 `/learn` sticky Kundli CTA under the tab bar | **Holds.** Top landing article at scroll 6000: `#learn-sticky-cta` spans 522–591 px, directly above the tab bar (top 591). Hidden until ~35 % scroll, by design. The bar is translucent, so one line of body text ghosts through just beneath it — cosmetic, not filed |
| #307 sub-12 px | **Mostly holds.** `/learn/` index: 0 sub-12 nodes (was 234). Tab-bar labels fine. Remainder is #366 (still open; `/` still 24 nodes at 11 px, same number as filed) |
| #305 rashi-name clipping | **Not verifiable this run** (result page not reached) |

### Open UI issues — do they still reproduce?

| Issue | Live result |
|---|---|
| #382 subscribe modal over the `/matching` and `/numerology` result | **Reproduces.** Fresh browser context, no prior visits, submit each form: the "Today's Rashifal in your inbox" modal sits over the result on both. Screenshots `res_match_top.png`, `res_numer_top.png` |
| #308 feedback FAB over reading text | **Reproduces.** On `/learn/rahu-mahadasha-ketu-antardasha/` at scroll 6000 the FAB clips "deep" and "transitio[n]" in the amber callout |
| #310 / #379 install banner | **Conditionally.** Chromium's CLI `--screenshot` run (virtual time) showed the banner over the form on all five pages at 375×667; Playwright's 2.5 s first load did not. That is consistent with the banner being gated on `beforeinstallprompt` (`base.html:1420`). I cannot say how often a real Android first load shows it, same limit as the 10-09 audit |
| #309, #380, #381 | Not re-tested this run (#380/#366 numbers consistent with what was filed; matching result shows 7 nodes at 9 px, which are the SVG chart labels #380 describes) |

Suggested comments to add (not posted, same denial): on #382 "reproduced 2026-10-22, fresh context, `/matching` and `/numerology`"; on #308 "still reproduces on the top `/learn` landing article".

---

## `/` (home)

**Saw.** At 375×667 the whole form is inside the usable fold. The tab bar starts at 591 px, so "usable" is 591, not 667: Name input 262–308, submit **490–538**. The ~3.4:1 / 11 px look of the trust strip ("No signup, no spam", "Questions every day") is gray-brown on cream-2 and legible; my sampler misread the background there (it sampled the night section below), so that is a false positive, not a finding. 24 text nodes at 11 px (= #366). No overflow, no console errors.
**Filed.** Nothing (all findings here are existing issues: #366, #310, #308).
**Considered and rejected.**
- *Anything about the hero or CTA position.* The CTA is already in the fold, GA4 (2026-09-21 → 10-18, 341 sessions) has `/` as the top landing at 77 Direct sessions with 32 % bounce and 3.77 pages/session. There is no number to beat, and #242/#244 are the precedent for not touching it blind.
- *Social-proof numbers like Astrotalk's.* See Rivals.

## `/kundli`

**Saw.** The H1 is no longer clipped. The page then opens with the H1 (101–209 px), a 7-line lead paragraph and a 2-line tagline ("Bhagya reads the sky, not your wallet…", `kundli_landing.html:29`) before the form. **Form card top 526 px; first input 729–779 px; submit 1095–1143 px**, against a usable fold of 591 px. So the first field is **188 px under the tab bar** and the button is a screen and a half down. The home page (same form) does the opposite and keeps all of it above the fold.
**GA4 numbers (window 2026-09-21 → 10-18, `measurements/ga4.json`):** `/kundli` landed **16 sessions** (10 Organic at 50 % bounce, 6 Direct at 100 % bounce). On 10-09 this was 1 session; it is still far too few to reach significance in one window.
**Filed.** Draft D (`design-proposal`), the cheapest test: on <640 px put the form card before the lead copy with CSS `order`, leaving the DOM and H1 where they are. The metric is a scripted fold position, not a conversion claim.
**Considered and rejected.**
- *Delete or shorten the lead paragraph.* It is the page's keyword copy; trimming it is an SEO decision with no number behind it. Reordering gets the same fold result without touching the words.
- *A sample chart beside the form.* Same as 10-09: no number to beat.

## `/matching`

**Saw.** Form top 217, first input 334–384 (in the fold). Two stacked person cards, 1,098 px of form, submit is the last thing; a duplicate submit exists with `form="matching-form"`. After submit the subscribe modal covers the result (#382). No clipped text, no overflow in English or Hindi.
**Filed.** Nothing new. #382 and #380 cover what I saw.
**Considered and rejected.**
- *"Person 1 (typically Groom) / Person 2 (typically Bride)" labels.* A cultural-default and wording question for product/astrology owners, not a design defect.
- *Shortening the two-person form.* It is two people's data; nothing to cut.

## `/numerology`

**Saw.** Tradition-disclaimer note, H1 (217–289), 7-line lead, form heading at 540; first input 611–661 (20 px under the tab bar), submit 769–817. The result renders cleanly but carries the smallest HTML text I measured on any tool page: **38 text nodes under 12 px at 375 px (6 at 9 px, 26 at 10 px, 6 at 11 px)**. Source: `numerology.html` lines 172, 174 ("Bhagya score" labels), 296, 358/360 (the Lo Shu cell's count chip at 10 px and "Missing" at **9 px**), 376/394 (arrow digit chips), 424/425 (mulank planet and count). #366's metric names only `/` and `/panchang`, so nothing in the queue would catch this page.
**Filed.** Draft C (`ui` + `skill:ui-fixer`).
**Considered and rejected.**
- *Moving the form above the fold.* It is 20 px off and the page is mostly a result page; no number to beat.
- *Hindi.* Not measured on the numerology result (only the landing, which has no sub-12 nodes and no overflow in Hindi).

## `/learn` (index) and articles

**Saw.** Index: 76 cards, no overflow, 0 sub-12 nodes (was 234), search and chips load. **Articles** are where traffic is (the top landing `/learn/rahu-mahadasha-ketu-antardasha/` has 28 Organic + 5 Direct sessions of 341, 28.6 % organic bounce, 1.04 pages/session). That article's amber callout says: *"…`<a href="/dasha">/dasha</a>` has the deep-dive reading…"* — a **raw URL path as link text** (`learn/rahu-mahadasha-ketu-antardasha.html:92`). I scanned all 76 live articles for anchors whose text is a path: **this is the only one.** `/dasha` is a real route (200, "Free Vimshottari Dasha Calculator…").
**Filed.** Draft B (`ui` + `skill:ui-fixer`), a one-line text change.
**Considered and rejected.**
- *Redesigning the article page, or moving its CTA higher.* It ranks; #276 (closed) and #304 already did the cheap work. First `/kundli` link is at 6,376 px of a 10,143 px page, but the sticky bar now covers that.
- *A scan for unrendered Jinja, literal `**`, double-escaped entities across 76 articles.* Run; found none.

---

## Contrast

Computed on all five pages at 375 px by sampling the real rendered background behind each text node (text made transparent in the screenshot), compositing translucent colours, and applying WCAG thresholds. 133 / 111 / 95 / 64 / 364 text nodes. The sweep flagged 17 elements; I reviewed them. **All were sampler artefacts** (footer links inside collapsed accordions, one hidden duplicate button, and the trust-strip mis-sample above), so **zero real contrast failures were found.** `scripts/verify_contrast.py` run locally passes all four gates. The 10-09 audit left the dark hero unmeasured; it is now covered by the same sweep. Limits: median-pixel background, so text over a gradient or an image is approximate; desktop contrast not run.

## Rivals (what was and was not fetchable)

Fetched successfully today: `https://www.astrosage.com/free/`, `https://www.drikpanchang.com/`, `https://www.astrotalk.com/`. **Failed: `https://www.prokerala.com/astrology/kundli/` returned HTTP 429, so I make no claim about Prokerala in this run.** WebFetch returns text, so everything below is structure and copy, never visual polish or conversion.

| What they do | Where | Do we do it better? |
|---|---|---|
| Tithi, nakshatra, yoga and karana each carry an **end time**: "Tithi: Dwadashi upto 02:35 PM", "Nakshatra: Purva Bhadrapada upto 09:02 PM", "Yoga: Dhruva upto 10:08 PM" | https://www.drikpanchang.com/ | **They are ahead.** Our `/panchang` text shows tithi/yoga/karana names "at sunrise" and I found no "upto"/"until" anywhere in it. This is a computation feature (the engine has no tithi-end function; `grep` finds one comment in `muhurat.py`), not a UI fix → route to product-manager. Not filed: no number to beat, and impressions on `/panchang/*` archive URLs in `measurements/gsc-all.json` are single digits per page with 1 click total in the rows I read |
| Rahu Kaal appears only as a link under "Panchang Utilities" and in the footer; its time is not on the home page | https://www.drikpanchang.com/ | **We are ahead.** Our home strip shows "Rahu Kaal (avoid) 10:55–12:22" and "Abhijit (best) 11:59–12:45" |
| City shown only in the heading and a hover tooltip; text shows no visible city selector | https://www.drikpanchang.com/ | Ours labels the city in the strip ("Friday in Mumbai"). Whether theirs is changeable I cannot tell from text |
| Free hub of ~20 tools in three unlabelled lists; sign-in modal ("Why Sign Up?"), "First Call/Chat FREE" pop-up, paid products on the same page | https://www.astrosage.com/free/ | Ours is clearer and has no pay prompts on tool pages. They do reach a kundli from four places (top bar, Home menu, Astrology menu, list item 2) |
| Hero leads with "India's most accurate astrology platform", CTA "Start Free Chat", social proof "5Cr+ users", "50,000+ verified astrologers", "4.7 … Based on 19L+ reviews", a live-activity feed | https://www.astrotalk.com/ | Different product (paid chat). **Do not copy the numbers** — we have none we can state honestly at ~340 sessions/28 days, and `CLAUDE.md` bars invented provenance. Their free-tool list does include "Lo Shu Grid", "Numerology" and "Kundli Matching" as direct links |

**Honest summary:** on structure and honesty we remain ahead of the three fetched rivals. The one concrete thing a rival does better that I could verify is Drik Panchang's end times. Where we lose is to ourselves: sub-12 px text, overlays over the first fold, and one page whose form sits under the tab bar.

---

## Issue drafts (not filed — see the first paragraph)

### Draft A — Engineering bug (NOT `ui`)
**Title:** `[BUG] /panchang shows yesterday's date and tithi from 00:00 to 05:30 IST while the home strip shows today's`
**Labels:** `bug`, `category:technical`, `priority:low`

> **Team: Engineering, not Design.** Found during a design audit; no visual fix exists. Deliberately not labelled `ui`.
>
> **Pages:** `/panchang`, and the Panchang strip on `/`.
>
> **What is wrong.** Between 00:00 and 05:30 IST the two surfaces answer "what is today?" differently. Both fetched within a minute, live, 2026-10-22 23:01 UTC = Fri 2026-10-23 04:31 IST:
> ```
> GET /panchang -> "Today's Panchang — 22 October 2026" ... "Tithi Shukla Ekadashi"
> GET /         -> strip: "Friday in Mumbai" ... "Tithi Shukla Dwadashi"
> ```
> https://www.drikpanchang.com/, fetched the same minute, lists Friday, October 23, 2026 with "Tithi: Dwadashi upto 02:35 PM" (New Delhi). So the strip agrees with the rest of the world and `/panchang` is a day behind. Repeated twice, same result.
>
> **Likely cause (read from the tree, not verified at runtime).** `src/astro_ai/routes/panchang.py:174` passes `date.today()` — the server's local date, UTC on Cloud Run — as the target date, then anchors the compute at local noon of that date (`_target_moment`, line 66). UTC rolls over at 05:30 IST, so for the first 5.5 h of each Indian day `/panchang` serves yesterday. `routes/deps.py:818` (`panchang_strip_for_city`) also keys its cache on `date.today()`; check whether the strip has the same lag even though it rendered "Friday". I did not confirm the container's TZ.
>
> **Not decided here: which convention is intended.** A sunrise-to-sunrise Hindu day would legitimately still be "22 October" at 04:31 IST. If that is intended, `/panchang` should say so and the strip should agree; today they disagree with each other and neither names a convention. That is the astrology owners' call.
>
> **Cheapest change to test.** Compute "today" once, in the resolved city's timezone (`chart.birth_tz` is already in hand), through one helper used by `/panchang`, the strip and the strip's cache key. No second date source.
>
> **Metric.** Behaviour-suite test: freeze the clock at 2026-10-22T23:00Z and assert the date shown by `/panchang` equals the date and weekday on the Mumbai home strip (today 22 Oct vs Fri 23 Oct → expect 0 mismatches). No engagement claim: the window is ~5.5 h/day of low-traffic hours.
>
> **Not checked:** whether `/rashifal`, the daily email and the "Today" badge on `/panchang/YYYY-MM-DD` share the same `date.today()`.

### Draft B — `ui`, `skill:ui-fixer`
**Title:** `[UI] Top /learn landing article uses the raw path "/dasha" as link text`

> **Page:** `/learn/rahu-mahadasha-ketu-antardasha/` (the top GA4 landing: 28 Organic + 5 Direct of 341 sessions, 2026-09-21 → 10-18).
>
> **What is wrong.** The amber "Generate your own Dasha timeline" callout ends *"`/dasha` has the deep-dive reading for your specific transition."* with the link text being the literal path: `<a href="/dasha">/dasha</a>` (`src/astro_ai/templates/learn/rahu-mahadasha-ketu-antardasha.html:92`). A reader sees a URL fragment in prose on the page that most visitors arrive on. Scanned all 76 live articles for anchors whose text is a path: this is the only one. `/dasha` returns 200 ("Free Vimshottari Dasha Calculator…").
>
> **Cheapest change.** Change the link text to words, e.g. `The dasha deep dive has the reading for your specific transition.` One string, no layout change.
>
> **Metric.** Scripted scan of the 76 rendered articles: anchors with text matching `^/[a-z-]+$` goes 1 → 0. No engagement claim — a text fix cannot be measured at ~33 sessions.

### Draft C — `ui`, `skill:ui-fixer`
**Title:** `[UI] /numerology result: 38 text nodes under 12px, down to 9px on the Lo Shu grid — #366's metric does not name this page`

> **Page:** `/numerology` result, mobile (375 px).
>
> **What is wrong.** Measured live, fresh context, POST `name=Priya Sharma`, `1990-05-15`, 375×667: **38 visible text nodes under 12 px — 6 at 9 px, 26 at 10 px, 6 at 11 px.** In the template: `numerology.html:172,174` (Bhagya-score label and "out of"), `296` (11 px italic subtitle), `358` (Lo Shu count chip, 10 px), `360` ("Missing", **9 px**), `376`/`394` (arrow digit chips, 10 px), `424`/`425` (mulank planet and count, 10 px). #366 lists `/`, `/panchang` and articles and its metric names only the first two, so nothing queued covers this page. Related: #307 (closed), #366, #247 (numerology redesign).
>
> **Cheapest change.** Swap those nine `text-[9|10|11px]` classes for `text-xs`. Check the 3×3 Lo Shu cell at 375 px for chip wrapping ("MISSING" at 12 px with `tracking-wider`).
>
> **Metric.** Same scripted count at 375 px on the numerology result: 38 → 0; add `numerology.html` to `TEXT_FLOOR_CLEAN` in `scripts/verify_redesign_tokens.py` as #366 prescribes. Legibility only; no engagement claim.

### Draft D — `design-proposal`, `needs-human-review`, `page:kundli`, `effort:s`, `risk:low`
**Title:** `[UI] /kundli on mobile: the first form field sits 188px under the tab bar — / keeps the same form wholly in the fold`

> **Page:** `/kundli`, mobile 375×667, first load.
>
> **What is wrong.** Usable fold is 591 px (tab bar top), not 667. Measured live: H1 101–209, lead paragraph and tagline follow, **form card top 526, first input 729–779, submit 1095–1143**. The home page's identical form has its first input at 262 and submit at 490–538, wholly inside the fold. GA4 2026-09-21 → 10-18: `/kundli` had 16 landing sessions, 10 Organic at 50 % bounce and 6 Direct at 100 % bounce (11 of 16 bounced). **That is far too few to establish cause**; the Direct rows may include non-human traffic.
>
> **Why `design-proposal`, not a fixer item.** It trades page copy position against fold position on a page that now ranks a little, and I have no funnel number for `/kundli` → `/reading`. A human should choose.
>
> **Cheapest change to test (not a redesign).** At <640 px, order the form card before the lead and tagline with CSS `order`; leave the DOM order, H1 and all copy untouched, so there is no SEO text change.
>
> **Metric.** Scripted at 375×667: first input bottom ≤ 591 px (today 779). Outcome, directional only: `/kundli` landing bounce (baseline 11/16) and `/kundli` → `/reading` submit rate from the event log, which I did not query; pull it before changing anything, and do not read a result from one 28-day window.

---

## What I could not verify

- **Kundli result page, #305 (tile clipping) and #266 (Groq ceiling) this run.** Not reached; I saw the 303 and the loading overlay only. A repeat request was denied by the permission layer, and I stopped. Both remain as the 10-09 audit left them.
- **Whether live equals `origin/main`.** Live `build_sha` 380769fd… is absent from this shallow clone. Only the stylesheet hash equality is confirmed.
- **Real devices, soft-keyboard behaviour, how often the install banner shows on a real first load** (#310/#379 evidence limit).
- **Desktop contrast; text over gradients or images** (approximate sampler).
- **Hindi layouts beyond overflow and sub-12 counts** (no overflow on `/`, `/kundli`, `/matching`, `/numerology` at 375 px; no rashi-name or result-page checks in Hindi).
- **Any rival's conversion, or Prokerala at all** (HTTP 429).
- **Side effects on production:** one `POST /reading` (accepted, 303), one `POST /matching`, one `POST /numerology`, all with a synthetic test person; nothing subscribed, signed in, or sent to `/feedback`. About 90 GETs (76 articles, plus pages and assets).
- **No files in the repo were created or changed by this audit**; scratch scripts and screenshots live in `/tmp/scripts` and `/tmp/shots`.
