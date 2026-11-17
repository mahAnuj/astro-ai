"""2026-11-17: knowledge files, top-level templates and /learn articles are
report-only rows, so knowledge or template PRs stop conflicting on one shared
number. tests/test_architecture_counts_gate.py."""

MUTATIONS = [
    ("arch counts: 'knowledge files' goes back to a hand-typed number",
     "scripts/verify_architecture_counts.py",
     '    "knowledge files",\n    "top-level templates",',
     '    "top-level templates",',
     "test_clean_doc_passes_and_prints_the_measured_values"),
]
