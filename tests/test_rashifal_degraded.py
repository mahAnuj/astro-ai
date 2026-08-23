"""What `/rashifal/{rashi}` does when generation goes wrong.

Three defects here, and the expensive ones were not "wrong output" — they were
UNBOUNDED COST and a broken degraded page. Both are invisible to a happy-path
check, which is exactly why they shipped.

`daily_cache` writes real files, so this module redirects it to a tmp dir. It
reads `BHAGYA_DAILY_CACHE_DIR` at import time, so the env var is set before the
module is imported anywhere.
"""
from __future__ import annotations

import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="bhagya-tests-")
os.environ["BHAGYA_DAILY_CACHE_DIR"] = _TMP


@pytest.fixture
def cache(today_iso):
    from astro_ai import daily_cache
    from astro_ai.routes import rashifal

    rashifal._regen_failures.clear()
    yield daily_cache
    rashifal._regen_failures.clear()


def _bad_reading(_n: int) -> str:
    """Raw passes the quality gate; the FIRST SECTION does not.

    This is the shape that caused the loop: `providers.chat` gates `raw`, the
    route stored `sections[0][1]`, so a value that passed on the way in failed
    on the way out and regenerated on every single pageview.
    """
    return "## Aries / Mesha\nToo short.\n\n## Taurus / Vrishabha\n" + ("x" * 1200)


def test_degraded_generation_is_bounded(client, cache, stub_llm, today_iso):
    """Defect: one live LLM call per pageview, per rashi, all day — on the
    quota that had just caused a 21-day outage.

    A first attempt at fixing this added a store-side gate only. That stopped
    bad content being cached but left the cost unbounded: still six
    generations for six requests. The cooldown is the half that bounds it.
    """
    calls = stub_llm(_bad_reading)
    cache.put("rashifal_single", "aries-en", {"body": ""}, today_iso)

    for _ in range(6):
        client.get("/rashifal/aries")

    assert calls["n"] == 1, f"{calls['n']} live generations across 6 requests; expected 1"


def test_healthy_generation_is_cached_not_regenerated(client, cache, stub_llm, today_iso, rashi_body):
    """The cooldown must not cost a healthy rashi anything."""
    calls = stub_llm(lambda _n: rashi_body(heading="Leo / Simha"))
    cache.put("rashifal_single", "leo-en", {"body": ""}, today_iso)

    codes = [client.get("/rashifal/leo").status_code for _ in range(5)]

    assert codes == [200] * 5, codes
    assert calls["n"] == 1, f"{calls['n']} generations; a healthy body must be cached after 1"


def test_cooldown_returns_a_card_not_a_document(client, cache, stub_llm, today_iso):
    """Defect: the cooldown used `raise HTTPException(503)`, which escapes the
    route before `is_htmx` is consulted.

    `base.html` sets `responseHandling: [{"code": ".*", "swap": true}]`, so htmx
    swaps whatever comes back into the flip card — and what came back was the
    entire 81 KB error page, `<head>`, duplicate script tags and all, into a
    card sized for a paragraph.
    """
    stub_llm(_bad_reading)
    cache.put("rashifal_single", "aries-en", {"body": ""}, today_iso)
    client.get("/rashifal/aries")                       # arm the cooldown

    frag = client.get("/rashifal/aries", headers={"HX-Rashifal-Fragment": "1"})

    assert frag.status_code == 503
    assert "<!doctype" not in frag.text.lower(), "a full document is being swapped into the card"
    assert "<html" not in frag.text.lower()
    assert "<head" not in frag.text.lower()
    assert len(frag.text) < 4000, f"fragment is {len(frag.text)} chars; expected a card"
    assert "Try again" in frag.text, "the card must offer a way out"


def test_cooldown_card_does_not_repeat_itself(client, cache, stub_llm, today_iso):
    """Defect: the heading is derived from `is_rate`, and the full sentence was
    ALSO passed as the body, so the card read:

        Still gathering today's sky…
        Still gathering today's sky. Try again in a few minutes.
    """
    import re

    stub_llm(_bad_reading)
    cache.put("rashifal_single", "aries-en", {"body": ""}, today_iso)
    client.get("/rashifal/aries")

    body = client.get("/rashifal/aries", headers={"HX-Rashifal-Fragment": "1"}).text
    heading = re.search(r'font-semibold text-stone-800">([^<]*)<', body).group(1).strip()
    message = re.search(r'text-stone-600 leading-relaxed">([^<]*)<', body).group(1).strip()

    stem = heading.rstrip("…").rstrip(".").strip()
    assert not message.startswith(stem), f"heading repeated in the body: {heading!r} / {message!r}"


def test_full_page_still_gets_the_real_error_page(client, cache, stub_llm, today_iso):
    """The fragment fix must not degrade the standalone page, which is a real
    URL people land on from search."""
    stub_llm(_bad_reading)
    cache.put("rashifal_single", "aries-en", {"body": ""}, today_iso)
    client.get("/rashifal/aries")

    page = client.get("/rashifal/aries")

    assert page.status_code == 503
    assert "<!doctype" in page.text.lower(), "the standalone page must be a full document"


def test_blank_cached_reading_regenerates_once(client, cache, stub_llm, today_iso, rashi_body):
    """Defect (#215): `_shared_three_tier` re-checks quality on every cache hit;
    the per-rashi path did not, so a blank body written once was served all day
    with no healthy retry. Observed in real fixtures with `body: ""`.
    """
    calls = stub_llm(lambda _n: rashi_body(heading="Virgo / Kanya"))
    cache.put("rashifal_single", "virgo-en", {"body": ""}, today_iso)

    first = client.get("/rashifal/virgo")
    second = client.get("/rashifal/virgo")

    assert first.status_code == 200 and second.status_code == 200
    assert calls["n"] == 1, "blank entry must regenerate exactly once, then cache"
    assert (cache.get("rashifal_single", "virgo-en", today_iso) or {}).get("body")
