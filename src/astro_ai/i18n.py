"""Tiny i18n module — flat translation dict + a Jinja-registered `t()` callable.

This is *not* full Babel/gettext — just a key → translated string lookup with
optional `str.format(**kwargs)` substitution. Fine for the handful of pages
we have; revisit if the surface grows.

Templates use it as `{{ t('rahu_kaal') }}` or `{{ t('outlook_named', name=...) }}`.
The active language is bound per-request in `main.py` via a Jinja context filter.
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------

# English is the fallback for any missing Hindi key, so it must be complete.
_EN: Final[dict[str, str]] = {
    # nav / common — labels chosen to match what readers actually search for
    # (matches AstroSage / Indian-astro convention).
    "nav_print":           "Print",
    "nav_home":            "Home",
    "nav_today_link":      "Today's Horoscope",
    "nav_natal_link":      "Kundli",
    "back_form":           "Back to the form",
    "new_reading":         "New reading",

    # today page header
    "outlook_named":       "{name}'s outlook",
    "outlook_anonymous":   "Your outlook today",
    "outlook_subtitle":    "Based on your natal chart (Lagna in {lagna}) and today's transits.",
    "today_label":         "Today",

    # transit chips
    "moon_transits":       "Moon transits",
    "sun_transits":        "Sun transits",
    "house_from_lagna":    "House {n} from natal Lagna",
    "nakshatra_suffix":    "Nakshatra",

    # sade sati badge
    "sade_sati":           "Sade Sati",
    "phase_rising":        "rising phase",
    "phase_peak":          "peak phase",
    "phase_setting":       "setting phase",

    # panchang section
    "todays_panchang":     "Today's Panchang",
    "ruled_by":            "ruled by",
    "rahu_kaal":           "Rahu Kaal",
    "rahu_kaal_tag":       "Avoid",
    "rahu_kaal_desc":      "Inauspicious window. Avoid starting new ventures, signing important papers, or big decisions during this time.",
    "abhijit_muhurta":     "Abhijit Muhurta",
    "abhijit_tag":         "Best time",
    "abhijit_desc":        "Most auspicious window of the day. Favourable for important actions, meetings, signing, beginnings.",
    "favourable_colour":   "Today's colour",
    "colour_caption":      "Associated with {lord}, the lord of {weekday}.",
    "solar_window":        "Sunrise & sunset",
    "solar_window_desc":   "Sunrise to sunset at your natal birthplace, used to derive today's Muhurta windows.",

    # daily reading
    "todays_reading":      "Today's reading",
    "all_transits_today":  "All transits today",
    "now_in":              "now in",
    "transiting_house":    "transiting your natal house",
    "computed_for":        "Computed for {moment}. Houses are reckoned from your natal Lagna in {lagna}.",
    "refresh_today":       "Refresh today",
    "back_home":           "Back home",

    # natal page - common
    "natal_title":         "{name}'s reading",
    "natal_title_anon":    "Your reading",
    "natal_subtitle":      "Born {date} at {time} · {place}",
    "lagna":               "Lagna",
    "moon_rashi":          "Moon · Rashi",
    "sun_rashi":           "Sun · Rashi",
    "computed_chart":      "Computed chart",
    "lagna_kundali":       "Lagna Kundali",
    "planetary_positions": "Planetary positions",
    "continue_chart":      "Continue your chart",
    "continue_chart_desc": "Now that we have your birth details, more readings unlock with one click.",
    "daily_horoscope":     "Daily horoscope",
    "daily_horoscope_desc":"Today's transits read against your natal chart — not a Sun-sign template.",
    "kundali_matching":    "Kundali matching",
    "kundali_matching_desc":"Ashtakoot Guna Milan for marriage compatibility against another chart.",
    "dasha_periods":       "Dasha periods",
    "dasha_periods_desc":  "Your active Vimshottari Mahadasha and Antardasha, plus what's next.",
    "badge_live":          "Live",
    "badge_soon":          "Soon",
    "generate_another":    "Generate another reading",
    "your_reading":        "Your reading",

    # Marriage & Love panel
    "marriage_title":      "Marriage & Love",
    "marriage_subtitle":   "What the 7th house and Venus suggest for partnership",
    "marriage_seventh":    "7th House (Kalatra Bhava)",
    "marriage_seventh_sign": "Sign",
    "marriage_lord":       "Lord",
    "marriage_occupants":  "Planets in 7th",
    "marriage_no_occupants": "no planets",
    "marriage_venus":      "Venus — love and romance",
    "marriage_in_house":   "in House {n}",
    "marriage_manglik_note":"Manglik dosha is present in this chart — see Mangal Dosh panel below for what it means and how cancellations may apply.",

    # Wealth & Money panel
    "wealth_title":        "Wealth & Money",
    "wealth_subtitle":     "What the 2nd house, 11th house, and Jupiter suggest about money",
    "wealth_dhana":        "2nd House (Dhana Bhava)",
    "wealth_dhana_desc":   "Accumulated wealth · family money · speech",
    "wealth_labha":        "11th House (Labha Bhava)",
    "wealth_labha_desc":   "Gains · income · fulfilled aspirations",
    "wealth_jupiter":      "Jupiter — wealth significator",
    "wealth_planets_label":"Planets",
    "wealth_no_planets":   "none",

    # Mangal Dosh explanatory panel
    "manglik_title":       "Mangal Dosh (Manglik)",
    "manglik_present":     "Present in this chart",
    "manglik_severity_high":     "High severity",
    "manglik_severity_moderate": "Moderate severity",
    "manglik_severity_low":      "Low severity",
    "manglik_houses_label":"Qualifying placements",
    "manglik_house_lagna": "Mars in {ord} house from Lagna",
    "manglik_house_moon":  "Mars in {ord} house from Moon",
    "manglik_about_label": "What this means",
    "manglik_about_high":  "Mars sitting in the 7th or 8th house from your Lagna or Moon is the most-discussed form of Manglik. Classically it suggests friction, restlessness, or assertive energy in marital matters, with the 7th house (partnership) and 8th house (spouse's longevity, transformation) being the most-cited concerns. The actual effect varies enormously with the rest of the chart.",
    "manglik_about_moderate":"Mars in the 1st, 4th, or 12th house is a moderate form of Manglik. The 1st affects personality and restlessness; the 4th affects home and inner peace; the 12th affects private life and expenses. Often less severe than 7th/8th placements but still worth noting.",
    "manglik_about_low":   "Mars in the 2nd house is the mildest form of Manglik, primarily affecting speech and family dynamics. Some traditions exclude 2nd-house Manglik entirely.",
    "manglik_cancel_label":"Possible cancellations",
    "manglik_cancel_text": "Manglik dosha is classically considered cancelled or mitigated when: Mars is in its own sign (Aries or Scorpio) or exalted (Capricorn); the spouse is also Manglik (matching cancels); Jupiter aspects Mars; specific conjunctions or benefic aspects apply. These cancellations are not computed here — consult a knowledgeable astrologer to determine if any apply to this chart.",

    # Sade Sati explanatory panel
    "sade_sati_title":     "Sade Sati",
    "sade_sati_active":    "Currently active",
    "sade_sati_duration":  "7.5 years total · 3 phases of ~2.5 years each",
    "sade_sati_rising_title": "Rising Phase (Arohini)",
    "sade_sati_peak_title":   "Peak Phase (Madhya)",
    "sade_sati_setting_title":"Setting Phase (Avarohini)",
    "sade_sati_rising_about": "Saturn is currently transiting the 12th house from your natal Moon — the opening phase of the 7.5-year Sade Sati cycle. This is the preparatory phase: pressures begin to build slowly.",
    "sade_sati_peak_about":   "Saturn is currently transiting your natal Moon's own sign — the midpoint and most-testing phase of the 7.5-year cycle. The pressure is most direct here.",
    "sade_sati_setting_about":"Saturn is currently transiting the 2nd house from your natal Moon — the closing phase of the 7.5-year cycle, focused on consolidation and gradual release.",
    "sade_sati_themes_label": "Common themes",
    "sade_sati_rising_themes":"Inner restructuring · sleep and dream changes · spiritual stirrings · careful finance management · foreign travel · late-night challenges",
    "sade_sati_peak_themes":  "Physical health attention · identity questions · slow progress · work overload · periods of isolation · family responsibilities",
    "sade_sati_setting_themes":"Wealth and savings shifts · family dynamics · speech matters · slow consolidation · gradual recovery",
    "sade_sati_guidance_label":"How to navigate",
    "sade_sati_rising_guidance":"Practice patience. Develop a daily discipline — meditation, exercise, journaling. Manage finances carefully. Use the inner stirring for genuine reflection rather than fighting it.",
    "sade_sati_peak_guidance":  "Focus on physical health and quiet routines. Accept limitations as teachers. Do disciplined work and avoid major life risks. The pressure is real but constructive — Saturn rewards integrity here.",
    "sade_sati_setting_guidance":"Be measured in speech. Rebuild finances steadily. Mend family rifts. Consolidate gains. This is where seeds planted during the cycle begin to mature.",

    # gochar highlights panel
    "gochar_title":        "Gochar (Slow Transits)",
    "gochar_subtitle":     "The slow-mover chapter the sky is writing — these define the multi-month backdrop",
    "gochar_house_lagna":  "{n}th from Lagna",
    "gochar_house_moon":   "{n}th from Moon",
    "favorability_favorable":    "Favorable",
    "favorability_neutral":      "Neutral",
    "favorability_challenging":  "Challenging",

    # monthly / yearly / matching — AstroSage-style vocabulary
    "nav_monthly_link":    "Monthly Horoscope",
    "nav_yearly_link":     "Horoscope {year}",
    "nav_matching_link":   "Kundli Matching",
    "nav_dasha_link":      "Dasha Periods",

    # Vimshottari Dasha
    "dasha_title":         "Vimshottari Dasha",
    "dasha_subtitle":      "The 120-year planetary-period system that defines your life's chapters",
    "dasha_active_maha":   "Active Mahadasha",
    "dasha_active_antar":  "Active Antardasha",
    "dasha_remaining":     "Remaining in this Maha",
    "dasha_upcoming":      "Upcoming Antardashas in current Mahadasha",
    "dasha_next_maha":     "Next Mahadasha",
    "dasha_period":        "{start} to {end}",
    "dasha_years_suffix":  "years",
    "dasha_card_title":    "Current Dasha",
    "dasha_card_subtitle": "Your active Vimshottari period",
    "dasha_view_full":     "Full Dasha timeline &rarr;",

    # kundali matching form
    "matching_title":      "Kundali Matching",
    "matching_subtitle":   "Ashtakoot Guna Milan — eight-fold compatibility scoring (max 36 points)",
    "matching_groom":      "Person 1 (typically Groom)",
    "matching_bride":      "Person 2 (typically Bride)",
    "matching_submit":     "Calculate Guna Milan",
    "matching_results":    "Compatibility result",
    "matching_total":      "Total Gunas",
    "matching_out_of":     "out of {max}",
    "matching_verdict":    "Verdict",
    "matching_mangal":     "Mangal Dosh compatibility",
    "matching_mangal_compat":  "Compatible",
    "matching_mangal_incompat":"Needs review",
    "matching_breakdown":  "Koota-by-Koota breakdown",
    "matching_col_koota":  "Koota",
    "matching_col_max":    "Max",
    "matching_col_score":  "Score",
    "matching_col_note":   "Note",
    "matching_back":       "Match different charts",
    "matching_verdict_uttam":   "Excellent compatibility (Uttam)",
    "matching_verdict_madhyam": "Good compatibility (Madhyam)",
    "matching_verdict_avara":   "Acceptable with caveats (Avara)",
    "matching_verdict_below":   "Below recommended threshold",
    "monthly_title":       "{name}'s month ahead",
    "monthly_title_anon":  "Your month ahead",
    "monthly_subtitle":    "30-day outlook based on your natal chart and the current slow-mover backdrop",
    "yearly_title":        "{name}'s year ahead",
    "yearly_title_anon":   "Your year ahead",
    "yearly_subtitle":     "12-month outlook focused on Jupiter, Saturn, and the Rahu/Ketu axis",
    "monthly_reading":     "This month's reading",
    "yearly_reading":      "This year's reading",
    "window_label":        "Window",
    "computed_today":      "Computed today",
    "events_title":        "Key transit events",
    "events_subtitle":     "Sign changes and retrograde flips of the inner planets, in chronological order",
    "events_none":         "No notable transit events detected in this window.",

    # Varshaphala — annual chart at solar return
    "varshaphala_title":     "Varshaphala &mdash; your annual chart",
    "varshaphala_subtitle":  "The chart cast at the moment Sun returns to its natal sidereal longitude this year",
    "varshaphala_solar_return": "Solar return moment",
    "varshaphala_annual_lagna": "Annual Lagna",
    "varshaphala_annual_moon":  "Annual Moon",
    "varshaphala_year_lord":    "Year Lord",
    "varshaphala_muntha":       "Muntha house",
    "varshaphala_muntha_note":  "Muntha is the house in the annual chart that holds the natal Sun's sign &mdash; classically known as the year's focus house.",

    # generic errors
    "error_chart":         "Couldn't compute the chart",
    "error_reading":       "Couldn't generate the reading",
    "error_key_missing":   "API key not configured",
}

_HI: Final[dict[str, str]] = {
    "nav_print":           "प्रिंट करें",
    "nav_home":            "मुख्य पृष्ठ",
    "nav_today_link":      "आज का राशिफल",
    "nav_natal_link":      "कुंडली",
    "back_form":           "फॉर्म पर वापस जाएं",
    "new_reading":         "नया पठन",

    "outlook_named":       "{name} का आज का संक्षेप",
    "outlook_anonymous":   "आपका आज का संक्षेप",
    "outlook_subtitle":    "आपकी जन्म कुंडली ({lagna} में लग्न) और आज के गोचर के आधार पर।",
    "today_label":         "आज",

    "moon_transits":       "चंद्र गोचर",
    "sun_transits":        "सूर्य गोचर",
    "house_from_lagna":    "जन्म लग्न से {n}वें भाव में",
    "nakshatra_suffix":    "नक्षत्र",

    "sade_sati":           "साढ़े साती",
    "phase_rising":        "आरोही चरण",
    "phase_peak":          "मध्य चरण",
    "phase_setting":       "अवरोही चरण",

    "todays_panchang":     "आज का पंचांग",
    "ruled_by":            "अधिपति",
    "rahu_kaal":           "राहु काल",
    "rahu_kaal_tag":       "वर्जित",
    "rahu_kaal_desc":      "अशुभ समय। इस अवधि में कोई नया कार्य आरम्भ करना, महत्वपूर्ण दस्तावेज़ों पर हस्ताक्षर करना, या बड़े निर्णय लेने से बचें।",
    "abhijit_muhurta":     "अभिजित मुहूर्त",
    "abhijit_tag":         "श्रेष्ठ समय",
    "abhijit_desc":        "दिन का सर्वोत्तम शुभ समय। महत्वपूर्ण कार्यों, बैठकों, हस्ताक्षरों और आरम्भों के लिए अनुकूल।",
    "favourable_colour":   "आज का शुभ रंग",
    "colour_caption":      "{weekday} के अधिपति {lord} से सम्बंधित।",
    "solar_window":        "सूर्योदय और सूर्यास्त",
    "solar_window_desc":   "आपके जन्मस्थान पर सूर्योदय से सूर्यास्त तक — आज के मुहूर्त इसी से निकाले गए हैं।",

    "todays_reading":      "आज का पठन",
    "all_transits_today":  "आज के सभी गोचर",
    "now_in":              "वर्तमान में",
    "transiting_house":    "आपके जन्म लग्न से {n}वें भाव में गोचर",
    "computed_for":        "{moment} पर परिकलित। भाव {lagna} में आपके जन्म लग्न से गिने गए हैं।",
    "refresh_today":       "आज को पुनः लोड करें",
    "back_home":           "मुख्य पृष्ठ पर वापस",

    "error_chart":         "कुंडली की गणना नहीं हो सकी",
    "error_reading":       "पठन उत्पन्न नहीं हो सका",
    "error_key_missing":   "API कुंजी कॉन्फ़िगर नहीं है",

    # natal page - common
    "natal_title":         "{name} का पठन",
    "natal_title_anon":    "आपका पठन",
    "natal_subtitle":      "जन्म {date} को {time} बजे · {place}",
    "lagna":               "लग्न",
    "moon_rashi":          "चंद्र · राशि",
    "sun_rashi":           "सूर्य · राशि",
    "computed_chart":      "परिकलित कुंडली",
    "lagna_kundali":       "लग्न कुंडली",
    "planetary_positions": "ग्रहों की स्थिति",
    "continue_chart":      "अपनी कुंडली के साथ आगे बढ़ें",
    "continue_chart_desc": "अब जब हमारे पास आपके जन्म विवरण हैं, एक क्लिक में और भी पठन उपलब्ध हैं।",
    "daily_horoscope":     "दैनिक राशिफल",
    "daily_horoscope_desc":"आपकी जन्म कुंडली के संदर्भ में आज के गोचर — न कि साधारण राशिचक्र टेम्पलेट।",
    "kundali_matching":    "कुंडली मिलान",
    "kundali_matching_desc":"विवाह संगतता के लिए अष्टकूट गुण मिलान।",
    "dasha_periods":       "दशा काल",
    "dasha_periods_desc":  "आपकी वर्तमान विंशोत्तरी महादशा और अंतर्दशा।",
    "badge_live":          "उपलब्ध",
    "badge_soon":          "जल्द",
    "generate_another":    "नया पठन उत्पन्न करें",
    "your_reading":        "आपका पठन",

    # Marriage & Love panel
    "marriage_title":      "विवाह और प्रेम",
    "marriage_subtitle":   "सप्तम भाव और शुक्र जो जीवनसाथी के संबंध में संकेत देते हैं",
    "marriage_seventh":    "सप्तम भाव (कलत्र भाव)",
    "marriage_seventh_sign": "राशि",
    "marriage_lord":       "अधिपति",
    "marriage_occupants":  "सप्तम में ग्रह",
    "marriage_no_occupants": "कोई ग्रह नहीं",
    "marriage_venus":      "शुक्र — प्रेम और रोमांस",
    "marriage_in_house":   "{n}वें भाव में",
    "marriage_manglik_note":"इस कुंडली में मंगल दोष उपस्थित है — विस्तृत जानकारी और संभावित निवारणों के लिए नीचे का मंगल दोष पैनल देखें।",

    # Wealth & Money panel
    "wealth_title":        "धन और समृद्धि",
    "wealth_subtitle":     "द्वितीय भाव, एकादश भाव और बृहस्पति से धन के संकेत",
    "wealth_dhana":        "द्वितीय भाव (धन भाव)",
    "wealth_dhana_desc":   "संचित धन · कुटुंब का धन · वाणी",
    "wealth_labha":        "एकादश भाव (लाभ भाव)",
    "wealth_labha_desc":   "लाभ · आय · इच्छाओं की पूर्ति",
    "wealth_jupiter":      "बृहस्पति — धन कारक",
    "wealth_planets_label":"ग्रह",
    "wealth_no_planets":   "कोई नहीं",

    # Mangal Dosh panel
    "manglik_title":       "मंगल दोष",
    "manglik_present":     "इस कुंडली में उपस्थित",
    "manglik_severity_high":     "उच्च प्रभाव",
    "manglik_severity_moderate": "मध्यम प्रभाव",
    "manglik_severity_low":      "अल्प प्रभाव",
    "manglik_houses_label":"योग्य स्थितियाँ",
    "manglik_house_lagna": "लग्न से {ord} भाव में मंगल",
    "manglik_house_moon":  "चंद्र से {ord} भाव में मंगल",
    "manglik_about_label": "इसका अर्थ",
    "manglik_about_high":  "लग्न या चंद्र से सप्तम अथवा अष्टम भाव में मंगल का होना मंगल दोष का सबसे चर्चित स्वरूप है। शास्त्रीय रूप से यह वैवाहिक मामलों में टकराव, अस्थिरता या तीव्र ऊर्जा का सूचक माना जाता है, जहाँ सप्तम (साझेदारी) और अष्टम (जीवनसाथी की आयु, परिवर्तन) सबसे चिंतनीय हैं। वास्तविक प्रभाव शेष कुंडली पर बहुत निर्भर करता है।",
    "manglik_about_moderate":"प्रथम, चतुर्थ अथवा द्वादश भाव में मंगल मंगल दोष का मध्यम स्वरूप है। प्रथम व्यक्तित्व व अस्थिरता को, चतुर्थ घर व मानसिक शांति को, और द्वादश निजी जीवन व व्यय को प्रभावित करता है। प्रायः सप्तम/अष्टम से कम गंभीर, परन्तु ध्यान देने योग्य।",
    "manglik_about_low":   "द्वितीय भाव में मंगल मंगल दोष का सबसे हल्का स्वरूप है, जो मुख्य रूप से वाणी और पारिवारिक गतिविधि को प्रभावित करता है। कुछ परंपराएँ द्वितीय-मंगल को मंगल दोष से बाहर भी रखती हैं।",
    "manglik_cancel_label":"संभावित निवारण",
    "manglik_cancel_text": "शास्त्रीय रूप से मंगल दोष निम्न स्थितियों में निरस्त या न्यून माना जाता है: मंगल अपनी ही राशि (मेष या वृश्चिक) में अथवा उच्च (मकर) में हो; जीवनसाथी भी मंगली हो (मिलान से दोष कटता है); गुरु की दृष्टि मंगल पर हो; विशेष युतियाँ या शुभ ग्रहों की दृष्टि हो। ये निवारण यहाँ नहीं गणित किए गए — किसी विद्वान ज्योतिषी से परामर्श करना उचित।",

    # Sade Sati panel
    "sade_sati_title":     "साढ़े साती",
    "sade_sati_active":    "वर्तमान में सक्रिय",
    "sade_sati_duration":  "कुल 7.5 वर्ष · 3 चरण, प्रत्येक लगभग 2.5 वर्ष",
    "sade_sati_rising_title": "आरोही चरण (आरोहिणी)",
    "sade_sati_peak_title":   "मध्य चरण",
    "sade_sati_setting_title":"अवरोही चरण (अवरोहिणी)",
    "sade_sati_rising_about": "शनि वर्तमान में आपके जन्म चंद्र से द्वादश भाव में गोचर कर रहे हैं — 7.5 वर्ष की साढ़े साती का आरम्भिक चरण। यह तैयारी का चरण है: दबाव धीरे-धीरे बढ़ने लगता है।",
    "sade_sati_peak_about":   "शनि वर्तमान में आपके जन्म चंद्र की राशि में गोचर कर रहे हैं — 7.5 वर्ष के चक्र का मध्य और सर्वाधिक परीक्षण का चरण। यहाँ दबाव सबसे प्रत्यक्ष होता है।",
    "sade_sati_setting_about":"शनि वर्तमान में आपके जन्म चंद्र से द्वितीय भाव में गोचर कर रहे हैं — 7.5 वर्ष के चक्र का समापन चरण, जो स्थिरीकरण और धीरे-धीरे विश्राम पर केंद्रित है।",
    "sade_sati_themes_label": "मुख्य प्रभाव",
    "sade_sati_rising_themes":"आंतरिक पुनर्निर्माण · नींद और स्वप्न में परिवर्तन · आध्यात्मिक जागरण · सावधानीपूर्ण वित्त प्रबंधन · विदेश यात्रा · रात्रिकालीन चुनौतियाँ",
    "sade_sati_peak_themes":  "शारीरिक स्वास्थ्य पर ध्यान · पहचान के प्रश्न · धीमी प्रगति · कार्यभार · एकांत के क्षण · पारिवारिक जिम्मेदारियाँ",
    "sade_sati_setting_themes":"धन और बचत में बदलाव · पारिवारिक संबंध · वाणी संबंधी विषय · धीमा स्थिरीकरण · क्रमिक सुधार",
    "sade_sati_guidance_label":"मार्गदर्शन",
    "sade_sati_rising_guidance":"धैर्य रखें। एक दैनिक अनुशासन विकसित करें — ध्यान, व्यायाम, चिंतन। वित्त सावधानी से प्रबंधित करें। आंतरिक स्पंदन को संघर्ष की बजाय वास्तविक आत्म-चिंतन के लिए उपयोग करें।",
    "sade_sati_peak_guidance":  "शारीरिक स्वास्थ्य और शांत दिनचर्या पर ध्यान दें। सीमाओं को शिक्षक मानें। अनुशासित कार्य करें और बड़े जोखिमों से बचें। दबाव वास्तविक है पर रचनात्मक — शनि यहाँ सत्यनिष्ठा को पुरस्कृत करते हैं।",
    "sade_sati_setting_guidance":"वाणी में संयम रखें। वित्त धीरे-धीरे पुनर्निर्मित करें। पारिवारिक मतभेद सुलझाएँ। यह वह चरण है जब चक्र के दौरान बोए गए बीज परिपक्व होने लगते हैं।",

    # gochar highlights panel
    "gochar_title":        "गोचर (मंद ग्रह संचार)",
    "gochar_subtitle":     "आकाश में चल रहा मंद-ग्रह अध्याय — ये कई महीनों की पृष्ठभूमि तय करते हैं",
    "gochar_house_lagna":  "लग्न से {n}वें भाव में",
    "gochar_house_moon":   "चंद्र से {n}वें भाव में",
    "favorability_favorable":    "अनुकूल",
    "favorability_neutral":      "तटस्थ",
    "favorability_challenging":  "चुनौतीपूर्ण",

    # monthly / yearly / matching — AstroSage-style vocabulary
    "nav_monthly_link":    "मासिक राशिफल",
    "nav_yearly_link":     "राशिफल {year}",
    "nav_matching_link":   "कुंडली मिलान",
    "nav_dasha_link":      "दशा काल",

    # Vimshottari Dasha
    "dasha_title":         "विंशोत्तरी दशा",
    "dasha_subtitle":      "120 वर्ष का ग्रह-दशा तंत्र जो आपके जीवन के अध्याय निर्धारित करता है",
    "dasha_active_maha":   "वर्तमान महादशा",
    "dasha_active_antar":  "वर्तमान अंतर्दशा",
    "dasha_remaining":     "इस महादशा में शेष",
    "dasha_upcoming":      "वर्तमान महादशा में आगामी अंतर्दशाएँ",
    "dasha_next_maha":     "अगली महादशा",
    "dasha_period":        "{start} से {end}",
    "dasha_years_suffix":  "वर्ष",
    "dasha_card_title":    "वर्तमान दशा",
    "dasha_card_subtitle": "आपकी सक्रिय विंशोत्तरी अवधि",
    "dasha_view_full":     "पूर्ण दशा समय-रेखा &rarr;",

    # kundali matching
    "matching_title":      "कुंडली मिलान",
    "matching_subtitle":   "अष्टकूट गुण मिलान — विवाह संगतता का आठ-कूट मूल्यांकन (अधिकतम 36 गुण)",
    "matching_groom":      "व्यक्ति 1 (सामान्यतः वर)",
    "matching_bride":      "व्यक्ति 2 (सामान्यतः वधू)",
    "matching_submit":     "गुण मिलान की गणना करें",
    "matching_results":    "मिलान का परिणाम",
    "matching_total":      "कुल गुण",
    "matching_out_of":     "{max} में से",
    "matching_verdict":    "निष्कर्ष",
    "matching_mangal":     "मंगल दोष संगतता",
    "matching_mangal_compat":  "अनुकूल",
    "matching_mangal_incompat":"समीक्षा आवश्यक",
    "matching_breakdown":  "कूट-वार विवरण",
    "matching_col_koota":  "कूट",
    "matching_col_max":    "अधिकतम",
    "matching_col_score":  "प्राप्त",
    "matching_col_note":   "टिप्पणी",
    "matching_back":       "अन्य कुंडलियों का मिलान",
    "matching_verdict_uttam":   "उत्तम संगतता",
    "matching_verdict_madhyam": "मध्यम संगतता",
    "matching_verdict_avara":   "स्वीकार्य (सावधानी के साथ)",
    "matching_verdict_below":   "अनुशंसित स्तर से कम",
    "monthly_title":       "{name} का मासिक भविष्यफल",
    "monthly_title_anon":  "आपका मासिक भविष्यफल",
    "monthly_subtitle":    "आपकी जन्म कुंडली और वर्तमान मंद-ग्रह पृष्ठभूमि के आधार पर 30 दिनों का दृष्टिकोण",
    "yearly_title":        "{name} का वार्षिक भविष्यफल",
    "yearly_title_anon":   "आपका वार्षिक भविष्यफल",
    "yearly_subtitle":     "बृहस्पति, शनि और राहु/केतु अक्ष पर केंद्रित 12 महीने का दृष्टिकोण",
    "monthly_reading":     "इस माह का पठन",
    "yearly_reading":      "इस वर्ष का पठन",
    "window_label":        "अवधि",
    "computed_today":      "आज परिकलित",
    "events_title":        "मुख्य गोचर घटनाएँ",
    "events_subtitle":     "आंतरिक ग्रहों के राशि-परिवर्तन और वक्री-मार्गी परिवर्तन, कालक्रम में",
    "events_none":         "इस अवधि में कोई उल्लेखनीय गोचर घटना नहीं मिली।",

    # Varshaphala
    "varshaphala_title":     "वर्षफल &mdash; आपका वार्षिक कुंडली",
    "varshaphala_subtitle":  "इस वर्ष जब सूर्य अपनी जन्म-सायन देशांश पर लौटेगा, उस क्षण पर निर्मित कुंडली",
    "varshaphala_solar_return": "सूर्य-प्रत्यागमन का क्षण",
    "varshaphala_annual_lagna": "वार्षिक लग्न",
    "varshaphala_annual_moon":  "वार्षिक चंद्र",
    "varshaphala_year_lord":    "वर्ष का स्वामी",
    "varshaphala_muntha":       "मुंथा भाव",
    "varshaphala_muntha_note":  "मुंथा वह भाव है जिसमें वार्षिक कुंडली के अनुसार जन्म-सूर्य की राशि स्थित है &mdash; शास्त्रीय रूप से वर्ष का केंद्रित भाव।",
}

_TABLES: Final[dict[str, dict[str, str]]] = {"en": _EN, "hi": _HI}


def translate(lang: str, key: str, **kwargs: Any) -> str:
    """Lookup `key` in `lang`'s table (fallback English). Apply `.format(**kwargs)` if given."""
    table = _TABLES.get(lang, _EN)
    text = table.get(key) or _EN.get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
