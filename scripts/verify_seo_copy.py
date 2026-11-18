#!/usr/bin/env python3
"""Verify the length of every crawled page's EFFECTIVE meta description.

WHY THIS EXISTS
---------------
#463 (deferred from #398/#451, finding F6). Nothing measured meta-description
length, and 7 of the 38 `seo_description` values on main were over the ~160
characters Google renders -- up to 187 (`manglik-remedies`) -- so the end of the
snippet, usually the part that says what is distinctive about the page, was cut
off in the SERP. The gate was held back from #451 because it could not land
green; it lands here in the same PR that shortens the 7.

#1178: THAT GATE MEASURED THE WRONG THING. It read `seo_description` only, and
`learn_article_base.html` renders `{{ article.seo_description or article.summary }}`,
so the 38 articles with an EMPTY `seo_description` fell back to a 210-330 character
`summary` the gate never looked at. Measured by crawling /sitemap.xml in-process on
2026-11-18, 54 of 202 pages were over 160: those 38 articles, plus `/` (309),
/muhurat (497), the five /muhurat/<event> landings, /kundli, /dasha, /panchang,
/numerology (406), /numerology/compatibility, /kaal-sarp-check, /about and /terms --
all green under this gate. The Rashifal meta (`rashifal_single_meta`, EN 190 / HI 172)
was over too and sits behind an LLM route no crawl here can render. So the gate now
measures what a crawler reads: the EFFECTIVE description.

THE LOAD-BEARING DETAIL: MEASURE THE DECODED STRING
---------------------------------------------------
The description is rendered into `<meta name="description" content="...">`, so
what a crawler counts is the HTML-decoded text. Source carrying `&mdash;` or
`&rsquo;` is 6-7 characters per entity raw and ONE character decoded. #451
round 2 reported `chandra-moon-remedies` as 192 for exactly that reason; decoded
it was 174. So every length below is `len(html.unescape(value))`. A gate that
counted the raw source would report a number no SEO tool reproduces.

RULES
-----
  Gate 1 - ceiling, articles.  The effective description, `seo_description or
      summary`, over 160 decoded characters FAILS -- whether it is a set value or
      the summary fallback.
  Gate 2 - floor, articles.  `seo_description` under 50 decoded characters FAILS.
      An empty or stub description is a worse defect than a long one, and a
      ceiling-only gate passes it. Only a description that is SET is held to the
      floor: an empty one falls back to `summary` by design (see
      `learn_registry.Article`) and the fallback is measured for the ceiling.
  Gate 3 - the rendered pages.  Every page in /sitemap.xml except /rashifal/*
      (it needs an LLM) is rendered in-process with Starlette's TestClient -- no
      network, no LLM, no GCS -- and the `<meta name="description">` it actually
      emits is held to the same 50-160 band. That covers every template block,
      the `base.html` default, `page_meta` strings built in routes, the
      EVENT_LANDING `seo_desc` values and both Panchang shapes (undated, and ONE
      dated URL in the future, which takes `dated_description` instead of the
      inline text). It also covers the Hindi twins, which share the templates.
      The `base.html` default is also read from the template source (Gate 3b):
      no sitemap page falls through to it, but error pages and the Rashifal
      fallback serve it, so a crawl alone never measures it.
  Gate 4 - the Rashifal meta.  /rashifal/<rashi> cannot be rendered hermetically,
      so `rashifal_single_meta` is rendered through `translate()` for EN and HI,
      for all 12 rashis and every day of a year (the date's length varies), and
      the longest is held to the ceiling. The key missing from a table is a
      failure: `translate()` returns the key name for it, which is short.

  VACUOUS-PASS RULE (#193).  The gate fails loudly -- non-zero -- if the sitemap
  yields no URLs, if no page was measured, if ANY page returns non-200 or has no
  description meta (an unreadable page is not a short one), if no future-dated
  Panchang URL is found to render, or if no article carries a description.

INFORMATIONAL, NOT A GATE: `seo_title` over 60 characters
---------------------------------------------------------
Four titles are 61-64 characters. They are printed and never fail the run.
Titles on ranking pages are being CTR-tested under #311 / #685, and changing
one would confound the analyst's scores for that page. When that experiment
ends, promote the title count to a ceiling here.

RULES FOR ANYONE EDITING THIS FILE
----------------------------------
1. Do not raise the ceiling or lower the floor to make a run green; shorten the
   copy. Shorten, do not rewrite: drop trailing or redundant words and add no
   claim the page does not already make.
2. Keep `_visible_length` decoding. `tests/test_seo_copy_gate.py` and the rows in
   `scripts/mutations/` both go red if it counts raw source.
3. Changing a page's description also changes `tests/english_surface_baseline.json`
   for that URL; re-capture it in the same commit (see `verify_english_surface.py`).
   Edit the entry, not the whole file: `--capture` drops the hand-written notes.
"""
from __future__ import annotations

