"""#1167 slice 2 -- the chart summary on each `form_ask` event.

Each row re-breaks one property and names the test that must go red. The first two are the
privacy rows: the owner ruled the event never stores birth date, time or place, and a longitude
or a timezone in the snapshot would let a reader recover them."""

_ASK = "src/astro_ai/routes/ask.py"

MUTATIONS = [
    ("#1167: the snapshot gains each planet's longitude (pins the birth time to minutes)",
     _ASK,
     '{p.name: {"rashi": p.rashi, "house": p.house}',
     '{p.name: {"rashi": p.rashi, "house": p.house, "longitude": p.longitude}',
     "test_the_snapshot_holds_no_birth_detail_in_any_form"),
    ("#1167: the snapshot gains the birth timezone (a place proxy)",
     _ASK,
     '        "lagna": chart.lagna_rashi,\n',
     '        "lagna": chart.lagna_rashi,\n        "tz": chart.birth_tz,\n',
     "test_the_snapshot_has_exactly_the_allow_listed_keys_and_values"),
    ("#1167: the form_ask event stops carrying the chart",
     _ASK,
     '        _event_data["chart"] = chart_snapshot(chart, dasha)\n',
     '        _event_data.pop("chart", None)\n',
     "test_a_fresh_generation_records_the_snapshot_and_no_birth_detail"),
    ("#1167: the snapshot is built only on a fresh generation, so a cache hit has none",
     _ASK,
     '        _event_data["chart"] = chart_snapshot(chart, dasha)\n',
     '        if not was_cached:\n            _event_data["chart"] = chart_snapshot(chart, dasha)\n',
     "test_a_cache_hit_records_the_snapshot_too"),
    ("#1167: the try/except around the snapshot is removed (a failure now loses the answer)",
     _ASK,
     '    except Exception:  # noqa: BLE001 — events are best-effort\n'
     '        log.debug("chart snapshot for form_ask event failed", exc_info=True)\n',
     '    except ZeroDivisionError:  # noqa: BLE001 — events are best-effort\n'
     '        log.debug("chart snapshot for form_ask event failed", exc_info=True)\n',
     "test_a_snapshot_failure_still_answers_and_records_without_a_chart_key"),
]
