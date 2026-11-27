# Design audit: shubhagya.com, 2026-11-27

Live build `7b0ee2f` (/health `build_sha` matches HEAD). Stylesheet check: the live `app.css` hash `963961b6` equals the tree's, and the pages reference `?v=963961b6`. There is no stale-CSS repeat of #253.

**Chief guidance:** `measurements/sync/chief-guidance.md` (2026-11-25) has no Design row. There was no instruction to follow or refuse. Its growth bias (#1076, #1107, #1065, #1430) is SEO work, not design.

**Method limits:**
- Screenshots came from headless Chromium at 375x667. I did not run desktop or tablet widths.
- I did not measure contrast numerically; the `verify_contrast.py` gate covers templates only.
- I filed no performance finding.

## Works-check (before any design claim)
| Page | HTTP | Time |
|---|---|---|
| / | 200 | 0.60s |
| /kundli | 200 | 0.78s |
| /matching | 200 | 0.54s |
| /numerology | 200 | 0.72s |
| /learn | 308 to /learn/ (200) | 0.32s |

No 503s and no Engineering bugs to hand over. I did not submit the forms, so the Groq-backed result paths are untested. The /learn 308 is already in #1107.

## /
- **Saw:** the birth-details form is first, with the panchang strip above it. The H1 falls below the fold at 375x667. The Name field is autofocused.
- **Filed:** nothing new. Autofocus is already #1269.
- **Rejected:** moving the H1 above the form. I have no CTR or funnel number to beat, and the page leads with the form on purpose. This is the #244 trap.

## /kundli
- **Saw:** a clean single card, with labelled fields about 293px wide. The H1 is three lines but readable.
- **Filed:** nothing.
- **Rival:** AstroSage (https://astrosage.com/kundli/, fetched; /free/kundli.asp returned 404) shows a long nav block first, a "Kundli" H1, then a form with Gender, a Day/Month/Year split, Hrs/Min/Sec, and hidden advanced settings (ayanamsa, chart style, KP number). Our form has four fields, a privacy line under the title, and a "free instantly" button. We already do better on friction. AstroSage's one edge is exposing ayanamsa and chart style. That is a product decision, not a design one, so I filed nothing.

## /matching
- **Saw:** two nested bordered cards, so the inputs are about 290px wide. Name is autofocused, which opens the keyboard over the form.
- **Filed:** #1529 (`ui`, `skill:ui-fixer`). It flattens the inner card below `sm`. The metric is form-start to submit rate at 375px. I told it to wait for #1076, the position 4.2 to 7.8 drop, so the two are not confused.
- **Rejected:** a wizard that splits Person 1 and Person 2. That is a redesign of a page whose ranking is already falling, with no baseline.

## /numerology
- **Saw:** a yellow "modern Western tradition, not classical Jyotish" notice above the H1, then the form.
- **Filed:** nothing.
- **Rejected:** moving or shrinking the notice. It is an authenticity disclosure tied to the "100% true" objective. A conversion gain does not outweigh it.
- **Noted, not measured:** the grey subtitle on cream looks light. I did not compute a ratio. Run `verify_contrast.py` before anyone files it.

## /learn
- **Saw:** a dark hero, a search box, and category chips with counts (77 articles). Good. The mobile bottom nav overlaps the chip row at the fold, which is normal for a scrollable page.
- **Filed:** nothing.
- **Rival:** Drik Panchang (https://www.drikpanchang.com/, fetched) leads with a live clock and today's panchang, and uses a grouped side menu for tools. Our home panchang strip does a smaller version of the same. Nothing to copy beyond what exists.

## Site-wide
- **Filed:** #1530 (`ui`, `skill:ui-fixer`). The bottom-nav "Ask" icon is a fullwidth "？" (U+FF1F). It renders as an empty box in headless Linux Chromium and depends on a CJK font fallback. Real-device impact is unknown, and the issue says so.

## Not filed
- No `design-proposal`: no finding needs a human eye without a CTR or funnel baseline.
- Rival comparison covered two sites (Drik Panchang and AstroSage). I did not fetch others.