import html
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from astro_ai.learn_registry import ARTICLES  # noqa: E402

DESC_CEILING = 160
DESC_FLOOR = 50
TITLE_ADVISORY = 60  # informational only -- see the docstring

# /rashifal/<rashi> and its /hi/ twin need an LLM to render a 200 (Gate 4 covers
# their meta through the i18n key instead).
_LLM_PAGE = re.compile(r"^/(?:hi/)?rashifal/[^/]+/?$")
_DATED_PANCHANG = re.compile(r"^/panchang/(\d{4}-\d{2}-\d{2})$")
_META = re.compile(r'<meta name="description" content="([^"]*)"')


def _visible_length(value: str) -> int:
    """Length of the text a crawler sees once the entities are decoded."""
    return len(html.unescape(value))


def check(articles) -> tuple[list[str], list[str]]:
    """Return (failures, advisories) for an iterable of Article-like objects.

    The ceiling is held to the EFFECTIVE description -- `seo_description or
    summary`, what `learn_article_base.html` renders -- the floor only to a
    description that is SET.
    """
    failures: list[str] = []
    advisories: list[str] = []
    for a in articles:
        if a.seo_description:
            n = _visible_length(a.seo_description)
            if n > DESC_CEILING:
                failures.append(
                    f"{a.slug}: seo_description is {n} chars decoded "
                    f"(ceiling {DESC_CEILING})")
            elif n < DESC_FLOOR:
                failures.append(
                    f"{a.slug}: seo_description is {n} chars decoded "
                    f"(floor {DESC_FLOOR})")
        else:
            n = _visible_length(getattr(a, "summary", "") or "")
            if n > DESC_CEILING:
                failures.append(
                    f"{a.slug}: seo_description is empty, so the summary is the "
                    f"meta description and is {n} chars decoded "
                    f"(ceiling {DESC_CEILING}) -- set a seo_description")
        if a.seo_title and _visible_length(a.seo_title) > TITLE_ADVISORY:
            advisories.append(
                f"{a.slug}: seo_title is {_visible_length(a.seo_title)} chars "
                f"(advisory {TITLE_ADVISORY})")
    return failures, advisories


def check_pages(rendered) -> list[str]:
    """Failures for `(url, status, description-or-None)` rows of rendered pages.

    A page that did not return 200, or that has no description meta, is a
    failure and never a skip: an unreadable page is not a short one (#193).
    """
    failures: list[str] = []
    for url, status, desc in rendered:
        if status != 200:
            failures.append(f"{url}: returned HTTP {status}, so its description was not measured")
        elif desc is None:
            failures.append(f"{url}: no <meta name=\"description\"> in the rendered page")
        else:
            n = _visible_length(desc)
            if n > DESC_CEILING:
                failures.append(
                    f"{url}: rendered meta description is {n} chars decoded "
                    f"(ceiling {DESC_CEILING})")
            if n < DESC_FLOOR:
                failures.append(
                    f"{url}: rendered meta description is {n} chars decoded "
                    f"(floor {DESC_FLOOR})")
    return failures


def sitemap_targets(locs, today: date) -> list[str]:
    """The paths to render: every sitemap URL, minus the LLM pages, with the
    dated Panchang archive reduced to the first future date (one is enough: all
    90 take the same `dated_description` path, and each costs an ephemeris run).
    """
    targets: list[str] = []
    dated: str | None = None
    for path in locs:
        if _LLM_PAGE.match(path):
            continue
        m = _DATED_PANCHANG.match(path)
        if m:
            if dated is None and date.fromisoformat(m.group(1)) > today:
                dated = path
            continue
        targets.append(path)
    if dated:
        targets.append(dated)
    return targets


def render_sitemap_pages():
    """Render the sitemap pages in-process. Returns (rendered, problems)."""
    os.environ.setdefault("OPENAI_API_KEY", "x")  # import-time requirement only; no call is made
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    client = TestClient(app)
    problems: list[str] = []
    resp = client.get("/sitemap.xml")
    if resp.status_code != 200:
        return [], [f"/sitemap.xml returned HTTP {resp.status_code}"]
    locs = re.findall(r"<loc>https?://[^/<]+(/[^<]*)</loc>", resp.text)
    if not locs:
        return [], ["/sitemap.xml listed no URLs"]
    targets = sitemap_targets(locs, date.today())
    if not any(_DATED_PANCHANG.match(t) for t in targets):
        problems.append("no future-dated /panchang/<date> URL in the sitemap to render")
    if "/panchang" not in targets:
        problems.append("/panchang is not in the sitemap")
    rendered = []
    for path in targets:
        r = client.get(path)
        m = _META.search(r.text) if r.status_code == 200 else None
        rendered.append((path, r.status_code, m.group(1) if m else None))
    return rendered, problems


