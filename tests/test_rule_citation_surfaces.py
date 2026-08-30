"""What the chart page actually prints under "Source:".

#216 / #218. Twelve yoga rules carried `source="Brihat Parashara Hora Shastra"`
and `result.html` rendered it verbatim, so the site told every reader a
provenance nobody here could check — BPHS is not in `data/`, is not one of the
eight books `scripts/fetch_corpus.py` registers, and never was. Forty lines
from one of those rules, `chart.py` documented that same rule's orb as
UNSOURCED.

`scripts/verify_rule_citations.py` checks the strings in the source file. This
checks the **page**, which is the thing the reader sees, and it is a separate
question: a label can be correct in `chart.py` and still not reach the panel,
or reach it through a branch the gate reads but nothing exercises. The two
tests that matter most here are the conditional ones — the Budha-Aditya orb
disclosure and the Manglik combust label only appear on charts that trigger
them, so a gate reading the source is the only other thing that sees them.

Chart 1957-09-07 01:05 fires both at once; that is why it is the fixture.
"""
from __future__ import annotations

import random
import re
from datetime import date, time as dtime

import pytest

# Both defects are on this one chart: Mercury is combust within 6° of the Sun
# (so Budha-Aditya renders its weakened form) AND Mars is combust within 6°
# (so the Manglik panel renders the cancellation whose label was never a
# citation). Found by sweep, not by hand — see the module docstring.
_BIRTH = {
    "name": "Citation Fixture",
    "birth_date": "1957-09-07",
    "birth_time": "01:05",
    "birth_place": "Mumbai",
}


@pytest.fixture
def result_page(client, stub_llm) -> str:
    """The rendered /kundli HTML for `_BIRTH`.

    POST /reading is a redirect-only save; the page renders at GET /kundli.
    The LLM is stubbed with a sectioned body so the route reaches the template
    instead of the 503 error page — the panels under test are computed from
    the chart, not from the reading.
    """
    stub_llm("## Overview\nA stubbed reading.\n\n## Relationships\nStubbed.\n")
    r = client.post("/reading", data=_BIRTH, follow_redirects=False)
    assert r.status_code == 303, r.status_code
    page = client.get("/kundli")
    assert page.status_code == 200, page.status_code
    return page.text


def _rendered(html: str) -> str:
    """The page with Jinja comments already gone — TemplateResponse drops them,
    so this is only a guard against reading a raw template by mistake."""
    return re.sub(r"\{#.*?#\}", "", html, flags=re.S)


def test_no_yoga_cites_a_book_the_repo_does_not_hold(result_page):
    """The #216 defect itself: the page named BPHS to the reader."""
    page = _rendered(result_page)
    assert "Source:" in page, "yoga panel did not render — the assertions below would be vacuous"
    for spelling in ("Brihat Parashara Hora Shastra", "BPHS"):
        assert spelling not in page, (
            f"the chart page prints {spelling!r} as a source. That book is not in "
            f"data/ and is not registered in scripts/fetch_corpus.py, so no reader "
            f"and no agent can check the claim (#216)."
        )


def test_yoga_sources_cite_the_book_we_actually_hold(result_page):
    """Removing the false citation must not mean removing the citation.

    Silence would hide the problem rather than fix it, and would cost the
    reader the ability to judge — so the panel must still carry a reference,
    and it must be to the text the rule was read in.
    """
    page = _rendered(result_page)
    assert "Rao, Vedic Astrology: An Integrated Approach" in page
    assert re.search(r"Source: Rao, Vedic Astrology: An Integrated Approach §11\.", page), \
        "yoga cards no longer carry a section-level citation"


def test_budha_aditya_discloses_that_its_6_degree_cutoff_is_unsourced(result_page):
    """The orb is ours, and the page has to say so where it is used.

    Rao gives the yoga and the principle that combustion weakens it, but writes
    only "too close" — no degree. knowledge/grahas.md §12.3 records the audit.
    This chart's Mercury IS within 6°, so the weakened wording renders and the
    disclosure must ride with it.
    """
    page = _rendered(result_page)
    assert "Mercury is combust within 6° of Sun" in page, \
        "fixture no longer triggers the combust branch — re-pick the chart"
    assert "the 6° cut-off is ours, not his" in page
    assert "contested" in page


def test_manglik_combust_rule_is_labelled_unsourced(result_page):
    """"Classical matching practice" was not a citation — it was a phrase
    shaped like one, sitting in a list beside real book names.

    The rule still fires (removing it would silently change whose dosha is
    cancelled); what changed is that the page now says it is unsourced.
    """
    page = _rendered(result_page)
    assert "Mars combust (within" in page, \
        "fixture no longer triggers the Manglik combust rule — re-pick the chart"
    assert "unsourced: absent from the classical Kuja-dosha antidote lists we hold" in page


