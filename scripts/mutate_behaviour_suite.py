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
import threading
import contextlib
import os
import pathlib
import re
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
     "test_english_block_tells_the_model_the_windows_are_background_only"),

    ("#270: the Hindi anti-copy sentence is dropped from the directive",
     "src/astro_ai/i18n.py",
     "अन्य निर्देशों के अंग्रेज़ी उदाहरण-वाक्यांश कभी न दोहराएँ",
     "अन्य निर्देश कभी न दोहराएँ",
     "test_hindi_block_forbids_naming_the_windows_and_any_clock_time"),

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
    # #495: loop-outcomes false positives -- partial/ and fix/ PRs, and GitHub's own
    # keyword auto-close on a human merge.
    ('#495: the agent-PR namespaces shrink back to issue/ (every partial/ and fix/ PR is invisible again)',
     "scripts/report_loop_outcomes.py",
     'AGENT_BRANCH_NAMESPACES = ("issue/", "partial/", "fix/")',
     'AGENT_BRANCH_NAMESPACES = ("issue/",)',
     'test_agent_prs_spans_issue_partial_and_fix_and_nothing_else'),

    ('#495: agent-work is not told about a merged partial/ PR (it reports a run that produced one as empty)',
     "scripts/report_loop_outcomes.py",
     'AGENT_BRANCH_NAMESPACES = ("issue/", "partial/", "fix/")',
     'AGENT_BRANCH_NAMESPACES = ("issue/", "fix/")',
     'test_check_work_counts_a_merged_partial_pr_as_what_the_run_produced'),

    ('#495: the pr-gates filter in check_merge reverts to issue/ (a partial/ gate run owes agent-merge nothing)',
     "scripts/report_loop_outcomes.py",
     'g["head_branch"].startswith(AGENT_BRANCH_NAMESPACES)]',
     'g["head_branch"].startswith("issue/")]',
     'test_check_merge_expects_agent_merge_to_answer_a_partial_prs_gate_run'),

    ('#495: claimed_issues widens its branch fallback to partial/ (the report demands a close the convention prevents)',
     "scripts/report_loop_outcomes.py",
     '    m = re.match(r"issue/(\\d+)", pr["head"]["ref"])',
     '    m = re.match(r"(?:issue|partial|fix)/(\\d+)", pr["head"]["ref"])',
     'test_claimed_issues_branch_namespaces_and_the_keyword_subset'),

    ("#495: a human close long after the merge counts as GitHub's keyword auto-close (no upper bound)",
     "scripts/report_loop_outcomes.py",
     '    return timedelta(0) <= ts(closed["created_at"]) - ts(pr["merged_at"]) <= KEYWORD_CLOSE_WINDOW',
     '    return timedelta(0) <= ts(closed["created_at"]) - ts(pr["merged_at"])',
     'test_the_keyword_auto_close_window_is_sixty_seconds_inclusive'),

    ("#495: a close BEFORE the merge counts as GitHub's keyword auto-close (no lower bound)",
     "scripts/report_loop_outcomes.py",
     '    return timedelta(0) <= ts(closed["created_at"]) - ts(pr["merged_at"]) <= KEYWORD_CLOSE_WINDOW',
     '    return ts(closed["created_at"]) - ts(pr["merged_at"]) <= KEYWORD_CLOSE_WINDOW',
     'test_the_keyword_auto_close_window_is_sixty_seconds_inclusive'),

    ('#495: a close by someone other than the merger counts as the keyword auto-close',
     "scripts/report_loop_outcomes.py",
     '    if actor == BOT or actor != (pr.get("merged_by") or {}).get("login"):',
     '    if actor == BOT:',
     'test_a_close_by_someone_other_than_the_merger_is_still_a_miss'),

    ('#495: a branch-name claim (no keyword) is excused as a keyword auto-close',
     "scripts/report_loop_outcomes.py",
     '    if closed is None or n not in claim["keyword"] or not pr.get("merged_at"):',
     '    if closed is None or n not in claim["expected"] or not pr.get("merged_at"):',
     'test_a_branch_name_claim_closed_by_the_merger_is_still_a_miss'),

    ('#495: an issue still open after a human merge is excused (no closed event required)',
     "scripts/report_loop_outcomes.py",
     '    if closed is None or n not in claim["keyword"] or not pr.get("merged_at"):',
     '    if n not in claim["keyword"] or not pr.get("merged_at"):',
     'test_a_keyword_issue_still_open_after_a_human_merge_is_still_a_miss'),

    ("#495: the loop's own close is reclassified as GitHub's keyword close (the BOT exclusion gone)",
     "scripts/report_loop_outcomes.py",
     '    if actor == BOT or actor != (pr.get("merged_by") or {}).get("login"):',
     '    if actor != (pr.get("merged_by") or {}).get("login"):',
     'test_a_bot_merger_does_not_make_a_bot_close_an_auto_close'),

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

    # Was anchored on `case "$PR_BRANCH" in` when eligibility was a branch-name
    # test. That moved to the AUTHOR on 2026-10-25, and the author is
    # attacker-chosen in exactly the same sense -- a fork PR carries whatever
    # login opened it -- so the #358 invariant now lives here.
    ("#358: the eligibility filter interpolates a PR value again",
     ".github/workflows/agent-merge.yml",
     '*",$PR_AUTHOR,"*)',
     '*",${{ steps.pr.outputs.author }},"*)',
     "test_the_eligibility_filter_reads_env_vars_not_interpolations"),

    # A NEW silent failure mode, introduced by that same move. `claude[bot]`
    # contains `[` and `]`, and the author is expanded into a `case` PATTERN --
    # the one position in shell where a variable's contents become matching
    # syntax. Only the quoting makes it literal; both forms parse. Unquoted it
    # fails CLOSED (the list matches nothing, so the loop merges nothing), which
    # is the benign direction and therefore the one nobody notices: #469 was the
    # last autonomous merge and four days passed before it was looked into.
    ("the author match reads [bot] as a glob class (loop silently merges nothing)",
     ".github/workflows/agent-merge.yml",
     '*",$PR_AUTHOR,"*)',
     '*,$PR_AUTHOR,*)',
     "test_the_eligibility_gate_executes_correctly_for_every_author"),

    # Every routed action in steward.md is "dispatch a cycle at the owning
    # issue", so a null here is a stall the steward can SEE and cannot ACT on.
    # Measured 2026-10-25: #521 and #524 sat `no-qa-verdict` 21h with green
    # gates, three steward runs cleared neither, and `steward-ineffective`
    # escalated both -- because their branches were `partial/` and the regex
    # was `^issue/`.
    # ---- #536 round 2: the independent round's findings, pinned -----------
    #
    # BUG-2. The guard used to test `exp_full`, the OUTPUT of the arithmetic, so
    # a clamped `pre` went unnoticed and the over-add of `rate x duration` was
    # booked as agreement. Because `pred` is 98-101% of `limit` for natal
    # (7,871 en / 8,056 hi against 8,000, measured 2026-10-25), `exp_full > 0`
    # REQUIRED a near-full bucket -- so the samples that survived were exactly
    # the invalid ones, and which ones survived depended on the answer.
    ("the clamp guard reads its own output again (samples chosen by the answer)",
     "src/astro_ai/ratelimit_probe.py",
     # Disables the ceiling test so the sample falls through and is BOOKED,
     # which is the old defect. Swapping the condition for `exp_full > limit`
     # is NOT the old behaviour -- the branch would still set `skip_full` -- and
     # an earlier draft of this row made exactly that mistake and reported
     # MIS-POINTED.
     "if raw_pre > limit or raw_mid > limit:",
     "if raw_pre > limit * 100:",
     "test_a_sample_whose_bucket_was_at_the_ceiling_is_never_counted_clean"),

    # BUG-3. ARCHITECTURE points at this panel twice to settle whether the
    # header is TPM. The value was computed at ops_data.py:1163 and dropped, so
    # the stated route to answering that question led to a page without it.
    ("the header-reported limit is computed and never rendered",
     "src/astro_ai/templates/admin_ops.html",
     ' · header-reported limit {{ "{:,}".format(r.last_limit) }}',
     "",
     "test_the_header_reported_limit_reaches_the_page"),

    # BUG-4. `groq` and `groq120` are one Groq bucket and two probe sequences,
    # so a sibling's charge is invisible and lowers Groq's figure below the
    # prediction -- pushing toward a FALSE FULL WEIGHT, the one verdict that
    # would justify leaving settle() alone for good.
    ("the probe scores a model two live chain entries share",
     "src/astro_ai/providers.py",
     "and not _model_is_shared(provider) else None)",
     "else None)",
     # Names the CALL-SITE test, not the helper test: deleting the guard from
     # `chat()` leaves `_model_is_shared` itself correct, so a row aimed at the
     # helper reports MIS-POINTED. An earlier draft did exactly that.
     "test_chat_books_no_sample_at_all_when_the_model_is_shared"),

    # ---- #536 round 3: D1/D2/D3, each pinned by the test that was missing ---
    #
    # D3(a). POPULATED has skip_full=0, so replacing the read with a literal 0
    # changed nothing on any page -- on the counter the operator is told to watch.
    ("the ceiling-skip count is never read from the probe (always 0 on the page)",
     "src/astro_ai/ops_data.py",
     '"full": n(probe, "skip_full")},',
     '"full": 0},',
     "test_a_nonzero_ceiling_count_reaches_the_page"),

    # D3(b). `raw_pre <= limit < raw_mid` is the completion-model clamp that
    # produced the original wrong samples; nothing covered it. (Dropping
    # `raw_pre > limit` ALONE is an equivalent mutant -- raw_mid >= raw_pre -- and
    # is deliberately not a row.)
    ("a bucket that would cross the ceiling DURING the call is booked as a clean sample",
     "src/astro_ai/ratelimit_probe.py",
     "if raw_pre > limit or raw_mid > limit:",
     "if raw_pre > limit:",
     "test_a_bucket_that_would_cross_the_ceiling_during_the_call_is_skipped_not_booked"),

    # D3(d). A header of 0 remaining is a floor, not a measurement.
    ("a zero-remaining header is booked as a sample (the empty-end clamp is gone)",
     "src/astro_ai/ratelimit_probe.py",
     "if exp_full <= 0 or remaining == 0:",
     "if exp_full <= 0:",
     "test_a_header_of_zero_remaining_is_a_clamp_skip_not_a_sample"),

    # D3(c). Only the ceiling half of the sentence was asserted.
    ("the fold's zero-remaining clause is reworded away",
     "src/astro_ai/templates/admin_ops.html",
     "reported zero remaining)",
     "reported an empty bucket)",
     "test_the_fold_says_what_the_empty_end_clamp_is"),

    # D1. The fix commit spliced its sentence into the middle of an older one.
    ("the fold's closing sentence is spliced into an older one again",
     "src/astro_ai/templates/admin_ops.html",
     "causes it is. A skipped call is never counted as agreement.",
     "causes it is. The arithmetic does not hold) &mdash; and is never counted as agreement.",
     "test_the_fold_skip_passage_reads_exactly_as_written_and_is_not_spliced"),

    # D2. `skip_full` with `warm_n` 0 is also what sparse traffic on a light
    # request produces, so "cannot be measured at all" over-claims.
    ("the fold says a ceiling skip means the path cannot be measured at all",
     "src/astro_ai/templates/admin_ops.html",
     "is therefore getting no usable samples,",
     "is therefore not under-deployed &mdash; it cannot be measured by this instrument at all,",
     "test_the_fold_does_not_say_a_ceiling_means_the_path_cannot_be_measured"),

    ("the stall detector cannot name a partial branch's issue (steward is mute)",
     "scripts/detect_stalls.py",
     'r"^(?:issue|partial|fix)/(\\d+)"',
     'r"^issue/(\\d+)"',
     "test_the_owning_issue_resolves_for_every_cycle_namespace"),

    # The opposite error, which is the obvious widening: ~8 measurement
    # branches a day, and `measurements/40140256532-1` would route a dispatch
    # at issue 40140256532.
    ("the stall detector reads a measurement run-id as an issue number",
     "scripts/detect_stalls.py",
     'r"^(?:issue|partial|fix)/(\\d+)"',
     'r"^[a-z]+/(\\d+)"',
     "test_a_measurement_branch_never_yields_an_issue"),

    # ---- qa-on-green: the dispatcher that fires on EVERY green ------------
    #
    # Unique among the dispatchers in that its trigger is frequent, so its
    # failure modes are not "inert" but "spends the Actions budget". The loop
    # guard is the one that bites: a cycle that runs a round, pushes a fix and
    # ends with no verdict leaves exactly the state this workflow fires on.
    ("qa-on-green dispatches at its own output forever (the loop guard loses the head)",
     ".github/workflows/qa-on-green.yml",
     "qa-on-green: dispatched at $head",
     "qa-on-green: dispatched at",
     "test_the_dispatch_is_remembered_against_the_head_commit"),

    # The `[bot]` glob trap, a third time in this repo. Unquoted, `claude[bot]`
    # is a character class matching only `b`, `o` or `t`, so the gate matches
    # nothing and the whole workflow is silently inert.
    ("qa-on-green reads [bot] as a glob class (the dispatcher never fires)",
     ".github/workflows/qa-on-green.yml",
     '*",$author,"*)',
     '*,$author,*)',
     "test_an_agent_author_is_accepted"),

    # ~8 measurement branches a day; `measurements/40140256532-1` would aim a
    # ~50-minute cycle at issue 40140256532.
    ("qa-on-green reads a measurement run-id as an issue number",
     ".github/workflows/qa-on-green.yml",
     "s#^(issue|partial|fix)/([0-9]+).*#",
     "s#^[a-z]+/([0-9]+).*#",
     "test_a_branch_with_no_owning_issue_yields_nothing"),

    # A push during the gate run moves the head, and a round aimed at a stale
    # green verifies code the gates never saw.
    ("qa-on-green acts on a green that belongs to an older commit",
     ".github/workflows/qa-on-green.yml",
     '[ "$head" != "$HEAD_SHA" ]',
     '[ "$head" = "" ]',
     "test_it_refuses_to_act_on_a_stale_green"),

    # A `qa-fail` PR needs a FIX, and which fix is a judgment `steward.md`'s
    # routing table holds across three kinds with different actions. Sending a
    # round at unaddressed findings returns the same FAIL at full cost.
    ("qa-on-green sends a round at a PR whose findings are unaddressed",
     ".github/workflows/qa-on-green.yml",
     '*",qa-fail,"*)',
     '*",qa-fail-never,"*)',
     "test_it_declines_a_pr_that_is_already_routed"),

    # #531 fixed the branch-name coupling in three places and the loop STILL
    # could not dispatch, because two more copies of the rule live as PROSE in
    # the steward's and chief's prompts: "an `issue/*` branch with an owning
    # issue, never a PR a human opened on their own branch". Both clauses were
    # false by then -- `agent-cycle` Step 2.5 adopts a branch whoever opened the
    # PR, and the repository owner opens PRs on cycle branches routinely (#521,
    # #524 were both `mahAnuj` on `partial/`). Nothing type-checks prose, so
    # these rows are the only thing that can notice it coming back.
    ("the steward's dispatch rule demands an `issue/*` branch again",
     ".claude/agents/steward.md",
     "one the detector printed an owning issue for",
     "an `issue/*` branch with an owning issue",
     "test_the_dispatch_rule_never_requires_an_issue_slash_branch"),

    ("the steward stands down on a PR the owner opened (the 21h stall)",
     ".claude/agents/steward.md",
     "- A PR the detector could not name an owning issue for",
     "- A PR a human opened is not this loop's.\n#",
     "test_the_dispatch_rule_never_refuses_a_pr_for_who_opened_it"),

    # chief's copy of the same rule. It is the LAST gate: `steward-ineffective`
    # routes every long-lived stall here, so a wrong refusal in this prompt
    # cannot be worked around by any other path.
    ("chief refuses a dispatch by who authored the PR rather than by trust",
     ".github/workflows/agent-steward.yml",
     "authored by neither `claude[bot]` nor the repository owner",
     "that a human authored",
     "test_chief_keeps_the_two_refusals_that_are_real"),

    # A dispatch the cycle cannot act on is worse than none: Step 2.5 reports
    # "no branch", opens a parallel one, and the stalled PR is never touched --
    # ~50 Actions minutes against a free-tier budget to clear nothing.
    ("a cycle cannot find the fix/ branch the steward dispatched about",
     ".claude/commands/agent-cycle.md",
     '"fix/<n>-*"   # a branch from an earlier cycle?',
     '# a branch from an earlier cycle?',
     "test_a_cycle_looks_for_every_namespace_the_steward_may_dispatch_at"),

    # The safety net in agent-work gated on `issue/*` until 2026-10-25, so a
    # cycle ending on a `partial/` branch was told "Cycle shipped nothing" and
    # exited 0 WITHOUT PUSHING -- discarding real commits inside a runner about
    # to be destroyed, which is the exact loss the step exists to prevent.
    # agent-cycle.md:363 had recorded it as a known gap. This is its first guard.
    ("the push net refuses a partial branch again (work lost with the runner)",
     ".github/workflows/agent-work.yml",
     "            main|HEAD)",
     "            main|HEAD|partial/*|fix/*)",
     "test_the_push_net_rescues_every_branch_a_cycle_may_end_on"),

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

    # The anchor gained its `and denom` in #473: a route with no sized call
    # must render a dash, not a confident 0.0. The mutation is unchanged in
    # spirit -- drop the output half and the figure stops being what both of
    # Groq's limits count.
    ("#355: tokens per request goes back to counting input only",
     "src/astro_ai/ops_data.py",
     "per_total = ((in_tok + out_tok) / m) if (m and denom) else None",
     "per_total = (in_tok / m) if (m and denom) else None",
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

    # The defect as it shipped: the blockquote carried no white-space rule, so
    # every "\n" collapsed to a space in the owner's mail client.
    ("#388: the feedback email blockquote loses white-space:pre-wrap",
     "src/astro_ai/routes/feedback.py",
     "background:#FAF6EF;white-space:pre-wrap;'>{msg}",
     "background:#FAF6EF;'>{msg}",
     "test_a_multi_line_message_keeps_its_line_breaks_in_the_owners_mail"),

    # The defect as it shipped: `import logging` inside the email `except`
    # block. A local import anywhere in a function makes the name local for the
    # WHOLE function, whatever the module binds -- so the Telegram handler
    # above it raised UnboundLocalError and a saved submission returned 500.
    ("#408: `import logging` back inside the email except (Telegram handler 500s)",
     "src/astro_ai/routes/feedback.py",
     '    except Exception as err:\n        logging.getLogger(__name__).warning("admin feedback',
     '    except Exception as err:\n        import logging\n        logging.getLogger(__name__).warning("admin feedback',
     "test_a_telegram_failure_does_not_500_a_saved_submission"),

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
     "    if not isinstance(cached, int) or isinstance(cached, bool) or cached < 0:\n"
     "        # Present but not a count (a string, a float, a bool) or negative. The\n"
     "        # provider DID say something and it is unusable, so this is a rejection\n"
     "        # and must not read as a measured zero either.\n"
     "        return prompt, None, True\n",
     "    if not isinstance(cached, int) or isinstance(cached, bool) or cached < 0:\n"
     "        return None\n",
     "test_prefix_usage_accepts_only_real_ints"),

    ("#396: the model allowlist is ignored, so a non-caching model's silence scores 0%",
     "src/astro_ai/llm_stats.py",
     "            measurable = (model in CACHE_REPORTING_MODELS",
     "            measurable = (True",
     "test_a_miss_on_a_non_reporting_model_is_not_scored_as_zero"),

    ("#396: the minimum-prefix threshold is ignored (an ineligible prompt scores 0%)",
     "src/astro_ai/llm_stats.py",
     "prompt_tokens >= MIN_CACHEABLE_PREFIX)", "True)",
     "test_a_prompt_under_the_minimum_cacheable_length_is_not_measurable"),

    # Superseded: there is no longer a `cached is not None or ...` disjunct to
    # remove -- separate numerators made it unnecessary. The equivalent defect in
    # the new design is restoring the outcome-dependence it replaced.
    ("#396: measurability reads the OUTCOME again (a hit counts, a miss of the same size does not)",
     "src/astro_ai/llm_stats.py",
     "            measurable = (model in CACHE_REPORTING_MODELS\n",
     "            measurable = (cached_tokens is not None or model in CACHE_REPORTING_MODELS\n",
     "test_measurability_never_depends_on_the_outcome_at_any_size"),

    ("#396: effective_pct borrows the shared numerator (a sub-floor hit inflates it)",
     "src/astro_ai/llm_stats.py",
     '_rate(v["cached_measurable"], v["prompt_measurable"],',
     '_rate(v["cached_tokens"], v["prompt_measurable"],',
     "test_a_sub_floor_report_does_not_inflate_the_effective_numerator"),

    # --- #410 QA round 3. Each row restores a defect round 3 measured.
    ("#410: a cached count larger than its own prompt is accepted again (5000% stored)",
     "src/astro_ai/providers.py",
     "    if cached > prompt:", "    if False:",
     "test_a_cached_count_larger_than_its_prompt_is_refused_at_the_source"),

    ("#410: the impossible flag leaves the route cell, invisible when Effective is a dash",
     "src/astro_ai/templates/admin_dashboard.html",
     "{{ route }}{% if pc.impossible %}", "{{ route }}{% if False %}",
     "test_the_anomaly_flag_is_visible_when_only_the_reported_side_is_broken"),

    ("#410: the table pairs the measurable denominator with the reported numerator again",
     "src/astro_ai/templates/admin_dashboard.html",
     "{{ pc.prompt_measurable }} / {{ pc.cached_measurable }}",
     "{{ pc.prompt_measurable }} / {{ pc.cached_tokens }}",
     "test_the_two_column_pairs_each_divide_to_their_own_rate"),

    ("#410: the unmeasurable-report notice drops the benign cause and the warning",
     "src/astro_ai/templates/admin_dashboard.html",
     "Most likely a non-Groq provider reporting\n", "Most likely nothing\n",
     "test_the_unmeasurable_report_notice_names_the_benign_cause_and_forbids_the_harmful_fix"),

    ("#410: a malformed stat_key is dropped silently again (a whole window can vanish)",
     "src/astro_ai/llm_stats.py",
     "                                compound_key, len(parts))\n                skipped_rows += 1",
     "                                compound_key, len(parts))",
     "test_a_malformed_stat_key_is_counted_and_logged_not_dropped_silently"),

    ("#410: the skip notice moves back inside the table's own if (total loss is silent)",
     "src/astro_ai/templates/admin_dashboard.html",
     "{% if llm_stats.aggregate.prefix_cache_skipped_rows and not llm_stats.aggregate.prefix_cache %}",
     "{% if False %}",
     "test_the_skip_notice_survives_when_every_row_is_skipped"),

    ("#410: the By-route table's headers are overwritten with the prefix-cache ones",
     "src/astro_ai/templates/admin_dashboard.html",
     '            <th class="text-right py-2">Response-cache hits</th>',
     '            <th class="text-right py-2">Measurable</th>',
     "test_the_by_route_table_still_has_its_own_headers"),

    ("#396: effective_pct divides by reported tokens, collapsing it into hit_pct (the original defect)",
     "src/astro_ai/llm_stats.py",
     '_rate(v["cached_measurable"], v["prompt_measurable"],\n'
     '                                               v["measurable"]),',
     '_rate(v["cached_measurable"], v["prompt_reported"],\n'
     '                                               v["measurable"]),',
     "test_the_two_rates_diverge_and_effective_is_the_honest_one"),

    # --- #410 QA round 1: the follow-up's own defects. Each row restores the
    # behaviour QA measured and the suite must go red.
    ("#410: MIN_CACHEABLE_PREFIX back to 1024 (a hit is measurable, a miss of the same size is not)",
     "src/astro_ai/llm_stats.py",
     "MIN_CACHEABLE_PREFIX = 128", "MIN_CACHEABLE_PREFIX = 1024",
     "test_a_miss_and_a_hit_at_the_same_size_are_both_measurable"),

    ("#410: an older stored schema is summed field-by-field again (mixed window published 571%)",
     "src/astro_ai/llm_stats.py",
     "            if not _PREFIX_ZERO.keys() <= pc.keys():", "            if False:",
     "test_an_old_schema_day_blob_is_skipped_whole_not_summed_field_by_field"),

    ("#410: the rate is no longer clamped (a misreporting provider puts 250% on the dashboard)",
     "src/astro_ai/llm_stats.py",
     "    return round(max(0.0, min(100.0, cached / prompt * 100)), 1)",
     "    return round(cached / prompt * 100, 1)",
     "test_a_rate_is_clamped_and_a_negative_count_is_refused"),

    ("#410: a negative cached count is accepted as a measurement",
     "src/astro_ai/providers.py",
     "or isinstance(cached, bool) or cached < 0:", "or isinstance(cached, bool):",
     "test_a_rate_is_clamped_and_a_negative_count_is_refused"),

    ("#410: the footnote names prompt overlays as if they were chat routes",
     "src/astro_ai/templates/admin_dashboard.html",
     "          A call is Measurable on one of the three cache-reporting models",
     "          <code>ask_matching</code> and <code>ask_numerology</code> are excluded.\n"
     "          A call is Measurable on one of the three cache-reporting models",
     "test_every_route_name_in_the_footnote_is_a_real_chat_route"),
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
    # ---- QA round 4 on #396. BUG-1 and BUG-2 were introduced by round 3 --
    # ---- the round that was fixing things. Each row below was checked to die
    # ---- on its OWN named test, not merely to turn the suite red.

    ("#396 r4: an impossible provider report is booked as a measured zero",
     "src/astro_ai/llm_stats.py",
     "            if reported_impossible:",
     "            if False and reported_impossible:",
     "test_an_impossible_report_is_not_booked_as_a_measured_zero"),

    ("#396 r4: a rejected report collapses back into a silence",
     "src/astro_ai/providers.py",
     "        return prompt, None, True\n    return prompt, cached, False",
     "        return prompt, None, False\n    return prompt, cached, False",
     "test_an_impossible_report_is_not_booked_as_a_measured_zero"),

    ("#396 r4: the measurable-side impossibility clause is deleted",
     "src/astro_ai/llm_stats.py",
     '            or v["cached_measurable"] > v["prompt_measurable"]\n',
     "",
     "test_the_measurable_side_of_the_impossibility_check_is_pinned"),

    ("#396 r4: the impossible-row tooltip stops saying the row is untrustworthy",
     "src/astro_ai/templates/admin_dashboard.html",
     "Every percentage on this row is clamped and untrustworthy.",
     "All good here.",
     "test_the_impossible_tooltip_says_the_row_is_untrustworthy"),

    ("#396 r4: the Effective fraction is guarded on `reported` (hides its own numerator)",
     "src/astro_ai/templates/admin_dashboard.html",
     "{% if pc.measurable %}{{ pc.prompt_measurable }} / {{ pc.cached_measurable }}",
     "{% if pc.reported %}{{ pc.prompt_measurable }} / {{ pc.cached_measurable }}",
     "test_the_effective_fraction_is_guarded_on_measurable_not_reported"),

    ("#396 r4: the By-route gap disclosure is removed from the panel",
     "src/astro_ai/templates/admin_dashboard.html",
     "{% if gap %}<strong>{{ gap.values() | sum }} call(s)",
     "{% if False %}<strong>{{ gap.values() | sum }} call(s)",
     "test_the_gap_against_by_route_is_counted_not_explained_away"),

    ("#396 r4: the By-route gap is never computed",
     "src/astro_ai/llm_stats.py",
     '                if n > prefix_acc.get(route, {}).get("calls", 0)',
     "                if False",
     "test_the_gap_against_by_route_is_counted_not_explained_away"),

    ("#396 r4: MIN_CACHEABLE_PREFIX excludes a prompt exactly at the floor",
     "src/astro_ai/llm_stats.py",
     "and prompt_tokens >= MIN_CACHEABLE_PREFIX",
     "and prompt_tokens > MIN_CACHEABLE_PREFIX",
     "test_a_prompt_exactly_at_the_floor_is_measurable"),

    ("#ops-today: the failure tile is scoped back to agent-work (the 2026-10-18 blindness)",
     "src/astro_ai/ops_today.py",
     '    "agent-measure.yml",\n',
     '',
     "test_every_loop_leg_counts_as_a_failure_not_just_agent_work"),

    ("#ops-today: a red pr-gates run counts as a loop failure (every caught defect reads as an outage)",
     "src/astro_ai/ops_today.py",
     '    "verify-production.yml",\n)',
     '    "verify-production.yml",\n    "pr-gates.yml",\n)',
     "test_a_red_pr_gate_is_not_a_loop_failure"),

    ("#ops-today: a clock-killed run stops counting (cancelled is not failed)",
     "src/astro_ai/ops_today.py",
     'SUCCEEDED_CONCLUSIONS = ("success", "skipped", "neutral")',
     'SUCCEEDED_CONCLUSIONS = ("success", "skipped", "neutral", "cancelled")',
     "test_a_run_killed_by_the_clock_counts_as_failed"),

    ("#ops-today: the runs query is bounded by today's UTC date (drops 00:00-05:30 IST)",
     "src/astro_ai/ops_today.py",
     'day = day_start.strftime("%Y-%m-%d")',
     'day = datetime.now(timezone.utc).strftime("%Y-%m-%d")',
     "test_the_actions_query_is_bounded_by_the_ist_day_start_not_todays_utc_date"),

    ("#ops-today: the workflow match reads the display name, not the path",
     "src/astro_ai/ops_today.py",
     'path = (r.get("path") or "").rsplit("/", 1)[-1]',
     'path = (r.get("name") or "") + ".yml"',
     "test_a_renamed_workflow_display_name_does_not_empty_the_tile"),

    ("#ops-today: live rows are merged with the snapshot instead of replacing it",
     "src/astro_ai/ops_data.py",
     '        "today_failed": (live_today.get("failed", []) if live_today is not None',
     '        "today_failed": (live_today.get("failed", []) + [r for r in today] if live_today is not None',
     "test_live_rows_replace_the_snapshot_rather_than_joining_them"),

    ("#ops-today: the failure alert is gated on loop.json again (the broken part reports itself)",
     "src/astro_ai/ops_data.py",
     '    if loop.get("today_failed"):\n        n = len(loop["today_failed"])',
     '    if loop.get("ok") and loop.get("today_failed"):\n        n = len(loop["today_failed"])',
     "test_the_failure_alert_fires_even_with_no_loop_json"),

    # --- QA round 1 on #418 (2026-10-18). Eleven findings; these are the
    # mutations for the ones that were real. Every behaviour below had NO gate
    # that could fail before this round. -----------------------------------
    ("#ops-today: the live cache is keyed on the clock alone (survives IST midnight)",
     "src/astro_ai/ops_data.py",
     '    if (_today_cache and _today_cache[1] == day\n'
     '            and now - _today_cache[0] < CACHE_TTL):',
     '    if _today_cache and now - _today_cache[0] < CACHE_TTL:',
     "test_the_live_cache_does_not_survive_ist_midnight"),

    ("#ops-today: the live-today catch narrows back to four types (IncompleteRead 500s the page)",
     "src/astro_ai/ops_data.py",
     "    except Exception as exc:  # noqa: BLE001 -- see below",
     "    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:",
     "test_a_failure_outside_the_four_old_exception_types_does_not_500_the_page"),

    ("#ops-today: a failure is not remembered (an outage costs a request per render)",
     "src/astro_ai/ops_data.py",
     '        _today_cache = (now, day, None)\n        return None',
     '        return None',
     "test_a_failing_live_path_is_not_retried_on_every_render"),

    ("#ops-today: shipped is sorted oldest-first",
     "src/astro_ai/ops_today.py",
     '"shipped": sorted(shipped.values(), key=lambda s: s["merged_at"], reverse=True)',
     '"shipped": sorted(shipped.values(), key=lambda s: s["merged_at"])',
     "test_shipped_and_failed_are_newest_first"),

    ("#ops-today: failed is sorted oldest-first",
     "src/astro_ai/ops_today.py",
     '"failed": sorted(failed.values(), key=lambda f: f["started"] or "", reverse=True)',
     '"failed": sorted(failed.values(), key=lambda f: f["started"] or "")',
     "test_shipped_and_failed_are_newest_first"),

    ("#ops-today: the live cache never expires (the tiles freeze for the process)",
     "src/astro_ai/ops_data.py",
     '            and now - _today_cache[0] < CACHE_TTL):',
     '            and True):',
     "test_the_live_cache_expires"),

    ("#ops-today: a truncated page is reported as complete (a silent undercount)",
     "src/astro_ai/ops_today.py",
     '        "truncated": pr_more or runs_more,',
     '        "truncated": False,',
     "test_a_truncated_runs_page_is_admitted_rather_than_undercounted"),

    ("#ops-today: the pager always spends MAX_PAGES (3x the budget on a quiet day)",
     "src/astro_ai/ops_today.py",
     '        if len(batch) < PER_PAGE:\n            return rows, False',
     '        if False:\n            return rows, False',
     "test_an_ordinary_day_still_costs_one_request_per_endpoint"),

    ("#ops-today: the steward drops off the loop (the leg that reports stoppage, invisible)",
     "src/astro_ai/ops_today.py",
     '    "agent-steward.yml",\n',
     '',
     "test_the_steward_counts_as_a_loop_leg"),

    ("#ops-today: the fallback alert renders a literal '?' to the reader",
     "src/astro_ai/ops_data.py",
     '            add("amber", f"{n} agent-work cycle(s) failed today",',
     '            add("amber", f"{n} loop run(s) failed today - ?",',
     "test_the_fallback_alert_does_not_render_a_literal_question_mark"),

    ("#ops-today: snapshot() is awaited inline (up to 12s of event loop, app-wide)",
     "src/astro_ai/routes/admin.py",
     '    ops = await asyncio.to_thread(ops_data.snapshot, app_days=days)',
     '    ops = ops_data.snapshot(app_days=days)',
     "test_the_ops_page_does_not_block_the_event_loop"),

    ("#ops-today: today_live is hardcoded (the drill-down picks the wrong renderer)",
     "src/astro_ai/routes/admin.py",
     '        "today_live": L.get("today_live", False),',
     '        "today_live": False,',
     "test_the_page_tells_the_drill_down_which_shape_the_rows_are"),

    ("#ops-today: a missing snapshot blanks the live tiles too",
     "src/astro_ai/ops_data.py",
     '                "today_failed": (live_today or {}).get("failed", []),',
     '                "today_failed": [],',
     "test_live_tiles_survive_a_missing_snapshot_file"),

    ("#ops-window: the app cache goes back to one slot (window A answers under B's heading)",
     "src/astro_ai/ops_data.py",
     "    hit = _app_cache.get(days)",
     "    hit = next(iter(_app_cache.values()), None)",
     "test_two_windows_do_not_share_one_cache_slot"),

    ("#ops-window: an unoffered window is clamped instead of refused (3650 renders as 30)",
     "src/astro_ai/ops_data.py",
     "    if app_days not in APP_WINDOWS:\n        app_days = DEFAULT_APP_DAYS",
     "    app_days = max(1, min(app_days, max(APP_WINDOWS)))",
     "test_an_unoffered_window_falls_back_rather_than_being_clamped"),

    ("#ops-window: a window above the event-retention ceiling is offered",
     "src/astro_ai/ops_data.py",
     "APP_WINDOWS = (1, 7, 30)",
     "APP_WINDOWS = (1, 7, 30, 90)",
     "test_the_offered_windows_stay_inside_the_retention_ceiling"),

    ("#ops-window: ?window=abc 422s the whole control room",
     "src/astro_ai/routes/admin.py",
     "async def admin_ops(request: Request, window: str = \"\") -> HTMLResponse:",
     "async def admin_ops(request: Request, window: int = 0) -> HTMLResponse:",
     "test_a_mistyped_window_renders_the_default_page_not_an_error"),

    ("#ops-trend: features are ranked per day, so a bar changes colour daily",
     "src/astro_ai/ops_data.py",
     "    ranked = sorted(totals, key=lambda r: -totals[r])",
     "    ranked = sorted(totals)",
     "test_features_are_ranked_over_the_window_not_per_day"),

    ("#ops-trend: the overflow features are dropped instead of grouped",
     "src/astro_ai/ops_data.py",
     '            key = "other" if route in rest else route\n            per[key] = per.get(key, 0) + n',
     '            if route in rest:\n                continue\n            per[route] = per.get(route, 0) + n',
     "test_beyond_the_top_n_features_are_grouped_never_dropped"),

    ("#ops-trend: the chart reads newest-first, so the trend runs backwards",
     "src/astro_ai/ops_data.py",
     '    rows = sorted(rows, key=lambda d: d.get("date") or "")',
     '    rows = sorted(rows, key=lambda d: d.get("date") or "", reverse=True)',
     "test_days_read_left_to_right_oldest_first"),

    ("#ops-trend: an empty window renders a flat zero chart instead of nothing",
     "src/astro_ai/ops_data.py",
     '    if not totals or not any(totals.values()):\n        return {"ok": False, "days": days}',
     '    if False:\n        return {"ok": False, "days": days}',
     "test_a_window_with_no_tokens_is_not_ok_rather_than_a_flat_zero_chart"),

    ("#ops-trend: the axis top ignores the peak, so the tallest bar overflows",
     "src/astro_ai/ops_data.py",
     '"total": day_total, "by_feature": per})\n\n    top = _nice_top(peak)',
     '"total": day_total, "by_feature": per})\n\n    top = _nice_top(peak // 2) if peak else 1',
     "test_no_bar_can_overflow_the_axis"),
    # ---- QA round 1 on #419. Every row below is a defect the reviewer found
    # ---- in this PR's own code, re-broken here so the new tests must stay red
    # ---- against it. The first three were mutants that survived all 705 tests.

    ("#ops-trend: the TPD line is clamped back onto the top edge (BUG-1, 4x overstatement)",
     "src/astro_ai/ops_data.py",
     '        "tpd_visible": top >= TPD_PER_MODEL,\n        "tpd_y": round(100 - TPD_PER_MODEL / top * 100, 2) if top else 100,',
     '        "tpd_visible": top >= TPD_PER_MODEL * 0.25,\n        "tpd_y": round(100 - min(TPD_PER_MODEL / top, 1.0) * 100, 2) if top else 100,',
     "test_the_tpd_line_appears_exactly_when_one_bucket_fits_on_the_chart"),

    ("#ops-trend: the TPD line is placed by its own scale, not the bars'",
     "src/astro_ai/ops_data.py",
     '        "tpd_y": round(100 - TPD_PER_MODEL / top * 100, 2) if top else 100,',
     '        "tpd_y": round(100 - TPD_PER_MODEL / (top * 2) * 100, 2) if top else 100,',
     "test_the_tpd_line_is_drawn_at_the_height_its_label_claims"),

    ("#ops-trend: the ranking counts input only, so the legend orders by half the budget (BUG-3)",
     "src/astro_ai/ops_data.py",
     '            totals[route] = (totals.get(route, 0)\n                             + int(tok.get("input_tokens") or 0)\n                             + int(tok.get("output_tokens") or 0))',
     '            totals[route] = totals.get(route, 0) + int(tok.get("input_tokens") or 0)',
     "test_the_ranking_is_by_total_tokens_not_input"),

    ("#ops-trend: a bar counts input only, so the stack understates the day",
     "src/astro_ai/ops_data.py",
     '            n = int(tok.get("input_tokens") or 0) + int(tok.get("output_tokens") or 0)',
     '            n = int(tok.get("input_tokens") or 0)',
     "test_the_stack_sums_to_the_underlying_blobs"),

    ("#ops-errors: the error read ignores the window (GUARD-1: a 0.29% day rendered 30.85%)",
     "src/astro_ai/ops_data.py",
     "        brk = events.error_breakdown(days=days) or {}",
     "        brk = events.error_breakdown() or {}",
     "test_the_window_is_honoured_so_a_quiet_day_is_not_scored_on_a_bad_month"),
    # ---- QA round 2 on #419. Six of these mutants survived all 745 tests AND
    # ---- the 195-row sweep; the sweep's own rows only mutated what the
    # ---- round-1 fix had moved, so they could not see the sign, the gate
    # ---- value, or any template branch.

    ("#ops-trend: the TPD gate is strict, so the whole (150k, 200k] band loses its line",
     "src/astro_ai/ops_data.py",
     '"tpd_visible": top >= TPD_PER_MODEL,',
     '"tpd_visible": top > TPD_PER_MODEL,',
     "test_the_tpd_line_appears_exactly_when_one_bucket_fits_on_the_chart"),

    ("#ops-trend: the TPD gate slides to half a bucket (line clipped, legend still promises it)",
     "src/astro_ai/ops_data.py",
     '"tpd_visible": top >= TPD_PER_MODEL,',
     '"tpd_visible": top >= TPD_PER_MODEL / 2,',
     "test_the_tpd_line_appears_exactly_when_one_bucket_fits_on_the_chart"),

    ("#ops-trend: tpd_y is measured from the bottom edge (11 buckets reads as none)",
     "src/astro_ai/ops_data.py",
     '"tpd_y": round(100 - TPD_PER_MODEL / top * 100, 2) if top else 100,',
     '"tpd_y": round(TPD_PER_MODEL / top * 100, 2) if top else 100,',
     "test_the_tpd_line_is_measured_from_the_top_of_the_chart_not_the_bottom"),

    ("#ops-errors: the count reverts to the capped sample",
     "src/astro_ai/ops_data.py",
     '"errors": errors_total,',
     '"errors": len(errors),',
     "test_the_count_and_the_rate_are_both_exact"),

    ("#ops-errors: the rate reverts to the capped sample (widening lowers it again)",
     "src/astro_ai/ops_data.py",
     '"error_rate": (round(errors_total / calls * 100, 2) if calls else None),',
     '"error_rate": (round(len(errors) / calls * 100, 2) if calls else None),',
     "test_widening_the_window_cannot_lower_the_rate_on_the_same_data"),

    ("#ops-errors: the rate is withheld on saturation (0.05% on a busy site shows no number)",
     "src/astro_ai/ops_data.py",
     '"error_rate": (round(errors_total / calls * 100, 2) if calls else None),',
     '"error_rate": (None if errors_truncated or not calls else round(errors_total / calls * 100, 2)),',
     "test_volume_alone_does_not_raise_an_alert"),

    ("#ops-errors: `exhausted` reads the wrong key, so provider failures read 0",
     "src/astro_ai/ops_data.py",
     '        exhausted = kinds.get("AllProvidersExhausted", 0)',
     '        exhausted = kinds.get("AllProvidersExhaused", 0)',
     "test_a_provider_failure_behind_many_newer_errors_is_still_counted"),

    ("#ops-errors: `too_large` reads the wrong key, so 413s read 0",
     "src/astro_ai/ops_data.py",
     '        too_large = kinds.get("RequestTooLarge", 0)',
     '        too_large = kinds.get("RequestTooLarg", 0)',
     "test_a_provider_failure_behind_many_newer_errors_is_still_counted"),

    ("#ops-tpl: the TPD line is drawn unguarded (y=-300 for a 50k peak)",
     "src/astro_ai/templates/admin_ops.html",
     '          {%- if ops.app.trend.tpd_visible %}\n          <line x1="0"',
     '          {%- if True %}\n          <line x1="0"',
     "test_the_page_draws_no_tpd_line_when_one_bucket_is_off_the_chart"),

    ("#ops-tpl: the TPD legend is shown unguarded (200,000 claimed on every window)",
     "src/astro_ai/templates/admin_ops.html",
     '          {%- if ops.app.trend.tpd_visible %}\n          <span class="lg"><i class="sw tpdsw"></i>',
     '          {%- if True %}\n          <span class="lg"><i class="sw tpdsw"></i>',
     "test_the_page_draws_no_tpd_line_when_one_bucket_is_off_the_chart"),

    ("#ops-errors: budget breaks count every error kind, not the two budget kinds",
     "src/astro_ai/ops_data.py",
     "            if kind in BUDGET_ERROR_TYPES:",
     "            if True:",
     "test_the_budget_breaks_are_counted_per_source_over_the_budget_kinds_only"),

    ("#ops-errors: the breakdown stops filtering on the event type (page views counted as errors)",
     "src/astro_ai/events.py",
     '            if evt.get("type") != "error":\n                continue\n            data = evt.get("data") or {}',
     '            data = evt.get("data") or {}',
     "test_the_count_and_the_rate_are_both_exact"),

    ("#ops-tpl: the error cell goes back to a hardcoded red threshold",
     "src/astro_ai/templates/admin_ops.html",
     "ops.app.error_rate >= ops.error_rate_red",
     "ops.app.error_rate >= 5",
     "test_the_error_cell_takes_its_red_threshold_from_the_module"),

    # ---- QA round 3 on #419, SB-1. The cap is gone; these guard the uncapped
    # ---- walk that replaced it, which had no direct test at all (every
    # ---- ops-side test stubs it, correctly -- so three mutants of the walk
    # ---- itself survived the whole suite).

    ("#ops-errors: the breakdown counts non-error events too (page views inflate the rate)",
     "src/astro_ai/events.py",
     '            if evt.get("type") != "error":\n                continue\n            data = evt.get("data") or {}',
     '            data = evt.get("data") or {}',
     "test_only_error_events_are_counted"),

    ("#ops-errors: the retention clamp is dropped, so every window reads one day",
     "src/astro_ai/events.py",
     "    days = max(1, min(days, EVENT_RETENTION_DAYS))\n    today = date.today()\n    wanted_days = [today - timedelta(days=i) for i in range(days)]\n\n    # Same fan-out",
     "    days = 1\n    today = date.today()\n    wanted_days = [today - timedelta(days=i) for i in range(days)]\n\n    # Same fan-out",
     "test_the_window_is_clamped_to_the_retention_ceiling"),

    ("#ops-errors: a marginal counts pair KEYS instead of pair COUNTS",
     "src/astro_ai/events.py",
     "        by_source[src] = by_source.get(src, 0) + n",
     "        by_source[src] = by_source.get(src, 0) + 1",
     "test_the_cross_tab_and_both_marginals_agree_with_the_total"),

    ("#ops-errors: an unclassifiable error is dropped rather than counted as '?'",
     "src/astro_ai/events.py",
     '            key = (data.get("error_type") or "?", data.get("source") or "?")',
     '            if not data.get("error_type"):\n                continue\n            key = (data.get("error_type") or "?", data.get("source") or "?")',
     "test_an_error_with_no_shape_is_counted_rather_than_dropped"),

    ("#ops-errors: a corrupt day blob aborts the walk instead of being skipped",
     "src/astro_ai/events.py",
     "    pairs: dict[tuple[str, str], int] = {}\n    for blob in blobs:\n        if blob is None:\n            continue",
     "    pairs: dict[tuple[str, str], int] = {}\n    for blob in blobs:\n        if blob is None:\n            raise RuntimeError('missing day')",
     "test_a_missing_or_unreadable_day_does_not_abort_the_walk"),
    # ---- QA round 2 on #418. Three ship-blocking findings. The first is the
    # ---- one this block exists for: `truncated` was computed and read NOWHERE
    # ---- while three places said the page showed it. 18 of the reviewer's 29
    # ---- hand-built mutants survived the suite AND the 179-row sweep.

    ("#ops-today r2: the truncation flag never reaches the view",
     "src/astro_ai/ops_data.py",
     '"failed_truncated": bool((live_today or {}).get("failed_truncated")),\n        # Travels WITH',
     '"failed_truncated": False,\n        # Travels WITH',
     "test_a_truncated_read_renders_an_at_least_on_the_tiles"),

    ("#ops-today r2: the tile prints a capped count as a total",
     "src/astro_ai/templates/admin_ops.html",
     "{{ '\\u2265' if L.failed_truncated }}{{ L.today_failed|length }}",
     "{{ L.today_failed|length }}",
     "test_a_truncated_read_renders_an_at_least_on_the_tiles"),

    ("#ops-today r2: a startup_failure counts as a success (a leg that never ran reads as 0)",
     "src/astro_ai/ops_today.py",
     'SUCCEEDED_CONCLUSIONS = ("success", "skipped", "neutral")',
     'SUCCEEDED_CONCLUSIONS = ("success", "skipped", "neutral", "startup_failure")',
     "test_any_conclusion_that_is_not_a_success_counts_as_a_failure"),

    ("#ops-today r2: conclusions go back to an allow-list of failures",
     "src/astro_ai/ops_today.py",
     "        if concl is None or concl in SUCCEEDED_CONCLUSIONS:\n            continue",
     '        if concl not in ("failure", "timed_out", "cancelled"):\n            continue',
     "test_any_conclusion_that_is_not_a_success_counts_as_a_failure"),

    ("#ops-today r2: _fetch keeps the four-type tuple (a truncated read 500s the page)",
     "src/astro_ai/ops_data.py",
     '        except Exception as exc:  # noqa: BLE001 -- see above\n            log.warning("ops_data: could not fetch %s: %s", url, exc, exc_info=True)',
     '        except (urllib.error.URLError, OSError, ValueError) as exc:\n            log.warning("ops_data: could not fetch %s: %s", url, exc)',
     "test_the_measurements_fetch_does_not_500_the_page_on_a_truncated_read"),

    ("#ops-today r2: the tiles fall back to a stale snapshot and no alert says so",
     "src/astro_ai/ops_data.py",
     '    if loop.get("fell_back"):',
     "    if False:",
     "test_a_programming_error_in_the_live_path_raises_an_alert"),

    ("#ops-today r2: fell_back is never computed for the delivery tiles",
     "src/astro_ai/ops_data.py",
     "fell_back=LIVE_TODAY and live_today is None)",
     "fell_back=False)",
     "test_a_programming_error_in_the_live_path_raises_an_alert"),

    # ---- QA round 3 on #418 (2026-10-20). Twelve guard gaps, each one proved
    # ---- by a hand-built mutant that survived the whole suite AND the 179-row
    # ---- sweep. Their shared shape, worth stating once: every one of them
    # ---- pinned a TRANSPORT and not a USE. `fetch_today` was tested against a
    # ---- day start handed to it already correct, so nothing tested the line
    # ---- that COMPUTES it; `truncated` was tested as a dict key, so nothing
    # ---- tested the badge; `today_live` was tested as a serialised JSON
    # ---- field, so nothing tested the branch that picks a renderer from it.

    ("#ops-today r3 G1: the IST day start is computed in UTC (THE original "
     "boundary bug, at the caller this time)",
     "src/astro_ai/ops_data.py",
     "    day_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)",
     "    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)",
     "test_the_page_computes_the_day_start_in_ist_not_in_utc"),

    ("#ops-today r3 G1: the date printed beside the tiles is the UTC one",
     "src/astro_ai/ops_data.py",
     '    today_ist = now_ist.strftime("%Y-%m-%d")',
     '    today_ist = now.strftime("%Y-%m-%d")',
     "test_the_day_start_handed_to_the_api_is_the_one_the_page_prints"),

    ("#ops-today r3 G2: the LIVE_TODAY kill switch stops switching anything",
     "src/astro_ai/ops_data.py",
     "    live_today = _live_today(day_start.astimezone(timezone.utc)) if LIVE_TODAY else None",
     "    live_today = _live_today(day_start.astimezone(timezone.utc))",
     "test_pinning_the_tiles_to_the_snapshot_makes_no_api_call_and_is_not_a_fallback"),

    ("#ops-today r3 G2: the behaviour suite can reach the network again",
     "tests/conftest.py",
     '    monkeypatch.setattr(urllib.request, "urlopen", _blocked)',
     "    assert _blocked",
     "test_the_behaviour_suite_cannot_reach_the_network"),

    ("#ops-today r3 G3: the live-BACKLOG catch narrows back to four types",
     "src/astro_ai/ops_data.py",
     "    except Exception as exc:  # noqa: BLE001\n"
     "        # Broad for the same reason as `_live_today` below",
     "    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:\n"
     "        # Broad for the same reason as `_live_today` below",
     "test_a_backlog_failure_outside_the_four_old_exception_types_does_not_500"),

    ("#ops-today r3 G3: the backlog falls back to a stale count and no alert says so",
     "src/astro_ai/ops_data.py",
     '    if issues.get("fell_back"):',
     "    if False:",
     "test_a_backlog_programming_error_degrades_the_panel_rather_than_the_page"),

    ("#ops-today r3 G4: the Shipped tile is badged `live` off the snapshot",
     "src/astro_ai/templates/admin_ops.html",
     "{% if L.today_live %}<span class=\"age\">live{% if L.shipped_truncated %}, at least{% endif %}</span>",
     "{% if True %}<span class=\"age\">live{% if L.shipped_truncated %}, at least{% endif %}</span>",
     "test_the_shipped_tile_says_live_only_when_it_is_live"),

    ("#ops-today r3 G4: the Failed-today fallback drops the agent-work-only caveat",
     "src/astro_ai/templates/admin_ops.html",
     "agent-work only, as of {{ ops.ages.Delivery.text }}",
     "as of {{ ops.ages.Delivery.text }}",
     "test_the_failed_tile_fallback_says_it_counts_agent_work_only"),

    ("#ops-today r3 G4: the Filed-today source badge is deleted outright",
     "src/astro_ai/templates/admin_ops.html",
     '      <span class="foot">new issues opened<br>\n'
     '        {% if I.live %}<span class="age">live</span>\n'
     '        {% else %}<span class="age {{ \'stale\' if ops.ages.Backlog.stale }}">'
     'as of {{ ops.ages.Backlog.text }}</span>{% endif %}</span>',
     '      <span class="foot">new issues opened</span>',
     "test_the_filed_tile_carries_its_own_source_badge"),

    ("#ops-today r3 G5: the drill-down hardcodes the cycle renderer (a panel of blanks)",
     "src/astro_ai/templates/admin_ops.html",
     '                      D.today_live ? "pr" : "cycle"],',
     '                      "cycle"],',
     "test_the_drill_down_picks_its_row_renderer_from_the_live_flag"),

    ("#ops-today r3 G5: every PR in the sheet links to the same pull request",
     "src/astro_ai/templates/admin_ops.html",
     'link(REPO + "/pull/" + r.pr, "PR diff &rarr;")',
     'link(REPO + "/pull/418", "PR diff &rarr;")',
     "test_the_drill_down_links_a_merged_pr_by_its_own_number"),

    ("#ops-today r3 G6: no snapshot AND no API renders three tiles reading `0 ... live`",
     "src/astro_ai/ops_data.py",
     '                "today_live": live_today is not None,',
     '                "today_live": True,',
     "test_no_snapshot_and_no_api_is_an_absence_not_three_live_zeroes"),

    ("#ops-today r3 G7: the fallback alert loses the whole explanation",
     "src/astro_ai/ops_data.py",
     '                "From the committed snapshot, not live, so this counts "\n'
     '                "agent-work only and may be out of date. A cycle that did not "\n'
     '                "deliver leaves its issue untouched.")',
     '                "A cycle that did not deliver leaves its issue untouched.")',
     "test_the_fallback_alert_says_the_count_is_stale_and_agent_work_only"),

    ("#ops-today r3 G8: Filed today borrows the delivery panel's live flag",
     "src/astro_ai/routes/admin.py",
     '        "filed_live": I.get("live", False),',
     '        "filed_live": True,',
     "test_the_filed_drill_down_flag_follows_the_backlog_not_the_delivery_read"),

    ("#ops-today r3 G9: the page cap goes to 99 (120/hour becomes 2,424/hour)",
     "src/astro_ai/ops_today.py",
     "MAX_PAGES = 3",
     "MAX_PAGES = 99",
     "test_a_pathological_day_is_capped_at_three_pages_per_endpoint"),

    ("#ops-today r3 G9: per_page drops to 30 (an ordinary day becomes 'at least')",
     "src/astro_ai/ops_today.py",
     "PER_PAGE = 100",
     "PER_PAGE = 30",
     "test_each_page_asks_for_a_hundred_rows"),

    ("#ops-today r3 G9: the day-boundary stop rule never fires",
     "src/astro_ai/ops_today.py",
     "        if oldest(batch[-1]) < since:\n"
     "            return rows, False          # paged back past the day start",
     "        if False:\n"
     "            return rows, False          # paged back past the day start",
     "test_the_pager_stops_at_the_day_boundary_not_only_on_a_short_page"),

    ("#ops-today r3 G9: a 403 body is accepted as an empty page (0/0/0, badged live)",
     "src/astro_ai/ops_today.py",
     "        if not isinstance(batch, list):\n"
     "            raise ValueError(f\"{base.rsplit('/', 1)[-1]} did not return a list\")",
     "        if not isinstance(batch, list):\n"
     "            batch = []",
     "test_a_page_that_is_not_a_list_raises_rather_than_counting_as_empty"),

    ("#ops-today r3 G11: failed loses its cross-page distinctness",
     "src/astro_ai/ops_today.py",
     '        failed[rid if rid is not None else ("no-id", len(failed))] = {',
     "        failed[(\"row\", len(failed))] = {",
     "test_a_run_repeated_across_a_page_boundary_is_counted_once"),

    ("#ops-today r3 G11: dedupe becomes a drop for a row with no id",
     "src/astro_ai/ops_today.py",
     '        failed[rid if rid is not None else ("no-id", len(failed))] = {',
     "        failed[rid] = {",
     "test_a_run_with_no_id_is_kept_rather_than_collapsed"),

    # RE-POINTED. F2 rewrote this paragraph from 84/hour to 120/hour, which
    # orphaned the old anchor -- and the new static pre-flight above caught it
    # in milliseconds, where the sweep would have spent a sandboxed suite run
    # to report ANCHOR MISSED. That is the whole argument for the pre-flight,
    # demonstrated by the change that introduced it.
    ("#ops-today r3 G12: the COST paragraph goes back to the pre-pager figure",
     "src/astro_ai/ops_today.py",
     "                                     = 120/hour",
     "                                     = 36/hour",
     "test_the_cost_paragraph_states_the_actual_worst_case"),

    ("#ops-today r3 G15: the ok path trusts a key the degraded path does not",
     "src/astro_ai/ops_data.py",
     '        "today_shipped": (live_today.get("shipped", []) if live_today is not None',
     '        "today_shipped": (live_today["shipped"] if live_today is not None',
     "test_a_live_dict_missing_a_key_blanks_a_tile_rather_than_500ing_the_page"),

    ("#ops-today r3 G10: the workflow exhaustiveness scan globs *.yml only",
     "tests/test_ops_today_live.py",
     '            if p.is_file() and p.suffix in (".yml", ".yaml")}',
     '            if p.is_file() and p.suffix == ".yml"}',
     "test_the_workflow_scan_sees_a_yaml_as_well_as_a_yml"),

    # Two 500s found by making the suite hermetic, in the branch that had never
    # once run under test because the tests rendering it were fetching the real
    # files over the network. `_loop_view` already carried the rule, in ten
    # lines, written after this exact failure; neither sibling inherited it.
    ("#ops-today r3: the backlog zero-state drops keys (KeyError: 'filed_today')",
     "src/astro_ai/ops_data.py",
     '        return {"ok": False, "generated_at": None, "live": False,\n'
     '                "fell_back": fell_back, "open": 0, "rows": [], "with_ask": 0,\n'
     '                "by_priority": {}, "by_area": {}, "by_type": {},\n'
     '                "blocked": [], "filed_today": []}',
     '        return {"ok": False, "rows": [], "live": False, "fell_back": fell_back}',
     "test_the_ops_page_survives_every_source_being_unreadable"),

    ("#ops-today r3: the cost zero-state drops keys (UndefinedError: known_usd)",
     "src/astro_ai/ops_data.py",
     '        return {"ok": False, "rows": [], "known_usd": 0, "unknown": [],\n'
     '                "shipped_30d": shipped_30d, "per_issue_usd": None}',
     '        return {"ok": False, "rows": []}',
     "test_the_ops_page_survives_every_source_being_unreadable"),
    # #409: visitor text at /admin/feedback is protected by autoescape ALONE.
    ("#409: autoescape turned off in the real environment",
     "src/astro_ai/routes/deps.py",
     '    autoescape=jinja2.select_autoescape(\n'
     '        enabled_extensions=("html", "htm", "xml", "svg"),\n'
     '        default_for_string=True,\n'
     '        default=False,\n'
     '    ),\n',
     '    autoescape=False,\n',
     "test_autoescape_is_on_for_html_templates"),

    ("#409: .html dropped from the autoescape extension list",
     "src/astro_ai/routes/deps.py",
     'enabled_extensions=("html", "htm", "xml", "svg"),',
     'enabled_extensions=("htm", "xml", "svg"),',
     "test_a_quote_and_angle_brackets_cannot_leave_the_mailto_attribute"),

    ("#409: |safe on the User-Agent at /admin/feedback (the field nobody mentions)",
     "src/astro_ai/templates/admin_feedback.html",
     "{{ e.ua }}", "{{ e.ua | safe }}",
     "test_feedback_templates_use_no_escape_hatch_at_all"),

    ("#409: |safe on the email inside the mailto: attribute",
     "src/astro_ai/templates/admin_feedback.html",
     'href="mailto:{{ e.email }}"', 'href="mailto:{{ e.email | safe }}"',
     "test_no_template_renders_a_visitor_field_through_an_escape_hatch"),

    ("#409: the scanner stops matching |safe (the check itself goes blind)",
     "tests/test_autoescape_pinned.py",
     '_UNSAFE = re.compile(r"\\|\\s*(?:safe|markup)\\b|\\bMarkup\\s*\\(")',
     '_UNSAFE = re.compile(r"\\|\\s*(?:safe_never|markup)\\b|\\bMarkup\\s*\\(")',
     "test_the_scanner_catches_each_escape_hatch"),
    ("#397: the /ask overlay re-asserts 'no cancelling conditions' for Nadi",
     "src/astro_ai/prompts/ask_matching.txt",
     '- Nadi is not among the Bhakoot parihāras. The exemptions the tradition records apply OUTSIDE the Madhya Nadi only and this product applies none of them — never tell a seeker whose Nadi is Madhya that one exists for their case. A slight (alpa) grade applies where pada-Nadi differs. Never invent any other Nadi condition.',
     "- Nadi has no cancelling conditions in this tradition. Never invent one.",
     "test_no_surface_asserts_nadi_has_no_cancelling_conditions"),

    ("#397: the two /ask overlays' Nadi lines drift apart",
     "src/astro_ai/prompts/ask_matching_third_party.txt",
     "apply OUTSIDE the Madhya Nadi only and this product applies none of them",
     "apply OUTSIDE the Madhya Nadi only and this product applies them",
     "test_both_ask_overlays_carry_the_identical_nadi_line"),

    ("#397: the engine's Nadi note re-asserts the absolute beside the exemption",
     "src/astro_ai/matching.py",
     '" Nadi is not among the Bhakoot parihāras and is required to be sound "\n        "alongside them, and the tradition prescribes shanti where it is present."',
     '" Nadi has no cancelling conditions in this tradition and is required to be sound "\n        "alongside them, and the tradition prescribes shanti where it is present."',
     "test_engine_note_states_the_narrowed_position_and_keeps_the_disclosure"),

    ("#397: /ask context stops feeding nd.unevaluated (overlay names what the model cannot see)",
     "src/astro_ai/llm.py",
     '        lines += [f"  not evaluated: {u}" for u in nd.unevaluated]\n',
     "",
     "test_ask_context_names_the_exemptions_the_overlay_refers_to"),

    ("#397: Hindi panel footnote regains the false first sentence",
     "src/astro_ai/i18n.py",
     '"भकूट के परिहारों में नाड़ी सम्मिलित नहीं है; किसी भी छूट से इसके अंक नहीं बढ़ते।",',
     '"नाड़ी का कोई परिहार नहीं होता। किसी भी छूट से इसके अंक नहीं बढ़ते।",',
     "test_panel_footnote_still_says_no_points_and_not_the_absolute"),

    # ---- QA round 1 on #397. All four blockers were introduced BY this
    # ---- change; the last row is a pre-existing hole the reviewer measured.

    ("#397 QA: the exemption sentence is unscoped again, so a Madhya pair is told one was declined",
     "src/astro_ai/matching.py",
     '    note += (\n        " The regional and community exemptions it records do not extend to the "\n        "Madhya Nadi."\n        if grave else\n        " It also records exemptions by region and community (shown below), "\n        "which we do not apply."\n    )',
     '    note += (\n        " It also records exemptions by region and community (shown below), "\n        "which we do not apply."\n    )',
     "test_a_madhya_pair_is_not_told_an_exemption_was_declined_for_it"),

    ("#397 QA: the Hindi footnote states the OPPOSITE position (ASCII _ABSOLUTE cannot see it)",
     "src/astro_ai/i18n.py",
     '"भकूट के परिहारों में नाड़ी सम्मिलित नहीं है; किसी भी छूट से इसके अंक नहीं बढ़ते।",',
     '"नाड़ी के परिहार लागू होते हैं; किसी भी छूट से इसके अंक नहीं बढ़ते।",',
     "test_the_hindi_footnote_states_the_position_and_not_only_the_points"),

    ("#397 QA: a contradicting overlay instruction on a line the old prefix scan could not see",
     "src/astro_ai/prompts/ask_matching.txt",
     "- The same holds for every Nadi mitigation:",
     "- Regional or community exemptions for Nadi are not part of this tradition; never tell the seeker one exists.\n- The same holds for every Nadi mitigation:",
     "test_no_other_line_in_an_overlay_restates_the_nadi_rule"),

    ("#397 QA: the alpa branch says the tradition REMOVES the dosha",
     "src/astro_ai/matching.py",
     '"dosha slight in this case — reduced, not removed."',
     '"dosha removed entirely in this case."',
     "test_the_alpa_branch_says_reduced_and_never_removed"),

    ("#397 QA: the alpa grading is inverted (no fixture reached this branch at all)",
     "src/astro_ai/matching.py",
     "            if g_pn != b_pn:\n                alpa = True",
     "            if g_pn == b_pn:\n                alpa = True",
     "test_the_alpa_branch_says_reduced_and_never_removed"),

    ("#397 QA: a same-Nadi pair is awarded 8/8 (18.0 Avara -> 26.0 Madhyam, 681 tests passed)",
     "src/astro_ai/matching.py",
     'name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=0.0,',
     'name="Nadi", sanskrit="नाड़ी", max_points=8, awarded=8.0,',
     "test_a_nadi_dosha_awards_no_points_however_it_is_graded"),
    # ---- QA round 2 on #397. S-1 is a fourth surface the round-1 FIX created;
    # ---- the rest are guards round 1's fixes shipped without. 13 of the
    # ---- reviewer's 19 hand-built mutants survived the suite AND the sweep.

    ("#397 r2: the /ask context NOTE is unscoped again (the 4th surface)",
     "src/astro_ai/llm.py",
     '"Madhya Nadi, and are not applied here."))',
     '"Madhya Nadi, and are applied here."))',
     "test_the_ask_context_scopes_the_exemption_on_the_grade"),

    ("#397 r2: the overlay scope is INVERTED (\"to the Madhya Nadi only\")",
     "src/astro_ai/prompts/ask_matching.txt",
     "apply OUTSIDE the Madhya Nadi only",
     "apply to the Madhya Nadi only",
     "test_both_ask_overlays_carry_the_identical_nadi_line"),

    ("#397 r2: the overlay's anti-hallucination clause is deleted",
     "src/astro_ai/prompts/ask_matching.txt",
     " Never invent any other Nadi condition.", "",
     "test_both_ask_overlays_carry_the_identical_nadi_line"),

    ("#397 r2: the English footnote asserts the OPPOSITE position",
     "src/astro_ai/i18n.py",
     '"Nadi is not among the Bhakoot parihāras, and no mitigation adds points to it.",',
     '"Nadi is among the Bhakoot parihāras, and no mitigation adds points to it.",',
     "test_the_english_footnote_states_the_position_and_not_only_the_points"),

    ("#397 r2: the scoped sentence never reaches the rendered panel",
     "src/astro_ai/templates/matching_result.html",
     "{{ _nd.note }}", "{{ '' }}",
     "test_the_scoped_sentence_actually_reaches_the_rendered_panel"),

    ("#397 r2: the exemption disclosure is suppressed, so \"(shown below)\" points at nothing",
     "src/astro_ai/templates/matching_result.html",
     "{% if _nd.unevaluated %}", "{% if False %}",
     "test_the_exemption_disclosure_reaches_the_rendered_panel"),

    ("#397 r2: the disclosure says we DO apply the exemptions",
     "src/astro_ai/matching.py",
     '"We do not apply those exemptions automatically.",',
     '"We apply those exemptions automatically.",',
     "test_the_exemption_disclosure_says_we_do_NOT_apply_them"),

    ("#397 r2: the alpa pointer claims the dosha is cleared, contradicting the mitigation below it",
     "src/astro_ai/matching.py",
     'note += " One mitigation applies, below."',
     'note += " A mitigation applies which clears this dosha, below."',
     "test_the_alpa_pointer_cannot_contradict_the_mitigation_it_points_at"),

    ("#397 r2: the Nadi absolute returns on /learn in a phrasing _ABSOLUTE never matched",
     "src/astro_ai/templates/learn/kundali-matching-ashtakoot-guna-milan.html",
     "  <div class=\"callout-label\">Nadi Dosh is graded, not cancelled</div>",
     "  <div class=\"callout-label\">Nadi Dosh is graded, not cancelled</div>\n"
     "  <p>Nadi can never be cancelled or waived by anything.</p>",
     "test_a_nadi_absolute_cannot_return_in_a_third_phrasing"),
    # ---- The gate that printed PASS against thirteen HTTP 500s. Every row
    # ---- below removes one of the three guards and must turn the suite red.

    ("#hindi-gate: no health probe, so a foreign server on the port is measured as ours",
     "scripts/verify_hindi_surface.py",
     '    if probe_code != 200 or \'"ok"\' not in probe:',
     '    if False:',
     "test_a_foreign_server_on_the_port_is_not_this_app"),

    ("#hindi-gate: any status is read as a page, so 500s sweep clean (the original defect)",
     "scripts/verify_hindi_surface.py",
     '        if code not in (200, 503):',
     '        if code not in (200, 503, 404, 500):',
     "test_a_page_status_the_gate_cannot_read_is_not_a_pass"),

    ("#hindi-gate: an empty <main> satisfies every negative check and is called a pass",
     "scripts/verify_hindi_surface.py",
     '        if not text.strip():',
     '        if False:',
     "test_an_empty_main_is_not_a_pass"),
    # ---- QA round 4 on #418: F1 and F2 ------------------------------------
    # F1. The truncation marker leaking onto a tile whose read was COMPLETE.
    # The old assertions were whole-PAGE substrings (`"≥" in body`), so this
    # mutant left 772 tests green while the page rendered `≥0 PRs merged`. The
    # scoped form that catches it was credited to this branch by a comment and
    # actually lived on #419, never an ancestor of it.
    ("#418/F1: the truncation flag leaks onto the SHIPPED tile",
     "src/astro_ai/ops_today.py",
     '"shipped_truncated": pr_more,',
     '"shipped_truncated": pr_more or runs_more,',
     "test_a_truncated_read_renders_an_at_least_on_the_tiles"),
    # F2. The COST paragraph's worst case is derived from BOTH pagers now, so
    # moving either constant must move the stated number or the gate is again
    # holding a wrong figure in place -- which is exactly what `+ 1` did.
    ("#418/F2: the backlog pager shrinks and the stated cost does not follow",
     "src/astro_ai/issue_backlog.py",
     "MAX_PAGES = 4",
     "MAX_PAGES = 1",
     "test_the_cost_paragraph_states_the_actual_worst_case"),
    # ---- QA round 4 on #418: F4-F10. Every mutant below was built FIRST and
    # confirmed to survive the suite, then the test was written against it. Two
    # of my first attempts were vacuous (F6 never put the hostile title on the
    # page; F9 mutated a fallback another fallback had already made dead code)
    # and one "catch" was a SyntaxError rather than a catch -- all three found
    # by probing, which is why each row here is parseable and proven.
    ("#418/F4: the tile says a floor and the alert states it as a total",
     "src/astro_ai/ops_data.py",
     'at_least = "At least " if loop.get("failed_truncated") else ""',
     'at_least = ""',
     "test_the_alert_admits_the_floor_when_the_tile_does"),

    # Round 5, N-1. The alert keyed its floor disclosure off `today_truncated`,
    # the OR of both endpoints, while the tile reads the per-endpoint flag -- so
    # with the PULLS read capped and the runs read complete the two disagreed
    # about one number on one screen, and the alert was the false one. Both
    # halves of the disclosure get a row, because they are two separate reads of
    # the same flag and F4 only ever pinned the first.
    ("#418/N1: the alert's floor disclosure goes back to the OR of both endpoints",
     "src/astro_ai/ops_data.py",
     'at_least = "At least " if loop.get("failed_truncated") else ""',
     'at_least = "At least " if loop.get("today_truncated") else ""',
     "test_a_capped_pulls_read_does_not_make_the_failure_count_a_floor"),

    ("#418/N1: the floor SENTENCE goes back to the OR of both endpoints",
     "src/astro_ai/ops_data.py",
     '"this is a floor, not a total." if loop.get("failed_truncated")',
     '"this is a floor, not a total." if loop.get("today_truncated")',
     "test_a_capped_pulls_read_does_not_make_the_failure_count_a_floor"),
    ("#418/F4b: the truncation flag never reaches the alert",
     "src/astro_ai/ops_data.py",
     '"today_truncated": bool((live_today or {}).get("truncated")),\n        # Per tile',
     '"today_truncated": False,\n        # Per tile',
     "test_the_alert_admits_the_floor_when_the_tile_does"),
    ("#418/F10: the alert stops deduping and names a workflow once per run",
     "src/astro_ai/ops_data.py",
     'sorted({f.get("workflow") or "an unnamed workflow"\n                                      for f in loop["today_failed"]})',
     'sorted([f.get("workflow") or "an unnamed workflow"\n                                      for f in loop["today_failed"]])',
     "test_every_failing_workflow_is_named_once"),
    ("#418/F9: a run with no name is no longer identified at all",
     "src/astro_ai/ops_today.py",
     '"workflow": r.get("name") or path',
     '"workflow": r.get("name")',
     "test_a_run_with_no_name_is_still_named_something"),
    ("#418/F6: a PR title can terminate the ops-data script block",
     "src/astro_ai/routes/admin.py",
     'json.dumps(client).replace("</", "<\\\\/")',
     "json.dumps(client)",
     "test_the_ops_json_blob_cannot_be_escaped_by_a_pr_title"),
    ("#418/F5: the GitHub token stops reaching the wire",
     "src/astro_ai/ops_today.py",
     'headers["Authorization"] = f"Bearer {token}"',
     "pass",
     "test_the_request_carries_a_user_agent_and_the_token_when_set"),
    ("#418/F5b: the User-Agent GitHub requires is dropped",
     "src/astro_ai/ops_today.py",
     '"User-Agent": _UA,',
     "",
     "test_the_request_carries_a_user_agent_and_the_token_when_set"),
    # ---- #442: the steward can dispatch, and a merge is not a refix ---------
    ("#442: the carrier stops refusing a lenient dispatch line",
     "scripts/dispatch_cycle.sh",
     "grep -oE '^issue=[0-9]+$'",
     "grep -oE 'issue=[0-9]+'",
     "test_anything_but_issue_equals_digits_is_refused"),
    ("#442: the carrier stops treating an unreadable concurrency check as busy",
     "scripts/dispatch_cycle.sh",
     'if [ "$busy" != "0" ]; then',
     'if [ "$busy" = "1" ]; then',
     "test_an_unreadable_concurrency_check_counts_as_busy"),
    ("#442: the carrier dispatches at a closed issue",
     "scripts/dispatch_cycle.sh",
     'if [ "$state" != "OPEN" ]; then',
     'if [ "$state" = "NEVER" ]; then',
     "test_a_closed_issue_is_refused"),
    ("#442: a merge after the verdict is called a fix again",
     "scripts/detect_stalls.py",
     "elif split[0] == 0 and split[1] > 0:",
     "elif False:",
     "test_a_merge_after_the_verdict_is_not_a_refix"),
    ("#442: merge-ness read from the message instead of the parent count",
     "scripts/detect_stalls.py",
     'if int(meta.get("parents", 1)) > 1:',
     'if (c.get("messageHeadline") or "").startswith("Merge"):',
     "test_merge_ness_comes_from_parent_count_not_the_message"),
    ("#442: unclassifiable commits assert a fix instead of hedging",
     "scripts/detect_stalls.py",
     "if split is None:",
     "if False:",
     "test_unclassifiable_commits_hedge_instead_of_guessing"),
    # ---- #409 round 2: the SVG sink, and the header that hid behind a platform.
    # Each anchor is executable code, never a comment -- the anchor validator
    # exists because a dead row once pinned itself to prose.
    ("#409: `.svg` dropped back out of the autoescape list (the XSS sink)",
     "src/astro_ai/routes/deps.py",
     'enabled_extensions=("html", "htm", "xml", "svg"),',
     'enabled_extensions=("html", "htm", "xml"),',
     "test_svg_is_autoescaped_and_text_is_not"),
    ("#409: the seeker's NAME routed round autoescape with |safe",
     "src/astro_ai/templates/cosmic_card.svg",
     "{{ display_name or 'Janma Kundli' }}",
     "{{ (display_name or 'Janma Kundli') | safe }}",
     "test_a_script_tag_in_a_visitor_field_cannot_reach_the_cosmic_card"),
    ("#409: the seeker's BIRTH PLACE routed round autoescape with |safe",
     "src/astro_ai/templates/cosmic_card.svg",
     "{{ details.birth_place }}",
     "{{ details.birth_place | safe }}",
     "test_a_script_tag_in_a_visitor_field_cannot_reach_the_cosmic_card"),
    ("#409: the session-derived card made publicly cacheable again",
     "src/astro_ai/routes/kundli_card.py",
     '"Cache-Control": "private, max-age=3600",',
     '"Cache-Control": "public, max-age=3600",',
     "test_the_cosmic_card_is_not_cacheable_by_a_shared_cache"),
    # ---- the conflict resolver's own parser, found by PR #443 x #425 --------
    # RE-TARGETED. This row used to replace the newline ASSERTION with
    # `assert True` -- and that assertion is a guard, not the mechanism:
    # `hunks()` is line-based and preserves newlines structurally, so removing
    # the assert changes no behaviour and no test could possibly catch it. The
    # row reported MISSED the first time the fast-path harness ran it, and under
    # the old harness it would have been MISSED too and nobody looked.
    #
    # A mutation must break the BEHAVIOUR the test asserts. `splitlines(True)`
    # is what keeps each row a row; without keepends every row in the hunk
    # collapses into one, which is exactly the defect that shipped into
    # ARCHITECTURE.md on 2026-10-20.
    ("#443: the dated union stops keeping line endings (rows get absorbed)",
     "scripts/merge_main_into_branch.py",
     "both = (theirs + ours).splitlines(True)",
     "both = (theirs + ours).splitlines()",
     "test_a_dated_union_never_absorbs_one_row_into_another"),
    ("#443: the dirty check counts untracked files again (script can never run)",
     "scripts/merge_main_into_branch.py",
     'git("status", "--porcelain", "--untracked-files=no")',
     'git("status", "--porcelain")',
     "test_the_dirty_check_ignores_untracked_files"),
    ("#443: a malformed hunk returns nothing instead of raising",
     "scripts/merge_main_into_branch.py",
     'raise RuntimeError("a conflict hunk has no `=======` separator")',
     'return out',
     "test_a_hunk_with_no_separator_raises_rather_than_returning_nothing"),

    # ---- QA round 5 on #396. S-1 / S-2 / G-2 were FALSE SENTENCES and a guard
    # ---- that could not tell `calls` from `measurable`. Each row restores one
    # ---- false clause (or breaks the number the clause is about) and must die on
    # ---- its OWN named test.
    ("#396 r5: an impossible report is described as counted in Hit rate again (S-1)",
     "src/astro_ai/templates/admin_dashboard.html",
     "discarded: it is in <em>neither</em> Hit rate <em>nor</em> Effective, and the call",
     "discarded: its figure counts toward Hit rate, and the call",
     "test_an_impossible_report_is_in_neither_rate_and_not_harmless_as_the_notice_says"),

    ("#396 r5: an impossible report is told it needs no action again (S-1)",
     "src/astro_ai/templates/admin_dashboard.html",
     "This one does need attention &mdash;", "This one needs no action &mdash;",
     "test_an_impossible_report_is_in_neither_rate_and_not_harmless_as_the_notice_says"),

    ("#396 r5: a rejected report is booked as Reported (the row would contradict the notice)",
     "src/astro_ai/llm_stats.py",
     '                pc["reported_unmeasurable"] = pc.get("reported_unmeasurable", 0) + 1\n',
     '                pc["reported_unmeasurable"] = pc.get("reported_unmeasurable", 0) + 1\n'
     '                pc["reported"] = pc.get("reported", 0) + 1\n',
     "test_an_impossible_report_is_in_neither_rate_and_not_harmless_as_the_notice_says"),

    ("#396 r5: the notice counts reports, not unmeasurable-report calls",
     "src/astro_ai/templates/admin_dashboard.html",
     "map(attribute='reported_unmeasurable') | sum", "map(attribute='reported') | sum",
     "test_the_unmeasurable_notice_sums_both_causes_into_its_count"),

    ("#396 r5: the genuine-report clause stops saying the figure is in Hit rate",
     "src/astro_ai/templates/admin_dashboard.html",
     "that figure is counted in", "that figure is dropped from",
     "test_a_genuine_unmeasurable_report_is_in_hit_rate_and_out_of_effective_as_the_notice_says"),

    ("#396 r5: a genuine unmeasurable report stops reaching the Hit-rate numerator",
     "src/astro_ai/llm_stats.py",
     'pc["cached_tokens"] = pc.get("cached_tokens", 0) + cached_tokens',
     'pc["cached_tokens"] = pc.get("cached_tokens", 0) + 0',
     "test_a_genuine_unmeasurable_report_is_in_hit_rate_and_out_of_effective_as_the_notice_says"),

    ("#396 r5: 'a route of only impossible reports shows a dash in both rates' is rewritten",
     "src/astro_ai/templates/admin_dashboard.html",
     "shows a dash in both rates.", "shows 0% in both rates.",
     "test_a_route_of_only_impossible_reports_shows_a_dash_in_both_rates_as_the_notice_says"),

    ("#396 r5: the notice names a floor the code does not apply",
     "src/astro_ai/templates/admin_dashboard.html",
     "It can also mean the 128-token floor", "It can also mean the 1024-token floor",
     "test_the_floor_the_notice_names_is_the_floor_the_code_applies"),

    ("#396 r5: the footnote miscounts the cache-reporting models",
     "src/astro_ai/templates/admin_dashboard.html",
     "on one of the three cache-reporting models", "on one of the four cache-reporting models",
     "test_the_footnote_count_of_cache_reporting_models_is_the_set_size"),

    ("#396 r5: the dash sentence goes back to three causes",
     "src/astro_ai/templates/admin_dashboard.html",
     "<strong>An Effective dash has four causes</strong>",
     "<strong>An Effective dash has three causes</strong>",
     "test_the_dash_causes_are_counted_and_the_fourth_is_the_impossible_report"),

    ("#396 r5: the dash sentence drops the impossible-report cause",
     "src/astro_ai/templates/admin_dashboard.html",
     "or every report it sent was\n          impossible and discarded",
     "or nothing at all was\n          sent",
     "test_the_dash_causes_are_counted_and_the_fourth_is_the_impossible_report"),

    ("#396 r5: the excluded-rows notice goes back to naming only the older schema",
     "src/astro_ai/templates/admin_dashboard.html",
     " (written by an older schema, or keyed\n          in a shape this page does not recognise), so their calls are missing",
     " (written by an older schema), so their calls are missing",
     "test_the_excluded_rows_notice_counts_rows_and_names_both_causes_and_the_calls_are_missing"),

    ("#396 r5: the excluded-rows notice prints the wrong count",
     "src/astro_ai/templates/admin_dashboard.html",
     "<strong>{{ llm_stats.aggregate.prefix_cache_skipped_rows }}\n          stored row(s) were excluded as unreadable",
     "<strong>{{ llm_stats.aggregate.prefix_cache | length }}\n          stored row(s) were excluded as unreadable",
     "test_the_excluded_rows_notice_counts_rows_and_names_both_causes_and_the_calls_are_missing"),

    ("#396 r5: the total-loss notice stops claiming it is every row",
     "src/astro_ai/templates/admin_dashboard.html",
     "&mdash; which is every row in this window", "&mdash; which is some of the rows in this window",
     "test_the_skip_notice_survives_when_every_row_is_skipped"),

    ("#396 r5: the gap is computed from `measurable`, not `calls` (G-2)",
     "src/astro_ai/llm_stats.py",
     '                route: n - prefix_acc.get(route, {}).get("calls", 0)\n'
     '                for route, n in by_route.items()\n'
     '                if n > prefix_acc.get(route, {}).get("calls", 0)\n',
     '                route: n - prefix_acc.get(route, {}).get("measurable", 0)\n'
     '                for route, n in by_route.items()\n'
     '                if n > prefix_acc.get(route, {}).get("measurable", 0)\n',
     "test_the_gap_against_by_route_is_counted_not_explained_away"),

    ("#396 r5: the gap sentence says the unaccounted calls ARE in Fresh calls (S-2)",
     "src/astro_ai/templates/admin_dashboard.html",
     "not counted in Fresh calls here</strong>", "counted in Fresh calls above</strong>",
     "test_the_gap_sentence_says_the_unaccounted_calls_are_not_in_fresh_calls"),

    ("#396 r5: the false 'count toward Fresh calls' sentence is reinstated (S-2)",
     "src/astro_ai/templates/admin_dashboard.html",
     "          Two ordinary causes:",
     "          Those calls count toward Fresh calls above. Two ordinary causes:",
     "test_the_gap_sentence_says_the_unaccounted_calls_are_not_in_fresh_calls"),

    ("#396 r5: every gap route is listed with the TOTAL instead of its own count",
     "src/astro_ai/templates/admin_dashboard.html",
     "{{ route }} {{ n }}{% if not loop.last %}",
     "{{ route }} {{ gap.values() | sum }}{% if not loop.last %}",
     "test_the_gap_lists_every_route_with_its_own_count_and_sums_them"),

    ("#396 r5: the gap stops naming the excluded-rows cause (S-2, second half)",
     "src/astro_ai/templates/admin_dashboard.html",
     "; and the stored rows excluded as unreadable", "; and nothing else",
     "test_the_gap_names_both_causes_and_a_skipped_row_really_does_widen_it"),

    ("#396 r5: the gap sentence goes back to the false vocabulary-mismatch claim",
     "src/astro_ai/templates/admin_dashboard.html",
     "both on the chat route", "web route there, chat route here",
     "test_both_lists_are_keyed_on_the_same_route_as_the_gap_sentence_claims"),

    ("#396 r5: the gap sentence stops saying it shrinks as older days age out",
     "src/astro_ai/templates/admin_dashboard.html",
     "shrinks as they age out of the window", "stays until it is cleared",
     "test_the_gap_copy_says_older_days_age_out"),

    ("#396 r5: the gap ignores the requested window (older days never age out)",
     "src/astro_ai/llm_stats.py",
     "    prefix_acc: dict[str, dict[str, int]] = {}\n    skipped_rows = 0",
     "    days = max(days, 3)\n    prefix_acc: dict[str, dict[str, int]] = {}\n    skipped_rows = 0",
     "test_the_part_of_the_gap_owed_to_older_days_does_shrink_as_they_age_out"),

    # ---- QA round 6 on #396. A THIRD round of false sentences in one paragraph.
    # ---- A sentence no test can fail on is DELETED (and its reinstatement is a
    # ---- row here); one that stays is tied to the code it describes.
    ("#396 r6 F-1: the false 'Measurable column tells the first two apart' sentence is reinstated",
     'src/astro_ai/templates/admin_dashboard.html',
     'not that nothing was measured.\n        </p>',
     'not that nothing was measured. The Measurable column tells\n          the first two apart from Fresh calls.\n        </p>',
     'test_sentences_that_no_test_could_pin_stay_deleted'),

    ("#396 r6 F-3: the overclaiming '(the notice above says so ...)' parenthetical is reinstated",
     'src/astro_ai/templates/admin_dashboard.html',
     'not that nothing was measured.\n        </p>',
     'not that nothing was measured (the notice above says so when that has happened).\n        </p>',
     'test_sentences_that_no_test_could_pin_stay_deleted'),

    ("#396 r6 F-4: the unpinned '732 tokens' parenthetical is reinstated",
     'src/astro_ai/templates/admin_dashboard.html',
     'the prompts were under the minimum;\n',
     "the prompts were under the minimum\n          (no route's system prompt is under 732 tokens, so this should not happen);\n",
     'test_sentences_that_no_test_could_pin_stay_deleted'),

    ("#396 r6 F-4: the unpinned 'survives our cold starts' claim is reinstated",
     'src/astro_ai/templates/admin_dashboard.html',
     "is Groq's, and\n          is opportunistic.",
     "is Groq's: it survives our cold starts, and\n          is opportunistic.",
     'test_sentences_that_no_test_could_pin_stay_deleted'),

    ("#396 r6 F-4: the unpinned 'expires after about 2 hours idle' claim is reinstated",
     'src/astro_ai/templates/admin_dashboard.html',
     "is Groq's, and\n          is opportunistic.",
     "is Groq's: it expires after about 2 hours idle, and\n          is opportunistic.",
     'test_sentences_that_no_test_could_pin_stay_deleted'),

    ("#396 r6 F-4: 'Widen the window, or re-record.' is reinstated",
     'src/astro_ai/templates/admin_dashboard.html',
     '        no table to show.\n',
     '        no table to show. Widen the window, or re-record.\n',
     'test_the_skip_notice_survives_when_every_row_is_skipped'),

    ('#396 r6 F-2: the Hit-rate dash tooltip enumerates causes again (false on the impossible-report row)',
     'src/astro_ai/templates/admin_dashboard.html',
     '{% if pc.hit_pct is none %}\n              <td class="py-2 text-right text-bhagya-muted tabular-nums" title="Unmeasured, not 0%:',
     '{% if pc.hit_pct is none %}\n              <td class="py-2 text-right text-bhagya-muted tabular-nums" title="Either no call returned a cache figure. Unmeasured, not 0%.',
     'test_the_footnote_and_the_column_tooltip_agree_on_what_a_dash_means'),

    ('#396 r6 F-2: the Effective dash tooltip enumerates three causes again (false on the fourth)',
     'src/astro_ai/templates/admin_dashboard.html',
     '{% if pc.effective_pct is none %}\n              <td class="py-2 text-right text-bhagya-muted tabular-nums" title="Unmeasured, not 0%:',
     '{% if pc.effective_pct is none %}\n              <td class="py-2 text-right text-bhagya-muted tabular-nums" title="Nothing measurable here: a non-reporting model, every prompt under the minimum cacheable length, or no usable usage block. Unmeasured, not 0%.',
     'test_the_footnote_and_the_column_tooltip_agree_on_what_a_dash_means'),

    ("#396 r6 F-4: the 'Unmeasured, not 0%' tooltip text stops saying it (Hit rate)",
     'src/astro_ai/templates/admin_dashboard.html',
     '{% if pc.hit_pct is none %}\n              <td class="py-2 text-right text-bhagya-muted tabular-nums" title="Unmeasured, not 0%:',
     '{% if pc.hit_pct is none %}\n              <td class="py-2 text-right text-bhagya-muted tabular-nums" title="Zero.',
     'test_the_footnote_and_the_column_tooltip_agree_on_what_a_dash_means'),

    ("#396 r6 F-4: an impossible report is 'fewer' cached tokens than the prompt, not more",
     'src/astro_ai/templates/admin_dashboard.html',
     'claimed more cached tokens than the',
     'claimed fewer cached tokens than the',
     'test_the_impossible_report_clause_names_exactly_what_the_code_rejects'),

    ("#396 r6 F-4: the 'not a non-negative whole number' half of the impossible-report clause is deleted",
     'src/astro_ai/templates/admin_dashboard.html',
     'or a count that was not a non-negative whole number',
     'or nothing else',
     'test_the_impossible_report_clause_names_exactly_what_the_code_rejects'),

    ("#396 r6 F-4: 'The counter cannot tell its two causes apart' becomes 'tells'",
     'src/astro_ai/templates/admin_dashboard.html',
     'The counter cannot tell its two causes apart',
     'The counter tells its two causes apart',
     'test_the_unmeasurable_notice_sums_both_causes_into_its_count'),

    ('#396 r6 F-4: older days are described as scored zero, not absent',
     'src/astro_ai/templates/admin_dashboard.html',
     'and so are absent rather than zero',
     'and so are zero',
     'test_the_gap_names_both_causes_and_a_skipped_row_really_does_widen_it'),

    ("#396 r6 F-4: the 'no usable usage block' cause is deleted from the dash list",
     'src/astro_ai/templates/admin_dashboard.html',
     '          the provider returned no usable <code>usage</code> block at all; or every report',
     '          every report',
     'test_all_four_dash_causes_render_identically_and_the_footnote_lists_them'),

    # --- #396 QA round 7 ---------------------------------------------------
    # Two of round 7's seventeen mutants SURVIVED. Both are claims the page makes
    # that no assertion could fail, and the rule here is that such a sentence is
    # deleted or pinned. Both are true, so they are pinned.
    ("#396 r7: Groq's prefix cache is promised as a guarantee",
     "src/astro_ai/templates/admin_dashboard.html",
     "is opportunistic.", "is guaranteed.",
     "test_the_two_caches_sentences_cannot_be_softened"),

    ("#396 r7: the response cache is claimed to outlive its instance",
     "src/astro_ai/templates/admin_dashboard.html",
     "dies with it.", "survives cold starts.",
     "test_the_two_caches_sentences_cannot_be_softened"),

    # N-1. The two rate columns dash under DIFFERENT rules, so ONE tooltip for
    # both is necessarily false on one of them -- which is what round 7 failed
    # the page on. This puts the shared tooltip back.
    ("#396 r7 N-1: one tooltip serves both dash columns again",
     "src/astro_ai/templates/admin_dashboard.html",
     'title="Unmeasured, not 0%: no call on this route reported a cache figure, or those '
     'that did reported no prompt tokens. Groq returns no figure on a miss, so this sits '
     'beside a real Effective number when nothing hit."',
     'title="Unmeasured, not 0%: no call on this route was Measurable. The note below the '
     'table lists the four causes."',
     "test_the_footnote_and_the_column_tooltip_agree_on_what_a_dash_means"),

    ("#396 r7 N-1: Effective's four causes are claimed of every dash again",
     "src/astro_ai/templates/admin_dashboard.html",
     "<strong>An Effective dash has four causes</strong>",
     "<strong>A dash has four causes</strong>",
     "test_the_footnote_and_the_column_tooltip_agree_on_what_a_dash_means"),

    # Round 7 called a zero reported-prompt total a possible SIXTH cause it had
    # not seeded. It is `_rate`'s second clause, and the tooltip must say so.
    ("#396 r7: the Hit-rate tooltip drops its denominator clause",
     "src/astro_ai/templates/admin_dashboard.html",
     ", or those that did reported no prompt tokens", "",
     "test_a_reported_prompt_total_of_zero_is_the_hit_rate_rules_second_clause"),

    # The code side of the same rule: with `not n` gone, a route where every call
    # missed reads a flat 0.0% hit rate instead of a dash -- "absent" booked as
    # "measured zero", the defect this whole panel exists to avoid.
    ("#396 r7: _rate books an unobserved rate as a measured zero",
     "src/astro_ai/llm_stats.py",
     "    if not n or prompt <= 0:", "    if prompt <= 0:",
     "test_an_all_miss_route_dashes_hit_rate_beside_a_real_effective"),
    # ---- #446: the derived test-count floor ---------------------------------
    ("#446: the floor compares against LOCAL main again (passes 543 >= 0)",
     "scripts/verify_test_floor.py",
     'base = git("merge-base", "HEAD", "origin/main").strip()',
     'base = git("merge-base", "HEAD", "main").strip()',
     "test_it_never_compares_against_local_main"),
    ("#446: a vanished test is no longer reported as missing",
     "scripts/verify_test_floor.py",
     "gone = sorted(before - head)",
     "gone = sorted(head - before)",
     "test_a_deleted_file_fails_and_names_every_test"),
    ("#446: any drop is accepted, declared or not",
     "scripts/verify_test_floor.py",
     "    if reason:",
     "    if True:",
     "test_a_declared_drop_needs_the_trailer_not_just_the_words"),
    ("#446: a missing tests/ directory reads as a pass",
     "scripts/verify_test_floor.py",
     'print(f"COULD NOT RUN (exit 2) — no {TESTS}/ directory. This is NOT a pass.")\n        return 2',
     'return 0',
     "test_a_missing_tests_directory_exits_2_not_0"),
    ("#446: a class method that disappears is not counted",
     "scripts/verify_test_floor.py",
     'elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):',
     "elif False:",
     "test_a_method_removed_from_a_test_class_fails"),

    # ---- #446 part 3 residual: parametrize case counts -----------------------
    # QA on PR #448 deleted one case from a literal list and got PASS, exit 0.
    ("#446: a deleted parametrize case is invisible again (names only)",
     "scripts/verify_test_floor.py",
     "elif before[name] is not None and head[name] < before[name]:",
     "elif False:",
     "test_a_deleted_parametrize_case_fails_and_names_the_function"),
    ("#446: stacked parametrize decorators are summed, not multiplied",
     "scripts/verify_test_floor.py",
     "else total * n",
     "else total + n",
     "test_stacked_parametrize_is_a_product"),
    ("#446: a literal list that became computed is read as still fine",
     "scripts/verify_test_floor.py",
     "if before[name] is not None and head[name] is None:",
     "if False:",
     "test_computed_argvalues_do_not_crash_and_a_literal_turned_computed_fails"),
    ("#446: a parametrize list held in a module-level name is not followed",
     "scripts/verify_test_floor.py",
     "if isinstance(node, ast.Name) and node.id in bound:",
     "if False:",
     "test_a_name_bound_once_to_a_literal_is_followed"),

    # --- #419/#452 QA round 4: F-1, F-2, F-3, F-5, F-6, BUG-5, BUG-6 --------
    # F-2 is the headline: the stacked bars had NO test and NO row, so all three
    # of these survived the whole suite and the 266-row sweep -- and the second
    # one DELETES the chart this work exists to add.
    ("#452/F-2a: the stack is drawn from the top edge, upside down",
     "src/astro_ai/templates/admin_ops.html",
     '''y="{{ '%.3f'|format(100 - ns.acc) }}"''',
     '''y="{{ '%.3f'|format(ns.acc) }}"''',
     "test_the_stack_is_anchored_at_the_axis_floor_not_the_top_edge"),

    ("#452/F-2b: the bar threshold emits nothing, deleting the chart outright",
     "src/astro_ai/templates/admin_ops.html",
     "{%- if v > 0 %}", "{%- if v > 999999999999 %}",
     "test_the_chart_draws_a_rect_for_every_non_zero_feature_day"),

    ("#452/F-2c: the bars use a different scale from the line across them",
     "src/astro_ai/templates/admin_ops.html",
     "{%- set h = v / ops.app.trend.top * 100 %}",
     "{%- set h = v / ops.app.trend.peak * 100 %}",
     "test_each_segment_height_is_its_share_of_the_axis_top"),

    # F-1. `top` and `peak` are one line apart in the same dict, and BOTH
    # existing placement fixtures pinned `peak == top`, which also made
    # `assert 'y1="-' not in html` blind. The old row mutated to `top * 2`,
    # which the TPD*2 fixture does separate -- so the row passed while the
    # realistic substitution walked through.
    ("#452/F-1: tpd_y is placed from the raw peak instead of the axis top",
     "src/astro_ai/ops_data.py",
     '"tpd_y": round(100 - TPD_PER_MODEL / top * 100, 2) if top else 100,',
     '"tpd_y": round(100 - TPD_PER_MODEL / peak * 100, 2) if top else 100,',
     "test_the_tpd_line_is_placed_from_the_axis_top_not_the_raw_peak"),

    # F-3. The only test of this decision used to `pytest.skip` on an empty
    # store, which IS the CI condition, so both of these were unguarded there.
    ("#452/F-3: the error-rate alert hardcodes its window",
     "src/astro_ai/ops_data.py",
     '''f"{app['days']} days.", "/admin/activity")''',
     '''f"7 days.", "/admin/activity")''',
     "test_an_app_alert_names_the_window_it_was_measured_over"),

    ("#452/F-3: the provider-fail alert hardcodes its window",
     "src/astro_ai/ops_data.py",
     '''f"in {app['days']}d",''',
     '''f"in 7d",''',
     "test_an_app_alert_names_the_window_it_was_measured_over"),

    ("#452/F-5: the day window is advertised as a rolling 24 hours",
     "src/astro_ai/templates/admin_ops.html",
     "1: 'the current day so far — a calendar day, not a rolling 24 hours',",
     "1: 'the last 24 hours',",
     "test_the_day_window_is_not_advertised_as_a_rolling_24_hours"),

    ("#452/F-6: an empty trend chart vanishes with no statement",
     "src/astro_ai/templates/admin_ops.html",
     "This is an absence, not a zero", "This is a zero",
     "test_an_empty_trend_says_so_rather_than_vanishing"),

    # The row shipped in #455 naming `test_the_window_selector`, which has
    # never existed. #455 was green alone because rows still ran the whole
    # suite then, and the GUARD GONE check arrived in a sibling PR -- so two
    # independently-green PRs made main red, and nothing noticed because
    # pr-gates does not run on main. Pointed at the guard that names the
    # defect: it reports "offers [1, 1, 1], the app accepts [1, 7, 30]".
    ("#452/BUG-5: the window selector hardcodes one window",
     "src/astro_ai/templates/admin_ops.html",
     'href="?window={{ d }}"', 'href="?window=1"',
     "test_the_template_offers_exactly_the_windows_the_module_declares"),

    # BUG-6. The old assertion was `peak <= _nice_top(peak)` restated, so it
    # could not fail; it now reads rendered coordinates at the boundary.
    ("#452/BUG-6: a bar segment is drawn past the axis floor",
     "src/astro_ai/templates/admin_ops.html",
     '''height="{{ '%.3f'|format(h) }}"''',
     '''height="{{ '%.3f'|format(h * 1.5) }}"''',
     "test_no_bar_can_overflow_the_axis"),

    # #449. The socket guard in tests/conftest.py is a defect fix whose proof is
    # that it bites, and every one of these is a way it could silently stop.
    # Each anchors on a line of the GUARD, never on a test. Not mutated, on
    # purpose: dropping the `connect` patch makes the self-test's refused
    # connect a REAL one (a SYN to TEST-NET-3), and a harness that emits packets
    # to prove a suite does not is the wrong shape.
    ("#449: the guard stops recording a refused lookup (a swallowed OSError passes)",
     "tests/conftest.py",
     '        violations.append(f"getaddrinfo({host!r})")',
     "        pass",
     "test_a_non_loopback_lookup_and_connect_are_refused_and_recorded"),

    ("#449: the guard stops recording a refused connect",
     "tests/conftest.py",
     '        violations.append(f"connect({address[0]!r})")',
     "        pass",
     "test_a_non_loopback_lookup_and_connect_are_refused_and_recorded"),

    ("#449: the teardown assertion is gone (the guard only raises, and is swallowed)",
     "tests/conftest.py",
     "    assert not violations, (",
     "    assert True or not violations, (",
     "test_a_swallowed_refusal_still_fails_the_test"),

    ("#449: network_allowed opens every host for lookup, not the named one",
     "tests/conftest.py",
     "        if str(host).lower() in allowed_hosts:",
     "        if True:",
     "test_the_marker_opens_only_the_host_it_names"),

    ("#449: network_allowed opens every host for connect, not the named one",
     "tests/conftest.py",
     "or str(host).lower() in allowed_hosts)",
     "or True)",
     "test_the_marker_opens_only_the_host_it_names"),

    # The two tests that reached a live provider. Un-stubbing the shared helper
    # un-stubs both; they pass on their own assertions (the route degrades to
    # "scores still returned"), so ONLY the guard's teardown can catch it.
    ("#449: the /matching nadi tests stop stubbing the provider (live LLM call)",
     "tests/test_nadi_position_coherence.py",
     '    stub_llm("## Compatibility\\n" + "A canned narrative body for the stub. " * 20)',
     "    pass",
     "test_the_scoped_sentence_actually_reaches_the_rendered_panel"),

    # #475. Per-MODEL token accounting and the busiest-minute figure. Each row
    # re-breaks one way the second store could quietly stop being true; the named
    # test is the only one the sweep runs, so a row pointing at the wrong test
    # shows up as MIS-POINTED.
    ("#475: the minute reset is gone (a new minute inherits the last one's total)",
     "src/astro_ai/llm_stats.py",
     '                pk["minute"] = minute\n                pk["tokens"] = 0\n',
     '                pk["minute"] = minute\n',
     "test_the_same_minute_accumulates_and_a_later_minute_resets"),

    ("#475: the peak is the LAST minute, not the max",
     "src/astro_ai/llm_stats.py",
     '                if pk["tokens"] > pk.get("peak", 0):',
     '                if True:',
     "test_the_same_minute_accumulates_and_a_later_minute_resets"),

    ("#475: a late arrival resets the open minute",
     "src/astro_ai/llm_stats.py",
     '            if pk.get("minute") is None or minute > pk["minute"]:',
     '            if pk.get("minute") is None or minute != pk["minute"]:',
     "test_a_late_arrival_neither_resets_nor_inflates_the_open_minute"),

    ("#475: the model store books a silent call as a measurement",
     "src/astro_ai/llm_stats.py",
     '        mm["calls"] = mm.get("calls", 0) + 1\n        sized = prompt_tokens is not None and completion_tokens is not None\n        if sized:\n            mm["measured"] = mm.get("measured", 0) + 1\n',
     '        mm["calls"] = mm.get("calls", 0) + 1\n        sized = prompt_tokens is not None and completion_tokens is not None\n        mm["measured"] = mm.get("measured", 0) + 1\n        if sized:\n',
     "test_a_silent_call_counts_as_a_call_and_touches_no_accumulator"),

    ("#475: the model key loses its provider (two providers share one model name)",
     "src/astro_ai/llm_stats.py",
     '        model_key = f"{provider}|{model}"',
     '        model_key = f"{model}"',
     "test_two_models_on_one_route_make_two_model_rows_and_one_route_row"),

    ("#475: usage_summary SUMS the peak across days (a minute that never happened)",
     "src/astro_ai/llm_stats.py",
     '                if mkey not in model_peak or pk > model_peak[mkey][0]:\n                    model_peak[mkey] = (pk, pm)\n',
     '                if True:\n                    model_peak[mkey] = (pk + model_peak.get(mkey, (0, None))[0], pm)\n',
     "test_across_days_the_peak_is_the_max_and_the_tokens_are_the_sum"),

    ("#475: model_days_recorded counts every day, recorded or not",
     "src/astro_ai/llm_stats.py",
     '        if isinstance(mbm, dict) and mbm:\n            model_days += 1\n',
     '        model_days += 1\n        if isinstance(mbm, dict) and mbm:\n',
     "test_across_days_the_peak_is_the_max_and_the_tokens_are_the_sum"),

    ("#475: the bucket percentage divides by the DAILY limit",
     "src/astro_ai/ops_data.py",
     'row["pct"] = round(row["peak"] / TPM_PER_MODEL * 100)',
     'row["pct"] = round(row["peak"] / TPD_PER_MODEL * 100)',
     "test_the_percentage_is_the_peak_over_the_module_constant"),

    ("#475: a non-Groq provider is scored against Groq's bucket",
     "src/astro_ai/ops_data.py",
     '                if provider.startswith("groq"):',
     '                if True:',
     "test_only_groq_models_get_a_percentage_of_the_groq_bucket"),

    # #475 Phase 1 (S1). The "blocked on bucket" store and column.
    ("#475: record() does not write paced_by_model",
     "src/astro_ai/llm_stats.py",
     '        if isinstance(pacing, dict):\n',
     '        if False:\n',
     "test_record_writes_paced_by_model_and_sums_across_calls"),

    ("#475: a call with no pacing still writes a zeroed paced_by_model entry (silence becomes a zero)",
     "src/astro_ai/llm_stats.py",
     '        if isinstance(pacing, dict):\n',
     '        if True:\n',
     "test_a_call_with_no_pacing_writes_no_key_at_all"),

    ("#475: usage_summary counts every day as a paced day",
     "src/astro_ai/llm_stats.py",
     '        if isinstance(pcd, dict) and pcd:\n            paced_days += 1\n',
     '        paced_days += 1\n        if isinstance(pcd, dict) and pcd:\n',
     "test_usage_summary_sums_pacing_and_counts_only_days_that_carried_it"),

    ("#475: a model with no pacing row reads 0 reserved instead of None",
     "src/astro_ai/llm_stats.py",
     '(paced[key][f] if key in paced else None)',
     '(paced[key][f] if key in paced else 0)',
     "test_a_model_with_no_pacing_row_reports_none_not_zero"),

    ("#475: the panel row drops the wait (wait_s is always 0)",
     "src/astro_ai/ops_data.py",
     'row["wait_s"] = round(int(o.get("wait_ms") or 0) / 1000, 1)',
     'row["wait_s"] = 0',
     "test_model_rows_turn_milliseconds_into_seconds_and_keep_the_counts"),

    ("#475: the panel prints a dash for a measured zero",
     "src/astro_ai/templates/admin_ops.html",
     "{%- if m.reserved is none %}—",
     "{%- if m.reserved is none or not m.wait_s %}—",
     "test_the_page_prints_zero_for_a_measured_zero"),

    # #475 Phase 1 (S2). The per-model token bucket in providers.py.
    ("#475: the bucket level never leaks (a charge is held forever)",
     "src/astro_ai/providers.py",
     "        return max(0.0, self._level - max(0.0, t0 - self._t) * self.rate)\n",
     "        return self._level\n",
     "test_the_level_leaks_with_time"),

    ("#475: an oversize request is not clamped to the bucket's capacity",
     "src/astro_ai/providers.py",
     "        n = min(max(int(tokens), 0), self.cap)\n",
     "        n = max(int(tokens), 0)\n",
     "test_an_oversize_request_is_clamped_and_waits_a_finite_time"),

    ("#475: a DENIED reserve still charges the bucket",
     "src/astro_ai/providers.py",
     "                return None, wait\n",
     "                self._level = level + n\n                self._t = t0\n                return None, wait\n",
     "test_a_denied_reserve_changes_nothing"),

    ("#475: settle ignores what the call actually used",
     "src/astro_ai/providers.py",
     "            self._level = max(0.0, self._level + max(int(actual), 0) - res.tokens)\n",
     "            self._level = max(0.0, self._level)\n",
     "test_settle_shrinks_and_grows_the_charge_and_only_once"),

    ("#475: a 429 keeps its estimate and a timeout is refunded (rule swapped)",
     "src/astro_ai/providers.py",
     "    if isinstance(err, RateLimitError) or (\n            isinstance(status, int) and not isinstance(status, bool) and 400 <= status < 500):\n",
     "    if not (isinstance(err, RateLimitError) or (\n            isinstance(status, int) and not isinstance(status, bool) and 400 <= status < 500)):\n",
     "test_a_429_is_refunded_because_nothing_was_consumed"),

    ("#475: the per-attempt _last_usage/_last_completion reset is removed",
     "src/astro_ai/providers.py",
     "                _last_usage.set(None)\n                _last_completion.set(None)\n",
     "",
     "test_a_later_attempt_is_not_settled_against_an_earlier_calls_figures"),

    ("#475: the pacing sleep happens while holding the bucket lock",
     "src/astro_ai/providers.py",
     "                    _pace_sleep(res.wait_s)\n",
     "                    with bucket._lock:\n                        _pace_sleep(res.wait_s)\n",
     "test_the_bucket_lock_is_free_while_a_caller_sleeps"),

    ("#475: the bucket key drops the provider name (no longer llm_stats' key)",
     "src/astro_ai/providers.py",
     '    return f"{provider.name}|{provider.model()}"\n',
     "    return provider.model()\n",
     "test_the_bucket_key_is_the_key_llm_stats_books_the_call_under"),

    ("#475: every provider is paced, not only Groq",
     "src/astro_ai/providers.py",
     '    return REQUEST_TOKEN_CEILING if host == "api.groq.com" else None\n',
     "    return REQUEST_TOKEN_CEILING\n",
     "test_only_groq_hosts_have_a_known_limit"),

    ("#475: the BHAGYA_TPM_PACING kill switch is ignored",
     "src/astro_ai/providers.py",
     '    return os.environ.get("BHAGYA_TPM_PACING", "1").strip().lower() not in (\n        "0", "false", "off", "no")\n',
     "    return True\n",
     "test_the_kill_switch_restores_the_unpaced_path_exactly"),

    ("#475: a denied reservation proceeds instead of skipping to the next provider",
     "src/astro_ai/providers.py",
     "                res, predicted = bucket.reserve(est, pace_left, force=force)\n",
     "                res, predicted = bucket.reserve(est, pace_left, force=True)\n",
     "test_a_provider_that_would_wait_too_long_is_skipped_before_any_sleep"),

    ("#475: the forced second pass is removed (pacing alone can exhaust the chain)",
     "src/astro_ai/providers.py",
     "        if too_large:\n            return\n        for _wait, p in sorted(",
     "        return\n        for _wait, p in sorted(",
     "test_when_every_provider_is_over_budget_the_call_is_forced_not_failed"),

    ("#475: the acceptance stub can no longer refuse (control must go red)",
     "tests/test_token_bucket.py",
     "LIMIT = 8000\n",
     'LIMIT = float("inf")\n',
     "test_without_the_bucket_the_same_burst_is_rejected"),

    # #475 Phase 1 (QA round 1). The job wait budget reaches chat(), and every
    # provider's pacing reaches llm_stats.
    ("#475: /admin/warm-rashifal stops passing a job deadline (jobs get the 6 s default)",
     "src/astro_ai/routes/subscribe.py",
     "                festival=festivals.festival_for_date(date.today()),\n"
     "                pace_deadline=pace_deadline,\n",
     "                festival=festivals.festival_for_date(date.today()),\n",
     "test_warm_rashifal_passes_a_job_deadline"),

    ("#475: /admin/send-daily-rashifal stops passing the deadline",
     "src/astro_ai/routes/subscribe.py",
     "                    pace_deadline=pace_deadline,\n"
     "                ),\n            )\n            sections_by_lang[lang]",
     "                ),\n            )\n            sections_by_lang[lang]",
     "test_send_daily_shares_ONE_deadline_across_both_languages"),

    ("#475: /admin/send-daily-rashifal computes a deadline PER LANGUAGE (24 calls, two allowances)",
     "src/astro_ai/routes/subscribe.py",
     '    pace_deadline = llm_providers.pace_deadline()\n    for lang in ("en", "hi"):\n',
     '    for lang in ("en", "hi"):\n        pace_deadline = llm_providers.pace_deadline()\n',
     "test_send_daily_shares_ONE_deadline_across_both_languages"),

    ("#475: the welcome email (interactive) is given a job deadline",
     "src/astro_ai/routes/subscribe.py",
     "                festival=festivals.festival_for_date(date.today()),\n            ),\n        )\n        sections = [",
     "                festival=festivals.festival_for_date(date.today()),\n"
     "                pace_deadline=llm_providers.pace_deadline(),\n            ),\n        )\n        sections = [",
     "test_the_welcome_email_is_interactive_and_passes_no_deadline"),

    # Anchor re-pointed for #475 Phase 3: `pacer` sat immediately before
    # `pace_deadline` and both were positional, so deleting the pacer shifted
    # this argument. Dropping the deadline entirely is the same defect the old
    # row caught -- the job silently falls back to the interactive wait budget.
    ("#475: generate_rashifal does not hand the deadline to its pool workers",
     "src/astro_ai/llm.py",
     "                pace_deadline,\n",
     "                None,\n",
     "test_generate_rashifal_hands_each_pool_call_its_own_wait_from_the_deadline"),

    ("#475: _generate_rashifal_single drops the deadline before providers.chat",
     "src/astro_ai/llm.py",
     'max_wait_s=providers.pace_wait_budget(pace_deadline))',
     'max_wait_s=None)',
     "test_generate_rashifal_hands_each_pool_call_its_own_wait_from_the_deadline"),

    ("#475: _generate_rashifal_single ignores the deadline and hands every call the full budget",
     "src/astro_ai/llm.py",
     'max_wait_s=providers.pace_wait_budget(pace_deadline))',
     'max_wait_s=providers.PACE_JOB_BUDGET_S)',
     "test_a_deadline_already_past_gives_every_pool_call_zero"),

    ("#475: the on-demand /rashifal/{rashi} card is given a job deadline (a user waits up to 150 s)",
     "src/astro_ai/llm.py",
     # Anchored on the FIRST argument line alone, and the mutation inserts the
     # kwarg straight after it. An anchor that spanned the call down to its
     # closing paren broke twice in one day as #513 added shape=,
     # opening_move= and gochara_block= between the two ends; keyword
     # arguments may be given in any order, so injecting here is equivalent
     # and cannot be displaced by the next kwarg. The pool call site uses
     # `anchor,` rather than `_RASHI_ANCHORS[rashi_index],`, so this still
     # matches exactly once.
     "        _RASHI_ANCHORS[rashi_index], day_signals_block, transit_block, prompt_path, lang,\n",
     "        _RASHI_ANCHORS[rashi_index], day_signals_block, transit_block, prompt_path, lang,\n"
     "        pace_deadline=providers.pace_deadline(),\n",
     "test_the_on_demand_rashi_card_passes_no_budget"),

    ("#475: pace_wait_budget lets the allowance go negative after the deadline (clamp at 0 dropped)",
     "src/astro_ai/providers.py",
     "    return max(0.0, min(PACE_JOB_BUDGET_S, deadline - _pace_clock()))\n",
     "    return min(PACE_JOB_BUDGET_S, deadline - _pace_clock())\n",
     "test_the_per_call_wait_is_zero_once_the_deadline_has_passed"),

    ("#475: pace_wait_budget drops the per-call cap (a far deadline lets one call wait past the budget)",
     "src/astro_ai/providers.py",
     "    return max(0.0, min(PACE_JOB_BUDGET_S, deadline - _pace_clock()))\n",
     "    return max(0.0, deadline - _pace_clock())\n",
     "test_the_per_call_wait_never_exceeds_the_budget_and_decays_with_the_clock"),

    ("#475: pace_wait_budget ignores the deadline (every call may wait the full budget)",
     "src/astro_ai/providers.py",
     "    return max(0.0, min(PACE_JOB_BUDGET_S, deadline - _pace_clock()))\n",
     "    return PACE_JOB_BUDGET_S\n",
     "test_24_calls_sleep_no_more_than_the_deadline_allows"),

    ("#475: pace_wait_budget measures from a stale clock (the allowance never decays)",
     "src/astro_ai/providers.py",
     "    return max(0.0, min(PACE_JOB_BUDGET_S, deadline - _pace_clock()))\n",
     "    return max(0.0, min(PACE_JOB_BUDGET_S, deadline - (deadline - PACE_JOB_DEADLINE_S)))\n",
     "test_24_calls_sleep_no_more_than_the_deadline_allows"),

    ("#475: pace_deadline ignores the job allowance constant",
     "src/astro_ai/providers.py",
     "    return _pace_clock() + (PACE_JOB_DEADLINE_S if allowance_s is None else allowance_s)\n",
     "    return _pace_clock() + 10_000.0\n",
     "test_the_per_call_wait_never_exceeds_the_budget_and_decays_with_the_clock"),

    ("#475: the job deadline default grows past the Cloud Run timeout's headroom",
     "src/astro_ai/providers.py",
     'os.environ.get("BHAGYA_PACE_JOB_DEADLINE_S", "230")',
     'os.environ.get("BHAGYA_PACE_JOB_DEADLINE_S", "290")',
     "test_the_job_deadline_leaves_headroom_under_the_300s_cloud_run_timeout"),

    ("#475: the job budget constant collapses to the interactive default",
     "src/astro_ai/providers.py",
     'os.environ.get("BHAGYA_PACE_JOB_BUDGET_S", "150")',
     'os.environ.get("BHAGYA_PACE_JOB_BUDGET_S", "6")',
     "test_the_job_budget_is_150_seconds_and_longer_than_the_interactive_default"),

    ("#475: chat() ignores max_wait_s and always uses the interactive default",
     "src/astro_ai/providers.py",
     "    pace_left = RETRY_AFTER_MAX_S if max_wait_s is None else max(0.0, float(max_wait_s))\n",
     "    pace_left = RETRY_AFTER_MAX_S\n",
     "test_the_job_budget_waits_where_the_interactive_default_skips"),

    ("#475: only the SERVING provider's pacing counters reach llm_stats",
     "src/astro_ai/providers.py",
     "pacing={k: dict(v) for k, v in paced.items()} or None,",
     "pacing={_bucket_key(provider): dict(pc)} if pc else None,",
     "test_a_provider_that_waited_then_429d_is_booked_under_its_own_key"),

    ("#475: record() books every provider's pacing under the SERVING model's key",
     "src/astro_ai/llm_stats.py",
     '                pm = data.setdefault("paced_by_model", {}).setdefault(\n                    pkey,',
     '                pm = data.setdefault("paced_by_model", {}).setdefault(\n                    model_key,',
     "test_one_record_call_books_every_model_in_the_mapping_under_its_own_key"),

    ("#475: a skip-only model reads '0 of 0 waited' again on /admin/ops",
     "src/astro_ai/templates/admin_ops.html",
     '{% if m.reserved == 0 and (m.skips or m.forced) %}none admitted{% else %}{{ "{:,}".format(m.waits) }} of {{ "{:,}".format(m.reserved) }} waited{% endif %}',
     '{{ "{:,}".format(m.waits) }} of {{ "{:,}".format(m.reserved) }} waited',
     "test_a_model_that_was_only_skipped_does_not_read_0_of_0_waited"),

    ("#475: a skip is no longer counted (the panel's 'skipped' stays 0)",
     "src/astro_ai/providers.py",
     '                    pc["skips"] += 1\n',
     '                    pc["skips"] += 0\n',
     "test_a_skipped_provider_that_did_not_serve_still_shows_its_skip"),

    # ---- #362 Part A1: the static prompt-contract gate. Two blocks. The first
    # deletes or rewrites ONE sentence of a shipped prompt, inside the sandbox
    # only, and the single contract test must go red: 13 of these left the whole
    # suite at "1084 passed" before the gate existed (measured 2026-10-23), which
    # is the claim this block exists to keep false. The second neuters the gate's
    # own checks, each pointed at the one test that proves it.
    ("#362: ask_matching_third_party loses 'Do NOT tell anyone to marry' (prompt)",
     "src/astro_ai/prompts/ask_matching_third_party.txt",
     "- Do NOT tell anyone to marry, not marry, call it off, or proceed. Give them the reading and leave the decision theirs.\n",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: ask_matching_third_party loses 'a cancelled dosha still scores ZERO' (prompt)",
     "src/astro_ai/prompts/ask_matching_third_party.txt",
     "A cancelled dosha still scores ZERO. A cancellation removes the DOSHA; it never restores the koota's points.\n",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: ask_matching_third_party stops speaking to the concern vs the couple (prompt)",
     "src/astro_ai/prompts/ask_matching_third_party.txt",
     "Answer in the second person about THEIR CONCERN, and in the third person about THE COUPLE.",
     "Answer plainly.",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: ask_matching_third_party gains the first-party framing (prompt, forbid)",
     "src/astro_ai/prompts/ask_matching_third_party.txt",
     "- Do NOT invent a partner for the seeker,",
     "- Speak about \"you and your partner\". Do NOT invent a partner for the seeker,",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: ask_matching loses 'NEVER recalculate a koota' (prompt)",
     "src/astro_ai/prompts/ask_matching.txt",
     "- NEVER recalculate a koota, re-add the total, or estimate a figure you were not given.\n",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: ask_numerology stops declaring its school (prompt, AC3)",
     "src/astro_ai/prompts/ask_numerology.txt",
     "The numerology block is modern Chaldean numerology. It is NOT classical Vedic astrology and it is NOT derived from the chart.",
     "The numerology block is numerology.",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: daily loses 'DO NOT explain WHY' (prompt)",
     "src/astro_ai/prompts/daily.txt",
     "- DO NOT explain WHY a theme is showing up.\n",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    # Starts mid-line: the pre-flight rejects an anchor whose own line begins with `#`.
    ("#362: monthly renames a section heading the route splits on (prompt)",
     "src/astro_ai/prompts/monthly.txt",
     "work decisions.\n\n## Money & Wealth\n",
     "work decisions.\n\n## Money and Wealth\n",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: yearly loses the plain-words rule on planets, signs and houses (prompt)",
     "src/astro_ai/prompts/yearly.txt",
     "- DO NOT name specific planets or signs or natal house numbers.\n",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: dasha_deep_dive loses the one-link rule (prompt)",
     "src/astro_ai/prompts/dasha_deep_dive.txt",
     "Only ONE such link per reading. Do not add links in other sections.",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: matching loses 'DO NOT cite specific koota scores' (prompt)",
     "src/astro_ai/prompts/matching.txt",
     "- DO NOT cite specific koota scores (\"Varna scored 1/1\", \"Nadi scored 0/8\"). The table shows these.\n",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: ask loses 'DO NOT predict death, terminal illness' (prompt)",
     "src/astro_ai/prompts/ask.txt",
     "- DO NOT predict death, terminal illness, specific accidents, or exact dates.\n",
     "",
     "test_every_shipped_prompt_satisfies_its_contract"),

    ("#362: rashifal_single is told to state clock times (prompt)",
     "src/astro_ai/prompts/rashifal_single.txt",
     "- DO NOT state any clock time",
     "- State any clock time",
     "test_every_shipped_prompt_satisfies_its_contract"),

    # The gate's own checks. Each is a defect that would let a prompt rewrite
    # through while the gate printed PASS.
    ("#362: the gate stops noticing a prompt with no row (ships uncontracted)",
     "scripts/verify_prompt_contracts.py",
     "    extra = sorted(on_disk - set(rows))", "    extra = []",
     "test_a_prompt_with_no_row_fails_naming_the_file"),

    ("#362: the gate stops noticing a row for a deleted prompt",
     "scripts/verify_prompt_contracts.py",
     "    stale = sorted(set(rows) - on_disk)", "    stale = []",
     "test_a_row_for_a_deleted_prompt_fails"),

    ("#362: the heading comparison is neutered (a renamed section passes)",
     "scripts/verify_prompt_contracts.py",
     "    if got != want:", "    if False:",
     "test_a_renamed_or_reordered_heading_fails"),

    ("#362: `all` is satisfied by ONE pattern matching (half a rule passes)",
     "scripts/verify_prompt_contracts.py",
     "    missing = [p for p in rule.get(\"all\", []) if not _rx(p).search(text)]\n",
     "    missing = [p for p in rule.get(\"all\", []) if not _rx(p).search(text)]\n    missing = missing if len(missing) == len(rule.get(\"all\", [])) else []\n",
     "test_every_pattern_of_an_all_rule_must_match"),

    ("#362: `same_line` accepts the tokens spread across lines (a dropped list entry passes)",
     "scripts/verify_prompt_contracts.py",
     "        if not any(all(r.search(line) for r in regexes) for line in text.splitlines()):",
     "        if not any(any(r.search(line) for r in regexes) for line in text.splitlines()):",
     "test_same_line_needs_one_line_to_state_every_token"),

    ("#362: the forbid check is neutered (a sibling's framing may leak in)",
     "scripts/verify_prompt_contracts.py",
     "    for pattern in rule.get(\"forbid\", []):", "    for pattern in []:",
     "test_a_forbidden_phrase_fires"),

    ("#362: the pin check is neutered (a rule deleted but echoed elsewhere passes)",
     "scripts/verify_prompt_contracts.py",
     "    if (rule.get(\"all\") or same) and not fails and not pin_lines(text, rule):",
     "    if False:",
     "test_a_rule_whose_words_survive_elsewhere_is_not_pinned"),

    ("#362: a pattern on TWO lines counts as pinned",
     "scripts/verify_prompt_contracts.py",
     "        hit = sorted({_line_of(text, m.start()) for m in _rx(pattern).finditer(text)})\n        if len(hit) == 1:",
     "        hit = sorted({_line_of(text, m.start()) for m in _rx(pattern).finditer(text)})\n        if len(hit) >= 1:",
     "test_a_rule_whose_words_survive_elsewhere_is_not_pinned"),

    ("#362: the covered_by delegate may stop naming natal.txt (natal silently uncovered)",
     "scripts/verify_prompt_contracts.py",
     "    if name not in delegate.read_text(encoding=\"utf-8\"):", "    if False:",
     "test_a_delegate_that_no_longer_names_natal_fails"),

    ("#362: covered_by may be combined with rules (the table pretends to double-cover)",
     "scripts/verify_prompt_contracts.py",
     "    if other:", "    if False:",
     "test_covered_by_cannot_be_combined_with_rules"),

    ("#362: a row that asserts nothing passes (a skip in disguise)",
     "scripts/verify_prompt_contracts.py",
     "    if not rules:", "    if False:",
     "test_a_row_that_declares_nothing_fails"),

    ("#362: a rule that declares no pattern passes",
     "scripts/verify_prompt_contracts.py",
     "    if not any(rule.get(key) for key in _PATTERN_KEYS):", "    if False:",
     "test_a_row_that_declares_nothing_fails"),

    ("#362: a rule with no `why` passes (what breaks if it goes is unrecorded)",
     "scripts/verify_prompt_contracts.py",
     "    if not rule.get(\"why\"):", "    if False:",
     "test_a_rule_with_no_why_fails"),

    ("#362: a bad regex escapes as a traceback instead of a named failure",
     "scripts/verify_prompt_contracts.py",
     "        except re.error as exc:", "        except KeyError as exc:",
     "test_an_invalid_regex_is_a_named_failure_not_a_traceback"),

    ("#362: a misspelt rule key is ignored (the check is silently dropped)",
     "scripts/verify_prompt_contracts.py",
     "    unknown = sorted(set(rule) - _RULE_KEYS)", "    unknown = []",
     "test_a_misspelt_key_is_a_failure_not_a_silently_dropped_check"),

    ("#362: a duplicate rule id is accepted",
     "scripts/verify_prompt_contracts.py",
     "        if rid in seen:", "        if False:",
     "test_an_unknown_group_and_a_duplicate_id_fail"),

    ("#362: a failure no longer names the file (AC2)",
     "scripts/verify_prompt_contracts.py",
     "    head = f\"{name} :: {rid} - \"", "    head = f\"{rid} - \"",
     "test_deleting_any_declared_rule_fails_and_names_the_file_and_the_rule"),

    ("#362: a failure no longer names the rule (AC2)",
     "scripts/verify_prompt_contracts.py",
     "    head = f\"{name} :: {rid} - \"", "    head = f\"{name} :: - \"",
     "test_deleting_any_declared_rule_fails_and_names_the_file_and_the_rule"),

    ("#362: could-not-run exits 0 (an unread table reads as green)",
     "scripts/verify_prompt_contracts.py",
     "the check did not run.\")\n        return 2", "the check did not run.\")\n        return 0",
     "test_a_missing_table_is_exit_two_not_zero"),

    ("#362: a failing gate exits 0",
     "scripts/verify_prompt_contracts.py",
     "            print(f\"  - {f}\")\n        return 1", "            print(f\"  - {f}\")\n        return 0",
     "test_main_exits_one_on_a_failure_and_zero_on_the_shipped_tree"),

    # #475 Phase 1b. The cached-token accounting probe (measure-only). Each row
    # re-breaks one way the probe could report a verdict the data does not
    # support; the CONTROL arm and the isolation rule are what make a verdict
    # mean anything, so most rows attack those.
    ("#475 1b: a cold call (cached 0 or absent) is counted as a warm sample",
     "src/astro_ai/ratelimit_probe.py",
     "        warm = bool(cached)                       # None (absent) and 0 are both cold\n",
     "        warm = True\n",
     "test_a_cold_call_runs_the_same_formula_but_is_never_a_warm_sample"),

    ("#475 1b: the adjacency check is removed (a call begun while another was in flight is scored)",
     "src/astro_ai/ratelimit_probe.py",
     "            adjacent = anchor if anchor is not None and anchor[3] + 1 == s else None\n",
     "            adjacent = anchor\n",
     "test_a_call_that_starts_while_another_is_in_flight_is_not_a_sample_even_if_it_finishes_first"),

    ("#475 1b: the sign of the error is flipped (a discount reads as extra charge)",
     "src/astro_ai/ratelimit_probe.py",
     "        e = exp_i - remaining                     # > 0: Groq charged MORE than predicted\n",
     "        e = remaining - exp_i\n",
     "test_a_header_above_the_prediction_by_most_of_the_cached_count_votes_discounted"),

    ("#475 1b: the verdict no longer requires a cold control",
     "src/astro_ai/ratelimit_probe.py",
     '    if n_w < MIN_WARM or n_c < MIN_COLD or out["f"] is None:\n',
     '    if n_w < MIN_WARM or out["f"] is None:\n',
     "test_verdict_is_insufficient_below_the_sample_floors_and_not_above_them"),

    ("#475 1b: the probe's counters are written into _PREFIX_ZERO (the ninth-key trap)",
     "src/astro_ai/llm_stats.py",
     '"cached_measurable": 0, "reported_unmeasurable": 0}',
     '"cached_measurable": 0, "reported_unmeasurable": 0, "warm_seen": 0}',
     "test_prefix_zero_is_untouched_and_prefix_rows_survive_a_probe_write"),

    ("#475 1b: settle() subtracts cached tokens (the measure-only phase changes the bucket)",
     "src/astro_ai/providers.py",
     "        res.bucket.settle(res, prefix[0] + completion)\n",
     "        res.bucket.settle(res, prefix[0] - (prefix[1] or 0) + completion)\n",
     "test_settle_is_unchanged_a_warm_call_is_still_charged_prompt_plus_completion"),

    ("#475 1b: _last_rl is not reset before an attempt (stale headers scored against the next provider)",
     "src/astro_ai/providers.py",
     "                _last_rl.set(None)\n",
     "                pass\n",
     "test_last_rl_is_reset_before_every_attempt"),

    ("#475 1b: every call makes a SECOND request to read the headers",
     "src/astro_ai/providers.py",
     "    raw = client.chat.completions.with_raw_response.create(**kwargs)\n",
     "    client.chat.completions.with_raw_response.create(**kwargs)\n"
     "    raw = client.chat.completions.with_raw_response.create(**kwargs)\n",
     "test_one_http_request_per_chat_call_and_no_probe_request"),

    ("#475 1b: a failed attempt is forgotten, so the next call is scored against the old anchor",
     "src/astro_ai/ratelimit_probe.py",
     "            _seq[ticket[0]] = _seq.get(ticket[0], 0) + 1\n"
     "            _anchor.pop(ticket[0], None)\n",
     "            _seq[ticket[0]] = ticket[1] - 1\n",
     "test_a_failed_attempt_breaks_the_chain_because_it_may_still_have_been_charged"),

    ("#475 1b: last_limit is summed across days (8,000 reads as 56,000)",
     "src/astro_ai/llm_stats.py",
     '                if not acc["last_limit"]:\n'
     '                    acc["last_limit"] = max(_as_int(r.get("last_limit")), 0)\n',
     '                acc["last_limit"] += max(_as_int(r.get("last_limit")), 0)\n',
     "test_usage_summary_sums_across_days_and_counts_only_days_that_carried_the_key"),

    ("#475 1b: a probe that ran and kept no warm sample prints a dash, not a zero",
     "src/astro_ai/templates/admin_ops.html",
     "          {%- if r.probe is none %}\n",
     "          {%- if not r.warm_n %}\n",
     "test_a_probe_that_ran_and_kept_no_warm_sample_prints_zero_not_a_dash"),

    ("#475 1b: the panel folds cold samples into the warm count",
     "src/astro_ai/ops_data.py",
     '            warm_n, cold_n = n(probe, "warm_n"), n(probe, "cold_n")\n',
     '            warm_n, cold_n = n(probe, "warm_n") + n(probe, "cold_n"), n(probe, "cold_n")\n',
     "test_cold_calls_are_never_folded_into_the_warm_sample_count"),

    # #475 1b, QA round 1: every sentence on the panel is pinned to what it describes.
    ("#475 1b: the fold says a dash always means the probe recorded nothing (false for a seen model with no warm sample)",
     "src/astro_ai/templates/admin_ops.html",
     "beside a quiet cold control. <b>—</b> means there is no figure to show: a row that is one\n"
     "          dash means the probe recorded nothing for the model in this window, and a dash in the\n"
     "          remaining-tokens, mean cached or discounted-fraction cell means the model was seen but no\n"
     "          warm sample was kept to average.",
     "beside a quiet cold control. <b>—</b> means the probe recorded nothing for the model in\n"
     "          this window;",
     "test_the_dash_sentence_is_true_for_both_dash_situations"),

    ("#475 1b: the fold says 'mean error' where the cold control uses the mean ABSOLUTE error",
     "src/astro_ai/templates/admin_ops.html",
     "mean absolute error\n",
     "mean error\n",
     "test_the_threshold_sentences_state_the_whole_rule_from_the_constants"),

    ("#475 1b: the fold drops the vote condition from DISCOUNTED (verdict() still requires it)",
     "src/astro_ai/templates/admin_ops.html",
     " or more and at least\n          {{ \"%d\"|format(RL.vote_min_pct) }}% did, and PARTIAL",
     " or more, and PARTIAL",
     "test_the_threshold_sentences_state_the_whole_rule_from_the_constants"),

    ("#475 1b: verdict() reads DISCOUNTED on the fraction alone (the sentence says the vote is required too)",
     "src/astro_ai/ratelimit_probe.py",
     '    elif out["f"] >= DISCOUNT_MIN_F and out["vote"] >= VOTE_MIN:\n',
     '    elif out["f"] >= DISCOUNT_MIN_F:\n',
     "test_the_threshold_sentences_state_the_whole_rule_from_the_constants"),

    ("#475 1b: the fold reverses the direction another caller of the key pushes the reading",
     "src/astro_ai/templates/admin_ops.html",
     "only make cached tokens look fully charged, never discounted,",
     "only make cached tokens look discounted, never fully charged,",
     "test_the_other_caller_sentence_is_what_the_probe_does"),

    ("#475 1b: a header BELOW the prediction (another caller) votes discounted as well as one above it",
     "src/astro_ai/ratelimit_probe.py",
     '            out["warm_disc"] = 1 if e < -cached * VOTE_CACHED_FRACTION else 0\n',
     '            out["warm_disc"] = 1 if abs(e) > cached * VOTE_CACHED_FRACTION else 0\n',
     "test_the_other_caller_sentence_is_what_the_probe_does"),

    ("#475 1b: the fold stops saying the verdict column is a live reading, not the recorded decision",
     "src/astro_ai/templates/admin_ops.html",
     "The verdict column is a live reading of this window, not the\n"
     "          recorded decision: the row in ARCHITECTURE.md is written by a person after at least\n"
     "          {{ RL.min_warm }} warm and {{ RL.min_cold }} cold samples for the model.\n",
     "",
     "test_the_live_verdict_is_not_the_recorded_decision_and_the_fold_says_so"),

    ("#461: pr-gates stops running on pushes to main, so a red main is invisible",
     ".github/workflows/pr-gates.yml",
     "  push:\n    branches: [main]\n",
     "",
     "test_pr_gates_runs_on_pushes_to_main"),

    ("#461: a main run becomes cancellable again, so the breaking commit leaves no verdict",
     ".github/workflows/pr-gates.yml",
     "  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}\n",
     "  cancel-in-progress: true\n",
     "test_a_main_run_is_not_cancelled_by_the_next_push"),
    ("#461: the red-main reporter tests for `failure`, so a cancelled or timed-out main reports nothing",
     ".github/workflows/main-red-report.yml",
     "      github.event.workflow_run.conclusion != 'skipped'\n",
     "      github.event.workflow_run.conclusion == 'failure'\n",
     "test_the_reporter_fires_on_cancelled_and_timed_out_not_only_on_failure"),

    ("#461: the sentinel is looked up with GitHub search again, which strips `[ ] -` and matches #461 itself",
     ".github/workflows/main-red-report.yml",
     "          sentinels=$(printf '%s' \"$issues\" \\\n"
     "                        | jq -r '[.[] | select(.title | startswith(\"[main-red] \"))] | .[].number')\n",
     "          sentinels=$(gh issue list --repo \"$GH_REPO\" --state open \\\n"
     "                        --search '\"[main-red]\" in:title' \\\n"
     "                        --json number --jq '.[0].number // empty')\n",
     "test_the_sentinel_lookup_does_not_match_the_issue_it_closes"),

    ("#461: the per-SHA dedup drops the backticks, so a bare hex run in the thread silences a real red commit",
     ".github/workflows/main-red-report.yml",
     "            if grep -qF -- \"\\`$short\\`\" <<<\"$bodies\"; then\n",
     "            if grep -qF -- \"$short\" <<<\"$bodies\"; then\n",
     "test_a_bare_hex_run_in_the_thread_does_not_suppress_a_report"),

    # QA round 2 found this one. `grep -q` exits at the first match, the
    # upstream `gh` dies of SIGPIPE, and `pipefail` makes the PIPELINE 141 --
    # so the dedup took the false branch and double-posted. It only shows on a
    # thread bigger than the pipe buffer, which is why the small-fixture
    # idempotence test stayed green while the real thing was broken.
    # QA round 2 found this. `grep -q` exits at the FIRST match, the upstream
    # `gh` then dies of SIGPIPE, and `pipefail` makes the PIPELINE 141 -- so the
    # dedup took the false branch and double-posted a SHA already recorded. It
    # only shows on a thread bigger than the pipe buffer, which is exactly why
    # the small-fixture idempotence test stayed green while the real thing was
    # broken. The mutation has to restore the WHOLE piped form: an earlier
    # attempt only added `| cat` inside the command substitution, where nothing
    # exits early, and was measured MISSED.
    ("#461: the dedup reads the thread through a pipe again, so pipefail + grep -q double-posts",
     ".github/workflows/main-red-report.yml",
     '            bodies=$(gh issue view "$existing" --repo "$GH_REPO" \\\n'
     '                       --json body,comments \\\n'
     "                       --jq '[.body] + [.comments[].body] | .[]')\n"
     '            # The backticks are part of the match, so a bare hex run elsewhere\n'
     '            # in the thread cannot suppress a real report.\n'
     '            if grep -qF -- "\\`$short\\`" <<<"$bodies"; then\n',
     '            if gh issue view "$existing" --repo "$GH_REPO" \\\n'
     '                 --json body,comments \\\n'
     "                 --jq '[.body] + [.comments[].body] | .[]' \\\n"
     '                 | grep -qF -- "\\`$short\\`"; then\n',
     "test_the_dedup_survives_a_large_comment_thread"),

    ("#461: a green main stops closing the sentinel, so a stale one collects the next unrelated red main",
     ".github/workflows/main-red-report.yml",
     "              gh issue close \"$n\" --repo \"$GH_REPO\"\n",
     "",
     "test_a_green_main_closes_the_open_sentinel"),

    ("#461: only the first open sentinel is closed on green, leaving the rest stale",
     ".github/workflows/main-red-report.yml",
     "            for n in $sentinels; do\n",
     "            for n in $(printf '%s' \"$sentinels\" | head -n 1); do\n",
     "test_every_open_sentinel_is_closed_not_just_the_first"),

    ("#461: the dedup reads comments only, so the SHA that OPENED the sentinel is reported twice",
     ".github/workflows/main-red-report.yml",
     '                       --json body,comments \\\n'
     "                       --jq '[.body] + [.comments[].body] | .[]')\n",
     "                       --json comments --jq '.comments[].body')\n",
     "test_the_sha_that_opened_the_sentinel_is_not_reported_twice"),

    ("#461: the first sentinel is taken through a pipe into `head`, the same pipefail+SIGPIPE class",
     ".github/workflows/main-red-report.yml",
     "          existing=${sentinels%%$'\\n'*}\n",
     '          existing=$(printf \'%s\' "$sentinels" | head -n 1)\n',
     "test_no_pipeline_feeds_an_early_exiting_reader"),

    ("#461: the reporter moves back inside pr-gates, where it cannot report its own job being killed",
     ".github/workflows/pr-gates.yml",
     "permissions:\n  contents: read\n",
     "permissions:\n  contents: read\n  issues: write\n",
     "test_pr_gates_has_no_reporter_step_and_cannot_write_issues"),

    # ---- #604 / #602: two guards that read plausible state and did not guard.
    # Both are the class #550 round 5 belonged to: the input is well formed and
    # means something other than what the code assumed, so nothing errors.
    ("#604: needs-human-review stops holding a PR on the edge-triggered path",
     ".github/workflows/agent-merge.yml",
     '            *,needs-human-review,*)\n'
     '              echo "::notice::needs-human-review is set',
     '            *,never-matches-any-label,*)\n'
     '              echo "::notice::needs-human-review is set',
     "test_needs_human_review_blocks_the_edge_triggered_path"),

    ("#602: an empty head SHA reaches the runs query, so GitHub returns every run in the repo",
     ".github/workflows/agent-work.yml",
     "          sha=${sha:-$(git rev-parse HEAD)}\n",
     "          sha=${sha}\n",
     "test_an_empty_head_sha_never_reaches_the_query"),
    # --- #384: the merge-conflict marker gate -------------------------------
    # ARCHITECTURE.md reached main carrying a live conflict block and all 27
    # gates passed over it. These rows are the properties of the gate that
    # replaced that silence; each one, broken, is a marker that ships again.
    #
    # THREE OF THESE REPLACE ROWS THAT PINNED THE BLINDNESS AS CORRECT. The
    # first version matched exactly seven marker characters and read file
    # content from the working tree, and had a row asserting that a wider run
    # must PASS -- so the suite would have gone red on the fix. A mutation row
    # is only as good as the premise under it.
    ("#384: the scanner drops git's diff3/zdiff3 base marker",
     "scripts/verify_conflict_markers.py",
     "DIRECTIONAL_CHARS = (OURS[0], BASE[0], THEIRS[0])",
     "DIRECTIONAL_CHARS = (OURS[0], THEIRS[0])",
     "test_the_diff3_base_marker_alone_turns_the_gate_red"),

    ("#384: the width goes back to EXACTLY seven, which `conflict-marker-size` defeats",
     "scripts/verify_conflict_markers.py",
     "        if len(run) >= MARKER_MIN:\n",
     "        if len(run) == MARKER_MIN:\n",
     "test_a_real_conflict_at_a_non_default_width_turns_the_gate_red"),

    ("#384: a wide run stops counting even with a same-width companion beside it",
     "scripts/verify_conflict_markers.py",
     "        if w == MARKER_MIN or len(chars_at_width[w]) > 1:\n",
     "        if w == MARKER_MIN:\n",
     "test_a_wide_block_is_caught_once_its_companion_is_there"),

    # Pointed at the CONTEXT test, not the setext one. A file holding only a
    # separator never reaches `markers()` -- the pre-filter in `scan()` looks
    # for the directional characters first -- so the setext test could not see
    # this mutation at all. Measured, not assumed: the row read MISSED until it
    # was repointed and the context test taught to count.
    ("#384: the separator becomes a trigger, so every setext heading blocks a PR",
     "scripts/verify_conflict_markers.py",
     "        if ch == SEPARATOR_CHAR:\n            continue\n",
     "        if False:\n            continue\n",
     "test_the_separator_is_reported_as_context_in_a_condemned_file"),

    ("#384: the gate reads the working tree again instead of the staged content",
     "scripts/verify_conflict_markers.py",
     "        data = content.get(sha)\n",
     "        data = (root / rel).read_bytes() if (root / rel).exists() else None\n",
     "test_the_gate_reads_the_index_not_the_working_tree"),

    # NO ROW FOR `stage != "0"`, and the absence is deliberate. Dropping that
    # filter reads like a gate and is not one: an unmerged path's stage 1/2/3
    # blobs are the PRE-merge sides, which carry no markers -- the markers exist
    # only in the working tree while the merge is live. Scanning the extra
    # stages therefore reports nothing new, the named test stays green, and the
    # row would have been a row that pins nothing. The filter stays for the
    # duplicate-path count it prevents; `test_an_unmerged_index_entry_is_skipped
    # _not_reported` documents the behaviour without pretending to gate it.

    ("#384: a condemned file no longer reports the separator line as context",
     "scripts/verify_conflict_markers.py",
     "        for n, line in separators(texts[rel]):\n",
     "        for n, line in []:\n",
     "test_the_separator_is_reported_as_context_in_a_condemned_file"),

    ("#384: the gate stops noticing that it excluded its own source from the scan",
     "scripts/verify_conflict_markers.py",
     "if mine and mine in tracked_files(root) and mine not in scanned:",
     "if mine and mine in tracked_files(root) and False:",
     "test_a_gate_that_excluded_its_own_source_exits_two"),
    # #573. The dispatch was unconditional, so EVERY cycle attached a second
    # `PR gates` run to the head SHA -- the one run agent-merge dedups to as
    # the latest, and the one run its `if:` refuses as a trigger (#352). The
    # last check to go green became the one check that cannot wake a merge.
    ("#573: agent-work dispatches pr-gates even when the SHA already has a run",
     ".github/workflows/agent-work.yml",
     '\n          if [ "$gates_runs" -gt 0 ]; then\n',
     "\n          if false; then\n",
     "test_an_existing_pr_gates_run_is_not_given_a_second_one"),

    # The `set -e` trap that made publish_measurements.sh's retry path
    # unreachable, in the same shape: `x=$(failing_cmd)` as a standalone
    # command carries that command's status and ends the script.
    ("#573: the poll's gh api failure ends the step instead of falling to the #322 rescue",
     ".github/workflows/agent-work.yml",
     "              2>/dev/null || echo 0)\n",
     "              2>/dev/null)\n",
     "test_an_unreadable_answer_falls_toward_the_rescue"),
    ("#387 notify: the owner's alert parses visitor text as Markdown again",
     "src/astro_ai/notify.py",
     '        "disable_web_page_preview": True,',
     '        "parse_mode": "Markdown",\n        "disable_web_page_preview": True,',
     "test_the_telegram_payload_asks_for_no_parse_mode"),

    ("#387 notify: the 'no name' placeholder is Markdown italics again",
     "src/astro_ai/notify.py",
     "f\"👤 {name or '(no name)'}\",",
     "f\"👤 {name or '_(no name)_'}\",",
     "test_no_formatter_emits_markup_or_escapes"),

    ("#387 notify: an unguarded inlined field prints the word None",
     "src/astro_ai/notify.py",
     "system={system or ''}\"",
     "system={system}\"",
     "test_a_missing_field_is_blank_not_the_word_none"),

    # --- #429: the Manglik severity ladder is editorial, and says so ----------
    ("#429: the checker credits the severity ladder to four unheld books again",
     "src/astro_ai/templates/manglik_check_result.html",
     "<strong>Basis:</strong>",
     "<strong>Classical basis:</strong> Manglik Dosh rules are compiled from Jataka Parijata, Phaladeepika, Jataka Chandrika, and Muhurtha Chintamani (per P.V.R. Narasimha Rao's Jagannath Hora rule-set).",
     "test_checker_page_names_no_unheld_book_as_the_basis"),

    ("#429: the checker stops saying the ladder is Bhagya's editorial weighting",
     "src/astro_ai/templates/manglik_check_result.html",
     "is Bhagya's own editorial weighting, not a classical grading",
     "is graded as follows",
     "test_checker_page_discloses_that_the_ladder_is_editorial"),

    ("#429: the LLM severity line presents the ladder as graded doctrine again",
     "src/astro_ai/chart.py",
     "an internal weighting of the qualifying \"\n        \"houses",
     "graded from the qualifying \"\n        \"houses",
     "test_llm_severity_line_does_not_present_the_ladder_as_classical"),

    ("#429: the LLM severity line hands the model the word 'editorial'",
     "src/astro_ai/chart.py",
     "an internal weighting of the qualifying \"",
     "an editorial weighting of the qualifying \"",
     "test_llm_severity_line_does_not_invite_the_model_to_say_editorial"),

    ("#429: the 1st-house grade moves (the tier decision is the owner's, not a side effect)",
     "src/astro_ai/chart.py",
     "    elif {1, 4, 12} & qualifying:",
     "    elif {4, 12} & qualifying:",
     "test_severity_grades_are_unchanged"),

    # --- #429: the matching page's severity sentence says the ladder is Bhagya's own ---
    ("#429 matching: the severity sentence presents the ladder as graded doctrine again",
     "src/astro_ai/matching.py",
     '"Severity here is an internal weighting, not a classical grade: counting "\n    "the houses Mars occupies from the Lagna, the Moon and Venus, 7th or 8th "',
     '"Severity here is graded from the houses Mars occupies counted from the "\n    "Lagna, the Moon and Venus: 7th or 8th "',
     "test_every_severity_note_discloses_the_ladder_is_not_classical"),

    ("#429 matching: the severity sentence hands the model the word 'editorial'",
     "src/astro_ai/matching.py",
     '"Severity here is an internal weighting, not a classical grade: counting "',
     '"Severity here is an editorial weighting, not a classical grade: counting "',
     "test_severity_note_does_not_invite_the_model_to_say_editorial"),

    ("#429 matching: the sentence says the 2nd house is moderate, the ladder says low",
     "src/astro_ai/matching.py",
     "2nd alone low",
     "2nd alone moderate",
     "test_sentence_ladder_agrees_with_compute_manglik_details"),

    ("#429 matching: the sentence drops the Venus-axis downgrade the ladder applies",
     "src/astro_ai/matching.py",
     "when only the Venus-axis count qualifies.",
     "when counted from any axis.",
     "test_sentence_still_states_the_venus_axis_downgrade_and_its_three_frames"),

    # --- #398 slice 10: the Manglik cancellations stop naming books nobody here holds ---
    ("#398 s10: the exalted-Mars cancellation is credited to Jataka Parijata again",
     "src/astro_ai/chart.py",
     'description="Mars exalted in Capricorn",\n            effect="cancels",\n            source=_MANGLIK_SRC_SIGN,',
     'description="Mars exalted in Capricorn",\n            effect="cancels",\n            source="Jataka Parijata",',
     "test_no_manglik_rule_names_a_book_the_repo_does_not_hold"),

    ("#398 s10: the Jupiter-aspect cancellation is credited to Phaladeepika again",
     "src/astro_ai/chart.py",
     'description="Jupiter aspects Mars (primary classical Mangal Dosha cancellation)",\n            effect="cancels",\n            source=_MANGLIK_SRC_REPEATED,',
     'description="Jupiter aspects Mars (primary classical Mangal Dosha cancellation)",\n            effect="cancels",\n            source="Phaladeepika",',
     "test_no_manglik_rule_names_a_book_the_repo_does_not_hold"),

    # --- #398 slice 11: the Manglik checker stops claiming every classical cancellation rule ---
    ("#398 s11: the /manglik-check lead claims every classical cancellation rule again",
     "src/astro_ai/routes/dosha.py",
     '    "Instant Mangal Dosh diagnosis from your birth details. It checks the "',
     '    "Instant Mangal Dosh diagnosis from your birth details, with every classical cancellation rule applied. It checks the "',
     "test_no_page_claims_the_checker_applies_every_cancellation_rule"),

    ("#398 s11: /matching claims the FULL classical evaluation again",
     "src/astro_ai/templates/matching.html",
     'Bhagya\'s matching goes beyond "Mars',
     'Bhagya\'s matching applies the FULL classical evaluation, not just "Mars',
     "test_no_page_claims_the_checker_applies_every_cancellation_rule"),

    ("#398 s11: /kundli claims all classical cancellation rules applied again",
     "src/astro_ai/templates/kundli_landing.html",
     "checked against the cancellations commonly listed",
     "all classical cancellation rules applied; checked against the cancellations commonly listed",
     "test_no_page_claims_the_checker_applies_every_cancellation_rule"),

    ("#398 s11: /about says Bhagya applies every cancellation rule again",
     "src/astro_ai/templates/about.html",
     "Bhagya applies the ones it implements",
     "Bhagya applies them all",
     "test_no_page_claims_the_checker_applies_every_cancellation_rule"),

    ("#398 s11: the result page's guide card promises every classical cancellation rule again",
     "src/astro_ai/templates/manglik_check_result.html",
     "Depth: the six qualifying houses, the cancellation rules the tradition repeats",
     "Depth: all six qualifying houses, every classical cancellation rule, the cancellation rules the tradition repeats",
     "test_the_result_page_makes_no_such_claim_either"),

    ("#398 s11: the checker lead names a rule the code does not implement instead of the Cancer/Leo one",
     "src/astro_ai/routes/dosha.py",
     "a Cancer or Leo ascendant",
     "a strong Moon aspecting Mars",
     "test_the_checker_lead_and_meta_name_only_rules_the_code_implements"),

    # --- #398 slice 12: the tithi characters are labelled, not deleted ---
    # `knowledge/vedic_reference.md` §29.8 called the Chaturthi row "the
    # sharpest tension §29 found between shipped copy and the corpus" and
    # recommended saying BOTH rather than deleting either. These rows re-break
    # that resolution on each of the three surfaces it landed on.
    ("#398 tithi: the prompt presents the table as classical again",
     "src/astro_ai/prompts/rashifal_single.txt",
     'Tithi character. The CHARACTERS below are POPULAR ASSOCIATION, NOT A CLASSICAL RULE\n(§29.10) — use one only if it fits, never as what the texts prescribe. The explicit\ncautions ARE sourced, and you may state them:\n',
     "Tithi character (reference in the reading only if it genuinely fits):\n",
     "test_the_prompt_does_not_present_the_table_as_classical"),

    ("#398 tithi: the prompt tells the reader to start things on the 4th again",
     "src/astro_ai/prompts/rashifal_single.txt",
     "- Chaturthi \u2192 Ganesh energy, removing obstacles. NOT a day to start things.\n",
     "- Chaturthi \u2192 Ganesh energy, start small things, remove obstacles\n",
     "test_the_prompt_does_not_tell_the_reader_to_start_things_on_the_fourth"),

    ("#398 tithi: the prompt drops the 8th's caution",
     "src/astro_ai/prompts/rashifal_single.txt",
     "- Ashtami \u2192 Durga/Shakti, courage, inner resolve. NOT a day to launch or decide.\n",
     "- Ashtami \u2192 Durga/Shakti, courage, focused action\n",
     "test_the_prompt_cautions_the_eighth_too"),

    ("#398 tithi: /panchang says start small things again",
     "src/astro_ai/chart.py",
     '    "Chaturthi":   ("Ganesh day \u2014 removing obstacles; a Rikta tithi, so the texts "\n                    "we hold do not favour starting new work on it"),\n',
     '    "Chaturthi":   "Ganesh day \u2014 remove obstacles, start small things",\n',
     "test_panchang_says_both_on_the_fourth"),

    ("#398 tithi: /panchang restores 'focused action' on the 8th",
     "src/astro_ai/chart.py",
     '    "Ashtami":     ("Durga/Shakti themes — courage, protection, inner resolve; "\n                    "Raman places the 8th on his avoid list for new "\n                    "undertakings, though Rao\'s table recommends it"),\n',
     '    "Ashtami":     "Durga/Shakti themes \u2014 courage, protection, focused action",\n',
     "test_panchang_drops_focused_action_on_the_eighth"),


    ("#398 tithi: the /panchang explainer calls the characters classical again",
     "src/astro_ai/templates/panchang.html",
     "Some tithis carry widely-held popular characters",
     "Some tithis have specific classical characters",
     "test_the_panchang_explainer_does_not_call_the_characters_classical"),

    ("#398 tithi: the 8th is called settled classical doctrine again",
     "src/astro_ai/chart.py",
     '"Raman places the 8th on his avoid list for new "',
     '"also on the classical avoid list for new "',
     "test_the_eighth_is_attributed_rather_than_called_settled"),

    ("#398 tithi: a leaked internal section marker stops being caught",
     "src/astro_ai/rashifal_quality.py",
     '    "cites a document section": re.compile(r"\u00a7\\s*\\d"),',
     '    "cites a document section": re.compile(r"ZZZ_NEVER_MATCHES"),',
     "test_a_reading_that_leaks_an_internal_section_marker_is_caught"),
    ("#398 tithi: the knowledge ledger claims this is still uncorrected",
     "src/astro_ai/knowledge/vedic_reference.md",
     "**CORRECTED 2026-10-30 (#398), by saying both rather than deleting either**",
     "**Flagged, not corrected** \u2014 the resolution is probably to say both",
     "test_the_knowledge_ledger_no_longer_says_flagged_not_corrected"),
    # --- #450: single-flight on the two live caches. Each row removes ONE
    # piece of the serialisation; the suite must notice every piece. --------
    ("#450: the backlog read is not serialised (N cold renders spend N)",
     "src/astro_ai/ops_data.py",
     "    with _live_lock:\n        return _live_issues_locked(objective)",
     "    return _live_issues_locked(objective)",
     "test_concurrent_cold_backlog_reads_spend_one_request"),

    ("#450: the today read is not serialised (N cold renders spend N)",
     "src/astro_ai/ops_data.py",
     "    with _today_lock:\n        return _live_today_locked(day_start, day)",
     "    return _live_today_locked(day_start, day)",
     "test_concurrent_cold_today_reads_spend_one_renders_worth"),

    ("#450: the backlog waiter does not re-check the cache once it has the lock",
     "src/astro_ai/ops_data.py",
     "    hit = _issues_fresh(now)\n    if hit:\n        return hit[1]\n    try:",
     "    try:",
     "test_concurrent_cold_backlog_reads_spend_one_request"),

    ("#450: the today waiter does not re-check the cache once it has the lock",
     "src/astro_ai/ops_data.py",
     "    hit = _today_fresh(day, now)\n    if hit:\n        return hit[2]\n    try:",
     "    try:",
     "test_concurrent_cold_today_reads_spend_one_renders_worth"),

    ("#450: the two caches share one lock (a slow backlog read blocks the tiles)",
     "src/astro_ai/ops_data.py",
     "_today_lock = threading.Lock()",
     "_today_lock = _live_lock",
     "test_one_cache_being_filled_does_not_block_the_other"),

    ("#450: the today lock is taken and never released (a waiter hangs)",
     "src/astro_ai/ops_data.py",
     "    with _today_lock:\n        return _live_today_locked(day_start, day)",
     "    _today_lock.acquire()\n    return _live_today_locked(day_start, day)",
     "test_a_failing_first_today_read_is_cached_and_the_lock_released"),
    # --- #607: every agent definition says where its output goes ---
    # The rule was stated once in CLAUDE.md, pointed at a gitignored file, and
    # 12 of 15 definitions ended up with no instruction to write anywhere
    # durable. These rows re-break each class so the gate cannot rot back out.
    ("#607 trail: an agent definition loses the output-goes section",
     ".claude/agents/engineer.md",
     "  `>>` only \u2014 never `>`, never Write, never Edit on that file.\n\n## Where your output goes",
     "  `>>` only \u2014 never `>`, never Write, never Edit on that file.\n\n## Notes",
     "test_every_agent_names_where_its_output_goes"),

    # The SYMMETRIC row. Its absence is why the issue-side check shipped
    # near-vacuous: `"issue" in block` was always true because the section
    # heading says "the issue is durable". QA on #609 inverted an agent's
    # issue instruction, left the heading intact, and the gate said `ok`.
    ("#607 trail: an agent names the PR but not the issue",
     ".claude/agents/infra-lead.md",
     "**On the issue:**",
     "Keep it in your own output:",
     "test_every_agent_names_both_the_issue_and_the_pr"),

    ("#607 trail: an agent names the issue but not the PR",
     ".claude/agents/qa.md",
     "**On the PR:** the full verdict comment first, then record the label with",
     "Also, eventually, somewhere: the full verdict comment first, then the label with",
     "test_every_agent_names_both_the_issue_and_the_pr"),

    ("#607 trail: an agent is told the heartbeat file is the record",
     ".claude/agents/architect.md",
     "`AGENT_STATUS.md` is a **local heartbeat only** \u2014 it is gitignored, so nothing in it",
     "`AGENT_STATUS.md` is where the trail belongs \u2014 append to it, and nothing in it",
     "test_no_agent_is_told_the_heartbeat_file_is_the_record"),

    ("#607 trail: CLAUDE.md drops the three-surfaces section",
     "CLAUDE.md",
     "nothing else. Every agent must leave a visible trail.\n\n### The three surfaces",
     "nothing else. Every agent must leave a visible trail.\n\n### Leaving a trail",
     "test_claude_md_no_longer_presents_the_gitignored_file_as_the_record"),


    # --- #461 round 5: the marker gate and the concurrency block ---
    # Both are load-bearing and neither had a row. QA deleted the whole
    # `concurrency:` block and all 65 tests stayed green.
    ("#461 r5: the marker gates the RED path too, silencing every red main",
     ".github/workflows/main-red-report.yml",
     '          if [ "$CONCLUSION" = success ]; then\n            if [ "$asserted" = "absent" ]; then',
     '          if true; then\n            if [ "$asserted" = "absent" ]; then',
     "test_the_marker_gates_only_the_green_path"),

    ("#461 r5: a green run with no gates closes the sentinel again",
     ".github/workflows/main-red-report.yml",
     '            if [ "$asserted" != "success" ]; then',
     '            if false; then',
     "test_a_green_run_that_skipped_every_gate_does_not_close_the_sentinel"),

    ("#461 r5: the reporter loses its concurrency group",
     ".github/workflows/main-red-report.yml",
     "concurrency:\n  group: main-red-report\n  cancel-in-progress: false\n",
     "",
     "test_the_reporter_is_serialised"),

    # --- verify_workflow_permissions, checks 1 and 2 (#610) ------------------
    # These nine rows carry more weight than most. `chief.md` cites this gate
    # by name as what makes clearing a `.github/workflows/` PR non-circular now
    # that the user widened Shape C to the whole trust boundary, so a hole in
    # either check is not one missing check — it is the only thing between an
    # agent and its own constraints.

    ("wf_permissions: an unknown permissions value ranks as ABSENT, not wide",
     "scripts/verify_workflow_permissions.py",
     'return {"<unparseable>": 2}', 'return {"<unparseable>": 0}',
     "test_an_unrecognised_permissions_shape_ranks_as_WIDE_not_as_absent"),

    ("wf_permissions: a job's own block is written to the top-level key instead",
     "scripts/verify_workflow_permissions.py",
     'if isinstance(job, dict) and "permissions" in job:\n            out[f"jobs.{jid}"] = normalise_perms(job["permissions"])\n        elif top is not _MISSING:',
     'if isinstance(job, dict) and "permissions" in job:\n            out["<top-level>"] = normalise_perms(job["permissions"])\n        elif top is not _MISSING:',
     "test_effective_jobs_resolves_own_then_top_level_then_repo_default"),

    ("wf_permissions: the TRUST_BOUNDARY block never ends, swallowing env keys",
     "scripts/verify_workflow_permissions.py",
     "if len(nxt) - len(nxt.lstrip()) <= indent:", "if False:",
     "test_the_block_ends_at_the_first_line_that_dedents"),

    ("wf_permissions: an unparseable workflow is swallowed instead of failing",
     "scripts/verify_workflow_permissions.py",
     'bad.append(f"{path}: cannot be parsed as YAML ({exc.__class__.__name__}), so its "',
     'pass  # MUTANT: swallow it. The line below is now a bare expression.\n            (',
     "test_check_1_goes_red_rather_than_quiet_on_a_workflow_it_cannot_parse"),

    ("wf_permissions: a brand-new permissions block grants nothing, apparently",
     "scripts/verify_workflow_permissions.py",
     "granted = sorted(k for k, v in a_block.items() if v > 0)",
     "granted = []",
     "test_check_1_goes_red_on_a_permissions_block_that_is_entirely_new"),

    ("wf_permissions: a widened scope is never above the threshold",
     "scripts/verify_workflow_permissions.py",
     "if rank > was:", "if rank > was + 9:",
     "test_check_1_goes_red_when_a_job_block_widens"),

    ("wf_permissions: write-all is compared as a scope name, not as <all>",
     "scripts/verify_workflow_permissions.py",
     'return {"<all>": _SCOPE_RANK.get(block.split("-", 1)[0], 2)}',
     'return {"<all>": 0}',
     "test_check_1_goes_red_on_write_all_replacing_a_narrow_block"),

    ("wf_permissions: TRUST_BOUNDARY compares the diff the wrong way round",
     "scripts/verify_workflow_permissions.py",
     "elif lost := sorted(b_tb - a_tb):", "elif lost := sorted(a_tb - b_tb):",
     "test_check_2_goes_red_when_a_boundary_path_is_removed"),

    ("wf_permissions: a deleted TRUST_BOUNDARY block reads as nothing lost",
     "scripts/verify_workflow_permissions.py",
     "if b_tb and not a_tb:", "if a_tb and not b_tb:",
     "test_check_2_goes_red_when_the_whole_block_disappears"),
    # --- ops/DAG agree on what a failure is (#628) ---------------------------
    # One fact with two consumers. The DAG had the set, `ops_today` did not, so
    # the DAG page read `loop-outcomes` as `reporting` while /admin/ops counted
    # the same runs as loop failures -- for weeks. These rows guard the fix's
    # two halves: the excuse exists, and it is ONE conclusion wide.

    ("#628: the contract excuse covers every conclusion, not just exit 1",
     "src/astro_ai/ops_today.py",
     "if path in CONTRACT_NONZERO and concl == CONTRACT_NONZERO_CONCLUSION:",
     "if path in CONTRACT_NONZERO:",
     "test_loop_outcomes_failing_ANY_OTHER_WAY_still_counts"),

    ("#628: nothing is excused, so a correct loop-outcomes run reads as failed",
     "src/astro_ai/ops_today.py",
     'CONTRACT_NONZERO = frozenset({"loop-outcomes.yml"})',
     "CONTRACT_NONZERO = frozenset()",
     "test_loop_outcomes_exiting_NON_ZERO_is_not_a_loop_failure"),

    ("#628: the excused conclusion is the one that means 'never started'",
     "src/astro_ai/ops_today.py",
     'CONTRACT_NONZERO_CONCLUSION = "failure"',
     'CONTRACT_NONZERO_CONCLUSION = "startup_failure"',
     "test_the_excused_conclusion_is_one_value_not_a_range"),

    ("#628: the DAG goes back to its own literal, free to drift again",
     "scripts/build_agent_cycle_dag.py",
     "from astro_ai.ops_today import CONTRACT_NONZERO  # noqa: E402",
     'CONTRACT_NONZERO = {"loop-outcomes.yml"}',
     "test_both_surfaces_read_the_SAME_object"),
    # --- chief clears the whole trust boundary (#610) ------------------------
    # The grant's two halves are the label being READ at all (nothing read it
    # before, so `chief.md` documented a release that did not happen) and the
    # ruling being bound to a SHA (an unbound label cost this repo #609 and
    # #564 in one week). A hole in either turns "chief has merge authority"
    # into "any label merges a boundary PR".

    ("#610: the ruling is matched without its SHA, so it survives a push",
     ".github/workflows/agent-merge.yml",
     'contains(\\"chief-cleared at $PR_SHA\\")',
     'contains(\\"chief-cleared\\")',
     "test_a_ruling_on_a_DIFFERENT_commit_does_not_release"),

    ("#610: a non-numeric comment count falls toward RELEASING the hold",
     ".github/workflows/agent-merge.yml",
     "case \"$ruled\" in ''|*[!0-9]*) ruled=0 ;; esac",
     "case \"$ruled\" in ''|*[!0-9]*) ruled=1 ;; esac",
     "test_a_NON_NUMERIC_comment_count_keeps_the_hold"),

    ("#610: the label alone releases the hold, with no ruling comment",
     ".github/workflows/agent-merge.yml",
     'if [ "$ruled" -gt 0 ]; then',
     'if [ "$ruled" -ge 0 ]; then',
     "test_the_label_ALONE_does_not_release"),

    ("#610: chief-cleared is never recognised, so the grant does nothing",
     ".github/workflows/agent-merge.yml",
     "*,chief-cleared,*)", "*,chief-was-here,*)",
     "test_chief_releases_the_hold_on_EVERY_boundary_path"),

    ("#610: a judge-only round is refused again, so no workflow PR gets a verdict",
     ".github/workflows/qa-on-green.yml",
     "            judge_only=true\n", "            exit 0\n",
     "test_a_workflow_touching_diff_IS_JUDGED_and_no_longer_declined"),

    ("#610: judge-only becomes the DEFAULT, so no cycle ever pushes again",
     ".github/workflows/qa-on-green.yml",
     "          judge_only=false\n", "          judge_only=true\n",
     "test_judge_only_defaults_to_false_before_anything_tests_the_diff"),

    ("#610: the flag never reaches the dispatch comment",
     ".github/workflows/qa-on-green.yml",
     "          JUDGE_ONLY: ${{ steps.pick.outputs.judge_only }}\n", "",
     "test_the_dispatch_comment_receives_the_flag_as_an_env_var"),

    ("#610: the no-push rule leaves agent-cycle.md and lives only in a PR comment",
     ".claude/commands/agent-cycle.md",
     "you cannot push to this branch", "you probably cannot push to this branch",
     "test_the_RULE_lives_in_agent_cycle_md_and_the_comment_only_reminds"),

    ("#610: the boundary step stops depending on `size`, bypassing gates and QA",
     ".github/workflows/agent-merge.yml",
     "        id: boundary\n        if: steps.size.outputs.ok == 'true'",
     "        id: boundary\n        if: always()",
     "test_the_release_block_sits_AFTER_the_gate_chain_steps"),

    ("#610: the hold comment names only the human route, hiding chief's",
     ".github/workflows/agent-merge.yml",
     'echo "1. \\`chief\\` rules on it', 'echo "1. Someone rules on it',
     "test_the_hold_comment_tells_the_reader_about_the_chief_route"),

    # --- effective-permissions check 1, after the independent round (#610) ---
    # The first draft compared DECLARED blocks, so a new job with no block of
    # its own inherited `agent-merge.yml`'s whole write set and the gate printed
    # PASS -- live on the shipped file, with 8 workflows exposed. These rows
    # guard the fix and the two false reds fixed alongside it.

    ('#610: check 1 reverts to declared blocks, so an inheriting job is invisible',
     "scripts/verify_workflow_permissions.py",
     '            after = effective_jobs(yaml.safe_load(a_txt))',
     '            after = perm_blocks(yaml.safe_load(a_txt))',
     'test_a_NEW_JOB_WITH_NO_BLOCK_inheriting_a_broad_top_level_is_caught'),

    ('#610: a workflow declaring no permissions ranks as granting nothing',
     "scripts/verify_workflow_permissions.py",
     '            out[f"jobs.{jid}"] = {REPO_DEFAULT: 2}',
     '            out[f"jobs.{jid}"] = {}',
     'test_a_NEW_WORKFLOW_declaring_no_permissions_anywhere_is_caught'),

    ('#610: the <all> fallback is dropped, so tightening write-all reds falsely',
     "scripts/verify_workflow_permissions.py",
     '    if "<all>" in block:\n        return block["<all>"]',
     '    if False:\n        return block["<all>"]',
     'test_TIGHTENING_write_all_to_a_narrow_mapping_is_not_a_false_red'),

    ('#610: no usable base returns 0 instead of 2 -- did-not-run reads as passed',
     "scripts/verify_workflow_permissions.py",
     '        print("This is NOT a pass: an unverified diff may be granting a power.")\n        return 2\n    try:',
     '        print("This is NOT a pass: an unverified diff may be granting a power.")\n        return 0\n    try:',
     'test_no_usable_base_exits_2_and_says_it_is_NOT_a_pass'),

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


# Where each named test lives, computed ONCE. `pytest tests -k NAME` imports
# every test module before it can filter, and that import is most of the cost:
# measured on this tree, `pytest tests -k NAME` is 0.96s against 0.66s for
# `pytest tests/the_file.py::NAME`, and the difference is collection, not the
# test. Across 467 rows that is ~140s of pure import, repeated.
#
# A name that is ambiguous or missing falls back to the whole directory, so the
# map can only ever make the run FASTER, never change its verdict. All 467
# named tests resolve uniquely on this tree; the fallback is for the row added
# next week that does not.
_TEST_FILE_CACHE: dict[str, str] | None = None


def _test_nodeid(sandbox: pathlib.Path, test: str) -> list[str]:
    """pytest args selecting one test as narrowly as the tree allows."""
    global _TEST_FILE_CACHE
    base = test.split("[", 1)[0]
    if _TEST_FILE_CACHE is None:
        found: dict[str, list[str]] = {}
        for f in sorted((ROOT / "tests").rglob("test_*.py")):
            try:
                body = f.read_text(errors="replace")
            except OSError:
                continue
            for name in re.findall(r"^def (test_\w+)\(", body, re.M):
                found.setdefault(name, []).append(f.relative_to(ROOT).as_posix())
        _TEST_FILE_CACHE = {k: v[0] for k, v in found.items() if len(v) == 1}
    rel = _TEST_FILE_CACHE.get(base)
    if rel and (sandbox / rel).exists():
        return [str(sandbox / rel), "-k", base]
    return [str(sandbox / "tests"), "-k", base]


def _sandbox_env() -> dict:
    """Parent env plus the repo's .env, which the sandbox cannot discover."""
    env = dict(os.environ)
    # A stale __pycache__ surviving a restore would serve the next row the
    # MUTATED module; see _worker_sandbox.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    dotenv = ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip("\"'"))
    return env


# ONE SANDBOX PER WORKER, not one per row. Each row used to build its own
# temporary tree: 5 directories, ~700 files, 14 MB, measured at 0.233s a copy,
# which across 467 rows is ~109s of pure file copying inside a step that takes
# 545s in CI. A worker reuses its tree and restores the single file it mutated,
# because a row mutates exactly one file and the sandbox is thread-local.
#
# THE ISOLATION PROPERTY IS PRESERVED, and it is the only thing that matters
# here. The original design note is still right -- "a sandbox removes the
# failure mode rather than handling it. There is no restore path to get wrong,
# and no signal that can beat it" -- and that argument was about the REPOSITORY,
# which is still never touched. What is reused is a throwaway copy under
# tempfile, so a missed restore can corrupt one worker's scratch tree and
# nothing a human owns.
#
# A missed restore would still be a silent gate failure, so it does not depend
# on `finally` alone: the file's original bytes are captured before the write
# and compared after the restore, and a mismatch retires that sandbox rather
# than handing it to the next row. And the CONTROL row is the end-to-end
# canary it always was -- a no-op edit that does NOT report MISSED means the
# harness has stopped measuring, whatever the cause.
#
# PYTHONDONTWRITEBYTECODE is set in the sandbox env for the same reason: a
# stale __pycache__ surviving a restore would serve the mutated module to the
# next row.
_SANDBOXES = threading.local()


@contextlib.contextmanager
def _worker_sandbox():
    """This thread's sandbox tree, built once and kept for the run."""
    existing = getattr(_SANDBOXES, "path", None)
    if existing is not None and existing.exists():
        yield existing
        return
    tmp = tempfile.mkdtemp(prefix="mutate-")
    _SANDBOX_DIRS.append(tmp)
    sandbox = pathlib.Path(tmp) / "repo"
    for sub in _SANDBOX_SUBDIRS:
        shutil.copytree(ROOT / sub, sandbox / sub,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                      "worktrees"))
    # ROOT-LEVEL FILES TOO (#607). The loop above copies directories, so until
    # now nothing at the repo root existed in the sandbox -- and that is the
    # same hole `.claude` had before 2026-10-25, with the same two
    # consequences the comment below records: a row naming `CLAUDE.md` dies
    # with FileNotFoundError, and any test that READS it fails to import in
    # the sandbox, which reports rc=2 on every row INCLUDING CONTROL and
    # blinds the whole harness. Observed on PR #609: one bad row made the
    # sweep print "CONTROL FAILED -- every verdict above is worthless".
    for f in _SANDBOX_FILES:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, sandbox / f)
    _SANDBOXES.path = sandbox
    yield sandbox


