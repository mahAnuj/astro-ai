"""#1105 -- no code path used to delete personal data; these do.

Covers `storage.delete`, `users.delete_user`, `users.delete_readings_for_chart`,
`POST /account/delete`, the reading cleanup in `POST /delete-chart`, and the
durable natal blobs (`llm/natal/...`) both of them erase.

The fake below stands in for GCS at the `storage.get_json` / `storage.update_json`
seam, which is where users.py and subscribers.py read and write. It keeps the real
contract that matters here: `update_json` returns None when storage is down (callers
must treat that as "not deleted"), and it persists exactly what the mutator returns, so
a mutator returning None writes `null` over the whole file. `storage.delete` is
faked too: it returns False for a key in `fake.blob_down` and True otherwise
(including for an absent key, like the real one), and removes the key from
`fake.natal` so a test can see what survived.

Mutation rows: scripts/mutations/account_deletion.py.
"""
from __future__ import annotations

import copy
import json

import pytest
from fastapi.testclient import TestClient

from astro_ai import session as S
from astro_ai import storage, subscribers, users
from astro_ai.llm import BirthDetails
from astro_ai.routes.kundli import _natal_cache_keys, natal_blob_keys

ALICE = {"sub": "sub-alice", "email": "alice@example.test", "name": "Alice"}
BOB = {"sub": "sub-bob", "email": "bob@example.test", "name": "Bob"}
CHART_A = dict(id="aaaa1111", name="Alice", birth_date="1990-04-12",
               birth_time="14:35", birth_place="Mumbai, India")
CHART_A2 = dict(id="aaaa2222", name="Alice2", birth_date="1991-05-13",
                birth_time="08:10", birth_place="Pune, India")
# Same birth data as CHART_A under another name: a different seeker's reading,
# which lives in its own blob and must survive Alice's deletion.
CHART_NAMESAKE = dict(CHART_A, id="cccc3333", name="Someone Else")


def _details(chart):
    return BirthDetails(name=chart["name"], birth_date=chart["birth_date"],
                        birth_time=chart["birth_time"], birth_place=chart["birth_place"])


def _blob_keys(chart):
    return [_natal_cache_keys(_details(chart), lang=lang)[1] for lang in ("en", "hi")]


def _reading(rid, chart_id):
    return {"id": rid, "kind": "natal", "chart_id": chart_id, "title": "t",
            "body": "body text", "created_at": "2026-11-01T00:00:00+00:00", "meta": {}}


@pytest.fixture
def fake_store(monkeypatch):
    """In-memory users.json + subscribers.json. `down` makes a key unwritable."""
    blobs = {
        users.USERS_KEY: {"users": [
            {**ALICE, "created_at": "x", "last_seen_at": "x",
             "charts": [CHART_A, CHART_A2], "active_id": CHART_A["id"],
             "readings": [_reading("r1", CHART_A["id"]), _reading("r2", CHART_A2["id"]),
                          _reading("r3", CHART_A["id"])]},
            {**BOB, "created_at": "x", "last_seen_at": "x",
             "charts": [CHART_A], "readings": [_reading("rb", CHART_A["id"])]},
        ]},
        subscribers.SUBSCRIBERS_KEY: {"subscribers": [
            {"email": ALICE["email"]}, {"email": BOB["email"]}]},
    }
    down: set[str] = set()
    blob_down: set[str] = set()
    natal = {k: "reading" for c in (CHART_A, CHART_A2, CHART_NAMESAKE)
             for k in _blob_keys(c)}

    def delete(key):
        if key in blob_down:
            return False
        natal.pop(key, None)
        return True

    def get_json(key):
        return copy.deepcopy(blobs.get(key))

    def update_json(key, mutator, *, default=None, max_retries=5):
        if key in down:
            return None
        new = mutator(copy.deepcopy(blobs.get(key, default)))
        # The real update_json writes json.dumps(<whatever the mutator returned>):
        # a None becomes the text `null` and the next writer rebuilds an empty
        # user list. Round-trip here so a mutator that returns None is visible.
        blobs[key] = json.loads(json.dumps(new))
        return copy.deepcopy(new)

    monkeypatch.setattr(storage, "get_json", get_json)
    monkeypatch.setattr(storage, "update_json", update_json)
    monkeypatch.setattr(storage, "delete", delete)
    return type("Fake", (), {"blobs": blobs, "down": down, "natal": natal,
                             "blob_down": blob_down})


def _cookie(user=ALICE, charts=(CHART_A, CHART_A2)):
    return S._serializer().dumps({
        "user": {"email": user["email"], "name": user["name"], "sub": user["sub"],
                 "since": "2026-11-01T00:00:00+00:00"},
        "charts": list(charts), "active_id": charts[0]["id"] if charts else None,
        "lang": "hi",
    })


