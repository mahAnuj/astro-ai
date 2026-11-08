"""scripts/verify_egress.py must go red on a new outbound host or client (#743).

Every case builds a throwaway `src/` under `tmp_path` and calls the gate's own
`check()` with explicit tables, so a test cannot pass by reading the live
allow-list. Only `test_the_real_tree_passes` touches the real tree.

NOTHING HERE SKIPS: `scripts/verify_behaviour.py` fails the suite on a skip.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = ROOT / "scripts" / "verify_egress.py"

_spec = importlib.util.spec_from_file_location("verify_egress", GATE_PATH)
gate = importlib.util.module_from_spec(_spec)
sys.modules["verify_egress"] = gate
_spec.loader.exec_module(gate)

HOSTS = {"api.ok.example": ("runtime", "fixture")}
CLIENTS = {"src/pkg/net.py": ({"httpx"}, "fixture")}
NET_OK = "import httpx\nURL = 'https://api.ok.example/v1'\n"


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def _run(tmp_path, files, hosts=HOSTS, clients=CLIENTS):
    return gate.check(_tree(tmp_path, files), hosts, clients)


def test_a_tree_matching_both_tables_passes(tmp_path):
    violations, errors = _run(tmp_path, {"src/pkg/net.py": NET_OK})
    assert (violations, errors) == ([], [])


def test_an_unlisted_host_in_a_plain_string_fails(tmp_path):
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK,
                                    "src/pkg/x.py": "U = 'https://evil.example.org/x'\n"})
    assert len(violations) == 1
    assert "src/pkg/x.py:1" in violations[0] and "evil.example.org" in violations[0]
    assert "ALLOWED_HOSTS" in violations[0]


def test_a_host_inside_an_fstring_fails(tmp_path):
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK,
                                    "src/pkg/x.py": "t = 'k'\nU = f'https://evil.example.org/{t}/send'\n"})
    assert any("evil.example.org" in v and "src/pkg/x.py:2" in v for v in violations)


def test_a_host_only_in_a_docstring_is_ignored(tmp_path):
    doc = ('"""Module note: see https://docs.example.org/page."""\n'
           'class C:\n    """Also https://docs.example.org/c."""\n'
           'def f():\n    """And https://docs.example.org/f."""\n')
    violations, errors = _run(tmp_path, {"src/pkg/net.py": NET_OK, "src/pkg/x.py": doc})
    assert (violations, errors) == ([], [])


def test_a_host_in_a_second_string_statement_is_not_a_docstring(tmp_path):
    # Only the FIRST statement is a docstring; a later bare string is code.
    src = '"""doc"""\n"https://evil.example.org/later"\n'
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK, "src/pkg/x.py": src})
    assert any("evil.example.org" in v for v in violations)


def test_a_new_file_importing_a_client_fails(tmp_path):
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK,
                                    "src/pkg/new.py": "import httpx\n"})
    assert len(violations) == 1
    assert "src/pkg/new.py" in violations[0] and "CLIENT_MODULES" in violations[0]


def test_a_lazy_import_inside_a_function_is_caught(tmp_path):
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK,
                                    "src/pkg/new.py": "def f():\n    from urllib.request import urlopen\n"})
    assert any("urllib.request" in v and "src/pkg/new.py:2" in v for v in violations)


def test_a_non_network_stdlib_import_is_not_a_client(tmp_path):
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK,
                                    "src/pkg/new.py": "from urllib.parse import quote\nimport json\n"})
    assert violations == []


def test_an_allowed_file_importing_an_extra_client_fails(tmp_path):
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK + "import requests\n"})
    assert len(violations) == 1
    assert "additional client" in violations[0] and "requests" in violations[0]


def test_from_google_import_cloud_counts_as_a_client(tmp_path):
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK,
                                    "src/pkg/new.py": "from google import cloud\n"})
    assert any("google.cloud" in v for v in violations)


def test_a_stale_host_entry_fails(tmp_path):
    hosts = {**HOSTS, "gone.example": ("runtime", "was removed")}
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK}, hosts=hosts)
    assert len(violations) == 1
    assert "stale" in violations[0] and "gone.example" in violations[0]


def test_a_stale_client_root_and_a_missing_file_fail(tmp_path):
    clients = {"src/pkg/net.py": ({"httpx", "requests"}, "r"), "src/pkg/gone.py": ({"httpx"}, "r")}
    violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK}, clients=clients)
    text = "\n".join(violations)
    assert "no longer imports 'requests'" in text
    assert "'src/pkg/gone.py'" in text and "file is gone" in text


def test_an_unparsable_file_is_exit_2_not_a_pass(tmp_path, capsys):
    _tree(tmp_path, {"src/pkg/bad.py": "def (:\n"})
    assert gate.main([str(tmp_path)]) == 2
    assert "COULD NOT VERIFY" in capsys.readouterr().out


def test_a_missing_src_dir_is_exit_2(tmp_path):
    assert gate.main([str(tmp_path)]) == 2


def test_a_violation_is_exit_1(tmp_path):
    _tree(tmp_path, {"src/pkg/x.py": "U = 'https://evil.example.org'\n"})
    assert gate.main([str(tmp_path)]) == 1


def test_the_real_tree_passes():
    r = subprocess.run([sys.executable, str(GATE_PATH)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
