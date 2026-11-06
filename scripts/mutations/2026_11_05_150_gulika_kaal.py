"""#150 slice 1: Gulika Kaal on /panchang (Saturn's part of the eight)."""

MUTATIONS = [
    ("#150: Saturday's Gulika ordinal is 2 instead of Rao Table 10's 1",
     "src/astro_ai/chart.py",
     "    5: 1,  # Saturday  — 1st part",
     "    5: 2,  # Saturday  — 1st part",
     "test_gulika_window_is_saturns_part_of_the_table_10_cycle"),

    ("#150: Sunday's Gulika ordinal is 8 (the lord-less slot) instead of 7",
     "src/astro_ai/chart.py",
     "    6: 7,  # Sunday    — 7th part",
     "    6: 8,  # Sunday    — 7th part",
     "test_gulika_window_is_saturns_part_of_the_table_10_cycle"),

    ("#150: Gulika's window is cut from the Rahu Kaal segment, not its own",
     "src/astro_ai/chart.py",
     "    gk_segment_idx = _GULIKA_SEGMENT[weekday]",
     "    gk_segment_idx = _RAHU_KAAL_SEGMENT[weekday]",
     "test_gulika_window_is_saturns_part_of_the_table_10_cycle"),

    ("#150: the Gulika card is gone from /panchang",
     "src/astro_ai/templates/panchang.html",
     "tracking-wider mb-1\">Gulika Kaal (avoid)</div>",
     "tracking-wider mb-1\">Gulikai (avoid)</div>",
     "test_the_page_shows_the_gulika_card_on_an_ordinary_day"),

    ("#150: the Gulika card prints Rahu Kaal's end instead of its own",
     "src/astro_ai/templates/panchang.html",
     "— {{ p.gulika_end.strftime('%H:%M') }}",
     "— {{ p.rahu_kaal_end.strftime('%H:%M') }}",
     "test_the_page_shows_the_gulika_card_on_an_ordinary_day"),

    ("#150: the Gulika subtitle drops the inference disclosure",
     "src/astro_ai/templates/panchang.html",
     "Saturn's 1/8 of daylight, inferred from Rao and confirmed against a published almanac",
     "Saturn's 1/8 of daylight, as stated by Rao",
     "test_the_page_shows_the_gulika_card_on_an_ordinary_day"),

    ("#150: the explainer says Gulikai is deferred again",
     "src/astro_ai/templates/panchang.html",
     "<strong>Yamaganda and Brahma Muhurta</strong> &mdash; two more classical timings we do not show yet",
     "<strong>Yamaganda / Gulikai</strong> &mdash; two more classical timings (deferred to a next release)",
     "test_the_deferred_line_names_only_what_is_still_deferred"),

    ("#150: the polar disclosure stops naming Gulika Kaal as withheld",
     "src/astro_ai/templates/panchang.html",
     "<strong>Rahu Kaal, Gulika Kaal, Abhijit Muhurat and Choghadiya are each",
     "<strong>Rahu Kaal, Abhijit Muhurat and Choghadiya are each",
     "test_a_polar_day_has_no_gulika_card_and_no_inverted_window"),

    ("#150: a second Gulika card is rendered OUTSIDE the daylight_ordinary guard (Tromso prints an inverted window)",
     "src/astro_ai/templates/panchang.html",
     "    {%- else %}\n    <div class=\"sm:col-span-2 lg:col-span-3 bg-amber-50 border border-amber-200 p-4\">\n      <div class=\"text-[11px] uppercase font-semibold text-amber-800 tracking-wider mb-1\">No ordinary sunrise-to-sunset day</div>",
     "    {%- else %}\n    <div class=\"p-4\"><div>Gulika Kaal (avoid)</div><div>{{ p.gulika_start.strftime('%H:%M') }} — {{ p.gulika_end.strftime('%H:%M') }}</div></div>\n    <div class=\"sm:col-span-2 lg:col-span-3 bg-amber-50 border border-amber-200 p-4\">\n      <div class=\"text-[11px] uppercase font-semibold text-amber-800 tracking-wider mb-1\">No ordinary sunrise-to-sunset day</div>",
     "test_a_polar_day_has_no_gulika_card_and_no_inverted_window"),

    ("#150: Gate 8's almanac row for Friday is shifted an hour",
     "scripts/verify_panchang_angas.py",
     "(\"2026-11-06\", \"Fri\", \"06:37\", \"17:33\", \"07:59\", \"09:21\"),",
     "(\"2026-11-06\", \"Fri\", \"06:37\", \"17:33\", \"08:59\", \"10:21\"),",
     "test_the_almanac_gate_is_green_and_can_go_red"),

    ("#150: Gate 8's tolerance is widened past one eighth of daylight",
     "scripts/verify_panchang_angas.py",
     "GULIKA_TOLERANCE_MIN = 1.0",
     "GULIKA_TOLERANCE_MIN = 100.0",
     "test_the_almanac_gate_is_green_and_can_go_red"),

    ("#150: Gate 8C no longer compares the ordinals",
     "scripts/verify_panchang_angas.py",
     "        ok = got == want\n",
     "        ok = True\n",
     "test_the_almanac_gate_is_green_and_can_go_red"),

    ("#150: a Gulika line is added to the LLM prompt block",
     "src/astro_ai/chart.py",
     "        f\"{panchang.rahu_kaal_start.strftime('%H:%M')}–{panchang.rahu_kaal_end.strftime('%H:%M')} local\\n\"",
     "        f\"{panchang.rahu_kaal_start.strftime('%H:%M')}–{panchang.rahu_kaal_end.strftime('%H:%M')} local; Gulika {panchang.gulika_start.strftime('%H:%M')}\\n\"",
     "test_gulika_adds_no_tokens_to_any_llm_prompt"),
]
