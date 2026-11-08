"""The rashifal run record is reported honestly (2026-11-08).

/admin/ops showed "no run recorded" beside a green job whose log said
"recorded -> rashifal_runs.json". storage.update_json returns None on a
refused write instead of raising, and _record_run printed success regardless."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
_spec = importlib.util.spec_from_file_location("publish_rashifal", ROOT / "scripts" / "publish_rashifal.py")
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def test_a_refused_record_write_is_reported_not_claimed(monkeypatch, capsys):
    monkeypatch.setattr(pr.storage, "update_json", lambda *a, **k: None)
    pr._record_run("2026-11-08", "en", 12)
    out = capsys.readouterr().out
    assert "::warning::" in out and "NOT written" in out
    assert "recorded ->" not in out


def test_an_exception_is_reported_the_same_way(monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("403 Forbidden")
    monkeypatch.setattr(pr.storage, "update_json", boom)
    pr._record_run("2026-11-08", "hi", 12)
    out = capsys.readouterr().out
    assert "NOT written" in out and "403 Forbidden" in out


def test_a_written_record_still_says_recorded(monkeypatch, capsys):
    monkeypatch.setattr(pr.storage, "update_json", lambda *a, **k: {"2026-11-08": {}})
    pr._record_run("2026-11-08", "en", 12)
    assert "recorded -> rashifal_runs.json[2026-11-08][en] = 12 sections" in capsys.readouterr().out
