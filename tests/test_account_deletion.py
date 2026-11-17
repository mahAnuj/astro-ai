"""#1105 -- no code path used to delete personal data; these do.

Covers `storage.delete`, `users.delete_user`, `users.delete_readings_for_chart`,
`POST /account/delete` and the reading cleanup in `POST /delete-chart`.

The fake below stands in for GCS at the `storage.get_json` / `storage.update_json`
seam, which is where users.py and subscribers.py read and write. It keeps the real
contract that matters here: `update_json` returns None when storage is down (callers
must treat that as "not deleted"), and it persists exactly what the mutator returns, so
a mutator returning None writes `null` over the whole file.

Mutation rows: scripts/mutations/account_deletion.py.
"""
from __future__ import annotations

import copy
import json

import pytest
from fastapi.testclient import TestClient

from astro_ai import session as S
from astro_ai import storage, subscribers, users

ALICE = {"sub": "sub-alice", "email": "alice@example.test", "name": "Alice"}
BOB = {"sub": "sub-bob", "email": "bob@example.test", "name": "Bob"}
CHART_A = dict(id="aaaa1111", name="Alice", birth_date="1990-04-12",
               birth_time="14:35", birth_place="Mumbai, India")
CHART_A2 = dict(id="aaaa2222", name="Alice2", birth_date="1991-05-13",
                birth_time="08:10", birth_place="Pune, India")


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
    return type("Fake", (), {"blobs": blobs, "down": down})


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
