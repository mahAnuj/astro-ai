"""#1341 (R1 of #1017, closes #1339): the finder ranks within a tier by score and names a top pick.

`MuhuratCandidate.score` carries the soft-scoring points behind the rating, the sort key is
`(tier, verdict_rank, -score, date)` (the verdict only in couple mode, #1344), and `top_pick` names the first valid row: an excellent/good/acceptable
day that, in couple mode, is not a verdict of "avoid". A booster- or Abujha-lifted day carries its
tier's floor as its score; no weight, cut-off or exclusion changed (the sweep below pins that
the rating is still a pure function of the points for every day nothing lifted).

The Range select must show the days that were searched (#1339): `prefill_days` is the clamped
value on a result and the raw value on an error re-render. The template is the frontend's half;
this file reads the route's context.

No network (geocoding is stubbed) and no LLM. Mutation rows:
scripts/mutations/2026_11_21_1341_muhurat_top_pick.py.
"""
from __future__ import annotations

import dataclasses
import html as _htmllib
import re
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from astro_ai import muhurat
from astro_ai.muhurat import MuhuratCandidate, _RATING_MIN_SCORE, rank_key, top_pick

CITY = "Delhi, India"
DELHI = (28.61, 77.21, "Asia/Kolkata")
TODAY = date(2026, 11, 21)
START = date(2026, 11, 22)
EVENTS = ["vivah", "griha_pravesh", "vidyarambh", "namkaran", "business"]


@pytest.fixture(autouse=True)
def _pinned(monkeypatch):
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    monkeypatch.setattr(chart, "geocode_place", lambda place: DELHI)
    monkeypatch.setattr(route, "reading_today", lambda: TODAY)


def _row(d: date, rating: str, score: int, verdict: str | None = None) -> MuhuratCandidate:
    """A candidate with only what ranking reads. `couple` is a stand-in: `top_pick` reads
    `combined_verdict` and nothing else of it."""
    return MuhuratCandidate(
        d=d, weekday=d.strftime("%A"), tithi="Panchami", tithi_paksha="Shukla",
        nakshatra="Rohini", rating=rating, reason="fixture", flags=(), score=score,
        couple=SimpleNamespace(combined_verdict=verdict) if verdict else None)


def _ranked(rows):
    return sorted(rows, key=rank_key)


@pytest.fixture
def ctx(monkeypatch):
    """The template context of every finder render, in order. The route's TemplateResponse is
    wrapped, not replaced, so the page still renders; the frontend's half of #1339 (the select
    itself) is not asserted here."""
    from astro_ai.routes.deps import templates

    seen: list[dict] = []
    real = templates.TemplateResponse

    def recording(request, name, context=None, *a, **k):
        if name == "muhurat_finder.html":
            seen.append(context)
        return real(request, name, context, *a, **k)

    monkeypatch.setattr(templates, "TemplateResponse", recording)
    return seen


# --- (a) the higher score wins inside a tier, even when it is later ----------------------


def test_the_higher_scoring_excellent_day_is_the_pick_even_when_later():
    early, late = _row(date(2026, 12, 1), "excellent", 5), _row(date(2026, 12, 9), "excellent", 6)
    pick, ties = top_pick(_ranked([early, late]))
    assert pick is late and ties == 0
    assert _ranked([early, late])[0] is late


def test_tier_still_outranks_score():
    # A "good" 4 never outranks an "excellent" 5: the tier is the first key element.
    good, excellent = _row(date(2026, 12, 1), "good", 4), _row(date(2026, 12, 9), "excellent", 5)
    assert top_pick(_ranked([good, excellent]))[0] is excellent


def test_the_pick_is_the_first_valid_row_of_the_ranked_list():
    rows = _ranked([_row(date(2026, 12, 1), "caution", 2), _row(date(2026, 12, 2), "good", 4),
                    _row(date(2026, 12, 3), "excellent", 6), _row(date(2026, 12, 4), "avoid", 0)])
    assert top_pick(rows)[0] is rows[0]


