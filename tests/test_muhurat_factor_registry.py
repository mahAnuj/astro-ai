"""#1017 R3: every factor and exclusion the finder applies has an entry in
`muhurat_factors.REGISTRY`, with a status, a source heading that still exists, and a page
sentence a visitor can read.

The issue's rule is "no factor reaches the page without one of the two": sourced (a
knowledge/ heading) or flagged as this finder's own convention. These tests read the real
scorer source (AST), the real knowledge files and the real `find_candidates` output; the
auditor's per-event exclusion table is the one thing written out literally, because it is the
ruling the code is checked against (astro-auditor, #1017, 2026-11-21).

No network (geocoding is stubbed) and no LLM. Mutation rows:
scripts/mutations/2026_11_21_1017_r3_factor_registry.py.
"""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

import pytest

from astro_ai import chart, muhurat as m
from astro_ai import muhurat_factors as mf
from test_muhurat_classical_copy import CLAIM, UNSOURCED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "verify_rule_citations", ROOT / "scripts" / "verify_rule_citations.py")
vrc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vrc)

SRC = ROOT / "src" / "astro_ai"
EVENTS = ["vivah", "griha_pravesh", "vidyarambh", "namkaran", "business"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DELHI = (28.61, 77.21, "Asia/Kolkata")
FORBIDDEN_IN_COPY = ("§", "Ch.", "knowledge/", ".md", "Chintamani", "BPHS", "Phaladeepika")
SOFT = ("good_tithi", "good_nakshatra", "good_weekday", "peak_day", "avoid_weekday_soft")

# The auditor's section A, by its own numbering: which exclusions each event applies.
NUM = {10: "adhik_maas", 11: "eclipse", 12: "nitya_yoga_block", 13: "panchak",
       14: "chaturmas", 15: "kharmas", 16: "dagdha", 17: "jupiter_combust",
       18: "venus_combust", 19: "mercury_combust", 20: "avoid_nakshatra",
       21: "avoid_nakshatra_pada", 22: "avoid_tithi", 23: "avoid_krishna_tithi",
       24: "avoid_weekday"}
AUDITOR_A = {
    "vivah": [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24],
    "griha_pravesh": [10, 11, 12, 13, 14, 15, 16, 17, 20, 22, 24],
    "vidyarambh": [10, 11, 12, 13, 16, 17, 20, 22, 24],
    "business": [10, 11, 12, 13, 15, 16, 19, 20, 22, 24],
    "namkaran": [10, 11, 12, 13, 20, 22, 24],
}
ABUJHA_SENTENCE = (
    "Listed as an Abujha date, a regional almanac custom this finder includes; no book it holds "
    "names it. The usual exclusion checks were not run for this date, so confirm the tithi, star "
    "and Panchak with your priest or panchang.")


def _cand(event="vivah", **kw):
    base = dict(d=date(2026, 12, 2), weekday="Wednesday", tithi="Dwitiya", tithi_paksha="Shukla",
                nakshatra="Hasta", rating="excellent", reason="", flags=())
    base.update(kw)
    return m.MuhuratCandidate(**base)


@pytest.fixture(scope="module")
def scans():
    mp = pytest.MonkeyPatch()
    mp.setattr(chart, "geocode_place", lambda place: DELHI)
    try:
        yield {e: m.find_candidates(e, "Delhi, India", date(2026, 11, 21), 200) for e in EVENTS}
    finally:
        mp.undo()


# ─── (a) every flag the scorer can emit has an entry ──────────────────────────────────────────
def _scorer_flag_literals() -> tuple[list[str], list[str]]:
    """(flag literals, booster names) found in muhurat.py by AST: `flags.append("x")`, a
    `flags=("x",)` keyword, and the name tuple inside `flags.extend(...)`."""
    tree = ast.parse((SRC / "muhurat.py").read_text(encoding="utf-8"))
    flags: list[str] = []
    boosters: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) \
                and fn.value.id == "flags":
            if fn.attr == "append" and node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                flags.append(node.args[0].value)
            if fn.attr == "extend":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Tuple) and sub.elts and all(
                            isinstance(e, ast.Constant) and isinstance(e.value, str)
                            for e in sub.elts):
                        boosters += [e.value for e in sub.elts]
        for kw in node.keywords:
            if kw.arg == "flags" and isinstance(kw.value, ast.Tuple):
                flags += [e.value for e in kw.value.elts
                          if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    return flags, boosters


def test_every_flag_the_scorer_can_emit_has_a_registry_entry():
    flags, boosters = _scorer_flag_literals()
    # a scan that finds nothing must fail, not pass (#193)
    assert len(flags) >= 17, flags
    assert len(boosters) == 3, boosters
    emitted = set(flags) | {b.lower().replace(" ", "_") for b in boosters}
    assert {"avoid_weekday", "abujha_muhurat", "amrit_siddhi", "panchak"} <= emitted
    keys = {mf.registry_key_for_flag(f, wd) for f in emitted for wd in WEEKDAYS}
    missing = (keys | set(SOFT)) - set(mf.REGISTRY)
    assert not missing, f"scorer flags with no registry entry: {sorted(missing)}"
    assert {"avoid_weekday", "avoid_weekday_soft"} <= keys


def test_the_hard_tuesday_and_the_soft_weekday_penalty_are_distinct_keys():
    assert mf.registry_key_for_flag("avoid_weekday", "Tuesday") == "avoid_weekday"
    for wd in ("Saturday", "Sunday"):
        assert mf.registry_key_for_flag("avoid_weekday", wd) == "avoid_weekday_soft"
    assert mf.registry_key_for_flag("panchak", "Tuesday") == "panchak"
    hard = mf.resolve("avoid_weekday", "vivah")
    soft = mf.resolve("avoid_weekday_soft", "vivah")
    assert hard[0] == "sourced" and soft[0] == "contested" and hard[3] != soft[3]
    assert "Tuesday" in hard[3] and "Saturday" in soft[3]


# ─── (b) statuses, sources and wording ────────────────────────────────────────────────────────
def _all_resolutions():
    for key, entry in mf.REGISTRY.items():
        for event in EVENTS:
            yield key, event, None
            for val in entry.get("when", {}).get(event, {}):
                yield key, event, val


def test_every_entry_is_sourced_contested_or_a_sentenced_site_convention():
    seen = 0
    for key, event, val in _all_resolutions():
        status, file, heading, sentence = mf.resolve(key, event, val)
        seen += 1
        assert status in mf.STATUSES, (key, event, val, status)
        assert sentence.strip(), (key, event, val)
        assert "{" not in sentence, (key, event, val, sentence)
        if status in ("sourced", "contested"):
            assert file and heading, (key, event, val)
    assert seen > 125


def test_raw_entries_use_only_known_events_statuses_and_fields():
    for key, entry in mf.REGISTRY.items():
        rows = [entry["default"], *entry.get("events", {}).values()]
        for per_event in entry.get("when", {}).values():
            rows += list(per_event.values())
        for r in rows:
            assert set(r) == {"status", "file", "heading", "sentence"}, (key, r)
            assert r["status"] in mf.STATUSES, (key, r)
            assert bool(r["file"]) == bool(r["heading"]), (key, r)
        assert set(entry.get("events", {})) <= set(m.EVENT_RULES), key
        assert set(entry.get("when", {})) <= set(m.EVENT_RULES), key
        assert entry["label"].strip(), key


def test_unknown_key_or_event_raises_instead_of_rendering_unlabelled():
    with pytest.raises(KeyError):
        mf.resolve("no_such_factor", "vivah")
    with pytest.raises(KeyError):
        mf.resolve("good_tithi", "no_such_event")


def _user_facing_strings():
    for key, event, val in _all_resolutions():
        yield f"{key}/{event}/{val}", mf.resolve(key, event, val)[3]
    for key, entry in mf.REGISTRY.items():
        yield f"{key}/label", entry["label"]
    for name in ("CLEARED_HEADING", "SCORED_HEADING", "NO_POINTS", "NOON_NOTE", "ABUJHA_NOTE"):
        yield name, getattr(mf, name)


def test_no_sentence_cites_a_book_section_a_file_or_an_unheld_name():
    n = 0
    for where, s in _user_facing_strings():
        n += 1
        for bad in FORBIDDEN_IN_COPY:
            assert bad not in s, (where, bad, s)
    assert n > 125
    text = (SRC / "muhurat_factors.py").read_text(encoding="utf-8")
    for label, pattern in vrc._MUHURAT_UNHELD:
        assert not re.search(pattern, text, re.I), (label, "named in muhurat_factors.py")


def test_no_sentence_pairs_classical_with_an_unsourced_rule():
    for where, s in _user_facing_strings():
        for part in re.split(r"(?<=[.!?])\s+", s):
            assert not (CLAIM.search(part) and UNSOURCED.search(part)), (where, part)


def test_the_abujha_row_sentence_is_the_auditors_verbatim():
    assert mf.resolve("abujha_muhurat", "vivah")[3] == ABUJHA_SENTENCE
    assert mf.ABUJHA_NOTE == ABUJHA_SENTENCE
    assert "universally" not in ABUJHA_SENTENCE


def test_the_amrit_siddhi_sentence_never_claims_the_grade_rose():
    text = mf.resolve("amrit_siddhi", "vivah")[3]
    assert "Raising the grade" not in text and "raised" not in text.lower()
    assert "Whether and how this finder lifts a grade" in text
    assert mf.REGISTRY["amrit_siddhi"]["label"].endswith("present")


# ─── (c) every named heading exists in the named knowledge file ───────────────────────────────
def _named_headings() -> set[tuple[str, str]]:
    out = set(mf._EVENT_HEADING.values())
    for entry in mf.REGISTRY.values():
        rows = [entry["default"], *entry.get("events", {}).values()]
        for per_event in entry.get("when", {}).values():
            rows += list(per_event.values())
        out |= {(r["file"], r["heading"]) for r in rows if r["file"]}
    return out


def test_every_named_heading_exists_as_a_line_prefix_in_its_knowledge_file():
    named = _named_headings()
    assert len(named) >= 10, named
    lines: dict[str, list[str]] = {}
    for file, heading in sorted(named):
        text = lines.setdefault(
            file, (SRC / "knowledge" / file).read_text(encoding="utf-8").splitlines())
        assert any(ln.startswith(heading) for ln in text), f"{file}: no line starts {heading!r}"


def test_the_headings_the_auditor_named_are_all_in_use():
    want = {("vedic_reference.md", h) for h in (
        "### 29.6 ", "### 29.9 ", "### 29.14 ", "### 27.4 ", "#### Griha Pravesh",
        "#### Vidyarambh", "#### Namkaran", "#### Business start")}
    want |= {("grahas.md", "### 12.5 ")}
    assert want <= _named_headings(), want - _named_headings()


def test_a_numbered_heading_prefix_carries_its_trailing_space():
    """"### 29.9" would also match 29.90; the prefix must end the number."""
    for _file, heading in _named_headings():
        if re.match(r"#+ \d", heading):
            assert heading.endswith(" "), heading


# ─── (d) what explain emits over a real scan ──────────────────────────────────────────────────
def test_every_item_explain_emits_over_a_real_scan_resolves_and_has_a_status(scans):
    auspicious = 0
    for event, rows in scans.items():
        for c in rows:
            ex = mf.explain(c, event)
            if c.rating not in m.AUSPICIOUS_RATINGS:
                assert not ex, (event, c.d, c.rating)
                assert ex.scored == () and ex.cleared == ()
                continue
            auspicious += 1
            assert ex.scored or ex.cleared, (event, c.d)
            for item in ex.scored + ex.cleared:
                status = mf.resolve(item.key, event, item.qual or None)[0]
                assert item.status == status in mf.STATUSES, (event, c.d, item)
            assert (mf.CLEARED_HEADING in ex.cleared_heading) and "local noon" in ex.cleared_heading
    assert auspicious > 100


def test_explain_is_empty_for_avoid_and_caution_rows_and_unknown_events():
    for rating in ("avoid", "caution"):
        assert not mf.explain(_cand(rating=rating), "vivah")
    assert not mf.explain(_cand(), "no_such_event")


def test_a_site_convention_item_says_so_and_a_contested_one_says_traditions_differ():
    c = _cand(weekday="Saturday", nakshatra="Ashwini", tithi="Dwitiya")
    ex = mf.explain(c, "business")
    by_key = {i.key: i for i in ex.scored}
    assert by_key["good_tithi"].status == "site_convention"
    assert by_key["avoid_weekday_soft"].against
    vivah = {i.key: i for i in mf.explain(_cand(weekday="Saturday"), "vivah").scored}
    assert vivah["avoid_weekday_soft"].status == "contested"


def test_the_qualifiers_reach_the_item_they_belong_to():
    krishna = {i.key: i for i in mf.explain(
        _cand(tithi="Dwitiya", tithi_paksha="Krishna"), "vivah").scored}["good_tithi"]
    shukla = {i.key: i for i in mf.explain(_cand(), "vivah").scored}["good_tithi"]
    assert (krishna.qual, krishna.status) == ("@Krishna", "contested")
    assert (shukla.qual, shukla.status) == ("", "sourced")
    dwa = {i.key: i for i in mf.explain(
        _cand(tithi="Dwadashi", weekday="Monday"), "vidyarambh").scored}["good_tithi"]
    assert (dwa.qual, dwa.status) == ("Dwadashi", "contested")
    for star, qual in (("Rohini", "Rohini"), ("Pushya", "")):
        it = {i.key: i for i in mf.explain(_cand(nakshatra=star), "vidyarambh").scored
              }["good_nakshatra"]
        assert it.qual == qual and it.status == ("contested" if qual else "sourced"), star


def test_boosters_are_listed_as_present_and_never_as_a_raise():
    c = _cand(nakshatra="Hasta", weekday="Sunday",
              boosters=("Amrit Siddhi Yoga (x)", "Sarvartha Siddhi Yoga (y)",
                        "Ravi Yoga (z)"))
    ex = mf.explain(c, "business")
    texts = {i.key: i.text for i in ex.scored}
    assert texts["amrit_siddhi"] == "Amrit Siddhi present"
    assert texts["sarvartha_siddhi"] == "Sarvartha Siddhi present"
    assert texts["ravi_yoga"] == "Ravi Yoga present"
    assert not any("rais" in t.lower() or "lift" in t.lower() for t in texts.values())


# ─── the Abujha row ───────────────────────────────────────────────────────────────────────────
def test_an_abujha_row_scores_only_itself_clears_nothing_and_has_no_boosters():
    c = _cand(flags=("abujha_muhurat",), boosters=("Amrit Siddhi Yoga (x)", "Ravi Yoga (z)"),
              reason="Abujha Muhurat - x (universally auspicious)")
    for event in EVENTS:
        ex = mf.explain(c, event)
        assert [i.key for i in ex.scored] == ["abujha_muhurat"], event
        assert ex.cleared == (), event
        assert ex.note == ABUJHA_SENTENCE, event
        assert ex.scored[0].status == "site_convention"
        assert "universally" not in ex.note


def test_the_abujha_override_is_pinned_to_the_branch_that_skips_every_exclusion(monkeypatch):
    """vivah 2026-11-21 (Moon in Revati = Panchak, Dwadashi, Saturday) is rated excellent as an
    Abujha date because that branch of `find_candidates` runs no hard exclusion (#1346). The
    explanation therefore may not list any cleared check. When #1346 changes the branch this
    test goes red on purpose: revisit `explain`'s Abujha override, do not just edit the date."""
    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)
    [c] = m.find_candidates("vivah", "Delhi, India", date(2026, 11, 21), 1)
    assert "abujha_muhurat" in c.flags and c.rating == "excellent", (c.flags, c.rating)
    assert m._is_panchak(c.nakshatra, 4) or c.nakshatra == "Revati", c.nakshatra
    ex = mf.explain(c, "vivah")
    assert ex.cleared == () and [i.key for i in ex.scored] == ["abujha_muhurat"]
    # and the finder's code still does not run the checks, which is why:
    score = m.score_event("vivah", m._MuhurtaInstant(c.tithi, c.tithi_paksha), c.weekday,
                          c.nakshatra, True, False, "", "", {})
    assert score[0] == "avoid" and "panchak" in score[2]


