#!/usr/bin/env python3
"""Search Console URL Inspection over every sitemap URL -> JSON on stdout (#1065).

THE GAP IT CLOSES. Nothing here read index status before. `fetch_gsc.py` calls
only searchAnalytics/query, so a page with zero impressions looked the same
whether it was not indexed, indexed and not ranking, or pointed at a different
canonical. Nothing compared "we changed this page" with "Google last crawled it",
so a heavily edited page could keep serving its old snippet for weeks.

For each URL in the live /sitemap.xml this calls
`urlInspection/index:inspect` once, sequentially (213 calls fit in the 600 per
minute and 2,000 per day per-property quota), maps the path to the repo file(s)
that render it, and flags:

  stale_in_index      the last commit touching those files is NEWER than Google's
                      lastCrawlTime
  not_indexed         verdict FAIL/NEUTRAL (PASS/PARTIAL -> false; absent -> null)
  canonical_mismatch  googleCanonical differs from userCanonical

and precomputes `request_indexing`, the top 10 worth asking Google to recrawl.
A not-indexed /learn page whose slug names NEXT year (#1571) is listed first, at most
five of the ten: it has no impressions yet, so impressions alone would never surface it.
Google has no API to REQUEST indexing for ordinary pages (the Indexing API covers
JobPosting and BroadcastEvent only), so the last click is the owner's: GSC ->
URL Inspection -> Request indexing, about 10 a day.

WHAT IS NOT KNOWN YET. The response field names and enum values below come from
Google's documentation, not from an observed response: no real call has been made
by the code that wrote this. The first live run must confirm (a) `index:inspect`
accepts the `webmasters.readonly` scope and the service account's GSC role, and
(b) the shapes used by `classify`. The test fixtures are doc-derived until one
real response is captured.

THE RULES, each of which cost a design decision:
  * Staleness is computed ONLY when `git rev-parse --is-shallow-repository` prints
    exactly `false`. A depth-1 clone (the agent-measure checkout default) gives
    every file the tip commit's date, which would flag every page. Otherwise
    `stale_in_index` is null with `stale_reason: "shallow-checkout"`.
  * A 429, or a 403 whose body says "quota", stops the run: `partial: true`, the
    unreached rows are `not_inspected` with every verdict field null. An
    unreached page is never reported as indexed, and a partial run is never merged
    with an older file (that would be guessing under a fresh timestamp).
  * A 401/403/400 on the FIRST call, an unreadable sitemap, zero URLs, or a run
    that inspected nothing: exit 1 and print nothing. An all-unknown file is noise.
  * Canonical-mismatch and blocked rows are flagged but kept out of
    `request_indexing`: "Request indexing" does not fix either.
  * base.html, i18n.py and learn_registry.py are NOT mapped into any page's file
    list: one edit to any of them would flag all 213 pages.

Zero LLM calls. The Authorization comes from `_gapi.token()` (ADC), as every
sibling collector does.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gapi import ApiError, post, token  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
API = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SITE = "sc-domain:shubhagya.com"
SITEMAP_URL = "https://shubhagya.com/sitemap.xml"
DAILY_LIMIT = 2000
SITEMAP_TIMEOUT = 30

TPL = "src/astro_ai/templates/"
# Fixed routes -> the file that renders them. Names were read off the live app
# (each route driven with a TestClient and the template name recorded), not
# guessed from the route. Dated /panchang/<date> pages share panchang.html.
FIXED_ROUTES = {
    "/": [TPL + "index.html"],
    "/rashifal": [TPL + "rashifal_grid.html"],
    "/matching": [TPL + "matching.html"],
    "/learn/": [TPL + "learn_index.html"],
    "/muhurat": [TPL + "muhurat_finder.html"],
    "/manglik-check": [TPL + "dosha_check_form.html"],
    "/sade-sati-check": [TPL + "dosha_check_form.html"],
    "/kaal-sarp-check": [TPL + "dosha_check_form.html"],
    "/numerology": [TPL + "numerology.html"],
    "/numerology/compatibility": [TPL + "numerology_compat.html"],
    "/kundli": [TPL + "kundli_landing.html"],
    "/dasha": [TPL + "dasha_landing.html"],
    "/panchang": [TPL + "panchang.html"],
    "/festivals": [TPL + "festivals_index.html"],
    "/about": [TPL + "about.html"],
    "/privacy": [TPL + "privacy.html"],
    "/terms": [TPL + "terms.html"],
}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

NOTE = (
    "base.html, i18n.py and learn_registry.py are excluded from every page's file list on "
    "purpose: one edit to any of them would flag all pages. /rashifal* and /panchang* change "
    "by data, not by commit, so commit staleness understates them. stale_in_index is null "
    "(never false) when it cannot be computed; a not_inspected row has no verdict at all."
)


class FirstCallError(Exception):
    """The first inspection failed in a way that makes the whole file noise."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_sitemap(xml: str | bytes) -> list[dict]:
    """[{url, priority}] in document order, de-duplicated. Pure.

    Reads only <url>/<loc> and <priority>. The xhtml:link hreflang annotations
    inside each <url> carry the SAME pages again and are ignored, so a Hindi twin
    is counted once, from its own <url> entry.
    """
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    out, seen = [], set()
    for el in ET.fromstring(data).iter():
        if _local(el.tag) != "url":
            continue
        loc, prio = None, None
        for child in el:
            name = _local(child.tag)
            if name == "loc" and child.text:
                loc = child.text.strip()
            elif name == "priority" and child.text:
                try:
                    prio = float(child.text.strip())
                except ValueError:
                    prio = None
        if loc and loc not in seen:
            seen.add(loc)
            out.append({"url": loc, "priority": prio})
    return out


