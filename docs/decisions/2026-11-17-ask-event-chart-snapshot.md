# Each `form_ask` event stores a compact chart summary, and never the birth details

- **Date:** 2026-11-17
- **PR / issue:** #1167 (slice 2). Owner's ruling, 2026-11-17: "Chart snapshot: yes. Each
  `form_ask` event also stores a compact chart summary: planet signs and houses, lagna, Moon
  nakshatra, the current mahadasha and antardasha. It never stores birth date, birth time or
  birth place."

## Why, measured

A weekly audit of Ask answers needs to grade chart-specific claims ("your Saturn is in the 7th")
against the chart the answer was written for, and the event held only the question and answer.

`routes/ask.chart_snapshot` returns `lagna`, `planets` (name -> sign and house), `moon_nakshatra`,
`mahadasha`, `antardasha`. For the 1990-04-15 07:30 New Delhi test chart that is 533 bytes of
compact JSON, so 2.7 MB at the `_MAX_EVENTS_PER_DAY = 5000` cap (the 4000-char answer cap already
allows ~20 MB). It is written for cache hits and fresh generations alike, because the chart is
computed before the cache lookup. It is the seeker's own chart under matching context, never the
partner's. 0 LLM calls, so 0 Groq tokens before and after.

Privacy is by construction. The dict is built from named fields, never from the Chart, so a field
added to Chart later cannot enter it. Left out on purpose: the lagna and planet longitudes (together
they pin the birth time to minutes), nakshatra pada, the retrograde flag, dasha start and end dates
and years (the Maha balance at birth pins the Moon's longitude), and lat/lon/tz/birth_utc.

Rejected: serialising the Chart and deleting fields (a blacklist leaks whatever is added next);
including pada or longitudes (more audit precision, but they re-identify a birth moment).

A failure to build the snapshot drops the `chart` key and keeps the answer and the event.
`templates/privacy.html` discloses it in the activity-log paragraph.
