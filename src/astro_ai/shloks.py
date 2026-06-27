"""Astrology-related shloks for the daily email and homepage.

Two collections:

  GRAHA_SHLOKS — 7 entries, one per weekday, each invoking the day's
  presiding graha (Sun for Sunday, Moon for Monday, etc.). In Vedic
  tradition each day of the week is sacred to one of the navagraha:

      Sunday    → Surya (Sun)
      Monday    → Chandra (Moon)
      Tuesday   → Mangal (Mars)
      Wednesday → Budh (Mercury)
      Thursday  → Brihaspati / Guru (Jupiter)
      Friday    → Shukra (Venus)
      Saturday  → Shani (Saturn)

  TITHI_OBSERVANCES — tithi-based spiritual days (Ekadashi, Pradosh,
  Purnima, Amavasya). Looked up by tithi number computed by chart.py's
  Panchang. Independent of weekday.

Both are content-only — no LLM calls, no external lookups.
"""

from __future__ import annotations

from datetime import date


# ─── Graha shloks, indexed by weekday number ────────────────────────────────
# Python's date.weekday(): Monday=0 ... Sunday=6.
# We index from Sunday=0 for readability — convert via `(d.weekday() + 1) % 7`.
GRAHA_SHLOKS: list[dict] = [
    {  # Sunday
        "weekday_name": "Sunday",
        "graha_en": "Surya (Sun)",
        "graha_hi": "सूर्य",
        "sanskrit": "ॐ सूर्याय नमः ।",
        "transliteration": "Om Suryaya Namah.",
        "meaning_en": "Salutations to Surya, the source of all life and clarity. Sunday is His day — pay respects to the rising Sun.",
        "meaning_hi": "सूर्य देव को नमस्कार, समस्त जीवन और प्रकाश के स्रोत। रविवार उनका दिन है — उगते सूर्य को प्रणाम करें।",
    },
    {  # Monday
        "weekday_name": "Monday",
        "graha_en": "Chandra (Moon)",
        "graha_hi": "चन्द्र",
        "sanskrit": "ॐ सोमाय नमः ।",
        "transliteration": "Om Somaya Namah.",
        "meaning_en": "Salutations to Chandra, ruler of the mind and emotions. Monday calms the mind — fast lightly, drink water, be gentle.",
        "meaning_hi": "चन्द्र देव को नमस्कार, मन और भावनाओं के स्वामी। सोमवार मन को शान्त करता है — हल्का व्रत रखें, जल पिएं, कोमल रहें।",
    },
    {  # Tuesday
        "weekday_name": "Tuesday",
        "graha_en": "Mangal (Mars)",
        "graha_hi": "मंगल",
        "sanskrit": "ॐ अं अङ्गारकाय नमः ।",
        "transliteration": "Om Am Angarakaya Namah.",
        "meaning_en": "Salutations to Mangal, ruler of courage and action. Tuesday is for facing what scares you — and Hanuman ji's blessings.",
        "meaning_hi": "मंगल देव को नमस्कार, साहस और कर्म के स्वामी। मंगलवार उस बात का सामना करने का दिन है जो डराती है — और हनुमान जी के आशीर्वाद का।",
    },
    {  # Wednesday
        "weekday_name": "Wednesday",
        "graha_en": "Budh (Mercury)",
        "graha_hi": "बुध",
        "sanskrit": "ॐ बुं बुधाय नमः ।",
        "transliteration": "Om Bum Budhaya Namah.",
        "meaning_en": "Salutations to Budh, ruler of intellect and communication. Wednesday favors learning, writing, and clear words.",
        "meaning_hi": "बुध देव को नमस्कार, बुद्धि और संवाद के स्वामी। बुधवार सीखने, लिखने और स्पष्ट वाणी के लिए शुभ है।",
    },
    {  # Thursday
        "weekday_name": "Thursday",
        "graha_en": "Brihaspati (Jupiter)",
        "graha_hi": "बृहस्पति",
        "sanskrit": "ॐ बृं बृहस्पतये नमः ।",
        "transliteration": "Om Brim Brihaspataye Namah.",
        "meaning_en": "Salutations to Guru Brihaspati, ruler of wisdom and dharma. Thursday is the day for guidance — listen to elders, study scripture.",
        "meaning_hi": "गुरु बृहस्पति को नमस्कार, ज्ञान और धर्म के स्वामी। गुरुवार मार्गदर्शन का दिन है — बड़ों की सुनें, शास्त्र पढ़ें।",
    },
    {  # Friday
        "weekday_name": "Friday",
        "graha_en": "Shukra (Venus)",
        "graha_hi": "शुक्र",
        "sanskrit": "ॐ शुं शुक्राय नमः ।",
        "transliteration": "Om Shum Shukraya Namah.",
        "meaning_en": "Salutations to Shukra, ruler of love, beauty, and pleasure. Friday favors relationships, art, and gentle indulgence.",
        "meaning_hi": "शुक्र देव को नमस्कार, प्रेम, सौन्दर्य और सुख के स्वामी। शुक्रवार सम्बन्धों, कला और सौम्य भोग के लिए शुभ है।",
    },
    {  # Saturday
        "weekday_name": "Saturday",
        "graha_en": "Shani (Saturn)",
        "graha_hi": "शनि",
        "sanskrit": "ॐ शं शनैश्चराय नमः ।",
        "transliteration": "Om Sham Shanaishcharaya Namah.",
        "meaning_en": "Salutations to Shani Dev, the great teacher who tests through patience. Saturday is for service, charity, and accepting karma's lessons.",
        "meaning_hi": "शनि देव को नमस्कार, धैर्य से परीक्षा लेने वाले महान गुरु। शनिवार सेवा, दान और कर्म के पाठ स्वीकारने का दिन है।",
    },
]


