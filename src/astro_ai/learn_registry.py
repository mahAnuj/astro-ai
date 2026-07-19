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
    title: str            # SEO + page <title> (full descriptive title)
    summary: str          # 1-2 sentences for cards + meta description
    category: str         # 'Doshas' | 'Grahas' | 'Yogas' | 'Concepts' | etc.
    hero_image: str       # absolute URL path to hero SVG/image
    read_time: str        # human-readable estimate, "6 min"
    related: tuple[str, ...] = ()        # related slugs
    faqs: tuple[dict, ...] = field(default_factory=tuple)
    last_updated: str = "2026-06"        # YYYY-MM for SEO freshness signal


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
    ),
    Article(
        slug="sade-sati",
        title="Sade Sati: The 7.5-Year Saturn Lesson, Without the Fear",
        summary="Saturn's transit across your Janma Rashi over 7.5 years — the most-feared transit in Vedic astrology and the most misunderstood. The three phases, what each really teaches, classical remedies, and why most lives are better on the other side.",
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
                "a": "Anu (Rising) — Saturn in 12th from Moon, ~2.5 years. Madhya (Peak) — Saturn in your Moon sign, ~2.5 years and most intense. Uttara (Setting) — Saturn in 2nd from Moon, ~2.5 years of integration. Each phase teaches different lessons; the Madhya phase is the hardest.",
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
    ),
    Article(
        slug="shani-saturn",
        title="Shani (Saturn): The Misunderstood Karmic Teacher",
        summary="The slowest-moving graha, the karmic taskmaster, the most-feared and most-essential planet in your chart. Why Saturn isn't the villain, what strong vs weak Saturn actually means, and the practical way of living that Saturn rewards.",
        category="Grahas",
        hero_image="/static/learn/shani-saturn/hero.svg",
        read_time="10 min",
        related=("sade-sati", "rahu-mahadasha-ketu-antardasha"),
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
    ),
    Article(
        slug="manglik-dosh",
        title="Manglik Dosh: What It Really Means, How to Check, and Remedies",
        summary="A clear, honest guide to Manglik Dosh — what it actually is, the houses that cause it, the cancellation rules most websites skip, and the remedies classical texts recommend.",
        category="Doshas",
        hero_image="/static/learn/manglik-dosh/hero.svg",
        read_time="7 min",
        related=("sade-sati",),
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
