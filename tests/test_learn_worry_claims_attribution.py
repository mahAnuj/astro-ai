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
    # #1513: the same motive, price and outcome families on four more pages and one registry FAQ.
    r"exploited", r"fear is misplaced", r"life-defining", r"exploitation happens", r"\bscam",
    r"₹\s?5-?25\s?k", r"₹\s?50\s?k",
)
# The round-2 pages are gated on the #1513 families only. The broad list above trips on sentences
# the issue does not name there ("most people" in rahu/shani prose, "K.N. Rao lineage" in the
# kundali-matching advice on choosing an astrologer), and widening the diff to rewrite those was
# out of scope; they are a follow-up for the auditor.
_BANNED_R2 = (r"exploiting", r"preys? on", r"over-?diagnos") + _BANNED[-7:]
_BANNED_RE = [re.compile(p) for p in _BANNED]
_BANNED_RE_R2 = [re.compile(p) for p in _BANNED_R2]
# _BANNED_R2 is sliced off the END of _BANNED, so a phrase appended to _BANNED silently changes which
# patterns round 2 pins; this makes that edit loud.
assert len(_BANNED_R2) == 10

# #1525: the price-and-motive family (a price band, or why a priest quotes one, stated as fact) on
# thirteen more pages and seven registry entries. A separate tuple, not an addition to _BANNED: appending
# there would shift the _BANNED[-7:] slice above, and would run the broad "most people" / "K.N. Rao"
# families over pages the issue does not name (the trap #1513 documented).
_BANNED_R3 = (
    r"selling anxiety", r"tens of thousands", r"exploiting fear", r"trading on (fear|emotional)",
    r"exploitative", r"heavily exploited", r"emotional urgency", r"inexpensive", r"almost nothing",
    r"cost lakhs", r"modest arrangements", r"extraordinary amounts", r"not a classical astrologer",
    r"under ₹\s?500", r"<\s?₹\s?500", r"₹\s?5-?15\s?k", r"₹\s?5,?000", r"often manipulative",
    r"misrepresenting the tradition", r"rampant", r"exploiting the", r"vendor manipulation",
)
# Page-only: the registry seo_description of five of these slugs says "without vendor manipulation"
# (and pitru-dosh-remedies "under ₹500"); search snippets are deferred (#311 scored a title change a
# miss), so the registry scan below skips seo_description and the page scan carries these too.
_BANNED_R3_PAGE = (r"vendor[- ](manipulation|scam|market)", r"dominates online", r"manipulative [\"']?puja")
_BANNED_RE_R3 = [re.compile(p) for p in _BANNED_R3]
_BANNED_RE_R3_PAGE = [re.compile(p) for p in _BANNED_R3 + _BANNED_R3_PAGE]


def _norm(s: str) -> str:
    s = html.unescape(s)
    s = (s.replace("’", "'").replace("‘", "'").replace(" ", " ")
          .replace("–", "-").replace("—", "-").replace("‑", "-"))
    return re.sub(r"\s+", " ", s).lower()


def _hits(text: str, patterns=None) -> list[str]:
    n = _norm(text)
    out = []
    for p in (_BANNED_RE if patterns is None else patterns):
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


def _registry_text(slug: str, fields=("summary", "seo_description", "llm_summary", "faqs")) -> str:
    art = _article(slug)
    parts = []
    for field in fields:
        parts.extend(_strings(getattr(art, field)))
    return " \n ".join(parts)


# #1513: the pages and the one FAQ #1511's QA round found still carrying the same families.
_ROUND2 = ("rahu-remedies", "mars-remedies", "kundali-matching-ashtakoot-guna-milan", "shani-saturn")
_ROUND2_REGISTRY = _ROUND2 + ("second-marriage-yoga-kundli",)


@pytest.mark.parametrize("slug", SLUGS)
def test_rendered_worry_page_carries_no_unsourced_claim_family(client, slug):
    assert _hits(_visible(client, slug)) == [], slug


@pytest.mark.parametrize("slug", _ROUND2)
def test_rendered_round2_page_carries_no_unsourced_claim_family(client, slug):
    assert _hits(_visible(client, slug), _BANNED_RE_R2) == [], slug


