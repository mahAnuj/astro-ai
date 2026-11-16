"""#1074: a dated /panchang/{date} snippet names its own date and carries the values."""

MUTATIONS = [
    ("#1074: a dated Panchang title says \"Today's\" again (false on every archive URL)",
     "src/astro_ai/templates/panchang.html",
     "{% block title %}{% if is_today %}Today's Panchang — {{ today_pretty }} · Tithi, Nakshatra, Rahu Kaal, Choghadiya{% else %}Panchang {{ today_pretty }}",
     "{% block title %}{% if True %}Today's Panchang — {{ today_pretty }} · Tithi, Nakshatra, Rahu Kaal, Choghadiya{% else %}Panchang {{ today_pretty }}",
     "test_a_dated_title_does_not_say_today_and_names_the_date"),

    ("#1074: a dated description is the generic values-free copy again",
     "src/astro_ai/templates/panchang.html",
     "{% block meta_description %}{% if not is_today %}{{ dated_description }}{% else %}",
     "{% block meta_description %}{% if False %}{{ dated_description }}{% else %}",
     "test_the_dated_description_carries_the_rendered_values"),

    ("#1074: the sentence prints a polar date's Rahu Kaal window (backwards, #227)",
     "src/astro_ai/routes/panchang.py",
     "    if p.daylight_ordinary:\n        parts.append(",
     "    if True:\n        parts.append(",
     "test_a_polar_date_omits_rahu_kaal_from_sentence_and_description"),
]