@pytest.fixture
def signed_in(client):
    client.cookies.set(S.COOKIE_NAME, _cookie())
    return client


def _subs(fake):
    return [s["email"] for s in fake.blobs[subscribers.SUBSCRIBERS_KEY]["subscribers"]]


def _subs_of(fake):
    return [u["sub"] for u in fake.blobs[users.USERS_KEY]["users"]]


def _session_cookie_cleared(resp) -> bool:
    headers = [h for h in resp.headers.get_list("set-cookie")
               if h.startswith(S.COOKIE_NAME + "=")]
    return len(headers) == 1 and ('=""' in headers[0] or "Max-Age=0" in headers[0])


# -- POST /account/delete -----------------------------------------------------
def test_account_delete_removes_record_readings_and_subscription(signed_in, fake_store):
    resp = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                          follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/"
    assert _subs_of(fake_store) == [BOB["sub"]], "Alice's record (charts+readings) must go"
    assert _subs(fake_store) == [BOB["email"]]
    bob = fake_store.blobs[users.USERS_KEY]["users"][0]
    assert [r["id"] for r in bob["readings"]] == ["rb"], "another user's data must survive"
    assert bob["charts"] == [CHART_A]
    assert _session_cookie_cleared(resp)


def test_account_delete_clears_the_whole_session(signed_in, fake_store):
    """Replays what the browser would hold afterwards: user, charts and lang gone."""
    resp = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                          follow_redirects=False)
    header = next(h for h in resp.headers.get_list("set-cookie")
                  if h.startswith(S.COOKIE_NAME + "="))
    value = header.split("=", 1)[1].split(";", 1)[0].strip('"')
    after = TestClient(signed_in.app)
    after.cookies.set(S.COOKIE_NAME, value)
    assert after.get("/account", follow_redirects=False).status_code == 303
    data = S._serializer().loads(value) if value else {}
    assert not data.get("user") and not data.get("charts") and not data.get("lang")


@pytest.mark.parametrize("confirm", [None, "", "delete", "Delete", " DELETE", "DELETE "])
def test_account_delete_needs_the_exact_confirmation(signed_in, fake_store, confirm):
    data = {} if confirm is None else {"confirm": confirm}
    before = copy.deepcopy(fake_store.blobs)
    resp = signed_in.post("/account/delete", data=data, follow_redirects=False)
    assert resp.status_code == 400
    assert fake_store.blobs == before, "a refused request must touch nothing"
    assert not [h for h in resp.headers.get_list("set-cookie")
                if h.startswith(S.COOKIE_NAME + "=")]


def test_account_delete_signed_out_redirects_and_touches_nothing(client, fake_store):
    before = copy.deepcopy(fake_store.blobs)
    resp = client.post("/account/delete", data={"confirm": "DELETE"},
                       follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/"
    assert fake_store.blobs == before


def test_account_delete_storage_failure_is_503_and_keeps_the_session(signed_in, fake_store):
    fake_store.down.add(users.USERS_KEY)
    resp = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                          follow_redirects=False)
    assert resp.status_code == 503
    assert "try again" in resp.text
    assert not [h for h in resp.headers.get_list("set-cookie")
                if h.startswith(S.COOKIE_NAME + "=")], "session must survive a failed delete"
    assert ALICE["sub"] in _subs_of(fake_store)
    # The other half still ran, and a retry once storage is back finishes the job.
    assert _subs(fake_store) == [BOB["email"]]
    fake_store.down.clear()
    retry = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                           follow_redirects=False)
    assert retry.status_code == 303
    assert _subs_of(fake_store) == [BOB["sub"]]


def test_account_delete_subscriber_failure_is_503(signed_in, fake_store):
    fake_store.down.add(subscribers.SUBSCRIBERS_KEY)
    resp = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                          follow_redirects=False)
    assert resp.status_code == 503
    assert not [h for h in resp.headers.get_list("set-cookie")
                if h.startswith(S.COOKIE_NAME + "=")]
    assert _subs_of(fake_store) == [BOB["sub"]], "the record half already succeeded"


def test_account_delete_erases_each_charts_natal_blobs_for_both_languages(signed_in, fake_store):
    assert len(fake_store.natal) == 6
    resp = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                          follow_redirects=False)
    assert resp.status_code == 303
    assert sorted(fake_store.natal) == sorted(_blob_keys(CHART_NAMESAKE)), \
        "Alice's four blobs (2 charts x en/hi) go; a different name's blob stays"


