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

CACHE HIT RATIO AND THE DAILY TOKEN CEILING were gaps in `NOT_COVERED` until
2026-11-06: `ops_data` computed them and raised nothing. They are judged now from
measurements/llm-usage.json (`cache-low`, `token-ceiling`), which
scripts/collect_llm_usage.py writes from the GCS usage doc in agent-measure.

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

sys.path.insert(0, str(ROOT / "src"))

from astro_ai.ops_data import _last_run_failed  # noqa: E402

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

#: Weekly Claude quota at or above this is a finding (2026-11-03). Every agent
#: shares ONE Claude Max subscription, and the seven-day window is the one that
#: binds (measured that day: 69%). Kept equal to ops_data.CLAUDE_QUOTA_ALERT so
#: the page and the loop alarm at the same number; a test pins it.
CLAUDE_QUOTA_ALERT = 0.85
#: The loop spending this share of its cycle time WITHOUT a result (a merged or
#: open PR, or a QA verdict) over loop.json's waste window is a finding. Measured
#: 2026-11-03 across 138 cycles: ~47% (1,303 + 440 of ~4,600 minutes).
WASTE_SHARE_ALERT = 0.40
#: ...and only once there are enough cycles for a share to mean anything.
WASTE_MIN_CYCLES = 5
#: The build lane idle this share of the window, with work open, is a finding.
IDLE_SHARE_ALERT = 0.75
#: Of the last STARVED_WINDOW build cycles, how many ending "nothing" means the
#: lane is starved rather than unlucky. 2026-11-10 ran 01:53 pr open, 02:06
#: nothing, 04:30 pr open, 05:02 nothing: the empties ALTERNATED with the one
#: item every cycle circled, so a "two in a row" rule never fires on it.
STARVED_WINDOW = 4
STARVED_EMPTY = 2
#: The app's own Groq budget and cache (owner, 2026-11-06: "monitor the cache usage
#: and see if it can increase the caching to reduce the token usage"). From
#: measurements/llm-usage.json, written by scripts/collect_llm_usage.py in
#: agent-measure's analyst job, the only job with GCS credentials. Absent file =
#: not collected yet = no finding; these are judged only once a reading exists.
CACHE_HIT_ALERT_PCT = 50       # overall, over the file's window (7 days)
CACHE_MIN_CALLS = 200
ROUTE_HIT_ALERT_PCT = 30       # any one route
ROUTE_MIN_CALLS = 50
GROQ_TPD = 200_000             # CLAUDE.md, "Token budget": the daily rashifal path's ceiling
TOKEN_DAY_ALERT = 0.80
#: `main-red-suspected` (2026-11-09): one test failing on this many open PRs at
#: once. Two is enough -- two unrelated diffs failing the same test is the
#: defect living on `main`, which is what #797 left for seven PRs overnight.
SHARED_FAILURE_MIN_PRS = 2

