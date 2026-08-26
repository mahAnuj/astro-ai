"""`/health` is the deploy marker CI waits on — guard its contract.

WHY THIS IS HERE, given the charter in conftest.py.

conftest says every test in this suite corresponds to a defect that actually
shipped. This one does not, and it is admitted knowingly rather than by drift.

The reason: `/health` exists only to be consumed by
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

The PATH is part of that contract too, and was the first thing to break it:
the endpoint originally answered on `/healthz`, which Google infrastructure
intercepts in front of Cloud Run, so the gate polled a URL that never reached
the app and timed out on its first run. `test_workflow_polls_the_path_the_app_serves`
below pins the two together; the measurement is in health.py.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

WORKFLOW = (Path(__file__).resolve().parent.parent
            / ".github" / "workflows" / "verify-production.yml")


def test_health_reports_local_sentinel_off_cloud_run(client, monkeypatch):
    """Off Cloud Run the vars are absent. `revision` must still be a usable
    string — the workflow compares it, so None or "" would make an absent
    endpoint look like a changed revision."""
    monkeypatch.delenv("K_REVISION", raising=False)
    monkeypatch.delenv("BUILD_SHA", raising=False)

    r = client.get("/health")

    assert r.status_code == 200
    assert r.json() == {"ok": True, "revision": "local", "build_sha": None}


def test_health_echoes_cloud_run_revision_and_build_sha(client, monkeypatch):
    """On Cloud Run, `K_REVISION` is injected automatically and changes on every
    deploy; `BUILD_SHA` is set by the Cloud Build trigger when configured."""
    monkeypatch.setenv("K_REVISION", "astro-ai-00231-xkq")
    monkeypatch.setenv("BUILD_SHA", "7665814" + "a" * 33)

    body = client.get("/health").json()

    assert body["revision"] == "astro-ai-00231-xkq"
    assert body["build_sha"] == "7665814" + "a" * 33


def test_health_never_invents_a_build_sha(client, monkeypatch):
    """`build_sha` must be null until the trigger really sets it.

    A fallback — the revision, a git SHA baked at build time, anything — would
    let the workflow's EXACT tier claim "this commit is serving" on no
    evidence. Null is the honest answer and keeps it in the weaker tier.
    """
    monkeypatch.delenv("BUILD_SHA", raising=False)
    monkeypatch.setenv("K_REVISION", "astro-ai-00231-xkq")

    assert client.get("/health").json()["build_sha"] is None


def test_health_does_no_storage_io(client, monkeypatch):
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
                lambda *a, _n=name, **k: pytest.fail(f"/health called storage.{_n}"),
            )

    assert client.get("/health").status_code == 200


def test_health_is_not_indexable(client):
    """No template, so the `meta_robots` Jinja block that covers /admin and /r
    cannot apply. The header is the non-HTML equivalent, and it must not be in
    the sitemap either."""
    r = client.get("/health")

    assert "noindex" in r.headers.get("x-robots-tag", "")
    # Compare parsed <loc> paths, not a substring: the sitemap legitimately
    # contains /learn/chronic-health-issues-kundli/, so `"health" not in text`
    # would fail on an unrelated article and read as this endpoint leaking.
    locs = re.findall(r"<loc>([^<]+)</loc>", client.get("/sitemap.xml").text)
    assert locs, "sitemap yielded no <loc> entries — this assertion would be vacuous"
    assert "/health" not in {urlsplit(u).path.rstrip("/") for u in locs}


def test_health_is_not_cached(client):
    """A cached /health is worse than none: CI would poll a stale revision
    string and time out straight through a perfectly good deploy."""
    cc = client.get("/health").headers.get("cache-control", "")

    assert "no-store" in cc


def test_workflow_polls_the_path_the_app_serves(client):
    """The path is half the cross-file contract, and it is the half that broke.

    The deploy gate's first run (32957675512) timed out after ~12 min and
    skipped all seven downstream steps, because it polled `/healthz` — which
    Google infrastructure intercepts in front of Cloud Run, so it never reaches
    this app at all. Every other path, including invented ones, gets through
    firebase.json's catch-all rewrite. The measurement is in health.py.

    Two assertions, and the second is not redundant: renaming the route back to
    `/healthz` *and* updating the workflow to match would satisfy the first and
    reproduce the outage exactly. `/healthz` is unusable here regardless of how
    consistently it is spelled.
    """
    step = (WORKFLOW.read_text(encoding="utf-8")
            .split("- name: Wait for the deploy", 1)[1].split("- name:", 1)[0])

    polled = set(re.findall(r'"\$SITE(/[A-Za-z0-9._~/-]*)"', step))

    assert polled, "found no \"$SITE/...\" poll URL — this test would be vacuous"
    for path in polled:
        assert client.get(path).status_code == 200, (
            f"deploy gate polls {path}, which this app does not serve — the gate "
            f"would time out on every push"
        )
        assert path != "/healthz", (
            "/healthz is intercepted by Google infrastructure before it reaches "
            "Cloud Run and can never answer in production, however the route is "
            "spelled locally — see the comment in src/astro_ai/routes/health.py"
        )


def test_workflow_only_reads_fields_health_actually_emits(client):
    """The cross-file gate this module exists for.

    Extracts the jq field paths the deploy-wait step reads out of
    /health, and asserts the endpoint emits every one. Renaming a key in
    health.py without touching the workflow turns the deploy gate into a
    permanent timeout; this fails loudly instead.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    step = text.split("- name: Wait for the deploy", 1)[1].split("- name:", 1)[0]

    fields = set(re.findall(r"jq\s+-[a-zA-Z]*\s+'\.([A-Za-z_][A-Za-z0-9_]*)", step))

    assert fields, "found no jq field reads — this test would be vacuous"
    assert fields <= set(client.get("/health").json()), (
        f"workflow reads {sorted(fields)} from /health, which does not emit all of them"
    )
