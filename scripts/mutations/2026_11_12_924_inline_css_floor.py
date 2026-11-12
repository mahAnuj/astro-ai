"""#924: the 12px text floor covers inline `<style>` font-size, and both offenders stay raised.

Each row re-breaks one property tests/test_text_floor_inline_css.py holds."""

MUTATIONS = [
    ("#924: the /learn callout label goes back to 0.7rem (11.2px)",
     "src/astro_ai/templates/learn_article_base.html",
     "    font-size: 0.75rem;\n    font-weight: 700;\n    text-transform: uppercase;",
     "    font-size: 0.7rem;\n    font-weight: 700;\n    text-transform: uppercase;",
     "test_callout_label_is_at_least_12px"),
    ("#924: the muhurat card label goes back to 10px below 1024px",
     "src/astro_ai/templates/muhurat_finder.html",
     "font-size: 12px; line-height: 1.2; font-weight: 600;",
     "font-size: 10px; line-height: 1.2; font-weight: 600;",
     "test_muhurat_card_label_is_at_least_12px"),
    ("#924: the gate reads rem as 100px, so 0.7rem is no longer seen as under the floor",
     "scripts/verify_redesign_tokens.py",
     "_REM_PX = 16",
     "_REM_PX = 100",
     "test_inline_scan_flags_px_and_rem_under_the_floor_inside_style"),
    ("#924: the gate stops scanning <style> blocks (the block regex matches nothing)",
     "scripts/verify_redesign_tokens.py",
     '_STYLE_BLOCK = re.compile(r"<style\\b[^>]*>',
     '_STYLE_BLOCK = re.compile(r"<stylx\\b[^>]*>',
     "test_inline_scan_flags_px_and_rem_under_the_floor_inside_style"),
]
