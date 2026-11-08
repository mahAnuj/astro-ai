#!/usr/bin/env python3
"""Gate: `src/` may not gain an outbound host or a network-client module unreviewed (#743).

WHY THIS EXISTS

The autonomous loop merges its own PRs on green gates, and the repo is public. A
PR that adds one call to a host nobody listed is a data-exfiltration path (a
chart, an email address, a subscriber record) and nothing here turned red on it.
`TRUST_BOUNDARY` guards `storage.py`, `notify.py` and `email_sender.py` by file,
which says nothing about a NEW file that opens a socket.

WHAT IT CHECKS (static, stdlib `ast`; nothing is fetched)

  1. Every `http(s)://host` inside a string literal in `src/**/*.py` is a key of
     `ALLOWED_HOSTS`. F-strings count (their literal parts are scanned).
     Docstrings and comments are NOT scanned: they cannot be executed, and the
     ones naming hosts (`app.brevo.com`, drikpanchang in `sankranti.py`) are prose.
  2. Every module that imports a network client (`CLIENT_ROOTS`, at top level or
     lazily) is a key of `CLIENT_MODULES` AND imports no client root beyond the
     ones listed for it. This is what catches a host built from a variable, which
     check 1 cannot see, but only when the CLIENT is new to that file.
  3. STALE entries fail: a listed host no literal still contains, a listed file
     that is gone or no longer imports a listed root. Otherwise a deleted feature
     leaves a standing permission behind.

WHAT THIS LETS THROUGH, stated plainly because a gate that overclaims is worse
than none:
  * a host assembled at runtime (`"https://" + h`, `f"https://{h}/x"`) in a file
    that is ALREADY allowed to hold a client (e.g. a new call in `notify.py`);
  * `ASTRO_AI_API_BASE` and provider env overrides: the base URL of the LLM call
    is an environment value, so what `providers.py` really contacts is set outside
    the tree;
  * redirects, DNS, and what a listed host does with the data it receives;
  * hosts contacted by the BROWSER (templates, `static/`), which is not server
    egress and is not scanned;
  * dynamic imports (`importlib`, `__import__`) and clients not in `CLIENT_ROOTS`;
  * a string literal that is the real host but is a docstring (it is skipped).
It is a tripwire that forces a reviewed edit, not a sandbox. Run-time egress
control would be a Cloud Run VPC egress rule, which is infrastructure, not tree.

Exit 0 pass, 1 violation or stale entry, 2 could not verify (no `src/`, a file
that does not parse, nothing scanned). 2 is never a pass.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMEDY = "add it to the allow-list with a kind and a reason: a deliberate, reviewed edit"

# host -> (kind, reason). `runtime` = the app connects to it; `reference` = an
# identifier, namespace or link that is rendered or compared, never fetched.
ALLOWED_HOSTS: dict[str, tuple[str, str]] = {
    "api.groq.com": ("runtime", "providers.py preset: Groq OpenAI-compatible API, the live LLM chain"),
    "api.cerebras.ai": ("runtime", "providers.py preset: cerebras (opt-in via BHAGYA_LLM_PROVIDERS)"),
    "api.together.xyz": ("runtime", "providers.py preset: together (opt-in via BHAGYA_LLM_PROVIDERS)"),
    "api.mistral.ai": ("runtime", "providers.py preset: mistral (opt-in via BHAGYA_LLM_PROVIDERS)"),
    "api.telegram.org": ("runtime", "notify.py: sendMessage alert to the owner's chat"),
    "api.brevo.com": ("runtime", "email_sender.py: BREVO_ENDPOINT, transactional mail"),
    "api.github.com": ("runtime", "ops_today.py and issue_backlog.py: read-only issue/PR listing for /admin/ops"),
    "raw.githubusercontent.com": ("runtime", "ops_data.py: reads measurements/*.json from main for /admin/ops"),
    "www.drikpanchang.com": ("reference", "festival_registry.py SOURCE_URL_BY_YEAR: a provenance link the /festivals "
                             "page renders; checked 2026-11-08, no code fetches it (sankranti.py/adhik_maas.py "
                             "mention it only in docstrings, which this gate skips)"),
    "shubhagya.com": ("reference", "routes/deps.py default site URL and snapshots.py; our own origin, a link"),
    "www.sitemaps.org": ("reference", "routes/seo.py: sitemap XML namespace URI, an identifier"),
    "www.w3.org": ("reference", "routes/seo.py: xhtml XML namespace URI, an identifier"),
}

# Import prefixes that open a network connection. A bare dotted prefix matches
# itself and its submodules (`urllib.request` does not match `urllib.parse`).
CLIENT_ROOTS = (
    "httpx", "requests", "urllib.request", "urllib3", "aiohttp", "http.client", "socket",
    "smtplib", "ftplib", "imaplib", "poplib", "telnetlib", "xmlrpc.client", "websockets",
    "websocket", "openai", "geopy", "google.cloud", "google.oauth2", "google.auth",
)

# path -> (client roots it may import, reason incl. the host that is NOT a literal).
CLIENT_MODULES: dict[str, tuple[set[str], str]] = {
    "src/astro_ai/notify.py": ({"httpx"}, "Telegram sendMessage (api.telegram.org)"),
    "src/astro_ai/email_sender.py": ({"httpx"}, "Brevo transactional mail (api.brevo.com)"),
    "src/astro_ai/ops_today.py": ({"urllib.request"}, "GitHub API read for /admin/ops (api.github.com)"),
    "src/astro_ai/issue_backlog.py": ({"urllib.request"}, "GitHub API read for the backlog panel (api.github.com)"),
    "src/astro_ai/ops_data.py": ({"urllib.request"}, "measurements from raw.githubusercontent.com"),
    "src/astro_ai/providers.py": ({"openai"}, "OpenAI SDK; api_base=None means api.openai.com (paid safety net), "
                                  "and ASTRO_AI_API_BASE can repoint any provider"),
    "src/astro_ai/chart.py": ({"geopy"}, "city geocoding via Nominatim (nominatim.openstreetmap.org)"),
    "src/astro_ai/storage.py": ({"google.cloud"}, "GCS blobs (storage.googleapis.com), the US bucket"),
    "src/astro_ai/routes/account.py": ({"google.oauth2", "google.auth"},
                                       "Google Sign-In ID-token check; fetches Google's public certs "
                                       "(www.googleapis.com/oauth2/v1/certs)"),
}

_HOST = re.compile(r"https?://([A-Za-z0-9.-]+)")


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                ids.add(id(first.value))
    return ids


def _client_root(name: str) -> str | None:
    for root in CLIENT_ROOTS:
        if name == root or name.startswith(root + "."):
            return root
    return None


def scan_file(path: Path, rel: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """(hosts as (line, host), client imports as (line, root)); SyntaxError propagates."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    skip = _docstring_ids(tree)
    hosts: list[tuple[int, str]] = []
    clients: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            for m in _HOST.finditer(node.value):
                hosts.append((node.lineno, m.group(1).rstrip(".").lower()))
        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
            clients += [(node.lineno, r) for n in names if (r := _client_root(n))]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            # `from google import cloud` names the submodule in the alias, not the module.
            names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            found = {r for n in names if (r := _client_root(n))}
            clients += [(node.lineno, r) for r in sorted(found)]
    return hosts, clients


