"""One Nadi position everywhere, not an absolute here and an exemption there (#397).

`/matching` rendered two sentences on one panel that could not both be true:
the note said Nadi "has no cancelling conditions in this tradition", and the
disclosure thirteen lines below said it is "waived in parts of the south, and
for some communities". The `/ask` overlays then enforced the absolute, so the
model was forbidden to acknowledge an exemption the page had just shown.

`knowledge/matching.md` v.34 is what decides it: Nadi is a precondition and not
among the Bhakoot parihāras (परन्तु नाडी सभीमें होनी चाहिये), the tika records a
regional/varna exemption (गोदावरीके दक्षिण अथवा क्षत्रिय आदिकोंको नहीं), a slight
grade where pada-Nadi differs (दोष अल्प है) and shanti. This product applies none
of the exemptions and awards no koota points for any mitigation. Every surface
must say that and nothing stronger.

Hermetic: charts are really computed (geocoding is stubbed by conftest), no LLM.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from astro_ai import chart as C
from astro_ai import llm, matching as M
from astro_ai.i18n import _EN, _HI

SRC = Path(__file__).resolve().parent.parent / "src" / "astro_ai"
PROMPTS = SRC / "prompts"

# `(?:</?em>)?` because the learn article once wrote "<em>no</em> cancelling".
_ABSOLUTE = re.compile(
    r"no\s*(?:</?em>)?\s*cancell?ing\s+conditions|no\s+parih[aā]ras?\b",
    re.IGNORECASE,
)

# THE ASCII PATTERN ABOVE IS A TAUTOLOGY AGAINST DEVANAGARI. QA round 1
# demonstrated it: a Hindi string asserting the OPPOSITE of this change's
# thesis -- "नाड़ी के परिहार लागू होते हैं", Nadi's parihāras DO apply -- passed
# `assert not _ABSOLUTE.search(text)` and the suite stayed green, because there
# is not an ASCII letter in it to match. A negative check in the wrong alphabet
# is not a weak check, it is no check.
_ABSOLUTE_HI = re.compile(
    r"कोई\s+परिहार\s+नहीं"          # "there is no parihāra at all" -- the old absolute
    r"|परिहार\s+लागू\s+होते"        # "the parihāras DO apply" -- the opposite error
)

# What the Nadi RULE is about, used to find a contradicting instruction
# anywhere in an overlay rather than only on the one line that happens to start
# "- Nadi ". The original #397 defect WAS such an instruction.
_RULE_TOPIC = re.compile(r"parih[aā]ra|exempt|cancell?ing|waive", re.IGNORECASE)

# WIDER THAN `_ABSOLUTE`, and scanned over `.md` too. `_ABSOLUTE` matches two
# exact phrasings, so QA round 2 reintroduced #397's defect on /learn in a third
# ("Nadi can never be cancelled or waived by anything") with the suite green.
# This matches the CLAIM -- that nothing can lift a Nadi dosha -- rather than two
# ways of writing it, and it covers `knowledge/*.md`, the file that decides the
# question and which the original scan skipped.
_ABSOLUTE_ANY = re.compile(
    r"no\s*(?:</?em>)?\s*cancell?ing\s+conditions"
    r"|no\s+parih[aā]ras?\b"
    r"|(?:nadi|नाड़ी)[^.]{0,60}?\b(?:can\s+never|cannot|can't)\b[^.]{0,60}?"
    r"\b(?:cancel|cancell?ed|waive[d]?|lifted|removed|mitigated)\b"
    r"|\bnothing\b[^.]{0,40}\b(?:cancel|waive)[sd]?\b[^.]{0,40}\bnadi\b",
    re.IGNORECASE,
)
_RULE_MARK = "not among the Bhakoot parih"


def _pair(d1, t1, d2, t2):
    guna = M.compute_guna_milan(C.compute_chart(d1, t1, "Mumbai"),
                                C.compute_chart(d2, t2, "Mumbai"))
    assert guna.nadi_dosha.present, f"fixture {d1} {t1} x {d2} {t2} no longer shares a Nadi"
    return guna


def _nadi_pair():
    """1990-01-01 and 1990-01-04 at 10:00 share the Madhya Nadi (checked).

    grave=True, alpa=False.
    """
    g = _pair("1990-01-01", "10:00", "1990-01-04", "10:00")
    assert g.nadi_dosha.grave and not g.nadi_dosha.alpa
    return g


def _nadi_pair_alpa():
    """Same day, 04:00 and 10:00: Madhya, and the padas differ -- grave AND alpa.

    THE ALPA BRANCH HAD NO FIXTURE AT ALL. QA round 1 put two mutants inside
    it and both survived the full suite: the mitigation text rewritten to say
    the tradition REMOVES the dosha entirely -- contradicting both the source
    and this change's thesis -- and the alpa grading inverted. The fixture, not
    the assertion, was what could not fail.
    """
    g = _pair("1990-01-01", "04:00", "1990-01-01", "10:00")
    assert g.nadi_dosha.grave and g.nadi_dosha.alpa
    return g


def _nadi_pair_nongrave():
    """1990-01-02 x 1990-01-03 at 10:00 share the ADI Nadi -- present, not grave.

    The branch the exemption actually applies to. Without it, every assertion
    about the scoped wording would be made on Madhya pairs alone, which is the
    half the source EXCLUDES.
    """
    g = _pair("1990-01-02", "10:00", "1990-01-03", "10:00")
    assert g.nadi_dosha.present and not g.nadi_dosha.grave
    assert g.nadi_dosha.nadi != "Madhya"
    return g


def test_no_surface_asserts_nadi_has_no_cancelling_conditions():
    hits = []
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in {".py", ".txt", ".html"}:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _ABSOLUTE.search(line):
                hits.append(f"{path.relative_to(SRC)}:{n}: {line.strip()[:90]}")
    assert not hits, (
        "the unsourced Nadi absolute is back; matching.md v.34 records regional "
        "and community exemptions, so 'no cancelling conditions' / 'no parihāras' "
        "contradicts the disclosure rendered beside it:\n  " + "\n  ".join(hits)
    )


def _nadi_lines(name):
    """Every line in an overlay that mentions Nadi at all.

    NOT `ln.startswith("- Nadi ")`. That collected one line and made every
    other instruction in the file invisible -- and the original #397 defect WAS
    such an instruction. QA round 1 demonstrated it: adding

        - Regional or community exemptions for Nadi are not part of this
          tradition; never tell the seeker one exists.

    to both overlays reintroduces the exact defect this change was opened to
    remove, and the suite stayed green.
    """
    return [ln.strip() for ln in (PROMPTS / name).read_text(encoding="utf-8").splitlines()
            if re.search(r"\bnadi\b", ln, re.IGNORECASE)]


def test_both_ask_overlays_carry_the_identical_nadi_line():
    mine = [ln for ln in _nadi_lines("ask_matching.txt") if _RULE_MARK in ln]
    third = [ln for ln in _nadi_lines("ask_matching_third_party.txt") if _RULE_MARK in ln]
    assert len(mine) == 1 and len(third) == 1, (mine, third)
    assert mine == third, "the two overlays' Nadi rules have drifted apart"
    assert "exemptions" in mine[0], "the overlay must acknowledge the disclosed exemptions"
    # THE FULL CLAUSE, NOT THE WORD "Madhya". QA round 2 rewrote both overlays
    # to the exact inverse -- "apply to the Madhya Nadi only" -- and the suite
    # stayed green, because "Madhya" was still present and the two files still
    # matched. The drift row cannot see it either: an identical inversion in
    # both files is not drift. That is round 1's BUG-2 pathology returning at a
    # different granularity -- a check that cannot fail on the error it exists
    # to catch -- inside the fix for BUG-1.
    assert "OUTSIDE the Madhya Nadi only" in mine[0], (
        "the overlay must scope the exemption AWAY from Madhya: the source reads "
        "मध्यनाडी छोड़के, EXCLUDING Madhya Nadi, so an unscoped -- or inverted -- "
        f"sentence tells exactly the couples the text excludes that an exemption "
        f"exists for them. Got: {mine[0]!r}"
    )
    assert "Never invent any other Nadi condition." in mine[0], (
        "the anti-hallucination clause is gone; losing it is how a model invents "
        "a Nadi parihāra the text does not grant"
    )
    assert "slight (alpa) grade applies where pada-Nadi differs" in mine[0], (
        "the alpa clause is gone, so the model has no basis for the one "
        "mitigation the text does grant"
    )


@pytest.mark.parametrize("name", ["ask_matching.txt", "ask_matching_third_party.txt"])
def test_no_other_line_in_an_overlay_restates_the_nadi_rule(name):
    """The rule is stated once per file, and nothing else in it argues.

    Two sentences on one surface that cannot both be true is the whole subject
    of this change. A second instruction about parihāras, exemptions,
    cancelling or waiving -- anywhere in the file, under any prefix -- is that
    defect returning, whatever it says.
    """
    lines = _nadi_lines(name)
    rule = [ln for ln in lines if _RULE_MARK in ln]
    assert len(rule) == 1, f"{name}: the Nadi rule appears {len(rule)} times"
    strays = [ln for ln in lines if ln not in rule and _RULE_TOPIC.search(ln)]
    assert not strays, (
        f"{name} carries a second Nadi instruction about exemptions or "
        f"parihāras beside the rule line:\n  " + "\n  ".join(strays)
    )


def test_engine_note_states_the_narrowed_position_and_keeps_the_disclosure():
    nd = _nadi_pair_nongrave().nadi_dosha
    assert not _ABSOLUTE.search(nd.note), nd.note
    assert _RULE_MARK in nd.note
    assert "exemptions" in nd.note and "which we do not apply" in nd.note
    # The disclosure the note points at ("shown below") must still be there.
    assert nd.unevaluated == M._NADI_UNEVALUATED and nd.unevaluated
    assert "region and community" in nd.unevaluated[0]


def test_a_madhya_pair_is_not_told_an_exemption_was_declined_for_it():
    """The source scopes the exemption to NON-Madhya; so must the sentence.

    मध्यनाडी छोड़के पार्श्वनाडियोंका दोष गोदावरीके दक्षिण अथवा क्षत्रिय आदिकोंको
    नहीं -- "EXCLUDING Madhya Nadi, the side-Nadi dosha is waived south of the
    Godavari and for Kshatriyas and others." The note was appended
    unconditionally to both branches, so a panel reading `Madhya · Gravest
    form` sat beside a flat claim that an exemption existed and we had chosen
    not to apply it -- to exactly the couples the text excludes from it, and
    directly above `_NADI_UNEVALUATED`, which IS scoped. One panel, the same
    claim twice, at two different scopes.
    """
    nd = _nadi_pair().nadi_dosha
    assert nd.grave and nd.nadi == "Madhya"
    assert "do not extend to the Madhya Nadi" in nd.note, nd.note
    assert "which we do not apply" not in nd.note, (
        "the unscoped 'we declined an exemption' sentence is back on a Madhya "
        "pair, which the source excludes from the exemption entirely"
    )
    # The scoped disclosure below it is unchanged and still says who it covers.
    assert "outside the " in nd.unevaluated[0] and "Madhya" in nd.unevaluated[0]


def test_the_alpa_branch_says_reduced_and_never_removed():
    """A pada-level difference makes the dosha slight. It does not clear it."""
    nd = _nadi_pair_alpa().nadi_dosha
    assert nd.alpa and nd.present
    assert len(nd.mitigations) == 1, nd.mitigations
    m = nd.mitigations[0]
    assert "reduced, not removed" in m, m
    assert "slight" in m
    # The grade is a wording decision only -- it must never clear the dosha or
    # move a point. Both halves asserted, because the mitigation note saying
    # "reduced" while the engine cleared the dosha would be the same
    # two-claims-one-panel defect in a new place.
    assert nd.present is True
    assert _ABSOLUTE.search(m) is None


def test_the_exemption_disclosure_says_we_do_NOT_apply_them():
    """G-4. Dropping the "not" leaves a sentence that is false and ships.

    `_NADI_UNEVALUATED` renders verbatim on every afflicted panel in both
    languages. QA round 2 flipped it to "We apply those exemptions
    automatically." and the suite stayed green -- a claim the product
    contradicts, on the panel whose subject is which claims the product makes.
    The adjacent SCOPE was already guarded; the verb was not.
    """
    u = M._NADI_UNEVALUATED[0]
    assert "We do not apply those exemptions" in u, (
        f"the disclosure no longer says the exemptions are unapplied: {u!r}"
    )
    assert "outside the " in u and "Madhya" in u, f"the scope is gone: {u!r}"


def test_the_alpa_pointer_cannot_contradict_the_mitigation_it_points_at():
    """G-5. The fixture reached the branch; the assertion did not follow it.

    `test_the_alpa_branch_says_reduced_and_never_removed` asserts on
    `nd.mitigations[0]` and never on `nd.note`, so the sentence that POINTS at
    the mitigation was unguarded. QA round 2 rewrote it to "A mitigation applies
    which clears this dosha, below." -- which renders directly above "the
    tradition calls the dosha slight in this case — reduced, not removed."

    Two sentences on one panel that cannot both be true is this change's
    defining defect, reproducible with one word and no test red.
    """
    nd = _nadi_pair_alpa().nadi_dosha
    assert "One mitigation applies, below." in nd.note, nd.note
    for claim in ("clears", "removes", "cancels", "waives", "no longer"):
        assert claim not in nd.note, (
            f"the note claims the dosha is {claim} while the mitigation it "
            f"points at says 'reduced, not removed': {nd.note!r}"
        )
    # And the note must still be the thing the panel renders, so the two
    # sentences are read together rather than one of them being dead text.
    assert "reduced, not removed" in nd.mitigations[0]


def test_a_nadi_dosha_awards_no_points_however_it_is_graded():
    """The first numeric assertion on the 36-point engine in this repo.

    QA round 1: `total_awarded` appears in ZERO test files, and changing the
    same-Nadi branch from `awarded=0.0` to `awarded=8.0` moves a real couple
    from 18.0/36 Avara to 26.0/36 Madhyam, flips `nadi_shuddha` true so the
    "requires clean Nadi" warning silently vanishes from the LLM context --
    and 681 tests pass. This file is the first ever to import the engine, and
    it asserted only prose. One line closes it, and it is on-thesis: no
    mitigation adds points.
    """
    for guna in (_nadi_pair(), _nadi_pair_alpa(), _nadi_pair_nongrave()):
        nadi = [k for k in guna.kootas if k.name == "Nadi"][0]
        assert nadi.max_points == 8
        assert nadi.awarded == 0.0, (
            f"a present Nadi dosha ({guna.nadi_dosha.nadi}, grave="
            f"{guna.nadi_dosha.grave}, alpa={guna.nadi_dosha.alpa}) awarded "
            f"{nadi.awarded} of 8 -- no mitigation may move a koota score"
        )


@pytest.mark.parametrize("table,needle", [
    (_EN, "no mitigation adds points"),
    (_HI, "अंक नहीं बढ़ते"),
])
def test_panel_footnote_still_says_no_points_and_not_the_absolute(table, needle):
    text = table["matching_nadi_nocancel"]
    assert needle in text, text
    assert not _ABSOLUTE.search(text)
    assert not _ABSOLUTE_HI.search(text), "the Hindi absolute is back"


def test_the_english_footnote_states_the_position_and_not_only_the_points():
    """The mirror of the Hindi test, and its absence was the mirror defect.

    Round 1's BUG-2 was "Hindi lost the positional claim and the guard could not
    see it". The fix added a Devanagari positive assertion -- and added none for
    English, leaving `_EN` checked for "no mitigation adds points" only: the
    points half, which is exactly the half BUG-2 said was not the problem.

    QA round 2 rewrote the English footnote to "Nadi is among the Bhakoot
    parihāras, and no mitigation adds points to it." -- the literal opposite of
    this change's thesis, rendered to every English reader on /matching -- and
    686 tests passed. `_ABSOLUTE` cannot match it: it contains neither "no
    cancelling conditions" nor "no parihāras".
    """
    en = _EN["matching_nadi_nocancel"]
    assert "not among the Bhakoot parih" in en, (
        f"the English footnote does not state Nadi's position: {en!r}"
    )
    assert "no mitigation adds points" in en, f"the points half was lost: {en!r}"
    assert not _ABSOLUTE.search(en), en


def test_the_hindi_footnote_states_the_position_and_not_only_the_points():
    """Hindi lost the positional claim instead of having it corrected.

    The English reads "Nadi is not among the Bhakoot parihāras, and no
    mitigation adds points to it." The Hindi had its first sentence DELETED,
    leaving only the points half -- so the claim that is this change's entire
    thesis was stated on five of six surfaces and not in Hindi.

    It passed review because the only check was `not _ABSOLUTE.search(text)`,
    an ASCII pattern run against Devanagari: it cannot fail, and a string
    asserting the exact opposite passed it. A negative check in the wrong
    alphabet needs a POSITIVE one beside it.
    """
    hi = _HI["matching_nadi_nocancel"]
    assert "भकूट" in hi, (
        "the Hindi footnote does not mention Bhakoot at all, so it cannot be "
        f"stating Nadi's position relative to its parihāras: {hi!r}"
    )
    assert "सम्मिलित नहीं" in hi, (
        f"the Hindi footnote does not say Nadi is NOT among them: {hi!r}"
    )
    assert "अंक नहीं बढ़ते" in hi, f"the points half was lost: {hi!r}"
    assert not _ABSOLUTE_HI.search(hi), hi


def test_ask_context_names_the_exemptions_the_overlay_refers_to():
    out = llm.format_guna_milan_for_prompt(_nadi_pair(), "A and B")
    # nd.unevaluated is fed the way bd.unevaluated is, or the overlay names
    # exemptions the model cannot see.
    assert f"  not evaluated: {M._NADI_UNEVALUATED[0]}" in out
    assert "gains no points from any mitigation" in out
    assert "not among the Bhakoot parih" in out
    assert not _ABSOLUTE.search(out)
    assert "NO cancelling" not in out


# --- QA round 2: the surfaces nothing rendered ---------------------------------

def _match_html(client, d1, t1, d2, t2):
    """POST /matching for a real pair and return the rendered page."""
    r = client.post("/matching", data={
        "g_name": "A", "g_birth_date": d1, "g_birth_time": t1, "g_birth_place": "Mumbai",
        "b_name": "B", "b_birth_date": d2, "b_birth_time": t2, "b_birth_place": "Mumbai",
    })
    assert r.status_code == 200, r.status_code
    return r.text


def test_the_scoped_sentence_actually_reaches_the_rendered_panel(client):
    """G-3. BUG-1 was a RENDERED defect; its fix was asserted on a dataclass.

    QA round 2 emptied `{{ _nd.note }}` in `matching_result.html` and the entire
    scoped sentence -- the fix -- vanished from the panel with 686 tests green.
    A fix for something a user reads has to be asserted where the user reads it.
    """
    html = _match_html(client, "1990-01-01", "10:00", "1990-01-04", "10:00")
    assert "gravest form of this affliction" in html
    assert "do not extend to the Madhya Nadi" in html, (
        "the scoped sentence is not on the page a Madhya couple is shown"
    )
    assert "which we do not apply" not in html, "the unscoped version is rendered"


def test_the_exemption_disclosure_reaches_the_rendered_panel(client):
    """G-3, second half. `{% if _nd.unevaluated %}` -> False stayed green.

    The non-grave note ends "(shown below)". With the disclosure block gone that
    pointer aims at nothing -- a panel referring the reader to text that is not
    there.
    """
    html = _match_html(client, "1990-01-02", "10:00", "1990-01-03", "10:00")
    assert "(shown below)" in html, "the non-grave note is not rendering"
    assert "We do not apply those exemptions" in html, (
        "the note says 'shown below' and nothing is shown below"
    )


def test_the_ask_context_scopes_the_exemption_on_the_grade(client):
    """S-1. The fourth surface, and the one this change created.

    On main the /ask NOTE made no exemption claim at all. The scoping fix
    covered `matching.py` and both overlays and missed this, so a Madhya
    couple's model context carried -- directly under their own "gravest form"
    line -- a flat statement that exemptions exist and are not applied here,
    with nothing saying they are excluded. `nd.note`, where the scoped sentence
    lives, is never fed to the model, so this line must carry the scope itself.

    Both branches asserted: pinning only the grave one would pass on a rule that
    said "do not extend to the Madhya Nadi" to every couple, which is false for
    the Adi and Antya pairs the exemption does reach.
    """
    grave = llm.format_guna_milan_for_prompt(_nadi_pair(), "A and B")
    assert "do not extend to the Madhya Nadi" in grave, grave
    assert "so none applies to this pair" in grave
    assert "are not applied here" not in grave, (
        "the unscoped sentence is still in a Madhya pair's context"
    )

    mild = llm.format_guna_milan_for_prompt(_nadi_pair_nongrave(), "A and B")
    assert "outside the \nMadhya Nadi" in mild or "outside the Madhya Nadi" in mild
    assert "are not applied here" in mild
    assert "do not extend to the Madhya Nadi" not in mild, (
        "a non-Madhya pair is told the exemption excludes them, which it does not"
    )


def test_a_nadi_absolute_cannot_return_in_a_third_phrasing(client):
    """G-6. `_ABSOLUTE` matched two wordings, so a third was free.

    QA round 2 rewrote the /learn callout to "Nadi can never be cancelled or
    waived by anything." -- #397's original defect, in words the pattern does
    not match, suite green. The scan also skipped `knowledge/*.md`, which is the
    file that DECIDES this question.
    """
    hits = []
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in {".py", ".txt", ".html", ".md"}:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _ABSOLUTE_ANY.search(line):
                hits.append(f"{path.relative_to(SRC)}:{n}: {line.strip()[:90]}")
    assert not hits, (
        "an absolute Nadi claim is back in a phrasing the original pattern did "
        "not cover:\n  " + "\n  ".join(hits)
    )


def test_no_nadi_instruction_hides_in_the_base_ask_prompt():
    """G-7. The overlay scan covered the two overlays, not `ask.txt`.

    All three land in the same composed system prompt, so an instruction added
    to the base file would be invisible to the per-overlay scan. There are zero
    Nadi mentions in `ask.txt` today, which is what makes this a floor rather
    than a fix.
    """
    base = (PROMPTS / "ask.txt").read_text(encoding="utf-8")
    strays = [ln.strip() for ln in base.splitlines()
              if re.search(r"\bnadi\b", ln, re.IGNORECASE)]
    assert not strays, (
        "the base ask prompt now carries a Nadi instruction, which the "
        "per-overlay scan cannot see:\n  " + "\n  ".join(strays)
    )


def test_the_fourth_grade_cell_is_reachable_and_correctly_scoped():
    """G-7. `grave=False, alpa=True` had no fixture; it is real.

    QA round 2 measured 144 of 9,730 pairs in that cell. Its note must carry the
    non-grave scoping AND the alpa pointer, which no other fixture combines.
    """
    # Measured, not guessed: 1990-01-02 04:00 x 10:00 Mumbai -> Adi, grave=False,
    # alpa=True. My first attempt at this fixture was a guess and the two charts
    # did not even share a Nadi -- the assertion caught it, which is the whole
    # argument for asserting the fixture's own shape before using it.
    guna = _pair("1990-01-02", "04:00", "1990-01-02", "10:00")
    nd = guna.nadi_dosha
    assert not nd.grave and nd.alpa, (
        f"fixture drifted: nadi={nd.nadi} grave={nd.grave} alpa={nd.alpa}")
    assert "One mitigation applies, below." in nd.note
    assert "which we do not apply" in nd.note, "the non-grave scope is missing"
    assert "do not extend to the Madhya Nadi" not in nd.note
    assert [k for k in guna.kootas if k.name == "Nadi"][0].awarded == 0.0
