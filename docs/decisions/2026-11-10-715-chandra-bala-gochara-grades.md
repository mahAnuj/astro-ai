# Chandra Bala grades the Moon's house from the held Gochara table, in two grades

- **Date:** 2026-11-10
- **PR / issue:** #715 (partial: `refs #715`, not `closes`)

## Why, measured

At 50ceff8, `_chandra_bala` from Aries printed `['neutral', 'neutral', 'strong', 'neutral']` for
houses 2, 5, 6, 9: three of twelve houses (25%) carried a grade that no held source has.
`_couple_verdict` counted `strong` and `neutral` as passing, so a Vivah day with either
partner's Moon in the 2nd, 5th or 9th from the natal Moon could read "good for both".
`knowledge/vedic_reference.md` 2A (Raman, *Astrology for Beginners*, Ch. XII) gives the Moon row
as benefic 1, 3, 6, 7, 10, 11 and malefic 2, 4, 5, 8, 9, 12, and states that Raman has "no
neutral third category".

**Chief's ruling, Option A (quoted from the ruling comment on #715):** *"Option A, shipped as
`partial/715-`, `refs #715`, not `closes`. Clause: Standing ruling 3 ('A user-facing claim that
cannot be sourced is corrected or qualified'; authenticity wins on the claim) and ruling 4
clause 5 (one source of truth: derive the grade from held 2A, do not keep a category the
source says does not exist)."* Disclosure wording was bound: state only what is held, no claim
about muhurta traditions, no BPHS.

**Changed.** `_CHANDRA_BALA_WEAK` is `{2, 4, 5, 8, 9, 12}`; `_chandra_bala` returns `strong` or
`weak` and nothing else; an import-time assertion requires the two sets to partition 1..12.
`_couple_verdict` passes only `strong`. The dead Hindi `neutral` mapping and colour entries were
removed from `rashifal_single.html`, `_rashifal_card_content.html`, `email/daily_rashifal.html`
and `muhurat_finder.html`. Two template comments still crediting BPHS for the house lists were
corrected. The finder prints one sentence (personal or couple mode) naming Raman's Gochara table
and the two house lists. English only: the finder has no Hindi pair.

**Effect on readers.** Houses 2, 5 and 9 now show `weak` (rashifal page, card, email) and no longer
pass the couple verdict. Rashifal prose prompts are unchanged: no file under
`src/astro_ai/prompts/` moved, and `scripts/rashifal_brief.py` / `publish_rashifal.py` do not read the
Chandra grade (`grep -ic chandra`: 0 in `publish_rashifal.py`; 1 in `rashifal_brief.py`, a comment only). Tokens: 0. Cached readings are unaffected; the grade is
rendered by templates, not generated.

**Not sourced, not changed.** #715's second half, that the muhurta surface should treat the 6th
house as unfavourable, rests on a Raman *Muhurtha* passage that is not in `knowledge/*.md` and
`data/` was absent on the runner (0 of 7 books). The 6th stays `strong` everywhere. It needs the
corpus loop to add the passage before anyone rules on it. The finder's footer line "Sources:
Brihat Parashara Hora Shastra, Muhurtha Chintamani, Phaladeepika" is a separate unheld
attribution left from #716 and is not touched here.

**Rejected.** Option B (keep `neutral`, label it): still lets an ungrounded grade decide Vivah
days. Option C (block both halves): no new information, and no corpus loop had run in four
days. A "muhurta texts differ" disclosure: as unsourced as the category removed.

**Would overturn this:** Raman's *Muhurtha*, once added to `knowledge/` and read, giving a
different Chandra Bala set for marriage; rule from that then.

**Gate.** `tests/test_chandra_bala_gochara_table.py` (typed-in expected sets, per house 1..12,
no neutral on any natal/transit pair, the couple verdict, the rendered disclosure) and seven rows
in `scripts/mutations/2026_11_10_715_chandra_bala.py`.
