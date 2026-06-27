"""Hindu festival calendar for the daily email.

Most major festivals fall on specific tithis of the Hindu calendar, so their
Gregorian date shifts each year. We hardcode the year-by-year mapping —
straightforward to maintain (one ~30-line dict per year, append a new year
each November when the Drikpanchang almanac releases the next year's dates).

The shape — `FESTIVALS_BY_DATE[year][YYYY-MM-DD]` → festival info — keeps
lookups O(1) per day and lets us cover specific year-specific quirks
(e.g. some festivals fall twice in some years due to lunar shifts).

Tithi-based daily observances (Ekadashi, Pradosh, Purnima, Amavasya) are
NOT here — they're computed from the day's tithi in shloks.py. This file
is only for named-festival callouts.
"""

from __future__ import annotations

from datetime import date


# ─── 2026 festival calendar ─────────────────────────────────────────────────
# Dates based on Drik Panchang for IST. Adjust if you trust a different
# almanac. Add 2027 entries by November 2026 — Drik publishes next year's
# tithi calendar around that time.
_FESTIVALS_2026: dict[str, dict] = {
    "2026-01-14": {
        "name_en": "Makar Sankranti",
        "name_hi": "मकर संक्रान्ति",
        "note_en": "Sun enters Capricorn — Uttarayana begins. Auspicious for new starts, charity, and bathing in holy rivers.",
        "note_hi": "सूर्य का मकर राशि में प्रवेश — उत्तरायण आरम्भ। नए कार्य, दान और पवित्र नदियों में स्नान के लिए शुभ।",
    },
    "2026-01-23": {
        "name_en": "Vasant Panchami",
        "name_hi": "वसन्त पञ्चमी",
        "note_en": "Saraswati Puja — honour the goddess of learning, music, and arts. Wear yellow.",
        "note_hi": "सरस्वती पूजा — ज्ञान, संगीत और कला की देवी का सम्मान। पीले वस्त्र धारण करें।",
    },
    "2026-02-15": {
        "name_en": "Maha Shivratri",
        "name_hi": "महा शिवरात्रि",
        "note_en": "The great night of Shiva. Fast, chant Om Namah Shivaya, stay awake for the four prahar of night worship.",
        "note_hi": "शिव की महानिशा। व्रत रखें, ॐ नमः शिवाय का जाप करें, चारों प्रहर जागरण करें।",
    },
    "2026-03-04": {
        "name_en": "Holi",
        "name_hi": "होली",
        "note_en": "Festival of colours — celebrate the victory of good over evil and the arrival of spring.",
        "note_hi": "रंगों का त्यौहार — बुराई पर अच्छाई की विजय और वसन्त के आगमन का उत्सव।",
    },
    "2026-04-06": {
        "name_en": "Ram Navami",
        "name_hi": "राम नवमी",
        "note_en": "Birth of Lord Rama — read or listen to Ramcharitmanas, visit a Ram temple, fast in remembrance.",
        "note_hi": "श्री राम जी का जन्मोत्सव — रामचरितमानस पढ़ें या सुनें, राम मन्दिर के दर्शन करें, स्मरण में व्रत रखें।",
    },
    "2026-04-23": {
        "name_en": "Hanuman Jayanti",
        "name_hi": "हनुमान जयन्ती",
        "note_en": "Birth of Hanuman ji. Recite Hanuman Chalisa, especially powerful on this day.",
        "note_hi": "हनुमान जी का जन्मोत्सव। हनुमान चालीसा का पाठ करें — इस दिन विशेष फलदायी।",
    },
    "2026-07-09": {
        "name_en": "Guru Purnima",
        "name_hi": "गुरु पूर्णिमा",
        "note_en": "Pay reverence to your gurus — spiritual, scholastic, parental. The day Jupiter's energy is strongest.",
        "note_hi": "अपने गुरुओं को नमन करें — आध्यात्मिक, विद्या के, मातापिता। इस दिन गुरु ग्रह की ऊर्जा सर्वाधिक प्रबल।",
    },
    "2026-08-09": {
        "name_en": "Raksha Bandhan",
        "name_hi": "रक्षा बन्धन",
        "note_en": "Sisters tie rakhi on brothers' wrists, exchange love and the promise of lifelong protection.",
        "note_hi": "बहन भाई की कलाई पर राखी बाँधती है, प्रेम और आजीवन रक्षा का वचन।",
    },
    "2026-09-04": {
        "name_en": "Krishna Janmashtami",
        "name_hi": "जन्माष्टमी",
        "note_en": "Midnight birth of Krishna — fast until midnight, sing bhajans, dress an infant Krishna idol.",
        "note_hi": "श्री कृष्ण का मध्यरात्रि जन्म — मध्यरात्रि तक उपवास, भजन गाएँ, बाल कृष्ण को वस्त्र पहनाएँ।",
    },
    "2026-09-14": {
        "name_en": "Ganesh Chaturthi",
        "name_hi": "गणेश चतुर्थी",
        "note_en": "Welcome Ganesh ji home. Begins 10 days of devotion ending in Visarjan.",
        "note_hi": "गणेश जी का स्वागत। 10 दिनों की भक्ति जो विसर्जन से समाप्त होती है।",
    },
    "2026-10-09": {
        "name_en": "Navratri (begins)",
        "name_hi": "नवरात्रि (आरम्भ)",
        "note_en": "Nine nights of Devi worship — each night honours one form of the Goddess. Fast, chant, and dance.",
        "note_hi": "नौ रातें देवी आराधना की — हर रात्रि देवी के एक रूप का सम्मान। व्रत, जप, और गरबा।",
    },
    "2026-10-18": {
        "name_en": "Dussehra (Vijayadashami)",
        "name_hi": "दशहरा",
        "note_en": "Victory of Rama over Ravana — start anything new today, it carries the blessing of dharma.",
        "note_hi": "रावण पर राम की विजय — आज कुछ भी नया आरम्भ करें, धर्म का आशीर्वाद साथ रहता है।",
    },
    "2026-11-05": {
        "name_en": "Karva Chauth",
        "name_hi": "करवा चौथ",
        "note_en": "Married women fast for the long life of their husband. Sight the moon, then break the fast.",
        "note_hi": "विवाहित स्त्रियाँ पति की दीर्घायु के लिए व्रत रखती हैं। चन्द्र दर्शन के बाद व्रत खोला जाता है।",
    },
    "2026-11-08": {
        "name_en": "Diwali (Deepavali)",
        "name_hi": "दीपावली",
        "note_en": "Festival of lights — Lakshmi Puja in the evening welcomes prosperity. Clean the home, light diyas, set off no firecrackers indoors.",
        "note_hi": "दीपों का त्यौहार — सायंकाल लक्ष्मी पूजा से समृद्धि का स्वागत। घर साफ करें, दीये जलाएँ।",
    },
    "2026-11-09": {
        "name_en": "Govardhan Puja",
        "name_hi": "गोवर्धन पूजा",
        "note_en": "The day Krishna lifted Mt Govardhan — honour cows, prepare annakut (mountain of food).",
        "note_hi": "जिस दिन कृष्ण ने गोवर्धन पर्वत उठाया — गायों का सम्मान, अन्नकूट तैयार करें।",
    },
    "2026-11-11": {
        "name_en": "Bhai Dooj",
        "name_hi": "भाई दूज",
        "note_en": "Sisters apply tilak on brothers' foreheads, pray for their long life. Brothers gift in return.",
        "note_hi": "बहनें भाई के माथे पर तिलक लगाती हैं, उनकी दीर्घायु की प्रार्थना। भाई बदले में उपहार देते हैं।",
    },
    "2026-11-25": {
        "name_en": "Tulsi Vivah",
        "name_hi": "तुलसी विवाह",
        "note_en": "Ceremonial marriage of Tulsi to Vishnu — marks the start of the Hindu wedding season.",
        "note_hi": "तुलसी का विष्णु से प्रतीकात्मक विवाह — हिन्दू विवाह ऋतु का शुभारम्भ।",
    },
}


FESTIVALS_BY_DATE: dict[int, dict[str, dict]] = {
    2026: _FESTIVALS_2026,
}


def festival_for_date(d: date) -> dict | None:
    """Look up the festival on `d`, if any. Returns the bilingual entry or None.

    Falls back gracefully if we don't yet have entries for the year — just
    returns None so the email still sends, sans festival callout.
    """
    year_table = FESTIVALS_BY_DATE.get(d.year)
    if year_table is None:
        return None
    return year_table.get(d.isoformat())
