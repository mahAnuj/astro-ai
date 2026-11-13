"""#959: the Kaal Sarp copy prints nothing that knowledge/ does not hold.

`knowledge/vedic_reference.md` section 3.2 says three things: Kaal Sarp is not in BPHS,
Phaladeepika, Saravali, Jataka Parijata or Brihat Jataka; it is a 20th-century innovation
popularised by Trimbakeshwar priests; and many classical scholars (including KN Rao) state it
has no scriptural basis. The pages used to add verbatim quotations attributed to K.N. Rao and
B.V. Raman, a claim about the ninth edition of Three Hundred Important Combinations, an
Astrological Magazine print history, and Uttara Kalamrita in the list of texts that lack it. None
of that is in knowledge/ and data/ is absent from the checkout, so none of it can be checked.

The same issue carried two Manglik leftovers from #838/#856: the manglik-dosh meta description
said "The six houses Mars must sit in", and the mars-remedies heading listed six houses flatly.

Three surfaces are scanned, because the defect lived on all three: the template files, the i18n
tables as loaded (EN and HI), and every string field of every learn article. Two rendered
checks then read the pages a visitor gets, so a phrase assembled from a context variable is
still seen. It is a phrase test: it catches the wording it names, not every rewording.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "astro_ai" / "templates"

# Each banned phrase is a piece of a quotation or claim removed in #959, matched case-insensitively
# after whitespace is collapsed.
_BANNED = (
    "biggest frauds",
    "not much importance in individual",
    "fright in clients",
    "much feared",
    "Astrological Magazine",
    "Three Hundred Important Combinations",
    "six houses Mars must sit",
    # Round-1 QA: attributions knowledge/ does not hold (section 3.3 supports only focus/struggle in
    # the Rahu/Ketu houses, and section 3.2 says the five texts do not contain the concept at all).
    "treat Kaal Sarp as binary",
    "modern practitioners say a true Kaal Sarp",
    # Hindi renderings of the same quotations and the magazine name.
    "सबसे बड़ी धोखाधड़",  # stem: the old text had the plural, धोखाधड़ियों
    "बहुत भयभीत करने वाला",
    "एस्ट्रोलॉजिकल मैगजीन",
)

# Section 3.2 lists five books. Uttara Kalamrita is not among them, so no Kaal Sarp surface may
# say it lacks the concept. (It is allowed on pages about something else.)
_KAAL_SARP_PAGES = ("kaal-sarp-dosh.html", "kaal-sarp-dosh-remedies.html", "_ksy_caveat.html")


def _norm(s: str) -> str:
    # NFC, because Devanagari nukta letters have a precomposed form (U+095C) and a decomposed one
    # (U+0921 U+093C) that print identically; a banned Hindi phrase typed one way would miss the
    # same words stored the other way.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).lower()


def _hits(text: str, phrases=_BANNED) -> list[str]:
    n = _norm(text)
    return [p for p in phrases if _norm(p) in n]


def _strings(obj):
    """Every string reachable from a dataclass field, tuple, list or dict."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for v in obj:
            yield from _strings(v)
    elif hasattr(obj, "__dataclass_fields__"):
        for f in obj.__dataclass_fields__:
            yield from _strings(getattr(obj, f))


def _visible(client, path: str, method: str = "get", **kw) -> str:
    r = getattr(client, method)(path, **kw)
    assert r.status_code == 200, (path, r.status_code)
    return re.sub(r"\s+", " ", r.text)


# --- the three source surfaces ------------------------------------------------------------

def test_no_template_carries_a_banned_phrase():
    bad = {}
    for p in sorted(TEMPLATES.rglob("*.html")):
        h = _hits(p.read_text(encoding="utf-8"))
        if h:
            bad[str(p.relative_to(TEMPLATES))] = h
    assert not bad, bad


def test_no_i18n_string_carries_a_banned_phrase():
    from astro_ai import i18n

    bad = {}
    for lang, table in i18n._TABLES.items():
        for key, value in table.items():
            h = _hits(value)
            if h:
                bad[f"{lang}:{key}"] = h
    assert not bad, bad


