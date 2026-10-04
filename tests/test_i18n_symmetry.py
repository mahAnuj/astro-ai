"""The _EN/_HI key sets must match — and until now nothing checked.

`ARCHITECTURE.md` has described this as "symmetric key sets (enforced)" for
some time. QA round 6 (#124) found there was no enforcement anywhere: no
assertion in `i18n.py`, no test, no gate. The claim was simply false.

Why it matters, measured. `translate()` is
`table.get(key) or _EN.get(key) or key`, so a key present in `_EN` and absent
from `_HI` does not raise and does not render a visible placeholder — it
renders ENGLISH, on a page whose `<html lang>` says Hindi:

    >>> del _HI["nav_home"]
    >>> translate("hi", "nav_home")
    'Home'

That is exactly the failure mode #124's QA rounds kept finding by hand —
English chrome on a Hindi page — and the fallback makes it invisible to every
happy-path check. It matters more now than it did: before this branch Hindi
had no indexable URL, so a leak was cosmetic. Now 13 URLs are in the sitemap
and a leak is indexed.

The fallback itself is deliberate and stays: rendering a raw key at a reader
is worse than rendering English. This file is the thing that makes the
fallback a safety net rather than a hiding place.
"""
from __future__ import annotations

from astro_ai.i18n import _EN, _HI


def test_key_sets_are_identical():
    missing_hi = sorted(set(_EN) - set(_HI))
    extra_hi = sorted(set(_HI) - set(_EN))
    assert not missing_hi, (
        f"{len(missing_hi)} key(s) have no Hindi: {missing_hi[:8]}. "
        "translate() will silently render English for these on a Hindi page."
    )
    assert not extra_hi, (
        f"{len(extra_hi)} Hindi key(s) have no English: {extra_hi[:8]}. "
        "Unreachable, and English is the fallback every other language needs."
    )


def test_no_hindi_value_is_accidentally_english():
    """A key can be present and still be a copy-paste of the English.

    Not every Hindi value must contain Devanagari — a few are deliberately
    shared (proper nouns, numerals, the `bhagya_out_of` separator). So this
    asserts the SET of such keys does not grow silently, rather than asserting
    none exist. If you add one, add it here and say why.
    """
    shared = {k for k in _HI if _HI[k] == _EN[k]}
    no_devanagari = {
        k for k, v in _HI.items()
        if not any("ऀ" <= ch <= "ॿ" for ch in v)
    }
    known = {"bhagya_out_of"}
    assert shared <= known, (
        f"Hindi values identical to English: {sorted(shared - known)}. "
        "Either translate them or add them to `known` with a reason."
    )
    assert no_devanagari <= known, (
        f"Hindi values with no Devanagari at all: {sorted(no_devanagari - known)}"
    )


def test_hindi_strings_invent_no_placeholder_the_callers_do_not_pass():
    """A Hindi string may use FEWER placeholders than its English twin, or
    different ones — the two languages name a rashi differently, so
    `rashifal_single_title` is `{rashi_en} {rashi_sa}` in English and
    `{rashi_hi}` in Hindi, and the call site passes all three. That is fine.

    The real risk is a Hindi string using a placeholder NOTHING passes,
    because `translate()` catches the KeyError and returns the string
    UNFORMATTED — so the reader is shown a literal `{n}` rather than seeing an
    error. Silent again, and Hindi-only.

    So the checkable invariant is: every placeholder a Hindi string uses is
    either in its English twin, or declared below with the call site that
    passes it. A new Hindi string that invents one fails here.
    """
    import re

    # key -> the placeholders Hindi uses that English does not, with the call
    # site that supplies them. Verified by execution, not assumed.
    DECLARED = {
        # today.html:201 — `t(lang, 'transiting_house', n=p.house)`. English
        # reads "transiting your natal house" and ignores the number; Hindi
        # needs the ordinal ("...5वें भाव में").
        "transiting_house": {"n"},
        # The rashi name differs by language; every call site passes
        # rashi_en, rashi_sa and rashi_hi together (rashifal_single.html).
        "rashifal_single_title": {"rashi_hi"},
        "rashifal_single_meta": {"rashi_hi"},
        "rashifal_single_share": {"rashi_hi"},
        "rashifal_single_alt": {"rashi_hi"},
        "rashifal_single_ld_headline": {"rashi_hi"},
        "rashifal_single_ld_desc": {"rashi_hi"},
        "rashifal_single_headline": {"rashi_hi"},
    }

    bad = []
    for key, hi in _HI.items():
        en_slots = set(re.findall(r"\{(\w+)\}", _EN.get(key, "")))
        hi_slots = set(re.findall(r"\{(\w+)\}", hi))
        invented = hi_slots - en_slots - DECLARED.get(key, set())
        if invented:
            bad.append((key, sorted(invented)))
    assert not bad, (
        "Hindi strings use placeholders their English twin does not, and that "
        "are not declared above. If a call site passes them, add them to "
        "DECLARED with the file and line. If not, the reader sees a literal "
        "brace:\n" + "\n".join(f"  {k}: {v}" for k, v in bad[:8])
    )