def test_the_yoga_panel_footer_does_not_reassert_the_false_provenance(result_page):
    """The footer said "Compiled from … Brihat Parashara Hora Shastra and
    Phaladeepika" — one sentence asserting for the whole panel what each card
    asserted individually. Fixing the cards and leaving it would have left the
    claim on the page."""
    page = _rendered(result_page)
    assert "Compiled from classical Vedic astrology texts" not in page
    assert "not a claim about where the rule first appears" in page


# ─── every rule, not just the ones this chart happens to fire ────────────
#
# The page tests above are worth exactly the yogas the fixture triggers, and
# that is roughly two thirds of them: mutating a yoga this chart does not have
# leaves them green. Measured, not assumed — reverting `sunaphaa_yoga` and
# `ubhayachara_yoga` to their #216 labels was invisible to every test above.
#
# So this sweep computes the rules directly over many charts and asserts on
# every label that actually gets produced. It is not a request-path test and
# does not pretend to be; it is the coverage the request-path test cannot have
# without rendering hundreds of pages.

_SWEEP_CHARTS = 400
_SWEEP_SEED = 20260827

# Slugs the sweep must reach, or its silence proves nothing. Deliberately not
# "all of them": Kemadruma and Vosi are genuinely rare, and a threshold that
# only passes on a lucky seed is a flaky test, not a strict one.
_MIN_DISTINCT_SLUGS = 14

# The full yoga catalogue compute_yogas() can emit. Written out rather than
# derived, so a yoga that silently stops being produced shows up as a coverage
# drop instead of shrinking the thing being checked along with the check.
_YOGA_SLUGS: frozenset[str] = frozenset({
    "ruchaka_yoga", "bhadra_yoga", "hamsa_yoga", "malavya_yoga", "sasha_yoga",
    "vesi_yoga", "vosi_yoga", "ubhayachara_yoga", "budha_aditya_yoga",
    "sunaphaa_yoga", "anaphaa_yoga", "duradhara_yoga", "kemadruma_yoga",
    "chandra_mangala_yoga", "gaja_kesari_yoga",
    "harsha_yoga", "sarala_yoga", "vimala_yoga",
    "guru_mangala_yoga", "trilochana_yoga", "amala_yoga", "vasumati_yoga",
    "adhi_yoga",
})


def _sweep():
    """(slug, source) for every yoga and Manglik rule over a fixed chart sweep.

    Stubs `geocode_place` ITSELF rather than relying on conftest's autouse
    `_offline_geocode`. That fixture is function-scoped (it uses `monkeypatch`),
    and this one is module-scoped, so pytest builds this sweep BEFORE the patch
    is installed — 400 charts each calling out to nominatim. With no network
    that is `OSError: Network is unreachable` on 6 tests.

    Which broke more than these tests. `scripts/mutate_behaviour_suite.py`
    copies src/ and tests/ into a sandbox and asks whether the suite goes red;
    a suite that is ALREADY red reports every mutation as CAUGHT, including the
    no-op CONTROL. The harness detected it and refused to be believed —
    `CONTROL FAILED — the sandbox reports CAUGHT for an edit that changes
    nothing` — so the repo's whole anti-vacuous-test mechanism was disabled by
    a scope mismatch in one fixture. #224 made the suite hermetic; this file
    reintroduced the hole through the one door #224's fixture cannot cover.
    """
    from unittest.mock import patch

    from astro_ai import chart as C

    rnd = random.Random(_SWEEP_SEED)
    seen: set[tuple[str, str]] = set()
    # Three-tuple, matching `geocode_place`'s real signature and conftest's
    # stub. A four-tuple here raises `ValueError: too many values to unpack`
    # at chart.py:415 — same six tests red, different reason, and the harness
    # would still have read BLIND.
    with patch.object(C, "geocode_place",
                      lambda place: (19.0760, 72.8777, "Asia/Kolkata")):
        for _ in range(_SWEEP_CHARTS):
            d = date(1950 + rnd.randrange(76), rnd.randrange(1, 13), rnd.randrange(1, 29))
            t = dtime(rnd.randrange(24), rnd.randrange(60))
            ch = C.compute_chart(d, t, "Mumbai")
            for y in C.compute_yogas(ch):
                seen.add((y.slug, y.source))
            for r in C.compute_manglik_details(ch).cancellations:
                seen.add((r.slug, r.source))
    return seen


@pytest.fixture(scope="module")
def swept():
    return _sweep()


def test_the_sweep_is_not_vacuous(swept):
    slugs = {slug for slug, _ in swept}
    assert len(slugs) >= _MIN_DISTINCT_SLUGS, (
        f"only {len(slugs)} distinct rules fired across {_SWEEP_CHARTS} charts; "
        f"the assertions below would be checking almost nothing"
    )