# ─── (e) the cleared list is derived from the rules, and equals what the scorer applies ───────
def _drive(event: str, **over):
    a = dict(tithi="Dwitiya", paksha="Shukla", weekday="Wednesday", nakshatra="Hasta",
             is_panchak=False, is_chaturmas=False, kharmas_reason="", eclipse_reason="",
             combust={}, adhik_reason="", nitya_yoga="", nitya_blocks=False, moon_pada=0)
    a.update(over)
    return m.score_event(
        event, m._MuhurtaInstant(a["tithi"], a["paksha"]), a["weekday"], a["nakshatra"],
        a["is_panchak"], a["is_chaturmas"], a["kharmas_reason"], a["eclipse_reason"],
        a["combust"], adhik_reason=a["adhik_reason"], nitya_yoga=a["nitya_yoga"],
        nitya_blocks=a["nitya_blocks"], moon_pada=a["moon_pada"])


# One trigger per hard key. The dagdha pair is the table's own first row, not a restated one.
_DAG_DAY, _DAG_TITHI = next(iter(m._DAGDHA_TITHI_BY_DAY.items()))
TRIGGERS = {
    "adhik_maas": dict(adhik_reason="Adhik Maas"),
    "eclipse": dict(eclipse_reason="eclipse"),
    "nitya_yoga_block": dict(nitya_blocks=True, nitya_yoga="Ganda"),
    "panchak": dict(is_panchak=True),
    "chaturmas": dict(is_chaturmas=True),
    "kharmas": dict(kharmas_reason="Kharmas"),
    "dagdha": dict(weekday=_DAG_DAY, tithi=_DAG_TITHI),
    "jupiter_combust": dict(combust={"jupiter": True}),
    "venus_combust": dict(combust={"venus": True}),
    "mercury_combust": dict(combust={"mercury": True}),
    "avoid_nakshatra": dict(nakshatra="Bharani"),
    "avoid_nakshatra_pada": dict(nakshatra="Magha", moon_pada=1),
    "avoid_tithi": dict(tithi="Chaturthi"),
    "avoid_krishna_tithi": dict(tithi="Ekadashi", paksha="Krishna"),
    "avoid_weekday": dict(weekday="Tuesday"),
}