# Two more registry entries the auditor ruled on whose FAQ carried the same families (Sade Sati
# "most people who work with it emerge stronger" under saturn-remedies; "classical cancellations most
# calculators ignore" under mars-remedies). Their templates are not in the ten.
_REGISTRY_ONLY = ("saturn-remedies", "mars-remedies")


@pytest.mark.parametrize("slug", SLUGS + tuple(dict.fromkeys(_REGISTRY_ONLY + _ROUND2_REGISTRY)))
def test_registry_entry_carries_no_unsourced_claim_family(slug):
    # The broad list for the entries #1509 ruled on; only the #1513 families for the round-2 ones,
    # whose other FAQs are outside this issue (see _BANNED_R2).
    pats = _BANNED_RE_R2 if slug in _ROUND2_REGISTRY and slug not in SLUGS + _REGISTRY_ONLY else None
    assert _hits(_registry_text(slug), pats) == [], slug


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


# #1513: one attribution sentence per round-2 page, verbatim from the replacement text.
_MARKER2 = {
    "rahu-remedies": "we hold no source that prices a rahu remedy",
    "mars-remedies": "hanuman chalisa is practice, not a held book",
    "kundali-matching-ashtakoot-guna-milan": "specific mantras and timing are practice, not a held book",
    "shani-saturn": "rewards sustained effort over decades - our reading, not a classical claim",
}
_REGISTRY_MARKER2 = {
    "shani-saturn": "that is our reading, not a classical claim",
    "second-marriage-yoga-kundli": "that is interpretive practice, and the sources we hold say nothing about second marriage",
    "rahu-remedies": "no held source prices a remedy",
    "pitru-dosh-remedies": "no held source prices a remedy",
    "kaal-sarp-dosh-remedies": "no held source prices a remedy",
}


@pytest.mark.parametrize("slug", _ROUND2)
def test_round2_page_names_whose_view_it_is(client, slug):
    assert _MARKER2[slug] in _norm(_visible(client, slug)), slug


@pytest.mark.parametrize("slug", sorted(_REGISTRY_MARKER2))
def test_round2_registry_entry_keeps_its_attribution(slug):
    assert _REGISTRY_MARKER2[slug] in _norm(_registry_text(slug)), slug


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


# #1525: the thirteen pages and seven registry entries that still said what a remedy costs and why a
# priest quotes it (pitru-dosh-remedies joined at build time: its page said "under ₹500" beside a FAQ
# the issue named).
_R3_PAGES = (
    "financial-struggles", "marriage-delayed", "mercury-remedies", "venus-remedies", "jupiter-remedies",
    "saturn-remedies", "pitru-dosh", "rahu-mahadasha-career-problems", "10th-lord-in-6th-house-career",
    "saturn-in-10th-house-career", "chronic-health-issues-kundli", "santan-prapti-children-in-kundli",
    "pitru-dosh-remedies",
)
_R3_REGISTRY = (
    "jupiter-remedies", "saturn-remedies", "marriage-delayed", "santan-prapti-children-in-kundli",
    "chronic-health-issues-kundli", "pitru-dosh", "pitru-dosh-remedies",
)
# seo_description is deferred (see _BANNED_R3_PAGE), so it is not read here.
_R3_FIELDS = ("summary", "llm_summary", "faqs")

