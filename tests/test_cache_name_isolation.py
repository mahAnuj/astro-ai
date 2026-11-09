"""#818: a reading generated for one visitor's NAME must not be served to another.

`cache.fingerprint_chart` hashes `birth_date|birth_time|birth_place` and nothing
else, but the prompt carries `Name: <name>` (natal, outlook, today) or
`GROOM:` / `BRIDE:` (matching) and the prompts tell the model it may address the
seeker by name. So two visitors with identical birth data shared a key, and the
second was handed the first's prose -- for natal from a GCS blob that never
expires and is shared across every instance.

`stub_llm` cannot see this: it returns fixed text whatever the request said.
The fake below echoes the name it was asked about into the body, which is the
only way a test can tell whose reading came back. The names are deliberately
unlike anything on the page chrome ("Asha" is a substring of "Ashadha").
"""
from __future__ import annotations

import re

import pytest

ASHA = "Zelphira"
RAVI = "Quentorix"
BIRTH = {"birth_date": "1990-04-12", "birth_time": "14:35", "birth_place": "Mumbai, India"}

# The four per-visitor routes, as (label, path). `/matching` is a POST and is
# driven separately.
_ROUTES = [("natal", "/kundli"), ("monthly", "/monthly"),
           ("yearly", "/yearly"), ("today", "/today")]


@pytest.fixture
def echo_llm(monkeypatch):
    """Replace the provider call with one that writes the requested name into
    its reply, and count the calls. Passes `passes_quality` on every route
    (>=800 chars, two `## ` headings)."""
    import astro_ai.llm as llm

    calls = {"n": 0, "names": []}
    filler = "The chart favours patient, deliberate work this season. "

    def fake(*a, **k):
        messages = k.get("messages") or a[0]
        user = next(m["content"] for m in messages if m["role"] == "user")
        names = re.findall(r"^(?:Name|GROOM|BRIDE): (.*)$", user, re.M)
        names = [n for n in names if n not in ("(not provided)", "(unnamed)")]
        calls["n"] += 1
        calls["names"].append(names)
        who = " and ".join(names) or "friend"
        return (f"## Overview\nDear {who}. " + filler * 10 + "\n\n"
                f"## Detail\nFor {who}. " + filler * 10 + "\n")

    monkeypatch.setattr(llm.providers, "chat", fake)
    return calls


@pytest.fixture
def fake_gcs(monkeypatch):
    from astro_ai import storage

    blobs: dict[str, str] = {}

    def _put(key, value, **kw):
        blobs[key] = value
        return True

    monkeypatch.setattr(storage, "get", lambda key: blobs.get(key))
    monkeypatch.setattr(storage, "put", _put)
    return blobs


@pytest.fixture
def cold_start():
    def _wipe():
        from astro_ai import cache

        cache.DB_PATH.unlink(missing_ok=True)

    return _wipe


def _view(client, saved_chart, name, path):
    saved_chart(name=name, **BIRTH)
    resp = client.get(path)
    assert resp.status_code == 200, (path, resp.status_code)
    return resp.text


# --- A. two names, identical birth data ------------------------------------

@pytest.mark.parametrize("label,path", _ROUTES)
def test_a_second_name_with_the_same_birth_data_is_not_shown_the_first(
        client, saved_chart, echo_llm, label, path):
    first = _view(client, saved_chart, ASHA, path)
    assert ASHA in first, f"{label}: the fake did not put the name on the page"
    second = _view(client, saved_chart, RAVI, path)

    assert echo_llm["n"] == 2, (
        f"{label}: {echo_llm['n']} generations for two differently-named "
        f"visitors with identical birth data; the second was served the first's"
    )
    assert ASHA not in second, f"{label}: {ASHA}'s reading was shown to {RAVI}"
    assert RAVI in second


