"""The mutation table's anchor pre-flight, in both directions (#418, QA round 5).

The pre-flight runs before the sweep and can fail the whole gate on its own, so
it is a gate in its own right -- and it was wrong. Round 5 measured it rejecting
**65 of 243 rows**: it looked for the anchor's first line by scanning EVERY line
of the target file, so any line that merely *contained* that text satisfied
`first in line`, and a comment quoting a line of code condemned the row that
mutates it. A false positive in the blocking direction, in the validator added
to stop exactly this class of mistake.

It cannot be imported to test it -- `scripts/mutate_behaviour_suite.py` has no
`__main__` guard, so importing it starts a ~40-minute sweep -- so these drive it
as a subprocess through `--preflight-only`.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/mutate_behaviour_suite.py"


def _run(path: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(path), "--preflight-only"],
                          capture_output=True, text=True, timeout=300)


def test_the_preflight_passes_on_the_real_table():
    """The N-5 regression. If this goes red, no sweep runs at all."""
    r = _run(SCRIPT)
    assert r.returncode == 0, (
        f"the pre-flight refuses the committed table, so the sweep cannot "
        f"run:\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")
    assert "anchor pre-flight:" in r.stdout, r.stdout[-500:]


def test_the_table_really_does_hold_multi_line_anchors():
    """Without this, the test above passes vacuously the day the last
    multi-line anchor is removed -- and the defect it guards is SPECIFIC to a
    multi-line anchor, whose first line is a short, ordinary line of code that
    a comment somewhere else is entirely likely to quote."""
    import ast
    rows = [n.value for n in ast.walk(ast.parse(SCRIPT.read_text()))
            if isinstance(n, ast.Assign)
            and any(getattr(t, "id", "") == "MUTATIONS" for t in n.targets)][0]
    multi = 0
    for el in rows.elts:
        try:
            _label, _rel, old, _new, _test = [ast.literal_eval(x) for x in el.elts][:5]
        except Exception:
            continue
        if "\n" in old:
            multi += 1
    assert multi >= 20, (
        f"only {multi} multi-line anchors; the pre-flight regression this file "
        f"exists for is specific to them")


def test_an_anchor_that_begins_on_a_comment_line_is_still_refused(tmp_path):
    """The other direction, so the fix did not simply disable the rule.

    A probe copy of the script is written INSIDE the repo, because the script
    derives `ROOT` from its own `__file__`; a copy in `tmp_path` would resolve
    every row's path against the wrong tree. It is removed again in `finally`.

    The marker is assembled at runtime from two fragments so that the row's own
    source text does not contain it -- otherwise the anchor would occur twice in
    the probe file and the pre-flight would refuse it for the wrong reason,
    which would make this test pass while proving nothing.
    """
    probe = SCRIPT.parent / "_preflight_probe_tmp.py"
    src = SCRIPT.read_text()
    needle = "_anchor_problems = _preflight_anchors()"
    assert needle in src
    injected = (
        'MUTATIONS = list(MUTATIONS) + [(\n'
        '    "PROBE: an anchor that begins on a comment line",\n'
        f'    "scripts/{probe.name}",\n'
        '    "# zzz-probe" + "-marker-line",\n'
        '    "# mutated-marker",\n'
        '    "test_nothing")]\n'
    )
    probe.write_text(src.replace(needle, injected + needle, 1)
                     + "\n# zzz-probe" "-marker-line\n")
    try:
        r = _run(probe)
        assert r.returncode == 1, (
            f"a row anchored on a COMMENT line was accepted:\n{r.stdout[-2000:]}")
        assert "begins on a COMMENT line" in r.stdout, r.stdout[-2000:]
        assert "PROBE:" in r.stdout, r.stdout[-2000:]
    finally:
        probe.unlink(missing_ok=True)


def test_a_comment_quoting_an_anchors_first_line_does_not_condemn_the_row():
    """The N-5 regression itself, which the committed table CANNOT express.

    Measured on this branch: the old scanning rule rejects 0 of 268 rows, the
    same as the fixed rule, so "the real table passes" proves nothing about it.
    The defect needs one comment anywhere in the target file that contains the
    anchor's FIRST line -- which is why round 5 demonstrated it by adding one,
    and why 67 of this table's anchors are one such comment away from being
    refused.

    The shape has to be a MULTI-LINE anchor: the full anchor occurs once (so the
    uniqueness check passes) while its first line occurs twice (once as the code
    being mutated, once inside prose). Written into a probe copy so the
    committed table is untouched.
    """
    probe = SCRIPT.parent / "_preflight_quote_probe_tmp.py"
    src = SCRIPT.read_text()
    needle = "_anchor_problems = _preflight_anchors()"
    assert needle in src
    # The anchor is two REAL lines of code; the row below carries them as one
    # source line with an escaped newline, so the two-line text occurs exactly
    # once in the file -- in the appended code, not in the row that names it.
    injected = (
        'MUTATIONS = list(MUTATIONS) + [(\n'
        '    "PROBE: multi-line anchor whose first line is quoted in a comment",\n'
        f'    "scripts/{probe.name}",\n'
        '    "zzz_probe_first = 1\\nzzz_probe_second = 2",\n'
        '    "zzz_probe_first = 9\\nzzz_probe_second = 2",\n'
        '    "test_nothing")]\n'
    )
    probe.write_text(
        src.replace(needle, injected + needle, 1)
        + "\nzzz_probe_first = 1\nzzz_probe_second = 2\n"
        + "# zzz_probe_first = 1  <- prose quoting the line above\n")
    try:
        body = probe.read_text()
        assert body.count("zzz_probe_first = 1\nzzz_probe_second = 2") == 1, (
            "the anchor must be unique or the pre-flight refuses it for the "
            "wrong reason and this test passes while proving nothing")
        assert sum(1 for l in body.splitlines()
                   if "zzz_probe_first = 1" in l
                   and l.lstrip().startswith("#")) == 1, (
            "the fixture needs exactly one COMMENT line quoting the first line")

        r = _run(probe)
        assert r.returncode == 0, (
            "a comment that merely QUOTES the anchor's first line condemned the "
            "row that mutates the code -- the round-5 false positive, in the "
            f"blocking direction:\n{r.stdout[-2000:]}")
        assert "COMMENT line" not in r.stdout, r.stdout[-2000:]
    finally:
        probe.unlink(missing_ok=True)
