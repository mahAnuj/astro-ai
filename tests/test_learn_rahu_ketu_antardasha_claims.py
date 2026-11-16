"""#993: /learn/rahu-mahadasha-ketu-antardasha/ stops attributing unsourced claims to 'the texts' and
'classical' interpretation.

`knowledge/*.md` holds the Vimshottari order and durations with Ketu 7 years and Rahu 18 years
(vedic_reference.md 5.1), the antardasha as the trigger inside the mahadasha backdrop (5.3), Rahu and Ketu as
mathematical shadow points always 180 degrees apart and Ketu's significations (grahas.md), the Rahu/Ketu
friendships and enmities (grahas.md), and Ketu's deity, gemstone and good deed (remedies.md section 5). It holds
NO description of Ketu antardasha inside Rahu mahadasha, no past-life framing, no Saturday donation / fast / Pitr
Tarpan for Ketu, and nothing for `tyaga` or a 'tenfold' return, and it does not call the two nodes enemies of each
other. The page's 'What the texts say' callout, 'perpetual enemies in classical Vedic terms', 'classical
interpretation', 'Classical remedies' and 'the texts say ... tenfold' therefore had nothing behind them (same
defect class as #978, #982 and #988).

The page now says so once, in a disclosure callout above the first section, and words the rest as practitioner
practice. Readings, headings, title and the Vimshottari arithmetic are unchanged.

Pinned through the real route, and on the registry fields the route renders (summary, FAQ answers -- the FAQ
lands in the page's JSON-LD) plus the llm_summary. A phrase test: it catches the wording it names, not every
possible rewording.
"""
from __future__ import annotations

import re

SLUG = "rahu-mahadasha-ketu-antardasha"

_BANNED = [
    "what the texts say",
    "classical vimshottari literature",
    "classical interpret",
    "classical remedies",
    "classical phrase",
    "the texts say",
    "perpetual enemies",
    "perpetual opposites",
    "classical vedic",
    "classically",
    "according to classical",
    "classical difficulty",
    "classical texts",
    "tenfold",
]
# The only 'classical' wording the page may keep: it DENIES an attribution.
_ALLOWED = ["not a quotation from a classical text"]


def _text(client) -> str:
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))


def _body(client) -> str:
    """Article body only: the page chrome ('Classical sources cited') is not what these tests are about."""
    t = _text(client)
    start = t.index("In short")
    end = t.index("They were the curriculum.") + 30
    return t[start:end]


def _article():
    from astro_ai.learn_registry import ARTICLES

    return next(a for a in ARTICLES if a.slug == SLUG)


def _registry_text() -> str:
    a = _article()
    return " ".join([a.summary, a.llm_summary] + [f["q"] + " " + f["a"] for f in a.faqs]).lower()


def test_disclosure_says_the_pairing_readings_are_practice_not_sourced(client):
    t = _text(client)
    assert "The sources we hold do not describe Ketu Antardasha inside Rahu Mahadasha" in t
    assert "how practitioners commonly describe it, not a quotation from a classical text" in t
    assert "is practice, not something those sources state" in t


def test_disclosure_comes_once_and_before_the_first_section(client):
    html = client.get(f"/learn/{SLUG}/").text
    assert html.count("What is sourced and what is practice") == 1
    assert html.index("What is sourced and what is practice") < html.index("The Rahu–Ketu axis: why this transition is special</h2>")


def test_disclosure_lists_what_the_sources_do_hold(client):
    """Each item traces to a knowledge file: Vimshottari order/durations (vedic_reference.md 5.1), antardasha as
    trigger (5.3), shadow points 180 degrees apart (grahas.md), Ketu significations (grahas.md), friendships
    (grahas.md), Ganesha / cat's eye / good deed (remedies.md 5)."""
    t = _text(client)
    for needle in (
        "the Vimshottari order and durations, with Ketu 7 years and Rahu 18 years",
        "the antardasha is the trigger that works inside the backdrop the mahadasha sets",
        "Rahu and Ketu are mathematical points rather than bodies, shadow planets that always sit 180 degrees apart",
        "Ketu signifies detachment, spirituality, moksha and hidden knowledge",
        "Rahu and Ketu are friendly with Venus and Saturn and enemies of the Sun, Moon and Mars",
        "Ketu is associated with Ganesha, its gemstone is cat's eye, and its listed good deed is meditation and supporting renunciates",
    ):
        assert needle in t, needle


def test_no_unsourced_reading_is_attributed_to_the_texts_or_classical_interpretation(client):
    t = _body(client).lower()
    for phrase in _ALLOWED:
        t = t.replace(phrase, "")
    for phrase in _BANNED:
        assert phrase not in t, phrase
    assert "classical" not in t
    assert not re.search(r"\btexts\b", t)


