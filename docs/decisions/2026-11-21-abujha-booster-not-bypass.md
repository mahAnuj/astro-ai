# An Abujha date is a booster applied after the hard exclusions, never a branch that skips them

- **Date:** 2026-11-21
- **PR / issue:** #1346, #1354 (closes both). Related: #1342 (edits the same hunks of `muhurat.py`), #1017 (the landing and registry slices that carried workarounds)

## Why, measured

`find_candidates` had a branch that returned an `excellent` row for any Abujha date and
`continue`d, so `score_event` and every hard exclusion never ran for it. Measured on this tree
(New Delhi, 2026-11-21): the Tulsi Vivah row for 2026-11-21 (Shukla Dwadashi, Moon in Revati)
was rated `excellent` for marriage while the same date is a Panchak day (Raman's Muhurtha
rejects the last quarter of Revati and the Nakshatra Panchaka,
`knowledge/vedic_reference.md` 2638-2648 and 3087), a Dwadashi (2587-2596) and a Saturday.
The row's reason said "universally auspicious" beside a disclosure that no book the site holds
names Abujha (`knowledge/vedic_reference.md` 29.14, UNSOURCED): that is #1354.

**The astro-auditor's ruling (2026-11-21, binding).** Abujha is a regional almanac custom, not
sourced. It may lift a day that passed the sourced exclusions and may never waive one. So it is
a BOOSTER inside `score_event`, applied after the exclusion block, with Sarvartha Siddhi
semantics: caution to good, acceptable or good to excellent, never lowers, one lift shared with
Sarvartha Siddhi and Ravi Yoga (a day with two of them is lifted once). The flag
`abujha_muhurat` is set only when the day reaches the booster step, so it never sits on a row
that failed an exclusion. A day that fails an exclusion stays in the list as an ordinary
`avoid` row with the exclusion's own flag and reason plus one sentence that the finder does not
waive that exclusion for an Abujha date.

**Measured outcome.** Every Abujha date-event pair from 2026-11-20 to 2027-12 (16 pairs:
vivah 7, griha_pravesh 4, business 4, vidyarambh 1) comes out `avoid` after the fix: Panchak on
five of the vivah ones (2026-11-20, 2026-11-21, 2027-02-11, 2027-11-10, 2027-11-11), an avoided
tithi on 2027-05-09, Shukra combust on 2027-07-12. The branch stays reachable: of the 88 pairs
from 2026-11-20 through 2033, 5 pass (2028-04-27 Akshaya Tritiya for vivah, griha_pravesh and
business; 2033-05-01 for vivah and griha_pravesh), and 2028-04-27 business is a real lift,
acceptable to excellent. The tests use that real date, not a monkeypatch. Auspicious rows in the
landing window (2026-11-21, 90 days, New Delhi, excellent+good counts before to after):
vivah 11 to 9, griha_pravesh 11 to 10, vidyarambh 17 to 16, business 8 to 7, namkaran
unchanged. The landing pages' counts of all auspicious ratings (the `ARCHITECTURE.md` row):
vivah 14 to 12, griha_pravesh 16 to 15, vidyarambh 21 to 20, business 11 to 10, namkaran 19.
0 LLM calls, 0 GCS operations: `score_event` runs once on at most about five days a year.

**What follows from it.**
- `explain()` loses its Abujha early return: an Abujha row now carries a real cleared list (the
  exclusions the event applies, derived from its rules), the Abujha item first, then the soft
  points, then the real Siddha and Ravi boosters. `ABUJHA_NOTE` says the checks WERE run. A
  failing row is an ordinary restricted row with no disclosure and no "Why this date".
- The vivah-only `LANDING_EXCLUDE_FLAGS` display filter is deleted, mechanism and entry: the
  finder no longer rates a Panchak day excellent, so there is nothing to hide, and the other
  four landing pages would have shown the 2027-02-11 row from about mid-January 2027.
- Tests whose premise is gone are replaced, not renamed; the PR lists each removed test name.

**Supersedes, without editing them.** `2026-11-21-muhurat-factor-registry.md`: its paragraph
"Abujha rows get an honest override" (the branch skips every exclusion, so the explanation
lists nothing cleared and the note says "the usual exclusion checks were not run"), and its
remark that Abujha rows for the other events appear unfiltered until #1346.
`2026-11-21-vivah-landing-dates.md`: the display filter `LANDING_EXCLUDE_FLAGS`, its
"why only vivah" paragraph and `test_the_abujha_exclusion_is_vivah_only`.

## Rejected

1. **A second exclusions list inside `find_candidates`, run before the override.** A hand
   written copy of `score_event`'s exclusions that drifts from it (the #163 shape); the auditor
   ruled booster.
2. **Abujha appended to the `boosters` tuple.** It leaks into `MuhuratCandidate.boosters`,
   which the page renders as a Siddha "boost" and `explain` maps through `_BOOSTERS`. It is its
   own keyword, `abujha_name`.
3. **Amrit-style always-excellent.** The ruling says Sarvartha semantics (see the choice below).
4. **Keeping the landing filter, or leaving `LANDING_EXCLUDE_FLAGS` empty.** A dead mechanism
   that hides the finder's own verdict.
5. **Editing the roughly fifteen `return "avoid"` sites to carry the suffix, or wrapping
   `score_event`.** The one caller, `find_candidates`, appends the suffix itself.
6. **Deleting `_ABUJHA_RULES`.** Outside the ruling; `verify_muhurat_tables.py` and
   `verify_learn_article_dates.py` read `_abujha_days`.

## The one choice the owner may overturn

The rating TIER an Abujha date gets is a finder convention, not a sourced rule: Sarvartha
Siddhi semantics (a lift of one step, never lowering, shared with the other lifts). The
alternative is "excellent for every date that passes the exclusions". The difference is small
today (the only passing pairs through 2033 are already excellent, bar 2028-04-27 business,
acceptable to excellent), but it changes how a future date with a weak soft score reads.
Changing it is one line in `score_event`'s booster block and one parametrised test.
