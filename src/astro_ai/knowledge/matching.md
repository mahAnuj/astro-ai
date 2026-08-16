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

## v.24 — Tara [TIKA]

Count bride's nakshatra → groom's, and groom's → bride's; divide each by 9;
remainders **3, 5, 7 are inauspicious**, the rest auspicious; auspicious scores 3.

## vv.25–26 — Yoni [TIKA]

Yoni assignments per nakshatra, with योनिमैत्री scoring **(४) गुण**. The animal
list is present and legible; the enemy-pair grid is **[UNREAD]**.

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

This is the sourced basis **#170** was missing.

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

The regional scoping matters for user-facing copy: per CLAUDE.md we state which
convention a page uses rather than implying one universal answer. Our Nadi output
currently implies a universal rule.

---

## Still unsourced after this pass

- The Yoni enemy-pair grid (vv.25–26 hold it; **[UNREAD]**).
- The Bhakoot 6/8 and 2/12 point values as distinct from the verdicts.
- Whether the partial Nadi restoration in `matching.py` (4 of 8) has any basis —
  it does not come from here.

**Do not blend traditions.** This text is the North Indian 36-guna Ashtakoota.
B. V. Raman's *Muhurtha* is South Indian and works in 12 poruthams; cite Raman
for what a koota *is*, never for what it *scores*.
