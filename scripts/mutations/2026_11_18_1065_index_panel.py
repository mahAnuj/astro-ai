"""Mutation rows for #1065 subtask 2 -- the /admin/ops index-status panel (2026-11-18).

One file per area, loaded and appended by `scripts/mutate_behaviour_suite.py`.
Each row re-opens one way the panel could mislead or break the page: dropping the
partial flag (a quota-stopped run read as complete), raising on a mistyped file (a 500
on the whole control room), lifting the list cap, and rendering file-supplied
strings unescaped.

DATA ONLY. `MUTATIONS` must stay a literal list: `verify_no_relaxation.py`
counts it by parsing, and a list built by a call or concatenation cannot be
counted and would read as rows deleted.
"""

MUTATIONS = [
    ("ops: the index panel drops the partial flag, so a quota-stopped run reads as complete",
     "src/astro_ai/ops_data.py",
     '            "partial": doc.get("partial") is True,',
     '            "partial": False,',
     "test_partial_and_its_reason_come_through"),
    ("ops: the index view lets a right-shaped but mistyped file raise instead of degrading",
     "src/astro_ai/ops_data.py",
     "    except Exception as exc:  # noqa: BLE001 -- a monitoring page must not 500",
     "    except KeyError as exc:  # noqa: BLE001 -- a monitoring page must not 500",
     "test_an_error_the_view_did_not_foresee_degrades_instead_of_raising"),
    ("ops: the index panel stops capping the request-indexing list at ten",
     "src/astro_ai/ops_data.py",
     "            if len(items) == INDEX_LIST_MAX:",
     "            if False:",
     "test_at_most_ten_items_and_each_has_a_reason"),
    ("ops: the index panel renders the URLs unescaped (|safe)",
     "src/astro_ai/templates/admin_ops.html",
     '<textarea class="ix-urls" id="ix-urls" readonly rows="{{ X.pages|length }}">{{ X.urls }}</textarea>',
     '<textarea class="ix-urls" id="ix-urls" readonly rows="{{ X.pages|length }}">{{ X.urls|safe }}</textarea>',
     "test_strings_from_the_file_are_escaped"),
    ("ops: the index panel renders the partial reason unescaped (|safe)",
     "src/astro_ai/templates/admin_ops.html",
     "<span class=\"d\">{{ X.partial_reason or 'no reason recorded' }}.",
     "<span class=\"d\">{{ (X.partial_reason or 'no reason recorded')|safe }}.",
     "test_strings_from_the_file_are_escaped"),
    ("ops: a partial run with an empty list claims no page is waiting",
     "src/astro_ai/templates/admin_ops.html",
     "{% if X.partial %}No inspected page is waiting on a recrawl request.",
     "{% if False %}No inspected page is waiting on a recrawl request.",
     "test_a_partial_run_with_nothing_to_list_does_not_claim_nothing_is_waiting"),
]
