# A Vivah groom on his own Janma day is no longer a Tara pass; the bride's is, following Raman's Muhurtha

- **Date:** 2026-11-11
- **PR / issue:** #714 (last slice; follows `2026-11-10-714-janma-disclosure` work, which disclosed the grade and changed none)

## Why, measured

Until now `_TARA_BALA_NAMES[1]` graded Janma "ok" and `_couple_verdict` counted "ok" as a pass for
both partners, so a groom on his own birth-star day could read `good-for-both`. That grade was an
unsourced simplification. Raman, *Muhurtha or Electional Astrology* (1948), is held in
`data/matching/` (one of seven books present when checked; the Raman djvu text was read directly,
the three PDFs present could not be searched, so no absence is claimed from them). Quoted with line
numbers in `knowledge/vedic_reference.md` 2A-ter:

- lines 1063-1066: "it is no doubt advisable to avoid a day that is ruled by the 1st, 3rd, 5th and
  7th constellations" (OCR `5tli`);
- lines 1081-1082: a Janma day "is ordinarily held to be unfavourable for an election";
- lines 1087-1088: Janma is "inauspicious for war, sexual union, shaving, taking medical treatment,
  travel and marriage";
- lines 1098-1099, after a page break (the book's own index, line 9123, lists "Woman's janma
  Nakshatra ... 23"): "For a woman, Janma Nakshatra would be quite favourable for marriage".

Astro-auditor ruled that the sentence at lines 1083-1086 ("nuptials ... Janma Nakshatra is
favourable without exception") **must not be cited for weddings**: the same passage lists
"marriage" as inauspicious, Raman uses "nuptials" elsewhere for the first-union ceremony
(lines 1781-1786, and line 967 lists "marriage, nuptials, entry into new houses" as three items),
and the nuptials star list at lines 1845-1862 says the Janma star should be avoided. The book
contradicts itself on that word.

## What changed

`_couple_verdict` reads a groom whose `tara_bala_name` is Janma as `avoid` for its Tara test, keyed
on `_JANMA_TARA_NAME = _TARA_BALA_NAMES[1][0]` rather than a second spelling. So groom-Janma with a
bride on `avoid` is `avoid`; groom-Janma with anyone else is `mixed`, never `good-for-both` or
`excellent-for-both`. A bride on her own Janma day still passes. Position 1 also covers the 10th and
19th stars from the birth star (the count is mod 9); Raman's nuptials list names all three
(lines 1860-1862), and the page says so.

The finder's "Tara Bala, Janma" paragraph is rewritten to say exactly this, to say the personal match
still shows "ok", and to say the finder reads whole-day nakshatra, so it does not apply the
ghati-level exception Raman allows "only under special circumstances when an election is to be
urgently made" (lines 1066-1079). The Janma ghati count is not independently confirmed in the
scan (the worked Vipat example fixes 7; the Janma "first" is read as one ghati), so the page names
no number.

Measured on two real charts (groom 1992-08-02 06:30 Delhi, Moon in Uttara Phalguni; bride
1995-03-14 12:00 Delhi), 2026-11-12 to 2027-02-10, Delhi: ten days were groom-Janma and two
flipped, 2026-12-30 and 2027-01-26, each `good-for-both` before and `mixed` after; the other eight
were already `mixed` (a weak Chandra or an avoid bride grade) and did not move. Both are rated
`avoid` by the universal event score, so the couple verdict is the second opinion there, not the first.
Those two days are Kharmas, so the page folds them away; to see the change on the rendered page, the
same bride with a groom born 1993-11-03 06:30 Delhi (Moon in Mrigashira), POST `/muhurat` for
2027-02-16 (rated `excellent`): main shows `good for both` (Bride Sadhaka, Groom Janma, both Chandra
strong), this change shows `mixed`. A groom born 1990-01-10 06:30 on 2027-02-25 (bride Vadha, an
avoid): `mixed` before, `avoid` after.

## Deliberately not changed

- **Every other event.** Griha Pravesh, Namkaran, Vidyarambh, Business keep their grades: Raman gives
  different verdicts per event (line 5012: Griha Pravesh in one's Janma star "highly beneficial";
  lines 5859-5861: illness begun on it "distress"), so Janma is not graded alike for every event.
- **The single-user personal match, `_tara_bala`, and `_TARA_BALA_NAMES` grades.** Janma is still `ok`
  there, pinned in `tests/test_janma_vivah_groom.py` and `tests/test_janma_tara_disclosure.py`. The
  per-partner chip in the couple row still reads "Janma / ok" for a groom; only the combined verdict moves.
- **The Tara names.** The code names Pratyari, Sadhaka, Vadha, Ati-Mitra; Raman (lines 892-914) has
  Pratyak, Sadhana, Naidhana, Parama Mitra. The page still says the names shown are not sourced to a
  held text. Renaming is a separate finding, not made here.
- **"Avoid only when BOTH partners avoid"** in `_couple_verdict` is itself unsourced and was not
  touched; it is why groom-Janma with a passing bride is `mixed` and not `avoid`. A follow-up.
- **No regional or school variation** is claimed; the text gives no basis for one.

## Caveats on the source

The djvu OCR reads `5tli` for `5th`, `Yipat`/`Naidliana` for `Vipat`/`Naidhana`, `lOtli` for `10th`,
`Anu_ Janma` for `Anujanma`, and prints a stray quote after "ruled by" at line 1081. None changes the
sense. The Narasimha Rao muhurta checklist (knowledge `29.7`) was quoted only for "a good tara with
respect to janma nakshatra" and was not re-read for a Janma-day rule.

## Cost

0 LLM calls, 0 tokens. `_couple_verdict` is a pure function of two already-computed partner records.
