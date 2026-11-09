"""#463: every /learn `seo_description` fits what a SERP renders, and a gate keeps it so.

Seven descriptions were 161-187 characters once HTML-decoded, and nothing measured them.
The load-bearing detail is the DECODING: `&mdash;` is seven characters raw and one
decoded, and a gate counting the raw source reports a number no SEO tool reproduces
(#451 round 2 called `chandra-moon-remedies` 192; decoded it was 174).

Hermetic: reads the registry and the rendered pages only, no network, no LLM.
"""
from __future__ import annotations

import html
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from astro_ai.learn_registry import ARTICLES

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("verify_seo_copy", ROOT / "scripts" / "verify_seo_copy.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_seo_copy"] = gate
_spec.loader.exec_module(gate)

# The seven that were over the ceiling on main @ 7b7bb90 (161, 162, 162, 174, 161, 187, 166).
SHORTENED = (
    "marriage-timing-kundli",
    "planets-in-7th-house-marriage",
    "ketu-remedies",
    "pitru-dosh-remedies",
    "kaal-sarp-dosh-remedies",
    "manglik-remedies",
    "dhana-yoga-wealth-combinations",
)


def _art(desc="", title="", slug="x"):
    return SimpleNamespace(slug=slug, seo_description=desc, seo_title=title)


def test_no_registered_description_exceeds_160_decoded_characters():
    over = {a.slug: len(html.unescape(a.seo_description)) for a in ARTICLES
            if len(html.unescape(a.seo_description)) > 160}
    assert not over, f"over 160 decoded characters: {over}"


@pytest.mark.parametrize("slug", SHORTENED)
def test_each_shortened_description_is_inside_the_bounds(slug):
    d = html.unescape(next(a for a in ARTICLES if a.slug == slug).seo_description)
    assert 50 <= len(d) <= 160, f"{slug}: {len(d)} chars: {d!r}"


def test_the_gate_passes_on_the_real_registry():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_seo_copy.py")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 outside 50-160" in r.stdout


def test_the_gate_measures_decoded_length_not_raw():
    # 40 entities: 280 raw characters, 40 decoded -- plus 110 plain = 150 decoded.
    raw = "&mdash;" * 40 + "a" * 110
    assert len(raw) > 160 and len(html.unescape(raw)) == 150
    failures, _ = gate.check([_art(raw)])
    assert failures == []


def test_the_gate_fails_a_description_whose_decoded_length_is_over_the_ceiling():
    failures, _ = gate.check([_art("&mdash;" * 10 + "a" * 151, slug="long")])
    assert len(failures) == 1 and "long" in failures[0] and "161" in failures[0]


def test_ceiling_boundary_is_160_inclusive():
    assert gate.check([_art("a" * 160)])[0] == []
    assert len(gate.check([_art("a" * 161)])[0]) == 1


def test_floor_boundary_is_50_inclusive_and_a_stub_fails():
    assert gate.check([_art("a" * 50)])[0] == []
    failures, _ = gate.check([_art("a" * 49, slug="stub")])
    assert len(failures) == 1 and "stub" in failures[0] and "floor" in failures[0]


def test_an_unset_description_is_not_measured():
    # Empty falls back to `summary` by design; the floor is for a description that is set.
    assert gate.check([_art("")])[0] == []


def test_a_long_title_is_reported_but_never_fails():
    failures, advisories = gate.check([_art("a" * 100, title="t" * 70, slug="t")])
    assert failures == [] and len(advisories) == 1 and "t:" in advisories[0]


@pytest.mark.parametrize("slug", SHORTENED)
def test_the_shortened_description_reaches_the_rendered_meta_tag(client, slug):
    art = next(a for a in ARTICLES if a.slug == slug)
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200
    desc = re.search(r'<meta name="description" content="(.*?)">', r.text, re.S).group(1)
    assert html.unescape(desc) == html.unescape(art.seo_description)
