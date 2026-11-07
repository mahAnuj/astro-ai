"""#762 -- swisseph's sidereal mode is per thread, so every sidereal call must select
Lahiri on the CALLING thread. Each row re-breaks one way of losing that."""

_CHART = "src/astro_ai/chart.py"

MUTATIONS = [
    ("#762: the helper stops selecting Lahiri (worker threads fall back to Fagan-Bradley)",
     _CHART,
     "        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)\n        _SID_TLS.lahiri = True",
     "        _SID_TLS.lahiri = True",
     "test_chart_is_identical_on_main_and_worker_thread"),
    ("#762: the 'already configured' flag is process-wide, so only the first thread selects Lahiri",
     _CHART,
     "_SID_TLS = threading.local()",
     "_SID_TLS = type('G', (), {})()",
     "test_worker_thread_reads_the_lahiri_ayanamsa"),
    ("#762: compute_chart calls swe.houses_ex directly again (lagna off by 0.88 deg on workers)",
     _CHART,
     "    _, ascmc = _sid_houses(julian_day, lat, lon)\n    asc_long = float(ascmc[0])  # sidereal ascendant longitude",
     "    _, ascmc = swe.houses_ex(julian_day, lat, lon, b\"W\", swe.FLG_SIDEREAL)\n    asc_long = float(ascmc[0])  # sidereal ascendant longitude",
     "test_no_module_calls_sidereal_swisseph_directly"),
]