def check(root: Path, allowed_hosts=None, client_modules=None) -> tuple[list[str], list[str]]:
    """(violations, errors) for the tree under `root`; tables default to the module's own."""
    allowed_hosts = ALLOWED_HOSTS if allowed_hosts is None else allowed_hosts
    client_modules = CLIENT_MODULES if client_modules is None else client_modules
    violations: list[str] = []
    errors: list[str] = []
    src = root / "src"
    if not src.is_dir():
        return [], [f"{src} is not a directory"]
    seen_hosts: set[str] = set()
    seen_clients: dict[str, set[str]] = {}
    files = sorted(src.rglob("*.py"))
    if not files:
        return [], [f"no .py files under {src}"]
    for f in files:
        rel = f.relative_to(root).as_posix()
        try:
            hosts, clients = scan_file(f, rel)
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            errors.append(f"{rel}: cannot parse ({type(exc).__name__}: {exc})")
            continue
        for line, host in hosts:
            seen_hosts.add(host)
            if host not in allowed_hosts:
                violations.append(f"{rel}:{line}: unlisted outbound host {host!r} -- {REMEDY} (ALLOWED_HOSTS)")
        for line, croot in clients:
            seen_clients.setdefault(rel, set()).add(croot)
            if rel not in client_modules:
                violations.append(f"{rel}:{line}: new network-client module imports {croot!r} -- {REMEDY} (CLIENT_MODULES)")
            elif croot not in client_modules[rel][0]:
                violations.append(f"{rel}:{line}: imports an additional client {croot!r} -- {REMEDY} (CLIENT_MODULES)")
    if errors:  # a stale verdict over a tree we could not fully read would be a guess
        return violations, errors
    for host in sorted(set(allowed_hosts) - seen_hosts):
        violations.append(f"ALLOWED_HOSTS: stale entry {host!r} appears in no string literal in src/ -- remove it")
    for rel, (roots, _why) in sorted(client_modules.items()):
        if not (root / rel).is_file():
            violations.append(f"CLIENT_MODULES: stale entry {rel!r}: the file is gone -- remove it")
            continue
        for croot in sorted(roots - seen_clients.get(rel, set())):
            violations.append(f"CLIENT_MODULES: stale entry {rel!r} no longer imports {croot!r} -- remove it")
    return violations, errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else ROOT
    violations, errors = check(root)
    if errors:
        for e in errors:
            print(f"  ?  {e}")
        print("\nCOULD NOT VERIFY (exit 2) -- an unreadable tree is not a pass.")
        return 2
    for v in violations:
        print(f"  x  {v}")
    if violations:
        print(f"\nFAIL -- {len(violations)} egress finding(s). New outbound hosts and clients are a "
              "data-exfiltration path: this is a reviewed edit, never a drive-by.")
        return 1
    print(f"PASS -- {len(ALLOWED_HOSTS)} hosts and {len(CLIENT_MODULES)} client modules, none unlisted, none stale.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