def test_the_nodes_oppose_each_other_but_are_not_called_enemies(client):
    t = _body(client)
    assert "the two ends of one axis, always 180 degrees apart, so they oppose each other across it" in t
    assert "enemies of each other" not in t.lower()


def test_unsourced_remedies_are_marked_and_sourced_ones_are_kept(client):
    t = _body(client)
    assert "the Saturday donation, the fast and Pitr Tarpan are common practice, not sourced" in t
    assert "a commonly suggested practice, not sourced" in t  # Saturday donation
    assert "Meditate and support renunciates" in t
    assert "Ganesh is the deity the sources we work from pair with Ketu" in t
    assert "Cat's eye gemstone (Lehsunia)" in t
    assert "never wear Ketu gems casually" in t
    assert "That is a saying, not a promise, and not something the sources we hold state." in t


def test_past_life_framing_says_it_is_practice(client):
    t = _body(client)
    assert "a past-life framing that is practice, not something the sources we hold state" in t


def test_the_vimshottari_arithmetic_is_kept(client):
    t = _body(client)
    assert "<" not in t
    assert "precisely 1 year, 0 months, 18 days by the Vimshottari proportions" in t
    assert "(7 × 18) / 120 = ~12.6 months" in t
    assert "roughly 10.5 years into the 18-year Rahu cycle" in t
    assert "the next Antardasha within Rahu Mahadasha is Venus — 3 years" in t
    assert (
        "Rahu/Rahu → Rahu/Jupiter → Rahu/Saturn → Rahu/Mercury → Rahu/Ketu → Rahu/Venus → Rahu/Sun → Rahu/Moon → Rahu/Mars"
        in t
    )


def test_page_keeps_its_headings_and_pullquote(client):
    r = client.get(f"/learn/{SLUG}/")
    for h in (
        "The Rahu–Ketu axis: why this transition is special",
        "What the 18-year Rahu Mahadasha actually feels like",
        "What the Ketu Antardasha brings, on top of all that",
        "The interaction: why this specific pair hits hardest",
        "What if Ketu is in the 11th house with Saturn?",
        "How long does this last?",
        "Remedies for Rahu Mahadasha + Ketu Antardasha",
        "What to actually do",
    ):
        assert f"<h2>{h}</h2>" in r.text, h
    assert "Ketu makes you stop asking, and notice what the real question was." in r.text


def test_registry_fields_carry_no_classical_attribution():
    t = _registry_text()
    for phrase in _BANNED:
        assert phrase not in t, phrase
    assert "classical" not in t
    assert not re.search(r"\btexts\b", t)


def test_registry_says_the_readings_are_practice():
    a = _article()
    assert "the sources we hold do not describe this pairing" in a.summary
    assert "practice, not sourced for this pairing" in a.llm_summary
    faq = {f["q"]: f["a"] for f in a.faqs}
    assert "a saying, not a promise or a sourced rule" in faq["What's the best remedy during Ketu Antardasha?"]
    assert "they oppose each other across the axis" in faq["Why is Rahu Mahadasha + Ketu Antardasha considered uniquely difficult?"]


def test_registry_keeps_the_arithmetic_and_every_faq_question():
    a = _article()
    assert "Precisely 1 year, 0 months, 18 days (~12.6 months)" in a.faqs[0]["a"]
    assert "(7 × 18) / 120 from the Vimshottari proportions" in a.faqs[0]["a"]
    assert [f["q"] for f in a.faqs] == [
        "How long does Ketu Antardasha inside Rahu Mahadasha last?",
        "What comes after Ketu Antardasha in Rahu Mahadasha?",
        "Why is Rahu Mahadasha + Ketu Antardasha considered uniquely difficult?",
        "If Ketu is in my 11th house with Saturn, what does this transition mean?",
        "What's the best remedy during Ketu Antardasha?",
    ]


def test_title_is_untouched_and_no_seo_override_was_added():
    a = _article()
    assert a.title == "Rahu Mahadasha + Ketu Antardasha: Surviving the Nodal Axis Flip"
    assert not getattr(a, "seo_title", "")
    assert not getattr(a, "seo_description", "")


# --- #1075: the 'effects' and 'remedies' intents are named in headings, with no new claim ---

_EFFECTS_H2 = "Effects of Rahu Mahadasha + Ketu Antardasha: what happens, at a glance"


def _effects_block(html: str) -> str:
    start = html.index(f"<h2>{_EFFECTS_H2}</h2>")
    end = html.index("<h2>The Rahu–Ketu axis: why this transition is special</h2>")
    return html[start:end]


