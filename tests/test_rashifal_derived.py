"""`/rashifal/{rashi}` must be served from the combined reading when it exists (#268).

The defect: on 2026-10-08 the Groq daily budget ran out (198,298 of 200,000 TPD)
and 21 of 24 rashifal pages returned 503 — while the 07:00 job had already cached
a combined reading that contains every one of those pages' text. The single route
only ever looked at its own cache and went straight to a ~3,330-token live call.

Every test here is that defect, or a way the fix can be broken that looks fine in
a browser: a reading served for the WRONG rashi, a derived body the route's own
gate would reject (an unbounded-regeneration loop), a corrupt blob promoted into
the cache the 07:00 blast reads, a bucket read on every request.

Hermetic: storage is an in-memory dict, the LLM is a counter. `stub_llm` and
`rashi_body` come from conftest.
"""
from __future__ import annotations

import time

import pytest

NAMES = [
    "Aries / Mesha", "Taurus / Vrishabha", "Gemini / Mithuna", "Cancer / Karka",
    "Leo / Simha", "Virgo / Kanya", "Libra / Tula", "Scorpio / Vrishchika",
    "Sagittarius / Dhanu", "Capricorn / Makara", "Aquarius / Kumbha", "Pisces / Meena",
]
SLUGS = [n.split(" / ")[0].lower() for n in NAMES]
_FILLER = "A steady day for measured work. " * 12          # ~384 chars, over the 300 floor


def _marker(i: int) -> str:
    return f"MARKER{SLUGS[i].upper()}END"


def _section(heading: str, marker: str) -> str:
    return f"## {heading}\n{marker} {_FILLER}"


def _combined(skip: int | None = None, headings=NAMES) -> str:
    return "\n\n".join(_section(h, _marker(i)) for i, h in enumerate(headings) if i != skip)


@pytest.fixture
def exhausted(stub_llm):
    """The 2026-10-08 state: every provider rate-limited. Any live call raises."""
    from astro_ai.providers import AllProvidersExhausted

    def _boom(_n):
        raise AllProvidersExhausted("All 2 provider(s) in chain failed.")

    return stub_llm(_boom)


@pytest.fixture
def gcs(monkeypatch):
    """An in-memory bucket. `.blobs` is the content, `.gets` every read attempted."""
    from astro_ai import storage

    class Bucket:
        blobs: dict[str, str] = {}
        gets: list[str] = []

    b = Bucket()
    b.blobs, b.gets = {}, []

    def get(key):
        b.gets.append(key)
        return b.blobs.get(key)

    def put(key, value, **_k):
        b.blobs[key] = value
        return True

    monkeypatch.setattr(storage, "get", get)
    monkeypatch.setattr(storage, "put", put)
    return b


@pytest.fixture
def seed(gcs, today_iso):
    """Put the combined reading where the 07:00 job puts it."""
    from astro_ai import daily_cache
    from astro_ai.rashifal_derive import combined_keys

    def _seed(text, lang="en", where="gcs"):
        if where == "daily":
            daily_cache.put("rashifal", lang, {"text": text, "lang": lang}, today_iso)
        else:
            gcs.blobs[combined_keys(lang, today_iso)[1]] = text

    return _seed


@pytest.mark.parametrize("where", ["daily", "gcs"])
def test_cold_page_is_served_from_the_combined_reading_with_no_llm_call(
        client, exhausted, seed, where):
    """THE #268 defect: the reading existed, the reader got a 503 anyway. `gcs` is
    what a cold instance actually has; `daily` is a warm one."""
    seed(_combined(), where=where)

    r = client.get("/rashifal/aries")

    assert r.status_code == 200, "a cached combined reading must not leave the page a 503"
    assert _marker(0) in r.text
    assert exhausted["n"] == 0, f"{exhausted['n']} live LLM calls for a page the blob could serve"


