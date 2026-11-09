"""New decisions go in docs/decisions/, never a new ARCHITECTURE.md §10 row (2026-11-09).

Every PR used to append a row to one table, so any two open PRs conflicted on it
by construction: #804, #809, #810, #811 and #812 each did on 2026-11-09 alone.
Owner: "make PRs without the requirement to update a common file at one place".
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
FROZEN_AFTER = "2026-11-09"
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9-]*\.md$")


def _section_10_dates() -> list[str]:
    text = (ROOT / "ARCHITECTURE.md").read_text()
    sec = text[text.index("## 10. Decision log"):text.index("## 11.")]
    return re.findall(r"^\| (\d{4}-\d{2}-\d{2}) \|", sec, re.M)


def test_no_decision_row_is_added_to_the_frozen_table():
    late = [d for d in _section_10_dates() if d > FROZEN_AFTER]
    assert not late, (f"{len(late)} row(s) dated after {FROZEN_AFTER} were added to ARCHITECTURE.md §10. "
                      f"Put each decision in its own file, docs/decisions/YYYY-MM-DD-<slug>.md "
                      f"(format in docs/decisions/README.md): a shared table conflicts every open PR.")


def test_the_frozen_table_is_still_there_to_read():
    assert len(_section_10_dates()) >= 100, "the history in §10 is kept, not deleted"


def test_every_decision_file_is_named_and_shaped_as_the_readme_says():
    files = [p for p in (ROOT / "docs" / "decisions").glob("*.md") if p.name != "README.md"]
    assert files, "docs/decisions/ holds no decisions"
    for p in files:
        m = NAME.match(p.name)
        assert m, f"{p.name}: must be YYYY-MM-DD-<lowercase-slug>.md"
        text = p.read_text()
        assert text.startswith("# "), f"{p.name}: first line must be a '# ' title"
        assert f"**Date:** {m.group(1)}" in text, f"{p.name}: needs '**Date:** {m.group(1)}'"
