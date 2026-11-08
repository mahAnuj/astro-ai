"""The rashifal run record says when it was not written (2026-11-08)."""

MUTATIONS = [
    ("run record: a refused write is reported as recorded again",
     "scripts/publish_rashifal.py",
     "    if written is None:\n",
     "    if False:\n",
     "test_a_refused_record_write_is_reported_not_claimed"),
]
