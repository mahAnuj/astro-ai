"""Mutation-test the behaviour suite: revert each fix, confirm the suite goes red.

A gate that has never failed is not evidence. Every mutation below restores,
verbatim, a defect that actually shipped into a commit and was caught by
review rather than by anything automated.

Run this after adding a test, and after any refactor of the code it guards.
Writing this harness immediately paid for itself: it found that two of the
concurrency tests reimplemented the logic inside the test body instead of
calling the real function, so they would have passed forever regardless of
what the code did. Two gates that could not fail, in the suite written to stop
exactly that.

It restores every file it touches, including on failure. It runs the WHOLE
suite per mutation, not the one test nominated in the table — the question is
"does the suite catch this", not "does the test I had in mind catch this", and
those differ: the `del` race is caught by a static guard in a different test
from the concurrency one.

    uv run python scripts/mutate_behaviour_suite.py     # exit 1 if any escapes
"""
import concurrent.futures
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile

MUTATIONS = [
    ("deps: del instead of pop (the HIGH KeyError race)",
     "src/astro_ai/routes/deps.py",
     "_fallback_cache.pop(key, None)", "del _fallback_cache[key]",
     "test_no_unguarded_del_on_a_shared_dict"),

    ("deps: live comprehension in eviction (dict changed size)",
     "src/astro_ai/routes/deps.py",
     "for stale in [k for k in tuple(_PANCHANG_STRIP_CACHE)",
     "for stale in [k for k in _PANCHANG_STRIP_CACHE",
     "test_eviction_is_concurrency_safe"),

    ("deps: fallback returns nothing (strip blanks)",
     "src/astro_ai/routes/deps.py",
     "        _remember_degraded(key, result)\n        return result",
     "        _remember_degraded(key, (None, None, \"\"))\n        return (None, None, \"\")",
     "test_fallback_keeps_the_strip_visible"),

    ("deps: no short-circuit on the default city (double solve)",
     "src/astro_ai/routes/deps.py",
     "            if resolved_city == _STRIP_DEFAULT_CITY:", "            if False:",
     "test_signed_out_outage_solves_once_not_twice"),

    ("rashifal: cooldown raises instead of returning (81KB into the card)",
     "src/astro_ai/routes/rashifal.py",
     "        if is_htmx:\n            return HTMLResponse(\n                _reading_error_fragment(canonical_slug, True, _cool_msg, lang,\n                                        request.url.path),\n                status_code=503,\n            )",
     "        if is_htmx:\n            raise HTTPException(status_code=503, detail='x')",
     "test_cooldown_returns_a_card_not_a_document"),

    ("rashifal: no regen cooldown (unbounded LLM cost)",
     "src/astro_ai/routes/rashifal.py",
     "    if reading_body is None and _regen_blocked(cache_key):",
     "    if False and _regen_blocked(cache_key):",
     "test_degraded_generation_is_bounded"),

    ("subscribe: subscriber list read twice (false 500)",
     "src/astro_ai/routes/subscribe.py",
     "    total = len(subs)", "    total = len(subscribers.list_subscribers())",
     "test_signup_landing_mid_run_is_not_a_false_failure"),

    ("#124: /hi catch-all normalises the path again (the 2-hop /learn bug)",
     "src/astro_ai/routes/hindi.py",
     "target = twin if twin is not None else hindi_pages.strip_hi_prefix(requested)",
     "target = twin if twin is not None else hindi_pages.english_url(requested)",
     "test_hi_redirects_take_exactly_one_hop"),

    ("#124: i18n symmetry — a Hindi key goes missing (silent English)",
     "src/astro_ai/i18n.py",
     '"nav_home":            "मुख्य पृष्ठ",',
     '"nav_home_DISABLED":            "मुख्य पृष्ठ",',
     "test_key_sets_are_identical"),

    ("#124: error fragment prefix back to language-keyed",
     "src/astro_ai/routes/rashifal.py",
     'prefix = "/hi" if (path or "").startswith("/hi/")',
     'prefix = "/hi" if lang == "hi"',
     "test_error_fragment_permalink_is_path_keyed"),

    ("#124: unknown-rashi 404 reverts to English",
     "src/astro_ai/routes/rashifal.py",
     '{"title": t(lang, "rashifal_unknown_title"),',
     '{"title": "Unknown rashi",',
     "test_unknown_rashi_404_is_localised"),

    ("#124: Hindi 404 directs the reader to the English hub",
     "src/astro_ai/i18n.py",
     "चुनने के लिए /hi/rashifal देखें",
     "चुनने के लिए /rashifal देखें",
     "test_hindi_404_does_not_send_readers_to_the_english_hub"),

    ("#124: cooldown degraded page reverts to English",
     "src/astro_ai/routes/rashifal.py",
     '{"title": t(lang, "rashifal_not_ready_title"),',
     '{"title": "Reading not ready yet",',
     "test_cooldown_degraded_page_is_localised"),

    ("#124: degraded card retry fetches the English fragment",
     "src/astro_ai/routes/rashifal.py",
     'hx-get="{prefix}/rashifal/{slug}"',
     'hx-get="/rashifal/{slug}"',
     "test_degraded_card_retry_stays_in_hindi"),

    ("#124: picker next reverts to the normalising english_url",
     "src/astro_ai/templates/_lang_picker.html",
     "{{ strip_hi_prefix(request.url.path) }}",
     "{{ english_url(request.url.path) }}",
     "test_language_control_posts_a_non_normalised_next"),

    ("#124: /lang stops routing Hindi to the published twin",
     "src/astro_ai/routes/account.py",
     "        target = hindi_pages.hindi_url(target) or target",
     "        pass",
     "test_language_switch_works_from_every_starting_state"),

    ("#124: lang_prefix keyed on language alone, ignoring the path",
     "src/astro_ai/routes/deps.py",
     '    return "/hi" if path.startswith("/hi/") or path == "/hi" else ""',
     '    return "/hi"',
     "test_lang_prefix_is_keyed_on_path_not_language_alone"),

    ("#124: Hindi card fragment links and shares the English URL",
     "src/astro_ai/routes/rashifal.py",
     '    if _lang_prefix(lang, request.url.path):\n        permalink = hindi_pages.hindi_url(permalink) or permalink\n',
     "",
     "test_hindi_card_fragment_stays_in_hindi"),

    ("#124: non-canonical URLs regain a one-sided hreflang set",
     "src/astro_ai/hindi_pages.py",
     "    if path != _normalise(path):\n        return []\n",
     "",
     "test_noncanonical_url_emits_no_hreflang"),

    ("#124: open redirect — same-origin guard removed",
     "src/astro_ai/routes/hindi.py",
     '    if not target.startswith("/") or target.startswith("//"):\n        target = "/"\n',
     "",
     "test_hi_catchall_cannot_redirect_off_site"),

    ("#124: Hindi hub tiles fetch English readings",
     "src/astro_ai/templates/rashifal_grid.html",
     'hx-get="{{ lang_prefix }}/rashifal/{{ slug }}"',
     'hx-get="/rashifal/{{ slug }}"',
     "test_hindi_hub_tiles_fetch_hindi_readings"),

    ("#124: hreflang x-default points at the Hindi URL",
     "src/astro_ai/hindi_pages.py",
     "(_DEFAULT_TAG, en),",
     "(_DEFAULT_TAG, hi),",
     "test_hreflang_hrefs_point_at_the_right_urls"),

    ("#124: hi-IN points at the English URL",
     "src/astro_ai/hindi_pages.py",
     "(_HI_TAG, hi),",
     "(_HI_TAG, en),",
     "test_hreflang_hrefs_point_at_the_right_urls"),

    ("#124: canonical reverts to the cross-language form",
     "src/astro_ai/templates/base.html",
     '<link rel="canonical" href="{{ site_url }}{{ request.url.path }}">',
     '<link rel="canonical" href="{{ site_url }}{{ english_url(request.url.path) }}">',
     "test_hindi_url_is_self_canonical"),

    ("#124: hreflang leaks onto pages with no Hindi twin",
     "src/astro_ai/templates/base.html",
     "hreflang_alternates(request.url.path)",
     "hreflang_alternates('/rashifal')",
     "test_unpublished_pages_emit_no_hreflang"),

    ("#124: /hi stops forcing Hindi",
     "src/astro_ai/routes/hindi.py",
     '    request.state.forced_lang = "hi"',
     "    pass",
     "test_hi_prefix_actually_serves_hindi"),

    ("#124: Hindi rashi title falls back to English chrome",
     "src/astro_ai/templates/rashifal_single.html",
     "{% block title %}{{ t(lang, 'rashifal_single_title'",
     "{% block title %}{{ t('en', 'rashifal_single_title'",
     "test_rashi_page_hindi_surface_is_actually_hindi"),

    ("subscribe: ok is always True (the 21-day silence)",
     "src/astro_ai/routes/subscribe.py",
     "    ok = not unreadable_list and not delivered_none and failed == 0", "    ok = True",
     "test_total_delivery_failure_is_not_reported_as_success"),

    # #220. Narrowing the handler to a class the loop never raises is the same
    # thing as having no handler, which is what the code did: one bad
    # subscriber row escaped past both alerts and past the outcome JSON.
    ("subscribe: per-subscriber raise escapes the loop again (#220)",
     "src/astro_ai/routes/subscribe.py",
     "        except Exception as exc:  # noqa: BLE001 — one bad row must not end the blast",
     "        except SystemExit as exc:  # noqa: BLE001 — mutated: catches nothing raised here",
     "test_a_raising_subscriber_does_not_abort_the_blast"),

    # #222. Raw addresses back into the Telegram channel and into the
    # /admin/activity error log GCS keeps for 30 days.
    ("subscribe: raw subscriber addresses back into the alert (#222)",
     "src/astro_ai/routes/subscribe.py",
     "                         f\" (first: {_mask_email(failures[0])})\"),",
     "                         f\": {failures[:5]}\"),",
     "test_partial_alert_carries_no_raw_subscriber_address"),

    # The three rows below came out of QA mutating this suite itself. Two guard
    # the follow-up fix to #220 — a non-string `email` raised inside the
    # partial alert, below the loop and outside its handler, so the loop's fix
    # had relocated the silence rather than removed it. The third guards a
    # behaviour that was already correct but ungated: QA reverted the no-`@`
    # branch to `return email` and all ten tests still passed.
    ("subscribe: _mask_email raises on a non-string email again",
     "src/astro_ai/routes/subscribe.py",
     "    if not isinstance(email, str):\n        return \"***\"",
     "    if isinstance(email, str) and False:\n        return \"***\"",
     "test_a_non_string_email_does_not_cost_the_alert_or_the_outcome_json"),

    ("subscribe: _mask_email returns the raw value when there is no `@`",
     "src/astro_ai/routes/subscribe.py",
     "    local, _, domain = email.partition(\"@\")\n    if not domain:\n        return \"***\"",
     "    local, _, domain = email.partition(\"@\")\n    if not domain:\n        return email",
     "test_masked_address_with_no_at_sign_reveals_nothing"),

    # Narrowing this handler to a class the alerts never raise is the same as
    # deleting it — #220's silence, moved below the loop instead of inside it.
    ("subscribe: a raising alert kills the outcome JSON again",
     "src/astro_ai/routes/subscribe.py",
     "    except Exception:  # noqa: BLE001 — alerting must never cost the outcome JSON",
     "    except SystemExit:  # noqa: BLE001 — mutated: catches nothing the alerts raise",
     "test_a_raising_alert_does_not_cost_the_outcome_json"),

    # #223. #220's guard covered a malformed FIELD; these two are the malformed
    # ROW and the malformed LIST, one and two frames further out. Both raise
    # outside every handler in the endpoint, so both reproduce #220's silence
    # exactly: HTML 500, no outcome JSON, no alert, no retry.
    ("subscribe: the row read moves back outside the guard (#223)",
     "src/astro_ai/routes/subscribe.py",
     "        send_err: Exception | None = None\n        email = \"\"\n        try:",
     "        email = sub.get(\"email\", \"\")\n        send_err: Exception | None = None\n        try:",
     "test_a_row_that_is_not_a_dict_does_not_abort_the_blast"),

    ("subscribe: an unreadable subscriber list is iterated anyway (#223)",
     "src/astro_ai/routes/subscribe.py",
     "    unreadable_list = not isinstance(subs, list)",
     "    unreadable_list = False",
     "test_an_unreadable_subscriber_list_still_reports_an_outcome"),

    # #225. The row above guards the FIRST alert block; this one guards the
    # SECOND, which was ungated — mutating it alone left the whole suite green,
    # because the only test that raised an alert drove a full 12-section
    # reading and never entered the short-sections branch.
    ("subscribe: a raising short-sections alert kills the outcome JSON",
     "src/astro_ai/routes/subscribe.py",
     "        except Exception:  # noqa: BLE001 — same: the outcome JSON outranks the alert",
     "        except SystemExit:  # noqa: BLE001 — mutated: catches nothing the alert raises",
     "test_a_raising_short_sections_alert_does_not_cost_the_outcome_json"),

    # #225. The last raise still standing between the send loop and the
    # response: `failures` carries whatever the blob held, and the JSON encoder
    # cannot take `bytes`.
    ("subscribe: a non-string address reaches the JSON encoder raw",
     "src/astro_ai/routes/subscribe.py",
     "        \"failed_emails\": [str(e) for e in failures[:20]],",
     "        \"failed_emails\": failures[:20],",
     "test_a_bytes_email_does_not_cost_the_outcome_json"),

    # #228. `DailyPanchang.daylight_ordinary` (#227) only helps a surface that
    # READS it, and five did not. Each row below restores one of them to the
    # shipped behaviour: rendering an eighth or a fifteenth of a daylight span
    # the date does not have. Two shapes, both real — Tromso 2026-05-17 came
    # out reversed ("Rahu Kaal 00:14-00:06"), and Reykjavik 2026-06-24, south
    # of the Arctic Circle, came out looking entirely ordinary ("13:30-16:08",
    # an eighth of a 21-hour day ending on the next date). The tests use the
    # second, because nothing about it raises, degrades or logs.
    ("strip: Rahu Kaal item renders without checking the flag (#228)",
     "src/astro_ai/templates/_panchang_strip.html",
     # ANCHORED ON THE PRECEDING COMMENT, not on the markup after the `if`.
     # There are TWO `{%- if panchang_strip.daylight_ordinary %}` blocks in
     # this file (Rahu Kaal and Abhijit) and their opening divs are identical,
     # so the original anchor could only tell them apart by the colour utility
     # on the label. #242 recoloured that (text-red-700 -> a palette token) and
     # the harness reported ANCHOR MISSED — silent coverage loss, not a
     # failure, which is the shape of defect this whole file exists to prevent.
     # The comment above the Rahu Kaal block is unique and carries no styling.
     "push the row into overflow at 320px. -#}\n      {%- if panchang_strip.daylight_ordinary %}",
     "push the row into overflow at 320px. -#}\n      {%- if True %}",
     "test_surface_hides_daylight_windows_when_there_is_no_daylight[homepage strip]"),

    # #270: the rashifal day-windows block went to the model half-English, and
    # the Hindi reading echoed the English fragments into Devanagari prose.
    ("#270: the band is looked up in English again (Hindi block leaks)",
     "src/astro_ai/chart.py",
     "band=translate(lang, band_key),", "band=translate(\"en\", band_key),",
     "test_hindi_block_carries_no_english_once_the_two_names_are_removed"),

    ("#270: the English band text drifts from the pre-localisation literal",
     "src/astro_ai/i18n.py",
     '"rahu_band_6": "mid-afternoon"', '"rahu_band_6": "mid afternoon"',
     "test_english_block_is_byte_identical_to_the_pre_localisation_literals"),

    ("#270: the Hindi anti-copy sentence is dropped from the directive",
     "src/astro_ai/i18n.py",
     "अन्य निर्देशों में दिए गए अंग्रेज़ी उदाहरण-वाक्यांशों को कभी न दोहराएँ",
     "अन्य निर्देशों को कभी न दोहराएँ",
     "test_hindi_block_still_gives_the_exact_names_and_forbids_clock_times"),

    ("/today: the two window cards render without checking the flag (#228)",
     "src/astro_ai/templates/today.html",
     "      {%- if panchang.daylight_ordinary %}\n\n      <!-- Rahu Kaal",
     "      {%- if True %}\n\n      <!-- Rahu Kaal",
     "test_surface_hides_daylight_windows_when_there_is_no_daylight[/today panchang grid]"),

    # The email rows are the ones that matter most: the blast computes panchang
    # per subscriber city, so these arrive in an inbox with no page to refresh
    # and no caveat anywhere near them.
    ("daily rashifal email: window rows render without checking the flag (#228)",
     "src/astro_ai/templates/email/daily_rashifal.html",
     "                    {%- if panchang.daylight_ordinary %}",
     "                    {%- if True %}",
     "test_surface_hides_daylight_windows_when_there_is_no_daylight[daily rashifal email]"),

    ("welcome email: window rows render without checking the flag (#228)",
     "src/astro_ai/templates/email/welcome.html",
     "                    {%- if panchang.daylight_ordinary %}",
     "                    {%- if True %}",
     "test_surface_hides_daylight_windows_when_there_is_no_daylight[welcome email]"),

    ("muhurat: candidate windows computed without checking the flag (#228)",
     "src/astro_ai/muhurat.py",
     "            if p.daylight_ordinary:\n                rk_str =",
     "            if True:\n                rk_str =",
     "test_muhurat_candidate_fields_are_empty_not_reversed"),

    # Not a leak — muhurat.py has already emptied the fields by then — but the
    # row renders the bare label "Abhijit" with nothing after it, which reads
    # as a rendering bug and tells the reader nothing. Silence is its own wrong
    # answer here, so it has its own row.
    ("muhurat finder: empty windows render as a bare label, unexplained (#228)",
     "src/astro_ai/templates/muhurat_finder.html",
     "            {% if c.abhijit_muhurta or c.rahu_kaal %}",
     "            {% if True %}",
     "test_surface_says_why_the_windows_are_missing[muhurat finder]"),

    # --- the natal 413 (/kundli down, "Limit 8000, Requested 8562") ---
    #
    # Two independent defects had to coincide, so each gets its own row. The
    # first three re-break the size guard; the last two re-break the chain's
    # handling of a 413.

    ("natal: the prompt grows back past the TPM ceiling",
     "src/astro_ai/prompts/natal.txt",
     "LANGUAGE & STYLE — write for an Indian reader",
     "PADDING " * 900 + "\nLANGUAGE & STYLE — write for an Indian reader",
     "test_the_whole_request_fits_under_the_tpm_ceiling"),

    ("natal: the size guard is bypassed (no token_budget passed)",
     "src/astro_ai/llm.py",
     "            details, chart, flags, life_chapters, dasha_state, token_budget=budget)},",
     "            details, chart, flags, life_chapters, dasha_state)},",
     "test_generate_reading_actually_applies_the_budget"),

    # The failure this one guards is silent: everything still works, readings
    # just quietly lose their /learn cross-links on every chart that is a few
    # tokens over. Nobody files a bug for that.
    ("natal: shedding drops the whole summaries block instead of one entry",
     "src/astro_ai/llm.py",
     "        block.text = block.shrink() if block.shrink is not None else \"\"",
     "        block.text = \"\"",
     "test_topic_summaries_are_trimmed_entry_by_entry_before_being_dropped"),

    ("natal: a Manglik/yoga verdict block becomes sheddable",
     "src/astro_ai/llm.py",
     "        _OptionalBlock(\"manglik detail\", manglik_block, 0),",
     "        _OptionalBlock(\"manglik detail\", manglik_block, 6),",
     "test_an_impossible_budget_never_sheds_a_verdict_block"),

    # The original bug, exactly: a 413 falls into the generic APIError branch
    # and the chain burns a second identical call on a model with the same cap.
    ("natal: a 413 is treated as transient again",
     "src/astro_ai/providers.py",
     "    if getattr(err, \"status_code\", None) == 413:\n        return True",
     "    if False:\n        return True",
     "test_a_413_is_caught_by_its_status_even_when_the_message_says_nothing"),

    # The inverse, and just as bad: classifying ordinary 429s as unfixable
    # stops the chain falling through and turns a recoverable blip into a
    # dead page.
    ("natal: an ordinary 429 is misread as a size failure",
     "src/astro_ai/providers.py",
     "    return \"request too large\" in text or \"too large for model\" in text",
     "    return \"rate limit\" in text or \"too large for model\" in text",
     "test_a_plain_rate_limit_is_not_mistaken_for_a_size_failure"),

    ("natal: the token estimator under-counts again",
     "src/astro_ai/providers.py",
     "_BYTES_PER_TOKEN_DATA = 3.65",
     "_BYTES_PER_TOKEN_DATA = 4.0",
     "test_the_token_estimator_never_under_counts_a_real_request"),

    # #268: /rashifal/{rashi} derives its reading from the cached combined text.
    ("#268: the route never tries the combined reading (503 with the blob in the bucket)",
     "src/astro_ai/routes/rashifal.py",
     "reading_body = derive_single_reading(idx, lang, today_iso)",
     "reading_body = None",
     "test_cold_page_is_served_from_the_combined_reading_with_no_llm_call"),

    ("#268: sections attributed by POSITION (an extra heading shifts every neighbour)",
     "src/astro_ai/rashifal_derive.py",
     "    return {i: bodies[0] for i, bodies in hits.items() if len(bodies) == 1}",
     "    return {i: b for i, (_t, b) in enumerate(parse_sectioned_reading(text or \"\")) if i < 12}",
     "test_an_extra_heading_in_one_reading_does_not_shift_its_neighbours"),

    ("#268: headings matched by SUBSTRING and first-hit-wins (`min` is inside Gemini)",
     "src/astro_ai/rashifal_derive.py",
     "        matched = [i for i, names in enumerate(_ALLOWED) if segments & names]\n        if len(matched) != 1:",
     "        matched = [i for i, names in enumerate(_ALLOWED)\n                   if any(n in seg for n in names for seg in segments)][-1:]\n        if len(matched) != 1:",
     "test_a_missing_section_is_never_filled_from_a_name_that_merely_contains_it"),

    ("#268: the derived body skips the single route's read gate (regeneration loop)",
     "src/astro_ai/rashifal_derive.py",
     "        ok, reason = llm_providers.passes_quality(body, \"rashifal_single\")",
     "        ok, reason = True, \"\"",
     "test_a_derived_body_the_read_gate_would_reject_is_not_served_and_does_not_loop"),

    ("#268: the bucket is read raw, bypassing the negative-miss cache (a GCS read per request)",
     "src/astro_ai/rashifal_derive.py",
     "            text = _durable_get(combined_keys(lang, today_iso)[1])",
     "            text = __import__(\"astro_ai.storage\", fromlist=[\"get\"]).get(combined_keys(lang, today_iso)[1])",
     "test_a_missing_blob_costs_one_bucket_read_per_negative_cache_window"),

    ("#268: a bucket hit is not written back to tier 0 (a GCS read per rashi)",
     "src/astro_ai/rashifal_derive.py",
     "            daily_cache.put(\"rashifal\", lang,\n                            {\"text\": text, \"lang\": lang, \"date_iso\": today_iso}, today_iso)",
     "            pass",
     "test_the_blob_is_fetched_once_for_all_twelve_rashis"),

    ("#268: a corrupt blob is promoted into the cache the 07:00 blast reads",
     "src/astro_ai/rashifal_derive.py",
     "            ok, reason = llm_providers.passes_quality(text, \"rashifal\")",
     "            ok, reason = True, \"\"",
     "test_a_corrupt_blob_is_not_promoted_into_the_cache_the_blast_reads"),

    ("#268: warm_rashifal writes the blob under a different key than derive reads",
     "src/astro_ai/routes/subscribe.py",
     "            storage_key=storage_key,\n            call_fn=lambda: generate_rashifal(",
     "            storage_key=f\"rashifal/{today_iso}-{lang}.txt\",\n            call_fn=lambda: generate_rashifal(",
     "test_a_reading_warmed_by_the_job_serves_a_cold_instance"),

    ("#268: warm reports ok on 12 sections although fewer pages are derivable",
     "src/astro_ai/routes/subscribe.py",
     "\"ok\": len(sections) == 12 and single_pages == 12,",
     "\"ok\": len(sections) == 12,",
     "test_warm_reports_how_many_pages_it_can_serve"),

    ("#268: warm does not alert when pages are not derivable",
     "src/astro_ai/routes/subscribe.py",
     "    if single_pages < 12:",
     "    if False:",
     "test_warm_reports_how_many_pages_it_can_serve"),

    ("#268: derive runs AFTER the cooldown (a gate-failed rashi cannot heal from the blob)",
     "src/astro_ai/routes/rashifal.py",
     "    if reading_body is None:\n        reading_body = derive_single_reading(idx, lang, today_iso)",
     "    if reading_body is None and not _regen_blocked(cache_key):\n        reading_body = derive_single_reading(idx, lang, today_iso)",
     "test_a_cooldown_does_not_hide_a_servable_blob"),

    ("#268: the Devanagari aries name is not recognised (every Hindi page falls to live generation)",
     "src/astro_ai/rashifal_derive.py",
     "    (\"मेष\",),",
     "    (\"मेष_\",),",
     "test_hindi_page_is_derived_from_devanagari_headings"),

    # #268 QA round: five re-breaks that left the first 13 tests green.
    ("#268: tier 0 is read with lang hard-coded to en (English reading on a Hindi page)",
     "src/astro_ai/rashifal_derive.py",
     "        hit = daily_cache.get(\"rashifal\", lang, today_iso)",
     "        hit = daily_cache.get(\"rashifal\", \"en\", today_iso)",
     "test_a_hindi_page_never_reads_the_english_tier_zero_file"),

    ("#268: a section naming two rashis is attributed to the first (multi-match guard gone)",
     "src/astro_ai/rashifal_derive.py",
     "        if len(matched) != 1:",
     "        if not matched:",
     "test_a_section_naming_two_rashis_is_attributed_to_neither"),

    ("#268: two sections for one rashi - the first wins (duplicate guard gone)",
     "src/astro_ai/rashifal_derive.py",
     "    return {i: bodies[0] for i, bodies in hits.items() if len(bodies) == 1}",
     "    return {i: bodies[0] for i, bodies in hits.items() if bodies}",
     "test_two_sections_for_one_rashi_are_attributed_to_neither"),

    ("#268: a derived reading is served but never stored in rashifal_single",
     "src/astro_ai/routes/rashifal.py",
     "derived from the combined reading\", cache_key)\n            daily_cache.put(\"rashifal_single\", cache_key, {",
     "derived from the combined reading\", cache_key)\n            _unused = (\"rashifal_single\", cache_key, {",
     "test_a_derived_reading_is_stored_so_the_next_request_reads_nothing"),

    ("#268: one Devanagari rashi name is misspelt (that rashi never derives in Hindi)",
     "src/astro_ai/rashifal_derive.py",
     "    (\"सिंह\",),",
     "    (\"सिंह_\",),",
     "test_every_devanagari_rashi_name_maps_to_its_own_index"),

    # #316: the loop-outcome report. Each re-breaks a rule whose absence let a
    # loop fail invisibly; the report that cannot go red is the defect it replaces.
    ("#316: a merge leg that fails every run is no longer BROKEN (the 422 leg hides behind its twin)",
     "scripts/report_loop_outcomes.py",
     "        if rs and ok == 0:",
     "        if False:",
     "test_defect1_a_merge_leg_that_always_fails_is_broken_even_though_merges_happen"),

    ("#316: a success that committed no report reads as idle, not broken",
     "scripts/report_loop_outcomes.py",
     "    if failed or nothing:",
     "    if failed:",
     "test_success_with_no_report_commit_is_broken_not_idle"),

    ("#316: a 403 in the measurement fetch is read as a received measurement",
     "scripts/report_loop_outcomes.py",
     "        return DENIED",
     "        return RECEIVED",
     "test_defect3_a_403_in_a_continue_on_error_step_is_not_a_green_run"),

    ("#316: an unreadable loop exits 0 (UNKNOWN reads as green)",
     "scripts/report_loop_outcomes.py",
     "    if any(f.verdict == UNKNOWN for f in findings):\n        return 2",
     "    if any(f.verdict == UNKNOWN for f in findings):\n        return 0",
     "test_unreadable_evidence_is_unknown_exits_two_and_is_never_green"),

    ("#316: an issue a human closed counts as closed by the loop (declined path)",
     "scripts/report_loop_outcomes.py",
     "                if closer == BOT:\n                    continue",
     "                if closer:\n                    continue",
     "test_defect4_close_on_evidence_that_closed_nothing_is_broken_and_prints_the_refs_line"),

    ("#316: an issue a human closed counts as closed by the loop (claimed path)",
     "scripts/report_loop_outcomes.py",
     "            elif closer == BOT:",
     "            elif closer:",
     "test_a_closing_keyword_closed_by_a_human_is_still_a_shortfall"),

    ("#316: a run still in flight is counted as a failed leg run",
     "scripts/report_loop_outcomes.py",
     "    real = [r for r in _done(runs) if r.get(\"conclusion\") != \"skipped\"]",
     "    real = [r for r in runs if r.get(\"conclusion\") != \"skipped\"]",
     "test_in_flight_work_is_excluded_not_broken"),

    ("#316: the measurement receipt reads the echoed script source, not the step's output",
     "scripts/report_loop_outcomes.py",
     "    lines = step_output(log, MEASURE_ANCHOR)\n    if not lines:\n        return UNKNOWN\n    text = \"\\n\".join(lines)",
     "    text = log",
     "test_measurement_receipt_reads_output_not_the_echoed_script"),

    ("#316: Refs no longer suppresses the branch-name fallback (a deliberate decline reads as a miss)",
     "scripts/report_loop_outcomes.py",
     "    return {\"expected\": sorted(closing | (branch - refs)),",
     "    return {\"expected\": sorted(closing | branch),",
     "test_refs_decline_on_a_still_open_issue_is_not_a_shortfall"),

    ("#316: the workflow loses pull-requests: read (the report would say UNKNOWN, forever)",
     ".github/workflows/loop-outcomes.yml",
     "      pull-requests: read    # agent PRs, their labels and merged_by\n",
     "",
     "test_workflow_grants_every_scope_the_scripts_endpoints_need"),

    ("#316: a PR merged before the window is judged (false BROKEN on a PR merely touched this week)",
     "scripts/report_loop_outcomes.py",
     '        return self.since <= ts(t) and self.settled(t)',
     '        return self.settled(t)',
     "test_a_pr_merged_before_the_window_and_merely_touched_inside_it_is_not_judged"),

    ("#316: the post-merge verification counts a PR merged before the window",
     "scripts/report_loop_outcomes.py",
     '    total = len([p for p in by_bot if p.get("merged_at") and window.merged_in(p["merged_at"])])',
     '    total = len([p for p in by_bot if p.get("merged_at") and window.settled(p["merged_at"])])',
     "test_a_pr_merged_before_the_window_and_merely_touched_inside_it_is_not_judged"),

    ("#316: an agent-work run that concluded failure is skipped instead of reported",
     "scripts/report_loop_outcomes.py",
     '            bad.append(f"run {r[\'id\']} concluded {r.get(\'conclusion\')}")\n            continue',
     '            continue',
     "test_a_work_run_that_concludes_failure_is_broken"),

    ("#316: a report loop's failed run is dropped (every run failed, nothing reported)",
     "scripts/report_loop_outcomes.py",
     '            failed.append(f"run {r[\'id\']} concluded {r.get(\'conclusion\')}")',
     '            pass',
     "test_a_report_loop_whose_every_run_failed_is_broken"),

    ("#316: a schedule that stopped firing reads as OK",
     "scripts/report_loop_outcomes.py",
     '    if len(runs) < need:',
     '    if False:',
     "test_a_schedule_that_does_not_fire_is_broken"),

    ("#316: a PR whose checks cannot be read is no longer UNKNOWN",
     "scripts/report_loop_outcomes.py",
     '    if uncertain:\n        return Finding(loop, UNKNOWN',
     '    if False:\n        return Finding(loop, UNKNOWN',
     "test_a_qa_pass_pr_whose_checks_cannot_be_read_is_unknown_not_stranded_or_fine"),

    ("#316: a PR whose checks are still running is called stranded",
     "scripts/report_loop_outcomes.py",
     '        return "its checks are still running", "pending"',
     '        return "its checks are still running", "definite"',
     "test_a_qa_pass_pr_whose_checks_are_still_running_is_in_flight_not_stranded"),

    ("#316: the in-flight grace boundary is exclusive (a run exactly GRACE old is not judged)",
     "scripts/report_loop_outcomes.py",
     '        return ts(t) <= self.until - GRACE',
     '        return ts(t) < self.until - GRACE',
     "test_the_grace_boundary_is_inclusive_one_second_either_side"),
    # #305: the /kundli identity tiles ellipsis-clipped 10 of 12 rashi names at 375px.
    ("#305: `truncate` back on the snapshot tile value line (Lagna clipped to an ellipsis)",
     "src/astro_ai/templates/result.html",
     "leading-tight text-bhagya-cream break-words\">",
     "leading-tight text-bhagya-cream truncate\">",
     "test_no_tile_clips_its_text"),

    ("#305: `truncate` back on the snapshot tile meta line (Uttara Ashadha Nakshatra clipped)",
     "src/astro_ai/templates/result.html",
     "text-bhagya-cream/[.62] mt-1 break-words\">",
     "text-bhagya-cream/[.62] mt-1 truncate\">",
     "test_no_tile_clips_its_text"),

    ("#305: meta words lose nowrap (the Mahadasha dates split at their hyphens)",
     "src/astro_ai/templates/result.html",
     "<span class=\"whitespace-nowrap\">{{ word }}</span>",
     "<span>{{ word }}</span>",
     "test_meta_words_are_nowrap_so_dates_do_not_split_at_hyphens"),

    # --- #338: loop/cost measurements ---
    ("#338: a run that printed 'no commits on' borrows the PR a later run opened",
     "scripts/collect_loop_measurements.py",
     '    (re.compile(r"no commits on (\\S+)"), True),',
     '    (re.compile(r"no commits on (\\S+)"), False),',
     "test_no_commits_run_is_nothing_and_does_not_borrow_a_later_runs_pr"),

    ("#338: a reused branch hands every run its NEWEST pr, not the one at run end",
     "scripts/collect_loop_measurements.py",
     '    seen = [p["number"] for p in prs if ts(p["created_at"]) <= run_end]',
     '    seen = [p["number"] for p in prs]',
     "test_a_reused_branch_gets_the_pr_that_existed_when_the_run_ended"),

    ("#345: dropping measure.if runs the ANALYST twice a day against the 5h cap",
     ".github/workflows/agent-measure.yml",
     "    if: github.event.schedule == '' || github.event.schedule == '0 21 * * *'\n",
     "",
     "test_the_second_slot_runs_the_collectors_without_the_analyst"),

    ("#353: the analyst guard goes back to a deny-list, which fails open on a new slot",
     ".github/workflows/agent-measure.yml",
     "    if: github.event.schedule == '' || github.event.schedule == '0 21 * * *'",
     "    if: github.event.schedule != '0 2 * * *'",
     "test_the_second_slot_runs_the_collectors_without_the_analyst"),

    ("#353: the three-hourly collector slots removed — team health goes back to 12 h stale",
     ".github/workflows/agent-measure.yml",
     '    - cron: "0 5,8,11,14,17,20 * * *"',
     '    - cron: "0 5 * * *"',
     "test_the_second_slot_runs_the_collectors_without_the_analyst"),

    ("#345: the collectors-only slot removed — a cycle's outcome is a day late again",
     ".github/workflows/agent-measure.yml",
     '    - cron: "0 2 * * *"',
     '    - cron: "0 3 * * *"',
     "test_the_second_slot_runs_the_collectors_without_the_analyst"),

    ("#338: a figure may stand on an explanation instead of 'known'/'free-tier' (zero for an unknown)",
     "scripts/collect_loop_measurements.py",
     "        elif status not in FIGURE_STATUSES:",
     "        elif False:",
     "test_a_zero_standing_on_an_explanation_fails"),

    # --- #255: birth details out of the Telegram relay and the events log ---
    #
    # Each row re-breaks one leak or one silent failure that the privacy work
    # closed. The Kaal Sarp row is the instructive one: it never failed loudly,
    # because the call sat in try/except-pass and swallowed the AttributeError.
    ("#255: the seeker's name and place go back into the kundli alert",
     "src/astro_ai/routes/kundli.py",
     "            key=short_key(_id_full), model=_model,",
     "            key=f\"{details.name} {details.birth_place} {short_key(_id_full)}\", model=_model,",
     "test_kundli_relay_is_a_diagnostic_not_an_identity"),

    ("#255: the raw birth place goes back into the form_kundli event",
     "src/astro_ai/routes/kundli.py",
     "                \"identity\": _id_full[:32],",
     "                \"identity\": _id_full[:32], \"birth_place\": details.birth_place,",
     "test_kundli_event_keeps_analytics_and_drops_identity"),

    ("#255: ChartError redaction disabled (a typo'd city reaches Telegram verbatim)",
     "src/astro_ai/routes/llm_support.py",
     "        if isinstance(err, ChartError):",
     "        if False and isinstance(err, ChartError):",
     "test_chart_error_is_relayed_without_its_message_or_traceback"),

    ("#255: Kaal Sarp alert reads the nonexistent `is_present` again (never fired)",
     "src/astro_ai/routes/dosha.py",
     "            is_present=kaal_sarp.is_kaal_sarp,",
     "            is_present=kaal_sarp.is_present,",
     "test_dosha_relay_carries_no_birth_detail"),

    ("#255: identity_key becomes an unkeyed hash (a lookup table from the plaintext)",
     "src/astro_ai/identity.py",
     "    return hmac.new(_subkey(), joined.encode(\"utf-8\"), hashlib.sha256).hexdigest()",
     "    return hashlib.sha256(joined.encode(\"utf-8\")).hexdigest()",
     "test_identity_key_is_not_an_unkeyed_hash"),

    ("#255: session cookie loses Secure on Cloud Run",
     "src/astro_ai/session.py",
     "        secure=bool(os.environ.get(\"K_REVISION\")),",
     "        secure=False,",
     "test_session_cookie_is_secure_on_cloud_run"),

    ("#255: audience_summary ignores the coarse age_band on new events",
     "src/astro_ai/profiling.py",
     "        _bump(age_hist, str(d.get(\"age_band\") or \"\")\n              or _age_bucket_from_dob(str(d.get(\"birth_date\", \"\"))))",
     "        _bump(age_hist, _age_bucket_from_dob(str(d.get(\"birth_date\", \"\"))))",
     "test_audience_summary_reads_new_shape_events"),

    ("#255: audience_summary drops the legacy raw-field fallback (30 days of events vanish)",
     "src/astro_ai/profiling.py",
     "        _bump(age_hist, str(d.get(\"age_band\") or \"\")\n              or _age_bucket_from_dob(str(d.get(\"birth_date\", \"\"))))",
     "        _bump(age_hist, str(d.get(\"age_band\") or \"\"))",
     "test_audience_summary_still_reads_legacy_raw_events"),

    ("#255: city goes back to storing the first comma token of a street address",
     "src/astro_ai/profiling.py",
     "    if len(tokens) > 3 or not tokens[0]:\n        return \"\"",
     "    if not tokens[0]:\n        return \"\"",
     "test_city_drops_street_addresses_instead_of_storing_a_fragment"),

    ("#255: city stops recognising address words (flat / road / villa fragments stored)",
     "src/astro_ai/profiling.py",
     "        if _ADDRESS_WORDS.intersection(re.findall(r\"[^\\W\\d_]+\", tok)):\n            return \"\"",
     "        if False:\n            return \"\"",
     "test_city_drops_street_addresses_instead_of_storing_a_fragment"),

    ("#255: city stops dropping c/o and email-shaped places",
     "src/astro_ai/profiling.py",
     "        if \"c/o\" in tok or \"@\" in tok:\n            return \"\"",
     "        if False:\n            return \"\"",
     "test_city_drops_street_addresses_instead_of_storing_a_fragment"),

    ("#255: city stops recognising Devanagari address words (Hindi addresses stored)",
     "src/astro_ai/profiling.py",
     "        if any(w in tok for w in _ADDRESS_SUBSTRINGS_DEVANAGARI):\n            return \"\"",
     "        if False:\n            return \"\"",
     "test_city_drops_street_addresses_instead_of_storing_a_fragment"),

    ("#255: /privacy points at a 'Delete my data' option that does not exist again",
     "src/astro_ai/templates/privacy.html",
     "<strong>Delete your data.</strong>",
     "<strong>Delete my data</strong>",
     "test_privacy_page_does_not_point_at_a_delete_option_that_does_not_exist"),

    ("#255: /admin/activity loses its legacy-row branch (old events render blank)",
     "src/astro_ai/templates/admin_activity.html",
     "{% if e.data.identity %}",
     "{% if True %}",
     "test_admin_activity_renders_both_event_shapes"),

    ("#255: /admin dashboard loses its legacy-row branch (old events render 'None')",
     "src/astro_ai/templates/admin_dashboard.html",
     "{% if e.data.get('identity') %}",
     "{% if True %}",
     "test_admin_dashboard_renders_both_event_shapes"),

    ("#354: trust boundary matches exact paths only (a nested prompt would merge)",
     ".github/workflows/agent-merge.yml",
     '"$entry"*) printf',
     '"$entry") printf',
     "test_protected_path_is_held"),

    ("#354: the merge step ignores the trust boundary (reads steps.size again)",
     ".github/workflows/agent-merge.yml",
     "      - name: Merge\n        if: steps.boundary.outputs.ok == 'true'",
     "      - name: Merge\n        if: steps.size.outputs.ok == 'true'",
     "test_every_step_after_the_boundary_waits_on_it"),

    ("#358: the pull_request_target leg stops checking the head repository",
     ".github/workflows/agent-merge.yml",
     "        && github.event.pull_request.head.repo.full_name == github.repository\n",
     "",
     "test_both_trigger_legs_require_the_head_to_be_this_repository"),

    ("#358: the agent-branch filter interpolates the branch name again",
     ".github/workflows/agent-merge.yml",
     'case "$PR_BRANCH" in',
     'case "${{ steps.pr.outputs.branch }}" in',
     "test_the_agent_branch_filter_reads_an_env_var_not_an_interpolation"),

    # The failure mode of the env: refactor itself: an undeclared name expands
    # to the empty string, so the post-merge issue comment goes to `gh issue
    # comment ""` AFTER the merge has happened. Nothing errors.
    ("#358: the merge step expands $PR_BRANCH without declaring it",
     ".github/workflows/agent-merge.yml",
     "          PR_BRANCH: ${{ steps.pr.outputs.branch }}\n"
     "          PR_NUMBER: ${{ steps.pr.outputs.number }}\n"
     "          PR_SHA: ${{ steps.pr.outputs.sha }}\n"
     "        run: |\n"
     '          gh pr merge "$PR_NUMBER"',
     "          PR_NUMBER: ${{ steps.pr.outputs.number }}\n"
     "          PR_SHA: ${{ steps.pr.outputs.sha }}\n"
     "        run: |\n"
     '          gh pr merge "$PR_NUMBER"',
     "test_every_managed_variable_a_step_expands_is_declared"),

    ("#357: the sweep stops requiring qa-pass",
     ".github/workflows/agent-merge.yml",
     'select([.labels[].name] | index("qa-pass"))',
     "select(true)",
     "test_a_pr_without_qa_pass_is_not_a_candidate"),

    ("#357: the sweep stops checking the head repository",
     ".github/workflows/agent-merge.yml",
     'select(.head.repo.full_name == "\'"$GH_REPO"\'")',
     "select(true)",
     "test_a_fork_head_is_never_a_candidate"),

    ("#374: the sweep stops checking whether its candidate can merge",
     ".github/workflows/agent-merge.yml",
     'if [ "$m" = "MERGEABLE" ]; then',
     'if true; then',
     "test_a_conflicting_candidate_is_skipped_for_the_next_one"),

    # UNKNOWN is what GitHub answers while it computes mergeability. Accepting
    # it makes the failure intermittent, which is worse than reliable.
    ("#374: the sweep accepts UNKNOWN as good enough",
     ".github/workflows/agent-merge.yml",
     'if [ "$m" = "MERGEABLE" ]; then',
     'if [ "$m" != "CONFLICTING" ]; then',
     "test_unknown_is_not_treated_as_mergeable"),

    # The defect this set was written after: providers.py also returns a BARE
    # `429` when the error text names neither window, and the first version of
    # the constant listed only 413/429_tpm/429_tpd -- so a real rate limit
    # counted as "not the budget" and the red metric under-reported.
    ("#355: a bare 429 stops counting as a token-budget failure",
     "src/astro_ai/ops_data.py",
     'BUDGET_FAIL_REASONS = ("413", "429", "429_tpm", "429_tpd")',
     'BUDGET_FAIL_REASONS = ("413", "429_tpm", "429_tpd")',
     "test_every_reason_providers_can_emit_is_classified"),

    ("#355: tokens per request goes back to counting input only",
     "src/astro_ai/ops_data.py",
     "per_total = ((in_tok + out_tok) / m) if m else None",
     "per_total = (in_tok / m) if m else None",
     "test_per_request_total_is_input_plus_output_over_misses"),

    ("#355: the daily figure becomes the last day instead of the worst",
     "src/astro_ai/llm_stats.py",
     "if day_tok > peak_tok:",
     "if day_tok >= 0:",
     "test_peak_day_reports_the_worst_day_and_names_it"),

    ("#355: an unrecorded peak reads as a quiet day rather than as no data",
     "src/astro_ai/llm_stats.py",
     '"peak_day_tokens": peak_tok or None,',
     '"peak_day_tokens": peak_tok,',
     "test_peak_day_is_none_when_nothing_was_recorded"),

    # RequestTooLarge SUBCLASSES AllProvidersExhausted, but `error_type` stores
    # the concrete class name, so dropping it misses every 413.
    ("#355: a 413 stops counting as a feature broken by the budget",
     "src/astro_ai/ops_data.py",
     'BUDGET_ERROR_TYPES = ("AllProvidersExhausted", "RequestTooLarge")',
     'BUDGET_ERROR_TYPES = ("AllProvidersExhausted",)',
     "test_request_too_large_is_a_break_although_it_subclasses_exhausted"),

    # The defect as it shipped: an anonymous visitor's 2,000 characters
    # interpolated raw into an HTML email sent from the site's own authenticated
    # sender domain.
    ("#373: the feedback email stops escaping the visitor's message",
     "src/astro_ai/routes/feedback.py",
     'msg = _html.escape(entry["message"] or "")',
     'msg = entry["message"] or ""',
     "test_a_script_payload_in_the_message_does_not_survive_as_markup"),

    ("#355: an unrecorded route latency reads as 0 (a zero reads as 'fast')",
     "src/astro_ai/llm_stats.py",
     'int(v["lat_sum"] / v["lat_n"]) if v["lat_n"] else None',
     'int(v["lat_sum"] / v["lat_n"]) if v["lat_n"] else 0',
     "test_a_day_file_from_before_the_change_is_unknown_not_fast"),

    ("#355: per-route latency averaged over calls-hits (old days dilute it)",
     "src/astro_ai/llm_stats.py",
     'acc["lat_n"] += r.get("miss_latency_n", 0)',
     'acc["lat_n"] += r.get("calls", 0) - r.get("hits", 0)',
     "test_a_day_file_from_before_the_change_is_unknown_not_fast"),

    ("#355: a 413 filed under 429_tpm (structural failure read as a rate limit)",
     "src/astro_ai/providers.py",
     '    if _is_request_too_large(err):\n        return "413"\n',
     '    if False:\n        return "413"\n',
     "test_failure_reason_classification"),

    ("#355: chat() drops the fallback reason on the way to llm_stats",
     "src/astro_ai/providers.py",
     "                        fallback_reason=last_reason,\n",
     '                        fallback_reason="",\n',
     "test_a_tpm_429_then_success_is_recorded_with_its_reason_and_provider"),

    ("#355: fallbacks counted but reasons not (the sum invariant)",
     "src/astro_ai/llm_stats.py",
     "            reasons[rkey] = reasons.get(rkey, 0) + 1\n",
     "            pass\n",
     "test_reasons_sum_to_fallbacks_across_mixed_failures"),

    ("#355: /admin/ops labels a configured bucket as local (or vice versa)",
     "src/astro_ai/storage.py",
     '        return f"gcs:{name}"',
     '        return f"local:{name}"',
     "test_describe_store_names_the_bucket_or_the_local_dir"),

    ("#355: /admin/ops never shows the 'local dev store' badge (store_is_local forced False)",
     "src/astro_ai/ops_data.py",
     '"store": store, "store_is_local": store.startswith("local:"),\n            "store_detail": store_detail,\n            "days": days,',
     '"store": store, "store_is_local": False,\n            "store_detail": store_detail,\n            "days": days,',
     "test_ops_says_it_is_reading_a_local_dev_store"),

    # #367. The triage script writes under the owner's identity on text strangers wrote; each
    # row re-breaks one clause of the chief's ruling. The close row is the one the ruling asked
    # for by name: a `gh issue close` call injected must turn the suite red.
    ("#367: a `gh issue close` call appears in the triage script",
     "scripts/triage_outsider_issues.py",
     '    n, problems = str(int(issue["number"])), []\n',
     '    n, problems = str(int(issue["number"])), []\n    gh(["issue", "close", n, "--repo", repo])\n',
     "test_no_close_path_exists_in_the_script"),

    ("#367: an UNRESOLVED resolver is treated as an outsider (fail open)",
     "scripts/triage_outsider_issues.py",
     '        return "error", f"resolver reported UNRESOLVED: {detail}".rstrip(": ")',
     '        return "outsider", ""',
     "test_any_other_resolver_code_fails_closed_with_a_named_cause"),

    # #377 DEF-1. The resolver's exit code and its printed verdict must be read TOGETHER: a
    # crash exits 1, which is OUTSIDER's own code, so status alone cannot tell a finding from
    # a traceback. This row restores the defect exactly -- believe the status, ignore the word.
    ("#377: provenance is read from the exit code alone, so a crash is an OUTSIDER finding",
     "scripts/triage_outsider_issues.py",
     "    said = verdict_printed(r.out, number)",
     "    said = _EXIT_VERDICT.get(r.rc)",
     "test_a_crashing_resolver_is_not_an_outsider"),

    # #377 DEF-2. The cap must bound the WORK. Capping only the printout left the surplus
    # labelled, and `already_done` reads that label, so the next run skipped the held-back
    # issues before they could be listed -- discarded, not deferred.
    #
    # TWO ROWS, because `... and False` is NOT the defect. It removes deferral AND the
    # printout cap, so it fails loudly on several assertions at once and proves less than it
    # appears to. QA round 2 made the point: the EXACT restoration keeps the cap branch and
    # its printed strings byte-identical and merely applies the decision before deferring --
    # the surplus is labelled and then held back, which is precisely how the bug was silent.
    # Keep both: the blunt one guards the branch existing, the exact one guards the ordering.
    ("#377: --cap bounds the printout but not the work, so held-back candidates are labelled",
     "scripts/triage_outsider_issues.py",
     "        if d.label == LABEL_REVIEWED and len(stage2) >= args.cap:",
     "        if d.label == LABEL_REVIEWED and False:",
     "test_the_cap_bounds_the_stage2_list"),

    ("#377: the deferred candidate is LABELLED before it is deferred (the exact DEF-2 defect)",
     "scripts/triage_outsider_issues.py",
     "        if d.label == LABEL_REVIEWED and len(stage2) >= args.cap:\n"
     "            deferred.append(n)",
     "        if d.label == LABEL_REVIEWED and len(stage2) >= args.cap:\n"
     "            if args.apply:\n"
     "                failures.extend(apply_decision(gh, args.repo, issue, d))\n"
     "            deferred.append(n)",
     "test_held_back_candidates_are_listed_by_the_next_run"),

    ("#367: the duplicate comment echoes the stranger's title",
     "scripts/triage_outsider_issues.py",
     'f"This looks similar to #{int(dup[0])}, which is older and still open. "',
     'f"This looks similar to #{int(dup[0])} ({issue.get(\'title\')}), which is older and still open. "',
     "test_the_duplicate_comment_links_the_candidate_and_nothing_else"),

    ("#367: the idempotence marker is ignored (a comment on every run)",
     "scripts/triage_outsider_issues.py",
     "    if d.comment is not None and not has_marker(issue, d.key):",
     "    if d.comment is not None:",
     "test_a_state_already_commented_by_this_token_posts_nothing_again"),


    # --- #361: issue provenance. The resolver is the control that keeps an outsider's
    # issue from reaching an engineer; each row makes it say TRUSTED when it must not.
    ("#361: permission 'none' resolves as trusted (every stranger is a maintainer)",
     "scripts/resolve_provenance.py",
     'PERM_TRUSTED = {"admin", "write"}',
     'PERM_TRUSTED = {"admin", "write", "none"}',
     "test_read_and_none_are_outsiders"),

    ("#361: a bot-applied provenance:trusted is honoured (the loop vouches for itself)",
     "scripts/resolve_provenance.py",
     '    if actor.get("type") != "User":',
     "    if False:",
     "test_a_bot_applied_override_is_ignored"),

    ("#361: a bot author is treated as trusted (no allowlist, and no default either)",
     "scripts/resolve_provenance.py",
     "    if is_bot:\n        base = OUTSIDER",
     "    if is_bot:\n        base = TRUSTED",
     "test_a_bot_author_is_an_outsider_whatever_its_permission"),

    ("#361: a 403 / 5xx collapses into 'outsider' instead of stopping (could-not-ask != no)",
     "scripts/resolve_provenance.py",
     'return Perm("unresolved", detail=f"gh exit {r.rc}: {r.err.strip()[:120]}")',
     'return Perm("absent", detail=f"gh exit {r.rc}: {r.err.strip()[:120]}")',
     "test_a_failure_to_ask_is_unresolved_never_a_default"),

    ("#361: the login regex is skipped (an attacker-shaped login reaches the API call)",
     "scripts/resolve_provenance.py",
     "    return login if _LOGIN.fullmatch(login) else None",
     "    return login",
     "test_an_invalid_login_is_unresolved_and_reaches_no_api_call"),

    ("#361: the login check backs off to match() -- a trailing newline survives `$`",
     "scripts/resolve_provenance.py",
     "    return login if _LOGIN.fullmatch(login) else None",
     "    return login if _LOGIN.match(login) else None",
     "test_a_trailing_newline_or_control_character_is_not_a_login"),

    ("#361: override events sorted by timestamp alone (a same-second unlabel loses to a label)",
     "scripts/resolve_provenance.py",
     '    relevant.sort(key=lambda e: (str(e.get("created_at", "")), e.get("id") or 0))',
     '    relevant.sort(key=lambda e: str(e.get("created_at", "")))',
     "test_a_same_second_label_and_unlabel_are_ordered_by_id"),

    ("#361: any comment carrying the marker silences the UNRESOLVED stop (spoofable)",
     "scripts/resolve_provenance.py",
     ' and c.get("viewerDidAuthor") is True',
     "",
     "test_a_copied_marker_in_someone_elses_comment_does_not_suppress_the_stop"),

    ("#396: a provider that omits prompt_tokens_details is recorded as a measured 0 (absent -> zero)",
     "src/astro_ai/providers.py",
     'cached = getattr(details, "cached_tokens", None)',
     'cached = getattr(details, "cached_tokens", 0)',
     "test_a_provider_that_does_not_report_is_absent_never_zero"),

    ("#396: chat() stops resetting the prefix figure before each call (provider A's cached count leaks to B)",
     "src/astro_ai/providers.py",
     "                _last_prefix.set(None)\n",
     "",
     "test_chat_resets_the_figure_before_each_call_so_a_stub_cannot_inherit_it"),

    # --- #396 follow-up: classifying a SILENCE. Groq sends no cache figure at
    # all on a miss, so "absent" means either "this model cannot report" or
    # "this model reported nothing". Only the first is unmeasurable. Each row
    # below collapses that distinction in one direction or the other -- the
    # first four inflate the saving, the fifth invents one.
    ("#396: a junk cache figure discards the prompt size too (a miss becomes unclassifiable)",
     "src/astro_ai/providers.py",
     "        return prompt, None\n", "        return None\n",
     "test_prefix_usage_accepts_only_real_ints"),

    ("#396: the model allowlist is ignored, so a non-caching model's silence scores 0%",
     "src/astro_ai/llm_stats.py",
     "                model in CACHE_REPORTING_MODELS and prompt_tokens >= MIN_CACHEABLE_PREFIX)",
     "                True)",
     "test_a_miss_on_a_non_reporting_model_is_not_scored_as_zero"),

    ("#396: the minimum-prefix threshold is ignored (an ineligible prompt scores 0%)",
     "src/astro_ai/llm_stats.py",
     "prompt_tokens >= MIN_CACHEABLE_PREFIX)", "True)",
     "test_a_prompt_under_the_minimum_cacheable_length_is_not_measurable"),

    ("#396: a call that REPORTED is no longer forced measurable (effective rate can exceed 100%)",
     "src/astro_ai/llm_stats.py",
     "            measurable = cached_tokens is not None or (",
     "            measurable = (",
     "test_a_reported_call_under_the_minimum_still_counts_so_the_rate_cannot_exceed_100"),

    ("#396: effective_pct divides by reported tokens, collapsing it into hit_pct (the original defect)",
     "src/astro_ai/llm_stats.py",
     'v["cached_tokens"] / v["prompt_measurable"] * 100',
     'v["cached_tokens"] / v["prompt_reported"] * 100',
     "test_the_two_rates_diverge_and_effective_is_the_honest_one"),
    # --- #400: the per-route token budget gate. A size gate that cannot go red is
    # the honour system it replaced; each row neuters one comparison it makes.
    ("#400: the ceiling comparison is neutered (an oversized prompt passes)",
     "scripts/verify_token_budget.py",
     "        if worst > ceiling:", "        if False and worst > ceiling:",
     "test_a_route_over_its_ceiling_fails_naming_the_route_the_ceiling_and_the_value"),

    ("#400: the growth comparison is neutered (#212 again: each step under the ceiling)",
     "scripts/verify_token_budget.py",
     "        if en > limit:", "        if False and en > limit:",
     "test_growth_under_the_ceiling_still_fails"),

    ("#400: the ceiling ignores the Hindi variant (+132 tok on every route unseen)",
     "scripts/verify_token_budget.py",
     "        worst = max(en, hi)", "        worst = en",
     "test_the_hindi_variant_is_judged_against_the_ceiling"),

    ("#400: a row whose route was never measured stops failing",
     "scripts/verify_token_budget.py",
     "        if route not in measured:", "        if False:",
     "test_a_row_for_a_route_that_was_not_measured_fails"),

    ("#400: a twelfth prompt file is no longer noticed (ships unbudgeted)",
     "scripts/verify_token_budget.py",
     "        extra = uncovered_prompts(declared, prompts_dir)", "        extra = []",
     "test_a_twelfth_prompt_file_with_no_budget_fails"),

    ("#400: an empty override is accepted (a pass that measured nothing)",
     "scripts/verify_token_budget.py",
     "if not path.is_file() or path.stat().st_size == 0:", "if False:",
     "test_an_override_that_is_empty_is_refused_not_skipped_past"),

    ("#400: could-not-run exits 0 (an unmeasured gate reads as green)",
     "scripts/verify_token_budget.py",
     "This is NOT a pass — the check did not run.\")\n        return 2",
     "This is NOT a pass — the check did not run.\")\n        return 0",
     "test_an_unavailable_tokenizer_is_exit_two_and_says_it_is_not_a_pass"),

    ("#400: the natal row drops the chart payload (#266 was the SUM)",
     "scripts/verify_token_budget.py",
     'measured["natal+payload"] = (n_en + user, n_hi + user)',
     'measured["natal+payload"] = (n_en, n_hi)',
     "test_the_natal_row_includes_the_chart_payload_not_only_the_system_prompt"),
]

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _die_cleanly(signum, _frame):
    """Turn SIGTERM/SIGHUP into SystemExit so TemporaryDirectory unwinds.

    `src/` is safe either way — the sandbox means the repo is never mutated —
    but a killed run left a ~7.6 MB copy of src+tests in $TMPDIR each time.
    Harmless and untidy; one line to stop.
    """
    raise SystemExit(f"terminated by signal {signum}")


