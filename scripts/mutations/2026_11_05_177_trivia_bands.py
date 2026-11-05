"""#177: the daily email's Ashtakoot trivia quotes the band edges /matching uses."""

MUTATIONS = [
    ("#177: trivia says 28+ is excellent again while /matching scores 30+ as Uttam",
     "src/astro_ai/trivia.py",
     "Bhagya reads 18+ as acceptable and 30+ as excellent;",
     "Bhagya reads 18+ as acceptable and 28+ as excellent;",
     "test_trivia_quotes_the_band_edges_matching_uses"),
]
