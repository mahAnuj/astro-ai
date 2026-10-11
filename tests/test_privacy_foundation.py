"""Privacy foundation (#255 part 1): keyed identity, Secure cookie, token usage,
coarse profiling fields.

Each test pins an observable property; none recomputes the value under test.
"""
from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from astro_ai import identity, profiling, providers


# ─── identity ──────────────────────────────────────────────────────────────


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setenv("ASTRO_AI_COOKIE_SECRET", "secret-one")


def test_identity_key_is_stable(secret):
    assert identity.identity_key("Asha", "1990-01-01", "10:30", "Delhi") == \
        identity.identity_key("Asha", "1990-01-01", "10:30", "Delhi")


def test_identity_key_depends_on_the_secret(monkeypatch):
    monkeypatch.setenv("ASTRO_AI_COOKIE_SECRET", "secret-one")
    a = identity.identity_key("Asha", "1990-01-01")
    monkeypatch.setenv("ASTRO_AI_COOKIE_SECRET", "secret-two")
    assert identity.identity_key("Asha", "1990-01-01") != a


def test_identity_key_is_not_an_unkeyed_hash(secret):
    # An unkeyed sha256 of the input is what an attacker can precompute over
    # the small birth-details space; the key must not equal it.
    key = identity.identity_key("a", "b")
    for joined in ("a\x1fb", "a|b", "a b", "ab"):
        assert key != hashlib.sha256(joined.encode()).hexdigest()
    assert len(key) == 64


def test_identity_key_part_boundaries_matter(secret):
    assert identity.identity_key("a|b", "c") != identity.identity_key("a", "b|c")
    assert identity.identity_key("ab", "c") != identity.identity_key("a", "bc")


def test_identity_key_normalises_case_and_whitespace(secret):
    assert identity.identity_key("  New   Delhi ", "X") == identity.identity_key("new delhi", "x")


def test_short_key_is_eight_hex_chars(secret):
    short = identity.short_key(identity.identity_key("a", "b"))
    assert len(short) == 8
    int(short, 16)  # raises if not hex


# ─── cookie flags ──────────────────────────────────────────────────────────


def _set_cookie(client) -> str:
    r = client.post("/lang", data={"lang": "hi", "next": "/"}, follow_redirects=False)
    assert r.status_code == 303
    return r.headers["set-cookie"]


def test_session_cookie_is_secure_on_cloud_run(client, monkeypatch):
    monkeypatch.setenv("K_REVISION", "bhagya-00042")
    header = _set_cookie(client).lower()
    assert "secure" in [p.strip() for p in header.split(";")]
    assert "httponly" in header
    assert "samesite=lax" in header


def test_session_cookie_is_not_secure_in_local_dev(client, monkeypatch):
    monkeypatch.delenv("K_REVISION", raising=False)
    header = _set_cookie(client).lower()
    assert "secure" not in [p.strip() for p in header.split(";")]
    assert "httponly" in header


# ─── token usage ───────────────────────────────────────────────────────────


def _fake_client(usage):
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="a reading"),
                                 finish_reason="stop")],
        usage=usage,
    )
    completions = SimpleNamespace(create=lambda **kw: resp)
    return lambda **kw: SimpleNamespace(chat=SimpleNamespace(completions=completions))


def _call(monkeypatch, usage):
    cfg = providers.ProviderConfig("groq120", "https://x", "openai/gpt-oss-120b", "GROQ_API_KEY")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(providers, "OpenAI", _fake_client(usage))
    return providers._call_one(cfg, [{"role": "user", "content": "x"}])


def test_last_used_tokens_reports_total_when_provider_sends_usage(monkeypatch):
    _call(monkeypatch, SimpleNamespace(total_tokens=2180, completion_tokens=300))
    assert providers.last_used_tokens() == 2180


def test_last_used_tokens_is_none_when_provider_sends_no_usage(monkeypatch):
    _call(monkeypatch, SimpleNamespace(total_tokens=2180))
    assert providers.last_used_tokens() == 2180
    # A later call without usage must not inherit the previous figure.
    _call(monkeypatch, None)
    assert providers.last_used_tokens() is None


# ─── profiling ─────────────────────────────────────────────────────────────


def _summary(monkeypatch, kundlis):
    monkeypatch.setattr(profiling.storage, "get_json", lambda k: None)
    monkeypatch.setattr(profiling.storage, "put_json", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(
        profiling.events, "recent",
        lambda types, days, limit: kundlis if types == ["form_kundli"] else [],
    )
    return profiling.audience_summary(days=30, force_refresh=True)


def _labels(rows):
    return {r["label"]: r["count"] for r in rows}


def test_coarse_profile_returns_band_and_city_only():
    out = profiling.coarse_profile("1900-05-05", "bombay, Maharashtra, India")
    assert set(out) == {"age_band", "city"}
    assert out["city"] == "Mumbai"
    assert out["age_band"] == "unknown"  # >120 years ago


def test_audience_summary_reads_new_shape_events(monkeypatch):
    out = _summary(monkeypatch, [
        {"type": "form_kundli", "data": {"age_band": "25-34", "city": "Pune", "lang": "en"}},
        {"type": "form_kundli", "data": {"age_band": "25-34", "city": "Pune", "lang": "hi"}},
    ])
    assert _labels(out["age_bands"]) == {"25-34": 2}
    assert _labels(out["top_cities"]) == {"Pune": 2}


def test_audience_summary_still_reads_legacy_raw_events(monkeypatch):
    year = profiling.date.today().year - 30
    out = _summary(monkeypatch, [
        {"type": "form_kundli", "data": {"birth_date": f"{year}-03-04",
                                         "birth_place": "Gurugram, Haryana", "lang": "en"}},
    ])
    assert _labels(out["age_bands"]) == {"25-34": 1}
    assert _labels(out["top_cities"]) == {"Gurgaon": 1}