_SANDBOX_DIRS: list[str] = []
# `.claude` is here because in THIS repo the agent definitions and slash
# commands are load-bearing behaviour, not configuration: the whole autonomous
# loop is prose in `.claude/agents/*.md` and `.claude/commands/*.md`, nothing
# type-checks it, and until 2026-10-25 no mutation row could reach it -- a row
# naming one of those files died with FileNotFoundError and, worse, any test
# that READ one failed to import in the sandbox, which reports rc=2 on every
# row including CONTROL and blinds the whole harness.
#
# `worktrees` is excluded in the copy above and that exclusion is load-bearing:
# `.claude/worktrees/` is untracked scratch space holding git worktrees, 4.2 GB
# of it when this was measured, and copying it per sandbox would make the sweep
# unrunnable rather than merely slow.
_SANDBOX_SUBDIRS = ("src", "tests", ".github", "scripts", "measurements", ".claude")
# Repo-root FILES the sandbox needs. `CLAUDE.md` is load-bearing behaviour in this
# repo the same way `.claude/` is -- it is loaded into every session, several gates
# and tests read it, and a mutation row targeting it could not run at all before
# #607. Keep this list short: every entry is copied into every worker sandbox.
_SANDBOX_FILES = ("CLAUDE.md",)


def _drop_worker_sandbox() -> None:
    """Retire this thread's tree so the next row builds a clean one."""
    path = getattr(_SANDBOXES, "path", None)
    _SANDBOXES.path = None
    if path is not None:
        shutil.rmtree(path.parent, ignore_errors=True)


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
    with _worker_sandbox() as sandbox:
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
        # (the tree itself is built once per worker — see _worker_sandbox)
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
        try:
            return _probe(sandbox, rel, target, test)
        finally:
            # Restore, then PROVE the restore. A sandbox that cannot be put
            # back is retired rather than reused: handing a still-mutated tree
            # to the next row would report CAUGHT for a defect nobody tested.
            try:
                target.write_text(source)
                restored = target.read_text() == source
            except OSError:
                restored = False
            if not restored:
                _drop_worker_sandbox()


