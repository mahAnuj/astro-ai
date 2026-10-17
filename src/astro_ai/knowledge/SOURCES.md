# Knowledge Extraction — Source Audit & Plan

Living document tracking what's been extracted from each source PDF,
what's still pending, and how new articles should cite them.

**Last updated:** 2026-10-17 (#191 — Rao textbook extraction: Ch. 6, Ch. 7,
Ch. 16/25/26 + Part 6, line-pinning of Ch. 11, 13 and 34, and a **correction to
this file's own chapter map**, which was wrong about Ch. 4-5, 6-8, 9-15 and the
muhurta chapter. Provenance ledger at the end. Earlier: 2026-08-27, #216 — the
`[BPHS]` citation licence withdrawn; corpus-dependency audit appended)

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
| 2 | `vedic_astro_textbook.pdf` | P.V.R. Narasimha Rao | 20,669 | 🟢 **Substantially extracted** — Ch. 3 (`grahas.md`), **Ch. 6 vargas (`divisional_charts.md`, 2026-10-17)**, **Ch. 7 houses + the four life areas (`houses.md`, 2026-10-17)**, Ch. 11 yogas (`yogas.md`, line-pinned 2026-10-17), Ch. 12 §12.5, Ch. 13 (`vedic_reference.md` §8.5, line-pinned), **Ch. 16/25/26 + Part 6 timing (`vedic_reference.md` §5B, 2026-10-17)**, Ch. 34 remedies (`remedies.md`, line-pinned 2026-10-17), §4.3 Other Upagrahas / Table 10 (`vedic_reference.md` §28, 2026-08-26). Still unextracted: Ch. 1, 2, 5, 8, 9, 10, 14, 15, 17–24, 27–33, 35–37 | MEDIUM — the high-value chapters are done |
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

### The map below was WRONG about four chapter ranges — corrected 2026-10-17

The previous version of this map sent readers to the wrong chapters, and two
extractions were planned against it. **Measured from the chapter heads with
`grep -nE "^[0-9]+\. [A-Z]"` over plain `pdftotext` (20,669 lines):**

| Ch. | Title | Plain line | The old map said |
|---|---|---|---|
| 1 | Basic Concepts | 308 | ✅ |
| 2 | Rasis | 1319 | ✅ |
| 3 | Planets | 1576 | ✅ |
| 4 | **Upagrahas** | 2161 | ❌ "Bhavas (houses)" |
| 5 | **Special Lagnas** | 2435 | ❌ "Bhavas (houses)" |
| 6 | **Divisional Charts** | 2642 | ⚠️ said "Ch. 6-8"; vargas are Ch. 6 **alone** |
| 7 | **Houses** | 3307 | ❌ mapped to "Vargas" |
| 8 | **Karakas** | 3812 | ❌ mapped to "Vargas" |
| 9 | **Arudha Padas** | 4186 | ❌ mapped to "Yogas, doshas" |
| 10 | **Aspects and Argalas** | 4702 | ❌ mapped to "Yogas, doshas" |
| 11 | Yogas | 5308 | ✅ (inside the 9-15 band) |
| 12 | Ashtakavarga | 6555 | ✅ |
| 13 | **Interpreting Charts** | 8723 | ❌ not named at all |
| 14 | Topics Related to Longevity | 9212 | ❌ not named |
| 15 | Strength of Planets and Rasis | 9476 | ❌ not named |
| 16 | Vimsottari Dasa | 10311 | ✅ |
| 17 | Ashtottari Dasa | 10801 | ✅ |
| 18 | Narayana Dasa | 11066 | ✅ |
| 19 | Lagna Kendradi Rasi Dasa | 12081 | ✅ |
| 20 | Sudasa | 12240 | ✅ |
| 21 | Drigdasa | 12371 | ✅ |
| 22 | Niryaana Shoola Dasa | 12549 | ✅ |
| 23 | Shoola Dasa | 12764 | ✅ |
| 24 | Kalachakra Dasa | 12991 | ✅ |
| 25 | **Transits and Natal References** | 13982 | ⚠️ the dasha band stopped at 25; Ch. 25 is transits |
| 26 | Transits: Miscellaneous Topics | 15187 | ✅ |
| 27 | Tajaka Chart Basics | 16124 | ✅ |
| 28 | Techniques of Tajaka Charts | 16461 | ✅ |
| 29 | Tajaka Yogas | 17260 | ✅ |
| 30 | Annual Dasas | 17619 | ✅ |
| 31 | Sudarsana Chakra Dasa | 17993 | ✅ |
| 32 | Impact of Birthtime Error | 18200 | ✅ |
| 33 | Rational Thinking | 18845 | ✅ |
| 34 | Remedial Measures | 19161 | ✅ |
| 35 | Mundane Astrology | 19529 | ✅ |
| 36 | Muhurta or Electional Astrology | 19835 | ⚠️ the old map put muhurta in "26-33" |
| 37 | Ethical Behavior of a Jyotishi | 20236 | ❌ not named |
| — | **Part 6: Real-life Examples** | **20324–20669** | ❌ not named, and it is the most product-useful part of the book |