def test_a_real_window_has_a_later_higher_scoring_excellent_day_and_the_pick_is_it():
    # Vidyarambh from 2026-11-22: 11-25 is the first excellent by date and only reaches the
    # excellent floor through a booster (score 5); 11-26 scores 6 from the soft factors alone.
    rows = muhurat.find_candidates("vidyarambh", CITY, START, 90)
    excellent = sorted((c for c in rows if c.rating == "excellent"), key=lambda c: c.d)
    first_by_date = excellent[0]
    best = max(excellent, key=lambda c: c.score)
    assert best.d > first_by_date.d and best.score > first_by_date.score, \
        "premise: a later excellent day outscores the first one by date"
    pick, _ties = top_pick(rows)
    assert pick.d != first_by_date.d
    assert pick.score == best.score
    assert pick.d == min(c.d for c in excellent if c.score == best.score)
    assert rows[0] is pick  # no caution/avoid-only reordering: the ranked head is the pick


@pytest.mark.parametrize("event", EVENTS)
def test_the_pick_equals_the_first_valid_row_of_the_real_ranked_list(event):
    rows = muhurat.find_candidates(event, CITY, START, 90)
    first_valid = next(c for c in rows if c.rating in muhurat.AUSPICIOUS_RATINGS)
    assert top_pick(rows)[0] is first_valid


# --- (b) eligibility and ties -----------------------------------------------------------


def test_a_couple_avoid_day_is_never_the_pick_but_stays_in_the_list():
    avoid_pair = _row(date(2026, 12, 1), "excellent", 7, verdict="avoid")
    ok_pair = _row(date(2026, 12, 9), "good", 4, verdict="good-for-both")
    rows = _ranked([avoid_pair, ok_pair])
    assert avoid_pair in rows and rows[0] is avoid_pair  # still listed, still ranked first
    assert top_pick(rows)[0] is ok_pair


def test_a_mixed_couple_verdict_is_still_eligible():
    mixed = _row(date(2026, 12, 1), "excellent", 5, verdict="mixed")
    assert top_pick([mixed])[0] is mixed


def test_all_couple_avoid_gives_no_pick():
    rows = [_row(date(2026, 12, 1), "excellent", 6, verdict="avoid"),
            _row(date(2026, 12, 2), "good", 4, verdict="avoid")]
    assert top_pick(rows) == (None, 0)


def test_caution_only_avoid_only_and_empty_give_no_pick():
    assert top_pick([]) == (None, 0)
    assert top_pick([_row(date(2026, 12, 1), "caution", 2)]) == (None, 0)
    assert top_pick([_row(date(2026, 12, 1), "avoid", 0)]) == (None, 0)
    assert top_pick([_row(date(2026, 12, 1), "caution", 2),
                     _row(date(2026, 12, 2), "avoid", 0)]) == (None, 0)


def test_a_caution_row_is_never_the_pick_when_a_valid_row_exists():
    rows = _ranked([_row(date(2026, 12, 1), "caution", 2), _row(date(2026, 12, 20), "acceptable", 3)])
    assert top_pick(rows)[0].rating == "acceptable"


def test_ties_pick_the_earliest_and_count_the_others():
    rows = _ranked([_row(date(2026, 12, 9), "excellent", 5), _row(date(2026, 12, 1), "excellent", 5),
                    _row(date(2026, 12, 5), "excellent", 5), _row(date(2026, 12, 2), "excellent", 6),
                    _row(date(2026, 12, 3), "excellent", 6), _row(date(2026, 12, 4), "good", 4)])
    pick, ties = top_pick(rows)
    assert pick.d == date(2026, 12, 2) and ties == 1  # the other score-6 day only


def test_a_couple_avoid_day_does_not_count_as_a_tie():
    rows = _ranked([_row(date(2026, 12, 1), "excellent", 5),
                    _row(date(2026, 12, 2), "excellent", 5, verdict="avoid"),
                    _row(date(2026, 12, 3), "excellent", 5)])
    pick, ties = top_pick(rows)
    assert pick.d == date(2026, 12, 1) and ties == 1


# --- (c) the 3-tuple, the default, and the rating-from-points invariant ------------------


def test_score_event_still_returns_the_three_tuple():
    out = muhurat.score_event(
        "vidyarambh", SimpleNamespace(tithi_name="Panchami", tithi_paksha="Shukla"),
        "Thursday", "Pushya", False, False, "", "", {})
    assert isinstance(out, tuple) and len(out) == 3
    assert out[0] in ("excellent", "good", "acceptable", "caution")


