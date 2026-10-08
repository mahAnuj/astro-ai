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
        # to check that its jq field reads still match what /health emits. A
        # sandbox missing a file the suite reads makes EVERY mutation look
        # CAUGHT — including the control, which is how this was noticed.
        for sub in ("src", "tests", ".github"):
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
