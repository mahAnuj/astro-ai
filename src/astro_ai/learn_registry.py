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
