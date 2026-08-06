"""Hindu festival date lookup for the daily email and the rashifal prompt.

The dates themselves live in `festival_registry.py` — that is the single
source of truth, one `Festival` record per festival carrying every year we
have. This module derives the by-date view from it at import time; to add or
correct a date, edit the registry, not this file.

Most major festivals fall on specific tithis of the Hindu calendar, so their
Gregorian date shifts each year, which is why the registry carries an explicit
year-by-year mapping rather than a rule. Append a new year each November, when
the Drikpanchang almanac releases the next year's dates.

The shape — `FESTIVALS_BY_DATE[year][YYYY-MM-DD]` → festival info — keeps
lookups O(1) per day and lets us cover year-specific quirks (e.g. some
festivals fall twice in some years due to lunar shifts). Each entry carries
`name_en` / `name_hi` / `note_en` / `note_hi` plus the registry `slug`.

Tithi-based daily observances (Ekadashi, Pradosh, Purnima, Amavasya) are
NOT here — they're computed from the day's tithi in shloks.py. This file
is only for named-festival callouts.

Reckoning conventions these dates assume:

* Location and timezone: New Delhi, IST. Festival dates are location-sensitive
  — the tithi boundary can fall on either side of local sunrise or moonrise,
  so a different city can legitimately land on the adjacent day.
* Month naming: purnimanta (North Indian). Note Diwali is amanta Ashwina
  Amavasya, which is purnimanta Kartika Amavasya — same day, two names.
* Observance window: several festivals are fixed by the tithi prevailing at a
  particular window rather than at sunrise — pradosh (dusk) for Diwali,
  nishita (midnight) for Maha Shivratri, madhyahna (midday) for Ram Navami and
  Ganesh Chaturthi, aparahna (afternoon) for Dussehra, moonrise for Karva
  Chauth. A naive "tithi at sunrise" rule will disagree with the almanac on
  those rows and it is the naive rule that is wrong, not the date.
* Regional divergence: some traditions genuinely observe a festival on an
  adjacent day. For 2026, Drik gives Ram Navami as 26 March in the Smarta
  reckoning while ISKCON observes 27 March. Both are correct within their
  sampradaya; we ship the Smarta/Drik date.

Before editing a date, verify against a published almanac AND a computed
tithi — do not adjust from memory. Nine of the original 2026 rows were off by
up to 21 days because they were entered without a source check.
"""

from __future__ import annotations

from datetime import date

from astro_ai import festival_registry


# Dates, bilingual copy and the classical rule for each festival live in
# festival_registry.py — one tuple of Festival records, verified against Drik
# Panchang plus an independent Swiss Ephemeris tithi computation. This module
# only flattens that registry into the by-date lookup shape the emails and the
# rashifal prompt expect.
FESTIVALS_BY_DATE: dict[int, dict[str, dict]] = {}
for _fest in festival_registry.FESTIVALS:
    for _year, _iso in _fest.dates.items():
        FESTIVALS_BY_DATE.setdefault(_year, {})[_iso] = {
            "name_en": _fest.name_en,
            "name_hi": _fest.name_hi,
            "note_en": _fest.note_en,
            "note_hi": _fest.note_hi,
            "slug": _fest.slug,
        }
del _fest, _year, _iso


def festival_for_date(d: date) -> dict | None:
    """Look up the festival on `d`, if any. Returns the bilingual entry or None.

    Falls back gracefully if we don't yet have entries for the year — just
    returns None so the email still sends, sans festival callout.
    """
    year_table = FESTIVALS_BY_DATE.get(d.year)
    if year_table is None:
        return None
    return year_table.get(d.isoformat())
