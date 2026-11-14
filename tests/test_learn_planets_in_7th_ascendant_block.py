"""#990: the per-Ascendant list on /learn/planets-in-7th-house-marriage/ gets its sign arithmetic right.

Before: "Taurus or Libra Ascendant, Venus in 7th: Venus is in his own sign in his own house -- the most powerful
Malavya Yoga configuration". The 7th from Taurus is Scorpio and from Libra is Aries, so Venus is in neither an own
sign nor Pisces (exalted), and no Malavya forms (vedic_reference.md section 4.1: own sign or exalted AND in a kendra).
The true case is the Aries or Scorpio Ascendant, whose 7th is Libra or Taurus. The Mars line beside it gave the reason
"a friendly sign of his own dispositor's mirror", which means nothing; vedic_reference.md section 1.3 rule 5 lists
Mars in a Venus sign (Taurus, Libra) as MITIGATING (not cancelling), and section 1.6 records that the cancellation
family is contested.

These are a phrase test and a sign-arithmetic test on the rendered route. They catch the wordings they name and any
bullet whose stated 7th-house sign does not follow from its Ascendant; they are not a proof of every wording in the
list, and they do not judge the astrology (the functional-malefic claims in the other bullets are not sourced here).
"""
from __future__ import annotations

import re

SLUG = "planets-in-7th-house-marriage"

# Zodiac order: the 7th house from sign i is sign (i + 6) % 12.
_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
          "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_OWN = {  # own-sign rulerships (the two-sign planets only; Sun and Moon own one sign each)
    "Mars": {"Aries", "Scorpio"}, "Venus": {"Taurus", "Libra"}, "Mercury": {"Gemini", "Virgo"},
    "Jupiter": {"Sagittarius", "Pisces"}, "Saturn": {"Capricorn", "Aquarius"},
}


def _seventh(sign: str) -> str:
    return _SIGNS[(_SIGNS.index(sign) + 6) % 12]


def _plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _bullets(client) -> list[tuple[str, str]]:
    """The per-Ascendant <li> items as (bold lead-in, plain text of the whole item)."""
    r = client.get(f"/learn/{SLUG}/")
    assert r.status_code == 200
    start = r.text.index("Per-Ascendant shifts")
    end = r.text.index("Reading the 7th house honestly")
    items = re.findall(r"<li>(.*?)</li>", r.text[start:end], flags=re.S)
    assert len(items) == 6, f"the per-Ascendant list should have 6 bullets, found {len(items)}"
    out = []
    for it in items:
        lead = re.search(r"<strong>(.*?)</strong>", it, flags=re.S).group(1)
        out.append((_plain(lead), _plain(it)))
    return out


def _bullet(client, lead_prefix: str) -> str:
    hits = [t for lead, t in _bullets(client) if lead.startswith(lead_prefix)]
    assert len(hits) == 1, f"expected exactly one bullet starting {lead_prefix!r}, found {len(hits)}"
    return hits[0]


def _ascendants(lead: str) -> list[str]:
    m = re.match(r"((?:[A-Z][a-z]+)(?: or [A-Z][a-z]+)?) Ascendant", lead)
    assert m, f"bullet lead-in does not start 'X [or Y] Ascendant': {lead!r}"
    return m.group(1).split(" or ")


def _planet(lead: str) -> str:
    return re.search(r"(\w+) in 7th", lead).group(1)


def test_false_taurus_libra_venus_claim_is_gone(client):
    r = client.get(f"/learn/{SLUG}/")
    text = _plain(r.text)
    assert "Taurus or Libra Ascendant, Venus in 7th" not in text
    assert not any(lead.startswith("Taurus or Libra Ascendant") for lead, _ in _bullets(client))


