#!/usr/bin/env python3
"""Is the weekly /ask answer audit due? (#1167)

agent-measure's `measure` job runs about once a day; the audit is weekly. It is
due when `measurements/ask-audit.json` is missing, unreadable, carries no
parseable `generated_at`, or that stamp is at least 6.5 days old. 6.5 rather
than 7 so a run that starts a little earlier than last week's still audits,
instead of slipping a whole day.

Fails OPEN to "due": a broken file must not silence the audit forever. The
cost of a spurious run is one Claude invocation; the cost of a stuck "not due"
is answers nobody grades, which is the state #1167 was filed to end.

Writes `due=true|false` to $GITHUB_OUTPUT when set, and prints the reason.
EXIT CODES: 0 always (the answer is in the output, not the exit status)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "measurements" / "ask-audit.json"
MIN_AGE = timedelta(days=6.5)


def is_due(path: Path, now: datetime) -> tuple[bool, str]:
    try:
        doc = json.loads(path.read_text())
    except FileNotFoundError:
        return True, f"{path.name} does not exist yet"
    except (OSError, ValueError) as exc:
        return True, f"{path.name} unreadable ({exc.__class__.__name__})"
    stamp = doc.get("generated_at") if isinstance(doc, dict) else None
    try:
        at = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return True, f"{path.name} has no parseable generated_at"
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    age = now - at
    if age >= MIN_AGE:
        return True, f"last audit {age.total_seconds() / 86400:.1f} days old"
    return False, f"last audit {age.total_seconds() / 86400:.1f} days old (< 6.5)"


def main(argv: list[str], now: datetime | None = None) -> int:
    path = Path(argv[1]) if len(argv) > 1 else AUDIT
    due, why = is_due(path, now or datetime.now(timezone.utc))
    print(f"ask audit due={str(due).lower()}: {why}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"due={str(due).lower()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