def test_derived_reading_belongs_to_the_requested_rashi(client, exhausted, seed):
    """Twelve distinct markers: every page carries its own and nobody else's."""
    seed(_combined())

    for i, slug in enumerate(SLUGS):
        text = client.get(f"/rashifal/{slug}").text
        assert _marker(i) in text, f"/rashifal/{slug} did not carry its own reading"
        foreign = [j for j in range(12) if j != i and _marker(j) in text]
        assert not foreign, f"/rashifal/{slug} carried the reading of {[SLUGS[j] for j in foreign]}"
    assert exhausted["n"] == 0


def test_a_missing_section_is_never_filled_from_a_name_that_merely_contains_it(
        client, stub_llm, seed, rashi_body):
    """`min` (a Pisces name token) is a SUBSTRING of "Gemini / Mithuna". A blob with
    no Pisces section must send Pisces to live generation, not serve Gemini."""
    seed(_combined(skip=11))
    calls = stub_llm(lambda _n: rashi_body(heading=NAMES[11]).replace("A steady", "LIVEPISCES steady", 1))

    text = client.get("/rashifal/pisces").text

    assert calls["n"] == 1, "Pisces has no section; it must be generated live"
    assert "LIVEPISCES" in text
    assert _marker(2) not in text, "Gemini's reading was served on the Pisces page"


def test_an_extra_heading_in_one_reading_does_not_shift_its_neighbours(client, exhausted, seed):
    """One call emitted a second `## ` heading. By POSITION that shifts every later
    section by one and Taurus's page would show Gemini's reading — no error, a
    plausible 200. By NAME the extra heading matches nothing."""
    text = _combined().replace(
        f"{_marker(0)} ", f"{_marker(0)} intro.\n\n## A Stray Heading\nstray text ", 1)
    seed(text)

    assert _marker(1) in client.get("/rashifal/taurus").text
    assert _marker(2) in client.get("/rashifal/gemini").text
    assert exhausted["n"] == 0


def test_a_derived_body_the_read_gate_would_reject_is_not_served_and_does_not_loop(
        client, stub_llm, seed, rashi_body):
    """A 100-char section passes the combined gate (the TOTAL is long) but fails the
    single route's 300-char gate. Serving/storing it would make the read gate
    discard it on the next view — one live call per pageview, all day."""
    short = _section(NAMES[2], "SHORTGEMINIBODY")[:100]
    seed("\n\n".join(short if i == 2 else _section(h, _marker(i)) for i, h in enumerate(NAMES)))
    calls = stub_llm(lambda _n: rashi_body(heading=NAMES[2]))

    codes = [client.get("/rashifal/gemini") for _ in range(5)]

    assert [c.status_code for c in codes] == [200] * 5
    assert all("SHORTGEMINIBODY" not in c.text for c in codes), "a sub-gate body was served"
    assert calls["n"] == 1, f"{calls['n']} live generations across 5 requests; expected 1"


def test_a_missing_blob_costs_one_bucket_read_per_negative_cache_window(
        client, stub_llm, gcs, rashi_body):
    """Nothing cached anywhere (the job has not run). Six different rashis must not
    each pay a cross-continent GCS round-trip — #144 was ~30 of them per render."""
    calls = stub_llm(lambda _n: rashi_body())

    for slug in SLUGS[:6]:
        assert client.get(f"/rashifal/{slug}").status_code == 200

    assert len(gcs.gets) == 1, f"{len(gcs.gets)} bucket reads for 6 rashis; expected 1"
    assert calls["n"] == 6, "with no blob the live path must run unchanged"


def test_the_blob_is_fetched_once_for_all_twelve_rashis(client, exhausted, seed, gcs):
    """A GCS hit is written back to tier 0; the other eleven pages read a local file."""
    seed(_combined())

    codes = [client.get(f"/rashifal/{slug}").status_code for slug in SLUGS]

    assert codes == [200] * 12
    assert len(gcs.gets) == 1, f"{len(gcs.gets)} bucket reads for 12 rashis; expected 1"
    assert exhausted["n"] == 0


