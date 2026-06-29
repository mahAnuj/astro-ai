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

- **Match with another Manglik** — the most commonly cited classical remedy; it neutralizes the dosha mutually (see rule 20).
- **Recitation of Hanuman Chalisa / Mangal stotra** — Mars's adhidevata. Traditional, low-risk, devotional.
- **Donation on Tuesday** — red lentils (masoor dal), red cloth, sweets. Classical Tuesday remedy for afflicted Mars.
- **Coral (moonga) gemstone** — ONLY after a competent astrologer reviews the whole chart. Wearing coral without analysis can amplify Mars if Mars is not actually benefic for the chart. Default LLM stance: suggest consultation, do not prescribe.

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

> Source: P.V.R. Narasimha Rao, Ch. 13 ("Interpreting Charts").
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
