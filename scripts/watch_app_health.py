#!/usr/bin/env python3
"""Read the live app's health from the bucket and emit it as ops findings.

WHY THIS EXISTS
---------------
The owner, 2026-11-14, seeing "10.19% of LLM calls are erroring" on /admin/ops:
"was this reported by the agent monitoring the ops dashboard?" -- it was not.
`detect_ops_regressions.py` runs from a plain checkout and lists the LLM error
rate, provider exhaustion, 413s and the fallback rate as NOT_COVERED, because
they live in the GCS event and usage logs. The only job that read the bucket
was the analyst, once a day. And the owner's follow-up: "the ops dashboard
monitoring should be more realtime vs nightly run".

So this runs in `agent-steward`, which fires after every `agent-work` cycle and
twice a day on a clock (22 runs over 11-12..11-14), already holds `id-token:
write` and `issues: write`, and already carries the findings into issues. It
authenticates with the same read-only identity the analyst uses and computes
`ops_data._app_view` -- the dashboard's own function -- then
`ops_data._app_alerts`, the dashboard's own alert rules. Same thresholds, same
words; nothing is re-implemented here.

THE WINDOW. Today so far (one UTC day), which is what "now" means for an
alarm, unless today has fewer than `MIN_CALLS` calls, when one bad request
would read as a 100% error rate; then the 7-day window, as the dashboard shows
by default. The finding's title names its window either way.

OUTPUT (--out): {"ok": bool, "days": N, "findings": [...], "why": "..."}.
`ok: false` means the bucket could not be read; `file_ops_findings.py` then
leaves the app-* issues exactly as they are rather than marking them cleared,
because an unreadable source is not a clean one.

EXIT CODES: 0 always (the document says what happened)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

MIN_CALLS = 30


def probe_bucket() -> tuple[bool, str]:
    """Can this job actually read production? Checked directly, not inferred.

    QA on #1002, and a reproduction after it: storage.get() swallows a 403 or a
    missing credential and returns None, and llm_stats/events then fall back to
    a LOCAL directory. Run with no credentials on a machine that had local
    stats, the watcher reported that machine's numbers as production's
    ("ok=True ... findings=[app-errors, ...]"). So read yesterday's
    llm_stats/<date>.json from the bucket itself: a site with traffic always
    has one, and any failure here means nothing below can be trusted."""
    from datetime import date, timedelta
    from astro_ai import storage
    name = os.environ.get("BHAGYA_STORAGE_BUCKET", "")
    if not name:
        return False, "no bucket configured"
    client = storage._client()
    if client is None:
        return False, "no GCS client (credentials missing or rejected)"
    key = f"llm_stats/{(date.today() - timedelta(days=1)).isoformat()}.json"
    try:
        client.bucket(name).blob(key).download_as_text()
    except Exception as exc:  # noqa: BLE001 - any failure is "could not read"
        return False, f"could not read gs://{name}/{key} ({exc.__class__.__name__})"
    return True, ""


def evaluate(view, probe=lambda: (True, "")) -> dict:
    """`view(days)` returns an `_app_view`-shaped dict; `probe()` says whether the
    bucket is readable at all. Pure apart from those two."""
    from astro_ai import ops_data
    readable, why = probe()
    if not readable:
        return {"ok": False, "days": 0, "findings": [], "why": why}
    app = view(1)
    days = 1
    if app.get("ok") and int(app.get("calls") or 0) < MIN_CALLS:
        app, days = view(7), 7
    if not app.get("ok"):
        return {"ok": False, "days": days, "findings": [],
                "why": "events/llm_stats could not be read from the bucket"}
    if str(app.get("store") or "").startswith("local:"):
        return {"ok": False, "days": days, "findings": [],
                "why": "no bucket configured (local store); production was not read"}
    # ZERO CALLS IS NOT A READING (QA on #1002). storage.get() swallows every
    # error -- a 403, missing credentials -- and returns None, so an unreadable
    # bucket comes back as ok:true with calls=0. Passed on, that "cleared" the
    # live error-rate issue and filed a false "No LLM calls recorded". A
    # production site with no LLM call in seven days is not a state worth
    # alarming on; a bucket this job could not read is. So: unreadable.
    if int(app.get("calls") or 0) == 0:
        return {"ok": False, "days": days, "findings": [],
                "why": "no LLM calls read in 7 days: cannot tell an idle app from an unreadable bucket"}
    findings = [{"kind": a["kind"], "level": a["level"], "title": a["title"],
                 "detail": a["detail"] + (f" Dashboard: {a['where']}." if a.get("where") else "")}
                for a in ops_data._app_alerts(app)
                if a["kind"] not in ("app-unreadable", "app-idle")]
    return {"ok": True, "days": days, "calls": int(app.get("calls") or 0),
            "error_rate": app.get("error_rate"), "findings": findings}


def main(argv: list[str], view=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    probe = lambda: (True, "")  # noqa: E731 - a test-supplied view needs no bucket
    if view is None:
        from astro_ai import ops_data
        view, probe = ops_data._app_view, probe_bucket
    try:
        doc = evaluate(view, probe)
    except Exception as exc:  # noqa: BLE001 - an unreadable source must say so, not crash the step
        doc = {"ok": False, "days": 0, "findings": [],
               "why": f"{exc.__class__.__name__}: {str(exc)[:160]}"}
    Path(a.out).write_text(json.dumps(doc, indent=1))
    print(f"app health: ok={doc['ok']} days={doc['days']} "
          f"findings={[f['kind'] for f in doc['findings']]} {doc.get('why', '')}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write(f"### App health ({doc['days']}d)\n")
            for f in doc["findings"]:
                fh.write(f"- **{f['level'].upper()}** {f['title']}\n")
            if not doc["findings"]:
                fh.write(f"- nothing raised{' — ' + doc['why'] if doc.get('why') else ''}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
