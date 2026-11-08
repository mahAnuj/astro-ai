"""/admin/ops showed the objective cut off at "increase the user base for"
(2026-11-08): read_objective took the first LINE of a blockquote that wraps."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from astro_ai.issue_backlog import read_objective  # noqa: E402


def _obj(tmp_path, text):
    p = tmp_path / "OBJECTIVE.md"
    p.write_text(text)
    return read_objective(str(p))


def test_a_wrapped_first_paragraph_is_read_whole(tmp_path):
    got = _obj(tmp_path, '# The objective\n\n> **"increase the user base for\n'
                         '> shubhagya.com while ensuring grounded astrology"**\n>\n'
                         '> Both halves bind every agent.\n')
    assert got == '"increase the user base for shubhagya.com while ensuring grounded astrology"'


def test_it_stops_at_the_end_of_the_quote_too(tmp_path):
    assert _obj(tmp_path, "> one\n> two\nnot quoted\n> later\n") == "one two"


def test_a_single_line_quote_is_unchanged(tmp_path):
    assert _obj(tmp_path, "> **Move the band into the top 5.**\n") == "Move the band into the top 5."


def test_no_file_or_no_quote_reads_empty(tmp_path):
    assert read_objective(str(tmp_path / "missing.md")) == ""
    assert _obj(tmp_path, "no quote here\n") == ""


def test_the_real_objective_is_not_cut_mid_sentence():
    got = read_objective(str(Path(__file__).resolve().parents[1] / "OBJECTIVE.md"))
    assert got.rstrip().endswith((".", '"', "”")), got
