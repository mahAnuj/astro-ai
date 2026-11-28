"""The four KPI cards at the top of /admin/ops Overview (#1133 slice 2a).

Cycles shipped, first-pass QA rate, cost per successful outcome, PRs merged: the
owner's four, in the owner's order (2026-11-17, answer 3). Each carries its
value, its sample size, its window, its source, and its change against the
window before.

PURE AND STDLIB-ONLY, and it READS NOTHING of its own. `build(ops)` takes the
dict `ops_data.snapshot()` already assembled and derives everything from the
rows in it, so the cards add 0 GCS reads, 0 GitHub reads and 0 LLM tokens, and
cannot disagree with the drill-down rows beside them: both come from the same
list in one call.

THE WINDOW IS FIXED, NOT THE PICKER'S. `WINDOW_DAYS` complete IST days ending
YESTERDAY, against the `WINDOW_DAYS` before them. Today is left out because it
is partial: a half-finished day would read as a fall against a whole one.
`loop.json` only starts on 2026-10-08, so a 30-day comparison does not exist
yet; the card says so rather than showing a delta it cannot back. The page's
`?window=` / `?day=` drive Token budget and App health and do not reach here.

WHAT EACH NUMBER COUNTS (the same sentences are on the cards, `DEFINITIONS`):
  * cycles shipped: build cycles (`kind != "qa-round"`) whose outcome is
    `shipped`, by IST start date. Several cycles can work one PR.
  * PRs merged: DISTINCT `pr` among rows whose outcome is `shipped`, the rule
    `collect_loop_measurements._window_tokens` uses (its docstring: "Count
    distinct pr values, not rows"). It is the PRs the loop shipped, not every PR
    merged on the repo, so the drill-down rows cannot disagree with the
    headline.
  * first-pass QA rate: among those PRs that have a verdict in
    `agents.json` `qa.rounds_per_issue`, the share whose FIRST verdict is PASS.
    That list is undated, so the join to `loop.json` (PR number, date) is what
    puts it in a window. It assumes the list is oldest-first.
  * cost per successful outcome: `cost_list_usd` summed over EVERY measured run
    in the window (QA rounds, empty cycles and failures included) divided by
    the distinct shipped PRs, the figure `token_summary` calls
    `cost_list_usd_per_merged_pr`. List price, not spend: the loop runs on a flat
    subscription.

NEVER RAISES. `snapshot()` promises the page never 500s and a malformed row must
not be the exception. `build` wraps the work and, on any failure, returns four
"unavailable" cards with `error` set. A card that cannot be computed says so; it
never shows a 0 that means "unknown".
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from datetime import date, timedelta

log = logging.getLogger(__name__)

WINDOW_DAYS = 7
# Below this many items a percentage change is noise, and the card says so.
MIN_N = 10

_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
# Mirrors collect_loop_measurements.TOKEN_FIELDS: a run is "measured" when all
# four are integers. tests/test_ops_kpis.py pins the two together.
_TOKEN_FIELDS = ("tokens_input", "tokens_output", "tokens_cache_read", "tokens_cache_write")
_VERDICTS = ("PASS", "FAIL")

# The keys a drill row carries, in order. Whitelisted, never `dict(row)`: a full
# loop row is ~600 B with token counts and agent maps the drill never shows, and
# these rows ride in the page's JSON blob.
SLIM_KEYS = ("run", "date_ist", "time_ist", "minutes", "trigger", "outcome",
             "issue", "pr", "attribution", "kind", "qa1", "usd")

DEFINITIONS = {
    "cycles": {
        "label": "Cycles shipped",
        "definition": ("Build cycles (every run except QA rounds) whose outcome is shipped, "
                       "by IST start date. Out of all build cycles in the window."),
        "source": "measurements/loop.json",
        "drill": "kpi-cycles",
    },
    "qa": {
        "label": "First-pass QA rate",
        "definition": ("Of the PRs shipped in the window that have a recorded QA verdict, the "
                       "share whose first verdict was PASS. A PR with no recorded verdict is "
                       "left out and counted separately."),
        "source": "measurements/agents.json (rounds_per_issue) joined to loop.json by PR number",
        "drill": "kpi-qa",
    },
    "cost": {
        "label": "Cost per successful outcome",
        "definition": ("List-price Claude cost of every measured run in the window, QA rounds "
                       "and failures included, divided by the distinct PRs shipped. List price, "
                       "not spend: the loop runs on a flat subscription."),
        "source": "measurements/loop.json (cost_list_usd)",
        "drill": "kpi-cost",
    },
    "prs": {
        "label": "PRs merged",
        "definition": ("Distinct pull requests the loop shipped in the window (several cycles "
                       "can work one PR). Not every PR merged on the repository."),
        "source": "measurements/loop.json",
        "drill": "kpi-prs",
    },
}
_ORDER = ("cycles", "qa", "cost", "prs")


def windows(today_ist: str, days: int = WINDOW_DAYS) -> tuple[list[str], list[str]]:
    """(current, previous): `days` complete IST dates each, oldest first.

    The current window ends YESTERDAY and the previous one ends the day before
    the current one starts, so the two are adjacent and equal in length. Raises
    on a malformed date or a non-positive `days`; `build` is the one that
    catches.
    """
    if days < 1:
        raise ValueError("days must be at least 1")
    today = date.fromisoformat(today_ist)
    current = [(today - timedelta(days=days - i)).isoformat() for i in range(days)]
    previous = [(today - timedelta(days=2 * days - i)).isoformat() for i in range(days)]
    return current, previous


def _span(dates: list[str]) -> str:
    """'2026-11-18 → 11-24'; the year is dropped from the end when it repeats."""
    start, end = dates[0], dates[-1]
    return f"{start} → {end[5:] if end[:4] == start[:4] else end}"


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _num(x):
    """`x` when it is a finite real number, else None."""
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    return x


def _txt(x, cap: int) -> str | None:
    return x[:cap] if isinstance(x, str) else None


def _clean(rows) -> tuple[list[dict], int]:
    """Rows this module can use, normalised, and how many it had to skip.

    A usable row is a dict with an ISO `date_ist` and a string `outcome`. A
    measured row whose `cost_list_usd` is present but not a number is skipped
    too: it would otherwise make the cost figure a guess.
    """
    out, skipped = [], 0
    for r in rows if isinstance(rows, list) else []:
        if (not isinstance(r, dict) or not isinstance(r.get("date_ist"), str)
                or not _ISO.fullmatch(r["date_ist"]) or not isinstance(r.get("outcome"), str)):
            skipped += 1
            continue
        measured = all(_is_int(r.get(k)) for k in _TOKEN_FIELDS)
        usd = 0.0
        if measured and r.get("cost_list_usd") is not None:
            usd = _num(r["cost_list_usd"])
            if usd is None:
                skipped += 1
                continue
        out.append({
            "date": r["date_ist"], "outcome": r["outcome"],
            "kind": r["kind"] if isinstance(r.get("kind"), str) else "",
            "pr": r["pr"] if _is_int(r.get("pr")) and r["pr"] > 0 else None,
            "measured": measured, "usd": float(usd), "src": r,
        })
    return out, skipped


def _first_verdicts(ops: dict) -> tuple[dict[int, str] | None, str]:
    """({pr: first verdict}, reason). The dict is None when the list is unreadable.

    Only PASS and FAIL are kept: anything else is "no verdict", not a fail.
    """
    qa = ((ops.get("agents") or {}).get("agents") or {}).get("qa")
    rpi = qa.get("rounds_per_issue") if isinstance(qa, dict) else None
    if not isinstance(rpi, dict):
        why = ("agents.json not read" if not (ops.get("agents") or {}).get("ok")
               else "rounds_per_issue not collected")
        return None, why
    first: dict[int, str] = {}
    for k, v in rpi.items():
        try:
            pr = int(k)
        except (TypeError, ValueError):
            continue
        verdict = v[0] if isinstance(v, list) and v else None
        if verdict in _VERDICTS:
            first[pr] = verdict
    return first, ""


def _stats(rows: list[dict], dates: list[str], first: dict[int, str] | None) -> dict:
    """Everything one window's four cards need, from the cleaned rows."""
    keep = set(dates)
    win = [r for r in rows if r["date"] in keep]
    builds = [r for r in win if r["kind"] != "qa-round"]
    shipped_rows = [r for r in win if r["outcome"] == "shipped"]
    prs = {r["pr"] for r in shipped_rows if r["pr"]}
    # PR -> the first date it shipped in THIS window. The bars under the cards
    # (ops_trends) put each PR on this day only, so they add up to `prs` above.
    pr_day: dict[int, str] = {}
    for r in shipped_rows:
        if r["pr"] and (r["pr"] not in pr_day or r["date"] < pr_day[r["pr"]]):
            pr_day[r["pr"]] = r["date"]
    verdict = {pr: first[pr] for pr in prs if first and pr in first}
    measured = [r for r in win if r["measured"]]
    return {
        "rows": win, "runs": len(win),
        "builds": len(builds),
        "shipped_cycles": sum(1 for r in builds if r["outcome"] == "shipped"),
        "shipped_rows": len(shipped_rows),
        "prs": len(prs),
        "pr_day": pr_day,
        "verdicts": len(verdict),
        "passed": sum(1 for v in verdict.values() if v == "PASS"),
        "measured": len(measured),
        "usd": round(sum(r["usd"] for r in measured), 2),
    }


