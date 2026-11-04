"""#399 — the natal remedy block is retrieved per chart, from remedies.md.

natal.txt used to carry a nine-planet remedy list on every call. It now carries
a short rule and the user message gets a `--- REMEDY RULES ---` block built by
`knowledge_lookup` for only the planets the chart flags DEBILITATED/COMBUST.
Four things can go wrong and each is pinned here:

  * the parse drifts (a table is reworded) and the block silently empties
  * a citation (a book, an author, a chapter) reaches the model, which
    natal.txt forbids it to repeat
  * the block costs more than the line it replaced, so the change is a
    token INCREASE on the very bucket that is already over
  * the lookup raises on the /kundli request path
"""
from __future__ import annotations

import itertools
import json
import logging
import re
from pathlib import Path

import pytest

from astro_ai import knowledge_lookup as kl
from astro_ai import llm, providers
from astro_ai.chart import (
    compute_chart,
    compute_dasha_state,
    compute_life_chapters,
    compute_vedic_flags,
    planet_dignities,
)

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / "src" / "astro_ai" / "prompts" / "natal.txt"
FIXTURES = Path(__file__).resolve().parent / "kundali-qa-fixtures.json"

NO_WEAK = "manglik-cancelled-by-jupiter"      # no DEBILITATED, no COMBUST
THREE_WEAK = "cancer-lagna-manglik-exempt"    # Mars (both tags), Jupiter, Mercury

# The banned shapes: books, authors, chapter marks, section marks and any
# parenthetical. "Narasimha" alone is a deity (Mars and Rahu rows) and must pass.
_NAMES = (r"\b(Rao|P\.V\.R\.|Raman|Parashara|BPHS|Phaladeepika|Jataka|Mansagari|Chintamani)\b"
          r"|Ch\.|Chapter|§")
CITATION = re.compile(_NAMES + r"|\(")      # for the block, which has no reason to hold a "("
# The assembled message holds "(" everywhere — the date, every house line, the
# combust separation — so a "(" ban over the whole message could never pass.
# The names and marks are what a model could repeat; they are banned everywhere.
CITATION_NAMES = re.compile(_NAMES)

# natal.txt's nine-planet remedy line, as measured with tiktoken o200k_base
# before it was replaced (scripts/verify_token_budget.py on main, 2026-11-04).
OLD_REMEDY_LINE_TOKENS = 189


@pytest.fixture(autouse=True)
def _fresh_parse():
    """The parse is memoised for the process; no test may inherit another's."""
    kl._tables.cache_clear()
    yield
    kl._tables.cache_clear()


def _fx(key: str):
    fx = json.loads(FIXTURES.read_text())[key]
    chart = compute_chart(fx["birth_date"], fx["birth_time"], fx["birth_place"])
    details = llm.BirthDetails(fx.get("name", ""), fx["birth_date"],
                               fx["birth_time"], fx["birth_place"])
    return details, chart


def _user_message(key: str) -> str:
    details, chart = _fx(key)
    return llm._format_seeker_message(
        details, chart, compute_vedic_flags(chart), compute_life_chapters(chart),
        compute_dasha_state(chart), token_budget=None,
    )


def _debilitated(*names: str):
    return [(n, ["DEBILITATED"]) for n in names]


# --------------------------------------------------------------------------
# the parse, against the REAL file
# --------------------------------------------------------------------------


def test_every_planet_resolves_a_deity_and_eight_a_grain_from_the_real_file():
    """Parse-drift tripwire: remedies.md is prose, and a reworded heading or
    table would otherwise turn this feature into a silent no-op."""
    planets = [*kl._PLANET_ORDER, "Rahu", "Ketu"]
    assert all(kl.deities_for(p) for p in planets), (
        [p for p in planets if not kl.deities_for(p)])
    with_grain = [p for p in planets if kl.grain_for(p)]
    assert len(with_grain) == 8 and "Ketu" not in with_grain, with_grain


def test_ketu_has_no_grain_and_is_not_a_keyerror():
    assert kl.grain_for("Ketu") is None
    block = kl.remedy_rules_for(_debilitated("Ketu"))
    # Ketu is never flagged by planet_dignities, but the lookup must tolerate it.
    assert "Ketu" not in kl._PLANET_ORDER and block == ""
    assert kl._render("Ketu") == "- Ketu: traditionally linked deities include Ganesha"