def test_a_candidate_built_without_a_score_defaults_to_zero():
    c = MuhuratCandidate(d=TODAY, weekday="Saturday", tithi="Panchami", tithi_paksha="Shukla",
                         nakshatra="Rohini", rating="good", reason="r", flags=())
    assert c.score == 0
    assert dataclasses.fields(MuhuratCandidate)[-1].name == "score"


def test_the_cutoffs_table_is_best_first_and_matches_the_documented_cutoffs():
    assert list(_RATING_MIN_SCORE.items()) == [("excellent", 5), ("good", 4), ("acceptable", 3)]


@pytest.fixture(scope="module")
def sweep():
    from astro_ai import chart

    # chart.geocode_place is patched per test by _pinned; the module fixture needs the same stub
    # without function-scoped monkeypatch, so it patches by hand and restores.
    real = chart.geocode_place
    chart.geocode_place = lambda place: DELHI
    try:
        return {ev: muhurat.find_candidates(ev, CITY, date(2026, 11, 22), 365) for ev in EVENTS}
    finally:
        chart.geocode_place = real


@pytest.mark.parametrize("event", EVENTS)
def test_sweep_the_rating_is_still_a_pure_function_of_the_points_unless_lifted(sweep, event):
    rows = sweep[event]
    assert len(rows) == 365
    plain = lifted = avoided = 0
    for c in rows:
        if c.rating == "avoid":
            assert c.score == 0, c
            avoided += 1
        elif c.boosters or "abujha_muhurat" in c.flags:
            floor = _RATING_MIN_SCORE.get(c.rating, 0)
            assert c.score >= floor, c
            lifted += 1
        else:
            derived = next((r for r, f in _RATING_MIN_SCORE.items() if c.score >= f), "caution")
            assert c.rating == derived, c
            plain += 1
    assert plain and avoided, "premise: the sweep reached both plain and avoided days"
    assert [rank_key(c) for c in rows] == sorted(rank_key(c) for c in rows)


def test_sweep_reaches_a_lifted_day_somewhere(sweep):
    # Guards the sweep's lifted branch from being vacuous across all five events.
    assert any(c.boosters or "abujha_muhurat" in c.flags for rows in sweep.values() for c in rows)


def test_an_abujha_day_carries_the_excellent_floor():
    # 2028-04-27 (Akshaya Tritiya) is an Abujha date that clears every hard exclusion for
    # business, where Abujha lifts acceptable to excellent (#1346). Vivah on 2027-02-11 is now
    # `avoid` (Panchak), so it no longer reaches the booster.
    rows = muhurat.find_candidates("business", CITY, date(2028, 4, 26), 3)
    abujha = [c for c in rows if "abujha_muhurat" in c.flags]
    assert abujha, "premise: 2028-04-27 is an Abujha date business does not exclude"
    assert all(c.rating == "excellent" and c.score >= _RATING_MIN_SCORE["excellent"] for c in abujha)


# --- the Range select shows the searched days (#1339) -------------------------------------


def test_a_get_with_days_14_puts_14_in_the_context(client, ctx):
    r = client.get("/muhurat", params={"event": "vivah", "city": CITY,
                                       "start": START.isoformat(), "days": 14})
    assert r.status_code == 200
    assert ctx[-1]["prefill_days"] == 14


def test_prefill_days_is_the_clamped_value(client, ctx):
    r = client.get("/muhurat", params={"event": "vivah", "city": CITY,
                                       "start": START.isoformat(), "days": 400})
    assert ctx[-1]["prefill_days"] == 365


def test_a_post_reports_the_days_it_searched(client, ctx):
    r = client.post("/muhurat", data={"event_type": "vivah", "city": CITY,
                                      "start_date": START.isoformat(), "days": "30"})
    assert ctx[-1]["prefill_days"] == 30


def test_error_re_renders_keep_the_requested_days(client, ctx):
    base = {"event": "vivah", "city": CITY, "start": START.isoformat(), "days": 14}
    for override in ({"event": "nope"}, {"start": "not-a-date"}, {"city": "x" * 101}):
        r = client.get("/muhurat", params={**base, **override})
        assert r.status_code == 400
        assert ctx[-1]["prefill_days"] == 14, override


