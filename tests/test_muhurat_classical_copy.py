"""#1024: muhurat pages must not call a rule "classical" that knowledge/ records as unsourced.

Chaturmas, Kharmas, Dagdha, the eclipse +/-1 day blocker, Choghadiya, the Amrit/Sarvartha/Ravi
boosters and the Abujha overrides are in no book this site holds (knowledge/vedic_reference.md
29.10), so the pages call them widely followed conventions the finder applies. Panchak, the five
blocking nitya yogas, Vishti and the combustion orbs are Raman's and may still be named as such.

The tests read the real template files and the real EVENT_LANDING; nothing is restated here.
"""

import re
from pathlib import Path

from astro_ai import muhurat as m

SRC = Path(m.__file__).parent
FINDER = (SRC / "templates" / "muhurat_finder.html").read_text(encoding="utf-8")
LANDING = (SRC / "templates" / "muhurat_landing.html").read_text(encoding="utf-8")
ABOUT = (SRC / "templates" / "about.html").read_text(encoding="utf-8")

UNSOURCED = re.compile(
    r"chaturmas|kharmas|malmas|dagdha|choghadiya|sarvartha|ravi yoga|abujha|eclipse", re.I)
CLAIM = re.compile(r"classical", re.I)  # also matches "classically"

# Phrases that were the defect, by name. The sentence check below is the general rule; these
# catch the ones whose unsourced rule sits in the NEXT sentence.
RETIRED = (
    "Classical criteria applied",
    "Classical criteria checked",
    "Grihya Sutra",
    "Classical tradition applies six",
    "Classical tradition names three",
    "seven classical criteria",
    "classically observed",
    "classically excluded",
)


def _landing_strings():
    for key, page in m.EVENT_LANDING.items():
        for field, val in page.items():
            if isinstance(val, str):
                yield f"{key}.{field}", val
            elif isinstance(val, list):
                for i, item in enumerate(val):
                    if isinstance(item, str):
                        yield f"{key}.{field}[{i}]", item


def _template_text(src: str) -> str:
    """Visible copy only: Jinja comments (which name the rules to explain them) and tags go."""
    src = re.sub(r"\{#.*?#\}", " ", src, flags=re.S)
    src = re.sub(r"<[^>]+>", " ", src)
    return re.sub(r"\s+", " ", src)


def _copy_units(src: str) -> list[str]:
    """Each paragraph, list item and meta/tool description on its own. A page-wide sentence
    split joins unpunctuated list items and nav into one "sentence", which flags nothing real."""
    src = re.sub(r"\{#.*?#\}", " ", src, flags=re.S)
    units = [m_.group(2) for m_ in re.finditer(r"<(p|li)\b[^>]*>(.*?)</\1>", src, re.S)]
    units += re.findall(r"\{% block meta_description %\}(.*?)\{% endblock %\}", src, re.S)
    units += re.findall(r'tool_desc = "(.*?)" %\}', src, re.S)
    units += re.findall(r'<meta[^>]+content="([^"]*)"', src)
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", u)) for u in units]


def _bad_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s for s in parts if CLAIM.search(s) and UNSOURCED.search(s)]


def _bad_in_template(src: str) -> list[str]:
    return [s for u in _copy_units(src) for s in _bad_sentences(u)]


def test_the_issue_repro_classical_criteria_applied_is_gone():
    assert FINDER.count("Classical criteria applied") == 0


def test_no_retired_phrase_survives_in_any_muhurat_surface():
    surfaces = {"muhurat_finder.html": FINDER, "muhurat_landing.html": LANDING,
                "about.html": ABOUT}
    surfaces.update(dict(_landing_strings()))
    hits = [(name, p) for name, text in surfaces.items() for p in RETIRED if p in text]
    assert not hits, hits


def test_no_finder_sentence_calls_an_unsourced_rule_classical():
    # includes the meta_description and tool_desc Jinja strings, which carry the issue's line 4/11
    assert not _bad_in_template(FINDER), _bad_in_template(FINDER)
    assert len(_copy_units(FINDER)) >= 15, "the unit extractor stopped finding the copy"


def test_no_landing_string_calls_an_unsourced_rule_classical():
    bad = [(k, s) for k, v in _landing_strings() for s in _bad_sentences(v)]
    assert not bad, bad


def test_the_finder_labels_its_own_conventions_and_names_the_sourced_ones():
    text = _template_text(FINDER)
    marker = "Widely followed conventions this finder applies"
    assert text.count(marker) == 1, "the conventions paragraph is gone or duplicated"
    sourced = text.split("Criteria applied:")[1].split(marker)[0]
    conventions = text.split(marker)[1].split("Combustion (asta)")[0]
    for name in ("Chaturmas", "Kharmas", "Dagdha", "eclipse", "Choghadiya",
                 "Sarvartha Siddhi", "Ravi Yoga", "Abujha"):
        assert name.lower() in conventions.lower(), name
        assert name.lower() not in sourced.lower(), name
    for name in ("Panchak", "Vyatipata", "Vaidhriti", "Raman"):
        assert name in sourced, name


def test_landing_rules_label_each_unsourced_rule_as_a_convention():
    for key, page in m.EVENT_LANDING.items():
        for line in page["rules_summary"]:
            if re.search(r"chaturmas|kharmas|dagdha|eclipse|basant panchami|devuthani",
                         line, re.I) and not line.startswith("Chaturmas, Kharmas"):
                assert "widely followed convention" in line, (key, line)


def test_the_real_routes_render_the_disclosure():
    from fastapi.testclient import TestClient

    from astro_ai.main import app

    client = TestClient(app)
    for path in ("/muhurat", "/muhurat/vivah", "/muhurat/griha-pravesh", "/muhurat/namkaran"):
        r = client.get(path)
        assert r.status_code == 200, path
        text = _template_text(r.text)
        assert "widely followed convention" in text.lower(), path
        assert not _bad_in_template(r.text), (path, _bad_in_template(r.text))
        assert "Grihya" not in text, path


def test_the_vivah_combustion_veto_is_labelled_a_convention_not_a_sourced_rule():
    """QA on #1024: knowledge/grahas.md 12.5 finds Raman's wedding criteria and Rao's Table 79
    list no combustion, so the Vivah Guru/Shukra veto is the finder's own convention."""
    text = _template_text(FINDER)
    sourced = text.split("Criteria applied:")[1].split("Widely followed conventions")[0]
    for sentence in re.split(r"(?<=[.!?])\s+", sourced):
        if "combust" in sentence.lower():
            assert "own convention" in sentence, sentence  # never listed beside Raman's items
    para = text.split("Combustion (asta):")[1].split("Namkaran checks none")[0]
    assert re.search(r"Vivah is this finder's own convention", para), para
    assert "Table 79" in para and "do not list combustion" in para, para
    intro = m.EVENT_LANDING["vivah"]["intro_paragraphs"][0]
    sourced_clause, _, conventions_clause = intro.partition("widely followed conventions")
    assert "combust" not in sourced_clause.lower(), sourced_clause
    assert "not combust" in conventions_clause, conventions_clause
    for line in m.EVENT_LANDING["vivah"]["rules_summary"]:
        if "uncombust" in line:
            assert "this finder's own convention" in line, line