def test_venus_grain_is_only_a_whitish_grain():
    assert kl.grain_for("Venus") == "a whitish grain"
    assert "name" not in kl.remedy_rules_for(_debilitated("Venus")).lower().split("whitish")[-1]


def test_the_parenthetical_is_stripped_from_the_toor_daal_cell():
    """Mars's grain cell is `Toor daal (dark yellow lentil)`; the Mars deity
    cell holds `Kartikeya (Subrahmanya)`. Neither parenthetical may survive."""
    assert kl.grain_for("Mars") == "toor daal"
    assert "Kartikeya" in kl.deities_for("Mars")
    assert not any("(" in d for p in kl._PLANET_ORDER for d in kl.deities_for(p))


def test_deities_are_capped_at_three_in_table_order():
    assert kl.deities_for("Jupiter") == ["Hayagreeva", "Vishnu", "Parameswara"]
    assert kl.deities_for("Moon") == ["Gauri", "Lalita", "Saraswati"]


def test_no_weekday_reaches_the_block():
    """Rao's only weekday example is Jupiter's, and the auditor ruled no
    planet gets one — the old prompt's weekday fasting was unsourced."""
    block = kl.remedy_rules_for(_debilitated(*kl._PLANET_ORDER[:3]))
    days = r"Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday"
    for p in kl._PLANET_ORDER:
        assert not re.search(days, kl.remedy_rules_for(_debilitated(p)), re.I)
    assert not re.search(days, block, re.I)


# --------------------------------------------------------------------------
# no citation reaches the model
# --------------------------------------------------------------------------


@pytest.mark.parametrize("planet", kl._PLANET_ORDER)
def test_no_citation_in_any_planets_block(planet):
    block = kl.remedy_rules_for(_debilitated(planet))
    assert block.startswith("--- REMEDY RULES ---\n- " + planet)
    assert not CITATION.search(block), CITATION.search(block).group(0)


def test_no_citation_in_the_worst_trio_or_the_assembled_message():
    block = kl.remedy_rules_for(_debilitated("Mars", "Jupiter", "Mercury"))
    assert block.count("\n- ") == 3 and not CITATION.search(block)
    message = _user_message(THREE_WEAK)
    assert "--- REMEDY RULES ---" in message
    # The whole user message, not just the block: this is the surface the
    # model reads, and the prompt bans naming texts in prose.
    found = CITATION_NAMES.search(message)
    assert not found, message[max(0, found.start() - 60): found.end() + 60]


def test_a_citation_in_a_table_cell_drops_that_planet_not_the_whole_block(monkeypatch, caplog):
    """The parenthetical strip is the first defence; this is the second. A
    cell that itself names a book must never be rendered."""
    real = kl._read_remedies
    monkeypatch.setattr(kl, "_read_remedies", lambda: real().replace(
        "| Sun | Shiva, Rama |", "| Sun | Shiva, Rao's pick |"))
    with caplog.at_level(logging.ERROR, logger=kl.__name__):
        block = kl.remedy_rules_for(_debilitated("Sun", "Moon"))
    assert "Sun" not in block and "- Moon:" in block
    assert any("citation" in r.getMessage() for r in caplog.records)


# --------------------------------------------------------------------------
# selection: tier, order, cap, once
# --------------------------------------------------------------------------


def test_cap_of_three_keeps_debilitated_before_combust_before_graha_order():
    dignities = [
        ("Sun", ["COMBUST (1.0° from Sun)"]),  # not meaningful for Sun; tier 1
        ("Moon", ["COMBUST (9.0° from Sun)"]),
        ("Mars", ["DEBILITATED"]),
        ("Mercury", ["COMBUST (2.0° from Sun)"]),
        ("Saturn", ["DEBILITATED"]),
    ]
    # Two debilitated first (Mars, Saturn), then the first combust in graha order.
    assert kl.select_planets(dignities) == ["Mars", "Saturn", "Sun"]
    block = kl.remedy_rules_for(dignities)
    assert block.count("\n- ") == 3 and "Moon" not in block and "Mercury" not in block


