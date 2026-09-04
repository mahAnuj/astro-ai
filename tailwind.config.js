/** @type {import('tailwindcss').Config} */

// Build-time Tailwind config. Ported verbatim from the inline
// `tailwind.config = {...}` that used to sit in base.html beside the Play
// CDN <script>, with two deliberate changes: the astro palette gains its
// missing 200/300/400 stops (#186), and a safelist covers the class names
// templates build dynamically.
//
// WHY THE BUILT CSS IS COMMITTED
// The Cloud Run image is Python-only (see Dockerfile — single stage, uv,
// no Node). The Cloud Build trigger is configured GCP-side and is not
// visible in this working tree, so a Node build stage cannot be tested
// before it reaches production, and production is the first place code
// runs here. Committing src/astro_ai/static/css/app.css keeps the deploy
// path completely unchanged. scripts/verify_css_build.py fails if the
// committed file is stale.

module.exports = {
  content: [
    './src/astro_ai/templates/**/*.html',
    './src/astro_ai/static/**/*.js',
  ],

  // ─── Safelist: classes Tailwind's scanner provably cannot see ──────────
  // Several templates assemble class names at render time, e.g.
  //   numerology.html:139  border-{{ _nc }}-300
  //   muhurat_finder.html:300  bg-{{ ch_class }}      (var carries family+shade)
  //   manglik_check_result.html:32  bg-{{ status_color[0] }}-50
  // The scanner is a plain text matcher — it never sees the rendered value,
  // so without this every one of those utilities is purged and the panel
  // ships colourless. This did not bite under the Play CDN because the CDN
  // generated rules from the live DOM at runtime.
  //
  // Families come from the render-time sources, all enumerated:
  //   chart.py:3567-3576      label_class -> emerald | astro | amber | rose
  //   numerology.py:492-498   label_class -> emerald | astro | amber | rose
  //   numerology_compat.html:111  v_colors -> emerald | stone | amber
  //   muhurat_finder.html:235-298 colors/personal/couple/ch -> emerald | amber | stone | rose
  //   manglik_check_result.html:26 status_color -> emerald | amber
  //   sade_sati_check_result.html:31 phase_info -> stone (+ phase_labels)
  //
  // scripts/verify_css_build.py re-derives this family list from the
  // templates and fails if one appears that is not listed here, so adding a
  // sixth colour to a dict cannot silently ship an unstyled panel.
  safelist: [
    {
      pattern:
        /^(bg|text|border|from|via|to)-(astro|emerald|amber|rose|stone)-(50|100|200|300|400|500|600|700|800|900)$/,
    },
  ],

  theme: {
    extend: {
      fontFamily: {
        // Manrope for Latin, Noto Sans Devanagari as a graceful fallback for Hindi text.
        //
        // #242 SWAPPED THE BODY FACE GLOBALLY, and the reason is arithmetic, not
        // taste. The homepage needs Marcellus loaded, and the font budget
        // (MAX_FONT_BYTES = 285,000 in scripts/verify_devanagari_serif.py) had
        // ~16 KB of headroom against a measured 268,820 B. Adding Marcellus on
        // top of Inter would have blown it. Measured from Google Fonts on
        // 2026-09-03, latin subset, the exact URLs this repo requests:
        //
        //   Inter    (variable, wght@400;500;600;700) ....... 48,256 B
        //   Manrope  (variable, wght@400;500;600;700) ....... 24,836 B
        //   Marcellus (static 400 — it has no other weight) . 14,552 B
        //
        // So swapping Inter out pays for Marcellus with 8,868 B to spare, and
        // the whole page drops to ~260 KB. Re-run the gate; do not re-derive
        // these from memory.
        //
        // `display` below is deliberately NOT swapped in the same motion. See
        // the note there.
        sans: ['Manrope', '"Noto Sans Devanagari"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        // #189: the Devanagari fallback here stays the SANS face, and the
        // serif Devanagari is applied by the [lang="sa"] rule in base.html
        // instead. Marcellus carries no Devanagari glyphs, so this second entry
        // is what renders any Devanagari inside a `font-display` element.
        //
        // Putting "Noto Serif Devanagari" here (the first shape of the #189
        // fix) worked visually but forced us to load the serif's 700 weight,
        // tripling its cost — 127,280 B variable against 51,048 B for a static
        // 400. Shlokas are the only Devanagari that needs a serif and they are
        // never bold, so the narrower hook is both cheaper and more accurate.
        display: ['Marcellus', '"Noto Sans Devanagari"', 'ui-serif', 'Georgia', 'serif'],

        // ─── Redesign stack (#233/#238) ───────────────────────────────
        // `display` and `marcellus` now resolve to the same stack: every screen
        // has migrated, so Crimson Pro was removed from the font request
        // entirely (#261). Both keys stay because ~30 templates say
        // `font-marcellus` and a handful still say `font-display`; collapsing
        // them is a rename with no payload effect, and not worth a sweep.
        //
        // NOTHING IN THIS TREE MAY PUT font-bold ON EITHER. Marcellus ships one
        // weight and Google Fonts will never serve another, so a bold is
        // SYNTHESISED — the same defect family as the synthesised oblique #189
        // exists to remove. The seven elements that used to carry one (two
        // wordmarks, four modal headings, the sign-in title) were unbolded when
        // Crimson Pro left; two of those four modal headings render Devanagari
        // under the Hindi toggle and now resolve to Noto Sans Devanagari 400,
        // which is real, loaded, and regular.
        //
        // Marcellus and Manrope ship NO Devanagari subset, so both keep
        // "Noto Sans Devanagari" as their second entry. That is not belt-and-
        // braces — the handoff proposed Marcellus + Manrope + Tiro Devanagari
        // Sanskrit and nothing else, which would have left every Hindi heading
        // in the tree falling back to a system font at
        // html[lang="hi"]{font-size:108%}. That is #189 returning, and
        // scripts/verify_devanagari_serif.py fails statically if the sans stops
        // being requested at 400-700 (#235).
        //
        // TIRO DEVANAGARI SANSKRIT IS NOT USED, AND THE REASON IS MEASURED.
        // The handoff specifies it for all Devanagari. Google Fonts serves its
        // devanagari subset at 183,900 B against Noto Serif Devanagari's
        // 50,952 B — 3.6x, +132,948 B — which takes the page from ~164 KB to
        // ~297 KB against a 285,000 B budget. It does not fit, and the correct
        // output when the budget does not fit is a stated finding rather than a
        // quiet overspend. Measured 2026-09-03 from the css2 URLs directly.
        marcellus: ['Marcellus', '"Noto Sans Devanagari"', 'ui-serif', 'Georgia', 'serif'],
        manrope: ['Manrope', '"Noto Sans Devanagari"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        cream: '#faf7f2',

        // ─── Redesign palette (#233/#238) ─────────────────────────────
        // Role-based, unlike the `astro` ramp below it: night is "the sky"
        // (hero/nav/footer panels), parchment is the editorial page the
        // reading sits on, saffron is action, gold is ornament ON NIGHT ONLY,
        // sindoor is glyphs and citations on the light surfaces.
        //
        // Namespaced under `bhagya` rather than dropped in at the top level
        // because `cream` already exists at #faf7f2 and the redesign's cream
        // is #FAF6EF. Two near-identical names for two different values is how
        // a migration ships a page that is half one palette and half the
        // other. The old one keeps its name until nothing uses it.
        //
        // THREE VALUES DIFFER FROM THE HANDOFF, and the arithmetic is the
        // reason (#236). WCAG AA needs 4.5:1 for normal text; the 3.0:1
        // exemption wants >=24px, or >=18.66px bold, and none of these is
        // close to either:
        //
        //   muted-2      #8A8175 -> #6F675E   was 3.56:1 on cream / 3.13:1 on
        //                                     cream-2, at 50 uses of 9-14px.
        //                                     Now 5.16 / 4.54.
        //   placeholder  #A9A096 -> #71675D   was 2.39:1, at 20 uses of
        //                                     10-15px. Now 5.13 / 4.52.
        //
        // The third correction is not a colour: the "myth line" on night moves
        // from rgba(250,246,239,.45) to .48 (4.29:1 -> 4.71:1). It lives in
        // whichever template renders that card, not here.
        //
        // The handoff's own README recommends #8A8175 as one of two safe
        // colours on cream, which is how all three got through its review. Add
        // each of these to DECLARED_PAIRS in scripts/verify_contrast.py as a
        // screen starts using it — the gate reads the real hex out of this
        // file and the built CSS, so declaring the pairing is all it needs.
        bhagya: {
          night:       '#140F1C',  // hero/nav/footer panels, primary button fill
          ink:         '#17131A',  // headings, primary text on the light surfaces
          'ink-soft':  '#4A4238',  // long-form body
          muted:       '#6B6259',  // secondary copy
          'muted-2':   '#6F675E',  // micro-labels, meta — CORRECTED from #8A8175
          placeholder: '#71675D',  // input placeholder — CORRECTED from #A9A096
          cream:       '#FAF6EF',  // page background
          'cream-2':   '#F1E7D8',  // alternating band, subtle card fill
          line:        '#E2D6C2',  // 1px dividers, hairline-grid gutters
          'line-2':    '#EDE4D5',  // list row dividers
          border:      '#DED4C2',  // input + card borders
          saffron:     '#E4913C',  // primary accent, CTA fill
          gold:        '#C8A44D',  // ornament — ON NIGHT ONLY, 2.20:1 on cream
          sindoor:     '#9E2B25',  // glyphs, eyebrows, citations, links on light
        },
        astro: {
          50:  '#f6f1fb',
          100: '#ece1f6',
          // ─── #186 ───────────────────────────────────────────────────
          // 200/300/400 were referenced 106 times across the templates
          // (62 + 33 + 11) but never defined, so every one of those
          // utilities emitted no colour rule and the element fell back to
          // Tailwind's default border grey — 95 borders rendering cold.
          //
          // Values are Tailwind's own violet-200/300/400. That is not an
          // arbitrary pick: this palette's 500 (#8b5cf6) and 600 (#7c3aed)
          // are already violet-500 and violet-600 exactly, so borrowing the
          // adjacent stops continues the ramp the palette was built on
          // instead of introducing a hand-mixed hue that would read muddy
          // between 100 and 500.
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          // ────────────────────────────────────────────────────────────
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6b21a8',
          800: '#581c87',
          900: '#3b0764',
        },
      },
      // ─── Motion vocabulary ────────────────────────────────────────
      // Consistent durations + easings across the whole site. Every
      // animation the templates use should reach for one of these
      // rather than inventing its own keyframes. The gate in base.html
      // (@media prefers-reduced-motion) neutralises all of them for
      // motion-sensitive users.
      // Declared here means EMITTED only if a template uses the utility —
      // Tailwind is JIT. `reveal-up`, `flicker`, `draw-in`, `spin-slow` and
      // `shimmer` were declared and never used by any template, so none of the
      // five ever reached app.css: `grep -c revealUp app.css` returned 0. A
      // vocabulary nobody speaks is not a vocabulary, and `revealUp` was
      // actively misleading — base.html defines a DIFFERENT animation of the
      // same name (700ms, 32px, with scale) which is the only one that has
      // ever rendered, so reading this file gave you the wrong values for the
      // behaviour you were looking at. Removed 2026-09-02 (#240).
      //
      // Add one back when a template actually needs it, not before.
      keyframes: {
        breathe: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%':      { transform: 'scale(1.025)' },
        },
        // The handoff's `bhagyaGlow`, verbatim. Both stops are OPACITY, and
        // 0%/100% carrying the same value is load-bearing: base.html's
        // prefers-reduced-motion gate sets animation-duration to 0.01ms and
        // iteration-count to 1, so a reduced-motion user lands on the 100%
        // frame immediately. A keyframe that ended somewhere else would leave
        // them staring at the end state of an animation they opted out of.
        glow: {
          '0%, 100%': { opacity: '0.55' },
          '50%':      { opacity: '0.9' },
        },
      },
      animation: {
        // _nav.html:31, the logo. base.html carries an identical `breathe`
        // keyframe for #kundli-loader .caption, which is plain CSS rather than
        // a utility — both are needed, and their values must not drift apart.
        'breathe': 'breathe 3s ease-in-out infinite',
        // index.html, the hero's radial saffron glow (#242).
        'glow': 'glow 9s ease-in-out infinite',
      },
    },
  },
};
