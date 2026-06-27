"""Rotating "Did you know" facts for the daily email.

Each entry is a short Vedic-astrology fact that builds reader knowledge
gradually. Index rotates daily by day-of-year so the same fact recurs ~once
a month (with 30 facts → ~12 cycles per year, manageable repetition).

Content principles:
  - Surprising or genuinely useful (not "the sun is in the centre of the
    solar system" trivia)
  - One concept per entry — Vedic astrology has plenty of depth without
    needing essays
  - 1-2 sentences max — emails should be skimmable
  - Bilingual (en + hi) — same fact, same length-feel in both
"""

from __future__ import annotations

from datetime import date


DID_YOU_KNOW: list[dict[str, str]] = [
    {
        "en": "Your Janma Rashi (Moon sign) is what drives your daily Rashifal — not your Sun sign. Vedic astrology centres the mind, which the Moon rules.",
        "hi": "आपकी दैनिक राशिफल आपकी जन्म राशि (चन्द्र राशि) पर आधारित है — सूर्य राशि पर नहीं। वैदिक ज्योतिष मन को महत्व देता है, जिसका स्वामी चन्द्र है।",
    },
    {
        "en": "The zodiac is divided into 27 nakshatras of 13°20′ each. Your birth nakshatra reveals personality details that the rashi alone can miss.",
        "hi": "राशिचक्र 27 नक्षत्रों में बँटा है, प्रत्येक 13°20' का। जन्म नक्षत्र वो विवरण बताता है जो केवल राशि से नहीं मिलता।",
    },
    {
        "en": "Saturn takes about 30 years to circle the zodiac, so Sade Sati (7.5 years) comes at most 2-3 times in a lifetime — making each one a lasting lesson.",
        "hi": "शनि को राशिचक्र पूरा करने में ~30 वर्ष लगते हैं, इसलिए साढ़े साती (7.5 वर्ष) जीवन में अधिकतम 2-3 बार आती है — हर बार गहरा पाठ देती है।",
    },
    {
        "en": "Jupiter (Guru) changes signs every ~13 months. When it transits over your Sun, Moon, or Lagna, doors open — note the dates and act.",
        "hi": "गुरु ~13 महीनों में राशि बदलता है। जब वह आपके सूर्य, चन्द्र या लग्न पर गोचर करता है, अवसर खुलते हैं — तिथि नोट करें और कार्य करें।",
    },
    {
        "en": "Rahu and Ketu aren't physical planets — they're the points where the Moon's orbit crosses the Sun's path. Yet their effects on the mind are profound.",
        "hi": "राहु और केतु भौतिक ग्रह नहीं हैं — ये वो बिन्दु हैं जहाँ चन्द्र की कक्षा सूर्य के मार्ग को काटती है। फिर भी इनका मन पर गहरा प्रभाव है।",
    },
    {
        "en": "Mars rules both Aries and Scorpio. Venus rules both Taurus and Libra. Each planet rules exactly two signs — except the Sun and Moon, which rule one each.",
        "hi": "मंगल मेष और वृश्चिक दोनों का स्वामी है। शुक्र वृष और तुला का। प्रत्येक ग्रह दो राशियों का स्वामी है — सूर्य और चन्द्र को छोड़कर, जो एक-एक के स्वामी हैं।",
    },
    {
        "en": "Vimshottari Dasha divides 120 years into 9 planetary periods — Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17.",
        "hi": "विम्शोत्तरी दशा 120 वर्षों को 9 ग्रह अवधियों में बाँटती है — केतु 7, शुक्र 20, सूर्य 6, चन्द्र 10, मंगल 7, राहु 18, गुरु 16, शनि 19, बुध 17।",
    },
    {
        "en": "Mercury never moves more than 28° from the Sun in the sky. That's why Mercury rules quick, near-by thinking and short trips.",
        "hi": "बुध आकाश में सूर्य से 28° से अधिक दूर नहीं जाता। इसीलिए बुध चपल बुद्धि और छोटी यात्राओं का स्वामी है।",
    },
    {
        "en": "Mangal Dosh only matters in marriage if both partners have it — they cancel each other out. One-sided Manglik isn't an automatic block.",
        "hi": "मांगलिक दोष विवाह में तभी मायने रखता है जब दोनों साथियों में हो — दोनों एक-दूसरे को रद्द कर देते हैं। एक-तरफ़ा मांगलिक स्वतः बाधा नहीं है।",
    },
    {
        "en": "Each nakshatra is ruled by a deity, planet, and element. Pushya nakshatra is the most auspicious — its very name means 'nourishing'.",
        "hi": "प्रत्येक नक्षत्र का एक देवता, ग्रह और तत्व है। पुष्य नक्षत्र सबसे शुभ है — इसका अर्थ ही है 'पोषक'।",
    },
    {
        "en": "The Lagna (rising sign) changes every ~2 hours, while the Moon takes ~2.25 days per sign. That's why birth time matters far more than birth date alone.",
        "hi": "लग्न ~2 घंटे में बदलता है, जबकि चन्द्र को एक राशि पार करने में ~2.25 दिन लगते हैं। इसीलिए जन्म तिथि से अधिक जन्म समय मायने रखता है।",
    },
    {
        "en": "There are 12 houses (bhavas) in a chart, each governing a life area — 1st is self, 7th is partner, 10th is career, 4th is home and mother.",
        "hi": "कुंडली में 12 भाव होते हैं, प्रत्येक जीवन के एक क्षेत्र का स्वामी — 1ला स्वयं, 7वाँ साथी, 10वाँ कर्म, 4था घर और माता।",
    },
    {
        "en": "A Yoga in astrology is a special planet combination that produces a specific result. Gaja Kesari Yoga (Jupiter + Moon together or aspecting) brings wisdom and respect.",
        "hi": "ज्योतिष में योग एक विशेष ग्रह संयोग है जो ख़ास फल देता है। गज केसरी योग (गुरु + चन्द्र एक साथ या दृष्टि से) ज्ञान और सम्मान लाता है।",
    },
    {
        "en": "The four padas of each nakshatra (3°20′ each) link to one of the 12 rashis — so your nakshatra-pada gives finer character detail than rashi alone.",
        "hi": "प्रत्येक नक्षत्र के चार पाद (3°20' का प्रत्येक) किसी एक राशि से जुड़े हैं — इसलिए नक्षत्र-पाद केवल राशि से अधिक चरित्र-विवरण देता है।",
    },
    {
        "en": "Rahu Kaal — about 90 minutes daily — is considered inauspicious for starting new ventures. Its timing varies by sunrise and weekday.",
        "hi": "राहु काल — दैनिक लगभग 90 मिनट — नये कार्य आरम्भ करने के लिए अशुभ माना जाता है। इसका समय सूर्योदय और वार के अनुसार बदलता है।",
    },
    {
        "en": "Abhijit Muhurta is the most auspicious 48-minute window of the day, centred on local solar noon. Good for signing, starting, deciding.",
        "hi": "अभिजित मुहूर्त दिन की सबसे शुभ 48 मिनट की अवधि है, जो स्थानीय सौर मध्याह्न पर केंद्रित होती है। हस्ताक्षर, आरम्भ, निर्णय के लिए श्रेष्ठ।",
    },
    {
        "en": "Vedic astrology uses the sidereal zodiac (fixed to stars), while Western uses tropical (fixed to seasons). The difference is ~24° — why your Western 'Sun sign' is often one rashi later.",
        "hi": "वैदिक ज्योतिष सायन (तारों से स्थिर) राशिचक्र प्रयोग करता है, पश्चिमी निरयन (ऋतुओं से स्थिर)। अंतर ~24° है — इसलिए आपकी पश्चिमी 'सूर्य राशि' अक्सर एक राशि बाद होती है।",
    },
    {
        "en": "Sun (Surya) is exalted in Aries and debilitated in Libra — opposite signs. Each planet has its own exaltation and debilitation point.",
        "hi": "सूर्य मेष में उच्च और तुला में नीच होता है — विपरीत राशियाँ। प्रत्येक ग्रह की अपनी उच्च और नीच राशि होती है।",
    },
    {
        "en": "Ashtakoot matching scores compatibility on 8 dimensions — 36 max points. 18+ is considered acceptable; 28+ excellent for marriage.",
        "hi": "अष्टकूट मिलान 8 आयामों में संगति आँकता है — कुल 36 अंक। 18+ स्वीकार्य; 28+ विवाह के लिए उत्कृष्ट।",
    },
    {
        "en": "The Moon spends about 2.25 days in each rashi — so within 27 days it visits all 12. Your tithi (lunar day) cycles every ~29.5 days.",
        "hi": "चन्द्र प्रत्येक राशि में ~2.25 दिन रहता है — इसलिए 27 दिनों में सभी 12 का भ्रमण करता है। आपकी तिथि (चन्द्र दिन) हर ~29.5 दिनों में पुनरावृत्त होती है।",
    },
    {
        "en": "Friday (शुक्रवार) is named for Shukra (Venus). Saturday (शनिवार) for Shani (Saturn). Every Indian weekday is named after a planet — a daily reminder of the navagraha.",
        "hi": "शुक्रवार शुक्र के नाम पर है। शनिवार शनि के नाम पर। प्रत्येक भारतीय वार किसी ग्रह के नाम पर है — दैनिक नवग्रह स्मरण।",
    },
    {
        "en": "The four pillars of Vedic astrology are: Lagna (rising sign — self), Moon (mind), Sun (soul), and Saptamesha (7th lord — partner).",
        "hi": "वैदिक ज्योतिष के चार स्तम्भ हैं: लग्न (स्वयं), चन्द्र (मन), सूर्य (आत्मा), और सप्तमेश (7वें भाव का स्वामी — साथी)।",
    },
    {
        "en": "Karaka means 'significator' — a planet that represents a life area. Jupiter is the karaka of children and wisdom; Venus, of partnership.",
        "hi": "कारक का अर्थ 'सूचक' — ग्रह जो किसी जीवन-क्षेत्र का प्रतिनिधि होता है। गुरु संतान और ज्ञान का कारक है; शुक्र, साथीत्व का।",
    },
    {
        "en": "Bhukti is the sub-period inside a Dasha. While Saturn's Mahadasha runs 19 years, you live through 9 bhuktis within it — each phase brings its own flavour.",
        "hi": "भुक्ति दशा के भीतर की उप-अवधि है। शनि की महादशा 19 वर्ष चलती है, पर उसमें 9 भुक्तियाँ होती हैं — प्रत्येक का अपना रंग।",
    },
    {
        "en": "Sade Sati happens in 3 phases — Saturn in the rashi before, on, and after your Moon. Each phase brings a different lesson; only the middle is most intense.",
        "hi": "साढ़े साती तीन चरणों में होती है — शनि आपकी चन्द्र राशि से पहले, उस पर, और बाद की राशि में। हर चरण अलग पाठ देता है; केवल बीच वाला सबसे तीव्र होता है।",
    },
    {
        "en": "The Sun spends about 30 days in each rashi. The date it changes signs is Sankranti — Makar Sankranti (Sun into Capricorn) on ~14 January is among the most celebrated.",
        "hi": "सूर्य प्रत्येक राशि में ~30 दिन रहता है। राशि बदलने का दिन संक्रांति है — मकर संक्रांति (सूर्य का मकर में प्रवेश) ~14 जनवरी सबसे प्रसिद्ध में से एक है।",
    },
    {
        "en": "Each nakshatra has a presiding deity — Magha is ruled by the Pitrs (ancestors), Mrigashira by Soma (the moon-god), and Rohini by Brahma.",
        "hi": "प्रत्येक नक्षत्र का एक अधिष्ठाता देव है — मघा के स्वामी पितृ हैं, मृगशिरा के सोम, और रोहिणी के ब्रह्मा।",
    },
    {
        "en": "Mars (Mangal) takes ~18 months in each sign during direct motion but ~6 months when retrograde — that's why Mangal periods often feel slow then sudden.",
        "hi": "मंगल प्रत्यक्ष गति में प्रत्येक राशि में ~18 महीने रहता है, पर वक्री में ~6 महीने — इसीलिए मंगल काल अक्सर पहले धीमा फिर तीव्र लगता है।",
    },
    {
        "en": "Birth time within 4 minutes' accuracy is enough for most chart calculations — but for Dasha and ashtakavarga, even 1-minute precision matters.",
        "hi": "अधिकांश कुंडली गणनाओं के लिए 4 मिनट तक की जन्म समय परिशुद्धता पर्याप्त है — पर दशा और अष्टकवर्ग के लिए 1 मिनट की भी मायने रखती है।",
    },
    {
        "en": "Vedic astrology doesn't predict fixed fate — it shows tendencies. Free will + remedy (mantra, charity, dharma) can soften any prediction.",
        "hi": "वैदिक ज्योतिष नियत भाग्य की भविष्यवाणी नहीं करता — यह प्रवृत्तियाँ दिखाता है। स्वतंत्र इच्छा + उपाय (मंत्र, दान, धर्म) किसी भी भविष्यवाणी को मृदु कर सकते हैं।",
    },
]


def trivia_for_date(d: date) -> dict[str, str]:
    """Pick the trivia for a given date by day-of-year, cycling through the list."""
    return DID_YOU_KNOW[d.timetuple().tm_yday % len(DID_YOU_KNOW)]