def test_a_planet_with_both_tags_counts_once_in_the_debilitated_tier():
    both = [("Mars", ["DEBILITATED", "COMBUST (7.7° from Sun)"]),
            ("Moon", ["COMBUST (9.0° from Sun)"]),
            ("Mercury", ["COMBUST (2.0° from Sun)"]),
            ("Jupiter", ["COMBUST (3.0° from Sun)"])]
    picked = kl.select_planets(both)
    assert picked == ["Mars", "Moon", "Mercury"]
    assert picked.count("Mars") == 1


def test_tags_are_tested_by_token_not_equality():
    """The combust tag carries its separation, so `== "COMBUST"` never matches
    — and a neutral/own-sign/exalted planet must not select."""
    assert kl.select_planets([("Moon", ["COMBUST (9.0° from Sun)"])]) == ["Moon"]
    assert kl.select_planets([("Sun", ["OWN SIGN"]), ("Moon", ["EXALTED"]),
                              ("Mars", [])]) == []


def test_the_real_charts_pick_what_the_dignity_block_flags():
    _, chart = _fx(THREE_WEAK)
    dignities = [(p.name, t) for p, t in planet_dignities(chart)]
    assert kl.select_planets(dignities) == ["Mars", "Jupiter", "Mercury"]
    _, calm = _fx(NO_WEAK)
    assert kl.select_planets([(p.name, t) for p, t in planet_dignities(calm)]) == []


# --------------------------------------------------------------------------
# the file: read once, and its absence is not an exception
# --------------------------------------------------------------------------


def test_the_parse_reads_the_file_once(monkeypatch):
    reads = []
    real = kl._read_remedies
    monkeypatch.setattr(kl, "_read_remedies", lambda: reads.append(1) or real())
    for _ in range(5):
        assert kl.remedy_rules_for(_debilitated("Sun"))
    assert len(reads) == 1


@pytest.mark.parametrize("content", [None, "", "# remedies\n\nno tables here\n"],
                         ids=["missing", "empty", "unparseable"])
def test_a_missing_empty_or_unparseable_file_returns_empty_and_logs_error(
        monkeypatch, tmp_path, caplog, content):
    path = tmp_path / "remedies.md"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(kl, "_REMEDIES_PATH", path)
    with caplog.at_level(logging.ERROR, logger=kl.__name__):
        assert kl.remedy_rules_for(_debilitated("Sun", "Mars")) == ""
    assert [r for r in caplog.records if r.levelno == logging.ERROR], "silent failure"


def test_a_failed_parse_is_retried_not_cached(monkeypatch, tmp_path):
    """lru_cache does not cache an exception; a file that appears later works."""
    path = tmp_path / "remedies.md"
    monkeypatch.setattr(kl, "_REMEDIES_PATH", path)
    assert kl.remedy_rules_for(_debilitated("Sun")) == ""
    monkeypatch.setattr(kl, "_REMEDIES_PATH", kl.Path(kl.__file__).parent / "knowledge" / "remedies.md")
    assert kl.remedy_rules_for(_debilitated("Sun"))


def test_sections_are_found_by_number_not_by_title():
    text = ("### 5.10 Other\n| Planet | Grain |\n|---|---|\n| Sun | Gold |\n"
            "### 5.1 Anything at all\n| Planet | Grain |\n|---|---|\n| Sun | Wheat |\n")
    assert kl._section_rows(text, "5.1") == {"Sun": "Wheat"}


def test_runtime_code_now_reads_knowledge():
    """CLAUDE.md said no runtime code reads knowledge/ (measured 2026-10-15).
    Now one does; this is the same grep, flipped, and it must find the read."""
    hits = []
    for py in (ROOT / "src" / "astro_ai").glob("*.py"):
        for line in py.read_text(encoding="utf-8").splitlines():
            code = line.split("#", 1)[0]
            if '"knowledge"' in code and "knowledge" in code:
                hits.append(f"{py.name}: {line.strip()}")
    assert hits, "no runtime code references knowledge/ any more"
    assert kl._REMEDIES_PATH.is_file()


# --------------------------------------------------------------------------
# the natal path
# --------------------------------------------------------------------------


