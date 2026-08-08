# Knowledge Extraction — Source Audit & Plan

Living document tracking what's been extracted from each source PDF,
what's still pending, and how new articles should cite them.

**Last updated:** 2026-08-08

---

## Available source PDFs (all in `/data/`, gitignored)

| # | File | Author | Text lines | Status | Priority |
|---|------|--------|------------|--------|----------|
| 1 | `Astrology For Beginners BVRaman_text.pdf` | BV Raman | 5,390 | ✅ **Fully extracted** | Done |
| 2 | `vedic_astro_textbook.pdf` | P.V.R. Narasimha Rao | 16,724 | 🟡 **Partially cited** (Ch. 34 remedies) | HIGH — full extraction pending |
| 3 | `book1-for-CD.pdf` | P.V.R. Narasimha Rao (Lessons Vol. I) | 7,757 | ❌ Not extracted | MEDIUM |
| 4 | `Astrology-e-book-compressed.pdf` | Chennareddy Vasudev | 4,558 | ❌ Not extracted | LOW (introductory) |
| 5 | `varahmihirHorasastram.pdf` | Varahamihira (~6th C) | **0 (scanned images)** | ⚠️ **Needs OCR** | HIGH but blocked |
| 6 | `Numerology-With Tantra, Ayurveda, and Astrology.pdf` | Harish Johari (Destiny Books / Inner Traditions, 1990) | 5,952 | 🟡 **Partially extracted** → `numerology.md` §1-§12 | MEDIUM |
| 7 | `Numerology-You.pdf` | Jayant Kumar, *Numerology & You* (Educreation, ISBN 978-1-61813-620-6, 2016) | 1,110 | 🟡 **Sample copy only** — 43 pp; Ch. 1-2 extracted → `numerology.md` §2.5, §12.5-§12.9. Ch. 3-24 not in the sample | LOW (blocked by source) |
| 8 | `Numerology.pdf` | Unidentified (Adobe Scan capture; no title/author metadata) | **0 (scanned images, 180 pp)** | ⚠️ **Needs OCR** — author unknown until OCR'd, so nothing from it is citable. **Permanently out of scope** (#178) | — |
| 9 | `Numerology the Complete Guide, Volume 1-The Personality Reading.pdf` | Matthew Oliver Goodwin, *Numerology: The Complete Guide, Vol. 1 — The Personality Reading* (Newcastle Publishing, North Hollywood, 1981) | **28,171** | 🔴 **Not yet extracted** — added 2026-08-08. Largest numerology source we hold | **HIGH** (#191) |

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

**Total text-searchable content available:** **~69,700 lines across 7 readable PDFs**
(BV Raman 5,390 · Rao textbook 16,724 · Rao Lessons 7,757 · Vasudev 4,558 · Johari 5,952 ·
Kumar 1,110 · Goodwin 28,171).
**Blocked:** Varahamihira (48MB scanned images) requires OCR and is spike-gated (#178). `Numerology.pdf` (59MB scanned) is **permanently out of scope** — no title/author metadata, so even a flawless OCR would be uncitable.

**Readable but unextracted (no OCR needed, ~44,000 lines):** Goodwin 28,171 · `vedic_astro_textbook.pdf` 16,724 remaining · Johari beyond §12. Tracked in #191 — mine these before considering any OCR.

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

Rao's teaching material, 7,757 lines. Companion to the textbook.
Likely reinforces the same material with worked chart examples.

**Extraction approach:** cross-reference with the main textbook.
If Lessons Vol. I provides clearer worked-example versions of textbook
chapters, cite the lesson-version for teaching-oriented articles.

---

## Chennareddy Vasudev e-book (`Astrology-e-book-compressed.pdf`)

Introductory text, 4,558 lines, 2019 publication. Likely covers
origins, purpose, philosophical framing of astrology. Useful for
philosophical/introductory articles but not the primary source for
technical extraction.

**Extraction approach:** skim for philosophical framings we might
want to reference in "why astrology" or history-oriented articles.
Not a primary extraction priority.

---

## Varahamihira Hora Sastra — OCR pipeline needed

**Blocked:** The PDF is scanned page images with no OCR layer.
`pdftotext` produces 0 lines. To extract, we need:

1. **`tesseract`** OCR pipeline: `pdftoppm` → PNG per page → `tesseract`
   per page → concatenate. Estimated 500-1000 pages, ~2-4 hours OCR
   compute time.
2. **Or: cloud OCR** — Google Cloud Vision or AWS Textract, better
   accuracy on Sanskrit but requires uploading to cloud (which we've
   deliberately not done for the PDFs).
3. **Or: find a text-version PDF** — many classical texts have been
   re-published with OCR'd text layers by sanskrit-e-text projects.
   sanskritdocuments.org sometimes has cleaner versions.

**Recommendation:** try `tesseract` first (free, local, no upload
required). If accuracy is poor, upgrade to Google Cloud Vision.

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

Never cite Varahamihira directly until OCR extraction is done.

---

## Extraction workflow

Same pattern that worked for BV Raman:

1. `pdftotext -layout <file>.pdf /tmp/bhagya-pdfs/<name>.txt`
2. Survey structure with `grep -n "^Chapter\|^\s*[0-9]\+\.[0-9]"`
3. Read relevant sections with `sed -n '<start>,<end>p'`
4. Write MD in `knowledge/` matching the citation style above
5. Commit each MD separately with source scope in the commit message

Each MD file should be reviewable in isolation (200-500 lines is the
sweet spot). Larger topics get split into sibling files rather than
one giant file.

---

*This document should be updated whenever a new extraction commits or when a source proves unusable.*
