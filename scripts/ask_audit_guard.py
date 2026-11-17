#!/usr/bin/env python3
"""Refuse /ask audit output that quotes a user (#1167).

The audit agent reads real users' questions and answers and then writes to
three public places: a GitHub issue, a committed JSON file and the job summary.
The rule is that a user's words never reach any of them verbatim. A prompt can
ask for that; it cannot guarantee it, and the questions themselves are text an
outsider wrote and an agent reads (qa.md #361 -- "Asking an LLM reviewer to be
robust against adversarial text ... has no reliable solution"). So the check is
deterministic and runs outside the model.

    ask_audit_guard.py leaks FILE...      exit 1 if any FILE quotes the sample;
                                          with --delete, removes those files
    ask_audit_guard.py issue-body FILE --labels a,b
                                          exit 1 if FILE quotes the sample OR its
                                          Evidence Block fails
                                          verify_issue_evidence.check()

WHAT COUNTS AS A QUOTE: any run of QUESTION_RUN consecutive words from a
question, or ANSWER_RUN from an answer, after lower-casing and stripping
punctuation. A question shorter than QUESTION_RUN words is checked whole once
it is MIN_CHARS long. Answers get a longer run because they are generated
prose and share stock phrases with the prompt an issue legitimately cites.

It never prints the matched text, nor the matched row's sample `id` -- only
the file it was found in -- since its own output lands in the same public log,
and a stable per-question hash there is one more handle on a user than anyone
reading the log needs (QA on PR #1169).

EXIT CODES: 0 clean   1 a quote (or a failing Evidence Block)   2 could not run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SAMPLE = Path("/tmp/ask-sample.json")
QUESTION_RUN = 6
ANSWER_RUN = 12
MIN_CHARS = 24

_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)


def _words(text: str) -> list[str]:
    return _PUNCT.sub(" ", str(text or "").lower()).split()


def _runs(text: str, k: int) -> set[str]:
    w = _words(text)
    if len(w) < k:
        whole = " ".join(w)
        return {whole} if len(whole) >= MIN_CHARS else set()
    return {" ".join(w[i:i + k]) for i in range(len(w) - k + 1)}


def quotes(text: str, sample: dict) -> list[str]:
    """Ids of sample answers whose question or answer `text` quotes."""
    hay = " " + " ".join(_words(text)) + " "
    hits = []
    for row in sample.get("answers") or []:
        needles = _runs(row.get("question", ""), QUESTION_RUN) | _runs(row.get("answer", ""), ANSWER_RUN)
        if any(f" {n} " in hay for n in needles):
            hits.append(str(row.get("id") or "?"))
    return hits


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sample", default=str(SAMPLE))
    sub = ap.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("leaks")
    lk.add_argument("files", nargs="+")
    lk.add_argument("--delete", action="store_true")
    ib = sub.add_parser("issue-body")
    ib.add_argument("file")
    ib.add_argument("--labels", default="")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        return 2
    sample = _load(Path(a.sample))
    if sample is None:
        print(f"COULD NOT VERIFY (exit 2) -- no readable sample at {a.sample}. This is NOT a pass.")
        return 2

    if a.cmd == "leaks":
        bad = 0
        for f in a.files:
            p = Path(f)
            if not p.exists():
                print(f"ok   {f}: absent")
                continue
            if quotes(p.read_text(errors="replace"), sample):
                bad += 1
                print(f"LEAK a user quote was found in {f}" + (" -- deleted" if a.delete else ""))
                if a.delete:
                    p.unlink()
            else:
                print(f"ok   {f}: no user text")
        return 1 if bad else 0

    body = Path(a.file).read_text(errors="replace") if Path(a.file).exists() else ""
    if not body:
        print(f"FAIL {a.file}: empty or missing")
        return 1
    if quotes(body, sample):
        print(f"FAIL a user quote was found in {a.file}. Paraphrase; never quote a user.")
        return 1
    from verify_issue_evidence import check  # noqa: PLC0415
    labels = [x.strip() for x in a.labels.split(",") if x.strip()]
    code, lines = check(body, labels, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    for line in lines:
        print(f"  {line}")
    print(("ok   " if code == 0 else "FAIL ") + f"{a.file}: Evidence Block")
    return 1 if code else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
