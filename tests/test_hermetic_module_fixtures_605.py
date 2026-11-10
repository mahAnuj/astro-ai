"""#605: a MODULE-scoped fixture must not reach Nominatim.

`conftest._offline_geocode` is function-scoped, so it has not run when a
module-scoped fixture is built. `test_rashifal_day_detail.py::natal` therefore made
one real geocoding call per run, and a 429 from Nominatim errored `natal` and every
test depending on it (#564 went red on an unrelated diff that way).

These tests read `chart.geocode_place` AS IT IS when a module-scoped fixture is
set up, which is the moment the function-scoped fixture cannot affect. They compare
identity against the real function captured at import, and never call it, so they go
red without themselves touching the network if `_offline_geocode_module` is removed.
"""
import pytest

from astro_ai import chart
from astro_ai.chart import compute_chart

# Collection time: before any fixture has patched anything.
_REAL = chart.geocode_place


@pytest.fixture(scope="module")
def geocode_at_module_setup():
    return chart.geocode_place


@pytest.fixture(scope="module")
def natal_like(geocode_at_module_setup):
    """Mirrors `test_rashifal_day_detail.natal`: a chart built at module scope.

    Refuses to build when the real geocoder is in place, so the red case fails
    here instead of making the request this file exists to forbid.
    """
    if geocode_at_module_setup is _REAL:
        pytest.fail("module-scoped fixture would have called the real geocoder")
    return compute_chart("2000-01-01", "12:00", "Pune, India")


def test_the_real_geocoder_is_not_in_place_when_a_module_fixture_is_built(
        geocode_at_module_setup):
    assert geocode_at_module_setup is not _REAL


def test_the_module_time_geocoder_resolves_a_place_without_the_network(
        geocode_at_module_setup):
    # Identity first: in the red case the call below would be the real request.
    assert geocode_at_module_setup is not _REAL
    assert geocode_at_module_setup("Anywhere, Nowhere") == (
        19.0760, 72.8777, "Asia/Kolkata")


def test_a_module_scoped_chart_builds_offline(natal_like):
    assert natal_like.birth_lat == pytest.approx(19.0760)
    assert natal_like.birth_tz == "Asia/Kolkata"