def _probe(sandbox, rel: str, target, test: str) -> tuple[bool, str]:
    """Run the suite against an already-mutated sandbox."""

    def _pytest(*extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "pytest", str(sandbox / "tests"),
             "-q", "--no-header", *extra],
            capture_output=True, text=True, cwd=sandbox, env=_sandbox_env(),
        )

    def _red(r: subprocess.CompletedProcess) -> bool:
        """A real assertion failure, not a collection error.

        A non-zero exit from a collection error looks like a catch and is
        worth nothing, which is why this reads the output and not just the
        code. pytest exits 5 on "no tests matched", which is neither.
        """
        #
        # A TEARDOWN error counts, and has to: the socket guard (#449) fails
        # a test whose body PASSED, so its only signal is `1 passed, 1
        # error` and a line `ERROR path::test`. A collection error has no
        # `::` in its line, so it is still not a catch.
        return r.returncode not in (0, 5) and (
            "FAILED" in r.stdout or "failed" in r.stdout
            or re.search(r"^ERROR \S+::", r.stdout, re.M) is not None)

    # EVERY ROW ALREADY NAMES THE TEST THAT MUST CATCH IT, so run that test
    # and not the other 766. Measured 2026-10-20 on this tree: one named
    # test is 0.34s against 19.5s for the whole suite, and this step was
    # 80% of every pr-gates run (1054s and 673s on two consecutive runs,
    # 191 rows x a full suite / 4 workers).
    #
    # It is also a STRICTER question than the one asked before. "The suite
    # goes red" and "THIS test goes red" are different claims, and each row
    # asserts the second -- the `test` field is not decoration, the
    # GUARD GONE check above already treats it as load-bearing.
    #
    # So the fast path can only ever CONFIRM a catch. It can never create a
    # failure, because a named test that stays green falls through to the
    # full suite below, exactly as before.
    if test and test != "_control":
        # Narrowed to the test's own FILE where the name resolves uniquely;
        # see _test_nodeid. Same question, less import.
        fast = subprocess.run(
            [sys.executable, "-m", "pytest", *_test_nodeid(sandbox, test),
             "-q", "--no-header"],
            capture_output=True, text=True, cwd=sandbox, env=_sandbox_env(),
        )
        if _red(fast):
            return True, "CAUGHT"

    # Reached when the named test did not catch it, or for the control row,
    # which must see the whole suite or it would stop being a control.
    result = _pytest()
    if result.returncode == 0:
        return False, "*** MISSED ***"
    if not _red(result):
        return False, f"NON-TEST FAILURE rc={result.returncode}"
    if test and test != "_control":
        # NEW INFORMATION, and it was invisible before: something caught the
        # mutation but not the test this row names. The row still counts as
        # caught -- the defect cannot escape -- but its `test` field is
        # wrong, and a wrong field is what the GUARD GONE check cannot see.
        return True, "CAUGHT BY ANOTHER TEST — row names `" + test + "`"
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

