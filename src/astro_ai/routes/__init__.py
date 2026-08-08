"""Route modules for the FastAPI app (issue #154 — the main.py split).

This file imports NOTHING on purpose. If it re-exported the submodules, then
``from astro_ai.routes import deps`` would pull in every router in the package,
and an accidental ``import astro_ai.main`` inside any one of them would become a
hard circular import instead of the loud, local ImportError it should be.

Rules for every module in this package:
  - absolute imports only (``from astro_ai import X`` / ``from astro_ai.X import Y``);
    sibling modules here shadow real top-level module names, so a relative
    import self-imports and fails as a confusing AttributeError
  - no module here may import ``astro_ai.main``; main imports these, never the reverse
"""
