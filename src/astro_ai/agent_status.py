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

#: One card per agent definition in .claude/agents/ (all 15, owner 2026-11-13:
#: "add cards for all agents ... we just show it upfront"), plus the merge
#: workflow, which is not an agent but is a step every change waits on.
#: (id, name, group, where it runs, role line). tests/test_agent_status.py
#: fails if a file in .claude/agents/ has no card here.
AGENTS: tuple[tuple[str, str, str, str, str], ...] = (
    ("dev-lead", "dev-lead", "build", "runs every build cycle (Agent work)", "coordinates one issue from design to a QA'd PR"),
    ("architect", "architect", "build", "called by dev-lead inside a build cycle", "designs a change before it is written"),
    ("engineer", "engineer", "build", "called by dev-lead inside a build cycle", "writes the code and commits it, unpushed"),
    ("frontend-engineer", "frontend-engineer", "build", "called by dev-lead inside a build cycle",
     "writes templates, CSS and client code"),
    ("qa", "QA", "build", "runs a QA round on every green PR", "reviews every PR before it can merge"),
    ("merge", "merge", "build", "a workflow, not an agent (Agent merge)", "merges PRs that passed QA and the gates"),
    ("chief", "chief", "decide", "woken for held PRs; oversight review (Agent sync)", "rules on PRs held for a decision"),
    ("project-manager", "project-manager", "decide", "runs the ranking (Agent prioritise)", "ranks the backlog"),
    ("product-manager", "product-manager", "decide", "leads discovery (Agent discover)", "finds and specifies what to build next"),
    ("analyst", "analyst", "measure", "runs the measurements (Agent measure)", "measures the loop and the site"),
    ("astro-auditor", "astro-auditor", "measure", "audits the rules (Agent research)", "checks astrology rules in code against the sources"),
    ("numerologist", "numerologist", "measure", "audits the numbers (Agent research)", "checks numerology tables against the sources"),
    ("steward", "steward", "operate", "checks for stalls (Agent steward)", "restarts work that has stalled"),
    ("infra-lead", "infra-lead", "operate", "reviews the platform (Agent infra)", "keeps the site up, fast and free"),
    ("conversion-lead", "conversion-lead", "on request", "chief or a session calls it for a drop-off question",
     "audits where visitors drop out"),
    ("qa-lead", "qa-lead", "on request", "chief or a session calls it when the kind of QA is unclear",
     "routes each change to the right verification"),
)
GROUPS = ("build", "decide", "measure", "operate", "on request")

#: "standby": the run this agent is called from is live, but which helper a
#: cycle is using at this minute is not visible from outside the Claude step.
STATES = ("building", "running", "standby", "queued", "blocked", "waiting", "done", "failed", "idle")
FAILED_CONCLUSIONS = {"failure", "timed_out", "cancelled", "startup_failure"}
QA_ROUND = re.compile(r"QA round: PR #(\d+)")
#: agent-work.yml's run-name for a cycle dispatched at one issue.
ISSUE_CYCLE = re.compile(r"Agent work: issue #(\d+)")
#: Cycle branches carry their issue number (CLAUDE.md: issue/, partial/, fix/).
CYCLE_BRANCH = re.compile(r"(?:issue|partial|fix)/(\d+)-")
#: How many issue titles snapshot() may fetch per refresh (one read each).
MAX_ISSUE_READS = 3
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


def _short(title: str | None, limit: int = 60) -> str:
    title = (title or "").strip()
    return title[: limit - 3].rstrip() + "…" if len(title) > limit else title


def _pr_line(pr: dict) -> str:
    title = _short(pr.get("title"))
    return f"PR #{pr.get('number')} · {title}" if title else f"PR #{pr.get('number')}"


def _issue_line(n: int | str, title: str | None) -> str:
    title = _short(title)
    return f"issue #{n} · {title}" if title else f"issue #{n}"


def _branch_issue(pr: dict) -> int | None:
    m = CYCLE_BRANCH.match(str((pr.get("head") or {}).get("ref", "")))
    return int(m.group(1)) if m else None


def cycle_issues(active: list[dict]) -> list[int]:
    """Issue numbers named by running 'Agent work: issue #N' runs, newest first."""
    seen: list[int] = []
    for r in active:
        m = ISSUE_CYCLE.search(r.get("display_title") or "")
        if m and int(m.group(1)) not in seen:
            seen.append(int(m.group(1)))
    return seen


