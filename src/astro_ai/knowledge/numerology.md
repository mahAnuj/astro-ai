# Numerology — Vedic + Chaldean integrated system

**Primary sources for this file:**
- **Johari** = Harish Johari, *Numerology — With Tantra, Ayurveda, and Astrology* (Destiny Books / Inner Traditions, 1990). Cited on Vedic 3-number system, per-planet-number traits, Vedic Square, Ayurvedic/Tantric correspondences.
- **Kumar** = Jayant Kumar, *Numerology & You — A Step By Step Approach* (Educreation Publishing, ISBN 978-1-61813-620-6, 2016). Cited on Western Chaldean 7-Core-Number taxonomy, Karmic Debt, Challenge/Pinnacle/Personal Year/Essence Cycle. **Sample copy only — pages 1-11 available; per-number chapters 3-24 not extractable.**
- **Cheiro** = Cheiro (William John Warner, "Count Louis Hamon", 1866–1936), *Cheiro's Book of Numbers* (Herbert Jenkins, London; seventh impression). 194 PDF pages, 33 chapters. **This is the origin of the Chaldean letter table that circulates in Indian numerology practice**, and the source of the compound-number series 10–52 the site already renders. Cited on name numerology, the single-vs-compound distinction, the zodiac number-periods, per-number lucky days/colours/stones, and the 4-and-8 doctrine. See **§14**.

Where the authors differ, the divergence is called out inline. Where they agree, cited as "Johari + Kumar". Johari-only claims cited "Johari". Kumar-only claims cited "Kumar". Cheiro-only claims cited "Cheiro".

This file is compiled for internal use by `numerology.py` and by content authors. It is dense and rule-based — narrative belongs in the article template, not here.

## §1 System overview

Vedic-integrated numerology assigns each of the nine single-digit numbers to a graha (Sun, Moon, Jupiter, Rahu, Mercury, Venus, Ketu, Saturn, Mars) rather than to the Western Uranus/Neptune. Each person is described by **three numbers** — Psychic, Destiny, and Name — and the character traits of each number derive from its ruling planet's Vedic significations (Jyotisha), its Ayurvedic dosha (Vata/Pitta/Kapha), and its Tantric deity/mantra/yantra. Odd numbers (1, 3, 5, 7, 9) are dynamic; even numbers (2, 4, 6, 8) are static. Number 6 is the "universal friend" (common to both odd and even groupings).

## §2 The three primary numbers

### 2.1 Psychic Number (Mulank)

**Calculation:** reduce the *day of birth* to a single digit. Born on the 12th → 1+2 = 3. Range: 1–9.
**Meaning:** how the native sees the self; drives food, sex, friendship, marriage, ambitions, desires. Corresponds astrologically to the Moon sign (Chandra Rashi) in the Hindu system.
**Active period:** from birth throughout life; **most dominant up to age 35–40**, after which Destiny Number takes over. Never entirely loses influence.
**Modifiable by:** name change, education, initiation, marriage.
**Boundary caveat per Johari (footnote 2):** in Hindu tradition, the date changes ~1–2 hours before sunrise. A person born at 2 AM the "night of the 12th" per modern midnight convention is astrologically still a 3, not a 4. Numerologist should compare tendencies with both to disambiguate.
**Pinpoint:** Johari, ch. 2, section "Psychic Number" — "The psychic number is obtained by making a simple whole number of the date of birth", followed by the author's own example (born on the 12th, 1+2 = 3). Plain `pdftotext` lines 273–275. Verified against the PDF 2026-08-08.

**Implemented as of #164:** `_birthday_number()` reduces the day of month **fully to 1–9** — `preserve_masters=False`. Masters are not kept here because this section fixes the range at 1–9 and §4 files every day of the month under a single-digit number. Days 11, 22 and 29 therefore return **2, 4 and 2**, which is exactly what §4's birthday lists say (11 and 29 under Number 2; 22 under Number 4) and what §5's compound table says (11 → 2, 22 → 4). The compound-number flavour of an 11th or 22nd birth is not lost — it lives in §5 as a separate layer on top of the reduced psychic number, which is where Johari puts it.

### 2.2 Destiny Number (Bhagyank)

