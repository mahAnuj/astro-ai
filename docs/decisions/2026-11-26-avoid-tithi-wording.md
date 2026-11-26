# The avoid_tithi legend says which kind of disagreement it is, and the vidyarambh dark-half sentence no longer cites "the extract we hold"

- **Date:** 2026-11-26
- **PR / issue:** #1497

## Why, measured

#1355 (see `docs/decisions/2026-11-25-dark-half-labels.md`) moved the `avoid_tithi` notes to
"contested" and wrote a vidyarambh dark-half sentence. Two defects remained in the user-facing
registry wording of `src/astro_ai/muhurat_factors.py`:

- The vidyarambh `@Krishna` sentence said "in the extract we hold", which leaks how the
  finder was built into copy a visitor reads. `grep -c "extract we hold"` was 1; it is 0 now.
- The one "traditions differ" badge covered three different things on `avoid_tithi`: two held
  tables that disagree over Purnima (vivah, griha_pravesh), an unclear figure (namkaran), and
  a list no held book gives for the event at all (business).

astro-auditor's ruling is binding (`knowledge/vedic_reference.md` section 29.13: the Griha
Pravesh table and the Vidyarambh table; `data/` was not re-read):

- `good_tithi` / `vidyarambh` / `@Krishna` stays contested. The Vedic table lists the tithi
  without naming a half; the Muhurtha list marks only its 1st as dark-half and names no half for
  the others, so neither table settles it. Reworded without the build-process phrase.
- `avoid_tithi` / `griha_pravesh` stays contested, and the note now says what differs: the
  Vedic table lists Purnima while the Muhurtha tradition's general list rejects it. Navami is
  this finder's addition; neither table rejects it for house entry.
- `avoid_tithi` / `business` moves from contested to `site_convention`. No held book gives a
  business tithi rule; the finder applies the Muhurtha general list to a new venture and adds
  Navami. The badge now reads "site convention", as the business `good_tithi` already does.

## Rejected

- Splitting the badge into several disagreement kinds: that needs a new status and a new
  rendering mechanism, for a distinction the sentence already carries.
- `site_convention` for griha_pravesh: it would hide five tithis Raman states for house entry,
  and the Purnima disagreement between the two tables is real.

## Out of scope, to be filed separately

Shashthi and Dwadashi are missing from the griha_pravesh and vivah avoid lists. Per the
auditor these are undocumented omissions: Raman's list rejects the 6th and 12th. The vivah
Dwadashi is deliberate (`muhurat.py` L746-748). Not changed here; a separate issue is to be
filed.