def test_a_corrupt_blob_is_not_promoted_into_the_cache_the_blast_reads(
        client, stub_llm, seed, rashi_body, today_iso):
    """`_daily_rashifal_text` returns a tier-0 hit with NO quality check. Writing a
    blob back ungated would let the 07:00 blast email it to every subscriber."""
    from astro_ai import daily_cache

    seed("## Aries / Mesha\n" + "x" * 120)               # one heading, 137 chars: fails 'rashifal'
    stub_llm(lambda _n: rashi_body())

    assert client.get("/rashifal/aries").status_code == 200   # via live generation
    assert daily_cache.get("rashifal", "en", today_iso) is None, \
        "a blob that fails the combined gate was cached locally"


@pytest.fixture
def admin_headers():
    from astro_ai.main import app
    from astro_ai.routes.deps import require_admin

    app.dependency_overrides[require_admin] = lambda: None
    yield {}
    app.dependency_overrides.pop(require_admin, None)


def test_a_reading_warmed_by_the_job_serves_a_cold_instance(
        client, admin_headers, stub_llm, gcs, monkeypatch, tmp_path, today_iso):
    """Ties the WRITER's keys to the READER's. Run the real warm endpoint against an
    in-memory bucket, wipe everything an instance owns (disk, SQLite, the miss
    dict), keep only the bucket, then ask for a page. If warm_rashifal and the
    derive path ever disagree about a key this finds nothing and 503s."""
    from astro_ai import cache, daily_cache
    from astro_ai.routes import llm_support, subscribe

    monkeypatch.setattr(subscribe, "generate_rashifal", lambda **k: _combined())
    r = client.post("/admin/warm-rashifal?lang=en", headers=admin_headers)
    assert r.status_code == 200 and r.json()["sections"] == 12, r.text
    assert gcs.blobs, "the warm job wrote nothing to the bucket"

    # A cold instance: new disk, new SQLite file, empty in-process state.
    monkeypatch.setattr(daily_cache, "_ROOT", tmp_path / "fresh_instance")
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "fresh.db")
    llm_support._DURABLE_MISSES.clear()

    from astro_ai.providers import AllProvidersExhausted

    def _boom(_n):
        raise AllProvidersExhausted("budget gone")

    calls = stub_llm(_boom)
    page = client.get("/rashifal/leo")

    assert page.status_code == 200 and _marker(4) in page.text
    assert calls["n"] == 0


_warm_runs = iter(range(1000))


def _warm(client, headers, monkeypatch, text, tmp_path, gcs, lang="en"):
    """One warm request against EMPTY caches, so the text under test is what gets
    generated rather than whatever an earlier call in the same test left behind."""
    from astro_ai import cache, daily_cache
    from astro_ai.routes import subscribe

    n = next(_warm_runs)
    monkeypatch.setattr(daily_cache, "_ROOT", tmp_path / f"warm{n}")
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / f"warm{n}.db")
    gcs.blobs.clear()
    alerts: list[str] = []
    monkeypatch.setattr(subscribe, "generate_rashifal", lambda **k: text)
    monkeypatch.setattr(subscribe, "_fire_error_alert",
                        lambda request, err, source: alerts.append(f"{source}: {err}"))
    r = client.post(f"/admin/warm-rashifal?lang={lang}", headers=headers)
    return r.status_code, r.json(), alerts


