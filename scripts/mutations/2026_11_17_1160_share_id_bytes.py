"""#1160: a share-link id must carry 128 bits, not 32.

One literal MUTATIONS list per file (CLAUDE.md); never the central table."""

MUTATIONS = [
    ("#1160: new share-link ids are 4 random bytes again (2^32, probeable)",
     "src/astro_ai/snapshots.py",
     "_ID_BYTES = 16",
     "_ID_BYTES = 4",
     "test_new_ids_carry_128_bits"),
    ("#1160: load() rejects a legacy-length id, so every link already shared dies",
     "src/astro_ai/snapshots.py",
     "len(short_id) > 32",
     "len(short_id) > 5",
     "test_link_minted_at_the_old_length_still_loads"),
]
