"""The durable (GCS) tier under `/kundli`'s natal reading.

The defect this covers is not wrong output, it is COST. The natal reading is
cached `ttl_days=None` — "never expires" — into SQLite on `/tmp`, which is
tmpfs, per-instance, min-instances 0. So "permanent" meant regenerated once per
instance, once per cold start and once per deploy, at ~7,800 input tokens
against an 8,000 TPM per-model free-tier bucket. Every one of those cost a
reading the site could have given somebody else.

Every test here clears the SQLite cache between requests where it wants to
simulate that cold start, because a warm instance never reaches the tier under
test. The last test asserts the opposite property — that a warm instance pays
ZERO cross-continent round-trips — which is the half that keeps this from
becoming #144 (~30 sequential bucket reads per render, a 13-second homepage).
"""
from __future__ import annotations

import pytest


def _natal_body(_n: int = 0) -> str:
    """A generated natal reading that passes `passes_quality(..., "natal")`:
    ≥800 chars and ≥2 `## ` headings."""
    filler = "The chart favours patient, deliberate work this season. "
    return (
        "## Personality\n" + filler * 10 + "\n\n"
        "## Career\n" + filler * 10 + "\n"
    )


@pytest.fixture
def fake_gcs(monkeypatch):
    """An in-memory stand-in for the bucket, with call counters.

    Patched on `astro_ai.storage` itself rather than on the name imported into
    `routes.llm_support`, so the stub cannot be sidestepped by a second module
    reaching for `storage.get`. Counting is the point: "a warm instance pays
    zero GCS ops" is not a claim a test can make without a counter.
    """
    from astro_ai import storage

    blobs: dict[str, str] = {}
    counts = {"get": 0, "put": 0}

    def _get(key: str):
        counts["get"] += 1
        return blobs.get(key)

    def _put(key: str, value: str, **kw) -> bool:
        counts["put"] += 1
        blobs[key] = value
        return True

    monkeypatch.setattr(storage, "get", _get)
    monkeypatch.setattr(storage, "put", _put)
    return {"blobs": blobs, "counts": counts}


@pytest.fixture
def cold_start():
    """Wipe the (tmp-isolated) SQLite cache — i.e. land on a fresh container.

    Deletes the file rather than the rows: `_conn()` recreates the schema on
    next use, and this way the fixture cannot drift if a table is added.
    """

    def _wipe():
        from astro_ai import cache

        cache.DB_PATH.unlink(missing_ok=True)

    return _wipe


def test_a_reading_survives_the_container(client, saved_chart, stub_llm,
                                          fake_gcs, cold_start):
    """The whole point: generated once, ever — not once per cold start."""
    calls = stub_llm(_natal_body)
    saved_chart()

    assert client.get("/kundli").status_code == 200
    cold_start()
    assert client.get("/kundli").status_code == 200

    assert calls["n"] == 1, (
        f"{calls['n']} live natal generations across two requests; the second "
        f"was served after a cold start and must come from the durable tier"
    )
    assert fake_gcs["counts"]["put"] == 1, fake_gcs["counts"]
    assert len(fake_gcs["blobs"]) == 1, sorted(fake_gcs["blobs"])
    key = next(iter(fake_gcs["blobs"]))
    assert key.startswith("llm/natal/en/") and key.endswith(".txt"), key


def test_a_bad_blob_is_discarded_and_regenerated_once(client, saved_chart,
                                                      stub_llm, fake_gcs,
                                                      cold_start):
    """A second place a bad value can live is a second place it can be served
    forever — or regenerated on every pageview, which is the #215 shape and the
    expensive half. The blob goes through the same `passes_quality` gate the
    SQLite tier uses, and the regeneration overwrites it."""
    calls = stub_llm(_natal_body)
    saved_chart()
    client.get("/kundli")                       # populates both tiers
    assert calls["n"] == 1

    key = next(iter(fake_gcs["blobs"]))
    fake_gcs["blobs"][key] = "## Too short.\n"  # below the 800-char natal floor
    cold_start()

    assert client.get("/kundli").status_code == 200
    cold_start()
    assert client.get("/kundli").status_code == 200

    assert calls["n"] == 2, (
        f"{calls['n']} total generations; the bad blob must cost exactly one "
        f"regeneration, not one per request and not zero (served bad)"
    )
    from astro_ai import providers as llm_providers
    ok, reason = llm_providers.passes_quality(fake_gcs["blobs"][key], "natal")
    assert ok, f"the regeneration did not heal the blob: {reason}"


