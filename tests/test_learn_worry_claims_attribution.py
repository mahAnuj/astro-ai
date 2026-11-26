"""#1509: the ten worry-topic /learn pages stop asserting what the held books do not give.

#1501 did this for the home-page cards; the same families of sentence lived on the articles the
cards link to: prevalence ("most online calculators ignore ...", "a lot of people labelled Manglik
actually aren't"), outcome ("most lives are better on the other side", "usually after 28-30"),
motive ("the industry preys on fear"), and attribution that knowledge/ does not hold ("K.N. Rao
states it has no scriptural basis", "20th-century innovation"). knowledge/vedic_reference.md
section 3.4 says the held Rao (Lessons) teaches Kala Sarpa as a yoga and calls it highly
problematic, so the old page also contradicted the book it leaned on. The astro-auditor ruling on
#1509 gave each claim a verdict; this test pins the families it removed.

Two surfaces are read for each of the ten slugs, because the defect lived on both: the page a
visitor receives (head and scripts stripped, so a title or JSON-LD headline is never scanned), and
every string field of the matching learn_registry Article except title and seo_title. It is a
phrase test: it catches the families it names, not every rewording; qa and the auditor read the
rest.
"""
from __future__ import annotations

import html
import re

import pytest

SLUGS = (
    "sade-sati",
    "manglik-dosh",
    "kaal-sarp-dosh",
    "manglik-remedies",
    "marriage-delayed",
    "kaal-sarp-dosh-remedies",
    "pitru-dosh-remedies",
    "ketu-remedies",
    "planets-in-7th-house-marriage",
    "career-during-sade-sati",
)

# Each pattern is a family of sentence the auditor ruled on, matched after _norm().
_BANNED = (
    r"over-?diagnos", r"misdiagnos", r"over-?(feared|interpret|read)",
    r"most (lives|people|online|modern|websites|calculators|charts|successful|well-known)",
    r"a lot of people", r"actually aren", r"better,? not worse", r"most intense", r"hardest",
    r"vast majority",
    r"preys? on", r"exploiting", r"weaponis", r"kinder than",
    r"k\.?n\.? rao", r"20th[- ]century", r"no scriptural basis",
    r"delayed marriage[^.]{0,30}(usually|often)", r"usually after 2", r"serendipit",
    r"psychological closure",
    r"folk-dramatis", r"rarely random", r"usually outperforms", r"most people'?s professional",
    r"steve jobs", r"₹\s?5,?000", r"most-cited", r"cited most",
    # #1509 QA round: outcome and prevalence families the first pass left on career-during-sade-sati,
    # sade-sati and marriage-delayed.
    r"almost always", r"\brarely\b", r"lots of people", r"better careers?",
    r"most simple calculators", r"nobody mentions", r"many charts that look like",
)
_BANNED_RE = [re.compile(p) for p in _BANNED]


def _norm(s: str) -> str:
    s = html.unescape(s)
    s = (s.replace("’", "'").replace("‘", "'").replace(" ", " ")
          .replace("–", "-").replace("—", "-").replace("‑", "-"))
    return re.sub(r"\s+", " ", s).lower()


def _hits(text: str) -> list[str]:
    n = _norm(text)
    out = []
    for p in _BANNED_RE:
        m = p.search(n)
        if m:
            # The surrounding words, so a failure says which sentence to change.
            out.append(f"{p.pattern!r}: ...{n[max(0, m.start() - 40):m.end() + 40]}...")
    return out


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(obj, (list, tuple, set, frozenset)):
        for v in obj:
            yield from _strings(v)


def _visible(client, slug: str) -> str:
    r = client.get(f"/learn/{slug}/")
    assert r.status_code == 200, (slug, r.status_code)
    t = r.text
    # The head carries <title>, og:title and the JSON-LD headline; titles are not this issue's.
    t = re.sub(r"(?is)<head\b.*?</head>", " ", t)
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    return re.sub(r"(?s)<[^>]+>", " ", t)


def _article(slug: str):
    from astro_ai.learn_registry import get_article

    art = get_article(slug)
    assert art is not None, slug
    return art


