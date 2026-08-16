# Kundali matching — Ashtakoota, as sourced

The 36-point Ashtakoota engine in `matching.py` was, until this file, the only
substantially **unsourced** feature in the repo (#177). Everything below is read
from a primary text and marked with how confidently.

## The source

**Muhurta Chintamani** of Daivagya Ramacharya, Vivaha prakarana (ch. 6), in the
edition carrying Mahidhar Sharma's **Hindi tika**. Held at
`data/matching/muhurta-chintamani-daivagya-ramacharya_sanskrit_djvu.txt` (CC0).

Two working notes, both learned the hard way:

- **The Hindi tika is the usable layer.** It states point values as digits where
  the Sanskrit states them as verse. Nearly every number below comes from the
  tika, not the mula.
- **The djvu OCR is not trustworthy for single glyphs.** It rendered विनालि as
  विनाखि, from which a plausible-but-wrong reading (विनाब्ज, "except Cancer")
  was reconstructed — the actual word is *ali*, **Scorpio**. Anything that turns
  on one akshara must be checked against the page image:
  `https://archive.org/download/<id>/page/n<N>.jpg`, cropped and enlarged.

Confidence markers used below:

- **[IMG]** — read at full page-image resolution, glyph-level certain.
- **[TIKA]** — read from djvu text plus a medium-resolution page image that
  agree with each other. Reliable for words, not yet glyph-certain for digits.
- **[UNREAD]** — located but not yet worked through.

---

## v.21 — the eight weights [IMG]

> वर्णमैत्री हो तो (१) गुण, वश्यमें (२), तारामें (३), योनिमें (४),
> ग्रहमैत्रीमें (५), गणमैत्रीमें (६), भकूटमैत्रीमें (७), नाडीमें गुण (८)
> इन सबका योग (३६) गुण होते हैं

Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot 7, Nadi 8;
total 36. **All eight match `matching.py` exactly.**

The OCR prints Graha Maitri's weight as ४. It is 5: the sequence is 1,2,3,4,?,6,7,8
and the verse states the total as 36, which pins the gap. Recovered by constraint,
not assumed.

## v.22 — Varna [IMG]

Pisces/Scorpio/Cancer = Brahmin; rashis 1/5/9 Kshatriya; 2/6/10 Vaishya;
3/7/11 Shudra. **All twelve match.**

> वर्णाधिक वर होनेमें (१) गुण मिलता है, कन्या अधिकमें नहीं

Groom's varna higher (or equal) scores 1; bride's higher scores 0. **All three
code branches match.**

## v.23 — Vashya [IMG]

> हित्वा मृगेन्द्रं नरराशिवश्याः सर्वे तथा जलजाश्च भव्याः ।
> सर्वेऽपि सिंहस्य वशे **विनालि** ज्ञेयं नराणां व्यवहारतोऽन्यत् ॥ २३ ॥

tika: वश्यकूट—मनुष्यराशि **३ । ६ । ७** योंके वशवर्ती **सिंह विना** सभी राशि हैं,
जलचर राशि भी मनुष्योंके भक्ष्य होनेसे उनके वश्य ही हैं तथा सिंहके वश **वृश्चिक
छोड़के** सभी राशि हैं। **अन्य परस्पर वश्यावश्य मानुष व्यवहारसे जानना**, यहां भी
वरकी राशिके वश्य कन्याकी राशि होनेमें (२) मिलते हैं, विपरीतमें नहीं।

What the verse actually establishes:

1. Vashya here is **class-based**, not a pair list — human rashis, aquatic
   rashis, and Leo as a special case.
2. The commentary names the human rashis as **3, 6, 7 only**. Recorded as
   printed. The conventional *nara-rashi* set also carries Aquarius (11) and
   the latter half of Sagittarius; this edition does not. Do not silently
   "correct" it — the divergence is the datum.
3. Leo is controlled by everything **except Scorpio** (*ali*). Confirmed twice
   independently: the mula's विनालि and the tika's वृश्चिक.
4. Scoring is **directional**: bride's rashi vashya to the groom's scores 2; the
   reverse scores nothing.
5. **The text declines to complete the table** — अन्य परस्पर वश्यावश्य मानुष
   व्यवहारसे जानना, "the rest is to be known from human practice."

Point 5 is the one that matters for **#175**. A fully enumerated 12×12 Vashya
table is a tradition-specific elaboration, *not* something this verse yields. So
the previously measured 58% disagreement between our `_RASHI_VASHYA` classes and
Raman's explicit pair list is not evidence that we are wrong — the two are
filling the same acknowledged gap by different conventions. Our class-based shape
is the closer of the two to this text.

### #175, settled against four further sources

v.23 alone speaks to only **44 of 144** pairs and defers the other 100 (69%).
So it was checked against everything else obtainable.

**The graded 5×5 matrix #175 asks for is not a single object.** Two sources
publish a full grid and they disagree on eight-plus of twenty-five cells:

| bride→groom | Saravali | freehoroscopesonline |
|---|---|---|
| Chatushpada→Manava | 0 | 1 |
| Chatushpada→Jalachara | 0 | 1 |
| Chatushpada→Vanachara | 0.5 | 1.5 |
| Manava→Jalachara | 1 | 1.5 |
| Manava→Vanachara | 0.5 | 0 |

One uses 0.5 and never 1.5; the other 1.5 and never 0.5. AstroMedha and
RashiRatanBhagya publish no grid at all — AstroMedha's page states outright that
any 5×5 matrix "would be invented rather than extracted". **Adopting "the"
matrix means picking one vendor's variant and calling it classical.** Both
classical texts we hold are binary instead: MC v.23 gives (२) or nothing, and
Raman's Vasya Kuta says "the unit of agreement is 2". Our 1.0 middle tier is
therefore unsourced, as #175 says — but collapsing to binary would require
deciding which pairs become 2 and which 0, which no source we hold does. Left in
place and disclosed.

**Aquarius as Manava is correct after all.** An earlier note here treated v.23's
omission of it as a contradiction. It is not: Saravali, RashiRatanBhagya and
freehoroscopesonline all place Aquarius in Manava exactly as we do, and v.23
declines to finish the classification anyway. Its silence is not a denial.

**The half-sign splits ARE convergent — implemented.** `_vashya_class` now cuts
Sagittarius and Capricorn at 15°:

| | Saravali | AstroMedha | freehoroscopes | MC |
|---|---|---|---|---|
| Capricorn 1st half | Quadruped | Quadruped | Quadruped | silent |
| Capricorn 2nd half | Jalachara | water | — | silent |
| Sagittarius 1st half | — | human | Manava | silent |
| Sagittarius 2nd half | — | quadruped | Chatushpada | silent |

Three agree on Capricorn, two on Sagittarius, **none contradict**. The splits
track the composite iconography — Sagittarius the centaur (human fore, equine
hind), Capricorn the makara (goat head, fish tail) — which is why the sources
that mention it agree. `PlanetPosition.longitude` already carried the degree, so
nothing needed computing. **32 of 144 sign-pairs now vary by degree.**

**Directionality: left alone, deliberately.** MC v.23 is directional (वरकी
राशिके वश्य कन्याकी राशि होनेमें (२) मिलते हैं, विपरीतमें नहीं) and Saravali's
grid is explicitly bride-rows × groom-columns and asymmetric. So the classical
form is directional and ours is symmetric. It was **not** changed, because the
modern symmetrisation is a deliberate reading rather than an error: this koota
was historically framed as the husband's control over the wife, and contemporary
practice equalises it. That makes it a values decision for the product owner,
not a correctness fix an agent should make unilaterally.

## v.24 — Tara [TIKA]

Count bride's nakshatra → groom's, and groom's → bride's; divide each by 9;
remainders **3, 5, 7 are inauspicious**, the rest auspicious; auspicious scores 3.

## vv.25–26 — Yoni [IMG] — **verified, no change needed**

Both halves check out exactly. This is the one koota that needed nothing.

**Assignments: 27/27 match.** The tika lists 14 yonis across 28 nakshatras —
it includes **Abhijit** (paired with Uttara Ashadha as नेवला/Mongoose), which
our 27-nakshatra scheme does not carry. Excluding Abhijit, every one of our 27
agrees:

Horse अश्व — Ashwini, Shatabhisha · Buffalo महिष — Swati, Hasta ·
Lion सिंह — Dhanishtha, P.Bhadrapada · Elephant हाथी — Bharani, Revati ·
Sheep मेढा — Pushya, Krittika · Monkey वानर — Shravana, P.Ashadha ·
Mongoose नेवला — U.Ashadha (+ Abhijit) · Serpent सर्प — Rohini, Mrigashira ·
Deer हरिण — Jyeshtha, Anuradha · Dog कुत्ता — Mula, Ardra ·
Cat बिल्ली — Punarvasu, Ashlesha · Rat चूहा — Magha, P.Phalguni ·
Tiger व्याघ्र — Vishakha, Chitra · Cow गौ — U.Phalguni, U.Bhadrapada

**Enemy pairs: 7/7 match**, set-identical to `_YONI_ENEMIES`:

> इनका वैर — गौ व्याघ्रका। गज सिंह। घोड़ा भैंसा। कुत्ता मृग। नेवला सर्प।
> वानर मेंढा। बिल्ली चूहा **इत्यादि लोकव्यवहारमें जानना**

Cow/Tiger, Elephant/Lion, Horse/Buffalo, Dog/Deer, Mongoose/Serpent,
Monkey/Sheep, Cat/Rat.

**Tiers.** एक योनि → उत्तम, सम योनि → सामान्य, योनिवैर → अशुभ, and योनिमैत्री
scores **(४)**. Our 4 / 2 / 0 matches that shape; the top and bottom are the
text's, but **the middle 2 is our interpolation** — the tika grades the middle
tier qualitatively (सामान्य) and never numbers it.

**Note the closing इत्यादि — "and so on, known from common practice."** The
same move as Vashya v.23. This text repeatedly gives anchors and then hands the
remainder to convention, which is a property of the source worth remembering
before treating any of its lists as exhaustive.

## vv.27–28 — Graha Maitri [IMG] — **implemented**

> वरकन्याके राशीश **मित्र** तथा **एकाधिपत्य**के हों तो **५** गुण, एवं
> **सममित्र**में **४**; **सम सम**में **३**, **मित्र शत्रु**में **२**,
> **सम शत्रु**में **१**, **शत्रु शत्रु**में **(०)** मिलता है।
> शत्रु शत्रुका मेल कहीं नहीं होता, मृत्युषट्काष्टक होता है।

| relationship | points |
|---|---|
| friend, or *ekadhipatya* (one graha lords both rashis) | 5 |
| neutral + friend | 4 |
| neutral + neutral | 3 |
| friend + enemy | **2** |
| neutral + enemy | **1** |
| enemy + enemy | 0 |

Our top three rows already matched. The bottom two were **1.0 / 0.5** — invented
by #174, which fixed a genuine inversion but had to guess the magnitudes and said
so. Corrected to 2.0 / 1.0. **44 of the 144 rashi pairs sit on those two rows.**

*Ekadhipatya* needs no branch: `_planet_relationship` already reports a planet as
its own friend.

The same page carries the **naisargika maitri** table (Sun's friends are Mars,
Jupiter, Moon; Moon has **no enemies**; etc.). Spot-checked against
`_PLANET_FRIENDS` — consistent.

## vv.29–30 — Gana [IMG] — **implemented**

**The 27 gana assignments (v.29) are verified 27/27 against our table.**

- राक्षस: Magha, Ashlesha, Dhanishtha, Jyeshtha, Mula, Shatabhisha, Krittika,
  Chitra, Vishakha
- मनुष्य: the three Purvas, the three Uttaras, Rohini, Bharani, Ardra
- देव: Anuradha, Punarvasu, Mrigashira, Shravana, Revati, Swati, Ashwini,
  Pushya, Hasta

**The scoring (v.30) was wrong, and wrong in kind as well as in value:**

> इस कूटमें गणसाम्यमें **६** गुण, देव मनुष्य में **५**, देव राक्षस एवं मनुष्य
> राक्षसमें गुण **(०)** है, कन्या राक्षसी वर देवमें **२**, कन्या देव वर
> मनुष्यमें **४** गुण

Read as unordered pairs this sentence contradicts itself — Deva/Rakshasa cannot
be both 0 and 2. Read **directionally** it is consistent, and that is the only
consistent reading available. It is also the structure the Varna rule already
uses (वर्णाधिक वर होनेमें गुण मिलता है — groom higher scores, bride higher does
not), and the prose above the table corroborates the asymmetry outright: वर
राक्षस + कन्या मनुष्य gives वैर, while वर मनुष्य + कन्या राक्षस gives वरकी
मृत्यु — one unordered pair, two different verdicts.

| groom | bride | points | |
|---|---|---|---|
| same | same | 6 | गणसाम्य |
| Deva | Manushya | 5 | the general देव-मनुष्य row |
| Manushya | Deva | **4** | कन्या देव वर मनुष्य — exception to it |
| Deva | Rakshasa | **2** | कन्या राक्षसी वर देव — exception |
| Rakshasa | Deva | 0 | the general देव-राक्षस row |
| Manushya | Rakshasa | **0** | stated flatly, no exception either way |
| Rakshasa | Manushya | **0** | |

Two changes. **Manushya/Rakshasa was 1.0 and is now 0** — that value had no
source. And **the koota is direction-dependent at all**, which the previous set
comparison could not express. **324 of the 729 nakshatra pairs are rescored**,
and 324 are now order-sensitive.

Consequence worth stating plainly: swapping which chart is the groom's now
changes the score. That is correct per the text, but it means a UI that lets
users enter the two charts in either order is making an astrological claim by
field placement.

## v.31 — Bhakoot [TIKA]

Gives the 6/8 and 2/12 afflictions. **The editor marks this verse प्रक्षिप्त
(interpolated).** Worth knowing before treating it as bedrock.

## vv.32–33 — दुष्टभकूटपरिहारः, the Bhakoot cancellations [TIKA]

The text lists **five** parihāras for shad-ashtaka dosha:

1. **मित्रषट्काष्टक** — the rashi lords are friends
2. **एकाधिपत्य** — one graha lords both rashis (1&8 both Mars; 2&7 both Venus)
3. **सबलांशेश मैत्री** — the *strong* navamsha lords are friendly
4. **राशिवश्यता** — the Vashya relation holds
5. **तारादि** — Tara shuddhi

> इनमेंसे **एक**के होनेमें भी षट्काष्टकदोष नहीं होता, **परन्तु नाडी सभीमें होनी
> चाहिये**

**Any one** of the five cancels the dosha. **Nadi shuddhi is not among them and
is required regardless** — Nadi is never cancelled by this list.

v.33 adds two more, for different doshas:

- rashi lords **and** navamsha lords mutually friendly → **Gana dosha** cancelled
- an auspicious rashi-kuta (3rd, 11th…) → **planetary-enmity dosha** cancelled
- राशीशोंकी प्रीति destroys shad-ashtaka and similar doshas

This is the sourced basis **#170** was missing. **Implemented** as
`_bhakoot_dosha`, with two deliberate constraints:

1. **A parihāra never moves a koota score.** The text performs one operation —
   षट्काष्टकदोष नहीं होता, the *dosha* does not occur — and assigns Bhakoot's
   seven points separately in v.21 as भकूटमैत्री. Restoring the seven was
   conflating two operations, and it moved **43 of the 72 dosha-carrying rashi
   pairs (60%)** a whole verdict band upward. That is now 0.
2. **Parihāra 3 is not evaluated.** सबल means *strong*, and there is no
   planetary-strength model in the repo — no shadbala anywhere in `chart.py`.
   Approximating "strong" would make the parihāra fire more often than the text
   warrants, which is the over-cancellation #170 exists to stop. It is reported
   as unevaluated on the result page so its silence is not read as its absence.

`nadi_shuddha` rides on the result rather than folding into `cancelled`,
because परन्तु नाडी सभीमें होनी चाहिये makes Nadi a precondition, not a
parihāra.

**Interpretive step, flagged.** Whether a cancelled dosha should also restore
the koota's points is a genuine divergence in practice, and the text does not
address it in so many words — it simply never awards them. We follow the text
literally and disclose the choice on both `/matching` and the explainer, since
a reader comparing us against a calculator that restores points will see a
different number for the same couple.

## v.34 — नाडीकूटं तदपवादश्च, Nadi and its exceptions [TIKA]

**Madhya Nadi is fully enumerated** and all nine match the standard group:
Pushya, Mrigashira, Chitra, Anuradha, Bharani, Dhanishtha, P.Ashadha,
P.Phalguni, U.Bhadrapada.

Adya is anchored on Jyeshtha, Ardra, U.Phalguni, Shatabhisha; Antya on Swati,
Krittika, Ashlesha, U.Ashadha — "दो दो नक्षत्रोंकी", two at a time. All eight
anchors fall in the standard Adya/Antya sets, so our table is corroborated.

Severity and exceptions:

- Same Nadi → inauspicious. **Both in Madhya Nadi → मृत्यु**, the gravest case.
- **मध्यनाडी छोड़के पार्श्वनाडियोंका दोष गोदावरीके दक्षिण अथवा क्षत्रिय आदिकोंको
  नहीं** — outside Madhya, the side-Nadi dosha **does not apply south of the
  Godavari, nor to Kshatriyas and others.** A regional and varna-scoped
  exemption, stated outright.
- Some hold Adya harms the groom, Antya the bride, Madhya both.
- **Pada-Nadi** (tri/chatur/pancha-nadi, counted from Ashwini / Krittika /
  Mrigashira): chatur-nadi is barred in Ahalya-desha, pancha-nadi in Punjab,
  tri-nadi everywhere.
- Where nakshatra-Nadi collides but pada-Nadi does not, **the dosha is slight**.
- Shanti prescribed (Mrityunjaya japa, gold donation) — i.e. the text itself
  does not treat Nadi as absolutely disqualifying.

**Implemented** as `_nadi_dosha`. `_nadi` is now the points table alone — 8 for
different Nadis, 0 for the same, binary as classical Nadi is. Two restorations
were removed:

1. **Full 8 for same-nakshatra-different-pada.** The text addresses exactly this
   case and does *not* cancel: दोष अल्प है, the dosha is SLIGHT. अल्प is a
   gradation, not an absence. Now reported as a mitigation.
2. **Partial 4 for same-rashi-different-nakshatra.** Unsourced before, and still
   unsourced after reading the section end to end — there is no same-rashi clause
   and no half-credit anywhere in it. Removed rather than rehomed, because there
   was nothing to rehome it to. It carried a "BPHS matching tradition" label that
   this reading does not support.

**The regional and community exemptions are deliberately not auto-applied.** Both
halves are genuine and sourced, and we apply neither. Birthplace is not the same
thing as the reckoning a family follows, and inferring someone's community from
their chart in order to discount an affliction is not something this calculator
should do. They are disclosed as context the reader can apply.

**Known tradition-blend, tracked.** The *concept* of a pada-level Nadi (चरणनाडी)
and the "slight" grading are from this North Indian text; the 108-pada *mapping*
in `_pada_nadi` is Raman's, which is South Indian. CLAUDE.md forbids blending the
two in one reading, and this is a blend. It is tolerable only because it now moves
no points — it decides the wording of a note. Do not promote it back into scoring
without a mapping from this tradition.

---

---

## The वर्णादिगुणचक्राणि tables (pp. 85–86) — transcribed, NOT adopted

Pages 85–86 carry a set of reference *charts* the earlier passes missed entirely.
The djvu OCR renders them as noise, so neither reading the text nor
`corpus_search.py` could ever have surfaced them; they are only visible in the
page images (`n96`, `n97`).

They matter because they answer questions this file previously recorded as
unanswerable. **They are transcribed here and deliberately NOT implemented** —
see the reliability section at the end, which is the whole point.

### ताराचक्रम् (9×9) — CONFIRMS our Tara

Graded **3 / १॥ / ०**: both taras favourable 3, one favourable 1½, neither 0.
Rows and columns 3, 5, 7 are the afflicted ones. **`_tara` matches this cell for
cell.** Our 0.0 branch is unreachable in practice because the two counts are
arithmetically linked (if one is 3/5/7 the other cannot be), but the logic is
right and the table enumerates all 81 cells for completeness.

Incidental but load-bearing: **१॥ = 1½ proves ॥ = ½**, the traditional Devanagari
half mark. That is what licenses reading ॥ as ½ in the Vashya table below.

### गणगुणाः (3×3) — CONTRADICTS the prose gloss

Columns वर (groom), rows कन्या (bride):

| bride ↓ groom → | देव | मनुष्य | राक्षस |
|---|---|---|---|
| **देव** | 6 | **5** | 0 |
| **मनुष्य** | 5 | 6 | 0 |
| **राक्षस** | 2 | 0 | 6 |

`_gana` ships bride-Deva + groom-Manushya = **4**, taken from the prose gloss
(कन्या देव वर मनुष्यमें ४ गुण). **The table says 5.** The prose and the table
disagree inside the same edition, and both readings are internally coherent:

- *For the table:* its other eight cells all match the prose, and the prose's own
  general clause देव मनुष्यमें ५ sits awkwardly with its later ४.
- *For the prose:* "general rule, then directional exception" is exactly the
  structure v.22 uses for Varna, and a 3×3 summary chart is precisely where a
  compiler would flatten an exception away.

**Unresolved. Code unchanged, still following the prose.** Resolving it needs a
second edition to collate against, not more staring at this one.

### वश्यगुण (5×5) — a real matrix, and it refutes an earlier claim here

| bride ↓ groom → | चतुष्पद | मनुष्य | जलचर | वनचर | कीट |
|---|---|---|---|---|---|
| **चतुष्पद** | 2 | ½ | 1 | 0 | 2 |
| **मनुष्य** | ½ | 2 | 0 | 0 | 0 |
| **जलचर** | 1 | 0 | 2 | 2 | 2 |
| **वनचर** | 0 | 0 | 2 | 2 | 0 |
| **कीट** | 1 | 0 | 1 | 0 | 2 |

Diagonal verified 2 in all five cells, which fixes the column order. Columns 1–4
were read twice at different crops and agree.

**This overturns what the #175 section above says.** That section claims no
canonical 5×5 matrix exists and that adopting one means picking a vendor's
variant. **Wrong** — one exists, in the same text as the rest of this engine, and
it was missed because the OCR destroys tables. The #175 issue comment carries the
same error and needs correcting.

It also shows our `_VASHYA_FRIENDLY` is wrong in kind, not just unsourced: we
score Manava/Jalachara as *friendly* 1.0 where this table says **0** — consistent
with the wider tradition treating a food relationship as undesirable rather than
as control.

Note the apparent conflict with v.23, which says जलचर rashis are वश्य to
मनुष्य rashis. It is not a conflict: being *food* is a vashya relation but an
inauspicious one, so the classification and the score point opposite ways.

### योनिगुणाः (14×14) — transcribed, and it does not survive its own checks

Order: अश्व, गज, मेष, सर्प, श्वान, मार्जार, मूषक, गो, भैंस, व्याघ्र, हरिण,
वानर, नकुल, सिंह. Values 0–4. Full transcription:

```
Horse     4 2 2 3 2 2 2 1 0 1 3 3 2 1
Elephant  2 4 3 3 2 2 2 2 3 1 2 2 2 0
Sheep     2 3 4 2 1 2 1 3 3 1 2 0 3 1
Serpent   3 3 2 4 2 1 1 1 1 2 2 2 0 2
Dog       2 2 1 2 4 2 1 2 2 1 0 2 1 1
Cat       2 2 2 3 2 4 0 2 2 2 3 3 2 2
Rat       2 2 1 1 1 0 4 2 2 2 2 2 2 1
Cow       1 2 3 2 3 2 2 4 3 0 3 2 2 1
Buffalo   0 2 3 2 2 2 2 3 4 1 2 3 2 2
Tiger     1 2 1 1 1 1 2 1 1 4 1 1 2 2
Deer      3 3 2 2 0 3 2 3 2 1 4 2 2 2
Monkey    3 3 0 2 2 3 2 2 1 1 2 4 3 2
Mongoose  2 3 3 0 1 2 1 2 2 2 2 3 4 2
Lion      1 0 1 2 1 1 0 0 3 2 1 2 2 4
```

What passes: diagonal is 4 in all 14 cells; all values in 0–4; **six of the seven
prose enemy pairs are 0 in both directions**, which is a strong independent
confirmation that the axis order and the reading are basically right.

What fails: **19 of 91 unordered pairs are asymmetric**, and the seventh enemy
pair is inconsistent — Cow×Tiger is 0 but Tiger×Cow is 1, though the prose names
गौ/व्याघ्र as mutual enemies. There are also two zeros outside the enemy list
(Cow/Lion, Lion/Rat) that no prose rule accounts for.

**The asymmetries are in the printed table, not in the transcription — verified
by a two-path read.** Re-reading the same rows the same way only confirms a
prior, so the Lion column (which alone accounts for 5 of the 19) was instead
read *vertically*, a different visual path from reading across a row:

| | |
|---|---|
| Lion column read top-down | `1 0 1 2 1 2 1 1 2 2 2 2 2 4` |
| same cells implied by the row-by-row transcription | `1 0 1 2 1 2 1 1 2 2 2 2 2 4` |
| **mismatches** | **none — transcription confirmed** |

Reading the same cells two different ways gives identical values. Those values
then disagree with the *Lion row* in exactly five places (Cat, Rat, Cow,
Buffalo, Deer), which is precisely the asymmetry set the symmetry check found.

So the two facts are cleanly separated: **the reading is right, and the table is
internally inconsistent.** Rows 7–12 were also re-read at higher magnification
and came back identical.

## Why none of the three tables is implemented

Because the cross-checking worked. A 196-cell matrix with 19 unexplained internal
asymmetries, one self-contradiction against its own prose, and no second edition
to collate against is **not** a sounder basis than the documented 4/2/0
simplification it would replace. Adopting it would be exactly the move this file
warns against elsewhere — trading a disclosed approximation for an unvalidated
transcription, and calling the result "sourced".

The same logic applies to Gana (prose vs table, unresolved) and, more marginally,
to Vashya, whose two asymmetric cells both sit in the one column read only once.

**What would unblock this:** a second printed edition or manuscript of Muhurta
Chintamani to collate the tables against. That is a book-acquisition task, not a
reasoning task. Until then the transcriptions live here as evidence, not as code.

## Still unsourced after this pass

Two entries that stood here have been resolved and are removed rather than left
to rot — a stale "still open" list is how someone later re-does finished work, or
worse, trusts a gap that has closed:

- ~~The Yoni enemy-pair grid, [UNREAD]~~ — **read and verified 7/7.** See the
  Yoni section above.
- ~~Whether the partial Nadi restoration (4 of 8) has any basis~~ — **it had
  none, and it is deleted.** There is no such restoration in `matching.py` any
  more, so the question no longer applies.

Genuinely still open:

- The Bhakoot 6/8 and 2/12 point values as distinct from the verdicts.
- The Yoni middle tier (2 of 4) — the tika grades it qualitatively (सामान्य) and
  never numbers it, and the 14×14 chart that would settle it fails its own
  consistency checks (see above).
- Bhakoot parihāra 3, सबलांशेश मैत्री — not evaluated, because there is no
  planetary-strength model in the repo.
- The pada-Nadi mapping in `_pada_nadi`, which is Raman's South Indian table
  inside this North Indian engine. Tolerable only because it now moves no points.

**Do not blend traditions.** This text is the North Indian 36-guna Ashtakoota.
B. V. Raman's *Muhurtha* is South Indian and works in 12 poruthams; cite Raman
for what a koota *is*, never for what it *scores*.