**There is no doshas chapter.** The old map's "Ch. 9-15 — Yogas, doshas,
Ashtakavarga" implied one. Measured: `kuja` **0**, `dosha`/`dosa`/`dosham`
**0**, `ashtama` **0** across all 20,669 plain lines. Rao's textbook carries no
Manglik, Kuja-dosha, Sade-Sati or Kaal-Sarp doctrine at all. Recorded in
`vedic_reference.md` §1.6 with the per-book counts.

**Extraction status by chapter, 2026-10-17:**

| Chapter | Target MD | Status |
|----------|-----------|--------|
| Ch. 3 (Planets) | `grahas.md` | ✅ done 2026-07-23; §12 combustion extended 2026-08-26 (cites under **`-layout`**) |
| **Ch. 6 (Divisional Charts)** | `divisional_charts.md` | ✅ **done 2026-10-17** — Table 11, the four planes, varga groups + amsa ladders, vargottama, §11.7.2's Parashara rule, §12.5, §36.4 |
| **Ch. 7 (Houses)** | `houses.md` | ✅ **done 2026-10-17** — §7.2 significations verbatim, §7.3 varga-scoping, §7.4.5/§7.4.6, plus the four life areas |
| **Ch. 11 (Yogas)** | `yogas.md` | ✅ content done 2026-07; **line-pinned and the BPHS misattribution corrected 2026-10-17** |
| Ch. 12 §12.5 (Ashtakavarga in vargas) | `divisional_charts.md` | ✅ done 2026-10-17 |
| Ch. 13 (Interpreting Charts) | `vedic_reference.md` §8.5 | ✅ content done; **line-pinned 2026-10-17** |
| **Ch. 16 / 25 / 26 / Part 6 (timing)** | `vedic_reference.md` **§5B** | ✅ **done 2026-10-17** — dasha→varga rule, Tripod of Life, transit rules, the five worked predictions, and Rao's refusal to call a competitive outcome from a dasha |
| Ch. 34 (Remedies) | `remedies.md` | ✅ content done 2026-07-24; **line-pinned and the shipped assignments audited 2026-10-17** |
| §4.3 Other Upagrahas / Table 10 | `vedic_reference.md` §28 | ✅ done 2026-08-26 |
| **Ch. 2 (Rasis)** | extend `rashis.md` | ❌ **P0** — Rao's finer classifications, and the Vishnu-limb material (line 1337; it is a RASI doctrine, not a bhava one) |
| Ch. 8 (Karakas) | `vedic_reference.md` §5A | 🟡 partially — chara/sthira karakas are there; not line-pinned |
| Ch. 9 (Arudha Padas) | new target needed | ❌ **P1** — `houses.md` and §5B now cite A5/A7/A10/AL/upapada repeatedly with no arudha reference file |
| Ch. 10 (Aspects and Argalas) | `aspects.md` | ❌ **P1** — `aspects.md`'s primary source is Raman, `[MISSING]` on most checkouts; argala is uncovered |
| Ch. 14 (Longevity), Ch. 15 (Strength) | `vedic_reference.md` | ❌ P2 |
| Ch. 17–24 (the other dasha systems) | new `dashas.md` | ❌ P2 — **§5B shows the product uses 1 of the 7 timing apparatus Rao used**, so this is now the clearest capability gap |
| Ch. 27–29 (Tajaka), Ch. 30–31 | new `dashas.md` | ❌ P2 — Rao's method of last resort for a dated question |
| Ch. 33 (Rational Thinking) | `vedic_reference.md` §8.2 | ✅ done |
| Ch. 36 (Muhurta) | `grahas.md` §12.5, `muhurat` material | 🟡 partially |
| Ch. 37 (Ethics) | `vedic_reference.md` §5B.6 | 🟡 cited, not extracted |

