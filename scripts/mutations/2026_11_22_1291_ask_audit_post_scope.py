"""#1291 -- `scripts/ask_audit_post.py` is bound to the audit's own issues.

The audit agent reads untrusted questions. Each row re-opens one way a prompt injection could
comment on and label `provenance:outsider` an issue that is not the audit's, or file more than
the cap, and names the test that must go red.

DATA ONLY. `MUTATIONS` must stay a literal list: `verify_no_relaxation.py` counts it by parsing.
"""

_POST = "scripts/ask_audit_post.py"

MUTATIONS = [
    ("#1291: the author test is dropped, so any issue with the label and line is the audit's",
     _POST,
     '    return (author["is_bot"] is True and is_self_app(login)\n            and LABEL_OUTSIDER in names',
     '    return (True\n            and LABEL_OUTSIDER in names',
     "test_a_comment_on_an_outsider_issue_copying_the_marker_and_label_is_refused"),
    ("#1291: the class-line test is dropped, so a loop issue is open to comment and label",
     _POST,
     'and MARKER_RE.search(body) is not None)',
     'and True)',
     "test_a_comment_on_a_loop_issue_without_the_marker_or_the_label_is_refused"),
    ("#1291: the outsider-label test is dropped, so a loop issue is open to comment and label",
     _POST,
     '            and LABEL_OUTSIDER in names and MARKER_RE',
     '            and True and MARKER_RE',
     "test_a_comment_on_a_loop_issue_without_the_marker_or_the_label_is_refused"),
    ("#1291: is_bot may be any value, so the string \"false\" is read as a bot",
     _POST,
     '    if not isinstance(author.get("is_bot"), bool):\n        return None',
     '    if False:\n        return None',
     "test_a_comment_fails_closed_on_a_gh_answer_it_cannot_trust"),
    ("#1291: the cap is off by one (a sixth issue is filed)",
     _POST,
     '    if count >= ISSUE_CAP:',
     '    if count > ISSUE_CAP:',
     "test_a_sixth_new_issue_in_the_window_is_refused"),
    ("#1291: the 24h window is ignored, so old issues count and lock the audit out",
     _POST,
     '        if ok and made >= cutoff:',
     '        if ok:',
     "test_the_cap_counts_only_audit_issues_inside_the_window"),
    ("#1291: the cap counts a human's issue that copied the marker and label",
     _POST,
     '        ok = _is_audit_issue(row)\n',
     '        ok = _is_audit_issue(dict(row, author={"login": "claude", "is_bot": True}))\n',
     "test_the_cap_is_counted_by_the_author_test"),
    ("#1291: a gh read that exits non-zero is believed if it printed JSON",
     _POST,
     '    if r.rc != 0:\n        return None, f"{what} failed (gh exit {r.rc})"',
     '    if False:\n        return None, f"{what} failed (gh exit {r.rc})"',
     "test_the_cap_fails_closed_when_it_cannot_be_counted"),
    ("#1291: a full listing page that never leaves the window is trusted as a count",
     _POST,
     '    if len(rows) >= LIST_LIMIT and oldest >= cutoff:',
     '    if False:',
     "test_the_cap_fails_closed_when_it_cannot_be_counted"),
    ("#1291: a new issue no longer needs the class line",
     _POST,
     '    if not MARKER_RE.search(body):\n        print("REFUSED a new issue',
     '    if False:\n        print("REFUSED a new issue',
     "test_a_new_issue_without_the_class_line_is_refused"),
    ("#1291: the --issue target is never read",
     _POST,
     '    refused = _check_target(gh, a.issue) if a.issue is not None else _check_cap(gh, body)',
     '    refused = None',
     "test_a_comment_on_a_human_filed_issue_is_refused"),
]
