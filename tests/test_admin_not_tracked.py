"""#735 -- /admin/* must not boot GA4 or Clarity.

An unauthenticated request to /admin/ops gets a 401 that main.py renders from the
generic `error.html`, which extends `base.html`, which wires `analytics.js` with the
site's GA4 id. A browser (or a JS-executing crawler) that renders that body therefore
recorded a session landing on /admin/ops: 19 of 603 sessions in the 28-day export.

`base.html` now blanks both ids on any `/admin` path. These tests render the real
pages through the app and assert on the config blob the browser would receive; the
public-page control proves the ids still reach every other page, so a "fix" that
deletes analytics everywhere cannot pass.
"""
from __future__ import annotations

import re

import pytest

GA4 = "G-TESTADMIN1"
CLARITY = "clarityadmin1"


@pytest.fixture
def tracked_client(client):
    """The test client with both provider ids configured (they are env-driven and
    empty under test, which would make every assertion below vacuous)."""
    from astro_ai.routes import deps

    env = deps.templates.env.globals
    saved = (env.get("ga4_measurement_id"), env.get("clarity_project_id"))
    env["ga4_measurement_id"] = GA4
    env["clarity_project_id"] = CLARITY
    try:
        yield client
    finally:
        env["ga4_measurement_id"], env["clarity_project_id"] = saved


def _config(body: str) -> dict[str, str]:
    m = re.search(r"window\.BHAGYA_ANALYTICS_CONFIG\s*=\s*\{(.*?)\}", body, re.S)
    assert m, "base.html no longer carries the analytics config blob"
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', m.group(1)))


def test_control_public_page_still_carries_the_ids(tracked_client):
    r = tracked_client.get("/")
    assert r.status_code == 200
    assert _config(r.text) == {"ga4": GA4, "clarity": CLARITY}


@pytest.mark.parametrize("path", ["/admin", "/admin/ops", "/admin/activity"])
def test_admin_401_carries_no_provider_id(tracked_client, path):
    r = tracked_client.get(path)
    assert r.status_code == 401
    assert 'Basic realm="Bhagya admin"' in r.headers.get("www-authenticate", "")
    assert _config(r.text) == {"ga4": "", "clarity": ""}
    assert GA4 not in r.text and CLARITY not in r.text


def test_admin_404_carries_no_provider_id(tracked_client):
    r = tracked_client.get("/admin/no-such-page")
    assert r.status_code in (401, 404)
    assert GA4 not in r.text and CLARITY not in r.text


def test_prefix_match_is_a_path_segment_not_a_substring(tracked_client):
    """`/administer` is not an admin route; it must keep tracking."""
    r = tracked_client.get("/administer")
    assert r.status_code == 404
    assert _config(r.text) == {"ga4": GA4, "clarity": CLARITY}
