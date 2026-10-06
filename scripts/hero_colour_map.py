#!/usr/bin/env python3
"""#259 — the colour map for the 76 /learn hero illustrations.

Committed as the record of WHAT WAS DECIDED AND WHY, because the SVGs it
produced carry no trace of the reasoning. Re-running it is a no-op; it exists so
the next person can see the rule rather than reverse-engineer it from 76 files.

WRITTEN DOWN BEFORE ANY EDITING, which is what the issue asks for.

SCOPE: the purple family ONLY. 15 distinct hexes, 205 file-uses. Everything
else stays:

  - The AMBER family (#fef3c7 in 60 files, #f59e0b in 38, #fbbf24 in 36,
    #78350f in 40) is the most-used group in the corpus and already reads warm
    against the new cream. The redesign's saffron #E4913C sits between #f59e0b
    and #fbbf24, so these are already in the family the brand moved TO.
  - The per-article greens, pinks, teals, blues, roses and limes are article
    IDENTITY. They never tracked the brand, so they cannot have drifted from
    it, and repainting them is 76 pictures repainted for no user benefit.

MAPPING RULE — by ROLE, taken from luminance, not by name:

  darkest purples  -> night   #140F1C   structural ink, outlines, deep fills
  mid purples      -> sindoor #9E2B25   the accent the brand uses on light
  light tints      -> cream-2 #F1E7D8   panel and wash fills

The boundary is where each hex actually sits: L < 0.06 is ink, L < 0.35 is an
accent, above that it is a wash. Applying that mechanically to all 15 keeps the
tonal STRUCTURE of every drawing — a dark outline stays the darkest thing in
its illustration, a wash stays the lightest — which is what stops a colour map
from flattening art it cannot see.

CHECKED, not assumed: sorting all 15 by source luminance and reading off the
target luminances must be monotonic. The first draft was not — #ede9fe and
#f0e7fb crossed over, which would have inverted two adjacent washes in any
drawing using both. Swapping their targets fixes it.
"""

MAP = {
    # dark — structural ink
    "#3b0764": "#140F1C",
    "#4c1d95": "#140F1C",
    "#581c87": "#17131A",
    "#6b21a8": "#9E2B25",   # the brand accent itself -> the new brand accent
    # mid — accent
    # NOT sindoor. #6b21a8 above is the brand accent itself and maps to the new
    # brand accent; #7c3aed is the brighter mid-purple that fills SHAPES —
    # bharani's vessel, ashwini's horse — and collapsing both onto one dark red
    # flattened the two most saturated drawings in the set. A terracotta at the
    # same luminance band keeps them lit.
    "#7c3aed": "#B03A22",
    "#8b5cf6": "#BE4A22",
    "#a855f7": "#CB5A2E",
    "#a78bfa": "#D98A45",
    "#c084fc": "#E4A96A",
    # light — washes
    "#c4b5fd": "#E2D6C2",
    "#ddd6fe": "#EDE4D5",
    "#e9d5ff": "#F1E7D8",
    "#f0e7fb": "#F1E7D8",
    "#ede9fe": "#FAF6EF",
    "#f6f1fb": "#FAF6EF",
}

# Not tokens, and deliberately so: the three mid-tones between sindoor and the
# lightest wash have no equivalent in a 14-colour role palette, and an
# illustration needs intermediate steps a UI palette does not. They are
# sindoor desaturated toward the cream, so they stay inside the brand's hue
# without pretending to be tokens.
NON_TOKEN = {"#BE4A22", "#CB5A2E", "#D98A45", "#E4A96A"}

# FIRST DRAFT OF THESE FOUR WAS TOO GREY. Mapped to a desaturated rose
# (S=0.34-0.67), which held the tone but rendered `bharani-nakshatra`'s vessel
# and `ashlesha-nakshatra`'s spiral visibly muddier than the purples they
# replaced — checked by rendering ten heroes before and after and looking at
# them, which is the only way this can be checked. Re-picked along the
# sindoor -> saffron axis at S=0.68-0.82, same luminance bands, and re-rendered.
# An illustration can carry chroma a UI palette would not.
