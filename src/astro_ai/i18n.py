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
    "gochar_base_rate":    "By classical reckoning the slow planets are demanding in most positions — Saturn, Rahu and Ketu in nine houses of twelve, Jupiter in seven. Seeing several marked challenging is the ordinary shape of this table, not a verdict on your year.",
    "strip_rahu_kaal":     "Rahu Kaal (avoid)",
    "strip_abhijit":       "Abhijit (best)",
    "strip_tithi":         "Tithi",
    "strip_moon":          "Moon",
    "strip_weekday_in":    "in",
    "strip_full_panchang": "Full Panchang",
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
    "manglik_about_label": "What this means",
    "manglik_about_high":  "Mars sitting in the 7th or 8th house — counted from your Lagna, your Moon or your Venus — is the most-discussed form of Manglik. Classically it suggests friction, restlessness, or assertive energy in marital matters, with the 7th house (partnership) and 8th house (spouse's longevity, transformation) being the most-cited concerns. The actual effect varies enormously with the rest of the chart.",
    "manglik_about_moderate":"Mars in the 1st, 4th, or 12th house is a moderate form of Manglik. The 1st affects personality and restlessness; the 4th affects home and inner peace; the 12th affects private life and expenses. Often less severe than 7th/8th placements but still worth noting.",
    "manglik_about_low":   "Mars in the 2nd house is the mildest form of Manglik, primarily affecting speech and family dynamics. Some traditions exclude 2nd-house Manglik entirely.",
    "manglik_cancel_label":"Possible cancellations",

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

    # Sade Sati — timing labels
    "sade_sati_timeline":    "Timeline",
    "sade_sati_started":     "Started",
    "sade_sati_ends":        "Ends fully",
    "sade_sati_phase_ends":  "Current phase ends",
    "sade_sati_elapsed":     "elapsed",
    "sade_sati_remaining":   "remaining",
    "sade_sati_years":       "years",
    "sade_sati_months":      "months",
    "sade_sati_precautions_label": "Traditional precautions",
    "sade_sati_precautions":
        "Donate black sesame, black cloth, or iron on Saturdays. "
        "Light a mustard-oil lamp under a peepal tree. "
        "Recite the Hanuman Chalisa or Shani Stotra regularly. "
        "Eat simple food, sleep on time, and avoid hasty decisions. "
        "Help the elderly, the poor, and those in service work — Saturn rewards humility and service.",
    "sade_sati_balance_label": "What this period gives in return",
    "sade_sati_balance":
        "Sade Sati is not a punishment. The pressure shapes lasting maturity, discernment, and resilience. "
        "Many people emerge with stronger character, clearer values, and structures that hold for decades. "
        "The classical view: those who meet Saturn with patience and discipline are rewarded with deep, durable gains.",

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
    "nav_rashifal_link":   "Rashifal",
    "nav_ask_link":        "Ask",

    # Rashifal page
    "rashifal_title":      "Today's Rashifal",
    "rashifal_subtitle":   "Daily predictions for all 12 Moon signs — find your Janma Rashi below.",
    "rashifal_dont_know":  "Don't know your Moon sign? Generate your free Kundli — it tells you instantly.",

    # Rashifal — the per-rashi standalone page (/rashifal/{rashi}), #124.
    #
    # Until this block existed the page was Hindi to a reader and English to a
    # crawler: `<title>`, `<meta description>`, `<h1>` and the Article JSON-LD
    # were hardcoded English while `reading_body` came back in Devanagari.
    #
    # The `{...}` fields are filled by the template. Every key takes the same
    # bag (rashi_en / rashi_sa / rashi_hi / date / element / quality / lord /
    # url) and ignores what it does not use, so the two tables can phrase the
    # same fact in a different order without the call site changing.
    "rashifal_single_title":    "{rashi_en} / {rashi_sa} Rashifal — {date} · Daily Vedic Horoscope",
    "rashifal_single_meta":     "{rashi_en} ({rashi_sa}) daily Rashifal for {date} — a substantive Vedic Moon-sign reading anchored on today's actual sky (weekday-lord, tithi, moon nakshatra). Free, sidereal Lahiri.",
    "rashifal_single_headline": "{rashi_en} Rashifal — {date}",
    "rashifal_single_ld_desc":  "{rashi_en} ({rashi_sa}) daily Vedic horoscope for {date} — sidereal Lahiri.",
    "rashifal_single_alt":      "{rashi_en} ({rashi_sa}) zodiac silhouette",
    "rashifal_single_attrs":    "Element: {element} · Quality: {quality} · Ruling planet (Swami): {lord}",
    "rashifal_single_share":    "{rashi_en} Rashifal — {url}",
    "rashifal_all_12":          "← All 12 rashis",
    "rashifal_share_whatsapp":  "Share on WhatsApp",
    "rashifal_deeper":          "Want a deeper reading?",
    "rashifal_kundli_cta":      "Free Janma Kundli →",
    "rashifal_kundli_desc":     "Full birth chart with dashas, yogas, and personalised reading — beyond the Moon sign.",
    "rashifal_panchang_cta":    "Today's Panchang →",
    "rashifal_panchang_desc":   "Tithi, nakshatra, Rahu Kaal, Abhijit, Choghadiya for your city.",

    # The 12 rashi names, keyed by the canonical slug. This is the SINGLE
    # source for the Devanagari forms — _subscribe_modal.html used to carry
    # its own inline copies and now reads them from here, so there is no
    # second list to drift. (rashifal_grid.html and routes/rashifal.py hold
    # per-rashi PRESENTATION tables — glyph, gradient, element — not names.)
    "rashi_name_aries":         "Aries",
    "rashi_name_taurus":        "Taurus",
    "rashi_name_gemini":        "Gemini",
    "rashi_name_cancer":        "Cancer",
    "rashi_name_leo":           "Leo",
    "rashi_name_virgo":         "Virgo",
    "rashi_name_libra":         "Libra",
    "rashi_name_scorpio":       "Scorpio",
    "rashi_name_sagittarius":   "Sagittarius",
    "rashi_name_capricorn":     "Capricorn",
    "rashi_name_aquarius":      "Aquarius",
    "rashi_name_pisces":        "Pisces",

    # Element / quality vocabulary, keyed on the lowercased English values in
    # routes/rashifal.py _RASHIFAL_UI_META so the template can look up whatever
    # the route hands it.
    "rashi_element_fire":       "Fire",
    "rashi_element_earth":      "Earth",
    "rashi_element_air":        "Air",
    "rashi_element_water":      "Water",
    "rashi_quality_movable":    "Movable",
    "rashi_quality_fixed":      "Fixed",
    "rashi_quality_dual":       "Dual",

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
    "dasha_view_full":     "Full Dasha timeline →",

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
    # /ask page header (BUG-7). These were hardcoded English, so the Hindi
    # page rendered them untranslated. The i18n completeness check added in
    # 16e07b7 is structurally blind to copy that never becomes a key — it can
    # only verify that keys IN USE exist in both tables — so hardcoded strings
    # are invisible to it by construction. Routing this block through keys is
    # what makes the check able to see it at all.
    "ask_eyebrow":            "Ask Shubh Bhagya",
    "ask_head_chart":         "Ask anything about your chart",
    "ask_head_matching":      "Ask anything about your match",
    "ask_head_numerology":    "Ask anything about your numbers",
    "ask_blurb_chart":        "Your question gets answered using your actual birth chart — placements, current Dasha, and Vedic flags. Honest, specific, no generic platitudes.",
    "ask_blurb_matching":     "Your question gets answered using both birth charts and your Guna Milan result — the koota scores, Mangal Dosh, and any doshas found. Honest, specific, no generic platitudes.",
    "ask_blurb_numerology":   "Your question gets answered using your numerology reading alongside your birth chart. Honest, specific, no generic platitudes.",
    # Third-party shape: the seeker ran the match for two other people, so only
    # THEIR chart is sent, plus the couple's Guna Milan. The "both birth charts"
    # copy above is wrong here and was live for a day (QA OBS-2).
    "ask_head_matching_third":   "Ask anything about this match",
    "ask_blurb_matching_third":  "You're asking about someone else's match. Your question gets answered using their Guna Milan result — the koota scores, Mangal Dosh, and any doshas found. Honest, specific, no generic platitudes.",
    "ask_asking_about_their":    "Asking about the match for:",
    "ask_opt_their_match":       "Their match",
    "ask_asking_for":         "Asking for:",
    "ask_asking_about":       "Asking about:",
    "ask_switch_chart":       "switch chart",
    "ask_new_match":          "new match",
    "ask_numerology_badge":   "Numerology context",
    "ask_answer_using":       "Answer using",
    "ask_opt_both_charts":    "Both charts",
    "ask_opt_my_chart":       "Just my chart",
    "matching_charts_heading": "Both charts",
    "matching_bhakoot":    "Bhakoot Dosh",
    "matching_bhakoot_cancelled":   "Cancelled",
    "matching_bhakoot_uncancelled": "Not cancelled",
    "matching_bhakoot_applies":     "Cancelling conditions that apply",
    "matching_bhakoot_uneval":      "Not evaluated",
    "matching_bhakoot_nopoints":
        "A cancellation removes the dosha. It does not add points to the score above.",
    "matching_nadi":        "Nadi Dosh",
    "matching_nadi_grave":  "Gravest form",
    "matching_nadi_alpa":   "Reduced",
    "matching_nadi_plain":  "Present",
    "matching_nadi_mitig":  "What reduces it",
    "matching_nadi_nocancel":
        "Nadi has no cancelling conditions. It does not gain points from any mitigation.",
    "matching_breakdown":  "Koota-by-Koota breakdown",
    "matching_col_koota":  "Koota",
    "matching_col_max":    "Max",
    "matching_col_score":  "Score",
    "matching_col_note":   "Note",
    "matching_back":       "Match different charts",
    "matching_verdict_uttam":   "Excellent compatibility (Uttam)",
    "matching_verdict_madhyam": "Good compatibility (Madhyam)",
    "matching_verdict_avara":   "Acceptable with caveats (Avara)",
    "matching_caveat_heading": "Ashtakoot is a starting point, not a full verdict",
    "matching_caveat_body_1":  "Guna Milan compares two Moon-sign compatibilities across eight areas. It does not check whether either chart carries individual afflictions — a heavily aspected 7th house, an afflicted Venus, malefics conjoined the Moon, or difficult Dasha timing — that classical astrology treats as essential for a marriage assessment.",
    "matching_caveat_body_2":  "Two people can score maximum points here and still face serious marital difficulty; two people can score below threshold and have chart-strengths that outweigh the deficit. Treat this score as the first filter, not the final answer.",
    "matching_caveat_body_3":  "Before a wedding decision, have both charts read individually — the 7th house and its lord, Venus and Jupiter placements, Upapada, and current Dashas all matter. If you'd like, ask your specific matching question below and we'll take the two charts into account.",
    "manglik_caveat_heading":  "Manglik is not the whole marriage story",
    "manglik_caveat_body":     "Mars-related dosha is one of several factors classical astrology weighs for marriage. A person with a well-placed Mars can still face marital difficulty if the 7th house lord, Venus, Upapada, or Dasha timing carry other afflictions. A Manglik chart with strong protective yogas can equally have a harmonious married life. Treat this as one data point among many — a full 7th-house reading with a trained astrologer is worth the time if marriage is your central question.",

    # Kaal Sarp caveat — sourced from classical-source research (2026-08-04):
    # not in BPHS, Brihat Jataka, Saravali, Phaladeepika, Jataka Parijata, or
    # Uttara Kalamrita. K.N. Rao dismissed it publicly; B.V. Raman added it as
    # an appendix (not main text) to Three Hundred Important Combinations 9th
    # ed. because it had "become much feared". First Indian print debate in
    # Astrological Magazine, late 1970s. Shown at TOP of /kaal-sarp-check.
    "ksy_caveat_heading":      "A note before you read this: Kaal Sarp is a modern classification",
    "ksy_caveat_body_1":       "Unlike the yogas and doshas we analyse elsewhere on this site, Kaal Sarp Yoga is not defined in the classical Sanskrit Jyotish texts we cite as sources — not in Brihat Parashara Hora Shastra, Brihat Jataka, Saravali, Phaladeepika, Jataka Parijata, or Uttara Kalamrita. The concept surfaces in Indian astrological writing only in the 20th century and was widely debated in The Astrological Magazine in the late 1970s and 1980s.",
    "ksy_caveat_body_2":       "Respected teachers disagree about its predictive weight. K.N. Rao (founder of the Bharatiya Vidya Bhavan Jyotish course) publicly dismissed Kaal Sarp Dosha as \"one of the biggest frauds in astrology\" and \"of not much importance in individual charts.\" B.V. Raman (editor of The Astrological Magazine) added it as an appendix to the ninth edition of Three Hundred Important Combinations because it had \"become much feared\" — his own treatment was nuanced, not alarmist.",
    "ksy_caveat_body_3":       "We show the geometry here because it is a real chart pattern users ask about — but treat any single Kaal Sarp reading, especially one urging expensive remedies at Trimbakeshwar or elsewhere, with healthy skepticism. Serious readings of Rahu and Ketu judge them by the houses and lords they conjoin, not by axis-based blanket yogas.",
    "ksy_present_heading":     "Kaal Sarp geometry — present",
    "ksy_present_subtitle":    "All seven non-shadow planets sit on one side of the Rahu-Ketu axis",
    "ksy_absent_heading":      "Kaal Sarp geometry — not present",
    "ksy_absent_body":         "The seven non-shadow planets are distributed on both sides of the Rahu-Ketu axis in your chart, so the Kaal Sarp pattern does not apply.",
    "ksy_variant_note":        "Traditional Naga label for this Rahu-house position. These twelve names are folk taxonomy from mid-20th-century Hindi almanac literature, not classical shastra — so we describe the geometry rather than assigning per-variant predictions.",

    # Numerology caveat — sourced from classical-source research (2026-08-04):
    # not in BPHS / Brihat Jataka / Saravali / Phaladeepika / Jataka Parijata /
    # Uttara Kalamrita. Modern "Indian" numerology descends from Cheiro (Wm
    # John Warner, 1866-1936), L. Dow Balliett (1908), Julia Seton (coined
    # the word ~1912), Juno Jordan (DeVorss). K.N. Rao was taught numerology
    # by his mother and DROPPED it; only Sanjay Rath defends it, and only on
    # philosophical (navagraha ↔ 1-9) rather than textual grounds. Shown at
    # TOP of /numerology, before both the form and any results.
    "num_caveat_heading":      "About this tool — honesty about the tradition",
    "num_caveat_body_1":       "The numerology systems on this page — Chaldean (Cheiro) and the Lo Shu grid — are modern traditions with 19th- and 20th-century Western and ancient Chinese roots, not branches of classical Vedic Jyotish. Foundational Sanskrit Jyotish texts (Brihat Parashara Hora Shastra, Brihat Jataka, Saravali, Phaladeepika, Jataka Parijata, Uttara Kalamrita) do not describe birth-date reduction or English-alphabet name numerology.",
    "num_caveat_body_2":       "The Life Path / Expression / Soul Urge framework was built by three Americans between 1908 and mid-20th century — L. Dow Balliett, Julia Seton (who coined the word \"numerology\" ~1912), and Juno Jordan. The \"Chaldean\" name-number tables in wide circulation trace to Cheiro (William John Warner, 1866–1936). Respected Jyotish teachers such as K.N. Rao practice without numerology; scholar Shyamasundara Dasa argues the method is calendar- and alphabet-dependent (reduce your birthdate in Vikram Samvat vs Saka vs Gregorian and you get different numbers) rather than universal.",
    "num_caveat_body_3":       "We publish these calculators because millions find them meaningful and they can prompt useful self-reflection. But treat the output as reflective, not predictive — and never as a substitute for a Jyotish analysis of your actual birth chart. Of the sections below, the Lo Shu grid is the most textually defensible (genuinely ancient Chinese, independent of the Gregorian calendar); the Life Path and Karmic Debt sections are 20th-century Western frameworks.",
    "num_reflective_header":   "Read the descriptions below as prompts for self-reflection, not predictions. \"Life Path 3\" isn't telling you what will happen — it's naming a pattern the tradition associates with your birth-date sum, one you can accept, question, or ignore.",

    # Download PDF button — uses browser's Print → Save as PDF path
    # (no server-side weasyprint dependency). Button JS sets a nice
    # document.title so the suggested filename is meaningful.
    "pdf_download":           "Download PDF",
    "pdf_download_hint":      "Uses your browser's print → save as PDF. Works on desktop; mobile users may see a print preview instead.",
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
    "varshaphala_title":     "Varshaphala — your annual chart",
    "varshaphala_subtitle":  "The chart cast at the moment Sun returns to its natal sidereal longitude this year",
    "varshaphala_solar_return": "Solar return moment",
    "varshaphala_annual_lagna": "Annual Lagna",
    "varshaphala_annual_moon":  "Annual Moon",
    "varshaphala_year_lord":    "Year Lord",
    "varshaphala_muntha":       "Muntha house",
    "varshaphala_muntha_note":  "Muntha is the house in the annual chart that holds the natal Sun's sign — classically known as the year's focus house.",

    # generic errors
    "error_chart":         "Couldn't compute the chart",
    "error_reading":       "Couldn't generate the reading",
    "error_key_missing":   "API key not configured",

    # ─── Nav labels added cycle 10 ───────────────────────────────────
    "nav_numerology_link":     "Numerology",
    "nav_learn_link":          "Learn",
    "nav_tools_menu":          "Tools",
    "nav_more_menu":           "More",
    "nav_tool_panchang":       "Panchang Today",
    "nav_tool_muhurat":        "Muhurat Finder",
    "nav_tool_festivals":      "Festival Calendar",
    "nav_tool_manglik":        "Manglik Check",
    "nav_tool_sade_sati":      "Sade Sati Report",
    "nav_tool_kaal_sarp":      "Kaal Sarp Check",

    # ─── Bhagya Score section (result.html) ─────────────────────────
    "bhagya_label":            "Bhagya",
    "bhagya_out_of":           "/ 100",
    "bhagya_heading":          "Your Bhagya Score",
    "bhagya_lede":             "Astrology is weather, not destiny. This number reflects your <strong>current chapter</strong> based on today's dashas and transits — it will shift as they shift. Below: the top signals feeding it.",
    "bhagya_why":              "Why this score",
    "bhagya_show_all":         "Show all {n} signals →",
    # Numerology-only Bhagya Score sits on /numerology
    "num_bhagya_heading":      "Your Numerology Bhagya Score",
    "num_bhagya_lede":         "Character-level snapshot from your numbers. Shifts slowly (only the Personal Year updates annually). For daily transit weather, generate your <a href=\"/kundli\" class=\"text-astro-700 hover:underline font-semibold\">Janma Kundli Bhagya Score</a>.",

    # ─── Ask CTA (_ask_cta.html) ────────────────────────────────────
    "ask_cta_free":            "Free · No signup",
    "ask_cta_remaining":       "{n} questions left today",
    "ask_cta_remaining_one":   "1 question left today",
    "ask_cta_head_saved":      "Ask 3 free questions {hint} today",
    "ask_cta_head_no_chart":   "Get 3 free personal questions with your Kundli",
    "ask_cta_body_saved":      "Real answers from your actual chart — marriage timing, career direction, when a specific transit lands. Not generic horoscope advice.",
    # Matching gets its own head/body rather than reusing the {hint}
    # interpolation. The hint is passed as an English literal from the calling
    # template, so it can never be translated — which is why the Hindi heading
    # below drops the placeholder entirely and says "your kundli" on a page
    # about two people. Dedicated keys sidestep that for the context where it
    # actually misleads.
    # Third-party shape: the person running the match is not in it (QA BUG-2).
    "ask_cta_head_matching_third": "Ask 3 free questions about this match today",
    "ask_cta_body_matching_third": "Real answers about their compatibility — how the weak kootas actually play out, what a dosha means in practice, timing for the wedding. Not generic horoscope advice.",
    "ask_cta_head_matching":   "Ask 3 free questions about your match today",
    "ask_cta_body_matching":   "Real answers using both birth charts and your Guna Milan result — how the weak kootas actually play out, what a dosha means in practice, timing for the wedding. Not generic horoscope advice.",
    "ask_cta_body_no_chart":   "Generate your free Janma Kundli and you unlock 3 daily questions like \"When will I marry?\" or \"What's the best career for me?\" — answered from your actual chart, not a template.",
    "ask_cta_button_saved":    "Ask a question →",
    "ask_cta_button_no_chart": "Generate my Kundli →",
    "ask_cta_hint_default":    "about your chart",

    # /ask honest disclosure — Shyamasundara Dasa (2026-08-02) argued
    # that AI cannot substitute for a trained astrologer's intuition
    # because it "has no connection with paramatma." Rather than argue,
    # we simply say so honestly on every answer and at page bottom.
    "ask_ai_note_short":       "Generated by AI from your natal chart. A trained astrologer's intuition catches patterns that pure calculation can't — treat this as a starting point, not a final reading.",
    "ask_ai_note_footer":      "Astrology shows tendencies, not fixed fate. This tool is AI-generated pattern reading from your chart data — not a substitute for a live consultation with a trained astrologer. Questions about timing, choices, and themes work best; avoid asking about death, illness, or hard guarantees.",

    # ─── Bhagya Score driver notes (chart.py compute_bhagya_score) ───
    # Each driver is a one-line reason shown in the "why" panel next to
    # a +/- weight pill. Kept short (~80-140 chars) so the panel stays
    # scannable. Interpolation vars: {n}=count, {names}=comma list,
    # {plural}='s'/'' for English pluralisation (empty in Hindi where
    # plurals are context-implied), {lord}/{node}=planet name,
    # {house}=already-localised ordinal (e.g. "2nd" or "2वें"),
    # {variant}=Kaal Sarp Naga name.
    "bs_yogas_active":         "{n} auspicious yoga{plural} active ({names})",
    "bs_manglik_cancelled":    "Manglik pattern cancelled by classical rules — no net Dosh",
    "bs_manglik_kuja_shukra":  "Kuja-Shukra pattern (Venus-axis only) — mainstream Lagna/Moon check reads as non-Manglik",
    "bs_manglik_mitigated":    "Manglik pattern partly mitigated (some cancellations apply)",
    "bs_manglik_present":      "Manglik Dosh present (no cancellations found in this chart)",
    "bs_sade_sati_peak":       "Sade Sati peak phase — the middle 2.5-year stretch",
    "bs_sade_sati_rising":     "Sade Sati rising phase — early ~2.5 years",
    "bs_sade_sati_setting":    "Sade Sati setting phase — exit ~2.5 years",
    "bs_sade_sati_inactive":   "Sade Sati is not active",
    "bs_ashtama_shani":        "Ashtama Shani transit (Saturn in 8th from natal Moon)",
    "bs_kantaka_shani":        "Kantaka Shani transit (Saturn in 4th from natal Moon)",
    "bs_kaal_sarp":            "Kaal Sarp pattern ({variant}) — 20th-century classification, treat as prompt not verdict",
    "bs_exalted":              "{n} planet{plural} exalted ({names})",
    "bs_debilitated":          "{n} planet{plural} debilitated ({names})",
    "bs_maha_benefic":         "Current Mahadasha: {lord} — a natural benefic period",
    "bs_maha_malefic":         "Current Mahadasha: {lord} — a demanding, patience-testing period",
    "bs_antar_benefic":        "Current Antardasha: {lord} — the next few months carry benefic sub-flavour",
    "bs_antar_malefic":        "Current Antardasha: {lord} — the next few months carry demanding sub-flavour",
    "bs_jup_gochar_good":      "Jupiter gochar in {house} from natal Moon — expansive transit",
    "bs_jup_gochar_slow":      "Jupiter gochar in {house} from natal Moon — a slower Jupiter phase",
    "bs_node_over_moon":       "{node} currently transiting over natal Moon — introspective / restless emotional weather",
    "bs_node_over_lagna":      "{node} currently transiting over natal Lagna — self-image being reshaped",

    # Chart Bhagya Score bucket labels
    "bs_label_strong":         "Strong current chapter",
    "bs_label_steady":         "Steady period",
    "bs_label_testing":        "Testing period — patience compounds",
    "bs_label_deep":           "Deep learning period — classical remedies matter more now",

    # ─── Numerology Bhagya Score drivers (numerology.py) ─────────────
    "nbs_master_lp":           "Master Number Life Path {lp} — rare, spiritually potent (elevated {base})",
    "nbs_supportive_lp":       "Life Path {lp} — traditionally ruled by {planet}, a naturally supportive number",
    "nbs_karmic_debt":         "Karmic Debt {names} present — a life-lesson theme (modern Western numerology reading)",
    "nbs_lp_dest_friend":      "Life Path {lp} and Destiny {d} are friendly numbers — inner drive and outer role aligned",
    "nbs_lp_dest_enemy":       "Life Path {lp} and Destiny {d} are enemy numbers — inner drive and outer role pull apart",
    "nbs_py_dynamic":          "Personal Year {py} — a dynamic, initiative-favouring year",
    "nbs_py_grind":            "Personal Year {py} — a slower, structural-work year",
    "nbs_py_harmony":          "Personal Year 6 — a harmony / family / responsibility year",
    "nbs_compound_good":       "Compound {n} — one of the most-fortunate name compounds in this tradition",
    "nbs_compound_challenge":  "Compound {n} — a challenging compound (rise-then-fall pattern in this tradition)",

    # Numerology Bhagya Score bucket labels
    "nbs_label_strong":        "Strong numerological chapter",
    "nbs_label_steady":        "Steady numerological base",
    "nbs_label_patience":      "Numerology signals ask for patience",
    "nbs_label_deep":          "Deep learning theme — remedies matter",
    # Degraded-path copy. Reached when every provider in the chain is
    # exhausted, which on a /hi/ URL used to render this English text under
    # <html lang="en"> at a self-canonical, hi-IN-annotated Hindi URL (#124,
    # QA 2026-10-04). The 503 keeps it out of the index, so the cost was to
    # the reader, not to search.
    "llm_busy_title":   "High demand right now",
    "llm_busy_msg":     "\U0001F64F Many seekers are asking questions at the same time. Please try again in a couple of minutes — your input is safe to re-submit exactly as you typed it.",
    "llm_error_title":  "Something went wrong",
    "llm_error_msg":    "We couldn't complete the reading this time. Please try again in a moment — your input is safe to re-submit exactly as you typed it.",
}