def test_account_delete_blob_failure_is_503_keeps_session_and_the_record(signed_in, fake_store):
    stuck = _blob_keys(CHART_A2)[1]
    fake_store.blob_down.add(stuck)
    resp = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                          follow_redirects=False)
    assert resp.status_code == 503 and "try again" in resp.text
    assert not [h for h in resp.headers.get_list("set-cookie")
                if h.startswith(S.COOKIE_NAME + "=")], "session must survive a failed delete"
    # The record is the only cross-device chart list, so it stays for the retry;
    # the subscription is not held hostage to the blob outage.
    assert ALICE["sub"] in _subs_of(fake_store)
    assert _subs(fake_store) == [BOB["email"]]
    assert stuck in fake_store.natal
    assert not set(_blob_keys(CHART_A)) & set(fake_store.natal), "the others still went"
    # Retry converges once storage is back, keys recomputed from the kept charts.
    fake_store.blob_down.clear()
    retry = signed_in.post("/account/delete", data={"confirm": "DELETE"},
                           follow_redirects=False)
    assert retry.status_code == 303
    assert _subs_of(fake_store) == [BOB["sub"]]
    assert sorted(fake_store.natal) == sorted(_blob_keys(CHART_NAMESAKE))


def test_account_delete_retry_finds_the_blobs_from_the_record_alone(client, fake_store):
    """A fresh device has no charts in its cookie; the record must supply them."""
    client.cookies.set(S.COOKIE_NAME, _cookie(charts=()))
    resp = client.post("/account/delete", data={"confirm": "DELETE"},
                       follow_redirects=False)
    assert resp.status_code == 303
    assert sorted(fake_store.natal) == sorted(_blob_keys(CHART_NAMESAKE))


def test_natal_erasure_keys_are_the_keys_the_render_path_writes():
    """Drift guard: erasure must be derived from `_natal_cache_keys`, the one
    builder both /kundli and the snapshot path write their blob with."""
    details = _details(CHART_A)
    written = {_natal_cache_keys(details, lang=lang)[1] for lang in ("en", "hi")}
    assert set(natal_blob_keys(details)) == written and len(written) == 2
    assert all(k.startswith("llm/natal/") for k in written)


def test_account_page_offers_the_delete_form(signed_in, fake_store):
    html = signed_in.get("/account").text
    assert 'action="/account/delete"' in html and 'name="confirm"' in html


# -- users.py -----------------------------------------------------------------
def test_delete_user_is_idempotent_and_reports_storage_failure(fake_store):
    assert users.delete_user(ALICE["sub"]) is True
    assert users.delete_user(ALICE["sub"]) is True, "absent user is success"
    assert users.find_by_sub(BOB["sub"]) is not None
    fake_store.down.add(users.USERS_KEY)
    assert users.delete_user(BOB["sub"]) is False
    assert users.delete_user("") is False


def test_delete_readings_for_chart_keeps_other_charts_and_the_record(fake_store):
    assert users.delete_readings_for_chart(ALICE["sub"], CHART_A["id"]) is True
    assert [r.id for r in users.list_readings(ALICE["sub"])] == ["r2"]
    assert users.find_by_sub(ALICE["sub"]) is not None
    assert [r.id for r in users.list_readings(BOB["sub"])] == ["rb"], \
        "same chart id on another user's record is not ours to delete"
    assert users.delete_readings_for_chart("nobody", CHART_A["id"]) is True
    # Scoping the other way round: Bob asking for chart A's id must not touch
    # Alice's record, which comes first in the store (#1105 QA round 1).
    assert users.delete_readings_for_chart(BOB["sub"], CHART_A["id"]) is True
    assert [r.id for r in users.list_readings(ALICE["sub"])] == ["r2"]
    assert [r.id for r in users.list_readings(BOB["sub"])] == []