**Calculation:** sum all digits of DOB (day + month + year, all digits added). Born May 12, 1934 → 5+1+2+1+9+3+4 = 25 → 2+5 = 7. The intermediate `25` also has effect — both digits (2 and 5) contribute secondary traits, but the reduced 7 is dominant.
**Pinpoint:** Johari, ch. 2, section "Destiny Number" — "The single whole number obtained from the addition of the date, month, and year of birth is called the destiny number", with this exact worked example (the author's own birthdate). Plain `pdftotext` lines 299–300, worked example line 302. Verified against the PDF 2026-08-08. Note this is *not* the reduce-month/day/year-separately method used in modern Western practice.

**Meaning:** what the world thinks of you; karma-driven; reflects samskaras from past lives. **Cannot be changed** — no external intervention modifies destiny.
**Active period:** peak from age 35–40 onward.

**Implemented as of #162:** `_life_path()` sums **every digit of the DOB** per this section, and keeps 11/22/33 **on the final total only** — `preserve_masters=True`. So 1990-01-11 sums to 22 and stays 22.

The method this replaced — reduce year, month and day separately, then sum those — was not a bug of ignorance. It is mainstream *Western* practice, taught explicitly: Goodwin, *Numerology: The Complete Guide, Vol. 1*, ch.3 "The Life Path", section "Calculation" (plain `pdftotext` lines 1861–1865) instructs the reader to "determine each separately"; the warning at lines 1989–1991 says that adding all at once means "you may end up with a master number that doesn't apply or lose a master number that should apply"; and the worked counter-example for March 12 1940 is annotated **"Incorrect. The master number has been lost."** (lines 2026–2028). Read straight, Goodwin calls the method this site now uses wrong.

That tension is recorded rather than smoothed over. This is a Vedic site, so it follows the Vedic source (Johari) over the Western one where they conflict. **Goodwin is cited here only as evidence that the previous behaviour was legitimate practice in its own school — never as authority for a Vedic reading.**

**Scope of the divergence:** the two methods can differ *only* by master-vs-base, never by which base number you land on. A digit sum is congruent to its value mod 9, and 11/22/33 ≡ 2/4/6, so both totals always agree mod 9. Measured across all 47,847 dates from 1900-01-01 to 2030-12-31: zero mismatches of the reduced base. What does change is the displayed number: over 1940–2012, 3,598 of 26,664 dates (**~13.5%**) differ, in both directions — 2,715 gain a master they did not previously show, 883 lose one. Everything keyed off the base number — per-number profiles (§4), compatibility (§7), remedies (§11) — is unaffected.

### 2.3 Name Number (Namank)

**Calculation:** sum Chaldean values (see §3.2) of every letter in the **popular name** (the one you're most known by in worldly dealings — usually the full public name on bank/passport/professional bylines).
**Sub-numbers to track alongside:**
- First-name number (used by intimates)
- Family-name number (used in that circle)
- Full popular-name number (official documents, business)

**Meaning:** creates a vibrational identity throughout life; strongly affects social relationships and marriage. Continues to influence even after death (writers, poets, architects, politicians benefit particularly). **The first letter of the full name is more potent than any other letter.**
**Modifiable by:** legal or common-use name change. A name change can bring the Name Number into harmony with the Psychic or Destiny number. When harmonized:
- Name ↔ Psychic → good friendships + social life
- Name ↔ Destiny → remembered after death

**Cheiro treats the Name Number at far greater length than Johari does — see §14.2.** He agrees the name to use is the most-used one, but differs on three points worth knowing before writing name copy: he ranks the Birth number *above* the Name number in authority, he counts titles and prefixes (Mr/Mrs/Miss/Sir/Dame) as part of the name when the person is habitually addressed that way, and he treats *adding an initial* rather than a full legal change as the normal correction. Details and citations in §14.2.

## §2.5 Kumar's extended 7-Core-Number taxonomy

Kumar (Ch.1) uses a **richer 7-number framework** commonly seen in modern Chaldean practice. It **extends** Johari's 3-number Vedic system rather than replacing it. The site should support both; users can choose depth.

### 2.5.1 Terminology bridge (Kumar ↔ Johari)

| Kumar's term | Johari's equivalent | Same calculation? |
|---|---|---|
| Life Path Number | Destiny (Bhagyank) | Yes — sum all digits of DOB, reduce |
| Birthday Number | Psychic (Mulank) | Yes — reduce day-of-birth |
| Expression / Destiny Number | Name (Namank) | Yes — sum Chaldean values of full name |
| Personality Number | (Johari does not split out) | Kumar-only — consonants of name only |
| Heart Desire / Soul Urge Number | (Johari does not split out) | Kumar-only — vowels of name only |
| Hidden Passion Number | (Johari does not split out) | Kumar-only — most-frequent letter-number in name |
| Karmic Lesson Number | (Johari does not split out) | Kumar-only — numbers 1-9 missing from name |

**Naming convention on this site:** we use Kumar's terminology in the calculator UI (Life Path / Birthday / Expression / Personality / Heart Desire) since it's more common in modern practice and matches what other numerology sites use. In article content that leans Vedic, we cross-reference Johari's Sanskrit terms (Mulank / Bhagyank / Namank).

### 2.5.2 Kumar's 5 Core Numbers vs Johari's 3 Primary Numbers

Kumar (Ch.1 §"Core Numbers"): "5 main numbers considered CORE NUMBER, building blocks — 2 from date of birth (Life Path + Birthday) + 3 from Name (Expression + Personality + Heart Desire)."

Johari: 3 primary numbers only — Psychic + Destiny + Name.

**Both are valid frameworks.** Kumar's 5-Core split gives finer granularity (separating vowel-sound-derived subconscious desires from consonant-derived outer personality). Johari's 3-number system is simpler and Vedic-authentic. For a full reading the site should present both.

### 2.5.3 Kumar's calculation-inputs summary (Ch.2 opening)

| For Calculation | You Need |
|---|---|
| Life Path Number | month + day + year (full DOB) |
| Birthday Number | birth date (day of month only) |
| Expression Number | Complete Name + Chaldean number for each letter |
| Personality Number | Consonants of name only |
| Heart Desire Number | Vowels of name only |
| Karmic Lesson Number | Numbers 1-9 missing from name |
| Hidden Passion Number | Highest frequency of number popping in name |
| Karmic Debt Number | 13, 14, 16, 19 appearing in any Core Number's intermediate calculation |
| Challenge Number | Four Challenge numbers using various combinations of dd/mm/yyyy |
| Pinnacle Number | Four Pinnacle numbers using various combinations of dd/mm/yyyy |
| Personal Year Number | Birth date + Universal year |
| Essence Cycle Number | Name + current age |

**Kumar's philosophical framing** (Introduction): "Numerology reveals the blueprint of what your soul has pre-chosen to accomplish in this life... It's the bridge between who you are now and who you have the potential to be." Same anti-prediction, self-knowledge orientation as Johari.

## §3 Planet-number mapping

### 3.1 The 9 numbers and their planets

| # | Planet | Sanskrit | Behavioural qualities (Johari) |
|---|---|---|---|
| 1 | Sun | Surya | Kinglike, kind, royal, disciplined, authoritative, strong, original |
| 2 | Moon | Chandra | Queenlike, royal, attractive, ever-changing, delicate |
| 3 | Jupiter | Guru / Brihaspati | Spiritual, counseling, friendly, self-centered, disciplined |
| 4 | **Rahu** | Rahu | Rebellious, impulsive, short-tempered, secretive |
| 5 | Mercury | Budha | Princely, entertaining, wily, intelligent, sensitive |
| 6 | Venus | Shukra | Romantic, slow, sensual, sweet-spoken, diplomatic, manipulative |
| 7 | **Ketu** | Ketu | Mystical, dreamlike, intuitive, inventive |
| 8 | Saturn | Shani | Wise, malefic, servant-like, laborious, struggling, suffering |
| 9 | Mars | Mangal | Warlike, strong, rough, rustic, perfectionist, doubting, fighting, alienating, discriminating |

**Divergence from Western system:** the Western tradition assigns **Uranus** to 4 (Sun-family) and **Neptune** to 7 (Moon-family). Johari uses **Rahu** (North Node) for 4 and **Ketu** (South Node) for 7 per Hindu tradition.

We can now name the Western source. Cheiro, Ch. II (`-layout` 1318–1326; table verified against the rendered image of PDF p.34 / printed p.33), prints the mapping as: 1 Sun, 2 Moon, 3 Jupiter, 4 **Uranus**, 5 Mercury, 6 Venus, 7 **Neptune**, 8 Saturn, 9 Mars. Every other number agrees with Johari; only 4 and 7 diverge, and the divergence is exactly Uranus/Neptune vs Rahu/Ketu. **Attribute, do not average** — a reading that calls 4 "Rahu" is following the Vedic line, one that calls it "Uranus" is following Cheiro, and both are legitimate within their own tradition. Cheiro also calls the Sun and Moon the only planets with "double numbers", writing them as 1–4 and 2–7 because Sun/Uranus and Moon/Neptune are "interrelated" (Cheiro Ch. II, `-layout` 1328–1337).

### 3.2 Chaldean letter values (Johari's "Unit System")

The standard Chaldean table is used (numerology.py already implements this). Johari confirms:

| Value | Letters |
|---|---|
| 1 | A, I, J, Q, Y |
| 2 | B, K, R |
| 3 | C, G, L, S |
| 4 | D, M, T |
| 5 | E, H, N, X |
| 6 | U, V, W |
| 7 | O, Z |
| 8 | F, P |
| 9 | — (no letter maps to 9 in Chaldean; treated as spiritual/complete) |

**Verified against our implementation:** the table above was compared letter-by-letter with `numerology.py`'s `_CHALDEAN` — **26/26, no mismatches** — by two independent parties, each reading the page image rather than the text layer.

**Divergence from Pythagorean:** Pythagorean assigns 1 to A, J, S (and value 9 exists) — a totally different mapping. Johari uses Chaldean only.

**Cheiro is the upstream source of this table, and it matches ours row for row.** Cheiro Ch. XII, printed p.70 (`-layout` 3075–3090) prints it as "This ancient Chaldean and Hebrew alphabet", saying its origin "is lost in antiquity" but that it is believed to have been originated by the Chaldeans and passed by them to the Hebrews. Two details our table flattens:

- Cheiro prints **one row reading "I or J = 1"** — I and J are a single letter to him, not two letters that happen to share a value. Same arithmetic, different reasoning; worth knowing if anyone ever asks why J is not on its own line in the classical source.
- He gives an explicit *reason* for the missing 9, which Johari does not: those ancient masters "knew that in the 'Highest Sphere' the number 9 represents the 9-lettered name of God, and for this reason no single letter was ascribed to it." A name may still *total* to 9; only no single letter carries it (Cheiro Ch. XII, `-layout` 3092–3103).

⚠️ **Verification note — do not re-extract this table from the text layer.** Plain and `-layout` `pdftotext` both silently drop rows A–M from Cheiro's alphabet page and render `Y = 1` as `Y = I`. Nothing in the output signals the loss; it simply looks like a short N–Z table. The values above were read off the rendered page image (`pdftoppm -f 71 -r 200 -png`) and independently cross-checked against four worked examples elsewhere in the book whose sums only balance if A–M carry these values: AUSTEN = 24 (printed p.74), CHAMBERLAIN = 32 (p.74), GEORGE = 25 and WASHINGTON = 40 (p.154), LEEDS = 20 (p.147).

Cheiro also states his allegiance directly: the two schools are "the Pythagorean and the more ancient one known as the Chaldean", and he advocates "returning to the original Chaldean, Hindu, and Hebrew system" (Ch. XXI, `-layout` 5023–5025, 5077–5082). This corroborates Kumar's Chaldean declaration in `Numerology-You.pdf`.

**Chaldean is the site's only letter table (#202).** A Pythagorean mode was offered until August 2026 and was removed. The reason was sourcing, not popularity: across all 13 books in `data/` (107,809 extracted lines) the word "Pythagorean" appears 12 times and **every one is a passing contrast mention — the table itself appears in none of them.** Goodwin's 28,171-line *Complete Guide*, our one Western numerology book, never names the system at all. The implementation had been a generated formula (`A=1..Z=26 mod 9`) traceable to nothing, which is the same defect class as #172's Lo Shu citation.

Note that popularity ran the other way: Kumar states "Pythagorean system is more popular especially in West but Chaldean Numerology is older." The case for dropping it rests on (a) our audience being Indian, where the Cheiro-derived Chaldean tables dominate, and (b) our inability to source the alternative — not on usage, which we have never measured.

Two shipped bugs came directly from having two tables that could disagree about the same name: #167, and the compound-number caption that needed three QA rounds to settle. With one table, `name_number` is `_reduce()` of the same integer `name_compound` is, so they cannot diverge — verified 0 exceptions over 864 readings. **Do not reintroduce a second system without a sourced table.**

### 3.3 Planet correspondences per number (favourable elements)

| # | Colour(s) | Gemstone | Metal | Day(s) | Direction | Deity |
|---|---|---|---|---|---|---|
| 1 | Orange, yellow, gold, copper | Ruby (Manikya) | Gold | Sun, Mon | East | Sun-god (Surya) |
| 2 | White, cream, light green | Pearl (Moti) | Silver | Mon | NW | Shiva |
| 3 | Yellow, gold, orange | Yellow Sapphire (Pukhraj) | Gold | Thu | NE | Vishnu (blue-skinned, four-armed) |
| 4 | Grey, khaki, electric blue | Hessonite Garnet (Gomed) | Panch-dhatu | Sat | SW | Ganesha (on golden throne) |
| 5 | Light green, turquoise, silvery-grey | Emerald (Panna) | Silver / Gold | Wed | N | Mahalakshmi (on pink lotus) |
| 6 | White, pink, pale blue, all light shades | Diamond (Heera) | Silver / Platinum | Fri | SE | Lakshmi (Venus is deity of semen/sensuous) |
| 7 | Iridescent green/blue, mother-of-pearl, ash | Cat's Eye (Lehsunia) | Panch-dhatu | Tue (some Sun) | S / SW | Nrisimha (Narasimha, lion-headed avatar) |
| 8 | Black, dark blue, dark purple, deep grey | Blue Sapphire (Neelam) | Panch-dhatu (5-metal alloy) | Sat | W | Shani-dev (idol in 5-metal mix) |
| 9 | Red, coral pink, deep pink | Red Coral (Moonga) | Copper | Tue | S | Hanuman (monkey god) / Kartikeya |

**Safety caveat on gemstones (Johari repeats throughout):** never wear a planet's gem without confirming that planet is functionally benefic in your natal chart. Blue Sapphire (Neelam) and Hessonite (Gomed) are the most dangerous — they can backfire within days. Ruby is women-only-cautioned (women use garnet substitutes). Pearl for Scorpio ascendants is contra-indicated (Moon debilitates there).

### 3.4 Ayurvedic dosha per number

| # | Dominant dosha | Notes |
|---|---|---|
| 1 | Pitta (bile) | Aggravated by anger/heat; avoid oily/fish/wine/curd |
| 2 | Kapha (mucus) | Slower metabolism; benefits from warming spices |
| 3 | Vata (wind) mixed pitta | Wind-related conditions common |
| 4 | Vata dominant | Nervous system, sudden changes, gas |
| 5 | Vata-pitta mixed | Nervous energy, restless |
| 6 | Kapha with Pitta | Sensual; overindulgence in sweet/rich foods |
| 7 | Vata | Dreamy, low grounding, spiritual dis-embodiment |
| 8 | Vata dominant | Struggle, chronic conditions, joints/bones |
| 9 | Pitta dominant | Bilious, fiery, prone to fevers |

## §4 Per-number traits (Johari)

### Number 1 — Sun / Surya
- **Assigned to birthdays:** 1, 10, 19, 28
- **Character:** fixity of purpose, clear expression, obstinate, authoritative, punctual, sober; loves freedom; needs attention/respect; luxurious tastes, spendthrift; enthusiastic in religion, mission-driven
- **Strengths:** leadership, correct-decisions, hardworking, creative, positive
- **Weaknesses:** irritability, dislike-of-criticism, obstinacy, requires-praise
- **Health:** circulatory issues, high BP after 50, eye problems, hospitalization after 56; pitta type
- **Career peak:** ages 35–49
- **Strong months:** Mar 21 – Apr 28; Jul 10 – Aug 20
- **Weak months:** Dec 21 – Feb 19 (avoid new ventures)
- **Good dates:** 1, 4, 10, 13, 19, 22, 28, 31 of any month
- **Good days:** Sunday, Monday (especially if Sun/Mon falls on 19 or 28)
- **Compatibility:** best with 1, 4, 2, 7; **worst with** 6 (deceptive-friendly), 8 (Saturn slows), 5 (unstable together). Number 1 as name creates authority — good for men; women's name-1 can create difficulty
- **Exalted 1:** from birth-date 28 (most fortunate)
- **Mantra:** *AUM HRIM HRIM SURIYAYE NAMAH AUM* — 7,000 times within ascending moon cycle
- **Fasting:** Sundays, single meal salt-free before sunset (chickpea bread + milk with dates + cardamom)

### Number 2 — Moon / Chandra
- **Birthdays:** 2, 11, 20, 29
- **Character:** gentle, tender, emotional, ever-changing, dependent, cooperative, imaginative, intuitive; queenlike attractiveness; strong feminine energy regardless of gender
- **Strengths:** empathy, aesthetic sense, adaptability, arbitration
- **Weaknesses:** indecisive, moody, dependency, timidity, worry, quick-changing
- **Health:** water-retention, breathing/lung issues, mental strain, insomnia; benefits from Rudraksha bead
- **Peak:** slower blooming; steady across life
- **Good dates:** 2, 11, 20, 29 (good); 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31 (moderate)
- **Good days:** Monday
- **Compatibility:** best with 1, 2, 7, 8, 9; strained with 3 (advice givers, not partners), 5 (Moon-Mercury enmity)
- **Exalted 2:** from birth-date 29
- **Master number 11:** discussed under 2 — mystic number, brings extra intuition + potential leadership; can become spiritual teachers. **Not treated as separate Western-style "master" — 11 reduces to 2, but 11-borns get extra sensitivity.**
- **Deity:** Shiva (on tiger skin, lotus posture)
- **Meditation:** on Shiva or on the Moon; visualise moon reflected in still water

### Number 3 — Jupiter / Guru / Brihaspati
- **Birthdays:** 3, 12, 21, 30
- **Character:** wise, spiritual, counsellor-natured, disciplined, disciplinarian, universal-helper, hardworking; expansive, over-committing ("says yes to everyone")
- **Strengths:** teaching, philosophy, guidance, dharma, ethical clarity
- **Weaknesses:** self-centered, disappoints friends by over-committing, preachy
- **Health:** wind/air disorders — gas, bloating, arthritis; heart trouble late; Rudraksha protective
- **Good dates:** 3, 12, 21, 30 (best); 6, 9, 15, 18, 24, 27 (secondary)
- **Good day:** Thursday
- **Compatibility:** best with 1, 3, 6, 9; strained with 7 (Jupiter-Ketu enmity), 5
- **Exalted 3:** from birth-date 12
- **Deity:** Vishnu (sky-blue, four-armed, preserver aspect)
- **Fasting:** Thursday, salt-free chickpeas + jaggery
- **Career:** teaching, law, medicine, priesthood, publishing, higher education

### Number 4 — Rahu (North Node)
- **Birthdays:** 4, 13, 22, 31
- **Character:** rebellious, impulsive, secretive, revolutionary, short-tempered; opposes convention; sudden changes; misunderstood
- **Strengths:** originality, resilience, independent thought, reformer's zeal
- **Weaknesses:** suspicion, isolation, temper, poor circle, tendency to violence if unchecked (especially birth-date 31)
- **Number 13:** karmic-marker — cautionary; represents obstacle-generating combinations. Born-13 people should meditate on their gemstones + practise ahimsa
- **Number 22:** discussed under 4 — master-number-like intensity, potent for architects/builders/movement-organisers. **Not Western "master 22" but analogous** — extra scale, extra karmic weight
- **Health:** nervous system, unexpected accidents, chronic conditions with sudden onset
- **Good dates:** 4, 13, 22, 31 (esp. if on Saturday or Wednesday)
- **Good day:** Saturday
- **Compatibility:** best with 1, 6, 4 (with self); strained with 3, 5, 9 (especially 9 which is Mars-enemy)
- **Exalted 4:** from birth-date 31
- **Deity:** Ganesha (golden throne, remover of obstacles)
- **Gemstone:** Hessonite Garnet (Gomed) — chart-check required

### Number 5 — Mercury / Budha
- **Birthdays:** 5, 14, 23
- **Character:** intelligent, mercurial, quick-witted, hardworking, sensitive; enjoys learning; princely; loves risks
- **Strengths:** communication, adaptability, learning, business acumen, media/writing/journalism
- **Weaknesses:** anxiety, weak periods of low confidence, over-thinking, restlessness
- **Health:** nervous exhaustion, digestive issues; often "feels weak and sad" because Mercury is nearest Sun (drawn by Sun's power)
- **Good dates:** 5, 14, 23 (especially when on Wed or Fri)
- **Good day:** Wednesday
- **Colours:** light greens, turquoise, silvery-grey
- **Compatibility:** best with 1 (gifts + support), 3 (positive), 5 (self), 6 (creative); strained with 2, 7, 8 (weakening)
- **Exalted 5:** from birth-dates 23 and 32
- **Deity:** Mahalakshmi (pink lotus in blue water)
- **Career:** writing, journalism, teaching, communications, trading, media, sales, tech

### Number 6 — Venus / Shukra
- **Birthdays:** 6, 15, 24
- **Character:** romantic, sensual, sweet-spoken, diplomatic, slow, aesthetic; artistically inclined; loves comfort/beauty
- **Strengths:** relationship-building, aesthetic sense, harmony, arts, luxury industries
- **Weaknesses:** slow to act, over-indulgent, manipulative when insecure, procrastinates; **can be overly attached to sensual pleasure**
- **The "Universal Friend":** number 6 alone bridges odd and even groupings — good social lubricant
- **Health:** kidneys, reproductive system, throat, weight gain from over-indulgence
- **Good dates:** 6, 15, 24 (best); 3, 9, 12, 18, 21, 27, 30 (secondary)
- **Good day:** Friday
- **Compatibility:** best with 4, 8, 9, 3; strained with 5 (both aesthetic + moody), 7 (introversion clashes)
- **Exalted 6:** from birth-dates 24 and 33
- **Deity:** Lakshmi (also Parvati)
- **Career:** interior design, arts, entertainment, jewelry, fashion, hospitality, cosmetics

### Number 7 — Ketu (South Node)
- **Birthdays:** 7, 16, 25
- **Character:** mystical, dreamlike, intuitive, inventive, philosophical; drawn to spirituality, healing arts, occult sciences; solitary
- **Strengths:** psychic sensitivity, research/analytical depth, spiritual pursuits, meditation, invention
- **Weaknesses:** dreamy escapism, indecision, difficulty grounding, prone to misunderstandings, isolation
- **Number 16:** karmic-marker — Sun+Venus conflict; "sixteenth day" people face rise-and-fall pattern; watch for accidents
- **Number 25:** Moon+Mercury tension; self-condemning nature; artistic but late-blooming; **should avoid risky ventures**
- **Health:** nervous system, sensitive to environment, prone to allergies, insomnia
- **Good dates:** 7, 16, 25 (especially when on Sunday or Monday)
- **Good day:** Tuesday (some traditions Sunday)
- **Compatibility:** best with 1 (political/cultural allies), 2, 3, 9; strained with 4 (mutual attraction with instability), 7 (troublesome with self)
- **Exalted 7:** from birth-dates 25 and 34
- **Deity:** Nrisimha (Narasimha, lion-headed Vishnu avatar)
- **Career:** research, philosophy, healing, astrology, occult sciences, priesthood, monasteries, writing

### Number 8 — Saturn / Shani
- **Birthdays:** 8, 17, 26
- **Character:** wise-through-struggle, laborious, servant-like, malefic (challenging), disciplined; slow-burning success
- **Strengths:** endurance, work-ethic, ability to withstand loss, long-term thinking, service to downtrodden
- **Weaknesses:** melancholy, slow progress, poverty in early life, victim of others' cruelty, stigmatised
- **Number 17:** Sun+Ketu tension → real spiritual understanding through inner conflict; "leaves mark on history after death"
- **Number 26:** Moon+Venus dependency on opposite-sex; **26-borns must be very careful selecting a life partner** (avoid 4, 8, 9; select 1, 3, 6)
- **Number 44 / 8-borns in general:** significant late-life success; **fame/wealth often comes after 40**
- **Health:** joints, bones, teeth, digestive-blocking, chronic conditions; benefits from vitamin A/D/E, calcium, iron; pearl-powder + Neelam-pishti supplementation (Ayurvedic gem powders)
- **Good dates:** 8, 17, 26 (best if on Sat); 1, 2, 4, 5, 7 (secondary friendship dates)
- **Good day:** Saturday
- **Compatibility:** best with 1, 3, 5, 6 for romance; **avoid 4, 8, 9** for marriage
- **Exalted 8:** from birth-dates 26 and 35
- **Deity:** Shani-dev (idol in 5-metal alloy — panch-dhatu)
- **Career:** politics, social work, iron/steel/mining, law enforcement, hard sciences, real-estate, agriculture, servitude professions
- **Fasting:** Saturday sunset only, moong-urad khichdi with rock salt

### Number 9 — Mars / Mangal
- **Birthdays:** 9, 18, 27
- **Character:** warlike, strong, rough, martial, doubting, perfectionist; discriminating; competitive
- **Strengths:** courage, protective instinct, athletic ability, leadership in crisis, sports/military/rescue
- **Weaknesses:** anger, doubt, alienation, restlessness, difficult marriage (especially Mars-Venus tension)
- **Number 18:** Sun+Saturn opposition + Mars overlay → obstinate, family friction, materialist, gains from wars/revolutions/upheavals; **rise after 40**
- **Number 27:** Moon+Ketu — planning ability + emotional intensity; if grounded, achieves major material success
- **Health:** bile-dominated, prone to all fevers, blood disorders, accidents, burns
- **Good dates:** 9, 18, 27 (especially Tuesdays)
- **Good day:** Tuesday
- **Compatibility:** number 6 women ideal for number 9 men; number 3 men ideal for number 9 women; **best partners: 1, 3, 6; avoid 5, 7, 9** for marriage
- **Exalted 9:** from birth-dates 27 and 36
- **Deity:** Hanuman (monkey god, celibate, service-focused)
- **Career:** military, police, surgery, athletics, engineering, mechanical trades, first-responder professions

## §5 Compound numbers 10 – 31 (birthdate influence)

Compound numbers are the *unreduced* birthdates from 10 to 31. They modify the psychic number they reduce to. Johari treats the ten's-digit as the "series" indicator — a 12 (in the 1-series) behaves differently from a 21 (in the 2-series) even though both reduce to 3.

**Pinpoint / scope warning:** Johari, ch. "The Compound Numbers", opening paragraph — the compound numbers "apply to the psychic numbers of those who were born on that date", i.e. the **day of the month, 10–31**, and are explicitly *not* defined for anything else. They are **not** a name-total interpretation, and there are no rows above 31. Verified against the PDF 2026-08-08. `numerology.py` currently applies this table to the Chaldean *name* total over a 10–52 range, and the interpretation strings it carries are Cheiro's rather than Johari's (see §13.3, and issue #160).

**Scope quote, now cited to the line (issue #163).** Johari, ch. "The Compound Numbers" (chapter heading at line 5668), **lines 5673–5674**: "…those born after the ninth day of any month. All compound numbers discussed here apply to the psychic numbers of those who were born on that date." He restates the range at **line 5677**: "…people born on dates from 10 to 31…". Line numbers are into a `pdftotext -layout` extraction of Johari — **the `-layout` flag matters**, plain `pdftotext` renumbers everything. This settles the scope: the compound number is the **unreduced day of the month, 10–31**, and nothing else. The pre-fix code applied this table to a Chaldean *name* total spanning 10–52; that had **no basis in this source** — rows 32–52 do not exist in it, and a name total is not a birth date.

### 5.1 Two different compound systems — Johari's and Cheiro's (issue #160)

The note above is correct **about Johari** and stands unchanged. What it could not know is that the engine was never implementing Johari here at all. `data/numerology/2015.70770.Cheiros-Book-Of-Numbers_text.pdf` (Cheiro, *Book of Numbers*) was added to the repo after that note was written, and it resolves the question: the strings in `_COMPOUND_NUMBER_MEANING` are **Cheiro's**, and Cheiro's system is legitimately name-scoped and legitimately runs to 52.

**These are two distinct systems and must never be conflated again:**

| | Johari | Cheiro |
|---|---|---|
| Input | unreduced **day of the month** | unreduced **name total** (and dates, added together) |
| Range | **10–31** (months end at 31) | **10–52** (52 weeks in a year) |
| Framing | planetary rulers, exalted numbers, psychic-number modifier | Tarot-derived symbolism; the "hidden forces" behind the name |
| Implemented? | **No** — still unimplemented, see below | **Yes** — this is what `/numerology` renders |

Line numbers below index a `pdftotext -layout` extraction of the Cheiro PDF. **The `-layout` flag matters** — plain `pdftotext` renumbers everything. Extraction reproduced and verified byte-identical 2026-08-10.

**Cheiro applies compound numbers to names, explicitly and repeatedly:**
- Line 7246: "The compound number of 10 made by his name…"
- Line 6906: "Now, turning to the compound number of the name, 16…"
- Lines 6987–6993: "…the compound Number 15, as set out on page 81…" / "…which the compound number of a name always denotes".
- Line 7595: "The compound number of President Roosevelt's name, which works out to a 22…"
- Lines 3243–3277: the Austen Chamberlain worked example sums the letters of the name to **32 = 5**, then reads both numbers off it — "Both the single numbers and the compound numbers in this name are singularly fortunate… The compound number 24 is also favourable."

  *Precision correction (added with §14, verified against the rendered image of PDF p.75 / printed p.74):* those are **two separate word-totals**, not one name-total plus a stray figure. AUSTEN = 24 = 6, CHAMBERLAIN = 32 = 5. Cheiro scores each word of a name on its own and only then combines — which is the whole point of the passage, and is the method §14.2 sets out. Nothing above depends on this, but anyone reusing the example should split the two.

**Cheiro's range bounds are stated, not assumed:**
- Lower, line 3447: "All numbers from 10 up become in symbolism 'double' or 'compound' numbers."
- Upper, line 3463: "Distinct symbolism has been given to the 'compound' numbers up to that mysterious number of 52."
- Closing, lines 3757–3758: "We have now completed the 52 numbers which represent the 52 weeks of our year; for all practical purposes there is no necessity to proceed further."

So **the 10–52 clamp in `compute()` is sourced.** Issue #160 called it "arbitrary… not a rule in any source"; that was true of the sources available when it was filed, and is not true now.

**The decisive row is 28**, which is why the mix-up was detectable at all. Cheiro, lines 3660–3669: "This number is full of contradictions… loss through trust in others, opposition and competition in trade, danger of loss through law." Johari's 28 (lines 6034–6035 and 6044, and the table above) is the **opposite**: "the number 28 is ruled by the Sun, a lucky number that brings success" … "They leave their marks on history." The page was printing Cheiro's reading under Johari's name.

**Also corrected in the same pass:** rows 13/14/16/19 opened with "KARMIC DEBT —", which is **Kumar's** category (§12.5), not Cheiro's compound reading — a second mixed attribution, and a directly contradictory one, since Cheiro's 19 is "regarded as fortunate and extremely favourable… the Prince of Heaven" (line 3586). Kumar's Karmic Debt logic is unaffected and still lives in `_karmic_debt_flags` / `_KARMIC_DEBT_NUMBERS`.

**Cheiro's 32–52 rows are mostly cross-references**, e.g. line 3710: "34 Has the same meaning as the number 25, which is the next to it in its own series of 'compound' numbers." The code stores these as aliases (`_COMPOUND_ALIAS`) rather than duplicating text. Numbers with their own text above 31: **32** (3697), **37** (3717), **43** (3736), **51** (3749).

**Still unimplemented — do not mistake this for done:** Johari's *birthdate* compound reading (the 10–31 table above) is a genuine, separate, unbuilt feature. Correcting the attribution of the Cheiro table does not deliver it. If it is built, it must be surfaced as a **distinct** panel keyed on the day of the month, never merged into the name-compound panel.

| # | Reduces to | Ruled by (compound flavor) | Character summary (Johari) |
|---|---|---|---|
| 10 | 1 | Sun + 0 (Anant) | Success after hard struggle; zero brings hidden enemies. Independent life needed |
| 11 | 2 | Moon + Moon (mystic) | Special "mystic number"; extra intuition; can become spiritual teacher |
| 12 | 3 | Sun + Moon | Anxious, last-minute decisions, unfinished projects; happy personal life; philosophical |
| 13 | 4 | Sun + Jupiter → Rahu | **Karmic-marker.** Obstacles, misunderstanding; meditate on gemstone + practise non-violence |
| 14 | 5 | Sun + Rahu | Risk-taking, gambling, wrong future-assessment; caution during natural calamities |
| 15 | 6 | Sun + Mercury → Venus | Luxury-loving, popular, artistic; interest in Tantra/magic; charming |
| 16 | 7 | Sun + Venus → Ketu | **Karmic-marker.** Rise-and-fall pattern, accident-prone; dreamers; occult/healing pull |
| 17 | 8 | Sun + Ketu → Saturn | Struggle then spiritual understanding; benefic despite Saturn; **remembered after death** |
| 18 | 9 | Sun + Saturn → Mars | Family friction, obstinate, materialist; gains from upheaval; **success after 40** |
| 19 | 1 | Sun + Mars → Sun | Very lucky psychic-1; enthusiasm; **more fortunate than 10, less than 28** |
| 20 | 2 | Moon + 0 | Impatience, unrewarded effort, weakness in relationships; spiritual practise needed |
| 21 | 3 | Moon + Sun → Jupiter | Social, popular, arbitrator/diplomat; **helped by combination** |
| 22 | 4 | Moon + Moon → Rahu | **Master-like:** intense builder-organiser; overcomes obstacles except marriage; **Johari's "extra scale"** |
| 23 | 5 | Moon + Jupiter → Mercury | Lucky, intelligent, jovial, supported by authority-figures; **considered lucky by Johari** |
| 24 | 6 | Moon + Rahu → Venus | Fortunate; secretive; helpful; but life-changes frequent; **exalted 6** |
| 25 | 7 | Moon + Mercury → Ketu | Self-condemning early; artistic; late-blooming; **avoid risky ventures**; **exalted 7** |
| 26 | 8 | Moon + Venus → Saturn | Opposite-sex dependency → main cause of suffering; **carefully select life partner** (only 1, 3, 6); **exalted 8** |
| 27 | 9 | Moon + Ketu → Mars | Planning power + emotional depth; success if grounded; **exalted 9** |
| 28 | 1 | Moon + Saturn → Sun | Struggle then success; **exalted 1** — most fortunate psychic-1; philosopher-politician type |
| 29 | 2 | Moon + Mars → Moon | Insecurity, restlessness; women should fast on Mon/Thu to attract harmonious partner; **exalted 2** |
| 30 | 3 | Jupiter + 0 | Less fortunate than pure 3; hard workers; sceptical of religion; philosopher-critic type |
| 31 | 4 | Jupiter + Sun → Rahu | Uncertainty, isolation, rebellion; leadership qualities but shy; **exalted 4** |

**Exalted numbers (Johari):** these compound-birthdates that produce a *particularly powerful* reduced number:
- 1 exalted from 28
- 2 exalted from 29
- 3 exalted from 12
- 4 exalted from 31
- 5 exalted from 23 and 32
- 6 exalted from 24 and 33
- 7 exalted from 25 and 34
- 8 exalted from 26 and 35
- 9 exalted from 27 and 36

**"Difficult" compound numbers (Johari's karmic-markers):** 13, 14, 16, 19, 26, 27 — carry extra karmic weight and require conscious practice/discipline.

## §6 The Vedic Square

The Vedic Square is a 9×9 multiplication table where each entry is reduced to a single digit (1–9). Origin: not attributable per Johari; documented in Keith Critchlow's *Islamic Patterns* (1984) as a design principle underlying Islamic and Vedic sacred geometry.

**Construction:** cell (row `r`, column `c`) = `(r × c)` reduced by adding digits until 1–9.

**Key observation Johari cites:** the number 9 repeats 21 times in the 9-column, 9-row, and 9-multiples — the highest repetition of any digit. Joining the midpoints of these 9-cells produces geometric patterns (yantras) used in temple architecture.

**Interpretive use:** each cell reveals the multiplicative interaction between two numbers → useful for compatibility analysis (row = person A's psychic, column = person B's psychic, cell = resulting interaction character).

**Not addressed in source:** no explicit compatibility-scoring formula from the Vedic Square — Johari uses it as a meditative visual, not a scoring engine. Compatibility scoring in §7 comes from the Relationships table, not from the Square itself.

## §7 Number compatibility (Johari's per-pair rules)

Johari provides a full "Number X and Number Y" section for every pair (see book pp. 1150-5700). Summarised:

### Friendly pairings (relaxed but sometimes unproductive)
- 1 ↔ 1, 4, 2 — royal support
- 2 ↔ 1, 7, 8, 9 — Moon's emotional resonance
- 3 ↔ 1, 3, 6, 9 — Jupiter's expansion
- 4 ↔ 1, 6, 8 — Rahu's affinity for opposite-support
- 5 ↔ 1, 3, 5, 6 — Mercury's mercurial harmony
- 6 ↔ 3, 4, 5, 6, 8, 9 — Venus's universal-friend nature (**5 corrected — see the 6↔5 note under Enemy pairings**)
- 7 ↔ 1, 2, 3, 9 — Ketu's spiritual alliances
- 8 ↔ 1, 3, 5, 6 — Saturn's slow-friend
- 9 ↔ 1, 3, 6 — Mars's warrior-alliances

### Enemy pairings (activate growth through friction)
- 1 ↔ 5 (both destabilise), 6 (deceptive friendship), 8 (Saturn drags Sun)
- 2 ↔ 3 (advisers not partners), 5 (Moon-Mercury enmity)
- 3 ↔ 5 (both distracted), 7 (Jupiter-Ketu tension — **DISPUTED, see note below; retained, not deleted**)
- 4 ↔ 3 (Rahu-Jupiter friction — **DISPUTED as a symmetric verdict, see note below**), 5 (both restless), 9 (Rahu-Mars war)
- 5 ↔ 2, 7, 8 (weakening)
- 6 ↔ 1 (only survives short-term), 7 (introvert-extrovert)
- 7 ↔ 4 (mutual attraction with instability), 7 (troublesome with self), 8 (Ketu-Saturn)
- 8 ↔ 4 (both bring difficulty), 8 (double Saturn), 9 (Mars-Saturn war)
- 9 ↔ 5 (both restless), 7 (both spiritual-doubting), 9 (double Mars)

#### Correction: 6 ↔ 5 is a FRIEND pair, not an enemy pair (issue #163)

This corpus previously listed `5` under 6's enemies, glossed as the two being moody in
each other's company. Johari says the opposite, **in both directions**, in the two
per-pair prose sections that cover it.

All line numbers below are into a `pdftotext -layout` extraction of Johari,
*Numerology: With Tantra, Ayurveda, and Astrology* — **the `-layout` flag matters**;
plain `pdftotext` renumbers everything by roughly a third, so a line number quoted
without the flag is not checkable.

- §"Number 5 and Number 6", **line 3514**: "Numbers 5 and 6 are mutual friends. Sixes are
  slow, and 5s are quick."
- Same section, **line 3516**: "Sixes are beneficial for 5s in friendship, business
  partnership, and marriage."
- §"Number 6 and Number 5", **line 3958**: "Numbers 6 and 5 are mutual friends. Fives help
  6s with psychological problems…"
- Same section, **lines 3965–3966**: 6s "can enter into business partnerships with 5s and
  select number 5 for important business appointments or for residential numbers."

The friendship is stated from both sides, and both sides extend it to business
partnership. The old enemy entry and its gloss were not in the source and have been
removed; `5` has been added to 6's friendly row.

One directional caveat the source does state, and which a symmetric table cannot carry
(**line 3964**): "Marriage between a number 6 woman and a number 5 man is not ideal, but
the reverse combination is very good." That is a gendered, directional qualifier on the
*marriage* reading only — it does not make the pair an enemy pair, and it is recorded
here rather than encoded.

#### Disputed: 3 ↔ 7 — retained above, but the book's relational prose contradicts it

The `(Jupiter-Ketu tension)` gloss traces to Johari's *planetary* sentence, **lines
2477–2478**: "Number 7 is ruled by Ketu, an unfriendly planet to Jupiter, but Jupiter has
a neutral attitude toward Ketu." Johari's relational prose then overrides that planetary
framing within the same section:

- §"Number 3 and Number 7", **lines 2484–2485**: "…both are interested in reforms, both
  are writers. As friends and business partners they can be very helpful to each other."
- §"Number 7 and Number 3", **line 4455**: "They are mutually beneficial in a friendship
  or business partnership."

So on the relational reading the book supports a *friend* verdict for 3↔7 — which is the
verdict `_FRIEND_PAIRS` in `numerology.py` already carries. **Treat the friend verdict as
the one the source supports.** The enemy-list entry is deliberately **not deleted**,
because the planetary rationale is genuinely in the source too; this is a real tension
inside Johari, not a transcription error, and removing one half would hide it.

#### Disputed: 4 ↔ 3 — the source states the asymmetry outright

**Line 2967**, §"Number 4 and Number 3": "Number 3s are neutral toward 4s, though 4s are
enemies of 3s."

One sentence, two different verdicts depending on direction — so *neither* a symmetric
"enemy" nor a symmetric "friend" entry is faithful to it. The same section continues
(**lines 2971–2972**) that "4s are benefited by this friendship, business partnerships,
etc. Number 4 women can select number 3 men for marriage, but the reverse is not true" —
directional again. Left in place and marked disputed; the subsection below says why it
cannot be resolved inside a symmetric table.

### Why the remaining pair disagreements are NOT resolved (directionality)

Issue #163 records 23 of 45 pairs on which the two compatibility tables disagree. Only
6↔5 is corrected above. The rest are left open for a sourcing reason, not an effort one:

1. **Johari's pair system is directional, not symmetric.** The reading instruction for his
   summary chart says so outright (**lines 5663–5665**): "…find your own psychic number on
   the far left vertical column, then the psychic number of the person with whom you wish
   to relate at the top horizontal column." A row-versus-column lookup is a directed 9×9
   grid — 81 cells — not a 45-pair symmetric set. The prose bears this out: 6↔5, 3↔7 and
   4↔3 above each carry a verdict that shifts by direction or by gender.
2. **Both summary grids are images whose bodies do not extract.** The headings survive —
   "Summary of Interaction Between Numbers" at **line 5658** and "Relationships and
   Characteristics of Numbers" at **line 6360** — but the cells under each come out blank
   in the `-layout` extraction. The authoritative tabular verdicts are simply not readable
   from this source.
3. **All 81 per-pair prose sections DO extract.** Verified: every `Number X and Number Y`
   heading for X,Y ∈ 1–9 is present in the `-layout` extraction (7 of them prefixed by a
   form-feed page-break character, which is why a naive line-anchored grep finds only 74),
   each followed by its prose.

Therefore: **a symmetric 45-pair table is not derivable from this source.** Reconciling
the 23 disagreements honestly means reading all 81 directed sections and modelling the
result as a directional 9×9 grid — a change to the data model, and **deliberately out of
scope** here. Until that happens the disagreements stay recorded and unresolved rather
than being settled by picking a side.

**Do not fill any of these cells from general numerology knowledge.** Anything not quoted
above with a line number was not read out of the book. `data/numerology/AnkitNotes/*.pdf`
(unattributed practitioner notes, drivers 1–5 only), the `chaldean-numerology-…-2888.pdf`
internet compilation, and Goodwin's Western/Pythagorean *Complete Guide* are **not**
acceptable sources for a Vedic pair verdict.

### Neutral pairings (inert, no strong help/harm)
- Most pairings not listed above are treated as neutral by Johari — some cooperation possible with effort.

**Johari's framing:** "friend numbers relax and stop progress; enemy numbers create alertness and activity, so enemies are actually friends for growth". Take compatibility as a description of dynamic, not verdict.

### Marriage-specific compatibility (Johari)
- **Best marriages** cluster around: 1+2, 1+4, 3+6, 3+9, 6+9, 2+7
- **Avoid** for marriage: 1+8, 4+9, 5+7, 7+7, 8+9, 9+9
- **Number 26 (Saturn-flavored 8):** especially careful — only select 1, 3, 6 partners
- **Number 29 (Moon-flavored 2):** marry early; late marriage brings mental problems

## §8 Master numbers 11, 22, 33 — Johari's Vedic treatment

Johari does **not** use the Western "master numbers" concept where 11/22/33 remain unreduced with elevated meanings. Instead:

- **11** discussed under 2 — "mystic number", intuitive gift, potential spiritual teacher, but still functionally a 2
- **22** discussed under 4 — extra scale/intensity for building-organizing work, but still functionally a 4
- **33** discussed only in passing as "exalted 6" — Venus-magnified expression

**Practical implication for the calculator:** Johari-mode does NOT preserve master numbers as separate categories — always reduces. The Chaldean/Western modes may preserve them. UI should let user choose — **not shipped; see the decision below.**

### Decision on the §8 user choice (issue #179)

The "let the user choose" recommendation above is **not implemented and is not planned.** One reduction convention is applied to everyone and declared on the page. This is the policy as it ships in `numerology.py`:

| Function | Number it produces | `preserve_masters` | Why |
|---|---|---|---|
| `_life_path` | Life Path / Destiny (Bhagyank) | `True` | All-digits Johari method per §2.2; masters kept on the **final total only** (#162) |
| `_birthday_number` | Birthday / Psychic (Mulank) | `False` | §2.1 fixes the range at 1–9 and §4's birthday lists are single-digit (#164) |
| `_personal_year` | Personal Year | `False` | §12.8 and §9 both give the cycle a range of 1–9 (#169) |
| `_sum_letters` | Expression / Personality / Heart Desire / Name (Namank) | `True` | Chaldean letter-value numbers, where 11/22/33 are part of the framework rather than an unreduced intermediate (#179) |

**Why no toggle.** A reader has no basis on which to pick a reduction convention — the choice is only meaningful to someone who already knows both traditions well enough not to need the calculator, and offering it makes the site look uncertain about its own method. One convention, applied to everyone and named on the page, beats a switch nobody can evaluate. The cost of reversing this is small: `_reduce()`'s `preserve_masters` parameter is keyword-only with **no default**, so every call site has to name its own policy, and adding a toggle later stays a call-site change rather than a rewrite.

**Honest flag — keeping masters on Life Path departs from §8.** §8 says Johari-mode always reduces; a strict reading of the corpus would drop 11/22/33 on the Life Path too, since Johari treats 11 as a 2 and 22 as a 4. Keeping them is a **deliberate product call, not a reading of Johari**: master numbers are what readers arrive expecting from every other numerology site, and silently dropping them on the site's headline number would read as a bug rather than as a tradition. The departure is confined to Life Path and the name-derived numbers — §2.1's Psychic and §12.8's Personal Year follow §8 exactly. Recorded here so the next audit finds a decision rather than a contradiction, and can reopen it as a decision if it disagrees.

## §9 Personal Year cycle (Projecting Into the Future)

**Calculation:** `month_of_birth + date_of_birth + last_two_digits_of_year + weekday_number_of_birthday_this_year` → reduce to single digit.

Weekday-to-planet map (used in personal-year calc):
- Sun = 1, Mon = 2, Tue = 9 (Mars), Wed = 5 (Mercury), Thu = 3 (Jupiter), Fri = 6 (Venus), Sat = 8 (Saturn)

**Example:** born May 12, 1934. Year 1991. May 12 1991 falls on Sunday (=1).
5 + 12 + 91 + 1 = 109 → 10 → 1 → **Personal Year 1**.

### Personal Year meanings (Johari)
- **Year 1 (Sun):** difficulties lessen; help from authority; health improves; new ventures favoured; name and fame; competitions
- **Year 2 (Moon):** magnetism increases; new friends; real-estate benefit; less stress; avoid unnecessary worry
- **Year 3 (Jupiter):** wisdom, project completion, financial gain, name+honor; **avoid signing contracts in Jupiter-year for businessmen** (frankness brings trouble); job promotions
- **Year 4 (Rahu):** success WITH difficulties; marriage-ready; children arrive; **poor for love affairs**; travel favoured; spiritual pursuits
- **Year 5 (Mercury):** business success, foreign travel, partnerships; conscious speech required; **memorable year**
- **Year 6 (Venus):** family relationships flourish; romance + conception; showbiz/arts/jewelry professions favoured; unexpected wealth
- **Year 7 (Ketu):** misunderstandings, difficulties; **more work, less profit**; good for healing arts, astrology, hypnosis; test friends; patience solves problems
- **Year 8 (Saturn):** good for politics, social work, iron/steel; **health precautions needed** (blood, heart); use pearl-powder + Neelam-pishti; independent action favoured
- **Year 9 (Mars):** completion, fulfillment, honour by society; unexpected financial gains (lottery, inheritance); slight disagreements with authority; spiritual pursuits recommended

## §10 Name auspiciousness rules (Johari)

- **First letter of full name is most potent** — matters more than any other letter for the vibration
- **Name Number should harmonise with either Psychic or Destiny:**
  - Name ↔ Psychic → good social life, friendships
  - Name ↔ Destiny → remembered after death, legacy-worthy
- **Family-name addition on marriage** (traditional Indian practice): can bring harmony but sometimes changes name-number to enemy of husband's family — check first
- **Professional identity name** (books, business, art) — this is the "popular name" that counts as the Name Number, not necessarily legal name
- **Business name:** Johari does not devote a dedicated section, but per-number recommendations imply:
  - **1 (Sun):** authority-branded — government-contract businesses, leadership consultancies
  - **3 (Jupiter):** teaching, publishing, wisdom-industries
  - **5 (Mercury):** trading, media, communication, tech
  - **6 (Venus):** hospitality, entertainment, beauty, arts
  - **8 (Saturn):** manufacturing, real-estate, heavy-industry, service-labor
  - **AVOID for business name:** 4, 7 (both bring uncertainty/losses)
- **Residential/city numbers:** house-number, street-number, city-name-value should each be compatible with Destiny Number of the resident. If not compatible, Johari advises against renting/buying that property.

**Cheiro corroborates and sharpens several of these — see §14.2 and §14.9.** Points of contact and of difference:

| Johari (§10) | Cheiro | Verdict |
|---|---|---|
| "Popular name" counts, not legal name | "the most used Christian and Surname"; titles count when habitually used | **Agree**, Cheiro more specific |
| Name should harmonise with Psychic **or** Destiny | Name should harmonise with the **Birth number** (day-of-month) | **Agree in substance** — Johari's Psychic Number *is* the reduced day of birth (§2.1) |
| Residence number vs **Destiny** number | Residence number vs **Birth** number, "and still more so if the person's name number is also in accord" | Different anchor; Cheiro adds a second, weaker test |
| Family-name change on marriage may hit an enemy number — check first | A woman keeps a private-life name number alongside her married/"trade" one | **Different remedies** for the same problem: Johari checks compatibility, Cheiro partitions by context |
| First letter of the name is most potent | No such rule anywhere in *Book of Numbers* | **Johari-only.** Do not attribute to Cheiro |
| Avoid 4 and 7 for business names | Avoid 4 and **8**. His 7 is *favourable* — "a magnetic number, and favourable if used by itself" (Ch. XII, `-layout` 3146–3148), and with 9 "the most important of all" for occult calculation (Ch. XI, `-layout` 2898–2901) | **Direct disagreement on 7**, and Cheiro's bad pair is 4/8 rather than 4/7. Attribute whichever you use; do not present "avoid 4 and 7" as universal |

## §11 Ayurvedic + Tantric correspondences per number

| # | Dosha | Rudraksha bead | Fasting day | Fasting food | Mantra count |
|---|---|---|---|---|---|
| 1 | Pitta | 12-mukhi | Sun | Salt-free sweet chickpea bread + milk with dates + cardamom | 7,000 per ascending moon |
| 2 | Kapha | 2-mukhi | Mon | Fruits + milk | 11,000 |
| 3 | Vata-Pitta | 5-mukhi | Thu | Chickpeas + jaggery | 19,000 |
| 4 | Vata | 8-mukhi | Sat | Salt-free millet or khichdi | 18,000 |
| 5 | Vata-Pitta | 4-mukhi | Wed | Fruits + green vegetables | 9,000 |
| 6 | Kapha-Pitta | 6-mukhi | Fri | Sweet dishes + white foods | 16,000 |
| 7 | Vata | 9-mukhi | Tue | Simple grain + herbal tea | 17,000 |
| 8 | Vata | 14-mukhi | Sat | Moong-urad khichdi with rocksalt (evening only) | 23,000 |
| 9 | Pitta | 3-mukhi | Tue | Wheat bread + jaggery + milk | 10,000 |

**Panch-dhatu (5-metal alloy)** — combines gold, silver, copper, iron, zinc; used for Rahu/Ketu/Saturn planetary rings and idols where a single metal would be karmically incompatible.

**Gem-powder (pishti) supplementation** — Ayurvedic tradition of ingesting powdered gems (Ruby → manikya pishti; Pearl → mukta pishti; Neelam → sapphire pishti) for chronic conditions. Johari cross-references his own *Healing Power of Gemstones* for full pharmacology.

## §12 Anti-exploitation guardrails

Johari's positioning throughout the book:
1. **"Do not accept information blindly"** — introduction explicitly asks readers to test rules against observation, not accept as revealed truth
2. **Numerology is general, astrology is precise** — numerology only covers "broad personality traits"; anyone selling exact predictions from numerology alone is over-reaching
3. **Gemstones require chart consultation** — never wear without verifying the planet's functional status; Blue Sapphire + Hessonite are dangerous
4. **Name changes should be checked FIRST** — a name change can break harmony (especially post-marriage adopting husband's family name) — get a numerologist's read before committing
5. **No specific-date predictions** — Personal Year gives *character of the year*, not specific event dates
6. **Residential numbers matter more than most modern practitioners admit** — before moving to a property, check house-number + street-number + city-name-number for Destiny compatibility

**Recommended user-facing guardrails (compiler's note, not from Johari):**
- Cost ceiling for name-analysis: no legitimate numerologist charges more than ₹500-2000 for a comprehensive reading; anyone quoting ₹5000+ is exploiting anxiety.
- Never change legal name based on numerology alone — the disruption cost (banking, identity, career continuity) usually outweighs any vibrational benefit.
- Numerology is a *lens*, not a replacement for medical, financial, or legal advice.
- "Master number" claims from Western sources should be flagged as tradition-specific — Johari's Vedic system reduces them.

## §12.5 Karmic Debt Numbers (Kumar Ch.1 + Ch.15)

Kumar formalises the classical **Karmic Debt Numbers** as a discrete category — Johari mentions 13/16 in passing under compound-number descriptions but does NOT treat them as a systematic category. Kumar's treatment:

**Four Karmic Debt Numbers: 13, 14, 16, 19.**

**Detection rule (Kumar):** a Karmic Debt Number applies when 13/14/16/19 appears as an **intermediate sum** during the calculation of any Core Number (Life Path, Birthday, Expression, Personality, Heart Desire) BEFORE final reduction to 1-9. Example:
- Life Path calculated as 13 → 4 carries the 13-Karmic-Debt-nature
- Life Path calculated as 22 → 4 with no 13 intermediate does NOT

**Karmic Debt vs Karmic Lesson (Kumar distinguishes these — often confused):**
- **Karmic Lesson** = area of improvement, derived from letters MISSING in name — teaches unfinished lessons
- **Karmic Debt** = burden from past-life karma, derived from 13/14/16/19 appearing in Core Number intermediates

**Traditional interpretations** (compilation from common Chaldean sources since Kumar Ch.15 not extractable):
- **13** — laziness / non-application in prior life → must learn discipline through consistent work; obstacles that force focus
- **14** — misuse of freedom / broken commitments in prior life → learn discipline through change; watch for over-indulgence
- **16** — pride / ego / hurt inflicted on others → forced humbling; may face sudden reversals; requires humility
- **19** — abuse of power / self-centered leadership → learn to lead with responsibility, not domination

**Solutions** (Kumar Ch.15 not extractable — book states "For every Karmic Debt Number there is a solution which helps you to reduce your Burden"). Common numerological remedies include: awareness practice (naming the pattern reduces its grip), conscious opposite-action (13 → discipline; 14 → commitment; 16 → humility; 19 → service-leadership), mantra + charity per corresponding planet (see §11).

**Framing (Kumar Ch.xxi):** Karmic Debt is presented as an opportunity for growth in this life, NOT as an unavoidable curse. Native has agency to reduce the burden through conscious life-choices.

## §12.6 Challenge Number (Kumar Ch.16 — sample only)

**Concept:** life divides into 4 long-term cycles (unequal duration, based on DOB). Each cycle has a Challenge Number indicating the specific difficulty the native must work through.

**Kumar's framing:** "For many of us, the same challenge is repeated. Others have four distinctly different lessons to learn." Challenge Number must be analyzed alongside Life Path Number for the specific period.

**Formula:** Kumar sample lists inputs as "various combinations of Birth dates (dd/mm/yyyy)" but the specific formula is in Ch.16 (not extractable). Standard Chaldean formula documented across sources:
- **1st Challenge** = |month reduced − day reduced|
- **2nd Challenge** = |day reduced − year reduced|
- **3rd Challenge** = |1st challenge − 2nd challenge|
- **4th Challenge** = |month reduced − year reduced|

**Per-challenge interpretations** (Kumar Ch.16 not extractable). Standard compilation:
- **Challenge 1** — need to develop confidence, leadership, individuality
- **Challenge 2** — need to develop cooperation, patience, sensitivity to others
- **Challenge 3** — need to develop self-expression, discipline, focus
- **Challenge 4** — need to develop consistency, work ethic, practical structure
- **Challenge 5** — need to develop freedom-with-responsibility, adaptability
- **Challenge 6** — need to develop nurturing without martyrdom
- **Challenge 7** — need to develop trust, spiritual grounding, avoid isolation
- **Challenge 8** — need to develop material discipline, honest power
- (No Challenge 9 in classical system — 9 is completion, not challenge)
- **Challenge 0** — spiritual/karmic pattern from prior lives, transcend all lower challenges

## §12.7 Pinnacle Number (Kumar Ch.17 — sample only)

**Concept:** parallel to Challenge but represents **opportunity** rather than difficulty. Four Pinnacle cycles corresponding to same 4 life-periods.

**Kumar's framing** (Ch.1): "Each Pinnacle cycle brings demand and opportunity to you. It forces you to deal with qualities of that pinnacle number. Overall, each Pinnacle cycle shapes you and your life."

**Formula** (Kumar Ch.17 not extractable). Standard Chaldean:
- **1st Pinnacle** = month + day reduced
- **2nd Pinnacle** = day + year reduced
- **3rd Pinnacle** = 1st + 2nd reduced
- **4th Pinnacle** = month + year reduced

**Cycle boundaries** (traditional):
- 1st Pinnacle: birth → age (36 − Life Path)
- 2nd Pinnacle: 9 years after 1st ends
- 3rd Pinnacle: 9 years after 2nd ends
- 4th Pinnacle: rest of life

**Per-pinnacle interpretations** (Kumar Ch.17 not extractable — parallels per-number Character traits from Johari §4).

## §12.8 Personal Year Number (Kumar Ch.18 — divergence from Johari §9)

**Kumar's formula** (Ch.1, calculation-inputs table): `birth_month + birth_date + universal_year` (all reduced).

**Johari's formula** (§9 above): `birth_month + birth_date + last_two_digits_of_year + weekday_number_of_birthday_this_year` (all reduced).

**Divergence:** Kumar uses **full 4-digit universal year**, Johari uses **last 2 digits + weekday number**. Both produce the same range (1-9). Kumar's is more common in modern practice; Johari's is more granular.

**Example — May 12 native, target year 2026:**
- Kumar: 5 + 12 + 2026 = 2043 → 2+0+4+3 = 9 → **Personal Year 9**
- Johari: 5 + 12 + 26 + (May 12 2026 = Tuesday = 9) = 52 → 5+2 = 7 → **Personal Year 7**

**Recommended:** show Kumar's method by default (simpler, more common), offer Johari's method as an optional "Vedic mode". Note the different results and let user choose.

**Implemented as of #169:** `_personal_year()` ships Kumar's method — birth month + birth day + target year — and reduces **fully to 1–9** (`preserve_masters=False`). Masters are not preserved because both formulas above are stated with a range of 1–9, and the panel that renders this captions itself "Cycles 1–9"; an 11 or 22 escaping into it would label a row the range says cannot exist. Any 11/22/33 row in `_PERSONAL_YEAR_THEME` is therefore unreachable — `_personal_year()` cannot return those values — and is dead code dropped under #169.

**Formula variant, and why it is not a divergence:** the code sums the *digits* of the month, day and target year, where Kumar writes the literal `month + day + year`. Under full reduction the two are provably identical, since a digit sum is congruent to its value mod 9. Measured across all 18,972 (month, day-of-month, target-year 2000–2050) combinations: zero disagreements. Preserve masters and they *do* diverge — 2,476 of the same 18,972 combinations — which is a second, independent reason the reduction here goes all the way to 1–9.

**9-year epicycle** (Kumar Ch.1): Life unfolds in 9-year cycles. Year 1 = new beginning, Year 9 = completion. Full cycle should be viewed together for arc.

**Kumar also mentions Personal Month and Personal Day** as computable — formulas in Ch.18 not extractable. Standard compilation:
- **Personal Month** = Personal Year + current calendar month, reduced
- **Personal Day** = Personal Month + current calendar day, reduced

## §12.9 Essence Cycle Number (Kumar Ch.19 — sample only)

Kumar's Ch.1 definition: "Combined total of Physical, Mental, and Spiritual Transits influencing you during a particular year of your life. Based on your name and current age."

**Kumar's positioning:** "When you want to know at age 24 how the timing will be, you must analyze Essence number for age 24 along with Personal Year number." — meaning Personal Year alone is insufficient; both are needed for a full-year forecast.

**Formula** (Kumar Ch.19 not extractable). Standard Chaldean method:
- Compute how many years each letter of your full name "activates" (letter value = years of activation, cycled through name repeatedly)
- At any given age, sum the currently-active-letter values
- Reduce to single digit or Karmic Debt / Master

**Not implemented on this site initially** — requires deep name-based transit computation. Deferred until Kumar's Ch.19 becomes available or a proxy source is added.

## §13 Gaps in source

### 13.1 Kumar fills these Johari gaps:
- **Karmic Debt Numbers as systematic category** (§12.5) — 13/14/16/19 detection rule in Core-Number intermediates
- **Karmic Lesson Numbers** (§2.5) — missing letters in name = areas of improvement
- **Hidden Passion Numbers** (§2.5) — most-frequent letter = concentrated talent
- **Challenge Numbers** (§12.6) — 4 life-cycles of difficulty
- **Pinnacle Numbers** (§12.7) — 4 life-cycles of opportunity
- **Essence Cycle Numbers** (§12.9) — age-based name transits
- **Personal Month + Personal Day** cycles (§12.8) — finer time-granularity than Johari's Personal Year alone

### 13.2 Still missing from both books:
- **Lo Shu grid / magic-square numerology** — Chinese tradition; different provenance; would need separate source (e.g. Feng Shui texts)
- **Explicit business-name numerology scoring formula** — Johari implies per-number ranges; Kumar mentions in Ch.19 but not extractable
- **Compatibility numeric scoring** — Johari provides per-pair descriptive text (see §7); no numeric scoring formula in either book
- **Kumar's per-number chapter details (Ch.3-11)** — Johari's per-number section (§4) covers this alternative

**Cheiro closes two of these** — name numerology in depth, and the compound series as
interpretation rather than a bare table. He does **not** close Lo Shu or numeric
compatibility scoring; see §13.3 and §14.7.

### 13.3 If implementing Lo Shu or business-name scoring:
Cite a separate source (Cheiro's *Book of Numbers* for extended compound numbers; Feng Shui texts for Lo Shu grid) and mark clearly in the article footer.

**Cheiro cannot be that source for Lo Shu.** Measured across the whole 14,183-line plain extract of *Cheiro's Book of Numbers*: `Lo Shu` **0**, `magic square` **0**, `Feng Shui` **0**, `Rudraksha` **0**. Adding Cheiro to `data/` does not close the Lo Shu gap, and no reading may cite him for it. He *does* close the extended-compound gap and the name-numerology gap — see §14.

---

## §14 Cheiro — name numerology, periods, and the practical apparatus

Source: Cheiro, *Cheiro's Book of Numbers* (Herbert Jenkins, London), 33 chapters over 194
PDF pages. Line numbers below are **`pdftotext -layout`** (8,389 lines); the plain extract
is 14,183 lines and numbers differently, so the flag is part of the citation. Printed page
numbers are given where a page image was consulted; **PDF page = printed page + 1**.

### 14.0 Reading this source — the OCR is actively misleading

This is a 1920s bitonal scan and its text layer fails in ways that do not look like
failures. Anyone extending this section must know three specific traps:

1. **The alphabet page silently truncates.** Both `pdftotext` modes drop rows A–M and
   render `Y = 1` as `Y = I`, leaving a plausible-looking N–Z table with no error marker.
   See the warning box in §3.2.
2. **Prose carries systematic substitutions**: `i8th` for `18th`, `m` for `in`, `ongm` for
   `origin`, `VWTH` for `WITH`, `Bnrth` for `Birth`. These are recoverable by eye in prose
   but silently corrupt any numeral.
3. **Chapter headings are misnumbered in the text layer.** `-layout` line 3389 reads
   "CHAPTER XI" but is Chapter XIII (printed p.78, matching the table of contents). Locate
   chapters by the printed page number in the running head, not by the OCR'd numeral.

**Rule for this section: prose may be quoted from the text layer; every table and every
numeral in §14 was read off a rendered page image** (`pdftoppm -f <page> -l <page> -r 200
-png`). Pages verified this way: 31, 33, 34, 71, 75, 89, 92, 39, 48. Where a figure could
not be verified it is marked and not used.

The source also has genuine errors of its own, independent of the scan: printed p.30
says "the whole of the **13** Signs of the Zodiac", which is on the page, not an OCR
artefact. Treat Cheiro as an authority on his own system, not on astronomy.

### 14.1 The two numbers and what each governs

This is the frame everything else in §14 hangs off, and it is sharper than anything in
Johari:

| | Cheiro's term | What it governs | Alterable? |
|---|---|---|---|
| **Birth number** | day-of-month digit, reduced | "the material side of life" | No |
| **Name number** | letters of the most-used name | "the more occult or spiritual side of our existence" | **Yes** |

> "the Birth number relates to the material side of life, the Name number to the more
> occult or spiritual side of our existence" — Ch. XV, `-layout` 4050–4052.

Crossing that is a second axis, **single vs compound**, which applies to *both*:

> "The single number of a name, it must be remembered, represents the man or woman as they
> appear to be. The 'double' or 'compound' number represents the hidden forces that use the
> man or woman as their instrument." — Ch. XII, `-layout` 3216–3219.

He restates it as "numbers of individuality and personality" for the singles, versus
numbers that "show the hidden influences that play their role behind the scenes… and in
some mysterious way often foreshadow the future" for the compounds (Ch. XIII, `-layout`
3409–3415, 3443–3446).

**So a full Cheiro reading has four cells, not two**: birth-single, birth-compound,
name-single, name-compound. `/numerology` currently renders three of them — Birthday Number
(birth-single), Name Number (name-single) and Name Compound Number. The gap is
**birth-compound**, the unreduced day of month, which §5 holds as Johari's 10–31 birthdate
series and which the template does not surface. Noted as an observation, not a request.

Cheiro's term for the final reduced digit is the **"spirit or soul number"** of all the
numbers added together, and his term for the reduction itself is **"natural addition, from
left to right"** (Ch. II, `-layout` 1369–1375).

**Which number wins.** Cheiro is unambiguous, and it is not the answer a name-focused
product would prefer: the **Birth number is the more important**, and he devotes a whole
chapter to why (Ch. XV, "Why the Birth Number is the Most Important"). Three reasons,
`-layout` 4039–4049: it is unalterable; it is fixed by the planet's influence at the moment
of birth; and the moment of birth "decides the note of harmony or vibration" for life. He
adds a fourth, practical reason that matters more than the metaphysics — see §14.2's
honesty clause.

### 14.2 Name numerology in depth (Cheiro's central contribution)

#### Which name to use

The governing rule, stated as an answer to a reader question:

> "it is the **most used** Christian and Surname that must be added together to give the
> Key-number; when the Surname is more used or more in evidence than the Christian name,
> then it is taken to give the Key number" — Ch. XII, `-layout` 3107–3114 (verified on the
> rendered image of PDF p.72).

Consequences he spells out explicitly, all from Ch. XXI (`-layout` 5109–5156):

- **Titles and prefixes count** when the person is habitually addressed with them. Mr, Mrs,
  Miss, Sir, Dame, and inherited or honorary titles are all part of the name if that is how
  the person is called.
- **Multiple given names**: "When a man or woman has many Christian names, they should only
  take the number made by the principal one that they are most known by."
- **A person can legitimately hold two name numbers at once.** A woman always addressed as
  "Miss Jones" at work should compute and use "Miss Jones" — Cheiro calls it her "trade
  name" — "**but only in relation to the business she is employed in**", while for "her home
  life or her private affairs she should work out the Christian name she is called by or the
  'pet' name she is known under." On marriage she recomputes for the new title, "but always
  keeping the numbers of her Christian or 'pet' name for her home and private life."
- **Regnal and generational suffixes count.** Napoleon = compound 41, single 5; as Emperor
  the name became "Napoleon I", adding 1 to make 42 / single 6 — both fortunate. "Napoleon
  III" makes 44 / single 8, which Cheiro's own compound table calls a number "of the gravest
  warnings… disasters brought about by association with others" (Ch. XXI, `-layout`
  5198–5222).
- **A title that reduces to 4 or 8 cancels the name's luck**: "In cases where the addition
  of the number of the title produces a 4 or an 8, it foreshadows that the fortunate
  numbers of the name have ceased their luck or power, and in such cases the title will
  become a detriment and not a happiness" (`-layout` 5193–5197).

**Nothing here is about the birth-certificate name.** Cheiro never asks for it. The input
is sociological — what are you actually called — which is why he treats the Name number as
the *changeable* one.

#### How a name is scored: word by word, then combined

Cheiro does **not** sum all the letters in one pass. Each word of the name gets its own
compound and single number; those are read individually; only then are the singles added to
give the whole-name number. Worked examples, all from Ch. XII:

- **Lloyd George** — "Lloyd" alone = 18 = 9, "George" alone = 25 = 7; the two singles
  added, 9 + 7, give the whole-name compound **16** (`-layout` 3139–3155). He then reads
  "Lloyd" and "George" *separately* as well: Lloyd's 18 carries the rayed-moon symbol,
  George's 25 is "strength gained by experience" (`-layout` 3191–3202).
- **Austen Chamberlain** — AUSTEN = 24 = 6, CHAMBERLAIN = 32 = 5, and with the title,
  Sir 6 + Austen 6 + Chamberlain 5 = 17 (`-layout` 3243–3288; letter values verified on the
  rendered image of PDF p.75).
- **Ramsay MacDonald** — Ramsay = 12 = 3, MacDonald = 32 = 5; singles 3 + 5 = 8; compounds
  12 + 32 = **44** (`-layout` 3301–3357).

Note the arithmetic in the last one: he adds the two *compound* numbers to get a whole-name
compound (12 + 32 = 44), while adding the two *singles* to get the whole-name single
(3 + 5 = 8). These are different reductions of the same name and he uses both.

**The interpretive payoff of doing it word by word** is the whole reason for the method: it
lets him say which *part* of a name is carrying the trouble. On Lloyd George — "if Lloyd
George had become known in the world as plain George he would have retained to the end the
high position he had gained" (`-layout` 3203–3206). On Ramsay MacDonald — "he would never
have allowed his party or his public to call him by the single word Ramsay… but insisted on
being called, if he could do it, by the single word MacDonald with its magical number of
32" (`-layout` 3367–3373).

This is the single most product-relevant idea in the book: **the actionable advice is
usually "change which part of your name people use", not "change your name".**

#### Name–Birth harmony, and the correction rule

> "If possible, make the Birth number and the number given by the Name agree; the vibrations
> will then all be in harmony, and will give a greater promise of success if the number is a
> favourable one." — Ch. XIV, `-layout` 3829–3832.

When they disagree, Cheiro describes the lived symptom rather than a doom: the two numbers
"would not be in vibration one to the other, and there would always be a muddle or jumble in
his affairs, and he would also not be able to decide which number to act on or what date he
should use" (`-layout` 3862–3868).

**The correction, verified on the rendered image of PDF p.89 / printed p.88:** since the
Birth number cannot be altered, alter the Name number — and the instrument is *adding a
middle initial*, not renaming. His worked case: "John Smith" = 17 = 8. Adding an initial
worth 3 (C, G, L or S) gives "John C. Smith" = 20 = 2, which then matches a birth number of
2 (2nd, 11th, 20th, 29th). The condition attached is behavioural, and he repeats it: the
person must insist "on being known and called as that" (`-layout` 3869–3882).

**The exceptions, both stated:**
- If the Name number already matches the Birth number, **do not change it**, even when the
  shared number is an unlucky one. "If, however, 'John Smith' was born under an 8… as the
  total of the numbers of his name also make an 8, I would then not advise him to add a
  letter or change the Name number, but to work under the 8" (`-layout` 3883–3887). Accord
  outranks favourability.
- If Birth is 4 and Name is 8, or Birth is 8 and Name is 4, change the name **away from
  both** — see §14.7.

He also gives the escalation ladder for advanced cases: "Those who are advanced students in
occult symbolism can utilise the hidden meaning given by both Christian and surnames to work
out the finer shades of destiny", but for ordinary readers he recommends the Birth number
rules (Ch. XV, `-layout` 4087–4098).

#### Cheiro's own honesty clause about the Name number

This is worth quoting in full because it is the most useful qualification in the book, and
it is the *real* reason he ranks the Birth number first:

> "Also the Name number is more difficult to be sure of; it must be the product of the name
> we are most known by. This presents a problem for the average man or woman. Many men are
> more known by their surnames than by their Christian and surname together, and many women
> are called by some 'pet' name to the complete extinction of their Christian name. In
> working out such cases mistakes may easily be made and a number allotted which is not the
> true one, whereas by going by the Birth number… no mistake can be made."
> — Ch. XV, `-layout` 4053–4066.

And the corollary, which is a genuinely useful confidence signal: if the name you think is
the right one produces the same number, or any degree of the same number, as the Birth
number, "then one can be absolutely certain that no mistake is being made" (`-layout`
4067–4079). **Agreement between the two numbers is evidence you picked the right name.**

#### Changing the spelling changes the number

Cheiro's example is Napoleon dropping the `u`: "Buonaparte" scored 5, "Bonaparte" scored 8,
and he reads the change as consequential (Ch. XVI, `-layout` 4130–4153). The general point
for our purposes: **transliteration choices are not cosmetic.** Sanjay/Sanjai, Shubh/Subh,
Lakshmi/Laxmi are different name numbers under this system. Any name feature we ship must
say which spelling it scored.

### 14.3 Reading the compound numbers 10–52 (interpretation, not the table)

The 43-row table is already in §5.1 from #160 and is **not** repeated here. What §5.1 does
not carry is how Cheiro says the rows are meant to be *used*:

- **The compounds are a different plane of meaning, not finer-grained singles.** "The
  meanings ascribed to the numbers 1 to 9 belong then to the *physical or material* side of
  things, and 'compound' numbers from 10 on belong to the more occult or spiritual side of
  life" (Ch. XIII, `-layout` 3459–3462).
- **A compound is read alongside its own root, never instead of it.** For 12 he notes the
  root is 3, "but at the same time the 1 and 2 of which the twelve is composed are
  'compound' and have a meaning of their own **distinct from** the number 3" (`-layout`
  3447–3452). A reading that reduces 12 to 3 and stops has thrown away the compound layer.
- **The 10–52 bound is cosmological, not arbitrary.** 5 × 9 = 45, plus the mystic 7 = 52,
  "which stands for the 52 weeks of a year" (`-layout` 3416–3427). Explains why our
  `compute()` clamp is what it is.
- **The symbols are pictorial and Tarot-adjacent.** "The universally accepted symbolism of
  the compound numbers in ancient times was given in pictures and may still be found in the
  Tarot Cards" (`-layout` 3477–3482). This is why the rows read as images ("a Shattered
  Citadel", "the Wheel of Fortune") rather than adjectives — the picture is the content, and
  paraphrasing it away loses the row.
- **A compound modifies, it does not overrule.** On 15: "If this number is associated with a
  good or fortunate single number, it can be very lucky and powerful" (Ch. XXI, `-layout`
  5162–5167). The compound's verdict is conditional on its single.
- **He applies compounds to non-persons too** — ships, cities, institutions — with the same
  table (Ch. XVI, `-layout` 4173–4207).

### 14.4 The "lucky day" method

This is the mechanism the compound table was built to serve, and it is a concrete algorithm
(Ch. XIII, `-layout` 3764–3784, with the worked example at 3786–3818):

1. Take the **Name number** (compound, or its single digit).
2. Add the **Birth number**.
3. Add the digit-sum of the **candidate date** (26 April → 2 + 6 = 8).
4. Look up the resulting **compound** number in the 10–52 table.
5. If it is unfavourable, try the next day, and the next, "until you come to a date that is
   indicated as favourable".

Worked: John Smith (name 17 → 8), born 8 January (birth 8), asking about 26 April (8).
8 + 8 = 16 → 7; 7 + 8 = 15. Compound 15 is favourable "for obtaining money, gifts, and
favours from others", so the date is a good one to ask for a raise.

⚠️ *Text-layer discrepancy, resolved:* the restatement at `-layout` 5425 reads "it is
unfortunate number" where the original at 3811–3812 reads "it is a fortunate number". The
surrounding sentence in both places concludes the date **is** favourable, so 5425 is a
dropped-character OCR artefact, not a contradiction. Cite 3811.

**Cheiro's own limit on this method** — and it is a real one, stated by him unprompted:

> "This was given only as an illustration of finding out if one particular date would be
> likely to be favourable for that special purpose, but I never intended this to be employed
> to the exclusion of the other definite rule for continual action all through the year on
> the series given by the Birth number… in the 'John Smith' case another life, namely the
> employer, is concerned, and in consequence the rule given would not work out with such
> certainty." — Ch. XXII, `-layout` 5428–5446.

That is: **the date calculation is a one-off tool for a specific ask, it degrades when
another person's chart is involved, and it does not replace the standing birth-series
rule.** Any product surfacing lucky dates should inherit that caveat rather than present
the output as flat fact.

### 14.5 Zodiac number-periods and weekday numbers

**Both tables below were read off rendered page images** (PDF pp.31, 33 and p.34 = printed
pp.30, 32, 33), Ch. I.

| Sign | Dates | Ruler (Cheiro) | Number |
|---|---|---|---|
| Aries | 21 Mar – 19 Apr | Mars, positive | 9 |
| Taurus | 20 Apr – 20 May | Venus, positive | 6 |
| Gemini | 21 May – 20 Jun | Mercury, positive | 5 |
| Cancer | 21 Jun – 20 Jul | Moon, positive | 2–7 |
| Leo | 21 Jul – 20 Aug | Sun, positive | 1–4 |
| Virgo | 21 Aug – 20 Sep | Mercury, negative | 5 |
| Libra | 21 Sep – 20 Oct | Venus, negative | 6 |
| Scorpio | 21 Oct – 20 Nov | Mars, negative | 9 |
| Sagittarius | 21 Nov – 20 Dec | Jupiter, positive | 3 |
| Capricorn | 21 Dec – 20 Jan | Saturn, positive | 8 |
| Aquarius | 21 Jan – 21 Feb | Saturn, negative | 8 |
| Pisces | 19 Feb – 20 Mar | Jupiter, negative | 3 |

Two rules attached:

- **Positive vs negative is physical vs mental**, not good vs bad. "the Positive giving the
  more physical and forceful qualities, the Negative the mental." His illustration: 9
  positive (Aries) is "a man in armour with his visor closed and a naked sword in his hand";
  9 negative (Scorpio) is the same man "with the visor up showing his face, and the sword in
  its sheath, giving the picture of the mental warrior rather than the physical" (`-layout`
  1293–1304).
- **The cusp is seven days at each end.** "seven days are allowed at the beginning of each
  sign and seven days at the end, which is called the 'Cusp of the Sign'; during this period
  the number of the month and the qualities it represents are not quite so strong… and
  partakes to a certain extent of the qualities of the Sign which is passing away with those
  of the one that is coming into action" (`-layout` 1283–1292). **This explains the
  otherwise-baffling date ranges elsewhere in the book** — "21st March to April 19th–26th",
  "21st July to the 28th August" are the same periods with the cusp added, and Cheiro
  footnotes this himself at `-layout` 1353–1355.

**Weekday numbers** (image-verified, printed p.33):

| Day | Number |
|---|---|
| Sunday | 1–4 |
| Monday | 2–7 |
| Tuesday | 9 |
| Wednesday | 5 |
| Thursday | 3 |
| Friday | 6 |
| Saturday | 8 |

**Compared against Johari §3.3, the weekday numbers agree on seven of nine and diverge on
exactly the two numbers whose planet differs** — which is a good independent check on both
tables:

| # | Johari's day (§3.3) | Cheiro's day | |
|---|---|---|---|
| 1 | Sun, Mon | Sunday | agree |
| 2 | Mon | Monday | agree |
| 3 | Thu | Thursday | agree |
| **4** | **Sat** | **Sunday** (via the 1–4 pair) | **diverge** — Rahu/Saturn vs Uranus/Sun |
| 5 | Wed | Wednesday | agree |
| 6 | Fri | Friday | agree |
| **7** | **Tue** (some Sun) | **Monday** (via the 2–7 pair) | **diverge** — Ketu vs Neptune/Moon |
| 8 | Sat | Saturday | agree |
| 9 | Tue | Tuesday | agree |

The two divergences fall precisely on 4 and 7, the two numbers where §3.1 records
Rahu/Ketu against Uranus/Neptune. Neither table is wrong; they are two consistent
derivations from different planetary assignments. Attribute rather than merge.

### 14.6 Per-number colours, days, stones, and periods (Cheiro)

This is a parallel set to Johari's §3.3 and §11, **from a different tradition, and it does
not agree with them.** It is recorded here so a reading can cite either deliberately. Prose
from the text layer; the two rows spot-checked against images are marked ✓ (printed pp.38
and 47).

| # | Lucky colours | Lucky stones | Best weekdays | Strong periods |
|---|---|---|---|---|
| 1 ✓ | All shades of gold, yellow, bronze to golden brown | Topaz, amber, yellow diamond; wear amber next the skin | Sunday, Monday | 21 Jul – 28 Aug; 21 Mar – 28 Apr |
| 2 | All shades of green (darkest to lightest), cream, white; **avoid** black, purple, dark red | Pearl, moonstone, pale green stones; carry jade next the skin | Sunday, Monday, Friday | 20 Jun – 27 Jul |
| 3 | Mauve, violet, purple (also in the rooms they live in); blue, crimson, rose as secondary | Amethyst, worn next the skin | Thursday (chief), Friday, Tuesday | 19 Feb – 20/27 Mar; 21 Nov – 20/27 Dec |
| 4 ✓ | "Half-shades", "half-tones", "electric colours"; electric blues and greys best | Sapphire, light or dark, next the skin | Saturday, Sunday, Monday | 21 Jun – 20/27 Jul; 22 Jul – end Aug |
| 5 | Light grey, white, glistening materials; light shades generally, dark as rarely as possible | Diamond (set in platinum, next the skin), platinum and silver | Wednesday, Friday | 21 May – 20/27 Jun; 21 Aug – 20/27 Sep |
| 6 | All shades of blue, all shades of rose or pink; **avoid** black and dark purple | Turquoise (or turquoise matrix) next the skin; emerald also lucky | Tuesday, Thursday, Friday | 20 Apr – 20/27 May; 21 Sep – 20/27 Oct |
| 7 | All shades of green, pale shades, white and yellow; avoid heavy dark colours | Moonstone, cat's-eye, moss agate next the skin | Sunday, Monday (as for 2) | 21 Jun – 20/27 Jul, less strongly to end Aug |
| 8 | Dark grey, black, dark blue, purple — light colours make them "look awkward" | Amethyst, dark-toned sapphire, black pearl, black diamond | Saturday (chief), Sunday, Monday | 21 Dec – 20/27 Jan; then to 19/26 Feb |
| 9 | All shades of crimson and red, rose tones, pink | Ruby, garnet, bloodstone, next the skin | Tuesday (chief, "Mars Day"), Thursday, Friday | 21 Mar – 19/26 Apr; 21 Oct – 20/27 Nov |

`-layout` citations, in order: 1 → 1445–1469; 2 → 1573–1608; 3 → 1705–1739; 4 → 1876–1901;
5 → 1976–2040; 6 → 2160–2177; 7 → 2349–2373; 8 → 2512–2534; 9 → 2877–2897.

**Divergences from Johari's §3.3 worth flagging in any reading that uses one of them:**

| # | Johari's gem | Cheiro's stone | Note |
|---|---|---|---|
| 1 | Ruby | Topaz / amber / yellow diamond | Cheiro gives ruby to **9**, not 1 |
| 3 | Yellow sapphire | Amethyst | Both Jupiter-ruled; different stone |
| 4 | Hessonite (Gomed) | Sapphire | Follows from Rahu vs Uranus |
| 7 | Cat's-eye (Lehsunia) | Moonstone / cat's-eye / moss agate | Partial agreement |
| 8 | Blue sapphire | Amethyst / dark sapphire / black pearl | Partial agreement |

**Colour agreement is much better than gem agreement.** Both give 1 gold/yellow, 2
white/cream, 6 blue and rose/pink, 8 dark grey/black/dark blue/purple, and 9 red/crimson/
pink — five of nine substantially aligned. The real colour divergences are 3 (Cheiro
mauve/violet/purple; Johari yellow/gold/orange), 5 (Cheiro light grey/white; Johari light
green/turquoise) and 7 (Cheiro green/white/yellow; Johari iridescent green-blue/
mother-of-pearl). Gems, by contrast, agree on almost nothing. **Do not present these as one
merged list**, and do not assume that because the colours line up the stones will.

#### The month-colour vs day-colour rule

A genuinely useful disambiguation Johari does not supply. A person born 6 January has a
day-number of 6 but falls in the "period of the 8". Which colours?

> "employ most decidedly in such a case the colours of the number 6 as the principal,
> individual, and 'lucky' colours to use, but as the person was born in the 'period of the
> 8' he or she can use, if they wish, **but as secondary colours**, those given by the
> number 8." — Ch. XXIII, `-layout` 5510–5521, restated 5555–5563.

The stated reason: "the number of the month is not as close or intimate in its relationship
to the individual as is the colour indicated by the number of birth" (`-layout` 5455–5460).
**Day-of-birth colours are primary; month-period colours are secondary.** The same
precedence should govern any month-vs-day conflict, not just colours.

### 14.7 Compatibility: Cheiro's group system

Cheiro does **not** work from a per-pair friend/enemy grid the way Johari's §7 does. He
works from three "interchangeable" groups plus a doctrine about 4 and 8:

| Group | Members | Basis |
|---|---|---|
| Sun family | **1, 2, 4, 7** | 1–4 (Sun/Uranus) and 2–7 (Moon/Neptune) are "interrelated"; the two pairs are mutually sympathetic |
| Jupiter/Venus/Mars family | **3, 6, 9** | stated as the interchangeable set for each of the three |
| 5 | **all numbers** | "Number 5 people make friends easily and get on with persons born under almost any other number, but their best friends are those born under their own number" |
| 8 | **4** (its own interchangeable), plus Saturday/Sunday/Monday | but see the 4-and-8 warning below |

Citations: 1's set (2, 4, 7) `-layout` 1453–1463 ✓image p.38; 3's set (6, 9) 1718–1726;
4's set (1, 2, 7) 1885–1888 ✓image p.47; 5 1983–1986; 6's set (3, 6, 9) 2161–2164; 7's set
(1, 2, 4) 2360–2363; 8's set (4) 2528–2530; 9's set (3, 6) 2892–2894. The explicit 1–4 /
2–7 sympathy statement is Ch. II, `-layout` 1338–1352.

**This is a real methodological divergence from Johari, not a detail.** Johari's §7 is
directional and pairwise, with friend/enemy/neutral verdicts per pair and documented
asymmetries (6↔5, 3↔7, 4↔3). Cheiro's is a symmetric three-family partition with **no enemy
category at all** — the closest he comes is the 4-and-8 combination, which is a warning
about *repetition in one life*, not about two people. A matching feature must pick one
system and say which; blending them produces verdicts neither author supports.

Checked pair by pair against §7, the two systems agree more than the different method
suggests, and where they disagree they disagree sharply:

**Where they agree —**
- **The 3–6–9 family is unanimous.** All three pairs (3↔6, 3↔9, 6↔9) are friendly in
  Johari's list *and* appear in his "best marriages" cluster, and all three are Cheiro's
  interchangeable set. Two traditions, same triad.
- **4 + 8 is the danger pair in both.** Johari: "8 ↔ 4 (both bring difficulty)", filed under
  Enemy. Cheiro: the entire §14.8 doctrine. This is the strongest convergence in the whole
  comparison and the one place a reading can say "both traditions agree" without hedging.
- 1↔2, 1↔4, 1↔7 and 2↔7 are friendly in Johari and inside Cheiro's Sun family.

**Where they contradict —**
- **4 ↔ 7.** Cheiro puts both in the same family and lists each as the other's
  interchangeable number (`-layout` 1885–1888, 2360–2363). Johari files it under Enemy:
  "7 ↔ 4 (mutual attraction with instability)". **Flat contradiction on a pair that a
  matching feature will hit often.**
- **The number 5.** Cheiro's 5 is the universal friend — "gets on with persons born under
  almost any other number". Johari's 5 is the *most-enemied* number in §7, in friction with
  2, 3, 4, 7, 8 and 9. These are opposite characterisations of the same number and cannot
  both drive one verdict.
- **2 ↔ 4.** Harmonious for Cheiro (same family); neither friend nor enemy for Johari, so
  neutral by §7's default. A mild divergence, noted for completeness.

Both systems are internally consistent; they start from different planets (§3.1) and from
different methods (groups vs directed pairs). **Record which one a verdict came from.**

### 14.8 The 4-and-8 doctrine

Cheiro's one systematic negative rule, and the exception to every other rule he gives.

The general instruction for everyone else is to **concentrate on your own number** — think
of yourself as that number, act on dates that make it, live at addresses that make it (Ch.
XXIV, `-layout` 5577–5639). For 4 and 8 he inverts it:

> "In the latter cases I recommend, then, **not to increase** the peculiar influence of the
> 4 and 8, but to choose more fortunate vibrations." — Ch. XV, `-layout` 3996–3999
> (✓ verified on the rendered image of PDF p.92 / printed p.91).

The escape route is precisely the Name number, which is why this belongs in a name section:

> "This is where the power and knowledge of the Name number will apply. A number 4 or a
> number 8 person who desires to get under more fortunate vibrations, as they cannot alter
> their Birth number they can at least **change their Name number** and live under it and so
> become equally as fortunate as those whose Birth number is a lucky one." — `-layout`
> 4000–4005 ✓image.

Attached rules:

- **The house/address rule.** A person whose Birth number makes an 8 should not live at an
  address reducing to 4, and one whose Birth number makes a 4 should not live at an address
  reducing to 8 — "not, at least, if they wish to escape sorrow, misfortune, and strange
  fatality" (Ch. XV, `-layout` 3973–3980 ✓image p.92; restated Ch. XIV `-layout` 3917–3926,
  which adds that country dwellers should *name* the house to produce the right number).
- **4 alone is not the problem; the 4-8 pairing is.** "The 4 in itself and all its series is
  not so much to be dreaded… It is only when the combination of the 4 and 8 are continually
  cropping up that those born under such numbers should do their utmost to avoid them"
  (Ch. XXVI, `-layout` 5772–5789). A 4-born person is advised to lean on 1 instead, since
  4 belongs to the 1–4 series.
- **Wear the colours and jewels of the new number**, not the old (Ch. XIV, `-layout`
  3910–3916).

⚠️ **An internal contradiction in the source, verified on both page images — do not
silently pick one.** Cheiro names the "more fortunate" targets to change a name toward
twice, and the lists differ:

| Chapter | Printed page | Target numbers | Image verified |
|---|---|---|---|
| XIV | p.88 | "a 1, 3, 6, or 9" | ✓ PDF p.89 |
| XV | p.91 | "a 1, 3, 5, or 6" | ✓ PDF p.92 |

Chapter XV then explains the omission of 9 — 4 (Uranus) and 8 (Saturn) are "so antagonistic
in their qualities to the 9, the symbol of Mars… that it is better to keep such numbers
apart" (`-layout` 4017–4038). That reasoning is specific to 4-and-8 people and postdates the
Ch. XIV list, so **for 4/8 name correction the Ch. XV list (1, 3, 5, 6) is the one with a
stated argument behind it**; the Ch. XIV list should be treated as superseded rather than
as an alternative. Both are on the page; neither is an OCR artefact. Ch. XXV restates
1, 3, 5, 6 (`-layout` 5735–5737), which corroborates XV.

### 14.9 Place, house and city numbers

Same alphabet, same reduction, applied to a place name; a place is fortunate for you when
its single number matches your Birth number, "and still more so if the person's name number
is also in accord" (Ch. XXIX, `-layout` 6299–6314). His worked example, MANCHESTER = 37 =
10 = 1, is arithmetically consistent with the image-verified alphabet, as are GEORGE = 25,
WASHINGTON = 40 and LEEDS = 20 elsewhere — which is the cross-check cited in §3.2.

Members of the 1, 2, 4, 7 group have the widest choice, since any place reducing to any of
those four will serve (`-layout` 6345–6353).

**Do not ship the specific city lists.** Cheiro's examples ("Birmingham, Boston, New York,
Alexandria, Whitechapel" for number 1) are period-specific and unremarkable, and the method
reproduces them in one line of arithmetic. The rule is the content; the list is not.

### 14.10 How Cheiro says a reading should be delivered

He is unusually explicit about this, and the guidance is directly usable as product copy
constraints:

- **Expect months, not days.** "when people begin to follow this idea, they must not expect
  to find their luck change in an instant, as if by magic." His cited case: a correspondent
  who reported no change after a week, then wrote again to report distinct improvement
  "towards the middle of the third month" (Ch. XXII, `-layout` 5400–5409; restated Ch. XXV,
  `-layout` 5751–5757). **Any name-change or lucky-number advice we surface should carry a
  months-long horizon, not an immediate promise.**
- **Say when a rule is weaker.** See the §14.4 quote — he flags that his own date method
  loses certainty once another person is involved.
- **Say when a number is hard to be sure of.** See §14.2's honesty clause on the Name
  number.
- **Debunk rather than exploit fear.** He devotes a full chapter to arguing the dread of 13
  is "not at all the unlucky number they imagine it to be", tracing the taboo to Church
  opposition to occultism and to a misread Tarot image, and quoting the Adepts' line "He who
  understands the number 13 hath the Keys of power and dominion" (Ch. XVIII, `-layout`
  4399–4426). This aligns with §12's anti-exploitation guardrails and is citable in support
  of them.
- **Ground claims in cases, not in prior books.** His stated objection to other numerology
  writers is that they "have modelled their theories on literature that has appeared in
  different times or have copied what has been written and have not themselves had practical
  experience in proving the various theories from a wide variety of cases from actual life,
  and so have endeavoured to lay down rules which have no real foundation" (Ch. XXI,
  `-layout` 4994–5004). Worth keeping in view given this repo's history with unsourced
  tables.
- **Write for the general reader.** He says outright that he is writing "for the masses,
  more than for the more limited erudite student", giving "the more simple facts" and
  leaving the higher philosophy aside (`-layout` 5090–5096).

### 14.11 What was deliberately not extracted, and what could not be verified

**Not extracted (judged not to make a reading richer):**
- Chapters XVII, XIX, XX, XXXI — biographical case studies (recurring numbers in lives,
  St Louis / Louis XVI, US presidents). Interesting as corroboration, but they are
  applications of §14.2's method to dead public figures, not new rules.
- Chapter XXX, horse-racing and numbers — gambling advice, excluded on §12 guardrail
  grounds.
- Chapter XXXII, the Bible and numbers — 400 lines on Psalm 117/119 and Hebrew chapter
  counts. Sectarian, and not applicable to this site's audience.
- Chapter XXVIII, "Number and Disease; Planetary Significance of Herbal Cures" — **excluded
  on safety grounds.** Cheiro names herbs per number. §12 forbids health claims and this is
  the clearest possible case; the chapter is noted here only so nobody "discovers" it later
  and mines it.
- Chapter XXVII's music–number correspondences and the per-number "famous people born
  under" lists — low value, and the latter are 1930s figures.
- The compound-number rows themselves, 10–52 — already held in §5.1 from #160 and not
  re-imported, per instruction.

**Could not be verified, and therefore not used:**
- The regnal-name arithmetic for King Edward VII and King George V (Ch. XXI, `-layout`
  5236–5330). The text layer renders the addition columns as fragments (`II`, `22`, `=7`,
  `13`) and the surrounding prose does not restate every figure. The *rules* they illustrate
  — titles count, regnal numerals count — are sourced from the prose at 5193–5231 and are
  used; the specific sums are not.
- The garbled Napoleon passage at `-layout` 4154–4167, which appears to give a compound
  number and a skeleton/scythe symbol for "Napoleon Bonaparte", is unreadable in the text
  layer. Skipped; the Buonaparte→Bonaparte 5→8 point at 4135–4148 is legible and is used.

**Measured absences in this source (do not re-search):** across the full 14,183-line plain
extract — `Lo Shu` 0, `magic square` 0, `Feng Shui` 0, `Rudraksha` 0. Cheiro is not a source
for any of them. See §13.3.

---

**Compilation quality note:** this file is a fair-use summary of Harish Johari's, Jayant Kumar's and Cheiro's numerology systems. All specific numerical claims (exalted numbers, mantra counts, fasting food, compatibility per pair) are Johari's; Kumar's Core-Number taxonomy, Karmic Debt detection rule, Challenge/Pinnacle/Personal Year/Essence Cycle definitions are Kumar's; the name-numerology apparatus, the zodiac number-periods, the weekday numbers, the per-number colour/stone/day sets in §14.6 and the 4-and-8 doctrine are Cheiro's; interpretive framing where no author provides is marked as compilation. All three books remain the citations for user-facing content. **Where two authors disagree the divergence is recorded, not resolved** — §3.1 (Rahu/Ketu vs Uranus/Neptune), §7 vs §14.7 (pairwise vs group compatibility), §3.3 vs §14.6 (gems and colours). A reading must pick a tradition and stay inside it rather than blending them.