for _sig in (signal.SIGTERM, signal.SIGHUP):
    signal.signal(_sig, _die_cleanly)

# A mutation that changes NOTHING. It must report MISSED on every run.
#
# Without it this harness could not fail, and did not, for a whole commit:
# `deps.py` calls `load_dotenv(override=True)`, which resolves `.env` by
# walking up from the importing file. In a sandbox that is a tmpdir, so the
# repo's `.env` was never found, no LLM provider registered, and five rashifal
# tests failed BEFORE any mutation was applied. Every mutation then reported
# CAUGHT — including a no-op — and "8/8 caught" measured nothing at all.
#
# Two fixes, and this row is the important one. Injecting the env stops the
# sandbox being red; the control row proves it, every run, forever. A harness
# whose whole purpose is "prove the gate can fail" must itself be provably
# able to fail.
_CONTROL = (
    "CONTROL: a no-op edit — MUST report MISSED, or this harness is blind",
    "src/astro_ai/routes/deps.py",
    "def panchang_strip_for_city(city: str) -> tuple:",
    "def panchang_strip_for_city(city: str) -> tuple:  # noqa: E501",
    "_control",
)


def _sandbox_env() -> dict:
    """Parent env plus the repo's .env, which the sandbox cannot discover."""
    env = dict(os.environ)
    dotenv = ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip("\"'"))
    return env


