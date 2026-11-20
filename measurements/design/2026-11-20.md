# Design audit — shubhagya.com, 2026-11-20

**Live state:** `/health` ok, revision `bhagya-00809-rp8`, `build_sha` 0f450d2 (the current main commit).

**Chief guidance:** `measurements/sync/chief-guidance.md` (2026-11-19) has no Design or UI row, so I had no role instruction to follow or to decline. Its Stop and Start lists are about the build lane and growth.

**Method:**
- Fetched each page with curl.
- Took 375x667 screenshots with headless Chromium.
- Checked the stylesheet against the repo.
- Did not run a full contrast pass. `verify_contrast.py` covers that.
- Did not test real touch devices.

**Working check:**
- All five pages return 200 in about 0.7s. No 5xx, so there is nothing to route to Engineering.
- `/learn` returns 308 to `/learn/`, which is fine.

**Stale-stylesheet check (#253):**
- The page links `app.css?v=2f1656a2`.
- The asset is served with `cache-control: public, max-age=31536000, immutable`, and the version is content-derived (`asset_v`).
- The live `app.css` is byte-identical to the repo's.
- Classes in the HTML but absent from `app.css` are the semantic ones (`nav-dropdown`, `learn-card`, `footer-group`, `chart-cast` and similar). `base.html` defines them in an inline `<style>` block, so this is not staleness.

## `/` (home)
- **Saw:**
  - The panchang strip, then the birth-details form.
  - At 375x667 the form fills the viewport and the H1 is below the fold.
  - The Name input is autofocused.
  - The bottom tab bar is clear and tap targets are generous.
- **Filed:** #1269 (design-proposal). It tests dropping Name autofocus on touch widths, shared with `/matching`.
- **Rejected:**
  - Moving the H1 above the form. That would redesign a page that ranks, and I have no CTR or funnel number to beat (the #244 instinct).
  - Adding tithi end times to the strip. Drik Panchang shows them (https://www.drikpanchang.com/), but that is a panchang-rule and data change, so it belongs to research and engineering, not UI.

## `/kundli`
- **Saw:**
  - A clean single-card form with a wrapped H1.
  - The H1 is fully visible, so #306's fix holds.
  - There is no autofocus.
  - The Name field and the Birth date label are visible in the first viewport.
- **Filed:** nothing.
- **Rival:** AstroSage's form has 5 core fields plus 7 behind "Advanced Settings" (https://www.astrosage.com/). Ours is 4 fields with no advanced panel, so we are ahead on friction. Its primary CTA is "Chat with Astrologer", a paid-product pattern we should not copy.
- **Rejected:** copying AstroSage's layout, because there is no evidence it converts better.

## `/matching`
- **Saw:**
  - A card inside a card, with a double border.
  - Inputs about 257px wide of 375px.
  - Autofocus on the Name field.
- **Filed:**
  - #1268 (ui-fixer). It drops the nested padding or border below `sm`.
  - #1269 covers the autofocus.
- **Rejected:** a stepped, wizard-style matching flow. It is a redesign with no funnel number.

## `/numerology`
- **Saw:**
  - A yellow tradition disclosure at the top, which is honest and good.
  - A short mobile subtitle.
  - A form that starts below the fold and is mostly hidden behind the tab bar.
- **Filed:** nothing.
- **Rejected:**
  - Moving the disclosure. It is a deliberate honesty cue.
  - Calling the muted subtitle low-contrast from the screenshot alone. The palette is governed by `verify_contrast.py`, and I did not measure it.

## `/learn/`
- **Saw:**
  - A dark hero followed by search and category chips, and 77 explainers.
  - All 78 images have `alt` text and `loading="lazy"`.
  - The HTML is 288 KB, with the hero SVGs lazy-loaded.
  - The chips wrap in 2 to 3 rows and are tappable.
- **Filed:** nothing.
- **Rejected:** a chip carousel, a pagination change and similar. No evidence they would move CTR.

## Not done
- Rival fetches that failed:
  - AstroSage `/free/free-kundli.asp`: 404.
  - Astro-Seek: 403.
  - I made no claims from either.
- I did not review the post-submit result pages (chart, matching score, numerology result). They need form input, and a design finding there should come with a real session.

## Issues filed
| # | Type | Page | Summary |
|---|---|---|---|
| 1268 | `ui` + `skill:ui-fixer` | `/matching` | Card-in-card wastes mobile width. |
| 1269 | `ui` + `design-proposal` | `/`, `/matching` | Test dropping mobile Name autofocus. It conflicts with the earlier decision in #67, so it needs a ruling. |
