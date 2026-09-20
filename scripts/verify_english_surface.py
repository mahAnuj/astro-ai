#!/usr/bin/env python3
"""Gate for #124 — the English URL surface must not move when Hindi arrives.

#124 adds Hindi URLs under `/hi/...`. The one hard constraint on the whole
change is that the EXISTING English URLs do not change, redirect, or break:
`/` and `/matching` are the best-converting SERP entries we have (10.7% and
11.4% CTR), and there is no staging environment — a push to `main` IS the
production deploy. So the English surface is captured mechanically BEFORE
anything moves, and every later subtask has to keep this green.

WHAT IT RECORDS, per URL, fetched with NO COOKIES and NO `?lang=`
(the crawler's-eye view — Googlebot has no session and does not send
`Accept-Language`, so neither does this):

    status            HTTP status of the final response
    final_path        path after redirects — catches a URL that STARTS
                      redirecting, which is the #124 failure mode that would
                      cost the most ranking
    title             <title>
    meta_description  <meta name="description"> content
    canonical         <link rel="canonical"> href
    html_lang         <html lang>
    hreflang_count    number of <link rel="alternate" hreflang=...> tags.
                      Baseline is 0 everywhere; when #124 adds hreflang pairs
                      this gate will go red and must be RE-CAPTURED
                      deliberately, with the new counts reviewed.

It deliberately does NOT record the body or a body hash. `/rashifal`,
`/panchang` and `/festivals` change every day by design, so a body hash would
flap daily and be muted within a week. The fields above are the SEO
load-bearing bytes.

DATES ARE NORMALISED, and this is not optional: `/panchang` and `/rashifal`
render today's date INTO the title and description ("Today's Panchang —
20 September 2026 · …"). A raw capture would fail tomorrow. Full dates are
replaced with `{DATE}` / `{ISO_DATE}` before storing and before comparing.
The cost of that is real and worth stating: a hard-coded festival date inside
a meta description would also be normalised away, so this gate cannot see a
date CHANGE. That is verify_festivals.py's job, not this one's.

/rashifal/{rashi} RECORDS 503 LOCALLY AND THAT IS CORRECT — DO NOT "FIX" IT.
The local `.env` default model `llama-3.3-70b-versatile` was decommissioned by
Groq and is the only provider in the local chain, so every LLM-dependent page
degrades to the 503 "High demand right now" template here. Production is
unaffected. The gate compares like-for-like on the same machine, and a rashi
URL flipping from 503 to a REDIRECT is still exactly the signal #124 needs.
Stubbing the LLM to get 200s would make the baseline unreproducible.

THE URL LIST IS DERIVED, NOT TYPED. The static pages are read out of
`routes/seo.py`'s sitemap `pages` list with `ast`, and the 12 rashi slugs out
of `astro_ai.llm.RASHI_CANONICAL_SLUGS`, so the gate cannot drift from the
sitemap. Add a static page to the sitemap and this gate reports it as not in
the baseline — correctly, because it then needs a reviewed re-capture.

USAGE
    uv run astro-ai &                                  # gate needs the server
    uv run python scripts/verify_english_surface.py --capture   # write baseline
    uv run python scripts/verify_english_surface.py             # compare

EXIT CODES
    0  PASS — every field matches the baseline
    1  FAIL — a named field on a named URL differs
    2  COULD NOT VERIFY — server unreachable, baseline missing, or the URL
       list could not be derived. Deliberately distinct from PASS: an
       unrunnable gate must never read as a green one.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / "tests" / "english_surface_baseline.json"
SEO_ROUTES = REPO_ROOT / "src" / "astro_ai" / "routes" / "seo.py"

DEFAULT_BASE = "http://127.0.0.1:8000"

# Floor, not a target — same reasoning as verify_behaviour.py's EXPECTED_TESTS.
# If the ast walk silently starts returning three paths, the gate would pass
# while checking almost nothing.
EXPECTED_STATIC_PAGES = 17

# Three /learn articles, named rather than sampled: a sampled set would change
# membership whenever an article is added and the baseline would need a
# re-capture for an unrelated reason. One evergreen explainer, one dasha page,
# one dated festival page (the shape most likely to be touched by a Hindi
# variant).
LEARN_SAMPLE = (
    "the-9-grahas-overview",
    "vimshottari-dasha-explained",
    "karva-chauth-2026",
)

FIELDS = (
    "status",
    "final_path",
    "title",
    "meta_description",
    "canonical",
    "html_lang",
    "hreflang_count",
)

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
_DATE_SUBS = (
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "{ISO_DATE}"),
    (re.compile(rf"\b\d{{1,2}} (?:{_MONTHS})\.? \d{{4}}\b"), "{DATE}"),
    (re.compile(rf"\b(?:{_MONTHS})\.? \d{{1,2}},? \d{{4}}\b"), "{DATE}"),
)


def _normalise(value):
    """Blank out rendered dates so a daily-fresh page does not flap the gate.

    Only whole dates match — a bare year survives, so `karva-chauth-2026` in a
    slug or title is compared as written.
    """
    if not isinstance(value, str):
        return value
    for pattern, token in _DATE_SUBS:
        value = pattern.sub(token, value)
    return value


class _HeadParser(HTMLParser):
    """Pulls the SEO head fields out of a response.

    HTMLParser rather than regex because `Today&#39;s Rashifal` has to compare
    equal to `Today's Rashifal` — convert_charrefs (on by default) does that,
    and a regex over the raw bytes would make an entity-encoding change look
    like a copy change.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self.meta_description: str | None = None
        self.canonical: str | None = None
        self.html_lang: str | None = None
        self.hreflang_count = 0
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html" and self.html_lang is None:
            self.html_lang = a.get("lang")
        elif tag == "title" and self.title is None:
            self._in_title = True
        elif tag == "meta":
            if a.get("name", "").lower() == "description" and self.meta_description is None:
                self.meta_description = a.get("content")
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if rel == "canonical" and self.canonical is None:
                self.canonical = a.get("href")
            elif rel == "alternate" and "hreflang" in a:
                self.hreflang_count += 1

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = "".join(self._title_parts).strip()


