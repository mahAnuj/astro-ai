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
    def test_under_400_lines_is_one_line_and_400_is_outlined(self):
        small = "def f():\n    pass\n" * 1 + "\n" * 10
        f = bci.describe("a.py", small, len(small.splitlines()) >= 400)
        assert len(bci._render(f, 70)) == 1
        body = "\n".join(f"def f{i}():\n    pass" for i in range(200)) + "\n"
        big = bci.describe("b.py", body, True)
        assert len(bci._render(big, 70)) == 201


class TestBudget:
    def test_400_functions_split_into_parts_and_nothing_is_dropped(self):
        body = "".join(f'def function_number_{i:03d}():\n    """Does thing {i} with a fairly long docstring line."""\n'
                        for i in range(400))
        parts = bci.pack([bci.describe("big.py", body, True)], 8000, "d")
        assert len(parts) > 1
        assert all(len(p) <= 8000 for p in parts)
        joined = "".join(parts)
        assert all(f"function_number_{i:03d}" in joined for i in range(400))
        assert "big.py part 2/" in parts[1] and "Line numbers are valid until the file is edited" in parts[1]

    def test_a_dir_that_fits_stays_one_part_by_shrinking_docstrings(self):
        files = [bci.describe(f"m{i}.py", f'"""{"x" * 90}"""\n', False) for i in range(75)]
        parts = bci.pack(files, 8000, "d")
        assert len(parts) == 1 and len(parts[0]) <= 8000

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

    def test_rerun_over_its_own_output_removes_stale_files_and_is_byte_identical(self, mini_repo, tmp_path_factory):
        out = tmp_path_factory.mktemp("idx")
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        (out / "stale.md").write_text("old")
        first = {p.name: p.read_bytes() for p in out.iterdir()}
        (out / "stale.md").unlink()
        assert bci.main(["--out", str(out)], root=mini_repo) == 0
        assert {p.name: p.read_bytes() for p in out.iterdir()} == {k: v for k, v in first.items() if k != "stale.md"}
        (out / "stale.md").write_text("old")
        assert bci.main(["--out", str(out)], root=mini_repo) == 0 and not (out / "stale.md").exists()
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
        assert max(len(p.read_text(encoding="utf-8")) for p in files) <= bci.MAX_CHARS

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

    @pytest.mark.parametrize("agent", AGENTS)
    def test_the_rule_is_pinned_in_every_agent_file(self, agent):
        text = (ROOT / ".claude" / "agents" / f"{agent}.md").read_text(encoding="utf-8")
        assert RULE in text
        assert "uv run python scripts/build_code_index.py <path>" in text
        assert "A stale line range is a pointer, not evidence." in text
