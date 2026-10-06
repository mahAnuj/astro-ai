#!/usr/bin/env python3
"""Probe an issue's `repro:` steps against live production, several times.

WHY THIS EXISTS
---------------
An open issue is not evidence that the problem still exists. `BACKLOG.md` has
recorded 36 open against 50 actual, and `project-manager`'s own definition says
titles lie. Every "verified" in this repo has historically meant verified against
`origin/main`; the last mile was done by hand, or not at all.

#266 is why the sample count is not 1. It was asserted to be a total outage from
its OPEN state alone. One page load looked fine. Two probes with different birth
data returned a 200 and a 503, and a retry of the failing one succeeded 26
seconds later. A single request would have closed it falsely; a single page load
would have left it open and wrongly described. The fault is intermittent, which
is a different bug from a deterministic one, with a different cause and fix.

So: several samples, varied inputs, and INTERMITTENT reported as its own verdict.

WHAT IT DOES NOT DO
-------------------
It does not close, label or comment. It prints a verdict and exits. The caller
decides, and in this repo a human closes.

THE REPRO GRAMMAR
-----------------
One `repro:` line in the issue's Evidence Block. Two shapes:

    repro: GET /kundli -> 200 contains "Lagna"
    repro: POST /reading birth_date=1990-01-15 birth_time=10:30 birth_place=Delhi
           -> follow -> 200 contains "Lagna" absent "high demand"

`-> follow` carries cookies through the 303 to GET /kundli. The chart lives in a
cookie and the LLM runs on the redirect target, so a POST alone proves nothing.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://shubhagya.com"
TIMEOUT = 180
# Varied inputs so a probe cannot pass by hitting one lucky code path: #266
# failed on a 1975 Chennai chart and passed on a 1990 Delhi one in the same
# minute. Every sample must be DISTINCT, not a cycle through a fixed list —
# repeating a fixture hits the cache and never reaches the LLM, so samples 4 and
# 5 of a 3-fixture cycle came back byte-identical to 1 and 2 and proved nothing
# about the path that was failing.
_PLACES = ["Delhi", "Chennai", "Mumbai", "Kolkata", "Jaipur", "Pune", "Lucknow", "Kochi"]


def fixture(i: int) -> dict:
    """A distinct birth chart per sample index. Spread across years, times of
    day and longitudes, since the failing request is the large one and size
    varies with dasha depth and place."""
    return {
        "name": f"S{i + 1}",
        "birth_date": f"{1962 + (i * 7) % 48:04d}-{1 + (i * 5) % 12:02d}-{1 + (i * 11) % 28:02d}",
        "birth_time": f"{(i * 9) % 24:02d}:{(i * 17) % 60:02d}",
        "birth_place": _PLACES[i % len(_PLACES)],
    }


def issue_body(n: int) -> str:
    out = subprocess.run(
        ["gh", "issue", "view", str(n), "--json", "body,title,comments"],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        sys.exit(f"gh issue view {n} failed: {out.stderr.strip()[:200]}")
    d = json.loads(out.stdout)
    # Comments matter: several in this repo carry corrections that invert the
    # original finding, and a repro added in a comment is the current one.
    parts = [d.get("body") or ""] + [c.get("body") or "" for c in d.get("comments", [])]
    return "\n".join(parts)


def parse_repro(text: str) -> dict | None:
    """Last `repro:` wins — a correction in a comment supersedes the body."""
    found = None
    for raw in re.findall(r"^\s*repro:\s*(.+?)(?:\n\s*\w+:|\Z)", text, re.M | re.S):
        line = " ".join(raw.split())
        m = re.match(r"(GET|POST)\s+(\S+)(.*)", line, re.I)
        if not m:
            continue
        method, path, rest = m.group(1).upper(), m.group(2), m.group(3)
        spec: dict = {"method": method, "path": path, "follow": "-> follow" in rest.lower()}
        spec["form"] = dict(
            kv.split("=", 1) for kv in re.findall(r"(\w+=[^\s]+)", rest.split("->")[0])
        )
        st = re.search(r"->\s*(?:follow\s*->\s*)?(\d{3})", rest)
        spec["status"] = int(st.group(1)) if st else 200
        spec["contains"] = re.findall(r'contains\s+"([^"]+)"', rest, re.I)
        spec["absent"] = re.findall(r'absent\s+"([^"]+)"', rest, re.I)
        found = spec
    return found


def one_sample(spec: dict, fixture: dict) -> tuple[bool, str]:
    """Run the repro once with its own cookie jar. Returns (passed, detail)."""
    jar = http.cookiejar.CookieJar()
    # 303 -> GET is what urllib does by default, and it keeps the jar.
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    url = SITE + spec["path"] if spec["path"].startswith("/") else spec["path"]
    data = None
    if spec["method"] == "POST":
        form = {k: (fixture.get(k) or v) for k, v in (spec["form"] or {}).items()}
        for k, v in fixture.items():
            form.setdefault(k, v)
        data = urllib.parse.urlencode(form).encode()

    try:
        req = urllib.request.Request(url, data=data, method=spec["method"],
                                     headers={"User-Agent": "astro-ai-validate/1"})
        with opener.open(req, timeout=TIMEOUT) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", "replace") if e.fp else ""
    except Exception as e:  # noqa: BLE001 — a probe must never raise
        # ERRORED, not FAILED. A prober that cannot run is inconclusive; counting
        # it as a reproduction would send an engineer after a bug that does not
        # exist, which is strictly worse than reporting nothing. An earlier
        # revision of this file passed `context=` to opener.open(), crashed on
        # every sample, and confidently reported REPRODUCES — deterministic.
        return None, f"{type(e).__name__}: {e}"

    if status != spec["status"]:
        return False, f"HTTP {status} (wanted {spec['status']})"
    missing = [s for s in spec["contains"] if s.lower() not in body.lower()]
    present = [s for s in spec["absent"] if s.lower() in body.lower()]
    if missing:
        return False, f"HTTP {status}, missing {missing!r}"
    if present:
        return False, f"HTTP {status}, found forbidden {present!r}"
    return True, f"HTTP {status}, {len(body)}b"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("issue", type=int)
    ap.add_argument("--samples", type=int, default=5)
    args = ap.parse_args()

    spec = parse_repro(issue_body(args.issue))
    if not spec:
        # Not a pass and not a fail. An issue with no executable repro cannot be
        # validated, and that is a discovery defect, not a verdict on the bug.
        print(f"#{args.issue}  NO-REPRO — no executable `repro:` line found")
        print("  -> label needs-evidence; route back to discovery")
        return 3

    print(f"#{args.issue}  {spec['method']} {spec['path']}"
          f"{' -> follow' if spec['follow'] else ''}  x{args.samples}")
    results = []
    for i in range(args.samples):
        fx = fixture(i)
        ok, detail = one_sample(spec, fx)
        results.append(ok)
        mark = "pass" if ok else ("ERR " if ok is None else "FAIL")
        print(f"  {i + 1}/{args.samples}  {mark}  "
              f"[{fx['name']} {fx['birth_date']} {fx['birth_place']}]  {detail}")

    errored = sum(1 for r in results if r is None)
    ran = [r for r in results if r is not None]
    passed = sum(1 for r in ran if r)
    print()
    if errored:
        print(f"  {errored}/{args.samples} samples could not run — the probe is broken, "
              f"not necessarily the feature")
        if not ran:
            print("  INCONCLUSIVE — fix the probe before drawing any verdict")
            print("  -> do NOT label, do NOT close, do NOT queue work from this")
            return 4
        print(f"  verdict below rests on the {len(ran)} sample(s) that ran")
    if ran and passed == len(ran):
        print(f"  CANNOT-REPRODUCE — {passed}/{len(ran)} passed")
        print("  -> comment with these samples, label cannot-reproduce, DO NOT close")
        return 1
    if passed == 0:
        print(f"  REPRODUCES — 0/{len(ran)} passed, deterministic")
        return 0
    print(f"  INTERMITTENT — {passed}/{len(ran)} passed "
          f"({100 * passed // len(ran)}% hit rate)")
    print("  -> a different bug from a deterministic one; say so on the issue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