def _run_in_sandbox(rel: str, old: str, new: str, test: str = "") -> tuple[bool, str]:
    """Apply one mutation to a COPY of the tree and run the suite there.

    The repository is never modified. An earlier version mutated `src/` in
    place and restored in a `finally`, which covers Ctrl-C and subprocess death
    but NOT a signal that does not raise: `kill -TERM` left the live-comprehension
    defect — the one that 500s `/` and `/rashifal` — sitting on disk inside a
    twenty-line comment block, where a casual `git diff` review skims past it.

    A sandbox removes the failure mode rather than handling it. There is no
    restore path to get wrong, and no signal that can beat it.
    """
    with tempfile.TemporaryDirectory(prefix="mutate-") as tmp:
        sandbox = pathlib.Path(tmp) / "repo"
        # `.github` because the suite now reads the verify-production workflow
        # to check that its jq field reads still match what /health emits.
        #
        # `scripts` for TWO independent reasons, arrived at separately — which is
        # itself the evidence that the omission was a trap and not an oversight:
        #   * #316: tests/test_loop_outcomes.py loads report_loop_outcomes.py by
        #     path, and the mutations above edit that file in the sandbox.
        #   * #325: tests/test_stall_ownership.py imports detect_stalls.py to pin
        #     how a stall is assigned an owner.
        #
        # A sandbox missing a file the suite reads breaks EVERY row at once, and
        # it has now done so twice. The first time every mutation read CAUGHT,
        # because the suite READ a missing file. The second time every row read
        # `NON-TEST FAILURE rc=2`, because it IMPORTED one and pytest died at
        # collection. Same cause, opposite signal, both invisible in a pass count.
        #
        # Both times the CONTROL is what exposed it: a no-op edit that does not
        # report MISSED means the harness is not measuring anything. Read that row
        # before any other.
        #
        # So the rule, stated because the next addition will hit it too: ANY
        # directory the suite reads or imports from must be copied here.
        #
        # `measurements` since #338: test_committed_measurement_files_pass_their_
        # validators reads loop.json and cost.json, and without them every row
        # would fail at that one test and read as CAUGHT.
        for sub in ("src", "tests", ".github", "scripts", "measurements"):
            shutil.copytree(ROOT / sub, sandbox / sub,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # GUARD GONE — "the defect escaped" and "the test meant to catch it no
        # longer exists" both used to print as MISSED, and the difference is
        # enormous: one is a weak test, the other is no test at all.
        #
        # A slice-based edit silently deleted six tests, two of them the named
        # guards for mutations registered here. This harness printed 35/38 and
        # exited 1 — correctly red, but mute about the cause, so both times it
        # took a manual hunt to discover the tests were simply gone.
        # (QA round 5 specified this check.)
        if test and test != "_control":
            suite_src = "\n".join(
                f.read_text() for f in (sandbox / "tests").rglob("test_*.py")
            )
            # Strip a parametrize id: entries are registered as
            # `test_foo[homepage strip]`, and the def is just `test_foo`.
            base = test.split("[", 1)[0]
            if f"def {base}(" not in suite_src:
                return False, f"GUARD GONE — no test named {base}"

        target = sandbox / rel
        source = target.read_text()
        if source.count(old) != 1:
            return False, f"ANCHOR MISSED ({source.count(old)})"
        target.write_text(source.replace(old, new))
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(sandbox / "tests"), "-q", "--no-header"],
            capture_output=True, text=True, cwd=sandbox, env=_sandbox_env(),
        )
        if result.returncode == 0:
            return False, "*** MISSED ***"
        # A non-zero exit from a collection error would look like a catch and
        # be worth nothing, so require an actual assertion failure.
        if "FAILED" not in result.stdout and "failed" not in result.stdout:
            return False, f"NON-TEST FAILURE rc={result.returncode}"
        return True, "CAUGHT"


