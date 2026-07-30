"""Registry of Vedic-astrology learning articles served at /learn/<slug>/.

Each article is a hand-written Jinja template at templates/learn/<slug>.html,
extending learn_article_base.html. The registry below holds the metadata
the index page + sitemap + structured-data need (title, summary, category,
hero image, FAQs).

Adding a new article = drop a new dict here + create the matching template
file under templates/learn/. No route changes; main.py resolves slug → file
lookup automatically.

We intentionally do NOT generate this content at runtime via LLM:
  - Static content compounds for SEO; LLM output has the AI-content stigma now
  - Authoritative human-written articles outrank generic LLM walls of text
  - Zero runtime LLM cost, zero "first visitor waits" problem
  - Easy to edit / version-control / improve over time
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Article:
    slug: str
    title: str            # Long descriptive title — shown in <h1> and card. Can exceed 60 chars.
    summary: str          # 1-2 sentences shown in cards + fallback meta description.
    category: str         # 'Doshas' | 'Grahas' | 'Yogas' | 'Concepts' | etc.
    hero_image: str       # absolute URL path to hero SVG/image
    read_time: str        # human-readable estimate, "6 min"
    related: tuple[str, ...] = ()        # related slugs
    faqs: tuple[dict, ...] = field(default_factory=tuple)
    last_updated: str = "2026-06"        # YYYY-MM for SEO freshness signal
    # ─── SEO overrides (optional) ────────────────────────────────────────
    # If set, these are used for the <title> and meta description tags.
    # Google truncates title around 60 chars and description around 160 chars.
    # These override the longer `title` and `summary` fields specifically for
    # SERP display without changing what the article page itself shows.
    seo_title: str = ""       # max 60 chars recommended; empty → falls back to `title`
    seo_description: str = "" # target 140-160 chars; empty → falls back to `summary`
    # ─── LLM enrichment summary (optional) ───────────────────────────────
    # Distilled classical takeaways from this article, ~50-100 tokens, for
    # use by the kundali/matching/ask LLM generators. When a chart matches
    # this article's topic (via topic_summaries_for_chart in chart.py) the
    # summary is injected into the prompt so the LLM can add specific depth
    # AND emit a "/learn/<slug>/" link in the relevant section. Empty ⇒ the
    # article is not exposed to the LLM path (still shown to users normally).
    # Keep summaries dense with classical rules; skip narrative fluff.
    llm_summary: str = ""
    # ─── QA status ────────────────────────────────────────────────────────
    # Tracks whether the article has passed the formal article-qa skill audit
    # (~/.claude/skills/article-qa/SKILL.md, all 6 checks: classical accuracy,
    # source coverage, AI-tell scan, information density, voice consistency,
    # link health). Prevents repeat auditing.
    #   "unaudited"      — never formally QA'd (default for new articles)
    #   "auto-scanned"   — passed automated batch scan (AI-tells, citation
    #                       footer, guardrails) but NOT the 6-check formal audit
    #   "qa-passed"      — passed the full formal article-qa skill
    #   "needs-revision" — audit found issues; fix pending
    # See Issue #117 for the deferred formal-audit cycle.
    qa_status: str = "unaudited"
    qa_date: str = ""            # YYYY-MM-DD of last audit (empty if unaudited)


ARTICLES: tuple[Article, ...] = (
    Article(
        slug="the-9-grahas-overview",
        title="The 9 Grahas: Meet the Planets of Your Kundli",
        summary="A quick tour of the nine planets Vedic astrology uses — what each one governs, which weekday and direction it rules, its exaltation and debilitation signs, and its gemstone. The starting point before any deeper study.",
        category="Grahas",
        hero_image="/static/learn/the-9-grahas-overview/hero.svg",
        read_time="9 min",
        related=("shani-saturn", "surya-sun-in-vedic-astrology", "chandra-moon-in-vedic-astrology"),
        faqs=(
            {
                "q": "Why does Vedic astrology use 9 planets when astronomy only counts 8?",
                "a": "The Vedic count is the seven classical grahas (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn — all visible with the naked eye) plus Rahu and Ketu, the two lunar nodes where the Moon's orbit crosses the Sun's path. Rahu and Ketu are mathematical points, not physical bodies, but Vedic astrology treats them as grahas because their positions correlate strongly with karmic and psychological patterns. Uranus, Neptune, and Pluto are used in Western astrology but not in classical Vedic — they weren't visible to ancient sages.",
            },
            {
                "q": "What's the difference between a benefic and a malefic planet?",
                "a": "Natural benefics (Jupiter, Venus, waxing Moon, Mercury when not conjunct malefics) tend to give pleasant results. Natural malefics (Saturn, Mars, Sun, Rahu, Ketu, waning Moon) tend to give difficult results — but 'difficult' means testing, structural, growth-inducing, not simply bad. Any planet can also become a functional benefic or malefic for a specific chart depending on which houses it rules — that's chart-specific and often reverses the natural classification.",
            },
            {
                "q": "Which planet is 'the strongest' in a chart?",
                "a": "There's no universal answer — it depends on placement. A planet is strong when it sits in its own sign, in exaltation, in a kendra (1st/4th/7th/10th) or trine (1st/5th/9th), aspected by Jupiter, or forming a named yoga. A weak planet is debilitated, combust (too close to the Sun), in an enemy sign, or in a dusthana (6th/8th/12th). Most charts have some strong and some weak — the mix is what makes the reading interesting.",
            },
            {
                "q": "What does exaltation and debilitation mean?",
                "a": "Each planet has one sign where it performs best (exaltation — highest expression of its qualities) and one directly opposite where it performs worst (debilitation — its qualities distort). Sun exalted in Aries, debilitated in Libra. Moon exalted in Taurus, debilitated in Scorpio. Jupiter exalted in Cancer, debilitated in Capricorn. Saturn exalted in Libra, debilitated in Aries. These matter enormously for how a planet behaves in the chart.",
            },
            {
                "q": "Do I really need to wear a gemstone for my ruling planet?",
                "a": "No. Gemstones only help when the planet is a functional benefic in your chart and needs strengthening. Wearing the wrong stone (for a functional malefic) can destabilise things quickly. Classical practice is to consult a knowledgeable astrologer BEFORE wearing any gem — especially Blue Sapphire (Saturn) and Red Coral (Mars), the two most likely to backfire. Devotional remedies (mantras, donations, deity worship) are safer and don't require a chart review.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 9 Grahas: 7 visible (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn) + 2 shadow-planets (Rahu, Ketu = lunar nodes)\n'
            '• Natural benefics: Jupiter, Venus, waxing Moon, unafflicted Mercury\n'
            '• Natural malefics: Saturn, Mars, waning Moon, Sun, Rahu, Ketu, afflicted Mercury\n'
            '• Karakas (significators): Sun→father/self, Moon→mind/mother, Mars→energy/siblings, Mercury→intellect/communication, Jupiter→wisdom/husband, Venus→spouse/luxury, Saturn→career/discipline, Rahu→foreign/ambition, Ketu→spirituality\n'
            '• Each planet has: own sign, exaltation sign (deepest at specific degree), debilitation sign, friendly/enemy signs\n'
            '• Vimshottari Dasha durations sum to 120 years — see Vimshottari Dasha article'
        ),
    ),
    Article(
        slug="vimshottari-dasha-explained",
        title="Vimshottari Dasha: Your 120-Year Life Map",
        summary="The most-used timing system in Vedic astrology divides your life into nine chapters totalling 120 years — each ruled by one planet. Understanding your current mahadasha and antardasha is the single most useful timing skill in Jyotish.",
        category="Concepts",
        hero_image="/static/learn/vimshottari-dasha-explained/hero.svg",
        read_time="10 min",
        related=("rahu-mahadasha-ketu-antardasha", "sun-mahadasha", "shani-saturn"),
        faqs=(
            {
                "q": "How is Vimshottari Dasha calculated?",
                "a": "The starting point is your Moon's exact nakshatra at birth. Each of the 27 nakshatras is ruled by one of nine planets in a fixed cycle: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury. The lord of your birth nakshatra begins your dasha sequence, and the balance of that period depends on how far through the nakshatra the Moon has travelled. The full 120-year cycle then plays out in that fixed order.",
            },
            {
                "q": "How long does each Mahadasha last?",
                "a": "Fixed durations: Sun 6 years, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17, Ketu 7, Venus 20. Total 120 years. The order in your life depends on which planet ruled your birth nakshatra.",
            },
            {
                "q": "What's the difference between Mahadasha and Antardasha?",
                "a": "Mahadasha is the major planetary period — the overall theme of a life chapter. Antardasha (sub-period) is a shorter window inside it, ruled by one of the 9 planets, that shapes specific events. The Mahadasha sets the backdrop; the Antardasha triggers what actually happens. Both matter for prediction.",
            },
            {
                "q": "Which Mahadasha is 'the best'?",
                "a": "Depends on how the planet is placed in your chart. A well-placed Jupiter Mahadasha (Jupiter in own sign / exalted / in a kendra) is often materially and spiritually rewarding. A well-placed Venus Mahadasha (20 years) frequently coincides with marriage and prosperity. But an afflicted Jupiter or Venus can be difficult. The Mahadasha's flavour comes from natal placement, not the planet itself.",
            },
            {
                "q": "Can Vimshottari Dasha predict specific events like marriage or job change?",
                "a": "It can indicate timing windows, not exact dates. A marriage typically fires during the Dasha or Antardasha of Venus (marriage karaka), Jupiter (dharma karaka), the 7th lord, or a planet sitting in / aspecting the 7th house. When multiple such signals cluster in the same window, marriage becomes probable. Transits (gochara) refine the timing further. Prediction is probabilistic — 'a window is more likely', not 'you will marry in March 2027'.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• 120-year life map, 9 planetary chapters, calculated from Moon's birth nakshatra\n"
            "• Durations: Ketu 7y · Venus 20y · Sun 6y · Moon 10y · Mars 7y · Rahu 18y · Jupiter 16y · Saturn 19y · Mercury 17y\n"
            "• Mahadasha lord sets the chapter's character; Antardasha (sub-period, months to years) sharpens the specific event window\n"
            "• Events cluster when multiple Dasha lords converge on the same karaka (e.g. Venus + 7th lord → marriage window)\n"
            "• Timing is probabilistic — narrows to years, not exact dates"
        ),
    ),
    Article(
        slug="surya-sun-in-vedic-astrology",
        title="Surya (Sun): The Soul of Your Chart",
        summary="Sun is the atma-karaka — the significator of your soul, self, vitality, and father. Where Sun sits shapes your identity, authority, and how you show up in the world. The most-quoted planet in classical Vedic literature, and the anchor of any reading.",
        category="Grahas",
        hero_image="/static/learn/surya-sun-in-vedic-astrology/hero.svg",
        read_time="10 min",
        related=("the-9-grahas-overview", "chandra-moon-in-vedic-astrology", "sun-mahadasha"),
        faqs=(
            {
                "q": "What does Sun signify in Vedic astrology?",
                "a": "Sun signifies the soul (atma), the self, vitality, father, government and authority figures, career visibility, physical health (especially heart and eyes), and the will to act. It's the karaka (natural significator) for the 1st, 5th, 9th, and 10th houses. Where Sun sits and what aspects it colours how confidently you take up space in your own life.",
            },
            {
                "q": "What is 'strong Sun' in a chart?",
                "a": "Sun is strong when it sits in Aries (exalted), Leo (own sign), or in the 10th house (its natural home). Sun aspected by Jupiter is also strengthened. Strong Sun people are usually confident, health-solid, respected in their field, and have a clear sense of purpose. Very strong Sun can also lean into ego or authoritarian tendencies — Sun rewards discipline but punishes arrogance.",
            },
            {
                "q": "What does debilitated Sun mean?",
                "a": "Sun debilitated in Libra weakens the sense of self and authority. It can show up as self-doubt, difficulty holding boundaries, complicated father-relationship, uneven physical vitality. Libra is Venus's sign — Sun there gets 'pulled toward relationships and pleasing others' rather than being centred in itself. Cancellation exists (Neechabhanga Raja Yoga) when the Sun's lord Venus is well-placed — debilitated Sun with strong Venus can actually flip into a powerful yoga.",
            },
            {
                "q": "What's Sun's relationship with the father?",
                "a": "Sun is the primary karaka for father in Vedic tradition (Jupiter is the secondary karaka). A strong, well-placed Sun typically indicates a stable relationship with an authoritative or respected father. A weak, afflicted, or badly-placed Sun often reflects a distant, absent, or complicated father figure. Reading the 9th house lord alongside Sun gives the fuller picture.",
            },
            {
                "q": "What's the best remedy for a weak Sun?",
                "a": "Sun-worship at sunrise — offer water to the rising Sun (Arghya) with the Aditya Hridayam or Gayatri Mantra. Fast or eat light on Sundays. Respect your father and paternal figures. Donate wheat, jaggery, or copper on Sundays. Ruby is the classical gem but should only be worn after a proper chart consultation — it can amplify ego or Sun-related health issues if Sun is a functional malefic in your chart.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Karaka: soul (atma), father, authority, government, name/fame, physical health (heart, eyes, bones)\n'
            '• Own sign: Leo (Simha). Exalted: Aries (deepest 10°). Debilitated: Libra (deepest 10°)\n'
            '• Mulatrikona: Leo 0-20°. Digbala (directional strength) in 10th house\n'
            '• Friends: Moon, Mars, Jupiter. Enemies: Venus, Saturn. Neutral: Mercury\n'
            '• Strong Sun: leadership, confidence, government service, strong father-relationship\n'
            '• Weak Sun: authority problems, low self-esteem, father-issues, ego traps\n'
            '• Safe remedies: Surya Namaskar sunrise, Aditya Hridaya Stotram, red-lentil/wheat Sunday charity'
        ),
    ),
    Article(
        slug="chandra-moon-in-vedic-astrology",
        title="Chandra (Moon): The Mind and Emotional Weather of Your Chart",
        summary="Where Sun is the soul, Moon is the mind. Your Janma Rashi (Moon sign), your emotional patterns, your relationship with your mother, and your inner well-being — Moon governs all of it. In Vedic astrology, Moon often matters more than Sun for day-to-day life.",
        category="Grahas",
        hero_image="/static/learn/chandra-moon-in-vedic-astrology/hero.svg",
        read_time="10 min",
        related=("the-9-grahas-overview", "surya-sun-in-vedic-astrology", "sade-sati"),
        faqs=(
            {
                "q": "Why does Vedic astrology emphasise Moon over Sun?",
                "a": "Sun is your soul essence — stable, slow-changing, foundational. Moon is your moment-to-moment mind — the layer of experience you actually live in. Vedic prediction (Rashifal, Sade Sati, Vimshottari Dasha calculations) all key off your Moon sign because that's what shifts your daily reality. Western astrology emphasises Sun because Western psychology emphasises the individual will; Vedic astrology emphasises Moon because Vedic psychology emphasises the fluctuating mind.",
            },
            {
                "q": "What is my Janma Rashi?",
                "a": "Your Janma Rashi is the sidereal zodiac sign the Moon occupied at your birth. It's the single most-used reference point in Vedic astrology — daily Rashifal, Sade Sati timing, Kundli matching (Ashtakoot Guna Milan), and most transit readings are all keyed off Janma Rashi. It's different from your Western 'sun sign' by about 24 degrees on average and by an entire sign for many people.",
            },
            {
                "q": "What does 'waxing' vs 'waning' Moon mean in my chart?",
                "a": "Moon is waxing (bright / building) from the day after Amavasya (new moon) to Purnima (full moon). Moon is waning (dark / releasing) from the day after Purnima to Amavasya. A waxing Moon at birth is treated as a natural benefic; a waning Moon is treated more like a natural malefic — because a bright Moon is 'full of Sun's light' and a dark Moon is 'stripped of it'. The difference matters for interpreting Moon's strength.",
            },
            {
                "q": "What is Sade Sati and why does it depend on my Moon?",
                "a": "Sade Sati is Saturn's 7.5-year transit through the rashi before your Moon sign, your Moon sign itself, and the rashi after. It's counted from Moon (not Lagna or Sun) precisely because Moon is where daily life is lived — Saturn crossing your Moon is felt in mind, health, home, and mother's affairs. See the dedicated Sade Sati guide for the full picture.",
            },
            {
                "q": "What are classical remedies for a weak or afflicted Moon?",
                "a": "Serve and respect your mother — Moon is the primary karaka for mother. Drink water in silver, wear white on Mondays, offer white flowers or milk at Shiva temples. Fast on Mondays with a light single meal. Chant Chandra Beej Mantra or the Shiva Panchakshari (Om Namah Shivaya). Pearl is the classical gem for Moon but requires chart review — an afflicted natal Moon can be destabilised further by wearing pearl.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Karaka: mind (manas), mother, emotions, water, public-facing life\n'
            '• Own sign: Cancer (Karka). Exalted: Taurus (deepest 3°). Debilitated: Scorpio (deepest 3°)\n'
            '• Digbala in 4th house. Waxing (bright half) = benefic; waning (dark half) = malefic\n'
            '• Friends: Sun, Mercury. Enemies: none. Neutral: Mars, Jupiter, Venus, Saturn\n'
            "• Vimshottari Dasha starts from Moon's nakshatra at birth — Moon is the timekeeper\n"
            '• Strong Moon: emotional stability, popularity, good mother-relationship\n'
            '• Weak Moon (Kemadruma yoga): loneliness, mood cycles, mother-issues, mental agitation\n'
            '• Safe remedies: Monday fasting, milk offering to Shiva, silver/pearl (with consultation), moon-gazing'
        ),
    ),
    Article(
        slug="guru-jupiter-in-vedic-astrology",
        title="Guru (Jupiter): The Great Benefic and Teacher",
        summary="Jupiter — Guru, Brihaspati — is the planet of wisdom, wealth, children, and dharma. The single most benevolent graha in the Vedic system, and often the one that decides whether a life feels expansive or constrained. Understanding your Jupiter is understanding what protects you.",
        category="Grahas",
        hero_image="/static/learn/guru-jupiter-in-vedic-astrology/hero.svg",
        read_time="11 min",
        related=("the-9-grahas-overview", "surya-sun-in-vedic-astrology", "shani-saturn"),
        faqs=(
            {
                "q": "Why is Jupiter called the 'Great Benefic'?",
                "a": "Jupiter is the strongest natural benefic — its energy expands, blesses, and protects the significations of any house or planet it aspects or occupies. A well-placed Jupiter cushions the effects of every other difficult placement in the chart. Classical texts call it Devaguru (teacher of the gods) precisely because Jupiter's role is to give wisdom that saves you from your own mistakes. This is why matching charts for marriage weighs Jupiter's placement so heavily.",
            },
            {
                "q": "What does Jupiter signify in Vedic astrology?",
                "a": "Jupiter is the karaka (natural significator) for the 2nd house (wealth, family), 5th (children, intelligence), 9th (dharma, teachers, fortune), and 11th (gains, elder siblings). It rules wisdom, learning (especially religious/spiritual learning), law, ethics, prosperity, and children. In a woman's chart Jupiter is also the karaka for husband and marriage.",
            },
            {
                "q": "What does 'strong Jupiter' mean?",
                "a": "Jupiter is strong when placed in Cancer (exalted), Sagittarius or Pisces (own signs), in a kendra (1st/4th/7th/10th), or aspected by other benefics. Strong Jupiter people tend to be wise, respected, materially comfortable, and blessed with good children. They also often serve as teachers or mentors to others, whether formally or informally.",
            },
            {
                "q": "What does debilitated Jupiter mean?",
                "a": "Jupiter debilitated in Capricorn loses its natural expansiveness — the sign belongs to Saturn (limits, structure), and Jupiter's optimism gets compressed. Common manifestations: struggles with children or fertility, difficulty finding good teachers, tendency toward pessimism, and material scarcity despite hard work. Cancellation exists — if the Capricorn lord Saturn is well-placed, Neechabhanga Raja Yoga forms and the debilitation flips into strength.",
            },
            {
                "q": "What's the best remedy for a weak Jupiter?",
                "a": "Honour your teachers and elders — Jupiter is the guru principle. Chant the Guru mantra 'Om Gum Gurave Namah' or 'Om Brahaspataye Namah' on Thursdays. Fast on Thursdays with yellow foods (turmeric rice, chana daal). Wear yellow, donate yellow items (turmeric, gram, saffron, gold, yellow cloth) on Thursdays. Yellow Sapphire (Pukhraj) is the classical gem but only after chart consultation — a functional-malefic Jupiter with Yellow Sapphire can inflate ego or worsen the very issues it's meant to solve.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Karaka: wisdom, dharma, teachers, gurus, children (progeny), husband (female chart), wealth\n'
            '• Own signs: Sagittarius, Pisces. Exalted: Cancer (deepest 5°). Debilitated: Capricorn (deepest 5°)\n'
            '• Mulatrikona: Sagittarius 0-10°. Digbala in Lagna (1st house)\n'
            '• Friends: Sun, Moon, Mars. Enemies: Mercury, Venus. Neutral: Saturn\n'
            '• Great benefic — even a mediocre Jupiter helps; strong Jupiter is transformative\n'
            '• Hamsa Yoga (Jupiter in kendra in own/exalted sign) is one of the 5 Panch Mahapurush yogas\n'
            '• Jupiter Mahadasha (16 years) often triggers marriage, wisdom, wealth accumulation\n'
            '• Safe remedies: Thursday fasting, yellow-item charity, chanting Guru Beej mantra, honour teachers'
        ),
    ),
    Article(
        slug="mangal-mars-in-vedic-astrology",
        title="Mangal (Mars): The Warrior Planet — Energy, Courage, and Manglik",
        summary="Mars is the karaka of courage, physical strength, siblings, and property — and the planet behind the most-searched dosha in Indian astrology. Understanding Mars means understanding your fight, your drive, and your capacity to act decisively when it matters.",
        category="Grahas",
        hero_image="/static/learn/mangal-mars-in-vedic-astrology/hero.svg",
        read_time="11 min",
        related=("manglik-dosh", "the-9-grahas-overview", "shani-saturn"),
        faqs=(
            {
                "q": "What does Mars signify in Vedic astrology?",
                "a": "Mars is the karaka for the 3rd house (courage, younger siblings, communication skill), the 6th house (enemies, disputes, service), and — indirectly — for real estate and physical labour. It governs energy, willpower, competitive drive, surgical / martial skill, muscle strength, blood, and the capacity to protect what's yours. In terms of relationships, Mars matters heavily for Manglik status; see our full Manglik guide.",
            },
            {
                "q": "What's the connection between Mars and Manglik Dosh?",
                "a": "Manglik Dosh forms when Mars sits in the 1st, 2nd, 4th, 7th, 8th, or 12th house counted from Lagna, Moon, or Venus. Because Mars is the karaka for aggression, its presence in the houses affecting marriage (7th) or its immediate neighbours can classically indicate friction in marital life. Multiple cancellation rules apply — Mars in own sign, exalted Mars, Jupiter aspect, Cancer/Leo Yogakaraka exclusion — see the dedicated Manglik article.",
            },
            {
                "q": "What is 'strong Mars' in a chart?",
                "a": "Mars is strong when placed in Aries (own sign, mooltrikona), Scorpio (own sign), Capricorn (exalted), in the 10th house (its Digbala — natural home), or aspected by Jupiter. Strong Mars people are usually courageous, physically robust, direct in speech, quick to act, and effective in competitive fields (military, sports, surgery, engineering). Very strong Mars can also mean aggression if not channelled — Mars rewards discipline more than it does raw force.",
            },
            {
                "q": "What does debilitated Mars mean?",
                "a": "Mars debilitated in Cancer loses much of its drive — the fiery planet in the watery, emotional sign becomes indecisive, easily upset, and less able to hold ground under pressure. Interestingly, a debilitated Mars in a Manglik house actually cancels the Manglik dosha per classical rule (Jataka Chandrika) — the weakened Mars lacks the strength to disturb marriage. Cancellation of debilitation (Neechabhanga) exists when the Cancer lord Moon is well-placed.",
            },
            {
                "q": "What's the best remedy for a difficult Mars?",
                "a": "The universal Mars remedy is Hanuman Chalisa daily, especially on Tuesdays — Hanuman is considered the mediator between the seeker and Mars's fierce energy. Recite the Mangal mantra 'Om Ang Angarakaya Namah' 108 times Tuesday morning. Fast on Tuesdays with a single meal, avoiding salt. Donate red lentils (masoor dal), copper, or jaggery on Tuesdays. Physical exercise is an underrated Mars remedy — controlled physical exertion channels the planet's energy productively. Red Coral (Moonga) requires chart consultation before wearing.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Karaka: courage, siblings (brothers), energy, real estate, blood, muscle, sports, military, surgery\n'
            '• Own signs: Aries, Scorpio. Exalted: Capricorn (deepest 28°). Debilitated: Cancer (deepest 28°)\n'
            '• Mulatrikona: Aries 0-12°. Digbala in 10th house (shared with Sun)\n'
            '• Friends: Sun, Moon, Jupiter. Enemies: Mercury. Neutral: Venus, Saturn\n'
            '• Manglik Dosha: Mars in houses 1/4/7/8/12 from Lagna (marriage caveat)\n'
            '• Strong Mars: courage, victory, real estate, athletic ability\n'
            '• Weak Mars: accidents, conflict, blood-related health, sibling stress\n'
            '• Safe remedies: Tuesday fasting, Hanuman Chalisa daily, red-item Tuesday charity, red-coral only with consultation'
        ),
    ),
    Article(
        slug="shukra-venus-in-vedic-astrology",
        title="Shukra (Venus): Love, Marriage, Comfort, and the Feminine Principle",
        summary="Venus is the karaka of marriage, romantic love, and material comfort — the planet that decides how much beauty, pleasure, and connection your life holds. Understanding Venus is understanding what you're drawn to and how you experience partnership.",
        category="Grahas",
        hero_image="/static/learn/shukra-venus-in-vedic-astrology/hero.svg",
        read_time="11 min",
        related=("the-9-grahas-overview", "manglik-dosh", "chandra-moon-in-vedic-astrology"),
        faqs=(
            {
                "q": "What does Venus signify in Vedic astrology?",
                "a": "Venus is the karaka for the 7th house (marriage, spouse) — and specifically the karaka for the wife in a male's chart (Jupiter serves this role for a female). It also governs love, romance, comfort, luxury, art, music, poetry, dance, vehicles, jewellery, beauty, cosmetics, and the feminine principle generally. Where Venus sits shapes what you find beautiful and how you experience partnership.",
            },
            {
                "q": "How does Venus determine marriage timing?",
                "a": "Marriage typically happens during the Mahadasha or Antardasha of Venus (in a male's chart), Jupiter (in a female's chart), the 7th house lord, or a planet occupying / aspecting the 7th house. When multiple such signals cluster in the same window, marriage becomes probable. Venus Mahadasha runs 20 years and often coincides with marriage; Venus Antardasha within other Mahadashas also frequently triggers it.",
            },
            {
                "q": "What is 'strong Venus' in a chart?",
                "a": "Venus is strong in Pisces (exalted), Taurus or Libra (own signs), in a kendra (especially the 7th, its natural home), or aspected by Jupiter. Strong Venus people are usually attractive, artistic, socially graceful, and enjoy comfortable material lives. They tend to have loving marriages and are drawn to beauty in all forms. When exalted in Pisces AND in a kendra, Venus forms Malavya Yoga — one of the five Pancha Mahapurush yogas — granting lifelong luxury and marital happiness.",
            },
            {
                "q": "What does debilitated Venus mean?",
                "a": "Venus debilitated in Virgo (Mercury's analytical, service-oriented sign) loses its natural warmth and grace. Common manifestations: difficulty in romantic relationships (over-analysis of partners), tendency toward criticism in love, delayed marriage, or discomfort with sensual pleasure and material luxury. Cancellation exists — if Mercury (the Virgo lord) is strong, Neechabhanga Raja Yoga forms.",
            },
            {
                "q": "What's the best remedy for a weak Venus?",
                "a": "Honour and support the women in your life — Venus is the feminine karaka. Fast on Fridays with white foods (rice, milk, yogurt). Wear white or light pink on Fridays. Chant 'Om Shum Shukraya Namah' 108 times Friday morning. Donate white items (rice, milk, sugar, silver, white cloth) or serve women in need. Diamond is the classical gem for Venus — the safest of the major gemstones to wear, though still worth a chart consultation. For unmarried people delaying marriage, worship Goddess Parvati or Lakshmi.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Karaka: spouse (male chart), love, luxury, arts, vehicles, cosmetics, refined pleasures, sexuality\n'
            '• Own signs: Taurus, Libra. Exalted: Pisces (deepest 27°). Debilitated: Virgo (deepest 27°)\n'
            '• Mulatrikona: Libra 0-15°. Digbala in 4th house (shared with Moon)\n'
            '• Friends: Mercury, Saturn. Enemies: Sun, Moon. Neutral: Mars, Jupiter\n'
            '• Malavya Yoga (Venus in kendra in own/exalted sign) is one of the 5 Panch Mahapurush yogas\n'
            '• Venus Mahadasha (20 years — longest) frequently coincides with marriage, comfort, artistic success\n'
            '• Strong Venus: harmonious relationships, prosperity, beauty appreciation\n'
            '• Safe remedies: Friday fasting, white-item Friday charity, Devi worship, diamond only with consultation'
        ),
    ),
    Article(
        slug="budha-mercury-in-vedic-astrology",
        title="Budha (Mercury): The Planet of Intellect and Communication",
        summary="Mercury governs your mind's analytical layer — how you speak, think, learn, calculate, and do business. Understanding Mercury tells you how you process information, why you communicate the way you do, and where your intellectual edge lies.",
        category="Grahas",
        hero_image="/static/learn/budha-mercury-in-vedic-astrology/hero.svg",
        read_time="10 min",
        related=("the-9-grahas-overview", "surya-sun-in-vedic-astrology", "guru-jupiter-in-vedic-astrology"),
        faqs=(
            {
                "q": "What does Mercury signify in Vedic astrology?",
                "a": "Mercury is the karaka for the 10th house (career, especially in communication or trade). Its themes are intellect, speech, writing, mathematics, education, commerce, short-distance travel, siblings' friends, and youthful mental agility. Mercury governs the nervous system and the throat/speech faculties. It's also the karaka for memory when studied via specific reference points in the chart.",
            },
            {
                "q": "What is 'strong Mercury' in a chart?",
                "a": "Mercury is strong in Virgo (both exalted and own sign — a rare combination), in Gemini (own sign), in the 1st house (its Digbala — natural home), or when forming Budha-Aditya Yoga (conjunct Sun). Strong Mercury people are quick-witted, articulate, mathematically inclined, and often successful in business, media, teaching, writing, or trade. They tend to be flexible, adaptable, and good at building networks.",
            },
            {
                "q": "What does Budha-Aditya Yoga mean?",
                "a": "Budha-Aditya Yoga forms when Sun and Mercury sit in the same sign. It's one of the most-cited beneficial combinations in classical Vedic astrology — grants intelligence, communication skill, career recognition, and respect. However, it's weakened when Mercury is combust (very close to the Sun, within ~14 degrees) — the Sun's fire burns Mercury's articulation. A Budha-Aditya without combustion is a much stronger gift than one with it.",
            },
            {
                "q": "What does debilitated Mercury mean?",
                "a": "Mercury debilitated in Pisces loses precision — the analytical planet in the mystical, boundless sign struggles with concrete thinking. Common manifestations: scattered focus, difficulty with numbers or details, tendency toward dreaminess over action. Interestingly, debilitated Mercury can be excellent for spiritual pursuits, poetry, and intuitive work — it's specifically the linear-analytical function that suffers. Cancellation exists when Jupiter (Pisces lord) is strong.",
            },
            {
                "q": "What's the best remedy for a weak Mercury?",
                "a": "Honour scholars, teachers, and young students — Mercury is the karaka for the youthful learning mind. Chant 'Om Bum Budhaya Namah' or the Vishnu Sahasranama on Wednesdays. Wear green on Wednesdays. Fast on Wednesdays with a single meal. Donate green items (moong dal, green vegetables), books, or educational supplies to students. Feed and care for young girls (kanya). Emerald (Panna) is the classical gem for Mercury — one of the safer gems to wear, though a chart consultation is still recommended.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Karaka: intellect, communication, speech, business, education, writing, humour, skin, nerves\n'
            '• Own signs: Gemini (mulatrikona 15-20°), Virgo. Exalted: Virgo (deepest 15°). Debilitated: Pisces (deepest 15°)\n'
            '• Digbala in Lagna (1st house, shared with Jupiter)\n'
            '• Friends: Sun, Venus. Enemies: Moon. Neutral: Mars, Jupiter, Saturn\n'
            '• Takes on nature of associated planet — friendly with benefics, malefic with malefics\n'
            '• Bhadra Yoga (Mercury in kendra in own/exalted sign) is one of the 5 Panch Mahapurush yogas — strong business signature\n'
            '• Combustion is common (Mercury close to Sun): reduces natural intellect expression\n'
            '• Safe remedies: Wednesday fasting, Vishnu worship, green-item charity, emerald only with consultation'
        ),
    ),
    Article(
        slug="rahu-in-vedic-astrology",
        title="Rahu: The Dragon's Head — Hunger, Obsession, and Foreign Paths",
        summary="Rahu is a mathematical point, not a physical planet — but its influence on your chart is anything but subtle. Where Rahu sits shapes what you obsessively chase, where you'll travel, what unconventional path calls you, and what your soul came here to explore in this lifetime.",
        category="Grahas",
        hero_image="/static/learn/rahu-in-vedic-astrology/hero.svg",
        read_time="11 min",
        related=("rahu-mahadasha-ketu-antardasha", "ketu-in-vedic-astrology", "the-9-grahas-overview"),
        faqs=(
            {
                "q": "What is Rahu if it's not a physical planet?",
                "a": "Rahu is the north lunar node — the mathematical point where the Moon's orbit crosses the Sun's ecliptic going northward. It's not a physical body you can point to in the sky, but its position is precisely calculable and its astrological effects are treated as fully real. Classical mythology tells the story of Rahu as the head of a demon (Svarbhanu) who drank the amrita (nectar of immortality) before being decapitated by Vishnu; the head became Rahu, the body became Ketu. Because both retained immortality, they became grahas.",
            },
            {
                "q": "What does Rahu signify in Vedic astrology?",
                "a": "Rahu signifies obsession, sudden ambition, hunger for the new, foreign lands and cultures, unconventional paths, technology, mass appeal, illusion, addiction, and karmic patterns brought forward from past lives. It amplifies whatever house it sits in — for good or ill. Rahu is the planet of 'this is different, I need to try it' — the outward pull toward what you haven't yet experienced.",
            },
            {
                "q": "Is Rahu always malefic?",
                "a": "Rahu is classified as a natural malefic but is deeply context-dependent. In favourable houses (3rd, 6th, 10th, 11th) with benefic aspects, Rahu can grant tremendous worldly success — foreign wealth, technology fortune, unconventional achievements. In unfavourable positions (like the 7th, disturbing marriage) or without benefic support, Rahu tends toward obsession, deception, and unstable ambition. Modern successful entrepreneurs, actors, and technology founders often have strong Rahu.",
            },
            {
                "q": "What does Rahu Mahadasha bring?",
                "a": "Rahu Mahadasha runs 18 years — the second-longest after Venus. It typically brings dramatic life transformation — foreign travel or settlement, obsessive pursuits, sudden career shifts, addiction risk, and boom-and-bust cycles. Where Rahu sits in your natal chart shapes which life area gets the transformation. See our detailed Rahu-Ketu antardasha guide for the classic mid-Mahadasha inflection point.",
            },
            {
                "q": "What's the best remedy for a difficult Rahu?",
                "a": "The classical Rahu remedy is Durga worship — chant 'Om Ram Rahave Namah' or the Durga Chalisa daily. Feed birds (especially crows), donate to lepers or the marginalised, and worship the goddess in her fierce forms (Kali, Durga, Chamunda). Blue or grey clothing on Saturdays. Meditation practice is unusually helpful for Rahu — the outward hunger settles when the mind learns to sit still. Hessonite (Gomedh) is the classical gemstone but requires careful chart consultation.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Shadow planet — northern lunar node. No physical body, no ownership of signs\n'
            '• Karaka: ambition, foreign, technology, unconventional paths, obsession, sudden gains/losses, alcohol/drugs, deception\n'
            '• Considered exalted in Taurus (some texts) or Gemini (other texts); debilitated in Scorpio or Sagittarius\n'
            '• Rahu Mahadasha (18 years) — the second-longest, and most disruptive\n'
            '• Strong Rahu: material success, foreign gains, entrepreneurial rise, technology mastery\n'
            '• Weak/afflicted Rahu: addictions, deception (self and others), scandal, confusion\n'
            '• Amplifies whichever house/planet it associates with — takes on that flavour\n'
            '• Safe remedies: Rahu Beej mantra, Durga worship, black gram Saturday charity, serve outsiders/marginalized'
        ),
    ),
    Article(
        slug="ketu-in-vedic-astrology",
        title="Ketu: The Dragon's Tail — Detachment, Moksha, and Past-Life Karma",
        summary="Ketu is Rahu's cosmic counterpart — the released half of the same karmic story. Where Rahu chases outward, Ketu drops inward. Where Rahu wants more, Ketu wants less. Understanding your Ketu tells you what you've already mastered in past lives and what your soul is here to release.",
        category="Grahas",
        hero_image="/static/learn/ketu-in-vedic-astrology/hero.svg",
        read_time="11 min",
        related=("rahu-in-vedic-astrology", "rahu-mahadasha-ketu-antardasha", "the-9-grahas-overview"),
        faqs=(
            {
                "q": "What is Ketu if it's not a physical planet?",
                "a": "Ketu is the south lunar node — the mathematical point exactly 180 degrees from Rahu, where the Moon's orbit crosses the Sun's ecliptic going southward. Like Rahu, it's not a physical body but a precisely calculated point. Mythologically, Ketu is the decapitated body of the demon Svarbhanu — the immortal remainder after Rahu (the head) was severed. Because Ketu retained the amrita, it too became a graha, and always sits exactly opposite Rahu in every chart.",
            },
            {
                "q": "What does Ketu signify in Vedic astrology?",
                "a": "Ketu signifies detachment, spiritual liberation (moksha), past-life karma and mastery, sudden endings, occult knowledge, introspection, isolation, and the capacity to renounce. Ketu is the karaka for moksha (via the 12th house from AK/Karakamsa in Rao's methodology). It amplifies whatever house it occupies — but where Rahu amplifies craving, Ketu amplifies detachment. Both grahas together represent your karmic axis: what you're pulled toward (Rahu) and what you're releasing (Ketu).",
            },
            {
                "q": "Why is Ketu sometimes called 'the mokshakaraka'?",
                "a": "Because Ketu's core signature is release rather than accumulation, it's associated with the path of liberation. Rao's methodology specifically flags Ketu in the 12th house from Karakamsa (AK's navamsa position) as a strong indicator of moksha-inclined life. Historically, many great spiritual figures have had strong Ketu — the planet of 'I don't need this' is naturally the planet of the renunciate.",
            },
            {
                "q": "What does Ketu Mahadasha bring?",
                "a": "Ketu Mahadasha runs 7 years — short but psychologically deep. Common themes: sudden loss of interest in what you were pursuing, spiritual awakening, isolation (voluntary or forced), health matters that seem to appear from nowhere and disappear the same way, and profound inner clarity that comes through subtraction rather than addition. Not a period for launching new ventures — Ketu clarifies through release, and permanent decisions made in Ketu often get regretted once Venus (which follows) opens.",
            },
            {
                "q": "What's the best remedy for a difficult Ketu?",
                "a": "The classical Ketu remedy is Ganesha worship — chant 'Om Gam Ganapataye Namah' 108 times daily. Ganesha, as the remover of obstacles and lord of beginnings, is considered Ketu's presiding deity. Serve dogs and stray animals (Ketu's associated creatures). Meditate daily — Ketu responds to inner stillness more than any other planet. Donate blankets, sesame oil, or grey/multi-coloured cloth on Tuesdays. Visit ancestral temples or perform Pitru Tarpan — Ketu rules ancestral karma. Cat's Eye (Lehsunia) is the classical gem but should never be worn without careful chart review.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Shadow planet — southern lunar node. No physical body, no ownership of signs\n'
            '• Karaka: detachment, moksha (spiritual liberation), past-life karma, hidden wisdom, spirituality, occult, chronic illness\n'
            '• Considered exalted in Scorpio; debilitated in Taurus\n'
            '• Ketu Mahadasha (7 years) — often the most spiritual period of life\n'
            '• Strong Ketu: intuition, spiritual insight, healing abilities, freedom from illusion\n'
            '• Weak/afflicted Ketu: mysterious ailments, isolation, loss, confusion about identity\n'
            '• Ketu in 12th house = classical moksha karaka; in 5th = past-life scholar returning\n'
            '• Safe remedies: Ganesha worship, sesame-oil charity, Ketu Beej mantra, spiritual retreat'
        ),
    ),
    Article(
        slug="gochar-2026-planetary-transits",
        title="Gochar 2026: The Year's Major Planetary Transits and How They Affect Your Rashi",
        summary="2026 is a rare year — Jupiter exalted in Cancer for the full year, Saturn still testing Aquarius/Pisces/Aries Moons via Sade Sati, and the Rahu-Ketu axis shifting into Capricorn-Cancer in December. Here's what's happening in the sky and what it means for each Moon sign.",
        category="Concepts",
        hero_image="/static/learn/gochar-2026-planetary-transits/hero.svg",
        read_time="12 min",
        related=("sade-sati", "guru-jupiter-in-vedic-astrology", "shani-saturn"),
        last_updated="2026-07",
        faqs=(
            {
                "q": "What is Gochar in Vedic astrology?",
                "a": "Gochar means 'movement' — it refers to the current transit of a planet through the zodiac, as opposed to its natal position in your birth chart. Transit interpretation asks 'where is Jupiter right now, and how does that interact with my natal Moon?' The two together — natal placement + current gochar — is how Vedic astrology predicts near-term events.",
            },
            {
                "q": "Which is the biggest transit of 2026?",
                "a": "Jupiter exalted in Cancer (Karka) — Jupiter entered Cancer in May 2026 and stays there until roughly May 2027. This happens only once every 12 years and is one of the most benevolent single transits in Vedic astrology. Jupiter in its exaltation sign amplifies its natural blessings — wisdom, wealth, children, dharma — for anyone whose Moon or Lagna is well-positioned relative to Cancer.",
            },
            {
                "q": "How long is Saturn in Pisces?",
                "a": "Saturn entered Pisces in early 2025 and stays there until roughly late February / early March 2027 — about 2.5 years total. During this window, Sade Sati is active for Aquarius (Sade Sati setting phase, final 2.5 years), Pisces (peak phase), and Aries Moons (rising phase). All three groups feel Saturn's transit differently.",
            },
            {
                "q": "What happens to the Rahu-Ketu axis in late 2026?",
                "a": "The Rahu-Ketu axis shifts around December 2026 — Rahu moves from Aquarius into Capricorn, and Ketu moves from Leo into Cancer. This is a major karmic-axis reset. Anyone with Moon or Lagna in Capricorn (new Rahu placement), Cancer (new Ketu placement), Aquarius (departing Rahu), or Leo (departing Ketu) feels the shift most.",
            },
            {
                "q": "How do I know how these transits affect me specifically?",
                "a": "Two things matter: your Janma Rashi (Moon sign) and your Lagna (rising sign). Every article per-rashi guidance in this post uses Moon sign because that's the primary reference in Vedic astrology. Generate your free Kundli on Shubh Bhagya to know your exact Moon sign, then read that section for the year's outlook.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Gochar = current planetary transits over natal houses (as of the reading date)\n'
            '• 2026 major shifts: Saturn continues in Pisces (12th-related themes for many), Jupiter transits Cancer (exaltation until mid-year)\n'
            '• Rahu-Ketu axis: check current transit house from natal Moon for major karmic themes\n'
            '• Transit effects are amplified when a planet passes over natal position (return) or over natal 7th/10th/1st\n'
            "• Transits refine Dasha's broad timing — always read Dasha first, then transit\n"
            '• Jupiter transit over 7th house is a classical marriage-timing trigger; Saturn over 10th signals career restructuring'
        ),
    ),
    Article(
        slug="kundali-matching-ashtakoot-guna-milan",
        title="Kundali Matching: The 36-Guna Compatibility System Explained",
        summary="Before Indian marriages, families traditionally match Kundlis to check compatibility. The Ashtakoot Guna Milan system scores compatibility on 36 points across 8 factors. Here's what each of the 8 factors measures, what the total score really means, and why it's not the whole story.",
        seo_title="Kundali Matching Explained: The 36-Guna Ashtakoot System",
        seo_description="Vedic Kundli matching for marriage uses 36 Guna points across 8 factors. Here's what each factor measures, what the score means, and its real limits.",
        category="Concepts",
        hero_image="/static/learn/kundali-matching-ashtakoot-guna-milan/hero.svg",
        read_time="11 min",
        related=("manglik-dosh", "shukra-venus-in-vedic-astrology", "guru-jupiter-in-vedic-astrology"),
        faqs=(
            {
                "q": "What is Ashtakoot Guna Milan?",
                "a": "Ashtakoot (eight factors) Guna Milan (matching of gunas) is the classical Vedic system for checking marriage compatibility between two Kundlis. It scores compatibility on 8 factors totalling 36 points. The classical guidance: 18+ acceptable (Avara), 24+ good (Madhyam), 30+ excellent (Uttam). Below 18 traditionally advises against marriage — though modern practice weighs individual factors, especially Nadi, more than the raw total.",
            },
            {
                "q": "What are the 8 kootas that get matched?",
                "a": "The eight kootas each measure a different dimension of compatibility: Varna (1 pt — spiritual affinity), Vashya (2 — mutual influence), Tara (3 — health/destiny), Yoni (4 — sexual compatibility), Graha Maitri (5 — mental compatibility), Gana (6 — temperament), Bhakoot (7 — emotional / love / family), and Nadi (8 — genetic/health/progeny). Note: point weights aren't equal — Nadi carries the most weight for a reason.",
            },
            {
                "q": "Is a 36/36 score guaranteed happiness?",
                "a": "No. Guna Milan measures compatibility potential, not lived experience. Many high-scoring matches have complicated marriages because Guna Milan doesn't measure Manglik status, individual chart strength, Navamsa (D-9 marriage chart) compatibility, current dasha timing, or the two people's actual emotional intelligence. A 32/36 with individual chart problems is often harder than a 22/36 with clean individual charts.",
            },
            {
                "q": "What is Nadi Dosha and why does it matter?",
                "a": "Nadi is the 8-point factor and by classical rules the single most-weighted koota. If both partners have the same Nadi (Adi, Madhya, or Antya — derived from birth Nakshatra), Nadi Dosha is said to form, classically indicating risk to progeny (fertility issues, health of children). This is why many high-scoring matches get rejected — even a 30/36 overall score with Nadi Dosha is considered problematic. Cancellations exist (same Rashi + same Nakshatra + different Pada; both partners Manglik; etc.), but the concern is taken seriously.",
            },
            {
                "q": "How can I get an accurate Kundli matching for my chart?",
                "a": "Use Shubh Bhagya's free Kundli matching tool at /matching. Enter both people's birth details and the tool computes all 8 kootas, the Manglik compatibility, and generates an AI-narrative interpretation of what the score actually means for the specific chart pair — not a generic 'compatible / not compatible' verdict.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 8 kootas (categories), 36 total gunas — measures compatibility between two birth Moons\n'
            '• Threshold: 18+ gunas = acceptable, 24+ = good, 30+ = excellent match\n'
            '• 8 kootas: Varna (spiritual), Vashya (attraction), Tara (health), Yoni (physical), Graha Maitri (mental), Gana (temperament), Bhakoot (family), Nadi (progeny)\n'
            '• Nadi Dosha (0/8 on Nadi) and Bhakoot Dosha have specific cancellations — do NOT reject a match on these alone\n'
            '• Guna Milan is one factor — also check Manglik status, 7th house condition of both charts, D-9 Navamsha compatibility\n'
            '• A 32+ match with Manglik mismatch is a real concern; a 20 match with strong D-9 harmony often works'
        ),
    ),
    Article(
        slug="sun-mahadasha",
        title="Sun Mahadasha: 6 Years of Authority, Vitality, and Visibility",
        summary="Sun's Mahadasha is short (6 years) but intense. Career visibility rises, father / authority themes activate, and the mandate is to become someone. What each of the nine antardashas within Sun Maha tends to bring, and how to make the most of the period.",
        category="Dasha",
        hero_image="/static/learn/sun-mahadasha/hero.svg",
        read_time="9 min",
        related=("vimshottari-dasha-explained", "surya-sun-in-vedic-astrology", "rahu-mahadasha-ketu-antardasha"),
        faqs=(
            {
                "q": "How long is Sun Mahadasha and when does it typically arrive?",
                "a": "Sun Mahadasha is exactly 6 years — the shortest of the nine Mahadashas (Ketu and Mars are next at 7 years each; Venus is longest at 20). Its position in your life depends on which planet ruled your birth nakshatra. For many people it falls in their late 20s or early 30s — Vimshottari's order places Sun after Venus, so its arrival depends on where you started the cycle.",
            },
            {
                "q": "Is Sun Mahadasha a good time for marriage?",
                "a": "Sun isn't a marriage karaka — Venus (in male charts) and Jupiter (in female charts) are. Sun Mahadasha alone doesn't strongly indicate marriage. However, the Antardasha of Venus, Jupiter, or the 7th lord within Sun Maha can definitely trigger it. Marriage is most likely when the Antardasha lord has a marriage-relevant role in your chart, not from Sun itself.",
            },
            {
                "q": "What kind of career changes can Sun Mahadasha bring?",
                "a": "Sun rules career visibility, authority, and government. Sun Maha often coincides with promotions, leadership roles, professional recognition, or dealings with government / authority figures. If Sun is well-placed in your chart (own sign, exalted, in 10th), these tend to be positive career moves. If Sun is debilitated or afflicted, the same period can bring conflict with bosses, health issues around the heart, or father-related stress.",
            },
            {
                "q": "Which Antardasha within Sun Maha is usually the toughest?",
                "a": "Sun-Saturn Antardasha (typically 12-14 months, near the end of Sun Maha) is often the hardest — Sun and Saturn are classical enemies (father vs son archetype). It can bring authority conflicts, health issues (heart, eyes, bones), or a sense of being blocked by structural forces. Sun-Rahu can also be turbulent — Sun's steady light meeting Rahu's fog. That said, the actual experience depends entirely on how Sun and Saturn are placed in your specific chart.",
            },
            {
                "q": "What's the best way to use Sun Mahadasha well?",
                "a": "Sun rewards effort in visible, authoritative work. Take on leadership roles, build your professional reputation, mend the relationship with your father if it needs work, pay attention to heart and eye health, honour any government or civic duties. Avoid ego-driven overreach — Sun punishes arrogance more than any planet. Practice the classical Sun Namaskar in the morning, offer water to the rising Sun on Sundays, and give the period the discipline it demands.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 6-year period ruled by Sun — shortest of the 9 Mahadashas\n'
            '• Themes: authority, visibility, father-figure influence, government dealings, career elevation, ego-tests\n'
            '• Well-placed Sun: recognition, promotion, government service opportunities, honour\n'
            '• Weak/afflicted Sun: conflict with authority, health of eyes/heart, father-related stress, ego problems\n'
            '• Peak-effect years: middle 2-3 years of the 6-year window\n'
            '• Antardashas within: Sun-Moon (public dealings), Sun-Mars (conflict/action), Sun-Rahu (sudden change)\n'
            '• Safe remedies: Surya Namaskar at sunrise, Aditya Hridaya Stotram, red-lentil/wheat/jaggery Sunday charity'
        ),
    ),
    Article(
        slug="sade-sati",
        title="Sade Sati: The 7.5-Year Saturn Lesson, Without the Fear",
        summary="Saturn's transit across your Janma Rashi over 7.5 years — the most-feared transit in Vedic astrology and the most misunderstood. The three phases, what each really teaches, classical remedies, and why most lives are better on the other side.",
        seo_title="Sade Sati: Saturn's 7.5-Year Lesson (Without the Fear)",
        seo_description="Sade Sati is Saturn's 7.5-year transit across your Janma Rashi — the 3 phases, what each really teaches, classical remedies, and why most emerge stronger.",
        category="Doshas",
        hero_image="/static/learn/sade-sati/hero.svg",
        read_time="8 min",
        related=("shani-saturn", "rahu-mahadasha-ketu-antardasha"),
        faqs=(
            {
                "q": "How do I know if I'm currently in Sade Sati?",
                "a": "Sade Sati is active when Saturn is in your Moon sign (Janma Rashi), or one rashi before, or one rashi after. Saturn is in Pisces (Meen) until early 2027 — so Aquarius, Pisces, and Aries Moons are currently in Sade Sati phases. Generate your free Kundli on Shubh Bhagya for the exact phase + dates.",
            },
            {
                "q": "What are the three phases of Sade Sati?",
                "a": "Arambha (Rising) — Saturn in 12th from Moon, ~2.5 years. Madhya (Peak) — Saturn in your Moon sign, ~2.5 years and most intense. Uttara (Setting) — Saturn in 2nd from Moon, ~2.5 years of integration. Each phase teaches different lessons; the Madhya phase is the hardest.",
            },
            {
                "q": "Is Sade Sati always bad?",
                "a": "No. People with strong natal Saturn (in own sign, exalted, or in a kendra) often experience Sade Sati as a period of major achievement — slow and hard-won, but real. The transit's difficulty depends entirely on how Saturn sits in your natal chart and how willingly you accept its discipline.",
            },
            {
                "q": "How many times does Sade Sati happen in a lifetime?",
                "a": "2 to 3 times — typically around ages 27-35 (first), 56-64 (second), and 86-94 (third, if you live to see it). Saturn takes ~30 years to circle the zodiac, so the cycle repeats roughly every 29-30 years.",
            },
            {
                "q": "What's the single best remedy for Sade Sati?",
                "a": "Daily Hanuman Chalisa, especially on Saturdays. Hanuman is the only deity classical texts say can intercede with Shani. Combine with serving the elderly, donating to those who have less, and accepting the lessons Saturn is teaching — Saturn rewards willing students more than ritual compliance.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• 7.5-year Saturn transit through the 12th, 1st, and 2nd houses from natal Moon\n"
            "• Rising phase (~2.5y in 12th) → financial pressure, isolation, mental strain\n"
            "• Peak phase (~2.5y in 1st) → health, identity, self-doubt themes\n"
            "• Setting phase (~2.5y in 2nd) → family, speech, financial recovery themes\n"
            "• Not universally bad — forces maturity, discipline, long-term foundation\n"
            "• Safe remedies: Hanuman Chalisa Saturdays, serve elderly, donate black daal / mustard oil\n"
            "• Do NOT blame all life difficulty on Sade Sati — check Dasha + transit context first"
        ),
    ),
    Article(
        slug="kaal-sarp-dosh",
        title="Kaal Sarp Dosh: What It Really Is, What It Isn't, and Healthy Scepticism",
        summary="When all seven planets sit between Rahu and Ketu in your chart. The most over-diagnosed and over-feared condition in modern Vedic astrology — and the cancellation rules the &quot;dosha removal&quot; industry doesn't want you to know.",
        category="Doshas",
        hero_image="/static/learn/kaal-sarp-dosh/hero.svg",
        read_time="8 min",
        related=("manglik-dosh", "rahu-mahadasha-ketu-antardasha"),
        faqs=(
            {
                "q": "Is Kaal Sarp Dosh in the classical Vedic texts?",
                "a": "No — Kaal Sarp Dosh is NOT mentioned in any major classical text (Brihat Parashara, Phaladeepika, Brihat Jataka). The concept entered popular astrology in the 19th-20th century via regional traditions, especially around Trimbakeshwar in Maharashtra. This doesn't make it fake, but the dramatic claims about it are folk wisdom rather than scriptural fact.",
            },
            {
                "q": "How is Kaal Sarp Dosh formed?",
                "a": "When all seven traditional planets (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn) fall on one side of the Rahu-Ketu axis in your chart — none on the opposite side — Kaal Sarp Dosh is said to form. Full Kaal Sarp requires strict containment; partial Kaal Sarp (one planet straddling the line) is much milder and far more common.",
            },
            {
                "q": "Are online Kaal Sarp checkers accurate?",
                "a": "Most aren't. The vast majority just check house numbers without verifying the precise degree of Rahu/Ketu, which means many charts get incorrectly flagged. A proper check considers Rahu's exact degree within its house. Shubh Bhagya's free Kundli uses degree-precise calculation.",
            },
            {
                "q": "What are real cancellation factors for Kaal Sarp?",
                "a": "Strong Lagna lord, Jupiter in a kendra (1st/4th/7th/10th) or trine (5th/9th), Rahu and Ketu in friendly signs, exalted planets, presence of Raja or Dhana yogas, and natural softening after age 40-45 all reduce or cancel the dosha's effects. Most charts have at least one of these.",
            },
            {
                "q": "Are expensive Kaal Sarp removal pujas necessary?",
                "a": "Usually not. The &quot;Kaal Sarp Shanti puja&quot; industry charges ₹5,000-50,000+ and preys on fear. For most charts, simple personal remedies (Mahamrityunjaya mantra, Hanuman Chalisa, Saturday donations) are sufficient. Before paying for an elaborate ceremony, get a clear assessment of whether the dosha applies and what cancellation factors are present.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Kaal Sarp = ALL 7 non-nodal planets between Rahu-Ketu axis (on one side)\n'
            '• 12 sub-types named by which house Rahu occupies (Ananta, Kulika, Vasuki, etc.)\n'
            '• Classical scriptures (BPHS, Phaladeepika) do NOT list Kaal Sarp as a named yoga — it is a modern (~20th century) construct\n'
            '• Modern astrologers report themes: obstacles despite effort, career struggles, ancestral karmic burden\n'
            '• Many charts are misdiagnosed — even one planet OUTSIDE the axis breaks the yoga classically\n'
            '• Healthy scepticism recommended — do not accept an expensive puja on the strength of Kaal Sarp alone\n'
            '• Safe remedies (if you feel it applies): Kaal Bhairava worship, Nag Panchami observance, ancestral tarpan'
        ),
    ),
    Article(
        slug="shani-saturn",
        title="Shani (Saturn): The Misunderstood Karmic Teacher",
        summary="The slowest-moving graha, the karmic taskmaster, the most-feared and most-essential planet in your chart. Why Saturn isn't the villain, what strong vs weak Saturn actually means, and the practical way of living that Saturn rewards.",
        category="Grahas",
        hero_image="/static/learn/shani-saturn/hero.svg",
        read_time="10 min",
        related=("sade-sati", "guru-jupiter-in-vedic-astrology", "the-9-grahas-overview"),
        faqs=(
            {
                "q": "Why is Saturn considered the most-feared planet?",
                "a": "Because Saturn delays gratification, demands discipline, and tests effort over decades. To a culture optimised for quick wins, Saturn feels punitive. Classical Vedic astrology actually treats Saturn as the great teacher — the parent who says no when you want candy. The fear is misplaced; people who respect Saturn don't suffer at his hands.",
            },
            {
                "q": "What is Shasha Yoga?",
                "a": "One of the five Panch Mahapurush yogas. Shasha Yoga forms when Saturn is in its own sign (Capricorn or Aquarius) or exalted (Libra) AND in a kendra (1st/4th/7th/10th) from the Lagna or Moon. Result: significant career achievement, executive ability, public reputation, longevity. Many long-serving political and judicial figures have it.",
            },
            {
                "q": "What does &quot;strong Saturn&quot; mean?",
                "a": "Not &quot;lucky Saturn&quot; — it means Saturn behaves like Saturn well. Discipline, patience, structure, long-game wins. A strong Saturn person is usually a late bloomer whose bloom is durable. Strong placements: Saturn in own sign or exalted, in a kendra, aspected by Jupiter, or forming Shasha Yoga.",
            },
            {
                "q": "What's the best remedy for difficult Saturn?",
                "a": "Daily Hanuman Chalisa (the universal Saturn remedy — Hanuman is the only deity that can intercede with Shani per classical texts), plus serving elders, working harder rather than less, and accepting the lessons Saturn is teaching. Specifically NOT: blue sapphire without a proper chart reading, which can be destabilising if Saturn is poorly placed.",
            },
            {
                "q": "When does Saturn give its best results?",
                "a": "In your 40s and 50s. Saturn's gifts are slow-built and structural. Anything you try to force into your 20s and 30s, Saturn often dismantles. The right strategy with Saturn is to plan the long arc — pick fewer things, stay longer, build durability. The rewards arrive in midlife and last.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Karaka: discipline, longevity, service, career (esp. long-term), delays, sorrow, elderly, iron, poor/marginalized\n'
            '• Own signs: Capricorn, Aquarius. Exalted: Libra (deepest 20°). Debilitated: Aries (deepest 20°)\n'
            '• Mulatrikona: Aquarius 0-20°. Digbala in 7th house\n'
            '• Friends: Mercury, Venus. Enemies: Sun, Moon, Mars. Neutral: Jupiter\n'
            '• Slowest planet — ~29.5 years per orbit. Sade Sati = 7.5-year Saturn transit through 12th/1st/2nd from Moon\n'
            '• Sasha Yoga (Saturn in kendra in own/exalted sign) is one of the 5 Panch Mahapurush yogas — leadership of multitudes\n'
            '• Strong Saturn: longevity, discipline, methodical success, respect in old age\n'
            '• Safe remedies: Saturday service (physical labor, elderly help), Shani Beej mantra, sesame-oil/iron Saturday charity, NEVER wear blue sapphire without full chart consultation'
        ),
    ),
    Article(
        slug="rahu-mahadasha-ketu-antardasha",
        title="Rahu Mahadasha + Ketu Antardasha: Surviving the Nodal Axis Flip",
        summary="The exact transition Reddit asks about: Rahu's 18-year outward hunger meeting Ketu's ~12-month inward release. What it feels like, why it hits so hard, what the classical texts say, and how to make it through.",
        category="Dasha",
        hero_image="/static/learn/rahu-mahadasha-ketu-antardasha/hero.svg",
        read_time="9 min",
        related=("manglik-dosh",),
        faqs=(
            {
                "q": "How long does Ketu Antardasha inside Rahu Mahadasha last?",
                "a": "Precisely 1 year, 0 months, 18 days (~12.6 months). Rahu's Mahadasha is 18 years; Ketu's share inside it is calculated as (7 × 18) / 120 from the Vimshottari proportions.",
            },
            {
                "q": "What comes after Ketu Antardasha in Rahu Mahadasha?",
                "a": "Venus Antardasha — 3 years of significantly softer, more pleasure-oriented energy. Most people describe the Rahu–Ketu period as a dark tunnel and Rahu–Venus as the light at the end. If you're in the hard part, mark that date on your calendar.",
            },
            {
                "q": "Why is Rahu Mahadasha + Ketu Antardasha considered uniquely difficult?",
                "a": "Rahu and Ketu sit exactly 180 degrees apart in your chart — they're perpetual opposites. When their energies overlap in time as well as space, internal contradiction maxes out. Part of you keeps chasing (Rahu); part of you is exhausted (Ketu). Both pull simultaneously and neither resolves.",
            },
            {
                "q": "If Ketu is in my 11th house with Saturn, what does this transition mean?",
                "a": "The 11th house rules gains, friendships, and ambition. Ketu in 11th means the very area you'd reach toward during Rahu Mahadasha is where you'll feel the dissolution — relationships go hollow, networks stop paying off, big ambitions deflate. Saturn alongside adds slow, grinding lessons. The combination teaches detachment from outcomes in social-economic life. Many with this placement end up doing meaningful work in service or quiet professions once the chasing stops.",
            },
            {
                "q": "What's the best remedy during Ketu Antardasha?",
                "a": "Beyond mantras and donations: classical texts emphasise tyaga (willing renunciation). What you give up during Ketu antardasha, you get back tenfold during the Venus antardasha that follows. Stop optimising for outcomes, reduce intake (news/social/ambition-feed), pick one anchor (one practice, one relationship, one piece of steady work), don't make permanent decisions in the worst weeks.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• Nodal axis flip — Rahu Mahadasha's Ketu Antardasha is a ~1-year window (Ketu Antardasha in Rahu Mahadasha = 12 months and 18 days)\n"
            '• Classical difficulty: Rahu wants to grasp, Ketu wants to release — internal tug-of-war\n'
            '• Common patterns: sudden loss of what Rahu had built, spiritual awakening, relationship endings, career detachment\n'
            '• Health themes: mysterious ailments, exhaustion, low immunity — Ketu weakens body\n'
            '• Not universally bad — often initiates the deepest spiritual work of Rahu Mahadasha\n'
            '• Remedies: Ganesha worship (removes obstacles for both nodes), Ketu Beej mantra, avoid major life decisions'
        ),
    ),
    Article(
        slug="manglik-dosh",
        title="Manglik Dosh: What It Really Means, How to Check, and Remedies",
        summary="A clear, honest guide to Manglik Dosh — what it actually is, the houses that cause it, the cancellation rules most websites skip, and the remedies classical texts recommend.",
        seo_title="Manglik Dosh: What It Means, How to Check, Remedies",
        seo_description="Manglik Dosh explained honestly — the houses that cause it, the cancellation rules most calculators ignore, and real classical remedies. Free check.",
        category="Doshas",
        hero_image="/static/learn/manglik-dosh/hero.svg",
        read_time="7 min",
        related=(
            "mangal-mars-in-vedic-astrology",
            "kundali-matching-ashtakoot-guna-milan",
            "mars-remedies",
            "sade-sati",
        ),
        faqs=(
            {
                "q": "Is Manglik Dosh real, or is it just superstition?",
                "a": "It's a real concept in Vedic astrology — Mars in the 1st, 2nd, 4th, 7th, 8th, or 12th houses is documented in classical compilations. Whether its effects play out depends heavily on Mars's strength, conjunctions, and aspects in your specific chart. Many seemingly Manglik people live happily married lives because of cancellation rules most online calculators ignore.",
            },
            {
                "q": "Does Cancer or Leo rising exclude me from Manglik?",
                "a": "Yes. For Cancer Lagna Mars rules the 5th and 10th houses, and for Leo Lagna Mars rules the 4th and 9th — in both cases Mars becomes a Yogakaraka (owns both a trine and a kendra). Per Jataka Parijata and Muhurtha Chintamani, a Yogakaraka cannot simultaneously be the source of a major dosha. If you have Cancer or Leo rising, you are effectively excluded from Manglik diagnosis regardless of where Mars sits.",
            },
            {
                "q": "Can a Manglik person marry a non-Manglik?",
                "a": "Classical texts strongly recommend Manglik-with-Manglik matches because the two charts cancel each other out. But cancellation can also happen via other placements — Mars in own sign or exalted, Jupiter aspecting or conjunct Mars, the Cancer/Leo Lagna Yogakaraka exclusion, or Mars combust the Sun. A proper Kundli matching analysis matters more than the simple Manglik label.",
            },
            {
                "q": "How can I check Manglik Dosh in my own chart?",
                "a": "Generate your free Janma Kundli on Shubh Bhagya — we flag Manglik Dosh along with the specific classical cancellation rules that apply, so you get the full picture, not just a yes/no. The panel colour shifts to green when the dosha is cancelled, so you know at a glance where you stand.",
            },
            {
                "q": "What are the most effective Manglik Dosh remedies?",
                "a": "Classical remedies focus on Mars pacification: fasting on Tuesdays, reciting the Mangal mantra or Hanuman Chalisa, donating red lentils or copper, wearing red coral (only after a chart consultation — never blindly). For marriage matching specifically, the classical recommendation is to match with another Manglik partner, which mutually cancels the dosha.",
            },
            {
                "q": "Does Manglik Dosh weaken with age?",
                "a": "You will often see online that Manglik Dosh 'weakens after age 28' or 'dissolves after 36'. This is modern folk tradition, not classical scripture — there is no such verse in Phaladeepika, Brihat Parashara Hora Shastra, Mansagari, or Jataka Parijata. It may resonate as folk wisdom (people do soften with age) but it should not be cited as classical authority.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• Mars in the 1st, 4th, 7th, 8th, or 12th house from Lagna = Manglik (also checked from Moon in some traditions)\n"
            "• Classically linked to marriage delay or spouse conflict — NOT to marriage denial\n"
            "• Cancellations (any ONE cancels): Jupiter aspect on Mars, mutual-Manglik partnership, Mars in own/exalted sign, Cancer/Leo Ascendant exemption, Mars in same house from both charts\n"
            "• Popular Manglik readings routinely ignore cancellations — always check\n"
            "• 'Weakens after age 28' is folk tradition, NOT classical scripture (not in BPHS, Phaladeepika, Mansagari, Jataka Parijata)\n"
            "• Effective status is per-chart: PRESENT / MITIGATED / CANCELLED"
        ),
    ),
    # ── Nakshatra series ─────────────────────────────────────────────────
    # 27 lunar mansions. Each page: archetype, deity, symbol, gana/nadi,
    # personality, career, relationships, and matching notes drawn from
    # vedic_reference.md §27. Ashwini is the template — the batch of the
    # remaining 26 follows.
    Article(
        slug="bharani-nakshatra",
        title="Bharani Nakshatra: The Bearer at the Threshold of Birth and Death",
        summary="Bharani is the second nakshatra — 13°20' to 26°40' of Aries. Ruled by Venus with Yama as its deity, its symbol is the yoni (womb). Bharani natives are the bearers — intense, sensual, unafraid of transformation.",
        category="Nakshatras",
        hero_image="/static/learn/bharani-nakshatra/hero.svg",
        read_time="7 min",
        related=("ashwini-nakshatra", "shukra-venus-in-vedic-astrology", "kundali-matching-ashtakoot-guna-milan"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Bharani nakshatra?",
                "a": "Your Moon needs to sit between 13°20' and 26°40' of Aries in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya — the planetary table shows your Janma Nakshatra under the Moon row, calculated with the Lahiri ayanamsa.",
            },
            {
                "q": "Why is Yama the deity of Bharani?",
                "a": "Yama is not the villain of Vedic myth — he is the first king of the dead and the first upholder of dharma. Bharani's yoni symbol represents the threshold where birth and death meet. Yama presides because the classical Vedic view is that to give birth is to accept eventual passing; the two are inseparable. Bharani natives carry this unflinching acceptance of hard truths.",
            },
            {
                "q": "What career suits Bharani nakshatra people?",
                "a": "Anything involving deep transformation: obstetrics and midwifery, gynecology, IVF, hospice and end-of-life care, psychology and therapy, funeral work, radical activism, law and criminal justice reform. Also arts that go deep — performance, sensual arts, fashion (Venus rulership). Bharani natives struggle with roles that require superficial engagement.",
            },
            {
                "q": "Is Bharani a good nakshatra for marriage?",
                "a": "Bharani is classified as Ugra (fierce) — not ideal for weddings by classical muhurta rules. For matching Bharani natives to partners: best matches are Manushya-gana partners with different Nadi (Uttara Phalguni is often cited as strong — same gana, different nadi). Same-nadi partners (Madhya-Madhya: Mrigashira, Pushya, Chitra, Anuradha, Dhanishta, Uttara Bhadrapada) lose 8 of 36 Ashtakoot points on Nadi Kuta.",
            },
            {
                "q": "What are Bharani's strengths and weaknesses?",
                "a": "Strengths: capacity to carry heavy responsibilities, strong moral compass, artistic and sensual depth, resilience through transformation, unshakeable when they know what's right. Weaknesses: rigidity when the moral compass tips into judgment, difficulty asking for help (the 'bearer' archetype makes it hard), intensity that can exhaust gentler partners.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 2nd of 27. Span: Aries 13°20'-26°40'. Lord: Venus\n"
            '• Symbol: yoni (womb). Deity: Yama (god of death and transition)\n'
            '• Nature: gatekeeper between birth and death, bearing burdens, moral intensity, creative fertility\n'
            '• Strong signature: hospice/palliative work, judiciary, creative arts requiring deep commitment, midwifery\n'
            '• Shadow: extremism, moral rigidity, self-imposed hardship, jealousy'
        ),
    ),
    Article(
        slug="krittika-nakshatra",
        title="Krittika Nakshatra: The Sacred Fire That Reveals",
        summary="Krittika is the third nakshatra — 26°40' Aries to 10°00' Taurus. Ruled by the Sun with Agni as its deity, symbolised by a razor or flame. Krittika natives are the truth-tellers — sharp, purifying, and unable to look away from what others avoid.",
        category="Nakshatras",
        hero_image="/static/learn/krittika-nakshatra/hero.svg",
        read_time="7 min",
        related=("ashwini-nakshatra", "bharani-nakshatra", "surya-sun-in-vedic-astrology"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Krittika nakshatra?",
                "a": "Your Moon needs to sit between 26°40' Aries and 10°00' Taurus in the sidereal zodiac. Krittika straddles two signs, which is unusual. Generate your free Janma Kundli on Shubh Bhagya to see your exact Moon position and nakshatra.",
            },
            {
                "q": "Why is Krittika linked to the Pleiades?",
                "a": "Krittika is astronomically associated with the Pleiades cluster in Taurus — the seven visible stars. In classical myth, six Krittika mothers nursed the war-god Kartikeya, born of Agni's spark. Kartikeya's name literally means 'son of the Krittikas'. This is why Krittika natives carry the fierce-nurturer archetype: the mother who tells you the truth because she loves you.",
            },
            {
                "q": "What career suits Krittika nakshatra people?",
                "a": "Anything requiring sharp judgment: editing, quality control, critique, investigative journalism, teaching with high standards, military and law enforcement, surgery and precision medicine, priesthood (Agni's classical portfolio), cooking, metalwork. Krittika natives struggle in roles requiring flattery, superficial diplomacy, or looking the other way.",
            },
            {
                "q": "Are Krittika natives too blunt?",
                "a": "Often — yes, at least by conventional standards. The gift is that they're the person others trust to tell the truth. The shadow is that when the cutting edge turns inward it becomes perfectionism, and when it turns outward without care it becomes cruelty. Classical remedy: remember Agni's role is fire that reveals, not fire that destroys.",
            },
            {
                "q": "Which nakshatras match well with Krittika?",
                "a": "Best matches by Ashtakoot Guna Milan: Rakshasa-gana partners with different Nadi — Vishakha, Jyeshtha, Chitra work well on Gana Kuta. Manushya-gana partners are workable if the other kutas score high. Same-Antya-nadi pairs (Rohini, Ashlesha, Magha, Swati, Uttara Ashadha, Shravana, Revati) lose 8 Nadi Kuta points, which is a serious deduction.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 3rd of 27. Span: Aries 26°40' - Taurus 10°. Lord: Sun\n"
            '• Symbol: razor / flame. Deity: Agni (fire) and the Krittikas (Pleiades — six mothers of Kartikeya)\n'
            '• Nature: cutting through illusion, sharp discernment, purification through fire, exposure of truth\n'
            "• Strong signature: judge, critic, editor, surgeon, teacher who cuts through student's confusion\n"
            '• Shadow: harsh criticism, over-cutting, wounding with truth, jealousy'
        ),
    ),
    Article(
        slug="jupiter-remedies",
        title="Jupiter Remedies: Guru Blessings, Wisdom Practices, Yellow Sapphire Guide",
        summary="Jupiter (Guru / Brihaspati) is Vedic astrology's great blessing — karaka of wisdom, wealth, children, marriage, and dharma. His remedies are among the safest and most effective. This guide covers mantras, good deeds, deity worship, and honest guidance on yellow sapphire without vendor manipulation.",
        category="Remedies",
        hero_image="/static/learn/jupiter-remedies/hero.svg",
        read_time="12 min",
        related=("saturn-remedies", "guru-jupiter-in-vedic-astrology", "gajakesari-yoga"),
        faqs=(
            {
                "q": "Is yellow sapphire safe to wear for anyone?",
                "a": "Safer than blue sapphire, but still requires knowing your Ascendant. For Aries, Cancer, Leo, Scorpio, Sagittarius, and Pisces Ascendants, Jupiter is a functional benefic and yellow sapphire generally helps. For Taurus and Libra Ascendants, Jupiter is a functional malefic and yellow sapphire should be avoided. Even for indicated Ascendants, a 3-5 day test period is traditionally recommended before permanent wearing. Never buy an expensive Pukhraj without knowing your Ascendant first.",
            },
            {
                "q": "What is Jupiter's mantra?",
                "a": "The classical bija (seed) mantra is: Om Graam Greem Graum Sah Gurave Namah. Recite 108 times per session on a mala, aiming for daily practice on Thursdays especially. Tradition suggests 16,000 total recitations for a full remedial cycle. Best time: Thursday morning early. Best location: facing north-east (Jupiter's direction). For deeper practice, add the Guru Chalisa or Vishnu Sahasranama (Vishnu being Jupiter's ruling deity).",
            },
            {
                "q": "What are the safest Jupiter remedies for anyone?",
                "a": "Four practices anyone can do without chart consultation: (1) Daily Vishnu Sahasranama recitation (Vishnu is Jupiter's ruling deity); (2) Weekly Thursday support of a child's education — sponsoring, tutoring, or reading to a child; (3) Weekly feeding of cows or donating to a gaushala; (4) Genuine respect for teachers you encounter. These four together, done consistently over a few months, produce measurable improvement in Jupiter-domain life themes.",
            },
            {
                "q": "How do Jupiter remedies help with marriage or children?",
                "a": "Jupiter is the karaka of husband for women and karaka of children for both parents. When these life events delay, Jupiter remedies specifically help. For women seeking marriage: Kanyadaan Vrata (participate in sponsoring the marriage of a girl in a poor family). For those seeking children: feeding children (own, siblings', charitable) generously on Thursdays. Donating school supplies. Special worship of Brihaspati during Guru Purnima (the annual festival of the guru).",
            },
            {
                "q": "How long before Jupiter remedies show results?",
                "a": "Jupiter's timeline is measured in months and years, not days. Consistent Thursday practice over a full lunar year (13 months) is a classical minimum. Faster results often mean the person was already close to alignment and just needed the trigger. Slower results usually indicate the karmic pattern is deeper — but genuine practice always creates change over time, just at Jupiter's pace not our impatient one.",
            },
            {
                "q": "Should I do expensive Guru puja packages?",
                "a": "Almost never. Genuine Jupiter puja is inexpensive — a simple havan with yellow flowers, ghee, and chick peas offered to Vishnu costs almost nothing. Any priest demanding tens of thousands is selling anxiety, not tradition. Mantras + Chalisa + Vishnu Sahasranama + genuine wisdom-seeking are more powerful than expensive rituals done without devotion. The core teaching: remedies are devotional acts, not transactional payments.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• Jupiter safe universal practices (any chart): Thursday fasting (light meal only), Vishnu Sahasranama chanting, Guru Beej mantra 'Om Gram Greem Groum Sah Gurave Namah'\n"
            '• Charity: yellow lentils (chana dal), turmeric, yellow cloth, gold (to genuine teachers or dharmic causes) on Thursdays\n'
            '• Behavioural: honour teachers/elders, study a wisdom tradition, keep Bhagavad Gita or comparable text in home\n'
            '• Gemstone (Pukhraj / yellow sapphire): CLASSICAL Jupiter gem BUT never wear without full chart consultation — a debilitated/afflicted Jupiter reacts unpredictably\n'
            '• Safer alternatives: yellow topaz (Sunela) or citrine as substitute gems\n'
            '• Vishnu worship on Thursdays, especially in Vaishnava traditions'
        ),
    ),
    Article(
        slug="mercury-remedies",
        title="Mercury Remedies: Working with Budha's Intellect Through Vishnu Worship",
        summary="Mercury (Budha) is Vedic astrology's kumara — karaka of intellect, speech, commerce, and the youthful learning mind. Mercury remedies are among the gentlest in the tradition, grounded in respect for scholars, service to students, disciplined speech, and Vishnu worship. This guide covers mantras, good deeds, deity worship, and honest guidance on emerald without vendor manipulation.",
        seo_title="Mercury Remedies: Vishnu Worship & Emerald Guide",
        seo_description="Classical Mercury (Budha) remedies — bija mantra, Vishnu worship, Wednesday practices, emerald safety per Ascendant. Honest, no vendor manipulation.",
        category="Remedies",
        hero_image="/static/learn/mercury-remedies/hero.svg",
        read_time="12 min",
        related=("saturn-remedies", "jupiter-remedies", "venus-remedies", "budha-mercury-in-vedic-astrology"),
        faqs=(
            {
                "q": "Is emerald safe to wear for anyone?",
                "a": "Emerald (Panna) is one of the safer major planetary gemstones — less risky than blue sapphire (Saturn) or red coral (Mars) — but still requires knowing your Ascendant. For Gemini and Virgo Ascendants (Mercury is the Ascendant lord), and for Taurus, Cancer, Libra, Capricorn, and Aquarius Ascendants (Mercury rules helpful houses), emerald is generally recommended. For Aries and Scorpio Ascendants, Mercury rules dusthanas and emerald can worsen nervous-system or communication patterns. For Leo, Sagittarius, and Pisces Ascendants, Mercury's status is mixed — best consulted case-by-case. If genuine emerald of adequate carat weight is beyond budget, classical substitutes include green tourmaline, peridot, or aventurine.",
            },
            {
                "q": "What is Mercury's mantra?",
                "a": "The classical bija (seed) mantra is: Om Braam Breem Braum Sah Budhaya Namah. Recite 108 times per session on a mala, aiming for daily practice with Wednesdays as the anchor day. Classical tradition suggests 17,000 total recitations for a full remedial cycle. Best time: Wednesday morning at dawn. Best direction: east (Mercury's classical direction alongside Jupiter). Best location: in front of a Vishnu icon, or facing east. For deeper practice, add the Budha Chalisa or the Vishnu Sahasranama (Vishnu being Mercury's ruling deity).",
            },
            {
                "q": "Why is Vishnu worship considered a strong Mercury remedy?",
                "a": "Vishnu (Maha Vishnu) is Mercury's primary ruling deity in classical Vedic tradition. Classical teaching holds that the deity form is often more accessible than the abstract planet — so worshipping Vishnu directly is often more effective than reciting Mercury's own mantras. Practical practices: daily Vishnu Sahasranama recitation (widely available in every major Indian language, safe for anyone), offering tulsi leaves (Vishnu's beloved plant), worshipping Vishnu icons on Wednesdays, and observing Ekadashi (11th day of the lunar fortnight, Vishnu's day). This is also why Buddha worship helps — the Buddha is considered a Vishnu avatar in classical Vedic tradition.",
            },
            {
                "q": "What are the safest Mercury remedies for anyone?",
                "a": "Four practices anyone can do without chart consultation: (1) Weekly Vishnu Sahasranama recitation — Vishnu is Mercury's ruling deity; safe universal Mercury practice; (2) Weekly Wednesday support of a student's education — sponsoring books, tutoring, or funding a young girl's schooling; (3) Daily disciplined speech practice — reducing unnecessary talk, cultivating clarity and precision; (4) Daily writing or study practice — 10 minutes of journal writing or rigorous study of any subject. Mercury is honored by discipline of the tongue and precision of the mind, not by volume. These four together produce measurable improvement in Mercury-domain themes and none can backfire.",
            },
            {
                "q": "Why does modern life weaken Mercury so much?",
                "a": "Because Mercury governs the nervous system and the faculty of attention — both of which are being systematically overloaded by modern information environments. Every hour of scattered content-scrolling (social media, news, notifications) actively weakens the Mercury faculty by fragmenting attention and overloading the nervous system with low-quality stimulus. Classical Mercury remedies (mantra, study, disciplined speech) work more slowly than modern content-consumption undoes them. If you're doing Mercury remedies while also consuming 4+ hours of social media daily, the second is undoing the first faster than the first can build. Modern Mercury practice must include a deliberate information diet.",
            },
            {
                "q": "How do Mercury remedies help with communication difficulty or stammer?",
                "a": "Mercury is the karaka of speech and the physical organs of speech (throat, tongue). Chronic communication difficulty — stammer, verbal freeze under pressure, meandering speech — usually indicates weak or afflicted Mercury. Classical remedies specifically help: daily reading aloud practice (10-15 minutes of scripture, poetry, or serious prose, read slowly and clearly), daily writing practice by hand, weekly Saraswati or Vishnu worship, chanting the Vishnu Sahasranama slowly and aloud (combines speech-practice and mantra dimensions), and reduced consumption of low-quality speech (gossip media, argumentative content). Mercury absorbs what he is fed — feed him well and he strengthens.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• Mercury safe universal practices: Wednesday fasting or vegetarian diet, Vishnu Sahasranama, Mercury Beej mantra 'Om Bram Breem Broum Sah Budhaya Namah'\n"
            '• Charity: green cloth, green lentils (moong dal), emerald-colored items, education-related donations on Wednesdays\n'
            '• Behavioural: teach a skill freely, help someone learn to read/write, honour communication tools (books, notebooks)\n'
            '• Gemstone (Emerald / Panna): NEVER without full chart consultation — combusted Mercury commonly problematic\n'
            '• Skin/nerve care important as Mercury governs these — meditation helps nervous system\n'
            "• Vishnu worship on Wednesdays; special connection to Vishnu's intellectual/wisdom aspect"
        ),
    ),
    Article(
        slug="venus-remedies",
        title="Venus Remedies: Working with Shukra's Grace Through Lakshmi Worship",
        summary="Venus (Shukra) is Vedic astrology's classical bhogakaraka — karaka of marriage, love, beauty, comfort, and the feminine principle. Venus remedies are among the gentlest in the tradition, grounded in respect for the feminine, aesthetic devotion, and Lakshmi worship. This guide covers mantras, good deeds, deity worship, and honest guidance on diamond without vendor manipulation.",
        seo_title="Venus Remedies: Lakshmi Worship & Diamond Guide",
        seo_description="Classical Venus (Shukra) remedies — bija mantra, Lakshmi worship, Friday practices, diamond safety per Ascendant. Honest, no vendor manipulation.",
        category="Remedies",
        hero_image="/static/learn/venus-remedies/hero.svg",
        read_time="12 min",
        related=("saturn-remedies", "jupiter-remedies", "mars-remedies", "shukra-venus-in-vedic-astrology"),
        faqs=(
            {
                "q": "Is diamond safe to wear for anyone?",
                "a": "Diamond (Heera) is one of the safer major planetary gemstones — less risky than blue sapphire (Saturn) or red coral (Mars) — but still requires knowing your Ascendant. For Taurus and Libra Ascendants (Venus is the Ascendant lord) and for Capricorn and Aquarius Ascendants (Venus is a Yogakaraka), diamond is classically recommended and generally supports Venus's positive effects. For Aries and Scorpio Ascendants, Venus rules dusthanas and diamond can worsen relationship or health patterns. For Cancer, Leo, Sagittarius, and Pisces Ascendants, Venus's status is mixed — best consulted case-by-case. If genuine diamond of adequate carat weight is beyond budget, classical alternatives include white sapphire, white zircon, or white topaz.",
            },
            {
                "q": "What is Venus's mantra?",
                "a": "The classical bija (seed) mantra is: Om Draam Dreem Draum Sah Shukraya Namah. Recite 108 times per session on a mala, aiming for daily practice with Fridays as the anchor day. Classical tradition suggests 20,000 total recitations for a full remedial cycle — the largest count among the seven planets, reflecting Venus's 20-year Mahadasha. Best time: Friday morning at dawn. Best direction: north (Venus's classical direction). For deeper practice, add the Shukra Chalisa, Lakshmi Ashtakam, or Sri Sukta.",
            },
            {
                "q": "Why is Lakshmi worship considered a strong Venus remedy?",
                "a": "Lakshmi is one of Venus's primary ruling deities in classical Vedic tradition. She represents Venus's ideal expression — abundance, grace, beauty, dharmic wealth, and the feminine principle in its most auspicious form. Classical tradition holds that Lakshmi worship pacifies Venus more effectively than direct Shukra worship because the deity form is more accessible than the abstract planet. Practical practices: daily Lakshmi Ashtakam recitation, weekly Sri Sukta on Fridays, offering white flowers and camphor to Lakshmi, extended Lakshmi puja during Diwali (her annual festival).",
            },
            {
                "q": "What are the safest Venus remedies for anyone?",
                "a": "Four practices anyone can do without chart consultation: (1) Weekly Sri Sukta recitation before a Sri Yantra — the universal safe Venus/Lakshmi practice, Friday mornings preferred; (2) Weekly Friday donation of white or silver items — rice, milk, sugar, camphor, jasmine, white cloth; (3) Deliberate cultivation of respect for the women in your life — actually listening, actually supporting, not performatively; (4) Daily aesthetic attention — genuinely noticing something beautiful each day. Venus is honored by the quality of attention, not the size of the offering. These four together produce measurable improvement in Venus-domain themes and none can backfire.",
            },
            {
                "q": "How do Venus remedies help with delayed marriage?",
                "a": "Venus is the karaka of the 7th house and specifically the karaka of the wife in a male's chart (Jupiter serves this role for a female — see our Jupiter remedies guide). When marriage delays despite the chart showing it is due, classical Venus remedies specifically help: Kanyadaan Vrata (participate in sponsoring the marriage of a girl in a poor family) is often the fastest marriage-timing remedy. Also: Friday worship of Parvati for women or Lakshmi for men, feeding young unmarried girls (kanya bhojan) on Fridays, and the Solah Somvar Vrat (16-Monday fast to Parvati) for unmarried women. The Katyayani mantra from Bhagavata Purana is the classical mantra of unmarried girls seeking a good husband.",
            },
            {
                "q": "Why does the classical tradition warn against Venus over-indulgence?",
                "a": "Because Venus is the karaka of enjoyment, and enjoyment can turn into grasping or excess if not held with discipline. Classical Vedic view: uncontrolled sensuality, over-consumption of luxury, and grasping for beautiful things actually weaken Venus's blessing rather than pleasing her. Genuine Venus wealth is what flows in and out with equanimity, enjoyed without clinging. This is the counter-intuitive teaching most modern content misses — the person Venus rewards is the one who has become worth loving, not the one who chants for love. Disciplined enjoyment within dharma is the classical rule.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• Venus safe universal practices: Friday fasting (or vegetarian), Sri Lalita Sahasranama, Devi/Lakshmi worship, Venus Beej mantra 'Om Draam Dreem Draum Sah Shukraya Namah'\n"
            '• Charity: white cloth, white sweets, sugar/rice, cow ghee, cosmetics/perfume to needy women on Fridays\n'
            '• Behavioural: honour the feminine (mothers, sisters, daughters), avoid harming animals, cultivate beauty in surroundings\n'
            '• Gemstone (Diamond / Heera): NEVER without full chart consultation — very expensive and unpredictable if wrong\n'
            '• Safer alternatives: white sapphire (Safed Pukhraj) as substitute\n'
            "• Sri Yantra recitation is universally safe (Sri = Lakshmi = Venus's presiding energy)"
        ),
    ),
    Article(
        slug="mars-remedies",
        title="Mars Remedies: Working with Mangal's Energy Through Hanuman Worship",
        summary="Mars (Mangal / Kuja) is Vedic astrology's warrior — karaka of energy, courage, siblings, and the Manglik marriage pattern. Working with Mars requires channelling his energy, not suppressing it. This guide covers mantras (especially Hanuman practices), good deeds, deity worship, and red coral guidance without vendor manipulation.",
        category="Remedies",
        hero_image="/static/learn/mars-remedies/hero.svg",
        read_time="12 min",
        related=("saturn-remedies", "jupiter-remedies", "manglik-dosh", "mangal-mars-in-vedic-astrology"),
        faqs=(
            {
                "q": "Is red coral safe to wear for anyone?",
                "a": "Moderately safe for most, but still requires knowing your Ascendant. For Cancer, Leo, Scorpio, Sagittarius, and Pisces Ascendants, Mars is functionally benefic and red coral generally helps. For Taurus, Gemini, and Virgo Ascendants, Mars becomes functionally malefic and red coral can worsen anger, conflicts, or blood-related health issues. Also: if your Mars is already over-active (aggressive personality, chronic conflicts), you may need to calm Mars rather than strengthen it — in which case coral would be counterproductive.",
            },
            {
                "q": "Why is Hanuman worship considered the best Mars remedy?",
                "a": "Because Hanuman himself is the archetypal disciplined warrior — the embodiment of Mars energy channelled through devotion and service rather than ego. Classical tradition holds that Hanuman worship pacifies Mars more effectively than direct Mangal worship because Hanuman represents Mars in his ideal form. The most-used practices: daily Hanuman Chalisa (especially Tuesdays and Saturdays), visits to Hanuman temples with red flowers and ghee lamps, Sundarakanda recitation for deeper practice.",
            },
            {
                "q": "What is Mars's mantra?",
                "a": "The classical bija (seed) mantra is: Om Kraam Kreem Kraum Sah Bhaumaya Namah. Recite 108 times per session on a mala, aiming for daily practice on Tuesdays especially. Tradition suggests 7,000 total recitations for a full remedial cycle. Best time: Tuesday morning early. Best direction: south (Mars's direction). For deeper practice, add the Hanuman Chalisa or Mangal Chalisa.",
            },
            {
                "q": "What are the safest Mars remedies for anyone?",
                "a": "Four practices anyone can do without chart consultation: (1) Daily Hanuman Chalisa recitation — the most universally recommended Mars practice; (2) Regular vigorous exercise as spiritual discipline — Mars is honored by disciplined use of physical energy; (3) Blood donation every 3 months — direct Mars-domain service; (4) Practicing controlled anger in daily provocative situations — Mars's own teaching applied as practice. These four together produce measurable improvement in Mars-domain themes and none can backfire.",
            },
            {
                "q": "Do Mars remedies remove Manglik Dosh?",
                "a": "They mitigate the difficult expressions of Manglik, but don't literally remove the astrological pattern. First check whether your Manglik is genuine or cancelled — many so-called Manglik charts have classical cancellations most calculators ignore (Cancer/Leo Ascendant, Mars in own sign or exalted, Jupiter aspect, Mars combust). See our Manglik Dosh article. If Manglik is genuinely present, the classical remedies are: weekly Hanuman Chalisa, matching with another Manglik partner (mutual cancellation), Tuesday fasting, donating red items on Tuesdays. Expensive 'Mangal nivaran' packages are selling anxiety, not tradition.",
            },
            {
                "q": "Why does my Mars keep causing anger issues?",
                "a": "Mars is energy. When it's blocked (chart shows weak Mars) it produces frustration and outbursts. When it's over-active (chart shows very strong Mars) it produces aggression and control issues. The remedy differs by which pattern you have. Weak Mars → strengthen through exercise, discipline, service. Over-active Mars → calm through Hanuman devotion, controlled anger practice, avoiding provocation. Rather than trying to eliminate Mars (which is impossible), work with him — channel the energy into disciplined action rather than suppressing or exploding it.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• Mars safe universal practices: Tuesday fasting, Hanuman Chalisa daily (esp. Tuesday/Saturday), Mars Beej mantra 'Om Kraam Kreem Kroum Sah Bhaumaya Namah'\n"
            '• Charity: red lentils (masoor dal), red cloth, jaggery, red-flowers to temples on Tuesdays\n'
            '• Behavioural: honour siblings (esp. brothers), donate blood, physical service to those in need\n'
            '• Gemstone (Red Coral / Moonga): CLASSICAL Mars gem BUT never without full chart consultation — Manglik or afflicted Mars can react badly\n'
            '• Hanuman worship is the STRONGEST classical Mars remedy — Hanuman is Rudra-Mars incarnate\n'
            "• Kartikeya/Muruga worship also strengthens Mars (Kartikeya is Mars's presiding deity)"
        ),
    ),
    Article(
        slug="saturn-remedies",
        title="Saturn Remedies: The Classical Vedic Approach to Working with Shani",
        summary="Saturn is Vedic astrology's most-feared planet and the most misunderstood. This guide walks through the genuine classical remedies from Rao's Ch. 34 — mantras, good deeds, deity worship, and the critical warnings about blue sapphire — without the vendor manipulation that dominates online content.",
        category="Remedies",
        hero_image="/static/learn/saturn-remedies/hero.svg",
        read_time="13 min",
        related=("shani-saturn", "sade-sati", "career-not-progressing"),
        faqs=(
            {
                "q": "Should I wear blue sapphire for Saturn?",
                "a": "Only after a proper chart consultation. Blue sapphire is Saturn's classical gemstone AND the single most dangerous gemstone in Vedic astrology when worn incorrectly. Rao (§34.2): wear a planet's gemstone only when that planet is a functional benefic in your chart. Saturn is a functional benefic mainly for Taurus and Libra ascendants (where Saturn is a Yogakaraka). For Aries, Cancer, Leo ascendants Saturn is a functional malefic and blue sapphire should be avoided. Even when indicated, classical tradition recommends a 3-5 day test period first — remove immediately if dreams disturb, sleep breaks, or health dips.",
            },
            {
                "q": "What is the safest Saturn remedy that works for anyone?",
                "a": "Daily Hanuman Chalisa recitation. This works via a classical myth — Hanuman once rescued Saturn, and Saturn promised anyone devoted to Hanuman would be protected from his harshest effects. Safe for any chart, no consultation needed, no cost. Other universal safe practices: (1) Weekly service to elderly relatives, (2) Sri Yantra worship, (3) Practicing patience deliberately in daily situations. None of these require chart consultation, none can backfire, and all four together are more effective than any expensive puja.",
            },
            {
                "q": "What is Saturn's mantra?",
                "a": "The classical bija (seed) mantra is: Om Praam Preem Praum Sah Shanaishcharaya Namah. Recite 108 times per session, aiming for daily practice on Saturdays especially. Rao (§34.4) recommends 19,000 total recitations for a full remedial cycle (typically completed over 40+ days). Best time: Saturday morning or Saturday sunset. For full nama stotras like Shani Chalisa, devotion matters more than pronunciation precision.",
            },
            {
                "q": "Is Sade Sati really as bad as people say?",
                "a": "Sade Sati is genuinely difficult but not the catastrophe online content portrays. It's Saturn's 7.5-year transit around your natal Moon sign — a period of restructuring, testing, and eventual maturation. Remedies during Sade Sati: daily Hanuman Chalisa (very effective), Saturday partial fasting (skip one meal), donations of mustard oil/black sesame/iron, service to elderly, avoiding major new commitments in the middle phase. Most people who work with Sade Sati's lessons emerge stronger. Most people who fight it find the difficulty extended.",
            },
            {
                "q": "Are expensive Shani puja packages worth it?",
                "a": "Almost never. Any priest demanding tens of thousands of rupees for a Shani nivaran puja is selling anxiety, not tradition. Genuine classical remedies are inexpensive — mantras + Chalisa + Hanuman worship + service to elderly costs almost nothing and is more powerful than expensive rituals done without devotion. The classical framing from Rao: 'Remedies are devotional acts, not transactional payments.' Anyone treating them as 'paying to make the problem go away' misunderstands the tradition and often makes the underlying pattern worse.",
            },
            {
                "q": "Can Saturn remedies remove my career problems?",
                "a": "No — and this is the honest answer. Rao (§34.1) is emphatic: 'Remedial measures manipulate the exact details of a fated pattern, not the pattern itself.' If Saturn's placement in your chart indicates a difficult career phase during a Saturn period, remedies can soften how the difficulty expresses — but they cannot make the phase disappear entirely. What genuine remedies do: refine the expression, deepen your capacity, align you with what Saturn is teaching. People who work with Saturn's discipline (rather than trying to escape it) often find his lessons open doors that no shortcut could have opened.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• Saturn safe universal practices: Saturday service (physical labor, help for elderly/poor), Shani Beej mantra 'Om Praam Preem Praum Sah Shanaishcharaya Namah', Dasharatha Krita Shani Stotram\n"
            '• Charity: black sesame seeds, iron items, mustard oil, black cloth to needy laborers on Saturdays\n'
            '• Behavioural: honour elders, feed stray animals (esp. black dogs, crows), avoid harming ants\n'
            '• Gemstone (Blue Sapphire / Neelam): the MOST DANGEROUS gemstone when worn wrong — NEVER without full chart consultation. Wrong Neelam can cause dramatic negative effects within 24-48 hours\n'
            '• Safer alternatives: amethyst (Jamunia) or blue topaz as substitute\n'
            '• Hanuman is the classical intercessor with Shani — Hanuman Chalisa Saturdays is safest\n'
            '• Peepal-tree Saturday oil lamp is a classical safe practice'
        ),
    ),
    Article(
        slug="marriage-delayed",
        title="Why Is My Marriage Delayed? 7 Chart Signals from Your Kundali",
        summary="Marriage delay is one of the most common Vedic astrology questions — and one where classical analysis differs sharply from fear-based online content. This guide walks the 7 chart signals (7th house, Venus/Jupiter, Manglik, current Dasha, Navamsha, Kundli matching, karmic dispositor) with honest classical framing.",
        category="Life Questions",
        hero_image="/static/learn/marriage-delayed/hero.svg",
        read_time="14 min",
        related=("manglik-dosh", "kundali-matching-ashtakoot-guna-milan", "shukra-venus-in-vedic-astrology"),
        faqs=(
            {
                "q": "How do I know if my chart shows marriage delay?",
                "a": "Check three primary signals: (1) Is your 7th house lord in a dusthana (6th, 8th, 12th house)? (2) Is Venus (for men) or Jupiter (for women) weak, combust, or aspected by Saturn/Rahu? (3) Is Mars in any of the 6 Manglik houses without a cancellation? If two or more signals apply, classical astrology suggests marriage typically comes later than culturally typical — often 30+. Generate your free Janma Kundli on Shubh Bhagya to check specific positions.",
            },
            {
                "q": "What is the most important house for marriage in Vedic astrology?",
                "a": "The 7th house (Kalatra Bhava) — spouse, marriage, partnerships. But marriage timing depends on the 7th lord's placement AND the current Dasha AND the strength of Venus (men) / Jupiter (women) AND the Navamsha (D-9) chart. No single signal decides marriage — the pattern of all signals together determines timing.",
            },
            {
                "q": "Does Manglik Dosh really block marriage?",
                "a": "Not automatically. Manglik Dosh is present when Mars is in the 1st, 2nd, 4th, 7th, 8th, or 12th house — but classical texts include several cancellation conditions most calculators ignore: Cancer or Leo Ascendant (Mars is Yogakaraka), Mars in own sign (Aries/Scorpio) or exalted (Capricorn), Jupiter aspecting or conjunct Mars, Mars combust, and mutual Manglik matching. See our dedicated Manglik Dosh article for complete details. Uncancelled Manglik tends to delay marriage but does NOT mean unmarriageable.",
            },
            {
                "q": "How does the current Dasha affect marriage timing?",
                "a": "Marriage tends to happen during specific Vimshottari Dasha windows — usually when the Antardasha of your 2nd/7th/11th house lord runs, OR when Venus's or Jupiter's Antardasha comes up. Many 'delayed marriage' complaints turn out to be someone moving through a period ruled by a planet with no natural relationship to marriage themes. When that Dasha ends and a marriage-relevant planet takes over, the window opens. Check your Dasha panel on your Kundli to see your upcoming marriage windows.",
            },
            {
                "q": "Should I do expensive puja for marriage delay?",
                "a": "Almost never. Any priest asking for tens of thousands of rupees for a 'marriage nivaran puja' is selling anxiety, not tradition. Genuine classical remedies are simple: Venus/Jupiter mantras, appropriate weekday fasting (Friday for Venus, Thursday for Jupiter), offering appropriate coloured flowers, worship of Shiva-Parvati as archetypal marriage. If Manglik-specific, matching with another Manglik partner is the classical solution — not a puja. Gemstones should never be worn without proper chart consultation.",
            },
            {
                "q": "What is Navamsha (D-9) and why does it matter for marriage?",
                "a": "The Navamsha is a divisional chart derived from the birth chart — each 30° sign is divided into 9 parts of 3°20' each. Classical Vedic astrology considers the D-9 chart the primary reference for marriage — often more important than the D-1 (rasi chart) for marriage-specific questions. The D-9 Ascendant sign describes the spouse's fundamental character. Planets in the D-9 7th house describe marriage quality more accurately than planets in the D-1 7th. This is one of the most consistently emphasised classical rules for marriage assessment.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• Marriage-delay indicators: Saturn or Rahu in 7th (or aspecting it), weak/afflicted 7th lord, retrograde 7th lord\n"
            "• Karaka afflictions: Venus (male chart) or Jupiter (female chart) combust or debilitated\n"
            "• D-9 Navamsha is the PRIMARY chart for marriage — often more decisive than D-1\n"
            "• Delay ≠ denial — Saturn-driven late marriages (mid-30s+) often prove more stable\n"
            "• Remedies focus on strengthening the marriage karaka (Venus for men, Jupiter for women), NOT 'removing' the yoga\n"
            "• Timing: activate in Venus / Jupiter / 7th-lord Dasha or Antardasha"
        ),
    ),
    Article(
        slug="financial-struggles",
        title="Why Do I Keep Losing Money? 7 Chart Signals for Financial Struggles",
        summary="If money keeps slipping through your hands, Vedic astrology has a specific framework for understanding why. Walks through 7 wealth-related chart signals — 2nd house, Jupiter, 11th house, classical Dhana Yogas, Daridra Yogas, current Dasha, Rahu-Ketu axis — with genuine remedies and honest patterns.",
        category="Life Questions",
        hero_image="/static/learn/financial-struggles/hero.svg",
        read_time="14 min",
        related=("guru-jupiter-in-vedic-astrology", "gajakesari-yoga", "vimshottari-dasha-explained"),
        faqs=(
            {
                "q": "Which house is most important for wealth in Vedic astrology?",
                "a": "Four houses together govern wealth: 2nd (liquid wealth, family resources), 5th (purva-punya and luck), 9th (fortune and blessing), 11th (gains and income beyond salary). These are the dhana sthanas. Wealth flows when their lords are strong and mutually connected. If your wealth-signature is weak in multiple of these houses, that's the classical pattern for financial struggle regardless of how hard you work.",
            },
            {
                "q": "What is Dhana Yoga and how do I know if I have it?",
                "a": "Dhana Yogas are classical combinations that produce wealth. Common ones: 2nd and 11th lords in mutual conjunction or exchange; 5th and 9th lords associated; Jupiter in the 2nd/5th/11th house; Jupiter aspecting your 2nd or 11th; Chandra-Mangala Yoga (Moon+Mars conjoined); Vipreet Raja Yoga (dusthana lords in dusthanas — the 'poverty to riches' arc). Generate your free Janma Kundli on Shubh Bhagya — the Yogas panel automatically flags common wealth yogas.",
            },
            {
                "q": "What is Daridra Yoga? Does it mean I will be poor?",
                "a": "No. Daridra Yoga does not mean poverty — it means wealth requires disproportionate effort and comes intermittently. Common Daridra patterns: 2nd or 11th lord in 6/8/12 house afflicted; Jupiter debilitated combined with weak 2nd lord; Kemadruma Yoga (isolated Moon); all dhana-sthana lords weak. Many people with Daridra Yoga build lives of adequacy through disciplined systematic work and mid-life success. Understanding the pattern helps you plan around it — prioritise steady income over speculation, build reserves during good periods.",
            },
            {
                "q": "How does my current Dasha affect my wealth?",
                "a": "Wealth accumulation is rarely uniform across a lifetime. Most people have specific 5-15 year windows when wealth accumulates unusually easily, and specific 5-15 year windows when it drains regardless of effort. Common wealth-favourable Dashas: Jupiter (16 years), Venus (20 years if well-placed), Mercury (17 years if Mercury is business-oriented). Common wealth-difficult Dashas: Saturn (19 years, though lessons often set up wealth in the following Mercury period), Rahu (18 years — unpredictable), Ketu (7 years).",
            },
            {
                "q": "Should I wear yellow sapphire for wealth?",
                "a": "Not without a proper chart consultation. Yellow sapphire is Jupiter's stone and CAN strengthen a well-placed Jupiter, but wearing it when Jupiter is a functional malefic in your chart (which depends on your Ascendant) can worsen the affliction. Yellow sapphire is generally safer than most other gems, but still requires classical analysis. Better free/safer alternatives: Sri Sukta recitation, worship of Lakshmi, Thursday fasting, feeding brahmins or the poor — no chart-consultation needed and no risk of worsening the pattern.",
            },
            {
                "q": "What are the genuine classical remedies for financial struggles?",
                "a": "The most reliable: (1) Sri Yantra worship — the classical universal wealth-generating practice, can be done by anyone. (2) For Jupiter strengthening: Sri Sukta, Guru mantra (Om Brihaspataye Namah), Thursday fasting, feeding brahmins. (3) For 2nd house strengthening: disciplined honest speech (2nd rules speech, honest speech produces wealth), generous feeding of family and guests. (4) For 11th house gains: serving elder siblings and mentors. (5) For Rahu-related unstable wealth: Rahu mantra, donating black sesame. Avoid: expensive 'Lakshmi puja packages', speculation without genuine analysis, treating astrological wealth Dashas as guaranteed outcomes.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 7 chart signals for financial difficulty: weak 2nd house/lord, weak 11th house/lord, 2nd/11th lord in dusthana (6/8/12), afflicted Jupiter (wealth karaka), afflicted Venus (money-flow karaka), Sade Sati impact on 2nd, malefic transits to 11th\n'
            '• Dhana Yogas (wealth combinations) require multiple positive factors — check 2+5+9+11 house lords for connections\n'
            '• Daridra Yogas (poverty combinations): 2nd/11th lord in 6th/8th/12th\n'
            '• Not fate — signals difficulty, not permanent poverty. Chart interacts with effort + circumstance\n'
            '• Timing: financial pressure often coincides with Saturn/Rahu Mahadasha or Sade Sati\n'
            '• Remedy focus: strengthen Jupiter (Thursdays) + Venus (Fridays); charity to those with less; never gamble to solve'
        ),
    ),
    Article(
        slug="career-not-progressing",
        title="Why Your Career Is Not Progressing: 7 Chart Signals to Check in Your Kundali",
        summary="If you feel your career keeps stalling despite hard work, Vedic astrology has a specific framework for understanding why. This guide walks through the 7 chart signals — 10th house, Sun, Saturn, Dashas, 6th/8th houses, career yogas, Rahu-Ketu axis — with what each affliction means and what to do.",
        seo_title="Career Not Progressing? 7 Kundali Signals to Check",
        seo_description="Career stalling despite hard work? 7 Vedic chart signals — 10th house, Sun, Saturn, Dasha — decode what's blocking you and what to do about it.",
        category="Life Questions",
        hero_image="/static/learn/career-not-progressing/hero.svg",
        read_time="12 min",
        related=("shani-saturn", "sade-sati", "vimshottari-dasha-explained"),
        faqs=(
            {
                "q": "Can astrology really tell me why my career is stuck?",
                "a": "Vedic astrology describes patterns and tendencies, not fixed outcomes. What it can honestly do is identify specific chart signatures classically associated with career blockage — weak 10th house lord, afflicted Sun, current Saturn/malefic Dasha, dusthana placements — and help you understand which patterns apply to your specific chart. Two people with identical 'career stagnation' chart signals can end up in different places based on their choices. The chart tells you the terrain; you still have to walk it.",
            },
            {
                "q": "What is the most important house for career in Vedic astrology?",
                "a": "The 10th house (Karma Bhava) is the primary house of profession, status, and worldly achievement. When checking career, always start here. Check: which sign is on your 10th, which planet rules it (that's your 10th lord), where that planet sits, and whether it's afflicted. The 10th lord's placement is often the single most decisive career signal — a strong 10th lord in a good house typically produces smooth career growth; a 10th lord in a dusthana (6/8/12) often produces the classical 'grinding but not advancing' pattern.",
            },
            {
                "q": "Does Saturn always block career?",
                "a": "No — Saturn is the teacher of patience, not the villain online astrology makes him out to be. Saturn in the 10th house (Digbala) is actually good for career — it gives durable, structured, institutional careers that build over decades. Saturn's 'blockages' usually correspond to the classical Vedic idea of karma phal: the work-fruit that comes when you've done enough foundation work. Saturn insists you do the unglamorous foundation before receiving the result. Those who skip steps find Saturn blocking them; those who do the work often find Saturn eventually opening doors.",
            },
            {
                "q": "How does the current Dasha affect my career?",
                "a": "This is where astrology becomes specific about timing. Career blockage that feels chronic is often tied to a specific Mahadasha or Antardasha that's due to end. Generate your free Janma Kundli on Shubh Bhagya and check the Dasha panel. If you're in a malefic-ruled period (Saturn, Mars, Rahu, Ketu, Sun) or a period ruled by a planet that governs your 6th, 8th, or 12th house, the career difficulty may lift when the period changes. Some Antardashas are simply hostile to career advancement; others are unusually generous.",
            },
            {
                "q": "Should I change careers if my chart shows blockage?",
                "a": "Not always — sometimes the answer is remedy (mantras, gemstones after consultation, patience through a dasha), sometimes it's waiting for a specific period to end, sometimes it's genuine redirection. If your Rahu is in the 10th house and you're in a very traditional career, or if your 10th lord is in the 12th (foreign) house and you've never left your home city, the chart may be pointing toward a genuine mismatch. But if your career-signature is strong and you're just in a rough Antardasha, staying the course through the period is often the right call.",
            },
            {
                "q": "What are the fastest classical remedies for career blockage?",
                "a": "Depends on which planet is afflicted. For weak Sun (career visibility): Aditya Hridayam mantra, Sunday fasting, arghya (water offering to Sun at dawn). For Saturn delays: Shani chalisa, Saturday oil-lamp, service to elderly/poor. For general 10th house strengthening: Vishnu Sahasranama, worship of your ishta devata, disciplined daily work as a spiritual practice. Never wear gemstones without a proper chart consultation — wrong stones can worsen the affliction. The most reliable remedy is often the simplest: doing genuinely good work in the classical Vedic spirit of nishkama karma (action without attachment to reward).",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 7 chart signals for career stagnation: weak 10th lord, 10th lord in dusthana (6/8/12), afflicted Sun (visibility) or Saturn (structure), current Ketu/Saturn Mahadasha, malefic transits to 10th house, weak D-10 Dashamsa Ascendant\n'
            "• Timing: career growth often blocked during Saturn Mahadasha's early years, Sade Sati peak phase, Ketu Antardasha windows\n"
            '• The pattern often SHIFTS at Saturn return (~29-30) or during favorable Jupiter transit to 10th\n'
            '• 10th lord placement matters more than planets IN 10th — see 10th-lord-in-6th-house-career for specific dusthana pattern\n'
            '• Some blockages are alignment issues: chart shows technical/service career, person pursues creative/hype fields\n'
            '• Remedies: strengthen 10th lord, aligned service (donate skill to needy), Hanuman Chalisa Tuesday/Saturday'
        ),
    ),
    Article(
        slug="saturn-in-10th-house-career",
        title="Saturn in the 10th House: Career Effects, Timing, and Remedies",
        summary="Saturn in the 10th house is one of the most misread placements in Vedic astrology. It is his digbala — his strongest directional placement. The pattern is delay-then-elevation, not blockage. Here is what Saturn-in-10 actually does, when it manifests, and how to work with it.",
        seo_title="Saturn in 10th House: Career Effects & Remedies",
        seo_description="Saturn in the 10th house — the delay-then-elevation career pattern. Effects, sign variations, Dasha timing, and classical remedies, explained honestly.",
        category="Life Questions",
        hero_image="/static/learn/saturn-in-10th-house-career/hero.svg",
        read_time="11 min",
        last_updated="2026-07",
        related=("career-not-progressing", "saturn-remedies", "sade-sati"),
        faqs=(
            {
                "q": "Is Saturn in the 10th house good or bad for career?",
                "a": "Classical Vedic tradition considers Saturn in the 10th house one of the stronger career placements — it is Saturn's digbala (directional strength). But the pattern is delay-then-elevation, not smooth early success. The waiting years (roughly ages 22–35) often feel harder than peers'; the elevation phase (roughly ages 36–56) tends to be where Saturn-10 careers peak. Whether the pattern manifests as growth or as chronic frustration depends on Saturn's sign, aspects, the 10th lord's condition, and the current Dasha. Generate your free Janma Kundli on Shubh Bhagya to see the exact configuration.",
            },
            {
                "q": "Does Saturn in the 10th house always give a government job?",
                "a": "Government service is one of the classical career signatures for Saturn in the 10th, but it is not the only one. Saturn rules structure, longevity, service, and institutional endurance — that shows up as government, judiciary, law, engineering, infrastructure, agriculture, elderly care, manufacturing, and long-tenure roles in private companies (operations, compliance, risk, quality). The through-line is: institutions that reward tenure and thoroughness. Hype-driven or youth-oriented fields tend to fight the placement.",
            },
            {
                "q": "At what age does Saturn in the 10th house give career results?",
                "a": "The classical pattern peaks in the second half of life — typically ages 36–56, after the first Saturn return around age 29–30. The delay is genuine: recognition often lags contribution by several years. Timing is also shaped by when Saturn's own Mahadasha or Antardasha activates in your Vimshottari sequence, which depends on your birth nakshatra. Some Saturn-10 natives peak in their thirties because Saturn's Dasha lands there; others peak in their fifties for the same reason.",
            },
            {
                "q": "Can the effects of Saturn in the 10th house be cancelled?",
                "a": "Not cancelled, but significantly moderated. Jupiter's aspect on Saturn or on the 10th house is the classical rescuer — it softens the harshness and adds ethical authority. A strong Sun elsewhere in the chart complements Saturn-10 (Sun provides visibility, Saturn provides structure). A well-placed 10th lord amplifies the good side. Debilitated Saturn in Aries can be partially rescued through Neechabhanga (cancellation of debility) if Moon or Mars are well-placed. Full cancellation is a marketing claim, not a classical concept.",
            },
            {
                "q": "What careers suit Saturn in the 10th house natives?",
                "a": "Government service and civil administration, judiciary and law, engineering and infrastructure (roads, bridges, dams, mining), agriculture and land-based work, elderly care and geriatric medicine, manufacturing and industrial trade, long-form scholarship and archival research, and load-bearing corporate functions like operations, compliance, quality, and risk. The unifying theme is: structured domains where seniority and thoroughness are the actual currency, and where tenure compounds into authority.",
            },
            {
                "q": "How do I strengthen Saturn for career growth?",
                "a": "Safe universal practices (no chart consultation needed): Saturday service (physical labor, help for elderly and poor), donating black sesame, iron, or mustard oil on Saturdays, chanting the Shani Beej mantra Om Praam Preem Praum Sah Shanaishcharaya Namah as a slow long-term practice, reciting Dasharatha Krita Shani Stotram on Saturdays, and lighting a mustard-oil lamp under a peepal tree on Saturday evening. Avoid: expensive Shani nivaran puja packages, and never wear blue sapphire without proper chart consultation — it is the single most dangerous gemstone when worn incorrectly. See our full Saturn remedies guide for details.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• Saturn in 10th = Saturn's digbala (directional strength) — one of the STRONGEST classical career placements\n"
            "• Delay-then-elevation pattern:\n"
            "    - Slow early career (~ages 22-35): hard work, under-recognition\n"
            "    - Turning point at Saturn return (~29-30)\n"
            "    - Elevation phase (~36-56): institutional respect that often outlasts peers'\n"
            "• Best-fit careers: government, judiciary, law, engineering, agriculture, elderly care, long-tenure private roles\n"
            "• Fights hype-driven, youth-focused, or short-cycle careers\n"
            "• Safe remedies: Saturday service, black-sesame/iron/mustard-oil charity, Shani Beej mantra\n"
            "• NEVER wear blue sapphire (Neelam) without full chart consultation — most dangerous gemstone if worn wrong"
        ),
    ),
    Article(
        slug="career-during-sade-sati",
        title="Career During Sade Sati: The 7.5-Year Career Reckoning",
        summary="Sade Sati is often felt at work first. The Arambha, Madhya, and Uttara phases each have a specific career arc — quiet restructuring, forced pivots or breakthroughs, and slow rebuild. Here is what actually happens in each phase, when to change jobs, why some people get promoted, and what to do if you have just been laid off mid-transit.",
        seo_title="Career During Sade Sati: What to Expect & Do",
        seo_description="Sade Sati career effects across the 3 phases — job loss, promotions, when to change jobs, what to do if laid off. Honest classical guidance, no fear.",
        category="Life Questions",
        hero_image="/static/learn/career-during-sade-sati/hero.svg",
        read_time="11 min",
        last_updated="2026-07",
        related=("sade-sati", "saturn-remedies", "career-not-progressing"),
        faqs=(
            {
                "q": "Does Sade Sati always cause job loss?",
                "a": "No. Job loss is a common Sade Sati outcome, especially in the Madhya (peak) phase, but it is far from universal. People with strong natal Saturn — in own sign (Capricorn or Aquarius), exalted in Libra, or in a kendra with Jupiter's support — often experience Sade Sati as a period of career elevation rather than loss. People already working in Saturn-native fields (government, judiciary, engineering, infrastructure, elderly care, agriculture, long-form scholarship) frequently see their biggest promotion of the decade during Sade Sati. The actual outcome depends on natal Saturn's strength, current Dasha, industry, and how willingly the person engages the transit. Generate your free Kundli on Shubh Bhagya to see your natal Saturn's condition.",
            },
            {
                "q": "Is it OK to change jobs during Sade Sati?",
                "a": "Yes, with timing. Classical Vedic tradition cautions against major voluntary moves in the first year of Madhya (peak) — decisions taken in that window often look wrong within twelve months. The safer sub-windows are late Madhya (the final 12–15 months of the peak phase, when Saturn has done most of its subtracting) and Uttara (the rebuild phase). If a change is forced on you by circumstances rather than chosen, treat it as data — take it thoughtfully, do not panic-search, and be willing to accept short contract work while a longer offer matures. Saturn punishes haste more than he punishes patience.",
            },
            {
                "q": "Can I get a promotion during Sade Sati?",
                "a": "Yes — and for certain chart configurations it is unusually likely. Classical tradition explicitly names the pattern: seniors, people in Saturn-native careers, and natives with strong natal Saturn often receive their most significant institutional recognition during the 7.5-year transit. This is because Saturn rewards patient, structural, long-tenure work — exactly the kind of work senior professionals are usually doing. Promotions during Sade Sati tend to come in late Madhya or Uttara rather than Arambha, and they usually reward years of previous groundwork rather than sudden brilliance.",
            },
            {
                "q": "Should I start a business during Sade Sati?",
                "a": "Not usually optimal, but not forbidden. The Vedic caution against major long-cycle commitments — a new company, significant debt, a co-founder relationship binding you for a decade — applies particularly to the first year of Madhya. Businesses started in that window survive but disproportionately struggle in years three to five. If you must start a business during Sade Sati, the safer sub-windows are Arambha (planning and quiet incorporation) and late Madhya to Uttara (launch phase, when the ground is more stable). And avoid the founder-with-partner setup unless the partner has been tested through a full year of Madhya first.",
            },
            {
                "q": "Which phase of Sade Sati is worst for career?",
                "a": "Madhya (Peak), the middle 2.5 years when Saturn transits directly on the natal Moon, is the most consequential and typically the hardest for career. This is when forced pivots, layoffs, business restructuring, and health-driven role changes cluster. Arambha (Rising) is quieter — more the sense of losing an internal sponsor, invisible support drying up, isolation from the inner circle at work. Uttara (Setting) is the rebuild — quieter career, family and career negotiating, savings discipline forced, but the acute pressure of Madhya has passed. The rank order for career difficulty is generally Madhya > Arambha > Uttara.",
            },
            {
                "q": "What remedies help career during Sade Sati?",
                "a": "Universal Saturn practices apply, with a career emphasis. Recite the Hanuman Chalisa daily (especially on Saturdays) — classical Vedic tradition names Hanuman as the deity whose recitation softens Shani's severity. Serve elders in your professional environment (Saturn rules seniority; being genuinely useful to older colleagues is direct Saturn karma). Work harder, not less — Saturn rewards effort, not escapism. Donate on Saturdays (black sesame, mustard oil, dark cloth, iron, footwear for the elderly poor). Avoid expensive Shani nivaran puja packages — the vendor manipulation around Sade Sati is enormous and largely ineffective. And never wear blue sapphire without a proper chart consultation — it is Saturn's most powerful gem and, when wrong for the chart, the fastest way to destabilise a difficult transit further.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• Sade Sati's 7.5 years typically forces career restructuring — job change, responsibility increase, or exit\n"
            '• Rising phase (12th from Moon): financial pressure, work-doubt, quiet exit planning\n'
            '• Peak phase (1st from Moon): major visible restructuring — promotion, demotion, or full career change\n'
            '• Setting phase (2nd from Moon): rebuilding on new foundation, family-financial adjustment\n'
            '• Sade Sati during Saturn Mahadasha (compound Saturn) = deepest restructuring\n'
            '• Sade Sati during Jupiter/Venus Mahadasha = softer, mentor/opportunity support arrives\n'
            '• Best-fit career strategies: choose depth over breadth, longer-tenure roles, service-oriented pivots\n'
            '• Worst-fit: high-hype speculative moves, gambling on quick wins — Saturn punishes shortcuts'
        ),
    ),
    Article(
        slug="debilitated-sun-career",
        title="Debilitated Sun in Your Kundli: Why Authority Feels Off and How to Fix It",
        summary="Sun debilitated in Libra is one of the most common 'why do I struggle with authority' chart signatures. It does not remove capability — it reshapes leadership into negotiation-forward, coalition-holding, advisory forms. Here is what the placement actually does, the Neecha Bhanga cancellations most explanations miss, which careers suit debilitated Sun natives, and honest classical remedies.",
        seo_title="Debilitated Sun in Kundli: Career Effects & Fix",
        seo_description="Sun in Libra debilitated — what it does to authority and career, Neecha Bhanga cancellation rules, best-fit careers, and classical remedies. No fear.",
        category="Life Questions",
        hero_image="/static/learn/debilitated-sun-career/hero.svg",
        read_time="12 min",
        last_updated="2026-07",
        related=("surya-sun-in-vedic-astrology", "sun-mahadasha", "career-not-progressing"),
        faqs=(
            {
                "q": "Is a debilitated Sun always bad?",
                "a": "No. Debilitated Sun (Sun in Libra) reshapes how authority operates in your life — from commanded to negotiated — but it does not remove capability. Many highly successful leaders across history and industry carry this placement, especially in fields where diplomatic authority matters more than dominant authority: judiciary, mediation, senior advisory, coalition politics, academic leadership. When Neecha Bhanga (debilitation cancellation) applies, the placement can even become a source of unusual strength called Neecha Bhanga Raja Yoga, a genuine classical yoga. The actual outcome depends on whether cancellation conditions are present, which house Sun sits in, and how well the career direction is matched to the placement.",
            },
            {
                "q": "What is Neecha Bhanga Raja Yoga for Sun?",
                "a": "Neecha Bhanga is classical Vedic cancellation of a planet's debilitation, and when it applies, the placement can produce genuine strength. The four most commonly cited conditions for Sun's debilitation in Libra to cancel: (1) Venus (the lord of Libra) is in a kendra (1st/4th/7th/10th) from the Lagna or Moon; (2) Saturn (which is exalted in Libra) is in a kendra from the Lagna or Moon; (3) Mars (which rules Aries, Sun's exaltation sign) is in a kendra from the Lagna or Moon; (4) Sun is exalted in the navamsha (D-9) chart. If any of these are present, the debilitation is functionally cancelled and the person often produces late-blooming institutional recognition and respected leadership. Generate your free Kundli on Shubh Bhagya to see if any of these apply.",
            },
            {
                "q": "Which careers suit debilitated Sun natives?",
                "a": "Careers where authority is earned through respect rather than commanded through position. The strongest fits: mediation and arbitration, judiciary and law, senior advisory and consulting, diplomacy and international relations, academic leadership (dean and department head roles), partnership-based professional services, collaborative arts (especially music and directing), and coalition politics. Careers that fight the placement: hard-charging sales, aggressive founder roles requiring unwavering conviction, competitive solo politics, and any role that requires you to dominate a room by presence alone. Debilitated Sun natives can absolutely succeed in tough-authority fields, but the placement works with them in negotiation-forward fields and often against them in dominance-forward fields.",
            },
            {
                "q": "How to strengthen a debilitated Sun?",
                "a": "Safe universal classical practices: offer arghya (water offering) to the rising Sun at dawn, especially on Sundays; recite the Aditya Hridayam (12 or 108 times on Sundays); practice daily Surya Namaskar; slow long-term chanting of the Sun beej mantra Om Hraam Hreem Hraum Sah Suryaya Namah; donate wheat, jaggery, red cloth, or copper vessels on Sundays; and consciously honour the father and elders in your life (Sun is the karaka of the father — repairing that relationship is often the deepest remedy). Never wear a ruby or Sun-related gemstone without a proper chart consultation — for a functional malefic Sun, ruby can amplify difficulty rather than help. Pattern-alignment remedies (matching career to placement) matter more than physical remedies.",
            },
            {
                "q": "Does Sun in Libra mean no government job?",
                "a": "No, this is a common misreading. Sun rules government and authority, so weak Sun sometimes reduces natural pull toward pure command-and-control government roles, but the placement can succeed excellently in government contexts that reward negotiation and judgement — judiciary, senior civil service in policy and diplomatic roles, arbitral bodies, election commissions, coalition ministerial roles. Many senior judges, diplomats, and civil servants carry this placement. What often does not fit: hard-charging populist political roles requiring dominant personal branding. What often does fit: institutional government roles where longevity, fairness, and judgement compound into respected authority.",
            },
            {
                "q": "Can debilitated Sun give success?",
                "a": "Yes, and often significant success — but the arc is typically late-blooming rather than early-flashy. The common pattern: early career of over-performance without proportionate recognition, mid-career forced elevation into a leadership role the person did not overtly seek, and late-career unexpected authority earned through years of quiet respect. When Neecha Bhanga applies, the late-career recognition can be substantial (chief justice, senior advisor, coalition leader, respected academic head). The people who suffer most with this placement are those who fight it — trying to force themselves into dominance-forward careers that punish the diplomatic instinct. Those who work with the placement often produce the most respected version of leadership in their field.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Debilitated Sun = Sun in Libra (deepest 10°). Reshapes authority expression, does NOT remove capability\n'
            '• Career pattern: over-perform without recognition early → forced-into-leadership mid → respected-authority late\n'
            '• Best-fit careers: negotiation-forward (judiciary, arbitration, advisory, diplomacy, consulting, academia)\n'
            '• Fights: dominance-forward (aggressive sales, competitive politics, alpha-founder roles)\n'
            '• Neechabhanga Raja Yoga (cancellation): Venus/Saturn/Mars in kendra from Lagna/Moon, OR Sun exalted in D-9\n'
            '• When cancelled, produces unusual late-career strength — chief-justice / senior-advisor patterns\n'
            '• Remedies: Sun-strengthening practices (Surya Namaskar, water offering), honour father-figures, wheat/jaggery Sunday charity'
        ),
    ),
    Article(
        slug="jupiter-in-10th-house-career",
        title="Jupiter in the 10th House: Career, Hamsa Yoga, and the Dharmic Path",
        summary="Jupiter in the 10th house is a natural karaka in the karma house — wisdom applied to profession. When Jupiter sits here in Cancer, Sagittarius, or Pisces, he forms Hamsa Yoga — one of the five Panch Mahapurush yogas — producing a lifelong gift of scholarly authority. When debilitated in Capricorn or afflicted, the karma-dharma path stalls. This guide covers the Hamsa Yoga configuration, the debilitated pattern, per-ascendant variations, the career fields Jupiter actually supports, and honestly what this placement does NOT automatically produce.",
        seo_title="Jupiter in 10th House: Career, Hamsa Yoga & Timing",
        seo_description="Jupiter in the 10th house — the Hamsa Yoga career placement. Per-ascendant effects, timing windows, dharmic career fit, and honest remedies.",
        category="Life Questions",
        hero_image="/static/learn/jupiter-in-10th-house-career/hero.svg",
        read_time="11 min",
        last_updated="2026-07",
        related=("guru-jupiter-in-vedic-astrology", "sun-in-10th-house-career", "vimshottari-dasha-explained"),
        faqs=(
            {
                "q": "Is Jupiter in the 10th house always good?",
                "a": "Not automatically. Jupiter in the 10th is one of the most fortunate career placements when Jupiter is dignified — in Sagittarius, Pisces, or exalted in Cancer — where it forms Hamsa Yoga (a Panch Mahapurush yoga). When debilitated in Capricorn (Aries ascendant), combust by Sun, retrograde without additional support, or conjoined with Rahu (Guru Chandala Yoga), the placement's benefits diminish significantly. Jupiter is a 10th house karaka but does NOT get digbala (directional strength) in the 10th — his digbala is in the Lagna. So Jupiter in the 10th needs additional dignity to produce the fullest classical outcomes. Generate your free Janma Kundli on Shubh Bhagya to check Jupiter's exact configuration in your chart.",
            },
            {
                "q": "What is Hamsa Yoga and does Jupiter in the 10th create it?",
                "a": "Hamsa Yoga is one of the five Panch Mahapurush (great person) yogas — the Jupiter version. It forms when Jupiter is in his own sign (Sagittarius or Pisces) or exalted (Cancer) AND in a kendra (1st, 4th, 7th, or 10th house) from the Lagna. Jupiter in the 10th qualifies for Hamsa Yoga specifically for three ascendants: Libra (Jupiter exalted in Cancer 10th — the strongest configuration), Gemini (Jupiter in own sign Pisces 10th), and Pisces (Jupiter in own sign Sagittarius 10th). Classical texts describe Hamsa Yoga natives as dignified, ethical, respected for judgement, drawn toward dharmic professions, and long-lived. The 10th house version is especially career-active — teaching, judiciary, advisory, spiritual leadership, and publishing are common signatures.",
            },
            {
                "q": "Which professions are best for Jupiter in the 10th house?",
                "a": "Careers where wisdom, judgement, or ethical authority is the actual product. Strongest fits: teaching at any level (schoolteacher to professor to formal mentor); law and jurisprudence (especially advisory, family, constitutional, and appellate work); medicine (particularly long-term care and complex-condition management); finance and wealth advisory (fiduciary, long-view, wealth-preservation side); publishing and editorial (books, journals, curation); religious and spiritual counsel; non-profit and foundation leadership; diplomacy and international relations. Careers that fight this placement: hard-charging sales, transactional dealmaking, industries rewarding youth and speed over depth, and short-cycle competitive businesses. Jupiter in the 10th produces careers that compound slowly through respect rather than win quickly through pressure.",
            },
            {
                "q": "When does Jupiter in the 10th house give career results?",
                "a": "Three timing windows. First — Jupiter Mahadasha (16 years, second-longest Vimshottari period after Venus) is the peak career activation window; recognition, institutional elevation, and wealth accumulation through dharmic work cluster here. Second — Jupiter Antardasha within another Mahadasha (roughly 2 years 4 months to 2 years 10 months depending on the outer Mahadasha lord) produces smaller versions of the same signature. Third — Jupiter transits: Jupiter takes about 12 years to complete a zodiacal cycle, and when he transits over the natal 10th house or aspects it, career expansion opportunities cluster; Jupiter returns (approximately ages 12, 24, 36, 48, 60, 72) frequently mark career inflection points.",
            },
            {
                "q": "Does retrograde Jupiter in the 10th house give different results?",
                "a": "Yes — retrograde Jupiter is not weaker, but inward. Retrograde Jupiter in the 10th often produces a career where the person's real work is done privately, refined internally, and only later recognised publicly. Scholars whose books arrive after decades of quiet research, researchers whose theories are appreciated years after publication, creators whose reputation grows posthumously or after a long lag — all common retrograde-Jupiter-in-10 patterns. The classical reading is neither straightforwardly beneficial nor harmful; it simply demands a different relationship to visibility. If you are early-career with retrograde Jupiter in the 10th and feeling the work is not being seen, the chart is often describing a delayed-recognition pattern rather than an unrecognised one.",
            },
            {
                "q": "Does Jupiter in the 10th house automatically bring wealth?",
                "a": "No — this is one of the most common misreadings. Wealth in Vedic astrology is read through the Dhana Yogas — connections between the 2nd house (accumulated wealth), 11th house (gains), 5th house (past-life merit), and their respective lords. Jupiter in the 10th elevates the career itself, but converting career elevation into accumulated wealth requires the wealth trinity (2nd + 11th + 5th) to also be strong. Many charts with Jupiter in the 10th produce distinguished careers with modest actual wealth. Others combine Jupiter in the 10th with strong Dhana Yogas and produce both career elevation and wealth. Reading Jupiter in the 10th as an automatic wealth marker sets false expectations. What the placement reliably produces is respect and dharmic career direction; wealth is a separate reading.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Jupiter in 10th = natural karaka in karma house (Jupiter is a 10th house karaka)\n'
            '• BUT: Jupiter does NOT have digbala in 10th — his digbala is in Lagna. Needs additional dignity to shine\n'
            '• Hamsa Yoga forms if Jupiter is in Cancer/Sagittarius/Pisces in 10th (Panch Mahapurush yoga)\n'
            '• Best-fit careers: teaching, judiciary, law, medicine, finance/wealth advisory, publishing, religion, non-profit\n'
            '• Debilitated in Capricorn (Aries ascendant): capable but institutional recognition stalls; check Neechabhanga\n'
            '• Guru Chandala Yoga (Jupiter+Rahu): scandal-prone wisdom; unorthodox teachings\n'
            '• Jupiter Mahadasha (16 years) is peak activation — recognition, wealth via dharma, marriage often triggers\n'
            '• Does NOT auto-produce wealth — check Dhana Yogas (2+11+5 house connections) separately'
        ),
    ),
    Article(
        slug="sun-in-10th-house-career",
        title="Sun in the 10th House: Career, Authority, and the Digbala Signature",
        summary="Sun in the 10th house is one of the strongest career placements in Vedic astrology — the natural karaka of the 10th, holding his digbala there. The pattern is natural authority rather than fought-for authority. But the placement's dignity, sign, and Dasha timing determine whether it produces the classical government/leadership outcomes or ego problems and father struggles. This guide walks the strong pattern, the shadow pattern, per-ascendant variations, timing windows, the father signature, and honest remedies scoped to your specific Sun.",
        seo_title="Sun in 10th House: Career Effects & Remedies",
        seo_description="Sun in the 10th house — digbala placement for career and authority. Per-ascendant effects, timing, father signature, and honest classical remedies.",
        category="Life Questions",
        hero_image="/static/learn/sun-in-10th-house-career/hero.svg",
        read_time="12 min",
        last_updated="2026-07",
        related=("saturn-in-10th-house-career", "surya-sun-in-vedic-astrology", "sun-mahadasha"),
        faqs=(
            {
                "q": "Does Sun in the 10th house always give a government job?",
                "a": "No. Sun in the 10th is one of the classical signatures for government service, judicial roles, and public leadership, but it does not automatically produce a government job. What it produces is the capacity for visible, authority-carrying work — that capacity translates into government, medicine, family-business leadership, senior corporate roles, politics, or any career where the person is seen and recognised. Whether a specific career shows up depends on Sun's dignity (own sign, exalted, debilitated), the sign of the 10th house, aspects on Sun, and the current Dasha. A weak Sun in the 10th often produces the pattern of high visibility without stable formal position. Generate your free Janma Kundli on Shubh Bhagya to see your Sun's exact configuration.",
            },
            {
                "q": "What if Sun in the 10th house is combust or debilitated?",
                "a": "Both configurations flip the natural authority pattern. Debilitated Sun in the 10th means Sun in Libra (Capricorn ascendant) — the capable person who cannot get promoted, authority that feels borrowed. However, Neecha Bhanga cancellation rules apply here and often cancel the debilitation, producing late-career elevation. A combust planet in the 10th (usually Mercury or Venus close to Sun) tends to burn the significations of that planet in career — Mercury combust here can indicate analytical skill that is never quite credited; Venus combust can dim creative or partnership recognition. Sun himself is not combust, but he can burn the 10th lord if that lord is close to him. In every case, the placement is workable — Neecha Bhanga, transit windows, and consciously choosing careers aligned to the actual configuration all shift the outcome.",
            },
            {
                "q": "Which ascendants benefit most from Sun in the 10th?",
                "a": "The three strongest configurations are: Cancer ascendant with Sun exalted in Aries in the 10th (Sun is also 2nd lord — an outstanding placement combining digbala, exaltation, and 2nd-lord elevation); Scorpio ascendant with Sun in his own sign Leo in the 10th (Sun in own sign with digbala — the classical kingly configuration for direct authority); and Aries ascendant with Sun in Capricorn in the 10th (Sun as 5th lord in the 10th — a classical Rajya Yoga configuration where career elevation comes through disciplined institutional work). Leo ascendant is also strong because Sun as lagnesh in the 10th produces the self-made public figure pattern, though Sun is not literally in Leo (Leo's 10th is Taurus).",
            },
            {
                "q": "How does Sun in the 10th house affect the father?",
                "a": "Sun is the karaka of the father (Pitru Karaka), so his placement in the 10th house always says something about the father's role. A strong Sun in the 10th usually indicates a father who was successful, respected, and a formative model of authority — often the person inherits the father's field or reacts against it. A weak or afflicted Sun in the 10th often indicates a father present but not fully authoritative, or an authority figure whose power was complicated in some way. Sun-Saturn conjunction in the 10th (Surya-Shani yoga) is classically difficult — father-child career competition or the father's shadow feels heavy across achievements. Sun-Rahu in the 10th often indicates a father who was foreign, unconventional, or unusually influential in unorthodox ways. None of these are fixed; consciously working through the father-Sun signature often shifts the pattern significantly.",
            },
            {
                "q": "What is the best career path with Sun in the 10th house?",
                "a": "Careers where visibility, authority, and personal recognition are structural to the work itself. Strongest fits: government service, judiciary, medicine (especially senior specialities), family business at the head, senior corporate leadership, politics, defense, and any career where the person is expected to be the public face. When Sun is dignified, careers requiring you to be seen suit the placement best — the Sun does not thrive in anonymous back-office work. When Sun is weak, the same field categories can still work but the person often does better in institutional roles where authority attaches to the position rather than the personality. The through-line: Sun in the 10th wants an audience. What varies with dignity is whether the audience arrives easily or has to be earned through slow institutional respect.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Sun in 10th = digbala (directional strength) — one of the STRONGEST career placements\n'
            '• Natural authority pattern: early recognition, visible positions, magnetic quality, respected reputation\n'
            '• Best-fit careers: government, judiciary, medicine (senior), family business at head, senior corporate, politics\n'
            '• Debilitated in Libra (Capricorn ascendant): borrowed-authority pattern; check Neechabhanga\n'
            '• Combust 10th lord (close to Sun): person does the work but credit goes elsewhere\n'
            '• Sun Mahadasha (6 years) peak-activates the placement — often career high-point\n'
            '• Father karaka: usually a strong father-figure OR complicated father-authority theme\n'
            '• Sun-Saturn conjunction: father-child career competition pattern'
        ),
    ),
    Article(
        slug="foreign-career-yoga-kundli",
        title="Foreign Career Yoga: When Your Kundali Points Abroad",
        summary="Vedic astrology has specific classical signatures for a foreign life — but \"foreign\" is not one thing. The 4th (home), 7th (foreign travel), 9th (long journeys), and 12th (foreign residence) houses each read differently. Rahu is the karaka of foreign matters; his placement in the 12th, 9th, or 7th, combined with 12th lord condition and Moon involvement, produces the strongest foreign-life yogas. This guide covers the classical distinctions, primary indicators, uprooting signatures, Dasha activation windows, migration types, and the honest limits on what any chart can say about a specific visa outcome.",
        seo_title="Foreign Career Yoga: Kundli Signs You Will Go Abroad",
        seo_description="Vedic foreign-life yogas — Rahu in 12th, 12th lord placements, Moon signatures. Migration types, Dasha timing, and honest limits on visa prediction.",
        category="Life Questions",
        hero_image="/static/learn/foreign-career-yoga-kundli/hero.svg",
        read_time="12 min",
        last_updated="2026-07",
        related=("rahu-in-vedic-astrology", "rahu-mahadasha-career-problems", "vimshottari-dasha-explained"),
        faqs=(
            {
                "q": "Which house indicates foreign settlement in Vedic astrology?",
                "a": "Primarily the 12th house (Vyaya Bhava) — classical texts explicitly name it as governing \"foreign residence and long journeys abroad.\" But foreign life is not one thing: the 4th house governs the home you leave; the 9th house governs long-distance journeys and higher study abroad; the 7th house governs foreign travel and trade plus marriage-based migration; the 12th house governs long-term foreign residence. Reading foreign potential requires looking at how these four houses interact with Rahu (the karaka of foreign matters) and the person's career houses. A chart with a strong 9th but weak 12th often produces a person who studies or works abroad for a few years and returns; a strong 12th with weak 4th often produces long-term settlement.",
            },
            {
                "q": "What is the strongest yoga for going abroad?",
                "a": "Classical Vedic tradition considers several combinations especially strong. The single most cited: Rahu in the 12th house, which classical rule directly states \"= foreign residence, gains from unusual expenditure abroad.\" Second: a parivartana (mutual exchange) between the 12th lord and the 9th lord — the two foreign-related houses exchanging rulers is one of the strongest foreign-settlement signatures. Third: the 4th lord placed in the 12th house — the ruler of home literally sits in the house of foreign residence. Fourth: Moon in the 12th aspected by Rahu, which orients the mind toward \"elsewhere\" and amplifies through Rahu's ambition. When two or more of these appear together, the foreign signature is significantly strong.",
            },
            {
                "q": "Does Rahu in 12th house mean I will settle abroad?",
                "a": "Rahu in the 12th house is one of the strongest foreign-life indicators — but it does not automatically mean permanent settlement. It means the karmic terrain leans toward foreign involvement, which can express as permanent migration, a decade abroad followed by return, repeated long-duration travel, or a career built around foreign clients from within India. The specific expression depends on the rest of the chart — especially the 4th house (attachment to home), the 10th lord's placement (whether career itself is location-tied), Moon's involvement (emotional connection to place), and the current Dasha. Rahu-12 combined with 4th house affliction typically produces permanent settlement. Rahu-12 with a well-placed 4th often produces long-term travel with home-country attachment intact.",
            },
            {
                "q": "When will I go abroad as per Kundali?",
                "a": "The classical activation windows: Rahu Mahadasha (18 years) is the primary foreign-triggering period — most people with foreign yogas activate them during Rahu Mahadasha or its important Antardashas. The Mahadasha or Antardasha of the 12th lord (whichever planet rules your 12th house) frequently triggers foreign events. Saturn Mahadasha activates whichever house Saturn sits in — Saturn in the 12th often produces the long-tenure NRI-professional pattern. Ketu Mahadasha can produce foreign travel motivated by spiritual seeking or unexpected relocation. Transit triggers include Jupiter transiting the 12th/9th/7th and Rahu-Ketu transiting the 4th-10th axis. Migration is most likely when a favourable Dasha and a supportive transit land on your foreign signature together.",
            },
            {
                "q": "Can Kundali predict visa approval?",
                "a": "No — this is one of the most important honest limits. What the Kundali shows is whether your natal chart carries a foreign-life signature strong enough to matter, which type of foreign life the signature favours, and which Dasha windows classically activate the yoga. It cannot predict specific visa outcomes — the immigration system is governed by policy, timing, administrative variables, and case-specific factors that no astrological reading accesses. Astrologers who guarantee visa approval or promise a specific country result from a single chart reading are overreaching what classical Vedic tradition actually supports. Foreign-yoga scams are common in this space — be careful with anyone selling certainty on visa outcomes specifically.",
            },
            {
                "q": "Which type of foreign work does my chart show?",
                "a": "Different yoga combinations point to different types of migration. Rahu + Mercury connection (10th or 3rd house) — technology-driven professional migration (the classical Indian-IT-abroad pattern). Rahu + Sun in 10th/9th/12th — government service abroad, diplomatic assignments, international institutions. Jupiter + 9th house strong (with 12th lord involvement) — academic migration for higher studies. Venus + Rahu in the 7th or 12th — marriage-based migration or foreign spouse. Saturn well-supported in the 12th — long-duration professional migration (25-year NRI pattern). Moon in water sign + Rahu-12 — maritime, hospitality, or travel-industry careers abroad. 4th lord in 12th + strong 11th house — the classic remittance-sending NRI professional pattern.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 'Foreign' reads differently per house: 4th (home you leave), 7th (foreign trade/marriage), 9th (long journeys/study abroad), 12th (foreign residence)\n"
            '• Primary indicator: Rahu placement — 12th (settlement), 9th (higher study), 7th (marriage/trade), 10th (foreign career)\n'
            '• 12th-lord + 9th-lord parivartana (mutual exchange) = strong foreign-life signature\n'
            '• 4th lord in 12th = uprooting from home country\n'
            '• Moon in water sign + Rahu = literal crossing-water migration\n'
            '• Timing: Rahu Mahadasha is the classical foreign-trigger; 12th-lord Dasha; Saturn in 12 activates long-tenure NRI pattern\n'
            '• Migration types: Rahu+Mercury (IT), Rahu+Sun (govt), Jupiter+9th (academic), Venus+Rahu (marriage)\n'
            '• Kundli CANNOT predict visa outcomes — that is administrative, not karmic'
        ),
    ),
    Article(
        slug="marriage-mahadasha-timing",
        title="Marriage Timing by Mahadasha — Which Vimshottari Dasha Windows Trigger Weddings",
        summary="Vimshottari Mahadashas do not fire marriage evenly across life. The classical marriage-trigger periods are Venus Mahadasha (20y, strongest for male charts), Jupiter Mahadasha (16y, especially for female charts), the 7th lord's own Mahadasha, and — with caveats — Rahu Mahadasha for unconventional marriage. Within any Mahadasha, Venus-Jupiter and Jupiter-Venus Antardashas are the classical wedding sub-periods. This guide walks each Mahadasha's marriage character, Antardasha refinements, and transit triggers that co-activate.",
        seo_title="Marriage Timing by Mahadasha: Venus, Jupiter, Rahu Windows",
        seo_description="Vimshottari Mahadasha marriage timing — Venus (20y), Jupiter (16y female), Rahu (unconventional), Saturn (delay). Antardasha and transit convergence rules.",
        category="Life Questions",
        hero_image="/static/learn/marriage-mahadasha-timing/hero.svg",
        read_time="12 min",
        last_updated="2026-07",
        related=("marriage-timing-kundli", "vimshottari-dasha-explained", "shukra-venus-in-vedic-astrology"),
        faqs=(
            {
                "q": "Does Venus Mahadasha always bring marriage?",
                "a": "No — but it is the strongest classical marriage-trigger period for male charts (Venus is the karaka of marriage for men). Venus Mahadasha runs 20 years (longest of the nine Vimshottari periods). If it starts in your 20s and you are unmarried, marriage is astrologically strongly indicated within the first 5-7 years. But Venus Mahadasha does NOT guarantee marriage — the 7th house condition must also be workable, Venus itself must not be debilitated (Virgo) or combust (close to Sun), and the person must be in a life situation where marriage is possible. Venus Mahadasha starting later in life (30s+, already married) more commonly expresses as marital harmony, artistic success, or financial prosperity.",
            },
            {
                "q": "Can marriage happen in Saturn Mahadasha?",
                "a": "Yes, but usually with delay and in the second half of the 19-year Mahadasha. Saturn is the classical planet of delay, discipline, and long structural building. Marriage during Saturn Mahadasha most often happens in the Antardashas of benefic sub-lords — Saturn-Venus and Saturn-Jupiter especially — or after the Mahadasha has been running for several years. Saturn-Mahadasha marriages tend toward mature, longer-tenure partnerships; older partner, marriages that survive external hardship, delay-driven stability. These marriages often prove more durable long-term than sudden-Venus-Mahadasha romances. If you are in Saturn Mahadasha and unmarried, do not panic — the window has not necessarily closed; check upcoming Antardashas.",
            },
            {
                "q": "Which Antardasha is best for marriage?",
                "a": "The classical wedding-Antardasha combinations are Venus-Jupiter and Jupiter-Venus — these two combine both marriage karakas (Venus for love/marriage and Jupiter for dharmic partnership) and are considered the strongest sub-period marriage triggers regardless of the outer Mahadasha lord. Also strong: any Antardasha of the 7th lord (within any Mahadasha activates marriage themes directly), and Antardashas of planets sitting in the 7th house of your natal chart. Moon Antardashas often trigger the meeting-the-future-partner phase even if not the wedding itself. The strongest overall timing convergence: a marriage-karaka Mahadasha (Venus or Jupiter) running WHILE a marriage-karaka or 7th-lord Antardasha is active AND a favourable Jupiter transit lands on the natal 7th.",
            },
            {
                "q": "Why did marriage happen in Jupiter Mahadasha for many women?",
                "a": "Because Jupiter is the classical karaka of husband in a female chart. Jupiter's dashas (Mahadasha or Antardasha) in a woman's chart directly activate the marriage-partner theme. Many female charts show marriage arriving within the first 5-6 years of Jupiter Mahadasha's 16-year period. The mother-in-law generation used to say 'as soon as Guru dasha starts, look for a boy' — a folk read that matches the technical Vedic reading. Jupiter Mahadasha in a MALE chart triggers marriage less directly (Venus is the male chart karaka), but often coincides with meeting-the-future-wife, engagement formation, or first serious long-term partnership even if the wedding happens later.",
            },
            {
                "q": "What if 7th lord Dasha runs but no marriage?",
                "a": "Several classical explanations. First, if your 7th lord is natally placed in a dusthana (6th, 8th, or 12th house), the Dasha still activates 7th-house themes but often expresses as conflict, delay, or hidden partnership rather than a visible wedding. Second, if 7th lord is combust (close to the Sun) or debilitated, the Dasha's marriage-triggering power is significantly reduced. Third, malefic transits during the Antardasha — Saturn or Rahu transiting the 7th house — can suppress marriage even when the Dasha would otherwise fire it. Fourth and most important: astrology does not force marriage on someone who is not ready or in circumstances that make marriage impossible. The window opens; whether you walk through it is your choice.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• Venus Mahadasha (20y): strongest marriage-trigger for male charts; marriage often in first 5-7y if starts in 20s-30s\n"
            "• Jupiter Mahadasha (16y): primary marriage trigger for female charts (Jupiter = husband karaka); also strong male chart secondary\n"
            "• Rahu Mahadasha (18y): unconventional/foreign/love marriages; first 2-3y (Rahu-Rahu) too confused for major decisions\n"
            "• Saturn Mahadasha (19y): delays marriage; when fires, usually in benefic Antardashas (Saturn-Venus, Saturn-Jupiter) or in the second half\n"
            "• Classical wedding-Antardashas: Venus-Jupiter and Jupiter-Venus (both marriage karakas combined) in ANY outer Mahadasha\n"
            "• Also strong: any Antardasha of the 7th lord, or Antardashas of planets sitting in the 7th natally\n"
            "• Convergence rule: marriage-karaka Mahadasha + marriage-karaka/7th-lord Antardasha + Jupiter transit over natal 7th = strongest window\n"
            "• 7th lord Dasha running WITHOUT marriage often means: 7th lord in dusthana, combust/debilitated, or malefic transit suppressing"
        ),
    ),
    Article(
        slug="love-vs-arranged-marriage-kundli",
        title="Love Marriage vs Arranged Marriage — What Your Kundli Actually Shows",
        summary="Your Kundali does not judge love marriage as better than arranged — it shows which pattern is more natural. Classical Vedic tradition names specific combinations for each: love-marriage yogas (Venus+Rahu, 5th-7th lord exchange, Rahu in 7th, Mars+Venus, Moon+Mars aspects) and arranged-marriage signatures (7th lord in kendra, Jupiter aspect on 7th, strong 4th house family involvement). Most modern Indian charts show a mix; the dominant leaning tells you which path feels effortless. This guide walks each signature set, the mixed case, and Dasha timing.",
        seo_title="Love Marriage or Arranged Marriage in Your Kundli?",
        seo_description="Vedic Kundli signatures for love vs arranged marriage — Venus+Rahu, 5th-7th lord exchange, Jupiter aspect, mixed case, Dasha timing, honest framing.",
        category="Life Questions",
        hero_image="/static/learn/love-vs-arranged-marriage-kundli/hero.svg",
        read_time="11 min",
        last_updated="2026-07",
        related=("marriage-timing-kundli", "kundali-matching-ashtakoot-guna-milan", "rahu-in-vedic-astrology"),
        faqs=(
            {
                "q": "Which yoga indicates love marriage in Kundli?",
                "a": "Several classical combinations. The most cited: Venus + Rahu conjunction or mutual aspect (breaks the marriage decision out of conventional channels); 5th lord and 7th lord exchange (parivartana) or conjunction (romance leads to marriage); 5th lord in 7th house or 7th lord in 5th house (mutual reinforcement of romance-to-marriage); Rahu in 7th house independently (unconventional partner choice); Mars + Venus conjunction (passionate connection that becomes marriage); Moon + Mars mutual aspect (emotional-physical connection formed before family involvement). When 2-3 of these fire together, love-marriage is astrologically leaning. When none fire, arranged is more natural.",
            },
            {
                "q": "Can Kundli predict inter-caste marriage?",
                "a": "It can indicate the LEANING toward cross-community marriage, not predict a specific outcome. The classical inter-caste indicators: Rahu in 7th house (primary signature — 'the outsider' partner), Venus with Rahu (unconventional partner choice), 7th lord in 12th house (foreign spouse or leaving community for marriage), 8th lord in 7th house (transformative or hidden marriage), Rahu-Ketu axis on 4th-10th (restructuring of home and public identity through partner). None of these mandate inter-caste marriage — they show the karmic terrain is open to it. Person still chooses within that terrain. Chart cannot predict the specific caste, religion, or community of the partner.",
            },
            {
                "q": "What if my chart shows both love and arranged marriage yoga?",
                "a": "This is the most common configuration in modern Indian charts — and it is not chart confusion; it is chart accuracy. Modern Indian marriages often blend the two: love-cum-arranged (parents introduce, but couple chooses), arranged-that-becomes-deeply-romantic, or love-marriage-with-family-blessing. When both sets are present at similar strength, look at your current Vimshottari Dasha to see which set is more likely to activate in the marriage window. Rahu Mahadasha typically activates the love-marriage side; Jupiter Mahadasha activates the arranged-marriage side. If neither is running, the CURRENT Antardasha within your Mahadasha usually tips the balance.",
            },
            {
                "q": "Is love marriage bad or good as per Vedic astrology?",
                "a": "Neither. This is one of the most important honest framings. Classical Vedic tradition does not moralize about love vs arranged marriage. Both patterns have been present in Indian family life for millennia, both are named as legitimate marriage yogas, and both produce equally happy — and equally difficult — marriages. What the chart genuinely reads is which mode feels more natural for THIS person's karmic terrain. A chart leaning love-marriage that goes into arranged marriage often reports never fully settling; a chart leaning arranged-marriage that goes into love-marriage without family involvement often lacks the community-support network the marriage needed. Honour the leaning where possible.",
            },
            {
                "q": "Does Rahu in 7th house mean love marriage?",
                "a": "Rahu in 7th house is one of the strongest love-marriage / unconventional-marriage signatures — but it does not guarantee love-marriage specifically. It indicates the marriage will not fit the fully conventional arranged-community pattern. That can express as: love-marriage (romance before family involvement), inter-caste marriage (partner from outside your community), foreign spouse (partner from another country), late marriage to an unusual person, or arranged marriage that turns out to be with a partner very different from what the family originally imagined. Multiple flavours; the specific expression depends on Rahu's sign, aspects, and the 7th lord's placement.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• Chart shows LEANING (love vs arranged), not verdict — neither is 'better'\n"
            "• Love-marriage yogas: Venus+Rahu conjunction/aspect, 5th lord+7th lord exchange or conjunction, 5th lord in 7th (or reverse), Rahu in 7th, Mars+Venus conjunction, Moon+Mars mutual aspect\n"
            "• Arranged-marriage signatures: 7th lord in kendra with benefic influence, Jupiter aspect on 7th, strong 4th house (mother's role), 9th lord influence on 7th, 7th lord in 2nd (family arrangement)\n"
            "• Inter-caste marriage indicators: Rahu in 7th (primary), Venus+Rahu, 7th lord in 12th (foreign), 8th lord in 7th\n"
            "• Mixed case (most common in modern India): love-cum-arranged pattern; check current Dasha to see which set activates\n"
            "• Timing: Rahu Mahadasha activates love side; Jupiter Mahadasha activates arranged side; Venus is neutral"
        ),
    ),
    Article(
        slug="marriage-timing-kundli",
        title="When Will I Get Married? Reading Marriage Timing in Your Kundli",
        summary="Your Kundali shows a marriage timing WINDOW, not a specific date. Classical Vedic tradition reads timing through four primary signals: the 7th house condition, the 7th lord's placement, Venus (male chart) or Jupiter (female chart) as karakas, and the current Vimshottari Dasha. When multiple signals converge — a marriage-karaka Mahadasha runs, the 7th lord's Antardasha activates, Jupiter transits over natal 7th — the classical marriage window is at peak. This guide walks each signal, the Dasha triggers, transit refinements, and honest limits on what any chart can say about the specific month.",
        seo_title="When Will I Get Married? Kundli Marriage Timing Guide",
        seo_description="Marriage timing in your Kundli — 4 primary signals, Vimshottari Dasha triggers (Venus, Jupiter, 7th lord), Antardasha refinement, transit windows, honest limits.",
        category="Life Questions",
        hero_image="/static/learn/marriage-timing-kundli/hero.svg",
        read_time="11 min",
        last_updated="2026-07",
        related=("marriage-delayed", "shukra-venus-in-vedic-astrology", "vimshottari-dasha-explained"),
        faqs=(
            {
                "q": "Which house shows marriage in Kundali?",
                "a": "Primarily the 7th house (Yuvati Bhava — the young companion), which classical Vedic tradition names as the house of spouse, marriage, and public partnerships. But the 7th house is not read in isolation — the 7th LORD's placement (wherever the ruler of your 7th sign sits) often matters more than what sits in the 7th. Supporting houses include the 2nd (family/wealth via marriage), 5th (romance leading to marriage), 8th (in-laws and hidden marriage themes), 11th (gains through marriage), and 12th (foreign spouse or married-away pattern). The D-9 Navamsha chart is the primary reference chart for marriage-specific questions, often more decisive than the D-1 rasi chart.",
            },
            {
                "q": "Which planet is responsible for marriage?",
                "a": "Classical Vedic tradition uses two primary karakas (significators). For a male chart, Venus is the karaka of marriage — Venus's condition, dignity, and Dasha timing heavily shape male marriage patterns. For a female chart, Jupiter is the karaka of husband — Jupiter's condition and Jupiter Mahadasha frequently trigger female marriage. Both charts also read the 7th lord as a secondary marriage significator regardless of gender. The Moon is a tertiary marriage-activator because marriage is a mental commitment. When Venus (male) or Jupiter (female) Mahadasha runs AND the 7th lord's Antardasha activates AND a favourable Jupiter transit lands on the natal 7th, the classical marriage window is at peak.",
            },
            {
                "q": "Can Kundali predict exact marriage date?",
                "a": "No — this is one of the most important honest limits in Vedic astrology. What the chart offers is a timing WINDOW that narrows to years, and sometimes to 12-18 month ranges when multiple signals converge. The chart cannot narrow to a specific month or day because marriage is a life event requiring two people, two families, external circumstance, individual readiness, and often career/visa/health timing that no astrological reading accesses. Astrologers who promise a specific month or year are usually reading a single indicator without checking convergence — a common shortcut that produces confident-sounding but frequently wrong predictions. A legitimate reading names the window, lists the converging factors, and stops there.",
            },
            {
                "q": "What is Venus Mahadasha and does it always bring marriage?",
                "a": "Venus Mahadasha is a 20-year Vimshottari period (the longest of the nine) ruled by Venus — the classical marriage karaka for male charts and the karaka of romance/luxury/relationships for all. Venus Mahadasha very often triggers marriage, particularly in the first 5-7 years of the period, IF the 7th house is not heavily afflicted and if Venus itself is not debilitated (Virgo) or combust. Venus Mahadasha does NOT always bring marriage — it can also express as artistic success, financial abundance, foreign travel, or partnership formation without wedding. What determines the specific expression is Venus's own placement in your chart plus the current Antardasha within the Mahadasha. Venus Mahadasha starting in your 20s often coincides with marriage; starting in your 40s+ more commonly expresses as second-half-of-life prosperity or partnership.",
            },
            {
                "q": "Why do some people marry early and others late?",
                "a": "Chart signature difference. Early-marriage charts (before 25) typically show: 7th lord in a kendra (1/4/7/10) with benefic influence, strong Venus/Jupiter as karakas, first marriage-favourable Vimshottari Mahadasha lord activating in the early 20s, no Saturn or Rahu affliction to the 7th house. Late-marriage charts (after 32) typically show: Saturn or Rahu in the 7th (delay pattern), 7th lord in a dusthana (6/8/12), Venus (male) or Jupiter (female) afflicted or debilitated, first marriage-favourable Mahadasha not arriving until mid-30s. Neither is 'better' — they are different karmic terrains. Late marriages often prove more stable when Saturn-driven; early marriages often benefit from Venus-driven ease. The chart shows the terrain; the walking through it is still yours.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• Marriage timing = a WINDOW (year or 12-18 months when signals converge), NEVER a specific date\n"
            "• 4 primary indicators: 7th house condition, 7th lord placement, Venus (male) or Jupiter (female) karaka, current Vimshottari Mahadasha\n"
            "• Classical Dasha triggers: Venus Mahadasha (20y, strongest for male charts), Jupiter Mahadasha (16y, esp. female), 7th lord Mahadasha, Moon Mahadasha (secondary)\n"
            "• Wedding-Antardasha combinations: Venus-Jupiter and Jupiter-Venus\n"
            "• Transit triggers: Jupiter over natal 7th (12mo window), Saturn over 7th (delay-then-mature), Rahu-Ketu axis on 1st-7th (major restructuring)\n"
            "• Convergence rule: Dasha + Antardasha + transit lining up = astrologically strongest window\n"
            "• 'You'll marry at 27' predictions usually ignore Dasha convergence and actual circumstance — treat with scepticism"
        ),
    ),
    Article(
        slug="job-or-business-kundli-guide",
        title="Job or Business? What Your Kundali Actually Says (Vyapar Yoga Guide)",
        summary="Your Kundali does not give a yes-or-no answer on job vs business — it gives a leaning through a 5-signal checklist. Classical Vedic tradition names Vyapar Yogas (business combinations) and Naukri indicators (employment combinations); most charts show both with one dominant. This guide walks the checklist, the classical yogas on each side, the mixed case with tiebreakers, and the Dasha windows that classically support switching direction.",
        seo_title="Job or Business Kundli Guide: Vyapar Yoga Signals",
        seo_description="Should you do a job or business? A 5-signal Kundali checklist — Vyapar Yogas, Naukri indicators, mixed-case tiebreakers, and Dasha timing for a career switch.",
        category="Life Questions",
        hero_image="/static/learn/job-or-business-kundli-guide/hero.svg",
        read_time="12 min",
        last_updated="2026-07",
        related=("career-not-progressing", "sun-in-10th-house-career", "vimshottari-dasha-explained"),
        faqs=(
            {
                "q": "Which house indicates business in Kundali?",
                "a": "No single house — business is read through a combination of the 10th house (career), 3rd house (own effort and initiative), 7th house (partnerships and public dealings), 11th house (gains), and 2nd house (accumulated wealth). Classical Vedic tradition specifically flags the 10th lord's placement in the 3rd or 11th house as a strong self-employment signature. Rahu's involvement in any of these houses — especially in the 10th or 11th — often marks the unconventional-business pattern (startups, technology, foreign trade, novel categories). A single signal in isolation is not decisive; what matters is the balance across the 5-signal checklist covered in the article.",
            },
            {
                "q": "Which planet is strongest for business?",
                "a": "Classically, Mercury is the primary karaka (significator) of business and trade. When Mercury is strong — in his own signs Gemini or Virgo, in a kendra (1st, 4th, 7th, or 10th house), or forming Bhadra Yoga (Mercury in Gemini or Virgo in a kendra) — the person often builds analytical, systematic, communication-driven businesses. Mars is the secondary business karaka for physical enterprise and independent initiative — real estate, construction, physical trades, competitive high-energy businesses. Rahu is the modern business karaka for unconventional paths — startups, technology, foreign trade, and novel categories that did not exist a generation ago. Well-placed Mercury, Mars, and Rahu together is one of the strongest possible business charts.",
            },
            {
                "q": "Can Kundali tell if I will succeed in business?",
                "a": "The Kundali shows whether your natal pattern leans toward business, which business fields fit your specific configuration, and which Dasha windows favour launching or expanding. It cannot predict specific commercial outcomes — no chart forecasts your exit valuation, your co-founders, or your customer acquisition cost. What classical Vedic tradition offers on the success question is: (1) is the chart's overall business signature strong or weak; (2) is the current Mahadasha supportive of business; (3) are the wealth yogas (Dhana Yogas — connections between the 2nd, 5th, 9th, and 11th houses) also strong. A strong business signature without strong Dhana Yogas often produces a busy business that does not compound wealth; a strong business signature WITH strong Dhana Yogas often produces sustained commercial success.",
            },
            {
                "q": "What if my Kundali shows both job and business yoga?",
                "a": "This is the most common configuration — most charts show signals on both sides with one leaning dominant. The classical tiebreakers: (1) which side has more dignified planets? (2) which side is the current Dasha activating? (3) which mode is more sustainable under your actual life circumstances — astrology cannot see your bank balance or family responsibilities. The common healthy pattern for mixed charts is employment first, business later — many charts with mixed signals reward a person who spends the first career phase learning inside an institution (employment karma), then transitions to independent work in the mid-30s or early 40s once skills, network, and capital are in place. Rahu in the 11th house and Mercury-in-10th signatures often play out exactly this way.",
            },
            {
                "q": "When is the right Dasha to start a business?",
                "a": "Mercury Mahadasha (17 years) is the classical business-favouring window — communication, trade, learning, and networks are all activated. Venus Mahadasha (20 years) favours businesses in beauty, art, luxury, hospitality, and any partnership-based venture. Jupiter Mahadasha (16 years) favours advisory-oriented businesses — consulting, teaching, publishing, dharmic institutions. Rahu Mahadasha (18 years) can produce spectacular business success OR spectacular failure — the first two years (Rahu-Rahu Antardasha) are peak-confusion and NOT the window to make major moves; wait for Rahu-Jupiter or Rahu-Mercury Antardashas within the Mahadasha. Sun Mahadasha and Saturn Mahadasha are traditionally less favourable for launching new businesses (though they can support scaling existing ones).",
            },
            {
                "q": "What is Bhadra Yoga and how does it help business?",
                "a": "Bhadra Yoga is one of the five Panch Mahapurush yogas — the Mercury version. It forms when Mercury sits in his own signs Gemini or Virgo AND is in a kendra (1st, 4th, 7th, or 10th house) from the Lagna. Classical texts describe the Bhadra Yoga native as characterised by \"learning, eloquence, systematic mind, business\" — often producing successful traders, analytical entrepreneurs, financial-services professionals, and business owners in communication-heavy fields (publishing, media, editorial, technology). Bhadra Yoga in the 10th specifically is one of the strongest possible chart signatures for career-through-business. Generate your free Janma Kundli on Shubh Bhagya to check whether your Mercury is placed to form Bhadra Yoga.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 5-signal checklist: 10th house strength, 10th lord placement, 3rd house/lord, Mercury vs Mars strength, Rahu's role\n"
            '• Business-favouring signatures: strong Mercury (Bhadra Yoga), 10th lord in 3rd/11th, Rahu in 10th, 3rd lord well-placed\n'
            '• Employment-favouring signatures: strong Sun/Saturn in 10th, 10th lord in 6th, 6th lord in 10th\n'
            '• Bhadra Yoga (Mercury in kendra in own sign) = strongest classical business signature\n'
            '• Timing: Mercury/Venus/Jupiter Mahadashas favour business; Sun/Saturn favour employment\n'
            '• Common healthy pattern: employment first (learn), business later (independent — early 30s to 40s)\n'
            '• Chart shows leaning, not verdict — bank balance, family obligations, risk tolerance matter equally'
        ),
    ),
    Article(
        slug="10th-lord-in-6th-house-career",
        title="10th Lord in the 6th House: When Your Career Feels Like Constant Struggle",
        summary="The 10th lord in the 6th house — the ruler of the career house sitting in the house of enemies and service — is the classical Vedic signature for careers built through friction. It is not a doomed placement. It produces doctors, litigators, union leaders, HR heads, investigative journalists. This guide walks the core pattern, per-ascendant flavours, when it hurts and when it helps, its relationship to Vipareeta Raja Yoga, Dasha timing, and honest classical remedies.",
        seo_title="10th Lord in 6th House: Career Effects & Remedies",
        seo_description="10th lord in 6th house — the career-through-struggle placement. Per-ascendant flavours, when it hurts, best careers, dashas, honest remedies.",
        category="Life Questions",
        hero_image="/static/learn/10th-lord-in-6th-house-career/hero.svg",
        read_time="13 min",
        last_updated="2026-07",
        related=("career-not-progressing", "vimshottari-dasha-explained", "career-during-sade-sati"),
        faqs=(
            {
                "q": "Is 10th lord in the 6th house good or bad?",
                "a": "Neither by default — it is a specifically shaped placement. Classical Vedic tradition holds that the 6th is a dusthana (difficult house) but also an Upachaya (growing house), and placements here tend to be difficult in the early years and increasingly rewarding in the later years. 10th lord in the 6th produces careers built through friction — doctors, litigators, HR heads in contested industries, investigative journalists, senior civil service, debt-recovery specialists. In a career that suits the placement, it produces unusually durable success; in a career that fights the placement, it produces years of unnecessary struggle. Amplifying factors (10th lord exalted or in own sign, Jupiter's aspect) and cancelling factors (Neechabhanga if the 10th lord is debilitated) change the reading significantly. Generate your free Kundli on Shubh Bhagya to see your specific configuration.",
            },
            {
                "q": "Does 10th lord in the 6th house mean job change frequently?",
                "a": "Not exactly — the placement is more about ongoing conflict within a career than about frequent switching between careers. Frequent job change is more commonly linked to Rahu-related placements or unstable 10th lord aspects. What 10th lord in the 6th typically produces is prolonged workplace conflict inside one professional context, resource battles inside one organisation, and the sense that every promotion has been fought for rather than handed over. That said, the placement can produce a specific pattern of two-career lives — the first career built through friction, walked away from around age 35–40, and the second career (often in a related field but on the person's own terms) built more sustainably.",
            },
            {
                "q": "Which careers suit 10th lord in the 6th house?",
                "a": "Careers where opposition, service, or overcoming daily obstacles is the actual work. Strongest fits: medicine (especially demanding specialties — surgery, emergency, oncology, infectious disease), law and litigation (trial lawyers, prosecutors, defence counsel, arbitration), human resources and labour relations in industries with real conflict, public service under adversity (police, military, disaster response, tax collection, regulatory enforcement), debt recovery and insolvency practice, opposition politics and coalition-building in hostile terrain, investigative journalism and forensic accounting, and senior customer-service escalation. Careers that fight the placement: frictionless creative roles, easy-flow consulting, hospitality without operational pressure, and hype-driven fields where visible ease is part of the brand.",
            },
            {
                "q": "Can 10th lord in the 6th house give success?",
                "a": "Yes, and often significant success — but the timing is late-blooming and the arc is unusually durable. The classical pattern: slow early career (before mid-thirties) that feels disproportionately hard versus peers', gradual accumulation of the specific skill the placement builds (persistence through friction), and recognition arriving in the mid-thirties into forties for something built through years of unglamorous work. When combined with 10th lord exalted or in own sign — Saturn exalted in Libra in the 6th for Taurus ascendant, Sun exalted in Aries in the 6th for Scorpio ascendant, Mars in Sagittarius in the 6th for Cancer ascendant — the classical reading tips toward significant career success achieved through struggle rather than effortless rise. This is the practical experience of Vipareeta Raja Yoga even when the strict technical yoga is not formed.",
            },
            {
                "q": "What remedies help 10th lord in the 6th house?",
                "a": "Safe universal classical practices: weekly worship of the deity associated with your specific 10th lord (Sun → Shiva or Rama; Moon → Devi; Mars → Hanuman or Kartikeya; Mercury → Vishnu; Jupiter → Vishnu or Sri Guru; Venus → Lakshmi or Devi; Saturn → Hanuman as Shani's intercessor); consciously serving people working under difficulty around you (office cleaning staff, delivery workers, security guards — direct 6th-house karma); confronting rather than avoiding professional conflicts (avoided 6th-house conflicts compound); managing debts carefully; maintaining health discipline (regular check-ups, sleep, refusal to overwork past physical limits — the 6th is the house of illness); donating to hospitals or medical charities. Avoid: gemstone remedies for your 10th lord without a proper chart consultation, and expensive dosha-removal packages (there is no such thing as a 10th-lord-in-6th nivaran puja).",
            },
            {
                "q": "Is 10th lord in the 6th house Vipreet Raja Yoga?",
                "a": "Not strictly. Classical Vedic tradition names three Vipareeta Raja Yogas — Harsha (6th lord in the 6th), Sarala (8th lord in the 8th), and Vimala (12th lord in the 12th). Your 10th lord in the 6th is a related but distinct pattern. It does not carry the strict Vipareeta Raja classical benefit by name. However, when combined with other favourable factors (10th lord exalted in the 6th, benefic aspects especially from Jupiter, strong navamsha placement, favourable Dasha windows), the classical reading tips toward significant career success achieved through struggle rather than effortless rise — the practical experience of Vipareeta Raja without the strict technical yoga formation. Charts that combine 10th lord in the 6th with an actual Harsha Yoga (6th lord also in the 6th) tend to produce especially strong career-through-struggle results.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 10th lord in 6th (dusthana) — classical career-through-friction signature\n'
            '• Pattern: slow early career (before 35), gradual skill-through-conflict, late-blooming durable recognition\n'
            '• Best-fit careers: medicine (esp. surgery/oncology), law/litigation, HR/labour relations, police/military, tax/regulatory, debt recovery, opposition politics, investigative journalism\n'
            "• Not strict Vipareeta Raja Yoga but shares 'success-through-struggle' character\n"
            '• Amplifiers: 10th lord exalted/own-sign in 6th, benefic aspects (esp. Jupiter)\n'
            '• Fights: frictionless creative work, hospitality, hype-driven fields\n'
            '• Timing: recognition arrives mid-30s into 40s after the struggle years compound into expertise\n'
            '• Remedies: worship deity of 10th lord, service to those working under hardship, confront rather than avoid conflict'
        ),
    ),
    Article(
        slug="rahu-mahadasha-career-problems",
        title="Rahu Mahadasha and Career: The Confusion Years and How to Navigate Them",
        summary="Rahu Mahadasha is 18 years — for career, famously the ambition-without-discipline chapter. Sudden foreign or unconventional openings, fast prestige, and structural confusion. Here is what actually happens in each phase, why the confusion is Rahu's design, and what actually helps.",
        seo_title="Rahu Mahadasha Career: What to Expect & What Helps",
        seo_description="Rahu Mahadasha career problems explained — the 3 phases of 18 years, which fields Rahu favours, why confusion is structural, and honest remedies.",
        category="Life Questions",
        hero_image="/static/learn/rahu-mahadasha-career-problems/hero.svg",
        read_time="12 min",
        last_updated="2026-07",
        related=("rahu-in-vedic-astrology", "rahu-mahadasha-ketu-antardasha", "career-not-progressing"),
        faqs=(
            {
                "q": "Is Rahu Mahadasha good or bad for career?",
                "a": "Neither by default — it depends on Rahu's placement in your chart. A well-placed Rahu (in the 3rd, 6th, 10th, or 11th house, in a friendly sign, aspected by benefics) in Mahadasha often produces spectacular career growth: foreign postings, sudden promotions, unconventional prestige, technology or media success. An afflicted Rahu (combust, badly aspected by Mars or Saturn, in the 8th or 12th without support) often produces compulsive job-hopping, obsession without direction, and the classical started-three-careers-mastered-none pattern. Generate your free Janma Kundli on Shubh Bhagya to see your Rahu placement.",
            },
            {
                "q": "Should I change jobs during Rahu Mahadasha?",
                "a": "Slow down big decisions in the first year of any difficult Antardasha within the Mahadasha. Rahu creates distortion the person cannot see in real-time — what looks like a life-defining opportunity often looks very different from year seven. Rahu-Rahu (the first sub-period, about 2 years 8 months) is peak-confusion and the classical window for big moves that later feel unclear. If you must change, keep exit doors open, avoid 5-year commitments in the first 6 months, and journal the pattern so your later self has a record of what you were actually thinking.",
            },
            {
                "q": "Why do I feel confused about my career in Rahu Mahadasha?",
                "a": "The confusion is structural, not a personal weakness. Classical Vedic tradition describes Rahu as the planet of maya (illusion) and vipreet buddhi (reversed intelligence). He amplifies ambition faster than he amplifies clarity — the person often knows exactly what they want to be seen as but has no idea what they actually want to do. This is a feature of the Mahadasha, not evidence that something is wrong with you. Recognising the pattern is the first step out of it.",
            },
            {
                "q": "Which careers thrive in Rahu Mahadasha?",
                "a": "Technology and software (Rahu's home in the modern world), foreign trade and cross-border consulting, media, film, advertising, content and social platforms, aviation and shipping and telecommunications, research (especially in fringe or unconventional fields), diplomacy and immigration law, and entrepreneurship in emerging categories. Rahu tends to struggle with traditional government service inside old bureaucracies, ancestral family businesses, classical long-cycle arts and priesthood, and pure-relationship sales in conservative industries.",
            },
            {
                "q": "How long does Rahu Mahadasha last?",
                "a": "18 years — the second-longest of the nine Vimshottari Mahadashas (only Venus at 20 years is longer). The 18 years break into 9 Antardashas: Rahu (2 years 8 months 12 days), Jupiter (2 years 4 months 24 days), Saturn (2 years 10 months 6 days), Mercury (2 years 6 months 18 days), Ketu (1 year 0 months 18 days), Venus (3 years 0 months 0 days), Sun (0 years 10 months 24 days), Moon (1 year 6 months 0 days), Mars (1 year 0 months 18 days). Each sub-period has a very different flavour, so knowing which one you are in matters more than the outer Mahadasha alone.",
            },
            {
                "q": "What are the best remedies for career during Rahu Mahadasha?",
                "a": "Safe universal practices: chant the Rahu Beej mantra Om Bhraam Bhreem Bhraum Sah Rahave Namah as a slow long-term practice (classical count 18,000 total), donate black gram daal or blue cloth on Saturdays, serve outsiders and the marginalised (Rahu is the karaka of outsiders), support research or unusual knowledge, undertake a pilgrimage to a shrine you have not visited, and worship Durga (Rahu's classical ruling deity). Avoid: expensive Rahu shanti puja packages, and never wear hessonite (gomedh) without proper chart consultation. The deepest remedy is often alignment — matching your work to what Rahu's placement actually wants.",
            },
        ),
        llm_summary=(
            "Keypoints:\n"
            "• Rahu Mahadasha = 18 years of ambition-outpacing-clarity in career\n"
            "• First 2-3 years (Rahu-Rahu Antardasha) = peak-confusion window — big moves here often feel unclear later\n"
            "• Rahu FAVOURS: technology, foreign work, media, novel categories, entrepreneurship in emerging fields\n"
            "• Rahu FIGHTS: traditional government service, ancestral businesses, classical priesthood, conservative sales\n"
            "• Best sub-periods for major decisions: Rahu-Jupiter and Rahu-Mercury Antardashas\n"
            "• Safe remedies: Rahu Beej mantra (18,000 count target), Durga worship, serve outsiders/marginalized, black-daal Saturday charity\n"
            "• NEVER wear hessonite (gomedh) without full chart consultation"
        ),
    ),
    Article(
        slug="santan-prapti-children-in-kundli",
        title="Santan Prapti: 7 Chart Signals for Children Delay in Your Kundli",
        summary="Children delayed or difficulty conceiving? Classical Vedic astrology reads the question through 7 specific chart signals — 5th house and its lord, Jupiter as karaka of progeny, Saptamsa (D-7) divisional chart, current Dasha, afflictions to the 5th, dispositor patterns, and remedy patterns. Honest framing on how to combine astrology with modern fertility care.",
        seo_title="Santan Prapti: 7 Kundli Signals for Children Delay",
        seo_description="Children delayed in your kundli? 7 Vedic chart signals — 5th house, Jupiter, Saptamsa (D-7), Dasha windows — read alongside modern fertility care.",
        category="Life Questions",
        hero_image="/static/learn/santan-prapti-children-in-kundli/hero.svg",
        read_time="13 min",
        last_updated="2026-07",
        related=("guru-jupiter-in-vedic-astrology", "jupiter-remedies", "pitru-dosh", "marriage-delayed"),
        faqs=(
            {
                "q": "How do I know if my chart shows Santan Prapti delay?",
                "a": "Check three primary signals: (1) Is your 5th house lord in a dusthana (6th, 8th, 12th house)? (2) Is Jupiter — the karaka of children — weak, combust, debilitated in Capricorn, or in the 6th/8th/12th without benefic support? (3) Is the 5th house occupied by Ketu, Rahu, or Saturn without Jupiter's aspect? If two or more signals apply, classical Vedic tradition reads this as a genuine delay pattern that argues for both classical remedy AND a consultation with a fertility specialist if you have been trying for over a year. Generate your free Janma Kundli on Shubh Bhagya to check specific positions.",
            },
            {
                "q": "Does Ketu in the 5th house mean I will have no children?",
                "a": "No — this is a common online over-reading, not classical astrology. Ketu in the 5th typically indicates one of several patterns: a first-child conception that requires effort while later children (if the couple chooses) come more easily; a soul who fulfils the 5th-house karma through adoption or step-parenting; or a specific karmic detachment from conventional family formation that the person themselves resonates with. Ketu in the 5th is a signal for classical remedy (Ganesha worship is the classical Ketu remedy) and for fertility consultation if you are trying. It is not a verdict.",
            },
            {
                "q": "What is Saptamsa (D-7) and why does it matter for children?",
                "a": "The Saptamsa is a divisional chart specifically for progeny — each 30° sign is divided into 7 parts of about 4°17' each. Classical Vedic tradition holds the D-7 as the primary reference for children questions, often more decisive than the D-1 5th house alone. The D-7 reveals number of children (though classical counts were written for pre-modern families and need softening), quality of the parent-child relationship, and fertility difficulty patterns. When the D-7 Ascendant lord is in a dusthana AND the D-1 5th house is afflicted, the classical two-signal difficulty pattern argues most strongly for combining astrological remedy with medical support.",
            },
            {
                "q": "When will I conceive according to my Dasha?",
                "a": "Children in classical Vedic tradition tend to arrive during specific Vimshottari Dasha windows — most often when the Antardasha of the 5th lord, the 9th lord (dharmic progeny), or Jupiter is running. Many 'why aren't we conceiving' questions turn out to involve a Dasha whose ruling planet has no relationship to progeny themes. When that Dasha ends and a children-relevant planet takes over, the window opens. Check your Dasha panel to see which Antardasha you are in and when your next Jupiter or 5th-lord Antardasha begins.",
            },
            {
                "q": "Should I do an expensive Santan Prapti puja to fix children delay?",
                "a": "Almost never. The vendor market around fertility-related pujas is one of the most exploitative corners of modern astrology. Any priest asking for tens of thousands of rupees for a 'santan nivaran' ceremony is trading on emotional urgency, not classical tradition. Genuine classical remedies are simple and inexpensive: Santan Gopala mantra recitation, Jupiter propitiation (Thursday fasting, yellow flowers, feeding brahmins), Krishna Balgopala worship, and worship of the deity ruling your 5th lord. If a Pitru pattern is also present, honouring ancestors through Shraddha helps. None of this should cost lakhs.",
            },
            {
                "q": "Can Vedic remedies replace IVF or fertility treatment?",
                "a": "No — and any practitioner who tells you otherwise is not a classical astrologer. Classical Vedic tradition places astrology alongside, not instead of, appropriate medicine. Modern fertility diagnostics identify treatable causes (hormonal, tubal, sperm quality, ovulation timing) that no chart reading can substitute for. The couples we see with the best outcomes usually do both: they work with a good doctor AND they engage classical practices for the 5th house and Jupiter. The two lenses together produce the best results — the doctor reads biology, the chart reads karmic weather, and both matter.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 7 chart signals for children delay: weak 5th house/lord, Jupiter (progeny karaka) afflicted, Saptamsa (D-7) weak, current Dasha unfavorable, 5th lord in dusthana, Ketu in 5th (spiritual detachment), Rahu in 5th (adoption/unconventional)\n'
            '• 5th house = children in general; D-7 Saptamsa = the deep truth of progeny\n'
            '• Jupiter is the primary progeny karaka — his position + condition heavily determines the picture\n'
            '• Timing: children often arrive during Jupiter Dasha or 5th-lord Dasha or beneficial transit to 5th\n'
            '• Chart shows tendency — combine with modern fertility care; astrology does NOT replace medical evaluation\n'
            '• Safe remedies: Santan Gopal mantra, Krishna worship, help children in need, Thursday practices\n'
            '• NEVER promise a specific timeline — anxious couples need hope grounded in honest limits, not false certainty'
        ),
    ),
    Article(
        slug="chronic-health-issues-kundli",
        title="Chronic Health Issues in the Kundli: 7 Chart Signals to Check",
        summary="Recurring health issues that keep coming back? Classical Vedic astrology reads the karmic side of health through 7 chart signals — Ascendant lord (constitution), 6th house (Roga Bhava), 8th house (chronic conditions), planetary karakas and dhatu rulership, current Dasha, Sade Sati and Ashtama Shani transits, and the Kalapurusha body-region mapping. Honest framing throughout — always alongside a doctor, never instead of one.",
        seo_title="Chronic Health in the Kundli: 7 Vedic Chart Signals",
        seo_description="Recurring health issues? 7 Vedic chart signals — 6th house, 8th house, planetary karakas, Sade Sati — read alongside medical care, never instead of it.",
        category="Life Questions",
        hero_image="/static/learn/chronic-health-issues-kundli/hero.svg",
        read_time="14 min",
        last_updated="2026-07",
        related=("shani-saturn", "sade-sati", "saturn-remedies", "jupiter-remedies"),
        faqs=(
            {
                "q": "Can Vedic astrology diagnose my illness?",
                "a": "No. Vedic astrology does not diagnose disease — that is a doctor's job, and any practitioner claiming otherwise is not practicing classical tradition. What Vedic astrology can do is describe patterns: which body regions your chart flags as vulnerable, which Dasha windows historically correlate with health themes surfacing, and which classical practices support the specific afflicted karaka in your chart. Astrology reads karmic weather; medicine reads biology. Use them together, never one instead of the other. If a practitioner tells you to skip a doctor because a remedy will handle it, walk away.",
            },
            {
                "q": "Which house shows disease in Vedic astrology?",
                "a": "The 6th house (Roga Bhava) is the primary house of daily illness, infection, and immune-system function. The 8th house is the house of chronic conditions, hidden illness, and longevity. The Ascendant and its lord describe the underlying constitution. A complete health reading always considers all three together, plus the planetary karakas (Sun for vitality/bones, Moon for blood/mental, Mars for injury/inflammation, Mercury for skin/nervous system, Saturn for chronic conditions) and the current Dasha. No single house tells the whole story.",
            },
            {
                "q": "What is Ashtama Shani and how does it affect health?",
                "a": "Ashtama Shani is Saturn's roughly 2.5-year transit through the 8th sign from your natal Moon. Classical Vedic tradition holds this as one of the more health-active transit periods — the 8th being the house of chronic conditions and longevity, Saturn being the karaka of both. Ashtama Shani does not mean illness is certain. It means the period is one to invest in preventive care, sleep hygiene, and honest engagement with any nagging symptoms rather than pushing through. Combined with Sade Sati (Saturn transiting the sign before / of / after natal Moon), it forms one of the longest health-active transit windows of a life.",
            },
            {
                "q": "How does dhatu rulership work for health readings?",
                "a": "Each visible graha rules a specific body tissue in classical Vedic tradition: Sun rules bones, Moon rules blood and body fluids, Mars rules marrow (and muscles in some readings), Mercury rules skin and nervous system, Jupiter rules fat and liver, Venus rules the reproductive system, Saturn rules muscles and joints. When a planet is afflicted in your chart — combust, debilitated, in a dusthana, or heavily aspected by malefics — the tissue it rules is often the site of recurring health themes. Combine the dhatu map with the Kalapurusha body-region map (each rashi rules a body region) for the most decisive reading.",
            },
            {
                "q": "Can classical remedies really help with chronic illness?",
                "a": "Classical remedies work at the karmic-support layer, not the biological one. Practices like the Mahamrityunjaya Mantra (for general health and longevity), Dhanvantari worship (the deity of Ayurveda), Hanuman worship (Saturn's classical intercessor for chronic conditions), planet-specific mantras and fasting all support the karmic weather around a condition. They do not replace medication, surgery, or specialist care. What we see with patients who engage both: the medical treatment holds its ground more reliably, the emotional side of the illness feels less isolating, and lifestyle discipline (which the remedies embed) supports the biological outcome. Both lenses matter — use them together.",
            },
            {
                "q": "Should I wear a gemstone to fix my health?",
                "a": "Only after a proper chart consultation — never on general advice. Health-related gemstone prescriptions are the highest-risk category in gemstone remedy: yellow sapphire (Jupiter) can worsen certain metabolic patterns if Jupiter is a functional malefic for your Ascendant; blue sapphire (Saturn) can destabilise a chart quickly if worn wrongly; red coral (Mars) can amplify inflammatory patterns. Safer classical alternatives that require no chart consultation: Mahamrityunjaya Mantra (universal health mantra), Dhanvantari worship, planet-appropriate weekday practices, and — always — competent medical care. Never treat a gemstone as a substitute for a doctor's visit.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 7 chart signals: weak Lagna lord, afflicted 6th house/lord, afflicted 8th house/lord, malefics in 1st, weak Sun (vitality) or Moon (fluids), Sade Sati impact, current Rahu/Ketu Mahadasha\n'
            '• Specific illness types per planet: Sun (heart, eyes, bones), Moon (mind, fluids, chest), Mars (blood, muscle, inflammation), Mercury (nerves, skin), Jupiter (liver, obesity, diabetes), Venus (kidneys, reproductive), Saturn (chronic, joints, teeth), Rahu (mysterious/toxin-related), Ketu (undiagnosed/karmic)\n'
            '• Kundli suggests SUSCEPTIBILITY — does not diagnose disease; always consult a doctor\n'
            '• Timing: chronic conditions often flare in Sade Sati peak, Saturn/Rahu Mahadashas, or Antardasha of afflicted 6th/8th lord\n'
            '• Safe remedies: strengthen Lagna lord + Sun/Moon; genuine karmic-cleansing practices; NEVER replace medical care with astrology\n'
            "• Warning: this is heavily exploited — avoid 'cure your disease' astrologers charging large fees"
        ),
    ),
    Article(
        slug="gajakesari-yoga",
        title="Gajakesari Yoga: The Elephant-Lion Combination of Fame and Wisdom",
        summary="Gajakesari Yoga forms when Jupiter sits in a quadrant from the Moon with benefic support. Classical texts call it a key yoga for ever-lasting fame, wealth, intelligence, and character. Learn how to check for it in your chart and what it actually produces.",
        category="Yogas",
        hero_image="/static/learn/gajakesari-yoga/hero.svg",
        read_time="8 min",
        related=("panch-mahapurush-yoga", "guru-jupiter-in-vedic-astrology", "chandra-moon-in-vedic-astrology"),
        faqs=(
            {
                "q": "How do I know if I have Gajakesari Yoga in my chart?",
                "a": "Check three things: (1) Is Jupiter in a quadrant from your Moon (the 1st, 4th, 7th, or 10th sign counted from Moon's sign)? (2) Is Jupiter well-placed — not debilitated (Capricorn), not combust (within 11° of Sun), not in enemy signs like Gemini or Virgo? (3) Is another benefic (Mercury, Venus, or waxing Moon) aspecting or conjoining Jupiter? If all three yes, you have functional Gajakesari Yoga. Generate your free Janma Kundli on Shubh Bhagya to check specific positions.",
            },
            {
                "q": "What does 'Gajakesari' actually mean?",
                "a": "The name combines two Sanskrit words: gaja (elephant) and kesari (lion). Both are royal animals in Vedic imagery — the elephant for wisdom, strength, and dignity; the lion for courage, leadership, and command. The yoga carries the combined qualities of both: wise dignity paired with commanding presence.",
            },
            {
                "q": "Why doesn't everyone with Gajakesari Yoga become famous?",
                "a": "Three honest reasons: (1) Magnitude matters — a Gajakesari where Jupiter is debilitated or combust is a very different animal from one where Jupiter is exalted in Cancer in the 10th house. Both are technically Gajakesari; only one produces the classical results. (2) Dashas time the effect — the yoga tends to manifest strongly during Jupiter or Moon Mahadashas. (3) Choices matter — the yoga gives capacity for wisdom/teaching/counselling work; if the person doesn't engage those domains, potential goes unused.",
            },
            {
                "q": "What kind of fame does Gajakesari Yoga produce?",
                "a": "Not fleeting viral celebrity — that comes from other yogas. Gajakesari produces durable respect that outlasts a career, sometimes outlasts a lifetime. Teachers remembered by generations, writers whose books stay in print, community leaders whose names are invoked years after their death — these charts often show Gajakesari. The fame is character-based, not attention-based.",
            },
            {
                "q": "Can Gajakesari Yoga cancel bad yogas?",
                "a": "Strong Gajakesari with Jupiter well-placed can significantly mitigate difficult yogas like Manglik, Sade Sati's harsher phases, and even some doshas. But it doesn't fully cancel them — a person with Gajakesari + strong Manglik will still experience Manglik effects, just with more grace and better outcomes than they would without Jupiter's blessing. Vedic astrology doesn't work by simple addition/subtraction; it's a woven pattern where every yoga colours every other.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Formation: Jupiter in a kendra (1/4/7/10) from Moon (or from Lagna in some traditions)\n'
            "• 'Elephant-Lion' combination — the strength of the elephant (Jupiter/wisdom) meets the courage of the lion (Moon/mind)\n"
            '• Classical effects: fame, wealth, intelligence, favour from authorities, respected reputation\n'
            '• Requires additional conditions: Jupiter not debilitated/combust, benefic association helps\n'
            '• Search-intent note: heavily searched — real classical yoga but often oversold as guaranteed success\n'
            '• Timing: activates in Jupiter or Moon Mahadasha/Antardasha\n'
            '• Confirmation in D-9 Navamsha strengthens the effect (per classical Raja Yoga confirmation rule)'
        ),
    ),
    Article(
        slug="panch-mahapurush-yoga",
        title="Panch Mahapurush Yoga: The Five Great Person Combinations",
        summary="Panch Mahapurush Yoga is a group of five classical yogas — Ruchaka (Mars), Bhadra (Mercury), Hamsa (Jupiter), Malavya (Venus), Sasa (Saturn). Each forms when its planet sits in a quadrant from Lagna in own or exaltation sign. Each produces a distinctive type of greatness.",
        category="Yogas",
        hero_image="/static/learn/panch-mahapurush-yoga/hero.svg",
        read_time="9 min",
        related=("gajakesari-yoga", "the-9-grahas-overview", "guru-jupiter-in-vedic-astrology"),
        faqs=(
            {
                "q": "What are the five Panch Mahapurush Yogas?",
                "a": "The five are: (1) Ruchaka Yoga — Mars in kendra in Ar/Sc/Cp; (2) Bhadra Yoga — Mercury in kendra in Ge/Vi; (3) Hamsa Yoga — Jupiter in kendra in Sg/Pi/Cn; (4) Malavya Yoga — Venus in kendra in Ta/Li/Pi; (5) Sasa Yoga — Saturn in kendra in Cp/Aq/Li. 'Kendra' = 1st, 4th, 7th, or 10th house from your Ascendant (Lagna). Each yoga produces a great person dominated by that planet's tattva (fire/earth/ether/water/air).",
            },
            {
                "q": "Why only these five planets? Where are Sun and Moon?",
                "a": "The rule requires the planet in own OR exaltation sign. Sun owns only Leo; Moon owns only Cancer. The 'tarah grahas' (star planets: Mars, Mercury, Jupiter, Venus, Saturn) each own two signs plus an exaltation sign, giving them three options for forming the yoga. Sun and Moon each have only two options (own + exaltation), and are classified as luminaries not tarah grahas. Rahu and Ketu are shadow planets that don't traditionally own signs.",
            },
            {
                "q": "How do I check for Panch Mahapurush Yogas in my chart?",
                "a": "Generate your free Janma Kundli on Shubh Bhagya. Look at your Ascendant sign — the signs sitting in your 1st, 4th, 7th, and 10th houses are your kendras. Then check each of the 5 tarah grahas — is any of them sitting in one of your kendras AND in its own or exalted sign? Every 'yes' is a Mahapurush Yoga present. It's possible to have multiple — the emperor Akbar had both Malavya and Sasa in his 1st house (Libra Ascendant).",
            },
            {
                "q": "What kind of 'greatness' does each yoga produce?",
                "a": "Ruchaka (Mars) — martial leaders, entrepreneurs, athletes, surgeons; fiery courage. Bhadra (Mercury) — scholars, writers, systematic craftsmen; earthy intellect. Hamsa (Jupiter) — sages, teachers, judges, counsellors; ethereal wisdom. Malavya (Venus) — artists, musicians, luxury-industry leaders; watery beauty. Sasa (Saturn) — long-serving executives, monks, explorers; airy endurance. Each produces distinctly different lives.",
            },
            {
                "q": "Does having a Panch Mahapurush Yoga guarantee wealth or fame?",
                "a": "No. These yogas describe a specific quality of personality — not a guaranteed outcome. Whether the quality translates into worldly recognition depends on other factors: the strength of the yoga-forming planet, the dashas, the aspects, and the person's own choices. Also, the yoga's effects concentrate during the Mahadasha and Antardasha of the yoga-forming planet, not throughout life. A Ruchaka native experiences Mars-greatness most vividly during Mars Mahadasha (7 years).",
            },
            {
                "q": "Can I have more than one Panch Mahapurush Yoga?",
                "a": "Yes — and it happens more often than people think. Because the rule requires each planet in own/exaltation in a kendra, someone with multiple planets well-placed in kendras can carry two, three, or (very rarely) more of these yogas simultaneously. Akbar had Malavya and Sasa both in his first house. When multiple mahapurush yogas combine, read them as complementary aspects of a many-sided greatness, not as competing forces.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• The 5 'Great Person' yogas — each formed by one of the 5 non-luminary planets in own/exalted sign in a kendra (1/4/7/10)\n"
            '• Ruchaka (Mars): Aries/Scorpio/Capricorn in kendra — courage, leadership, victory\n'
            '• Bhadra (Mercury): Gemini/Virgo in kendra — learning, eloquence, business acumen\n'
            '• Hamsa (Jupiter): Sagittarius/Pisces/Cancer in kendra — wisdom, dharma, scholarly fame\n'
            '• Malavya (Venus): Taurus/Libra/Pisces in kendra — beauty, luxury, artistic success, marital happiness\n'
            '• Sasa (Saturn): Capricorn/Aquarius/Libra in kendra — discipline, leadership of multitudes, longevity\n'
            '• Each grants LIFELONG signature qualities of that planet — not period-bound\n'
            "• Activates fully during that planet's Mahadasha; confirmation in D-9 amplifies"
        ),
    ),
    Article(
        slug="pitru-dosh",
        title="Pitru Dosh: What It Really Means, How to Check, and Classical Remedies",
        summary="A clear, honest guide to Pitru Dosh — the classical Vedic idea that unresolved ancestral karma can show up as recurring blockages. Covers the real classical basis, the online exaggerations, and the traditional remedies including their honest limits.",
        category="Doshas",
        hero_image="/static/learn/pitru-dosh/hero.svg",
        read_time="9 min",
        related=("kaal-sarp-dosh", "manglik-dosh", "surya-sun-in-vedic-astrology"),
        faqs=(
            {
                "q": "How do I know if I have Pitru Dosh in my chart?",
                "a": "The strongest classical signal is Sun conjunct or aspected by Rahu/Ketu, especially in the 9th house (the father's house). Also check whether your 9th house lord sits in the 6th, 8th, or 12th house, or whether malefics occupy the 9th without any benefic aspect. Generate your free Janma Kundli on Shubh Bhagya to see your planetary positions. Important: having one of these combinations does NOT automatically mean catastrophic Pitru Dosh — classical assessment includes checking benefic protection (Jupiter's aspect often shields the 9th house even when malefics are present).",
            },
            {
                "q": "Is Pitru Dosh in the classical Vedic texts, or is it a modern idea?",
                "a": "Both, partially. Pitru Dosh appears in some classical compilations and is heavily emphasised in later folk Hindu practice, but it is less systematic in the core classical Vedic canon (Brihat Parashara Hora Shastra, Phaladeepika, Jataka Parijata) than Mangal Dosh or Sade Sati. What's definitely classical: Sun conjunct or aspected by Rahu/Ketu weakens the Sun's karakas (father, authority, health, ego). What's more folk than classical: the specific label 'Pitru Dosh' with elaborate remedy schedules. We treat this as respected tradition rather than pure scripture.",
            },
            {
                "q": "What are the classical remedies for Pitru Dosh?",
                "a": "The core classical remedies focus on acknowledgment and offering rather than payment: (1) Pitru Paksha shraaddha during the annual 16-day fortnight (typically September-October); (2) Tarpana (water offerings) on Amavasya days, especially Mahalaya Amavasya; (3) Feeding the poor, cows, or crows in ancestors' names; (4) Visits to Gaya, Prayag, or Haridwar for pinda-daan; (5) Family memorials or dedicating charitable work to ancestors. Any priest demanding tens of thousands for 'Pitru Dosh nivaran puja' is selling anxiety, not tradition — genuine Pitri offerings are simple.",
            },
            {
                "q": "Does Pitru Dosh mean I cannot have children or succeed?",
                "a": "No. Pitru Dosh represents difficulty, not impossibility. Many highly successful people have chart patterns that classical texts would label Pitru Dosh — they've simply worked with the pattern rather than being defeated by it. Common manifestations include difficulty having children, recurring career blockages despite genuine effort, unexplained family disputes across generations, and financial patterns of 'almost prospering' that keep collapsing. These are signals to work with, not sentences.",
            },
            {
                "q": "Does Pitru Dosh mean my ancestors are angry at me?",
                "a": "No — this is a common misreading. The classical model is karmic-mechanical, not vengeful. Ancestors don't punish; unresolved karmic patterns simply carry forward until worked through. The Pitri Paksha rituals aren't about appeasing angry spirits — they're about consciously acknowledging what was inherited, so the pattern can be understood and transformed. The genuine work is usually psychological too: understanding family patterns, having difficult conversations with living relatives, and choosing to break inherited cycles by conscious action.",
            },
            {
                "q": "When is Pitru Paksha 2026?",
                "a": "Pitru Paksha 2026 runs from Bhadrapada Purnima to Ashwina Amavasya — approximately mid-September to early October 2026 (exact dates vary by lunar calendar; check a Panchang for your specific timings). The Mahalaya Amavasya (the final day, considered the most powerful Pitri offering day of the year) is the peak. This is the traditional time for shraaddha ceremonies, tarpana, and feeding the poor in ancestors' names.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Ancestral-karma dosha — indicated by Sun-Rahu, Sun-Saturn, or 9th house afflictions\n'
            '• Effects: unresolved father-line issues, delayed progeny, career obstruction, financial instability, family peace disruption\n'
            '• Classical identification: 9th lord in dusthana (6/8/12), Sun conjunct/aspected by malefics in 9th\n'
            '• Genuine remedy = actual ancestor honoring, not fear-based puja packages\n'
            "• Safe practices: Amavasya (new moon) tarpan, feeding brahmins/needy in ancestors' names, Gaya Shraddha (once in lifetime)\n"
            '• Every chart with 9th-house affliction is NOT Pitru Dosh — check family history + Dasha context\n'
            '• Warning: this is heavily exploited by paid astrologers — be cautious of ₹5,000+ puja packages'
        ),
    ),
    Article(
        slug="hasta-nakshatra",
        title="Hasta Nakshatra: Savitar's Skilled Hand — The Healer, The Craftsman",
        summary="Hasta is the thirteenth nakshatra — Virgo 10°00'–23°20'. Ruled by the Moon with Savitar (the Sun as inspirer) as its deity, symbolised by an open palm. Hasta natives are the skilled hands of the zodiac — dexterous, healing, quietly capable.",
        category="Nakshatras",
        hero_image="/static/learn/hasta-nakshatra/hero.svg",
        read_time="8 min",
        related=("uttara-phalguni-nakshatra", "chandra-moon-in-vedic-astrology", "chitra-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Hasta nakshatra?",
                "a": "Your Moon needs to sit between 10°00' and 23°20' of Virgo in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya to see your Moon position. Hasta natives always have the Moon as their first Mahadasha (10 years), producing a distinctive mother-shaped early childhood.",
            },
            {
                "q": "Who is Savitar, the deity of Hasta?",
                "a": "Savitar is one of the oldest and most sacred deities in the Vedas — the aspect of the Sun that inspires and awakens human awareness. The Gayatri Mantra, one of the most powerful classical prayers, is addressed to Savitar. What Savitar inspires, the human being executes with their hands. This is the Hasta connection — divine inspiration delivered through the physical hand.",
            },
            {
                "q": "What careers suit Hasta natives?",
                "a": "Medicine (especially surgery, physiotherapy, dentistry, obstetrics), massage and bodywork, craft trades (carpentry, jewellery-making, tailoring, watchmaking, luthiery), culinary arts, fine arts (painting, calligraphy, sculpture, ceramics), teaching young children, astrology and palmistry (Hasta is the classical nakshatra of hand-reading), magic and illusion (sleight-of-hand is literal Hasta work). Hasta natives struggle in purely abstract intellectual roles with no physical outlet.",
            },
            {
                "q": "What is the shadow side of Hasta?",
                "a": "Perfectionism. The skill-orientation can tip into never-being-satisfied-with-the-work. Combined with Virgo's already-critical mind, Hasta natives can drive themselves and collaborators hard trying to reach a standard that keeps moving. The Moon rulership softens this — the mature Hasta learns that 'good enough, delivered with warmth' often serves people better than 'perfect, delivered late'.",
            },
            {
                "q": "Which nakshatras match well with Hasta?",
                "a": "By Ashtakoot Guna Milan: best matches are Deva-gana partners with Adi or Madhya nadi — Ashwini (Adi), Punarvasu (Adi), Pushya (Madhya — often cited as classical strong Hasta partner), Anuradha (Madhya). Same-Antya-nadi partners (Krittika, Rohini, Ashlesha, Magha, Swati, Uttara Ashadha, Shravana, Revati) lose 8 Nadi Kuta points.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 13th of 27. Span: Virgo 10°-23°20'. Lord: Moon\n"
            '• Symbol: hand. Deity: Savitar (sun as inspirer, giver of skill)\n'
            '• Nature: skilled hand, craftsmanship, healing touch, precise work, cleverness, dexterity\n'
            '• Strong signature: craftsman, surgeon, artisan, chef, magician, healer, IT/coding\n'
            '• Shadow: manipulative cleverness, restlessness, thievery (in shadow expression), nervousness'
        ),
    ),
    Article(
        slug="chitra-nakshatra",
        title="Chitra Nakshatra: Vishvakarma's Dazzling Jewel",
        summary="Chitra is the fourteenth nakshatra — Virgo 23°20' to Libra 6°40'. Ruled by Mars with Vishvakarma (the divine architect) as its deity, symbolised by a bright pearl or gem. Chitra natives are the striking designers — beautiful, constructive, magnetic.",
        category="Nakshatras",
        hero_image="/static/learn/chitra-nakshatra/hero.svg",
        read_time="8 min",
        related=("hasta-nakshatra", "mangal-mars-in-vedic-astrology", "swati-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Chitra nakshatra?",
                "a": "Your Moon needs to sit between 23°20' Virgo and 6°40' Libra. Chitra straddles two signs — the first two padas are in Virgo (precise, service-oriented), the last two in Libra (aesthetic, relational). Generate your free Janma Kundli on Shubh Bhagya to see your Moon position. Chitra natives always have Mars as their first Mahadasha (7 years).",
            },
            {
                "q": "Who is Vishvakarma, the deity of Chitra?",
                "a": "Vishvakarma is the classical divine craftsman — the one who designed and built everything from the palaces of the gods to Indra's weapons to the golden city of Lanka. His name literally means 'the maker of all', and he holds patronage over every trade that shapes raw material into something beautiful and functional. As Chitra's deity, he gives the nakshatra its quality of seeing design possibility in whatever is present.",
            },
            {
                "q": "Why does 'chitra' mean 'picture'?",
                "a": "The Sanskrit word chitra is still used in modern Indian languages (Hindi, Marathi, Tamil, etc.) to mean 'picture', 'image', or 'painting'. This isn't accidental — the nakshatra name specifically evokes visual composition, the arrangement of elements into something the eye finds beautiful. Chitra natives usually have a strong instinct for visual arrangement, whether or not they work professionally in visual arts.",
            },
            {
                "q": "What careers suit Chitra natives?",
                "a": "Architecture and interior design (Vishvakarma's direct portfolio), fashion and jewellery design, visual arts (painting, photography, graphic design), film (especially cinematography and production design), engineering and construction, fine crafts (metalwork, ceramics, glassblowing), landscape design, cosmetics and aesthetics. Chitra natives struggle in purely administrative roles with no design element.",
            },
            {
                "q": "Which nakshatras match well with Chitra?",
                "a": "By Ashtakoot Guna Milan: best matches are Rakshasa-gana partners with Adi or Antya nadi — Vishakha (Antya — often specifically cited as classical Chitra partner, both Rakshasa with different nadi), Jyeshtha (Adi), Mula (Adi), Ashlesha (Antya). Same-Madhya-nadi partners (Bharani, Mrigashira, Pushya, Purva Phalguni, Anuradha, Purva Ashadha, Dhanishta, Uttara Bhadrapada) lose 8 Nadi Kuta points.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 14th of 27. Span: Virgo 23°20' - Libra 6°40'. Lord: Mars\n"
            '• Symbol: dazzling jewel / pearl. Deity: Vishvakarma (celestial architect)\n'
            '• Nature: dazzling beauty, artistic brilliance, structural/architectural design, striking presence\n'
            '• Strong signature: architect, designer, fashion, jewellery, engineering, film-industry visual work\n'
            '• Shadow: vanity, superficial focus on appearance, unstable emotions, drama-seeking'
        ),
    ),
    Article(
        slug="swati-nakshatra",
        title="Swati Nakshatra: The Self-Going Wind — Independence and Diplomatic Grace",
        summary="Swati is the fifteenth nakshatra — Libra 6°40'–20°00'. Ruled by Rahu with Vayu (wind) as its deity, symbolised by a young shoot swaying in the breeze. Swati natives are the independents — self-directed, diplomatic, refusing to be tied down.",
        category="Nakshatras",
        hero_image="/static/learn/swati-nakshatra/hero.svg",
        read_time="8 min",
        related=("chitra-nakshatra", "rahu-in-vedic-astrology", "vishakha-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Swati nakshatra?",
                "a": "Your Moon needs to sit between 6°40' and 20°00' of Libra in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya to see your Moon position. Swati natives always have Rahu as their first Mahadasha (18 years, the longest first-Mahadasha of any nakshatra), producing a distinctive Rahu-shaped early life — unusual family circumstances, international influences, or early independence.",
            },
            {
                "q": "Who is Vayu, the deity of Swati?",
                "a": "Vayu is one of the five great Vedic elemental deities (with Agni/fire, Varuna/water, Prithvi/earth, Akasha/space). But Vayu is distinctive: the wind cannot be held, cannot be tied down, cannot be permanently owned. It moves where it wishes, fills what needs filling, withdraws when the moment passes. This is Swati's essential quality — attachment causes suffering, and the moment something starts to own the Swati native rather than the other way around, an internal Vayu-quality rises and starts looking for the exit.",
            },
            {
                "q": "What does the 'coral' symbolism mean for Swati?",
                "a": "Some classical texts give Swati a secondary symbol: coral. Coral self-forms in the sea — it doesn't need a template, an architect, or an external framework. It builds itself into beautiful shapes according to its own inner rules. This is the deeper Swati message: independent doesn't mean rootless; it means self-directed. The Swati native, like coral, has an internal ordering principle that doesn't need external validation.",
            },
            {
                "q": "What careers suit Swati natives?",
                "a": "Diplomacy and international relations, business (especially trade, import/export, brokerage — Swati is classically strong for commerce), law (especially mediation and arbitration), consulting and advisory work, aviation and shipping (literal Vayu portfolio), freelancing, music (especially wind instruments and voice work — Vayu rules breath), journalism and translation. Swati natives struggle in rigid corporate hierarchies with no autonomy.",
            },
            {
                "q": "What is the shadow side of Swati?",
                "a": "Rootlessness. The independence quality can tip into chronic inability to commit — to relationships, careers, places, or communities. Swati natives sometimes discover in mid-life that they haven't built deep roots anywhere, and the wind that seemed liberating starts to feel lonely. Classical remedy: distinguish between healthy self-direction and reflexive avoidance of anything that might bind.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 15th of 27. Span: Libra 6°40'-20°. Lord: Rahu\n"
            '• Symbol: young shoot bending in wind / coral. Deity: Vayu (god of wind)\n'
            '• Nature: independent, self-going, diplomatic, adaptable, learning through movement, restlessness\n'
            '• Strong signature: diplomat, trader, business, mediator, independent consultant, foreign trade\n'
            '• Shadow: isolation, over-independence, indecisive, restlessness that never settles'
        ),
    ),
    Article(
        slug="magha-nakshatra",
        title="Magha Nakshatra: The Royal Throne of the Ancestors",
        summary="Magha is the tenth nakshatra — Leo 0°00'–13°20'. Ruled by Ketu with the Pitris (ancestors) as its deities, symbolised by the royal throne. Magha natives carry the classical weight and grace of inherited authority — dignified, ancestrally-carried, quietly royal.",
        category="Nakshatras",
        hero_image="/static/learn/magha-nakshatra/hero.svg",
        read_time="8 min",
        related=("ashlesha-nakshatra", "ketu-in-vedic-astrology", "purva-phalguni-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Magha nakshatra?",
                "a": "Your Moon needs to sit between 0°00' and 13°20' of Leo in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya — the planetary table shows your Janma Nakshatra. Magha natives always have Ketu as their first Mahadasha (7 years), typically producing an unusually reflective/philosophical early childhood.",
            },
            {
                "q": "Who are the Pitris, the deities of Magha?",
                "a": "The Pitris are the collective ancestors of the family lineage — especially the paternal line back three generations (father, grandfather, great-grandfather). Vedic tradition places enormous weight on the Pitri connection. The annual Pitru Paksha (ancestor fortnight) is dedicated to offerings for the ancestors. Magha natives, more than any other nakshatra, carry ancestral weight directly — their successes and struggles often trace back to the family line more clearly than for others.",
            },
            {
                "q": "Why is Ketu the ruler of a throne-symbolised nakshatra?",
                "a": "The classical paradox: Magha's symbol is the throne (worldly authority) but its ruler is Ketu (dissolving the ego, moksha). Held together this is the Vedic recognition that true authority is inherited, not earned — the throne isn't yours in any personal sense. You sit on it because those before you sat on it. Your role is to hold it well and pass it on. Many Magha lives include a mid-life humbling that opens the door to spiritual maturity.",
            },
            {
                "q": "What careers suit Magha natives?",
                "a": "Leadership and executive roles (CEO, senior government, military command), family business succession, politics and public service, traditional profession with lineage (priesthood, classical arts), historical research and genealogy, antique dealing and heritage conservation, foundation and endowment stewardship. Magha natives struggle in startup-like environments requiring rapid pivots without institutional weight.",
            },
            {
                "q": "Which nakshatras match well with Magha?",
                "a": "By Ashtakoot Guna Milan: best matches are Rakshasa-gana partners with Adi or Madhya nadi — Jyeshtha (Adi), Chitra (Madhya), Mula (Adi). Same-Antya-nadi partners (Krittika, Rohini, Ashlesha, Swati, Uttara Ashadha, Shravana, Revati) lose 8 Nadi Kuta points. Deva-gana partners create Gana-Kuta friction as Magha's intensity can overwhelm the more refined Deva types.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 10th of 27. Span: Leo 0°-13°20'. Lord: Ketu\n"
            '• Symbol: royal throne. Deity: Pitrs (the ancestors)\n'
            '• Nature: royal lineage, ancestral pride, ceremonial authority, past-life inherited status\n'
            '• Strong signature: government service, ancestor-honouring roles, royal-family adjacent, ceremonial/religious authority\n'
            '• Shadow: entitlement, ancestral karma weight, arrogance, disconnection from present-life effort'
        ),
    ),
    Article(
        slug="purva-phalguni-nakshatra",
        title="Purva Phalguni Nakshatra: Bhaga's Bed of Delight",
        summary="Purva Phalguni is the eleventh nakshatra — Leo 13°20'–26°40'. Ruled by Venus with Bhaga (delight, luxury, patron of good fortune) as its deity, symbolised by the front legs of a bed. Purva Phalguni natives are the joyful creators — magnetic, artistic, deeply present to pleasure.",
        category="Nakshatras",
        hero_image="/static/learn/purva-phalguni-nakshatra/hero.svg",
        read_time="8 min",
        related=("magha-nakshatra", "shukra-venus-in-vedic-astrology", "uttara-phalguni-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Purva Phalguni nakshatra?",
                "a": "Your Moon needs to sit between 13°20' and 26°40' of Leo. Generate your free Janma Kundli on Shubh Bhagya to see your Moon position and nakshatra. Purva Phalguni natives always have Venus as their first Mahadasha (20 years, the longest of all) — two decades of taste-and-art development shaping their early identity.",
            },
            {
                "q": "Who is Bhaga, the deity of Purva Phalguni?",
                "a": "Bhaga is one of the twelve Adityas (solar deities), the god of delight, luxury, marital happiness, and good fortune. His name is the root of the Sanskrit word 'bhagya' (fortune, destiny) — which is where Shubh Bhagya's own name comes from. Importantly: Bhaga rules the enjoyment of fortune, not the accumulation of it. A modest meal shared with joy honours Bhaga more than a lavish feast eaten grudgingly.",
            },
            {
                "q": "What does the 'front legs of a bed' symbol mean?",
                "a": "Classical texts break the bed symbol across the Phalguni pair: Purva Phalguni is the bed as a place of pleasure (where lovers meet, where creative dreams arise), while Uttara Phalguni is the same bed as a place of commitment (where marriage vows are consummated). Together they represent the classical Vedic vision of romantic love: pleasure and commitment held in a single frame.",
            },
            {
                "q": "What careers suit Purva Phalguni natives?",
                "a": "Performing arts (music, dance, theatre, cinema — Purva Phalguni is classically the strongest performance nakshatra), visual arts (painting, photography, fashion, jewellery design), hospitality (luxury hotels, fine dining, event planning), media and entertainment, wedding industry (bridal wear, wedding planning), romantic writing and poetry, sensory arts (perfumery, sommelierie, pastry). Purva Phalguni natives struggle in joyless corporate environments.",
            },
            {
                "q": "Which nakshatras match well with Purva Phalguni?",
                "a": "By Ashtakoot Guna Milan: Uttara Phalguni is often the classical strongest match — the two halves of the bed complete each other. Also good: Rohini (Antya nadi), Ardra (Adi nadi), Purva/Uttara Ashadha, Purva/Uttara Bhadrapada. Same-Madhya-nadi partners (Bharani, Mrigashira, Pushya, Chitra, Anuradha, Purva Ashadha, Dhanishta, Uttara Bhadrapada) lose 8 Nadi Kuta points.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 11th of 27. Span: Leo 13°20'-26°40'. Lord: Venus\n"
            '• Symbol: front legs of bed / hammock. Deity: Bhaga (god of delight, marriage, luck)\n'
            '• Nature: pleasure, comfort, romance, luxury, generous hospitality, creative expression\n'
            '• Strong signature: entertainment, arts, hospitality, romance/wedding industry, luxury goods, sales\n'
            '• Shadow: laziness, indulgence, superficial charm, pleasure-addicted'
        ),
    ),
    Article(
        slug="uttara-phalguni-nakshatra",
        title="Uttara Phalguni Nakshatra: Aryaman's Contract of Lasting Friendship",
        summary="Uttara Phalguni is the twelfth nakshatra — Leo 26°40' to Virgo 10°00'. Ruled by the Sun with Aryaman (patron of contracts, friendship, hospitality) as its deity, symbolised by the back legs of a bed. Uttara Phalguni natives are the reliable patrons — steadfast, generous, keepers of long promises.",
        category="Nakshatras",
        hero_image="/static/learn/uttara-phalguni-nakshatra/hero.svg",
        read_time="8 min",
        related=("purva-phalguni-nakshatra", "surya-sun-in-vedic-astrology", "hasta-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Uttara Phalguni nakshatra?",
                "a": "Your Moon needs to sit between 26°40' Leo and 10°00' Virgo. Uttara Phalguni straddles two signs — the first pada is in Leo (warm, generous), the last three padas are in Virgo (precise, service-oriented). Generate your free Janma Kundli on Shubh Bhagya to see your exact position. Uttara Phalguni natives always have the Sun as their first Mahadasha (6 years).",
            },
            {
                "q": "Who is Aryaman, the deity of Uttara Phalguni?",
                "a": "Aryaman is one of the twelve Adityas (solar deities), specifically the god of lasting bonds — sacred contracts of marriage, pledges of friendship, vows of patronage, covenants of hospitality between host and guest. Where Purva Phalguni's Bhaga governs the enjoyment of what is present, Aryaman governs the keeping of what has been promised. Classical Vedic society placed enormous weight on Aryaman's contracts.",
            },
            {
                "q": "Why is the Purva–Uttara Phalguni pairing classical?",
                "a": "The two Phalguni nakshatras complete each other's symbolism. Purva is the front legs of a bed (pleasure, where lovers meet); Uttara is the back legs (commitment, where they stay). Together they represent the Vedic vision of romantic love in a single frame. Consequently, Purva Phalguni + Uttara Phalguni pairing consistently ranks among the strongest Ashtakoot Guna Milan matches in classical literature.",
            },
            {
                "q": "What careers suit Uttara Phalguni natives?",
                "a": "Contract law (Aryaman's classical portfolio), HR and executive coaching, diplomatic and ambassadorial work, long-term project management, marriage/family therapy, nonprofit leadership, long-term-care medicine (geriatrics, family practice), family business steward roles. Uttara Phalguni natives struggle in fly-by-night startup work where reliability is treated as naive.",
            },
            {
                "q": "What is the shadow side of Uttara Phalguni?",
                "a": "Over-obligation. Because Uttara Phalguni natives take commitments so seriously, they can accumulate more than they can carry. The Aryaman quality can tip into codependence — carrying friends and family who should be carrying themselves. Classical remedy: the mature Uttara Phalguni learns to distinguish between commitments they've chosen and obligations others have assumed.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 12th of 27. Span: Leo 26°40' - Virgo 10°. Lord: Sun\n"
            '• Symbol: back legs of bed / hammock. Deity: Aryaman (god of contracts, friendship, patronage)\n'
            '• Nature: dependable partnership, contract-honouring, lasting friendship, humanitarian, patronage\n'
            '• Strong signature: law, marriage, non-profit leadership, HR/talent management, philanthropy\n'
            "• Shadow: over-committing, dependency on approval, boring reliability, judgement of others' unreliability"
        ),
    ),
    Article(
        slug="punarvasu-nakshatra",
        title="Punarvasu Nakshatra: The Return Home — Aditi's Boundless Renewal",
        summary="Punarvasu is the seventh nakshatra — Gemini 20°00' to Cancer 3°20'. Ruled by Jupiter with Aditi (mother of the gods) as its deity, symbolised by a quiver of arrows or a house. Punarvasu natives are the renewers — resilient, warm, wisdom-carrying, and always finding their way back.",
        category="Nakshatras",
        hero_image="/static/learn/punarvasu-nakshatra/hero.svg",
        read_time="8 min",
        related=("ardra-nakshatra", "guru-jupiter-in-vedic-astrology", "pushya-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Punarvasu nakshatra?",
                "a": "Your Moon needs to sit between 20°00' Gemini and 3°20' Cancer. Punarvasu spans two signs — the first three padas are in Gemini (airy communicative quality), the last pada is in Cancer (watery emotional-home). Generate your free Janma Kundli on Shubh Bhagya to see your exact Moon position. Punarvasu natives always have Jupiter as their first Mahadasha.",
            },
            {
                "q": "What does 'Punarvasu' actually mean?",
                "a": "Classical texts break it into two Sanskrit roots: punar (again) and vasu (wealth, goods, resources). Together: 'the return of the wealth'. This is unusual — most nakshatras are named after their symbol or character, but Punarvasu is named after its promise. What was lost will return. The Aditi-mothering quality carries through: whatever leaves Aditi's household eventually comes back.",
            },
            {
                "q": "What careers suit Punarvasu natives?",
                "a": "Teaching, writing, publishing (Jupiter's classical portfolio), counselling and mentoring, law (especially advisory), real estate and hospitality (the 'house' symbol taken literally), publishing and editing, travel writing and cultural bridging, restoration work (art, historical buildings, cultural revival). Punarvasu natives struggle in aggressive competitive environments where their Sattvic temperament is a liability.",
            },
            {
                "q": "What is the shadow side of Punarvasu?",
                "a": "'Over-return.' Sometimes Punarvasu natives go back to relationships, jobs, or patterns that shouldn't be revisited — attaching the recovery archetype to something that has genuinely completed its arc. The classical remedy is to honour the return-instinct but check with a trusted friend whether this particular return serves growth. Distinguishing 'coming home' from 'going back to what harmed me' is the key skill.",
            },
            {
                "q": "Which nakshatras match well with Punarvasu?",
                "a": "By Ashtakoot Guna Milan: best matches are Deva-gana partners with Madhya or Antya nadi — Pushya is often specifically cited (same gana, different nadi, complementary Jupiter–Saturn temperaments), Hasta (Antya), Anuradha (Madhya), Shravana (Antya), Revati (Antya). Same-Adi-nadi (Ashwini, Ardra, Hasta's Adi pada, Jyeshtha, Mula, Shatabhisha, Purva Bhadrapada) lose 8 Nadi Kuta points.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 7th of 27. Span: Gemini 20° - Cancer 3°20'. Lord: Jupiter\n"
            '• Symbol: quiver of arrows / house. Deity: Aditi (boundless mother, mother of the gods)\n'
            '• Nature: return home, renewal, unconditional love, teaching, moral compass, philosophical\n'
            '• Strong signature: teacher, philosopher, ethical business, mother-figure roles, hospitality/lodging\n'
            "• Shadow: over-idealism, escapism to 'home', naive trust, philosophical arrogance"
        ),
    ),
    Article(
        slug="pushya-nakshatra",
        title="Pushya Nakshatra: The Nourisher — Most Auspicious of the 27 (Except for Weddings)",
        summary="Pushya is the eighth nakshatra — Cancer 3°20' to 16°40'. Classical Vedic tradition ranks it the most auspicious nakshatra of the zodiac. Ruled by Saturn with Brihaspati (guru of the gods) as deity. Pushya natives are the quiet teachers and nourishers.",
        category="Nakshatras",
        hero_image="/static/learn/pushya-nakshatra/hero.svg",
        read_time="8 min",
        related=("punarvasu-nakshatra", "shani-saturn", "guru-jupiter-in-vedic-astrology"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Pushya nakshatra?",
                "a": "Your Moon needs to sit between 3°20' and 16°40' of Cancer in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya to see your Moon position and nakshatra. Pushya natives always have Saturn as their first Mahadasha — the longest of all Mahadashas at 19 years — which shapes their whole approach to life from childhood.",
            },
            {
                "q": "Why is Pushya called the most auspicious nakshatra?",
                "a": "The combination is unique: Saturn's discipline + Brihaspati's dharma + Deva gana refinement + Cancer's emotional depth. This collection of factors is more universally favourable than any other single nakshatra. Ancient muhurta rules use 'when the Moon is in Pushya' as the default good time for almost any auspicious activity — with one striking exception.",
            },
            {
                "q": "Why should you not marry during Pushya nakshatra?",
                "a": "This is Pushya's one classical exception. Muhurta texts explicitly exclude Pushya from wedding date suggestions. Reasons vary: some say because Pushya is Brihaspati's nakshatra and his grace prefers scholarly over romantic beginnings; others say Cancer's emotional intensity + Saturn's slowness makes for a heavy start to a marriage. Either way, muhurta calendars honour this exclusion. Every other kind of auspicious start is welcomed on Pushya days.",
            },
            {
                "q": "What careers suit Pushya nakshatra people?",
                "a": "Teaching (Brihaspati's portfolio), medicine and healthcare (nourishing/healing archetype), food and hospitality (chefs, nutritionists, dieticians), financial advising and wealth management (Saturn's discipline applied to protecting others' resources), priesthood and ritual work, agriculture and dairy (literal cow-udder symbolism), real estate, long-term project management. Pushya natives struggle in fast-moving glamour-industry work.",
            },
            {
                "q": "Which nakshatras match well with Pushya?",
                "a": "By Ashtakoot Guna Milan: Punarvasu-Pushya is a classical strong pairing (same Deva gana, different nadi, complementary Jupiter–Saturn temperaments). Also good: Ashwini (Adi nadi), Hasta (Antya), Shravana (Antya), Revati (Antya). Same-Madhya-nadi partners (Bharani, Mrigashira, Purva Phalguni, Chitra, Anuradha, Purva Ashadha, Dhanishta, Uttara Bhadrapada) lose 8 Nadi Kuta points.",
            },
            {
                "q": "What is 'Pushya Nakshatra shopping'?",
                "a": "A well-known Indian folk tradition: buying gold, silver, or long-term assets on the day the Moon transits Pushya nakshatra brings prosperity. Jewellers actively market 'Pushya Nakshatra shopping days'. Classical support: Pushya is Kshipra (swift/light) + auspicious + Saturn-ruled — all favouring the accumulation of durable wealth. Even skeptical shoppers often check the Pushya calendar for large purchases.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 8th of 27. Span: Cancer 3°20'-16°40'. Lord: Saturn\n"
            '• Symbol: udder / lotus / arrow. Deity: Brihaspati (Jupiter, guru of the gods)\n'
            '• Nature: MOST auspicious nakshatra classically — nourishment, blessings, dharmic support\n'
            '• EXCEPT: classical rule forbids weddings on Pushya days (screenshot-worthy fact)\n'
            '• Strong signature: teacher, priest, physician, counsellor, government service, family-business patriarch\n'
            '• Shadow: over-protectiveness, self-sacrifice to burnout, rigid tradition'
        ),
    ),
    Article(
        slug="ashlesha-nakshatra",
        title="Ashlesha Nakshatra: The Entwiner — Serpent Wisdom and Occult Power",
        summary="Ashlesha is the ninth nakshatra — Cancer 16°40' to 30°00'. Ruled by Mercury with the Nagas (serpent beings) as its deities, symbolised by a coiled serpent. Ashlesha natives are the mystical readers of hidden patterns — hypnotic, penetrating, capable of both healing and harm.",
        category="Nakshatras",
        hero_image="/static/learn/ashlesha-nakshatra/hero.svg",
        read_time="9 min",
        related=("pushya-nakshatra", "budha-mercury-in-vedic-astrology", "magha-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Ashlesha nakshatra?",
                "a": "Your Moon needs to sit between 16°40' and 30°00' of Cancer. Ashlesha natives always have Mercury as their first Mahadasha (17 years). Generate your free Janma Kundli on Shubh Bhagya to see your Moon position. Note: the very last portion of Ashlesha (Cancer 26°40'–30°00') is the gandanta zone — a classical 'spiritual knot' before Leo begins, considered turbulent for children born there but potent for spiritual work later.",
            },
            {
                "q": "Are Nagas evil in Vedic astrology?",
                "a": "No — this is a common Western misreading. In Vedic tradition the Nagas (serpent beings) are wisdom-carriers. Vasuki was the churning-rope in the classical churning of the ocean of milk that produced Amrita, the nectar of immortality. Shesha is the coiled bed on which Vishnu rests. Snakes in Vedic imagination are not adversaries — they are the beings who hold what is too dangerous or profound for the surface world.",
            },
            {
                "q": "What careers suit Ashlesha natives?",
                "a": "Medicine (especially toxicology, pharmacology, snake-bite research), depth psychology and psychiatry (trauma work, personality disorders), occult and tantra at professional depth, investigative work (journalism, intelligence, criminal investigation), Ayurvedic medicine and herbalism (Nagas are classical teachers of pharmacology), politics behind the scenes (Ashlesha is more effective as strategist/advisor than as public leader), research and analysis roles.",
            },
            {
                "q": "What is the shadow side of Ashlesha?",
                "a": "'Manipulation'. Because Ashlesha natives read others so well and can be so hypnotically persuasive, the shadow expression is using this capacity for personal gain rather than healing. Classical texts warn about the 'coiled serpent' quality turning inward as self-poisoning (chronic resentment, brooding, holding grudges) or outward as manipulation. The mature Ashlesha uses the serpent's gift to heal; the immature one uses it to bind.",
            },
            {
                "q": "What is the gandanta zone?",
                "a": "Gandanta means 'spiritual knot' — the classical name for the last portion of a watery sign that borders a fiery sign. Ashlesha (end of Cancer, before Leo) is one of three gandanta zones. Classical texts consider births in the very final degrees of Ashlesha (~26°40'–30°00' Cancer) turbulent — the transition-energy is intense. But the same texts also emphasise that gandanta natives who survive early difficulty develop unusual spiritual power. The serpent that swallows poison and transforms it is the exact archetype.",
            },
            {
                "q": "Which nakshatras match well with Ashlesha?",
                "a": "By Ashtakoot Guna Milan: best matches are Rakshasa-gana partners with Adi or Madhya nadi — Jyeshtha (Adi), Chitra (Madhya), Mula (Adi). Manushya-gana partners work if other kutas score high. Same-Antya-nadi partners (Krittika, Rohini, Magha, Swati, Uttara Ashadha, Shravana, Revati) lose 8 Nadi Kuta points. Deva-gana partners create Gana-Kuta friction.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 9th of 27. Span: Cancer 16°40'-30°. Lord: Mercury\n"
            '• Symbol: coiled serpent. Deity: the Nagas (serpent beings)\n'
            '• Nature: hypnotic charm, occult knowledge, kundalini/serpent wisdom, entwining, penetrating insight\n'
            '• Strong signature: mystic, occultist, psychologist, poison-antidote medicine, hypnotherapist, mystery writer\n'
            '• Shadow: manipulation, hidden motives, addiction, entangled relationships'
        ),
    ),
    Article(
        slug="rohini-nakshatra",
        title="Rohini Nakshatra: The Moon's Favourite, Nakshatra of Growth and Abundance",
        summary="Rohini is the fourth nakshatra — Taurus 10°00'–23°20'. Ruled by the Moon with Brahma the Creator as its deity, symbolised by a chariot or the banyan tree. Rohini natives are the makers — sensual, magnetic, patient builders of beauty and abundance.",
        category="Nakshatras",
        hero_image="/static/learn/rohini-nakshatra/hero.svg",
        read_time="8 min",
        related=("ashwini-nakshatra", "chandra-moon-in-vedic-astrology", "shukra-venus-in-vedic-astrology"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Rohini nakshatra?",
                "a": "Your Moon needs to sit between 10°00' and 23°20' of Taurus in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya — the planetary table shows your Janma Nakshatra under the Moon row. Rohini natives get a double blessing: Moon rules the nakshatra AND Moon is exalted in Taurus (exaltation degree is 3° Taurus).",
            },
            {
                "q": "Why is Rohini called 'the Moon's favourite'?",
                "a": "In classical Vedic myth, Chandra (the Moon-god) was married to all 27 nakshatra sisters but openly favoured Rohini. His preference was so obvious that the other 26 wives complained to their father Daksha, who cursed Chandra to wax and wane monthly. Astrologically, this myth is why Rohini is where the Moon expresses its most beautiful, abundant, sensually-alive form.",
            },
            {
                "q": "What careers suit Rohini natives?",
                "a": "Agriculture and horticulture (literal Rohini portfolio), fashion, textiles, cosmetics, jewellery, hospitality and food-service, music and dance (Moon+Venus is the strongest artistic combo in Vedic astrology), real estate and land, caregiving professions (Brahma-the-creator theme), and steady-accumulation finance work. Rohini natives struggle with high-volatility work requiring frequent pivots.",
            },
            {
                "q": "What are the strengths and weaknesses of Rohini natives?",
                "a": "Strengths: visible beauty or magnetism, capacity to attract abundance, patient growth of things (gardens, families, businesses, art), sensual/aesthetic sense, emotional steadiness. Weaknesses: attachment (the Moon holds what it loves — hard to let go), Sthira stubbornness, weight-gain tendency, resistance to necessary change.",
            },
            {
                "q": "Which nakshatras match well with Rohini?",
                "a": "By classical Ashtakoot Guna Milan: best matches are Manushya-gana partners with different nadi — Ardra (Adi nadi), Bharani (Madhya), Purva/Uttara Phalguni, Purva/Uttara Ashadha, Purva/Uttara Bhadrapada. Same-Antya-nadi partners (Krittika, Ashlesha, Magha, Swati, Vishakha, Uttara Ashadha, Shravana, Revati) lose 8 Nadi Kuta points.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 4th of 27. Span: Taurus 10°-23°20'. Lord: Moon (Moon's own nakshatra — Moon's exaltation degree falls here)\n"
            '• Symbol: chariot / banyan. Deity: Brahma (creator)\n'
            "• Nature: growth, abundance, beauty, sensuality, wealth-accumulation, the Moon's favourite\n"
            '• Strong signature: agriculture, luxury goods, arts, hospitality, banking, real estate\n'
            '• Shadow: materialism, jealousy, indulgence, possessiveness'
        ),
    ),
    Article(
        slug="mrigashira-nakshatra",
        title="Mrigashira Nakshatra: The Seeker Who Searches for the Nectar",
        summary="Mrigashira is the fifth nakshatra — Taurus 23°20' to Gemini 6°40'. Ruled by Mars with Soma as its deity, symbolised by a deer's head. Mrigashira natives are the curious wanderers of the zodiac — always searching for the essence beneath the surface.",
        category="Nakshatras",
        hero_image="/static/learn/mrigashira-nakshatra/hero.svg",
        read_time="8 min",
        related=("rohini-nakshatra", "mangal-mars-in-vedic-astrology", "ardra-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Mrigashira nakshatra?",
                "a": "Your Moon needs to sit between 23°20' Taurus and 6°40' Gemini. Mrigashira spans two signs — the first two padas are in Taurus (earthy grounding), the last two in Gemini (airy quick-mind). Generate your free Janma Kundli on Shubh Bhagya to see your exact Moon position.",
            },
            {
                "q": "What is Soma, the deity of Mrigashira?",
                "a": "Soma in Vedic tradition is both a sacred plant (whose exact botanical identity is still debated) and the essence extracted from it — the nectar of immortality that the gods drink. Ritually, Soma is the nectar of the moon, the cool luminous essence of insight. As Mrigashira's deity, Soma gives the nakshatra its distinctive quality of always seeking the essence beneath the surface. Mrigashira natives don't stop at the appearance of things.",
            },
            {
                "q": "What careers suit Mrigashira nakshatra people?",
                "a": "Research and investigation (journalism, academic research, private investigation, market research), travel writing/photography/tourism, astrology and occult work, music (especially exploratory or multi-instrumental), consulting (assess-and-move-on style), teaching, perfumery and taste-based crafts (winemaking, tea, fragrance). Mrigashira natives struggle with repetitive assembly-line work.",
            },
            {
                "q": "What is the shadow side of Mrigashira?",
                "a": "'Never settling.' The searching quality can become an avoidance of arrival. Mrigashira natives sometimes discover in mid-life that they have half-completed skills in twenty domains rather than mastery in one. In relationships, the restless 'is this really the one?' question can undermine partnerships that would deepen if given time. The classical advice: distinguish between search-as-discovery (healthy) and search-as-avoidance (a Vata-nervous pattern needing grounding).",
            },
            {
                "q": "Which nakshatras match well with Mrigashira?",
                "a": "By Ashtakoot Guna Milan: best matches are Deva-gana partners with Adi or Antya nadi — Ashwini (Adi), Hasta (Antya), Shravana (Antya), Revati (Antya). Ashwini and Hasta are often cited as strong Mrigashira partners. Same-Madhya-nadi partners (Bharani, Pushya, Purva Phalguni, Chitra, Anuradha, Purva Ashadha, Dhanishta, Uttara Bhadrapada) lose 8 Nadi Kuta points.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 5th of 27. Span: Taurus 23°20' - Gemini 6°40'. Lord: Mars\n"
            "• Symbol: deer's head. Deity: Soma (moon nectar) / Chandra\n"
            '• Nature: gentle seeker, restless search for essence, curiosity, poetry, timid explorer\n'
            '• Strong signature: writer, poet, researcher, traveller, journalist, hunter of ideas\n'
            '• Shadow: never satisfied, indecisive, wanders without settling, suspicion'
        ),
    ),
    Article(
        slug="ardra-nakshatra",
        title="Ardra Nakshatra: The Storm That Breaks Through — Rudra's Teardrop",
        summary="Ardra is the sixth nakshatra — Gemini 6°40' to 20°00'. Ruled by Rahu with Rudra (the storm form of Shiva) as its deity, symbolised by a teardrop. Ardra natives carry the classical energy of transformation through crisis — sharp, questioning, capable of breakthrough after storm.",
        category="Nakshatras",
        hero_image="/static/learn/ardra-nakshatra/hero.svg",
        read_time="9 min",
        related=("mrigashira-nakshatra", "rahu-in-vedic-astrology", "punarvasu-nakshatra"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Ardra nakshatra?",
                "a": "Your Moon needs to sit between 6°40' and 20°00' of Gemini in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya to see your Moon position and nakshatra. Ardra natives will also see their first Mahadasha listed as Rahu — often with many years already elapsed by adulthood.",
            },
            {
                "q": "Why is Rudra the deity of Ardra?",
                "a": "Rudra is one of the oldest deities in the Rig Veda — older than the classical Shiva. He is the fierce storm-god whose approach terrifies but whose passing leaves the land washed and fertile. Rudra doesn't destroy for destruction's sake; he destroys what has become stagnant so new life can grow. This is the Ardra pattern — the most difficult periods of life often turn out to have been the necessary clearing before what came next.",
            },
            {
                "q": "What careers suit Ardra nakshatra people?",
                "a": "Research (forensic, epidemiological, historical, investigative journalism), emergency response and trauma medicine, trauma-focused psychology, technology and engineering (Rahu-in-Gemini rulership makes Ardra one of the most tech-oriented nakshatras), cybersecurity/cryptography, comedy and satire (dark humour instinct), meteorology, occult and tantric practice.",
            },
            {
                "q": "Is Ardra an unlucky nakshatra?",
                "a": "No — but it's an intense one. The classical texts describe Ardra as a Tikshna (sharp) nakshatra suited for confrontational and transformative work, not for gentle beginnings. Ardra natives often live through unusually intense life events, but the pattern is turbulence-then-clearing, not misfortune. The classical Vedic view is that Rudra's storms are always followed by growth — the difficulty is real but so is the transformation.",
            },
            {
                "q": "Which nakshatras match well with Ardra?",
                "a": "By Ashtakoot Guna Milan: best matches are Manushya-gana partners with Madhya or Antya nadi — Rohini (Antya — often cited as one of the strongest Ardra partners, grounding earth-water for Ardra's storm-air), Bharani (Madhya), Purva/Uttara Phalguni, Purva/Uttara Ashadha, Uttara Bhadrapada. Same-Adi-nadi partners (Ashwini, Punarvasu, Hasta, Jyeshtha, Mula, Shatabhisha, Purva Bhadrapada) lose 8 Nadi Kuta points.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 6th of 27. Span: Gemini 6°40'-20°. Lord: Rahu\n"
            '• Symbol: teardrop / diamond. Deity: Rudra (fierce Shiva — the storm)\n'
            '• Nature: destruction-that-clears, transformation through storm, emotional intensity, breakthrough after breakdown\n'
            '• Strong signature: research (esp. destruction/rebuilding), storm-chasers, mental-health work, IT (Rahu-Mercury)\n'
            '• Shadow: emotional volatility, addictive patterns, difficulty with grief, deception'
        ),
    ),
    Article(
        slug="ashwini-nakshatra",
        title="Ashwini Nakshatra: The Celestial Healer, First of the 27 Lunar Mansions",
        summary="Ashwini is the first nakshatra of the zodiac — the archetype of speed, initiation, and healing. Ruled by Ketu with the Ashwini Kumaras as deities, it defines the personality of anyone born with the Moon in Aries 0°00'–13°20'.",
        category="Nakshatras",
        hero_image="/static/learn/ashwini-nakshatra/hero.svg",
        read_time="8 min",
        related=("mangal-mars-in-vedic-astrology", "ketu-in-vedic-astrology", "kundali-matching-ashtakoot-guna-milan"),
        faqs=(
            {
                "q": "How do I know if I have Moon in Ashwini nakshatra?",
                "a": "Your Moon needs to be between 0°00' and 13°20' of Aries in the sidereal zodiac. Generate your free Janma Kundli on Shubh Bhagya — the chart engine calculates your Janma Nakshatra automatically using the Lahiri ayanamsa and displays it under the Moon row in the planetary table.",
            },
            {
                "q": "What is the ruling planet of Ashwini and why does it matter?",
                "a": "Ashwini is ruled by Ketu — the south lunar node, significator of moksha, past-life karma, and detachment. If you're born with Moon in Ashwini, your Vimshottari Mahadasha sequence starts with Ketu (7 years). This is why Ashwini natives often live front-loaded lives — early spiritual questioning, then breakthrough, then a long Venus period at ~7 that shapes their taste and relationships.",
            },
            {
                "q": "Who are the Ashwini Kumaras?",
                "a": "The Ashwini Kumaras are the twin celestial healers of the Rig Veda — physicians to the gods. They are famous for arriving at dawn just before the Sun, on a golden chariot, to heal the sick and restore the dying. This is why Ashwini nakshatra is associated with speed, medicine, dawn (new beginnings), and healing that comes 'just in time'.",
            },
            {
                "q": "What kind of career suits Ashwini nakshatra people?",
                "a": "Anything involving speed, healing, or being first: medicine and surgery (especially emergency), veterinary practice, sports and athletics, motorsports, first-responder work, entrepreneurship, and any pioneer role. Ashwini natives often thrive as the person who starts something new but hand it off to someone else to sustain — the archetype is 'the one who arrives first, heals, and moves on'.",
            },
            {
                "q": "Which nakshatras are compatible with Ashwini for marriage?",
                "a": "By classical Ashtakoot Guna Milan, Ashwini pairs strongly with other Deva-gana, Adi-nadi female nakshatras — Punarvasu, Pushya (Deva gana), or Hasta / Swati / Anuradha (also Deva) with a compatible nadi. Same-nadi matches (Adi-Adi) score zero on Nadi Kuta (8 points), which is a serious deduction, so an Ashwini native looking at another Ashwini or Ardra or Punarvasu partner should check the rest of the chart carefully. A proper Ashtakoot analysis matters more than any single-attribute rule.",
            },
            {
                "q": "What are the strengths and weaknesses of Ashwini natives?",
                "a": "Strengths: speed of thought, initiative, healing capacity (medical or emotional), youthful energy, physical grace, willingness to try. Weaknesses: impatience, difficulty finishing what they start, restlessness in relationships (the 'move on to next thing' pattern), and a tendency to burn out from taking on too many pioneer projects at once.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            "• 1st of 27 nakshatras. Span: Aries 0°-13°20'. Lord: Ketu\n"
            '• Symbol: horse-head. Deity: Ashwini Kumaras (twin celestial healers)\n'
            '• Nature: rapid healing, first-mover energy, medicine, sports, initiation, speed\n'
            '• Strong signature: doctor/healer, athlete, EMT, first-responder, entrepreneur\n'
            '• Shadow: impulsive action without follow-through, restlessness, accident-proneness'
        ),
    ),
    Article(
        slug="planets-in-7th-house-marriage",
        title="Planets in the 7th House and What They Mean for Your Marriage",
        summary="The 7th house is the mirror of your Ascendant — the partner it attracts. This guide walks each of the nine grahas placed in the 7th house (Sun through Ketu), the classical marriage pattern each one produces, and the per-Ascendant shifts that turn the same placement into a very different reading depending on your Lagna.",
        seo_title="Planets in 7th House: Marriage Meaning of Each Graha",
        seo_description="What Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, or Ketu in the 7th house means for your marriage — classical Vedic reading with per-Ascendant shifts.",
        category="Life Questions",
        hero_image="/static/learn/planets-in-7th-house-marriage/hero.svg",
        read_time="13 min",
        last_updated="2026-07",
        related=(
            "7th-lord-placement-marriage-guide",
            "manglik-dosh",
            "marriage-timing-kundli",
            "shukra-venus-in-vedic-astrology",
        ),
        faqs=(
            {
                "q": "Which planet in the 7th house is best for marriage?",
                "a": "Classically, Venus in the 7th house (in her own signs Taurus or Libra) is the most benefic placement — it produces Malavya Yoga, one of the five Panch Mahapurush yogas, indicating a beautiful and refined spouse, marital happiness, and lifelong prosperity. Jupiter in the 7th is the second-most benefic (wise, dharmic partner and blessings through marriage), with the classical caveat that in a female chart it can indicate late marriage. Waxing Moon in the 7th is also highly favourable — a nurturing, emotionally responsive spouse. The most challenging single-planet placements are Saturn (delay), Rahu (unconventional/foreign, sometimes unstable), Ketu (detachment or separation), and Mars (Manglik friction) — though none of these dooms a marriage; they name specific karmic patterns that need to be worked with.",
            },
            {
                "q": "What does Venus in 7th house mean for marriage?",
                "a": "Venus in the 7th is one of the strongest marriage placements. The partner tends to be physically attractive, aesthetically inclined, often in beauty, art, luxury, or hospitality fields. Multiple partnership offers are common — the challenge is choosing well, not finding at all. When Venus sits in her own signs Taurus or Libra in the 7th, Malavya Yoga forms — a classical Panch Mahapurush yoga indicating exceptional prosperity, married happiness, and refined tastes. The one caveat: Venus debilitated (Virgo) or combust (too close to the Sun) reverses the reading — partnership friction over money, spouse's spending, or comfort-seeking beyond means.",
            },
            {
                "q": "Is Saturn in 7th house bad for marriage?",
                "a": "No — Saturn in the 7th is one of the most misread placements. Classical texts are more balanced about it than modern astrologers usually are. The primary reading is delayed marriage (late 20s or 30s for first marriage), an older or more mature spouse (three to ten years older is common), and a long-tenure partnership that lasts because of the accepted commitment Saturn brings. Divorce rates for Saturn-in-7th marriages are classically lower than average. The caution is emotional distance — the Saturnine coolness can leave the marriage feeling steady but not warm; consciously cultivating warmth benefits both partners. Saturn in his own signs (Capricorn or Aquarius) in the 7th produces one of the most stable, dignified marriage signatures.",
            },
            {
                "q": "What does Rahu in 7th house mean?",
                "a": "Rahu in the 7th is one of the most transformation-heavy 7th-house placements. Classical readings: foreign or unconventional spouse (inter-caste, foreign country, different cultural background), sudden marriage (often with short courtship, sometimes a fated-meeting narrative), fascination-based attraction (magnetic initial pull, reality catches up later), and elevated instability risk when untreated. Untreated Rahu in 7th combined with Saturn or with 7th lord in a dusthana is classically one of the primary second-marriage signatures. Well-modified (Jupiter aspect, own-sign placement, Ashtakoot Guna Milan compatibility with spouse), Rahu in 7th can produce genuinely transformative and enduring inter-cultural marriages.",
            },
            {
                "q": "Does Mars in 7th house always cause Manglik dosha?",
                "a": "Mars in the 7th is one of the six Manglik-triggering houses (1, 2, 4, 7, 8, 12), but 'Manglik' does not equal 'bad marriage'. Cancellation rules apply and are often ignored by simple online calculators — Cancer or Leo Ascendant excludes Mars from Manglik reading regardless of placement (Mars becomes Yogakaraka), Mars in own sign (Aries, Scorpio) or exalted (Capricorn) softens the dosha significantly, Jupiter aspecting or conjunct Mars cancels much of it, and Manglik-with-Manglik matching classically cancels the dosha between partners. Read our full Manglik Dosh guide for the complete cancellation logic — the label without the cancellation check is over-diagnosed.",
            },
            {
                "q": "What if I have two or more planets in the 7th house?",
                "a": "Real charts often have conjunctions in the 7th. Read them as a blend, not additively: Sun + Venus in 7th produces the beautiful-and-dominant partner (Sun's authority + Venus's aesthetics); Saturn + Rahu in 7th compounds delay AND unconventional partner AND separation risk (the most difficult 7th-house combination classically); Mercury + Venus in 7th produces a witty, artistically-inclined, often younger-looking spouse with a strong communication-driven partnership. When reading a conjunction, prioritise: (1) the lord of the sign the conjunction sits in, (2) the dominant planet by dignity (own sign or exalted planet dominates the reading), (3) the modifier planets that colour the primary reading.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 7th house planet = the FLAVOUR of the spouse/partnership (self-mirror principle)\n'
            '• Sun in 7th: dominant/authority spouse, ego friction; Moon in 7th: nurturing, mood-dependent, best when waxing\n'
            '• Mars in 7th: Manglik trigger + energetic/short-tempered spouse; check cancellations\n'
            '• Mercury in 7th: communicative, younger-looking spouse, business-partnership orientation\n'
            '• Jupiter in 7th: wise/dharmic spouse, blessings; classical late-marriage flag for women\n'
            '• Venus in 7th: BEST — Malavya Yoga possibility (own sign), refined spouse, marital happiness\n'
            '• Saturn in 7th: delay + older spouse + long-tenure marriage; NOT verdict of bad marriage\n'
            '• Rahu in 7th: foreign/unconventional spouse, sudden marriage, fascination-based attraction, second-marriage risk if untreated\n'
            '• Ketu in 7th: detached/spiritual spouse, past-life karma theme, most sombre single placement\n'
            '• Per-Ascendant shifts matter: Cancer/Leo lagna Saturn in 7th (own sign) reads very differently'
        ),
    ),
    Article(
        slug="7th-lord-placement-marriage-guide",
        title="7th Lord Placement Guide: How Your Marriage Life Reads From the Ruler of Partnership",
        summary="The 7th lord is different from planets IN the 7th — it is the planet ruling the sign that falls in your 7th house, and where it sits shows WHERE your marriage energy is directed. This guide walks all twelve house placements of the 7th lord: 1st (extension of self), 6th (conflict/service), 10th (power-couple), 12th (foreign/spiritual), and every position between.",
        seo_title="7th Lord Placement Guide: Marriage Reading Across 12 Houses",
        seo_description="Where your 7th lord sits — 1st through 12th — shapes your marriage. Classical Vedic reading of 7th lord in every house, with softener rules and Dasha timing.",
        category="Life Questions",
        hero_image="/static/learn/7th-lord-placement-marriage-guide/hero.svg",
        read_time="14 min",
        last_updated="2026-07",
        related=(
            "planets-in-7th-house-marriage",
            "marriage-timing-kundli",
            "10th-lord-in-6th-house-career",
            "vimshottari-dasha-explained",
        ),
        faqs=(
            {
                "q": "What does 7th lord in 6th house mean for marriage?",
                "a": "The 6th is a dusthana — the house of conflict, service, illness, and enemies. The 7th lord placed in the 6th classically indicates recurring friction pattern in the partnership, sometimes a service-profession spouse (medicine, nursing, social work), and elevated separation risk if the placement is unmodified by benefics. Softeners matter: if the 7th lord in the 6th is exalted, in own sign, or aspected by Jupiter, the friction reads much softer and can express as a marriage where both partners work through significant challenges together, ultimately strengthening the bond. Never a verdict — many marriages with this placement endure through conscious relational work.",
            },
            {
                "q": "Is 7th lord in 8th house always bad?",
                "a": "No — but it is one of the most complex marriage placements and is honestly named in classical texts as elevating second-marriage probability. The 8th house governs hidden things, transformation, in-laws, and sudden change; the 7th lord here indicates a marriage carrying dimensions that are not visible from outside, potentially significant in-law involvement, and a transformation of the native's identity that either the marriage survives or does not. Not a verdict — many 7th-lord-in-8th marriages endure fully. When the 7th lord in the 8th is exalted, aspected by Jupiter, or in own sign, the difficult readings soften substantially. Always check the D-9 Navamsha before drawing conclusions.",
            },
            {
                "q": "What if 7th lord is in own house (7th)?",
                "a": "The 7th lord in its own house (swakshetra) is the strongest possible placement for the 7th lord and one of the most classically-praised marriage signatures. Marriage becomes central to life as an organising structure; timing is on-schedule (the karaka is well-placed to activate through its own Dasha); the partnership is stable and long-tenure, with classically low divorce rates. The one caveat: if the 7th lord in the 7th is combust, retrograde, or heavily afflicted, the strength converts to intensity — the marriage is still central, but central as all-consuming or dramatically difficult rather than serenely stable.",
            },
            {
                "q": "Does 7th lord in 12th house mean foreign spouse?",
                "a": "Foreign spouse is one of the primary classical readings of 7th lord in the 12th, yes — either a partner from a foreign country, or a marriage that results in the native settling abroad, or long periods of the marriage lived in a foreign land. But the 12th (Vyaya Bhava — loss/foreign/spirituality) also carries other readings: spiritual partnership possibility (marriage takes on an ashram-like quality), physical-separation pattern (work-related travel, foreign postings), and interestingly the classical 'bedroom pleasures' theme (strong physical-intimacy compatibility even if other dimensions feel less settled). The 'foreign spouse' reading is the most common modern expression, but not the only one.",
            },
            {
                "q": "Which placement of 7th lord is best for happy marriage?",
                "a": "The classical shortlist of most-benefic 7th lord placements: (1) 7th lord in own house (7th) — swakshetra dignity, marriage as central life anchor; (2) 7th lord in the 9th (dharmic spouse, marriage brings good fortune, often educated or highly-learned partner); (3) 7th lord in the 1st (spouse feels like extension of self, on-time marriage, high compatibility); (4) 7th lord in the 5th (love-marriage signature, children early, playful lifelong dynamic); (5) 7th lord in the 4th (home-oriented spouse, domestic stability, emotional shelter). The most challenging placements are 6th (conflict), 8th (hidden challenges), and 12th (separation) — but all three can be significantly softened by dignity, Jupiter aspect, or Dasha timing.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• 7th lord = planet ruling the sign in the 7th house; different from planets IN the 7th\n'
            "• 7th lord placement = WHERE the marriage energy is directed (which life-domain)\n"
            '• Benefic placements: 1st (extension of self), 5th (love marriage), 7th (own house — strongest), 9th (dharmic + lucky), 10th (power couple), 11th (gains through marriage)\n'
            '• Challenging placements: 6th (conflict, separation risk), 8th (hidden challenges, second-marriage flag), 12th (foreign/separation)\n'
            '• Neutral-with-flavour: 2nd (family wealth), 3rd (courageous spouse), 4th (home-oriented)\n'
            '• Softeners: dignity (own sign/exalted), Jupiter aspect, Dasha timing, D-9 confirmation\n'
            '• Always confirm with D-9 Navamsha 7th lord before drawing conclusions'
        ),
    ),
    Article(
        slug="second-marriage-yoga-kundli",
        title="Second Marriage Indicators in Kundli — Classical Rules and Honest Reading",
        summary="Second marriage is a life event, not a moral judgement. The chart shows tendency, never verdict. Classical Vedic tradition names specific signatures — 7th lord in 8th or 12th, malefics in 7th, Venus in 8th, 8th lord in 7th — that shift second-marriage probability. This guide walks the classical framework, the Dasha windows that activate the pattern, and the editorial guardrails we hold ourselves to on a topic that is often misused for prediction.",
        seo_title="Second Marriage Yoga in Kundli: Classical Rules, Honest Reading",
        seo_description="Second-marriage indicators in Kundli — 7th lord in dusthana, malefics in 7th, Venus in 8th, D-9 confirmation. Tendency signatures, never verdicts.",
        category="Life Questions",
        hero_image="/static/learn/second-marriage-yoga-kundli/hero.svg",
        read_time="12 min",
        last_updated="2026-07",
        related=(
            "planets-in-7th-house-marriage",
            "7th-lord-placement-marriage-guide",
            "marriage-timing-kundli",
            "kundali-matching-ashtakoot-guna-milan",
        ),
        faqs=(
            {
                "q": "Which yoga indicates second marriage in Kundli?",
                "a": "No single yoga is verdict-level, but a specific set of classical signatures shifts probability when they converge: (1) 7th lord in a dusthana (6th, 8th, or 12th house) — 8th is the strongest single signature; (2) malefics (Mars, Saturn, Rahu, Ketu) in the 7th house, especially two or more conjunct; (3) Venus in the 8th house in a male chart, or Jupiter in the 8th in a female chart (marriage karaka in transformation house); (4) 8th lord placed in the 7th house; (5) multiple planets in a dual (dvi-swabhava) sign in the 7th; (6) 7th house heavily aspected by malefics. Convergence of three or more of these, confirmed in the D-9 Navamsha, produces a meaningful tendency reading. Isolated single signatures should never be taken as prediction.",
            },
            {
                "q": "Does Venus in 8th house always mean second marriage?",
                "a": "No — this is one of the most over-diagnosed placements in commercial astrology. Venus in the 8th in a male chart is a tendency signature (Venus is the karaka of marriage; 8th is the transformation house — the karaka in a transformative house increases probability of marriage transitions). But 'tendency' is not 'certainty'. Many male charts with Venus in the 8th spend their lives in first marriages, particularly when Venus is well-aspected (Jupiter's aspect is strongly protective), in own sign (Taurus or Libra), or when the 7th house itself is otherwise clean. The signature matters when it converges with other signatures (7th lord in 8th, malefics in 7th, weak Jupiter). Alone, it is a probability shift, not a prediction.",
            },
            {
                "q": "Can Kundli predict divorce?",
                "a": "No chart predicts divorce as a specific event. What the chart can indicate is whether your karmic terrain contains patterns that make first-marriage transition more probable, and which Dasha windows most heavily activate those patterns. That information is genuinely useful — worth understanding, worth taking into account — but it is never verdict. Chart-based statements about divorce should always be framed as 'your chart carries the signature for elevated separation risk during X Dasha window' rather than 'you will divorce'. If an astrologer confidently predicts divorce as a fact, they are overreaching what classical astrology actually says. Divorce, when it happens, is a function of the whole chart plus the specific person you married plus the specific choices both partners made — most of which no chart can see.",
            },
            {
                "q": "Is second marriage yoga always bad?",
                "a": "Not at all. Second marriage is a life event, not a moral judgement. Many second marriages are the healthiest, most emotionally mature partnerships in a person's life — arriving with self-knowledge, clarity about what matters, and the practical relational skills the first marriage taught. Classical Vedic tradition does not attach moral valence to second marriage; it simply reads the chart terrain honestly. Where the tradition is worth listening to: the same karmic patterns that made the first marriage difficult can carry into the second unless consciously addressed. Signatures need not be avoided — they need to be understood.",
            },
            {
                "q": "Which Dasha activates second marriage?",
                "a": "If a chart carries second-marriage signatures, several Dasha windows classically increase the probability of the pattern firing: (1) Mahadasha of a malefic afflicting the 7th (Saturn, Rahu, Ketu Mahadashas are the classical peak-risk periods — Rahu Mahadasha especially, sudden and unexpected transitions); (2) Mahadasha or Antardasha of the 8th lord (activates the transformation/hidden themes); (3) Antardasha of a planet placed in the 7th during a difficult Mahadasha (e.g., Rahu Antardasha in Saturn Mahadasha when Rahu sits in the 7th); (4) Sade Sati (7.5-year Saturn transit) landing on charts with second-marriage signatures; (5) Rahu-Ketu axis transit across natal 1st-7th (~18-month window every ~9 years). A natal signature can sit dormant for decades until Dasha activates it — if the activating Dasha passes without transition, the signature often stays dormant for the rest of life.",
            },
            {
                "q": "What should I do if my chart shows second-marriage signatures?",
                "a": "The practical response is not fatalism, it is informed attention. First: understand the signature specifically — which houses, which planets, which Dasha window activates it? Vague reassurances are less useful than specific understanding. Second: notice the current Dasha — if the activating Dasha is decades away, this is low priority for immediate attention. Third: address the underlying karmic themes — the signatures point at real patterns (communication styles, conflict tolerance, ability to accommodate a partner) — work on these directly through therapy, counselling, or classical remedies for the relevant planets. Fourth: do NOT read the signature to your spouse as evidence — 'the chart shows we're not meant to last' is not a legitimate conversation opener. Fifth: get a second astrological opinion for major decisions. The chart informs; the life decisions belong to you.",
            },
        ),
        llm_summary=(
            'Keypoints:\n'
            '• Second marriage = life event, not moral judgement; chart shows tendency, not verdict\n'
            '• Classical signatures (need 3+ convergence): 7th lord in dusthana (6/8/12 — 8 strongest), malefics in 7th (Mars/Saturn/Rahu/Ketu), Venus in 8 (male) or Jupiter in 8 (female), 8th lord in 7th, multiple planets in dvi-swabhava sign in 7th, 7th aspected by malefics\n'
            '• D-9 Navamsha 7th house MUST confirm before drawing conclusions\n'
            '• Timing: Rahu/Saturn Mahadashas peak-risk, 8th lord Dasha, Sade Sati window, Rahu-Ketu 1st-7th transit\n'
            '• Supportive signatures against transition: 7th lord in kendra with Jupiter aspect, benefics in 7th, strong Venus/Jupiter karaka, clean D-9\n'
            '• Guardrails: never predict divorce as fact, never predict spouse-death, always frame as tendency + context'
        ),
    ),
    # ─── Cycle 8 remedy cluster (#97-102, #107) ───────────────────────
    Article(
        slug="rahu-remedies", title="Rahu Remedies: 7 Classical Practices to Soften a Difficult Rahu",
        summary="Rahu is Vedic astrology's karaka of ambition, foreignness, and sudden change. When afflicted, produces confusion, foreign complications, and reputation shocks. Classical remedies focus on Beej mantra, Durga worship, Ganesha protection, service to outsiders, Saturday charity, and — for severe cases — Trimbakeshwar Nagbali. This guide walks the 7 most classically-cited Rahu remedies with honest expectations for what each does. NO risky gemstones required.",
        seo_title="Rahu Remedies: 7 Classical Practices That Actually Work",
        seo_description="7 classical Rahu remedies from BPHS + Phaladeepika — Beej mantra, Durga worship, service to outsiders, Saturday charity. Honest, safe, no expensive rituals.",
        category="Grahas", hero_image="/static/learn/rahu-remedies/hero.svg", read_time="10 min", last_updated="2026-07",
        related=("rahu-in-vedic-astrology", "rahu-mahadasha-ketu-antardasha", "kaal-sarp-dosh", "ketu-in-vedic-astrology"),
        faqs=(
            {"q": "Which is the strongest remedy for Rahu?", "a": "Consistency across multiple practices > intensity of any single one. The classical primary pairing: daily Rahu Beej mantra (108x) + weekly Durga Chalisa on Saturdays + monthly serving of marginalised communities. Trimbakeshwar Nagbali is the deepest single ritual but only for severe cases with proper chart confirmation."},
            {"q": "Can I do Rahu remedies without a gemstone?", "a": "Yes — and it's actually recommended. Rahu's classical gemstone (hessonite) can backfire when Rahu is a functional malefic for your Ascendant. All the practices in this guide (mantra, service, charity, Durga worship, Ganesha, Trimbakeshwar) are safe universal remedies that don't require chart analysis."},
            {"q": "How long do Rahu remedies take to show effect?", "a": "Weeks 1-4: mostly building the habit; internal shifts (quieter mind). Months 2-6: perceptible shifts — situations that used to trigger panic feel manageable. Months 6-12: structural shifts — old patterns dissolve. Year 2+: Rahu's underlying karma unfolds; remedies compound. Faster than medication, slower than instant relief."},
            {"q": "Do I need to visit Trimbakeshwar for Kaal Sarp remedy?", "a": "Only for serious cases: full Kaal Sarp Dosh + active Rahu Mahadasha + repeated life shocks. For most Rahu afflictions, daily mantra + weekly Durga + monthly service is sufficient. Trimbakeshwar priests are officially registered — beware of touts; legitimate costs are ₹5,000-25,000 range, anyone quoting lakhs is exploiting."},
            {"q": "Can Rahu remedies fix my addiction?", "a": "Remedies are a support layer, not a substitute for professional care. Rahu-driven addictions (substances, phone/gaming, compulsive behaviours) need therapy + medical support if severe. Remedies help by reducing the underlying restless craving over time."},
        ),
        llm_summary=(
            'Keypoints:\n• Rahu = shadow planet, karaka of ambition, foreignness, obsession, sudden change\n• 7 classical remedies: (1) Rahu Beej mantra "Om Bhram Bhreem Bhraum Sah Rahave Namah" 108x daily, (2) service to outsiders/marginalised/animals, (3) Durga worship (Chalisa, Argala Stotram), (4) Saturday charity (black gram/urad daal, blue clothes, coconut), (5) Ganesha pre-invocation, (6) fasting Saturdays (partial), (7) Trimbakeshwar Nagbali for severe cases\n• Presiding deity: Durga\n• Day: Saturday\n• SAFE — no gemstone needed; hessonite requires chart analysis first\n• Timeline: weeks (habit), 2-6 mo (shifts), 6-12 mo (structural), year 2+ (deep)\n• Anti-exploitation: legitimate Trimbakeshwar Nagbali ₹5-25K; anything quoted in lakhs is scam'
        ),
        qa_status="qa-passed", qa_date="2026-07-30",
    ),
    Article(
        slug="ketu-remedies", title="Ketu Remedies: Classical Practices for Ketu's Detachment Effects",
        summary="Ketu is Rahu's shadow twin — karaka of detachment, past-life karma, spiritual insight, and mysterious losses. Classical remedies center on Ganesha worship (Ketu's presiding deity), Ketu Beej mantra, service to ascetics/elderly/orphans, Tuesday charity, fasting, and Pitru Paksha shraddha. Ketu is a spiritual planet — remedies help you cooperate with detachment consciously rather than being blindsided by it.",
        seo_title="Ketu Remedies: Ganesha, Mantra, Service — What Actually Works",
        seo_description="Classical Ketu remedies — Ganesha worship, Ketu Beej mantra, service to elderly/ascetics, Tuesday charity, ancestral shraddha. Honest, safe, no expensive rituals.",
        category="Grahas", hero_image="/static/learn/ketu-remedies/hero.svg", read_time="9 min", last_updated="2026-07",
        related=("ketu-in-vedic-astrology", "rahu-mahadasha-ketu-antardasha", "kaal-sarp-dosh", "pitru-dosh"),
        faqs=(
            {"q": "Which deity is worshipped for Ketu?", "a": "Ganesha. Classical Vedic tradition assigns Ganesha as Ketu's presiding deity. Ganesha is the remover of obstacles and bridges material/spiritual realms — perfectly matched to Ketu's liminal nature. Sankashti Chaturthi observance is Ketu's peak devotional day."},
            {"q": "Can I wear Cat's Eye for Ketu remedy?", "a": "Only after chart consultation. Cat's Eye (Lehsunia) is Ketu's classical gemstone but can backfire when Ketu is functional malefic for your Ascendant. All the practices in this guide (mantra, Ganesha, service, fasting, shraddha) are safe universal remedies that don't require chart analysis."},
            {"q": "What is the connection between Ketu and Pitru Dosh?", "a": "Ketu carries ancestral lineage karma — the unfinished business from previous generations. When Ketu is heavily afflicted, Pitru Paksha shraddha directly addresses the ancestral-debt aspect. See our separate Pitru Dosh Remedies guide for the full ancestral karma framework."},
            {"q": "Why does Ketu cause 'mysterious' losses?", "a": "Ketu operates through what's karmically due to end. When something is meant to conclude — a relationship, career phase, health condition — Ketu accelerates its ending. Sometimes this looks 'mysterious' because there's no visible outer cause. Remedies help you cooperate with the ending consciously rather than resisting."},
        ),
        llm_summary=(
            'Keypoints:\n• Ketu = shadow planet, karaka of detachment, past-life karma, mysterious losses, spiritual insight\n• 6 classical remedies: (1) Ganesha worship (presiding deity — Om Gam Ganapataye Namah 108x, Sankashti vrat), (2) Ketu Beej mantra "Om Sram Sreem Sraum Sah Ketave Namah" 108x, (3) service to elderly/ascetics/orphans/animals, (4) Tuesday charity (sesame oil, grey clothes, blankets), (5) fasting (Tuesday partial, Amavasya full, Ekadashi), (6) Pitru Paksha shraddha\n• Day: Tuesday (shared with Mars)\n• SAFE — no gemstone; cat\'s eye requires chart analysis\n• Timeline: weeks (habit), 2-6 mo (attachments loosen), year 2+ (subtle awareness emerges)'
        ),
        qa_status="qa-passed", qa_date="2026-07-30",
    ),
    Article(
        slug="surya-sun-remedies", title="Sun Remedies: Strengthening Surya for Confidence, Authority, and Vitality",
        summary="The Sun (Surya) is Vedic astrology's karaka of self, authority, father, vitality, and confidence. Weak Sun manifests as low self-worth, difficulty asserting oneself, father-relationship issues, and physical vitality drops. Classical Sun remedies are safe and immediate — daily Surya Namaskar, Aditya Hridaya Stotra, copper vessel water offering at sunrise, Sunday charity of wheat and jaggery, Sun Beej mantra, Sunday partial fast, and serving father/authority.",
        seo_title="Sun (Surya) Remedies: Surya Namaskar + Aditya Hridaya",
        seo_description="Classical Sun remedies — Surya Namaskar daily, Aditya Hridaya Stotra, sunrise water offering (arghya), Sunday charity, mantra. Safe, immediate, no expensive rituals.",
        category="Grahas", hero_image="/static/learn/surya-sun-remedies/hero.svg", read_time="8 min", last_updated="2026-07",
        related=("surya-sun-in-vedic-astrology", "sun-mahadasha", "debilitated-sun-career", "sun-in-10th-house-career"),
        faqs=(
            {"q": "How many rounds of Surya Namaskar should I do?", "a": "Traditional: 12 rounds daily at sunrise facing east — one for each of the 12 Aditya names. Beginners: start with 3 rounds and build to 12 over weeks. Sundays are the peak day; missing weekdays is fine but never miss Sunday."},
            {"q": "Can I wear Ruby (Manik) without astrologer consultation?", "a": "No. Ruby is safer than hessonite or blue sapphire but STILL requires chart analysis. Never wear ruby when Sun is a functional malefic for your Ascendant (Aquarius, Pisces), combust, or in a dusthana. The practices above are safe universal remedies that don't need chart analysis."},
            {"q": "What is the Aditya Hridaya Stotra?", "a": "A Sanskrit hymn from the Ramayana (Yuddha Kanda) where Agastya Rishi taught it to Rama on the battlefield before slaying Ravana. Sun's most powerful shastric hymn. Recite once daily at sunrise (~8 minutes), three times on Sundays."},
            {"q": "How do Sun remedies help with father-relationship?", "a": "Sun is father-karaka. Classical practice: if father is living, serve consciously (touch feet, seek blessings, listen); if deceased, perform annual shraddha. Sun rewards those who honor the father archetype — this often produces healing in the actual relationship over months."},
        ),
        llm_summary=(
            'Keypoints:\n• Sun = atmakaraka (self), karaka of authority, father, vitality, confidence\n• 7 classical remedies: (1) Surya Namaskar 12 rounds daily at sunrise, (2) Aditya Hridaya Stotra recitation, (3) copper vessel water offering at sunrise (arghya), (4) Sunday charity (wheat, jaggery, red flowers, copper), (5) Sunday partial fast, (6) Sun Beej mantra "Om Hraam Hreem Hraum Sah Suryaya Namah" 108x, (7) serving father and honoring authority\n• Day: Sunday\n• Ruby (Manik) — SAFER than hessonite/blue sapphire but still needs chart check\n• Timeline: 4-6 weeks morning-energy shift; 6-12 mo confidence shift; year 2+ structural'
        ),
        qa_status="qa-passed", qa_date="2026-07-30",
    ),
    Article(
        slug="chandra-moon-remedies", title="Moon Remedies: Chandra Practices for Emotional Peace and Mental Health",
        summary="The Moon (Chandra) is Vedic astrology's karaka of mind, emotion, mother, memory, and mental peace. Since psychological wellbeing depends more on Moon than any other planet, Moon remedies are among the most consequential. Classical remedies focus on Monday practices, milk offering to Shiva, Chandra Beej mantra, silver items, pearl gemstone, mother-service, and modern extensions (Nadi Shodhana, sleep hygiene). Complement — never replace — professional mental healthcare.",
        seo_title="Moon (Chandra) Remedies: Shiva Puja, Silver, Somvar Vrat",
        seo_description="Classical Moon remedies — Monday Shiva puja, silver items, Chandra Beej mantra, mother-service. Support mental peace; combine with professional mental healthcare when needed.",
        category="Grahas", hero_image="/static/learn/chandra-moon-remedies/hero.svg", read_time="8 min", last_updated="2026-07",
        related=("chandra-moon-in-vedic-astrology", "the-9-grahas-overview"),
        faqs=(
            {"q": "Are Moon remedies enough for depression or anxiety?", "a": "No. Moon remedies support mental peace but are NOT a substitute for professional mental healthcare. If you have symptoms of depression, anxiety disorder, bipolar, PTSD, or any other diagnosed condition, please consult a mental health professional. Remedies work best as adjunct to treatment."},
            {"q": "Why milk to Shiva for Moon remedy?", "a": "Shiva holds the crescent Moon on his forehead — he is the deity most closely associated with regulating Chandra's turbulent nature. Monday temple abhishek (milk pouring) + 108 recitations of 'Om Namah Shivaya' + 10 minutes of quiet sitting is the classical primary Moon remedy."},
            {"q": "What is Solah Somvar vrat?", "a": "16 consecutive Monday fasts (partial: one meal only, no rice, no lentils). Traditionally observed by unmarried women seeking a good spouse, or by anyone with severe emotional difficulty. Peak during Shravana month (July-August). Not for those with medical conditions or pregnancy."},
            {"q": "Can I wear Pearl (Moti) as Moon remedy?", "a": "Pearl is safer than most gemstones but still requires Ascendant verification. Cancer, Scorpio, Pisces most compatible. Consult a qualified astrologer before wearing. The Monday practices + silver items are safe universal remedies."},
        ),
        llm_summary=(
            'Keypoints:\n• Moon = karaka of mind (manas), emotion, mother, mental peace\n• Moon remedies matter MORE than other planet remedies for mental wellbeing\n• Classical: (1) Monday milk offering to Shiva at temple, (2) Somvar vrat / Solah Somvar, (3) Chandra Beej mantra "Om Shraam Shreem Shraum Sah Chandramase Namah" 108x, (4) silver items (glass, ring), (5) Monday charity (rice, milk, white clothes), (6) serving mother, (7) Nadi Shodhana + Brahmi + sleep hygiene as modern complements\n• Day: Monday\n• Pearl (Moti) — safer than most but verify Ascendant\n• CRITICAL: complement — do not replace — professional mental healthcare'
        ),
        qa_status="qa-passed", qa_date="2026-07-30",
    ),
    Article(
        slug="pitru-dosh-remedies", title="Pitru Dosh Remedies: Classical Rituals to Clear Ancestral Karma",
        summary="Pitru Dosh — ancestral karmic debt — is one of the most misdiagnosed categories in Indian astrology commerce. Genuine remedies are simple: Pitru Paksha shraddha, tarpan (water offering), feeding a Brahmin+cow+crow on death anniversaries, monthly Amavasya practice, and Gaya tri-pindi shraddha for serious cases. This guide walks the classical remedies with strong guardrails against exploitation.",
        seo_title="Pitru Dosh Remedies: Shraddha, Tarpan, Gaya Pilgrimage",
        seo_description="Classical Pitru Dosh remedies — Pitru Paksha shraddha, tarpan, Ganesha worship, Gaya pilgrimage. Anti-exploitation guide; every remedy under ₹500 (except optional Gaya trip).",
        category="Doshas", hero_image="/static/learn/pitru-dosh-remedies/hero.svg", read_time="9 min", last_updated="2026-07",
        related=("pitru-dosh", "kaal-sarp-dosh", "sade-sati", "chandra-moon-remedies"),
        faqs=(
            {"q": "How much does Pitru Dosh puja actually cost?", "a": "All classical remedies in this guide can be done for under ₹500 (except Gaya pilgrimage which costs travel + ₹5-15K for tri-pindi shraddha from Gayawal priests). Anyone quoting ₹50,000+ for 'Pitru Shanti Yagna' or lakhs for Kaal Sarp is exploiting anxiety."},
            {"q": "What is Pitru Paksha and when is it?", "a": "The 15-day period preceding Sharad Navratri (typically September). Dedicated to ancestor offerings. Peak remedial window for Pitru Dosh. Minimum practice: daily tarpan facing south with sesame water, feed a Brahmin+cow+crow at least once, avoid celebrations."},
            {"q": "Do I need to go to Gaya?", "a": "Only for serious Pitru Dosh — chronic career/marriage/children obstacles, repeated pattern across generations. Alternatives if Gaya is not accessible: Trimbakeshwar (Nagbali + Narayan Bali), Kurukshetra during eclipses, Rameshwaram for South Indian traditions. Consistent annual Pitru Paksha observance is often sufficient."},
            {"q": "How do I know if I really have Pitru Dosh?", "a": "Classical signatures: Sun heavily afflicted by Rahu/Saturn, 9th/12th house lords afflicted, Rahu-Ketu on 9th-3rd or 12th-6th axis. Life patterns: repeated obstacles despite competence, children delayed, money slips through fingers, frequent ancestor-related dreams. Verify with proper chart reading before investing in remedies."},
        ),
        llm_summary=(
            'Keypoints:\n• Pitru Dosh = ancestral karmic debt (Sun+Rahu/Saturn affliction, 9th/12th house issues)\n• MOST OVER-EXPLOITED category in Indian astrology commerce\n• 6 classical remedies: (1) Pitru Paksha 15-day observance (tarpan, feed Brahmin/cow/crow), (2) annual death anniversary tarpan (Barsi), (3) monthly Amavasya practice, (4) Gaya tri-pindi shraddha for serious cases, (5) Ganesha + Vishnu worship (Ekadashi vrat), (6) serving living elders\n• ALL remedies < ₹500; Gaya adds travel + ₹5-15K\n• Anti-exploitation: anyone quoting ₹50K+ for Pitru Shanti is scamming'
        ),
        qa_status="qa-passed", qa_date="2026-07-30",
    ),
    Article(
        slug="kaal-sarp-dosh-remedies", title="Kaal Sarp Dosh Remedies: Classical Practices That Actually Work",
        summary="Kaal Sarp Dosh — all 7 non-shadow planets on one side of the Rahu-Ketu axis — is the most exploited category in Indian astrology commerce. Real remedies are simple: Nag Panchami observance, Shiva worship on Mondays, silver serpent offering, combined Rahu+Ketu Beej mantras, and Trimbakeshwar Nagbali for severe cases. This guide walks the seven classically-cited remedies with strong guardrails against exploitation.",
        seo_title="Kaal Sarp Dosh Remedies: Shiva Puja, Nag Panchami, Trimbakeshwar",
        seo_description="Classical Kaal Sarp Dosh remedies — Monday Shiva puja, Nag Panchami, silver serpent offering, Trimbakeshwar Nagbali. Anti-exploitation guide with cost sanity checks.",
        category="Doshas", hero_image="/static/learn/kaal-sarp-dosh-remedies/hero.svg", read_time="9 min", last_updated="2026-07",
        related=("kaal-sarp-dosh", "rahu-remedies", "ketu-remedies", "pitru-dosh-remedies"),
        faqs=(
            {"q": "How much does Trimbakeshwar Kaal Sarp Puja cost?", "a": "Legitimate registered priests at Trimbakeshwar charge ₹5,000-25,000 depending on scope + family size. Anyone quoting ₹50,000+ is overcharging; anyone quoting lakhs is exploiting anxiety. Go through the temple trust, not touts approaching at the town."},
            {"q": "Is Kaal Sarp Dosh really that serious?", "a": "It's real when all 7 planets are truly between Rahu and Ketu on one semicircle. But it's over-diagnosed — check your chart with our free /kaal-sarp-check tool first. Even genuine KSD is not a curse; it's a specific karmic pattern with named 12 types (Anant, Kulik, Padma, etc.) each with distinct life themes."},
            {"q": "When is Nag Panchami?", "a": "5th day of the bright half of Shravana month (typically August). Classical annual serpent-worship day and KSD's peak remedial day. Fast during the day, offer milk to serpent images at temple, perform Nag Devata puja."},
            {"q": "Can I do KSD remedy at home instead of Trimbakeshwar?", "a": "Yes. Weekly Monday Shiva visits, Nag Panchami observance, silver serpent offering, and Rahu+Ketu Beej mantras done consistently at home are the accessible starting point. Save the Trimbakeshwar pilgrimage for when you're certain of the diagnosis and have the time to do it well."},
        ),
        llm_summary=(
            'Keypoints:\n• Kaal Sarp Dosh = all 7 non-shadow planets on one semicircle of Rahu-Ketu axis\n• MOST EXPLOITED category in astrology commerce; real remedies are cheap\n• 7 classical remedies: (1) Monday Shiva worship + milk abhishek + Om Namah Shivaya 108x, (2) Nag Panchami annual observance (fast + serpent milk offering), (3) silver serpent offering at Shiva temple or river (₹500-2K, once), (4) Rahu+Ketu Beej mantras combined 108x each, (5) Trimbakeshwar Nagbali Puja ₹5-25K for severe cases, (6) symbolic serpent-serving (donate to reptile rescues), (7) year-long weekly practice\n• Cost sanity: anyone quoting lakhs for KSD Shanti is scamming; ₹15-25K is the ceiling for legitimate Trimbakeshwar puja'
        ),
        qa_status="qa-passed", qa_date="2026-07-30",
    ),
    Article(
        slug="manglik-remedies", title="Manglik Remedies: Classical Practices to Soften Mars in Marriage Charts",
        summary="Manglik Dosh (Mangal Dosh) remedies focus on softening Mars's placement in the six qualifying houses (1, 2, 4, 7, 8, 12) that classical tradition flags for marriage friction. The most powerful remedies are Hanuman worship (Mars's presiding deity), Tuesday practices, Kumbh Vivah for severe cases, and Ashtakoot matching. This guide walks the seven classically-cited remedies with the honest note that cancellation rules often mean no remedy is even needed.",
        seo_title="Manglik Remedies: Hanuman Worship, Kumbh Vivah, Matching",
        seo_description="Classical Manglik Dosh remedies — Hanuman Chalisa, Tuesday practices, Kumbh Vivah, matching another Manglik. Check cancellation rules first — most 'Manglik' charts are actually cancelled.",
        category="Doshas", hero_image="/static/learn/manglik-remedies/hero.svg", read_time="9 min", last_updated="2026-07",
        related=("manglik-dosh", "mangal-mars-in-vedic-astrology", "mars-remedies", "kundali-matching-ashtakoot-guna-milan"),
        faqs=(
            {"q": "Is Kumbh Vivah remedy legitimate?", "a": "Classical tradition prescribes it for severe uncancelled Manglik before marriage — marriage to a clay pot (kumbh) or peepal tree that 'consumes' the first Manglik-marriage karma. Cost ₹2K-10K from legitimate priests. Not universally accepted by modern astrologers; some question efficacy. Often more valuable as psychological closure than ritual mechanic."},
            {"q": "Do I need to check Manglik cancellation before doing remedies?", "a": "YES — this is the most important first step. Use our /manglik-check tool which explicitly applies classical cancellation rules (Cancer/Leo Lagna Yogakaraka, Jupiter aspect, own-sign Mars, etc.). Most 'Manglik' charts are actually cancelled and need no remedy at all."},
            {"q": "Can red coral (Moonga) cancel Manglik?", "a": "Red Coral is Mars's classical gemstone but can backfire when Mars is a functional malefic for your Ascendant. NEVER wear coral without proper chart analysis. Hanuman worship + Tuesday practices are safe universal remedies that don't need chart verification."},
            {"q": "What if I'm Manglik and my partner is not?", "a": "Classical tradition strongly recommends Manglik-Manglik matching (the two doshas cancel each other). If mismatch: soften with Hanuman practices + Vishnu worship + Kumbh Vivah before marriage. Also: many 'mismatch' cases are actually cancelled Manglik in one or both charts — verify with our /manglik-check tool first."},
        ),
        llm_summary=(
            'Keypoints:\n• Manglik = Mars in 1/2/4/7/8/12 from Lagna OR Moon\n• CHECK CANCELLATION FIRST — most Manglik is cancelled by classical rules (Cancer/Leo Lagna, Jupiter aspect, own-sign Mars, matching)\n• 7 classical remedies: (1) Hanuman worship (Chalisa daily, Ashtak Tuesdays), (2) Vishnu Sahasranama + Ekadashi vrat, (3) Mars Beej mantra "Om Kraam Kreem Kraum Sah Bhaumaya Namah" 108x, (4) Tuesday charity (toor daal/arhar — Mars classical grain, plus red masoor folk offering, jaggery, red items), (5) Kumbh Vivah before marriage for severe cases (folk-remedial practice, not attested in BPHS), (6) Ashtakoot Guna Milan matching (Manglik-Manglik cancels), (7) behavioural (exercise, avoid red meat/alcohol during intensive remedy)\n• Day: Tuesday\n• Red Coral needs chart check; unsafe as blanket remedy\n• STRONGEST REMEDY: finding a compatible partner via proper matching'
        ),
        qa_status="qa-passed", qa_date="2026-07-30",
    ),
    Article(
        slug="dhana-yoga-wealth-combinations", title="Dhana Yogas: 9 Classical Wealth Combinations to Check in Your Kundli",
        summary="Dhana Yogas — wealth combinations in your Kundli — form when the lords of the 2nd, 5th, 9th, and 11th houses interact favourably with each other or with strong benefics. Classical texts (BPHS, Phaladeepika, Saravali) list dozens; this guide covers the 9 most consequential: Lakshmi Yoga, Chandra-Mangala, Guru-Mangala, Kubera Yoga, Vasumati, Adhi Yoga, Neelkantha, Panch Mahapurush wealth angles, and Vipreeta Raja Yoga.",
        seo_title="Dhana Yogas: 9 Wealth Combinations in Your Kundli",
        seo_description="9 classical Dhana Yogas (wealth combinations) in Vedic astrology — Lakshmi Yoga, Kubera Yoga, Vasumati, Vipreeta Raja Yoga. When Dasha activates them, wealth arrives.",
        category="Yogas", hero_image="/static/learn/dhana-yoga-wealth-combinations/hero.svg", read_time="10 min", last_updated="2026-07",
        related=("panch-mahapurush-yoga", "gajakesari-yoga", "financial-struggles", "shukra-venus-in-vedic-astrology", "2nd-lord-placement-wealth-guide", "11th-lord-placement-gains-guide"),
        faqs=(
            {"q": "Which is the strongest Dhana Yoga?", "a": "No single one dominates — the strength comes from multiple yogas combined. Lakshmi Yoga (9th lord well-placed + Venus in kendra) is the classical wealth-blessing archetype. Vipreeta Raja Yoga (dusthana lord exchange) often marks self-made wealth. Both together in one chart is exceptional."},
            {"q": "Do I need multiple Dhana Yogas or is one enough?", "a": "A single strong Dhana Yoga can produce comfortable wealth. Major wealth typically requires 2-3+ combined Dhana Yogas activating in overlapping Dasha periods. Also need supporting infrastructure: strong Jupiter, well-placed 2nd house lord, no severe Saturn afflictions."},
            {"q": "What if I have Dhana Yogas but still struggle financially?", "a": "The yogas need the right Dasha window to activate. If you're in an unsupportive Mahadasha (Rahu, Saturn, or 6th/8th/12th lord's Dasha), even strong yogas underperform. Also: yogas produce POTENTIAL — actual wealth needs effort + right decisions. Some charts also have Vipreeta Raja Yoga which produces wealth AFTER adversity, not before."},
            {"q": "How do I check Dhana Yogas in my chart?", "a": "Generate your free Janma Kundli on Shubh Bhagya — the Yogas panel automatically detects most Dhana Yogas including Panch Mahapurush, Gajakesari, and others. For deeper wealth analysis, combine with the 2nd Lord and 11th Lord placement guides."},
            {"q": "What is Vipreeta Raja Yoga?", "a": "The counterintuitive wealth yoga — formed when the lords of the 6th, 8th, and 12th houses (all dusthanas) exchange positions among themselves. Effect: wealth arises from overcoming adversity. Often present in rags-to-riches biographies and self-made wealthy people. The obstacles themselves become the ladder."},
        ),
        llm_summary=(
            'Keypoints:\n• Dhana Yoga = wealth combination from interaction of 2nd + 5th + 9th + 11th house lords with benefics\n• 9 most consequential: Lakshmi Yoga (9L in own/exalted + Venus in kendra), Chandra-Mangala (Moon+Mars), Guru-Mangala (Jupiter+Mars), Kubera Yoga (2L+11L+Jupiter in kendras), Vasumati (benefics in 3/6/10/11), Adhi Yoga (benefics 6/7/8 from Moon), Neelkantha (Jupiter+Mercury), Panch Mahapurush wealth (Ruchaka/Bhadra/Hamsa/Malavya/Shasha), Vipreeta Raja Yoga (6/8/12 lords exchange)\n• Activation: Mahadasha of yoga-planet, Antardasha of 2/5/9/11 lord, Jupiter transit over yoga planet\n• Single yoga = comfortable wealth; 2-3+ combined = major potential; still needs effort'
        ),
        qa_status="auto-scanned", qa_date="2026-07-30",
    ),
    Article(
        slug="2nd-lord-placement-wealth-guide", title="2nd Lord Placement Guide: Where the Ruler of Wealth Sits Shapes Your Money Life",
        summary="The 2nd lord — the planet ruling the sign in your 2nd house — directs your wealth, family, speech, and accumulated resources. Where it sits across the 12 houses shapes HOW money enters your life and what kind of resources you accumulate. Companion to the 7th Lord (marriage) and 10th Lord (career) placement guides.",
        seo_title="2nd Lord in Different Houses: How Your Wealth Pattern Reads",
        seo_description="Where your 2nd lord (ruler of wealth) sits across 12 houses shapes your money life. Complete classical reading of all 12 placements with modifier rules.",
        category="Life Questions", hero_image="/static/learn/2nd-lord-placement-wealth-guide/hero.svg", read_time="9 min", last_updated="2026-07",
        related=("dhana-yoga-wealth-combinations", "7th-lord-placement-marriage-guide", "10th-lord-in-6th-house-career", "financial-struggles"),
        faqs=(
            {"q": "What does 2nd lord in 11th house mean?", "a": "Second-strongest placement after own house. Networks, elder siblings, group ventures drive wealth. Multiple income streams. Classical marker for successful traders and network-based entrepreneurs. Amplified further if 2nd + 11th lords are conjunct."},
            {"q": "Is 2nd lord in 6th house always bad for wealth?", "a": "No. 6th is a dusthana but wealth here often accumulates through service industries, litigation, medicine, or debt-financing (banking). Recurring inflows AND outflows; requires financial discipline. Softeners like Jupiter aspect can transform this into a strong service-industry wealth signature."},
            {"q": "What if 2nd lord is in own house (2nd)?", "a": "Strongest placement (Swakshetra). Family wealth is stable, savings accumulate naturally, native speaks with authority. Classical marker for family businesses running across generations."},
            {"q": "Does 2nd lord in 12th house mean no wealth?", "a": "Not 'no wealth' — wealth flows outward. Spending on travel, luxury, charity, foreign lands, spiritual pursuits. Best when consciously channelled. Combined with Vipreeta Raja Yoga, this can flip to unusual wealth patterns. Alone, native tends toward experience-wealth rather than material-wealth."},
            {"q": "How do I find my 2nd lord?", "a": "Look at which sign is in your 2nd house — that sign's ruling planet is your 2nd lord. Aries/Scorpio = Mars, Taurus/Libra = Venus, Gemini/Virgo = Mercury, Cancer = Moon, Leo = Sun, Sagittarius/Pisces = Jupiter, Capricorn/Aquarius = Saturn. Generate your free Kundli on Shubh Bhagya to see it computed."},
        ),
        llm_summary=(
            'Keypoints:\n• 2nd lord = ruler of sign in 2nd house = director of wealth, family, speech, accumulated resources\n• Best placements: 2nd (own), 11th (gains), 9th (fortune), 5th (creative)\n• Weakest (require softeners): 6th (service+debt), 8th (hidden/sudden), 12th (outflow)\n• Kendra placements (1/4/7/10): wealth becomes central life theme\n• Modifiers: Jupiter aspect blesses; Saturn delays; Rahu adds sudden/foreign patterns\n• 2nd+11th lord conjunction = classic Dhana Yoga\n• Companion to 7th Lord (marriage) + 10th Lord (career) + 11th Lord (gains) placement guides'
        ),
        qa_status="auto-scanned", qa_date="2026-07-30",
    ),
    # ─── Muhurat cluster (#94, #95, #103, #104) ───────────────────────
    Article(
        slug="vivah-muhurat-2027", title="Vivah Muhurat 2027 — Classical Rules for Auspicious Wedding Dates",
        summary="A Vivah Muhurat is not just a 'good day' — it's a specific window where six classical criteria align: Guru + Shukra visibility, no Malamas, no Chaturmas, favourable nakshatra + tithi, no Panchak, no Rahu Kaal in ceremony hour. This guide walks the 2027 rules, seasonal patterns, personal chart intersections, and honest guidance beyond the calendar.",
        seo_title="Vivah Muhurat 2027 — Classical Rules for Wedding Dates",
        seo_description="Vivah Muhurat 2027 — 6 classical criteria for auspicious wedding dates. Seasonal windows Jan-Feb, Apr-Jun, mid-Nov onwards. Personal chart matters beyond calendar.",
        category="Life Questions", hero_image="/static/learn/vivah-muhurat-2027/hero.svg", read_time="8 min", last_updated="2026-07",
        related=("marriage-timing-kundli", "kundali-matching-ashtakoot-guna-milan", "manglik-dosh", "griha-pravesh-muhurat-2026-2027"),
        faqs=(
            {"q": "Which months in 2027 are best for marriage?", "a": "Jan-Feb 2027 (winter window), Apr-Jun 2027 (spring/summer, most popular), and mid-Nov 2027 onwards (post-Chaturmas resumption). Chaturmas (mid-Jul to mid-Nov) is traditionally weddings-restricted. Adhik Maas dates are additional blackout — verify with Panchang."},
            {"q": "What is Deva Uthani Ekadashi and why does it matter?", "a": "Deva Uthani Ekadashi marks the end of Chaturmas — Vishnu 'awakens' from his four-month sleep. This day resumes auspicious ceremonies including weddings. Typically falls in mid-November. Post-Deva-Uthani through spring is the year's densest wedding season."},
            {"q": "Can I get married during Chaturmas?", "a": "Classical tradition says no; modern practice varies by region and family. If you must marry during Chaturmas, consult a priest for compensating rituals. The tradition's rationale: Vishnu (protector of dharmic bonds) is sleeping, so ceremonies lack full blessing."},
            {"q": "What is Panchak and why avoid it?", "a": "5-day period when Moon transits the last 5 nakshatras (Dhanishta latter half through Revati). Classical tradition considers Panchak inauspicious for many ceremonies including weddings. Some specific classes of Panchak (Mrityu Panchak on Saturday, Roga Panchak on Tuesday) are particularly cautioned."},
            {"q": "How do I match a wedding date to my kundli specifically?", "a": "Use our free /manglik-check + /sade-sati-check tools for both partners. Then generate full kundlis via /kundli. Check nakshatra harmony with the intended date's nakshatra, avoid Rahu-Rahu or Ketu-Ketu antardashas, and confirm no severe Sade Sati Peak. We're building a personalised Muhurat Finder tool."},
        ),
        llm_summary=(
            'Keypoints:\n• Vivah Muhurat = wedding date meeting 6 classical criteria\n• (1) Guru + Shukra visible above horizon uncombust, (2) not Malamas/Adhik Maas, (3) not Chaturmas (mid-Jul to mid-Nov), (4) favourable nakshatra + tithi, (5) no Panchak, (6) no Rahu Kaal in ceremony hour\n• 2027 windows: Jan-Feb (winter), Apr-Jun (spring/summer), mid-Nov onwards (post-Chaturmas peak)\n• Auspicious nakshatras: Rohini, Mrigashira, Magha, Uttara Phalguni, Hasta, Swati, Anuradha, Mula, Uttara Ashadha, Uttara Bhadrapada, Revati\n• Personal factors matter: Sade Sati Peak caution, Rahu antardasha caution, Manglik-Manglik matching preferred\n• Personalised date computation deferred to Muhurat Finder tool (#108)'
        ),
        qa_status="auto-scanned", qa_date="2026-07-30",
    ),
    Article(
        slug="griha-pravesh-muhurat-2026-2027", title="Griha Pravesh Muhurat 2026-27 — Auspicious House-Warming Dates",
        summary="Griha Pravesh (house-warming) marks entry into a new home. Classical tradition names three types (Apoorva, Sapoorva, Dwandwa) and seven criteria for auspicious dates. Dates cluster around Nov 2026 (post-Diwali) through May 2027 (pre-Chaturmas). Personal chart matters — this guide walks the criteria, personal factors, and honest guidance on modern practical constraints like builder handover dates.",
        seo_title="Griha Pravesh Muhurat 2026-27 — Auspicious House-Warming Dates",
        seo_description="Griha Pravesh Muhurat 2026-27 — 7 classical criteria, three types (Apoorva/Sapoorva/Dwandwa), personal factors, guidance on developer handover conflicts.",
        category="Life Questions", hero_image="/static/learn/griha-pravesh-muhurat-2026-2027/hero.svg", read_time="7 min", last_updated="2026-07",
        related=("vivah-muhurat-2027", "gochar-2026-planetary-transits", "kaal-sarp-dosh", "sade-sati"),
        faqs=(
            {"q": "What is the best month for Griha Pravesh in 2027?", "a": "Given the 7 classical criteria, prime windows are Nov 2026 (Dev Uthani onwards, peak season), Dec 2026-Feb 2027 (winter window), Mar-Jun 2027 (spring/summer). Chaturmas (mid-Jul to mid-Nov) is traditionally avoided; verify Adhik Maas dates via Panchang."},
            {"q": "Can I do Griha Pravesh during Chaturmas?", "a": "Traditional practice: no. Modern flexibility varies. If forced (developer handover): do a symbolic entry (bring water, diya, small idol) on an auspicious muhurat, delay full ceremony to next window, or perform compensating ritual via a priest."},
            {"q": "Does my personal chart matter for Griha Pravesh?", "a": "Yes. A universally-good date can be personally difficult if your moon nakshatra clashes with the date's nakshatra, you're in a Rahu-Rahu antardasha, or currently in Sade Sati Peak. Use our free /sade-sati-check + /kundli tools for personal factors."},
            {"q": "What if the builder's possession date isn't auspicious?", "a": "Common modern conflict. Options: (1) perform symbolic entry on auspicious muhurat before moving, (2) do provisional entry on handover date and full ceremony later, (3) consult priest for compensating ritual. Never let a bad date force a bad ceremony — always check with an astrologer."},
            {"q": "Do I need a priest?", "a": "For full traditional Griha Pravesh, yes — the ceremony involves specific mantras + fire ritual + specific offerings a householder cannot easily do alone. For simpler observance: bring water, milk, honey, diya into the new home while chanting Gayatri or Vishnu Sahasranama, distribute prasad, and follow up with full ceremony later."},
        ),
        llm_summary=(
            'Keypoints:\n• Griha Pravesh = house-warming ceremony, 3 types (Apoorva new, Sapoorva returning, Dwandwa inherited)\n• 7 criteria: Guru visible + favourable nakshatra + favourable tithi + no Chaturmas + no eclipse + no Panchak + auspicious weekday (Mon/Wed/Thu/Fri best)\n• 2026-27 windows: Nov 2026 (Dev Uthani onwards, peak), Dec-Feb (winter), Mar-Jun 2027 (spring)\n• Personal factors: moon nakshatra harmony, Sade Sati Peak caution, Rahu antardasha caution\n• Builder handover conflict: symbolic entry on auspicious muhurat + full ceremony later'
        ),
        qa_status="auto-scanned", qa_date="2026-07-30",
    ),
    Article(
        slug="diwali-muhurat-2026", title="Diwali Muhurat 2026 — Complete 5-Day Ritual Windows",
        summary="Diwali 2026 spans five days of specific muhurats — Dhanteras (buying), Naraka Chaturdashi (cleansing), Lakshmi Puja (main), Govardhan (food offering), Bhai Dooj (sibling bond). Each has its own auspicious window. This guide walks the classical muhurat rules for all five days.",
        seo_title="Diwali Muhurat 2026 — Dhanteras, Lakshmi Puja, Bhai Dooj",
        seo_description="Diwali Muhurat 2026 — all 5 days: Dhanteras buying window, Lakshmi Puja pradosh kaal, Govardhan Puja, Bhai Dooj afternoon muhurat. Classical rules.",
        category="Life Questions", hero_image="/static/learn/diwali-muhurat-2026/hero.svg", read_time="6 min", last_updated="2026-07",
        related=("griha-pravesh-muhurat-2026-2027", "vivah-muhurat-2027", "shani-saturn", "sade-sati"),
        faqs=(
            {"q": "When is Lakshmi Puja on Diwali 2026?", "a": "Falls on the Amavasya of Kartik month (typically late Oct or early Nov 2026 — verify exact date with Panchang). Puja can be performed in Pradosh Kaal (~6-8 PM, most common), Nishita Kaal (midnight, traditional tantric), or Mahanishita Kaal (deep night, specialised)."},
            {"q": "What time is the Dhanteras buying muhurat?", "a": "Traditional Dhanteras buying window is Pradosh Kaal — roughly 6-8 PM local time on Dhanteras evening. Gold, silver, brass, utensils, and vehicle purchases are considered especially auspicious in this window. Verify exact times for your city via Panchang."},
            {"q": "Should businesses do Chopda Pujan on Diwali?", "a": "Yes — Chopda Pujan (worshipping new account books) is traditional for businesses on Diwali night, ideally during Pradosh Kaal Lakshmi Puja. Symbolises starting the new financial year with Lakshmi's blessing. Choose the muhurat that fits your local Panchang."},
            {"q": "What is Govardhan Puja?", "a": "Falls on Pratipada of Kartik Shukla paksha (day after Diwali). Commemorates Krishna lifting Govardhan hill. Traditional practice: prepare Annakut (mountain of foods), offer to Krishna, distribute as prasad. Morning muhurat preferred."},
        ),
        llm_summary=(
            'Keypoints:\n• Diwali 2026 = 5-day sequence: Dhanteras, Naraka Chaturdashi (Chhoti Diwali), Lakshmi Puja, Govardhan Puja, Bhai Dooj\n• Dhanteras: Pradosh Kaal (~6-8 PM) buying window\n• Lakshmi Puja: Pradosh Kaal most common, also Nishita (midnight), Mahanishita (deep night)\n• Business Chopda Pujan on Diwali night\n• Govardhan: Annakut morning muhurat\n• Bhai Dooj: afternoon Aparahnakaal, sisters apply tilak to brothers\n• Location-dependent: exact windows via Panchang for your city'
        ),
        qa_status="auto-scanned", qa_date="2026-07-30",
    ),
    Article(
        slug="karva-chauth-2026", title="Karva Chauth 2026 — Complete Vrat Timing, Moon Sighting, and Muhurat",
        summary="Karva Chauth 2026 is the classical fast observed by married women for husband's wellbeing. Falls on 4th tithi of Kartik Krishna paksha (October 2026). This guide walks the 2026 timing, hour-by-hour vrat sequence (sargi, nirjala fast, puja, moon sighting, breaking fast), classical significance, and honest modern guidance on observance including health cautions.",
        seo_title="Karva Chauth 2026 — Vrat Timing, Moon Rise, Puja Muhurat",
        seo_description="Karva Chauth 2026 timing — sargi pre-dawn, nirjala vrat, evening puja, moonrise (~8:15-8:45 PM Delhi). Classical rules + honest modern guidance.",
        category="Life Questions", hero_image="/static/learn/karva-chauth-2026/hero.svg", read_time="6 min", last_updated="2026-07",
        related=("vivah-muhurat-2027", "chandra-moon-in-vedic-astrology", "kundali-matching-ashtakoot-guna-milan"),
        faqs=(
            {"q": "When is Karva Chauth 2026?", "a": "Falls on 4th tithi (Chaturthi) of Krishna paksha in Kartik month — typically late October or early November 2026. Verify exact date via Panchang."},
            {"q": "What time is moonrise on Karva Chauth 2026?", "a": "Location-dependent. For Delhi: approximately 8:15-8:45 PM local time. For other cities: check Panchang moonrise times for the specific Karva Chauth date. The moon must be sighted to break the fast."},
            {"q": "Can I do Karva Chauth if I'm pregnant or on medication?", "a": "Never do nirjala vrat (without water) if pregnant, nursing, diabetic, or on medication that requires food/water. Observe modified vrat (with water) instead, or skip entirely — your health matters more than any ritual."},
            {"q": "Is Karva Chauth only for Hindu women?", "a": "Traditionally observed within Hindu married women's practice, but modern observance varies. Some observe as personal choice from any background; some observe for same-sex partners; some men observe for their wives. The vrat's core is intention + care + community — how you frame it is personal."},
        ),
        llm_summary=(
            'Keypoints:\n• Karva Chauth = 4th tithi Kartik Krishna paksha, Oct 2026\n• Sequence: Sargi pre-dawn (mother-in-law offers meal), nirjala vrat from sunrise, Pradosh Kaal puja (community), moonrise (~8:15-8:45 PM Delhi), husband feeds first sip\n• Classical significance: sindoor-strengthening, community observance, discipline, devotional bhakti\n• Health-first: no nirjala vrat if pregnant/diabetic/medication; consent matters\n• Modern flexibility: same-sex partners, non-traditional families, some men observe'
        ),
        qa_status="auto-scanned", qa_date="2026-07-30",
    ),
    Article(
        slug="11th-lord-placement-gains-guide", title="11th Lord Placement Guide: How Your Gains and Ambitions Take Shape",
        summary="The 11th lord — planet ruling the sign in your 11th house (Labha Bhava) — directs your gains, income, ambitions, and network. Where it sits across the 12 houses shapes HOW gains arrive. 11th lord in own house or 2nd brings direct accumulation; in 10th brings career-driven gains; in 12th brings foreign/spiritual gains that don't accumulate materially.",
        seo_title="11th Lord in Different Houses: How Your Gains Pattern Reads",
        seo_description="Where your 11th lord (ruler of gains) sits shapes how income arrives — 12 house placements with classical readings.",
        category="Life Questions", hero_image="/static/learn/11th-lord-placement-gains-guide/hero.svg", read_time="8 min", last_updated="2026-07",
        related=("dhana-yoga-wealth-combinations", "2nd-lord-placement-wealth-guide", "7th-lord-placement-marriage-guide"),
        faqs=(
            {"q": "What does 11th lord in 12th house mean?", "a": "Gains flow outward — foreign lands, luxury, spiritual pursuits, charity. Wealth doesn't accumulate materially; goes to experiences. Combined with 2nd lord in accumulating house, this can produce a natural spend-what-you-earn pattern. Best when consciously channelled to meaningful causes."},
            {"q": "Is 11th lord in 6th house good for career?", "a": "For employment yes, for business less. Service industries, competition-based earnings, medicine, law. Recurring income patterns. Enemies-become-clients paradox: obstacles become opportunities."},
            {"q": "What if 11th lord is in own house (11th)?", "a": "Strongest placement. Multiple simultaneous income streams. Networks are prosperous. Group ventures succeed. Elder siblings supportive. Combined with strong 2nd lord = classic multi-source wealth signature."},
            {"q": "How is 11th lord different from 2nd lord?", "a": "2nd lord = wealth accumulated and held (savings, family wealth). 11th lord = wealth as it arrives (income, gains, network profits). Ideally both are strong; if only one is strong, that domain dominates the wealth story (high earner but poor saver = strong 11th + weak 2nd)."},
        ),
        llm_summary=(
            'Keypoints:\n• 11th lord = ruler of Labha Bhava = director of gains, income, ambitions, network, elder siblings\n• Strongest placements: 11th (own), 10th (career-driven), 2nd (accumulating gains), 9th (fortune-blessed)\n• Weakest placements: 8th (hidden/sudden), 12th (outward flow)\n• 6th house placement: employment > business, service-industry wealth\n• Modifiers: Jupiter aspect blesses; Saturn disciplines; Rahu adds sudden/foreign patterns\n• 2L+11L conjunction/exchange = classic Dhana Yoga\n• DIFFERENCE from 2nd lord: 11th = gains ARRIVING, 2nd = wealth ACCUMULATED'
        ),
        qa_status="auto-scanned", qa_date="2026-07-30",
    ),
)


def all_articles() -> tuple[Article, ...]:
    """Every published article, in display order (most recent / important first)."""
    return ARTICLES


def get_article(slug: str) -> Article | None:
    """Look up an article by URL slug. Returns None for unknown slugs."""
    for a in ARTICLES:
        if a.slug == slug:
            return a
    return None


def related_articles(slug: str) -> tuple[Article, ...]:
    """The cross-link targets for an article. Missing slugs are silently skipped."""
    article = get_article(slug)
    if not article:
        return ()
    out = []
    for s in article.related:
        a = get_article(s)
        if a is not None:
            out.append(a)
    return tuple(out)