# STATIC ANCHOR PRE-FLIGHT (#418/F7). Claimed in two PR comments -- "a static
# anchor validator now runs over every 5-tuple", upgraded to "zero rows anchor
# on a comment" -- and it was in neither the repo nor any workflow. QA round 4
# looked for it and reported the quoted counts as unreproducible. So it is built
# here rather than claimed again.
#
# WHY STATIC AND AHEAD OF THE SWEEP. `_run_in_sandbox` already reports
# ANCHOR MISSED, but only per row, only at run time, and only for uniqueness --
# so a bad anchor costs a full sandboxed suite run before it says so, and an
# anchor sitting on a COMMENT passes it completely. A row anchored on a comment
# mutates prose: it changes no behaviour, so it reports MISSED for a defect that
# is in fact guarded, and the row silently stops being a gate. One did, for two
# QA rounds (#ops-today's clock-killed run), and that is this log's recurring
# subject.
#
# Cheap: pure text, no subprocess, no suite. It runs before anything is spent.
def _preflight_anchors() -> list[str]:
    problems: list[str] = []
    for label, rel, old, new, test in MUTATIONS:
        path = ROOT / rel
        if not path.exists():
            problems.append(f"{label}: {rel} does not exist")
            continue
        # THE SANDBOX MUST CONTAIN IT (#607). Existing in the repo is not
        # enough: the sweep runs each row in a copy that holds only
        # `_SANDBOX_SUBDIRS` plus `_SANDBOX_FILES`, so a row naming anything
        # else dies with FileNotFoundError mid-sweep -- and, worse, a TEST
        # that reads such a path fails to import in the sandbox, which reports
        # rc=2 on every row including CONTROL and blinds the whole harness.
        # Observed on PR #609, where one such row made the sweep print
        # "CONTROL FAILED -- every verdict above is worthless" after 40
        # minutes. This check is free and says so before anything is spent.
        top = pathlib.PurePosixPath(rel).parts[0]
        if top not in _SANDBOX_SUBDIRS and rel not in _SANDBOX_FILES:
            problems.append(
                f"{label}: {rel} is outside the sandbox — the sweep copies "
                f"{list(_SANDBOX_SUBDIRS)} and {list(_SANDBOX_FILES)}, so this "
                f"row cannot run. Add it to _SANDBOX_FILES/_SANDBOX_SUBDIRS or "
                f"drop the row deliberately.")
            continue
        src = path.read_text(encoding="utf-8")
        n = src.count(old)
        if n != 1:
            problems.append(f"{label}: anchor matches {n}x in {rel}, need exactly 1")
            continue
        if old == new:
            problems.append(f"{label}: the mutant is identical to the anchor")
        # The anchor must not BEGIN on a comment line: mutating prose changes no
        # behaviour, so such a row cannot ever catch anything.
        #
        # Read off the anchor's OWN resolved position, never by scanning the file
        # for its first line. The scanning version rejected 65 of 243 rows: any
        # line anywhere that merely CONTAINED the anchor's first line satisfied
        # `first in line`, so a comment quoting a line of code condemned the row
        # that mutates it -- and the pre-flight exits before the sweep, so it was
        # a false positive in the blocking direction, in the validator added to
        # stop exactly this class of mistake. `old` is already known to occur
        # EXACTLY ONCE (checked above), so its position is not a search.
        at = src.index(old)
        bol = src.rfind("\n", 0, at) + 1
        eol = src.find("\n", at)
        line = src[bol:eol if eol != -1 else len(src)]
        if line.lstrip().startswith(("#", "//", "<!--")):
            problems.append(
                f"{label}: anchor begins on a COMMENT line in {rel} -- mutating "
                f"prose changes no behaviour, so this row cannot ever catch "
                f"anything: {line.strip()[:70]}")
    return problems


