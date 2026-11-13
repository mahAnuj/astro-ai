"""What each agent is doing right now: the "Agents right now" cards.

Shown on /admin/ops and served as JSON at /api/agents/status, which
anujmahajan.com's /agent-cycle page reads, so one function decides every
card on both. The repository is public, so nothing here is more than GitHub
already shows: workflow run titles, PR numbers, titles and labels.

WHERE EACH STATE COMES FROM
---------------------------
Live, three GitHub API reads per refresh (never more):

    actions/runs?status=in_progress   what is running
    actions/runs?status=queued        what is waiting for a runner
    pulls?state=open                  PR labels: qa-fail, needs-human-review,
                                      qa-pass, chief-cleared

and, for an agent that is not running, its last run and result from the
committed `measurements/agents.json` (via `ops_data._fetch`), which
`agent-measure` refreshes after build cycles. Asking the API for each
workflow's last run would cost one read per agent, ~8 more per refresh,
against the 60/hour unauthenticated budget this page already shares
(ops_data.py, ARCHITECTURE.md 2026-10-18 and 2026-10-30).

So a refresh is 3 reads, cached CACHE_TTL: 60 s with OPS_GH_TOKEN, 300 s
without (36 reads/hour at most). One lock, re-checked inside, so concurrent
cold renders spend one refresh between them, the #450 pattern. Any failure
returns the last good answer marked `live: false`, or cards built from
agents.json alone; it never raises into the page.

STATES (one colour each, the same on both pages)
------------------------------------------------
    building  a build cycle is running (developer)
    running   any other agent run in progress
    queued    a run is waiting for a runner
    blocked   needs something before it can move: a failed QA round with no
              fix, or a hold only chief can clear
    waiting   ready for the next agent: a PR to review, a PR to merge
    done      last run succeeded
    failed    last run failed, timed out or was cancelled
    idle      nothing to do and no recorded run
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any

from astro_ai import ops_data

log = logging.getLogger(__name__)

GH_REPO = ops_data.GH_REPO
API = f"https://api.github.com/repos/{GH_REPO}"
GH_TOKEN = os.environ.get("OPS_GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or None
HTTP_TIMEOUT = 4.0
CACHE_TTL = float(os.environ.get("AGENT_STATUS_TTL") or (60 if GH_TOKEN else 300))

#: The cards, in display order: (id, name, workflow file or None, role line).
AGENTS: tuple[tuple[str, str, str | None, str], ...] = (
    ("developer", "developer", "agent-work.yml", "builds the next issue, end to end"),
    ("qa", "QA", None, "reviews every PR before it can merge"),
    ("merge", "merge", "agent-merge.yml", "merges PRs that passed QA and the gates"),
    ("chief", "chief", None, "rules on PRs held for a decision"),
    ("steward", "steward", "agent-steward.yml", "restarts work that has stalled"),
    ("analyst", "analyst", "agent-measure.yml", "measures the loop and the site"),
    ("discover", "discover", "agent-discover.yml", "finds what to build next"),
    ("prioritise", "prioritise", "agent-prioritise.yml", "ranks the backlog"),
)

STATES = ("building", "running", "queued", "blocked", "waiting", "done", "failed", "idle")
FAILED_CONCLUSIONS = {"failure", "timed_out", "cancelled", "startup_failure"}
QA_ROUND = re.compile(r"QA round: PR #(\d+)")
#: Branches whose PRs self-merge without QA (CLAUDE.md: measurement PRs).
SELF_MERGING = ("measurements/",)


def _ago(ts: str | None, now: datetime) -> str:
    if not ts:
        return ""
    try:
        then = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ""
    s = max(0, int((now - then).total_seconds()))
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


def _labels(pr: dict) -> set[str]:
    return {lab.get("name", "") for lab in pr.get("labels") or []}


def _pr_line(pr: dict) -> str:
    title = (pr.get("title") or "").strip()
    if len(title) > 60:
        title = title[:57].rstrip() + "…"
    return f"PR #{pr.get('number')} · {title}" if title else f"PR #{pr.get('number')}"


def build(
    active: list[dict],
    prs: list[dict],
    loops: list[dict],
    *,
    now: datetime | None = None,
    live: bool = True,
) -> dict:
    """The cards, from already-fetched data. Pure: the tests drive this."""
    now = now or datetime.now(timezone.utc)
    last = {r.get("workflow"): r for r in loops if isinstance(r, dict)}
    work_prs = [p for p in prs if not str((p.get("head") or {}).get("ref", "")).startswith(SELF_MERGING)]

    def runs_of(workflow_name: str) -> list[dict]:
        return [r for r in active if r.get("name") == workflow_name]

    def from_history(workflow: str | None, what: str) -> dict:
        row = last.get(workflow) if workflow else None
        if not row or not row.get("last_run"):
            return {"state": "idle", "detail": f"no recent {what}", "at": None}
        bad = row.get("last_conclusion") in FAILED_CONCLUSIONS
        return {
            "state": "failed" if bad else "done",
            "detail": f"last {what} {'failed' if bad else 'finished'} {_ago(row['last_run'], now)}",
            "at": row["last_run"],
            "url": f"https://github.com/{GH_REPO}/actions/workflows/{workflow}",
        }

    def from_run(run: dict, state: str, detail: str) -> dict:
        at = run.get("run_started_at") or run.get("created_at")
        verb = "queued" if run.get("status") == "queued" else "started"
        return {
            "state": "queued" if run.get("status") == "queued" else state,
            "detail": f"{detail} · {verb} {_ago(at, now)}",
            "at": at,
            "url": run.get("html_url"),
        }

    work_runs = runs_of("Agent work")
    build_runs = [r for r in work_runs if not QA_ROUND.search(r.get("display_title") or "")]
    qa_runs = [r for r in work_runs if QA_ROUND.search(r.get("display_title") or "")]
    failed_qa = [p for p in work_prs if "qa-fail" in _labels(p)]
    held = [p for p in work_prs if "needs-human-review" in _labels(p) and "chief-cleared" not in _labels(p)]
    passed = [p for p in work_prs if "qa-pass" in _labels(p) and "needs-human-review" not in _labels(p)]
    unreviewed = [p for p in work_prs if not _labels(p) & {"qa-pass", "qa-fail"} and not p.get("draft")]
    newest_cycle_pr = next(
        (p for p in work_prs if re.match(r"(issue|partial|fix)/\d+", str((p.get("head") or {}).get("ref", "")))),
        None,
    )

    cards: dict[str, dict] = {}

    # developer
    if build_runs:
        detail = f"working on {_pr_line(newest_cycle_pr)}" if newest_cycle_pr else "building the next ranked issue"
        cards["developer"] = from_run(build_runs[0], "building", detail)
    else:
        cards["developer"] = from_history("agent-work.yml", "build cycle")

    # QA
    if qa_runs:
        n = QA_ROUND.search(qa_runs[0].get("display_title") or "").group(1)
        cards["qa"] = from_run(qa_runs[0], "running", f"reviewing PR #{n}")
    elif failed_qa:
        p = failed_qa[0]
        more = f" (+{len(failed_qa) - 1} more)" if len(failed_qa) > 1 else ""
        cards["qa"] = {"state": "blocked", "detail": f"{_pr_line(p)} failed QA: waiting for a fix{more}",
                       "at": p.get("updated_at"), "url": p.get("html_url")}
    elif unreviewed:
        p = unreviewed[0]
        cards["qa"] = {"state": "waiting", "detail": f"{_pr_line(p)} waiting for review",
                       "at": p.get("updated_at"), "url": p.get("html_url")}
    else:
        cards["qa"] = {"state": "idle", "detail": "nothing waiting for review", "at": None}

    # merge
    merge_runs = runs_of("Agent merge")
    if merge_runs:
        cards["merge"] = from_run(merge_runs[0], "running", "checking PRs that passed QA")
    elif passed:
        p = passed[0]
        cards["merge"] = {"state": "waiting", "detail": f"{_pr_line(p)} passed QA, ready to merge",
                          "at": p.get("updated_at"), "url": p.get("html_url")}
    else:
        cards["merge"] = from_history("agent-merge.yml", "merge run")

    # chief
    if held:
        p = held[0]
        more = f" (+{len(held) - 1} more)" if len(held) > 1 else ""
        cards["chief"] = {"state": "blocked", "detail": f"{_pr_line(p)} held for a ruling{more}",
                          "at": p.get("updated_at"), "url": p.get("html_url")}
    else:
        cards["chief"] = {"state": "idle", "detail": "no PR held for a ruling", "at": None}

    # the scheduled agents
    for key, workflow_name, workflow, what in (
        ("steward", "Agent steward", "agent-steward.yml", "check"),
        ("analyst", "Agent measure", "agent-measure.yml", "measurement"),
        ("discover", "Agent discover", "agent-discover.yml", "discovery run"),
        ("prioritise", "Agent prioritise", "agent-prioritise.yml", "ranking"),
    ):
        running = runs_of(workflow_name)
        cards[key] = from_run(running[0], "running", f"{what} in progress") if running else from_history(workflow, what)

    agents = []
    for key, name, _workflow, role in AGENTS:
        card = {"id": key, "name": name, "role": role, "url": None, **cards[key]}
        agents.append(card)
    counts = {s: sum(1 for a in agents if a["state"] == s) for s in STATES}
    return {
        "repo": GH_REPO,
        "generated_at": now.isoformat(timespec="seconds"),
        "live": live,
        "agents": agents,
        "counts": counts,
        "open_prs": len(work_prs),
    }


# ── fetching ──────────────────────────────────────────────────────────────

_cache: tuple[float, dict] | None = None
_lock = threading.Lock()


def _get(path: str) -> Any:
    req = urllib.request.Request(f"{API}/{path}", headers={"Accept": "application/vnd.github+json",
                                                        "User-Agent": "shubhagya-ops"})
    if GH_TOKEN:
        req.add_header("Authorization", f"Bearer {GH_TOKEN}")
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:  # noqa: S310 -- fixed https host
        return json.loads(resp.read().decode("utf-8"))


def _loops() -> list[dict]:
    doc = ops_data._fetch("agents.json")
    return doc["loops"] if isinstance(doc, dict) and isinstance(doc.get("loops"), list) else []


def snapshot() -> dict:
    """The cards, refreshed at most every CACHE_TTL. Never raises."""
    global _cache
    hit = _cache
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]
    with _lock:
        hit = _cache
        if hit and time.monotonic() - hit[0] < CACHE_TTL:
            return hit[1]
        try:
            active = []
            for status in ("in_progress", "queued"):
                body = _get(f"actions/runs?status={status}&per_page=30")
                active += (body.get("workflow_runs") or []) if isinstance(body, dict) else []
            prs = _get("pulls?state=open&per_page=50")
            prs = prs if isinstance(prs, list) else []
            doc = build(active, prs, _loops())
        # Broad on purpose, for the reason ops_data._fetch records: a narrow
        # tuple missed http.client.IncompleteRead and 500'd the whole page.
        except Exception as exc:  # noqa: BLE001
            log.warning("agent_status: live read failed, serving the last answer: %s", exc, exc_info=True)
            if hit:
                stale = dict(hit[1], live=False)
                _cache = (time.monotonic(), stale)
                return stale
            try:
                doc = build([], [], _loops(), live=False)
            except Exception:  # noqa: BLE001
                doc = {"repo": GH_REPO, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "live": False, "agents": [], "counts": {}, "open_prs": 0}
        _cache = (time.monotonic(), doc)
        return doc
