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


# ---- QA round 1 (#804): bypasses of the host match, and branches no test pinned ----

def _only_host_violations(tmp_path, literal_line):
    violations, errors = _run(tmp_path, {"src/pkg/net.py": NET_OK, "src/pkg/x.py": literal_line + "\n"})
    assert errors == []
    return violations


def test_userinfo_cannot_dress_an_unlisted_host_as_a_listed_one(tmp_path):
    # `api.ok.example@evil.example.org` dials evil.example.org.
    v = _only_host_violations(tmp_path, "U = 'https://api.ok.example@evil.example.org/x'")
    assert any("evil.example.org" in x and "unlisted" in x for x in v)
    assert any("userinfo" in x for x in v)


def test_userinfo_on_a_listed_host_is_a_violation_of_its_own(tmp_path):
    v = _only_host_violations(tmp_path, "U = 'https://user:pw@api.ok.example/x'")
    assert len(v) == 1 and "userinfo" in v[0] and "'api.ok.example'" in v[0]


# What a real client leaves INSIDE the authority: it ends only at `/ ? #`. Checked
# 2026-11-08 with urlsplit(...).hostname == 'evil.example.org' for every one of these.
_INSIDE_THE_AUTHORITY = [" ", '"', "'", "<", ">", "\xa0", "\u3000", "\x85", "\x0b", "\x0c",
                         "\x1c", "\x1d", "\\", "\t", "\r", "\n"]


def test_an_at_after_any_non_delimiter_character_is_userinfo(tmp_path):
    # `https://api.ok.example<c>@evil.example.org/x` dials evil.example.org.
    for c in _INSIDE_THE_AUTHORITY:
        v = _only_host_violations(tmp_path, "U = " + repr(f"https://api.ok.example{c}@evil.example.org/x"))
        assert any("evil.example.org" in x and "unlisted" in x for x in v), repr(c)
        assert any("userinfo" in x for x in v), repr(c)


def test_a_backslash_is_inside_the_authority(tmp_path):
    v = _only_host_violations(tmp_path, "U = 'https://api.ok.example\\\\@evil.example.org/x'")
    assert any("evil.example.org" in x and "unlisted" in x for x in v)
    assert any("userinfo" in x for x in v)  # the wide view must see the `@` past the backslash


def test_an_at_after_a_hash_or_a_query_is_not_userinfo(tmp_path):
    # Every client dials api.ok.example here: the `@` sits in the fragment / query, not
    # the authority. Pins the wide view ending at `/ ? #` against a "simplification" to
    # "an @ anywhere in the literal".
    for lit in ("https://api.ok.example#@evil.example.org", "https://api.ok.example?@evil.example.org",
                "https://api.ok.example/path@evil.example.org"):
        assert _only_host_violations(tmp_path, "U = " + repr(lit)) == [], lit


def test_prose_after_a_url_is_not_part_of_its_host(tmp_path):
    # The tight view gives the host: a real client would reject this, so it is no finding.
    assert _only_host_violations(tmp_path, "U = 'see https://api.ok.example for details'") == []


def test_an_at_with_no_delimiter_after_the_url_fails_closed(tmp_path):
    # The documented false positive: no `/ ? #` between the URL and an `@`.
    v = _only_host_violations(tmp_path, "U = 'see https://api.ok.example or mail a@b.example'")
    assert any("userinfo" in x for x in v) and any("'b.example'" in x for x in v)


def test_tab_cr_and_lf_are_each_deleted_before_the_host_is_read(tmp_path):
    # urlsplit deletes each of these, so `api.ok.example<c>.evil.example.org` dials
    # api.ok.example.evil.example.org. One assertion per character: a strip set missing
    # one of them passes the other two.
    for c, name in (("\t", "tab"), ("\r", "CR"), ("\n", "LF")):
        v = _only_host_violations(tmp_path, "U = " + repr(f"https://api.ok.example{c}.evil.example.org/x"))
        assert any("'api.ok.example.evil.example.org'" in x for x in v), name


def test_an_uppercase_scheme_is_still_a_url(tmp_path):
    v = _only_host_violations(tmp_path, "U = 'HTTPS://evil.example.org/x'")
    assert any("evil.example.org" in x for x in v)


