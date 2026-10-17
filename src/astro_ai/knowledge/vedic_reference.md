# Vedic Astrology Reference — Classical Texts & Modern Practice

> **Purpose.** This file is the canonical knowledge base for the LLM when
> generating Kundali readings, Manglik panels, Sade Sati explanations, and
> dasha interpretations. It is curated from classical Jyotish texts (BPHS,
> Mansagari, Phaladeepika, Jataka Parijata, Saravali, Brihat Jataka) and
> cross-checked against widely-accepted modern practice.
>
> **How to use.** When a chart panel flags a dosha or yoga, the LLM should
> cite the rule and its source from this file rather than inventing
> generic statements. When in doubt, prefer the conservative classical
> reading over modern WhatsApp-forward dramatizations.
>
> **What this file is NOT.** Not a replacement for the chart computation
> in `chart.py`. The code decides *what is true* about the chart; this
> file decides *what to say about it* in a grounded, defensible way.

---

## 1. Mangal Dosha (Manglik / Kuja Dosha)

### 1.1 Definition (classical)

Mars placed in the **1st, 2nd, 4th, 7th, 8th, or 12th house** — measured
from **Lagna, from Chandra (Moon), or from Shukra (Venus)** — creates
Mangal Dosha. The 7th and 8th are considered most serious because they
directly govern marriage and longevity of the spouse.

> Source: *Brihat Parashara Hora Shastra* (BPHS), chapter on Vivaha
> (Marriage); *Mansagari*, Mangal Dosha prakaran; *Jataka Parijata*
> chapters on marriage.

### 1.2 The term "Angshik Manglik" — be careful

"Angshik Manglik" (अंशिक मांगलिक — partial Manglik) is a **modern Hindi
astrology term**, not a classical Sanskrit one. The classical equivalent
is **Mangal Dosha Bhanga** ("breaking" of the dosha) or **Parihara**
("mitigation"). When writing readings, prefer one of:

- "Mangal Dosha is present but cancelled by …" (when a full cancellation
  rule applies)
- "Mangal Dosha is present but its effect is reduced by …" (when only
  mitigation applies)

Do NOT say "this is Angshik Manglik" as if quoting a classical category —
it is a colloquialism, not scripture.

### 1.3 Cancellation rules (Mangal Dosha Bhanga Yogas)

These rules are compiled from *Mansagari*, *Jataka Parijata*, *Phaladeepika*,
*Muhurtha Chintamani*, and consolidated by Jagannath Hora's classical
rule-set. Each rule is tagged **cancels** (dosha is fully nullified) or
**mitigates** (effect is softened, not removed).

#### A. Sign-based

| # | Rule | Effect | Primary source |
|---|---|---|---|
| 1 | Mars in **own sign** (Aries / Scorpio) in a Manglik house | cancels | Jataka Parijata |
| 2 | Mars **exalted** (Capricorn) in a Manglik house | cancels | Jataka Parijata |
| 3 | Mars **debilitated** (Cancer) in a Manglik house | cancels (debated) | Jataka Chandrika |
| 4 | Mars in **movable signs** (Aries, Cancer, Libra, Capricorn) when placed in 1/2/4/7/8/12 | cancels | Jataka Parijata (explicit Sanskrit verse) |
| 5 | Mars in signs of **Jupiter** (Sagittarius, Pisces) or **Venus** (Taurus, Libra) — friendly to relationships | mitigates | Classical consensus |

#### B. Benefic-aspect & conjunction

| # | Rule | Effect | Primary source |
|---|---|---|---|
| 6 | **Jupiter aspects Mars** (Guru drishti on Kuja) | cancels — primary classical cancellation | Multiple texts |
| 7 | Jupiter aspects the 7th house OR the 7th lord | cancels | Classical |
| 8 | Venus aspects or conjuncts Mars | mitigates → cancels | Classical |
| 9 | Strong Moon aspects Mars | mitigates | Classical (mixed weight) |
| 10 | Mars **conjunct Jupiter** in the same house | cancels (full neutralization of marital disturbance) | Jataka Parijata |
| 11 | Mars conjunct Mercury | mitigates | Lesser-cited classical |

#### C. Ascendant-specific exclusions

| # | Rule | Effect | Primary source |
|---|---|---|---|
| 12 | **Cancer Lagna** — Mars rules 5th (trikona) + 10th (kendra), becomes **Yogakaraka**; cannot simultaneously be a dosha-source | EXCLUDED from Manglik diagnosis | Jataka Parijata + Muhurtha Chintamani |
| 13 | **Leo Lagna** — Mars rules 4th (kendra) + 9th (trikona); Yogakaraka principle applies | EXCLUDED | Jataka Parijata + Muhurtha Chintamani |
| 14 | **Aries Lagna**, Mars in 1st (own sign) | cancels | Classical |
| 15 | **Scorpio Lagna**, Mars in 8th (own sign) | mitigates → cancels | Classical |
| 16 | **Sagittarius / Pisces Lagna**, Mars in 12th (own sign) | mitigates | Regional |

#### D. Weakness-based

| # | Rule | Effect | Primary source |
|---|---|---|---|
| 17 | **Retrograde Mars** in dosha house | character changed (internalized), not cancelled — DISPUTED | Classical (contested) |
| 18 | **Combust Mars** (within ~6° of Sun) | cancels (Mars loses functional strength) | Classical matching practice |
| 19 | Mars in enemy signs (Gemini, Virgo) | mitigates | Lesser-cited |

#### E. Mutual cancellation

| # | Rule | Effect | Primary source |
|---|---|---|---|
| 20 | **Both partners are Manglik** of comparable severity | cancels for the marriage match | Classical compatibility rule |

#### F. EXPLICITLY REJECTED — folk myth, NOT classical

| # | Folk rule | Reality |
|---|---|---|
| 21 | "Manglik dosha weakens after age 28" | **NO classical text states this.** It is a modern folk claim. Do NOT cite it. |
| 22 | "Manglik must marry a banana tree / pot first" | Modern remedial folk practice, not in BPHS/Mansagari/Phaladeepika. Cite as cultural practice if at all, NOT as scripture. |
| 23 | "Manglik = bad temper and abusive spouse, guaranteed" | Gross over-reading. Classical texts speak of "marital disturbance" or "early widowhood risk" probabilistically, NOT character determinism. |

### 1.4 How to phrase Manglik in a reading

**Severity ladder for the LLM:**

1. **Manglik present + cancellation rule applies** → "Mangal Dosha is technically present (Mars in [house] from [reference]) but cancelled by [specific rule], so it should not be treated as an obstacle to marriage. Per [text], this is a recognized Mangal Dosha Bhanga Yoga."
2. **Manglik present + mitigation only** → "Mangal Dosha is present and softened by [rule]. The classical effect is reduced but worth knowing — see Section 1.5 on practical guidance."
3. **Manglik present + no cancellation** → "Mangal Dosha is present in your chart (Mars in [houses]). Per [text], this traditionally indicates [specific effect — delay, mismatch, etc.]. Practical guidance: see Section 1.5."

**Avoid:**
- "Manglik means your marriage will fail" — false and harmful
- "You must marry a tree" — folk, not scripture
- "Manglik is cured at 28" — folk, not scripture

### 1.5 Practical / remedial guidance (classical)

- **Match with another Manglik of comparable severity** — the most commonly cited classical remedy; it neutralizes the dosha mutually (see rule 20).
- **Recitation of Hanuman Chalisa / Mangal stotra** — Mars's adhidevata. Traditional, low-risk, devotional.
- **Donation on Tuesday** — red lentils (masoor dal), red cloth, sweets. Classical Tuesday remedy for afflicted Mars.
- **Coral (moonga) gemstone** — ONLY after a competent astrologer reviews the whole chart. Wearing coral without analysis can amplify Mars if Mars is not actually benefic for the chart. Default LLM stance: suggest consultation, do not prescribe.

---

### 1.6 Rao's textbook does not treat Mangal Dosha at all — measured 2026-10-17 (#191)

**This is an absence finding on the corpus's canonical Vedic authority, and it
bears directly on §1.3 rule 18 (combust Mars), on §1.1's severity claim, and on
`chart.py`'s three-tier severity grading.**

Measured against `data/vedic_astro_textbook.pdf` (P.V.R. Narasimha Rao, *Vedic
Astrology: An Integrated Approach*), plain `pdftotext`, **20,669 lines** — the
fingerprint `SOURCES.md` records:

| term | hits in Rao's textbook |
|---|---|
| `kuja` | **0** |
| `dosha` / `dosa` / `dosham` | **0** |
| `mangal` | **3**, none of them a dosha — line 5476 `Chandra-Mangala Yoga`, line 5828 `Guru-Mangala Yoga`, line 19876 *"Mangal sutra worn by a lady"* |
| `ashtama` | **0** |

So **the book this repo treats as its canonical Vedic authority contains no
Manglik / Kuja-dosha doctrine whatsoever** — no definition, no house list, no
cancellation set, no severity grading. He has a 36-section predictive apparatus
and a marriage-timing method (§5.5 here, Rao §16.5 and §31.4) and never invokes
the dosha.

That is not evidence the dosha is fake. It is evidence that **Rao cannot be
cited for anything about it**, including for anything the shipped code does,
and that the doctrine reaches this product only through books we hold in
weaker form or do not hold at all.

**What the corpus actually holds on Kuja dosha**, re-measured 2026-10-17 across
**14 books, 94,019 `-layout` lines** (`scripts/corpus_search.py "kuja dosha"`):

| Book | hits | What it gives |
|---|---|---|
| Vasudev, *Astrology* (`Astrology-e-book-compressed.pdf`) | **11** | A full discussion — and a hostile one |
| Raman, *Muhurtha or Electional Astrology* (1948) | **7** | The "ANTIDOTES FOR KUJA DOSHA" list — see `grahas.md` §12.4 |
| Rao, *Vedic Astrology: An Integrated Approach* | **0** | — |
| Rao, *Lessons on Vedic Astrology* Vol. I | **0** | — |
| everything else | 0 | — |

#### 1.6.1 Vasudev's treatment — the house list, and his rejection of the cancellations

Vasudev, *Astrology* (Chennareddy Vasudev), section *"The excessive unwanted
importance of 'Kuja Dosham'"*, printed pp. **90–94**, `-layout` lines
**2566–2695** (heading at 2566). `Astrology-e-book-compressed.pdf` is `-layout` 4,558 lines /
plain 5,220 lines; the ranges here are **`-layout`**, matching
`corpus_search.py`'s numbering and `grahas.md` §12.4's Vasudev citations.

- **Houses** (lines 2568–2575): *"It is said that 'Kuja dosham' exists if MARS
  is placed in 2,4,7,8,12 bhavas of a horoscope. **Some include 1 bhava also.**
  Some go further and say that the above bhavas to be checked from Moon and
  Venus also. If truely checked, we won't find any body without kuja dosham.
  Hence, for our discussion, let us limit Kuja doshan from ascendant only."*
  — so **the 1st house is optional even in his own framing**, and the
  Moon/Venus references are something he explicitly declines to use.
- **He opens by denying its pedigree** (line 2568): *"The 'Kuja Dosham' is not
  to be found in the standard astrological texts."*
- **Per-house effects** (lines 2630–2662), which is the nearest thing in the
  corpus to a severity ordering: 2nd — family fights, undiplomatic speech; 4th
  — depression, dullness, family fights, *"4th mars is suitable for gain of
  lands"*; 7th — *"damages the relationship with ego, arguements, agression …
  If other malefics aspect or associate, then seperation takes place"*; 8th —
  *"very bad for women since it is a husbands location in a woman's chart … if
  aspected or associated with malefics, tries to kill the husband"*; 12th —
  bed comforts, misunderstanding, non-compatibility.
- **He rejects Mars-exclusivity** (lines 2662–2680): replace Mars with Saturn,
  Sun, Rahu or Ketu and *"similar problems at a different scale can be
  experienced"*; Sun, Saturn and Rahu are *"Terrorist Planets"* whose lone
  placement in the 7th is *"as serious as that of MARS placement"*; *"giving
  excessive importance to only MARS in the name of 'Kuja Dosham' is wrong."*
- **He rejects the cancellation rules specifically** (lines 2613–2617), already
  recorded in `grahas.md` §12.4: of a pundit who applied *"various dictums
  given in texts for compensation conditions of Kuja dosham"* — *"But these
  rules were not given by maharshis and I found them not working well in many
  circumstances."*

#### 1.6.2 Verdicts for the open findings

| Finding | Verdict | Basis |
|---|---|---|
| **Combust Mars cancels Manglik** (§1.3 rule 18, `chart.py` `mars_combust`, `effect="cancels"`, `source="Classical matching practice"`) | **still UNSOURCED, and now absent from the canonical authority too.** No change to the #218 verdict; the evidence against it is stronger | `kuja`/`dosha` = **0** in Rao's textbook (20,669 plain lines) and **0** in Rao's *Lessons*; absent from Raman's dedicated antidote list (`grahas.md` §12.4); Vasudev discusses the compensations at length and does not list it, while rejecting the whole family of them |
| **Cancellation conditions and their orbs, generally** | **UNSOURCED in Rao; CONTESTED in the corpus.** Rao gives none because he gives no dosha. Raman gives a list that does not match `chart.py`. Vasudev gives a list and then disowns it. The only quantified orb anywhere near this is Rao's **6°** for a *Raja-Yoga* association (`yogas.md` §7.4) — a different rule about a different thing | as above |
| **The severity ladder: "high" (7th/8th) / "moderate" (1st/4th/12th) / "low" (2nd)** — `chart.py:1031`, graded at `chart.py:1033–1037` | **still UNSOURCED as a ladder.** Rao does not grade it. Two parts have weak corroboration and one is positively counter-indicated | **"7th and 8th most serious"**: weakly corroborated by Vasudev's per-house prose (7th = separation at line 2648, 8th = *"tries to kill the husband"* at line 2655) — but he grades no tiers and the 8th reads worse than the 7th in his text, which is the opposite of a tie. **"1st in the moderate tier"**: counter-indicated — Vasudev's own list is 2/4/7/8/12 and the 1st is *"Some include 1 bhava also"* (line 2570). **"2nd alone is lowest"**: not stated anywhere |
| **§1.1's "The 7th and 8th are considered most serious"**, sourced to *BPHS*, *Mansagari*, *Jataka Parijata* | **citation defect, #216 class.** All three books are absent from `data/` and absent from `fetch_corpus.py`'s registry. The claim is now *partly* traceable to Vasudev, who is present — but Vasudev is an introductory text that opens by saying the dosha is not in the standard texts, which is a different claim from the one §1.1 makes | `SOURCES.md` → "Which books our claims depend on" |

**Nothing here changes a rule.** `chart.py` and `matching.py` are untouched.

---

## 2. Sade Sati (Saturn's 7.5-year transit through 12th, 1st, 2nd from Moon)

### 2.1 Definition

Saturn transits the rashi 12th from the natal Moon (rising / **arambha**),
then the natal Moon rashi itself (peak / **madhya**), then the 2nd from
natal Moon (setting / **uttara**). Each phase ~2.5 years, total ~7.5 years.

> Source: *Phaladeepika* (Mantreshwara), chapters on Saturn transits;
> *Brihat Jataka* (Varahamihira); *Saravali* (Kalyana Varma).

### 2.2 Three phases — themes

| Phase | Saturn house from Moon | Theme | Common manifestations |
|---|---|---|---|
| **Arambha (rising)** | 12th | Endings, withdrawal, hidden losses | Job changes, isolation, sleep issues, financial pressure |
| **Madhya (peak)** | 1st (over natal Moon) | Identity stripped to essentials, mental burden | Self-doubt, health (especially mind/bones), relationship strain |
| **Uttara (setting)** | 2nd | Family, finances, speech under pressure | Family obligations, money discipline forced, voice/throat issues |

### 2.3 What Sade Sati is NOT

- **Not 7.5 years of unrelenting misfortune.** Classical texts describe it as a **maturity-forcing transit** — Saturn ages the native. Many people experience their biggest career achievements during Sade Sati (Saturn rewards hard work).
- **Not the same severity for everyone.** A strong natal Saturn (own/exalted/in good house) significantly softens Sade Sati. A weak/afflicted Saturn intensifies it.
- **Not always linked to bad events.** Sometimes Sade Sati simply manifests as a slow, heavy, restructuring phase — uncomfortable but constructive.

### 2.4 Ashtama Shani (separate but related)

Saturn transit through the **8th from natal Moon** is called Ashtama Shani —
~2.5 years. Distinct from Sade Sati. Often a phase of internal collapse,
hidden illness, deep introspection. Worth flagging in readings.

> Source: Classical transit literature; commonly referenced in modern
> practice (BV Raman, KN Rao).

### 2.5 Kantaka Shani

Saturn transit through the **4th from natal Moon** — pressure on home,
mother, comfort, vehicles. Less severe than Sade Sati but worth noting
if active.

### 2.6 Remedies (classical + commonly cited)

- Hanuman Chalisa daily — Saturn's specific protector deity in modern tradition
- Donation Saturday — black sesame, mustard oil, iron, dark cloth
- Service to elderly, labourers, the disabled — direct Saturn karma
- Avoid taking on new debt, new marriages, major risks during Madhya phase
- Sapphire (neelam) — **never without expert review**; a wrong sapphire can devastate within days

---

### 2.7 Sade Sati — what is sourced and what is not, measured 2026-10-17 (#191)

**§2.1 above cites *Phaladeepika*, *Brihat Jataka* and *Saravali*. None of the
three is in `data/`, and none is in `fetch_corpus.py`'s registry** — the same
#216 defect the `[BPHS]` licence was withdrawn for. What follows replaces that
citation with a book we hold, and marks what remains unsourced.

#### 2.7.1 SOURCED: the definition and the durations — Rao, *Lessons* Vol. I

`data/book1-for-CD.pdf` (P.V.R. Narasimha Rao, *Lessons on Vedic Astrology*,
Vol. I), **plain `pdftotext`, 12,244 lines**. Lesson #1, numbered note **11**,
printed p. 4, **lines 281–287**:

> *"The periods when transit Sa is posited in three signs i.e., the sign behind
> the Moon, the sign of the Mo and the sign ahead of the Mo are called
> Sade-Sati period. This period is important because Mo is the significator of
> the mind and Saturn's placement in these signs may cause much trouble to
> mind. So each Sade-sati period is for 2.5 years and the total is 7.5 years
> for one full rotation of the zodiac."*

That sources, from a book in `data/`:

- the three-sign span — **12th from Moon, Moon's own rasi, 2nd from Moon**;
- **2.5 years per phase, 7.5 years total**;
- the **rationale** — Moon is the significator of the mind, so the affliction is
  mental. §2.2's "mental burden" column is Rao's own reasoning, not ours.

#### 2.7.2 SOURCED: why a strong Saturn softens it — and how strong

Same book, Lesson #1 note **29**, printed p. 7, **lines 476–478**:

> *"If Sa is LL or Yogakaraka, it is hardly going to trouble the person even in
> a Sade Sathi Period."*

**This sources §2.3's third bullet, but narrower than §2.3 states it.** §2.3
says *"A strong natal Saturn (own/exalted/in good house) significantly softens
Sade Sati."* Rao's condition is **functional**, not dignity-based: Saturn as
**lagna lord** or as **yogakaraka** for the ascendant. Own-sign, exaltation and
"good house" are *our* generalisation and remain **UNSOURCED**. The distinction
is load-bearing — Saturn is lagna lord for Capricorn and Aquarius and
yogakaraka for Taurus and Libra, which is a specific, computable set, whereas
"strong" is not.

Note **28** on the same page (lines 474–475) gives the general frame our
dasha/transit material rests on: *"Position in the natal chart is the main
thing – shows what one has to go through in life. Transits show the time when
one has to go though it."* And note **27**: *"In which area Sa wants the native
to work hard depends upon his position in different Varga chakras."*

#### 2.7.3 UNSOURCED: every phase NAME, in both the engine's and this file's spelling

Measured with `scripts/corpus_search.py --absent` across **14 books, 94,019
`-layout` lines**:

