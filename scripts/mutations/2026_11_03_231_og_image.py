"""#231 (PR #693): a shared /r/{id} link advertises an og:image a crawler can use.

Moved out of the central table in mutate_behaviour_suite.py when #691 froze it
(merging main into #691); rows unchanged."""

MUTATIONS = [
    ("#231: the snapshot page's og:image is the session-derived SVG card again",
     "src/astro_ai/templates/result.html",
     "   session; that is the part of #231 still open. #}\n",
     "   session; that is the part of #231 still open. #}\n"
     "{% block og_image %}{{ site_url }}/kundli/card{% endblock %}\n",
     "test_snapshot_og_image_is_a_png_not_the_session_derived_card"),
    ("#231: the card's 1080x1920 size is declared over a 1200x630 PNG (declared != served)",
     "src/astro_ai/templates/result.html",
     "   session; that is the part of #231 still open. #}\n",
     "   session; that is the part of #231 still open. #}\n"
     "{% block og_image_width %}1080{% endblock %}\n",
     "test_snapshot_declared_size_matches_the_bytes_served"),
]
