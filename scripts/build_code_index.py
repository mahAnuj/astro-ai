#!/usr/bin/env python3
"""Outline files with line ranges so an agent can look a symbol up instead of reading a whole file.

WHY THIS EXISTS (#1256, #1466)
93.9% of agent-work tokens are cache reads: every turn re-reads the whole context, and a
`Read` of a 5,000-line file sits in it for every later turn. An agent that looks `compute_dasha`
up and reads lines 2100-2180 keeps the other 5,000 lines out of that cache read.

    uv run python scripts/build_code_index.py <path>   print the outline of a file or directory
    uv run python scripts/build_code_index.py          write the index to .code-index/ (gitignored)
    uv run python scripts/build_code_index.py --out DIR

THE RULES
  * A file under 400 lines gets ONE line (`name  N lines  docline`); a longer one a full outline.
    An explicitly named FILE is always outlined in full: the agent asked for it.
  * Python: top-level def / async def / class as `name  start-end  docline`, start = the first
    decorator, so a range read includes `@router.get(...)`. Methods as `Class.method` only when
    the class spans more than 60 lines. A top-level constant spanning 30+ lines is `(data)`.
    Nested classes (`Outer.Inner`) and functions nested in functions are NOT listed.
    A syntax error is one `PARSE ERROR L<n>` line and indexing continues.
  * Markdown: ATX headings only (`## Title`), each ending before the next heading of the same
    or a higher level. Headings inside ``` or ~~~ fences and YAML front matter are ignored.
    SETEXT headings (underlined with === or ---) are NOT indexed.
  * Templates: `{% block %}` and `{% macro %}` ranges, `{# ── Title` section landmarks, the
    extends/includes, and where the template is "named in". NAMED IN IS NOT PROOF OF RENDERING:
    it is every string literal ending .html (or an f-string with a literal `dir/` prefix, shown
    as a glob like `learn/*.html`) in src/astro_ai/**/*.py, attributed to its outermost def.
    A name built any other way is invisible to it.
  * Every written file is at most MAX_CHARS. Docstring text shrinks 70 -> 40 -> 0 chars, then the
    index splits into parts (`<dir>.2.md`) at file boundaries, then inside one file at entry
    boundaries (`chart.py part 2/3`). Nothing is dropped.
  * Output is byte-deterministic: sorted, no timestamps, no absolute paths.
  * LINE NUMBERS ARE VALID UNTIL THE FILE IS EDITED. A stale range is a pointer, not evidence.

EXIT CODES  0 done (a content problem is a stderr warning); 2 bad usage, --out is a non-empty
directory that this script did not write (no INDEX.md marker), or --out cannot be written.
A re-run deletes only the files the previous INDEX.md lists; any other file in --out stays.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_CHARS = 8000
SMALL_FILE_LINES = 400
CLASS_METHODS_OVER = 60
DATA_LINES = 30
LINE_CAP = 200
DOC_LADDER = (70, 40, 0)
STALE = "Line numbers are valid until the file is edited. Regenerate: uv run python scripts/build_code_index.py <path>"
EXCLUDE_DIRS = {"tests", "measurements", "data", "static", "node_modules", ".venv", ".git",
                ".code-index", "__pycache__", "worktrees"}
TOP_DIRS = ("src", "scripts", "docs", ".claude")
ROUTE_METHODS = {"get": "GET", "post": "POST", "put": "PUT", "delete": "DELETE", "api_route": "ROUTE"}

Entry = tuple[str, str]          # (label, docline); the docline is what the ladder shrinks
FileOutline = tuple[str, int, str, list[Entry], bool]   # name, lines, docline, entries, full


class UsageError(Exception):
    pass


def _lines(text: str) -> list[str]:
    out = text.replace("\r\n", "\n").split("\n")
    if out and out[-1] == "":
        out.pop()
    return out


def _first(doc: str | None) -> str:
    for ln in (doc or "").splitlines():
        if ln.strip():
            return ln.strip()
    return ""


# ---------------------------------------------------------------- Python
def _py(text: str) -> tuple[str, list[Entry]]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError) as e:
        return "", [(f"PARSE ERROR L{getattr(e, 'lineno', None) or 0}", "")]
    out: list[Entry] = []

    def span(n: ast.AST) -> str:
        start = min([d.lineno for d in getattr(n, "decorator_list", [])] + [n.lineno])
        return f"{start}-{n.end_lineno}"

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append((f"{node.name}  {span(node)}", _first(ast.get_docstring(node))))
            if isinstance(node, ast.ClassDef) and node.end_lineno - node.lineno + 1 > CLASS_METHODS_OVER:
                for m in node.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.append((f"{node.name}.{m.name}  {span(m)}", _first(ast.get_docstring(m))))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.end_lineno - node.lineno + 1 >= DATA_LINES:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if names:
                out.append((f"{names[0]}  {node.lineno}-{node.end_lineno}  (data)", ""))
    return _first(ast.get_docstring(tree)), out


def outline_python(text: str) -> list[Entry]:
    return _py(text)[1]


# -------------------------------------------------------------- Markdown
def _md(text: str) -> tuple[str, list[Entry]]:
    lines = _lines(text)
    i = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() in ("---", "..."):
                i = j + 1
                break
    heads: list[tuple[int, int, str]] = []
    fence = None
    for n in range(i, len(lines)):
        ln = lines[n]
        m = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", ln)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        h = re.match(r"(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$", ln)
        if h:
            heads.append((n + 1, len(h.group(1)), h.group(2)))
    out: list[Entry] = []
    for k, (start, level, title) in enumerate(heads):
        end = next((s - 1 for s, lv, _ in heads[k + 1:] if lv <= level), len(lines))
        out.append((f"{start}-{end}  {'#' * level} {title}", ""))
    doc = heads[0][2] if heads else next((l.strip() for l in lines[i:] if l.strip()), "")
    return doc, out


def outline_markdown(text: str) -> list[Entry]:
    return _md(text)[1]


# -------------------------------------------------------------- Templates
_COMMENT = re.compile(r"\{#(.*?)#\}", re.S)
_TAG = re.compile(r"\{%[-+]?\s*(block|endblock|macro|endmacro)\b[ \t]*(\w*)")
_LINK = re.compile(r"""\{%[-+]?\s*(extends|include|import|from)\s+["']([^"']+)["']""")


def _tpl(text: str) -> tuple[str, list[Entry]]:
    text = text.replace("\r\n", "\n")
    marks: list[tuple[int, Entry]] = []
    doc = ""
    for m in _COMMENT.finditer(text):
        body = m.group(1).strip()
        if not doc:
            doc = _first(body)
        if body.startswith("──"):
            title = _first(body[2:]).strip("─ ").strip()[:90]
            at = text.count("\n", 0, m.start()) + 1
            marks.append((at, (f"{at}  ── {title}", "")))
    code = _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)  # a comment may quote a tag
    stack: list[tuple[str, str, int]] = []
    for ln, line in enumerate(code.split("\n"), 1):
        for t in _TAG.finditer(line):
            if t.group(1) in ("block", "macro"):
                stack.append((t.group(1), t.group(2), ln))
            elif stack:
                kind, name, start = stack.pop()
                marks.append((start, (f"{kind} {name}  {start}-{ln}", "")))
    marks.sort(key=lambda p: p[0])      # stable: the sort key is the line, ties keep source order
    links: dict[str, list[str]] = {}
    for kind, name in _LINK.findall(code):
        links.setdefault(kind, [])
        if name not in links[kind]:
            links[kind].append(name)
    head: list[Entry] = []
    if "extends" in links:
        head.append((f"extends: {', '.join(links['extends'])}", ""))
    inc = [n for k in ("include", "import", "from") for n in links.get(k, []) if n]
    if inc:
        head.append((f"includes: {', '.join(dict.fromkeys(inc))}", ""))
    return doc, head + [e for _, e in marks]


def outline_template(text: str) -> list[Entry]:
    return _tpl(text)[1]


def _walk_py(root: Path):
    base = root / "src" / "astro_ai"
    for p in sorted(base.rglob("*.py")) if base.is_dir() else []:
        if not EXCLUDE_DIRS & set(p.relative_to(base).parts[:-1]):
            yield p


def template_refs(root: Path) -> list[tuple[str, str]]:
    """(template name or glob, where it is named) for every .html literal under src/astro_ai."""
    found: set[tuple[str, str]] = set()
    base = root / "src" / "astro_ai"

    def route(dec: ast.AST) -> str | None:
        if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                and dec.func.attr in ROUTE_METHODS and dec.args
                and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str)):
            return f"{ROUTE_METHODS[dec.func.attr]} {dec.args[0].value}"
        return None

    for p in _walk_py(root):
        try:
            tree = ast.parse(p.read_bytes().decode("utf-8", errors="replace"))
        except (SyntaxError, ValueError, RecursionError):
            continue
        mod = p.relative_to(base).as_posix()

        def labels(owner):
            if owner is None:
                return [f"{mod} (module level)"]
            return [r for r in map(route, owner.decorator_list) if r] or [f"{mod}:{owner.name}"]

        def visit(node, owner):
            for ch in ast.iter_child_nodes(node):
                if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) and owner is None:
                    visit(ch, ch)
                    continue
                if isinstance(ch, ast.Constant) and isinstance(ch.value, str) and ch.value.endswith(".html"):
                    found.update((ch.value, lb) for lb in labels(owner))
                elif isinstance(ch, ast.JoinedStr):
                    pat = re.sub(r"\*+", "*", "".join(
                        v.value if isinstance(v, ast.Constant) else "*" for v in ch.values))
                    if pat.endswith(".html") and "*" in pat and pat.split("*")[0].endswith("/"):
                        found.update((pat, lb) for lb in labels(owner))
                    for v in ch.values:
                        if isinstance(v, ast.FormattedValue):
                            visit(v, owner)
                    continue
                visit(ch, owner)

        visit(tree, None)
    return sorted(found)


def _template_links(root: Path) -> dict[str, dict[str, list[str]]]:
    """{"included": {target: [referrers]}, "extended": {...}} over every template, sorted."""
    base = root / "src" / "astro_ai" / "templates"
    out: dict[str, dict[str, set[str]]] = {"included": {}, "extended": {}}
    for p in sorted(base.rglob("*.html")) if base.is_dir() else []:
        code = _COMMENT.sub("", p.read_bytes().decode("utf-8", errors="replace"))
        me = p.relative_to(base).as_posix()
        for kind, name in _LINK.findall(code):
            out["extended" if kind == "extends" else "included"].setdefault(name, set()).add(me)
    return {k: {n: sorted(v) for n, v in d.items()} for k, d in out.items()}


def _named_in(key: str, tidx: tuple[list[tuple[str, str]], dict]) -> str:
    refs, links = tidx

    def fmt(names: list[str]) -> str:
        names = sorted(set(names))
        return ", ".join(names[:6]) + (f" (+{len(names) - 6} more)" if len(names) > 6 else "")

    hits = [lb for pat, lb in refs if fnmatch.fnmatchcase(key, pat)]
    if hits:
        return "named in: " + fmt(hits)
    parts = [f"{w} by: {fmt(links[k][key])}" for w, k in (("included", "included"), ("extended", "extended"))
             if key in links[k]]
    return "; ".join(parts) or "no literal reference found (dynamic name?)"


# ---------------------------------------------------------------- Packing
def _clip(line: str) -> str:
    return line if len(line) <= LINE_CAP else line[:LINE_CAP - 1] + "…"


def _render(f: FileOutline, doclen: int) -> list[str]:
    name, n, doc, entries, full = f

    def one(label: str, d: str, indent: str) -> str:
        return _clip(f"{indent}{label}" + (f"  {d[:doclen]}" if d and doclen else ""))

    return [one(f"{name}  {n} lines", doc, "")] + ([one(l, d, "  ") for l, d in entries] if full else [])


def _header(title: str, i: int, n: int) -> str:
    return f"# {title}" + (f"  (part {i}/{n})" if n > 1 else "") + f"\n{STALE}\n"


def pack(files: list[FileOutline], cap: int = MAX_CHARS, title: str = "index") -> list[str]:
    """Render `files` into parts of at most `cap` chars. Never drops an entry."""
    budget = cap - len(_header(title, 99, 99))
    size = lambda ls: sum(len(l) + 1 for l in ls)
    for doclen in DOC_LADDER:
        body = [l for f in files for l in _render(f, doclen)]
        if size(body) <= budget:
            return [_header(title, 1, 1) + "".join(l + "\n" for l in body)]
    units: list[list[str]] = []
    for f in files:
        lines = _render(f, DOC_LADDER[0])
        if size(lines) <= budget:
            units.append(lines)
            continue
        room = budget - LINE_CAP - 1
        groups: list[list[str]] = [[]]
        for l in lines[1:]:
            if size(groups[-1]) + len(l) + 1 > room:
                groups.append([])
            groups[-1].append(l)
        for k, g in enumerate(groups, 1):
            head = f"{f[0]} part {k}/{len(groups)}  {f[1]} lines" + (f"  {f[2][:DOC_LADDER[0]]}" if k == 1 and f[2] else "")
            units.append([_clip(head)] + g)
    parts: list[list[str]] = [[]]
    for u in units:
        if parts[-1] and size(parts[-1]) + size(u) > budget:
            parts.append([])
        parts[-1].extend(u)
    return [_header(title, i, len(parts)) + "".join(l + "\n" for l in p) for i, p in enumerate(parts, 1)]


# ------------------------------------------------------------------ Driver
def describe(name: str, text: str, full: bool, tkey: str | None = None, tidx=None) -> FileOutline:
    n = len(_lines(text))
    suffix = name.rsplit(".", 1)[-1]
    doc, entries = {"py": _py, "md": _md, "html": _tpl}.get(suffix, lambda t: ("", []))(text)
    if entries and entries[0][0].startswith("PARSE ERROR"):
        print(f"warning: {name}: syntax error ({entries[0][0]})", file=sys.stderr)
        if not full:                # a full outline already shows the entry; once is enough
            doc = doc or entries[0][0]
    if suffix == "html" and tkey is not None and tidx is not None:
        entries = [(_named_in(tkey, tidx), "")] + entries
    return name, n, doc, entries, full or False


def _read(p: Path) -> str | None:
    try:
        return p.read_bytes().decode("utf-8", errors="replace")
    except OSError as e:
        print(f"warning: cannot read {p}: {e}", file=sys.stderr)
        return None


def _in_scope(rel: str) -> bool:
    parts = rel.split("/")
    if len(parts) == 1:
        return rel.endswith(".md")
    if rel.startswith("src/astro_ai/"):
        return rel.endswith(".py") or (rel.endswith(".html") and parts[2] == "templates") \
            or (rel.endswith(".md") and parts[2] == "knowledge")
    if parts[0] == "scripts":
        return len(parts) == 2 and rel.endswith(".py")
    return parts[0] in ("docs", ".claude") and rel.endswith(".md")


def _scan(root: Path) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for d, dirs, files in os.walk(root):
        rel_d = Path(d).relative_to(root).as_posix()
        rel_d = "" if rel_d == "." else rel_d
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDE_DIRS and (rel_d or x in TOP_DIRS))
        for fn in sorted(files):
            rel = f"{rel_d}/{fn}" if rel_d else fn
            if _in_scope(rel):
                groups.setdefault(rel_d, []).append(fn)
    return groups


def _template_key(root: Path, p: Path) -> str | None:
    try:
        return p.resolve().relative_to((root / "src" / "astro_ai" / "templates").resolve()).as_posix()
    except ValueError:
        return None


def _check_out(out: Path) -> None:
    if out.exists() and (not out.is_dir() or (any(out.iterdir()) and not (out / "INDEX.md").is_file())):
        raise UsageError(f"{out} exists and was not written by this script (no INDEX.md); refusing to touch it")


_LISTED = re.compile(r"([\w.\-]+\.md)  ")


def _previous_names(out: Path) -> list[str]:
    """Files the last run wrote, read from its INDEX.md. A name with a path separator can never
    match, and INDEX.md itself is rewritten, not unlinked: a hand-edited index cannot make this
    delete anything outside the directory or anything the tool did not list."""
    try:
        text = (out / "INDEX.md").read_text(encoding="utf-8")
    except OSError:
        return []
    return [m.group(1) for m in map(_LISTED.match, text.split("\n")) if m and m.group(1) != "INDEX.md"]


def build(root: Path, out: Path) -> list[str]:
    root, out = Path(root), Path(out)
    _check_out(out)
    tidx = (template_refs(root), _template_links(root))
    out.mkdir(parents=True, exist_ok=True)
    for stale in _previous_names(out):      # only what this tool wrote: never `*.md` (#1466 QA)
        (out / stale).unlink(missing_ok=True)
    index = ["# Code index", STALE, "Written by scripts/build_code_index.py; generated, never committed.", ""]
    names: list[str] = []
    for rel_d, fns in sorted(_scan(root).items()):
        files = []
        for fn in fns:
            p = root / rel_d / fn
            text = _read(p)
            if text is not None:
                full = len(_lines(text)) >= SMALL_FILE_LINES
                files.append(describe(fn, text, full, _template_key(root, p), tidx))
        if not files:
            continue
        stem = (rel_d or "_root").replace("/", "__")
        parts = pack(files, MAX_CHARS, rel_d or "(repo root)")
        for i, body in enumerate(parts, 1):
            fname = f"{stem}.md" if i == 1 else f"{stem}.{i}.md"
            (out / fname).write_text(body, encoding="utf-8")
            names.append(fname)
            index.append(f"{fname}  {rel_d or '(repo root)'}  {len(files)} files" + (f"  part {i}/{len(parts)}" if len(parts) > 1 else ""))
    (out / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return names


def outline_path(root: Path, target: Path) -> str:
    tidx = (template_refs(root), _template_links(root))
    paths = [target]
    if target.is_dir():
        paths = []
        for d, dirs, fs in os.walk(target):
            dirs[:] = sorted(x for x in dirs if x not in EXCLUDE_DIRS)
            paths += [Path(d) / f for f in sorted(fs) if f.endswith((".py", ".md", ".html"))]
    files = []
    for p in paths:
        text = _read(p)
        if text is not None:
            try:
                name = p.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                name = p.as_posix()
            full = target.is_file() or len(_lines(text)) >= SMALL_FILE_LINES
            files.append(describe(name, text, full, _template_key(root, p), tidx))
    return "".join("".join(l + "\n" for l in _render(f, DOC_LADDER[0])) for f in files)


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description="Outline files with line ranges (see the module docstring).")
    ap.add_argument("path", nargs="?", help="file or directory to print; omit to write the index")
    ap.add_argument("--out", help="index directory (default .code-index/)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    try:
        if args.path:
            if args.out:
                raise UsageError("--out is for writing the index; it cannot be combined with a path")
            target = Path(args.path)
            if not target.exists():
                raise UsageError(f"{args.path}: no such file or directory")
            sys.stdout.write(outline_path(root, target))
        else:
            names = build(root, Path(args.out) if args.out else root / ".code-index")
            print(f"wrote {len(names) + 1} files")
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: cannot write the index: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