| Term | Where it is used in this repo | Hits |
|---|---|---|
| `arohini` | `chart.py:651`, `i18n.py:172` — "Rising Phase (Arohini)" | **0** (3 spellings) |
| `avarohini` | `chart.py:653`, `i18n.py:174` — "Setting Phase (Avarohini)" | **0** (4 spellings) |
| `arambha` | this file §2.1/§2.2, `learn_registry.py:635`, `templates/learn/career-during-sade-sati.html` | **0** (3 spellings) |
| `madhya` | this file §2.1/§2.2, the article, the registry | **1** — Raman, *Astrology for Beginners*, and not about Sade Sati |
| `uttara` | this file §2.1/§2.2, the article, the registry | 48 — **all nakshatra names** (Uttara Phalguni / Uttaraashaadha etc.), not phase names |
| `elinati` (the Telugu name) | nowhere | **0** |
| `ashtama shani` | this file §2.4 | **0** (6 spellings) |

**Rao names no phases.** He describes them positionally — *"the sign behind the
Moon, the sign of the Mo and the sign ahead of the Mo"* — and stops. So:

| Open finding | Verdict |
|---|---|
| Engine says `arohini` / `avarohini`; `knowledge/` says `Arambha` / `Uttara`; both sets absent from the corpus | **BOTH UNSOURCED. The corpus cannot settle it, and the right answer is NOT to pick one.** This is a CONTESTED-by-silence case: the names are real in modern practice (they are in wide circulation) but no book we hold uses either set, so neither can be presented to a reader as classical |
| The *incoherence* between the two — the same product calls the same phase two different Sanskrit names on two surfaces | **A real defect, and it is the defect.** It is a consistency bug, not a sourcing one, and it is fixable without a source: pick one vocabulary, or describe the phases positionally as Rao does ("Saturn in the sign before your Moon") and drop the Sanskrit |
| `Madhya` as the peak-phase name | **UNSOURCED for this use.** Its single corpus hit is unrelated |
| §2.4 Ashtama Shani (Saturn in the 8th from Moon, ~2.5 years), sourced to "Classical transit literature; BV Raman, KN Rao" | **UNSOURCED.** `ashtama shani` = 0 across all 14 books, and `ashtama` = 0 in Rao's textbook. KN Rao is not in `data/` and not in the registry |

**Positional description is always safe and always sourced.** "Saturn moving
through the sign before your Moon sign, then your Moon sign, then the one
after — about two and a half years each" is Rao's own formulation and needs no
Sanskrit label.

**Nothing here changes a rule.** `chart.py:651–653` and `i18n.py:172–174` are
untouched; so is the article.

---

## 2A. Gochara — transit results by house from the natal Moon

**Gochara is measured from the Janma Rashi (the natal Moon sign), never from
the Lagna.** Raman, verbatim:

> "The passage of planets through certain angular positions from the radical
> Moon is technically termed Gochara."
>
> "The following results are produced by the different planets while
> transiting the different signs from Janma Rasi (Radical Moon)."

§2 (Sade Sati) and §2.4 (Ashtama Shani) above are both special cases of this
same table — Saturn in the 12th/1st/2nd and Saturn in the 8th, counted from
the Moon; Raman confirms the link himself ("*his transit in the 12th, the 1st
and the 2nd from the radical Moon ... goes under the technical name of Sade
Sati*").

> **A correction worth keeping.** The first version of this section quoted a
> different line as *"the Moon and the birth [rashi] play a prominent part"*.
> The book says the birth **constellation**, and Raman uses "constellation"
> for nakshatra throughout — the bracket converted a claim about the birth
> star into one about the birth sign. The conclusion was right and the
> evidence was tampered with, which is the harder failure to catch. The two
> quotes above need no brackets.

Benefic and malefic houses, counted from the natal Moon:

| Planet | Benefic houses | Malefic houses |
|---|---|---|
| Sun | 3, 6, 10, 11 | 1, 2, 4, 5, 7, 8, 9, 12 |
| Moon | 1, 3, 6, 7, 10, 11 | 2, 4, 5, 8, 9, 12 |
| Mars | 3, 6, 11 | 1, 2, 4, 5, 7, 8, 9, 10, 12 |
| Mercury | 2, 4, 6, 8, 10, 11 | 1, 3, 5, 7, 9, 12 |
| Jupiter | 2, 5, 7, 9, 11 | 1, 3, 4, 6, 8, 10, 12 |
| Venus | 1, 2, 3, 4, 5, 8, 9, 11, 12 | 6, 7, 10 |
| Saturn | 3, 6, 11 | 1, 2, 4, 5, 7, 8, 9, 10, 12 |
| Rahu / Ketu | 3, 6, 11 | 1, 2, 4, 5, 7, 8, 9, 10, 12 |

> Source: B.V. Raman, *Astrology for Beginners*, Ch. XII "Transits or
> Gochara" — benefic/malefic table, p.101 (the copy in `data/`; line 5203+
> under `pdftotext -layout`). The per-house prose on pp.98-100 was read
> independently and agrees with the table for Jupiter, Saturn and Rahu/Ketu.
> Rahu and Ketu share ONE row in Raman; he gives them no separate lists.
>
> Two OCR notes, both resolved by cross-reading the prose: Jupiter's malefic
> row prints as `1, 3, 4, .p, 8, 10,12` — the artefact is `6`, confirmed
> because benefic (2,5,7,9,11) plus malefic must cover all twelve, and the
> prose gives 6) *"grief and misery"*. Saturn's 5th and 6th entries are
> garbled mid-page; the table supplies both.

**Independently corroborated.** Narasimha Rao's `vedic_astro_textbook.pdf`
carries the same table twice by a different route — §25.2 Tables 53-59 and
§26.3 Table 63 — including the Rahu/Ketu row. That matters most for Ketu,
where our code previously carried an invented value; it is now sourced twice
rather than once. One wrinkle recorded so the next reader is not surprised:
Rao's Table 58 marks Venus's 8th and 12th "Bad" while his own Table 63 lists
both as auspicious. Raman and Rao-Table-63 agree; Table 58 is the outlier.
This section follows Raman.

**Every house is classified.** There is no "neutral" third category in Raman —
each of the twelve is benefic or malefic for each planet. Code that lists only
a handful of houses and defaults the rest to neutral is inventing a category
the source does not have.

**Scope note.** `chart.py:compute_gochar_impacts` evaluates only Saturn,
Jupiter, Rahu and Ketu. Raman supports that emphasis: *"the transiting effects
of the slow moving ones, viz., Jupiter, Saturn and Rahu are universally held
to be most powerful. The triennial influence may be read from Saturn, the
yearly influence from Jupiter..."*. The other five rows are recorded here so
the source is not lost if the scope widens.

