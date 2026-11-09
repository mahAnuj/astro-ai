"""#798: /festivals and /muhurat take "today" from the IST day, not the server's UTC date."""

MUTATIONS = [
    ("#798: /festivals takes today from the server's UTC date again (a day behind the strip 00:00-05:30 IST)",
     "src/astro_ai/routes/festivals.py",
     "    today = reading_today()\n",
     "    from datetime import date\n    today = date.today()\n",
     "test_festivals_window_starts_on_the_ist_day"),

    ("#798: /muhurat/<event> pre-fills the start date from the server's UTC date again",
     "src/astro_ai/routes/muhurat.py",
     "         \"prefill_city\": prefill_city,\n         \"prefill_start\": reading_today().isoformat(),\n         \"has_saved_chart\"",
     "         \"prefill_city\": prefill_city,\n         \"prefill_start\": __import__(\"datetime\").date.today().isoformat(),\n         \"has_saved_chart\"",
     "test_muhurat_prefills_the_ist_day"),

    ("#798: /muhurat pre-fills the start date from the server's UTC date again",
     "src/astro_ai/routes/muhurat.py",
     "         \"prefill_city\": prefill_city,\n         \"prefill_start\": reading_today().isoformat(),\n         \"event_types\"",
     "         \"prefill_city\": prefill_city,\n         \"prefill_start\": __import__(\"datetime\").date.today().isoformat(),\n         \"event_types\"",
     "test_muhurat_prefills_the_ist_day"),
]