def test_venus_line_is_the_aries_or_scorpio_case_and_names_malavya(client):
    t = _bullet(client, "Aries or Scorpio Ascendant, Venus in 7th")
    assert "Malavya" in t
    assert "Libra" in t and "Taurus" in t
    assert "kendra" in t
    # §4.1 lists beauty, luxury, art, marital happiness; the unsourced ranking is not kept.
    assert "marital happiness" in t
    for banned in ("most powerful", "exceptional marriage prosperity"):
        assert banned not in t


def test_venus_is_not_called_his_anywhere_in_the_block(client):
    for lead, t in _bullets(client):
        if "Venus" in lead:
            assert "his own" not in t, t
            assert "her own sign" in t, t
    assert "in his own sign in his own house" not in _plain(client.get(f"/learn/{SLUG}/").text)


def test_meaningless_dispositor_mirror_reason_is_gone(client):
    t = _plain(client.get(f"/learn/{SLUG}/").text)
    assert "dispositor's mirror" not in t
    assert "dispositor’s mirror" not in t
    assert "significantly softened" not in _bullet(client, "Aries or Scorpio Ascendant, Mars in 7th")


def test_mars_line_gives_the_supported_reason_and_stays_a_mitigation(client):
    t = _bullet(client, "Aries or Scorpio Ascendant, Mars in 7th")
    assert "Venus" in t and "Libra" in t and "Taurus" in t
    assert "mitigate" in t and "at least softened" in t
    # §1.3 rule 4: Mars in a movable sign (Libra, the Aries Ascendant's 7th) cancels on some lists, so the
    # line must not say the reading is never removed (QA round 1 on #991) ...
    assert "not removed" not in t and "so the reading is removed" not in t
    assert "movable" in t and "Libra" in t and "on lists that" in t
    # ... and must not state the cancellation as the page's own verdict: it is qualified and contested.
    assert t.count("cancels") == 1 and "on lists that count movable signs Mars there cancels" in t
    assert "contested" in t  # §1.6: the cancellation family is disputed
    assert 'href="/learn/manglik-dosh/"' in client.get(f"/learn/{SLUG}/").text


def test_every_stated_7th_house_sign_follows_from_its_ascendant(client):
    """Derive the 7th sign from each named Ascendant and compare it with every sign the bullet states.

    Mentions of the Ascendant itself ('X Ascendant', 'a X one', a bare 'for X') are removed first. What is
    left must equal the derived 7th signs, in order, and where a bullet says the planet is in its OWN sign the
    derived signs must be that planet's own signs."""
    stated_any = 0
    for lead, text in _bullets(client):
        ascs = _ascendants(lead)
        assert all(a in _SIGNS for a in ascs), ascs
        derived = [_seventh(a) for a in ascs]
        body = re.sub(r"\b[A-Z][a-z]+ Ascendant\b", " ", text)
        body = re.sub(r"\ba [A-Z][a-z]+ one\b", " ", body)
        stated: list[str] = []
        for m in re.finditer(r"\b(" + "|".join(_SIGNS) + r")\b", body):
            # A bare mention of the Ascendant itself ("not a functional malefic for Cancer") is not a 7th claim.
            if m.group(1) not in stated and m.group(1) not in ascs:
                stated.append(m.group(1))
        if stated:
            stated_any += 1
            assert stated == derived, f"{lead!r}: 7th from {ascs} is {derived}, bullet states {stated}"
        planet = _planet(lead)
        if re.search(r"\b(his|her) own sign\b", body) and planet in _OWN:
            assert set(derived) <= _OWN[planet], f"{lead!r}: {derived} are not own signs of {planet}"
    assert stated_any >= 5, "the bullets that state a sign must be read, not skipped"


def test_arithmetic_helper_is_right():
    """Guard the helper itself, so the derivation above cannot drift into agreeing with a wrong bullet."""
    assert [_seventh(a) for a in ("Aries", "Scorpio", "Taurus", "Libra", "Cancer", "Leo", "Gemini", "Virgo")] == [
        "Libra", "Taurus", "Scorpio", "Aries", "Capricorn", "Aquarius", "Sagittarius", "Pisces"]