def test_an_effects_heading_names_the_intent_and_sits_near_the_top(client):
    """The issue's own repro: an h2 containing 'effects' (was 0). It follows the disclosure and precedes the first section."""
    html = client.get(f"/learn/{SLUG}/").text
    assert len(re.findall(r"<h[23][^>]*>[^<]*effects", html, flags=re.I)) >= 1
    assert "what happens" in _EFFECTS_H2.lower()
    assert html.index("In short") < html.index("What is sourced and what is practice") < html.index(f"<h2>{_EFFECTS_H2}</h2>")
    assert html.index(f"<h2>{_EFFECTS_H2}</h2>") < html.index("<h2>The Rahu–Ketu axis: why this transition is special</h2>")


def test_effects_block_is_labelled_practitioner_reading_and_adds_no_source_claim(client):
    block = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _effects_block(client.get(f"/learn/{SLUG}/").text)))
    assert "how practitioners commonly describe the period, not something the sources we hold state" in block
    assert "(a practitioner reading)" in block
    low = block.lower()
    assert "classical" not in low
    assert not re.search(r"\btexts\b", low)
    for remedy_word in ("remed", "cat's eye", "gem", "mantra", "ganesh", "donat", "fast ", "tarpan", "puja", "meditat", "wear "):
        assert remedy_word not in low.replace("the remedies heading further down", ""), remedy_word


_EFFECT_PAIRS = (  # (as worded in the effects block, as the page already words it below), lower-cased
    ("projects can collapse", "projects can collapse"),
    ("money may become erratic", "money may become erratic"),
    ("ketu tends to loosen the grip on accumulation", "ketu tends to loosen the grip on accumulation"),
    ("loss of wealth", "loss of wealth"),
    ("relationships may end", "relationships may end"),
    ("separation", "separation"),
    ("identities loosen", "identities loosen"),
    ("foreign environments can turn unwelcoming", "foreign environments can turn unwelcoming"),
    ("sudden direction changes", "sudden direction changes"),
    ("strange dreams, sleep disturbance and psychological intensity", "strange dreams, sleep disturbance, psychological intensity"),
    ("deep doubt", "deep doubt, then deep clarity"),
    ("old addictions sometimes tighten before they are forced to break", "old addictions sometimes tighten before they're forced to break"),
    ("expansion", "sudden expansion"),
    ("foreign travel", "foreign travel"),
    ("obsessive interests", "obsessive interests"),
    ("boom-and-bust cycles", "boom-and-bust cycles"),
)


def test_every_effects_line_restates_a_sentence_the_page_already_makes(client):
    """The block summarises; it does not extend. Each reading it gathers must be in the block AND in the sections below it."""
    html = client.get(f"/learn/{SLUG}/").text
    flat = lambda h: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).lower()
    block = flat(_effects_block(html))
    below = flat(html[html.index("<h2>The Rahu–Ketu axis"):])
    for in_block, in_page in _EFFECT_PAIRS:
        assert in_block in block, in_block
        assert in_page in below, in_page


def test_effects_block_carries_exactly_the_seven_areas_and_no_other_bullet(client):
    """Adding an eighth claim must be a deliberate edit of this test, which is where the 'already on the page' check lives."""
    block = _effects_block(client.get(f"/learn/{SLUG}/").text)
    labels = re.findall(r"<li><strong>([^<]+)</strong>", block)
    assert labels == [
        "Work and money:", "Relationships:", "Place:", "Mind and sleep:", "Habits:", "The Rahu backdrop:", "How long:",
    ]
    assert block.count("<li>") == 7


def test_remedies_heading_uses_the_searchers_words_and_the_sourced_split_is_intact(client):
    html = client.get(f"/learn/{SLUG}/").text
    assert "<h2>Remedies for Rahu Mahadasha + Ketu Antardasha</h2>" in html
    assert "Remedies for surviving" not in html
    t = _body(client)
    assert "Ganesha, meditation and the cat's eye caution below are in the sources we hold; the Saturday donation, the fast and Pitr Tarpan are common practice, not sourced" in t


def test_head_query_surfaces_are_untouched_and_no_section_was_cut(client):
    """Title, H1 source, meta and the opening callout stay; the effects block adds a section and removes none."""
    a = _article()
    assert a.title == "Rahu Mahadasha + Ketu Antardasha: Surviving the Nodal Axis Flip"
    assert not getattr(a, "seo_title", "") and not getattr(a, "seo_description", "")
    assert "the nodal axis flip" in _text(client).lower()
    html = client.get(f"/learn/{SLUG}/").text
    assert html.count("<h2>") == 9  # 8 article sections before; the block adds one and cuts none
