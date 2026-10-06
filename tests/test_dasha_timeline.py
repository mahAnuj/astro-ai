"""The window `dasha_timeline` picks out of the Vimshottari sequence.

The redesign renders the Mahadasha sequence as one horizontal strip whose
segments are sized by each period's LENGTH — Ketu's 7 years visibly next to
Venus's 20 — so that a reader can see at a glance whether they are in a long
period or a short one. Two properties carry that, and both are arithmetic
rather than styling, which is why they are tested here and not left to a
visual check:

1. The window has to CONTAIN the active period. A strip that quietly slides
   off the current Mahadasha is worse than no strip: it still looks
   authoritative, and it is answering a different question.
2. It has to return `span` segments whenever the sequence is long enough,
   INCLUDING at the ends. The natural implementation — `active_index - 2` to
   `active_index + 4` — silently returns four segments for someone in their
   first Mahadasha and five in their second, because the left edge clamps and
   nothing compensates on the right. A chart for an infant would render a
   visibly shorter strip than one for an adult, for no reason the reader could
   see.

Ages here are chosen to put the active period at different offsets: a chart
from the 2020s is in its first or second Mahadasha, one from the 1990s is a
few in, and the count is asserted rather than the lord names, which depend on
the Moon's nakshatra and are the ephemeris's business, not this function's.
"""
from __future__ import annotations

import pytest

from astro_ai.chart import compute_chart, compute_dasha_state, dasha_timeline


# (birth_date, birth_time, place) — real charts, so the sequence is real.
CHARTS = [
    ("2024-03-02", "06:15", "Jaipur, India"),   # infant: active period at/near index 0
    ("2015-11-20", "14:40", "Mumbai, India"),   # child
    ("1994-08-14", "10:30", "Jaipur, India"),   # adult, a few periods in
    ("1958-01-09", "04:05", "Kolkata, India"),  # older, further along
]


@pytest.mark.parametrize("birth", CHARTS)
def test_the_window_always_contains_the_active_mahadasha(birth):
    state = compute_dasha_state(compute_chart(*birth))
    window = dasha_timeline(state)
    assert state.mahadasha in window, (
        f"{birth}: active {state.mahadasha.lord} "
        f"({state.mahadasha.start}–{state.mahadasha.end}) is not in the window "
        f"{[p.lord for p in window]} — the strip would be showing a stretch of "
        f"life the reader is not in."
    )


@pytest.mark.parametrize("birth", CHARTS)
def test_the_window_is_full_width_even_at_the_start_of_a_life(birth):
    state = compute_dasha_state(compute_chart(*birth))
    window = dasha_timeline(state, span=6)
    expected = min(6, len(state.sequence))
    assert len(window) == expected, (
        f"{birth}: active_index={state.active_index}, sequence={len(state.sequence)}, "
        f"got {len(window)} segments, expected {expected}. Clamping the left edge "
        f"without taking the difference from the right is how a young chart ends "
        f"up with a shorter strip than an old one."
    )


@pytest.mark.parametrize("birth", CHARTS)
def test_the_window_is_a_contiguous_run_in_chronological_order(birth):
    """A strip is a timeline; gaps or reordering would make the widths lie."""
    state = compute_dasha_state(compute_chart(*birth))
    window = dasha_timeline(state)
    for earlier, later in zip(window, window[1:]):
        assert earlier.end == later.start, (
            f"{birth}: {earlier.lord} ends {earlier.end} but {later.lord} starts "
            f"{later.start} — the segments are not adjacent, so their relative "
            f"widths no longer describe one continuous span of years."
        )


def test_a_sequence_shorter_than_the_span_comes_back_whole():
    state = compute_dasha_state(compute_chart("1994-08-14", "10:30", "Jaipur, India"))
    assert dasha_timeline(state, span=len(state.sequence) + 5) == state.sequence


def test_segment_widths_are_proportional_to_years_not_equal():
    """The point of the component. Vimshottari periods run 6 to 20 years, so a
    real window must contain segments of visibly different length."""
    state = compute_dasha_state(compute_chart("1994-08-14", "10:30", "Jaipur, India"))
    window = dasha_timeline(state)
    years = {round(p.years, 1) for p in window}
    assert len(years) > 1, (
        f"every segment is {years} years long — either the window collapsed onto "
        f"one lord or the sequence is not being read; a strip of equal boxes "
        f"carries no information a list does not."
    )