def _static_paths() -> list[str]:
    """Read the sitemap's literal `pages` list out of routes/seo.py.

    Static parse, not an import: the list is a local inside `sitemap()`, so
    there is nothing importable, and parsing keeps the gate honest about what
    the sitemap actually ships rather than what someone retyped here.
    """
    tree = ast.parse(SEO_ROUTES.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "pages" not in targets or not isinstance(node.value, ast.List):
            continue
        paths = []
        for elt in node.value.elts:
            if isinstance(elt, ast.Tuple) and elt.elts:
                first = elt.elts[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    paths.append(first.value)
        if paths:
            return paths
    return []


def _rashi_slugs() -> tuple[str, ...]:
    from astro_ai.llm import RASHI_CANONICAL_SLUGS

    return tuple(RASHI_CANONICAL_SLUGS)


def _urls() -> list[str]:
    paths = list(_static_paths())
    static_count = len(paths)
    if static_count < EXPECTED_STATIC_PAGES:
        raise LookupError(
            f"only {static_count} static sitemap paths derived from "
            f"{SEO_ROUTES.name}, expected at least {EXPECTED_STATIC_PAGES}"
        )
    paths.append("/panchang")  # de-duped below; named here because #124 touches it
    paths += [f"/rashifal/{slug}" for slug in _rashi_slugs()]
    paths += [f"/learn/{slug}/" for slug in LEARN_SAMPLE]

    seen, ordered = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


def _fetch(base: str, path: str, timeout: int) -> dict:
    # Default opener: no cookie jar, so a Set-Cookie the app hands back is
    # never sent onward, and redirects are followed so `final_path` can catch a
    # URL that starts redirecting. No Accept-Language header either — a crawler
    # sends none, and the whole point of #124's constraint is that the
    # cookie-less, param-less view of an English URL stays English.
    opener = urllib.request.build_opener()
    req = urllib.request.Request(
        base + path,
        headers={"User-Agent": "verify_english_surface/1.0", "Accept": "text/html"},
    )
    try:
        resp = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as exc:  # 4xx/5xx still carry a body we want
        resp = exc
    body = resp.read().decode("utf-8", "replace")
    final = resp.geturl()
    parser = _HeadParser()
    parser.feed(body)
    record = {
        "status": resp.status,
        "final_path": final[len(base):] if final.startswith(base) else final,
        "title": parser.title,
        "meta_description": parser.meta_description,
        "canonical": parser.canonical,
        "html_lang": parser.html_lang,
        "hreflang_count": parser.hreflang_count,
    }
    return {k: _normalise(v) for k, v in record.items()}


def _capture(base: str, timeout: int) -> dict:
    surface = {}
    for path in _urls():
        surface[path] = _fetch(base, path, timeout)
        print(f"  {surface[path]['status']}  {path}")
    return surface


def _commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _compare(baseline: dict, current: dict) -> list[str]:
    diffs = []
    for path in sorted(set(baseline) | set(current)):
        if path not in baseline:
            diffs.append(f"{path}  NOT IN BASELINE — new URL, re-capture deliberately")
            continue
        if path not in current:
            diffs.append(f"{path}  MISSING — baselined URL was not fetched")
            continue
        for field in FIELDS:
            was, now = baseline[path].get(field), current[path].get(field)
            if was != now:
                diffs.append(
                    f"{path}  {field}:\n"
                    f"      baseline: {was!r}\n"
                    f"      current : {now!r}"
                )
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=DEFAULT_BASE, help="base URL of a running server")
    ap.add_argument("--capture", action="store_true", help="write the baseline instead of comparing")
    ap.add_argument("--timeout", type=int, default=90, help="per-request timeout, seconds")
    args = ap.parse_args()
    base = args.url.rstrip("/")

    print("English URL surface (#124) — these URLs must not change or redirect\n")

    try:
        with urllib.request.urlopen(base + "/robots.txt", timeout=10) as r:
            r.read(1)
    except Exception as exc:
        print(f"COULD NOT VERIFY: {base} is not reachable ({exc}).")
        print("  Start it with: uv run astro-ai")
        return 2

    try:
        urls = _urls()
    except LookupError as exc:
        print(f"COULD NOT VERIFY: {exc}")
        return 2

    print(f"  {len(urls)} URLs, no cookies, no ?lang=\n")
    current = _capture(base, args.timeout)
    print()

    if args.capture:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(
            json.dumps(
                {
                    "_what": "English SEO surface before #124 added /hi/ URLs. "
                             "Dates are normalised to {DATE}/{ISO_DATE}; see "
                             "scripts/verify_english_surface.py.",
                    "_captured_commit": _commit(),
                    "urls": current,
                },
                indent=2, sort_keys=True, ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"CAPTURED {len(current)} URLs -> {BASELINE.relative_to(REPO_ROOT)}")
        return 0

    if not BASELINE.exists():
        print(f"COULD NOT VERIFY: no baseline at {BASELINE.relative_to(REPO_ROOT)}.")
        print("  Capture one on a clean tree: --capture")
        return 2

    baseline = json.loads(BASELINE.read_text(encoding="utf-8")).get("urls", {})
    diffs = _compare(baseline, current)
    if diffs:
        print(f"FAIL — {len(diffs)} difference(s) from the baseline:\n")
        for d in diffs:
            print(f"  {d}")
        print("\n  English URLs are load-bearing for search. If a change here is")
        print("  intended, re-capture the baseline in the SAME commit and say why.")
        return 1

    print(f"PASS ({len(current)} URLs unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