def _cleared_keys(event: str, **kw) -> list[str]:
    return [i.key for i in mf.explain(_cand(**kw), event).cleared]


def test_the_cleared_list_equals_the_auditors_table_for_every_event():
    assert {e: len(v) for e, v in AUDITOR_A.items()} == {
        "vivah": 14, "griha_pravesh": 11, "vidyarambh": 9, "business": 10, "namkaran": 7}
    for event in EVENTS:
        assert _cleared_keys(event) == [NUM[n] for n in AUDITOR_A[event]], event


def test_the_cleared_list_equals_what_score_event_actually_checks():
    assert set(TRIGGERS) == set(NUM.values()), "a hard key has no trigger"
    for event in EVENTS:
        # the baseline passes every check, or a "fires" below would prove nothing
        assert _drive(event)[0] != "avoid", event
        applied = set(_cleared_keys(event))
        for key, trig in TRIGGERS.items():
            rating, _reason, flags = _drive(event, **trig)
            assert (key in flags) == (key in applied), (event, key, flags, sorted(applied))


def test_the_cleared_list_is_derived_not_static():
    """Flip one check_* flag and the list follows; it is read from EVENT_RULES each call."""
    saved = m.EVENT_RULES["namkaran"]["check_dagdha"]
    try:
        m.EVENT_RULES["namkaran"]["check_dagdha"] = True
        assert "dagdha" in _cleared_keys("namkaran")
    finally:
        m.EVENT_RULES["namkaran"]["check_dagdha"] = saved
    assert "dagdha" not in _cleared_keys("namkaran")


