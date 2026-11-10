# The finder discloses how it grades Janma (Tara position 1); the grade is not changed

- **Date:** 2026-11-10
- **PR / issue:** #714 (partial: `refs #714`, not `closes`)

## Why, measured

At 018fce1, `_tara_bala("Ashwini", "Ashwini")` returned `(1, "Janma", "ok")` and
`_couple_verdict` with a groom on his own Janma printed `good-for-both` (bride `good`/Sampat,
groom `ok`/Janma, both Chandra `strong`; and `good-for-both` again with both partners on Janma).
`_couple_verdict` counts `ok` as passing, for every event, for either partner. The finder's help text
lists the auspicious and avoided Tara positions and says nothing about Janma. The only Janma-related
line held in `knowledge/` is `vedic_reference.md` ~L2269 (Rao: the Moon at a muhurta should be a
"good tara" from the janma nakshatra), which grades no Janma position per event. The Raman *Muhurtha*
passage #714 quotes is the issue author's transcription: `data/` held 0 of 7 books on the runner, so it
was not verified and is not relied on.

**Chief's ruling, Option A (quoted from `/tmp/chief-714.md`, the ruling on #714):** *"Option A, ship
as `partial/714-`, refs #714 (not closes). Disclose, change no grade. Clause that decided it:
Standing ruling 3, 'a user-facing claim that cannot be sourced is corrected or qualified ... Removing a
working feature is not the default remedy. Qualify first', and, between A and B, Standing ruling 4
clause 3: B changes a computed grade on a rule no held text supports, and by the issue's own quoted
passage it would demote the bride's Janma day, which that passage calls favourable."* The bound
wording: state only what the code does and what is held; **no Raman citation and no per-event claim**.

**Changed.** One English paragraph in `muhurat_finder.html`, shown when `personal_active or
couple_active` (the same condition as the Chandra Bala note): Janma is graded "ok" and counts as
passing for either partner, the grade is the same for every event and both partners, and the Tara names
shown are not sourced to a text this site holds. English only; the finder has no Hindi pair. The code
comment on `_TARA_BALA_NAMES[1]` ("variable (traditionally cautious)") was an unsourced claim of its
own and now says it is an unsourced simplification. No grade, no tara name, `_tara_bala` and
`_couple_verdict` are untouched. Tokens: 0; `git diff --stat -- src/astro_ai/prompts` is empty.

**Rejected.** Option B (vary Janma per event, or demote it): changes a computed grade on a rule no
held text supports, and would demote the bride's Janma day that the issue's own passage calls
favourable. Option C (block both halves until the corpus has the passage): it is the remainder of A,
not an alternative, and needs a corpus-loop job, not a product decision.

**Remainder, #714 stays open.** The per-event table needs Raman *Muhurtha* (Janma section) added to
`knowledge/*.md`, verified against the book with `data/` present. A grade change is then sourced and
can be ruled on again.

**Would overturn this:** Raman's per-event Janma rule landing in `knowledge/*.md`, verified against
the book. Then a per-event table is a sourced change, not a patch.

**Gate.** `tests/test_janma_tara_disclosure.py` (the sentence under personal and couple modes, absent
when neither is active, no Raman / classical / tradition wording in it, Janma still `(1, "Janma", "ok")`,
a groom on his own Janma still `good-for-both`) and five rows in
`scripts/mutations/2026_11_10_714_janma_disclosure.py`. The two grade pins are typed in: changing either
is a deliberate edit to that test.