# Run the mutations concurrently. Each one already builds its own temporary
# sandbox and shells out to its own pytest, so they share nothing and the work
# is embarrassingly parallel — serially it was 281s, 61% of every pr-gates run,
# against a GitHub Actions free-tier allowance this repo is already outgrowing.
#
# Threads rather than processes: the time is spent inside subprocess.run waiting
# on pytest, which releases the GIL, and threads need nothing pickled.
#
# The worker count is capped. Each sandbox runs a full pytest, so N workers mean
# N interpreters compiling and importing at once; past the core count they
# contend and the wall time stops improving. `cpu_count or 1` because it returns
# None on some platforms.
_WORKERS = min(int(os.environ.get("MUTATE_WORKERS", "4")), (os.cpu_count() or 1))

_work = [_CONTROL] + list(MUTATIONS)
_verdicts: dict[int, tuple[str, str]] = {}

with concurrent.futures.ThreadPoolExecutor(max_workers=_WORKERS) as _pool:
    _futures = {
        _pool.submit(_run_in_sandbox, rel, old, new, test): (i, label, test)
        for i, (label, rel, old, new, test) in enumerate(_work)
    }
    for _f in concurrent.futures.as_completed(_futures):
        i, label, test = _futures[_f]
        try:
            _ok, verdict = _f.result()
        except Exception as exc:  # noqa: BLE001
            # A worker that raised is NOT a caught mutation. Saying so keeps a
            # crashed sandbox from counting as coverage — the same reason the
            # control row exists.
            verdict = f"HARNESS ERROR ({type(exc).__name__}: {exc})"
        _verdicts[i] = (label, verdict)