#: What this script cannot see, named so silence is never read as health. Each
#: entry is (concern, where it is computed, why a checkout cannot reach it).
NOT_COVERED = (
    ("LLM error rate", "ops_data._alerts", "GCS event log, read at render time"),
    ("provider exhaustion (the 'high demand' page)", "ops_data._alerts", "GCS event log"),
    ("RequestTooLarge / 413s", "ops_data._alerts", "GCS event log"),
    ("fallback rate", "ops_data._alerts", "GCS usage doc"),
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


def issue_history(days: int, now: datetime | None = None) -> list[tuple[datetime, dict]]:
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
    # ONE clock per run: `find()` passes its `now` down. A second
    # `datetime.now()` here made the window drift away from the fixture's
    # clock and the test suite a time bomb (the agents.json leg went red
    # ~31h after #639 landed, on every PR at once).
    cut = (now or datetime.now(timezone.utc)) - timedelta(days=days * 3)
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
        # #738 item 1. `alerts` grades the SCHEDULE, so a weekly loop whose
        # last run was red between slots (`not-due-yet` / `ok` + `last_run_health:
        # red`) is in no alert and this carrier filed nothing, while /admin/ops
        # showed it amber. The predicate is ops_data's own -- one fact, one
        # definition, so the page and the issue cannot disagree (#628).
        #
        # ONE finding naming every such loop: the carrier files one issue per
        # `kind` and drops repeats, so a finding per loop would announce only
        # the first and hide the rest.
        flagged = set(agents.get("alerts") or [])
        failed = sorted(r.get("workflow") or "?" for r in agents.get("loops") or []
                        if _last_run_failed(r) and r.get("workflow") not in flagged)
        if failed:
            add("loop-last-run-failed", "amber",
                f"{', '.join(failed)}: last run failed",
                "The schedule verdict is fine, so `agents.json` raised no alert, but the "
                "most recent run of each loop named here was red. A weekly loop is not "
                "re-run before its next slot, so nothing else will notice. Check whether "
                "a fix has landed since; if one has, dispatch the workflow.", "/admin/ops")
        d = agents.get("delivery") or {}
        y = d.get("yield_pct")
        if isinstance(y, (int, float)) and d.get("ok") and y < YIELD_FLOOR_PCT:
            add("delivery-yield", "amber", f"Delivery yield is {y}%",
                f"{d.get('cycles')} cycles, {(d.get('outcomes') or {}).get('shipped')} "
                f"shipped. Below {YIELD_FLOOR_PCT}% the loop is spending the "
                f"Claude cap without moving the backlog.", "/admin/ops")

    # --- the Claude subscription and the loop's time (2026-11-03) -----------
    # Owner: "the agent monitoring the ops dashboard should look at these data
    # to take action and finetune". Each finding names the lever, so the issue
    # the carrier files from it is workable rather than a status report.
    try:
        usage = _read("claude_usage.json")
    except (OSError, json.JSONDecodeError) as exc:
        unreadable.append(f"claude_usage.json ({exc.__class__.__name__})")
    else:
        latest = usage.get("latest") or {}
        seven = latest.get("seven_day")
        rejected = usage.get("rejected_runs") or []
        if isinstance(seven, (int, float)) and (seven >= CLAUDE_QUOTA_ALERT or rejected):
            add("claude-quota", "red" if rejected else "amber",
                f"Claude weekly quota {round(seven * 100)}% used",
                f"Every agent shares one Claude Max subscription. "
                f"{len(rejected)} run(s) in the sample hit a limit. Levers, cheapest "
                f"first: stop dispatching ranked (`/agent-cycle`) cycles that end in "
                f"nothing; space out the weekly agent loops; keep QA rounds to one "
                f"per head. Do not add a parallel build lane until it resets.", "/admin/ops")
    # --- the app's Groq budget and cache (2026-11-06) ------------------------
    try:
        llm = _read("llm-usage.json")
    except FileNotFoundError:
        llm = None                        # not collected yet: judge nothing
    except (OSError, json.JSONDecodeError) as exc:
        llm = None
        unreadable.append(f"llm-usage.json ({exc.__class__.__name__})")
    if llm:
        calls, rate = int(llm.get("total_calls") or 0), int(llm.get("hit_rate_pct") or 0)
        cold = [r for r in llm.get("by_route") or []
                if int(r.get("calls") or 0) >= ROUTE_MIN_CALLS
                and int(r.get("hit_rate_pct") or 0) < ROUTE_HIT_ALERT_PCT]
        if (calls >= CACHE_MIN_CALLS and rate < CACHE_HIT_ALERT_PCT) or cold:
            worst = ", ".join(f"{r['route']} {r['hit_rate_pct']}% of {r['calls']} calls "
                              f"(~{r.get('tokens_per_miss', 0)} tok/miss)" for r in cold[:4])
            add("cache-low", "amber",
                f"LLM cache hit rate {rate}% over {llm.get('days')}d"
                + (f"; cold routes: {len(cold)}" if cold else ""),
                f"{calls} calls, {llm.get('cache_misses')} misses. Every miss spends Groq "
                f"free-tier tokens. Cold routes: {worst or 'none below the route floor'}. "
                f"Levers, cheapest first: normalise the cache key (date, rashi, language) so "
                f"equivalent requests share an entry; lengthen the TTL where the output is "
                f"date-stable; precompute the shared part in a scheduled Claude Code job (the "
                f"#515 nightly-rashifal pattern) and serve it from cache; keep the shared "
                f"prompt prefix ahead of the per-request part. Measure tokens before and "
                f"after with scripts/verify_token_budget.py.", "/admin/ops")
        peak = llm.get("peak_day_tokens")
        if isinstance(peak, (int, float)) and peak >= GROQ_TPD * TOKEN_DAY_ALERT:
            add("token-ceiling", "red" if peak >= GROQ_TPD else "amber",
                f"Peak day used {round(peak / GROQ_TPD * 100)}% of the Groq daily budget",
                f"{int(peak)} tokens on {llm.get('peak_day')} against ~{GROQ_TPD} TPD per "
                f"model (CLAUDE.md, \"Token budget\"). Overshooting it is an outage, not "
                f"slowness. Raise the cache hit rate first (see cache-low); move bulk generation "
                f"to a scheduled Claude Code job; never widen a prompt to fill the gap. Adding "
                f"a model is the owner's decision.", "/admin/ops")
    try:
        loop = _read("loop.json")
    except (OSError, json.JSONDecodeError) as exc:
        unreadable.append(f"loop.json ({exc.__class__.__name__})")
        loop = {}
    w = loop.get("waste") or {}
    share = w.get("share_without_result")
    if isinstance(share, (int, float)) and (w.get("cycles") or 0) >= WASTE_MIN_CYCLES \
            and share >= WASTE_SHARE_ALERT:
        m = w.get("minutes_by_outcome") or {}
        add("cycle-waste", "amber",
            f"{round(share * 100)}% of cycle time produced no result in {w.get('days')}d",
            f"{round(w.get('minutes_without_result') or 0)} of {round(w.get('minutes_total') or 0)} "
            f"minutes: nothing {round(m.get('nothing') or 0)}, failed {round(m.get('failed') or 0)}, "
            f"unknown {round(m.get('unknown') or 0)}. Read the `nothing` rows in loop.json by "
            f"`kind` -- a ranked cycle that keeps standing down is a ranking problem, an issue "
            f"cycle that does is an issue that is not workable as written.", "/admin/ops")
    idle = w.get("build_idle_share")
    if isinstance(idle, (int, float)) and idle >= IDLE_SHARE_ALERT:
        add("loop-idle", "amber",
            f"Build lane idle {round(idle * 100)}% of the last {w.get('days')}d",
            f"{w.get('build_idle_hours')}h with no build cycle running. With a backlog open "
            f"that is unused capacity: the schedule, not the work, is the limit. Check the "
            f"Claude weekly quota first -- if it has headroom, more cron slots in "
            f"agent-work.yml are the lever; if not, idle is the right answer.", "/admin/ops")

    # --- the build lane is starved (2026-11-10) ------------------------------
    # Build cycles that build nothing are not idle capacity (that is loop-idle)
    # but an empty workable queue. Measured that day: 63 of 112
    # open issues failed the Evidence Block gate, so the ranker had nothing it
    # was allowed to hand over. chain_cycle.py dispatches the retrofit itself;
    # this makes the state visible on /admin/ops and in the ops issue.
    builds = sorted((r for r in loop.get("rows") or []
                     if r.get("kind") != "qa-round" and r.get("started")),
                    key=lambda r: r["started"])[-STARVED_WINDOW:]
    empty = [r for r in builds if r.get("outcome") == "nothing"]
    if len(builds) == STARVED_WINDOW and len(empty) >= STARVED_EMPTY:
        add("loop-starved", "amber",
            f"{len(empty)} of the last {STARVED_WINDOW} build cycles built nothing",
            f"Empty cycles started {', '.join(r['started'][:16] for r in empty)}. Usually the "
            f"ranker has only one or two items it may hand over because the rest fail "
            f"scripts/verify_issue_evidence.py, which the cycle may not fix for itself. Lever: "
            f"agent-prioritise.yml with mode=evidence (chain_cycle.py dispatches it once 3+ "
            f"open issues fail the gate, at most once per 6h); check its last run, then "
            f"scripts/evidence_backlog.py for what is left.", "/admin/ops")

    # --- one test red on several PRs = `main` is red (2026-11-09) -----------
    # `collect_gate_failures.py` tallies the pytest failures on every open PR's
    # gates. A test failing on two PRs with unrelated diffs is on `main`; each
    # PR alone reads it as its own defect, and a red PR gets no QA round. #797
    # left seven PRs red on one date-dependent test overnight while nothing
    # connected them -- this is the connection.
    try:
        gates = _read("gate_failures.json")
    except FileNotFoundError:
        gates = None                      # not collected yet: judge nothing
    except (OSError, json.JSONDecodeError) as exc:
        gates = None
        unreadable.append(f"gate_failures.json ({exc.__class__.__name__})")
    if gates:
        gen = _instant(gates.get("generated_at", ""))
        if gen is None or (now - gen) > timedelta(hours=STALE_HOURS):
            unreadable.append("gate_failures.json (stale or no generated_at)")
        else:
            if gates.get("fetch_failed") and not gates.get("logs_fetched"):
                unreadable.append(f"gate_failures.json (all {gates['fetch_failed']} "
                                  f"job-log fetches failed)")
            shared = [r for r in gates.get("by_test") or []
                      if len(r.get("prs") or []) >= SHARED_FAILURE_MIN_PRS]
            if shared:
                names = "; ".join(f"`{r['test']}` on " + ", ".join(f"#{n}" for n in r["prs"])
                                  for r in shared[:5])
                add("main-red-suspected", "red",
                    f"{len(shared)} test(s) fail on {SHARED_FAILURE_MIN_PRS}+ open PRs at once",
                    f"{names}. The same test failing on PRs with unrelated diffs is a defect "
                    f"on `main`, not in any of them -- do not fix it per PR. Reproduce on "
                    f"`origin/main` with `uv run pytest <test>`; if it passes, suspect the "
                    f"clock (a date or timezone the test and the code disagree on, as with "
                    f"#797's IST fixture against a UTC-keyed cache) and re-run it with the "
                    f"date skewed. Fix once, on one branch; the PRs go green on their next "
                    f"gates run.", "measurements/gate_failures.json")

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
    hist = issue_history(TREND_DAYS, now)
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


def main(argv: list[str], now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--coverage", action="store_true",
                    help="also print what this script cannot see")
    args = ap.parse_args(argv[1:])

    try:
        findings, unreadable = find(now)
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
