#!/usr/bin/env python3
"""Verify the length of every /learn article's `seo_description`.

WHY THIS EXISTS
---------------
#463 (deferred from #398/#451, finding F6). Nothing measured meta-description
length, and 7 of the 38 `seo_description` values on main were over the ~160
characters Google renders -- up to 187 (`manglik-remedies`) -- so the end of the
snippet, usually the part that says what is distinctive about the page, was cut
off in the SERP. The gate was held back from #451 because it could not land
green; it lands here in the same PR that shortens the 7.

THE LOAD-BEARING DETAIL: MEASURE THE DECODED STRING
---------------------------------------------------
`seo_description` is rendered into `<meta name="description" content="...">`, so
what a crawler counts is the HTML-decoded text. Source carrying `&mdash;` or
`&rsquo;` is 6-7 characters per entity raw and ONE character decoded. #451
round 2 reported `chandra-moon-remedies` as 192 for exactly that reason; decoded
it was 174. So every length below is `len(html.unescape(value))`. A gate that
counted the raw source would report a number no SEO tool reproduces.

RULES
-----
  Gate 1 - ceiling.  `seo_description` over 160 decoded characters FAILS.
  Gate 2 - floor.    `seo_description` under 50 decoded characters FAILS. An
      empty or stub description is a worse defect than a long one, and a
      ceiling-only gate passes it. Only a description that is SET is measured:
      an empty one falls back to `summary` by design (see `learn_registry.Article`).

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
   `scripts/mutations/seo_copy.py` both go red if it counts raw source.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from astro_ai.learn_registry import ARTICLES  # noqa: E402

DESC_CEILING = 160
DESC_FLOOR = 50
TITLE_ADVISORY = 60  # informational only -- see the docstring


def _visible_length(value: str) -> int:
    """Length of the text a crawler sees once the entities are decoded."""
    return len(html.unescape(value))


def check(articles) -> tuple[list[str], list[str]]:
    """Return (failures, advisories) for an iterable of Article-like objects."""
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
        if a.seo_title and _visible_length(a.seo_title) > TITLE_ADVISORY:
            advisories.append(
                f"{a.slug}: seo_title is {_visible_length(a.seo_title)} chars "
                f"(advisory {TITLE_ADVISORY})")
    return failures, advisories


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
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
