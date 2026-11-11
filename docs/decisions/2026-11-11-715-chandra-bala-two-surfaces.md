# Chandra Bala has two grade tables: Gochara for the Rashifal, Gochara-plus-Raman-Muhurtha for the finder

- **Date:** 2026-11-11
- **PR / issue:** #715 (muhurta 6th-house slice; follows `2026-11-10-715-chandra-bala-gochara-grades.md`, which left the 6th strong everywhere because the passage was not held)

## Why, measured

Raman, *Muhurtha or Electional Astrology* (1948), now in `data/matching/` (the only one of seven
books present when checked), lines 927-933: the Moon should not occupy "in the election chart, a
position that happens to represent the 6th [OCR `Gth`], 8th or 12th from the person's Janma Rasi".
The worked example (lines 935-951) agrees: Moon in Mesha is the 12th from Taurus, so no Chandrabala.
`knowledge/vedic_reference.md` 2A-bis now quotes it and says no more than it says: it does not call
2, 4, 5 or 9 fine, and it does not contradict the 2A Gochara row. `corpus_search.py "Chandrabala"`
finds it at line 927 (8 hits in the book).

**Chief's ruling, Option A (comment on #715):** two grade tables, one per surface. The finder
(personal match and Vivah couple verdict) marks a house weak when EITHER held source names it, so
weak = 2A {2,4,5,8,9,12} union Raman Muhurtha {6,8,12} = {2,4,5,6,8,9,12}, strong = {1,3,7,10,11}.
The Rashifal (`chandra_bala_by_rashi`, used by `routes/rashifal.py` and `routes/subscribe.py`)
keeps 2A exactly, house 6 strong, because it reads a transit for oneself and not an election.
Conditions: Rashifal grades unchanged and pinned; the knowledge text says what the passage says and no
more; the finder discloses only held content; the unheld footer is removed.

**Changed.** `_CB_GOCHARA_*` and `_CB_MUHURTA_*`, both asserted to partition 1..12 at import.
`_chandra_bala` takes a required keyword `surface` with no default, so a future caller that forgets
which question it asks gets a `TypeError`, not the wrong grade; `chandra_bala_by_rashi` says
`"gochara"`, `_personal_match_for` and `_partner_factors_for` say `"muhurta"`. The finder's Chandra
sentence names both Raman books and both house lists. Its footer now names Raman's two books
(for the Chandra Bala grades) instead of Brihat Parashara Hora Shastra, Muhurtha Chintamani and
Phaladeepika.

**Effect, measured at origin/main b68adae vs this change** (no LLM on this path, tokens 0):
- All 144 (natal rashi, transit rashi) pairs: finder surface strong 72 -> 60, weak 72 -> 84; Rashifal
  surface strong 72, weak 72 (unchanged).
- Over all 1,728 (bride Moon, groom Moon, transit Moon) triples, days where both partners are strong
  on the finder: 432 -> 300 (-31%).
- A concrete 60-day search from 2026-12-01 (Delhi, bride Moon Cancer, groom Moon Virgo): the personal
  grade changed on 5 days (2026-12-10, 12-11, 2027-01-06, 01-07, 01-08, all house 6, strong -> weak);
  weak days 31 -> 36 for the bride, 30 -> 35 for the groom. `good-for-both` stayed 4 days
  (12-26, 12-30, 01-22, 01-26) because each house-6 day was already `mixed` on tara or the other partner.
  One pair is not a rate; the 1,728-triple figure is the general effect.

**Rejected** (chief's ruling): **B**, grade 6 strong on both surfaces and only disclose the Muhurtha
rule: it keeps merged slice 1's finder grade of "strong" for a house a held muhurta source says to
avoid. **C**, withhold the whole muhurta grade until more of the corpus is read: leaves a grade the
cited election source contradicts, for no new information. **D**, use the Muhurtha set on the
Rashifal too: the Rashifal is a gochara reading, 2A (and Rao's tables, noted there) call the 6th good
for the Moon, and Raman's passage is about an election chart.

**Not done here.** Janma Tara (#714) is untouched. Other pages that name BPHS or Phaladeepika (about,
the `/learn` articles, `result.html`) are outside this issue. The finder's Tara Bala names remain
unsourced, as its own disclosure says.

**Would overturn this:** a read of Raman's *Muhurtha* (or Muhurtha Chintamani, if ever held) that
gives a different set for an election.

**Gate.** `tests/test_chandra_bala_surfaces.py` (typed sets for both surfaces, house 6 strong via
`chandra_bala_by_rashi` and weak via `_chandra_bala`/`_personal_match_for`/`_partner_factors_for`, the
couple verdict through `find_candidates`, no default `surface`), `tests/test_chandra_bala_gochara_table.py`
(re-anchored; disclosure and footer), and ten rows in
`scripts/mutations/2026_11_11_715_chandra_bala_surfaces.py`.
