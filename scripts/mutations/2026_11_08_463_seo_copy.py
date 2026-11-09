"""#463: every /learn seo_description fits a SERP, and verify_seo_copy.py measures it decoded.

Each row re-breaks one property and names the test that must go red."""

MUTATIONS = [
    ("#463: manglik-remedies gets its 187-char tail back, so a description is over 160 decoded",
     "src/astro_ai/learn_registry.py",
     "matching another Manglik. Check cancellation rules first.\"",
     "matching another Manglik. Check cancellation rules first — most 'Manglik' charts are actually cancelled.\"",
     "test_no_registered_description_exceeds_160_decoded_characters"),
    ("#463: the gate counts the raw source, where &mdash; is seven characters and one decoded",
     "scripts/verify_seo_copy.py",
     "return len(html.unescape(value))",
     "return len(value)",
     "test_the_gate_measures_decoded_length_not_raw"),
    ("#463: the gate drops its floor, so a stub description passes",
     "scripts/verify_seo_copy.py",
     "elif n < DESC_FLOOR:",
     "elif False:",
     "test_floor_boundary_is_50_inclusive_and_a_stub_fails"),
    ("#463: the gate's ceiling is raised to make a run green",
     "scripts/verify_seo_copy.py",
     "DESC_CEILING = 160",
     "DESC_CEILING = 200",
     "test_ceiling_boundary_is_160_inclusive"),
    ("#463: an over-long seo_title becomes a failure, confounding the #311/#685 CTR tests",
     "scripts/verify_seo_copy.py",
     "            advisories.append(",
     "            failures.append(",
     "test_a_long_title_is_reported_but_never_fails"),
]
