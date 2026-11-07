"""#762: Swiss Ephemeris keeps its sidereal mode PER THREAD, so a chart computed off the
thread that imported `chart` used Fagan-Bradley, 0.883 deg larger than Lahiri.

Starlette runs a plain `def` route on a worker thread, `hot_cache` refreshes on a
`threading.Thread` and the rashifal job fans out over a `ThreadPoolExecutor`, so the
claim worth testing is "the same moment gives the same sky on every thread". The
TestClient serves requests on a portal thread, so before this fix the whole behaviour
suite computed Fagan-Bradley and nothing could notice.
"""
from __future__ import annotations

import ast
import dataclasses
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

import swisseph as swe

from astro_ai import chart

SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
MUMBAI = (19.076, 72.8777, "Asia/Kolkata")


def _on_worker(fn):
    out: list = []
    err: list = []

    def run():
        try:
            out.append(fn())
        except BaseException as e:  # pragma: no cover - surfaced below
            err.append(e)

    t = threading.Thread(target=run)
    t.start()
    t.join()
    assert not err, err
    return out[0]


def _chart_longitudes():
    c = chart.compute_chart("1990-04-12", "14:35", "Mumbai, India")
    return c.lagna_longitude, [dataclasses.asdict(p) for p in c.planets]


def test_chart_is_identical_on_main_and_worker_thread(monkeypatch):
    monkeypatch.setattr(chart, "geocode_place", lambda place: MUMBAI)
    main = _chart_longitudes()
    worker = _on_worker(_chart_longitudes)
    assert main[0] == worker[0]
    assert main[1] == worker[1]


def test_worker_thread_reads_the_lahiri_ayanamsa():
    # swe.get_ayanamsa_ut reports the mode the CALLING thread selected; the helper's
    # job is to have selected Lahiri there before any sidereal call.
    jd = 2448000.0
    lahiri = swe.get_ayanamsa_ut(jd)  # main thread: configured by chart's import

    def probe():
        chart._sid_calc_ut(jd, swe.SUN)
        return swe.get_ayanamsa_ut(jd)

    assert abs(_on_worker(probe) - lahiri) < 1e-9
    assert abs(lahiri - 23.7215) < 0.01


def test_panchang_and_month_naming_agree_across_threads(monkeypatch):
    from astro_ai import adhik_maas

    monkeypatch.setattr(chart, "geocode_place", lambda place: MUMBAI)

    def panchang():
        c = chart.compute_chart("1990-04-12", "14:35", "Mumbai, India")
        p = chart.compute_panchang(c, datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc))
        return dataclasses.asdict(p)

    assert panchang() == _on_worker(panchang)
    jd = swe.julday(2026, 4, 14, 0.0)  # near a sankranti: rashi is ayanamsa-sensitive
    assert adhik_maas._sun_rashi(jd) == _on_worker(lambda: adhik_maas._sun_rashi(jd))


def test_no_module_calls_sidereal_swisseph_directly():
    """Every sidereal call must go through `_sid_calc_ut` / `_sid_houses`, which are the
    only places the per-thread mode is selected. A new `swe.calc_ut(..., FLG_SIDEREAL)`
    elsewhere would silently regress #762 on whatever thread it runs on."""
    offenders = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            if fn.name in {"_sid_calc_ut", "_sid_houses"}:
                continue
            src = ast.get_source_segment(path.read_text(), fn) or ""
            if re.search(r"swe\.(houses_ex|houses)\(", src):
                offenders.append(f"{path.name}:{fn.name} swe.houses*")
            for call in ast.walk(fn):
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "calc_ut"
                        and "FLG_SIDEREAL" in ast.dump(call)):
                    offenders.append(f"{path.name}:{fn.name} calc_ut(FLG_SIDEREAL)")
    assert not offenders, offenders
