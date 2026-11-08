"""#794: rashifal, /today, /outlook and the email path take "today" from the IST day."""

MUTATIONS = [
    ("#794: reading_today() returns the server's UTC date (a day behind from 00:00-05:30 IST)",
     "src/astro_ai/chart.py",
     "    return local_today(RASHIFAL_REFERENCE_TZ)\n",
     "    return local_today(\"UTC\")\n",
     "test_reading_today_is_the_ist_date_not_the_utc_date"),

    ("#794: the /rashifal grid dates the page by the server's UTC date",
     "src/astro_ai/routes/rashifal.py",
     "    lang = _lang(request)\n    today_iso = reading_today().isoformat()\n    return _no_cdn_cache(",
     "    lang = _lang(request)\n    today_iso = __import__(\"datetime\").date.today().isoformat()\n    return _no_cdn_cache(",
     "test_the_rashifal_grid_names_the_ist_day"),

    ("#794: /rashifal/{rashi} reads and writes the daily cache under the UTC date",
     "src/astro_ai/routes/rashifal.py",
     "    ui = _RASHIFAL_UI_META[canonical_slug]\n    today_iso = reading_today().isoformat()",
     "    ui = _RASHIFAL_UI_META[canonical_slug]\n    today_iso = __import__(\"datetime\").date.today().isoformat()",
     "test_a_single_rashifal_is_looked_up_and_dated_by_the_ist_day"),

    ("#794: /today dates the page by the server's UTC date",
     'src/astro_ai/routes/today.py',
     '            "today_date": reading_today().isoformat(),\n            "today_pretty": _pretty_date(reading_today().isoformat(), lang),',
     '            "today_date": __import__("datetime").date.today().isoformat(),\n            "today_pretty": _pretty_date(__import__("datetime").date.today().isoformat(), lang),',
     'test_today_and_outlook_name_the_ist_day'),

    ("#794: /monthly and /yearly date the page by the server's UTC date",
     'src/astro_ai/routes/outlook.py',
     '            "today_date": reading_today().isoformat(),\n            "today_pretty": _pretty_date(reading_today().isoformat(), lang),',
     '            "today_date": __import__("datetime").date.today().isoformat(),\n            "today_pretty": _pretty_date(__import__("datetime").date.today().isoformat(), lang),',
     'test_today_and_outlook_name_the_ist_day'),

    ("#794: the email context dates the message by the server's UTC date",
     "src/astro_ai/routes/subscribe.py",
     "    today = reading_today()\n    panchang = _panchang_for_city(",
     "    today = __import__(\"datetime\").date.today()\n    panchang = _panchang_for_city(",
     "test_the_email_context_dates_the_message_by_the_ist_day"),
]