def test_warm_reports_how_many_pages_it_can_serve(client, admin_headers, gcs, monkeypatch, tmp_path):
    """The detector the issue asked for. A combined text can have 12 sections and
    still serve fewer than 12 pages (an unrecognised heading), and HTTP 200 /
    sections==12 says nothing about that."""
    code, body, alerts = _warm(client, admin_headers, monkeypatch, _combined(), tmp_path, gcs)
    assert (code, body["sections"], body["single_pages"], body["ok"]) == (200, 12, 12, True)
    assert alerts == []

    headings = list(NAMES)
    headings[5] = "Something Else Entirely"                  # 12 sections, 11 derivable
    code, body, alerts = _warm(client, admin_headers, monkeypatch,
                              _combined(headings=headings), tmp_path, gcs)
    assert code == 200, "Cloud Scheduler judges the status; it must stay 200"
    assert (body["sections"], body["single_pages"], body["ok"]) == (12, 11, False)
    assert len(alerts) == 1 and "11/12" in alerts[0] and "rashifal:warm:en" in alerts[0]


def test_a_cooldown_does_not_hide_a_servable_blob(client, stub_llm, seed, today_iso):
    """A live generation that failed the gate arms a 5-minute cooldown. The blob
    arrives (or was always there); the page must heal from it, not 503 for five
    minutes."""
    from astro_ai.routes import rashifal

    rashifal._regen_failures.clear()
    stub_llm(lambda _n: "## Aries / Mesha\nToo short.\n\n## Taurus / Vrishabha\n" + "x" * 1200)
    assert client.get("/rashifal/aries").status_code != 200
    assert "aries-en" in rashifal._regen_failures, "precondition: the cooldown is armed"

    from astro_ai.routes import llm_support

    llm_support._DURABLE_MISSES.clear()    # the first request recorded a 30s negative
    seed(_combined())
    r = client.get("/rashifal/aries")
    rashifal._regen_failures.clear()

    assert r.status_code == 200 and _marker(0) in r.text


def test_hindi_page_is_derived_from_devanagari_headings(client, exhausted, seed):
    """ASSUMED FORMAT — NOT MEASURED. No production Hindi combined text was
    available when this was written. rashifal_single.txt tells the model to emit
    `## {English} / {Sanskrit}` while the Hindi suffix says to translate headings
    into Hindi; this fixture assumes the latter, in the spelling i18n.py uses
    (कुम्भ), because that is the only Devanagari form the repo already commits
    to. If the model's real Hindi headings differ, this test still passes and
    `single_pages` in the warm response is what will say so."""
    hindi = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला",
             "वृश्चिक", "धनु", "मकर", "कुम्भ", "मीन"]
    body = "आज का दिन शुभ है। " * 40
    seed("\n\n".join(f"## {h}\n{_marker(i)} {body}" for i, h in enumerate(hindi)), lang="hi")

    for i in (0, 10):                                         # first, and the कुम्भ spelling
        r = client.get(f"/hi/rashifal/{SLUGS[i]}")
        assert r.status_code == 200 and _marker(i) in r.text, SLUGS[i]
    assert exhausted["n"] == 0


# --- holes QA found by re-breaking the fix five independent ways -------------
# Each test below is one re-break that left all of the above green.

def _live_body(rashi_body, rashi_idx: int, tag: str) -> str:
    """A live-generation reply for a rashi, carrying a tag the page can be searched for."""
    return rashi_body(heading=NAMES[rashi_idx]).replace("A steady", f"{tag} steady", 1)


def test_a_hindi_page_never_reads_the_english_tier_zero_file(
        client, exhausted, seed, rashi_body):
    """Re-break: derive reads tier 0 with lang hard-coded "en". An English blob on
    disk and none for Hindi would then serve an ENGLISH reading under a Hindi URL
    (<html lang=hi>) — plausible, 200, and wrong for the reader."""
    seed(_combined(), lang="en", where="daily")

    r = client.get("/hi/rashifal/aries")

    assert _marker(0) not in r.text, "the English reading was served on the Hindi page"
    assert exhausted["n"] == 1, "with no Hindi blob the live path must run (and here 503s)"
    assert r.status_code == 503


def _two_rashis_in_one_title() -> str:
    headings = list(NAMES)
    headings[2] = "Gemini / Karka"           # Mithuna's section naming Cancer's Sanskrit name too
    return _combined(headings=headings)


