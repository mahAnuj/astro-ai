"""#1315: /privacy must disclose the sign-out record (Google sub + timestamp, kept after account
deletion, pruned on write). tests/test_privacy_copy.py."""

_P = "src/astro_ai/templates/privacy.html"
_R = "src/astro_ai/revocation.py"

_LI = (
    "        <li>&bull; <strong>Sign-out record:</strong> when you sign out or delete your account, "
    "we store your Google account ID (an opaque identifier, not your email or name) and the time, "
    "so that a copy of your sign-in cookie on another device stops working. Deleting your account "
    "does not remove it. Entries older than 90 days are dropped the next time the record is "
    "written, which happens whenever anyone signs out or deletes an account, so one can stay a "
    "little longer than 90 days.</li>\n"
)

MUTATIONS = [
    ("#1315: the sign-out record line is deleted from /privacy",
     _P, _LI, "",
     "test_privacy_page_discloses_the_sign_out_record"),
    ("#1315: the sign-out record line says 30 days where the code keeps 90",
     _P, "Entries older than 90 days are dropped", "Entries older than 30 days are dropped",
     "test_privacy_page_discloses_the_sign_out_record"),
    ("#1315: revoke() stops pruning stale entries, so the line's 'dropped on write' is false",
     _R, "if isinstance(v, (int, float)) and v >= horizon}",
     "if isinstance(v, (int, float))}",
     "test_revocation_record_holds_only_the_sub_and_a_timestamp"),
]