def test_a_bytes_literal_is_scanned(tmp_path):
    v = _only_host_violations(tmp_path, "U = b'https://evil.example.org/x'")
    assert any("evil.example.org" in x for x in v)


def test_ipv6_and_unicode_hosts_are_reported_not_skipped(tmp_path):
    v6 = _only_host_violations(tmp_path, "U = 'http://[::1]:9/'")
    assert any("'[::1]'" in x for x in v6)
    vu = _only_host_violations(tmp_path, "U = 'https://\u00e9vil.example.org'")
    assert any("\u00e9vil.example.org" in x for x in vu)


def test_websocket_and_ftp_schemes_are_scanned(tmp_path):
    for scheme in ("wss", "ws", "ftp", "ftps"):
        v = _only_host_violations(tmp_path, f"U = '{scheme}://evil.example.org'")
        assert any("evil.example.org" in x for x in v), scheme


def test_ssl_and_subprocess_are_clients(tmp_path):
    for mod in ("ssl", "subprocess"):
        violations, _ = _run(tmp_path, {"src/pkg/net.py": NET_OK, "src/pkg/new.py": f"import {mod}\n"})
        assert any(f"'{mod}'" in v and "CLIENT_MODULES" in v for v in violations), mod


def test_a_listed_host_with_an_empty_authority_or_a_port_matches(tmp_path):
    # `"https://" + h` has no authority to read; `:443` is not part of the host.
    src = "U = 'https://api.ok.example:443/x'\nV = 'https://' + 'x'\nW = f'https://{U}/p'\n"
    assert _only_host_violations(tmp_path, src) == []


def test_host_matching_ignores_ascii_case(tmp_path):
    # Without the .lower() `API.OK.EXAMPLE` is not a key of the (lower-case) table.
    violations, errors = _run(tmp_path, {"src/pkg/net.py": "import httpx\nURL = 'https://API.OK.EXAMPLE/v1'\n"})
    assert (violations, errors) == ([], [])


def test_a_trailing_dot_is_the_same_host(tmp_path):
    # `api.ok.example.` is the fully-qualified spelling of a listed host.
    violations, errors = _run(tmp_path, {"src/pkg/net.py": "import httpx\nURL = 'https://api.ok.example./v1'\n"})
    assert (violations, errors) == ([], [])


def test_a_relative_import_named_like_a_client_is_not_that_client(tmp_path):
    # `from .httpx import Client` imports the sibling module src/pkg/httpx.py.
    src = "from .httpx import Client\nfrom . import socket_helper\nfrom ..requests import get\n"
    violations, errors = _run(tmp_path, {"src/pkg/net.py": NET_OK, "src/pkg/new.py": src})
    assert (violations, errors) == ([], [])


def test_an_undecodable_file_is_an_error_not_a_crash(tmp_path):
    _tree(tmp_path, {"src/pkg/net.py": NET_OK})
    (tmp_path / "src/pkg/latin.py").write_bytes(b"# \xff\xfe not utf-8\nX = 1\n")
    violations, errors = gate.check(tmp_path, HOSTS, CLIENTS)
    assert len(errors) == 1 and "latin.py" in errors[0] and "UnicodeDecodeError" in errors[0]
    assert gate.main([str(tmp_path)]) == 2


def test_a_parse_error_suppresses_the_stale_verdict(tmp_path):
    # With the tree partly unread, "stale" would be a guess: only the error is reported.
    hosts = {**HOSTS, "gone.example": ("runtime", "was removed")}
    clients = {**CLIENTS, "src/pkg/gone.py": ({"httpx"}, "r")}
    violations, errors = _run(tmp_path, {"src/pkg/net.py": NET_OK, "src/pkg/bad.py": "def (:\n"},
                              hosts=hosts, clients=clients)
    assert len(errors) == 1 and "bad.py" in errors[0]
    assert not any("stale" in v for v in violations)


def test_a_src_dir_with_no_python_is_exit_2_not_a_pass(tmp_path):
    # Every table entry is stale against an empty tree; exit 2 must win over exit 1.
    (tmp_path / "src").mkdir()
    _violations, errors = gate.check(tmp_path, HOSTS, CLIENTS)
    assert len(errors) == 1 and "no .py files" in errors[0]
    assert gate.main([str(tmp_path)]) == 2


def test_the_real_tree_passes():
    r = subprocess.run([sys.executable, str(GATE_PATH)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
