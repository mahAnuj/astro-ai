"""#1104: a Cloud Run revision refuses to start when a secret is unset, blank or a
public dev placeholder; local dev keeps the fallbacks.

Each test is a defect that could ship: the fallbacks are committed in this public
repo, and production deploys through a Cloud Build trigger that never runs
deploy.sh's own check. The lifespan is entered for real (`with TestClient(app)`);
only the geocoding warm-up is neutralised so nothing touches the network.
"""
from __future__ import annotations

import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from astro_ai import session, subscribers
from astro_ai import main as main_mod
from astro_ai.main import app
from astro_ai.routes import deps

GOOD_ADMIN = "unit-test-admin-password-7f3a"
GOOD_COOKIE = "unit-test-cookie-secret-91c2"
NAMES = ("ADMIN_PASSWORD", "ASTRO_AI_COOKIE_SECRET")
PLACEHOLDERS = (deps._ADMIN_DEV_FALLBACK, session._DEV_SECRET)


@pytest.fixture(autouse=True)
def _no_warmup(monkeypatch):
    monkeypatch.setattr(main_mod, "_warm_process_globals", lambda: None)


def _env(monkeypatch, *, revision, admin=GOOD_ADMIN, cookie=GOOD_COOKIE):
    for name, value in zip(NAMES, (admin, cookie)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    if revision:
        monkeypatch.setenv("K_REVISION", "astro-ai-00001-abc")
    else:
        monkeypatch.delenv("K_REVISION", raising=False)


def _bad_values():
    yield "unset", None
    yield "empty", ""
    yield "whitespace", "   "
    for p in PLACEHOLDERS:
        yield f"placeholder:{p}", p


@pytest.mark.parametrize("which", NAMES)
@pytest.mark.parametrize("label,bad", list(_bad_values()), ids=lambda v: v if isinstance(v, str) else None)
def test_cloud_run_refuses_to_start_on_a_bad_secret(monkeypatch, which, label, bad):
    kw = {"admin": GOOD_ADMIN, "cookie": GOOD_COOKIE}
    kw["admin" if which == "ADMIN_PASSWORD" else "cookie"] = bad
    _env(monkeypatch, revision=True, **kw)
    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    msg = str(exc.value)
    assert which in msg
    # The other, healthy variable is not blamed, and no value leaks into the message.
    other = next(n for n in NAMES if n != which)
    assert other not in msg
    for secret in (GOOD_ADMIN, GOOD_COOKIE, *PLACEHOLDERS):
        assert secret not in msg


def test_cloud_run_names_every_bad_secret(monkeypatch):
    _env(monkeypatch, revision=True, admin=None, cookie=None)
    with pytest.raises(RuntimeError) as exc:
        with TestClient(app):
            pass
    assert all(n in str(exc.value) for n in NAMES)


def test_cloud_run_starts_with_real_values(monkeypatch):
    _env(monkeypatch, revision=True)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


def test_the_refusal_comes_before_the_warm_up(monkeypatch):
    calls = []
    monkeypatch.setattr(main_mod, "_warm_process_globals", lambda: calls.append(1))
    _env(monkeypatch, revision=True, admin=None)
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass
    assert calls == []


def test_local_dev_keeps_the_fallbacks(monkeypatch):
    _env(monkeypatch, revision=False, admin=None, cookie=None)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        r = client.get("/admin/ops", auth=("admin", deps._ADMIN_DEV_FALLBACK))
        assert r.status_code != 401
        assert client.get("/admin/ops", auth=("admin", "wrong")).status_code == 401
    assert session.cookie_secret() == session._DEV_SECRET


def test_insecure_secrets_reads_the_environment_at_call_time(monkeypatch):
    _env(monkeypatch, revision=False, admin=None)
    assert deps.insecure_secrets() == ["ADMIN_PASSWORD"]
    monkeypatch.setenv("ADMIN_PASSWORD", GOOD_ADMIN)
    assert deps.insecure_secrets() == []


# --- unsubscribe key -------------------------------------------------------


def _old_token(email: str, secret: str) -> str:
    # The formula as it stood before #1104: key = the env value's bytes.
    return hmac.new(secret.encode(), email.strip().lower().encode(), hashlib.sha256).hexdigest()[:24]


def test_unsubscribe_tokens_already_sent_still_verify(monkeypatch):
    monkeypatch.setenv("ASTRO_AI_COOKIE_SECRET", GOOD_COOKIE)
    sent = _old_token("reader@example.com", GOOD_COOKIE)
    assert subscribers.unsubscribe_token("  Reader@Example.com ") == sent
    assert subscribers.verify_unsubscribe_token("reader@example.com", sent)


def test_unsubscribe_fallback_is_not_the_admin_password(monkeypatch):
    monkeypatch.delenv("ASTRO_AI_COOKIE_SECRET", raising=False)
    assert subscribers._unsubscribe_secret() != deps._ADMIN_DEV_FALLBACK.encode()
    assert subscribers._unsubscribe_secret() == session._DEV_SECRET.encode()
    # ... so a token minted with the admin placeholder no longer verifies.
    forged = _old_token("reader@example.com", deps._ADMIN_DEV_FALLBACK)
    assert not subscribers.verify_unsubscribe_token("reader@example.com", forged)
