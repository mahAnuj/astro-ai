#!/usr/bin/env python3
"""Findings from the committed ops measurements — the half a loop can act on.

WHY THIS EXISTS

Asked whether any workflow reads the ops dashboard and acts on what it finds —
"the error rate, agent health, low cache hit ratio, app health, increasing
backlog and not fixing high priority issues" — the answer measured 2026-11-01
was NO. `/admin/ops` and `ops_today` appear in `.github/workflows/` only inside
comments. `grep -rn "admin/ops\\|ops_today" .github/workflows/ scripts/ .claude/`
found no caller. Every number on that page is computed for a human who has to
open it.

This is the detector half of closing that: deterministic, no model, no
credentials, exit 1 when it finds something. A carrier workflow turns findings
into issues; the judgment lives here where a test can drive it.

WHAT IT DELIBERATELY CANNOT SEE, AND WHY THAT IS STATED RATHER THAN IMPLIED

`ops_data._alerts()` builds sixteen alert types, and the ones covering the
PRODUCT — error rate, provider exhaustion, 413s, fallback rate, the daily token
ceiling — are computed at render time from GCS event and usage data. A plain
checkout cannot read any of it, and a runner would need the service-account
credentials `agent-measure.yml` holds.

So this script reports its own blind spots in `--coverage` and never implies a
clean bill of health. That is `ops_data._alerts()`'s own first rule, carried
across rather than restated: "Silence means checked-and-clear, never
not-checked. A source that could not be read emits its own alert rather than
contributing nothing, so an empty strip can be trusted."

WHAT IS NOT WATCHED HERE, AND THE CORRECTION THAT PRODUCED THIS LIST

The first draft of this script carried two more findings, `triage-debt` and
`high-priority-stalled`, both derived from `issues.json`'s `by_priority`. The
owner asked whether `agent-prioritise` already writes those labels. Checking
properly showed the first draft's reasoning was wrong, so both are gone:

  * `/prioritise` dispatches `project-manager`, whose declared tools are
    `Read, Grep, Glob, Bash, WebFetch` -- no write path at all. It produces a
    RANKED REPORT at `measurements/prioritise/latest.md`, not labels, and that
    report IS consumed: `project-manager.md:26` reads it first on every later
    run, and `/agent-cycle` Step 2 re-dispatches that agent. RANKING HAPPENS.
    It just does not happen through a label.
  * `project-manager` reads every open issue and is told "do not rank from
    issue titles". It does not filter on `priority:` either. So the claim the
    first draft shipped -- 89 of 128 unlabelled means ranking sees only 39 --
    was false.
  * The ONLY consumer of a `priority:` label is
    `issue_backlog.derive_priority()`, which exists to produce the dashboard's
    `by_priority` counter. Nothing routes, ranks or gates on it.

So the label is vestigial: written by nobody, read by one counter. A weekly
finding about it would have been a false alarm every week -- the precise
failure this file's test module argues against, shipped inside the detector
itself. It is worth one issue, once, not a recurring alert, and it is filed
that way.

Watching "a high-priority issue is not getting fixed" needs a signal the loop
actually uses, which means the ranked queue rather than the label. That is not
machine-readable today -- `latest.md` is an agent's prose -- and inventing a
parser for it here would be guessing.

CACHE HIT RATIO is a genuine gap and stays in `NOT_COVERED`: `ops_data`
computes `hits` and `misses` (~line 1306) and raises nothing at any threshold.
The number is rendered and never judged. It needs the GCS usage doc.

EXIT CODES
  0  nothing found
  1  at least one finding
  2  could not read a required measurement — NOT a pass

USAGE
  uv run python scripts/detect_ops_regressions.py [--json] [--coverage]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEASUREMENTS = ROOT / "measurements"

#: A week. Both trend findings compare the newest committed snapshot against
#: the oldest one at least this old, so a single bad day cannot fire either.
TREND_DAYS = 7

#: Delivery yield below this is the loop running and shipping nothing.
#: Measured 2026-11-01: 51% over 96 cycles. A floor well under that, because a
#: floor set near the current value fires on noise and gets ignored.
YIELD_FLOOR_PCT = 35

#: The analyst leg of `agent-measure` runs daily on a `0 21 * * *` cron. GitHub
#: delivers a scheduled run LATE, always: measured over 30 `agent-work` fires
#: 2026-10-17..11-01, min +1h42m, median +3h19m, max +6h21m, and not one inside
#: 100 minutes. So "a day old" is not a usable threshold -- 24h would fire on a
#: normal late run.
#:
#: 32h, and the arithmetic matters because the first draft got it wrong: 30h
#: was written as "a missed day plus the worst observed skew", but 24 + 6h21m
#: is 30.35h, so a run delayed by the worst skew two days running would have
#: read as stale. `test_a_NORMALLY_LATE_scheduled_run_does_not_read_as_stale`
#: asserts the relationship rather than the number, which is what caught it.
STALE_HOURS = 32

#: What this script cannot see, named so silence is never read as health. Each
#: entry is (concern, where it is computed, why a checkout cannot reach it).
NOT_COVERED = (
    ("LLM error rate", "ops_data._alerts", "GCS event log, read at render time"),
    ("provider exhaustion (the 'high demand' page)", "ops_data._alerts", "GCS event log"),
    ("RequestTooLarge / 413s", "ops_data._alerts", "GCS event log"),
    ("fallback rate", "ops_data._alerts", "GCS usage doc"),
    ("daily token ceiling", "ops_data._alerts", "GCS usage doc"),
    ("cache hit ratio", "NOTHING — computed, never alerted on",
     "GCS usage doc; see this file's header"),
    ("whether a high-priority issue is getting fixed",
     "NOTHING — and the `priority:` label cannot answer it",
     "the loop ranks from measurements/prioritise/latest.md, which is prose"),
)


def _read(name: str) -> dict:
    return json.loads((MEASUREMENTS / name).read_text(encoding="utf-8"))


def _git(*a: str) -> str:
    r = subprocess.run(("git", "-C", str(ROOT), *a),
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()[:200]}")
    return r.stdout


def _instant(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat((text or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def issue_history(days: int) -> list[tuple[datetime, dict]]:
    """(commit date, parsed issues.json) for each revision, newest first.

    Read from git rather than from the dated `measurements/*.md` files because
    the counts this compares are in the JSON and nothing guarantees a `.md`
    exists for a given day -- 2026-10-15..20 and 10-26 have none.

    A revision that cannot be parsed is SKIPPED rather than fatal: the file is
    machine-written, but a history long enough to be useful will eventually
    contain a format older than the current reader.
    """
    out: list[tuple[datetime, dict]] = []
    try:
        log = _git("log", "--format=%H %cI", "--", "measurements/issues.json")
    except RuntimeError:
        return out
    cut = datetime.now(timezone.utc) - timedelta(days=days * 3)
    for line in log.splitlines():
        sha, _, iso = line.partition(" ")
        when = _instant(iso)
        if when is None or when < cut:
            continue
        try:
            doc = json.loads(_git("show", f"{sha}:measurements/issues.json"))
        except (RuntimeError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("open"), int):
            out.append((when, doc))
    return out


def find(now: datetime | None = None) -> tuple[list[dict], list[str]]:
    """(findings, unreadable sources). Both matter; see the module header."""
    now = now or datetime.now(timezone.utc)
    findings: list[dict] = []
    unreadable: list[str] = []

    def add(kind, level, title, detail, where=""):
        findings.append({"kind": kind, "level": level, "title": title,
                         "detail": detail, "where": where})

    # --- loop liveness, straight from the collector's own verdict ----------
    try:
        agents = _read("agents.json")
    except (OSError, json.JSONDecodeError) as exc:
        unreadable.append(f"agents.json ({exc.__class__.__name__})")
        agents = {}
    else:
        gen = _instant(agents.get("generated_at", ""))
        if gen is None:
            unreadable.append("agents.json (no readable generated_at)")
        elif (now - gen) > timedelta(hours=STALE_HOURS):
            hrs = (now - gen).total_seconds() / 3600
            add("measurement-stale", "red",
                f"agents.json is {hrs:.0f}h old",
                f"The analyst leg of `agent-measure` has not committed in over "
                f"{STALE_HOURS}h, so every loop finding below is about that "
                f"snapshot and not about now.", "/admin/ops")
        # The collector already decides this; re-deriving it here would be a
        # second opinion that can disagree, which is #628 all over again.
        for wf in agents.get("alerts") or []:
            verdict = next((r.get("verdict") for r in agents.get("loops") or []
                            if r.get("workflow") == wf), "?")
            add("loop-broken", "red", f"{wf} is {verdict}",
                "`collect_agent_performance.py` flagged this loop. A loop that "
                "does not run produces nothing, and nothing is indistinguishable "
                "from a quiet day on every other tile.", "/admin/ops")
        d = agents.get("delivery") or {}
        y = d.get("yield_pct")
        if isinstance(y, (int, float)) and d.get("ok") and y < YIELD_FLOOR_PCT:
            add("delivery-yield", "amber", f"Delivery yield is {y}%",
                f"{d.get('cycles')} cycles, {(d.get('outcomes') or {}).get('shipped')} "
                f"shipped. Below {YIELD_FLOOR_PCT}% the loop is spending the "
                f"Claude cap without moving the backlog.", "/admin/ops")

    # --- the backlog, and the triage debt under it ------------------------
    try:
        issues = _read("issues.json")
    except (OSError, json.JSONDecodeError) as exc:
        unreadable.append(f"issues.json ({exc.__class__.__name__})")
        return findings, unreadable

    # NO FINDING IS DERIVED FROM `by_priority`, deliberately, and the first
    # draft of this file got that wrong. See the module header: the label is
    # written by nobody and read by one dashboard counter, so a threshold on it
    # fires forever on a number the loop never consults. `project-manager`
    # ranks from `measurements/prioritise/latest.md` and the issues themselves,
    # and is told "do not rank from issue titles" -- it does not filter on a
    # label either.
    hist = issue_history(TREND_DAYS)
    if len(hist) < 2:
        unreadable.append(
            f"issues.json history (only {len(hist)} usable revision(s); a trend needs two)")
        return findings, unreadable

    newest_when, newest = hist[0]
    older = [(w, d) for w, d in hist if (newest_when - w) >= timedelta(days=TREND_DAYS)]
    if not older:
        span_h = (newest_when - hist[-1][0]).total_seconds() / 3600
        unreadable.append(
            f"issues.json history (spans {span_h:.0f}h, needs {TREND_DAYS * 24}h for a trend)")
        return findings, unreadable

    base_when, base = older[0]
    days = (newest_when - base_when).days or 1

    # A rising count is not automatically bad -- discovery filing real work
    # raises it too -- so this is amber and says both numbers rather than
    # asserting a cause.
    if isinstance(base.get("open"), int) and newest["open"] > base["open"]:
        add("backlog-growing", "amber",
            f"Backlog rose {base['open']} -> {newest['open']} in {days}d",
            "Filing faster than closing. This is not automatically wrong -- "
            "discovery finding real work looks the same -- but it is the number "
            "the objective is judged on.", "/admin/ops")

    return findings, unreadable


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--coverage", action="store_true",
                    help="also print what this script cannot see")
    args = ap.parse_args(argv[1:])

    try:
        findings, unreadable = find()
    except Exception as exc:  # noqa: BLE001 - an unreadable detector is not a pass
        print(f"COULD NOT RUN (exit 2) — {exc.__class__.__name__}: {exc}")
        return 2

    if args.json:
        print(json.dumps({"findings": findings, "unreadable": unreadable,
                          "not_covered": [list(n) for n in NOT_COVERED]}, indent=2))
    else:
        order = {"red": 0, "amber": 1}
        for f in sorted(findings, key=lambda f: order.get(f["level"], 9)):
            print(f"{f['level'].upper():5} [{f['kind']}] {f['title']}")
            print(f"      {f['detail']}")
        for u in unreadable:
            print(f"UNREAD      {u}")
        if args.coverage:
            print("\nNOT COVERED by this script — silence here is not health:")
            for concern, where, why in NOT_COVERED:
                print(f"  - {concern}: computed by {where} ({why})")
        if not findings and not unreadable:
            print("No findings, and every source was readable.")

    # Unreadable counts as a finding. A detector that exits 0 because it could
    # not look is the failure this repo keeps finding one layer up.
    return 1 if (findings or unreadable) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