def _delta(cur, prev, *, mode: str, good_when: str, prev_window: str, prev_n: int,
           prev_text: str, blocked: str | None = None, predates: str | None = None,
           na_text: str = "n/a: previous window had 0") -> dict:
    """The change against the previous window, or the reason there is none.

    `mode` is "pct" (relative change, for counts and money) or "pp" (percentage
    points, for a rate). `predates` is the first date in the data when the
    previous window starts before it: a window only partly covered would
    compare a week with a few days. `blocked` is any other reason the caller
    has for refusing. The text always carries an arrow and a direction word, so
    colour is never the only signal.
    """
    base = {"state": "unavailable", "text": "", "direction": None, "good": None,
            "amount": None, "previous_text": prev_text, "previous_n": prev_n,
            "previous_window": prev_window}
    if predates:
        # No "was N" beside a refusal (#1490): a previous window that starts
        # before the data holds a partial week, and "was 0" would read as a fact.
        return {**base, "previous_text": "", "text": f"unavailable: data starts {predates}"}
    if blocked:
        return {**base, "text": blocked}
    # A relative change against nothing is "n/a", not a division. `prev` is None
    # for cost when the previous window shipped no PR to divide by.
    if mode == "pct" and (prev is None or prev == 0):
        return {**base, "state": "na", "text": na_text}
    if prev is None:
        return {**base, "text": "unavailable: previous window had no value"}
    if mode == "pp":
        change = cur - prev
        flat = round(change, 1) == 0
        amount = f"{abs(change):.1f} pp"
    else:
        change = (cur - prev) / prev * 100
        flat = abs(change) < 0.5
        amount = f"{abs(change):.0f}%"
    where = f"vs {prev_window} (n={prev_n})"
    if flat:
        return {**base, "state": "ok", "direction": "flat", "amount": 0.0,
                "text": f"▬ flat {where}"}
    direction = "up" if change > 0 else "down"
    return {**base, "state": "ok", "direction": direction, "amount": round(change, 1),
            "good": direction == good_when,
            "text": f"{'▲' if direction == 'up' else '▼'} {direction} {amount} {where}"}


