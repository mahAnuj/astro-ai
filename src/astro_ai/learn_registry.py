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
