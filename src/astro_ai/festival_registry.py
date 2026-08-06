"""Registry of named Hindu festivals — dates, classical rules, and copy.

Single source of truth for festival dates. `festivals.py` derives its
`FESTIVALS_BY_DATE` lookup table from this module at import time, and the
/festivals hub renders `significance` / `observance` inline.

Dates cover 2026-2028 (`DATA_YEARS`) and were verified on 2026-08-06 against
two independent sources that agreed on every row:
  (A) drikpanchang.com Hindu calendar, New Delhi (NCT), IST
  (B) Swiss Ephemeris tithi computation (pyswisseph 2.10.03, Lahiri sidereal,
      Delhi 28.6139N 77.2090E), checked against each festival's own observance
      window — pradosh / nishita / madhyahna / aparahna / moonrise — rather
      than against sunrise alone

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


DATA_YEARS: tuple[int, ...] = (2026, 2027, 2028)

SOURCE_NAME = "Drik Panchang"

SOURCE_URL_BY_YEAR: dict[int, str] = {
    2026: "https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=2026",
    2027: "https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=2027",
    2028: "https://www.drikpanchang.com/calendars/hindu/hinducalendar.html?year=2028",
}


# Calendar order by the 2026 date.
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
         "is_past": False, "festivals": [{"slug", "name_en", "name_hi"}, …]}

    `festivals` is a list, not a single entry: two festivals can legitimately
    fall on the same date, and dropping the second would make the grid quietly
    disagree with the cards.
    """
    if entries is None:
        entries = upcoming(today, months)

    by_date: dict[date, list[dict]] = {}
    for fest_date, fest in entries:
        by_date.setdefault(fest_date, []).append(
            {"slug": fest.slug, "name_en": fest.name_en, "name_hi": fest.name_hi}
        )

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
