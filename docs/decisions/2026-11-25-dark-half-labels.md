# The finder's dark-half tithi credit is labelled "traditions differ" wherever the sources do not name the half

- **Date:** 2026-11-25
- **PR / issue:** #1355

## Why, measured

The finder credits a good tithi without looking at the half, so Krishna-paksha Dwitiya,
Tritiya and the rest earn the same +2 as the bright half. Only `vivah` carried a dark-half label
(`@Krishna`); house entry (`griha_pravesh`) and learning the alphabet (`vidyarambh`) showed
"Good tithi" as plain sourced. The repro is `griha_pravesh`, Delhi, from 2026-11-14 for 60 days:
the row for 26 Nov 2026 (Dwitiya, Krishna) read as sourced.

astro-auditor's ruling (knowledge/vedic_reference.md only; `data/` was absent, so the books
were not re-read):

- `good_tithi` / `griha_pravesh` / `@Krishna`: contested. One table lists the tithi without
  naming a half; the Muhurtha tradition's list names the bright half, and the only dark-half
  tithi it lists is the 1st.
- `good_tithi` / `vidyarambh` / `@Krishna`: contested. The table names no half; the extract
  held does not say whether the Muhurtha list's other tithis are bright-half only.
- `namkaran` and `business` good_tithi are unchanged (sourced; site convention).
- `avoid_tithi` for `griha_pravesh`, `namkaran`, `business` and `vivah`: sourced to contested
  (the held books differ, or support the list only in part). The griha and business sentences
  now name the sourced tithis (4th, 8th, 14th, New Moon, Full Moon) and say Navami is this
  finder's own addition. `vidyarambh` stays sourced.

**Krishna Pratipada is a non-issue.** The issue asked about it, but "Pratipada" is in no
event's `good_tithis`, so the finder never credits it in either half; there is nothing to
label. A test pins that over the real `EVENT_RULES`. Raman lists it for house entry and the
finder gives it no credit: a possible under-credit, out of scope here.

**Precedence swap.** `_soft_items` tried `@Krishna` before the tithi, so a vidyarambh Krishna
Dwadashi resolved to the half-wide entry and its own, more specific "Dwadashi" entry (the
tables list it, the Muhurtha list rejects it) was unreachable. The tithi is now tried first.
Both are contested, so the visible status is the same; the sentence is the more specific one.

## Rejected

- A composite `Dwadashi@Krishna` key: a second lookup grammar for one cell; the swap is one
  line and keeps the `when` keys plain.
- A `Pratipada` key: there is no credit to qualify.
- Splitting Navami into its own avoid-list entry: the ruling words it inside one sentence.
- Touching `muhurat.py`: the scoring is unchanged; only the label on the credit is. The page
  gives no weight to the half.

## Expected visible effect

Every auspicious row for `vivah`, `griha_pravesh`, `namkaran` and `business` now shows
"traditions differ" on "Not an avoided tithi" (it was "sourced"); Krishna-half rows for
`griha_pravesh` and `vidyarambh` show the same on "Good tithi". Grades and scores do not change.
No LLM call and no prompt is touched: 0 tokens.

Out of scope, noted for later: Shashthi and Dwadashi are omitted from the griha_pravesh and
vivah avoid lists.