# -- POST /delete-chart -------------------------------------------------------
def test_delete_chart_removes_that_charts_readings_only(signed_in, fake_store):
    resp = signed_in.post("/delete-chart", data={"chart_id": CHART_A["id"]},
                          follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/"
    assert [r.id for r in users.list_readings(ALICE["sub"])] == ["r2"]
    assert [r.id for r in users.list_readings(BOB["sub"])] == ["rb"]


def test_delete_chart_removes_only_that_charts_natal_blobs(signed_in, fake_store):
    resp = signed_in.post("/delete-chart", data={"chart_id": CHART_A["id"]},
                          follow_redirects=False)
    assert resp.status_code == 303
    assert set(fake_store.natal) == set(_blob_keys(CHART_A2)) | set(_blob_keys(CHART_NAMESAKE))


def test_delete_chart_still_redirects_when_the_blob_delete_fails(signed_in, fake_store):
    fake_store.blob_down.update(_blob_keys(CHART_A))
    resp = signed_in.post("/delete-chart", data={"chart_id": CHART_A["id"]},
                          follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/"
    assert [r.id for r in users.list_readings(ALICE["sub"])] == ["r2"], \
        "the readings cleanup still ran"


def test_delete_chart_still_redirects_when_the_blob_delete_raises(signed_in, fake_store,
                                                                  monkeypatch):
    def boom(key):
        raise RuntimeError("storage exploded")

    monkeypatch.setattr(storage, "delete", boom)
    resp = signed_in.post("/delete-chart", data={"chart_id": CHART_A["id"]},
                          follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/"


def test_delete_chart_still_redirects_when_reading_cleanup_raises(signed_in, fake_store,
                                                                  monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("storage exploded")

    monkeypatch.setattr(users, "delete_readings_for_chart", boom)
    resp = signed_in.post("/delete-chart", data={"chart_id": CHART_A["id"]},
                          follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/"


# -- a second device still signed in after the account is gone ----------------
# Session cookies are stateless (1 year), so deleting on device 1 leaves device 2
# signed in. Its next chart removal / reading save finds no record for the sub.
# That must change NOTHING: before the fix the mutators returned None, the real
# update_json wrote `null`, and the next write rebuilt users.json as empty
# (QA on PR #1173: Bob's record gone).
def _delete_alice_on_device_one(client, fake_store):
    client.cookies.set(S.COOKIE_NAME, _cookie())
    resp = client.post("/account/delete", data={"confirm": "DELETE"},
                       follow_redirects=False)
    assert resp.status_code == 303
    assert _subs_of(fake_store) == [BOB["sub"]]


def test_stale_device_delete_chart_after_account_delete_keeps_other_users(client, fake_store):
    _delete_alice_on_device_one(client, fake_store)
    before = copy.deepcopy(fake_store.blobs[users.USERS_KEY])
    client.cookies.set(S.COOKIE_NAME, _cookie())  # device 2: same cookie, never cleared
    resp = client.post("/delete-chart", data={"chart_id": CHART_A2["id"]},
                       follow_redirects=False)
    assert resp.status_code == 303
    assert fake_store.blobs[users.USERS_KEY] == before
    assert users.find_by_sub(BOB["sub"]) is not None


def test_save_charts_and_save_reading_for_a_missing_user_change_nothing(fake_store):
    assert users.delete_user(ALICE["sub"]) is True
    before = copy.deepcopy(fake_store.blobs[users.USERS_KEY])
    coll = users.ChartCollection(charts=(), active_id=None)
    assert users.save_charts(ALICE["sub"], coll) is False
    assert users.save_reading(ALICE["sub"], "natal", CHART_A["id"], "t", "body") is False
    assert fake_store.blobs[users.USERS_KEY] == before
    assert [u["sub"] for u in fake_store.blobs[users.USERS_KEY]["users"]] == [BOB["sub"]]
    # and a present user still saves and reports True
    assert users.save_reading(BOB["sub"], "natal", CHART_A["id"], "t", "body") is True
    assert users.save_charts(BOB["sub"], coll) is True


# -- storage.delete -----------------------------------------------------------
class _Blob:
    def __init__(self, exc=None):
        self.exc, self.deleted = exc, 0

    def delete(self):
        self.deleted += 1
        if self.exc:
            raise self.exc


def test_storage_delete_success_404_and_failure(monkeypatch):
    from google.api_core import exceptions as gapi

    ok = _Blob()
    monkeypatch.setattr(storage, "_blob", lambda key: ok)
    assert storage.delete("k") is True and ok.deleted == 1

    monkeypatch.setattr(storage, "_blob", lambda key: _Blob(gapi.NotFound("gone")))
    assert storage.delete("k") is True, "already absent is the state asked for"

    class Coded(Exception):
        code = 404

    monkeypatch.setattr(storage, "_blob", lambda key: _Blob(Coded()))
    assert storage.delete("k") is True

    monkeypatch.setattr(storage, "_blob", lambda key: _Blob(gapi.Forbidden("no")))
    assert storage.delete("k") is False

    monkeypatch.setattr(storage, "_blob", lambda key: _Blob(RuntimeError("boom")))
    assert storage.delete("k") is False


def test_storage_delete_unconfigured_is_false(monkeypatch):
    monkeypatch.delenv(storage._BUCKET_ENV, raising=False)
    assert storage.delete("k") is False