_anchor_problems = _preflight_anchors()
if _anchor_problems:
    print(f"ANCHOR PRE-FLIGHT FAILED - {len(_anchor_problems)} row(s), "
          f"nothing was run:")
    for _p in _anchor_problems:
        print(f"  {_p}")
    print("\nA row whose anchor is wrong is not a weak gate, it is no gate. Fix")
    print("the anchor or remove the row deliberately; do not let the sweep")
    print("spend a sandboxed suite run per row to tell you the same thing.")
    raise SystemExit(1)
print(f"anchor pre-flight: {len(MUTATIONS)} rows -- every anchor resolves exactly "
      f"once, differs from its mutant, and does not begin on a comment line")

if "--preflight-only" in sys.argv:
    # The pre-flight is a gate in its own right, it runs BEFORE the sweep, and it
    # can fail the whole run on its own -- so it has to be checkable without
    # paying for a sandboxed suite run per row. This module cannot be imported to
    # test it (there is no __main__ guard; importing starts the sweep), so the
    # only way in is argv. Used by tests/test_mutation_preflight.py.
    raise SystemExit(0)

# --- DIFF SCOPING: fewer rows on a PR, every row on main ---------------------
#
# The remaining cost is pytest start-up, ~0.66s that every row pays and no
# narrowing removes. The only way past it is running fewer rows, and that is a
# GATE RELAXATION, not an optimisation -- so it is opt-in, it is loud about
# what it skipped, and `main` never uses it.
#
# WHAT IT ASSUMES, stated so it can be argued with: for a file a PR does not
# touch, whether its guard can still go red was proven by the last full sweep
# on main and nothing in the PR changed it. That holds only if the PR also did
# not touch the TEST, so a row is selected when EITHER its mutated file or its
# named test's file is in the diff. The second half is the one that matters --
# a PR deleting a guard must still hit that row's GUARD GONE check.
#
# FOUR ESCAPE HATCHES, all of which run everything:
#   * the diff cannot be computed (no base, not a repo, git failed)
#   * this harness itself changed -- it decides what is proven
#   * tests/conftest.py changed -- shared fixtures reach every row
#   * pyproject.toml / uv.lock changed -- the interpreter under every row
# Failure falls back to the FULL sweep. A scoping bug must cost time, never
# coverage.
#
# The CONTROL is never scoped out. A run that skips it cannot tell whether it
# is measuring anything at all.
_ALWAYS_FULL = ("scripts/mutate_behaviour_suite.py", "tests/conftest.py",
                "pyproject.toml", "uv.lock")


