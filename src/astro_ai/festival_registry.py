"""Registry of named Hindu festivals — dates, classical rules, and copy.

Single source of truth for festival dates. `festivals.py` derives its
`FESTIVALS_BY_DATE` lookup table from this module at import time, and the
/festivals hub renders `significance` / `observance` inline.

Dates cover 2026-2028 (`DATA_YEARS`) and were verified against two independent
sources that agreed on every row:
  (A) drikpanchang.com Hindu calendar, New Delhi (NCT), IST
  (B) Swiss Ephemeris tithi computation (pyswisseph 2.10.03, Lahiri sidereal,
      Delhi 28.6139N 77.2090E), checked against each festival's own observance
      window — pradosh / nishita / madhyahna / aparahna / moonrise — rather
      than against sunrise alone

The first seventeen festivals were verified on 2026-08-06. The thirteen added
on 2026-08-07 (marked `# verified 2026-08-07` below) were sourced from scratch
against the same two sources, each Drik date read twice off two different
pages — the year calendar and the New Delhi monthly calendar — so a single
misread page cannot carry a date through. No date in this file is carried over
from memory or from an earlier unreviewed draft.

Reckoning: purnimanta (North Indian) month naming, New Delhi / IST. Note that
Diwali is amanta Ashwina Amavasya = purnimanta Kartika Amavasya — same night,
two names. Some regional traditions legitimately observe a festival on the
adjacent day; where the almanac splits (Ram Navami, Janmashtami) we ship the
Smarta / Drik date.

Before editing a date, verify against a published almanac AND a computed
tithi — do not adjust from memory. Nine of the original 2026 rows were wrong
by up to 21 days because they were entered without a source check.

Cheap internal-consistency gate when editing (necessary, NOT sufficient — a
pair can be mutually consistent and jointly wrong): Karva Chauth (Kartika
Krishna Chaturthi) to Diwali (Kartika Amavasya) is 11 tithis, so ~10-11 days.
Navratri (Shukla Pratipada) to Dussehra (Shukla Dashami) is 9 tithis, ~9 days.

`note_en` / `note_hi` ship in the daily rashifal email, the welcome email and
the rashifal LLM prompt. Do not reword them casually.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from astro_ai.learn_registry import Article


@dataclass(frozen=True)
class Festival:
    """One named festival, with an explicit date per year in `DATA_YEARS`.

    `tier` separates the two kinds of row the hub renders:

    * ``"major"`` — a named festival with a hand-verified Gregorian date per
      year, which is every row in `FESTIVALS`. These get a card, an entry in
      the emails, and a mark on the calendar grid.
    * ``"recurring"`` — a monthly observance whose date is *computed* from the
      day's tithi rather than tabulated (Purnima, Amavasya, Ekadashi, Pradosh).
      Nothing in this module is `"recurring"` yet; the value exists so the hub
      and the template can already distinguish the two and so adding the
      computed rows later does not have to change this dataclass.

    The default is `"major"`, so a row that omits `tier` behaves exactly as
    every row did before the field existed.
    """

    slug: str
    name_en: str
    name_hi: str
    note_en: str            # one-line callout, shipped in the emails + LLM prompt
    note_hi: str
    dates: dict[int, str]   # year → ISO date, DATA_YEARS only
    rule: str               # classical definition, e.g. "Kartika Krishna Chaturthi (purnimanta)"
    observance_window: str  # tithi window that fixes the date: moonrise, pradosh, nishita, …
    significance: str       # what the day means — rendered on the /festivals hub
    observance: str         # what is actually done — rendered on the /festivals hub
    tier: str = "major"     # "major" (tabulated, verified) | "recurring" (computed from tithi)


DATA_YEARS: tuple[int, ...] = (2026, 2027, 2028)

SOURCE_NAME = "Drik Panchang"

SOURCE_URL_BY_YEAR: dict[int, str] = {
    2026: "https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=2026",
    2027: "https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=2027",
    2028: "https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=2028",
}


# Calendar order by the 2026 date. Where two festivals share a date, the more
# widely-observed / pan-Indian one is declared first, because `festivals.py`
# resolves a shared date by declaration order and the single-slot surfaces (the
# daily email, the rashifal prompt) take the first entry only.
#
# The `# verified …` comment on a row records where that row's dates came from.
# Rows without one predate the convention and are covered by the module header.
FESTIVALS: tuple[Festival, ...] = (
    Festival(
        slug="makar-sankranti",
        name_en="Makar Sankranti",
        name_hi="मकर संक्रान्ति",
        note_en="Sun enters Capricorn — Uttarayana begins. Auspicious for new starts, charity, and bathing in holy rivers.",
        note_hi="सूर्य का मकर राशि में प्रवेश — उत्तरायण आरम्भ। नए कार्य, दान और पवित्र नदियों में स्नान के लिए शुभ।",
        dates={2026: "2026-01-14", 2027: "2027-01-15", 2028: "2028-01-15"},
        rule="solar — Sun enters Capricorn",
        observance_window="sunrise",
        significance=(
            "Makar Sankranti marks the Sun's entry into Capricorn and the start of Uttarayana, "
            "the northward half of the solar year. Unlike most Hindu festivals it follows the solar "
            "calendar, which is why it holds steady around mid-January while the lunar festivals "
            "drift. Classically the day is read as a turning of the light — the nights begin to "
            "shorten, and what is associated with beginnings, giving and gratitude is held to carry "
            "further. It is kept under many names across the country: Pongal in the south, Uttarayan "
            "in Gujarat, Magh Bihu in Assam."
        ),
        observance=(
            "Bathe early, at a river if you can reach one, and offer arghya to the Sun at sunrise. "
            "Til (sesame) and gur (jaggery) are the day's foods — eaten, and given away as til-gur "
            "laddoos with the customary line about speaking sweetly. Donating grain, blankets, ghee "
            "or sesame is traditional. No fast is prescribed; this is a feast day, and kite-flying "
            "is the north-western custom."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and the
    # monthly calendar page, which print Pongal as "on Makara Sankranti day" for
    # all three years. Solar, so it shares Makar Sankranti's date exactly; this
    # is the shared-date pair `festivals.py` was built for.
    Festival(
        slug="pongal",
        name_en="Pongal (Thai Pongal)",
        name_hi="पोंगल",
        note_en="Tamil harvest thanksgiving — new rice is boiled over in the open and offered to the Sun as Uttarayana begins.",
        note_hi="तमिल फसल उत्सव — उत्तरायण के आरम्भ पर खुले में नया चावल उबालकर सूर्य को अर्पित किया जाता है।",
        dates={2026: "2026-01-14", 2027: "2027-01-15", 2028: "2028-01-15"},
        rule="solar — first day of Thai, the month that opens at Makar Sankranti",
        observance_window="sunrise",
        significance=(
            "Thai Pongal opens the Tamil month of Thai on the day the Sun turns into "
            "Capricorn, which is the same solar moment as Makar Sankranti — the two are one "
            "event under two names, and that is why both hold steady in mid-January while "
            "the lunar festivals drift. The festival is a thanksgiving to Surya, to the rain "
            "and to the cattle for the harvest just taken in, and it runs four days: Bhogi "
            "for discarding what is finished, Thai Pongal for the Sun, Mattu Pongal for the "
            "cattle, Kaanum Pongal for visiting. Thai pirandhaal vazhi pirakkum — when Thai "
            "is born, a way opens — is the line the month carries."
        ),
        observance=(
            "New rice is cooked with milk and jaggery in a clay pot set outdoors at sunrise, "
            "and the moment it boils over the household calls out Pongalo Pongal; the "
            "boiling over is the point, not an accident. The first serving goes to Surya on "
            "a banana leaf with sugarcane, a turmeric plant tied to the pot, and the "
            "season's fruit. A kolam is drawn at the threshold before dawn. Cattle are "
            "bathed, painted and garlanded on Mattu Pongal. It is a feast; no fast is kept."
        ),
    ),
    Festival(
        slug="vasant-panchami",
        name_en="Vasant Panchami",
        name_hi="वसन्त पञ्चमी",
        note_en="Saraswati Puja — honour the goddess of learning, music, and arts. Wear yellow.",
        note_hi="सरस्वती पूजा — ज्ञान, संगीत और कला की देवी का सम्मान। पीले वस्त्र धारण करें।",
        dates={2026: "2026-01-23", 2027: "2027-02-11", 2028: "2028-01-31"},
        rule="Magha Shukla Panchami",
        observance_window="madhyahna",
        significance=(
            "Vasant Panchami falls on the fifth tithi of Magha's waxing fortnight and opens the "
            "spring season in the Hindu reckoning. The day belongs to Saraswati — speech, learning, "
            "music and the arts — and by long custom it is treated as an abujha muhurat, a day "
            "whose auspiciousness is taken as given and needs no further calculation. Children are "
            "traditionally given their first letters on it, books and instruments are set before the "
            "goddess, and the mustard fields in bloom lend the day its yellow."
        ),
        observance=(
            "Wear yellow and offer yellow flowers, saffron rice or kesari sweets to Saraswati in the "
            "forenoon, where the puja is classically placed. Books, pens, instruments and the tools "
            "of one's study are placed before the image and left unused for the day as a mark of "
            "respect. No fast is required, though many keep a light satvik diet. New learning — and "
            "a child's first writing lesson — is begun today."
        ),
    ),
    Festival(
        slug="maha-shivratri",
        name_en="Maha Shivratri",
        name_hi="महा शिवरात्रि",
        note_en="The great night of Shiva. Fast, chant Om Namah Shivaya, stay awake for the four prahar of night worship.",
        note_hi="शिव की महानिशा। व्रत रखें, ॐ नमः शिवाय का जाप करें, चारों प्रहर जागरण करें।",
        dates={2026: "2026-02-15", 2027: "2027-03-06", 2028: "2028-02-23"},
        rule="Phalguna Krishna Chaturdashi",
        observance_window="nishita (midnight)",
        significance=(
            "Maha Shivratri falls on the fourteenth tithi of Phalguna's waning fortnight — the dark "
            "night just before the new moon — and is the greatest of the twelve monthly Shivratris. "
            "The classical framing is that the night itself is the point: Shiva is honoured in the "
            "deep hours rather than at midday, and the Puranas tie the night variously to his "
            "marriage with Parvati and to the appearance of the jyotirlinga. In practice it is a "
            "night of stillness and repetition rather than celebration. The mood is inward."
        ),
        observance=(
            "A fast is kept, from nirjala to a phalahar diet of fruit and milk. Abhishek of the "
            "Shivling with water, milk, honey and bel patra is the central act, classically repeated "
            "in each of the four prahars of the night, with the nishita kala near midnight held "
            "most valuable. Om Namah Shivaya or the Mahamrityunjaya is chanted through the vigil. "
            "The fast is broken next morning after the final puja."
        ),
    ),
    Festival(
        slug="holi",
        name_en="Holi",
        name_hi="होली",
        note_en="Festival of colours — celebrate the victory of good over evil and the arrival of spring.",
        note_hi="रंगों का त्यौहार — बुराई पर अच्छाई की विजय और वसन्त के आगमन का उत्सव।",
        dates={2026: "2026-03-04", 2027: "2027-03-22", 2028: "2028-03-11"},
        rule="day after Phalguna Purnima (Holika Dahan falls on the Purnima)",
        observance_window="full day",
        significance=(
            "Holi runs over two days: Holika Dahan on the night of the Phalguna full moon, and "
            "Rangwali Holi — the colours — the following morning. The bonfire recalls Prahlad, who "
            "walked out of the fire his aunt Holika could not survive; the colours belong to Krishna "
            "and the Braj country. Classically the festival closes the winter and opens the harvest "
            "season, and its licence — the levelling of age, rank and formality for a morning — is "
            "part of the observance rather than a departure from it."
        ),
        observance=(
            "On Holika Dahan evening the pyre is lit in the prescribed window after sunset, avoiding "
            "bhadra; people circle it and offer grain, coconut and the new harvest. The next morning "
            "is for colour, water and visiting, with gujiya and thandai as the customary foods. Some "
            "keep a light fast until the Dahan is done. Ash from the fire is traditionally applied "
            "to the forehead the following day."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both printing "Nutan Varsh Prarambha / Ugadi / Gudi Padwa" on
    # Chaitra Shukla Pratipada. Tithi confirmed independently (pyswisseph): Pratipada
    # current on each date. In 2026 Pratipada begins after sunrise and runs through the
    # day, which is the almanac's Pratipada-vyapini convention, not a discrepancy.
    Festival(
        slug="ugadi-gudi-padwa",
        name_en="Ugadi / Gudi Padwa",
        name_hi="उगादि / गुड़ी पड़वा",
        note_en="Lunar new year in the Deccan — hear the year's panchang read aloud, taste the six flavours of what is coming.",
        note_hi="दक्कन का चान्द्र नववर्ष — वर्ष का पञ्चाङ्ग श्रवण करें, आने वाले वर्ष के षड्रस चखें।",
        dates={2026: "2026-03-19", 2027: "2027-04-07", 2028: "2028-03-27"},
        rule="Chaitra Shukla Pratipada",
        observance_window="sunrise, Pratipada prevailing",
        significance=(
            "The first tithi of Chaitra's bright fortnight opens the lunar year across the "
            "Deccan — Ugadi in Andhra, Telangana and Karnataka, Gudi Padwa in Maharashtra "
            "and Goa, Cheti Chand for Sindhis, Navreh in Kashmir, and the same morning "
            "begins Chaitra Navratri in the north. Classically it is the day Brahma is held "
            "to have begun creation, and it is one of the three and a half abujha muhurats "
            "of the year, auspicious without a calculated window. Which day counts as new "
            "year is regional convention rather than a single rule: north India largely "
            "reckons from Diwali and Gujarat from Govardhan Puja, and none of those is "
            "wrong within its own tradition."
        ),
        observance=(
            "In Maharashtra the gudi goes up at the door in the morning — a bamboo pole, "
            "bright silk, neem and mango leaves, a sugar garland and an inverted copper pot "
            "at the top — and comes down before sunset. Ugadi pachadi is eaten first: neem "
            "flower, jaggery, tamarind, green chilli, salt and raw mango, six tastes for the "
            "six things a year brings, taken together and deliberately. Panchanga shravanam "
            "follows, the coming year's almanac read aloud. Bathe with oil beforehand, put "
            "on new clothes, and begin whatever you have been holding back."
        ),
    ),
    Festival(
        slug="ram-navami",
        name_en="Ram Navami",
        name_hi="राम नवमी",
        note_en="Birth of Lord Rama — read or listen to Ramcharitmanas, visit a Ram temple, fast in remembrance.",
        note_hi="श्री राम जी का जन्मोत्सव — रामचरितमानस पढ़ें या सुनें, राम मन्दिर के दर्शन करें, स्मरण में व्रत रखें।",
        dates={2026: "2026-03-26", 2027: "2027-04-15", 2028: "2028-04-03"},
        rule="Chaitra Shukla Navami",
        observance_window="madhyahna",
        significance=(
            "Ram Navami marks the birth of Rama on the ninth tithi of Chaitra's bright fortnight, at "
            "midday, and closes the Chaitra Navratri that begins nine days earlier. Both the Valmiki "
            "Ramayana and the Ramcharitmanas place the birth in the madhyahna hours, which is why "
            "this festival is fixed by midday rather than by midnight as at Janmashtami. The day is "
            "read as dharma taking human form, and the qualities remembered are steadiness, "
            "restraint and keeping one's word rather than conquest."
        ),
        observance=(
            "A fast is commonly kept from sunrise until the midday puja and taken as phalahar. The "
            "birth is celebrated at noon with a cradle ceremony; panakam — jaggery and pepper "
            "sherbet — and kosambari are offered as prasad in the south. Reciting or listening to "
            "the Balkand or the Sundarkand is traditional, as is visiting a Rama temple. Grains, "
            "onion and garlic are set aside for the day."
        ),
    ),
    Festival(
        slug="hanuman-jayanti",
        name_en="Hanuman Jayanti",
        name_hi="हनुमान जयन्ती",
        note_en="Birth of Hanuman ji. Recite Hanuman Chalisa, especially powerful on this day.",
        note_hi="हनुमान जी का जन्मोत्सव। हनुमान चालीसा का पाठ करें — इस दिन विशेष फलदायी।",
        dates={2026: "2026-04-02", 2027: "2027-04-20", 2028: "2028-04-09"},
        rule="Chaitra Purnima",
        observance_window="sunrise",
        significance=(
            "Hanuman Jayanti falls on the Chaitra full moon in the North Indian reckoning and "
            "celebrates the appearance of Hanuman — the servant, the strength, and one of the "
            "chiranjivis the texts hold to be still present. Because Hanuman is invoked for courage, "
            "protection, and relief from the harder transits of Shani and Mangal, the day carries a "
            "practical reputation alongside the devotional one. Southern and western traditions keep "
            "Hanuman's day at other points in the year; the Chaitra Purnima date is the northern custom."
        ),
        observance=(
            "Read the Hanuman Chalisa, the Sundarkand or the Bajrang Baan, at sunrise or in the "
            "evening after bathing. The offerings are sindoor mixed with chameli oil, a red flag or "
            "cloth, boondi or laddoo, and tulsi. Many keep a fast on fruit and milk through the day, "
            "breaking it after the evening puja. Simple food and brahmacharya for the day are the "
            "customary discipline."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Parashurama Jayanti / Akshaya Tritiya", Vaishakha Shukla
    # Tritiya. Tithi confirmed independently (pyswisseph): Tritiya current at sunrise
    # or midday on each date. Drik splits the pair — Parashurama Jayanti takes the
    # pradosh-vyapini Tritiya, Akshaya Tritiya the earlier one — so in 2027 they land
    # on consecutive days. That split is the classical rule, not a data error.
    Festival(
        slug="akshaya-tritiya",
        name_en="Akshaya Tritiya",
        name_hi="अक्षय तृतीया",
        note_en="Whatever is begun or given today is held never to diminish. A day that is its own muhurat.",
        note_hi="आज जो आरम्भ या दान किया जाए वह कभी क्षीण नहीं होता। यह दिन स्वयं मुहूर्त है।",
        dates={2026: "2026-04-19", 2027: "2027-05-09", 2028: "2028-04-27"},
        rule="Vaishakha Shukla Tritiya",
        observance_window="sunrise to madhyahna, Tritiya prevailing",
        significance=(
            "Akshaya means undiminishing, and the third tithi of Vaishakha's bright "
            "fortnight is held to keep whatever is started on it from wearing out. It is one "
            "of the three and a half abujha muhurats — days taken as auspicious in full, "
            "needing no further calculation — and the astrological reason usually given is "
            "that the Sun is exalted in Aries and the Moon in Taurus around this window. The "
            "Puranas hang several beginnings on it: Parashurama's appearance, Vyasa "
            "beginning to dictate the Mahabharata to Ganesha, the Akshaya Patra given to "
            "Draupadi, Sudama's handful of rice. The classical instruction on the day is "
            "about giving; buying gold is a later commercial custom laid over that."
        ),
        observance=(
            "Begin what has been waiting — a business, a build, a marriage, a course of "
            "study — without checking a muhurat, since the day is one. Daan is the "
            "prescribed act, and the traditional list is seasonal and unglamorous: water, "
            "a pot, curd-rice, sattu, grain, an umbrella, footwear, a fan. Lakshmi-Narayana "
            "are worshipped with tulsi and yellow flowers, many keeping a light fast until "
            "the puja is done. In Braj the Banke Bihari's feet are visible only today."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Vat Savitri Vrat / Shani Jayanti" on Jyeshtha Krishna
    # Amavasya. Tithi confirmed independently (pyswisseph): Amavasya at sunrise on all
    # three dates. 2026 has an Adhik Jyeshtha (17 May - 15 Jun); this amavasya falls
    # before it and is the nija one, which is why the 2026 -> 2027 jump is +19 days.
    Festival(
        slug="vat-savitri",
        name_en="Vat Savitri Vrat",
        name_hi="वट सावित्री व्रत",
        note_en="Married women fast and circle the banyan, remembering Savitri who argued her husband back from Yama.",
        note_hi="विवाहित स्त्रियाँ व्रत रखकर वट वृक्ष की परिक्रमा करती हैं — सावित्री का स्मरण, जिसने यम से पति को लौटाया।",
        dates={2026: "2026-05-16", 2027: "2027-06-04", 2028: "2028-05-24"},
        rule="Jyeshtha Krishna Amavasya (purnimanta)",
        observance_window="sunrise, Amavasya prevailing",
        significance=(
            "Savitri followed Yama when he took Satyavan and did not plead but argued, until "
            "the boons she had been granted left him no way to keep her husband — and the "
            "place she waited was under a banyan. The vat is chosen for what it is: a tree "
            "that drops roots from its branches and outlives everything around it. Note the "
            "regional split, which is real and not a discrepancy in the almanac. North India "
            "keeps the vrat on the Jyeshtha amavasya; Maharashtra, Gujarat and much of the "
            "south keep it a fortnight later on the Jyeshtha Purnima as Vat Purnima. We ship "
            "the amavasya date. The same day is Shani Jayanti."
        ),
        observance=(
            "The fast is kept from sunrise, nirjala in its strict form and on fruit in the "
            "commoner one. A banyan is circled an odd number of times — 108 by the fuller "
            "custom — with raw cotton thread wound round the trunk at each turn. Water, "
            "sindoor, soaked black chana, mango and the season's fruit are offered at the "
            "root, and the Savitri-Satyavan katha is heard sitting there. The fast is broken "
            "with the soaked chana. Where no banyan is reachable a branch or a drawn figure "
            "is worshipped instead, which the tradition allows."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page, monthly
    # calendar page, and the dedicated Ganga Dussehra page, which states "Dashami Tithi
    # of Jyeshtha Shukla Paksha" and gives Monday, May 25, 2026 for New Delhi. Tithi
    # confirmed independently (pyswisseph): Shukla Dashami current at midday on all
    # three dates. Checked deliberately because 2026's Adhik Jyeshtha makes this row
    # the easiest in the file to get a month wrong.
    Festival(
        slug="ganga-dussehra",
        name_en="Ganga Dussehra",
        name_hi="गंगा दशहरा",
        note_en="The day Ganga came down to earth — bathe in a river, offer arghya, and give away ten of something.",
        note_hi="जिस दिन गंगा पृथ्वी पर अवतरित हुईं — नदी में स्नान करें, अर्घ्य दें, दस वस्तुओं का दान करें।",
        dates={2026: "2026-05-25", 2027: "2027-06-13", 2028: "2028-06-02"},
        rule="Jyeshtha Shukla Dashami",
        observance_window="madhyahna, Dashami prevailing",
        significance=(
            "On the tenth tithi of Jyeshtha's bright fortnight Ganga is held to have come "
            "down from Shiva's hair to the plain, after Bhagiratha's tapasya, to carry his "
            "ancestors' ashes. Ten is the number the day is built on: the tenth tithi, and "
            "the dasha-hara of the name — the ten faults, three of the body, four of speech "
            "and three of the mind, that the classical texts say a bath today addresses. "
            "This is not the autumn Dussehra; the two share a word and nothing else. It "
            "falls in the hottest stretch of the year, which is why water, shade and cooling "
            "food are what the day asks you to give away."
        ),
        observance=(
            "Bathe in the Ganga if you can reach her, and if not add a little Ganga jal to "
            "your water and take the name — the tradition is explicit that the remembrance "
            "carries where the river does not. Offer arghya facing the stream at midday and "
            "float a lamp at dusk. Give away ten of things: ten lamps, ten fruits, ten "
            "measures of grain, sesame, and the season's daan of water pots, hand fans, "
            "sattu and sherbet. No fast is prescribed; the day is one of giving rather than "
            "abstaining."
        ),
    ),
    Festival(
        slug="guru-purnima",
        name_en="Guru Purnima",
        name_hi="गुरु पूर्णिमा",
        note_en="Pay reverence to your gurus — spiritual, scholastic, parental. The day Jupiter's energy is strongest.",
        note_hi="अपने गुरुओं को नमन करें — आध्यात्मिक, विद्या के, मातापिता। इस दिन गुरु ग्रह की ऊर्जा सर्वाधिक प्रबल।",
        dates={2026: "2026-07-29", 2027: "2027-07-18", 2028: "2028-07-06"},
        rule="Ashadha Purnima",
        observance_window="sunrise",
        significance=(
            "Guru Purnima falls on the Ashadha full moon and is kept as the day Vyasa was born — and "
            "in the Buddhist reckoning, the day of the first sermon at Sarnath. The classical sense "
            "of guru is wider than teacher: anyone through whom something was genuinely transmitted, "
            "spiritual, scholastic or parental. The day also opens Chaturmas, the four monsoon "
            "months when monastics traditionally stay in one place and study rather than travel, "
            "which is why learning and reverence share this date."
        ),
        observance=(
            "Bathe early and offer puja to your teacher in person where possible, or to their image "
            "or padukas where not; the traditional offering is flowers, fruit, cloth and whatever "
            "dakshina is within your means. Many fast until the puja is done, or eat once. Reading "
            "from a text received from your teacher — and honestly reviewing how much of it you have "
            "actually practised this year — is the substance of the day."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Nag Panchami", Shravana Shukla Panchami. Tithi confirmed
    # independently (pyswisseph): Shukla Panchami at sunrise on all three dates.
    Festival(
        slug="nag-panchami",
        name_en="Nag Panchami",
        name_hi="नाग पञ्चमी",
        note_en="Offer milk to the Naga deities — the day for serpent worship and for Kaal Sarp and Rahu-Ketu remedies.",
        note_hi="नाग देवताओं को दूध अर्पित करें — नाग पूजा तथा कालसर्प और राहु-केतु दोष की शान्ति का दिन।",
        dates={2026: "2026-08-17", 2027: "2027-08-06", 2028: "2028-07-26"},
        rule="Shravana Shukla Panchami",
        observance_window="sunrise",
        significance=(
            "The fifth tithi of Shravana's bright fortnight belongs to the great Nagas — "
            "Ananta, Vasuki, Takshaka, Karkotaka and the rest named in the Puranas. The "
            "timing is not arbitrary: this is the peak of the monsoon, when flooded burrows "
            "drive snakes into fields and houses, so the reverence has always been practical "
            "as well as devotional. In jyotish the day is the one usually prescribed for "
            "Kaal Sarp yoga and for Rahu-Ketu remedies, since the two nodes are the chhaya "
            "grahas classically figured as the head and tail of a serpent. In Braj the story "
            "kept is Krishna dancing on Kaliya, which the tradition reads as subduing rather "
            "than destroying."
        ),
        observance=(
            "Bathe early and offer milk, water, haldi, durva and lotus at an anthill, a Naga "
            "image or the serpent at a Shiva temple — the classical offering goes to the "
            "image or the burrow, never poured on a live snake. Naga figures are drawn at "
            "the doorway in haldi, chandan or cowdung. Digging the earth, ploughing and "
            "cutting are traditionally set aside for the day so nothing underground is "
            "disturbed. Many eat once, keeping to kheer, rice and satvik food."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Onam", with the rule printed as "Sun in Simha & Shravana
    # Nakshatra". Confirmed independently (pyswisseph, Lahiri sidereal): on each of the
    # three dates the Moon is in Shravana nakshatra and the Sun in Simha rashi.
    # NOT tithi-based, so it is exempt from the lunar-drift gate — the +17 day move
    # from 2026 to 2027 is normal for a nakshatra-in-solar-month rule.
    Festival(
        slug="onam",
        name_en="Onam (Thiruvonam)",
        name_hi="ओणम",
        note_en="Kerala's harvest festival and Mahabali's one day home — pookalam at the door, sadya on a banana leaf.",
        note_hi="केरल का फसल उत्सव और राजा महाबली की वार्षिक वापसी — द्वार पर पूकलम, केले के पत्ते पर सद्या।",
        dates={2026: "2026-08-26", 2027: "2027-09-12", 2028: "2028-09-01"},
        rule="Thiruvonam nakshatra with the Sun in Simha (Chingam, Malayalam solar month)",
        observance_window="sunrise",
        significance=(
            "Onam is fixed by the Malayalam solar calendar rather than by a tithi — "
            "Thiruvonam nakshatra falling in the month of Chingam — which is why it moves "
            "differently from the lunar festivals and can swing more than a fortnight "
            "between years. It marks the annual return of Mahabali, the asura king whose "
            "reign Kerala remembers as a time when nobody was cheated and nothing was "
            "measured short, pressed into the netherworld by Vamana and granted one day a "
            "year to see his people. Ten days run from Atham to Thiruvonam. It is kept "
            "across communities in Kerala rather than by one alone, and is a harvest "
            "festival before it is a religious one."
        ),
        observance=(
            "A pookalam — a carpet of flowers laid on the swept ground at the threshold — is "
            "begun on Atham and made larger each of the ten days. The onasadya is the centre "
            "of Thiruvonam: a vegetarian feast of some two dozen preparations served on a "
            "banana leaf in a fixed order, ending in payasam. Onakkodi, new clothes, are "
            "given to the household. Small clay figures of Mahabali and Vamana are set at "
            "the pookalam and honoured. Vallamkali boat races, Thiruvathira kali and "
            "Pulikali fill the day. No fast is kept."
        ),
    ),
    Festival(
        slug="raksha-bandhan",
        name_en="Raksha Bandhan",
        name_hi="रक्षा बन्धन",
        note_en="Sisters tie rakhi on brothers' wrists, exchange love and the promise of lifelong protection.",
        note_hi="बहन भाई की कलाई पर राखी बाँधती है, प्रेम और आजीवन रक्षा का वचन।",
        dates={2026: "2026-08-28", 2027: "2027-08-17", 2028: "2028-08-05"},
        rule="Shravana Purnima",
        observance_window="aparahna, after bhadra ends",
        significance=(
            "Raksha Bandhan falls on the Shravana full moon. A sister ties a rakhi on her brother's "
            "wrist and he takes up her protection — though the older sense of the raksha sutra is "
            "broader: a thread tied by a priest, a wife, or anyone offering safekeeping. The same "
            "day is Shravani Upakarma, when the sacred thread is ritually renewed. What the festival "
            "holds is less an obligation than an annual, deliberate restatement of a tie that "
            "otherwise goes unspoken all year."
        ),
        observance=(
            "The tying is done in the aparahna hours and, importantly, only after bhadra has ended — "
            "a bhadra-period tying is traditionally avoided, so the almanac's window matters more "
            "here than for most festivals. The sister performs aarti, applies tilak, ties the thread "
            "on the right wrist and feeds him something sweet; he gives a gift in return. Many "
            "sisters keep a light fast until the rakhi is tied."
        ),
    ),
    Festival(
        slug="krishna-janmashtami",
        name_en="Krishna Janmashtami",
        name_hi="जन्माष्टमी",
        note_en="Midnight birth of Krishna — fast until midnight, sing bhajans, dress an infant Krishna idol.",
        note_hi="श्री कृष्ण का मध्यरात्रि जन्म — मध्यरात्रि तक उपवास, भजन गाएँ, बाल कृष्ण को वस्त्र पहनाएँ।",
        dates={2026: "2026-09-04", 2027: "2027-08-25", 2028: "2028-08-13"},
        rule="Bhadrapada Krishna Ashtami",
        observance_window="nishita (midnight)",
        significance=(
            "Janmashtami marks Krishna's birth on the eighth tithi of Bhadrapada's dark fortnight — "
            "at midnight, in Rohini nakshatra. The texts are unusually specific about the hour, "
            "which is why the festival is fixed by the nishita window rather than by sunrise. "
            "Almanacs often publish two days, one for the smarta householder reckoning and one for "
            "the Vaishnava line; both are correct within their own tradition. The tone of the day is "
            "affectionate rather than solemn — the deity being honoured is an infant."
        ),
        observance=(
            "The fast runs from sunrise to midnight, kept nirjala or on fruit and milk, and is "
            "broken after the midnight puja. An infant Krishna image is bathed in panchamrit, "
            "dressed, laid in a cradle and rocked; bhajans and the Bhagavata's tenth canto fill the "
            "evening. Dahi-handi follows the next morning in Maharashtra. Grains are avoided; the "
            "prasad is makhan-mishri, panjiri and dhaniya."
        ),
    ),
    Festival(
        slug="ganesh-chaturthi",
        name_en="Ganesh Chaturthi",
        name_hi="गणेश चतुर्थी",
        note_en="Welcome Ganesh ji home. Begins 10 days of devotion ending in Visarjan.",
        note_hi="गणेश जी का स्वागत। 10 दिनों की भक्ति जो विसर्जन से समाप्त होती है।",
        dates={2026: "2026-09-14", 2027: "2027-09-04", 2028: "2028-08-23"},
        rule="Bhadrapada Shukla Chaturthi",
        observance_window="madhyahna",
        significance=(
            "Ganesh Chaturthi falls on the fourth tithi of Bhadrapada's bright fortnight, in the "
            "madhyahna hours, and celebrates the appearance of Ganesha — the one addressed before "
            "any work begins. The ten-day public form dates from Tilak's revival in Maharashtra, but "
            "the household puja is far older. The festival's arc has a deliberate shape: the murti "
            "is welcomed as a guest, hosted, and then given back to the water at visarjan, which is "
            "as much of the meaning as the arrival was."
        ),
        observance=(
            "Install the murti in the madhyahna window with pranapratishtha, then shodashopachar "
            "puja. Modak — twenty-one by custom — durva grass in odd numbers and red flowers are the "
            "offerings; the Ganapati Atharvashirsha is the classical recitation. Aarti twice daily "
            "for as long as the murti stays, whether that is a day and a half, five days or ten. "
            "Visarjan closes it. Looking at the moon on Chaturthi night is traditionally avoided."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both giving Bhadrapada Shukla Tritiya. Tithi confirmed
    # independently (pyswisseph): Shukla Tritiya current on each date. In 2026 Drik
    # prints "Hartalika Teej" and "Ganesh Chaturthi" on the SAME day, 14 September —
    # read twice, on two different pages, because it is a shared date. Declared after
    # Ganesh Chaturthi so the single-slot surfaces lead with the pan-Indian festival.
    Festival(
        slug="hartalika-teej",
        name_en="Hartalika Teej",
        name_hi="हरतालिका तीज",
        note_en="A nirjala fast for a husband's long life or a good marriage, before a Shiva-Parvati shaped from clay.",
        note_hi="पति की दीर्घायु या सुयोग्य वर हेतु निर्जला व्रत, बालू से बने शिव-पार्वती की पूजा।",
        dates={2026: "2026-09-14", 2027: "2027-09-03", 2028: "2028-08-22"},
        rule="Bhadrapada Shukla Tritiya",
        observance_window="pratah and pradosh, Tritiya prevailing",
        significance=(
            "The third tithi of Bhadrapada's bright fortnight, usually the day before Ganesh "
            "Chaturthi and in some years — 2026 among them — the same day, when the two "
            "tithis run close enough to share a sunrise. The name is harat and alika, the "
            "friend who carried her off: Parvati's companions took her into the forest so "
            "she could not be married to Vishnu against her wish, and it was there she kept "
            "the tapasya that finally won Shiva. Of the three Teejs it is the strictest. It "
            "is largely a north and central Indian observance — UP, Bihar, MP, Rajasthan, "
            "and Maharashtra as Haritalika — rather than a pan-Indian one."
        ),
        observance=(
            "The fast is nirjala, kept through the day and by the fuller custom through the "
            "night as well, and is not broken even for water. Shiva, Parvati and Ganesha are "
            "shaped from river sand or clay and worshipped at pratahkal and again at "
            "pradosh, with belpatra, dhatura, flowers and the sixteen shringar offered to "
            "the goddess. The katha is heard, the night passed in bhajan and jagran, and the "
            "fast broken the next morning after the final puja. Mehndi, green bangles and "
            "green cloth are the day's mark."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Ganesh Visarjan / Anant Chaturdashi", Bhadrapada Shukla
    # Chaturdashi. Tithi confirmed independently (pyswisseph): Shukla Chaturdashi at
    # sunrise on all three dates.
    Festival(
        slug="anant-chaturdashi",
        name_en="Anant Chaturdashi",
        name_hi="अनन्त चतुर्दशी",
        note_en="Ganesh Visarjan day, and the vrat of Ananta Vishnu — tie the thread of fourteen knots.",
        note_hi="गणेश विसर्जन का दिन और अनन्त विष्णु का व्रत — चौदह गाँठों वाला अनन्त सूत्र बाँधें।",
        dates={2026: "2026-09-25", 2027: "2027-09-14", 2028: "2028-09-02"},
        rule="Bhadrapada Shukla Chaturdashi",
        observance_window="madhyahna, Chaturdashi prevailing",
        significance=(
            "Two observances share the fourteenth tithi of Bhadrapada's bright fortnight. It "
            "closes the ten days of Ganesh Chaturthi with visarjan, the murti returned to "
            "water; and it is the vrat of Ananta — Vishnu in his endless form, resting on "
            "Shesha — which the Mahabharata has Krishna prescribe to Yudhishthira during the "
            "exile, as the thing to do when a stretch of life cannot be shortened and must "
            "simply be got through. Fourteen is the number the day turns on: fourteen knots, "
            "fourteen years of the vrat, the fourteen lokas. In the Jain reckoning the same "
            "day closes Paryushana as Kshamavani, the day of asking forgiveness."
        ),
        observance=(
            "Ananta Vishnu is worshipped in the forenoon, with a kalash and an image of "
            "Shesha wound from durva and kusha grass. A cotton thread of fourteen knots, "
            "dyed in haldi, is offered and then tied — the right arm for men, the left for "
            "women — and worn until it is replaced next year. Fourteen puris and fourteen "
            "sweet cakes are offered and shared out. Where the ten-day Ganesh utsav has been "
            "kept, the same afternoon is the visarjan procession, the murti carried to water "
            "with Ganpati Bappa Morya, pudhchya varshi lavkar ya — come back soon next year."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Sarva Pitru Amavasya", printed as Ashwina Krishna Amavasya
    # (purnimanta, consistent with Drik's "Pitrupaksha Begins = Ashwina Krishna
    # Pratipada"). Tithi confirmed independently (pyswisseph): Amavasya through the
    # aparahna window on all three dates.
    Festival(
        slug="mahalaya-amavasya",
        name_en="Mahalaya Amavasya (Sarva Pitru)",
        name_hi="महालया अमावस्या (सर्वपितृ)",
        note_en="Last day of Pitru Paksha — shraddha for every ancestor, including those whose tithi is not known.",
        note_hi="पितृ पक्ष का अन्तिम दिन — सभी पितरों का श्राद्ध, उनका भी जिनकी तिथि ज्ञात नहीं।",
        dates={2026: "2026-10-10", 2027: "2027-09-29", 2028: "2028-09-18"},
        rule="Ashwina Krishna Amavasya (purnimanta), closing Pitru Paksha",
        observance_window="aparahna (kutup muhurat)",
        significance=(
            "The amavasya that closes the fortnight of Pitru Paksha. Shraddha through that "
            "fortnight is normally offered on the tithi an ancestor died; this last day "
            "gathers all of them at once, which is why it is called Sarva Pitru — and why it "
            "is the day that covers anyone whose date was never written down, who died away "
            "from home, or whose rites were never completed. In Bengal the same dawn is "
            "Mahalaya, when the Devi is invoked and the count to Durga Puja begins, so the "
            "fortnight given to the dead hands straight over to the fortnight given to the "
            "Goddess. The tone is obligation quietly discharged rather than mourning."
        ),
        observance=(
            "Tarpan is offered with water, black sesame and kusha grass, facing south, in "
            "the aparahna hours — the kutup muhurat around midday is the classical window. "
            "Pind daan of rice follows. Portions are set aside for the crow, the cow, the "
            "dog and the fire before anyone in the house eats, and a brahmana or a guest is "
            "fed and given cloth. Speak the names aloud if you know them. The fortnight's "
            "restraint — no new purchases, no auspicious beginnings — ends with this day."
        ),
    ),
    Festival(
        slug="navratri",
        name_en="Navratri (begins)",
        name_hi="नवरात्रि (आरम्भ)",
        note_en="Nine nights of Devi worship — each night honours one form of the Goddess. Fast, chant, and dance.",
        note_hi="नौ रातें देवी आराधना की — हर रात्रि देवी के एक रूप का सम्मान। व्रत, जप, और गरबा।",
        dates={2026: "2026-10-11", 2027: "2027-09-30", 2028: "2028-09-19"},
        rule="Ashwina Shukla Pratipada",
        observance_window="sunrise",
        significance=(
            "Sharad Navratri begins on the first tithi of Ashwina's bright fortnight and runs nine "
            "nights, each given to one of the nine forms of Durga, closing at Dussehra on the tenth. "
            "This is the autumn Navratri, the most widely kept of the four in the year. Classically "
            "it is a stretch of discipline as much as of celebration — the fast, the daily paath and "
            "the restraint on food and diversion are the frame, and the garba and dandiya of the "
            "evenings sit inside that frame rather than replace it."
        ),
        observance=(
            "Ghatasthapana on the first morning, within the prescribed pratipada window, sets a clay "
            "pot with sown barley that is watered daily. Many keep the full nine-day fast on kuttu "
            "or singhara flour, sendha namak, fruit and milk, avoiding grains, onion and garlic. The "
            "Durga Saptashati or the Durga Chalisa is read each day. Kanya pujan on Ashtami or "
            "Navami, feeding and honouring young girls, closes the vrat."
        ),
    ),
    Festival(
        slug="dussehra",
        name_en="Dussehra (Vijayadashami)",
        name_hi="दशहरा",
        note_en="Victory of Rama over Ravana — start anything new today, it carries the blessing of dharma.",
        note_hi="रावण पर राम की विजय — आज कुछ भी नया आरम्भ करें, धर्म का आशीर्वाद साथ रहता है।",
        dates={2026: "2026-10-20", 2027: "2027-10-09", 2028: "2028-09-27"},
        rule="Ashwina Shukla Dashami",
        observance_window="aparahna",
        significance=(
            "Vijayadashami falls on the tenth tithi of Ashwina's bright fortnight, after the nine "
            "nights. It carries two stories at once — Rama's victory over Ravana in the north, "
            "Durga's over Mahishasura in the east — and both are read as the same thing: a long "
            "contest finally finishing. The day is one of the three and a half abujha muhurats of "
            "the year, auspicious throughout without needing a calculated window, which is why so "
            "much is traditionally begun on it."
        ),
        observance=(
            "The observance window is aparahna, the late afternoon, when the Ravana effigies burn "
            "and Shami puja and Aparajita puja are performed. Tools, books, vehicles and instruments "
            "are honoured in the ayudha puja, and children are traditionally started on their "
            "letters. Beginning a journey, a business or any new undertaking today needs no further "
            "muhurat check. Exchanging apta leaves as symbolic gold is the Maharashtrian custom."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Kojagara Puja / Sharad Purnima". Tithi confirmed
    # independently (pyswisseph): Purnima current from moonrise through nishita on all
    # three dates. Drik lists a separate "Ashwina Purnima" on the FOLLOWING day in 2026
    # and 2027 — that is the sunrise-reckoned snan-daan Purnima, a different rule for
    # a different purpose. Sharad Purnima is the night one; that is the row here.
    Festival(
        slug="sharad-purnima",
        name_en="Sharad Purnima (Kojagari)",
        name_hi="शरद पूर्णिमा (कोजागरी)",
        note_en="The moon at its fullest sixteen kalas — leave kheer out in the moonlight, and stay awake for Lakshmi.",
        note_hi="चन्द्रमा सोलह कलाओं से पूर्ण — खीर चाँदनी में रखें और लक्ष्मी हेतु जागरण करें।",
        dates={2026: "2026-10-25", 2027: "2027-10-14", 2028: "2028-10-02"},
        rule="Ashwina Purnima",
        observance_window="moonrise to nishita",
        significance=(
            "The Ashwina full moon is the one night of the year the classical texts say the "
            "Moon shows all sixteen of its kalas, with the monsoon just cleared and the air "
            "at its most transparent. It is also Kojagari Purnima — ko jagarti, who is "
            "awake — the night Lakshmi is said to move about and to give to whoever she "
            "finds still up, which is why the vigil rather than the puja is the substance of "
            "it. In Braj the same night holds the Maharaas of Krishna and the gopis. Because "
            "the day is fixed by the Purnima prevailing at moonrise and through the night, "
            "it can fall a day before the Purnima the almanac marks for the morning "
            "snan-daan; both entries are correct, for different windows."
        ),
        observance=(
            "Kheer is cooked and set out under the open sky through the night in a silver or "
            "clay vessel, and eaten as prasad at dawn — the tradition holds the night's rays "
            "to be medicinal, and ayurveda uses the practice for respiratory and pitta "
            "complaints. Lakshmi is worshipped at moonrise, lamps left burning, and the "
            "night passed in jagran with bhajan, dice and conversation rather than sleep. "
            "Many keep a fast through the day and break it with the kheer."
        ),
    ),
    Festival(
        slug="karva-chauth",
        name_en="Karva Chauth",
        name_hi="करवा चौथ",
        note_en="Married women fast for the long life of their husband. Sight the moon, then break the fast.",
        note_hi="विवाहित स्त्रियाँ पति की दीर्घायु के लिए व्रत रखती हैं। चन्द्र दर्शन के बाद व्रत खोला जाता है।",
        dates={2026: "2026-10-29", 2027: "2027-10-18", 2028: "2028-10-07"},
        rule="Kartika Krishna Chaturthi (purnimanta)",
        observance_window="moonrise",
        significance=(
            "Karva Chauth falls on the fourth tithi of the waning fortnight of Kartika in the "
            "purnimanta reckoning, four days after the full moon. Married women keep a day-long fast "
            "for the long life of their husbands and break it only after sighting the moon — which "
            "is why the date is set by moonrise rather than sunrise, and why the timing shifts from "
            "city to city. The Punjabi and western-UP custom is the best known, with the katha of "
            "Veeravati and the sargi at its centre."
        ),
        observance=(
            "The fast begins before dawn with sargi, food sent by the mother-in-law, and strict "
            "observers keep it nirjala through the day. In the evening women gather, hear the Karva "
            "Chauth katha and pass the karva — the clay pot — in the customary circle. After "
            "moonrise the moon is viewed through a sieve, arghya is offered, the husband's face is "
            "seen, and he gives the first sip of water."
        ),
    ),
    Festival(
        slug="diwali",
        name_en="Diwali (Deepavali)",
        name_hi="दीपावली",
        note_en="Festival of lights — Lakshmi Puja in the evening welcomes prosperity. Clean the home, light diyas, set off no firecrackers indoors.",
        note_hi="दीपों का त्यौहार — सायंकाल लक्ष्मी पूजा से समृद्धि का स्वागत। घर साफ करें, दीये जलाएँ।",
        dates={2026: "2026-11-08", 2027: "2027-10-29", 2028: "2028-10-17"},
        rule="Kartika Amavasya (purnimanta) = Ashwina Amavasya (amanta)",
        observance_window="pradosh (dusk), Lakshmi Puja",
        significance=(
            "Diwali falls on the Kartika Amavasya — the darkest night of the month in the purnimanta "
            "reckoning, which the amanta calendar names Ashwina Amavasya. Same night, two names. The "
            "north remembers Rama's return to Ayodhya, the west Krishna's defeat of Narakasura, and "
            "Lakshmi is welcomed everywhere at dusk. That the festival of lights is set on the "
            "year's darkest night is the whole point of it: the lamps mean more against that "
            "background than they would against any other."
        ),
        observance=(
            "Lakshmi Puja is performed in the pradosh window at dusk, with a sthir lagna preferred "
            "where the almanac offers one. Clean the house first — the classical instruction is that "
            "Lakshmi enters where things are in order. Offer lotus, kamal gatta, batasha and kheel, "
            "and light diyas at the threshold, at the tulsi and at every doorway, leaving one to "
            "burn through the night. Account books are opened afresh."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page. Both print "Lakshmi Puja / Narak Chaturdashi / Diwali" together on
    # 8 Nov 2026 and again on 17 Oct 2028, and put Narak Chaturdashi one day BEFORE
    # Diwali in 2027 (28 Oct vs 29 Oct). Read twice on two pages precisely because the
    # 2026 collision is the load-bearing claim here. Tithi confirmed independently
    # (pyswisseph): Krishna Chaturdashi is current before dawn on all three dates,
    # which is the window that fixes this festival — hence the same-day landings.
    # Declared after Diwali so the single-slot surfaces lead with Diwali.
    Festival(
        slug="narak-chaturdashi",
        name_en="Narak Chaturdashi (Choti Diwali)",
        name_hi="नरक चतुर्दशी (छोटी दीवाली)",
        note_en="Choti Diwali — the pre-dawn oil bath, and one lamp facing south for Yama. Some years it falls on Diwali itself.",
        note_hi="छोटी दीवाली — प्रातःकाल अभ्यंग स्नान और द्वार पर दक्षिणमुखी यम दीपक। कुछ वर्षों में यह दीपावली के दिन ही पड़ती है।",
        dates={2026: "2026-11-08", 2027: "2027-10-28", 2028: "2028-10-17"},
        rule="Kartika Krishna Chaturdashi (purnimanta)",
        observance_window="pre-dawn, Chaturdashi prevailing at Chandrodaya (Abhyanga Snan)",
        significance=(
            "The fourteenth tithi of Kartika's dark fortnight, the day before Amavasya, "
            "remembers Krishna and Satyabhama killing Narakasura and releasing the sixteen "
            "thousand he held. Because the day is fixed by the Chaturdashi prevailing before "
            "dawn rather than at sunrise, it lands on the same Gregorian date as Diwali in "
            "some years and the day before in others — the almanac working correctly, not a "
            "contradiction, and worth saying plainly because the two readings both circulate. "
            "It is Kali Chaudas in Gujarat and the west, where the night is given to Kali "
            "instead, and Roop Chaudas for the bath that is the day's other name."
        ),
        observance=(
            "The abhyanga snan is the central act and it has to be done in the dark: an oil "
            "massage with til or coconut oil, an ubtan of chickpea flour and haldi, and a "
            "bath before sunrise while the Chaturdashi still runs, which the texts rate "
            "alongside a bath in the Ganga. Apamarga leaves are circled over the head "
            "beforehand. At dusk a single lamp — the Yama deepak — is lit at the threshold "
            "facing south, the only lamp of the year set in that direction, and it is not "
            "moved. Food stays light; the house is finished for Diwali."
        ),
    ),
    Festival(
        slug="govardhan-puja",
        name_en="Govardhan Puja",
        name_hi="गोवर्धन पूजा",
        note_en="The day Krishna lifted Mt Govardhan — honour cows, prepare annakut (mountain of food).",
        note_hi="जिस दिन कृष्ण ने गोवर्धन पर्वत उठाया — गायों का सम्मान, अन्नकूट तैयार करें।",
        dates={2026: "2026-11-10", 2027: "2027-10-30", 2028: "2028-10-18"},
        rule="Kartika Shukla Pratipada",
        observance_window="sunrise",
        significance=(
            "Govardhan Puja falls on the first tithi of Kartika's bright fortnight, the day after "
            "Diwali. It remembers Krishna lifting Mount Govardhan on one finger for seven days to "
            "shelter Braj from Indra's rain, and the lesson drawn classically is a plain one about "
            "where sustenance actually comes from — the hill, the cattle, the land — rather than "
            "about the miracle itself. In Braj and Gujarat it is also Annakut, the mountain of food, "
            "and in Gujarat it begins the new year."
        ),
        observance=(
            "A small hill of cowdung or earth is shaped in the courtyard, decorated with flowers and "
            "grass, and worshipped at sunrise with parikrama around it. Annakut — dozens of dishes, "
            "fifty-six by custom — is offered to Krishna and then shared. Cows and bullocks are "
            "bathed, garlanded and fed first. Where the shila tradition holds, the Govardhan stone "
            "is given abhishek. It is a day of feeding, not of fasting."
        ),
    ),
    Festival(
        slug="bhai-dooj",
        name_en="Bhai Dooj",
        name_hi="भाई दूज",
        note_en="Sisters apply tilak on brothers' foreheads, pray for their long life. Brothers gift in return.",
        note_hi="बहनें भाई के माथे पर तिलक लगाती हैं, उनकी दीर्घायु की प्रार्थना। भाई बदले में उपहार देते हैं।",
        dates={2026: "2026-11-11", 2027: "2027-10-31", 2028: "2028-10-19"},
        rule="Kartika Shukla Dwitiya",
        observance_window="aparahna",
        significance=(
            "Bhai Dooj falls on the second tithi of Kartika's bright fortnight and closes the five "
            "days of Diwali. The story kept is of Yamuna receiving her brother Yama at her home, "
            "feeding him and marking his forehead, and of the boon he gave in return — that a "
            "brother who takes his sister's tilak on this day need not fear an untimely end. Where "
            "Raksha Bandhan places the sister under her brother's protection, Bhai Dooj turns the "
            "direction around: here it is her blessing, at her house."
        ),
        observance=(
            "The tilak is applied in the aparahna hours, at the sister's home by custom. She "
            "performs aarti, marks his forehead with roli and rice, feeds him a full meal she has "
            "cooked herself, and prays for his long life; he gives a gift in return. Many sisters "
            "eat only once the tilak is done. Brothers without a sister traditionally go to a "
            "cousin's house, or to a riverbank."
        ),
    ),
    # verified 2026-08-07 · Drik Panchang, New Delhi — year calendar page and monthly
    # calendar page, both "Chhath Puja" on Kartika Shukla Shashthi. Tithi confirmed
    # independently (pyswisseph): Shukla Shashthi current at the sandhya-arghya window
    # on all three dates. The date shipped is the Shashthi — the sandhya arghya — which
    # is day three of four; the usha arghya that ends the vrat is the next morning.
    Festival(
        slug="chhath-puja",
        name_en="Chhath Puja",
        name_hi="छठ पूजा",
        note_en="Arghya to the setting Sun, then to the rising one, standing in water — the hardest vrat in the calendar.",
        note_hi="जल में खड़े होकर पहले अस्ताचल और फिर उदयाचल सूर्य को अर्घ्य — पञ्चाङ्ग का कठिनतम व्रत।",
        dates={2026: "2026-11-15", 2027: "2027-11-04", 2028: "2028-10-23"},
        rule="Kartika Shukla Shashthi",
        observance_window="sandhya arghya at sunset, then usha arghya at sunrise",
        significance=(
            "Chhath is kept on the sixth tithi of Kartika's bright fortnight for Surya and "
            "for Chhathi Maiya, whom the tradition names as his sister and the protector of "
            "children, chiefly in Bihar, Jharkhand, eastern UP and the Nepal Terai. What "
            "sets it apart is the order of the offering: arghya goes first to the setting "
            "Sun and only afterwards to the rising one, and the tradition's own reading of "
            "that is direct — a thing in decline is owed the same regard as a thing at its "
            "height. It is also a lay observance in a way little else in the calendar is. "
            "There is no priest, no idol and no intermediary; the vrati stands in the water "
            "herself."
        ),
        observance=(
            "Four days: nahay-khay, then kharna with a single evening meal, then a nirjala "
            "fast of roughly thirty-six hours. On Shashthi evening the vrati stands in a "
            "river or pond and offers water and milk to the setting Sun from a bamboo soop "
            "carrying thekua, sugarcane, coconut, turmeric root and the season's fruit; the "
            "usha arghya at sunrise the next morning ends the fast. The prasad is cooked on "
            "a mud stove without salt or onion, and the cleanliness of its preparation is "
            "held to weigh as much as the fast itself."
        ),
    ),
    Festival(
        slug="tulsi-vivah",
        name_en="Tulsi Vivah",
        name_hi="तुलसी विवाह",
        note_en="Ceremonial marriage of Tulsi to Vishnu — marks the start of the Hindu wedding season.",
        note_hi="तुलसी का विष्णु से प्रतीकात्मक विवाह — हिन्दू विवाह ऋतु का शुभारम्भ।",
        dates={2026: "2026-11-21", 2027: "2027-11-11", 2028: "2028-10-29"},
        rule="Kartika Shukla Ekadashi/Dwadashi",
        observance_window="pradosh",
        significance=(
            "Tulsi Vivah is the ceremonial marriage of the tulsi plant to Vishnu in his shaligram "
            "form, kept on the eleventh or twelfth tithi of Kartika's bright fortnight, just after "
            "Devuthani Ekadashi when Vishnu is held to wake from the four months of Chaturmas. "
            "Because auspicious ceremonies pause through those months, this wedding is the first of "
            "the season and formally reopens the Hindu marriage calendar. Households without a "
            "daughter traditionally take on the merit of kanyadaan by performing it."
        ),
        observance=(
            "The tulsi pot is cleaned, given a small mandap of sugarcane, draped in a red chunri "
            "with bangles, and married to a shaligram or a Krishna murti at pradosh with the full "
            "wedding sequence — mangalashtak, the thread, the seven steps. Amla, tamarind and the "
            "season's fruit are offered. Many keep the Ekadashi fast the day before. Prasad is "
            "distributed as at any wedding."
        ),
    ),
)


BY_SLUG: dict[str, Festival] = {f.slug: f for f in FESTIVALS}


def get_festival(slug: str) -> Festival | None:
    """Look up a festival by slug. Returns None for unknown slugs."""
    return BY_SLUG.get(slug)


def _add_months(d: date, months: int) -> date:
    """Return `d` shifted forward by `months` calendar months.

    Clamps the day when the target month is shorter (31 Aug + 6 → 28/29 Feb),
    so the window end is a real date rather than a 30-day approximation.
    """
    total = (d.year * 12 + (d.month - 1)) + months
    year, month = divmod(total, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def upcoming(today: date, months: int = 6) -> list[tuple[date, Festival]]:
    """Every (date, festival) falling in [today, today + `months` months].

    Sorted ascending. Crosses year boundaries. Silently skips years we have no
    dates for, and skips any unparseable ISO string rather than raising — the
    hub should degrade to a shorter list, never to a 500.
    """
    end = _add_months(today, months)
    out: list[tuple[date, Festival]] = []
    for fest in FESTIVALS:
        for year in DATA_YEARS:
            iso = fest.dates.get(year)
            if not iso:
                continue
            try:
                d = date.fromisoformat(iso)
            except ValueError:
                continue
            if today <= d <= end:
                out.append((d, fest))
    out.sort(key=lambda pair: (pair[0], pair[1].slug))
    return out


def month_grid(
    today: date,
    entries: list[tuple[date, Festival]] | None = None,
    months: int = 6,
) -> list[dict]:
    """Month-by-month calendar scaffolding for the /festivals hub.

    Covers every calendar month touched by [today, today + `months` months] —
    so a 6-month window normally yields 7 blocks, the first and last of them
    partly outside the window.

    Built from `entries` (default: `upcoming(today, months)`) rather than from
    FESTIVALS directly, so the calendar and the card list below it are driven
    by exactly the same rows and cannot disagree about which days are marked.

    Returns, per month::

        {"year": 2026, "month": 10, "label_en": "October 2026",
         "weeks": [[cell | None, …7], …]}

    Weeks are Sunday-first (Indian convention); None is a leading or trailing
    blank. A cell is::

        {"day": 29, "date_iso": "2026-10-29", "is_today": False,
         "is_past": False, "festivals": [{"slug", "name_en", "name_hi", "tier"}, …]}

    `festivals` is a list, not a single entry: two festivals can legitimately
    fall on the same date, and dropping the second would make the grid quietly
    disagree with the cards.
    """
    if entries is None:
        entries = upcoming(today, months)

    by_date: dict[date, list[dict]] = {}
    for fest_date, fest in entries:
        by_date.setdefault(fest_date, []).append({
            "slug": fest.slug,
            "name_en": fest.name_en,
            "name_hi": fest.name_hi,
            "tier": fest.tier,
        })

    end = _add_months(today, months)
    cal = calendar.Calendar(firstweekday=6)  # 6 = Sunday
    out: list[dict] = []
    year, month = today.year, today.month
    while (year, month) <= (end.year, end.month):
        weeks: list[list[dict | None]] = []
        for raw_week in cal.monthdayscalendar(year, month):
            week: list[dict | None] = []
            for day in raw_week:
                if day == 0:
                    week.append(None)
                    continue
                d = date(year, month, day)
                week.append({
                    "day": day,
                    "date_iso": d.isoformat(),
                    "is_today": d == today,
                    "is_past": d < today,
                    "festivals": by_date.get(d, []),
                })
            weeks.append(week)
        out.append({
            "year": year,
            "month": month,
            "label_en": date(year, month, 1).strftime("%B %Y"),
            "weeks": weeks,
        })
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def learn_article_for(fest: Festival) -> "Article | None":
    """The /learn article for this festival, if one exists.

    Matches an article whose slug is exactly the festival slug or begins with
    `<slug>-` — so `karva-chauth` finds `karva-chauth-2026` and `diwali` finds
    `diwali-muhurat-2026`, while a short slug cannot swallow an unrelated
    article (`guru-purnima` will not match `guru-jupiter-in-vedic-astrology`).

    Most festivals have no article; None is the normal answer, not an error.
    Imported lazily — learn_registry is a large module and the emails that use
    festival data have no need for it.
    """
    from astro_ai import learn_registry

    prefix = fest.slug + "-"
    for article in learn_registry.all_articles():
        if article.slug == fest.slug or article.slug.startswith(prefix):
            return article
    return None
