"""#735: /admin/* must not boot GA4 or Clarity.

Rows target templates/base.html, rendered by tests/test_admin_not_tracked.py. One area
file, a literal list (test_mutation_tables.py requires it)."""

MUTATIONS = [
    ("#735: the GA4 id is no longer blanked on /admin paths",
     "src/astro_ai/templates/base.html",
     "{% set _ga4_id = '' if _no_track else ga4_measurement_id %}",
     "{% set _ga4_id = ga4_measurement_id %}",
     "test_admin_401_carries_no_provider_id"),
    ("#735: the Clarity id is no longer blanked on /admin paths",
     "src/astro_ai/templates/base.html",
     "{% set _clarity_id = '' if _no_track else clarity_project_id %}",
     "{% set _clarity_id = clarity_project_id %}",
     "test_admin_401_carries_no_provider_id"),
    ("#735: every page loses analytics, not only /admin",
     "src/astro_ai/templates/base.html",
     "{% set _no_track = request.url.path == '/admin' or request.url.path.startswith('/admin/') %}",
     "{% set _no_track = true %}",
     "test_control_public_page_still_carries_the_ids"),
    ("#735: the /admin match becomes a substring, so /administer stops tracking",
     "src/astro_ai/templates/base.html",
     "request.url.path == '/admin' or request.url.path.startswith('/admin/')",
     "request.url.path.startswith('/admin')",
     "test_prefix_match_is_a_path_segment_not_a_substring"),
]
