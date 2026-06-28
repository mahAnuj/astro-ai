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
                "a": "It's a real concept in Vedic astrology — Mars in the 1st, 4th, 7th, 8th, or 12th houses is documented in classical texts. Whether its effects play out depends heavily on Mars's strength, conjunctions, and aspects in your specific chart. Many seemingly Manglik people live happily married lives because of cancellation rules most online calculators ignore.",
            },
            {
                "q": "Can a Manglik person marry a non-Manglik?",
                "a": "Classical texts strongly recommend Manglik-with-Manglik matches because the two charts cancel each other out. But cancellation can also happen via other placements — Mars in own sign, aspect from Jupiter, certain nakshatra combinations. A proper Kundli matching analysis matters more than the simple Manglik label.",
            },
            {
                "q": "How can I check Manglik Dosh in my own chart?",
                "a": "Generate your free Janma Kundli on Shubh Bhagya — we flag Manglik Dosh along with its severity and cancellation factors, so you get the full picture, not just a yes/no.",
            },
            {
                "q": "What are the most effective Manglik Dosh remedies?",
                "a": "Classical remedies focus on Mars pacification: fasting on Tuesdays, reciting the Mangal mantra or Hanuman Chalisa, donating red lentils or copper, wearing red coral (only after checking your chart — never blindly). For marriage specifically, the Kumbh Vivah ceremony is mentioned in some traditions as a symbolic pre-marriage.",
            },
            {
                "q": "Does Manglik Dosh weaken with age?",
                "a": "Yes — classical texts say Manglik Dosh significantly reduces after age 28, and is considered minor after 36. The reasoning is that Mars's malefic effects on marriage decline as Saturn matures the individual.",
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
