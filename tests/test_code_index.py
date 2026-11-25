"""scripts/build_code_index.py -- the look-up-before-you-read index (#1466, part of #1256).

93.9% of agent-work tokens are cache reads, and a whole-file `Read` of a 5,000-line file sits in
every later turn. The index lets an agent read one line range instead. Its whole value is that a
listed range IS the symbol, so these tests pin ranges (decorators, EOF), the fences and front
matter that would invent phantom headings, the 8,000-char budget with nothing dropped, and that
writing the index can never clobber a directory the script did not make.

Fixtures are tmp_path trees; the last class runs against the real repo.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_code_index", ROOT / "scripts" / "build_code_index.py")
bci = importlib.util.module_from_spec(_spec)
sys.modules["build_code_index"] = bci
_spec.loader.exec_module(bci)

RULE = "**Look up before you read (#1256).**"
AGENTS = ("backend-engineer", "frontend-engineer", "qa", "architect")


def labels(entries):
    return [e[0] for e in entries]


class TestPython:
    def test_decorator_range_starts_at_the_decorator_and_async_is_listed(self):
        src = textwrap.dedent('''\
            import x

            @router.get("/a")
            @other
            def a():
                """First line.

                More."""
                return 1

            async def b():
                pass
            ''')
        got = dict(bci.outline_python(src))
        assert "a  3-9" in got and got["a  3-9"] == "First line."
        assert "b  11-12" in got

    def test_class_over_60_lines_lists_methods_and_a_short_one_does_not(self):
        big = "class Big:\n" + "".join(f"    def m{i}(self):\n        pass\n" for i in range(32))
        small = "class Small:\n    def only(self):\n        pass\n"
        out = labels(bci.outline_python(big + small))
        assert any(l.startswith("Big.m0  ") for l in out) and any(l.startswith("Big.m31  ") for l in out)
        assert not any(l.startswith("Small.") for l in out)

    def test_a_30_line_constant_is_data_and_a_29_line_one_is_not(self):
        rows = "".join(f"    {i},\n" for i in range(28))
        out = labels(bci.outline_python(f"TABLE = [\n{rows}]\nSMALL = [\n{rows[:-12]}]\n"))
        assert out == ["TABLE  1-30  (data)"]

    def test_syntax_error_is_one_line_and_does_not_crash(self):
        assert labels(bci.outline_python("def ok():\n    pass\ndef broken(:\n")) == ["PARSE ERROR L3"]


class TestMarkdown:
    def test_nested_ranges_and_last_heading_runs_to_eof(self):
        md = "# A\ntext\n## B\ntext\n### C\n## D\nlast\n"
        assert labels(bci.outline_markdown(md)) == [
            "1-7  # A", "3-5  ## B", "5-5  ### C", "6-7  ## D"]

    def test_heading_inside_a_fence_is_ignored(self):
        md = "# A\n```bash\n# not a heading\n```\n~~~\n# nor this\n~~~\n## B\n"
        assert labels(bci.outline_markdown(md)) == ["1-8  # A", "8-8  ## B"]

    def test_front_matter_comment_is_ignored(self):
        md = "---\n# a yaml comment\ntitle: x\n---\n# Real\nbody\n"
        assert labels(bci.outline_markdown(md)) == ["5-6  # Real"]


TEMPLATE = textwrap.dedent('''\
    {% extends "base.html" %}
    {# a comment quoting {% block ghost %} must not open a block #}
    {% from "macros.html" import card %}
    {% block content %}
      {# ── Hero. The first section. ──── #}
      {% include "partials/nav.html" %}
      {% macro row(x) -%}
        <td>{{ x }}</td>
      {%- endmacro %}
      {% block inner %}
      {% endblock inner %}
      {% include "partials/nav.html" %}
    {% endblock %}
    ''')


class TestTemplate:
    def test_blocks_macro_landmark_extends_includes(self):
        out = labels(bci.outline_template(TEMPLATE))
        assert out[0] == "extends: base.html"
        assert out[1] == "includes: partials/nav.html, macros.html"
        assert "block content  4-13" in out and "macro row  7-9" in out
        assert "block inner  10-11" in out
        assert "5  ── Hero. The first section." in out
        assert not any("ghost" in l for l in out)

    def test_routes_name_the_template(self, tmp_path):
        py = tmp_path / "src" / "astro_ai" / "routes"
        py.mkdir(parents=True)
        (py / "r.py").write_text(textwrap.dedent('''\
            @router.get("/x")
            def page(request):
                return templates.TemplateResponse(request, "x.html", {})

            def learn(slug):
                return templates.TemplateResponse(request, f"learn/{slug}.html", {})

            def helper():
                return f"{slug}.html"
            '''))
        refs = bci.template_refs(tmp_path)
        assert ("x.html", "GET /x") in refs
        assert ("learn/*.html", "routes/r.py:learn") in refs
        assert not any(p == "*.html" for p, _ in refs)       # no literal dir prefix: too broad
        links = {"included": {"inc.html": ["a.html", "b.html"]}, "extended": {}}
        assert bci._named_in("x.html", (refs, links)) == "named in: GET /x"
        assert bci._named_in("learn/vata.html", (refs, links)) == "named in: routes/r.py:learn"
        assert bci._named_in("inc.html", (refs, links)) == "included by: a.html, b.html"
        assert bci._named_in("lost.html", (refs, links)).startswith("no literal reference found")

    def test_full_outline_of_a_named_template_says_where_it_is_named(self, tmp_path):
        (tmp_path / "src" / "astro_ai" / "templates").mkdir(parents=True)
        (tmp_path / "src" / "astro_ai" / "routes").mkdir()
        (tmp_path / "src" / "astro_ai" / "routes" / "r.py").write_text(
            '@router.get("/x")\ndef p():\n    return "x.html"\n')
        t = tmp_path / "src" / "astro_ai" / "templates" / "x.html"
        t.write_text("{% block a %}\n{% endblock %}\n")
        assert "named in: GET /x" in bci.outline_path(tmp_path, t)


class TestSmallFileRule:
    @staticmethod
    def _py_lines(n):
        """A python file of exactly n lines holding 3 top-level defs."""
        body = "".join(f"def f{i}():\n    pass\n" for i in range(3)) + "# pad\n" * (n - 6)
        assert len(body.splitlines()) == n
        return body

    def test_399_lines_is_one_line_and_400_is_outlined_through_build(self, tmp_path, tmp_path_factory):
        # Driven through build() with LITERAL sizes, so a changed threshold (10, 399, 401, 4000)
        # goes red; the old test recomputed the threshold in its own body and could not.
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "a399.py").write_text(self._py_lines(399))
        (tmp_path / "scripts" / "b400.py").write_text(self._py_lines(400))
        out = tmp_path_factory.mktemp("small")
        assert bci.main(["--out", str(out)], root=tmp_path) == 0
        got = (out / "scripts.md").read_text().split("\n")
        assert "a399.py  399 lines" in got                       # one line, no entries under it
        assert "b400.py  400 lines" in got
        after = got[got.index("b400.py  400 lines") + 1:]
        assert after[:3] == ["  f0  1-2", "  f1  3-4", "  f2  5-6"]
        assert not any(l.startswith("  f") for l in got[:got.index("b400.py  400 lines")])

    def test_399_and_400_lines_through_the_path_form(self, tmp_path):
        a, b = tmp_path / "a399.py", tmp_path / "b400.py"
        a.write_text(self._py_lines(399))
        b.write_text(self._py_lines(400))
        out = bci.outline_path(tmp_path, tmp_path).split("\n")
        assert out.count("a399.py  399 lines") == 1 and "  f0  1-2" in out[out.index("b400.py  400 lines"):]
        assert not any(l.startswith("  f") for l in out[:out.index("b400.py  400 lines")])
        assert "  f2  5-6" in bci.outline_path(tmp_path, a).split("\n")   # a named file is always full


class TestBudget:
    def test_400_functions_split_into_parts_and_nothing_is_dropped(self):
        body = "".join(f'def function_number_{i:03d}():\n    """Does thing {i} with a fairly long docstring line."""\n'
                        for i in range(400))
        parts = bci.pack([bci.describe("big.py", body, True)], title="d")   # the default cap
        assert len(parts) > 1
        assert all(len(p) <= 8000 for p in parts)
        joined = "".join(parts)
        assert all(f"function_number_{i:03d}" in joined for i in range(400))
        assert "big.py part 2/" in parts[1] and "Line numbers are valid until the file is edited" in parts[1]

    def test_a_dir_that_fits_stays_one_part_by_shrinking_docstrings(self):
        files = [bci.describe(f"m{i}.py", f'"""{"x" * 90}"""\n', False) for i in range(75)]
        parts = bci.pack(files, title="d")
        assert len(parts) == 1 and len(parts[0]) <= 8000

    def test_build_writes_files_of_at_most_8000_chars(self, tmp_path, tmp_path_factory):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "big.py").write_text("".join(
            f'def function_number_{i:03d}():\n    """Does thing {i} with a fairly long docstring line."""\n'
            for i in range(900)))
        out = tmp_path_factory.mktemp("budget")
        assert bci.main(["--out", str(out)], root=tmp_path) == 0
        sizes = [len(p.read_text(encoding="utf-8")) for p in out.glob("scripts*.md")]
        assert len(sizes) > 1 and max(sizes) <= 8000 and max(sizes) > 6000   # full parts, not tiny ones

    def test_a_single_line_is_hard_truncated(self):
        assert len(bci._clip("x" * 500)) == bci.LINE_CAP


@pytest.fixture
def mini_repo(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "s.py").write_text('"""A script."""\ndef go():\n    pass\n')
    (tmp_path / "README.md").write_text("# Hi\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("def hidden():\n    pass\n")
    return tmp_path


class TestCliAndSafety:
    def test_path_form_prints_and_writes_nothing(self, mini_repo, capsys):
        before = sorted(p.name for p in mini_repo.rglob("*"))
        assert bci.main([str(mini_repo / "scripts")], root=mini_repo) == 0
        assert "s.py  3 lines  A script." in capsys.readouterr().out
        assert sorted(p.name for p in mini_repo.rglob("*")) == before

    def test_bad_usage_exits_2(self, mini_repo):
        assert bci.main([str(mini_repo / "nope")], root=mini_repo) == 2
        assert bci.main(["--bogus"], root=mini_repo) == 2
        assert bci.main([str(mini_repo), "--out", str(mini_repo / "o")], root=mini_repo) == 2

    def test_out_on_a_foreign_nonempty_dir_exits_2_and_leaves_it_intact(self, mini_repo, tmp_path_factory):
        out = tmp_path_factory.mktemp("foreign")
        (out / "precious.md").write_text("mine")
        assert bci.main(["--out", str(out)], root=mini_repo) == 2
        assert (out / "precious.md").read_text() == "mine" and not (out / "INDEX.md").exists()

    def test_rerun_keeps_files_it_did_not_write_and_removes_its_own_stale_parts(self, mini_repo, tmp_path_factory):
        out = tmp_path_factory.mktemp("keep")
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        (out / "precious.md").write_text("mine")
        (out / "NOTES.md").write_text("notes")
        (out / "zzz.9.md").write_text("not listed, so not ours")
        # a part file the PREVIOUS run listed and this run no longer produces
        (out / "scripts.2.md").write_text("old part")
        idx = out / "INDEX.md"
        idx.write_text(idx.read_text() + "scripts.2.md  scripts  1 files  part 2/2\n")
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        assert not (out / "scripts.2.md").exists()
        assert "scripts.2.md" not in idx.read_text()
        assert (out / "precious.md").read_text() == "mine"
        assert (out / "NOTES.md").read_text() == "notes" and (out / "zzz.9.md").exists()
        assert (out / "scripts.md").is_file() and (out / "_root.md").is_file()

    def test_a_dotfile_part_is_listed_in_the_index_and_removed_when_stale(self, mini_repo, tmp_path_factory):
        (mini_repo / ".claude").mkdir()
        (mini_repo / ".claude" / "x.md").write_text("# X\n")
        out = tmp_path_factory.mktemp("dot")
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        assert (out / ".claude.md").is_file() and ".claude.md  .claude" in (out / "INDEX.md").read_text()
        (mini_repo / ".claude" / "x.md").unlink()
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        assert not (out / ".claude.md").exists()

    def test_an_uncreatable_out_is_one_stderr_line_and_exit_2(self, mini_repo, tmp_path, capsys):
        blocker = tmp_path / "afile"
        blocker.write_text("x")
        assert bci.main(["--out", str(blocker / "idx")], root=mini_repo) == 2
        err = capsys.readouterr().err
        assert err.startswith("error: ") and "Traceback" not in err and len(err.strip().splitlines()) == 1

    def test_a_binary_py_file_reports_its_parse_error_once(self, tmp_path):
        (tmp_path / "bin.py").write_bytes(b"\x00\x01\xff" * 600)
        assert bci.outline_path(tmp_path, tmp_path / "bin.py").count("PARSE ERROR") == 1

    def test_rerun_over_its_own_output_is_byte_identical(self, mini_repo, tmp_path_factory):
        out = tmp_path_factory.mktemp("idx")
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        first = {p.name: p.read_bytes() for p in out.iterdir()}
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        assert {p.name: p.read_bytes() for p in out.iterdir()} == first
        assert "tests" not in (out / "INDEX.md").read_text() and "hidden" not in "".join(
            p.read_text() for p in out.iterdir())

    def test_index_dir_is_gitignored(self):
        # The mutation sandbox does not copy the root .gitignore (same trap as
        # test_research_corpus_fetch.py on #1063: the CONTROL row went blind), so the check
        # runs wherever the file exists -- every real checkout and pr-gates.
        gi = ROOT / ".gitignore"
        if gi.exists():
            assert ".code-index/" in gi.read_text().split()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("real")
    t = time.perf_counter()
    assert bci.main(["--out", str(out)]) == 0
    return out, time.perf_counter() - t


class TestRealRepo:
    def test_full_run_is_fast_and_every_file_fits(self, built):
        out, secs = built
        assert secs < 5
        files = list(out.glob("*.md"))
        assert len(files) > 10 and (out / "INDEX.md").is_file()
        assert max(len(p.read_text(encoding="utf-8")) for p in files) <= 8000   # literal, not bci.MAX_CHARS

    def test_every_chart_py_range_is_structurally_valid(self):
        lines = (ROOT / "src" / "astro_ai" / "chart.py").read_text(encoding="utf-8").split("\n")
        n = len(lines) - 1
        entries = bci.outline_python("\n".join(lines))
        assert len(entries) > 50
        for label, _ in entries:
            m = re.match(r"(\S+)  (\d+)-(\d+)", label)
            assert m, label
            name, start, end = m.group(1), int(m.group(2)), int(m.group(3))
            assert 1 <= start <= end <= n, label
            assert name.split(".")[-1] in lines[start - 1] or "@" in lines[start - 1], label
            assert lines[end - 1].strip(), label              # the range ends on code, not a blank
            if end < n:                                       # and what follows is blank or a new top-level line
                nxt = lines[end]
                assert not nxt.strip() or not nxt[0].isspace(), label

    @pytest.mark.parametrize("agent", AGENTS)
    def test_the_rule_is_pinned_in_every_agent_file(self, agent):
        text = (ROOT / ".claude" / "agents" / f"{agent}.md").read_text(encoding="utf-8")
        assert RULE in text
        assert "uv run python scripts/build_code_index.py <path>" in text
        assert "A stale line range is a pointer, not evidence." in text
