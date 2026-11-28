"""#1285: qa_verdict.sh posts the verdict comment BEFORE any label and writes the FULL head sha
into it. tests/test_qa_verdict_comment_first.py drives the real script against a `gh` stub that
logs its writes in order."""

_S = "scripts/qa_verdict.sh"
_COMMENT = 'gh pr comment "$PR" --repo "$GH_REPO" --body "$body" || fail "pr comment"'

MUTATIONS = [
    ("#1285 qa_verdict: a failed comment post is ignored and the labels are written anyway",
     _S, '--body "$body" || fail "pr comment"', '--body "$body" || true',
     "test_a_failed_comment_writes_no_label_and_exits_4"),
    ("#1285 qa_verdict: a label is written before the comment",
     _S, _COMMENT,
     'gh pr edit "$PR" --repo "$GH_REPO" --add-label qa-pass || true\n' + _COMMENT,
     "test_the_comment_is_posted_before_any_label_write"),
    ("#1285 qa_verdict: the abbreviated --sha is written verbatim, not expanded to the head",
     _S, 'FULL=$HEAD ;; esac', 'FULL=$SHA ;; esac',
     "test_an_abbreviated_sha_is_written_as_the_full_head"),
    ("#1285 qa_verdict: a FAIL readies the draft",
     _S,
     'if [ "$VERDICT" = PASS ]; then\n  if [ "$(gh pr view "$PR" --repo "$GH_REPO" --json isDraft',
     'if true; then\n  if [ "$(gh pr view "$PR" --repo "$GH_REPO" --json isDraft',
     "test_a_fail_comment_precedes_labels_and_a_draft_is_not_readied"),
    ("#1285 qa_verdict: the removal paragraph claims the removal already happened",
     _S, 'is being cleared by this PASS on $clears', 'removed on $clears',
     "test_the_removal_paragraph_does_not_claim_the_removal_already_happened"),
    ("#1285 qa_verdict: the removal paragraph names issue #none",
     _S, '[ "$ISSUE" = none ] || clears=', 'clears=',
     "test_the_removal_paragraph_does_not_name_issue_none"),
    ("#1285 qa_verdict: a --sha shorter than 7 characters is accepted",
     _S, 'if [ "${#SHA}" -lt 7 ] || [ "${#SHA}" -gt 40 ]; then', 'if false; then',
     "test_a_too_short_or_non_hex_sha_is_bad_usage_and_writes_nothing"),
    ("#1285 qa_verdict: a non-hex --sha is accepted",
     _S, '  *[!0-9a-fA-F]*) echo', '  *[!0-9a-fA-F]x*) echo',
     "test_a_too_short_or_non_hex_sha_is_bad_usage_and_writes_nothing"),
    ("#1427 qa_verdict: an uppercase --sha is not lowercased",
     _S, """SHA=$(printf '%s' "$SHA" | tr A-F a-f)""", """SHA=$(printf '%s' "$SHA")""",
     "test_an_uppercase_fail_sha_binds_to_the_full_head"),
]