**The old priority table is retired.** It listed `grahas.md`, `yogas.md` and
`remedies.md` as "New" files; all three have existed since July 2026, and the
instruction to create them is how a reader ends up duplicating a file instead
of extending it.

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
- `[Vasudev, Origin & Purpose of Astrology, p. 42]`

Never cite Varahamihira directly — we do not hold the text (see above).
Cite the proximate source that quotes him instead.

### The `[BPHS]` licence is withdrawn (2026-08-27, #216)

This list used to carry a fifth entry:

> `[BPHS] / [Phaladeepika]` — when the rule is universally cited and
> attributed to the original classical text (Rao and Raman are the
> proximate sources but the rule itself is from BPHS/Phala)

It is gone, and the same rule now binds BPHS as binds Varahamihira: **cite the
proximate source you actually read, never the ur-text you did not.**

The licence was not theoretical. Twelve yoga rules in `chart.py` carried
`source="Brihat Parashara Hora Shastra"` or `"BPHS / Phaladeepika"`, and
`templates/result.html` renders that string to the reader as
`Source: Brihat Parashara Hora Shastra` under every yoga card. BPHS is not in
`data/`, is not one of the eight entries in `scripts/fetch_corpus.py`, and
never was — so no reader and no agent could check any of them. Forty lines from
one of those rules, the same file documented its orb as UNSOURCED. All twelve
were re-audited on 2026-08-27 and resolve to **Rao Ch. 11**, which we hold;
they now cite him by section.

