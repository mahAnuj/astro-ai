"""Issue provenance (#361): every test is a way the loop could act on an outsider's issue.

WHY THESE EXIST. The loop used to work any issue from anyone. `scripts/resolve_provenance.py`
now classifies the author, and the chief's ruling on #361 fixes the shape: fail closed, no
bot allowlist, an override honoured by WHO applied it, and "could not ask" kept distinct from
"asked and the answer was no". Each test below is one of those clauses. A resolver that
answers TRUSTED when it should answer OUTSIDER or UNRESOLVED is the defect, so the
assertions are on the verdict, and the `#361` rows of `scripts/mutate_behaviour_suite.py`
re-break the load-bearing ones to prove they can go red.

Hermetic: the `gh` runner is a fake. Nothing here touches the network, and `run_gh` is
poisoned in `_no_network` so an accidental real call fails loudly.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("resolve_provenance", ROOT / "scripts" / "resolve_provenance.py")
rp = importlib.util.module_from_spec(_spec)
sys.modules["resolve_provenance"] = rp          # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(rp)

REPO = "o/r"
OK = lambda out: rp.Result(0, out)              # noqa: E731
ERR = lambda code, msg: rp.Result(1, "", f"gh: {msg} (HTTP {code})")   # noqa: E731


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a provenance test reached for the network")
    monkeypatch.setattr(subprocess, "run", refuse)


class FakeGh:
    """Routes an argv to a canned Result and remembers every call."""

    def __init__(self, author=("alice", False), labels=(), perms=None, events=None,
                 view_result=None, events_result=None):
        self.calls: list = []
        self.author, self.labels = author, list(labels)
        self.perms = perms or {}
        self.events = events if events is not None else []
        self.view_result, self.events_result = view_result, events_result

    def __call__(self, args):
        self.calls.append(list(args))
        if args[:2] == ["issue", "view"]:
            if self.view_result is not None:
                return self.view_result
            login, is_bot = self.author
            return OK(json.dumps({"author": {"login": login, "is_bot": is_bot},
                                  "labels": [{"name": n} for n in self.labels]}))
        if args[0] == "api" and args[1].endswith("/events"):
            return self.events_result or OK(json.dumps(self.events))
        if args[0] == "api" and "/collaborators/" in args[1]:
            login = args[1].split("/collaborators/")[1].split("/permission")[0]
            login = login.replace("%5B", "[").replace("%5D", "]")
            return self.perms.get(login, ERR(404, "Not Found"))
        if args[0] == "label" or args[:2] in (["issue", "edit"], ["issue", "comment"]):
            return OK("")
        raise AssertionError(f"unexpected gh call {args}")

    def permission_calls(self):
        return [c for c in self.calls if c[0] == "api" and "/collaborators/" in c[1]]


def labeled(name, actor, actor_type="User", at="2026-10-15T10:00:00Z", id_=1):
    return {"event": "labeled", "id": id_, "created_at": at, "label": {"name": name},
            "actor": {"login": actor, "type": actor_type}}


def unlabeled(name, actor, at, id_):
    return {"event": "unlabeled", "id": id_, "created_at": at, "label": {"name": name},
            "actor": {"login": actor, "type": "User"}}


def verdict(fake, n=7):
    return rp.classify(fake, REPO, n).verdict


# ---- the author's permission ---------------------------------------------------------

@pytest.mark.parametrize("perm", ["admin", "write"])
def test_admin_and_write_are_trusted(perm):
    assert verdict(FakeGh(perms={"alice": OK(perm + "\n")})) == rp.TRUSTED


@pytest.mark.parametrize("perm", ["read", "none"])
def test_read_and_none_are_outsiders(perm):
    # Mutated by mutate_behaviour_suite.py: 'none' answering TRUSTED.
    assert verdict(FakeGh(perms={"alice": OK(perm)})) == rp.OUTSIDER


def test_a_404_is_an_outsider_not_an_error():
    # An absent account is "not a user": positively classified, not unresolved.
    assert verdict(FakeGh(perms={})) == rp.OUTSIDER


@pytest.mark.parametrize("res", [
    ERR(403, "Resource not accessible by integration"),
    ERR(500, "Server Error"),
    ERR(502, "Bad Gateway"),
    rp.Result(124, "", "timeout"),
    rp.Result(127, "", "OSError: gh missing"),
])
def test_a_failure_to_ask_is_unresolved_never_a_default(res):
    v = rp.classify(FakeGh(perms={"alice": res}), REPO, 7)
    assert v.verdict == rp.UNRESOLVED
    assert rp.EXIT[v.verdict] == 2


@pytest.mark.parametrize("out", ["", "\n", "maintain", "triage", "Admin", "true"])
def test_empty_or_unrecognised_permission_output_is_unresolved(out):
    assert verdict(FakeGh(perms={"alice": OK(out)})) == rp.UNRESOLVED


def test_author_association_is_never_consulted():
    # `CONTRIBUTOR` is "has had a PR merged". The resolver must not even ask for it.
    fake = FakeGh(perms={"alice": OK("none")})
    verdict(fake)
    asked = [c for c in fake.calls if c[:2] == ["issue", "view"]]
    assert all("author_association" not in " ".join(c) for c in asked)


# ---- bots and bad logins -------------------------------------------------------------

@pytest.mark.parametrize("login", ["app/github-actions", "app/dependabot",
                                   "dependabot[bot]", "app/renovate",
                                   "claudex", "app/claude-bot", "app/not-claude"])
def test_every_bot_but_this_repos_own_app_is_an_outsider(login):
    """THE NARROWNESS GUARD, and the reason the exception below is affordable.

    Mutated: a bot author treated as trusted. Even a bot that WOULD resolve to
    write. The near-misses are in this list deliberately -- `claudex` and
    `claude-bot` are what a substring or `startswith` comparison would let in,
    and either would trust any App whose name begins with the right letters,
    including one installed years from now by someone else.
    """
    bare = login[len("app/"):] if login.startswith("app/") else login
    fake = FakeGh(author=(login, True), perms={bare: OK("write")})
    assert verdict(fake) == rp.OUTSIDER
    assert fake.permission_calls() == []        # no lookup that could grant it


@pytest.mark.parametrize("login", ["app/claude", "claude[bot]", "app/Claude"])
def test_this_repos_own_app_is_trusted(login):
    """THE 2026-11-01 EXCEPTION, measured: 40 of the 130 open issues were filed
    by this App, and a cycle aimed at any of them stopped at `/agent-cycle`
    Step 0a having built nothing. PR #642 was dispatched twice and died both
    times on #616, an issue the loop had filed itself.

    Three renderings, all real. `gh issue view --json author` says
    `app/claude`; the REST API and AGENT_AUTHORS say `claude[bot]`; and GitHub
    logins are case-insensitive, so `Claude` is the same account. Only the
    first reaches this script today, and a change in any of the other two must
    not silently restore the stall.
    """
    fake = FakeGh(author=(login, True))
    assert verdict(fake) == rp.TRUSTED


def test_the_own_app_is_trusted_without_asking_for_a_permission():
    """`claude[bot]` resolves to permission `none` and the App is not a
    collaborator, so CONSULTING the API would answer OUTSIDER for the very
    account this exception is about. The grant has to come from the login, and
    the absence of the call is what proves no second predicate crept in."""
    fake = FakeGh(author=("app/claude", True))
    assert verdict(fake) == rp.TRUSTED
    assert fake.permission_calls() == []


def test_a_HUMAN_named_claude_is_still_judged_on_permission():
    """The exception is for a BOT author. A human account that happens to share
    the App's name must go through `collaborators/<login>/permission` like
    anyone else, or the gate could be walked through by registering a name."""
    fake = FakeGh(author=("claude", False), perms={})     # 404 -> not a collaborator
    assert verdict(fake) == rp.OUTSIDER
    assert len(fake.permission_calls()) == 1


def test_the_exception_is_exactly_one_login_wide():
    """A collection here invites a second entry, and one login is the whole of
    why this is affordable. Pinned as a type, because `SELF_APP = ["claude",
    "github-actions"]` would still pass every behavioural test above."""
    assert isinstance(rp.SELF_APP, str), (
        f"SELF_APP is {type(rp.SELF_APP).__name__}; a collection of trusted bot "
        "logins is the allowlist this script's header refuses"
    )
    assert rp.SELF_APP == "claude"


def test_the_grant_says_which_kind_of_trust_it_is():
    """`provenance:trusted` means two different things now, and a reader of the
    record has to be able to tell them apart: an admin wrote the issue, or the
    loop did."""
    bot = rp.classify(FakeGh(author=("app/claude", True)), REPO, 7)
    human = rp.classify(FakeGh(perms={"alice": OK("admin")}), REPO, 7)
    assert "own delivery App" in bot.reason, bot.reason
    assert "write access" in human.reason, human.reason
    assert bot.reason != human.reason


@pytest.mark.parametrize("login", ["x;id", "a b", "$(id)", "-lead", "a--" + "b" * 50,
                                   "foo\nbar", "", "../../x", "ok/../x", "app/", "a[bot]x"])
def test_an_invalid_login_is_unresolved_and_reaches_no_api_call(login):
    fake = FakeGh(author=(login, False), perms={})
    assert verdict(fake) == rp.UNRESOLVED
    assert fake.permission_calls() == []


@pytest.mark.parametrize("login", ["a\n", "x[bot]\n", "alice\n", "alice\r\n", "alice\x00", "alice "])
def test_a_trailing_newline_or_control_character_is_not_a_login(login):
    # `$` matches before a trailing newline; the login must be a FULL match.
    assert rp.normalise_login(login) is None
    assert rp.normalise_login("app/" + login) is None
    fake = FakeGh(author=(login, False), perms={"alice": OK("write")})
    assert verdict(fake) == rp.UNRESOLVED
    assert fake.permission_calls() == []


@pytest.mark.parametrize("login", ["a", "alice", "x[bot]", "app/claude", "a-b"])
def test_ordinary_logins_still_validate(login):
    assert rp.normalise_login(login) is not None


def test_a_missing_or_malformed_author_is_unresolved():
    for bad in ('{"author": null, "labels": []}', '{"labels": []}', "not json",
                '{"author": {"login": "alice"}, "labels": []}',
                '{"author": {"login": "alice", "is_bot": "false"}, "labels": []}'):
        assert verdict(FakeGh(view_result=OK(bad))) == rp.UNRESOLVED, bad


def test_an_unreadable_issue_is_unresolved():
    assert verdict(FakeGh(view_result=ERR(502, "Bad Gateway"))) == rp.UNRESOLVED


def test_the_login_is_one_argv_element_never_a_shell_string():
    # `x;id` is rejected by the regex, so drive the lookup directly: even if validation were
    # bypassed, the login is a single URL-encoded element of an argv LIST.
    fake = FakeGh(perms={})
    rp.lookup_permission(fake, REPO, "x;id")
    (call,) = fake.permission_calls()
    assert isinstance(call, list)
    assert [a for a in call if "x" in a and "id" in a] == [call[1]]
    assert call[1] == f"repos/{REPO}/collaborators/x%3Bid/permission"
    assert ";" not in call[1] and " " not in call[1]


def test_the_real_runner_uses_an_argv_list_and_no_shell(monkeypatch):
    seen = {}

    def spy(argv, **kw):
        seen["argv"], seen["kw"] = argv, kw
        return subprocess.CompletedProcess(argv, 0, "admin\n", "")
    monkeypatch.setattr(subprocess, "run", spy)
    rp.run_gh(["api", "repos/o/r/collaborators/x%3Bid/permission"])
    assert seen["argv"] == ["gh", "api", "repos/o/r/collaborators/x%3Bid/permission"]
    assert not seen["kw"].get("shell")
    assert seen["kw"].get("timeout")


def test_the_script_has_no_shell_escape_hatch():
    src = (ROOT / "scripts" / "resolve_provenance.py").read_text()
    for banned in ("shell=True", "os.system", "os.popen", "subprocess.getoutput"):
        assert banned not in src


def test_a_timeout_in_the_real_runner_is_a_result_not_an_exception(monkeypatch):
    def boom(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 60)
    monkeypatch.setattr(subprocess, "run", boom)
    assert rp.run_gh(["api", "x"]).rc == 124


# ---- the provenance:trusted override -------------------------------------------------

def outsider_with(events, labels=("provenance:trusted",), perms=None, **kw):
    p = {"mallory": OK("read")}
    p.update(perms or {})
    return FakeGh(author=("mallory", False), labels=labels, perms=p, events=events, **kw)


def test_a_human_maintainers_override_is_honoured():
    fake = outsider_with([labeled("provenance:trusted", "mahAnuj")], perms={"mahAnuj": OK("admin")})
    v = rp.classify(fake, REPO, 7)
    assert v.verdict == rp.TRUSTED and v.override_valid


def test_a_bot_applied_override_is_ignored():
    # Mutated: honouring a bot-applied provenance:trusted.
    fake = outsider_with([labeled("provenance:trusted", "claude[bot]", actor_type="Bot")],
                         perms={"claude[bot]": OK("write")})
    assert verdict(fake) == rp.OUTSIDER


def test_a_bot_applied_override_on_a_bot_filed_issue_is_ignored():
    """The author is `app/dependabot` since 2026-11-01, not `app/claude`: this
    repo's own App is now trusted on its login, so using it here would reach
    TRUSTED before the override was ever consulted and the test would pass
    while proving nothing. The rule under test is unchanged -- a bot labelling
    an issue is not evidence, whoever filed it."""
    fake = FakeGh(author=("app/dependabot", True), labels=["provenance:trusted"],
                  events=[labeled("provenance:trusted", "github-actions", actor_type="Bot")])
    assert verdict(fake) == rp.OUTSIDER


def test_the_own_app_needs_no_override_label_at_all():
    """The complement, stated so the two cannot be confused: the exception is a
    LOGIN grant, so no label is involved and none is read. A reader who sees
    the test above must not conclude the loop labels its own issues."""
    fake = FakeGh(author=("app/claude", True))          # no labels, no events
    assert verdict(fake) == rp.TRUSTED
    assert not [c for c in fake.calls if c[0] == "api" and c[1].endswith("/events")]


def test_an_override_that_was_then_removed_is_ignored():
    fake = outsider_with([labeled("provenance:trusted", "mahAnuj", id_=1, at="2026-10-15T10:00:00Z"),
                          unlabeled("provenance:trusted", "mahAnuj", "2026-10-15T11:00:00Z", 2)],
                         perms={"mahAnuj": OK("admin")})
    assert verdict(fake) == rp.OUTSIDER


def test_a_same_second_label_and_unlabel_are_ordered_by_id():
    # GitHub timestamps to the second, so a quick label+unlabel ties on created_at and only the
    # event id says which came last. Dropping the id tiebreak makes this order arbitrary.
    t = "2026-10-15T10:00:00Z"
    perms = {"mahAnuj": OK("admin")}
    # labeled (id 5) then unlabeled (id 6): removed, so ignored. The unlabeled event is listed
    # FIRST in the payload, so a sort that ignores id would leave the LABELED event last.
    removed = [unlabeled("provenance:trusted", "mahAnuj", t, 6),
               labeled("provenance:trusted", "mahAnuj", at=t, id_=5)]
    assert verdict(outsider_with(removed, perms=perms)) == rp.OUTSIDER
    # unlabeled (id 5) then labeled (id 6): honoured. The lower-id event is listed LAST, and
    # must not win just because it is last in the payload.
    relabeled = [labeled("provenance:trusted", "mahAnuj", at=t, id_=6),
                 unlabeled("provenance:trusted", "mahAnuj", t, 5)]
    assert verdict(outsider_with(relabeled, perms=perms)) == rp.TRUSTED
    ev = rp.latest_label_event(relabeled, "provenance:trusted")
    assert ev is not None and ev["id"] == 6


def test_the_latest_labeler_decides_not_the_first():
    # Maintainer labels, removes it, then a bot labels it again: the LATEST actor is the bot.
    events = [labeled("provenance:trusted", "mahAnuj", id_=1, at="2026-10-15T10:00:00Z"),
              unlabeled("provenance:trusted", "mahAnuj", "2026-10-15T11:00:00Z", 2),
              labeled("provenance:trusted", "claude[bot]", actor_type="Bot", id_=3, at="2026-10-15T12:00:00Z")]
    assert verdict(outsider_with(events, perms={"mahAnuj": OK("admin")})) == rp.OUTSIDER


def test_an_override_by_a_human_without_write_access_is_ignored():
    fake = outsider_with([labeled("provenance:trusted", "randomuser")], perms={"randomuser": OK("read")})
    assert verdict(fake) == rp.OUTSIDER


def test_an_override_by_a_non_collaborator_404_is_ignored():
    assert verdict(outsider_with([labeled("provenance:trusted", "ghostuser")])) == rp.OUTSIDER


def test_an_override_whose_labeler_cannot_be_resolved_is_unresolved():
    fake = outsider_with([labeled("provenance:trusted", "mahAnuj")],
                         perms={"mahAnuj": ERR(403, "forbidden")})
    assert verdict(fake) == rp.UNRESOLVED


def test_unreadable_events_with_an_override_label_present_is_unresolved():
    fake = outsider_with([], events_result=ERR(502, "Bad Gateway"))
    assert verdict(fake) == rp.UNRESOLVED


def test_an_override_label_with_no_event_to_attribute_is_ignored():
    # The label is on the issue but no live `labeled` event names who applied it.
    assert verdict(outsider_with([])) == rp.OUTSIDER


def test_other_labels_events_do_not_count_as_an_override():
    fake = outsider_with([labeled("bug", "mahAnuj")], perms={"mahAnuj": OK("admin")})
    assert verdict(fake) == rp.OUTSIDER


def test_the_override_is_not_even_looked_up_when_the_label_is_absent():
    fake = FakeGh(author=("mallory", False), labels=[], perms={"mallory": OK("none")})
    assert verdict(fake) == rp.OUTSIDER
    assert not [c for c in fake.calls if c[0] == "api" and c[1].endswith("/events")]


def test_a_labelers_login_is_validated_before_any_lookup():
    fake = outsider_with([labeled("provenance:trusted", "x;id")])
    assert verdict(fake) == rp.UNRESOLVED
    assert [c for c in fake.permission_calls() if "x" in c[1] and "id" in c[1]] == []


def test_paginated_event_pages_are_read_as_one_stream():
    # `gh api --paginate` prints one JSON array per page, back to back.
    page1 = json.dumps([labeled("bug", "mahAnuj", id_=1)])
    page2 = json.dumps([labeled("provenance:trusted", "mahAnuj", id_=2, at="2026-10-15T12:00:00Z")])
    fake = outsider_with([], events_result=OK(page1 + page2), perms={"mahAnuj": OK("admin")})
    assert verdict(fake) == rp.TRUSTED


# ---- --apply: the record -------------------------------------------------------------

def run_main(fake, *extra):
    return rp.main(["7", "--repo", REPO, *extra], gh=fake)


def writes(fake):
    return [c for c in fake.calls if c[0] in ("label", "issue") and c[1] in ("create", "edit", "comment")]


def test_without_apply_nothing_is_written(capsys):
    fake = FakeGh(perms={"alice": OK("none")})
    assert run_main(fake) == 1
    assert writes(fake) == []
    assert "OUTSIDER" in capsys.readouterr().out


def test_exit_codes_are_0_1_2(capsys):
    assert run_main(FakeGh(perms={"alice": OK("write")})) == 0
    assert run_main(FakeGh(perms={"alice": OK("read")})) == 1
    assert run_main(FakeGh(perms={"alice": ERR(403, "no")})) == 2


def test_apply_labels_an_outsider_and_creates_the_label_first():
    fake = FakeGh(perms={"alice": OK("none")})
    assert run_main(fake, "--apply") == 1
    w = writes(fake)
    assert w[0][:3] == ["label", "create", "provenance:outsider"]
    assert any(c[:3] == ["issue", "edit", "7"] and "--add-label" in c and "provenance:outsider" in c for c in w)


def test_apply_removes_a_stale_trusted_label_from_an_outsider():
    # The bot-applied provenance:trusted is not a valid override, so it must not linger.
    fake = outsider_with([labeled("provenance:trusted", "claude[bot]", actor_type="Bot")])
    assert run_main(fake, "--apply") == 1
    assert any("--remove-label" in c and "provenance:trusted" in c for c in writes(fake))


def test_apply_keeps_a_valid_human_override_and_drops_the_outsider_label():
    fake = outsider_with([labeled("provenance:trusted", "mahAnuj")],
                         labels=("provenance:trusted", "provenance:outsider"),
                         perms={"mahAnuj": OK("admin")})
    assert run_main(fake, "--apply") == 0
    removed = [c[c.index("--remove-label") + 1] for c in writes(fake) if "--remove-label" in c]
    assert removed == ["provenance:outsider"]


def test_apply_on_unresolved_comments_once_and_is_idempotent():
    first = FakeGh(perms={"alice": ERR(403, "no")})
    assert run_main(first, "--apply") == 2
    comments = [c for c in first.calls if c[:2] == ["issue", "comment"]]
    assert len(comments) == 1 and rp.UNRESOLVED_MARKER in comments[0][comments[0].index("--body") + 1]

    # Second run: the marker is already on the issue, so no second comment.
    class Seen(FakeGh):
        def __call__(self, args):
            if args[:2] == ["issue", "view"] and "comments" in args[-1]:
                self.calls.append(list(args))
                return OK(json.dumps({"comments": [{"body": rp.UNRESOLVED_MARKER + " earlier",
                                                    "viewerDidAuthor": True}]}))
            return super().__call__(args)
    second = Seen(perms={"alice": ERR(403, "no")})
    assert run_main(second, "--apply") == 2
    assert [c for c in second.calls if c[:2] == ["issue", "comment"]] == []


def test_a_copied_marker_in_someone_elses_comment_does_not_suppress_the_stop():
    class Spoofed(FakeGh):
        def __call__(self, args):
            if args[:2] == ["issue", "view"] and args[-1] == "comments":
                self.calls.append(list(args))
                return OK(json.dumps({"comments": [{"body": rp.UNRESOLVED_MARKER, "viewerDidAuthor": False},
                                                   {"body": rp.UNRESOLVED_MARKER}]}))
            return super().__call__(args)
    fake = Spoofed(perms={"alice": ERR(403, "no")})
    assert run_main(fake, "--apply") == 2
    assert len([c for c in fake.calls if c[:2] == ["issue", "comment"]]) == 1


def test_the_unresolved_comment_never_echoes_an_attacker_login():
    fake = FakeGh(author=("x;id $(whoami)", False))
    run_main(fake, "--apply")
    body = [c for c in fake.calls if c[:2] == ["issue", "comment"]][0]
    assert "whoami" not in body[body.index("--body") + 1]


def test_a_failed_apply_is_not_a_pass(capsys):
    class NoWrite(FakeGh):
        def __call__(self, args):
            if args[0] == "label":
                self.calls.append(list(args))
                return ERR(403, "Resource not accessible")
            return super().__call__(args)
    assert run_main(NoWrite(perms={"alice": OK("none")}), "--apply") == 2
    assert "APPLY FAILED" in capsys.readouterr().err


def test_a_bad_repo_or_issue_number_is_unresolved_not_a_crash():
    fake = FakeGh()
    assert rp.main(["7", "--repo", "not a repo; id"], gh=fake) == 2
    assert rp.main(["0", "--repo", REPO], gh=fake) == 2
    assert fake.calls == []
