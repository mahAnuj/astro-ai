"""#593: /panchang and the home strip take "today" from the city's timezone."""

MUTATIONS = [
    ("#593: /panchang takes today from the server's UTC date again (a day behind the strip 00:00-05:30 IST)",
     "src/astro_ai/routes/panchang.py",
     "_render_panchang(request, None, city)",
     "_render_panchang(request, date.today(), city)",
     "test_panchang_and_the_home_strip_name_the_same_day"),

    ("#593: the Today badge on an archive page compares against the server's UTC date",
     "src/astro_ai/routes/panchang.py",
     "    today_iso = local_today(\n        chart_for_loc.birth_tz if chart_for_loc else \"Asia/Kolkata\").isoformat()",
     "    today_iso = date.today().isoformat()",
     "test_the_today_badge_follows_the_citys_date_not_the_servers"),

    ("#593: a cached strip is served as today after its city has rolled past midnight",
     "src/astro_ai/routes/deps.py",
     "if hit_today is not None and _strip_is_current(hit_today[0]):",
     "if hit_today is not None:",
     "test_the_strip_cache_rolls_over_at_the_citys_midnight"),

    ("#593: the strip's currency check compares against the server's UTC date, not the city's",
     "src/astro_ai/routes/deps.py",
     "_WEEKDAY_NAMES[local_today(pan.sunrise.tzinfo).weekday()]",
     "_WEEKDAY_NAMES[date.today().weekday()]",
     "test_the_strip_cache_rolls_over_at_the_citys_midnight"),

    ("#593: the page stops stating which day convention it uses",
     "src/astro_ai/templates/panchang.html",
     "data-day-convention>{{ t(lang, 'panchang_day_convention', city=city_display) }}",
     "data-day-x>{{ t(lang, 'panchang_day_convention', city=city_display) }}",
     "test_the_page_states_which_day_it_means_in_both_languages"),

    ("#593: the Hindi page falls back to the English convention line",
     "src/astro_ai/i18n.py",
     "\"panchang_day_convention\": \"तारीख़ और वार",
     "\"panchang_day_convention\": \"Date and weekday follow the civil day in {city}. तारीख़ और वार",
     "test_the_page_states_which_day_it_means_in_both_languages"),
]