"Universally cited" is exactly the condition under which nobody checks. It is
the same failure as the invented `[BPHS]` retrograde orbs (`chart.py`,
`COMBUSTION_ORBS`) and the Cheiro Lo Shu attribution (#172): a real book's name
attached to a claim it was never read for, which then reads as verified.

**A citation is a promise that someone here opened the page.** If you did not,
say which text you did open, or say the rule is unsourced.
`scripts/verify_rule_citations.py` enforces this for `chart.py`'s rule labels:
it fails on any book absent from the registry, unconditionally on BPHS, and —
where the cited book is present in `data/` — checks that the cited section
exists in its text.

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

---

## Corpus facts moved from CLAUDE.md (2026-08-26)

*Relocated because this is sourcing-time knowledge: it was being loaded
into every agent on every turn at ~970 tokens, and is needed by the few
that actually search the corpus. The rules that bind everyone stayed in
CLAUDE.md; the detail lives here.*

### Source books in `data/` — all seven are readable

The two scanned, OCR-blocked PDFs (`varahmihirHorasastram.pdf`, `Numerology.pdf`) have
been **deleted**. Every PDF now in `data/` extracts with plain `pdftotext`. There is no
OCR-blocked source left, and #178 is acquisition-only.

Line counts below are **plain `pdftotext`** (no `-layout`), measured 2026-08-08. The flag
matters: `-layout` yields ~30% fewer lines because it reflows columns. Quote the flag
whenever you quote a count — the older figures in this file and `SOURCES.md` disagreed
purely because they mixed the two.

| PDF | lines | note |
|---|---|---|
| `Numerology the Complete Guide…` / Goodwin | 28,171 | largest numerology source; Western/Pythagorean |
| `vedic_astro_textbook.pdf` / Rao | 20,669 | richest astrology source, largely unextracted |
| `Astrology For Beginners BVRaman_text.pdf` | 15,409 | fully extracted |
| `book1-for-CD.pdf` / Rao Lessons Vol. I | 12,244 | not extracted |
| `Numerology-With Tantra…` / Johari | 5,952 | primary *Vedic* numerology authority |
| `Astrology-e-book-compressed.pdf` / Vasudev | 5,220 | introductory/philosophical |
| `Numerology-You.pdf` / Jayant Kumar | 1,110 | 43pp sample only |

**88,775 lines total.** Most of it is unextracted — see #191.

**RE-MEASURED 2026-10-17 (#191): the corpus is now 14 books, 94,019 `-layout`
lines, not 7 books / 85,979.** `scripts/corpus_search.py` prints the live list;
it now includes **Cheiro, *Book of Numbers*** (8,389 `-layout` lines — which
bears on #172/#160 and was previously recorded as "not in `data/`"), a
Chaldean-numerology compilation (4,829), *Muhurta Chintamani* in Sanskrit
(8,040) and four small number-compatibility PDFs. Note that
`Astrology For Beginners BVRaman_text.pdf` reports **5,390** `-layout` lines
against 15,409 plain, which is a much bigger gap than the ~30% the rest of this
file assumes — worth checking before any absence is claimed against Raman.
New absences measured 2026-10-17 across all 14 books, with the search run
recorded beside each: `Surya Namaskar` **0** (4 spellings), `namaskar` **0**,
`red lentil` **0** (3), `masoor` **0** (4), `Hanuman Chalisa` **0** (6),
`Shani Beej` **0** (6), `Rahu Beej` **0** (4), `arohini` **0** (3),
`avarohini` **0** (4), `arambha` **0** (3), `elinati` **0** (4),
`ashtama shani` **0** (6), `Manglik` **0** (3). Present but not where it was
assumed: `sesame oil` **2** (both Johari, Ayurvedic massage), `outsiders`
**1** (Cheiro), `madhya` **1** (Raman AfB, unrelated), `sade sati` **1**
(Rao *Lessons*, as `Sade Sathi`), `kuja dosha` **18** (Vasudev 11, Raman
*Muhurtha* 7, **Rao's textbook 0**).

**Measured absences — SUPERSEDED 2026-08-16, and the correction matters more than the
note did.** This block used to record `Vashya` **0**, `Lo Shu` **0**, `Ashtakoot` **0**
and `Yoni` as three false positives, marked "do not re-search". Adding
`data/matching/raman-muhurtha-1948-electional-astrology_djvu.txt` (B.V. Raman,
*Muhurtha or Electional Astrology*, 1948, out of copyright) falsified three of those:

| term | old | now |
|---|---|---|
| `Vashya` | 0 | **2** — "Vasya Kuta" §8, with the Aries/Leo pairings |
| `Graha Maitri` | 0 | **5** — named, with its cancellation rules |
| `Yoni` | 3 false positives | **12** — the 27-nakshatra animal table and hostile pairs |
| `Nadi` | — | **32** |
| `Gana` | — | **6** |

Still absent, verified across all 85,979 lines: `Bhakoot` **0**, `Guna Milan` **0**,
`Lo Shu` **0**.

**Two lessons, both paid for.** First, a "do not re-search" note is only true until the
corpus changes, and nothing here re-checked it — the note outlived its evidence by two
days. Re-run rather than trust it. Second, the same day this was corrected, a false
POSITIVE was also found: `scripts/corpus_search.py` was counting `data/emails/sarbani.pdf`
— our own outreach message — as a source book, so `Ashtakoot` briefly appeared present
because we had written the word ourselves.

**Use `scripts/corpus_search.py` rather than grep.** It expands transliterations
(`vimshottari` finds `vimsottari`, 2 hits vs 134), excludes non-book directories, refuses
to run on a partially-extracted corpus, and its `--absent` mode makes "unsourced" a
checkable claim. Note what it proves: the TERM is absent, not the CONCEPT — `nitya yoga`
matches nothing while `vyatipata` and `vaidhriti` are both in the books.

**Raman's is the SOUTH INDIAN tradition** — 12 poruthams (Dina, Gana, Mahendra, Rajju,
Sthree Dheergha …), not the North Indian 36-guna Ashtakoota our `matching.py` implements.
The koota definitions largely overlap; the point weights do not. Cite it for what a koota
*is*, not for what it *scores*, and never blend the two systems in one reading.

**Present and citable, contrary to earlier notes:** `Numerology-You.pdf` line 815 carries a
"Chaldean And Pythagorean System" section stating the book uses **Chaldean** values for its
alphabet table, and names the Karmic Debt numbers (13, 14, 16, 19) and Master numbers
(11, 22, 33) outright. It is a real source for the numerology-table questions.

`data/` is gitignored for copyright hygiene. Cite work and chapter; never paste pages.
See `knowledge/SOURCES.md` for per-book extraction status, and #191 for the extraction
backlog.



---

## Which books our claims depend on, and which are not here (measured 2026-08-27)

Added for #216. `data/` is gitignored, so this is a snapshot of one checkout —
**re-run `uv run python scripts/fetch_corpus.py` before quoting any of it**, and
say which books were present whenever you report an absence (CLAUDE.md).

On this checkout the registry reported **4 of 8 usable**:

| Present | Absent |
|---|---|
| Rao, *Vedic Astrology: An Integrated Approach* | Raman, *Astrology for Beginners* |
| Rao, *Lessons on Vedic Astrology*, Vol. I | Johari, *Numerology* |
| Vasudev, *Astrology* (e-book) | Kumar, *Numerology & You* (sample only) |
| Raman, *Muhurtha or Electional Astrology* (1948) | Goodwin, *Numerology: The Complete Guide*, Vol. 1 |

**BPHS is in neither column: it is not in the registry at all.** Nor are
Phaladeepika, Jataka Parijata, Jataka Chandrika, Muhurtha Chintamani, Saravali,
Brihat Jataka, Raman's *Three Hundred Important Combinations*, or Cheiro's
*Book of Numbers* — all of which this repo's code or knowledge files cite by
name. A book absent from the registry is worse than one marked `[MISSING]`:
`fetch_corpus.py` at least tells you the second is gone.

### The knowledge files rest on books that are not here

Ten files in `knowledge/` besides this one. Counting only books the registry
tracks, **six name a primary source that is currently `[MISSING]`**:

| File | Primary source named | Status |
|---|---|---|
| `aspects.md` | Raman, *Astrology for Beginners* | `[MISSING]` |
| `divisional_charts.md` | Raman, *Astrology for Beginners* | `[MISSING]` |
| `grahas.md` | Raman, *Astrology for Beginners* (with Rao, present) | `[MISSING]` |
| `houses.md` | Raman, *Astrology for Beginners* | `[MISSING]` |
| `rashis.md` | Raman, *Astrology for Beginners* (with Rao, present) | `[MISSING]` |
| `numerology.md` | Johari; Kumar; Goodwin | all `[MISSING]` |

Widening to books the registry does not track at all, **nine of the ten** name
at least one: BPHS in `aspects.md`, `divisional_charts.md`, `grahas.md`,
`houses.md`, `rashis.md`, `vedic_reference.md` and `yogas.md`; Cheiro in
`numerology.md`; Muhurta Chintamani in `matching.md`, whose stated path
`data/matching/muhurta-chintamani-…_djvu.txt` is not on this checkout.
`remedies.md` is the only file resolving entirely to a book we hold (Rao Ch. 34).

### Shipped tables that rest on an absent book

`chart.py`'s `_GOCHAR_BENEFIC_HOUSES` — the transit favourability the site
renders — is sourced to **Raman, *Astrology for Beginners*, Ch. XII, p.101**,
"transcribed from `pdftotext -layout` of the copy in `data/`". That copy is
`[MISSING]` today, so the transcription cannot be re-checked here. This is not
a claim that the table is wrong: `scripts/verify_gochar_table.py` passes, but
it compares the code table against `knowledge/vedic_reference.md` — tree
against tree. Neither reaches the book.

**This is a finding, not a task.** Do not try to resolve it in a citation fix.
What would resolve it is supplying the book (`--from-dir` / `--from-bucket`),
after which the transcription can be verified against p.101 for the first time
since it was written.


---

## Provenance ledger — Rao textbook extraction, 2026-10-17 (#191)

**Flag, stated once and binding on every range below: PLAIN `pdftotext`, no
`-layout`.** `data/vedic_astro_textbook.pdf` = **20,669 lines**, re-verified
2026-10-17 against the fingerprint in the table at the top of this file.
`data/book1-for-CD.pdf` (Rao *Lessons* Vol. I) = **12,244 lines**, also plain.
`data/Astrology-e-book-compressed.pdf` (Vasudev) is cited under **`-layout`**
(**4,558 lines**) because `grahas.md` §12.4's Vasudev citations and
`corpus_search.py`'s line numbers both use that scheme and the two must agree.

**`grahas.md` §12 remains under `-layout` (16,724 lines) and says so.** The two
schemes are live in the corpus simultaneously. That is not ideal, but silently
renumbering §12 would break every citation in it, and the right fix is that
every section declares its flag — which they all now do.

| MD file + section | Rao source | Plain lines | What it settles |
|---|---|---|---|
| `divisional_charts.md` → "Rao on the vargas" | §6.1–6.2 | 2643–2688 | the 16 divisions are Parashara's, 4 more are Jaimini/Tajaka; Rao computes 20 and excludes D-108/D-150 and the D-2/D-3/D-8/D-11 variants |
| ↳ Table 11 significations | §6.3 | 3034–3098 | D-9 = marriage/dharma/basic skills/inner self; D-10 = career and achievements in society. Supersedes the uncited BPHS rows where they disagree; D-40/D-45's "maternal/paternal karmic inheritance" is CONTESTED |
| ↳ the four planes | §6.4 | 3120–3140 | 1–12 physical, 13–24 mental, 25–36 sub-conscious, >36 karmic, with Rao's "find a guru first" footnote on the last group |
| ↳ varga groups + amsa ladders | §6.6 | 3179–3280 | Shadvarga / Saptavarga / **Dasavarga (10)** / Shodasavarga memberships and the nine-step Dasavarga ladder |
| ↳ vargottama defined | §11.7.3 fn | 6351 | same sign in Rasi and Navamsa — sources a rule that had no citation |
| ↳ **the #398 B verdict** | §11.7.2 | 6151–6234 | Parashara's rule is a **ten-chart Dasavarga count** on the two yoga-forming planets, not a D-9 survival test. `prompts/natal.txt:65` is **CONTRADICTED** and its Parashara attribution is **WRONG** |
| ↳ Ashtakavarga in every varga | §12.5 | 7808–7881 | Parasara did not restrict it to D-1; the Vajpayee example explains a career from **D-10's SAV** |
| ↳ which chart "manifestation" means | §36.4 | 20217–20219 | *"Rasi is the chart of physical manifestation; navamsa is the chart of dharma and inner self; and, dasamsa is the chart of achievements in society."* |
| `houses.md` → Rao's significations | §7.2 | 3346–3388 | all twelve houses verbatim; 2nd = wealth/assets, 11th = income/gains, 6th = enemies/service/servants |
| ↳ house meaning is varga-scoped | §7.3 | 3402–3411 | the 4th house means education in D-24, vehicle in D-16, house in D-4, mother in D-12 |
| ↳ positional logic + halves | §7.4.5–7.4.6 | 3741–3762 | trines prosper, quadrants sustain, upachayas grow, dusthanas obstruct, argala decides; 7th–12th visible, 1st–6th invisible |
| ↳ **studies and exams** | §7.3.5 + §13.4.1 | 3505–3517, 8966–8993 | **success in competition = 5th from ARUDHA LAGNA in D-24**; scholarship = 5th from lagna; memory = 5th from paaka lagna; awards = A5. **The 6th house is NOT Rao's exam house** |
| ↳ career / marriage / money | §7.2, §6.3, §6.5, §11.9, §18.5, Part 6 | see the file | 10th + D-10 + GL + AL + A10; 7th + D-9 + upapada; 2nd vs 11th + D-2 + HL |
| `vedic_reference.md` **§5B.1** | §16.5.1 | 10486–10513 | *"A planet gives the results promised by its positions in various divisional charts"* + nine worked dasha-result examples |
| ↳ **§5B.2 Tripod of Life** | §16.5.3 | 10543–10563 | Sun judges the **mahadasha**, Moon the **antardasha**, lagna the **pratyantardasha**; Ravi yogas pay in MD, Chandra yogas in AD, **Raja yogas primarily in PD** |
| ↳ §5B.3 transits | §25.2, 25.3, 25.4, 25.7, §7.3.5 | 13994–13999, 14376–14398, 14440–14452, 15106–15115, 3517–3521 | the transit of the **Vimsottari dasha lord** is the important one; the master transit rule; coarse vs fine timing; Rao's own-research disclaimer on varga transits |
| ↳ §5B.4 timing an event | Part 6 Ex. 1–5 | 20328–20669 | the full chain Rao uses — varga → varga dasha → MD → AD → PD → transit → a second dasha system → cultural filter. **The product has 1 of 7** |
| ↳ **§5B.5 the refusal** | Part 6 Ex. 4 | 20559–20576 | *"We cannot look at the dasas one is running and conclude whether one will win the award or not."* The citable stance for "will I pass / will I get it" |
| ↳ §8.5 pinned | Ch. 13 | 8723–9211 | the five-step funnel is §13.4.1, lines 8955–9010 |
| ↳ **§1.6 Manglik** | absence | — | `kuja` 0, `dosha` 0, `ashtama` 0 in 20,669 lines. Vasudev (`-layout` 2566–2695) extracted instead |
| ↳ **§2.7 Sade Sati** | *Lessons* Vol. I | 281–287, 474–478 | definition, 2.5/7.5 years and the mind rationale now sourced to a book we hold; the softening condition is **Saturn as lagna lord or yogakaraka**, not "strong"; **every phase name is UNSOURCED** |
| `yogas.md` §7.4, §13, §14 | §11.1–11.11 | 5309–6549 | Ch. 11 subsection map; the amsa ladder re-attributed from "(from BPHS)" to **Sage Parasara** (line 6174); the 6° Raja-Yoga orb sourced (6163–6164, fn 6256) |
| `remedies.md` §11, §12 | §34.1–34.6 | 19162–19523 | every section pinned; the eleven `prompts/natal.txt:68` assignments audited — 3 WRONG, 4 UNSOURCED, 4 CORRECT |

### Findings this extraction produced, for whoever files them

**Not filed. No issue was opened and no rule was edited.** `chart.py`,
`matching.py`, `muhurat.py`, `numerology.py`, `prompts/*.txt` and
`templates/*` are untouched by this work.

1. `prompts/natal.txt:65` — "raja or wealth yoga surviving into D-9 is fully
   manifested per Parashara" is **CONTRADICTED and misattributed**.
2. `prompts/natal.txt:68` — **three WRONG remedy rows** (Sun→red lentils,
   Moon→Shiva, Saturn→Hanuman) with sourced correct values, and **four
   UNSOURCED** with measured absences.
3. `vedic_reference.md:125` — "red lentils (masoor dal)" as a Tuesday/Mars
   remedy is **UNSOURCED**: `red lentil` and `masoor` are **0 hits** in all
   94,019 `-layout` lines. Rao's Mars grain is **toor daal**.
4. `chart.py:1031` Manglik severity ladder — **UNSOURCED as a ladder**, and the
   "1st house = moderate" tier is **counter-indicated** by the only corpus
   source that lists the houses (Vasudev: *"Some include 1 bhava also"*).
5. `chart.py:651–653` vs `i18n.py:172–174` vs `knowledge/` vs
   `learn_registry.py` — **four surfaces, two different Sanskrit vocabularies**
   for the Sade Sati phases, none of which is in any book we hold.
6. `prompts/ask.txt` — no studies/education category
   (`grep -ciE "exam|studies|education|student"` = **0**), one topic line per
   category naming no classical rule, and **no transit data on the `/ask`
   path**. The houses and charts for all four life areas are now sourced in
   `houses.md`; Rao's refusal to call an outcome is in §5B.5.
7. `divisional_charts.md` self-divergence — the file's own "a yoga is activated
   only if it ALSO appears in the D-9" bullet is uncited and contested by Rao.
   Flagged in place rather than deleted.
8. `aspects.md`, `houses.md`, `rashis.md`, `divisional_charts.md` all still
   name **BPHS** or a `[MISSING]` Raman as a primary source. Rao's Ch. 7 now
   covers the houses from a book we hold; the BPHS lines in those headers are
   still the #216 defect and were not touched here.