def same_site(entries: list[dict], sitemap_url: str) -> tuple[list[dict], int]:
    """Keep only http(s) entries on the sitemap's own host. Returns (kept, dropped). Pure.

    The sitemap is data. An off-site or file:// <loc> would be sent to URL Inspection
    as an inspectionUrl (quota spent, an error row written), so it is dropped here.
    """
    host = urllib.parse.urlsplit(sitemap_url).netloc.lower()
    kept = []
    for e in entries:
        parts = urllib.parse.urlsplit(e["url"])
        if parts.scheme in ("http", "https") and parts.netloc.lower() == host:
            kept.append(e)
    return kept, len(entries) - len(kept)


def fetch_sitemap(url: str) -> bytes:
    if not url.startswith(("https://", "http://")):
        raise ValueError(f"sitemap url must be http(s): {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": "shubhagya-index-status/1"})
    with urllib.request.urlopen(req, timeout=SITEMAP_TIMEOUT) as r:  # noqa: S310 - scheme checked
        return r.read()


def route_files(path: str) -> list[str]:
    """Repo-relative files that render a URL path; [] when the route is unknown."""
    if path == "/hi" or path.startswith("/hi/"):
        path = path[3:] or "/"
    if path in FIXED_ROUTES:
        return list(FIXED_ROUTES[path])
    parts = [p for p in path.split("/") if p]
    if len(parts) == 2 and parts[0] == "learn" and _SLUG.match(parts[1]):
        return [f"{TPL}learn/{parts[1]}.html"]
    if len(parts) == 2 and parts[0] == "rashifal" and _SLUG.match(parts[1]):
        return [TPL + "rashifal_single.html"]
    if len(parts) == 2 and parts[0] == "panchang" and _DATE.match(parts[1]):
        return [TPL + "panchang.html"]
    if len(parts) == 2 and parts[0] == "muhurat" and _SLUG.match(parts[1]):
        # The landing copy lives in muhurat.py's EVENT_LANDING, not in the template.
        return [TPL + "muhurat_landing.html", "src/astro_ai/muhurat.py"]
    return []


def _git(args: list[str], root: Path) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=root, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return r.returncode, r.stdout


