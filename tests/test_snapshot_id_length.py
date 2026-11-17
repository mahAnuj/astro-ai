"""Share-link ids must not be probeable — #1160.

`/r/{id}` shows the sender's name and birth details to anyone holding the id,
and viewing is not rate-limited. A 4-byte id (2^32) is within reach of a
request loop, so new ids are 16 bytes. Links minted at the old length must keep
loading until their 30-day expiry: there is no migration.
"""
from __future__ import annotations

from datetime import timedelta

from astro_ai import snapshots

_DETAILS = {"name": "A", "birth_date": "1990-01-01", "birth_time": "10:00", "birth_place": "Delhi"}


def _fake_storage(monkeypatch) -> dict:
    blobs: dict = {}
    monkeypatch.setattr(snapshots.storage, "put_json", lambda k, v: blobs.__setitem__(k, v) or True)
    monkeypatch.setattr(snapshots.storage, "get_json", lambda k: blobs.get(k))
    return blobs


def test_new_ids_carry_128_bits(monkeypatch):
    _fake_storage(monkeypatch)
    snap = snapshots.create(birth_details=_DETAILS, reading_text="r", lang="en")
    assert snap is not None
    assert len(snap.id) >= 22, f"id {snap.id!r} is shorter than 16 bytes of token_urlsafe"
    assert len({snapshots.create(birth_details=_DETAILS, reading_text="r", lang="en").id
                for _ in range(20)}) == 20


def test_link_minted_at_the_old_length_still_loads(monkeypatch):
    blobs = _fake_storage(monkeypatch)
    legacy = "9AK2X7"  # what token_urlsafe(4) produced
    fresh = snapshots.create(birth_details=_DETAILS, reading_text="old link", lang="en")
    blobs[snapshots._blob_key(legacy)] = {**blobs[snapshots._blob_key(fresh.id)], "id": legacy}
    loaded = snapshots.load(legacy)
    assert loaded is not None and loaded.reading_text == "old link"


def test_expired_legacy_link_still_expires(monkeypatch):
    blobs = _fake_storage(monkeypatch)
    legacy = "Zq3_x1"
    fresh = snapshots.create(birth_details=_DETAILS, reading_text="gone", lang="en")
    past = (snapshots._now() - timedelta(days=1)).isoformat(timespec="seconds")
    blobs[snapshots._blob_key(legacy)] = {**blobs[snapshots._blob_key(fresh.id)],
                                          "id": legacy, "expires_at": past}
    assert snapshots.load(legacy) is None