_HI: Final[dict[str, str]] = {
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
    "gochar_base_rate":    "शास्त्रीय गणना के अनुसार मंद ग्रह अधिकांश स्थितियों में कठिन फल देते हैं — शनि, राहु और केतु बारह में से नौ भावों में, तथा गुरु सात में। इसलिए कई ग्रहों का चुनौतीपूर्ण दिखना इस तालिका का सामान्य स्वरूप है, आपके वर्ष पर कोई निर्णय नहीं।",
    "strip_rahu_kaal":     "राहु काल (वर्जित)",
    "strip_abhijit":       "अभिजित (श्रेष्ठ)",
    "strip_tithi":         "तिथि",
    "strip_moon":          "चंद्र",
    "strip_weekday_in":    "में",
    "strip_full_panchang": "पूरा पंचांग",
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
    "manglik_about_label": "इसका अर्थ",
    "manglik_about_high":  "लग्न, चंद्र अथवा शुक्र से सप्तम अथवा अष्टम भाव में मंगल का होना मंगल दोष का सबसे चर्चित स्वरूप है। शास्त्रीय रूप से यह वैवाहिक मामलों में टकराव, अस्थिरता या तीव्र ऊर्जा का सूचक माना जाता है, जहाँ सप्तम (साझेदारी) और अष्टम (जीवनसाथी की आयु, परिवर्तन) सबसे चिंतनीय हैं। वास्तविक प्रभाव शेष कुंडली पर बहुत निर्भर करता है।",
    "manglik_about_moderate":"प्रथम, चतुर्थ अथवा द्वादश भाव में मंगल मंगल दोष का मध्यम स्वरूप है। प्रथम व्यक्तित्व व अस्थिरता को, चतुर्थ घर व मानसिक शांति को, और द्वादश निजी जीवन व व्यय को प्रभावित करता है। प्रायः सप्तम/अष्टम से कम गंभीर, परन्तु ध्यान देने योग्य।",
    "manglik_about_low":   "द्वितीय भाव में मंगल मंगल दोष का सबसे हल्का स्वरूप है, जो मुख्य रूप से वाणी और पारिवारिक गतिविधि को प्रभावित करता है। कुछ परंपराएँ द्वितीय-मंगल को मंगल दोष से बाहर भी रखती हैं।",
    "manglik_cancel_label":"संभावित निवारण",

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

    # Sade Sati — timing labels
    "sade_sati_timeline":    "समय-रेखा",
    "sade_sati_started":     "आरम्भ",
    "sade_sati_ends":        "पूर्ण समाप्ति",
    "sade_sati_phase_ends":  "वर्तमान चरण समाप्त",
    "sade_sati_elapsed":     "बीत चुके",
    "sade_sati_remaining":   "शेष",
    "sade_sati_years":       "वर्ष",
    "sade_sati_months":      "महीने",
    "sade_sati_precautions_label": "पारंपरिक सावधानियाँ",
    "sade_sati_precautions":
        "शनिवार को काले तिल, काला कपड़ा या लोहे का दान करें। "
        "पीपल वृक्ष के नीचे सरसों के तेल का दीपक जलाएँ। "
        "हनुमान चालीसा या शनि स्तोत्र का नियमित पाठ करें। "
        "सादा भोजन करें, समय पर सोएँ, और जल्दबाज़ी में निर्णय लेने से बचें। "
        "वृद्धों, ज़रूरतमंदों और सेवा कर्म करने वालों की सहायता करें — शनि विनम्रता और सेवा का पुरस्कार देते हैं।",
    "sade_sati_balance_label": "इस अवधि का सकारात्मक पक्ष",
    "sade_sati_balance":
        "साढ़े साती कोई दण्ड नहीं है। यह दबाव चरित्र को परिपक्व, विवेकशील और सशक्त बनाता है। "
        "बहुत से लोग इस अवधि से अधिक मज़बूत चरित्र, स्पष्ट मूल्यों और स्थिर संरचनाओं के साथ निकलते हैं। "
        "शास्त्रीय मत: जो धैर्य और अनुशासन के साथ शनि का सामना करते हैं, उन्हें गहरे, टिकाऊ लाभ मिलते हैं।",

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
    "nav_rashifal_link":   "राशिफल",
    "nav_ask_link":        "पूछें",

    # Rashifal page
    "rashifal_title":      "आज का राशिफल",
    "rashifal_subtitle":   "सभी 12 राशियों के लिए आज का भविष्यफल — अपनी जन्म राशि नीचे खोजें।",
    "rashifal_dont_know":  "अपनी जन्म राशि नहीं जानते? मुफ्त कुंडली बनाएँ — तुरंत पता चलेगा।",

    # Rashifal — the per-rashi standalone page (/rashifal/{rashi}), #124.
    #
    # HARVESTED, not invented. Nobody on this change is a native Hindi
    # speaker, so the wording is reused from Hindi already written in this
    # repo by a human: "आज का राशिफल" / "भविष्यफल" / "जन्म राशि" from the
    # keys just above, "व्हाट्सएप पर साझा करें" from templates/rashifal.html,
    # "पूरा विश्लेषण" / "जन्म कुंडली" from templates/email/welcome.html,
    # "राहु काल" / "अभिजित मुहूर्त" / "तिथि" / "नक्षत्र" from the panchang
    # keys. Composed-from-parts, and so the first thing a Hindi reviewer
    # should read: rashifal_deeper, rashifal_kundli_desc, the word "चौघड़िया"
    # (no Devanagari form of Choghadiya existed anywhere in the repo), and the
    # three labels in rashifal_single_attrs.
    "rashifal_single_title":    "{rashi_hi} राशिफल आज — {date} · दैनिक वैदिक भविष्यफल",
    "rashifal_single_meta":     "{rashi_hi} ({rashi_en}) राशि का आज का राशिफल, {date} — आज की वास्तविक ग्रह स्थिति पर आधारित विस्तृत वैदिक भविष्यफल: वार का स्वामी, तिथि और चंद्र नक्षत्र। पूरी तरह मुफ्त।",
    "rashifal_single_headline": "{rashi_hi} राशिफल — {date}",
    "rashifal_single_ld_desc":  "{rashi_hi} ({rashi_en}) राशि का आज का वैदिक राशिफल — {date}।",
    "rashifal_single_alt":      "{rashi_hi} ({rashi_en}) राशि का चिह्न",
    "rashifal_single_attrs":    "तत्व: {element} · स्वभाव: {quality} · स्वामी ग्रह: {lord}",
    "rashifal_single_share":    "{rashi_hi} राशिफल — {url}",
    "rashifal_all_12":          "← सभी 12 राशियाँ",
    "rashifal_share_whatsapp":  "व्हाट्सएप पर साझा करें",
    "rashifal_deeper":          "और विस्तृत पठन चाहते हैं?",
    "rashifal_kundli_cta":      "मुफ्त जन्म कुंडली →",
    "rashifal_kundli_desc":     "दशा, योग और व्यक्तिगत विश्लेषण सहित पूरी जन्म कुंडली — जन्म राशि से कहीं आगे।",
    "rashifal_panchang_cta":    "आज का पंचांग →",
    "rashifal_panchang_desc":   "आपके शहर के लिए तिथि, नक्षत्र, राहु काल, अभिजित मुहूर्त और चौघड़िया।",

    # The 12 rashi names in Devanagari, as spelled in knowledge/rashis.md
    # (§"The 12 rashis — appearance, character, body region"). That spelling
    # is also the one _subscribe_modal.html shipped, so moving the modal onto
    # this table leaves its rendered bytes untouched — note कुम्भ, not the
    # कुंभ that the unreferenced templates/rashifal.html uses.
    "rashi_name_aries":         "मेष",
    "rashi_name_taurus":        "वृषभ",
    "rashi_name_gemini":        "मिथुन",
    "rashi_name_cancer":        "कर्क",
    "rashi_name_leo":           "सिंह",
    "rashi_name_virgo":         "कन्या",
    "rashi_name_libra":         "तुला",
    "rashi_name_scorpio":       "वृश्चिक",
    "rashi_name_sagittarius":   "धनु",
    "rashi_name_capricorn":     "मकर",
    "rashi_name_aquarius":      "कुम्भ",
    "rashi_name_pisces":        "मीन",

    # Element / quality vocabulary — the same Devanagari the 12 cards on
    # rashifal_grid.html already show (its 8th and 9th tuple fields), so the
    # grid and the page a reader taps through to cannot disagree. Matches the
    # Tattva and Chara/Sthira/Dwiswabhava tables in knowledge/rashis.md.
    "rashi_element_fire":       "अग्नि",
    "rashi_element_earth":      "पृथ्वी",
    "rashi_element_air":        "वायु",
    "rashi_element_water":      "जल",
    "rashi_quality_movable":    "चर",
    "rashi_quality_fixed":      "स्थिर",
    "rashi_quality_dual":       "द्विस्वभाव",

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
    "dasha_view_full":     "पूर्ण दशा समय-रेखा →",

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
    "ask_eyebrow":            "शुभ भाग्य से पूछें",
    "ask_head_chart":         "अपनी कुंडली के बारे में कुछ भी पूछें",
    "ask_head_matching":      "अपने कुंडली मिलान के बारे में कुछ भी पूछें",
    "ask_head_numerology":    "अपने अंकों के बारे में कुछ भी पूछें",
    "ask_blurb_chart":        "आपके प्रश्न का उत्तर आपकी वास्तविक जन्म कुंडली से दिया जाता है — ग्रह स्थिति, वर्तमान दशा और वैदिक संकेत। स्पष्ट और सटीक, सामान्य बातें नहीं।",
    "ask_blurb_matching":     "आपके प्रश्न का उत्तर दोनों जन्म कुंडलियों और आपके गुण मिलान से दिया जाता है — कूट अंक, मंगल दोष, और कोई भी दोष। स्पष्ट और सटीक, सामान्य बातें नहीं।",
    "ask_blurb_numerology":   "आपके प्रश्न का उत्तर आपके अंकशास्त्र विश्लेषण और जन्म कुंडली, दोनों के आधार पर दिया जाता है। स्पष्ट और सटीक, सामान्य बातें नहीं।",
    "ask_head_matching_third":   "इस कुंडली मिलान के बारे में कुछ भी पूछें",
    "ask_blurb_matching_third":  "आप किसी और के मिलान के बारे में पूछ रहे हैं। आपके प्रश्न का उत्तर उनके गुण मिलान के आधार पर दिया जाता है — कूट अंक, मंगल दोष, और कोई भी दोष। स्पष्ट और सटीक, सामान्य बातें नहीं।",
    "ask_asking_about_their":    "किसके मिलान के बारे में:",
    "ask_opt_their_match":       "उनका मिलान",
    "ask_asking_for":         "किसके लिए:",
    "ask_asking_about":       "किसके बारे में:",
    "ask_switch_chart":       "कुंडली बदलें",
    "ask_new_match":          "नया मिलान",
    "ask_numerology_badge":   "अंकशास्त्र संदर्भ",
    "ask_answer_using":       "उत्तर किसके आधार पर",
    "ask_opt_both_charts":    "दोनों कुंडलियाँ",
    "ask_opt_my_chart":       "केवल मेरी कुंडली",
    "matching_charts_heading": "दोनों कुंडलियाँ",
    "matching_bhakoot":    "भकूट दोष",
    "matching_bhakoot_cancelled":   "परिहार लागू",
    "matching_bhakoot_uncancelled": "परिहार नहीं",
    "matching_bhakoot_applies":     "लागू परिहार",
    "matching_bhakoot_uneval":      "जाँच नहीं की गई",
    "matching_bhakoot_nopoints":
        "परिहार दोष को हटाता है। यह ऊपर दिए गए अंकों में वृद्धि नहीं करता।",
    "matching_nadi":        "नाड़ी दोष",
    "matching_nadi_grave":  "गंभीरतम रूप",
    "matching_nadi_alpa":   "अल्प",
    "matching_nadi_plain":  "विद्यमान",
    "matching_nadi_mitig":  "जो इसे कम करता है",
    "matching_nadi_nocancel":
        "नाड़ी का कोई परिहार नहीं होता। किसी भी छूट से इसके अंक नहीं बढ़ते।",
    "matching_breakdown":  "कूट-वार विवरण",
    "matching_col_koota":  "कूट",
    "matching_col_max":    "अधिकतम",
    "matching_col_score":  "प्राप्त",
    "matching_col_note":   "टिप्पणी",
    "matching_back":       "अन्य कुंडलियों का मिलान",
    "matching_caveat_heading": "अष्टकूट केवल पहला फ़िल्टर है, अंतिम निर्णय नहीं",
    "matching_caveat_body_1":  "गुण मिलान दो चंद्र-राशियों की आठ क्षेत्रों में तुलना करता है। यह यह नहीं जाँचता कि किसी एक कुंडली में स्वयं गंभीर दोष है या नहीं — भारी पापी दृष्टियों वाला सप्तम भाव, पीड़ित शुक्र, चंद्रमा से युत पापी ग्रह, या कठिन दशा-समय — जिन्हें शास्त्रीय ज्योतिष विवाह-निर्णय के लिए अनिवार्य मानता है।",
    "matching_caveat_body_2":  "दो व्यक्ति यहाँ पूर्ण अंक भी पा सकते हैं और फिर भी वैवाहिक कठिनाई झेल सकते हैं; दो व्यक्ति सीमा से नीचे भी हो सकते हैं और कुंडली की अन्य शक्तियाँ उस कमी की भरपाई कर सकती हैं। इस अंक को पहला फ़िल्टर मानें, अंतिम उत्तर नहीं।",
    "matching_caveat_body_3":  "विवाह-निर्णय से पहले दोनों कुंडलियों का व्यक्तिगत रूप से अध्ययन करवाएँ — सप्तम भाव और उसका स्वामी, शुक्र और गुरु की स्थिति, उपपद, तथा वर्तमान दशा सभी महत्वपूर्ण हैं। यदि आप चाहें, नीचे अपना विशिष्ट मिलान-प्रश्न पूछें — हम दोनों कुंडलियों को ध्यान में रखते हुए उत्तर देंगे।",
    "manglik_caveat_heading":  "मंगल दोष विवाह की पूरी कहानी नहीं है",
    "manglik_caveat_body":     "मंगल-सम्बन्धी दोष शास्त्रीय ज्योतिष के विवाह-मूल्यांकन में कई कारकों में से एक है। अच्छी स्थिति वाले मंगल के बावजूद भी यदि सप्तमेश, शुक्र, उपपद, या वर्तमान दशा में अन्य दोष हों तो वैवाहिक कठिनाई सम्भव है। इसी प्रकार, मजबूत रक्षक योगों वाली मंगली कुंडली में सुखी विवाह भी हो सकता है। इसे कई डेटा-बिन्दुओं में से एक मानें — यदि विवाह आपका मुख्य प्रश्न है तो किसी अनुभवी ज्योतिषी से सप्तम भाव का पूर्ण अध्ययन करवाना उचित है।",

    "ksy_caveat_heading":      "पढ़ने से पहले जानें: काल सर्प एक आधुनिक वर्गीकरण है",
    "ksy_caveat_body_1":       "इस साइट पर विश्लेषण किए जाने वाले अन्य योगों और दोषों के विपरीत, काल सर्प योग शास्त्रीय संस्कृत ज्योतिष ग्रंथों में परिभाषित नहीं है — न बृहत् पराशर होरा शास्त्र में, न बृहज्जातक में, न सारावली में, न फलदीपिका, जातक पारिजात, या उत्तर कालामृत में। यह अवधारणा भारतीय ज्योतिष लेखन में केवल 20वीं शताब्दी में उभरी और 1970-1980 के दशक के अंत में एस्ट्रोलॉजिकल मैगजीन में इस पर व्यापक बहस हुई।",
    "ksy_caveat_body_2":       "इसके भविष्यसूचक महत्त्व पर सम्मानित आचार्यों में मतभेद है। के.एन. राव (भारतीय विद्या भवन के ज्योतिष पाठ्यक्रम के संस्थापक) ने काल सर्प दोष को सार्वजनिक रूप से \"ज्योतिष की सबसे बड़ी धोखाधड़ियों में से एक\" तथा \"व्यक्तिगत कुंडलियों में अधिक महत्त्व का नहीं\" कहकर अस्वीकृत किया है। बी.वी. रमन (एस्ट्रोलॉजिकल मैगजीन के संपादक) ने Three Hundred Important Combinations के नौवें संस्करण में इसे परिशिष्ट के रूप में जोड़ा क्योंकि यह \"बहुत भयभीत करने वाला\" बन गया था — उनका स्वयं का उपचार सूक्ष्म था, भयजनक नहीं।",
    "ksy_caveat_body_3":       "हम यहाँ ज्यामिति दिखाते हैं क्योंकि यह एक वास्तविक कुंडली-पैटर्न है जिसके बारे में उपयोगकर्ता पूछते हैं — किंतु किसी भी एकल काल सर्प पठन को, विशेषकर त्र्यंबकेश्वर या अन्यत्र महँगे उपायों की सलाह देने वाले पठन को, स्वस्थ संदेह के साथ लें। राहु और केतु का गम्भीर पठन उनके साथ युत ग्रहों और भावेशों को देखकर होता है, न कि अक्षीय व्यापक योगों से।",
    "ksy_present_heading":     "काल सर्प ज्यामिति — उपस्थित",
    "ksy_present_subtitle":    "सातों गैर-छाया ग्रह राहु-केतु अक्ष के एक ओर स्थित हैं",
    "ksy_absent_heading":      "काल सर्प ज्यामिति — अनुपस्थित",
    "ksy_absent_body":         "आपकी कुंडली में सातों गैर-छाया ग्रह राहु-केतु अक्ष के दोनों ओर वितरित हैं, इसलिए काल सर्प पैटर्न लागू नहीं होता।",
    "ksy_variant_note":        "इस राहु-भाव स्थिति के लिए पारंपरिक नाग नाम। ये बारह नाम मध्य-20वीं शताब्दी के हिंदी पंचांग साहित्य से लोक-वर्गीकरण हैं, शास्त्रीय शास्त्र नहीं — इसलिए हम ज्यामिति का वर्णन करते हैं, प्रति-प्रकार भविष्यवाणी नहीं देते।",

    "num_caveat_heading":      "इस टूल के बारे में — परम्परा को लेकर ईमानदारी",
    "num_caveat_body_1":       "इस पृष्ठ पर दिखाई गई अंक-प्रणालियाँ — कालडियन (चीरो) और लो शू ग्रिड — 19वीं और 20वीं शताब्दी की पश्चिमी तथा प्राचीन चीनी जड़ों वाली आधुनिक परम्पराएँ हैं, शास्त्रीय वैदिक ज्योतिष की शाखाएँ नहीं। मूलभूत संस्कृत ज्योतिष ग्रंथ (बृहत् पराशर होरा शास्त्र, बृहज्जातक, सारावली, फलदीपिका, जातक पारिजात, उत्तर कालामृत) जन्मतिथि-न्यूनीकरण या अंग्रेजी-वर्णमाला नाम-अंकशास्त्र का वर्णन नहीं करते।",
    "num_caveat_body_2":       "लाइफ पाथ / एक्सप्रेशन / सोल अर्ज ढाँचा 1908 से मध्य-20वीं शताब्दी के बीच तीन अमेरिकियों — एल. डो बैलियेट, जूलिया सीटन (जिन्होंने ~1912 में \"numerology\" शब्द गढ़ा), और जूनो जॉर्डन ने बनाया था। व्यापक प्रचलन में \"कालडियन\" नाम-अंक तालिकाएँ चीरो (विलियम जॉन वार्नर, 1866-1936) से आती हैं। के.एन. राव जैसे सम्मानित ज्योतिष आचार्य अंकशास्त्र के बिना अभ्यास करते हैं; विद्वान श्यामसुन्दर दास तर्क देते हैं कि यह विधि सर्वव्यापी न होकर पंचांग- और वर्णमाला-निर्भर है (विक्रम संवत बनाम शक बनाम ग्रेगोरियन में अपनी जन्मतिथि को न्यूनीकरण करें और आपको अलग अंक मिलेंगे)।",
    "num_caveat_body_3":       "हम ये कैलकुलेटर इसलिए प्रकाशित करते हैं क्योंकि लाखों लोगों को यह अर्थपूर्ण लगता है और यह उपयोगी आत्म-चिंतन को प्रेरित कर सकता है। किन्तु परिणाम को चिंतनशील मानें, भविष्यसूचक नहीं — और अपनी वास्तविक जन्म कुंडली के ज्योतिष विश्लेषण के विकल्प के रूप में कभी नहीं। नीचे के खण्डों में से लो शू ग्रिड सबसे पाठ-सम्मत है (वास्तव में प्राचीन चीनी, ग्रेगोरियन पंचांग से स्वतंत्र); लाइफ पाथ और कर्मिक डेब्ट खण्ड 20वीं शताब्दी के पश्चिमी ढाँचे हैं।",
    "num_reflective_header":   "नीचे दिए गए विवरणों को भविष्यवाणी नहीं, आत्म-चिंतन के संकेत के रूप में पढ़ें। \"लाइफ पाथ 3\" यह नहीं बता रहा कि क्या होगा — यह उस पैटर्न का नाम है जिसे परम्परा आपकी जन्म-तिथि के योग से जोड़ती है, जिसे आप स्वीकार कर सकते हैं, प्रश्न कर सकते हैं, या अनदेखा कर सकते हैं।",

    "pdf_download":           "PDF डाउनलोड करें",
    "pdf_download_hint":      "आपके ब्राउज़र के प्रिंट → PDF के रूप में सहेजें विकल्प का उपयोग करता है। डेस्कटॉप पर काम करता है; मोबाइल पर प्रिंट पूर्वावलोकन दिखा सकता है।",
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
    "varshaphala_title":     "वर्षफल — आपका वार्षिक कुंडली",
    "varshaphala_subtitle":  "इस वर्ष जब सूर्य अपनी जन्म-सायन देशांश पर लौटेगा, उस क्षण पर निर्मित कुंडली",
    "varshaphala_solar_return": "सूर्य-प्रत्यागमन का क्षण",
    "varshaphala_annual_lagna": "वार्षिक लग्न",
    "varshaphala_annual_moon":  "वार्षिक चंद्र",
    "varshaphala_year_lord":    "वर्ष का स्वामी",
    "varshaphala_muntha":       "मुंथा भाव",
    "varshaphala_muntha_note":  "मुंथा वह भाव है जिसमें वार्षिक कुंडली के अनुसार जन्म-सूर्य की राशि स्थित है — शास्त्रीय रूप से वर्ष का केंद्रित भाव।",

    # ─── Nav labels added cycle 10 ───────────────────────────────────
    "nav_numerology_link":     "अंकशास्त्र",
    "nav_learn_link":          "सीखें",
    "nav_tools_menu":          "उपकरण",
    "nav_more_menu":           "अधिक",
    "nav_tool_panchang":       "आज का पंचांग",
    "nav_tool_muhurat":        "मुहूर्त खोजें",
    "nav_tool_festivals":      "त्यौहार कैलेंडर",
    "nav_tool_manglik":        "मंगल दोष जाँच",
    "nav_tool_sade_sati":      "साढ़े साती",
    "nav_tool_kaal_sarp":      "काल सर्प जाँच",

    # ─── Bhagya Score section ───────────────────────────────────────
    "bhagya_label":            "भाग्य",
    "bhagya_out_of":           "/ 100",
    "bhagya_heading":          "आपका भाग्य स्कोर",
    "bhagya_lede":             "ज्योतिष मौसम है, नियति नहीं। यह अंक आपके <strong>वर्तमान अध्याय</strong> को दर्शाता है — आज के महादशा और गोचर के आधार पर। जैसे ये बदलेंगे, यह अंक भी बदलेगा। नीचे देखें कौन से संकेत इसे प्रभावित कर रहे हैं।",
    "bhagya_why":              "यह अंक क्यों",
    "bhagya_show_all":         "सभी {n} संकेत दिखाएँ →",
    "num_bhagya_heading":      "आपका अंकशास्त्र भाग्य स्कोर",
    "num_bhagya_lede":         "आपकी संख्याओं से चरित्र-स्तरीय झलक। धीरे बदलती है (केवल व्यक्तिगत वर्ष सालाना बदलता है)। दैनिक गोचर के मौसम के लिए, अपनी <a href=\"/kundli\" class=\"text-astro-700 hover:underline font-semibold\">जन्म कुंडली भाग्य स्कोर</a> बनाएँ।",

    # ─── Ask CTA ─────────────────────────────────────────────────────
    "ask_cta_free":            "मुफ्त · कोई साइनअप नहीं",
    "ask_cta_remaining":       "आज {n} प्रश्न बाकी",
    "ask_cta_remaining_one":   "आज 1 प्रश्न बाकी",
    "ask_cta_head_saved":      "आज अपनी कुंडली के बारे में 3 प्रश्न मुफ्त पूछें",
    "ask_cta_head_no_chart":   "कुंडली बनाकर 3 मुफ्त व्यक्तिगत प्रश्न पाएं",
    "ask_cta_body_saved":      "आपकी वास्तविक कुंडली से सटीक उत्तर — विवाह का समय, करियर की दिशा, विशेष गोचर कब आएंगे। सामान्य राशिफल जैसी सलाह नहीं।",
    "ask_cta_head_matching_third": "आज इस कुंडली मिलान के बारे में 3 प्रश्न मुफ्त पूछें",
    "ask_cta_body_matching_third": "उनकी अनुकूलता पर सटीक उत्तर — कमज़ोर कूट व्यवहार में क्या असर डालते हैं, किसी दोष का वास्तविक अर्थ क्या है, विवाह का शुभ समय। सामान्य राशिफल जैसी सलाह नहीं।",
    "ask_cta_head_matching":   "आज अपने कुंडली मिलान के बारे में 3 प्रश्न मुफ्त पूछें",
    "ask_cta_body_matching":   "दोनों कुंडलियों और आपके गुण मिलान के आधार पर सटीक उत्तर — कमज़ोर कूट व्यवहार में क्या असर डालते हैं, किसी दोष का वास्तविक अर्थ क्या है, विवाह का शुभ समय। सामान्य राशिफल जैसी सलाह नहीं।",
    "ask_cta_body_no_chart":   "अपनी मुफ्त जन्म कुंडली बनाएँ और रोज़ 3 प्रश्न पूछें — \"मेरा विवाह कब होगा?\" या \"मेरे लिए सबसे अच्छा करियर क्या है?\" — आपकी वास्तविक कुंडली से उत्तर, टेम्पलेट से नहीं।",
    "ask_cta_button_saved":    "प्रश्न पूछें →",
    "ask_cta_button_no_chart": "मेरी कुंडली बनाएँ →",
    "ask_cta_hint_default":    "अपनी कुंडली के बारे में",

    "ask_ai_note_short":       "आपकी जन्म कुंडली से AI द्वारा उत्पन्न। एक प्रशिक्षित ज्योतिषी की अंतर्दृष्टि उन पैटर्नों को पकड़ती है जो मात्र गणना नहीं कर सकती — इसे प्रारम्भ बिन्दु मानें, अंतिम पठन नहीं।",
    "ask_ai_note_footer":      "ज्योतिष प्रवृत्तियाँ दिखाता है, निश्चित भाग्य नहीं। यह उपकरण आपकी कुंडली डेटा से AI-उत्पन्न पैटर्न पठन है — प्रशिक्षित ज्योतिषी के साथ जीवंत परामर्श का विकल्प नहीं। समय, चयन, और विषयों के प्रश्न सबसे अच्छे कार्य करते हैं; मृत्यु, बीमारी, या कठिन गारंटी के प्रश्न पूछने से बचें।",

    "bs_yogas_active":         "{n} शुभ योग सक्रिय ({names})",
    "bs_manglik_cancelled":    "शास्त्रीय नियमों से मंगल दोष निरस्त — कोई शुद्ध दोष नहीं",
    "bs_manglik_kuja_shukra":  "कुज-शुक्र पैटर्न (केवल शुक्र-अक्ष) — मुख्यधारा लग्न/चंद्र जाँच में मंगली नहीं",
    "bs_manglik_mitigated":    "मंगल दोष आंशिक रूप से न्यून (कुछ निवारण लागू)",
    "bs_manglik_present":      "मंगल दोष उपस्थित (इस कुंडली में कोई निवारण नहीं मिला)",
    "bs_sade_sati_peak":       "साढ़े साती चरम चरण — मध्य 2.5 वर्ष",
    "bs_sade_sati_rising":     "साढ़े साती आरोहण चरण — प्रारम्भिक ~2.5 वर्ष",
    "bs_sade_sati_setting":    "साढ़े साती निर्गम चरण — बाहर निकलने के ~2.5 वर्ष",
    "bs_sade_sati_inactive":   "साढ़े साती सक्रिय नहीं",
    "bs_ashtama_shani":        "अष्टम शनि गोचर (चंद्रमा से 8वें भाव में शनि)",
    "bs_kantaka_shani":        "कण्टक शनि गोचर (चंद्रमा से 4थे भाव में शनि)",
    "bs_kaal_sarp":            "काल सर्प पैटर्न ({variant}) — 20वीं-शताब्दी का वर्गीकरण, इसे संकेत मानें, अंतिम निर्णय नहीं",
    "bs_exalted":              "{n} ग्रह उच्च राशि में ({names})",
    "bs_debilitated":          "{n} ग्रह नीच राशि में ({names})",
    "bs_maha_benefic":         "वर्तमान महादशा: {lord} — एक स्वाभाविक शुभ काल",
    "bs_maha_malefic":         "वर्तमान महादशा: {lord} — एक कठिन, धैर्य-परीक्षक काल",
    "bs_antar_benefic":        "वर्तमान अंतर्दशा: {lord} — आगामी माह शुभ उप-प्रभाव लिए",
    "bs_antar_malefic":        "वर्तमान अंतर्दशा: {lord} — आगामी माह कठिन उप-प्रभाव लिए",
    "bs_jup_gochar_good":      "बृहस्पति गोचर चंद्रमा से {house} में — विस्तारक गोचर",
    "bs_jup_gochar_slow":      "बृहस्पति गोचर चंद्रमा से {house} में — धीमी बृहस्पति अवस्था",
    "bs_node_over_moon":       "{node} वर्तमान में जन्म चंद्रमा पर गोचर — अन्तर्मुखी / अशांत भावनात्मक वातावरण",
    "bs_node_over_lagna":      "{node} वर्तमान में जन्म लग्न पर गोचर — आत्म-छवि पुनर्गठित हो रही",

    "bs_label_strong":         "मजबूत वर्तमान अध्याय",
    "bs_label_steady":         "स्थिर काल",
    "bs_label_testing":        "परीक्षा काल — धैर्य फल देता है",
    "bs_label_deep":           "गहन शिक्षण काल — शास्त्रीय उपायों का महत्व अभी अधिक",

    "nbs_master_lp":           "मास्टर संख्या लाइफ पाथ {lp} — दुर्लभ, आध्यात्मिक रूप से सशक्त (उन्नत {base})",
    "nbs_supportive_lp":       "लाइफ पाथ {lp} — परंपरागत रूप से {planet} द्वारा शासित, एक स्वाभाविक सहायक संख्या",
    "nbs_karmic_debt":         "कर्मिक डेब्ट {names} उपस्थित — जीवन-पाठ विषय (आधुनिक पश्चिमी अंकशास्त्र पठन)",
    "nbs_lp_dest_friend":      "लाइफ पाथ {lp} और डेस्टिनी {d} मित्र संख्याएँ हैं — आंतरिक प्रेरणा और बाहरी भूमिका संरेखित",
    "nbs_lp_dest_enemy":       "लाइफ पाथ {lp} और डेस्टिनी {d} शत्रु संख्याएँ हैं — आंतरिक प्रेरणा और बाहरी भूमिका विरोधाभासी",
    "nbs_py_dynamic":          "पर्सनल ईयर {py} — गतिशील, पहल-अनुकूल वर्ष",
    "nbs_py_grind":            "पर्सनल ईयर {py} — धीमा, संरचनात्मक-कार्य वर्ष",
    "nbs_py_harmony":          "पर्सनल ईयर 6 — सामंजस्य / परिवार / उत्तरदायित्व वर्ष",
    "nbs_compound_good":       "कम्पाउंड {n} — इस परम्परा में सबसे शुभ नाम-संयुक्तांकों में से एक",
    "nbs_compound_challenge":  "कम्पाउंड {n} — चुनौतीपूर्ण संयुक्तांक (इस परम्परा में उठान-फिर-पतन पैटर्न)",

    "nbs_label_strong":        "मजबूत अंकशास्त्रीय अध्याय",
    "nbs_label_steady":        "स्थिर अंकशास्त्रीय आधार",
    "nbs_label_patience":      "अंकशास्त्रीय संकेत धैर्य माँगते हैं",
    "nbs_label_deep":          "गहन शिक्षण विषय — उपायों का महत्व",
    # See the _EN block for why these exist. COMPOSED, not harvested — a
    # native reader should check them along with the six already flagged.
    "llm_busy_title":   "अभी बहुत माँग है",
    "llm_busy_msg":     "\U0001F64F इस समय बहुत से जिज्ञासु एक साथ प्रश्न पूछ रहे हैं। कृपया कुछ मिनट बाद फिर प्रयास करें — आपकी दी हुई जानकारी सुरक्षित है और वैसी ही दोबारा भेजी जा सकती है।",
    "llm_error_title":  "कुछ त्रुटि हुई",
    "llm_error_msg":    "इस बार पठन पूरा नहीं हो सका। कृपया थोड़ी देर बाद फिर प्रयास करें — आपकी दी हुई जानकारी सुरक्षित है और वैसी ही दोबारा भेजी जा सकती है।",
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


# ---------------------------------------------------------------------------
# Devanagari lookups for astrology terms interpolated into strings
# ---------------------------------------------------------------------------
#
# The Bhagya-Score driver notes (chart.py compute_bhagya_score) render
# planet + yoga names inside translated sentences. If we pass raw
# English names ("Jupiter", "Malavya Yoga") the Hindi output reads
# "वर्तमान महादशा: Jupiter — एक स्वाभाविक शुभ काल" — jarring for a
# Hindi reader.
#
# These lookups localize a single planet or yoga name at a time so the
# call-site can render "बृहस्पति" or "मालव्य योग" in Hindi contexts.
# English name is returned unchanged for any lang != 'hi' or any name
# not in the lookup (defensive fallback — unknown names never break
# the sentence).

# 9 grahas in the classical Jyotish sequence. Sanskrit-Devanagari forms
# match K.N. Rao / P.V.R. Narasimha Rao conventions. Jupiter uses "गुरु"
# (Guru), which is more common in astrology contexts than "बृहस्पति"
# though both are correct.
_PLANET_NAMES_HI: Final[dict[str, str]] = {
    "Sun":     "सूर्य",
    "Moon":    "चंद्र",
    "Mars":    "मंगल",
    "Mercury": "बुध",
    "Jupiter": "गुरु",
    "Venus":   "शुक्र",
    "Saturn":  "शनि",
    "Rahu":    "राहु",
    "Ketu":    "केतु",
}

# 12 Kaal Sarp Naga variant labels encoded in chart.py _KAAL_SARP_TYPES.
# These are traditional Naga names in mid-20th-c. Hindi almanac literature
# (see chart.py provenance comment on classical status). Roman-Sanskrit
# in the compute layer → Devanagari for Hindi UI.
_KAAL_SARP_HI: Final[dict[str, str]] = {
    "Anant":     "अनंत",
    "Kulik":     "कुलिक",
    "Vasuki":    "वासुकी",
    "Shankhpal": "शंखपाल",
    "Padma":     "पद्म",
    "Mahapadma": "महापद्म",
    "Takshak":   "तक्षक",
    "Karkotak":  "कर्कोटक",
    "Shankchur": "शंखचूड़",
    "Ghatak":    "घातक",
    "Vishdhar":  "विषधर",
    "Sheshnag":  "शेषनाग",
}


# Classical yoga names encoded in chart.py compute layer. Sanskrit
# spellings. Fallback: return the English name unchanged.
_YOGA_NAMES_HI: Final[dict[str, str]] = {
    "Adhi Yoga":                     "अधि योग",
    "Amala Yoga":                    "अमला योग",
    "Anaphaa Yoga":                  "अनफा योग",
    "Bhadra Yoga":                   "भद्र योग",
    "Chandra-Mangala Yoga":          "चंद्र-मंगल योग",
    "Duradhara Yoga":                "दुरूधरा योग",
    "Gaja-Kesari Yoga":              "गजकेसरी योग",
    "Hamsa Yoga":                    "हंस योग",
    "Kemadruma Yoga":                "केमद्रुम योग",
    "Malavya Yoga":                  "मालव्य योग",
    "Ruchaka Yoga":                  "रुचक योग",
    "Sasha Yoga":                    "शश योग",
    "Sunaphaa Yoga":                 "सुनफा योग",
    "Trilochana Yoga":               "त्रिलोचन योग",
    "Ubhayachara Yoga":              "उभयचरी योग",
    "Vasumati Yoga":                 "वसुमती योग",
    "Vesi Yoga":                     "वेसि योग",
    "Vosi Yoga":                     "वोसि योग",
    "Harsha Yoga (Vipareeta Raja)":  "हर्ष योग (विपरीत राज)",
    "Sarala Yoga (Vipareeta Raja)":  "सरल योग (विपरीत राज)",
    "Vimala Yoga (Vipareeta Raja)":  "विमल योग (विपरीत राज)",
}


def planet_name(name: str, lang: str) -> str:
    """Localize a planet name. English pass-through for non-Hindi langs."""
    if lang == "hi":
        return _PLANET_NAMES_HI.get(name, name)
    return name


def yoga_name(name: str, lang: str) -> str:
    """Localize a yoga name. English pass-through for non-Hindi langs."""
    if lang == "hi":
        return _YOGA_NAMES_HI.get(name, name)
    return name


def kaal_sarp_variant_name(name: str, lang: str) -> str:
    """Localize a Kaal Sarp Naga variant label. English pass-through for
    non-Hindi langs. Unknown label falls through unchanged."""
    if lang == "hi":
        return _KAAL_SARP_HI.get(name, name)
    return name


def planet_names_joined(names, lang: str, sep: str = ", ") -> str:
    """Localize an iterable of planet names and join. Common helper for
    the Bhagya driver notes that need e.g. 'Jupiter, Venus' as one arg."""
    return sep.join(planet_name(n, lang) for n in names)


def yoga_names_joined(names, lang: str, sep: str = ", ") -> str:
    """Localize an iterable of yoga names and join. Common helper for
    the Bhagya driver notes that render 'N auspicious yogas active (...)'.
    """
    return sep.join(yoga_name(n, lang) for n in names)
