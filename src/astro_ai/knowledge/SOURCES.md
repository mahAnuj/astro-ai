# Knowledge Extraction — Source Audit & Plan

Living document tracking what's been extracted from each source PDF,
what's still pending, and how new articles should cite them.

**Last updated:** 2026-08-08

---

## Available source PDFs (all in `/data/`, gitignored)

**All counts below are plain `pdftotext` (no `-layout`), re-measured 2026-08-08.** This
matters: an earlier revision of this table mixed `-layout` and plain counts, which made its
total meaningless. `-layout` reflows columns and yields ~30% fewer lines. Always state the
flag alongside a count.

The two OCR-blocked scans (`varahmihirHorasastram.pdf`, `Numerology.pdf`) have been
**deleted from `data/`**. Nothing in the corpus now requires OCR.

| # | File | Author | Text lines | Status | Priority |
|---|------|--------|------------|--------|----------|
| 1 | `Astrology For Beginners BVRaman_text.pdf` | BV Raman | 15,409 | ✅ **Fully extracted** | Done |
| 2 | `vedic_astro_textbook.pdf` | P.V.R. Narasimha Rao | 20,669 | 🟡 **Partially cited** (Ch. 34 remedies; **§4.3 Other Upagrahas / Table 10 → `vedic_reference.md` §28**, 2026-08-26) | HIGH — full extraction pending |
| 3 | `book1-for-CD.pdf` | P.V.R. Narasimha Rao (Lessons Vol. I) | 12,244 | ❌ Not extracted | MEDIUM |
| 4 | `Astrology-e-book-compressed.pdf` | Chennareddy Vasudev | 5,220 | ❌ Not extracted | LOW (introductory) |
| 6 | `Numerology-With Tantra, Ayurveda, and Astrology.pdf` | Harish Johari (Destiny Books / Inner Traditions, 1990) | 5,952 | 🟡 **Partially extracted** → `numerology.md` §1-§12 | MEDIUM |
| 7 | `Numerology-You.pdf` | Jayant Kumar, *Numerology & You* (Educreation, ISBN 978-1-61813-620-6, 2016) | 1,110 | 🟡 **Sample copy only** — 43 pp; Ch. 1-2 extracted → `numerology.md` §2.5, §12.5-§12.9. Ch. 3-24 not in the sample | LOW (blocked by source) |
| 9 | `Numerology the Complete Guide, Volume 1-The Personality Reading.pdf` | Matthew Oliver Goodwin, *Numerology: The Complete Guide, Vol. 1 — The Personality Reading* (Newcastle Publishing, North Hollywood, 1981) | **28,171** | 🔴 **Not yet extracted** — added 2026-08-08. Largest numerology source we hold | **HIGH** (#191) |

*(Numbers 5 and 8 are retired — the deleted scans. Row numbers are kept stable so older
issue comments referencing "source 9" still resolve.)*

### Kumar (source 7) declares its own school — use it

Line 815 of the extraction opens a section titled **"Chaldean And Pythagorean System"**:

> "In this book, Chaldean Numerology has been used to determine Alphabetical numbers."

It also names the **Karmic Debt numbers (13, 14, 16, 19)** and **Master numbers (11, 22,
33)** outright. Both are inside the 43-page sample, so both are citable. This bears
directly on the numerology-table issues (#160/#163/#167) and on `_karmic_debt_flags`.

### Note on source 9 (Goodwin) — read this before citing it

**It is Western/Pythagorean, not Vedic.** Measured hit counts across its 28,171 lines:

| present | absent |
|---|---|
| Life Path 387 · Expression 482 · Soul Urge 241 · Master Number 105 · Karmic Debt 102 | Chaldean **0** · Pythagorean **0** · Lo Shu **0** · Rudraksha **0** · Personal Year **0** · compound number **0** |

So it can settle the Western-school questions (#161 Karmic Debt intermediates, #164/#169/#179 master-number policy) and **nothing** about Lo Shu (#172), Rudraksha (#173), or Johari's compound-number table (#160).

**Its decisive contribution is #162.** Goodwin, line 1989 of the extraction, states the reduction rule verbatim:

> "Always add the numbers after separately determining the number representing the month, day and year. If you add them all…"

— followed by a worked example (March = 3; 12 = 1+2 = 3; 1940 = 1+9+4+0). **That is exactly the method `numerology.py` implements**, which Johari contradicts (§2.2, sum all digits).

**This does not make our code "correct" — it makes #162 a properly sourced two-school divergence.** Both schools are now citable in-repo. Under the project's sourcing rule the defect is therefore the **silence**, not the value: the page must declare which school it follows. Citing a 1981 Californian Western text as the authority for a reading advertised as *Vedic* would be its own error — Goodwin evidences that our method is legitimate practice, not that it is the Vedic method.

**Total text-searchable content available:** **88,775 lines across 7 PDFs**, all readable
(Goodwin 28,171 · Rao textbook 20,669 · BV Raman 15,409 · Rao Lessons 12,244 · Johari 5,952 ·
Vasudev 5,220 · Kumar 1,110).

**Nothing is OCR-blocked any more.** The two scanned PDFs were deleted; #178 is now
acquisition-only (finding a text-layer Varahamihira), not an OCR spike.

**Unextracted, ~66,000 lines:** Goodwin 28,171 · Rao textbook (most of 20,669) · Rao
Lessons 12,244 · Vasudev 5,220 · Johari beyond §12. Tracked in **#191** — this is the whole
of the remaining corpus work, and it needs no tooling we do not already have.

### Known gaps in the numerology corpus

Recorded during the 2026-08-08 `astro-auditor` pass over `numerology.py`, so the next
audit does not re-derive them:

- **Lo Shu 3×3 grid** — implemented in `numerology.py` and rendered on `/numerology`,
  but absent from both numerology books above. `numerology.md` §13.2 flags it as
  Chinese-tradition material needing a Feng Shui source; §13.3 assigns Cheiro to
  *compound numbers*, not to Lo Shu. Cheiro's *Book of Numbers* is **not in `data/`**
  and has not been read. See issue #172.
- **Per-number Rudraksha mukhi mapping** (`numerology.md` §11, Rudraksha column) — does
  not trace to Johari: `grep -i rudraksha` over the Johari extraction returns 2
  incidental prose mentions and no per-number table. Source unlocated. See issue #173.
- **Life Path reduction method** — `numerology.md` §2.2 documents "sum all digits of
  DOB" and Johari states it verbatim ("The single whole number obtained from the
  addition of the date, month, and year of birth", ch. "Destiny Number"). The
  reduce-components-separately method that `numerology.py` implements is real modern
  practice but is **not sourced anywhere in this repo**. See issue #162.
- **Symmetry of the §7 compatibility pairs** — §7 lists several pairs (1↔8, 5↔6, 3↔5)
  as friendly under one number's row and as enemies under the other's. Needs a pass
  against Johari's per-pair sections before any code table is regenerated from it.
  See issue #163.

---

## Rao textbook (`vedic_astro_textbook.pdf`) — chapter map

The most systematically-organised source. 407+ numbered sections.

**Sections extractable now (highest ROI):**

- **Ch. 1** — Introduction: grahas, rasis, bhavas, nakshatras, tithis, ayanamsa, dasha overview
- **Ch. 2** — Rasis in detail: characteristics, elements, gunas, directions, indications (2.1–2.3+)
- **Ch. 3** — Planets in detail: characteristics, Vishnu avatars, benefics/malefics, deities, gunas, abodes (3.1–3.2.11+)
- **Ch. 4-5** — Bhavas (houses) and their significations
- **Ch. 6-8** — Vargas (divisional charts) in Rao's canonical treatment
- **Ch. 9-15** — Yogas, doshas, Ashtakavarga
- **Ch. 16-25** — Dasha systems (Vimshottari, Yogini, Chara, others)
- **Ch. 26-33** — Predictive techniques, timing, muhurta
- **Ch. 34** — Remedies (**already partially cited in vedic_reference.md §7A**)
- **Ch. 35+** — Practical case studies, birthtime rectification

**Sections priority for MD extraction:**

| Priority | Chapters | Target MD file |
|----------|----------|----------------|
| P0 | Ch. 2 (Rasis) | Extend existing `rashis.md` with Rao's finer classifications |
| P0 | Ch. 3 (Planets) | New `grahas.md` (currently we have per-planet articles but no consolidated ref) |
| P1 | Ch. 4-5 (Bhavas) | Extend existing `houses.md` with Rao's Vishnu-limb assignments and finer rules |
| P1 | Ch. 9-15 (Yogas/Doshas/Ashtakavarga) | New `yogas.md` + expand `vedic_reference.md §4` |
| P2 | Ch. 6-8 (Vargas) | Extend existing `divisional_charts.md` |
| P2 | Ch. 16-25 (Dashas) | New `dashas.md` (consolidate all dasha systems, not just Vimshottari) |
| P3 | Ch. 34 (Remedies) | New `remedies.md` (deferred from BV Raman since Raman is thin here) |

---

## Rao Lessons Vol. I (`book1-for-CD.pdf`) — likely coverage

Rao's teaching material, 12,244 lines (plain `pdftotext`). Companion to
the textbook. Likely reinforces the same material with worked chart
examples.

**Extraction approach:** cross-reference with the main textbook.
If Lessons Vol. I provides clearer worked-example versions of textbook
chapters, cite the lesson-version for teaching-oriented articles.

---

## Chennareddy Vasudev e-book (`Astrology-e-book-compressed.pdf`)

Introductory text, 5,220 lines (plain `pdftotext`), 2019 publication.
Likely covers
origins, purpose, philosophical framing of astrology. Useful for
philosophical/introductory articles but not the primary source for
technical extraction.

**Extraction approach:** skim for philosophical framings we might
want to reference in "why astrology" or history-oriented articles.
Not a primary extraction priority.

---

## Varahamihira Hora Sastra — not in the corpus

**Not held.** `varahmihirHorasastram.pdf` was a scan with no text layer
and has been **deleted from `data/`**. There is no OCR work to plan here:
nothing in the corpus requires OCR, and #178 is acquisition-only — the
task is finding a Varahamihira edition that already carries a text layer,
not building an OCR pipeline for one we no longer have. Do not propose
`tesseract` or a cloud-OCR spike for this book.

**Meanwhile:** Varahamihira is heavily quoted in every other classical
source. Rao's textbook cites him. BV Raman cites him. So we get
Varahamihira's rules *indirectly* through the extracted sources —
just not with original verse citations.

---

## Citation convention

When writing articles or extending reference MDs, cite the source
inline like the existing pattern:

- `[BV Raman, Ch. II, p. 15]`
- `[Rao, Vedic Astrology: An Integrated Approach, §3.2.5]`
- `[Rao Lessons Vol. I, Lesson 12]`
- `[BPHS] / [Phaladeepika]` — when the rule is universally cited and
  attributed to the original classical text (Rao and Raman are the
  proximate sources but the rule itself is from BPHS/Phala)
- `[Vasudev, Origin & Purpose of Astrology, p. 42]`

Never cite Varahamihira directly — we do not hold the text (see above).
Cite the proximate source that quotes him instead.

---

## Extraction workflow

Same pattern that worked for BV Raman.

**Quote the flag with every line number.** Plain `pdftotext` and
`pdftotext -layout` produce different line counts for the same PDF —
`-layout` reflows columns and yields roughly 30% fewer lines. Every count
and every citation range in this file and in `knowledge/*.md` is **plain
`pdftotext`** (no `-layout`), measured 2026-08-08. A range extracted under
`-layout` will not resolve against them. Earlier versions of this file
mixed the two, which is the only reason its figures disagreed with
`CLAUDE.md`.

1. `pdftotext <file>.pdf /tmp/bhagya-pdfs/<name>.txt` — no `-layout`, so
   the line numbers match the counts above. Use `-layout` only for an
   ad-hoc look at a table, never for a range you intend to cite.
2. Survey structure with `grep -n "^Chapter\|^\s*[0-9]\+\.[0-9]"`
3. Read relevant sections with `sed -n '<start>,<end>p'`
4. Write MD in `knowledge/` matching the citation style above
5. Commit each MD separately with source scope in the commit message

Each MD file should be reviewable in isolation (200-500 lines is the
sweet spot). Larger topics get split into sibling files rather than
one giant file.

---

*This document should be updated whenever a new extraction commits or when a source proves unusable.*


---

## Note on `corpus_search.py` line numbers (added 2026-08-26)

`scripts/corpus_search.py` numbers lines with `str.splitlines()`, which splits on
**form feeds** as well as newlines. `vedic_astro_textbook.pdf` alone contains 515 form
feeds, so the tool's reported line numbers run ahead of `grep -n` / `sed -n` by roughly
one per PDF page — measured +53 at line ~1688 and +55 sixty lines later.

**A line number copied from `corpus_search` output cannot be located again with
`sed -n 'Np'`.** When recording provenance, re-take the number with `grep -n` against the
`.corpus-cache/` file, or cite the PDF page instead. Hit *counts* and `--absent` verdicts
are unaffected; only the line numbers are.

## Note on `data/` completeness in ephemeral environments (added 2026-08-26)

`data/` is gitignored, so a fresh checkout or sandbox may hold **a subset** of the seven
books. An audit run there produces absences that are absences *over that subset only*.
Always state which books were present alongside any `--absent` result — `corpus_search`
prints the list in its header, so paste it. The #150 ruling was made with **one** book
present (`vedic_astro_textbook.pdf`), and two of its three verdicts are pending B.V.
Raman's *Muhurtha or Electional Astrology* (1948) being restored to `data/`.