def _registry_text(slug: str) -> str:
    art = _article(slug)
    parts = []
    for field in ("summary", "seo_description", "llm_summary", "faqs"):
        parts.extend(_strings(getattr(art, field)))
    return " \n ".join(parts)


@pytest.mark.parametrize("slug", SLUGS)
def test_rendered_worry_page_carries_no_unsourced_claim_family(client, slug):
    assert _hits(_visible(client, slug)) == [], slug


# Two more registry entries the auditor ruled on whose FAQ carried the same families (Sade Sati
# "most people who work with it emerge stronger" under saturn-remedies; "classical cancellations most
# calculators ignore" under mars-remedies). Their templates are not in the ten.
_REGISTRY_ONLY = ("saturn-remedies", "mars-remedies")


@pytest.mark.parametrize("slug", SLUGS + _REGISTRY_ONLY)
def test_registry_entry_carries_no_unsourced_claim_family(slug):
    assert _hits(_registry_text(slug)) == [], slug


# Attribution each page must keep: the replacement text says whose view a sentence is, or that no
# held book gives it. One marker per page, taken from the sentence that carries the attribution, so
# deleting it turns the test red (a list of loose markers passed on any "we hold" anywhere).
_MARKER = {
    "sade-sati": "that is our approach, not a classical claim",
    "manglik-dosh": "the one antidote list we hold gives only the conjunction",
    "kaal-sarp-dosh": "no book we hold gives a kaal sarp cancellation list",
    "manglik-remedies": "the lists differ on which rules count",
    "marriage-delayed": "delayed marriage is the usual online claim, not found in them",
    "kaal-sarp-dosh-remedies": "we have not traced that to a book we hold",
    "pitru-dosh-remedies": "we hold no book that defines it",
    "ketu-remedies": "that is practice, not a held book",
    "planets-in-7th-house-marriage": "the one antidote list we hold",
    "career-during-sade-sati": "this is practical advice, not a rule",
}


@pytest.mark.parametrize("slug", SLUGS)
def test_worry_page_names_what_we_hold_or_whose_view_it_is(client, slug):
    assert _MARKER[slug] in _norm(_visible(client, slug)), slug


def test_sade_sati_keeps_the_one_sourced_softening(client):
    n = _norm(_visible(client, "sade-sati"))
    assert "hardly going to trouble the person" in n
    # ... and says it is Rao's wording, not a general claim of benefit.
    assert "our reading, not his" in n


def test_kaal_sarp_page_says_what_the_held_rao_says(client):
    n = _norm(_visible(client, "kaal-sarp-dosh"))
    assert "highly problematic" in n
    # The body sentence, not the bare phrase: the FAQ below the article also says "other yogas may not function".
    assert "rao says the opposite of an override" in n
    assert "counts either order" in n
    assert "we do not hold bphs" in n


def test_kaal_sarp_remedies_page_does_not_call_it_unnamed(client):
    n = _norm(_visible(client, "kaal-sarp-dosh-remedies"))
    assert "highly problematic" in n
    assert "even name as a dosha" not in n


def test_manglik_page_says_the_lists_differ_and_labels_online_rules(client):
    n = _norm(_visible(client, "manglik-dosh"))
    # The sentence, not the bare phrase: "how far the lists differ" appears further down the page.
    assert "and the lists differ. the dosha isn't a flat yes/no" in n
    assert "repeated online" in n
    assert "vasudev" in n
    # Raman ranks the dosha from all three reference points; the page may not say "from only one,
    # the dosha is mild" as though that were his reading.
    assert "from only one, the dosha is mild" not in n


@pytest.mark.parametrize("slug", ("marriage-delayed", "planets-in-7th-house-marriage"))
def test_manglik_cancellations_are_labelled_repeated_online(client, slug):
    n = _norm(_visible(client, slug))
    assert "repeated online" in n, slug
    assert "exclude the person from manglik diagnosis entirely" not in n
    assert "cancels manglik in most classical readings" not in n
