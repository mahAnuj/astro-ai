"""#463: every /learn `seo_description` fits what a SERP renders, and a gate keeps it so.

Seven descriptions were 161-187 characters once HTML-decoded, and nothing measured them.
The load-bearing detail is the DECODING: `&mdash;` is seven characters raw and one
decoded, and a gate counting the raw source reports a number no SEO tool reproduces
(#451 round 2 called `chandra-moon-remedies` 192; decoded it was 174).

Hermetic: reads the registry and the rendered pages only, no network, no LLM.
"""
from __future__ import annotations

import dataclasses
import datetime
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


def _art(desc="", title="", slug="x", summary=""):
    return SimpleNamespace(slug=slug, seo_description=desc, seo_title=title, summary=summary)


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


def test_an_unset_description_is_not_held_to_the_floor():
    # Empty falls back to `summary` by design; the floor is for a description that is set.
    assert gate.check([_art("")])[0] == []
    assert gate.check([_art("", summary="short")])[0] == []


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


# --- #1178: the EFFECTIVE description, not only a set `seo_description` --------------------


def test_every_article_effective_description_is_inside_the_ceiling():
    over = {a.slug: len(html.unescape(a.seo_description or a.summary)) for a in ARTICLES
            if len(html.unescape(a.seo_description or a.summary)) > 160}
    assert not over, f"effective meta description over 160 decoded characters: {over}"


def test_an_over_length_summary_fallback_is_a_failure():
    # The pre-#1178 gate passed this: seo_description empty, so it measured nothing, while the
    # page rendered a 210-330 character summary as its meta description.
    failures, _ = gate.check([_art("", slug="fallback", summary="s" * 161)])
    assert len(failures) == 1 and "fallback" in failures[0] and "161" in failures[0]
    assert "summary" in failures[0]
    # ... and the fallback is measured DECODED, like everything else here.
    assert gate.check([_art("", summary="&mdash;" * 40 + "s" * 110)])[0] == []


def test_a_set_description_decides_the_effective_value_not_the_summary():
    # The summary feeds cards and may be long; it is only the meta description when nothing else is.
    assert gate.check([_art("d" * 100, summary="s" * 300)])[0] == []


def test_the_gate_measures_the_real_summary_fallback():
    # Real registry shape: blank one description and the long summary behind it must trip the gate.
    victim = next(a for a in ARTICLES if len(a.summary) > 160)
    blanked = dataclasses.replace(victim, seo_description="")
    failures, _ = gate.check([blanked])
    assert failures and victim.slug in failures[0]


def test_an_over_length_template_description_fails_the_rendered_check(monkeypatch):
    # Render through the real app, with one EVENT_LANDING `seo_desc` pushed over the ceiling.
    from astro_ai import muhurat

    monkeypatch.setitem(muhurat.EVENT_LANDING["vivah"], "seo_desc", "w" * 200)
    rendered, problems = gate.render_sitemap_pages()
    assert problems == []
    failures = gate.check_pages(rendered)
    assert len(failures) == 1 and "/muhurat/vivah" in failures[0] and "200" in failures[0], failures


def test_check_pages_ceiling_floor_and_decoding():
    ok = [("/a", 200, "x" * 160), ("/b", 200, "x" * 50), ("/c", 200, "&mdash;" * 40 + "x" * 110)]
    assert gate.check_pages(ok) == []
    assert len(gate.check_pages([("/a", 200, "x" * 161)])) == 1
    stub = gate.check_pages([("/a", 200, "x" * 49)])
    assert len(stub) == 1 and "floor" in stub[0]


def test_a_page_that_is_not_200_or_has_no_description_fails():
    # An unreadable page is not a short one: skipping it is the vacuous pass #193 names.
    bad = gate.check_pages([("/down", 503, None), ("/redirect", 307, None), ("/bare", 200, None)])
    assert len(bad) == 3
    assert "503" in bad[0] and "307" in bad[1] and "no <meta" in bad[2]


def test_a_crawl_that_measures_zero_pages_fails(monkeypatch, capsys):
    monkeypatch.setattr(gate, "render_sitemap_pages", lambda: ([], []))
    assert gate.main() == 1
    assert "zero pages" in capsys.readouterr().out


def test_a_crawl_problem_fails_the_gate(monkeypatch, capsys):
    monkeypatch.setattr(gate, "render_sitemap_pages",
                        lambda: ([("/x", 200, "d" * 100)], ["/sitemap.xml returned HTTP 500"]))
    assert gate.main() == 1
    assert "/sitemap.xml returned HTTP 500" in capsys.readouterr().out


def test_the_crawl_renders_one_future_dated_panchang_and_no_llm_page():
    today = datetime.date(2026, 11, 18)
    locs = ["/", "/rashifal", "/rashifal/aries", "/hi/rashifal/aries", "/hi/rashifal",
            "/panchang", "/panchang/2026-11-17", "/panchang/2026-11-18",
            "/panchang/2026-11-19", "/panchang/2026-11-20", "/learn/ketu-remedies/"]
    got = gate.sitemap_targets(locs, today)
    assert "/rashifal/aries" not in got and "/hi/rashifal/aries" not in got
    assert "/rashifal" in got and "/hi/rashifal" in got
    assert [t for t in got if t.startswith("/panchang/")] == ["/panchang/2026-11-19"]
    assert "/panchang" in got and "/learn/ketu-remedies/" in got


def test_the_real_crawl_measures_both_panchang_shapes_and_the_hindi_twins():
    rendered, problems = gate.render_sitemap_pages()
    assert problems == []
    urls = {u for u, _, _ in rendered}
    assert "/panchang" in urls and any(u.startswith("/panchang/") for u in urls)
    assert any(u.startswith("/hi/") for u in urls)
    assert len(rendered) > 50
    assert gate.check_pages(rendered) == []


def test_an_over_length_rashifal_meta_key_fails_the_gate(monkeypatch, capsys):
    assert gate.check_rashifal_meta(gate.rashifal_meta_lengths()) == []
    from astro_ai import i18n

    monkeypatch.setitem(i18n._EN, "rashifal_single_meta", "{rashi_en} " + "w" * 200)
    failures = gate.check_rashifal_meta(gate.rashifal_meta_lengths())
    assert len(failures) == 1 and "[en]" in failures[0]
    # ... and it is main(), the thing CI runs, that goes red -- not only the helper.
    monkeypatch.setattr(gate, "render_sitemap_pages", lambda: ([("/x", 200, "d" * 100)], []))
    assert gate.main() == 1
    assert "rashifal_single_meta [en]" in capsys.readouterr().out
    monkeypatch.setitem(i18n._HI, "rashifal_single_meta", "{rashi_hi} " + "व" * 200)
    assert len(gate.check_rashifal_meta(gate.rashifal_meta_lengths())) == 2


def test_a_missing_rashifal_meta_key_is_a_failure_not_a_short_pass(monkeypatch):
    from astro_ai import i18n

    monkeypatch.delitem(i18n._EN, "rashifal_single_meta")
    monkeypatch.delitem(i18n._HI, "rashifal_single_meta")
    assert len(gate.check_rashifal_meta(gate.rashifal_meta_lengths())) == 2