def test_storage_unavailable_degrades_to_todays_behaviour(client, saved_chart,
                                                          stub_llm, monkeypatch,
                                                          cold_start):
    """No bucket configured is the normal local-dev case and the failure case
    for a credential problem in production. A cache is never allowed to break a
    reading, so this must look exactly like the world before the tier existed:
    one generation per cold start, and no exception."""
    from astro_ai import storage

    monkeypatch.setattr(storage, "get", lambda key: None)
    monkeypatch.setattr(storage, "put", lambda key, value, **kw: False)
    calls = stub_llm(_natal_body)
    saved_chart()

    assert client.get("/kundli").status_code == 200
    cold_start()
    assert client.get("/kundli").status_code == 200

    assert calls["n"] == 2, f"{calls['n']} generations; expected today's 1-per-cold-start"


def test_storage_raising_never_reaches_the_seeker(client, saved_chart,
                                                  stub_llm, monkeypatch,
                                                  cold_start):
    """`storage.get`/`put` already swallow GCS errors, so this covers the
    unexpected — a credential refresh or an import blowing up. The seeker still
    gets their reading."""
    from astro_ai import storage

    def _boom(*a, **kw):
        raise RuntimeError("bucket on fire")

    monkeypatch.setattr(storage, "get", _boom)
    monkeypatch.setattr(storage, "put", _boom)
    calls = stub_llm(_natal_body)
    saved_chart()

    assert client.get("/kundli").status_code == 200
    cold_start()
    assert client.get("/kundli").status_code == 200
    assert calls["n"] == 2, calls["n"]


def test_a_warm_instance_pays_zero_gcs_round_trips(client, saved_chart,
                                                   stub_llm, fake_gcs):
    """SQLite first, GCS only on a local miss.

    The bucket is US multi-region and Cloud Run is in asia-south1, so a read
    here is a cross-continent round-trip. Putting one on every render is
    exactly #144. Asserted on the counter, not on latency — a timing assertion
    is what let #144's predecessor ship a strip that did not render at all.
    """
    stub_llm(_natal_body)
    saved_chart()
    client.get("/kundli")                       # cold: 1 GET (miss) + 1 PUT

    fake_gcs["counts"]["get"] = 0
    for _ in range(3):
        assert client.get("/kundli").status_code == 200

    assert fake_gcs["counts"]["get"] == 0, (
        f"{fake_gcs['counts']['get']} bucket reads on warm renders; a SQLite "
        f"hit must never touch GCS"
    )


def test_a_chart_in_neither_tier_does_not_re_read_the_bucket_every_render(
        client, saved_chart, stub_llm, fake_gcs, cold_start, monkeypatch):
    """A miss is remembered briefly, so a seeker refreshing an ungenerated
    chart does not spend a Class B op and ~0.4s cross-continent per refresh.

    Deliberately short-TTL, not permanent: a permanent negative cache would
    pin this instance to "not generated" forever (2026-08-23 decision log).
    The expiry is asserted by moving the clock rather than sleeping — a test
    that sleeps 30s is a test that gets deleted.
    """
    from astro_ai.routes import llm_support

    # Writes fail, so nothing ever lands in the bucket and every render is a
    # genuine miss — the shape this cache exists for.
    monkeypatch.setattr(llm_support.storage, "put", lambda key, value, **kw: False)
    stub_llm(_natal_body)
    saved_chart()

    for _ in range(3):
        assert client.get("/kundli").status_code == 200
        cold_start()

    assert fake_gcs["counts"]["get"] == 1, (
        f"{fake_gcs['counts']['get']} bucket reads for 3 renders of a chart "
        f"that is in neither tier; the miss must be remembered"
    )

    # ...but only briefly. Past the TTL the bucket is consulted again.
    for key in llm_support._DURABLE_MISSES:
        llm_support._DURABLE_MISSES[key] -= llm_support._DURABLE_MISS_TTL_S + 1
    assert client.get("/kundli").status_code == 200
    assert fake_gcs["counts"]["get"] == 2, fake_gcs["counts"]