**What this table does NOT cover.** Raman immediately adds two qualifiers we
do not implement: *"There are exceptions under which certain planets said to
produce malefic effect while transiting certain house, do not manifest
anything unfavourable at all"* — he points at his own Ashtakavarga book for
these, and does **not** use the word *Vedha* anywhere (0 occurrences in the
whole text). The Vedha machinery, with its exception rules ("Sun and Saturn do
not cause vedha on each other; Moon and Mercury do not cause vedha on each
other"), is Narasimha Rao, `vedic_astro_textbook.pdf` §26.3 Table 63. An
earlier draft of this section credited Vedha to Raman; it should not have. And
Mars and the Sun act in the first 10° of a sign, Jupiter and Venus in the
second 10°, while Rahu acts throughout. A bare house verdict is therefore the
first approximation, not the finished judgement — say so rather than
overstating certainty.

---

## 3. Kaal Sarp Dosh

### 3.1 Definition

All 7 traditional grahas (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn)
fall on one side of the **Rahu-Ketu axis**. Twelve named variations based
on which house Rahu occupies (Anant, Kulika, Vasuki, Shankhapal, Padma,
Mahapadma, Takshak, Karkotaka, Shankhachuda, Ghatak, Vishdhar, Sheshnag).

### 3.2 Classical status — important

**Kaal Sarp Dosh is NOT in BPHS, Phaladeepika, Saravali, Jataka Parijata,
or Brihat Jataka.** It is a **20th-century innovation**, popularized
heavily by Trimbakeshwar temple priests in Maharashtra. Many classical
scholars (including KN Rao) explicitly state it has no scriptural basis.

> Source: KN Rao, "Predicting Through Jaimini's Chara Dasha", and several
> contemporary critiques.

### 3.3 How to phrase Kaal Sarp Dosh in a reading

- Honest framing: "Your chart shows the Kaal Sarp pattern — all planets on one side of the Rahu-Ketu axis. This is a modern classification not found in classical texts like BPHS or Phaladeepika, so treat it with measured caution. The pattern can indicate periods of focus or struggle in the houses Rahu/Ketu occupy, but does NOT guarantee misfortune."
- Avoid alarmist framing or prescribing the Trimbakeshwar puja as the only solution.

---

## 4. Yogas — classical planetary combinations

Yogas are named patterns of planetary placement that grant specific gifts
or burdens. Computed deterministically from the chart, so they belong in
the Python layer (`chart.py: compute_yogas`) rather than in prompt-injected
text. This section is the spec the Python rules implement.

> Primary source for sections 4.1–4.5: P.V.R. Narasimha Rao,
> *Vedic Astrology: An Integrated Approach*, Chapter 11 (freely
> distributed by the author; PDF at `data/vedic_astro_textbook.pdf`).
> Cross-referenced against BPHS and Phaladeepika.

### 4.1 Pancha Mahapurusha — the "Five Great Person" Yogas

Formed when a non-luminary graha (Mars, Mercury, Jupiter, Venus, Saturn)
is in **own sign or exalted AND in a kendra (1/4/7/10) from Lagna**.

| Yoga | Planet | Required sign | Effects |
|---|---|---|---|
| **Ruchaka** | Mars | Aries, Scorpio, Capricorn | Fiery great-man; courage, leadership, victory, occult skill |
| **Bhadra** | Mercury | Gemini, Virgo | Earthy great-man; learning, eloquence, systematic mind, business |
| **Hamsa** | Jupiter | Sagittarius, Pisces, Cancer | Ethery great-man; wisdom, respect, dharma, scholarly fame |
| **Malavya** | Venus | Taurus, Libra, Pisces | Watery great-man; beauty, luxury, art, marital happiness |
| **Sasha** | Saturn | Capricorn, Aquarius, Libra | Airy great-man; discipline, leadership of multitudes, charity |

### 4.2 Surya (Sun) Yogas

| Yoga | Definition | Effects |
|---|---|---|
| **Vesi** | A planet (not Moon) in 2nd from Sun | Balanced outlook, truthful, content |
| **Vosi** | A planet (not Moon) in 12th from Sun | Skillful, charitable, famous, learned |
| **Ubhayachara** | Planets (not Moon) in BOTH 2nd and 12th from Sun | All comforts; royal stature |
| **Budha-Aditya (Nipuna)** | Sun and Mercury conjunct in one sign | Intelligent, skillful, respected (weakened if Mercury is combust within ~6°) |

### 4.3 Chandra (Moon) Yogas

| Yoga | Definition | Effects |
|---|---|---|
| **Sunaphaa** | Planets (not Sun) in 2nd from Moon | Royal stature; intelligent, wealthy, famous; self-earned wealth |
| **Anaphaa** | Planets (not Sun) in 12th from Moon | Good-looking, disease-free, reputed, comfortable |
| **Duradhara** | Planets (not Sun) in BOTH 2nd and 12th from Moon | Pleasures, charity, wealth, vehicles, good servants |
| **Kemadruma** | NO planets (other than Sun) in 1st, 2nd, or 12th from Moon AND no planets in kendras from Lagna | Unlucky, troubled — KILLS other good yogas. Flag with care; cancellations exist when Moon conjoins/aspects a planet, or kendras are occupied. |
| **Chandra-Mangala** | Moon and Mars conjunct | Worldly-wise, materially successful; classical warning: may earn unscrupulously / mistreat women |
| **Gaja-Kesari** | Jupiter in a kendra (1/4/7/10) FROM Moon — strict version adds: Jupiter not debilitated/combust/in enemy sign | Famous, wealthy, intelligent, virtuous, liked by authority |

### 4.4 Vipareeta Raja Yogas (success from struggle)

Lords of the dusthanas (6/8/12) placed in dusthanas neutralize their own
houses' negative effects and grant **tremendous success after struggle**.

| Yoga | Definition |
|---|---|
| **Harsha** | 6th lord placed in the 6th |
| **Sarala** | 8th lord placed in the 8th |
| **Vimala** | 12th lord placed in the 12th |

### 4.5 Other high-signal classical yogas

| Yoga | Definition | Effects |
|---|---|---|
| **Guru-Mangala** | Jupiter and Mars conjunct or in mutual 7th | Righteous, energetic in dharmic action |
| **Trilochana** | Sun, Moon and Mars in mutual trines (4 signs apart) | Wealthy, intelligent, long-lived, victorious |
| **Amala** | Only natural benefics in 10th from Lagna OR Moon | Ever-lasting fame, royal respect, virtue |
| **Vasumati** | Benefics occupy upachayas (3rd, 6th, 10th, 11th) | Abundant wealth |
| **Kulavardhana** | Every planet in 5th from Lagna OR Moon OR Sun | Brings honor to lineage; line of successors |
| **Adhi** | Natural benefics in 6th, 7th and 8th from Moon | King, minister, or army chief |
| **Sakata** | All planets in 1st and 7th | Classical negative: friendlessness, hardship — verify with cancellations before flagging |
| **Sarpa** | Three kendras occupied by natural malefics | Classical negative: cruelty, dependence — verify before flagging |

### 4.6 Nabhasa Yogas (shape / count of occupied signs)

Pattern yogas formed by the distribution of the 7 classical planets across
signs and houses. Many; only the highest-signal ones are worth surfacing:

| Yoga | Definition |
|---|---|
| **Rajju** | All planets in movable signs (Aries, Cancer, Libra, Capricorn) |
| **Musala** | All planets in fixed signs (Taurus, Leo, Scorpio, Aquarius) |
| **Nala** | All planets in dual signs (Gemini, Virgo, Sagittarius, Pisces) |
| **Mala** | Three kendras occupied by natural benefics |
| **Kamala** | All 7 planets in kendras (1/4/7/10) |
| **Chakra** | All planets in odd houses (1/3/5/7/9/11) |
| **Samudra** | All planets in even houses (2/4/6/8/10/12) |

### 4.7 Benefic / malefic classification (used by yoga rules)

- **Natural benefics:** Jupiter, Venus, Moon (when waxing and not afflicted),
  Mercury (when not joined by malefics).
- **Natural malefics:** Saturn, Mars, Sun, Rahu, Ketu, Moon (when waning/dark).
- **Functional** benefic/malefic is chart-specific (rules over benefic houses
  vs. dusthanas); deferred — for V1 we use natural classification.

### 4.8 How to phrase yogas in a reading

- Name detected yogas explicitly. "Your chart has a Hamsa Yoga — formed by Jupiter exalted in Cancer in a kendra. Per Parashara, this grants wisdom, dharmic respect, and scholarly success across life."
- **Cite source** when the yoga has a strong classical pedigree ("per BPHS", "per P.V.R. Narasimha Rao's compilation of classical yogas").
- For **negative yogas** (Kemadruma, Sakata, Sarpa, Sula): mention only with the cancellation context. A bare "you have Kemadruma" is harmful and usually wrong — these have multiple classical cancellations the Python should check before flagging.
- Pancha Mahapurusha yogas are lifelong gifts — frame as such, not as period-bound.

---

## 5. Vimshottari Dasha — interpretation principles

### 5.1 Sequence and durations

Ketu 7y → Venus 20y → Sun 6y → Moon 10y → Mars 7y → Rahu 18y →
Jupiter 16y → Saturn 19y → Mercury 17y. Total 120 years.

### 5.2 Reading a Mahadasha — the three-factor rule

A Mahadasha's results depend on:

1. **Natal strength of the dasha lord** — own/exalted/well-aspected = strong, gives best of that planet's significations. Debilitated/combust/afflicted = weak, gives troubles.
2. **House the dasha lord rules** — the lord activates its owned houses' significations during its period.
3. **House the dasha lord occupies** — the lord delivers results through that house.

> Source: *BPHS*, dasha chapters; *Phaladeepika* chapter on dashas.

### 5.3 Antardasha (sub-period) — the trigger

The Mahadasha sets the BACKDROP. The Antardasha within it sets the EVENT.
Marriage, job, child, illness — these specific events are typically triggered
by the Antardasha lord (especially if it rules a relevant house).

### 5.4 Common reading patterns

- **Sun Mahadasha** — career, identity, authority, father, government. Not a marriage period unless an Antardasha activates Venus/7th-lord.
- **Moon Mahadasha** — emotional life, mother, home, public roles, mind.
- **Mars Mahadasha** — energy, conflict, property, siblings, surgery, sports/military.
- **Mercury Mahadasha** — communication, business, learning, networks. Often a money/career-building phase.
- **Jupiter Mahadasha** — wisdom, children, marriage (very often marriage triggers in Jupiter dasha), wealth, dharma.
- **Venus Mahadasha** — marriage, comfort, luxury, partnerships, art. Strongest marriage-trigger dasha.
- **Saturn Mahadasha** — discipline, structure, hard work, long-term gains, sometimes loss/withdrawal.
- **Rahu Mahadasha** — sudden rise/fall, foreign things, technology, ambition, obsession, unconventional paths.
- **Ketu Mahadasha** — detachment, spirituality, loss, isolation, mokshic themes.

### 5.5 Marriage timing — classical indicators

Marriage typically happens when ONE OR MORE of these are running:

- Dasha or Antardasha of **Venus** (karaka for marriage in male chart)
- Dasha or Antardasha of **Jupiter** (karaka for marriage in female chart)
- Dasha or Antardasha of the **7th lord**
- Dasha or Antardasha of a planet **occupying or aspecting the 7th house**
- A **transit of Jupiter** through the 7th house or over the natal Moon

If none of these are running, marriage is unlikely in that window even if
the seeker is anxious about it.

---

## 5A. Karakas — Significators

> Source: P.V.R. Narasimha Rao, Ch. 8 ("Karakas"). Three karaka systems with
> distinct purposes — Rao is emphatic that they must NOT be mixed.

### 5A.1 The three karaka systems

| Type | Count | Deity | Domain of use |
|---|---|---|---|
| **Naisargika** (natural) | 9 (7 planets + Rahu + Ketu) | Brahma | All general Phalita Jyotish — every life matter |
| **Chara** (variable, Jaimini) | 8 (7 planets + Rahu; **no Ketu**) | Vishnu | Raja yogas, sustenance, spiritual progress, karma carried across lives |
| **Sthira** (fixed) | 7 planets only | Shiva | **Timing the DEATH of specific relatives only** — not for general prediction |

> *"One should not use the three types of karakas in a mixed-up way. Karakas of each type have a specific purpose."*

### 5A.2 Naisargika Bhava Karakas — planet per house

The planet that signifies each of the 12 houses regardless of chart specifics:

| House | Karaka | Matter |
|---|---|---|
| 1st | **Sun** | Self, physical body, soul, health |
| 2nd | **Jupiter** | Family, wealth |
| 3rd | **Mars** | Younger siblings, courage |
| 4th | **Moon** | Mother |
| 5th | **Jupiter** | Children |
| 6th | **Mars** | Enemies |
| 7th | **Venus** | Spouse, marital bliss, relationships |
| 8th | **Saturn** | Longevity, troubles |
| 9th | **Jupiter** | Teacher, religion, fortune |
| 10th | **Mercury** | Work, achievements, honors |
| 11th | **Jupiter** | Elder siblings, gains |
| 12th | **Saturn** | Losses |

Computable trivially. When reading any house, also examine the karaka planet's placement.

### 5A.3 Naisargika "Nth house from karaka" technique

For naisargika karakas: to study a matter, look at the **Nth house from the karaka planet** (where N is the house associated with that matter).

> *"Mercury and 5th house show memory and so the 5th house from Mercury shows memory."*

Extended significations table (lesser-known mappings worth surfacing):
- **Mars** → real estate (4th from Mars), loans (6th from Mars)
- **Mercury** → speech (2nd from Mercury), credits/credibility (11th from Mercury)
- **Jupiter** → traditional learning (4th from Jupiter)
- **Saturn** → following/disciples (5th from Saturn), hospitalization (12th from Saturn)
- **Rahu** → pilgrimages, foreign travel (9th from Rahu)
- **Ketu** → moksha (12th from Ketu)

### 5A.4 Chara Karakas (Jaimini) — computation

Eight karakas assigned by **degrees of advancement within sign**, in decreasing order:

| Rank | Karaka | Slug | Represents |
|---|---|---|---|
| 1 (highest deg) | **Atma Karaka** | AK | Self, inner self |
| 2 | Amatya Karaka | AmK | Ministers, advisors |
| 3 | Bhratri Karaka | BK | Siblings |
| 4 | Matri Karaka | MK | Mother |
| 5 | Pitri Karaka | PiK | Father (can also = boss) |
| 6 | Putra Karaka | PK | Children, subordinates |
| 7 | Jnaati Karaka | GK | Rivals, enemies |
| 8 (lowest deg) | Dara Karaka | DK | Spouse |

**Computation procedure:**
1. Take 8 planets — Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu (no Ketu)
2. For each, find advancement from start of its rasi (longitude within sign)
3. **Exception for Rahu**: use `30° − Rahu's longitude-in-sign` (he counts backward)
4. Sort descending by advancement → assign AK through DK

Ties: compare minutes, then seconds. If exact tie, both share the karakatwa and the next slot has no ruler — fall back to the corresponding sthira karaka.

**COMPUTABLE: YES** — pure arithmetic on longitudes. Deferred to V2 for our chart code; would unlock Jaimini-style readings (Karakamsa, AK's significations as inner-self, etc.).

### 5A.5 Sthira Karakas — relatives' death only

| Relative | Sthira karaka |
|---|---|
| Father | Sun OR Venus (whichever is stronger) |
| Mother | Moon OR Mars (whichever is stronger) |
| Younger siblings, brother/sister-in-law (spouse-of-sibling) | Mars |
| Maternal relatives | Mercury |
| Husband, sons, paternal grandparents | Jupiter |
| Wife, father-in-law, mother-in-law, maternal grandparents | Venus |
| Elder siblings | Saturn |

Strict scope — Rao is emphatic these are only for timing relatives' death, NOT for general prediction.

### 5A.6 The marriage-karaka warning (Rao)

> *"Some astrologers use the 7th from Jupiter instead of the 7th from Venus to predict marriage. However, Venus is the natural significator of marriage and the 7th from Venus should be used for predicting marriage, both in male and female charts. When predicting the death of spouse, we use Jupiter in female charts and Venus in male charts."*

Important distinction — our marriage logic uses Venus, which aligns with Rao.

### 5A.7 Karaka Bhava Nashaya — NOT covered by Rao

The classical principle "a planet sitting in the house it is karaka for damages that house" appears in BPHS/Phaladeepika tradition but is **not stated in Rao's textbook**. If our knowledge file references it, source it from BPHS, not Rao.

---

## 5B. Timing — Rao's dasha and transit apparatus (extracted 2026-10-17, #191)

**Why this section exists.** Every question the live site actually gets — *will
I clear this exam, will I get a job, will I marry this year, when will the
money come* — is a **timing** question, and `prompts/ask.txt`'s CATEGORY
GUIDANCE gives one topic line per category and names no classical rule at all.
The `/ask` request carries natal chart, current dasha and the vedic flags, and
**no transit data whatsoever**. So the timing doctrine was being supplied
entirely from model recall. This section is what Rao actually says, so the gap
is at least visible and citable.

**Flag and fingerprint:** all line ranges are **plain `pdftotext`** (no
`-layout`) over `data/vedic_astro_textbook.pdf` = **20,669 lines**, and over
`data/book1-for-CD.pdf` (Rao, *Lessons* Vol. I) = **12,244 lines**. `grahas.md`
§12 cites the textbook under `-layout` (16,724 lines); the schemes do not
interchange.

**Chapter map correction.** `SOURCES.md` lists the dashas as "Ch. 16-25" and
predictive techniques as "Ch. 26-33". Measured: **Ch. 16–24** are the dasha
systems (Vimsottari 10311, Ashtottari 10801, Narayana 11066, Lagna Kendradi
12081, Sudasa 12240, Drigdasa 12371, Niryaana Shoola 12549, Shoola 12764,
Kalachakra 12991), **Ch. 25–26** are transits (13982, 15187), **Ch. 27–29** are
Tajaka (16124, 16461, 17260), **Ch. 30–31** are annual and Sudarsana Chakra
dasas (17619, 17993), Ch. 32 is birthtime error (18200) and Ch. 33 is rational
thinking (18845). There is also an unnumbered **Part 6: Real-life Examples**
(20324–20669) which the map does not mention at all and which is the single
most useful part of the book for this product.

### 5B.1 The general rule: a dasha lord delivers what it promises IN A VARGA

[Rao §16.5.1, lines 10486–10513]

> *"Vimsottari dasa is a very general phalita dasa that can also be used as an
> ayur dasa. All kinds of general results can be seen from it. **A planet gives
> the results promised by its positions in various divisional charts.**"*
> — lines 10494–10496

**This is Rao's answer to "does this Mahadasha/Antardasha lord support this
bhava".** It is not a lookup on the lord's natal house in D-1; it is *the
lord's placement in the varga that owns the question.* Rao's nine examples,
verbatim [lines 10497–10509]:

| # | Rao's example | Life area |
|---|---|---|
| 1 | *"Period of the 5th lord in D-7 can give a child."* | children |
| 2 | *"Period of the 8th lord in rasi chart can give some troubles and frustration."* | general |
| 3 | *"Period of a planet exalted in GL in D-10 can give power and authority in career."* | **career** |
| 4 | *"Period of an exalted planet in the 12th from AK in D-9 can give serious thoughts related to spiritual liberation."* | spiritual |
| 5 | *"Period of the 7th lord in D-9 can give marriage."* | **marriage** |
| 6 | *"Period of a planet with Rahu in the 9th in D-4 can give foreign residence."* | relocation |
| 7 | *"Period of an exalted planet aspecting HL from the 11th from AL in rasi chart can give a lot of wealth."* | **money** |
| 8 | *"Period of a planet joined by Moon and Saturn in the 8th house in D-30 may give serious psychological problems and suicidal tendencies."* | mental health |
| 9 | *"Period of a well-disposed planet aspecting A3 in D-10 may make one write some books."* | output |

And the recursion rule [lines 10510–10513]: *"Each planet gives the results
indicated by it in its dasas and antardasas. **When analyzing antardasas, we
can take the dasa lord as a temporary lagna and analyze the charts.**"*

**Example 8 is a safety matter, not a feature.** Rao writes it as a dasha
result; this product must never render anything of that kind. It is recorded
here because an engineer reading §16.5.1 will meet it, and because Rao's own
ethics rule (§5B.6) is the right response to it.

### 5B.2 Which dasha level answers which question — the Tripod of Life

[Rao §16.5.3 "Rath's 'Tripod of Life' Principle", lines 10543–10563]

> *"Sun, Moon and lagna form the 'tripod of life'. **Parasara clearly said that
> we should analyze all charts with respect to the positions of Sun, Moon and
> lagna.**"* — lines 10547–10548

Rao's assignment, which is the most directly useful rule in the chapter:

| Dasha level | Reference point to judge it from | Rao's reason |
|---|---|---|
| **Mahadasha** | **Sun** (soul) | *"The results experienced due to soul (Sun) last long and change slowly."* |
| **Antardasha** | **Moon** (mind) | *"The results experienced due to mind (Moon) last shorter and change fast."* |
| **Pratyantardasha** | **Lagna** (body) | *"The results experienced due to body (lagna) change even faster."* |

[lines 10552–10558]

And the matching rule for **when a yoga pays out**, which is new material for
this corpus [lines 10559–10562]:

> *"If a planet takes part in a **Ravi yoga** (solar combination), it gives the
> results of the yoga in its **mahadasa**. If a planet takes part in a
> **Chandra Yoga** (lunar combination), it gives the results of the yoga in its
> **antardasas**. If a planet takes part in other yogas (e.g. a **Raja Yoga**),
> it gives the results of the yoga primarily in its **pratyantardasas**."*

> *"In addition, dasa lord can be taken as a reference point when interpreting
> antardasas."* — line 10563

**Note what this does to the #398 B question.** Rao's own timing rule puts a
Raja Yoga's payout at the **pratyantardasha** level — the shortest, finest
level — which is the opposite of "fully manifested". See `yogas.md` §13.1.

### 5B.3 Transits — the half the `/ask` path does not have

| Rule | Rao | Lines |
|---|---|---|
| **Natal vs transit, stated plainly** | *"Natal positions stand for the innate potential of a nativity and the transit positions show the temporary influences – planetary pulls and pushes."* | §25.7, 15108–15110 |
| Rao's *Lessons* puts it more usably | *"Position in the natal chart is the main thing – shows what one has to go through in life. **Transits show the time when one has to go though it.**"* | *Lessons* Vol. I, Lesson #1 note 28, printed p. 7, lines **474–475** |
| **The master transit rule** (Rao sets it in bold type) | *"A planet occupying or aspecting a rasi in transit influences the matters signified by the houses and planets stationed in that rasi in the natal chart. The exact nature of the influence exerted by a planet depends on its inherent nature and the matters it stands for in the natal chart."* | §25.3, 14394–14398 |
| **The dasha↔transit link** | *"The most popular natal reference in transit analysis is Moon … **The transit of Vimsottari dasa lord is particularly important, because he is the one who has the greatest influence on one's mental state during a period.**"* | §25.2, 13994–13999 |
| Coarse vs fine timing | *"the interaction between the **natal divisional charts and the transit rasi chart** helps in **coarse** timing of events and the interaction between the **natal rasi chart and transit divisional charts** helps in **fine** timing of events."* | §25.7, 15111–15113 |
| Worked marriage transits | *"Jupiter transiting in the Ta may give marriage to someone born in Sc lagna, because Ta is the 7th house from Sc. Saturn transiting in Ar may give relationship problems or marital problems for someone born in Li lagna, because Ar is the 7th house from Li."* Also: Jupiter in Virgo aspects Taurus (7th from Scorpio) **and** natal Venus in Pisces, *"and hence he may give marriage"* | §25.3, 14376–14384 (sign transits) and 14385–14391 (aspects) |
| Saturn transits over the three lagnas | *"Saturn's transit over the rasi containing one's lagna may throw obstructions and hamper one's activities. Saturn's transit over the rasi containing one's Chandra lagna may create frustration and mental depression. Saturn's transit over the rasi containing one's paaka lagna may leave one feeling sick all the time and attack the physical vitality."* | §7.3.5, 3517–3521 |

**One honesty marker to preserve.** Rao flags his own varga-transit method as
*his own research*, not classical: *"the actual approach is essentially based on
this author's own researches … readers are advised to keep in mind that what
follows is a product of the very limited intelligence of this author and hence
prone to errors."* [§25.4, lines 14440–14452]. If this product ever ships
varga transits, that provenance travels with them.

### 5B.4 Timing an event, not a tendency — Rao's method as he actually works it

**Part 6: Real-life Examples** (lines 20324–20669) is five worked predictions
with the reasoning shown. This is the only place in the book where Rao answers
the question shape our users ask.

| # | Question asked of Rao | Lines | The apparatus he used |
|---|---|---|---|
| 1 | *"exactly when she would get married"* | 20328–20380 | Vimsottari MD (Jupiter, lagna lord in 11th, aspecting 7th house and 7th lord) → AD (7th lord of **D-9**, which was too late) → Jupiter's **rasi transit** (Pisces = natal lagna, aspecting the 7th and the rasi holding natal Mercury) → **PD** (Mercury, 7th lord in rasi and lagna in D-9, also DK) → cross-check with **Sudarsana Chakra dasa** → cross-check with **Tajaka annual chart** (2nd lord exchange, *vivaha saham*, *muntha* lord, *ithasala* with Venus, upapada lord) → **Patyayini dasa** narrowing to Dec 98/Feb–Mar 99 → then a **cultural** filter: the lunar month of Maagha brings *"the season of marriages in India"* |
| 2 | child's birth date | 20382–20459 | **Narayana dasa of D-7** |
| 3 | *"asked if there was a change of job for him"* | 20460–20542 | **Narayana dasa of D-10**, antardasa read as the **8th from A10** (*"which can show the workplace"*) with its lord in the 12th from A10 → prediction of deterioration, being forced out in June, a better job in July → **PD** resolution in retrospect (Scorpio PD = 8th lord + debilitated Moon = pressure; Sagittarius PD = Sun as lagna lord and lord of the 5th from AL = new job with higher status). A year later, the same native asked whether his career would be stable enough to buy a house — answered from the running MD/AD, plus the **yogada** rule for money and power |
| 4 | *"if her friend's son would get an award or not"* | 20543–20594 | Tajaka **monthly** chart → Tajaka **sixty-hour** chart. See §5B.5 |
| 5 | retro-timing a marriage during birthtime rectification | 20595–20669 | Vimsottari MD (Mercury as 7th lord in the 7th of navamsa) → AD candidates (Mars owning the 2nd and upapada and joining lagna lord; Jupiter) |

**The pattern, stated once:** *pick the varga that owns the question → run that
varga's dasha (Narayana for vargas, Vimsottari for general) → narrow MD → AD →
PD → confirm with a transit → confirm with a second, independent dasha system
(Sudarsana Chakra / Tajaka Patyayini) → apply any cultural or practical filter.*
Rao never predicts from one apparatus.

**What the product has of that chain, measured in `src/astro_ai/` on
2026-10-17:**

| Rao's input | In the code? |
|---|---|
| Vimsottari **mahadasha + antardasha** | ✅ `chart.py` (`DashaPeriod`, `antardasha`) |
| Vimsottari **pratyantardasha** | ❌ `grep -ciE "pratyantar"` = **0** across `src/astro_ai/` |
| D-9 and D-10 | ✅ computed (`navamsa`/`dasamsa`, 10 hits in `chart.py`) |
| **Narayana dasa** (of D-1 or of any varga) | ❌ **0** — the only `narayana` hit is "Lakshmi-Narayana" in `festival_registry.py:388` |
| **Sudarsana Chakra dasa** | ❌ **0** |
| **Patyayini dasa / sahams / a 60-hour Tajaka chart** | ❌ **0**. `chart.py:2948` names Patyayini only to say it is *out of scope*: *"The full Tajik system includes Muntha, Year Lord (Patyayini Dasha lord), Sahams, and dozens of other layers. For v1 we expose the four headline elements…"* |
| Tajaka **annual** chart | 🟡 **partially** — `Varshaphala` (solar return, Muntha house, year lord) exists in `chart.py:2944+`, but it is consumed **only** by `routes/outlook.py` and `templates/outlook.html`. It never reaches `/ask` or the natal reading |
| Ashtottari, Kalachakra, Drigdasa, Sudasa, Shoola | ❌ **0** each |
| **Transits on the `/ask` path** | ❌ `grep -ciE "gochar\|transit"` on `routes/ask.py` = **0** |

So a "will I marry this year" answer from `/ask` is built from **Vimsottari
MD/AD plus the natal chart** — two of the seven inputs Rao used to answer that
exact question, and without the transit step he treats as the one that fixes
the date.

### 5B.5 Rao REFUSES to answer a binary competitive outcome from a dasha

**This is the most product-relevant passage in the book, and it should be read
before any further work on the exam and job categories.** Real-life Example 4,
lines 20559–20576, on whether an Oscar nominee would win:

> *"For someone in the entertainment business, an Oscar nomination itself is a
> major achievement. **We cannot look at the dasas one is running and conclude
> whether one will win the award or not.** Because of the nomination, one will
> get a lot of good publicity. If one doesn't get the award, one may be unhappy
> on that night and the next couple of days. **We cannot say that one will not
> get the award because a bad pratyantardasa is running or that one will get the
> award because a good pratyantardasa is running.** We need to go much deeper
> and look at the 1-2 days surrounding the award. We need to understand the
> native's mood on the morning of March 27. That alone can say whether the
> native won the award on March 26 or not. **Irrespective of whether one wins
> the award or not, a few weeks before March 26 and a few months after March 26
> are bound to be excellent in the native's career. The mood on March 27 is the
> clinching factor."*

Three things follow, and all three are citable:

1. **A dasha does not settle a pass/fail.** Rao says it twice, in both
   directions, about the finest dasha level he uses.
2. **What a dasha DOES settle is the surrounding period's quality** — *"a few
   weeks before … and a few months after … are bound to be excellent in the
   native's career"* — which is exactly the shape of a legitimate answer: the
   period, not the verdict.
3. **His method of last resort is a 60-hour Tajaka chart read for the native's
   MOOD**, not for the outcome. The product computes no Tajaka chart of any
   kind, so it cannot do even this.

**Finding for `prompts/ask.txt` (a finding, not a fix).** The file already
forbids guaranteeing outcomes, in its HONESTY block at **lines 26–30**:
*"Astrology shows tendencies, not certainties"*, *"DO NOT promise outcomes"*,
*"Astrology CANNOT pinpoint specific countries, exact future events, names of
future partners, or guarantee outcomes."* (re-measured 2026-10-17). Rao supplies the *positive*
form of that constraint: the corpus supports answering "what will this period
be like for your studies / your career" and does **not** support answering
"will you pass". The `general` category currently absorbs every exam question
("interpret per question text") with no rule attached, and there is no
studies/education category at all — `grep -ciE "exam|studies|education|student"`
returns **0** in both `prompts/ask.txt` and `routes/ask.py`, and
`grep -ciE "gochar|transit"` returns **0** in `routes/ask.py` — so a
time-bound question reaches the model with no transit data at all, which is
half of Rao's apparatus missing (§5B.3). Both re-measured 2026-10-17; the
CATEGORY GUIDANCE block is `prompts/ask.txt:48–56` and gives one topic line
per category naming no bhava, no chart and no dasha lord. The houses,
charts and references for the studies question **are** now sourced — see
`houses.md` → "Studies and exams" (D-24; 4th for education, 5th for
intelligence/scholarship, 5th from AL for success in competition, 9th for
higher studies, Mercury and Jupiter as karakas) — so the category can be
grounded without inventing a prediction rule.

### 5B.6 Rao's ethics constraint on any timing answer

> *"An ethical astrologer will not scare a client by predicting death, but he
> may caution a client gently before critical periods and suggest some remedial
> measures."*
> — Rao Ch. 13, already quoted at §8.5.5 above

The whole of **Ch. 37 "Ethical Behavior of a Jyotishi"** (lines 20236–20299)
is the long form. And Rao's remedy framing (`remedies.md` §1.1) is the
constructive half: a timing answer that names a hard period should name a
remedy with it.

**Nothing in this section is a prediction rule, and nothing here was added to
any prompt or to `chart.py`.** It is what the book says, with line numbers.

---

## 6. Houses (Bhavas) — significations and structural principles

> Source: P.V.R. Narasimha Rao, Ch. 7 ("Houses"). Cross-checked with BPHS.
> Rao uses Whole Sign houses strictly (our `chart.py` also uses Whole Sign).

### 6.1 Whole Sign houses — Rao's stance

> *"Each rasi is a house. The rasi containing the reference point is the 1st house and the next rasi is the 2nd house."*

Rao explicitly rejects Bhava Chakra, Chalit, Equal House, and Sripathi methods. Our chart code matches this — house = `((sign_index − reference_sign_index) mod 12) + 1`.

### 6.2 House categories (Rao's grid)

| Category | Houses | What it means |
|---|---|---|
| **Trines (Trikonas)** | 1, 5, 9 | Abode of Lakshmi — prosperity, flourishing |
| **Quadrants (Kendras)** | 1, 4, 7, 10 | Abode of Vishnu — sustenance |
| **Panapharas** | 2, 5, 8, 11 | Succedant (kendras from 2nd) |
| **Apoklimas** | 3, 6, 9, 12 | Precedent (kendras from 3rd) |
| **Upachayas** | 3, 6, 10, 11 | Growth houses — gains over time |
| **Dusthanas / Trik** | 6, 8, 12 | Setbacks and obstacles |
| **Chaturasras** | 4, 8 | Square axis |

### 6.3 Purushartha trines (Rao's framework)

| Purushartha | Trine bases |
|---|---|
| **Dharma** (righteousness) | 1, 5, 9 |
| **Artha** (wealth, livelihood) | 2, 6, 10 |
| **Kaama** (desire, relationships) | 3, 7, 11 |
| **Moksha** (liberation) | 4, 8, 12 |

Counting planetary strength in each trikona group reveals which life-aim dominates.

### 6.4 Dusthana inversion rule — Rao's important counter-intuitive insight

> *"If a dusthana is fortified or afflicted by malefics, it may show serious obstacles. If a dusthana is weak, it shows that obstacles will be easily overcome. For example, exalted 8th lord may show a lot of troubles and debilitated 8th lord may show easy sailing."*

So for 6/8/12 houses: **strong lord = stronger obstacles; weak/debilitated lord = fewer problems.** Inverted from the usual "lord strong = good" rule. Worth surfacing in any reading where dusthana lords are involved.

### 6.5 Per-house significations (Rao Ch. 7, augmented)

| # | Sanskrit | Body part | Karaka | Primary | Notable lesser-known |
|---|---|---|---|---|---|
| **1** | Tanu | Head | Sun | Body, complexion, personality, intelligence, strength, fame | Caste; "true self" — distinct from physical self (paaka lagna) and perceived self (arudha lagna) |
| **2** | Dhana | Eyes, mouth, face, voice | Jupiter | Wealth, family, speech, food | Speech read from 2nd from Lagna AND 2nd from Mercury |
| **3** | Sahaja / Vikrama | Throat, ears, arms | Mars | Younger siblings, courage, communication, creativity | Confidants; father's death (maraka — 7th from 9th); expenditure on vehicles/house (12th from 4th) |
| **4** | Sukha / Bandhu | Heart | Moon | Mother, home, vehicles, education, comforts | Motherland, childhood, state of mind, peace; D-12 = mother, D-4 = house, D-16 = vehicles, D-24 = education — different vargas split its topics |
| **5** | Putra / Mantra | Stomach | Jupiter | Children, intelligence, knowledge, mantras | **Poorvapunya** (past-life merit); authority/fame; love and affection; speculation |
| **6** | Ari / Shatru | Hips | Mars | Enemies, service, illness, debt | Agriculture, accidents, mental tension; mother's younger brother (3rd from 4th) |
| **7** | Kalatra / Yuvati | Below navel | Venus | Marriage, spouse, partnership, sex | Long journeys; **death** (7th is a maraka). Marriage read from 7th from Lagna AND 7th from Venus |
| **8** | Ayur / Randhra | Genitals | Saturn | Longevity, sudden events, occult | Loss of friends; **gifts and unearned wealth**; disgrace; secrets. **Inverted rule:** exalted 8th lord = more troubles |
| **9** | Bhagya / Dharma | Thighs | Sun (father), Jupiter | Father, fortune, dharma, gurus, religion | Foreign fortune; **diksha** (religious order); **past life and cause of birth**; intuition, compassion |
| **10** | Karma | Knees | Sun, Mercury, Jupiter, Saturn | Career, profession, status, action | Self-respect; dignity. 10th from Chandra Lagna = mental activity in career; 10th from AL = professional status events |
| **11** | Labha | Ankles | Sun, Moon, Jupiter | Gains, friends, elder siblings | Hopes as distinct from gains; friends as distinct from gains |
| **12** | Vyaya / Moksha | Left eye, feet | Saturn (loss); Ketu (moksha) | Loss, expenditure, foreign residence, **moksha** | Bed pleasures; sleep; **meditation**; donation; secret enemies; residence away from birthplace |

### 6.6 Bhavat Bhavam ("house from a house")

A second-order technique Rao explicitly endorses: meanings of houses can be composed. Examples:

- 4th = 2nd from 3rd → wealth/speech of younger sibling
- 9th = 7th from 3rd → younger sibling's spouse
- 3rd = 12th from 4th → expenditure on vehicles and house
- 3rd = 7th from 9th → father's death (maraka to the 9th)

> *"We can find houses from houses and concatenate the meanings."*

Computable: `meaning(houseA from houseB) = house at position ((A − B) mod 12) + 1 from Lagna`, combined semantically. Useful for nuanced LLM readings — currently deferred to V2 (would expand significations table 12× and risk over-interpretation).

### 6.7 Reference points — what "lagna" to count from

The same house has different meanings depending on which reference you count from:

| Reference | What it reveals |
|---|---|
| **Lagna** | True self — intentions, knowledge, persistence |
| **Chandra Lagna (Moon)** | Mind — happiness, ambition, mental view of matters |
| **Ravi Lagna (Sun)** | Soul, physical vitality |
| **Arudha Lagna** | Perceived self — status, material illusion, how the world sees you |
| **Paaka Lagna** (Lagna lord's sign) | Physical self |
| **Karakamsa** (AK in D-9) | Inner self in navamsa; 12th from it → moksha (especially with Ketu) |
| **Graha Lagnas** | Karaka planet as reference (see §6.8) |

> *"Academic reputation is related more to the perceived self (AL) than the true self (lagna). So it is seen from the 5th from arudha lagna. Intelligence and scholarship, on the other hand, are related to the true self and they are seen from the 5th from lagna."*

### 6.8 Graha Lagnas (Rao Table 12) — houses signified by planets

When a karaka planet is stronger than Lagna for a topic, count that house FROM the karaka instead:

| Planet | Houses it signifies |
|---|---|
| Sun | 9th, 10th, 11th |
| Moon | 1st, 2nd, 4th, 9th, 11th |
| Mars | 3rd |
| Mercury | 6th |
| Jupiter | 5th |
| Venus | 7th |
| Saturn | 8th, 12th |

> *"If Mars is stronger than lagna, then the 3rd house from Mars may be more important than the 3rd house from lagna."*

### 6.9 Divisional chart routing (Rao's question→varga table)

When generating predictions about a specific topic, the most accurate read often comes from the topic-specific divisional chart, not the natal D-1. Our V1 only uses D-1 — V2 should layer these:

| Question | Chart |
|---|---|
| Marriage as dharma | D-9 (Navamsa) |
| Career & honors | D-10 (Dasamsa) |
| Education | D-24 (4th house) |
| Intelligence, scholarship | D-24 (5th house) |
| Religion / spirituality | D-20 |
| Vehicles | D-16 |
| Children | D-7 |
| Siblings | D-3 |
| Parents | D-12 |
| Inherent nature, temperament | D-27 |
| Death / longevity primary | Rasi (D-1) |
| Forces of death secondary | D-11 (Rudramsa) |

---

## 7. Doshas to handle honestly

| Dosha | Classical basis | LLM treatment |
|---|---|---|
| Mangal Dosha | Strong (BPHS, Mansagari, multiple texts) | Cite cancellations from Section 1.3 |
| Sade Sati | Strong (Phaladeepika, classical) | Explain phases, avoid alarm |
| Ashtama Shani | Classical transit literature | Mention if active |
| Pitru Dosh | Mentioned in some classical compilations | Cite cautiously — popular but less systematic in classical canon |
| Kaal Sarp Dosh | **NOT in classical texts** | Note as modern classification |
| Guru Chandala (Jupiter-Rahu conjunction) | Classical | Real, worth explaining |
| Shrapit Dosh (Saturn-Rahu conjunction) | Mentioned in modern compilations, weak classical basis | Cite carefully |
| Grahan Dosh (Sun/Moon-Rahu/Ketu conjunction) | Classical eclipse-related | Real, but often over-dramatized |

**Rule of thumb:** if a "dosha" is heavily marketed by puja-vendors and
absent from BPHS/Phaladeepika, treat it as folk classification, not
scripture. Be honest with the seeker about which is which.

---

## 7A. Remedies — classical per-graha catalogue

> Source: P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated Approach*,
> Chapter 34 "Remedial Measures". Rao deliberately keeps this chapter brief
> and defers detailed remedy work to Sanjay Rath's *Vedic Remedies in
> Astrology*. Treat what's here as a starting point, never as prescription.

### 7A.1 Rao's framing — the rules every remedy panel must respect

- *"Those who have no belief in Vedic remedies may skip this chapter."* — remedies are devotional, not transactional.
- Remedies **manipulate the exact details of a fated pattern, not the pattern itself**. They do not overturn karma; they refine its expression.
- Four routes of pacification: (1) gemstones, (2) good deeds, (3) mantras/stotras, (4) deity propitiation.
- **Common-sense action is the first remedy.** If the chart indicates accidents, drive carefully. If it indicates conflict with authority, restrain yourself. No mantra substitutes for prudence.

### 7A.2 Gemstones — Rao's strict cautions

- **Wear a gemstone ONLY for functional benefics in your own chart.** A blue sapphire for someone whose Saturn is a functional malefic can devastate.
- **"Gemstones of functional malefics in a chart should be avoided as far as possible."**
- **"The gemstones of marakas should be avoided when one is running maraka dasas."**
- Gemstones **speed fructification of good already promised**; they do not manufacture results.
- First wearing on the planet's weekday, when the planet is strong in transit.

**Per-graha stones and metals (use ONLY after expert review):**

| Planet | Gemstone | Metal | Weekday |
|---|---|---|---|
| Sun | Ruby | Gold | Sunday |
| Moon | White pearl | Gold | Monday |
| Mars | Red coral | Copper | Tuesday |
| Mercury | Emerald | Silver / Platinum | Wednesday |
| Jupiter | Yellow sapphire | Gold | Thursday |
| Venus | Diamond | Silver / Platinum | Friday |
| Saturn | Blue sapphire | Iron / silver | Saturday |
| Rahu | Hessonite (gomedh) | Silver | Saturday |
| Ketu | Cat's eye | Silver | Tuesday |

**Product stance:** The kundali UI may NAME the stone associated with a graha, but must NOT recommend wearing it. Always defer the wear-decision to a competent astrologer. Anchor the message on Rao's exact quote.

### 7A.3 Good deeds and charity per graha

These are safe to recommend — devotional and harm-free.

| Planet | Good deed | Donation (grain) |
|---|---|---|
| Sun | Help a temple; serve a father-figure | Wheat |
| Moon | Donate to a music institute; help a kind lady | Rice |
| Mars | Physical exercise; donate to a school gymnasium | Toor daal |
| Mercury | Donate to scholarship; honor a scholar | Moong daal |
| Jupiter | Honor a learned priest or guru; donate cows | Chick peas |
| Venus | Read or sponsor poetry; help an artist | A whitish grain |
| Saturn | Manual labor; help labourers and the elderly | Sesame seeds |
| Rahu | Donate to research; go on pilgrimage | Black gram (urad) |
| Ketu | Meditate; quiet retreats | — |

Donate on the planet's weekday morning. Per Rao: small, sincere, regular > large, transactional, one-off.

### 7A.4 Mantras and stotras — Rao's pronunciation caution

> *"Some mantras can produce negative effects with improper recitation. So one should be careful with mantras."*

- Rao deliberately gives mantras only in Devanagari (refuses Roman transliteration) to discourage mispronunciation. Our UI should follow the same convention: show mantras in Devanagari + audio if possible; provide Roman only as a labelled best-effort approximation.
- **Stotras (hymns) are safer than bija mantras** — devotional emphasis matters more than exact intonation. Result is slower but harm-free.
- Reciting the 108 names (Ashtottara Shatanama) of a graha is the safest "mantra" suggestion.
- Repeat on the planet's weekday.

**Recommended recitation counts per graha:**

| Planet | Count |
|---|---|
| Sun | 6,000 | Moon | 10,000 | Mars | 7,000 | Mercury | 17,000 | Jupiter | 16,000 |
| Venus | 20,000 | Saturn | 19,000 | Rahu | 18,000 | Ketu | 7,000 |

### 7A.5 Deity propitiation

| Planet | Primary deities |
|---|---|
| Sun | Shiva, Rama |
| Moon | Gauri, Lalita, Saraswati, Krishna |
| Mars | Hanuman, Rudra, Kartikeya, Narasimha |
| Mercury | Vishnu, Narayana, Buddha |
| Jupiter | Hayagreeva, Vishnu, Parameshwara, Dattatreya, any guru |
| Venus | Lakshmi, Parvati |
| Saturn | Vishnu, Brahma |
| Rahu | Durga, Narasimha |
| Ketu | Ganesha |

Rao's caveat: *"The guidelines given in books are merely guidelines. The exact application depends on an astrologer's knowledge of mythology and classics and familiarity with the natures of various deities."* — a chart-aware deity match is an art.

### 7A.6 Specifically NOT in Rao's Ch. 34

He does **not** cover: Manglik-specific remedies, Sade Sati-specific remedies, yantras, Bhrigu Bindu offerings, or per-dosha remedy lists (Kaal Sarp, Pitru, Kemadruma). For those, our knowledge file uses Mansagari/folk practice with explicit labelling — never citing Rao for what he didn't say.

---

## 8. Tone guardrails for kundali generation

Strengthened with P.V.R. Narasimha Rao's principles from Chapter 33
("Rational Thinking"). These are the author's actual stance, not paraphrase.

### 8.1 Core tone rules

- **Tentative language, never deterministic.** "Tends to…", "often shows up as…", "the chart suggests…", "the likelihood is elevated…" — never "you WILL…" or "this MEANS…" or "you are destined to…"
- **Cite source when stating a classical rule.** "Per Mansagari…", "BPHS describes this as…", "Mantreshwara in Phaladeepika notes…", "Per P.V.R. Narasimha Rao's compilation…"
- **Distinguish classical from folk.** Banana-tree marriage, age-28 Manglik cancellation, Trimbakeshwar puja, "Kaal Sarp = guaranteed misfortune" — name these as folk practice, never as scripture.
- **Refuse to do harm.** Never tell a seeker "your marriage will fail", "you'll lose a parent", "you will die in [year]", "this disease is certain". Translate dosha findings into preparation, not prophecy.
- **Respect agency.** Sade Sati / Manglik / Saturn dasha challenges are TRAINING phases, not punishments. Frame them as such.

### 8.2 Rao's rationalist principles (Ch. 33) — apply throughout

1. **Astrology is interpretive, not (currently) settled science.**
   *"A lot of astrological knowledge of Vedic times became corrupt in the last few hundred years."* Do not claim scientific certainty. Do not say "the stars prove…" or "guaranteed…".

2. **Match the time-scale of the cause to the time-scale of the event.**
   *"Attributing an isolated incident in a day to a dasa that runs for 10 years is irrational."*
   - Daily mood swing → fast transit or sookshma dasa, not Mahadasha
   - Multi-year life phase → Mahadasha is appropriate
   - Don't blame "you're in Saturn Mahadasha" for one bad meeting

3. **Reject vague rules that cover everything.**
   Yogas/aspects/lordships that fire on most charts are not predictive. If we need 6 ORed conditions to explain a marriage, the technique is wrong, not the chart. Stake on ONE strong indicator.

4. **Care about P(B|A), not P(A|B).**
   What matters: *"given this combination, will the event occur?"* — not *"given the event occurred, was the combination present?"* Don't cherry-pick post-hoc explanations.

5. **A correct prediction does not validate the method.**
   *"Success of a prediction does not prove the validity of the methods used."* Don't use anecdotes ("this prediction came true!") as evidence of soundness.

6. **Astrology is probabilistic — at best.**
   Phrase outputs as likelihoods, tendencies, windows ("a marriage window is more likely in 2027–2028" — not "you will marry in March 2027"). Calibrated language, never deterministic.

7. **A true researcher does not compromise.**
   Prefer *"the chart is ambiguous on this point"* over inventing a confident-sounding hand-wave. Hedging through honest uncertainty is better than hedging through manufactured ambiguity.

### 8.3 Direct Rao quotes worth citing in product copy

These are short, attribution-friendly, and align with our stance. Use sparingly — one quote per page is sufficient:

- *"Success of a prediction does not prove the validity of the methods used."* — Ch. 33
- *"Attributing an isolated incident in a day to a dasa that runs for 10 years is irrational."* — Ch. 33
- *"Those who have no belief in Vedic remedies may skip this chapter."* — Ch. 34 (lets us honor the seeker's worldview)
- *"The guidelines given in books are merely guidelines."* — Ch. 34 (justifies our 'consult an astrologer' deferrals)
- *"Some mantras can produce negative effects with improper recitation."* — Ch. 34 (justifies our Devanagari-first mantra display)

---

## 8.5 Reading methodology — Rao's funnel (engineering reference)

> Source: P.V.R. Narasimha Rao, Ch. 13 ("Interpreting Charts"), **plain
> `pdftotext` lines 8723–9211** (chapter head at 8723; §13.1 Introduction 8724,
> §13.2 Functional Nature 8734, §13.3 Baadhakas 8886, **§13.4 Analyzing Charts
> 8949**, §13.5 Examples 9050, §13.6 Conclusion 9203). Pinned 2026-10-17 —
> this section had section numbers but no ranges.
>
> The **five-step funnel in §8.5.1 below is §13.4.1 "Basic Guidelines", lines
> 8955–9010** — (1) divisional chart 8955–8965, (2) house 8966–8972,
> (3) reference 8973–8986, (4) house vs arudha 8987–8993, (5) influences
> 8994–9005, (6) standard results 9006–9010. The family-member rules in
> §8.5.5 are **§13.4.2, lines 9011–9049**.
>
> This section is for engineers building chart-analysis features. It is NOT
> injected into LLM prompts — the natal prompt already instructs the LLM to
> stay at the human-experience layer.

### 8.5.1 The 5-step "Rao Funnel" — apply per question

For any specific question asked of a chart, Rao recommends this funnel:

1. **Pick the right divisional chart** for the topic (see §6.9). Marriage as dharma → D-9; career → D-10; education → D-24; etc.
2. **Pick the right house** within that chart (e.g., within D-24: 4th = education, 5th = intelligence/scholarship/awards).
3. **Pick the right reference point** — Lagna for true self, Arudha for perceived self, the relevant karaka if it's stronger than Lagna.
4. **Choose House vs. Arudha** — Arudha pada when the matter is about perception/maya rather than reality (e.g., A5 for awards vs. 5th house for actual intelligence).
5. **Analyze influences** on the chosen house — occupants, lord, graha drishti, rasi drishti, argala, baadhaka; then positional logic — quadrants sustain, trines let prosper, upachayas let grow, dusthanas bring obstacles.

### 8.5.2 The recursive opening pattern

Rao's worked examples (Madonna, Swami Chandrasekhara Saraswathi, Rajiv & Sanjay Gandhi, twins) all follow the same opening pattern:

1. **State what the Lagna sign indicates** about the native (e.g., Leo → royal/authoritative).
2. **Locate the Lagna lord**, name the yoga it forms.
3. **Identify major yogas** (Rajayoga via 5L/9L conjunction, Tapaswi, Bhadra, Sasa, Budha-Aaditya).
4. **Cross-check against Arudha Lagna** — planets in trines from AL are good, malefics in 3/6/11 from AL are good, malefics in trines from AL are bad.
5. **Repeat the pattern inside the relevant divisional chart**.

Our LLM prompt doesn't expose specific planets/houses to the seeker (per the natal.txt rules), but the underlying chart data we pass to the LLM should provide the conclusions this funnel would generate.

### 8.5.3 Composite analysis rules

**Yogas do not cancel — they coexist.**
> *"There is a powerful rajayoga involving lagna lord and GL lord in the 7th from AL. That yoga cannot go waste. So this native must've enjoyed some power and influence in the society."*

The Swami had renunciation yogas AND a Raja yoga. Rao reads them as compartmentalized life areas (renunciate AND influential), not as cancellation. Apply this when our `compute_yogas()` finds contradictory yogas — let both manifest in the reading.

**Natural vs. functional nature analogy:**
> *"Whether a planet is a natural benefic or natural malefic is analogous to whether a person is inherently good or bad. Whether a planet is a functional benefic or functional malefic is analogous to whether a person does good or bad to one."*

Hold both layers when describing a planet's role.

**Family-chart mirroring expectation:**
> *"Usually, we have such links between the charts of related people."*

For any "read my partner / parent" feature, expect (and surface) parallel placements across related charts.

### 8.5.4 Strength assessment stack

Rao's heuristic order for judging whether a planet/house will deliver:

```
inherent nature  →  functional nature per Lagna  →  yogada/yogakaraka status
              →  placement (own/exalt/quadrant/trine/dusthana)
              →  ashtakavarga rekhas  →  avastha  →  involvement in yogas
```

**Strength signals:** own sign, exaltation, friendly sign, uttamamsa, kendra/trine, yogakaraka, functional benefic (trine lord), yogada, named yoga involvement, high ashtakavarga rekhas (5–7).

**Weakness signals:** debilitation, functional malefic in kendra/trine (unless very strong), dusthana placement (general), baadhaka influence, maraka status.

### 8.5.5 Life-area judgment specifics

**Health & longevity** (Rao Ch. 13, used by /today and any health-adjacent reading):
- Primary chart: Rasi. Secondary: D-11 (Rudramsa), D-30
- Houses of life: 3rd (vitality) + 8th (longevity) — both should be STRONG
- Houses of death: 2nd + 7th (12th from 3rd and 12th from 8th) — both should be WEAK for good longevity
- Marakas: 2L + 7L; their signs are maraka sthanas
- **Ethics:** *"An ethical astrologer will not scare a client by predicting death, but he may caution a client gently before critical periods and suggest some remedial measures."* Apply this rigorously in any longevity-adjacent prediction.

**Career** (D-10):
- Lagna of D-10, Lagna lord, 10th house and lord, AL of D-10, GL of D-10 (for fame), HL of D-10 (for income)
- For authors: read A3 in D-10 (books) separately from 3rd house (writing skill)

**Wealth:**
- Use HL (Hora Lagna) as the money reference
- Any planet aspecting/conjoining/owning BOTH Lagna and HL becomes a **yogada for money** — gives money luck regardless of functional nature

**Children** (D-7):
- 5th house = first child generally; 5L as Lagna of first child; 7L = second; 9L = third
- Direction: odd D-7 Lagna → count forward through odd signs first; even → count backward through even signs first

**Siblings** (D-3):
- 3rd house = younger sibling; 11th house = elder sibling
- 5th = 2nd younger sibling (3rd from 3rd); 9th = 2nd elder sibling

### 8.5.6 What this implies for our LLM prompts

We don't need to expose this methodology to the LLM directly. Instead:
- The structured data we pass (chart, yogas, manglik, sade_sati, dasha) already encodes the conclusions of the funnel
- The LLM's job is narration in plain language, NOT chart analysis
- When we add a new computable rule from this methodology to `chart.py`, the LLM gets it as a flag/value, never as raw doctrine
- Engineering this way keeps the prompt small (Llama free tier) and the analysis verifiable (Python)

---

## 9. Source bibliography

All listed sources are verified live on archive.org (as of June 2026).

### Primary classical texts (English translations, freely downloadable)

| Text | Translator | Archive.org / source |
|---|---|---|
| Brihat Parashara Hora Shastra (BPHS) | R. Santhanam (2 vols) | https://archive.org/details/BPHSEnglish |
| Brihat Parashara Hora Shastra | R. Santhanam (alt scan) | https://archive.org/details/brihatparasarahorashastrabyr.santhanam |
| Brihat Parashara Hora Shastra | Girish Chand Sharma | https://archive.org/details/brihatparasarahorasastrawithenglishtranslationgirishchandsharmavolume1_547_G |
| Phaladeepika | V. Subrahmanya Sastri (1950 ed.) | https://archive.org/details/Phaladeepika2ndEd.1950ByVSubrahmanyaSastri |
| Phaladeepika | V. Subrahmanya Sastri (alt) | https://archive.org/details/in.ernet.dli.2015.92117 |
| Phaladeepika (Hindi, Ojha) | Pandit Gopesh Kumar Ojha | https://archive.org/details/in.ernet.dli.2015.292174 |
| Jataka Parijata | V. Subrahmanya Sastri (vol 1) | https://archive.org/details/JatakaParijataVolIOfIIByVSubrahmanyaSastri |
| Jataka Parijata | V. Subrahmanya Sastri (vol 2) | https://archive.org/details/JatakaParijataVolIIOfIIByVSubrahmanyaSastri |
| Jataka Parijata (original Sanskrit) | Vaidyanatha Dikshita | https://archive.org/details/in.ernet.dli.2015.312156 |

### Rule-compilation references (modern, citation-aware)

- Jagannath Hora — Mangal Dosha Cancellation Rules (compiled from Jataka Parijata, Muhurtha Chintamani): https://jagannathhora.com/mangal-dosha-cancellation-rules/
- AstroSight / Cosmic Squares — modern cancellation rule summaries (cross-reference, not primary)

### Modern scholarship (for cross-checking practice)

- **P.V.R. Narasimha Rao** — *Vedic Astrology: An Integrated Approach* (2000, freely distributed by author in 2010). **Primary modern source** for this knowledge file. PDF stored at `data/vedic_astro_textbook.pdf`. Author is the creator of Jagannath Hora software whose Manglik cancellation rules underpin Section 1.3 above.
  - Chapter 7 ("Houses") — source for Section 6 (houses, Bhavat Bhavam, purushartha trines, dusthana inversion, reference points, divisional routing)
  - Chapter 8 ("Karakas") — source for Section 5A (naisargika/chara/sthira karaka systems)
  - Chapter 11 ("Yogas") — source for Section 4 and `chart.py: compute_yogas()`
  - Chapter 13 ("Interpreting Charts") — source for Section 8.5 (Rao's reading methodology funnel)
  - Chapter 33 ("Rational Thinking") — source for Section 8 tone guardrails
  - Chapter 34 ("Remedial Measures") — source for Section 7A
- KN Rao — *Predicting Through Jaimini's Chara Dasha* (paid)
- BV Raman — *A Manual of Hindu Astrology* (some scans on archive.org)
- Sanjay Rath — *Vedic Remedies in Astrology* (Rao defers detailed remedy work to this text)

### Texts to add later

- *Mansagari* — full English translation. Scribd has fragments; a clean
  archive.org scan is the goal. Until then, Mansagari rules are cited via
  Jagannath Hora's compilation.

---

## 10. Updating this file

When adding new rules:

1. **Cite the source** — text, chapter/verse if known. No source ≠ no add.
2. **Tag classical vs. modern vs. folk.** Honesty about provenance is the
   value of this file.
3. **Add a short example or "how to phrase" line** for the LLM.
4. **Cross-link** to related sections — e.g., a new Saturn rule should
   reference Section 2 (Sade Sati) if relevant.
5. **Date the addition** if it might become stale (current date: 2026-06-29).

---

*Last updated: 2026-06-29*
*Maintained for: Shubh Bhagya (shubhagya.com)*

---

## 27. Nakshatras — the lunar mansions

Nakshatras are the **27 divisions of the 360° zodiac**, each spanning
**13°20'** (800 arc-minutes). Every nakshatra is further split into **4
padas** (quarters) of 3°20' each — the pada system feeds Navamsha
calculations. The Moon transits one nakshatra roughly every 24 hours,
which is why the system is called the **"lunar mansions"**.

The **nakshatra of the Moon at birth** — called the **Janma Nakshatra**
— carries the most weight in classical practice:

- It determines the **first Mahadasha** in the Vimshottari sequence
  (via the nakshatra lord — see §5).
- It's what a subscriber's daily Rashifal is ideally personalised to.
- It's the primary axis of **Ashtakoot Guna Milan** compatibility
  (see the Kundali Matching article).

Every nakshatra carries a fixed set of attributes that classical texts
(Brihat Parashara Hora Shastra, Brihat Samhita, Muhurta Chintamani,
Nakshatra Vijnana) use for interpretation, remedies, and matching.

### 27.1 Attribute glossary

| Attribute | Values | What it decides |
|-----------|--------|-----------------|
| **Ruling planet** (Lord) | Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury, Ketu, Venus | Vimshottari Dasha sequence; general nakshatra flavour |
| **Deity** | Vedic deity (varies) | Psychological / spiritual theme |
| **Symbol** | Object or image | Iconography, easy remembering |
| **Gana** | Deva / Manushya / Rakshasa | Temperament + marriage compatibility (Gana Kuta) |
| **Guna** | Sattva / Rajas / Tamas | Inherent quality (pure / active / inertial) |
| **Varna** | Brahmin / Kshatriya / Vaishya / Shudra | Occupation type (Varna Kuta) |
| **Yoni** | Animal (14 kinds) | Instinct + physical compatibility (Yoni Kuta) |
| **Nadi** | Adi / Madhya / Antya | Health/dosha type (Nadi Kuta — most weighted, 8 pts) |
| **Direction** | Cardinal direction | Beneficial direction for muhurta |
| **Nature** (activity) | Chara / Sthira / Ugra / Mridu / Kshipra / Mishra / Tikshna | What kinds of activities suit this nakshatra |

### 27.2 The 27 nakshatras — canonical reference table

Below: name (Sanskrit), sidereal range (degrees within the zodiac),
lord (Vimshottari), deity, symbol, gana, guna, and 1-line psychological
theme. **Vimshottari lord cycle** is Ketu → Venus → Sun → Moon → Mars →
Rahu → Jupiter → Saturn → Mercury, repeating every 9 nakshatras.

| # | Name | Range | Lord | Deity | Symbol | Gana | Guna | Theme |
|---|------|-------|------|-------|--------|------|------|-------|
| 1 | **Ashwini** | Ari 0°00'–13°20' | Ketu | Ashwini Kumaras (celestial healers) | Horse's head | Deva | Rajas | Speed, initiation, healing, first-mover |
| 2 | **Bharani** | Ari 13°20'–26°40' | Venus | Yama (god of death & dharma) | Yoni / womb | Manushya | Rajas | Bearing, transformation, endurance, sensual power |
| 3 | **Krittika** | Ari 26°40'–Tau 10°00' | Sun | Agni (fire) | Razor / flame | Rakshasa | Rajas | Sharp cutting away, purification, criticism |
| 4 | **Rohini** | Tau 10°00'–23°20' | Moon | Brahma (creator) | Chariot / banyan tree | Manushya | Rajas | Growth, sensual beauty, abundance, favourite of the Moon |
| 5 | **Mrigashira** | Tau 23°20'–Gem 6°40' | Mars | Soma (moon nectar) | Deer's head | Deva | Tamas | Seeking, curious, restless, searching for truth |
| 6 | **Ardra** | Gem 6°40'–20°00' | Rahu | Rudra (storm form of Shiva) | Teardrop | Manushya | Tamas | Storm, breakthrough after grief, sudden change |
| 7 | **Punarvasu** | Gem 20°00'–Can 3°20' | Jupiter | Aditi (mother of gods) | Quiver of arrows / house | Deva | Sattva | Renewal, return home, wisdom after wandering |
| 8 | **Pushya** | Can 3°20'–16°40' | Saturn | Brihaspati (guru of gods) | Cow's udder / lotus | Deva | Tamas | Nourishment, most auspicious nakshatra, spiritual growth |
| 9 | **Ashlesha** | Can 16°40'–30°00' | Mercury | Nagas (serpents) | Coiled serpent | Rakshasa | Sattva | Occult, hypnotic, cunning, healing through poison |
| 10 | **Magha** | Leo 0°00'–13°20' | Ketu | Pitris (ancestors) | Royal throne | Rakshasa | Tamas | Ancestral pride, authority, ritual, lineage |
| 11 | **Purva Phalguni** | Leo 13°20'–26°40' | Venus | Bhaga (delight, wealth) | Front legs of a bed | Manushya | Rajas | Enjoyment, love-making, creativity, leisure |
| 12 | **Uttara Phalguni** | Leo 26°40'–Vir 10°00' | Sun | Aryaman (patron of contracts) | Back legs of a bed | Manushya | Rajas | Commitment, patronage, generous friendship, second half of Phalguni's rest |
| 13 | **Hasta** | Vir 10°00'–23°20' | Moon | Savitar (Sun as inspirer) | Palm of a hand | Deva | Rajas | Craftsmanship, skill of the hand, sleight, healing touch |
| 14 | **Chitra** | Vir 23°20'–Lib 6°40' | Mars | Vishvakarma (divine architect) | Bright jewel / pearl | Rakshasa | Tamas | Design, dazzling appearance, artistic construction |
| 15 | **Swati** | Lib 6°40'–20°00' | Rahu | Vayu (wind) | Young shoot swaying in wind / coral | Deva | Tamas | Independence, movement, sway, unattached self-going |
| 16 | **Vishakha** | Lib 20°00'–Sco 3°20' | Jupiter | Indra & Agni (dual power) | Triumphal arch / potter's wheel | Rakshasa | Sattva | Goal-oriented, focused ambition, determined pursuit |
| 17 | **Anuradha** | Sco 3°20'–16°40' | Saturn | Mitra (friendship, contracts) | Lotus / triumphal arch | Deva | Tamas | Devotion, loyalty in friendship, disciplined love |
| 18 | **Jyeshtha** | Sco 16°40'–30°00' | Mercury | Indra (chief of gods) | Umbrella / earring | Rakshasa | Sattva | Seniority, protective authority, hidden burdens of the eldest |
| 19 | **Mula** | Sag 0°00'–13°20' | Ketu | Nirriti (goddess of dissolution) | Bunch of roots / tied roots | Rakshasa | Tamas | Getting to the root, uprooting, deep investigation, difficult starts |
| 20 | **Purva Ashadha** | Sag 13°20'–26°40' | Venus | Apas (cosmic waters) | Fan / winnowing basket | Manushya | Rajas | Invincible, cleansing waters, undefeatable optimism |
| 21 | **Uttara Ashadha** | Sag 26°40'–Cap 10°00' | Sun | Vishvedevas (all-gods) | Elephant tusk / small bed | Manushya | Sattva | Late-blooming victory, lasting achievements, patient success |
| 22 | **Shravana** | Cap 10°00'–23°20' | Moon | Vishnu (preserver) | Ear / three footsteps | Deva | Rajas | Listening, learning, connection to sacred sound (Om) |
| 23 | **Dhanishta** | Cap 23°20'–Aqu 6°40' | Mars | Ashta Vasus (eight elemental gods) | Drum / flute | Rakshasa | Tamas | Rhythm, wealth, music, group cohesion |
| 24 | **Shatabhisha** | Aqu 6°40'–20°00' | Rahu | Varuna (cosmic waters, oaths) | 100 flowers / empty circle | Rakshasa | Tamas | Healing the many, mystic, secretive, veiled |
| 25 | **Purva Bhadrapada** | Aqu 20°00'–Pis 3°20' | Jupiter | Aja Ekapada (one-footed goat) | Front legs of a funeral bed / two-faced man | Manushya | Sattva | Intensity, penance, transformative fire |
| 26 | **Uttara Bhadrapada** | Pis 3°20'–16°40' | Saturn | Ahir Budhnya (serpent of the deep) | Back legs of a funeral bed / twin | Manushya | Tamas | Depth, wisdom from the depths, calm after storm |
| 27 | **Revati** | Pis 16°40'–30°00' | Mercury | Pushan (nourisher, shepherd of souls) | Fish / drum | Deva | Sattva | Wholeness, safe passage, gentle guide, completion |

### 27.3 Gana / Yoni / Nadi cheat-sheet (for matching)

**Gana** — temperament:
- **Deva** (godly): Ashwini, Mrigashira, Punarvasu, Pushya, Hasta,
  Swati, Anuradha, Shravana, Revati.
- **Manushya** (human): Bharani, Rohini, Ardra, Purva & Uttara
  Phalguni, Purva & Uttara Ashadha, Purva & Uttara Bhadrapada.
- **Rakshasa** (demonic — intense, driven): Krittika, Ashlesha, Magha,
  Chitra, Vishakha, Jyeshtha, Mula, Dhanishta, Shatabhisha.

**Nadi** — dosha type (used for Nadi Kuta, most heavily weighted at 8
of 36 points in Ashtakoot matching):
- **Adi (Vata / air)**: Ashwini, Ardra, Punarvasu, Uttara Phalguni,
  Hasta, Jyeshtha, Mula, Shatabhisha, Purva Bhadrapada.
- **Madhya (Pitta / fire)**: Bharani, Mrigashira, Pushya, Purva
  Phalguni, Chitra, Anuradha, Purva Ashadha, Dhanishta, Uttara
  Bhadrapada.
- **Antya (Kapha / earth-water)**: Krittika, Rohini, Ashlesha, Magha,
  Swati, Vishakha, Uttara Ashadha, Shravana, Revati.

### 27.4 Nakshatra activity types (Muhurta selection)

Classical Muhurta Chintamani groups nakshatras by suitable activity:

- **Chara (movable)**: Punarvasu, Swati, Shravana, Dhanishta, Shatabhisha
  → travel, buying vehicles, moving.
- **Sthira (fixed)**: Rohini, Uttara Phalguni, Uttara Ashadha, Uttara
  Bhadrapada → building, gruha pravesh, coronations, planting.
- **Ugra (fierce)**: Bharani, Magha, Purva Phalguni, Purva Ashadha,
  Purva Bhadrapada → confrontation, destruction of enemies, difficult
  medical procedures. Avoid for weddings.
- **Mridu (soft)**: Mrigashira, Chitra, Anuradha, Revati → art, music,
  friendship, marriage, romance.
- **Kshipra (swift/light)**: Ashwini, Pushya, Hasta → learning,
  transactions, trade, medicine.
- **Mishra (mixed)**: Krittika, Vishakha → mixed activities, festivals.
- **Tikshna (sharp)**: Ardra, Ashlesha, Jyeshtha, Mula → tantra, occult,
  surgery, exorcism. Avoid for weddings.

### 27.5 How to phrase nakshatra readings

- Lead with the **archetype** (2-3 words: "the healer", "the seeker",
  "the ancestral throne") — that's what readers remember.
- Then explain the **classical symbol + deity** — this is what
  distinguishes serious sources from generic sun-sign content.
- Then move to practical: **career suits**, **relationship style**,
  **health tendencies**, **which nakshatras it matches well/poorly
  with**.
- Always ground in the **chart engine** where possible: if the reader
  has a saved chart, surface their Moon nakshatra explicitly ("Your
  Moon is in Ashwini — you're the initiator archetype in Vedic
  terms.").
- **Avoid deterministic language**: never "you will marry X" or "your
  career must be Y". Frame as tendencies: "Ashwini natives often
  gravitate toward…".

---

*Nakshatra reference last updated: 2026-07-20*

---

## 28. The eight parts of the day — Gulika, Maandi, and the Yamaganda question

**Added 2026-08-26 for issue #150.** This section exists so that any window the
app renders from the eight-part division of daylight can be checked in the
standard place rather than from a comment in `chart.py`.

**Source for everything in §28.1:** P.V.R. Narasimha Rao, *Vedic Astrology: An
Integrated Approach*, §4.3 "Other Upagrahas" (printed pp. 42–44). In this
repo: `data/vedic_astro_textbook.pdf`, **PDF page 55** for Table 10.
`pdftotext -layout` line numbers (the ones `grep -n` will find — see §28.6
before quoting any other line number): §4.3 heading **1687**, upagraha list
**1688–1691**, day/night boundary **1693–1695**, daytime rule and worked
example **1707–1712**, Table 10 DAY **1714–1723**, Table 10 NIGHT
**1724–1734**, night rule **1736–1741**, upagraha rising points **1754–1759**,
footnote 9 **1783**.

**Table 10 was verified against the rendered page image**
(`pdftoppm -f 55 -l 55 -r 200 -png`), not read from the text layer alone —
`scripts/corpus_search.py`'s own header warns that scanned tables lose rows
silently, and the `-layout` text of this table has collapsed columns.

### 28.1 What Rao states

**The day/night boundary and the division** (line 1693):

> "A day starts at the time of sunrise and ends at the time of sunset. A night
> starts at the time of sunset and ends at the time of next day's sunrise."

— and the length of whichever period the moment falls in is divided into
**8 equal parts**.

**The daytime rule** (lines 1707–1708):

> "The first part is ruled by the lord of weekday and then we cover planets in
> the order of weekdays. The part after the one ruled by Saturn is lord-less.
> After that, Sun's part comes."

So the daytime cycle is **eight** slots — `Sun, Moon, Mars, Mercury, Jupiter,
Venus, Saturn, (lord-less)` — entered at the weekday lord. Nighttime starts
instead at the **5th planet from** the weekday lord (line 1736); the night
table is not reproduced here because none of the panchang windows below use it.

**Table 10 — Rulers of the 8 parts of the DAY** (PDF p. 55, verified against
the page image):

| Weekday | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---|---|---|---|---|---|---|---|
| Sun | Sun | Moon | Mars | Merc | Jup | Ven | **Sat** | — |
| Mon | Moon | Mars | Merc | Jup | Ven | **Sat** | — | Sun |
| Tue | Mars | Merc | Jup | Ven | **Sat** | — | Sun | Moon |
| Wed | Merc | Jup | Ven | **Sat** | — | Sun | Moon | Mars |
| Thu | Jup | Ven | **Sat** | — | Sun | Moon | Mars | Merc |
| Fri | Ven | **Sat** | — | Sun | Moon | Mars | Merc | Jup |
| Sat | **Sat** | — | Sun | Moon | Mars | Merc | Jup | Ven |

("—" is Rao's lord-less slot.)

**Where the upagrahas rise** (lines 1754–1759):

> "(4) Yama Ghantaka rises at the middle of Jupiter's part. (5) Gulika rises at
> the middle of Saturn's part. (6) Maandi rises at the beginning of Saturn's
> part."

**Nature** (lines 1689–1691): Kaala is "a malefic upagraha similar to Sun",
Mrityu "a malefic upagraha similar to Mars", "Yamaghantaka is similar to
Jupiter. Gulika and Maandi are similar to Saturn." Rao elsewhere treats Gulika
as an afflicting point ("Situation of Gulika within 1º from lagna is also
undesirable").

**Rao records a dispute about the rising POINT** (footnote 9, line 1783):

> "Some scholars suggest that Kaala rises at the beginning of Sun's part. The
> same thing applies to others."

This matters in our favour: the disputed thing is *where inside the part* the
upagraha rises. **Which part it is** is not disputed, and a panchang window is
the whole part.

### 28.2 Gulika Kaal — CONFIRMED

Gulika = **Saturn's part** of the eight. Read off Table 10:

| Weekday | Gulika = Saturn's part |
|---|---|
| Sunday | 7th |
| Monday | 6th |
| Tuesday | 5th |
| Wednesday | 4th |
| Thursday | 3rd |
| Friday | 2nd |
| Saturday | 1st |

**These ordinals do not depend on whether Rao's lord-less slot exists.** Proof,
not observation: counting always starts at the weekday lord, which is one of
the seven planets; Saturn is the *last* planet before the lord-less slot; so
the count reaches Saturn before it can ever pass the blank. Formally, with the
weekday lord at cycle index `s ∈ {0..6}` and Saturn at index 6, the ordinal is
`1 + ((6 − s) mod 8) = 1 + ((6 − s) mod 7) = 7 − s` under both an 8-slot and a
7-planet cycle. Verified for all seven weekdays.

**The one inferential step, stated plainly.** Rao computes Gulika as a
*longitude* — the lagna rising at the midpoint of Saturn's part — and never
uses the phrase "Gulika Kaal". Identifying the panchang window with Saturn's
part is an inference. It is signed off here because (a) Rao assigns both Gulika
and Maandi to that same part, (b) his footnote 9 makes the *point* contested
while leaving the *part* untouched, so the part is the more robust object, and
(c) it is the same structural move already shipped for Rahu Kaal — a
weekday-indexed eighth of daylight.

**What is NOT sourced from Rao:** any specific prohibition ("do not sign", "do
not travel"). Rao supports only that Gulika is Saturn-natured and afflicting.
Copy must not attribute stronger guidance to him.

### 28.3 Yamaganda — BLOCKED, do not code it

`scripts/corpus_search.py "yamaganda" --absent` → **0 hits, 3 spellings**, over
the 16,724 `-layout` lines of the one book present. Rao names the *upagraha*
**Yamaghantaka**; "Yamaganda", the panchang window, does not appear.

Two independent blockers:

1. **The identification is unverified.** Yamaghantaka-the-upagraha is not
   stated by Rao (or by anything else we hold) to be Yamaganda-the-window.
2. **The ordinal is genuinely in dispute on exactly two weekdays.** Jupiter
   sits at cycle index 4, *before* the lord-less slot, so the blank does shift
   it — unlike Saturn:

   | Weekday | Jupiter's part, Rao's 8-slot | Jupiter's part, 7-planet cycle |
   |---|---|---|
   | Sun–Thu | 5, 4, 3, 2, 1 | 5, 4, 3, 2, 1 (agree) |
   | **Friday** | **8th** | **7th** |
   | **Saturday** | **7th** | **6th** |

   Five weekdays agree; Friday and Saturday differ by one full eighth of
   daylight (~96 minutes at Delhi). That is ~104 days a year rendering an
   adjacent, entirely plausible-looking time.

**What would unblock it.** A named book in `data/` that gives Yamaganda for
**Friday and Saturday**. A source silent on those two weekdays does not
unblock. The obvious candidate is **B.V. Raman, *Muhurtha or Electional
Astrology* (1948)** — the same glossary that already sources
`_RAHU_KAAL_SEGMENT` and states these windows as clock times against a 6 a.m.
sunrise. That file is **not present in `data/` as of 2026-08-26**.

**The discriminating test**, at an idealised 06:00 sunrise / 18:00 sunset
(1h30m parts):

- Friday's Yamaganda is either **16:30–18:00** (Rao, part 8) or **15:00–16:30**
  (7-planet, part 7).
- Saturday's is either **15:00–16:30** (Rao, part 7) or **13:30–15:00**
  (7-planet, part 6).

Anything else means a third scheme and the whole table reopens.

### 28.4 Brahma Muhurta — not in this corpus

- `corpus_search.py "brahma muhurta" --absent` → **0 hits, 6 spellings**.
- "muhurta" occurs 44 times in Rao, but **always meaning "an elected moment"**,
  never as a unit of time. Rao defines *hora* as 1/24 of sunrise-to-sunrise
  (line 816) and defines ghati/hora lagnas, but **nowhere defines a muhurta as
  a duration, and nowhere divides day or night into 15**.
- Rao explicitly hands this topic off (line 15907): "Out of the modern books on
  muhurta in English language, the one by Dr. B.V. Raman is very good."

**`[UNSOURCED — widely cited, not in corpus]`** — the standard definition, held
here as a *claim to be checked*, not as a sourced rule: a muhurta is 1/15 of
the night, and Brahma Muhurta is the **14th of the 15 nocturnal muhurtas** —
i.e. **one** muhurta wide, beginning two muhurtas before sunrise and **ending
one muhurta before sunrise**. Under the nominal 48-minute muhurta that is
sunrise −96 min to sunrise −48 min.

**Sourced fragments that do survive**, and can be reused when the rest is
settled:

- The night is **yesterday's sunset → today's sunrise** — Rao §4.3, line 1693,
  quoted above. This is the correct boundary and it is properly sourced.
- Dividing the *daylight* into 15 muhurtas is already sourced in this repo to
  Raman, *Muhurtha*, pp. 31–32 (see the Abhijit comment in `chart.py`). That
  establishes the **proportional** treatment of the unit; it does not establish
  any ordinal.

**Two errors to avoid when this is finally implemented:**

1. **"The two muhurtas before sunrise" is not Brahma Muhurta.** Brahma Muhurta
   ends one muhurta *before* sunrise; a window ending *at* sunrise is roughly
   twice too wide. Measured at New Delhi: 40.3 min vs 80.6 min (2026-06-21),
   47.6 vs 95.2 (2026-09-23), 54.9 vs 109.8 (2026-12-21).
2. **Fixed vs proportional is a real but smaller divergence.** New Delhi start
   times differ by 15.4 min (Jun solstice), 0.8 min (equinox) and 13.8 min
   (Dec solstice); Srinagar reaches 19.1 min. Whichever is chosen, the page
   must say which — this is a CONTESTED convention, and the defect would be
   silence, not the value.

### 28.5 What must NOT be inferred from Table 10

- **The lord-less slot is not Rahu Kaal.** Tempting, and wrong: it coincides
  with `_RAHU_KAAL_SEGMENT` on only 2 of 7 weekdays (Sunday and Wednesday).
  Rao's eight-part cycle contains no Rahu at all.
- **Rao uses two different definitions of "day".** §4.3 (this section):
  sunrise → sunset. §1.3.11 Hora (line 816): sunrise → *next* sunrise. Never
  cite "Rao's day" without the section.
- **Gulika never collides with Rahu Kaal** on any weekday, so the two can be
  shown side by side without a same-window clash.

### 28.6 Citation hygiene — `corpus_search.py` line numbers are not `grep -n` line numbers

`scripts/corpus_search.py` numbers lines with `str.splitlines()`, which splits
on form feeds as well as newlines. This book contains **515** form feeds
(page breaks), so the tool's line numbers run ahead of `grep -n` / `sed -n` by
roughly one per PDF page — +53 at the upagraha list, +55 sixty lines later,
and up to +515 at the end of the book. **A line number copied from
`corpus_search` output cannot be located again with `sed -n 'Np'`.** Every line
number in §28 was taken with `grep -n` on the cache file and is directly
reachable. Re-verify before quoting tool output as a citation.

---

*Section 28 last updated: 2026-08-26. Books present in `data/` when written:
`vedic_astro_textbook.pdf` only (1 of 7).*

---

## 29. The five angas of the Panchanga — tithi, vara, nakshatra, yoga, karana

**Added 2026-08-26 for issue #151.** `/panchang` renders all five angas to
users and the Muhurat Finder blocks on two of them, but nothing in this corpus
stated what they are or how they are computed. This section is where any
panchang claim gets checked. It follows §28's format deliberately.

**Books present in `data/` when this was written: 4 of 8** —
`vedic_astro_textbook.pdf`, `book1-for-CD.pdf`,
`Astrology-e-book-compressed.pdf`, and — **arriving part-way through this
extraction** — `matching/raman-muhurtha-1948-electional-astrology_djvu.txt`.
Johari, Goodwin and Kumar are not present. Every absence recorded in §29.10 is
an absence *against those four*, not against the tradition.

**Scope — read this before citing §29 as a discharge of #151.** §29 sources
the **five angas themselves**: what each is, how each is computed, the
enumerated lists, and the index conventions `chart.py` uses. Those are done,
and four of the five are now doubly sourced. §29 does **not** source the
**significance layer** the same pages render on top of them — most of
`_TITHI_SIGNIFICANCE`, seven of eleven `_KARANA_SIGNIFICANCE` notes, most of
`_NITYA_YOGA_SIGNIFICANCE`, `_DAGDHA_TITHI_BY_DAY`, Choghadiya,
`_PANCHAK_NAKSHATRAS`, `_SARVARTHA_SIDDHI_YOGA` and `_RAVI_YOGA_NAKSHATRAS`
remain unsourced or contested. §29.10 enumerates exactly what is still open.
**Do not read §29 as covering more than the angas.**

**Read §29.9 before using the Raman file for anything.** It is OCR of a 1948
scan and it is demonstrably lossy. It **is** properly registered — commit
`a391535` added it to `scripts/fetch_corpus.py` (line 92) and to `SOURCES.md`
(line 276) with hash verification, and `fetch_corpus.py` reports it
`[VERIFIED]`. §29.1–§29.8 were written against the three PDFs alone and do not
depend on it.

**The registry counts EIGHT books, not seven.** `fetch_corpus.py` lists
`Astrology For Beginners BVRaman_text.pdf` as an eighth entry, currently
`[MISSING]`. Today it reports **`corpus completeness: 4/8 usable`**. Any
"N of 7" phrasing elsewhere in this repo predates that entry.

### Sources for §29

**Source A — P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated
Approach*** (`data/vedic_astro_textbook.pdf`). Everything in §29.1–§29.5 and
§29.8 is from here.

| Rao's section | Printed pp. | PDF pp. | `-layout` lines |
|---|---|---|---|
| §1.3.6 Table 2, Nakshatras | 11 | 23 | 557–591 |
| §1.3.8 / §1.3.8.1 Tithis + **Table 3** | 12–14 | 24–26 | 603–696 |
| §1.3.8.2 Lunar Months + **Table 4** | 14–15 | 26–27 | 699–751 |
| §1.3.9 Yogas + **Table 5** | 15–17 | 27–29 | 753–805 |
| §1.3.10 Karanas | 17 | 29 | 807–813 |
| §1.3.11 Hora (weekday lords) | 17 | 29 | 815–832 |
| §1.3.12 **Panchaanga** | 18 | 30 | 836–844 |
| §1.3.13 Ayanamsa | 18 | 30 | 846–860 |
| §26.8 Sarvatobhadra Chakra (tithi groups) | 357–361 | 369–373 | 12235–12341 |
| §36.3 Basics of Muhurta + **Table 79** | 472–474 | 484–486 | 15944–16056 |

**Source B — P.V.R. Narasimha Rao, *Lessons on Vedic Astrology, Vol. I***
(`data/book1-for-CD.pdf`) — compiled lesson notes, two printed pages per PDF
page. Used only in §29.6 and §29.7.

| Lesson | Printed pp. | PDF p. | `-layout` lines | Topic |
|---|---|---|---|---|
| #5 | 17–22 | 17–19 | 644–830 | lunar calendar, paksha, amanta/suklanta, **the sunrise rule** |
| #6 | 25–26 | 21 | 980–992 | anga ↔ tatwa (partial, self-contradicting) |
| #13 | 61–62 | 39 | 2360–2364 | anga ↔ tatwa |
| #22 | 97–99 | 57–58 | 3559–3668 | panchanga definition, anga ↔ tatwa, nakshatra table |

**Source C — B.V. Raman, *Muhurtha or Electional Astrology*, 1st edn.,
Raman Publications, Bangalore, 1948** —
`data/matching/raman-muhurtha-1948-electional-astrology_djvu.txt`, the
archive.org `djvu.txt` OCR. **9,158 lines, 238,966 bytes, sha256
`dfd15e4c…8aa0b1c`** — record the hash with any citation, because this is a
loose text file rather than a PDF and nothing else pins which artefact you
read. Used only in §29.9, where its limits are set out.

| Raman's section | Printed pp. | Line numbers |
|---|---|---|
| Ch. II "General Hints" — the Panchanga and its five limbs | 11–15 | 651–815 |
| Ch. III — Panchaka (five-source energy) | 20–21 | 961–1040 |
| Ch. IV — Panchanga Suddhi, 1st of the 21 Mahadoshas | 29–30 | 1317–1367 |
| "Electing a Time for Marriage" | 101–102 | 3690–3766 |
| Glossary — "Thithies, Different kinds of" | — | 7403–7407 |
| Index | — | 7598, 9082 |

**Tables 3 and 5 were verified against the rendered page images**
(`pdftoppm -f 24 -l 24` and `-f 28 -l 28`, `-r 150 -png`), not read from the
text layer alone — `scripts/corpus_search.py`'s header warns that scanned
tables drop rows silently. Both render complete: Table 3 has all 16 rows
covering 30 tithis, Table 5 all 27 rows. The Lessons nakshatra table was
likewise checked at PDF p. 58.

**All line numbers here were taken with `grep -n` on `pdftotext -layout`
output and read back with `sed -n 'Np'`. See §28.6 — `corpus_search.py`
line numbers are NOT these numbers.**

### 29.0 What "panchanga" means

Rao, §1.3.12 (line 837):

> "Panchaanga means 'one with 5 limbs'. Almanacs published in India with
> planetary positions are traditionally called panchaangas. Along with the
> planetary positions, they give the start and end times of tithi, vaara
> (week day – Sunday, Monday etc), nakshatra, yoga and karana running on each
> day. These five are the limbs of panchaanga."

Restated in the muhurta chapter (line 15945): "Tithi, yoga, karana, weekday
and nakshatra form the 5 limbs of 'panchaanga'." And its purpose, line 843:

> "When we choose a muhurta (an auspicious time for starting a venture), we
> should choose an auspicious tithi, vaara, nakshatra, yoga and karana."

The *Lessons* give the same five (Lesson #22, lines 3642–3643) and add a gloss
worth keeping: "The five panchangas are divisions of time to show the quality
of time" (line 3562).

**Convention this repo follows: sidereal (nirayana), Chitrapaksha/Lahiri.**
Rao, §1.3.13 line 852: "We use the sidereal zodiac in Vedic astrology", and
line 860: "We will use Chitrapaksha/Lahiri ayanamsa in this book". *Lessons*
Lesson #5 line 821 names Chitrapaksha and Lahiri as the same ayanamsa and line
827 names Raman's as 1.5° different — so the choice is a real fork and naming
it is not decoration.

### 29.1 Tithi — CONFIRMED

**Definition** (Rao §1.3.8.1, line 606):

> "In lunar calendar, one day stands for one tithi. Tithi or lunar day is a
> period in which the difference between the longitudes of Moon and Sun
> changes by exactly 12°."

**The computation**, Rao's own four steps (lines 660–665), paraphrased in his
order: take `(Moon − Sun)`, add 360° if negative; divide by 12° and keep the
quotient; add 1; the result is 1..30 and indexes Table 3.

**Paksha** (lines 646–650): a lunar month is 30 tithis in two fortnights.
Sukla/Suddha paksha is waxing, Moon ahead of Sun by 0°–180°; Krishna/Bahula
paksha is waning, Moon ahead by 180°–360°. So tithis 1–15 are Shukla and
16–30 Krishna — exactly the split `/panchang` renders.

**Table 3 — Names of Tithis** (printed p. 12, PDF p. 24, lines 608–633;
verified against the page image). Rao gives a **lord per tithi**, which this
repo does not currently carry anywhere:

| Shukla | Krishna | Name (Rao's spellings) | Lord |
|---|---|---|---|
| 1st | 16th | Pratipat / Pratipada / Padyami | Sun |
| 2nd | 17th | Dwitiya / Vidiya | Moon |
| 3rd | 18th | Tritiya / Tadiya | Mars |
| 4th | 19th | Chaturthi / Chaviti / Chauth | Mercury |
| 5th | 20th | Panchami | Jupiter |
| 6th | 21st | Shashti | Venus |
| 7th | 22nd | Saptami | Saturn |
| 8th | 23rd | Ashtami | Rahu |
| 9th | 24th | Navami | Sun |
| 10th | 25th | Dasami | Moon |
| 11th | 26th | Ekadasi | Mars |
| 12th | 27th | Dwadasi | Mercury |
| 13th | 28th | Trayodasi | Jupiter |
| 14th | 29th | Chaturdasi | Venus |
| 15th | — | Paurnami / Paurnimasya / Poornima (Full Moon) | Saturn |
| — | 30th | Amavasya (New Moon) | Rahu |

**Naming convention** (lines 666–673): paksha first, then tithi name —
"Krishna Saptami" is the 22nd tithi, "Sukla Saptami" the 7th.

**Independently confirmed** by Raman, *Muhurtha*, Ch. II — but for the tithi
alone use Rao's 12°, because Raman's OCR gives 13°. See §29.9 before citing.

**Verified against the code.** Rao's Example 2 (lines 678–692): Moon 24°12'
Ge, Sun 17°46' Sc → elongation 216.43° → 19th tithi → "Krishna Chaturthi".
Running Rao's arithmetic through `chart.py`'s own `_TITHI_NAMES` reproduces
`Krishna Chaturthi`, index 19 of 30. `_tithi_at()` implements exactly Rao's
formula; its 30 names are Table 3's in Table 3's order.

### 29.2 Vara — the weekday

**Sourced:** the weekday lords, from Rao §1.3.11 (lines 822–825):

> "The first hora of any day … is ruled by the lord of the weekday (Sun for
> Sunday, Moon for Monday, Mars for Tuesday, Mercury for Wednesday, Jupiter
> for Thursday, Venus for Friday and Saturn for Saturday)."

That is the exact list `/panchang` prints under "Vara (weekday)". §28.1 uses
the same seven for the eight-part division, from a different Rao section.

**Also sourced:** vara is the **fiery/agni** limb — *Lessons* Lesson #13 line
2362 ("Vara (agni, physical)") and Lesson #6 line 980 ("Weekday - Agni tatwa
and represent physical vitality"), with Lesson #9 line 1621 adding "From
Panchanga, the physical entity is seen by the vara or the weekday."

**Per-weekday judgements ARE sourced — but only in Raman, and he contradicts
himself between chapters.** See §29.9. Rao gives the lord and nothing more.

**NOT sourced anywhere in the four books:** the day-lord *colour* the app
renders. Nobody gives a palette.

**Careful — Rao uses two different "days".** §1.3.11 (line 816): "Each day
starts at sunrise and ends at next day's sunrise." §4.3 (line 1693, see §28):
day = sunrise → sunset. Never cite "Rao's day" without the section.

### 29.3 Nakshatra — see §27, which this does not repeat

§27 already carries the 27 nakshatras with ranges, Vimshottari lords, deities,
symbols, gana, guna, nadi and activity type. **Do not duplicate it here.** Two
things §27 lacked that panchang work needs:

1. **The nakshatra is the 3rd anga** — Rao §1.3.12 line 839, quoted in §29.0.
   §27 never says so.
2. **Rao's Table 2** (printed p. 11, PDF p. 23, lines 557–587) independently
   confirms §27's **range** and **Vimshottari lord** columns for all 27 —
   checked row by row, zero mismatches. Reproduced identically in *Lessons*
   Lesson #22 (lines 3636–3668). That table is captioned "Source: Vedic
   Astrology: An Integrated Approach by PVR Narasimha Rao" — legible on the
   rendered page image (`pdftoppm -f 58 -l 58`) and present in **plain**
   `pdftotext` output at line 5486, but line-broken out of the `-layout`
   output, so `grep -n` on `-layout` will not find it.
3. **28 nakshatras when the chakra needs them** — Rao line 590: "For the
   purpose of some special charts like Kota Chakra and Sarvatobhadra Chakra,
   we consider 28 nakshatras. The last quarter of Uttarashadha is known as
   'Abhijit'. However, we consider 27 nakshatras for all other purposes."

**A warning about Rao's DEITY column — do NOT source §27 to it.** Rao's
Table 2 deities disagree with §27's for twelve consecutive nakshatras, and
the disagreement looks like a one-row offset — measured precisely below:

| Nakshatra | Rao Table 2 (line) | §27.2 |
|---|---|---|
| Magha | Sun (570) | Pitris |
| Purva Phalguni | Aryaman (571) | Bhaga |
| Uttara Phalguni | Sun (572) | Aryaman |
| Hasta | Viswakarma (573) | Savitar |
| Chitra | Vaayu (574) | Vishvakarma |
| Swati | Indra (575) | Vayu |
| Vishakha | Mitra (576) | Indra & Agni |
| Anuradha | Indra (577) | Mitra |
| Jyeshtha | Nirriti (578) | Indra |
| Mula | Varuna (579) | Nirriti |
| Purva Ashadha | Viswadeva (580) | Apas |
| Uttara Ashadha | Brahma (581) | Vishvedevas |
| Shravana | Vishnu (582) | Vishnu — **back in step** |

**What is measured**, at the resolution the table above supports. Twelve
consecutive rows disagree (Magha 10 → Uttara Ashadha 21), and across the middle
of that stretch Rao's entry for nakshatra *N* is §27's entry for *N + 1*:

- **Name-identical shift, 7 rows** — N = 11, 13, 14, 16, 17, 18, 20
  (Aryaman, Vishvakarma, Vayu, Mitra, Indra, Nirriti, Vishvedevas).
- **Same deity, different epithet, 3 rows** — N = 12 (Rao "Sun" vs §27
  "Savitar", which §27 itself glosses as "the Sun as inspirer"), N = 15
  (Indra vs "Indra & Agni"), N = 19 (Varuna vs "Apas", both the cosmic
  waters). Call these a shift only if you accept the equivalences.
- **The two ends do not shift** — N = 10 (Magha: Rao "Sun", §27 "Pitris";
  nothing shifts *in*) and N = 21 (Uttara Ashadha: Rao "Brahma", §27
  "Vishvedevas", while §27's Shravana is "Vishnu"). The lists are back in step
  from Shravana (22) onward.

So the offset is **strong in the middle and unexplained at both ends**, which
is worth stating precisely: a claim of "a clean one-row shift" would be an
overstatement of what the two tables actually show.

**What is NOT sourced, and was wrongly stated as fact in the first version of
this section:** that the offset is explained by the 28-nakshatra scheme
inserting Abhijit, "whose classical deity is Brahma". **Nothing in this corpus
gives Abhijit a deity.** `scripts/corpus_search.py abhijit` → 7 hits across all
four books (Lessons 242, 448, 5706; Raman 1161, 7478; Rao 590, 12246) and not
one of them names a presiding deity for it. `[UNSOURCED — a hypothesis, not a
finding]`: the Abhijit explanation is offered here only as the thing to test,
because Rao's line 590 does put Abhijit in the last quarter of Uttarashadha and
his Uttara Ashadha row does carry Brahma. That is a coincidence worth checking,
not evidence.

**Verdict: CONTESTED, unresolved — and it must stay unresolved from this
corpus,** which nowhere states the deities independently of Rao's Table 2.
Do not "fix" §27 to match Rao. **Blast radius, measured rather than guessed:**
`src/astro_ai/templates/learn/` holds **15** per-nakshatra articles
(`ls learn/ | grep -c nakshatra`), `learn_registry.py` names **16** slugs (the
extra, `vishakha-nakshatra`, is a pre-existing dangling `related` reference
with no template). **Six of the 15 fall inside the disputed stretch** — Magha,
Purva Phalguni, Uttara Phalguni, Hasta, Chitra, Swati — and **four of those
name the deity in the article TITLE**: Purva Phalguni/Bhaga, Uttara
Phalguni/Aryaman, Hasta/Savitar, Chitra/Vishvakarma. The other two title a
gloss rather than the name (Magha "Royal Throne of the Ancestors", Swati "The
Self-Going Wind"). **All six carry it in the summary AND in a dedicated FAQ
question** ("Who is Vayu, the deity of Swati?"). An earlier draft said "two of
those", which understated the blast radius of the very caution this paragraph
exists to give — measured against `learn_registry.py`, not estimated. Changing §27 on the strength of a table that self-evidently
drifts would be the #141 failure again. What would settle it: any text giving
the 28-nakshatra deity list in full. We hold none.

### 29.4 Yoga (the Nitya or Sun–Moon yoga) — CONFIRMED

**Not** the natal-chart yogas of §4. Rao calls these **"Sun-Moon Yogas"**.

**The computation** (Rao §1.3.9, lines 754–760):

> "Add the longitudes of Sun and Moon. Remove 360º from the sum if it is
> greater than 360º. Divide the sum by the length of one nakshatra (13°20' or
> 800'). Ignore fractions and take the integer part. Add 1 to it and the
> result is the index of the yoga running."

Note it is a **sum**, not a difference — which is why the yoga, unlike the
tithi, is *not* invariant under ayanamsa choice: the two shifts add instead of
cancelling. §29.0's Lahiri statement is therefore load-bearing here and only
here among the five angas.

**Table 5 — Sun-Moon Yogas** (printed p. 16, PDF p. 28, lines 762–790;
verified against the page image). Rao's spelling, then his gloss:

| # | Yoga | Rao's meaning | # | Yoga | Rao's meaning |
|---|---|---|---|---|---|
| 1 | Vishkambha | Door bolt/supporting pillar | 15 | Vajra | Diamond (strong) |
| 2 | Preeti | Love/affection | 16 | Siddhi | Accomplishment |
| 3 | Aayushmaan | Long-lived | 17 | **Vyatipaata** | **Great fall** |
| 4 | Saubhaagya | Long life of spouse (good fortune) | 18 | Variyan | Chief/best |
| 5 | Sobhana | Splendid, bright | 19 | Parigha | Obstacle/hindrance |
| 6 | Atiganda | Great danger | 20 | Shiva | Lord Shiva (purity) |
| 7 | Sukarman | One with good deeds | 21 | Siddha | Accomplished/ready |
| 8 | Dhriti | Firmness | 22 | Saadhya | Possible |
| 9 | Shoola | Shiva's weapon of destruction (pain) | 23 | Subha | Auspicious |
| 10 | Ganda | Danger | 24 | Sukla | White, bright |
| 11 | Vriddhi | Growth | 25 | Brahma | Creator (good knowledge and purity) |
| 12 | Dhruva | Fixed, constant | 26 | Indra | Ruler of gods |
| 13 | Vyaaghaata | Great blow | 27 | **Vaidhriti** | **A class of gods** |
| 14 | Harshana | Cheerful | | | |

**Independently confirmed** by Raman, *Muhurtha*, Ch. II, lines 713–734 — the
same 13°20' joint-motion definition and the same 27 names in the same order,
from a second author. §29.9.

**Verified against the code.** Rao's Example 3 (lines 793–801): Sun 23°50' Cp,
Moon 17°20' Li → sum 131°10' → 10th → "Ganda yoga". `chart.py`'s
`_NITYA_YOGA_NAMES` returns `Ganda` at that index. All 27 positions match Table 5
**in order**; **12 of the 27 differ in spelling** from Rao and **9 from Raman**
(e.g. `Priti`/Preeti, `Ayushman`/Aayushmaan, `Shula`/Shoola,
`Variyana`/Variyan, `Vaidhriti`/Vydhruti). **The two counts are not measured
the same way, and saying so matters.** The Rao figure of 12 IS an exact string
comparison. The Raman figure of 9 is NOT: raw, Raman differs on **17**, because
its OCR reads `Ayusliman`, `Sowbliagya`, `Soblmna`, `Sulrarma`, `Yriddlii`,
`Dkruva`, `Yyaghata`, `Harsliana`, `Sadbya`, `SuMa`, `India`. Repairing those
scanning artefacts before comparing gives 9 — defensible, since they are
damage rather than transliteration, but it is a normalised comparison and an
earlier draft described it as exact. Likewise **13** byte-identical in all
three holds only after the repair; raw it is **9**. The transliterations are cosmetic; **the ordinal
positions are what the code indexes and what is sourced.** `muhurat.py` keys its
blocker set on `Vyatipata` and `Vaidhriti`, which are positions 17 and 27 in
both. **The sequence and the indices are doubly sourced. The blocking is sourced
only by Raman, and he condemns five yogas rather than two — see §29.9.**

Also sourced, and useful: Rao's gloss for Vriddhi is "growth", and he uses it
approvingly of his own writing muhurta (line 16152).

### 29.5 Karana — CONFIRMED, structure and all

Rao §1.3.10, lines 808–813, in full — this one short passage settles the whole
structure:

> "Each tithi is divided into 2 karanas. There are 11 karanas: (1) Bava, (2)
> Balava, (3) Kaulava, (4) Taitula, (5) Garija, (6) Vanija, (7) Vishti, (8)
> Sakuna, (9) Chatushpada, (10) Naga, and, (11) Kimstughna. The first 7
> karanas repeat 8 times starting from the 2nd half of the first lunar day of
> a month. The last 4 karanas come just once in a month, starting from the 2nd
> half of the 29th lunar day and ending at the 1st half of the first lunar
> day."

Unpacked against a 0-based index over the 60 half-tithis of a lunar month:

| Index | Half-tithi | Karana | Rao's words |
|---|---|---|---|
| 0 | 1st half of tithi 1 | Kimstughna | "…ending at the 1st half of the first lunar day" |
| 1..56 | 2nd half of tithi 1 → 1st half of tithi 29 | Bava…Vishti ×8 | "repeat 8 times starting from the 2nd half of the first lunar day" (56 = 7 × 8) |
| 57 | 2nd half of tithi 29 | Sakuna | "starting from the 2nd half of the 29th lunar day" |
| 58, 59 | both halves of tithi 30 | Chatushpada, Naga | — |

**Independently confirmed** by Raman, *Muhurtha*, Ch. II, lines 744–763 —
same eleven names, same order, same "first seven … eight times … commencing
with the second half of the first lunar day" and same "last four … with the
second half of the 29th lunar day". Two authors, 60 years apart, identical.

`chart.py`'s `_karana_at()` produces exactly this: index 0 → Kimstughna,
1 → Bava, 57 → Shakuni, 58/59 → Chatushpada/Naga, with 1..56 cycling the seven
movable names. **The indexing that `scripts/verify_panchang_angas.py` guards
is Rao's, verbatim.**

**What Rao does NOT say about karanas:** he gives no per-karana character
except in passing — "Unfavorable sakuna karana was running at the time"
(line 16105). He never calls Vishti inauspicious, and he never equates Vishti
with Bhadra. Raman supplies part of what Rao omits, and disagrees with our
table on two of the three karanas he characterises — §29.9.

### 29.6 Which civil day a tithi belongs to — the sunrise rule

This is the rule `/panchang` and `festivals.py` both depend on, and it is
sourced. *Lessons* Lesson #5, lines 806–824:

> "Look at the sunrise to determine a Tithi. Do not confuse the civil calendar
> with lunar calendar. Its possible that a Tithi may span 2 civil days.
> Sunrise time will be the guiding factor."

and, on picking the festival day (line 824): "pick the civil day where, at the
time of sunrise, the Tithi has already occurred."

Three consequences the same passage states explicitly:

- **A tithi can exceed 24 hours and span more than two civil days** (line
  816). So "today's tithi" is a *choice of sampling instant*, not a fact.
- **The tithi's start instant is the same worldwide** — it is a geocentric
  Sun–Moon angle (lines 758–768: "If a particular Tithi started at a
  particular time in India, it will start at the exact time here also");
  geocentric coordinates are recommended (line 785). What differs by location
  is only *which sunrise* it is caught at (lines 746–756).
- Therefore the same tithi legitimately lands on **different civil dates in
  different countries** — the passage works this through for India vs USA.

`chart.py` samples all five angas at **local sunrise** (`compute_panchang`,
"Tithi at local sunrise — the classical convention for 'today's tithi'"), and
`DailyPanchang` documents tithi/paksha as location-independent. That comment is
right about the *value* being geocentric and wrong-sounding about the *day*:
the tithi VALUE is universal, but the tithi ATTRIBUTED TO A CALENDAR DAY is
not, because the sunrise that selects it is local. The Lessons passage is the
citation for both halves.

**Purnimanta vs amanta is a real, sourced fork** (Lesson #5, lines 695–721):

> "Within lunar calendar there are two types, AMANTA and SUKLANTA. … In
> AMANTA, new months starts just after AMAVASYA. … IN SUKLANTA, month ends
> with end of SUKLA PAKSHA, new month starts when SUN and MOON are exactly
> opposite each other."

with "Varahamihira and Jaimini spoke about Suklanta" (line 703), "AMANTA is
more important for mundane matters" (line 717) and the full-moon reckoning
"more important for spiritual matters" (lines 719–721). Rao's textbook Table 4
(printed p. 15, lines 722–739) names the twelve months by the rasi of the
Sun–Moon conjunction — i.e. **amanta**, without saying so. CLAUDE.md already
requires a page to state which reckoning it uses; this is the source that
makes that statable.

**Adhika maasa is sourced twice** — textbook lines 741–751 (two Sun–Moon
conjunctions in one rasi; "Nija" = real, "Adhika" = extra; "comes once in
every 3 years") and *Lessons* lines 772–796, which puts it at "2 times in 5
years". The two Rao texts give different frequencies; `adhik_maas.py` computes
it rather than tabulating it, which is the right answer to that disagreement.

### 29.7 What each anga is used for

- **All five, together:** electional astrology. Rao line 843: choose an
  auspicious tithi, vaara, nakshatra, yoga and karana. Table 79 (printed
  pp. 473–474, lines 15966–16051) gives per-task tithi / weekday / lagna /
  nakshatra lists for eight tasks (house construction, house entry, naming a
  child, first rice, teaching the alphabet, sacred thread, **wedding**, idol
  installation). Rao immediately qualifies it (line 16053): "These are merely
  guidelines and not final recommendations", and line 16064: "Planetary
  strength is more important than strictly following these thumbrules."
- **Tithi:** also the base of the **Annual Tithi Pravesha** chart (*Lessons*
  line 3564), and of the derived tithis Rao defines at lines 12332–12339 —
  *karma tithi* (elongation × 10) and *dhana tithi* (× 2) for career and
  wealth questions.
- **Vara:** the physical/agni limb, above (§29.2).
- **Nakshatra:** §27, plus muhurta use — "The nakshatra occupied by Moon at
  the time of a muhurta should be a good tara with respect to janma nakshatra"
  (line 15948).
- **Yoga and karana:** Rao names them in his muhurta checklist (line 15946)
  and reads them in worked examples: "Tithi is Saptami – an auspicious tithi.
  Yoga is Vriddhi yoga (growth). Karana is Vanija" (lines 16152–16153).
- **The elemental mapping**, agreed by three separate lesson notes (lines
  2360–2364, 3568–3576, and partially 980/987): tithi = water, vara = fire,
  nakshatra = air, yoga = ether/akasha, karana = earth. *(Lesson #6 line 989
  lists the same five against the same five tatwas but explicitly declines to
  pair them — "not in the same order, however" — so use the two lessons that
  do pair them.)*

### 29.8 Tithi groups — Nanda, Bhadra, Jaya, Rikta, Poorna

Rao §26.8, printed p. 358, lines 12250–12254:

| Group | Tithis |
|---|---|
| **Nanda** | 1, 6, 11, 16, 21, 26 |
| **Bhadra** | 2, 7, 12, 17, 22, 27 |
| **Jaya** | 3, 8, 13, 18, 23, 28 |
| **Rikta** | 4, 9, 14, 19, 24, 29 |
| **Poorna** | 5, 10, 15, 20, 30 |

Rao introduces these for Sarvatobhadra vedha, not for muhurta, and **gives no
qualitative gloss for any group.** But his own Table 79 is checkable against
them, and the result is clean enough to record:

> Union of the tithis Table 79 recommends across all eight tasks:
> {2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 15}.
> Nanda → 6, 11 recommended. Bhadra → 2, 7, 12. Jaya → 3, 8, 13.
> Poorna → 5, 10, 15. **Rikta → none.**

So **no Rikta tithi (4, 9, 14) is recommended for any of Rao's eight tasks**,
while every other group has members recommended. Taken alone that is a derived
observation about one table, not a stated rule. Rao adds one tithi judgement in
prose (line 16109): "Chaturdasi tithi (14th lunar day) is usually not
considered auspicious" — Chaturdasi is Rikta, consistent.

**Raman turns the derivation into a stated rule** (§29.9). Ch. II line 802:
"The 4th, 8th, 12th and 14th lunar days both in the bright and the dark half
are unsuitable for undertaking any auspicious work"; Panchanga Suddhi line
1329 adds the 6th, Purnima and Amavasya; the marriage chapter (line 3729)
rejects "Riktha Thithis" by name. **4, 9 and 14 are excluded by an explicit
rule in a second author, not merely absent from Rao's table.**

**This bears on `/panchang`.** `chart.py`'s `_TITHI_SIGNIFICANCE` renders
Chaturthi (tithi 4, Rikta) as "Ganesh day — remove obstacles, start small
things" — a favourable note for a tithi Rao's only muhurta table excludes from
all eight tasks and Raman names outright as unsuitable for auspicious work.
The Ganesh association is real and widely held, and a panchang character note
is not the same claim as a muhurta rule — but the page currently says
"start small things" on a day one source we hold says not to start things.
That is the sharpest tension §29 found between shipped copy and the corpus.
**Flagged, not corrected** — the resolution is probably to say both, not to
delete either.

### 29.9 B.V. Raman, *Muhurtha* (1948) — what it settles, and its limits

This file appeared in `data/matching/` **while §29 was being written** (it was
briefly absent and re-fetched mid-run, so the extraction below was taken from a
hash-pinned snapshot). It is an archive.org OCR of a 1948 scan. Three
consequences, and they bind:

1. **It is lossy in ways that change meaning.** Its tithi definition
   (lines 670–672) OCRs as "the difference of the increment of longitude of the
   Sun and the Moon amounts to **13°**". That is wrong, and it is the OCR
   rather than Raman: his karana definition seventy lines later (lines
   743–744) reads "the distance which should be the multiple of **G°** between
   the Sun and Moon" — `G` is itself an OCR of `6` — and a karana is half a
   tithi, so 6 × 2 = 12, which is Rao's figure. **Do not cite Raman for the
   12°; cite Rao (§29.1).** The same page gives "(0) Vanija" for "(6) Vanija"
   (line 746), and elsewhere the scan yields "India" for "Indra" (733),
   "Biktha" for "Riktha" (3729), "Amita" for "Amrita" (1766) and "the 16th
   (Atiganda)" (1344) where his own list numbers Atiganda 6th (line 726).
   **Every digit in this file is suspect.**
2. **No page images exist for it** — there is no PDF, so the §28 / §29
   discipline of confirming a table against `pdftoppm` output *cannot be
   applied*. Treat every list in it as provisional.
3. **It is registered, and this section originally said otherwise.** The first
   version of §29 claimed `fetch_corpus.py` and `SOURCES.md` did not know the
   file. That was measured before `a391535` landed and was **false by the time
   §29 was committed**:
   `git show 4c4394a:scripts/fetch_corpus.py | grep -n raman-muhurtha` → line
   92, and the same grep on `SOURCES.md` → line 276. Recorded here rather than
   quietly deleted, because "I measured it earlier" is exactly the drift this
   file warns about elsewhere.

With those caveats, it independently confirms and materially extends §29.

**Confirms, from a second author, 60 years earlier:**

- **The five limbs** (line 656): "The Panchanga consists of five limbs or
  accessories, viz., Thithi (lunar day), Vara (week day), Nakshatra
  (constellation), Yoga (a luni-solar day) and Karana (half a lunar day)" —
  with a ranking Rao does not give (line 661): "by far the most important ones
  are the lunar day, constellation and week day."
- **The yoga definition and all 27 names in our order** (lines 713–734): "the
  period during which the joint motion in longitude of the Sun and the Moon
  amounts to 13° 20'", then Vishkambha … Vyatipata (17) … Vydhruti (27).
  Position-for-position identical to Rao's Table 5 and to
  `chart.py:_NITYA_YOGA_NAMES`.
- **All 11 karanas in our order, and the whole fixed/movable structure**
  (lines 744–763): "The first seven come by rotation eight times in a lunar
  month, commencing with the second half of the first lunar day … The last four
  are said to be permanent karanas and occur in order with the second half of
  the 29th lunar day." Word for word the same rule as Rao §1.3.10.
- **The five tithi groups** (glossary, lines 7403–7407): Nanda 1/6/11,
  Bhadra 2/7/12, Jaya 3/8/13, Riktha 4/9/14, Poorna 5/10/15 — identical to
  Rao §26.8 (§29.8). Used in the body too, e.g. line 1747 "Bhadra (2nd, 7th
  and 12th lunar days)".

**Extends — these were UNSOURCED before this file arrived:**

- **The condemned yogas are real, and there are FIVE of them, not two.**
  Panchanga Suddhi, lines 1343–1346:

  > "Coming to the Yoga (vide page 12) the 16th (Atiganda) the 9th (Sula) 10th
  > (Ganda) 17th (Vyathipatha) and 27th (Vaidhruti) have deleterious effects
  > upon events which are started or commenced under them."

  ("16th" is an OCR slip for 6th — Atiganda is 6th in his own list at line 726
  and in Rao's Table 5.) For **marriage specifically** he rejects ten (lines
  3757–3759): "Vyatipata, Dhruva, Mrityu, Ganda, Vajra, Sula, Vishkambha,
  Atiganda, Vyaghata, and Parigha" — note "Mrityu" is **not** one of the 27,
  so that list needs its own check before use.

  So `muhurat.py:397 _BLOCKING_NITYA_YOGAS = {"Vyatipata", "Vaidhriti"}` is now
  **sourced but narrower than its source**, and `panchang.html`'s "Vaidhriti
  and Vyatipata are the two most inauspicious yogas" is **not what Raman
  says** — he names five as deleterious and singles out none as "the two
  most". Reported, not changed.
- **Bhadra is a karana, and it is the one to reject.** Line 1351: "Bhadra is
  unfit for any good work but is eminently suitable for violent and cruel
  deeds." Line 3761: "Vishtikarana must invariably be discarded." Raman's own
  **index** carries "Bhadra Karana 29, 39" (line 7598) and "Visti 13" (line
  9082) — p. 29 is the Panchanga Suddhi page, p. 13 the karana list. His
  karana list has no entry named Bhadra, and Visti is the only karana he
  condemns. **The identification Vishti = Bhadra is therefore strongly implied
  and still not stated in one sentence anywhere we hold.** That is a real
  improvement on "unsourced", and it is not the same thing as sourced.
- **Per-karana character** (lines 1349–1354): "Bava is auspicious for starting
  works of permanent importance while Thaithula is propitious for marriage …
  For getting mantras Sakini Karana is propitious." Against
  `chart.py:_KARANA_SIGNIFICANCE`: **Bava matches** ("favourable for stable,
  long-lasting undertakings"); **Taitila does not** — the code says "favourable
  for trade and negotiation" where Raman says marriage; Shakuni is "remedial
  and medicinal work" where Raman says mantras. The other eight have no
  counterpart here.
- **Tithis to avoid**, stated twice and not identically. Ch. II line 802: "The
  4th, 8th, 12th and 14th lunar days both in the bright and the dark half are
  unsuitable for undertaking any auspicious work." Panchanga Suddhi line 1329:
  "the 4th, 6th, 8th, 12th and 14th, full and new moon days should be
  avoided." The second adds the 6th, Purnima and Amavasya. For marriage (lines
  3728–3732) he rejects the 11th of the dark half through New Moon, the Riktha
  tithis, the 8th, 12th and 6th, and calls the 2nd, 3rd, 5th, 7th, 10th, 11th
  and 13th of the bright half best — which is close to Rao's Table 79 list
  (§29.8) and confirms the Rikta observation there from a stated rule rather
  than a derived one.
- **Weekday judgements.** Line 790: "Tuesday and Saturday should be invariably
  avoided for all good and auspicious work." Line 1331: "Thursday and Friday
  are held to be suitable for all work. Tuesday is to be generally avoided
  except when it happens to be the 10th, 12th or 16th day of the child's
  birth." For marriage (lines 3734–3746): Monday, Wednesday, Thursday, Friday
  best; Sunday and Saturday middling; Tuesday invariably rejected. Note Ch. II
  and the marriage chapter disagree about Saturday. This is the first sourced
  per-weekday guidance in the corpus, and it is **CONTESTED within one book** —
  which is exactly why the app should say which rule it applies.

**Does NOT settle:**

- **`dagdha` — still 0 hits, now across four books.** No "burnt" either. The
  seven-row `_DAGDHA_TITHI_BY_DAY` remains unsourced. (`burnt` returns 1 hit,
  Rao line 9991, about cremation — unrelated.) Its comment credits
  "Muhurtha Chintamani", which is not a book we hold.
- **`choghadiya` — still 0 across four books.**
- **`_PANCHAK_NAKSHATRAS` — a false positive waiting to happen, and the exact
  measurement matters.** Two commands, two opposite-looking answers:

  ```
  $ scripts/corpus_search.py panchak --absent
  NO SPELLING MATCHED — 0 hits for any of 2 spellings across 38,197 lines.
  $ scripts/corpus_search.py panchaka
  raman-muhurtha-…_djvu.txt — 31 hit(s)      (all 31 in Raman; 0 elsewhere)
  ```

  The spelling `muhurat.py` uses (`panchak`) is **genuinely absent**; the
  spelling Raman uses (`panchaka`) is everywhere in his Ch. III — and it is
  **a different concept**. Lines 961–991 define Panchaka as a *number*: add
  the lunar-day, weekday, constellation and lagna indices, divide by 9, read
  the remainder (1 mrityu, 2 agni, 4 raja, 6 chora, 8 roga). It has nothing to
  do with `muhurat.py`'s five nakshatras Dhanishta→Revati. **So the rule stays
  UNSOURCED, and a hit count is not what makes it sourced or not** — 0 under
  one spelling and 31 under another, with the 31 irrelevant.
- **`kharmas` and `chaturmas`** — re-measured across all four books,
  **0 hits** (3 and 5 spellings, 38,197 `-layout` lines).

**Amrit Siddhi and Sarvartha Siddhi — the terms are absent, the CONCEPT is
present, and that changes the verdict.** `corpus_search.py "amrit siddhi"
--absent` and `"sarvartha siddhi" --absent` both return 0 across four books.
But Raman's **Ch. VI, "On Certain Special Yogas"** (lines 1688–1773) is exactly
this material under the name **Siddha Yoga** (line 1692): "When a certain week
day coincides with a certain asterism and a certain thithi, it becomes
specially auspicious for good work."

- **Amrit Siddhi.** Line 1763: "Sunday to Saturday respectively coinciding with
  the constellations Hasta, Sravana, Aswini, Anuradha, Pushya, Revati and
  Rohini will give rise to Amita Siddha Yoga." ("Amita" is OCR for *Amrita*.)
  Against `muhurat.py:323 _AMRIT_SIDDHI_YOGA`, **six of seven weekdays match
  exactly**; **Monday does not** — the code has **Mrigashira**, Raman has
  **Shravana**.

  **Verdict: CONTESTED, not wrong** — and the grounds are sourced, not
  appealed to.

  (a) **Rao says to expect exactly this.** §36.1, printed p. 471, line 15905:
  "The topic of muhurta has a lot of controversies. Different guidelines are
  given in different classics and different conventions are in vogue in
  different regions of India." The code credits *Muhurta Chintamani*; Raman is
  a different classic. Raman himself demonstrates the regional half on the very
  page we are reading from — the marriage chapter, printed p. 101, lines
  3707–3712, contrasts what "a Tamilian would not mind" with the "strong
  objection … taken by people living in Andhra and Karnataka."

  (b) **There is no page image for this file**, so a single-word disagreement
  in a 1948 OCR cannot be confirmed — though *Shravana* and *Mrigasira* are
  not plausibly confusable, which is what makes this worth chasing rather than
  dismissing.

  **`[UNSOURCED — could not establish]`:** the tidiest explanation would be
  that Raman (title page, lines 10 and 24: "Bangalore Venkata Raman" and an
  imprint city of "Bangalore") records a southern recension while *Muhurta Chintamani* carries a northern one — the
  same split `matching.md` already declares for Ashtakoota. **We cannot source
  the second half of that**: *Muhurta Chintamani* is not in `data/` in any
  form, so nothing here establishes its provenance. Do not write it as fact.

  **What settles it:** the printed p. 40 of Raman, or *Muhurta Chintamani*
  itself. Until then the honest statement is that our Monday entry has one
  source against it and no source for it.

- **Sarvartha Siddhi.** Raman's per-weekday Siddha Yoga lists (lines
  1699–1743) are a near-neighbour of `muhurat.py:340
  _SARVARTHA_SIDDHI_YOGA` but are **not the same table**. Measured overlap
  (code ∩ Raman / code size): Sunday 6/7, Thursday 4/5, Monday 3/5,
  Wednesday 3/5, Tuesday 2/4, Friday 2/5, Saturday 2/3. Sunday is
  near-identical — code has Ashwini where Raman has Shravana, the other six
  agree — and the rest diverge widely.

  **Two things follow, and the second matters more.** The code's table is
  **not sourced by Raman** and stays UNSOURCED. And Raman's rule carries a
  **tithi condition** on several weekdays (Sunday "coinciding with the 1st,
  4th, 6th, 7th, or 12th lunar day"; Wednesday "coinciding with Bhadra and
  Jaya"; Saturday "with lunar days Bhadra and Riktha") which
  `_sarvartha_siddhi_flag()` does not implement at all — it keys on
  `weekday|nakshatra` only. If our table ever *is* traced to a text that
  states it Raman's way, the missing tithi leg is a defect, not a
  simplification.

### 29.10 Still NOT in this corpus — measured across 4 of 8 registry entries

Re-measured after the Raman file arrived, with
`scripts/corpus_search.py <term> --absent` over **38,197 `-layout` lines,
4 books**. Every one returned **0 hits across every spelling variant the tool
generates**:

| Term | Spellings | What depends on it | Verdict |
|---|---|---|---|
| `dagdha` | 3 | `muhurat.py:800 _DAGDHA_TITHI_BY_DAY` — all 7 rows | UNSOURCED |
| `choghadiya` | 4 | `/panchang` Choghadiya block, Muhurat Finder Phase B | UNSOURCED |
| `kharmas` | 3 | Muhurat Finder blocker | UNSOURCED |
| `chaturmas` | 5 | Muhurat Finder blocker | UNSOURCED |
| `amrit siddhi` | 5 | `muhurat.py:323` | **term absent, concept present — §29.9** |
| `sarvartha siddhi` | 7 | `muhurat.py:340` | **term absent, concept present — §29.9** |

**`panchak` is still 0** — it is in the table above precisely because it stays
absent under the spelling the code uses. The *concept-shaped* hit is under
`panchaka` (31, all Raman) and is a different rule entirely — §29.9. One term
that was 0 against three books genuinely is **no longer absent**:
`bhadra karana`, 1 hit, Raman's index line 7598.

**A zero proves the TERM is absent, not the CONCEPT, and a non-zero proves
neither.** Both failure directions are now demonstrated inside this one
section: Siddha Yoga (concept present under another name, terms score 0) and
Panchaka (a near-name scoring 31 for an unrelated rule). The `SOURCES.md`
warning should carry the second example as well as the first.

What the four books *do* hold on this ground is Rao's Table 79 (§29.7),
the tithi groups (§29.8) and Raman's Panchanga Suddhi (§29.9).

**Still with no counterpart in any of the four:**

1. **Most of `_TITHI_SIGNIFICANCE`.** Raman gives which tithis to *avoid*
   (§29.9); nobody here gives the per-tithi *characters* the page prints —
   "Ganesh day", "Nag/Saraswati themes", "Sun-themed", "Durga/Shakti themes",
   "Devi themes", "Vijayadashami undertones". Ekadashi-as-fasting and
   Amavasya-as-ancestral-rites are widely held but are not in these books.
   The one that is arguably *contradicted* rather than merely unsourced is
   Chaturthi — §29.8.
2. **Seven of the eleven `_KARANA_SIGNIFICANCE` notes.** Raman covers four —
   Bava (matches), Taitila (differs), Shakuni (differs) and Vishti (§29.9).
   The remaining seven are Balava,
   Kaulava, Gara, Vanij, Chatushpada, Naga and Kimstughna, which have no
   source in any of the four.
3. **Most of `_NITYA_YOGA_SIGNIFICANCE`.** Rao's Table 5 supplies one-word
   glosses for all 27 (§29.4) and Raman condemns five (§29.9); neither
   supports "favourable for accomplishment and completion" for Siddhi or
   "joy, celebration, favourable news" for Harshana as *guidance*. Note the
   dict also carries a key **"Amrita"**, which is not one of the 27 yoga names
   in either source — it is dead, and if it was meant to be Amrita Siddhi
   Yoga (§29.9) it is in the wrong table.
4. **`_RAVI_YOGA_NAKSHATRAS`** — its own comment calls it a "simplified rule",
   and nothing in these four books states it.

**What would close the rest:** *Muhurta Chintamani*, which three separate code
comments cite and which is **not in `data/`** in any form as of 2026-08-26; and
a clean scan of Raman with page images, since the copy we now hold is OCR only.

### 29.11 What must NOT be inferred

- **"Bhadra" means two unrelated things in Rao.** It is tithi group 2 (2, 7,
  12, 17, 22, 27 — §29.8, line 12251) and it is the word he glosses at line
  12236 as "auspicious or well". It is **not** used by him for Vishti karana.
  A future extractor who greps `bhadra` and finds line 12236 will read
  "auspicious" and reach the exact opposite of what `muhurat.py` means.
- **"Vyatipata" means two unrelated things in Rao** — nitya yoga 17 (line 780)
  *and* an upagraha computed as `360° − Dhuma` (§4.2, lines 1641, 1649). Both
  are in Table 5's book, and only one is what `muhurat.py` blocks on.

  **A live `corpus_search.py` spelling gap sits on top of that**, and the exact
  shape of it matters:

  ```
  $ scripts/corpus_search.py vyatipata     -> 7 hits: Rao 1650/1678/1679/1680
                                              (ALL the upagraha, §4.2)
                                              Raman 731/3758/9085
  $ scripts/corpus_search.py vyatipaata    -> Rao 780 (Table 5) appears
  ```

  `vyatipata` **never surfaces Rao's Table 5**, because Rao spells it
  *Vyatipaata* and that is not among the six variants the tool expands. The
  search is only rescued by Raman line 731 — his 27-yoga list — which is a
  book we did not hold until this session. **Before the Raman file arrived,
  that one command returned the upagraha and nothing else.** Search both
  spellings; the gap is worth its own issue.
- **"Yoga" in §29.4 is not "yoga" in §4.** Sun+Moon Nitya yogas vs natal
  combinations. `chart.py` already carries this warning; it belongs in the
  corpus too.
- **Rao's Table 79 tithi lists are per-task, not a general auspicious-tithi
  ranking**, and Rao himself downgrades them twice (lines 16053, 16064). Do
  not turn §29.8's Rikta observation into a shipped blocker without a source
  that states it as a rule.
- **Do not source §27's nakshatra deities to Rao's Table 2** — §29.3.
- **"Panchaka" in Raman is not our Panchak.** 31 hits under the spelling
  `panchaka` (0 under `panchak`), a different rule entirely — §29.9. A grep
  that finds the word is not a source.
- **"Bhadra" now means THREE things across the corpus.** Tithi group 2
  (Rao line 12251, Raman line 7404); Rao's gloss "auspicious or well"
  (line 12236); and Raman's condemned karana (line 1351, index line 7598).
  Raman uses the first and the third **within four lines of each other** at
  1742–1747 and 1351. Never resolve `bhadra` from a grep hit alone.
- **Raman's "Siddha Yoga" is not `chart.py`'s yoga #21 "Siddha".** Different
  object: #21 is a nitya yoga, Siddha Yoga is a weekday+nakshatra+tithi
  coincidence (§29.9). Three unrelated things now share the stem in this
  corpus, alongside Siddhi (#16).
- **The tithi is ayanamsa-invariant; the yoga is not.** `(Moon − Sun)` cancels
  the ayanamsa, `(Moon + Sun)` doubles it. A tropical slip is invisible in
  tithi and karana and moves the yoga about two places all year.

### 29.12 Verification already in place

`scripts/verify_panchang_angas.py` checks the computed tithi, yoga and karana
against transcribed **drikpanchang.com** New Delhi day pages, plus structural
and coverage gates. §29 is the *other* half of that: the gate proves the
computation reproduces a published almanac; this section proves the tables and
the index conventions are Rao's — and, since §29.9, Raman's too. Neither
substitutes for the other.

**Nothing in §29 has changed any behaviour.** Where the extraction and the code
disagree — Amrit Siddhi's Monday, Taitila's and Shakuni's characters, the count
of blocking yogas, `panchang.html`'s "the two most inauspicious", the dead
`"Amrita"` key, Sarvartha Siddhi's missing tithi leg — the finding is recorded
here and filed, not applied. A rule change needs the fix loop, a verification
gate and QA.

---

*Section 29 last updated: 2026-08-26. Books present in `data/` when written:
`vedic_astro_textbook.pdf`, `book1-for-CD.pdf`,
`Astrology-e-book-compressed.pdf`, and
`matching/raman-muhurtha-1948-electional-astrology_djvu.txt`, which appeared
mid-extraction and is OCR-only. `fetch_corpus.py` reports
`corpus completeness: 4/8 usable`, all four `[VERIFIED]`; the eighth registry
entry is `Astrology For Beginners BVRaman_text.pdf`, `[MISSING]`.
Vasudev's e-book contains no
panchang-anga material at all: over its 4,558 `-layout` lines, `tithi`,
`vaara` and `lunar day` return zero and `corpus_search.py karana` scores it
**0**; the 9 raw substring matches for `karana` are all inside *Antahkarana*
or *Vyakarana* (lines 334, 523, 558, 1191, 1243, 1244, 2725, 3670, 3774) and
none is the anga. The only `panchang` hits are
line 1399 ("preparing Panchangas") and line 2914 (a stotra name). It
contributes nothing to §29 and should not be re-searched for it.*
