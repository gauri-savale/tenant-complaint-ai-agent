"""
nlp/sentiment.py
-----------------
A small lexicon-based sentiment & urgency analyzer.

We deliberately avoid heavy NLP downloads (e.g. NLTK corpora) so the
project runs fully offline on a fresh laptop. This is a legitimate,
well-understood NLP technique (lexicon/valence scoring) and is easy to
explain in a viva: "we score each word against a curated positive/negative
lexicon and normalize by sentence length."
"""

import re

from nlp.entity_extraction import NEGATIVE_WORDS, POSITIVE_WORDS, INTENSITY_WORDS

EXCLAMATION_WEIGHT = 0.15
CAPS_WORD_WEIGHT = 0.05


def _tokenize(text: str):
    return re.findall(r"[a-zA-Z']+", text.lower())


def analyze_sentiment(text: str) -> dict:
    tokens = _tokenize(text)
    if not tokens:
        return {"label": "Neutral", "score": 0.0}

    neg_hits = sum(1 for w in NEGATIVE_WORDS if w in text.lower())
    pos_hits = sum(1 for w in POSITIVE_WORDS if w in text.lower())

    raw_score = (pos_hits - neg_hits) / max(len(tokens) ** 0.5, 1)

    # Exclamation marks and ALL-CAPS words push sentiment more negative/intense
    exclamations = text.count("!")
    caps_words = sum(1 for w in re.findall(r"[A-Za-z']+", text) if w.isupper() and len(w) > 2)
    raw_score -= exclamations * EXCLAMATION_WEIGHT
    raw_score -= caps_words * CAPS_WORD_WEIGHT

    score = max(-1.0, min(1.0, round(raw_score, 3)))

    if score <= -0.15:
        label = "Negative"
    elif score >= 0.15:
        label = "Positive"
    else:
        label = "Neutral"

    return {"label": label, "score": score}


def analyze_urgency(text: str) -> dict:
    """
    Urgency is distinct from sentiment: a calm-sounding message can still be
    urgent ("Please note the gas smell in unit 4B"). We score based on
    intensity words, emergency keyword density, and punctuation cues.
    """
    text_l = text.lower()
    intensity_hits = sum(1 for w in INTENSITY_WORDS if w in text_l)
    exclamations = text.count("!")
    urgent_phrases = ["right now", "immediately", "asap", "as soon as possible",
                       "urgent", "emergency", "can't wait", "since last night",
                       "getting worse"]
    phrase_hits = sum(1 for p in urgent_phrases if p in text_l)

    raw = intensity_hits * 0.25 + exclamations * 0.2 + phrase_hits * 0.35
    score = max(0.0, min(1.0, round(raw, 3)))

    if score >= 0.5:
        label = "High"
    elif score >= 0.2:
        label = "Medium"
    else:
        label = "Low"

    return {"label": label, "score": score}