def _changed_files(base: str) -> list[str] | None:
    """Paths changed against `base`, or None if that cannot be answered."""
    try:
        r = subprocess.run(["git", "diff", "--name-only", base, "HEAD"],
                           capture_output=True, text=True, cwd=ROOT, timeout=60)
        if r.returncode != 0:
            return None
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception:  # noqa: BLE001 - see _ALWAYS_FULL
        return None


def _scope_rows(base: str) -> tuple[list, str]:
    """(rows to run, one line saying why). Falls back to every row."""
    changed = _changed_files(base)
    if changed is None:
        return list(MUTATIONS), f"could not diff against {base!r} — running every row"
    if not changed:
        return list(MUTATIONS), f"no changes against {base!r} — running every row"
    hit = sorted(set(changed) & set(_ALWAYS_FULL))
    if hit:
        return list(MUTATIONS), f"{', '.join(hit)} changed — running every row"

    changed_set = set(changed)
    # Build the name -> test file map the same way the fast path does.
    test_file: dict[str, str] = {}
    seen: dict[str, int] = {}
    for f in sorted((ROOT / "tests").rglob("test_*.py")):
        rel_f = f.relative_to(ROOT).as_posix()
        for name in re.findall(r"^def (test_\w+)\(", f.read_text(errors="replace"), re.M):
            seen[name] = seen.get(name, 0) + 1
            test_file.setdefault(name, rel_f)

    picked = []
    for row in MUTATIONS:
        _label, rel, _old, _new, test = row
        base_name = (test or "").split("[", 1)[0]
        tf = test_file.get(base_name) if seen.get(base_name) == 1 else None
        # An unresolvable test name selects the row rather than dropping it.
        if rel in changed_set or tf is None or tf in changed_set:
            picked.append(row)
    return picked, (f"{len(changed)} file(s) changed against {base!r} — "
                    f"{len(picked)} of {len(MUTATIONS)} rows touch them "
                    f"(by mutated file or by named test's file)")


