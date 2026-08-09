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
        // Inter for Latin, Noto Sans Devanagari as a graceful fallback for Hindi text.
        sans: ['Inter', '"Noto Sans Devanagari"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        // #189: the Devanagari fallback here stays the SANS face, and the
        // serif Devanagari is applied by the [lang="sa"] rule in base.html
        // instead. Crimson Pro carries no Devanagari glyphs, so this second
        // entry is what renders any Devanagari inside a `font-display`
        // element — including the Hindi-toggle headings in
        // _subscribe_modal.html and rashifal.html, which are `font-bold`.
        //
        // Putting "Noto Serif Devanagari" here (the first shape of the #189
        // fix) worked visually but forced us to load the serif's 700 weight
        // for those headings, tripling its cost — 127,280 B variable against
        // 51,048 B for a static 400. Shlokas are the only Devanagari that
        // needs a serif and they are never bold, so the narrower hook is
        // both cheaper and more accurate. Full reasoning at the font <link>
        // in base.html.
        display: ['"Crimson Pro"', '"Noto Sans Devanagari"', 'ui-serif', 'Georgia', 'serif'],
      },
      colors: {
        cream: '#faf7f2',
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
      keyframes: {
        revealUp: {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        breathe: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%':      { transform: 'scale(1.025)' },
        },
        flicker: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.85' },
        },
        drawIn: {
          '0%':   { strokeDashoffset: '100%' },
          '100%': { strokeDashoffset: '0' },
        },
        spinSlow: {
          'from': { transform: 'rotate(0deg)' },
          'to':   { transform: 'rotate(360deg)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'reveal-up': 'revealUp 400ms ease-out forwards',
        'breathe':   'breathe 3s ease-in-out infinite',
        'flicker':   'flicker 1.4s ease-in-out infinite',
        'draw-in':   'drawIn 1.2s ease-out forwards',
        'spin-slow': 'spinSlow 20s linear infinite',
        'shimmer':   'shimmer 2s ease-in-out infinite',
      },
    },
  },
};
