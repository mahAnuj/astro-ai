"""#1272: the kundli-submissions export counts fresh generations and marks probes."""

MUTATIONS = [
    ("#1272: a day with no events at all is exported as 0 generations, not unknown",
     "scripts/collect_kundli_submissions.py",
     "        if any_events[d] == 0 or any_events[d] >= cap:\n",
     "        if any_events[d] >= cap:\n",
     "test_a_day_with_no_events_at_all_is_null_not_zero"),
    ("#1272: the form_kundli event stops carrying the probe marker",
     "src/astro_ai/routes/kundli.py",
     '                "probe": probe.is_probe(request),\n',
     '',
     "test_a_probe_request_marks_the_form_kundli_event"),
    ("#1272: is_probe loosens to any non-empty header, so a forged value marks a probe",
     "src/astro_ai/probe.py",
     "        return request.headers.get(PROBE_HEADER) == PROBE_VALUE\n    except Exception:\n"
     "        # No `.headers`, a mapping that raises",
     "        return bool(request.headers.get(PROBE_HEADER))\n    except Exception:\n"
     "        # No `.headers`, a mapping that raises",
     "test_is_probe_is_an_exact_match_and_never_raises"),
    ("#1272: a mixed marked/unmarked day reports a partial probe split instead of unknown",
     "scripts/collect_kundli_submissions.py",
     '        marked = all(isinstance((e.get("data") or {}).get("probe"), bool) for e in ks)\n',
     '        marked = any(isinstance((e.get("data") or {}).get("probe"), bool) for e in ks) or not ks\n',
     "test_a_day_mixing_marked_and_unmarked_events_is_unknown_not_a_partial_split"),
]
