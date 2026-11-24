"""#1295: the Hindi suffix may not license Sanskrit terms the prompt files forbid.

rashifal_single.txt says "In Hindi, use everyday spoken Hindi, not Sanskrit-heavy words", and
_LANG_SUFFIX["hi"] is appended LAST, so it wins any conflict. It used to say "Use Sanskrit Vedic
terms naturally", so the model got an instruction and its opposite in one system prompt. The
suffix now names everyday Hindi and keeps the six common terms; dasha_deep_dive.txt still asks
for Sanskrit dasha terms, so the suffix must not forbid Sanskrit outright either.

Both tests assemble the real prompt through llm._system_prompt; no text is restated here.
"""
import re

from astro_ai import llm
from astro_ai.routes import deps

CORE_TERMS = ("राशि", "लग्न", "ग्रह", "नक्षत्र", "भाव", "मंगल दोष")


def test_hindi_rashifal_prompt_does_not_license_sanskrit_beside_its_own_ban():
    prompt = llm._system_prompt(deps.RASHIFAL_PROMPT_PATH, "hi")
    assert "not Sanskrit-heavy" in prompt, "the rashifal prompt lost its everyday-Hindi rule"
    assert not re.search(r"Sanskrit[^.]*naturally", prompt), (
        "an unconditional licence for Sanskrit terms sits beside the 'not Sanskrit-heavy' rule")
    for term in CORE_TERMS:
        assert term in prompt, f"the common term {term} must stay in the Hindi suffix"


def test_hindi_suffix_does_not_forbid_the_sanskrit_dasha_terms_outright():
    prompt = llm._system_prompt(deps.DASHA_DEEP_DIVE_PROMPT_PATH, "hi")
    assert "Use Sanskrit terms (Mahadasha" in prompt
    suffix = llm._LANG_SUFFIX["hi"]
    assert not re.search(r"(avoid|never|do not use|don't use)[^.]*Sanskrit", suffix, re.I), (
        "the suffix is last and would override dasha_deep_dive.txt's request for Sanskrit terms")