def test_a_durable_hit_is_not_reported_as_a_fresh_generation(client, saved_chart,
                                                             stub_llm, fake_gcs,
                                                             cold_start,
                                                             monkeypatch):
    """A reading restored from the bucket is a re-view, not a new kundli.

    Counting it as fresh would send the owner a duplicate Telegram ping and
    write a phantom `form_kundli` event for every cold start — the exact
    duplication the `if not was_cached` guard was added to stop, re-entering
    through the new tier.
    """
    from astro_ai import events
    from astro_ai.routes import kundli as kundli_routes

    fired = {"notify": 0, "event": 0}
    monkeypatch.setattr(kundli_routes.notify, "kundli_generated",
                        lambda **kw: fired.__setitem__("notify", fired["notify"] + 1))

    _real_record = events.record

    def _record(*a, **kw):
        if kw.get("type") == "form_kundli":
            fired["event"] += 1
        return _real_record(*a, **kw)

    monkeypatch.setattr(kundli_routes.events, "record", _record)

    stub_llm(_natal_body)
    saved_chart()
    client.get("/kundli")
    assert (fired["notify"], fired["event"]) == (1, 1), fired

    cold_start()
    client.get("/kundli")

    assert fired == {"notify": 1, "event": 1}, (
        f"{fired} — a durable-tier hit fired an owner notification and/or a "
        f"form_kundli event for a reading that was not generated"
    )


# --- properties the tier ADVERTISES, each caught escaping under mutation -----
#
# Every test below was written because the property it checks survived a
# mutation of the code that provides it: the suite was green with the property
# removed. A green suite that survives the mutation is coverage that is not
# there, whatever the count says.


def test_the_blob_key_carries_the_prompt_version(client, saved_chart, stub_llm,
                                                 fake_gcs, cold_start, monkeypatch):
    """`_cached`'s "a stale read is impossible by construction" rests entirely
    on `prompt_fp` — which carries `PROMPT_LOGIC_VERSION` — being in the blob
    path. Drop it and a future bump keeps serving superseded-prompt readings
    out of the bucket forever, invisibly, because nothing can list or diff
    them. `lang` dropping was already caught; this is the same key's other
    dimension.
    """
    from astro_ai import cache

    calls = stub_llm(_natal_body)
    saved_chart()
    client.get("/kundli")
    assert calls["n"] == 1
    first = set(fake_gcs["blobs"])

    # A prompt-logic bump is the manual invalidation lever; `fingerprint_prompt`
    # reads the module global at call time, so this is the real mechanism.
    monkeypatch.setattr(cache, "PROMPT_LOGIC_VERSION", "vTEST")
    cold_start()
    assert client.get("/kundli").status_code == 200

    assert calls["n"] == 2, (
        "a PROMPT_LOGIC_VERSION bump served the OLD reading out of the bucket; "
        "the blob key is not versioned by the prompt"
    )
    new = set(fake_gcs["blobs"]) - first
    assert len(new) == 1, f"expected a second, distinct blob; blobs={sorted(fake_gcs['blobs'])}"


def test_a_durable_hit_warms_sqlite_so_the_next_view_is_free(client, saved_chart,
                                                             stub_llm, fake_gcs,
                                                             cold_start):
    """The GCS hit must backfill SQLite, not just return.

    Without the backfill every post-cold-start view of the same chart pays a
    fresh cross-continent GET — the exact cost this tier advertises it removes,
    and invisible to a warm-instance test that populated SQLite by GENERATING.
    """
    stub_llm(_natal_body)
    saved_chart()
    client.get("/kundli")          # populates both tiers via the generate path
    cold_start()
    client.get("/kundli")          # durable hit — must also warm SQLite

    fake_gcs["counts"]["get"] = 0
    for _ in range(3):
        assert client.get("/kundli").status_code == 200

    assert fake_gcs["counts"]["get"] == 0, (
        f"{fake_gcs['counts']['get']} bucket reads after a durable hit; the hit "
        f"did not warm SQLite, so every later view pays the round-trip again"
    )