def _match(client, g_name, b_name, *, swap=False):
    g = {"g_birth_date": "1990-04-12", "g_birth_time": "14:35",
         "g_birth_place": "Mumbai, India"}
    b = {"b_birth_date": "1992-08-03", "b_birth_time": "06:10",
         "b_birth_place": "Delhi, India"}
    if swap:
        g = {k.replace("g_", "b_"): v for k, v in g.items()}
        b = {k.replace("b_", "g_"): v for k, v in b.items()}
    resp = client.post("/matching", data={"g_name": g_name, "b_name": b_name, **g, **b})
    assert resp.status_code == 200, resp.status_code
    return resp.text


@pytest.mark.parametrize("first,second,leaked", [
    ((ASHA, "Bhavnoor"), (RAVI, "Bhavnoor"), ASHA),     # groom changed
    ((ASHA, "Bhavnoor"), (ASHA, "Charvikesh"), "Bhavnoor"),  # bride changed
])
def test_matching_with_either_name_changed_is_a_new_reading(
        client, echo_llm, first, second, leaked):
    _match(client, *first)
    page = _match(client, *second)
    assert echo_llm["n"] == 2, (
        f"{echo_llm['n']} generations; a changed name must be a new reading "
        f"(groom and bride are both in the prompt)"
    )
    assert leaked not in page


# --- B. the durable tier, across a cold start ------------------------------

def test_a_cold_start_does_not_serve_another_names_blob(
        client, saved_chart, echo_llm, fake_gcs, cold_start):
    _view(client, saved_chart, ASHA, "/kundli")
    cold_start()
    second = _view(client, saved_chart, RAVI, "/kundli")

    assert echo_llm["n"] == 2, echo_llm["n"]
    assert ASHA not in second
    blobs = sorted(k for k in fake_gcs if k.startswith("llm/natal/"))
    assert len(blobs) == 2, blobs

    # ...and each name still finds its own blob after yet another cold start.
    cold_start()
    again = _view(client, saved_chart, ASHA, "/kundli")
    assert echo_llm["n"] == 2, "the first name's own blob was not found again"
    assert ASHA in again and RAVI not in again


# --- C. a blob or row written under the OLD key shape is never served ------

def _old_natal_keys():
    from astro_ai import cache
    from astro_ai.routes.deps import PROMPT_PATH

    chart_fp = cache.fingerprint_chart(*BIRTH.values())
    prompt_fp = cache.fingerprint_prompt(PROMPT_PATH)
    return (f"natal:{chart_fp}:en:{prompt_fp}",
            f"llm/natal/en/{prompt_fp}/{chart_fp}.txt")


@pytest.mark.parametrize("name", [RAVI, ""])
def test_a_legacy_named_reading_is_not_served(
        client, saved_chart, echo_llm, fake_gcs, cold_start, name):
    from astro_ai import cache

    sql_key, blob_key = _old_natal_keys()
    legacy = ("## Overview\nDear " + ASHA + ". " + "Legacy reading text. " * 60
              + "\n\n## Detail\n" + "More legacy text. " * 60 + "\n")
    cache.put(sql_key, legacy, route="natal", ttl_days=None)
    fake_gcs[blob_key] = legacy

    page = _view(client, saved_chart, name, "/kundli")
    assert echo_llm["n"] == 1, "the legacy SQLite row was served"
    assert ASHA not in page

    cold_start()
    page = _view(client, saved_chart, name, "/kundli")
    assert echo_llm["n"] == 1, "the new reading was not stored under the new key"
    fake_gcs[blob_key] = legacy
    cold_start()
    page = _view(client, saved_chart, name, "/kundli")
    assert ASHA not in page, "the legacy GCS blob was served after a cold start"


# --- D. no hit-rate regression ----------------------------------------------

@pytest.mark.parametrize("label,path", _ROUTES)
def test_the_same_name_in_another_case_or_spacing_is_one_generation(
        client, saved_chart, echo_llm, label, path):
    for variant in ("Zelphira", "  zelphira ", "ZELPHIRA", "Zelphira\t"):
        _view(client, saved_chart, variant, path)
    assert echo_llm["n"] == 1, (
        f"{label}: {echo_llm['n']} generations for one visitor's name in four spellings"
    )