def test_a_section_naming_two_rashis_is_attributed_to_neither(
        client, stub_llm, seed, rashi_body):
    """Re-break: the multi-match guard goes and the FIRST rashi named wins. The
    section's text was written for one rashi; which one is not recoverable from a
    title that names two, so serving it as Gemini is a guess."""
    seed(_two_rashis_in_one_title())
    calls = stub_llm(lambda _n: _live_body(rashi_body, 2, "LIVEGEMINI"))

    gemini = client.get("/rashifal/gemini")

    assert _marker(2) not in gemini.text, "an ambiguous section was served as Gemini"
    assert "LIVEGEMINI" in gemini.text and calls["n"] == 1, "Gemini must fall to live generation"
    # Cancer has its own, unambiguous section and is not collateral damage.
    assert _marker(3) in client.get("/rashifal/cancer").text
    assert calls["n"] == 1


def test_two_sections_for_one_rashi_are_attributed_to_neither(
        client, stub_llm, seed, rashi_body):
    """Re-break: the duplicate guard goes and the FIRST section wins. Two sections
    for Leo means one call emitted another's heading or the job concatenated twice;
    neither body is known to be Leo's."""
    text = _combined() + "\n\n" + _section(NAMES[4], "DUPLICATELEOEND")
    seed(text)
    calls = stub_llm(lambda _n: _live_body(rashi_body, 4, "LIVELEO"))

    leo = client.get("/rashifal/leo")

    assert _marker(4) not in leo.text and "DUPLICATELEOEND" not in leo.text, \
        "one of two competing Leo sections was served"
    assert "LIVELEO" in leo.text and calls["n"] == 1
    assert _marker(5) in client.get("/rashifal/virgo").text and calls["n"] == 1


def test_a_derived_reading_is_stored_so_the_next_request_reads_nothing(
        client, exhausted, seed, gcs, today_iso):
    """Re-break: the derived body is served but not written to `rashifal_single`.
    Every later view of the page then re-derives — free while the tier-0 file
    exists, a bucket read per request the moment it does not (a new instance)."""
    from astro_ai import daily_cache
    from astro_ai.routes import llm_support

    seed(_combined())
    assert client.get("/rashifal/aries").status_code == 200
    stored = daily_cache.get("rashifal_single", "aries-en", today_iso)
    assert stored and _marker(0) in stored["body"], "the derived reading was not stored"

    # Take away everything the DERIVE path could read from.
    for f in (daily_cache._ROOT / "rashifal").glob("*.json"):
        f.unlink()
    llm_support._DURABLE_MISSES.clear()
    reads_before = len(gcs.gets)

    again = client.get("/rashifal/aries")

    assert again.status_code == 200 and _marker(0) in again.text
    assert len(gcs.gets) == reads_before, "the second request went back to the bucket"
    assert exhausted["n"] == 0


def test_every_devanagari_rashi_name_maps_to_its_own_index():
    """All twelve, not a sample. Names are read from i18n's `rashi_name_*` keys —
    the spelling the site itself prints (knowledge/rashis.md) — so a name edited
    here, or an i18n spelling change, fails. The Hindi FORMAT the model emits is
    still unmeasured (see rashifal_derive); this pins only that the names we accept
    are attributed to the right rashi. The two variants are assumed spellings."""
    from astro_ai.i18n import translate
    from astro_ai.rashifal_derive import sections_by_rashi

    for i, slug in enumerate(SLUGS):
        name = translate("hi", f"rashi_name_{slug}")
        got = sections_by_rashi(f"## {name}\n{_marker(i)} {_FILLER}\n\n## {NAMES[(i + 1) % 12]}\nother")
        assert got.get(i, "").startswith(_marker(i)), f"{name!r} did not map to {slug}"

    for variant, i in (("कुंभ", 10), ("वृष", 1)):
        assert sections_by_rashi(f"## {variant}\n{_marker(i)} {_FILLER}").get(i, "").startswith(_marker(i)), variant