_scope_base = ""
for _i, _a in enumerate(sys.argv):
    if _a == "--changed-since" and _i + 1 < len(sys.argv):
        _scope_base = sys.argv[_i + 1]
if _scope_base:
    _rows, _why = _scope_rows(_scope_base)
    print(f"scope: {_why}")
    if len(_rows) < len(MUTATIONS):
        print("       rows for untouched files were proven by the last full "
              "sweep on main; this is a PR-only narrowing, never used there")
else:
    _rows = list(MUTATIONS)

_work = [_CONTROL] + _rows
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
mispointed: list[str] = []
for label, verdict in rows:
    if verdict.startswith("CAUGHT BY ANOTHER TEST"):
        # CAUGHT, so it does NOT count as bad: the defect cannot escape, which
        # is what this harness is for. What is wrong is the row's `test` field,
        # and that is reported separately below rather than turning the gate
        # red -- a speed change may not invent failures, or nobody will trust
        # the number it prints.
        mispointed.append(f"{label} -> {verdict}")
    elif verdict != "CAUGHT":
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
if mispointed:
    print()
    print(f"{len(mispointed)} row(s) are MIS-POINTED: the mutation was caught, but not by")
    print("the test the row names. The protection is real; the bookkeeping is wrong,")
    print("and until 2026-10-20 this was invisible because every row ran the whole")
    print("suite and any failure read as CAUGHT.")
    for line in mispointed:
        print(f"  - {line}")
if not control_ok:
    print()
    print("CONTROL FAILED — the sandbox reports CAUGHT for an edit that changes")
    print("nothing, so every verdict above is worthless. Fix the sandbox before")
    print("believing any number this printed.")
sys.exit(0 if control_ok and caught == real else 1)