def test_a_failed_search_keeps_the_requested_days(client, ctx, monkeypatch):
    from astro_ai.routes import muhurat as route

    def boom(*a, **k):
        raise ValueError("no such city")

    monkeypatch.setattr(route, "_search", boom)
    r = client.get("/muhurat", params={"event": "vivah", "city": CITY,
                                       "start": START.isoformat(), "days": 14})
    assert r.status_code == 500
    assert ctx[-1]["prefill_days"] == 14


def test_the_route_hands_the_template_the_pick(client, ctx):
    r = client.get("/muhurat", params={"event": "vidyarambh", "city": CITY,
                                       "start": START.isoformat(), "days": 90})
    pick = ctx[-1]["top_pick"]
    assert pick is not None and pick.d == date(2026, 11, 26)
    assert isinstance(ctx[-1]["top_pick_ties"], int)


def test_a_bare_form_has_no_pick(client, ctx):
    r = client.get("/muhurat")
    assert r.status_code == 200
    assert "top_pick" not in ctx[-1]


# --- the template: the card and the Range select as the visitor gets them (#1341, #1339) --------

DISCLOSURE = ("Among dates of the same grade, this card goes first to the one with the most points "
              "under this site's own point count: the classical rules fix which dates qualify, but "
              "the tradition we follow gives no weighting between them.")
COUPLE_DISCLOSURE = ("Among dates of the same grade, this card goes first to a date this finder marks "
                     "good for both partners, ahead of a mixed one, and then to the one with the "
                     "most points. Both orders are this site's own convention: the classical rules "
                     "fix which dates qualify, but the tradition we follow gives no ranking between "
                     "them.")
COUPLE = {"bride_name": "Sita Verma", "bride_dob": "1995-03-04", "bride_time": "06:30",
          "bride_place": "Jaipur, India", "groom_name": "Ram Verma", "groom_dob": "1993-07-19",
          "groom_time": "11:15", "groom_place": "Lucknow, India"}


def _fmt(d: date) -> str:
    return d.strftime("%b %d, %Y")


def _get(client, event="vidyarambh", days=90, start=START, **extra):
    return client.get("/muhurat", params={"event": event, "city": CITY, "start": start.isoformat(),
                                          "days": days, **extra})


def _post(client, event="vidyarambh", days=90, start=START, **extra):
    return client.post("/muhurat", data={"event_type": event, "city": CITY,
                                         "start_date": start.isoformat(), "days": str(days), **extra})


def _card(h: str) -> str:
    m = re.search(r'<div id="top-pick".*?</p>\s*</div>', h, re.S)
    return m.group(0) if m else ""


def _card_text(h: str) -> str:
    return re.sub(r"\s+", " ", _htmllib.unescape(re.sub(r"<[^>]+>", " ", _card(h)))).strip()


def _first_table_date(h: str) -> str:
    table = re.search(r"<table.*?</table>", h, re.S).group(0)
    return re.search(r'data-label="Date"[^>]*>([^<]+)<', table).group(1).strip()


def _days_options(h: str) -> list[tuple[str, bool, str]]:
    sel = re.search(r'<select name="days" id="days".*?</select>', h, re.S).group(0)
    return [(v, "selected" in attrs, label.strip())
            for v, attrs, label in re.findall(r'<option value="(\d+)"([^>]*)>([^<]*)</option>', sel)]


@pytest.mark.parametrize("how", [_get, _post])
@pytest.mark.parametrize("event", EVENTS)
def test_the_rendered_top_pick_is_the_ranked_head_and_the_first_table_row(client, how, event):
    r = how(client, event)
    assert r.status_code == 200
    rows = muhurat.find_candidates(event, CITY, START, 90)
    pick, _ties = top_pick(rows)
    card = _card_text(r.text)
    assert card.startswith("Top pick"), card
    assert f"{pick.weekday}, {_fmt(pick.d)}" in card
    assert _first_table_date(r.text) == _fmt(pick.d)
    assert r.text.count('id="top-pick"') == 1