# One page-specific attribution clause per page, verbatim from the replacement text.
_MARKER3 = {
    "financial-struggles": 'very large quote for a "lakshmi puja" package',
    "marriage-delayed": 'very large quote for "marriage puja packages"',
    "mercury-remedies": 'very large quote for "budha dosha nivaran packages"',
    "venus-remedies": 'very large quote for "shukra dosha nivaran packages"',
    "jupiter-remedies": 'very large quote for "guru puja packages"',
    "saturn-remedies": 'very large quote for "shani nivaran puja" packages',
    "pitru-dosh": 'very large quote for a "pitru dosh nivaran puja"',
    "rahu-mahadasha-career-problems": 'very large quote for "rahu shanti puja packages"',
    "10th-lord-in-6th-house-career": 'there is no such thing as "10th lord in 6th nivaran puja"',
    "saturn-in-10th-house-career": 'very large quote for "shani nivaran puja packages"',
    "chronic-health-issues-kundli": 'very large quote for "health nivaran puja" packages',
    "santan-prapti-children-in-kundli": 'very large quote for "santan prapti puja packages"',
    "pitru-dosh-remedies": "we hold no source for what a fair price is, so we give no figure",
}
_REGISTRY_MARKER3 = {
    "jupiter-remedies": "very large quote for a jupiter puja package",
    "saturn-remedies": "very large quote for a shani nivaran puja package",
    "marriage-delayed": "very large quote for a 'marriage nivaran puja'",
    "santan-prapti-children-in-kundli": "very large quote for a 'santan nivaran' ceremony",
    "chronic-health-issues-kundli": "be cautious of anyone promising a cure",
    "pitru-dosh": "be cautious of a very large puja quote",
    "pitru-dosh-remedies": "we hold no source for what a pitru dosh puja should cost",
}


@pytest.mark.parametrize("slug", _R3_PAGES)
def test_rendered_round3_page_carries_no_price_or_motive_claim(client, slug):
    assert _hits(_visible(client, slug), _BANNED_RE_R3_PAGE) == [], slug


@pytest.mark.parametrize("slug", _R3_REGISTRY)
def test_registry_round3_entry_carries_no_price_or_motive_claim(slug):
    assert _hits(_registry_text(slug, _R3_FIELDS), _BANNED_RE_R3) == [], slug


@pytest.mark.parametrize("slug", _R3_PAGES)
def test_round3_page_says_what_we_hold_about_price(client, slug):
    assert _MARKER3[slug] in _norm(_visible(client, slug)), slug


@pytest.mark.parametrize("slug", _R3_REGISTRY)
def test_round3_registry_entry_keeps_its_caution(slug):
    assert _REGISTRY_MARKER3[slug] in _norm(_registry_text(slug, _R3_FIELDS)), slug


# Safety messages the rewrite must keep. These turn red if a rewrite deletes the caution instead of
# the price or motive claim.
def test_chronic_health_page_keeps_the_medical_care_warning(client):
    n = _norm(_visible(client, "chronic-health-issues-kundli"))
    assert "neither is optional" in n
    assert "do not skip medical care" in n
    assert "skipping medical care is not something our guidance supports" in n


def test_santan_prapti_page_keeps_the_medical_care_warning(client):
    assert "do not skip medical care" in _norm(_visible(client, "santan-prapti-children-in-kundli"))


def test_saturn_remedies_keeps_the_rao_quote_and_the_blue_sapphire_caution(client):
    n = _norm(_visible(client, "saturn-remedies"))
    assert "those who have no belief in vedic remedies may skip this chapter" in n
    assert "blue sapphire without a proper chart consultation" in n


def test_rahu_mahadasha_page_keeps_the_hessonite_caution(client):
    n = _norm(_visible(client, "rahu-mahadasha-career-problems"))
    assert "hessonite" in n
    assert "without prior chart consultation" in n


def test_chronic_health_registry_keeps_the_never_replace_medical_care_line():
    n = _norm(_registry_text("chronic-health-issues-kundli", _R3_FIELDS))
    assert "never replace medical care" in n


def test_marriage_delayed_registry_keeps_the_gemstone_caution():
    n = _norm(_registry_text("marriage-delayed", _R3_FIELDS))
    assert "gemstones should never be worn without proper chart consultation" in n


def test_saturn_registry_does_not_put_a_paraphrase_in_raos_mouth():
    # remedies.md quotes Rao on belief only ("may skip this chapter"); "devotional acts, not
    # transactional payments" was the repo's own sentence, printed in quotation marks and attributed.
    n = _norm(_registry_text("saturn-remedies", _R3_FIELDS))
    assert "from rao: '" not in n
    # The sentence may stay, but only as the site's own reading.
    assert n.count("devotional acts, not transactional payments") == n.count(
        "in our reading, remedies are devotional acts, not transactional payments")