def _card(key: str, window_text: str, *, state: str, value=None, display: str = "",
          n: int = 0, n_text: str = "", floor: bool = False, delta: dict | None = None) -> dict:
    d = DEFINITIONS[key]
    low = state == "ok" and n < MIN_N
    return {
        "key": key, "label": d["label"], "state": state, "value": value, "display": display,
        "n": n,
        "n_text": n_text + (" — too few to read" if low else ""),
        "low_n": low, "floor": floor,
        "window_text": window_text, "definition": d["definition"], "source": d["source"],
        "drill": d["drill"],
        "delta": delta or {"state": "unavailable", "text": "no change shown: no current value",
                           "direction": None, "good": None, "amount": None,
                           "previous_text": "", "previous_n": 0, "previous_window": ""},
    }


def _unavailable(reason: str, *, error: bool, days: int = WINDOW_DAYS) -> dict:
    """Four unavailable cards: the shape a template can render unconditionally."""
    return {
        "error": error, "reason": reason, "days": days,
        "window": {"text": "", "previous_text": "", "start": "", "end": ""},
        "as_of": {"text": "age unknown", "stale": True, "at_ist": None},
        "caption": "", "skipped": 0, "rows": [], "pr_days": [],
        "cards": [_card(k, "", state="unavailable", display="unavailable", n_text=reason)
                  for k in _ORDER],
    }