def test_the_card_names_tithi_paksha_nakshatra_rating_and_reason(client):
    r = _get(client)
    pick, _ = top_pick(muhurat.find_candidates("vidyarambh", CITY, START, 90))
    card = _card_text(r.text)
    reason = pick.reason[:1].upper() + pick.reason[1:] + "."
    for needle in (f"{pick.tithi_paksha} {pick.tithi}", pick.nakshatra, pick.rating, reason):
        assert needle in card, needle


def test_the_card_never_prints_the_score_and_never_says_best(client):
    r = _get(client)
    card = _card(r.text)
    pick, _ = top_pick(muhurat.find_candidates("vidyarambh", CITY, START, 90))
    assert "best" not in card.lower()
    assert "score" not in card.lower()
    assert not re.search(rf"\b{pick.score}\s*(points|pts)", _card_text(r.text))


@pytest.mark.parametrize("event", EVENTS)
def test_the_disclosure_is_always_in_the_card(client, event):
    assert DISCLOSURE in _card_text(_get(client, event).text)


@pytest.mark.parametrize("event", EVENTS)
def test_the_tie_line_is_the_route_count_and_only_when_there_are_ties(client, ctx, event):
    r = _get(client, event)
    ties = ctx[-1]["top_pick_ties"]
    card = _card_text(r.text)
    if ties:
        word = "date" if ties == 1 else "dates"
        assert f"Tied on points with {ties} other {word}; earliest first." in card
    else:
        assert "Tied on points" not in card


def test_a_pick_that_won_on_order_alone_says_so(client, ctx):
    # griha_pravesh over 90 days: every excellent day scores 5 (decision doc), so the pick ties.
    r = _get(client, "griha_pravesh")
    assert ctx[-1]["top_pick_ties"] > 0, "premise: the pick has tied days"
    assert "earliest first" in _card_text(r.text)


def test_a_booster_pick_shows_the_boost_badge(client, ctx):
    for event in EVENTS:
        r = _get(client, event, 180)
        pick = ctx[-1]["top_pick"]
        if pick.boosters:
            assert "★ boost" in _card(r.text)
            return
    pytest.skip("no event's pick carries a booster in this window")


def test_no_card_for_a_window_with_no_auspicious_date(client):
    r = _get(client, "griha_pravesh", 20, start=date(2026, 12, 20))
    assert r.status_code == 200
    assert "No auspicious dates found in this window" in r.text
    assert 'id="top-pick"' not in r.text and "Top pick" not in r.text
    assert "no top pick is shown" not in r.text


def test_no_card_on_the_bare_form(client):
    r = client.get("/muhurat")
    assert 'id="top-pick"' not in r.text and "Top pick" not in r.text


def _all_couple_avoid(monkeypatch):
    real = muhurat.find_candidates

    def fake(*a, **k):
        return [dataclasses.replace(c, couple=dataclasses.replace(c.couple, combined_verdict="avoid"))
                if c.couple else c for c in real(*a, **k)]

    monkeypatch.setattr(muhurat, "find_candidates", fake)


def test_a_couple_search_shows_the_verdict_and_the_not_an_endorsement_line(client):
    r = _post(client, "vivah", 180, **COUPLE)
    assert "Couple</th>" in r.text, "premise: couple mode was active"
    card = _card_text(r.text)
    assert "Couple verdict:" in card
    assert "It is not a classical endorsement for your two charts." in card
    assert "own both-partners rule (explained below)" in card
    assert "Dates marked avoid for the couple are skipped here" in card
    assert COUPLE_DISCLOSURE in card
    assert DISCLOSURE not in card  # the non-couple sentence is replaced, not stacked
    assert "Tied on points" not in card  # a couple's tie line names the verdict as well
    # The pick is the first table row whose couple verdict is not "avoid" (a couple-avoid row
    # stays in the table, so it may sit above the pick; sorting within a tier now puts one below
    # a mixed or good-for-both row, so there is no fixed date to name here).
    table = re.search(r"<table.*?</table>", r.text, re.S).group(0)
    rows = re.findall(r'data-label="Date"[^>]*>([^<]+)<.*?title="Combined bride\+groom verdict">'
                      r'\s*([^<]+?)\s*<', table, re.S)
    first_ok = next(d for d, verdict in rows if verdict != "avoid")
    assert first_ok in card


