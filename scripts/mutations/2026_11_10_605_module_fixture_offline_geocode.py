"""#605: tests/conftest.py's module-scoped `_offline_geocode_module` keeps a module-scoped
fixture (`test_rashifal_day_detail.natal`) off Nominatim; the function-scoped fixture cannot."""

_FIXTURE_DECL = ('@pytest.fixture(scope="module", autouse=True)\n'
                 'def _offline_geocode_module():')
_PATCH = '        mp.setattr(chart, "geocode_place", _stub_geocode_place)\n'

MUTATIONS = [
    # Dropping autouse leaves the fixture defined and unused, which reads as fine in review.
    ("#605: the module-scoped offline fixture loses autouse, so nothing requests it",
     "tests/conftest.py",
     _FIXTURE_DECL,
     '@pytest.fixture(scope="module")\ndef _offline_geocode_module():',
     "test_the_real_geocoder_is_not_in_place_when_a_module_fixture_is_built"),
    ("#605: the module-scoped offline fixture patches nothing",
     "tests/conftest.py",
     _PATCH,
     "        pass\n",
     "test_the_real_geocoder_is_not_in_place_when_a_module_fixture_is_built"),
    # raising=False is what lets a wrong name pass silently; a bare setattr would raise.
    ("#605: the module-scoped offline fixture patches a name `compute_chart` never reads",
     "tests/conftest.py",
     _PATCH,
     '        mp.setattr(chart, "geocode_place_x", _stub_geocode_place, raising=False)\n',
     "test_the_real_geocoder_is_not_in_place_when_a_module_fixture_is_built"),
    ("#605: the module-scoped chart fixture is built while the real geocoder is in place",
     "tests/conftest.py",
     _FIXTURE_DECL,
     '@pytest.fixture(scope="function", autouse=True)\ndef _offline_geocode_module():',
     "test_a_module_scoped_chart_builds_offline"),
]
