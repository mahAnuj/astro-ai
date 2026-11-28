"""The /admin/ops tab shell: which tabs exist, which one is open, the rail links
and the System Healthy block (#1133 slice 1).

Pure and stdlib-only on purpose. `TABS` is the one place a key, its label and
its order are written; the route validates `?tab=` against it and the template
loops over what `tab_links` returns, so the rail cannot list a tab the route
would refuse or the reverse.

Governance is deliberately absent: its data does not exist yet (slice 8 builds
the collector), and a rail item that opens a panel with no data is what the
issue forbids. `?tab=governance` is therefore an unknown value and lands on
Overview like any other.
"""
from __future__ import annotations

from urllib.parse import urlencode

# (key, label). Labels are the owner's words (2026-11-17); Backlog is kept
# because dropping it would lose an existing panel.
TABS: tuple[tuple[str, str], ...] = (
    ("overview", "Overview"),
    ("agents", "Agents"),
    ("workflows", "Workflows"),
    ("runs", "Runs & Traces"),
    ("backlog", "Backlog"),
    ("analytics", "Analytics"),
    ("monitoring", "Monitoring"),
)
DEFAULT = "overview"

# Which keys of the page's `ops-data` JSON blob each tab ships (#1133 slice 1,
# step 3). The blob was 438,553 B on every tab -- `cycles` 364,803 B and
# `issues` 65,675 B of it -- while only the drill-downs read them. A key is
# listed here only if a drill-down ON THAT TAB reads it:
#   cycles  -> the `.day-btn` rows (Runs)
#   issues  -> the Backlog tile (Overview) and the `#bars` buttons (Backlog)
#   today_*, filed_* -> the three "today" tiles (Overview)
#   kpi_rows -> the four KPI cards' drill-downs (Overview, #1133 slice 2a)
#   by_*    -> the `#bars` chart (Backlog)
# `repo` is read on every tab (the sheet's links). The script guards each
# omitted key (`D.cycles || []`), so a missing key is an empty drill, never a
# throw. Add a drill-down to a tab and its key to this table in one commit;
# tests/test_ops_tab_shell.py fails on a drill-down whose data is not shipped.
_BASE = frozenset({"repo"})
BLOB_KEYS: dict[str, frozenset] = {
    "overview": _BASE | {"issues", "today_shipped", "today_failed", "today_live",
                         "filed_live", "filed_today", "kpi_rows"},
    "agents": _BASE,
    "workflows": _BASE,
    "runs": _BASE | {"cycles"},
    "backlog": _BASE | {"issues", "by_priority", "by_area", "by_type"},
    "analytics": _BASE,
    "monitoring": _BASE,
}

#: The issue's acceptance criterion for slice 2: Overview is no larger than the old whole
#: page, 418,318 B in the measured render (2026-11-17). One constant, so the page-size tests
#: cannot disagree (they carried 245,000 and 250,000 literals that the open-issue count,
#: not the code, kept breaking: #1562). Trigger to slim the `issues` rows `blob_for`
#: ships: real Overview past 380,000 B.
OVERVIEW_MAX_BYTES = 418_318

_KEYS = frozenset(k for k, _ in TABS)
_LABELS = dict(TABS)


def pick_tab(raw) -> str:
    """The tab to render for a raw `?tab=` value; never raises.

    Membership in `TABS` and nothing else: an unknown value falls back to the
    default rather than 422ing, the same rule `?window=` and `?day=` follow
    (a mistyped URL must not take the control room down).
    """
    key = str(raw or "").strip().lower()
    return key if key in _KEYS else DEFAULT


def blob_for(tab: str, full: dict) -> dict:
    """`full` cut down to the keys `tab` ships; an unknown tab gets Overview's."""
    keep = BLOB_KEYS.get(tab, BLOB_KEYS[DEFAULT])
    return {k: v for k, v in full.items() if k in keep}


def tab_label(key: str) -> str:
    """The display label for an already-validated key."""
    return _LABELS.get(key, _LABELS[DEFAULT])


def tab_links(active: str, app_days, day: str) -> list[dict]:
    """The rail: one link per tab, carrying the window or the picked day.

    Takes ALREADY-VALIDATED values (`ops["app_days"]` is from `APP_WINDOWS`,
    `ops["app"]["day"]` is an ISO date from `pick_day` or ""). Nothing from the
    raw query string reaches an href through here. A picked day wins over the
    window, exactly as it does in `snapshot()`, so switching tab keeps the view.
    """
    links = []
    for key, label in TABS:
        extra = ("day", day) if day else ("window", app_days)
        links.append({
            "key": key,
            "label": label,
            "href": "?" + urlencode([("tab", key), extra]),
            "current": key == active,
        })
    return links


def health(alerts, reds, missing) -> dict:
    """The System Healthy block, from what the page already measured.

    It says only what the page checked (alerts, red count, panels whose data
    file is missing), never an unmeasured "all agents operational".
    """
    n_alerts = len(alerts or [])
    n_missing = len(missing or [])
    reds = int(reds or 0)
    if reds > 0:
        return {"state": "bad", "label": "Needs attention",
                "detail": f"{reds} red", "count": reds}
    if n_alerts or n_missing:
        n = n_alerts + n_missing
        return {"state": "watch", "label": "Needs a look",
                "detail": f"{n} finding{'' if n == 1 else 's'}", "count": n}
    return {"state": "ok", "label": "System healthy",
            "detail": "No open findings", "count": 0}
