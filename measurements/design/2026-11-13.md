# Design audit — shubhagya.com, 2026-11-13

Live revision `bhagya-00687-6wf`, `build_sha` 82b45f1 (equal to `main` HEAD). Live `app.css` is byte-identical to the committed file, so there is no stale-stylesheet problem. It is served with `max-age=300`.

I used headless Chromium at 375x667. Every page was reachable: `/`, `/kundli`, `/matching` and `/numerology` returned 200, and `/learn` returned 307 to `/learn/`, which is fine. Nothing here is a 503 or an Engineering bug.

**Chief's row for design:** "not rated, no instruction". There was nothing to follow or to refuse.

**Limits of this audit:** I did not run a measured contrast pass or a desktop pass. I only reviewed screenshots at 375x667 (home also at a tall viewport), so no contrast ratios were measured. I could not reproduce the PWA banner (#310) in headless Chrome.

## /
- **Saw:** the panchang strip, then the birth-details form on the first fold. The H1 ("Your Janma Kundli, simply explained") sits just below it, followed by trust chips, a stats grid and the "Don't fear your Kundli" cards. The layout is coherent and the form-first design reads well.
- **Filed:** nothing.
- **Rejected:**
  - Moving the H1 above the form. The form is the conversion path, and I have no CTR or funnel number to beat.
  - A hero redesign. #198 and #233 are already open with `needs-human-review`.
  - #310 (the PWA banner) already covers the first-fold overlap. I did not duplicate it.

## /kundli
- **Saw:** a clear H1, then a form with its first field on the first fold. No defects.
- **Filed:** nothing.

## /matching
- **Saw:** the H1, then a card nested inside a card, with Person 1's fields starting on the first fold. The nested border costs about 24px per side at 375px. That is cosmetic, and I have no evidence it affects completion.
- **Filed:** nothing.
- **Rejected:** flattening the nested card, because it has no metric.

## /numerology
- **Saw:** the disclaimer and a long lede fill the first fold. The form's first field is at the very bottom, behind the tab bar.
- **Filed:** #944, `ui` + `design-proposal`. It proposes trimming the lede on mobile. The disclaimer stays untouched, because it is a grounding line. The metric is the mobile form-submit rate. There is no baseline, so the analyst must state the traffic needed to score it.

## /learn
- **Saw:** a good hero, a search box and category chips. The search placeholder is cut off mid-example at 375px.
- **Filed:** #943, `ui` + `skill:ui-fixer`. It shortens the placeholder.

## Rivals (fetched)
- **https://www.astrosage.com/** — The Kundli form competes with about five other calls to action: Chat with Astrologer, sign-in, wallet recharge, a promo banner, and about 25 priced astrologer entries. There is no hero headline. Our single-form first fold is cleaner. We do not need to copy their layout.
- **https://www.drikpanchang.com/** — Today's panchang is plain text under an H1 and a date card, with an inline "more" link. Ours is a compact strip. They show more fields (sunrise, sunset, nakshatra, yoga, karana). Nothing here is cheap to test without a CTR number, so I did not file one.
- **https://astro-seek.com/** — This returned 403 to fetch, so I make no claim about it.
