# /muhurat/vivah lists the next five auspicious dates with the finder's Abujha rows dropped, beside a disclosure of what the finder does not check

- **Date:** 2026-11-21
- **PR / issue:** #1017 (slice 8, refs not closes: R3, R4, R6, F1/F2 remain)

## Why, measured

Vivah is the fifth member of the #1325 landing allow-list. It supersedes only the sentence
"vivah is left unchanged until #1026" in `2026-11-21-muhurat-landing-dates.md`; that file is
NOT edited. Same pattern: `_landing_upcoming`, `hot_cache.get_or_compute`,
`muhurat_landing.html#next-dates`, no new route, module or cache layer. `muhurat.py` is not
touched.

**The auditor's ruling.** The vivah finder's day-level rules (weekday, tithi, nakshatra, nitya
yoga, Panchak, a few almanac conventions) are sourced enough to list dates, with one exception
and one disclosure, below.

**The exception: Abujha rows are dropped.** In `muhurat.py` the finder's Abujha branch
`continue`s past `score_event` and every hard exclusion. Verified on this tree (2026-11-21,
New Delhi): the row for 2026-11-21 (Shukla Dwadashi, Revati) is rated `excellent` through that
override although the same date is a Panchak day, a Dwadashi and a Saturday. That is a RULE
defect in the finder, filed as #1346, and it is not fixed here: it changes every event and a
documented griha-pravesh behaviour, and it would collide with open PR #1342, which edits
`muhurat.py`. Here it is worked around at DISPLAY time only: `LANDING_EXCLUDE_FLAGS =
{"vivah": frozenset({"abujha_muhurat"})}` in `routes/muhurat.py`, applied before the
`[:LANDING_SHOW]` slice so the page still lists five. `find_candidates` is called exactly as
before, nothing new is stored, and the finder page keeps showing those rows. One dict entry to
delete when #1346 is fixed.

**Why only vivah.** The ruling is vivah-only and says the other four must not change. Measured
today, griha_pravesh, vidyarambh and business each hold one Abujha row in their 90-day
auspicious list (2027-02-11, Basant Panchami, Revati), namkaran none; none is inside today's
earliest five, so the filter would not change a page today but would change them once that date
enters the earliest five (about mid-January 2027). So the four live pages will show the same
unfiltered Abujha row from about 2027-01 until #1346 is fixed.
`test_the_abujha_exclusion_is_vivah_only` pins the four as unchanged, and #1346's fix changes
that test deliberately.

**The disclosure.** One static `<p>` inside `#next-dates`, directly after the provenance line,
vivah only (`{% if event_key == 'vivah' %}`), no interpolation, no `|safe`. It says the finder
checks the day only and does not read the lagna or the 7th house; quotes Rao's table of muhurta
guidelines ("These are merely guidelines and not final recommendations"), and that planetary
strength matters more than the thumb-rules; names the almanac conventions as not from the
texts this site is built on; and calls a listed date a starting point for a priest. It is inside
the section on purpose: when the list is omitted (no auspicious date, or a failure) the caveat
goes too, since there is nothing to disclaim. Sentence 1 of the auditor's text is the existing
provenance line, a superset (it adds the zone and the 90-day window), so it is not printed twice.

**The Rao quote and where it is sourced.** `knowledge/vedic_reference.md` (Rao, Table 79:
"These are merely guidelines and not final recommendations", Rao line 16053, and "Planetary
strength is more important than strictly following these thumbrules", line 16064) and
`knowledge/grahas.md`, which describes Table 79 as "Muhurta guidelines", a table of eight tasks
with the wedding among them, NOT a table of wedding conditions. Hence "Rao's table of muhurta
guidelines, weddings included", and the second claim is an unquoted paraphrase. A test reads the
quoted fragment out of `vedic_reference.md`, so it cannot be reworded off-corpus. `data/` was
absent, so this is checked against the corpus transcription, not the book.

**Sentence 3 is reworded, and why.** As ruled it ended "... are not in the classical texts this
site is built on". `tests/test_muhurat_classical_copy.py` fails any `<p>` or `<li>` sentence that
contains "classical" together with `chaturmas|kharmas|dagdha|sarvartha|abujha|...`, and its
`test_the_real_routes_render_the_disclosure` renders exactly `/muhurat/vivah`. The sentence
disclaims the claim; the gate cannot tell. Weakening that regex is a gate change, so the
sentence says "come from common almanac practice, not from the texts this site is built on".
Meaning unchanged. If "classical" is wanted back, the route is a reviewed change to that test,
as its own issue.

**Cost, measured** (`find_candidates('vivah', 'New Delhi, India', 2026-11-21, 90)`): 90 rows,
14 auspicious (2 of them Abujha, so 12 listable), 1 caution. 0.51 s on a first call in a
process that had not computed vivah before and 0.13 s on the second (the architect measured 1.47
s in a fresh process including ephemeris warm-up). 0 GCS ops, 0 LLM tokens per call and per day,
no paid service. Five events now compute at most once per instance per IST day. A failure omits
the section and keeps HTTP 200 (existing `except Exception`, cached `ERROR_TTL_S`).

**Rejected.**
- The Abujha filter on all five events: changes four live pages beyond the ruling, with no rule
  basis recorded for them; the real fix is #1346.
- Fixing the precedence in `muhurat.py` here: a RULE change for every event, collides with #1342.
- A parameter on `find_candidates`: touches `muhurat.py` and the finder's own results.
- The disclosure text in `EVENT_LANDING` or in the cached dict: `muhurat.py` is off-limits, and
  cached text is a second copy of copy that the copy gate does not read.
- The disclosure on all five landings: the other four's rules were sourced in #1058, and the
  lagna and 7th-house caveats would be noise there.
- Warming vivah at startup, computing on the event loop, `get_or_refresh`: same rejections as
  `2026-11-21-muhurat-landing-dates.md`.
- Exempting the sentence in `test_muhurat_classical_copy.py`: weakens a gate for one word.

**Not done.** Observed, not changed: the first listed row (a Wednesday, Pratipada, Rohini) is
`excellent` only through the Sarvartha Siddhi booster, and Pratipada is in neither the vivah good
nor avoid tithi set; 2026-12-12 is a Saturday listed as `acceptable`. Boosters overriding the
day-level rules is the family #1021 and #1023 describe, not this slice.