# Results come back out of order; report in table order so runs stay diffable.
rows = []
control_ok = True
for i, (label, _rel, _old, _new, _test) in enumerate(_work):
    _, verdict = _verdicts[i]
    if _test == "_control":
        # Inverted: for the control, MISSED is the pass.
        control_ok = verdict == "*** MISSED ***"
        rows.append((label, "OK (correctly missed)" if control_ok else f"BLIND ({verdict})"))
        continue
    rows.append((label, verdict))

print(f"{'mutation':<58} {'verdict'}")
print("-" * 76)
bad = 0
for label, verdict in rows:
    if verdict != "CAUGHT":
        bad += 1
    print(f"  {label:<56} {verdict}")
print()
# The control row never has the verdict "CAUGHT" — whether it passes
# ("OK (correctly missed)") or fails ("BLIND (...)") — so it always adds
# exactly 1 to `bad`. Subtract it once, unconditionally.
real = len(rows) - 1
caught = real - (bad - 1)
print(f"{caught}/{real} mutations caught")
print("repository untouched: mutations run in a temporary copy")
if not control_ok:
    print()
    print("CONTROL FAILED — the sandbox reports CAUGHT for an edit that changes")
    print("nothing, so every verdict above is worthless. Fix the sandbox before")
    print("believing any number this printed.")
sys.exit(0 if control_ok and caught == real else 1)