_BASE_DEFAULT = re.compile(
    r'<meta name="description" content="\{% block meta_description %\}(.*?)\{% endblock %\}"')


def base_default_description() -> str | None:
    """The `base.html` default meta description, read from the template source.

    No sitemap page falls through to it (every one overrides the block), so a crawl
    never measures it -- yet error pages and `/rashifal/<rashi>` fallbacks still serve
    it. Reading the source is the only way to hold it to the band.
    """
    src = (Path(__file__).resolve().parent.parent / "src" / "astro_ai" / "templates"
           / "base.html").read_text(encoding="utf-8")
    m = _BASE_DEFAULT.search(src)
    return m.group(1) if m else None


def check_base_default(value: str | None) -> list[str]:
    if value is None:
        return ["base.html: the default meta_description block was not found (gate cannot measure it)"]
    n = _visible_length(value)
    if n > DESC_CEILING:
        return [f"base.html default meta_description is {n} chars decoded (ceiling {DESC_CEILING})"]
    if n < DESC_FLOOR:
        return [f"base.html default meta_description is {n} chars decoded (floor {DESC_FLOOR})"]
    return []


def rashifal_meta_lengths() -> dict[str, tuple[int, str]]:
    """Longest decoded `rashifal_single_meta` per language, over 12 rashis x 365 days."""
    from astro_ai.i18n import translate
    from astro_ai.llm import _RASHI_ANCHORS
    from astro_ai.routes.deps import _pretty_date

    first = date(2026, 1, 1)
    out: dict[str, tuple[int, str]] = {}
    for lang in ("en", "hi"):
        dates = {_pretty_date((first + timedelta(days=i)).isoformat(), lang)
                 for i in range(365)}
        longest = (0, "")
        for anchor in _RASHI_ANCHORS:
            slug = anchor["en"].lower()
            hi_name = translate(lang, f"rashi_name_{slug}")
            for pretty in dates:
                text = html.unescape(translate(
                    lang, "rashifal_single_meta", rashi_en=anchor["en"],
                    rashi_sa=anchor["sa"], rashi_hi=hi_name, date=pretty))
                if len(text) > longest[0]:
                    longest = (len(text), text)
        out[lang] = longest
    return out


def check_rashifal_meta(lengths) -> list[str]:
    failures: list[str] = []
    for lang, (n, text) in lengths.items():
        if text == "rashifal_single_meta" or n < DESC_FLOOR:
            failures.append(f"rashifal_single_meta [{lang}]: missing or stub ({n} chars: {text!r})")
        elif n > DESC_CEILING:
            failures.append(
                f"rashifal_single_meta [{lang}]: {n} chars decoded at its longest "
                f"(ceiling {DESC_CEILING}): {text}")
    if set(lengths) != {"en", "hi"}:
        failures.append("rashifal_single_meta: EN and HI were not both measured")
    return failures


def main() -> int:
    articles = list(ARTICLES)
    measured = sum(1 for a in articles if a.seo_description)
    # A registry that yields nothing to measure passes vacuously (#193).
    if not measured:
        print("FAIL: no article carries a seo_description -- nothing was measured")
        return 1
    failures, advisories = check(articles)
    for line in advisories:
        print(f"info: {line}")
    for line in failures:
        print(f"FAIL: {line}")
    print(f"seo_description: {measured} measured of {len(articles)} articles, "
          f"{len(failures)} outside {DESC_FLOOR}-{DESC_CEILING} decoded; "
          f"{len(advisories)} seo_title over {TITLE_ADVISORY} (informational)")

    rendered, problems = render_sitemap_pages()
    page_failures = problems + check_pages(rendered)
    if not rendered:
        page_failures.append("the crawl rendered zero pages -- nothing was measured")
    for line in page_failures:
        print(f"FAIL: {line}")
    print(f"rendered meta description: {len(rendered)} pages measured in-process, "
          f"{len(page_failures)} failures (band {DESC_FLOOR}-{DESC_CEILING} decoded)")

    base_failures = check_base_default(base_default_description())
    for line in base_failures:
        print(f"FAIL: {line}")
    print(f"base.html default meta_description: {len(base_failures)} failures")

    rashifal = rashifal_meta_lengths()
    rashifal_failures = check_rashifal_meta(rashifal)
    for line in rashifal_failures:
        print(f"FAIL: {line}")
    print("rashifal_single_meta longest: "
          + ", ".join(f"{lang.upper()} {n}" for lang, (n, _) in sorted(rashifal.items()))
          + f"; {len(rashifal_failures)} failures")
    return 1 if (failures or page_failures or base_failures or rashifal_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