def test_a_basic_search_has_no_couple_line(client):
    assert "Couple verdict" not in _card_text(_get(client, "vivah", 180).text)


def test_every_date_couple_avoid_says_so_and_shows_no_card(client, monkeypatch):
    _all_couple_avoid(monkeypatch)
    r = _post(client, "vivah", 180, **COUPLE)
    assert "Couple</th>" in r.text, "premise: couple mode was active"
    assert "Every date in this range is marked avoid for the couple, so no top pick is shown." in r.text
    assert 'id="top-pick"' not in r.text and "Top pick" not in r.text


# --- the Range select (#1339) ----------------------------------------------------------------


@pytest.mark.parametrize("how", [_get, _post])
@pytest.mark.parametrize("days", [14, 30, 60, 90, 180, 365, 1000])
def test_the_range_select_shows_the_days_searched(client, how, days):
    opts = _days_options(how(client, "vidyarambh", days).text)
    chosen = [v for v, sel, _ in opts if sel]
    assert chosen == [str(min(days, 365))]
    values = [v for v, _, _ in opts]
    assert len(values) == len(set(values)), "a standard value is listed twice"
    assert values == sorted(values, key=int)
    assert {"30", "60", "90", "180"} <= set(values)


def test_the_standard_labels_are_unchanged_and_an_odd_value_is_labelled_in_days(client):
    labels = {v: label for v, _, label in _days_options(_get(client, "vidyarambh", 14).text)}
    assert labels == {"14": "14 days", "30": "30 days", "60": "60 days", "90": "90 days",
                      "180": "6 months"}
    assert {v: label for v, _, label in _days_options(_get(client, "vidyarambh", 1).text)}["1"] == "1 day"


def test_a_bare_form_defaults_to_sixty(client):
    opts = _days_options(client.get("/muhurat").text)
    assert [(v, label) for v, sel, label in opts if sel] == [("60", "60 days")]
    assert [v for v, _, _ in opts] == ["30", "60", "90", "180"]


def test_the_next_date_link_lands_on_a_form_that_shows_the_same_range(client):
    start = date(2026, 12, 20)
    r = _get(client, "griha_pravesh", 20, start=start)
    link = re.search(r'href="([^"]+)" class="underline">[A-Z][a-z]+, ', r.text)
    assert link, "premise: the zero-result page links the next auspicious date"
    from urllib.parse import parse_qs, urlparse
    q = parse_qs(urlparse(_htmllib.unescape(link.group(1))).query)
    assert q["days"] == ["20"]
    followed = client.get(_htmllib.unescape(link.group(1)))
    chosen = [v for v, sel, _ in _days_options(followed.text) if sel]
    assert chosen == ["20"]


def test_an_error_re_render_keeps_the_searched_days_selected(client, monkeypatch):
    from astro_ai.routes import muhurat as route

    def boom(*a, **k):
        raise ValueError("no such city")

    monkeypatch.setattr(muhurat, "find_candidates", boom)
    for how in (_get, _post):
        r = how(client, "vidyarambh", 14)
        assert r.status_code == 500
        assert [v for v, sel, _ in _days_options(r.text) if sel] == ["14"]
    assert route  # the route module is the one the client drives


def test_a_bad_request_re_render_keeps_the_searched_days_selected(client):
    r = _get(client, "nope", 90 * 2)
    assert r.status_code == 400
    assert [v for v, sel, _ in _days_options(r.text) if sel] == ["180"]
    r = client.get("/muhurat", params={"event": "vivah", "city": CITY, "start": "bad", "days": 14})
    assert r.status_code == 400
    assert [v for v, sel, _ in _days_options(r.text) if sel] == ["14"]
    r = client.get("/muhurat", params={"event": "nope", "city": CITY, "start": START.isoformat(), "days": 1000})
    assert r.status_code == 400
    # Out of range on an error re-render (the route does not clamp there): the form falls back to 60.
    assert [(v, label) for v, sel, label in _days_options(r.text) if sel] == [("60", "60 days")]
    assert [v for v, _, _ in _days_options(r.text)] == ["30", "60", "90", "180"]


# --- #1344: in couple mode the combined verdict ranks inside a tier -------------------------


