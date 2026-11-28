"""#1133 slice 2d, step 2: the Recent activity panel on /admin/ops Overview
(templates/admin_ops.html). One area file, a literal list. Every row names the test
(tests/test_ops_activity_page.py) that must go red. The backend rows are in
2026_11_28_1133_ops_recent_activity.py.

Not here, and why:
 * "the panel renders on every tab": it sits inside the Overview tab's own
   `{% if tab == 'overview' %}`, and the route builds `activity` for that tab only, so no
   one-string template change can make it render elsewhere (an equivalent mutant);
   `test_no_other_tab_has_the_panel` reads the result.
 * the colours, whether a row wraps cleanly at 375px, the focus ring on a chip and the
   click landing on the panel: browser-only; looked at in headless Chromium by hand."""

T = "src/astro_ai/templates/admin_ops.html"

MUTATIONS = [
    ("#1133 activity page: a row drops its state word, so a state is a coloured dot only",
     T,
     '<span class="lw">{{ r.word }}</span>{% if r.subtitle %}',
     '<span class="lw"></span>{% if r.subtitle %}',
     "test_every_row_has_a_state_word_a_type_chip_a_time_and_a_repo_link"),
    ("#1133 activity page: the current chip loses aria-current",
     T,
     '<a class="win{{ \' on\' if c.current }}" href="{{ c.href }}"{% if c.current %} aria-current="true"{% endif %}>',
     '<a class="win{{ \' on\' if c.current }}" href="{{ c.href }}">',
     "test_four_chips_are_links_labelled_in_order_and_exactly_one_is_current"),
    ("#1133 activity page: every chip claims to be the current one",
     T,
     '<a class="win{{ \' on\' if c.current }}" href="{{ c.href }}"{% if c.current %} aria-current="true"{% endif %}>',
     '<a class="win on" href="{{ c.href }}" aria-current="true">',
     "test_four_chips_are_links_labelled_in_order_and_exactly_one_is_current"),
    ("#1133 activity page: a row's time loses its machine-readable datetime",
     T,
     '<time class="ra-t" datetime="{{ r.iso }}" title="{{ r.at_ist }} IST">',
     '<time class="ra-t" title="{{ r.at_ist }} IST">',
     "test_every_row_has_a_state_word_a_type_chip_a_time_and_a_repo_link"),
    ("#1133 activity page: a row's type chip is dropped, so Agent, Workflow and Issue rows look alike",
     T,
     '</div><span class="chip">{{ r.type_label }}</span><time class="ra-t"',
     '</div><time class="ra-t"',
     "test_every_row_has_a_state_word_a_type_chip_a_time_and_a_repo_link"),
    ("#1133 activity page: a row's title is printed unescaped (|safe)",
     T,
     '<a href="{{ r.href }}">{{ r.title }}</a>{% else %}{{ r.title }}{% endif %}</b>',
     '<a href="{{ r.href }}">{{ r.title|safe }}</a>{% else %}{{ r.title|safe }}{% endif %}</b>',
     "test_a_script_string_in_a_title_subtitle_or_workflow_name_is_escaped"),
    ("#1133 activity page: a row's subtitle is printed unescaped (|safe)",
     T,
     '<span class="lc">{{ r.subtitle }}</span>',
     '<span class="lc">{{ r.subtitle|safe }}</span>',
     "test_a_script_string_in_a_title_subtitle_or_workflow_name_is_escaped"),
    ("#1133 activity page: View all links Runs for every chip, though Runs shows no workflow or issue rows",
     T,
     '<a href="{{ activity.view_all.href }}">View all &rarr;</a>',
     '<a href="?tab=runs&amp;window=7">View all &rarr;</a>',
     "test_view_all_is_the_rails_own_href_for_that_kind_of_row"),
    ("#1133 activity page: the panel moves before Key metrics",
     T,
     '  {% set UN = {\'organic\': \'clicks\', \'issues\': \'closed\'} %}',
     '  {% if activity %}<section id="recent-activity"></section>{% endif %}\n  {% set UN = {\'organic\': \'clicks\', \'issues\': \'closed\'} %}',
     "test_the_panel_is_on_overview_once_after_key_metrics_and_before_goals"),
    ("#1133 activity page: a chip link loses the anchor, so a click lands at the top of a 250 KB page",
     T,
     '<a class="win{{ \' on\' if c.current }}" href="{{ c.href }}"',
     '<a class="win{{ \' on\' if c.current }}" href="{{ c.href|replace(\'#recent-activity\', \'\') }}"',
     "test_chip_hrefs_are_the_overview_href_plus_the_filter_and_the_anchor"),
    ("#1133 activity page: an unreadable source's reason is not printed, so the panel says nothing at all",
     T,
     "{%- if activity.state == 'unavailable' %}",
     "{%- if false %}",
     "test_empty_says_so_in_a_status_paragraph_and_unavailable_says_why"),
    ("#1133 activity page: the note that closed issues are not listed is dropped",
     T,
     ' Closed issues are not listed: the issue file carries no title for them.',
     '',
     "test_the_notes_say_closed_issues_are_not_listed_and_where_today_comes_from"),
    ("#1133 activity page: the time wraps under 640px no more, so a row overflows at 375px",
     T,
     '@media (max-width:640px){.ra-list>li{flex-wrap:wrap}.ra-t{margin-left:19px}}',
     '@media (max-width:640px){.ra-t{margin-left:19px}}',
     "test_the_row_wraps_under_640px_and_the_chip_keeps_its_size"),
]