def test_the_snapshot_path_shares_the_blob_with_the_render_path(client, saved_chart,
                                                                stub_llm, fake_gcs,
                                                                cold_start):
    """`_cached` is called from TWO places in `kundli.py` and missing the
    second is the easy mistake — the render path is the one anybody testing
    this would drive.

    Asserted in both directions, because passing `durable_key` at one site
    gives a write the other never reads, or a read nothing ever writes.
    """
    from astro_ai.routes import kundli as kundli_routes

    kundli_routes._SNAPSHOT_CREATED_TODAY.clear()
    calls = stub_llm(_natal_body)
    saved_chart()

    # snapshot writes → render reads
    assert client.post("/kundli/snapshot").status_code == 200
    assert calls["n"] == 1, calls["n"]
    cold_start()
    assert client.get("/kundli").status_code == 200
    assert calls["n"] == 1, (
        f"{calls['n']} generations; the snapshot path did not persist the "
        f"reading the render path then had to regenerate"
    )

    # render writes → snapshot reads
    natal_blobs = {k: v for k, v in fake_gcs["blobs"].items() if k.startswith("llm/natal/")}
    assert len(natal_blobs) == 1, sorted(natal_blobs)
    cold_start()
    assert client.post("/kundli/snapshot").status_code == 200
    assert calls["n"] == 1, (
        f"{calls['n']} generations; the snapshot path does not READ the durable "
        f"tier the render path wrote"
    )


def test_a_durable_hit_is_logged_as_a_hit_with_no_tokens(client, saved_chart,
                                                         stub_llm, fake_gcs,
                                                         cold_start):
    """No LLM call was made, so /admin/usage must not be told one was.

    `_cached` estimates `in_tok`/`out_tok` from the returned text, so logging a
    durable hit as a miss would attribute a full natal call's worth of
    estimated tokens to a request that spent none — and the token numbers are
    the instrument this whole change is measured with.
    """
    import sqlite3

    from astro_ai import cache

    stub_llm(_natal_body)
    saved_chart()
    client.get("/kundli")                       # the real generation: one miss
    cold_start()                                # wipes llm_calls too
    client.get("/kundli")                       # served from the bucket

    conn = sqlite3.connect(str(cache.DB_PATH))
    rows = conn.execute(
        "SELECT cache_hit, input_tokens, output_tokens FROM llm_calls WHERE route='natal'"
    ).fetchall()
    conn.close()

    assert rows, "no natal call was logged at all"
    assert all(hit == 1 for hit, _, _ in rows), f"a durable hit was logged as a MISS: {rows}"
    assert all(i == 0 and o == 0 for _, i, o in rows), (
        f"a durable hit reported token spend that never happened: {rows}"
    )


def test_the_miss_cache_sweep_drops_by_age_not_wholesale(monkeypatch):
    """#182's own comment forbids `clear()` here: a size-triggered wipe evicts
    LIVE entries, which re-admits exactly the round-trips this dict removes —
    and the eviction lands on whoever is unlucky, not on whoever is stale.

    Driven through `_durable_get` rather than a private sweep helper so the
    trigger condition is under test too.
    """
    import time as _t

    from astro_ai import storage
    from astro_ai.routes import llm_support

    monkeypatch.setattr(storage, "get", lambda key: None)

    now = _t.time()
    stale = f"llm/natal/en/vX/stale.txt"
    fresh = f"llm/natal/en/vX/fresh.txt"
    for i in range(llm_support._DURABLE_MISS_SWEEP_AT + 1):
        llm_support._DURABLE_MISSES[f"filler-{i}"] = now - 3600
    llm_support._DURABLE_MISSES[stale] = now - 3600
    llm_support._DURABLE_MISSES[fresh] = now          # live: still inside the TTL

    llm_support._durable_get("llm/natal/en/vX/trigger.txt")   # over the threshold → sweep

    assert fresh in llm_support._DURABLE_MISSES, (
        "the sweep dropped a live entry; a wholesale clear() is not a sweep"
    )
    assert stale not in llm_support._DURABLE_MISSES, "the stale entry was not swept"
