# Numerology — Vedic + Chaldean integrated system

**Primary sources for this file:**
- **Johari** = Harish Johari, *Numerology — With Tantra, Ayurveda, and Astrology* (Destiny Books / Inner Traditions, 1990). Cited on Vedic 3-number system, per-planet-number traits, Vedic Square, Ayurvedic/Tantric correspondences.
- **Kumar** = Jayant Kumar, *Numerology & You — A Step By Step Approach* (Educreation Publishing, ISBN 978-1-61813-620-6, 2016). Cited on Western Chaldean 7-Core-Number taxonomy, Karmic Debt, Challenge/Pinnacle/Personal Year/Essence Cycle. **Sample copy only — pages 1-11 available; per-number chapters 3-24 not extractable.**

Where the two authors differ, the divergence is called out inline. Where they agree, cited as "Johari + Kumar". Johari-only claims cited "Johari". Kumar-only claims cited "Kumar".

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

**Divergence from Pythagorean:** Pythagorean assigns 1 to A, J, S (and value 9 exists) — a totally different mapping. Johari uses Chaldean only.

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
- 6 ↔ 3, 4, 6, 8, 9 — Venus's universal-friend nature
- 7 ↔ 1, 2, 3, 9 — Ketu's spiritual alliances
- 8 ↔ 1, 3, 5, 6 — Saturn's slow-friend
- 9 ↔ 1, 3, 6 — Mars's warrior-alliances

### Enemy pairings (activate growth through friction)
- 1 ↔ 5 (both destabilise), 6 (deceptive friendship), 8 (Saturn drags Sun)
- 2 ↔ 3 (advisers not partners), 5 (Moon-Mercury enmity)
- 3 ↔ 5 (both distracted), 7 (Jupiter-Ketu tension)
- 4 ↔ 3 (Rahu-Jupiter friction), 5 (both restless), 9 (Rahu-Mars war)
- 5 ↔ 2, 7, 8 (weakening)
- 6 ↔ 1 (only survives short-term), 5 (moody together), 7 (introvert-extrovert)
- 7 ↔ 4 (mutual attraction with instability), 7 (troublesome with self), 8 (Ketu-Saturn)
- 8 ↔ 4 (both bring difficulty), 8 (double Saturn), 9 (Mars-Saturn war)
- 9 ↔ 5 (both restless), 7 (both spiritual-doubting), 9 (double Mars)

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
| `_sum_letters` | Expression / Personality / Heart Desire / Name (Namank) | `True` | Chaldean/Pythagorean letter-value numbers, where 11/22/33 are part of the framework rather than an unreduced intermediate (#179) |

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

### 13.3 If implementing Lo Shu or business-name scoring:
Cite a separate source (Cheiro's *Book of Numbers* for extended compound numbers; Feng Shui texts for Lo Shu grid) and mark clearly in the article footer.

---

**Compilation quality note:** this file is a fair-use summary of Harish Johari's + Jayant Kumar's numerology systems. All specific numerical claims (exalted numbers, mantra counts, fasting food, compatibility per pair) are Johari's; Kumar's Core-Number taxonomy, Karmic Debt detection rule, Challenge/Pinnacle/Personal Year/Essence Cycle definitions are Kumar's; interpretive framing where neither author provides is marked as compilation. Both books remain the citations for user-facing content.