def test_no_rule_anywhere_cites_a_book_the_repo_does_not_hold(swept):
    """The exhaustive form of the first page test.

    BPHS is the one this is named for. The other unheld compendia in
    `_manglik_cancellations()` are the same defect class and are NOT asserted
    against here — they are disclosed in `scripts/verify_rule_citations.py`'s
    `_UNHELD_ATTRIBUTIONS` ledger and remain open on #216. Asserting them here
    would mean fixing them in this commit, which is not what was scoped; a
    test that pretends otherwise is worse than the ledger.
    """
    offenders = [(slug, src) for slug, src in swept
                 if "parashara" in src.lower() or "BPHS" in src]
    assert not offenders, (
        f"these rules still cite Brihat Parashara Hora Shastra, which is not in "
        f"data/ and is not registered in scripts/fetch_corpus.py: {sorted(offenders)}"
    )


def test_every_rule_says_something_about_where_it_came_from(swept):
    """Silence is not the fix. A blank or whitespace source removes the reader's
    ability to judge the claim, which is the outcome #172 warns against from the
    other direction — there, the nearest plausible reference was attached."""
    blank = sorted(slug for slug, src in swept if not src.strip())
    assert not blank, f"rules with an empty source string: {blank}"


def test_every_yoga_label_is_either_a_citation_or_an_admission(swept):
    """A yoga label must name the book we read the rule in, or admit a gap.

    "Classical Vedic tradition" did neither. It was not a citation and not an
    admission — the same shape of phrase as the "Classical matching practice"
    #218 removed from `mars_combust`. Five yogas carried it, outside #218's
    scope (the twelve BPHS labels).

    ALL FIVE ARE NOW CITED TO RAO, so the expected set is empty. QA of 5843ad5
    reported that the ledger understated the position — it said only
    Guru-Mangala and Amala were in Rao "and the others are unchecked". All five
    are there, and each definition was checked against the book, not assumed:

        Guru-Mangala  §11.6    line 4661  "Jupiter and Mars together or in the
                                           7th from each other" == delta 0 or 6
        Amala         §11.6    line 4665  "only natural benefics in the 10th
                                           from lagna or Moon"
        Trilochana    §11.6    line 4843  "Sun, Moon and Mars in mutual trines"
        Vasumati      §11.6    line 4923  "benefics occupy upachayas"
        Adhi          §11.3.6  line 4318  "natural benefics in 6th, 7th and 8th
                                           from Moon"

    This assertion is now a REGRESSION GUARD, and the direction matters: an
    empty set is the goal, and any reappearance means a new rule shipped a
    phrase that names no book and admits no gap.
    """
    vague = sorted({slug for slug, src in swept
                    if src == "Classical Vedic tradition"})
    assert vague == [], (
        f"a yoga is carrying the un-audited 'Classical Vedic tradition' label "
        f"again: {vague}. It names no book and admits no gap. Cite the text the "
        f"rule was read in, or say plainly that it is unsourced."
    )


def test_audited_yogas_all_cite_rao_by_section(swept):
    """The twelve #216 labels, checked over every chart that produces them.

    `_YOGA_SLUGS` is the full catalogue; anything in it that is not in the
    un-audited set above must carry a section-level citation to the book in
    `data/`. This is the assertion the single-chart page test cannot make:
    mutating a yoga the fixture does not have was measured to leave every
    page test green.
    """
    unaudited = {"guru_mangala_yoga", "trilochana_yoga", "amala_yoga",
                 "vasumati_yoga", "adhi_yoga"}
    checked = 0
    for slug, src in sorted(swept):
        if slug not in _YOGA_SLUGS or slug in unaudited:
            continue
        assert src.startswith("Rao, Vedic Astrology: An Integrated Approach §"), (
            f"{slug} cites {src!r}, which is neither the book we hold nor a "
            f"stated gap"
        )
        checked += 1
    assert checked >= 10, f"only {checked} audited yoga labels seen; too few to mean much"


def test_gaja_kesari_does_not_overstate_what_rao_supports(swept):
    """We test one of Rao's three conditions, so the label says "simplified".

    §11.6 requires (1) Jupiter in a quadrant from Moon, (2) a benefic conjoining
    or aspecting Jupiter, and (3) Jupiter not debilitated, combust or in an
    enemy's house. `_moon_yogas()` tests (1) and uses (3)'s debilitation as a
    note. Citing him flat for a looser rule is the same defect as citing a book
    we do not hold — a citation the reader cannot check against what it names.
    """
    labels = {src for slug, src in swept if slug == "gaja_kesari_yoga"}
    assert labels, "Gaja-Kesari did not fire in the sweep"
    for src in labels:
        assert "simplified" in src and "benefic-aspect condition is not applied" in src, (
            f"Gaja-Kesari cites {src!r} without disclosing that only one of Rao's "
            f"three conditions is tested"
        )