def test_a_row_with_no_nakshatra_drops_every_nakshatra_based_check():
    for event in EVENTS:
        keys = _cleared_keys(event, nakshatra="")
        assert not {"panchak", "avoid_nakshatra", "avoid_nakshatra_pada"} & set(keys), event
        assert "avoid_tithi" in keys and "avoid_weekday" in keys
    # and the scorer agrees: an empty nakshatra reaches none of those checks
    for event in EVENTS:
        assert _drive(event, nakshatra="")[0] != "avoid"


def test_the_cleared_heading_is_qualified_at_local_noon_and_never_all_day():
    assert "local noon" in mf.CLEARED_HEADING
    assert "all day" not in mf.CLEARED_HEADING.lower()
    assert "local noon" in mf.NOON_NOTE


# ─── the legend ───────────────────────────────────────────────────────────────────────────────
def test_the_legend_lists_each_used_sentence_once_with_the_noon_note(scans):
    for event, rows in scans.items():
        lg = mf.legend(rows, event)
        keys = [(e.key, e.label) for e in lg.entries]
        assert len(keys) == len(set(keys)), event
        assert lg.noon == mf.NOON_NOTE
        assert all(e.status in mf.STATUSES and e.sentence for e in lg.entries)
        assert "soft_scoring_weights" in {e.key for e in lg.entries}
    assert not mf.legend([], "vivah")


def test_the_legend_labels_all_five_combustion_combinations_as_not_sourced(scans):
    expect = {"vivah": {"jupiter_combust", "venus_combust"}, "griha_pravesh": {"jupiter_combust"},
              "vidyarambh": {"jupiter_combust"}, "business": {"mercury_combust"},
              "namkaran": set()}
    for event, want in expect.items():
        entries = {e.key: e for e in mf.legend(scans[event], event).entries}
        assert want <= set(entries), (event, want - set(entries))
        for key in want:
            assert entries[key].status in ("site_convention", "contested"), (event, key)
            sentence = entries[key].sentence
            assert "own convention" in sentence or "own extension" in sentence, (event, key)
        assert not (set(entries) & {"jupiter_combust", "venus_combust", "mercury_combust"}) - want
