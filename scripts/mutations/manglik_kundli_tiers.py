"""#429: the /kundli result page stops presenting the Manglik tiers as classical.

Each row restores one piece of the old, undisclosed text (or breaks the wiring
that shows the new text) and names the test that must go red."""

MUTATIONS = [
    ("#429: the English moderate-tier text is 'a moderate form of Manglik' again",
     "src/astro_ai/i18n.py",
     "counts toward Manglik here, and Bhagya grades it moderate, below the 7th and 8th. "
     "That grade is Bhagya's own weighting, not a classical grade, and it is not drawn "
     "from the classical texts we hold.",
     "is a moderate form of Manglik.",
     "test_english_lower_tiers_say_the_grade_is_bhagyas_own_weighting"),
    ("#429: the English low-tier text is 'the mildest form of Manglik' again",
     "src/astro_ai/i18n.py",
     "counts toward Manglik here, and Bhagya grades it low. That grade is Bhagya's own "
     "weighting, not a classical grade, and it is not drawn from the classical texts we hold.",
     "is the mildest form of Manglik.",
     "test_english_lower_tiers_say_the_grade_is_bhagyas_own_weighting"),
    ("#429: the Hindi moderate-tier text is 'मध्यम स्वरूप' again",
     "src/astro_ai/i18n.py",
     "यह श्रेणी शुभ भाग्य का अपना भार-निर्धारण है, कोई शास्त्रीय श्रेणी नहीं, और हमारे पास उपलब्ध "
     "शास्त्रीय ग्रंथों से नहीं ली गई है। प्रथम व्यक्तित्व",
     "यह मंगल दोष का मध्यम स्वरूप है। प्रथम व्यक्तित्व",
     "test_hindi_lower_tiers_say_the_grade_is_bhagyas_own_weighting"),
    ("#429: the Hindi low-tier text is 'सबसे हल्का स्वरूप' again",
     "src/astro_ai/i18n.py",
     "यह श्रेणी शुभ भाग्य का अपना भार-निर्धारण है, कोई शास्त्रीय श्रेणी नहीं, और हमारे पास उपलब्ध "
     "शास्त्रीय ग्रंथों से नहीं ली गई है। द्वितीय मुख्य",
     "यह मंगल दोष का सबसे हल्का स्वरूप है। द्वितीय मुख्य",
     "test_hindi_lower_tiers_say_the_grade_is_bhagyas_own_weighting"),
    ("#429: the 2nd-house text claims 'some traditions exclude' it again (both held lists include it)",
     "src/astro_ai/i18n.py",
     "The 2nd mainly affects speech and family dynamics.",
     "The 2nd mainly affects speech and family dynamics. Some traditions exclude 2nd-house Manglik entirely.",
     "test_the_2nd_house_text_no_longer_claims_traditions_exclude_it"),
    ("#429: the result page shows the low tier the moderate text",
     "src/astro_ai/templates/result.html",
     "'low': 'manglik_about_low'}.get(manglik.severity",
     "'low': 'manglik_about_moderate'}.get(manglik.severity",
     "test_result_page_low_tier_carries_the_disclosure_in_both_languages"),
    ("#429: the result page stops keying the about-text off the severity (every tier reads 'high')",
     "src/astro_ai/templates/result.html",
     "{{ t(lang, manglik_about_key) }}</p>",
     "{{ t(lang, 'manglik_about_high') }}</p>",
     "test_result_page_moderate_tier_carries_the_disclosure_in_both_languages"),
    ("#429: the high tier's text is replaced by the moderate one on the result page",
     "src/astro_ai/templates/result.html",
     "{'high': 'manglik_about_high', 'moderate'",
     "{'high': 'manglik_about_moderate', 'moderate'",
     "test_result_page_high_tier_is_unchanged"),
]