def _slim(r: dict, first: dict[int, str] | None) -> dict:
    """One drill row: the whitelisted keys only, strings capped, types checked."""
    src, pr = r["src"], r["pr"]
    return {
        "run": src["run"] if _is_int(src.get("run")) else None,
        "date_ist": r["date"],
        "time_ist": _txt(src.get("time_ist"), 5),
        "minutes": None if _num(src.get("minutes")) is None else round(src["minutes"], 1),
        "trigger": _txt(src.get("trigger"), 17),
        "outcome": _txt(r["outcome"], 8),
        "issue": src["issue"] if _is_int(src.get("issue")) else None,
        "pr": pr,
        "attribution": _txt(src.get("attribution"), 12),
        "kind": _txt(r["kind"], 8),
        "qa1": first.get(pr) if first and pr else None,
        "usd": round(r["usd"], 4) if r["measured"] else None,
    }


def _build_unsafe(ops: dict, days: int) -> dict:
    loop = ops["loop"]
    if not loop.get("ok") or not isinstance(loop.get("rows"), list):
        return _unavailable("unavailable: loop.json not read", error=False, days=days)
    cur_dates, prev_dates = windows(ops["today_ist"], days)
    rows, skipped = _clean(loop["rows"])
    # Rows `_loop_view` dropped before this module saw them (#1492); they are no
    # longer in loop["rows"], so none is counted twice.
    skipped += int(loop.get("skipped_rows") or 0)
    first, why = _first_verdicts(ops)
    first_date = min((r["date"] for r in rows), default=None)
    predates = first_date if first_date and prev_dates[0] < first_date else None

    cur = _stats(rows, cur_dates, first)
    prev = _stats(rows, prev_dates, first)
    wtext, ptext = _span(cur_dates), _span(prev_dates)
    common = {"prev_window": ptext, "predates": predates}

    # --- Cycles shipped
    if cur["builds"] == 0:
        cycles = _card("cycles", wtext, state="empty", display="no runs",
                       n_text="no build cycles in this window")
    else:
        cycles = _card(
            "cycles", wtext, state="ok", value=cur["shipped_cycles"],
            display=str(cur["shipped_cycles"]), n=cur["builds"],
            n_text=f"of {cur['builds']} build cycles",
            delta=_delta(cur["shipped_cycles"], prev["shipped_cycles"], mode="pct",
                         good_when="up", prev_n=prev["builds"],
                         prev_text=str(prev["shipped_cycles"]), **common))

    # --- First-pass QA rate
    # None, never 0.0, when nothing has a verdict: 0% would read as "every first
    # submission failed".
    rate = cur["passed"] / cur["verdicts"] * 100 if cur["verdicts"] else None
    if first is None:
        qa = _card("qa", wtext, state="unavailable", display="unavailable",
                   n_text=f"unavailable: {why}")
    elif cur["prs"] == 0:
        qa = _card("qa", wtext, state="empty", display="no PRs",
                   n_text="no PR shipped in this window")
    elif rate is None:
        qa = _card("qa", wtext, state="unavailable", display="unavailable",
                   n_text=f"none of the {cur['prs']} PRs has a recorded verdict")
    else:
        prev_rate = prev["passed"] / prev["verdicts"] * 100 if prev["verdicts"] else None
        missing = cur["prs"] - cur["verdicts"]
        qa = _card(
            "qa", wtext, state="ok", value=rate, display=f"{rate:.1f}%", n=cur["verdicts"],
            n_text=(f"{cur['passed']} of {cur['verdicts']} PRs passed first time; "
                    f"{missing} had no verdict"),
            delta=_delta(rate, prev_rate, mode="pp", good_when="up", prev_n=prev["verdicts"],
                         prev_text="" if prev_rate is None else f"{prev_rate:.1f}%", **common))

    # --- Cost per successful outcome
    if cur["runs"] == 0:
        cost = _card("cost", wtext, state="empty", display="no runs",
                     n_text="no runs in this window")
    elif cur["prs"] == 0 or cur["measured"] == 0:
        why_cost = ("no PR shipped in this window" if cur["prs"] == 0
                    else "no run in this window has token data")
        cost = _card("cost", wtext, state="unavailable", display="unavailable", n_text=why_cost)
    else:
        per = round(cur["usd"] / cur["prs"], 2)
        prev_per = round(prev["usd"] / prev["prs"], 2) if prev["prs"] else None
        partial = cur["measured"] < cur["runs"]
        full = (cur["measured"] == cur["runs"] and prev["runs"] > 0
                and prev["measured"] == prev["runs"])
        cost = _card(
            "cost", wtext, state="ok", value=per, display=f"${per:,.2f}", n=cur["prs"],
            n_text=(f"${cur['usd']:,.2f} list price over {cur['prs']} PRs; "
                    f"{cur['measured']} of {cur['runs']} runs measured"
                    + ("; a floor" if partial else "")),
            floor=partial,
            delta=_delta(per, prev_per, mode="pct", good_when="down", prev_n=prev["prs"],
                         prev_text="" if prev_per is None else f"${prev_per:,.2f}",
                         blocked=None if full else
                         (f"unavailable: cost not fully measured in both windows "
                          f"({cur['measured']} of {cur['runs']}, "
                          f"{prev['measured']} of {prev['runs']} runs)"),
                         na_text="n/a: previous window had 0 PRs", **common))

    # --- PRs merged
    if cur["runs"] == 0:
        prs = _card("prs", wtext, state="empty", display="no runs",
                    n_text="no runs in this window")
    else:
        prs = _card(
            "prs", wtext, state="ok", value=cur["prs"], display=str(cur["prs"]), n=cur["prs"],
            n_text=f"distinct PRs, from {cur['shipped_rows']} shipped cycles",
            delta=_delta(cur["prs"], prev["prs"], mode="pct", good_when="up",
                         prev_n=prev["prs"], prev_text=str(prev["prs"]), **common))

    by_key = {"cycles": cycles, "qa": qa, "cost": cost, "prs": prs}
    # One entry per window day, oldest first: how many loop rows the day has and
    # which PRs first shipped on it. `runs` is what tells "no runs" from a real 0.
    runs_on = Counter(r["date"] for r in cur["rows"])
    by_day: dict[str, list[int]] = {d: [] for d in cur_dates}
    for pr, d in cur["pr_day"].items():
        by_day[d].append(pr)
    pr_days = [{"date": d, "runs": runs_on.get(d, 0), "prs": sorted(by_day[d])}
               for d in cur_dates]
    ages = ops.get("ages") or {}
    age = ages.get("Delivery") if isinstance(ages.get("Delivery"), dict) else {}
    return {
        "error": False, "reason": "", "days": days,
        "window": {"text": wtext, "previous_text": ptext,
                   "start": cur_dates[0], "end": cur_dates[-1]},
        "as_of": {"text": age.get("text") or "age unknown", "stale": bool(age.get("stale", True)),
                  "at_ist": age.get("at_ist")},
        "caption": (f"Last {days} complete IST days, ending yesterday, against the {days} before. "
                    "Fixed: the range picker does not move these cards."),
        "skipped": skipped,
        "cards": [by_key[k] for k in _ORDER],
        "pr_days": pr_days,
        "rows": [_slim(r, first) for r in cur["rows"]],
    }


def build(ops, *, days: int = WINDOW_DAYS) -> dict:
    """The KPI row for `ops` (a `snapshot()` dict). Never raises."""
    try:
        return _build_unsafe(ops, days)
    except Exception as exc:  # noqa: BLE001 - the page must render without the KPI row
        log.warning("KPI cards could not be computed: %s", exc)
        return _unavailable("unavailable: could not be computed", error=True, days=days)