def test_no_learn_article_field_carries_a_banned_phrase():
    from astro_ai.learn_registry import ARTICLES

    bad = {}
    for art in ARTICLES:
        h = [p for s in _strings(art) for p in _hits(s)]
        if h:
            bad[art.slug] = sorted(set(h))
    assert not bad, bad


@pytest.mark.parametrize("name", _KAAL_SARP_PAGES)
def test_kaal_sarp_templates_do_not_list_uttara_kalamrita(name):
    t = (TEMPLATES / "learn" / name if name != "_ksy_caveat.html" else TEMPLATES / name)
    assert "uttara kalamrita" not in t.read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_ksy_caveat_strings_do_not_list_uttara_kalamrita(lang):
    from astro_ai import i18n

    for key in ("ksy_caveat_body_1", "ksy_caveat_body_2", "ksy_caveat_body_3"):
        v = i18n._TABLES[lang][key].lower()
        assert "uttara kalamrita" not in v and "उत्तर कालामृत" not in v, (lang, key)


# --- what a visitor receives --------------------------------------------------------------

_PAGES = [
    "/learn/kaal-sarp-dosh/",
    "/learn/kaal-sarp-dosh-remedies/",
    "/kaal-sarp-check",
    "/kaal-sarp-check?lang=hi",
    "/learn/manglik-dosh/",
    "/learn/mars-remedies/",
]


@pytest.mark.parametrize("path", _PAGES)
def test_rendered_page_has_no_banned_phrase(client, path):
    assert _hits(_visible(client, path)) == [], path


@pytest.mark.parametrize("path", ["/kaal-sarp-check", "/kaal-sarp-check?lang=hi"])
def test_kaal_sarp_result_page_has_no_banned_phrase(client, path):
    birth = {"name": "Fixture", "birth_date": "1957-09-07", "birth_time": "01:05",
             "birth_place": "Mumbai"}
    t = _visible(client, path, "post", data=birth)
    assert _hits(t) == [], path


def test_kaal_sarp_article_says_what_section_3_2_holds(client):
    t = _visible(client, "/learn/kaal-sarp-dosh/")
    assert "20th-century innovation" in t
    assert "Trimbakeshwar" in t
    assert "no scriptural basis" in t
    assert "Uttara Kalamrita" not in t


def test_caveat_strings_state_the_three_things_and_hindi_matches(client):
    from astro_ai import i18n

    en = i18n._TABLES["en"]["ksy_caveat_body_1"] + i18n._TABLES["en"]["ksy_caveat_body_2"]
    assert "20th-century innovation" in en and "Trimbakeshwar" in en and "no scriptural basis" in en
    hi = i18n._TABLES["hi"]["ksy_caveat_body_1"] + i18n._TABLES["hi"]["ksy_caveat_body_2"]
    assert "20वीं शताब्दी" in hi and "त्र्यंबकेश्वर" in hi and "शास्त्रीय आधार नहीं" in hi
    # The Hindi caveat must be what the Hindi result page serves, not an English fallback. (The
    # form page renders this partial in English even at ?lang=hi; that is not #959's to fix.)
    birth = {"name": "Fixture", "birth_date": "1957-09-07", "birth_time": "01:05",
             "birth_place": "Mumbai"}
    t = _visible(client, "/kaal-sarp-check?lang=hi", "post", data=birth)
    assert "त्र्यंबकेश्वर मंदिर के पुरोहितों" in t


# --- the Manglik leftovers ----------------------------------------------------------------

def test_manglik_dosh_meta_description_states_five_houses_with_the_1st_optional(client):
    t = _visible(client, "/learn/manglik-dosh/")
    m = re.search(r'<meta name="description" content="([^"]*)"', t)
    assert m, "no meta description rendered"
    d = m.group(1)
    assert "five houses" in d and "1st optional" in d
    assert "six houses" not in d
    assert len(d) <= 160, len(d)


def test_mars_remedies_heading_states_five_houses_with_the_1st_optional(client):
    t = _visible(client, "/learn/mars-remedies/")
    assert "Manglik Dosh (Mars in 2, 4, 7, 8, or 12, with the 1st as an optional addition)" in t
    assert "Mars in 1, 2, 4, 7, 8, or 12)" not in t