def test_a_chart_with_no_weak_planet_gets_no_block_and_still_generates(monkeypatch, caplog):
    sent: dict = {}

    def fake_chat(messages, route):
        sent["messages"], sent["route"] = messages, route
        return "## Personality & Character\nx"

    monkeypatch.setattr(llm.providers, "chat", fake_chat)
    details, chart = _fx(NO_WEAK)
    with caplog.at_level(logging.INFO, logger=llm.__name__):
        out = llm.generate_reading(
            details, chart=chart, flags=compute_vedic_flags(chart),
            life_chapters=compute_life_chapters(chart), prompt_path=PROMPT,
            dasha_state=compute_dasha_state(chart),
        )
    assert out.startswith("## Personality")
    system, user = (m["content"] for m in sent["messages"])
    assert "REMEDY RULES" not in user
    # The two things that must NOT depend on retrieval.
    assert "No block, no remedy line" in system or "no block, no remedy line" in system
    assert "consult a knowledgeable astrologer first" in system
    assert "planets=[] (none weak)" in caplog.text


def test_a_chart_with_weak_planets_gets_the_block_and_one_log_line(caplog):
    with caplog.at_level(logging.INFO, logger=llm.__name__):
        message = _user_message(THREE_WEAK)
    assert message.count("--- REMEDY RULES ---") == 1
    lines = [r.getMessage() for r in caplog.records
             if r.getMessage().startswith("knowledge retrieval")]
    assert len(lines) == 1, lines
    assert re.fullmatch(
        r"knowledge retrieval route=natal sections=remedies\.md§5\.1,§7\.1 "
        r"planets=\['Mars', 'Jupiter', 'Mercury'\] tok~\d+", lines[0]), lines[0]
    # After the dignity block it keys on, never before the chart it describes.
    assert message.index("PLANET DIGNITY") < message.index("--- REMEDY RULES ---")


def test_the_block_is_never_shed():
    """Rank 0, like the dignity block it is keyed on: a reading that carries
    a flagged planet and no remedy rules would invent the remedy it was told
    to take from the block."""
    details, chart = _fx(THREE_WEAK)
    flags = compute_vedic_flags(chart)
    tiny = llm._format_seeker_message(
        details, chart, flags, compute_life_chapters(chart),
        compute_dasha_state(chart), token_budget=1)
    assert "--- REMEDY RULES ---" in tiny


def test_natal_txt_no_longer_carries_the_nine_planet_list():
    text = PROMPT.read_text(encoding="utf-8")
    for gone in ("Hanuman Chalisa", "Beej mantra", "wheat charity",
                 "Monday fasting", "Thursday fasting", "Friday fasting",
                 "Tuesday charity", "Saturday service"):
        assert gone not in text, gone
    assert "No block, no remedy line" in text or "no block, no remedy line" in text
    assert "consult a knowledgeable astrologer first" in text
    assert re.search(r"large sum for a puja", text)


# --------------------------------------------------------------------------
# the cost
# --------------------------------------------------------------------------


@pytest.mark.network_allowed(
    "openaipublic.blob.core.windows.net",
    reason="tiktoken downloads the o200k_base vocabulary on first use; "
           "a dependency fetch, not LLM spend (#449)")
def test_the_heaviest_block_costs_less_than_the_line_it_replaced():
    """The whole case for this change on a bucket that is already over is that
    it SHRINKS the request. Worst case: three flagged planets with the
    heaviest rows, priced with the separator the message joins with."""
    tiktoken = pytest.importorskip("tiktoken")
    enc = tiktoken.get_encoding("o200k_base")
    new_line = next(l for l in PROMPT.read_text(encoding="utf-8").splitlines()
                    if l.startswith("- REMEDIES"))
    worst = max(
        len(enc.encode("\n\n" + kl.remedy_rules_for(_debilitated(*trio))))
        for trio in itertools.combinations(kl._PLANET_ORDER, 3)
    )
    net = len(enc.encode(new_line)) + worst - OLD_REMEDY_LINE_TOKENS
    assert net < 0, (
        f"worst-case net is {net:+d} tok: rule line {len(enc.encode(new_line))} + "
        f"heaviest block {worst} vs the {OLD_REMEDY_LINE_TOKENS} it replaced")