def build(
    active: list[dict],
    prs: list[dict],
    loops: list[dict],
    *,
    issues: dict[int, str] | None = None,
    now: datetime | None = None,
    live: bool = True,
) -> dict:
    """The cards and the running workflows, from already-fetched data. Pure:
    the tests drive this. ``issues`` maps an issue number to its title, for the
    issues a running cycle names (snapshot() fetches at most MAX_ISSUE_READS)."""
    now = now or datetime.now(timezone.utc)
    issues = issues or {}
    issue_url = f"https://github.com/{GH_REPO}/issues/{{}}"
    pr_by_number = {p.get("number"): p for p in prs}
    pr_by_branch = {str((p.get("head") or {}).get("ref", "")): p for p in prs}

    def pr_for_issue(n: int) -> dict | None:
        return next((p for p in prs if _branch_issue(p) == n), None)

    def target_of(run: dict) -> dict:
        """What one run is working on: a PR, an issue, or what started it.
        Only facts GitHub states: a run-name, a branch, an open PR. Never a guess."""
        title = run.get("display_title") or ""
        m = QA_ROUND.search(title)
        if m:
            n = int(m.group(1))
            pr = pr_by_number.get(n)
            return {"kind": "pr", "number": n, "label": _pr_line(pr) if pr else f"PR #{n}",
                    "url": (pr or {}).get("html_url") or f"https://github.com/{GH_REPO}/pull/{n}"}
        m = ISSUE_CYCLE.search(title)
        if m:
            n = int(m.group(1))
            return {"kind": "issue", "number": n, "label": _issue_line(n, issues.get(n)), "url": issue_url.format(n)}
        branch = str(run.get("head_branch") or "")
        pr = pr_by_branch.get(branch) if branch and branch != "main" else None
        if pr:
            return {"kind": "pr", "number": pr.get("number"), "label": _pr_line(pr), "url": pr.get("html_url")}
        mb = CYCLE_BRANCH.match(branch)
        if mb:
            n = int(mb.group(1))
            return {"kind": "issue", "number": n, "label": _issue_line(n, issues.get(n)), "url": issue_url.format(n)}
        event = run.get("event") or ""
        label = {
            "schedule": "scheduled run",
            "workflow_run": "started by another workflow finishing",
            "push": f"push to {branch or 'a branch'}",
        }.get(event)
        if label is None:
            label = title if title and title != run.get("name") else (f"{event} run" if event else "run")
        return {"kind": "trigger", "number": None, "label": _short(label, 80), "url": run.get("html_url")}
    last = {r.get("workflow"): r for r in loops if isinstance(r, dict)}
    work_prs = [p for p in prs if not str((p.get("head") or {}).get("ref", "")).startswith(SELF_MERGING)]

    def runs_of(workflow_name: str) -> list[dict]:
        return [r for r in active if r.get("name") == workflow_name]

    def from_history(workflow: str | None, what: str) -> dict:
        row = last.get(workflow) if workflow else None
        if not row or not row.get("last_run"):
            return {"state": "idle", "detail": f"no recent {what}", "at": None}
        conclusion = row.get("last_conclusion")
        bad = conclusion in FAILED_CONCLUSIONS
        # agents.json is collected while runs are live, so its newest row can be
        # a run that had not finished, or one GitHub skipped. Say which.
        verb = ("failed" if bad else "was skipped" if conclusion == "skipped"
                else "started" if conclusion in (None, "", "in_progress", "queued") else "finished")
        return {
            "state": "failed" if bad else "done",
            "detail": f"last {what} {verb} {_ago(row['last_run'], now)}",
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
    cards: dict[str, dict] = {}

    # dev-lead. The target comes from the run itself: agent-work.yml names a
    # dispatched cycle "Agent work: issue #N". A ranked cycle (no input) picks
    # its issue inside the Claude step, so nothing outside it can know which
    # until it opens a PR, and the card says that rather than guessing.
    if build_runs:
        run = build_runs[0]
        t = target_of(run)
        if t["kind"] == "issue":
            pr = pr_for_issue(t["number"])
            detail = f"working on {t['label']}" + (f" · PR #{pr.get('number')}" if pr else "")
        elif t["kind"] == "pr":
            detail = f"working on {t['label']}"
        else:
            detail = "picking the next issue from the ranked backlog"
        cards["dev-lead"] = from_run(run, "building", detail)
        if t["kind"] != "trigger":
            cards["dev-lead"]["url"] = t["url"]
    else:
        cards["dev-lead"] = from_history("agent-work.yml", "build cycle")

    # QA
    if qa_runs:
        t = target_of(qa_runs[0])
        pr = pr_by_number.get(t["number"])
        n_issue = _branch_issue(pr) if pr else None
        cards["qa"] = from_run(qa_runs[0], "running",
                               f"reviewing {t['label']}" + (f" · issue #{n_issue}" if n_issue else ""))
        cards["qa"]["url"] = t["url"]
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
        # The sweep picks its PR inside the job (lowest number first, and it
        # skips any it cannot merge), and its run names no PR. So the card
        # counts the candidates rather than naming one it may not take.
        n = len(passed)
        what = (f"checking {n} PR{'s' if n != 1 else ''} that passed QA" if n
                else "checking for PRs that passed QA")
        cards["merge"] = from_run(merge_runs[0], "running", what)
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
    elif runs_of("Agent sync"):
        cards["chief"] = from_run(runs_of("Agent sync")[0], "running", "oversight review in progress")
    else:
        cards["chief"] = {"state": "idle", "detail": "no PR held for a ruling", "at": None}

    # helpers called inside a build cycle: standby while one runs
    for key in ("architect", "engineer", "frontend-engineer"):
        if build_runs:
            card = from_run(build_runs[0], "standby", "on call in the running build cycle")
            card["state"] = "standby" if build_runs[0].get("status") != "queued" else "queued"
            cards[key] = card
        else:
            cards[key] = {"state": "idle", "detail": "waits for the next build cycle", "at": None}

    # on request only: nothing schedules them
    for key in ("conversion-lead", "qa-lead"):
        cards[key] = {"state": "idle", "detail": "not on any schedule", "at": None}

    # the scheduled agents, one workflow each
    for key, workflow_name, workflow, what in (
        ("steward", "Agent steward", "agent-steward.yml", "check"),
        ("analyst", "Agent measure", "agent-measure.yml", "measurement"),
        ("product-manager", "Agent discover", "agent-discover.yml", "discovery run"),
        ("project-manager", "Agent prioritise", "agent-prioritise.yml", "ranking"),
        ("astro-auditor", "Agent research", "agent-research.yml", "research audit"),
        ("numerologist", "Agent research", "agent-research.yml", "research audit"),
        ("infra-lead", "Agent infra", "agent-infra.yml", "platform review"),
    ):
        running = runs_of(workflow_name)
        cards[key] = from_run(running[0], "running", f"{what} in progress") if running else from_history(workflow, what)

    agents = []
    for key, name, group, where, role in AGENTS:
        card = {"id": key, "name": name, "group": group, "where": where, "role": role, "url": None, **cards[key]}
        agents.append(card)
    counts = {s: sum(1 for a in agents if a["state"] == s) for s in STATES}
    workflows = []
    for run in sorted(active, key=lambda r: (r.get("status") != "in_progress",
                                             r.get("run_started_at") or r.get("created_at") or "")):
        at = run.get("run_started_at") or run.get("created_at")
        t = target_of(run)
        workflows.append({
            "name": run.get("name") or "workflow",
            "state": "queued" if run.get("status") == "queued" else "running",
            "target": t["label"],
            "target_kind": t["kind"],
            "target_url": t["url"],
            "at": at,
            "ago": _ago(at, now),
            "url": run.get("html_url"),
        })
    return {
        "repo": GH_REPO,
        "generated_at": now.isoformat(timespec="seconds"),
        "live": live,
        "agents": agents,
        "groups": list(GROUPS),
        "counts": counts,
        "open_prs": len(work_prs),
        "workflows": workflows,
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
            issues: dict[int, str] = {}
            for n in cycle_issues(active)[:MAX_ISSUE_READS]:
                try:
                    body = _get(f"issues/{n}")
                    issues[n] = str(body.get("title") or "") if isinstance(body, dict) else ""
                except Exception:  # noqa: BLE001 -- a missing title still names the issue
                    issues[n] = ""
            doc = build(active, prs, _loops(), issues=issues)
        # Broad on purpose, for the reason ops_data._fetch records: a narrow
        # tuple missed http.client.IncompleteRead and 500'd the whole page.
        except Exception as exc:  # noqa: BLE001
            # One line, not a traceback: this fires on every refresh while
            # GitHub is unreachable (QA note on #947).
            log.warning("agent_status: live read failed, serving the last answer: %r", exc)
            if hit:
                stale = dict(hit[1], live=False)
                _cache = (time.monotonic(), stale)
                return stale
            try:
                doc = build([], [], _loops(), live=False)
            except Exception:  # noqa: BLE001
                doc = {"repo": GH_REPO, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "live": False, "agents": [], "counts": {}, "open_prs": 0, "workflows": []}
        _cache = (time.monotonic(), doc)
        return doc
