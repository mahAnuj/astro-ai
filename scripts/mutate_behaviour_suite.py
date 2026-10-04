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
     "test_expired_entry_under_concurrency_does_not_raise"),

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
     "        if is_htmx:\n            return HTMLResponse(\n                _reading_error_fragment(canonical_slug, True, _cool_msg),\n                status_code=503,\n            )",
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
     "      {%- if panchang_strip.daylight_ordinary %}\n\n      <div class=\"flex items-center gap-1 min-w-0\">\n        <span class=\"text-red-700",
     "      {%- if True %}\n\n      <div class=\"flex items-center gap-1 min-w-0\">\n        <span class=\"text-red-700",
     "test_surface_hides_daylight_windows_when_there_is_no_daylight[homepage strip]"),

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


def _run_in_sandbox(rel: str, old: str, new: str) -> tuple[bool, str]:
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


rows = []
control_ok = True
for label, rel, old, new, _test in [_CONTROL] + list(MUTATIONS):
    ok, verdict = _run_in_sandbox(rel, old, new)
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
