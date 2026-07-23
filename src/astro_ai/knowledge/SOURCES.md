# Knowledge Extraction — Source Audit & Plan

Living document tracking what's been extracted from each source PDF,
what's still pending, and how new articles should cite them.

**Last updated:** 2026-07-23

---

## Available source PDFs (all in `/data/`, gitignored)

| # | File | Author | Text lines | Status | Priority |
|---|------|--------|------------|--------|----------|
| 1 | `Astrology For Beginners BVRaman_text.pdf` | BV Raman | 5,390 | ✅ **Fully extracted** | Done |
| 2 | `vedic_astro_textbook.pdf` | P.V.R. Narasimha Rao | 16,724 | 🟡 **Partially cited** (Ch. 34 remedies) | HIGH — full extraction pending |
| 3 | `book1-for-CD.pdf` | P.V.R. Narasimha Rao (Lessons Vol. I) | 7,757 | ❌ Not extracted | MEDIUM |
| 4 | `Astrology-e-book-compressed.pdf` | Chennareddy Vasudev | 4,558 | ❌ Not extracted | LOW (introductory) |
| 5 | `varahmihirHorasastram.pdf` | Varahamihira (~6th C) | **0 (scanned images)** | ⚠️ **Needs OCR** | HIGH but blocked |

**Total text-searchable content available:** ~34,400 lines across 4 PDFs.
**Blocked:** Varahamihira (48MB scanned images — requires OCR pipeline).

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