def test_within_a_tier_good_for_both_ranks_before_mixed_even_when_later_and_lower_scoring():
    early_mixed = _row(date(2026, 12, 1), "excellent", 5, verdict="mixed")
    late_gfb = _row(date(2026, 12, 20), "excellent", 5, verdict="good-for-both")
    high_mixed = _row(date(2026, 12, 2), "excellent", 6, verdict="mixed")
    rows = _ranked([early_mixed, high_mixed, late_gfb])
    assert rows[0] is late_gfb
    assert top_pick(rows)[0] is late_gfb


def test_verdict_order_is_excellent_good_mixed_avoid():
    d = date(2026, 12, 1)
    rows = [_row(d + timedelta(days=i), "excellent", 5, verdict=v)
            for i, v in enumerate(["avoid", "mixed", "good-for-both", "excellent-for-both"])]
    assert [c.couple.combined_verdict for c in _ranked(rows)] == [
        "excellent-for-both", "good-for-both", "mixed", "avoid"]


def test_tier_still_outranks_the_verdict():
    gfb_good = _row(date(2026, 12, 1), "good", 4, verdict="good-for-both")
    mixed_excellent = _row(date(2026, 12, 20), "excellent", 5, verdict="mixed")
    rows = _ranked([gfb_good, mixed_excellent])
    assert rows[0] is mixed_excellent
    assert top_pick(rows)[0] is mixed_excellent


def test_non_couple_rows_rank_zero_for_the_verdict():
    rows = [_row(date(2026, 12, 9), "excellent", 5), _row(date(2026, 12, 1), "good", 4),
            _row(date(2026, 12, 5), "excellent", 6), _row(date(2026, 12, 3), "excellent", 5),
            _row(date(2026, 12, 4), "caution", 2)]
    assert all(rank_key(c)[1] == 0 for c in rows)
    old = sorted(rows, key=lambda c: (muhurat._TIER_ORDER.get(c.rating, 99), -c.score, c.d))
    assert _ranked(rows) == old


def test_a_tie_counts_only_the_same_verdict():
    rows = _ranked([_row(date(2026, 12, 1), "excellent", 5, verdict="mixed"),
                    _row(date(2026, 12, 2), "excellent", 5, verdict="mixed"),
                    _row(date(2026, 12, 3), "excellent", 5, verdict="mixed"),
                    _row(date(2026, 12, 10), "excellent", 5, verdict="good-for-both"),
                    _row(date(2026, 12, 11), "excellent", 5, verdict="good-for-both")])
    pick, ties = top_pick(rows)
    assert pick.d == date(2026, 12, 10) and ties == 1


def test_an_unknown_verdict_does_not_raise_and_ranks_as_mixed():
    odd = _row(date(2026, 12, 1), "excellent", 5, verdict="something-new")
    mixed = _row(date(2026, 12, 1), "excellent", 5, verdict="mixed")
    gfb = _row(date(2026, 12, 1), "excellent", 5, verdict="good-for-both")
    assert rank_key(odd) == rank_key(mixed) and rank_key(gfb) < rank_key(odd)
    assert top_pick([odd])[0] is odd


def test_the_real_finder_never_headlines_a_worse_verdict_than_the_tier_has():
    """A property over the real finder, no date pinned: which vivah days exist changes with the
    rules (#1357), so the test reads the window's own rows."""
    from astro_ai import chart
    from astro_ai.routes import muhurat as route

    bride = chart.compute_chart("1995-03-14", "10:30", "Delhi")
    groom = chart.compute_chart("1993-07-02", "18:15", "Delhi")
    cs, _, _ = route._search("vivah", "Delhi", START, 365, None, bride, groom)
    eligible = [c for c in cs if c.rating in muhurat.AUSPICIOUS_RATINGS
                and c.couple.combined_verdict != "avoid"]
    assert any(c.couple.combined_verdict == "good-for-both" for c in eligible), (
        "premise: a good-for-both auspicious day exists, so the property is not vacuous")
    pick, _ = top_pick(cs)
    best_in_tier = min(muhurat._verdict_rank(c) for c in eligible if c.rating == pick.rating)
    assert muhurat._verdict_rank(pick) == best_in_tier