def shlok_for_date(d: date) -> dict:
    """Return the graha shlok appropriate for the day of the week.

    Sunday → index 0, Monday → 1, ... Saturday → 6. Python's
    date.weekday() returns Monday=0; we shift so Sunday=0.
    """
    sunday_indexed = (d.weekday() + 1) % 7
    return GRAHA_SHLOKS[sunday_indexed]


# ─── Tithi-based observances ────────────────────────────────────────────────
# Tithi values returned by compute_panchang() are 1..30 (1-15 = Shukla
# fortnight, 16-30 = Krishna fortnight). Some observances repeat in both
# fortnights (Ekadashi happens twice a month, both 11 and 26).

TITHI_OBSERVANCES: dict[int, dict] = {
    11: {  # Shukla Ekadashi
        "name_en": "Ekadashi",
        "name_hi": "एकादशी",
        "note_en": "Auspicious for fasting, spiritual practice, and offerings to Vishnu.",
        "note_hi": "व्रत, साधना और विष्णु जी की आराधना के लिए शुभ।",
    },
    13: {  # Shukla Trayodashi → Pradosh
        "name_en": "Pradosh Vrat",
        "name_hi": "प्रदोष व्रत",
        "note_en": "Sacred to Shiva. Evening worship between sunset and night brings blessings.",
        "note_hi": "शिव जी को समर्पित। सूर्यास्त और रात्रि के बीच की पूजा फलदायी।",
    },
    15: {  # Purnima
        "name_en": "Purnima",
        "name_hi": "पूर्णिमा",
        "note_en": "Full moon — favourable for meditation, mantra chanting, and acts of generosity.",
        "note_hi": "पूर्णिमा — ध्यान, मंत्र जप और दानशीलता के लिए शुभ।",
    },
    26: {  # Krishna Ekadashi
        "name_en": "Ekadashi",
        "name_hi": "एकादशी",
        "note_en": "Auspicious for fasting, spiritual practice, and offerings to Vishnu.",
        "note_hi": "व्रत, साधना और विष्णु जी की आराधना के लिए शुभ।",
    },
    28: {  # Krishna Trayodashi → Pradosh
        "name_en": "Pradosh Vrat",
        "name_hi": "प्रदोष व्रत",
        "note_en": "Sacred to Shiva. Evening worship between sunset and night brings blessings.",
        "note_hi": "शिव जी को समर्पित। सूर्यास्त और रात्रि के बीच की पूजा फलदायी।",
    },
    30: {  # Amavasya
        "name_en": "Amavasya",
        "name_hi": "अमावस्या",
        "note_en": "New moon — auspicious for honouring ancestors (Pitr Tarpan) and inward reflection.",
        "note_hi": "अमावस्या — पितृ तर्पण और आत्म-चिन्तन के लिए शुभ।",
    },
}


def observance_for_tithi(tithi: int | None) -> dict | None:
    """Lookup the spiritual observance for today's tithi, if any."""
    if tithi is None:
        return None
    return TITHI_OBSERVANCES.get(tithi)