def is_shallow(root: Path) -> bool:
    """True unless git says exactly `false`: an unanswerable question is not 'full history'."""
    rc, out = _git(["rev-parse", "--is-shallow-repository"], root)
    return not (rc == 0 and out.strip() == "false")


def _parse_time(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # Google emits nanoseconds ("...123456789Z"); fromisoformat takes at most six.
    s = re.sub(r"(\.\d{6})\d+", r"\1", s)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def last_change(files: list[str], root: Path) -> tuple[str, str] | None:
    """(committer date ISO, sha) of the newest commit touching any of `files`, one git call."""
    if not files:
        return None
    rc, out = _git(["log", "-1", "--format=%cI%x09%H", "--", *files], root)
    line = out.strip()
    if rc != 0 or "\t" not in line:
        return None
    when, sha = line.split("\t", 1)
    return when, sha


def inspect_one(url: str, site: str, bearer: str) -> dict:
    return post(API, {"inspectionUrl": url, "siteUrl": site, "languageCode": "en-US"}, bearer)


_NOT_INDEXED = {"FAIL": True, "NEUTRAL": True, "PASS": False, "PARTIAL": False}


def classify(raw: dict) -> dict:
    """The fields we keep from one response, plus the three derived flags."""
    s = ((raw or {}).get("inspectionResult") or {}).get("indexStatusResult") or {}
    verdict = s.get("verdict")
    g, u = s.get("googleCanonical"), s.get("userCanonical")
    robots, state = s.get("robotsTxtState"), s.get("indexingState")
    return {
        "verdict": verdict,
        "coverageState": s.get("coverageState"),
        "lastCrawlTime": s.get("lastCrawlTime"),
        "googleCanonical": g,
        "userCanonical": u,
        "robotsTxtState": robots,
        "indexingState": state,
        "pageFetchState": s.get("pageFetchState"),
        # An unspecified/absent verdict is unknown, never "not indexed".
        "not_indexed": _NOT_INDEXED.get(verdict),
        "canonical_mismatch": (g != u) if (g and u) else None,
        "blocked": robots == "DISALLOWED" or str(state or "").startswith("BLOCKED"),
    }


def stale(changed_at: str | None, last_crawl: str | None, shallow: bool) -> tuple[bool | None, str | None]:
    """(stale_in_index, reason). Compares tz-aware datetimes, never strings."""
    if shallow:
        return None, "shallow-checkout"
    if not changed_at:
        return None, "no-source-file"
    crawl, changed = _parse_time(last_crawl), _parse_time(changed_at)
    if crawl is None:
        return None, "never-crawled" if not last_crawl else "unparsable-crawl-time"
    if changed is None:
        return None, "unparsable-change-time"
    return changed > crawl, None


def _quota_stop(e: ApiError) -> bool:
    return e.status == 429 or (e.status == 403 and "quota" in str(e).lower())


def _empty_verdict() -> dict:
    return {k: None for k in ("verdict", "coverageState", "lastCrawlTime", "googleCanonical",
                              "userCanonical", "robotsTxtState", "indexingState",
                              "pageFetchState", "not_indexed", "canonical_mismatch", "blocked")}


def run(entries: list[dict], site: str, bearer: str, root: Path,
        impressions: dict | None = None) -> dict:
    """Inspect every entry in order. Returns {rows, partial, partial_reason, calls, shallow}.

    Raises FirstCallError when the first call is a 400/401/403.
    """
    shallow = is_shallow(root)
    rows, calls = [], 0
    partial, reason = False, None

    for i, e in enumerate(entries):
        url = e["url"]
        path = urllib.parse.urlsplit(url).path or "/"
        files = route_files(path)
        row = {"url": url, "path": path, "sitemap_priority": e.get("priority"),
               "impressions": None if impressions is None else impressions.get(url, 0),
               "source_files": files, "status": "not_inspected", **_empty_verdict(),
               "changed_at": None, "changed_sha": None,
               "stale_in_index": None, "stale_reason": None}
        rows.append(row)
        if partial:
            continue

        raw, err = None, None
        for attempt in (1, 2):
            calls += 1
            try:
                raw = inspect_one(url, site, bearer)
                break
            except ApiError as ex:
                if _quota_stop(ex):
                    partial, reason = True, f"quota: HTTP {ex.status} after {calls - 1} successful call(s)"
                    break
                if i == 0 and ex.status in (400, 401, 403):
                    raise FirstCallError(str(ex)) from None
                err = f"HTTP {ex.status}"
                if ex.status < 500:
                    break  # permanent for this URL; a retry cannot change a 4xx
            except (urllib.error.URLError, TimeoutError, OSError) as ex:
                err = f"{type(ex).__name__}: {ex}"[:200]
            except ValueError as ex:  # a body that is not JSON
                err = f"unreadable response: {ex}"[:200]
                break
        if partial:
            continue
        if raw is None:
            row["status"], row["error"] = "error", err
            continue

        row["status"] = "inspected"
        row.update(classify(raw))
        if shallow:
            change = None
        else:
            change = last_change(files, root)
        if change:
            row["changed_at"], row["changed_sha"] = change
        row["stale_in_index"], row["stale_reason"] = stale(
            row["changed_at"], row["lastCrawlTime"], shallow)
    return {"rows": rows, "partial": partial, "partial_reason": reason,
            "calls": calls, "shallow": shallow}


def _is_inspected(r: dict) -> bool:
    return r["status"] == "inspected"


def _names_year(url: str, year: int) -> bool:
    """A /learn article whose slug names `year` as a whole number (not 12027, not a /panchang date)."""
    parts = [p for p in urllib.parse.urlsplit(url).path.split("/") if p]
    if parts[:1] == ["hi"]:
        parts = parts[1:]
    return len(parts) == 2 and parts[0] == "learn" and re.search(rf"(?<!\d){year}(?!\d)", parts[1]) is not None


def rank_requests(rows: list[dict], limit: int = 10, today=None) -> list[dict]:
    # The next-year successor of a year-bound article (#1571) has no impressions
    # to rank by, so it sank below the stale pages and was never asked for.
    year = (today or datetime.now(timezone.utc).date()).year + 1
    picked = []
    for r in rows:
        if not _is_inspected(r) or r.get("blocked") or r.get("canonical_mismatch") is True:
            continue
        reasons = []
        ask_first = False
        if r.get("stale_in_index") is True:
            reasons.append("changed after Google's last crawl")
        if r.get("not_indexed") is True:
            reasons.append(f"not indexed: {r.get('coverageState') or r.get('verdict')}")
            if _names_year(r["url"], year):
                reasons.append(f"names {year}: ask before it has impressions")
                ask_first = True
        if reasons:
            picked.append((r, reasons, ask_first))
    picked.sort(key=lambda p: (-(p[0].get("impressions") or 0),
                               -(p[0].get("sitemap_priority") or 0), p[0]["url"]))
    # Capped at half the list so a year-end batch of new pages cannot hide every stale page.
    first = [p for p in picked if p[2]][:limit // 2]
    rest = [p for p in picked if p not in first]
    picked = [(r, why) for r, why, _ in first + rest]
    return [{"url": r["url"], "reasons": why, "impressions": r.get("impressions"),
             "changed_at": r.get("changed_at"), "lastCrawlTime": r.get("lastCrawlTime")}
            for r, why in picked[:limit]]


def counts(rows: list[dict]) -> dict:
    ins = [r for r in rows if _is_inspected(r)]
    return {
        "total": len(rows),
        "inspected": len(ins),
        # Unreached AND errored rows: either way there is no verdict to report.
        "not_inspected": len(rows) - len(ins),
        "errors": sum(1 for r in rows if r["status"] == "error"),
        "indexed": sum(1 for r in ins if r["verdict"] == "PASS"),
        "not_indexed": sum(1 for r in ins if r["not_indexed"] is True),
        "stale": sum(1 for r in ins if r["stale_in_index"] is True),
        "canonical_mismatch": sum(1 for r in ins if r["canonical_mismatch"] is True),
        "blocked": sum(1 for r in ins if r["blocked"]),
        "unknown": sum(1 for r in ins if r["not_indexed"] is None),
    }


def load_impressions(path: Path) -> dict | None:
    """{url -> impressions} from a fetch_gsc.py page export, or None if unreadable."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        return {r["page"]: int(r["impressions"]) for r in doc["rows"]}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def build_doc(result: dict, site: str, sitemap_url: str, impressions: dict | None,
              impressions_source: str | None, limit_urls: int | None = None) -> dict:
    rows = result["rows"]
    matched = None
    if impressions is not None:
        wanted = [u for u, n in impressions.items() if n > 0]
        have = {r["url"] for r in rows}
        # Reported against the pages that HAD impressions, so a URL-form mismatch
        # (trailing slash, host) shows up as a low number instead of silent zeros.
        matched = {"matched": sum(1 for u in wanted if u in have), "with_impressions": len(wanted)}
    doc = {
        "source": "gsc-url-inspection", "site": site,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sitemap_url": sitemap_url, "git_shallow": result["shallow"],
        "partial": result["partial"], "partial_reason": result["partial_reason"],
        "quota": {"calls": result["calls"], "limit_per_day": DAILY_LIMIT},
        "impressions_source": impressions_source, "impressions_matched": matched,
        "note": NOTE, "counts": counts(rows), "request_indexing": rank_requests(rows),
        "rows": rows,
    }
    if limit_urls is not None:
        doc["limit_urls"] = limit_urls
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--site", default=os.environ.get("GSC_SITE_URL", SITE))
    ap.add_argument("--sitemap-url", default=SITEMAP_URL)
    ap.add_argument("--sitemap-file", default=None, help="read the sitemap from a file (tests)")
    ap.add_argument("--impressions", default=None,
                    help="fetch_gsc.py page export to rank by (default measurements/gsc-all.json)")
    ap.add_argument("--limit-urls", type=int, default=None, help="inspect only the first N URLs")
    ap.add_argument("--root", default=str(ROOT), help="repo checkout git history is read from")
    args = ap.parse_args(argv)
    root = Path(args.root)

    try:
        xml = (Path(args.sitemap_file).read_bytes() if args.sitemap_file
               else fetch_sitemap(args.sitemap_url))
        entries = parse_sitemap(xml)
    except (OSError, ValueError, ET.ParseError, urllib.error.URLError) as e:
        print(f"fetch_index_status: sitemap unreadable: {e}", file=sys.stderr)
        return 1
    entries, off_site = same_site(entries, args.sitemap_url)
    if off_site:
        print(f"fetch_index_status: skipped {off_site} sitemap URL(s) not on "
              f"{urllib.parse.urlsplit(args.sitemap_url).netloc}", file=sys.stderr)
    if args.limit_urls is not None:
        entries = entries[:max(args.limit_urls, 0)]
    if not entries:
        print("fetch_index_status: sitemap lists zero URLs", file=sys.stderr)
        return 1

    imp_path = Path(args.impressions) if args.impressions else root / "measurements" / "gsc-all.json"
    impressions = load_impressions(imp_path)
    imp_source = None
    if impressions is not None:
        try:
            imp_source = imp_path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            imp_source = str(imp_path)

    try:
        result = run(entries, args.site, token(), root, impressions)
    except FirstCallError as e:
        print(f"fetch_index_status: first inspection refused, nothing written: {e}",
              file=sys.stderr)
        return 1
    if not any(_is_inspected(r) for r in result["rows"]):
        print(f"fetch_index_status: no URL was inspected "
              f"({result['partial_reason'] or 'every call failed'}); nothing written",
              file=sys.stderr)
        return 1

    print(json.dumps(build_doc(result, args.site, args.sitemap_url, impressions, imp_source,
                               args.limit_urls), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
