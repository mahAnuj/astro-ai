"""`/healthz` is the deploy marker CI waits on — guard its contract.

WHY THIS IS HERE, given the charter in conftest.py.

conftest says every test in this suite corresponds to a defect that actually
shipped. This one does not, and it is admitted knowingly rather than by drift.

The reason: `/healthz` exists only to be consumed by
`.github/workflows/verify-production.yml`, which polls it to decide whether a
deploy has landed before asserting anything against production. That contract
spans a Python file and a YAML file, so nothing type-checks it and no import
would break if it were violated. And its failure mode is silent in the worst
way — rename `revision`, or return it from a template, and the workflow does
not error, it *times out on every push*. The natural response to a gate that
times out is to weaken the wait, at which point the assertions run against the
pre-deploy revision and pass. That is precisely the "gate that cannot fail"
this repo has already paid for twice.

So: a constant shared across two files, with no gate and a silent failure mode
— the #141/#146 lesson. The tests below assert the contract, not the
implementation; the last one reads the workflow itself so the two files cannot
drift apart unnoticed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOW = (Path(__file__).resolve().parent.parent
            / ".github" / "workflows" / "verify-production.yml")


def test_healthz_reports_local_sentinel_off_cloud_run(client, monkeypatch):
    """Off Cloud Run the vars are absent. `revision` must still be a usable
    string — the workflow compares it, so None or "" would make an absent
    endpoint look like a changed revision."""
    monkeypatch.delenv("K_REVISION", raising=False)
    monkeypatch.delenv("BUILD_SHA", raising=False)

    r = client.get("/healthz")

    assert r.status_code == 200
    assert r.json() == {"ok": True, "revision": "local", "build_sha": None}


def test_healthz_echoes_cloud_run_revision_and_build_sha(client, monkeypatch):
    """On Cloud Run, `K_REVISION` is injected automatically and changes on every
    deploy; `BUILD_SHA` is set by the Cloud Build trigger when configured."""
    monkeypatch.setenv("K_REVISION", "astro-ai-00231-xkq")
    monkeypatch.setenv("BUILD_SHA", "7665814" + "a" * 33)

    body = client.get("/healthz").json()

    assert body["revision"] == "astro-ai-00231-xkq"
    assert body["build_sha"] == "7665814" + "a" * 33


def test_healthz_never_invents_a_build_sha(client, monkeypatch):
    """`build_sha` must be null until the trigger really sets it.

    A fallback — the revision, a git SHA baked at build time, anything — would
    let the workflow's EXACT tier claim "this commit is serving" on no
    evidence. Null is the honest answer and keeps it in the weaker tier.
    """
    monkeypatch.delenv("BUILD_SHA", raising=False)
    monkeypatch.setenv("K_REVISION", "astro-ai-00231-xkq")

    assert client.get("/healthz").json()["build_sha"] is None


def test_healthz_does_no_storage_io(client, monkeypatch):
    """Polled every 15s during a deploy. The bucket is in the US and Cloud Run
    is in asia-south1, so a single blob read here would put a cross-continent
    round-trip on the one route that has to answer while the app is unhealthy
    (#144's lesson, applied before it happens rather than after)."""
    from astro_ai import storage

    for name in dir(storage):
        fn = getattr(storage, name)
        if (not name.startswith("_") and callable(fn)
                and getattr(fn, "__module__", None) == "astro_ai.storage"):
            monkeypatch.setattr(
                storage, name,
                lambda *a, _n=name, **k: pytest.fail(f"/healthz called storage.{_n}"),
            )

    assert client.get("/healthz").status_code == 200


def test_healthz_is_not_indexable(client):
    """No template, so the `meta_robots` Jinja block that covers /admin and /r
    cannot apply. The header is the non-HTML equivalent, and it must not be in
    the sitemap either."""
    r = client.get("/healthz")

    assert "noindex" in r.headers.get("x-robots-tag", "")
    assert "healthz" not in client.get("/sitemap.xml").text


def test_healthz_is_not_cached(client):
    """A cached /healthz is worse than none: CI would poll a stale revision
    string and time out straight through a perfectly good deploy."""
    cc = client.get("/healthz").headers.get("cache-control", "")

    assert "no-store" in cc


def test_workflow_only_reads_fields_healthz_actually_emits(client):
    """The cross-file gate this module exists for.

    Extracts the jq field paths the deploy-wait step reads out of
    /healthz, and asserts the endpoint emits every one. Renaming a key in
    health.py without touching the workflow turns the deploy gate into a
    permanent timeout; this fails loudly instead.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("- name: Wait for the deploy", 1)[1].split("- name:", 1)[0]

    fields = set(re.findall(r"jq\s+-[a-zA-Z]*\s+'\.([A-Za-z_][A-Za-z0-9_]*)", step))

    assert fields, "found no jq field reads — this test would be vacuous"
    assert fields <= set(client.get("/healthz").json()), (
        f"workflow reads {sorted(fields)} from /healthz, which does not emit all of them"
    )
