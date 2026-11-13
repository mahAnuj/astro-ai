"""#433: the Hindi-surface gate's guards, each pinned by a test that dies without it.

Rows target scripts/verify_hindi_surface.py and are driven by
tests/test_hindi_surface_gate.py (a stub server on an ephemeral port, the gate's own
main()). One area file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    # ---- findings 1 and 2: both clauses of the /health identity check, and `revision`
    ("#433/1: the /health identity clause is dropped, so any 200 is this app",
     "scripts/verify_hindi_surface.py",
     "    if probe_code != 200 or not _is_this_app(probe):",
     "    if probe_code != 200:",
     "test_health_200_with_foreign_json_is_not_this_app"),
    ("#433/1: the /health status clause is dropped, so a 503 carrying our JSON is this app",
     "scripts/verify_hindi_surface.py",
     "    if probe_code != 200 or not _is_this_app(probe):",
     "    if not _is_this_app(probe):",
     "test_health_503_with_our_own_json_is_not_a_pass"),
    ("#433/2: `revision` is no longer required, so {ok: true} from anything is this app",
     "scripts/verify_hindi_surface.py",
     '    return isinstance(d, dict) and d.get("ok") is True and "revision" in d',
     '    return isinstance(d, dict) and d.get("ok") is True',
     "test_health_200_with_foreign_json_is_not_this_app"),
    ("#433/2: identity is back to the substring \"ok\", which {status: ok, service: grafana} satisfies",
     "scripts/verify_hindi_surface.py",
     '    return isinstance(d, dict) and d.get("ok") is True and "revision" in d',
     '    return \'"ok"\' in probe',
     "test_health_200_with_foreign_json_is_not_this_app"),
    # ---- finding 3: the PASS line's honesty
    ("#433/3: every page is counted as a 200 in the PASS line, so thirteen 503s claim the floor",
     "scripts/verify_hindi_surface.py",
     "        if code == 200:\n            floored += 1\n",
     "        if True:\n            floored += 1\n",
     "test_the_pass_line_does_not_claim_the_floor_for_pages_that_503"),
    # ---- findings 4 and 7: the empty-<main> guard on a 503
    ("#433/4+7: the empty-<main> guard is exempted on a 503, re-opening the PASS/0 hole",
     "scripts/verify_hindi_surface.py",
     "        if not text.strip():",
     "        if not text.strip() and code == 200:",
     "test_an_empty_main_on_a_503_is_not_a_pass"),
    # ---- findings 4 and 6: a 503 must be Hindi
    ("#433/6: a 503 is held to no Devanagari floor, so <p>Shubh Bhagya</p> passes",
     "scripts/verify_hindi_surface.py",
     "            floor = DEGRADED_FLOOR\n",
     "            floor = 0.0\n",
     "test_a_503_that_is_not_hindi_fails_the_degraded_floor"),
    ("#433/6: DEGRADED_FLOOR is weakened below what a half-English card scores",
     "scripts/verify_hindi_surface.py",
     "DEGRADED_FLOOR = 0.60\n",
     "DEGRADED_FLOOR = 0.05\n",
     "test_a_half_english_503_fails_the_degraded_floor"),
    # ---- finding 5: the nav label is read from the page
    ("#433/5: the nav label is never looked for in the page, so deleting <nav> is green",
     "scripts/verify_hindi_surface.py",
     "            missing_nav += [w for w in NAV_EXPECTED.values() if w not in nav_main]",
     "            pass",
     "test_a_503_needs_no_nav_but_a_200_does"),
    ("#433/5: the nav label is demanded on a 503 too, which renders no nav and so always fails",
     "scripts/verify_hindi_surface.py",
     "        if code == 200:\n            missing_nav +=",
     "        if True:\n            missing_nav +=",
     "test_a_503_needs_no_nav_but_a_200_does"),
    # ---- finding 8: an unreadable page may not discard a real problem
    ("#433/8: an unreadable page returns 2 at once, discarding the leak already collected",
     "scripts/verify_hindi_surface.py",
     "        if code not in (200, 503):\n            unreadable.append(",
     "        if code not in (200, 503):\n            return 2\n            unreadable.append(",
     "test_an_unreadable_page_does_not_discard_a_real_leak"),
    ("#433/8: unreadable pages outrank a found problem, so a FAIL is reported as a skip",
     "scripts/verify_hindi_surface.py",
     "    if problems:\n        return 1\n    if unreadable:\n        return 2\n",
     "    if unreadable:\n        return 2\n    if problems:\n        return 1\n",
     "test_an_unreadable_page_does_not_discard_a_real_leak"),
]