@pytest.mark.parametrize("label,path", _ROUTES)
def test_a_blank_name_twice_is_one_generation(client, saved_chart, echo_llm, label, path):
    _view(client, saved_chart, "", path)
    _view(client, saved_chart, "   ", path)
    assert echo_llm["n"] == 1, f"{label}: {echo_llm['n']}"


@pytest.mark.parametrize("label,path", _ROUTES)
def test_a_blank_name_does_not_share_with_a_named_one(
        client, saved_chart, echo_llm, label, path):
    _view(client, saved_chart, ASHA, path)
    # A fresh visitor: re-saving the same chart with a blank name keeps the
    # name already on the cookie (session.py dedup), which would not be blank.
    client.cookies.clear()
    page = _view(client, saved_chart, "", path)
    assert echo_llm["n"] == 2, f"{label}: a blank name was served a named reading"
    assert ASHA not in page


def test_matching_with_the_two_people_swapped_is_still_one_generation(client, echo_llm):
    _match(client, ASHA, RAVI)
    _match(client, RAVI, ASHA, swap=True)
    assert echo_llm["n"] == 1, (
        f"{echo_llm['n']} generations; the pair key is sorted so that order "
        f"does not matter, and attaching the names must keep it so"
    )


def test_matching_names_are_normalised_and_blank_is_stable(client, echo_llm):
    _match(client, "Zelphira", "Quentorix")
    _match(client, " ZELPHIRA", "quentorix  ")
    assert echo_llm["n"] == 1, echo_llm["n"]
    _match(client, "", "")
    _match(client, "  ", "")
    assert echo_llm["n"] == 2, echo_llm["n"]


# --- E. the snapshot path builds the same key as the render path -----------

def test_the_snapshot_path_does_not_serve_another_names_reading(
        client, saved_chart, echo_llm, fake_gcs, cold_start):
    from astro_ai.routes import kundli as kundli_routes

    kundli_routes._SNAPSHOT_CREATED_TODAY.clear()
    saved_chart(name=ASHA, **BIRTH)
    assert client.get("/kundli").status_code == 200
    cold_start()
    saved_chart(name=RAVI, **BIRTH)
    assert client.post("/kundli/snapshot").status_code == 200

    assert echo_llm["n"] == 2, "the snapshot path served the first name's blob"
    snapshots = [v for k, v in fake_gcs.items() if not k.startswith("llm/")]
    assert snapshots and all(ASHA not in v for v in snapshots), (
        f"{RAVI}'s shared snapshot carries {ASHA}'s reading"
    )


def test_the_snapshot_and_render_paths_share_one_blob_per_name(
        client, saved_chart, echo_llm, fake_gcs, cold_start):
    """Parity in both directions, for a named seeker: a divergence between the
    two call sites would silently regenerate a reading already paid for."""
    from astro_ai.routes import kundli as kundli_routes

    kundli_routes._SNAPSHOT_CREATED_TODAY.clear()
    saved_chart(name=ASHA, **BIRTH)
    assert client.post("/kundli/snapshot").status_code == 200
    cold_start()
    assert client.get("/kundli").status_code == 200
    cold_start()
    assert client.post("/kundli/snapshot").status_code == 200
    assert echo_llm["n"] == 1, echo_llm["n"]
    assert len([k for k in fake_gcs if k.startswith("llm/natal/")]) == 1


# --- the helper itself -------------------------------------------------------

def test_fingerprint_name_normalises_and_separates():
    from astro_ai import cache

    fp = cache.fingerprint_name
    assert fp("Zelphira") == fp("  ZELPHIRA ") == fp("zelphira\t")
    assert fp("Anil  Kumar") == fp("anil kumar") == fp(" Anil Kumar")
    assert fp("Zelphira") != fp("Quentorix")
    assert fp("") == fp("   ") == fp(None) == "anon"
    assert fp("Zelphira") != "anon"
    assert "zelphira" not in fp("Zelphira").lower()
