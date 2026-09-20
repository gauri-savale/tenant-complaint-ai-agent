"""
nlp/similarity.py
------------------
Semantic-ish similarity search over complaint descriptions using
TF-IDF vectorization + cosine similarity (scikit-learn).

This is the project's "information retrieval" component: it powers
both duplicate-complaint detection (very high similarity to a *recent*
complaint from a similar location) and the "search similar complaints"
agent tool (broader similarity across the whole history).

TF-IDF/cosine is chosen over full sentence-transformer embeddings so the
project has zero heavyweight model downloads and runs instantly on any
laptop — an explicit, defensible design decision to raise in the viva.
"""

from datetime import datetime, timedelta

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DUPLICATE_SIMILARITY_THRESHOLD = 0.55
DUPLICATE_WINDOW_HOURS = 72


def _vectorize(corpus: list):
    if len(corpus) == 0:
        return None, None
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(corpus)
    return vectorizer, matrix


def find_similar_complaints(new_text: str, history_df: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
    """Return the top_k most similar past complaints with a similarity_score column."""
    if history_df is None or history_df.empty:
        return pd.DataFrame()

    corpus = history_df["description"].fillna("").tolist() + [new_text]
    vectorizer, matrix = _vectorize(corpus)
    if matrix is None:
        return pd.DataFrame()

    new_vec = matrix[-1]
    history_vecs = matrix[:-1]
    sims = cosine_similarity(new_vec, history_vecs).flatten()

    result = history_df.copy()
    result["similarity_score"] = sims
    result = result.sort_values("similarity_score", ascending=False).head(top_k)
    return result[result["similarity_score"] > 0.05]


def detect_duplicate(new_text: str, location: str, history_df: pd.DataFrame):
    """
    Look for a near-identical, recently-submitted complaint from the same
    location. Returns (is_duplicate, matched_complaint_id, similarity_score)
    """
    if history_df is None or history_df.empty:
        return False, None, 0.0

    recent = history_df.copy()
    try:
        recent["timestamp_dt"] = pd.to_datetime(recent["timestamp"], errors="coerce")
        cutoff = datetime.now() - timedelta(hours=DUPLICATE_WINDOW_HOURS)
        recent = recent[recent["timestamp_dt"] >= cutoff]
    except Exception:
        pass  # if timestamps are malformed, just compare against everything

    if location and location != "Unspecified" and "location" in recent.columns:
        loc_matches = recent[recent["location"].str.lower() == location.lower()]
        candidates = loc_matches if not loc_matches.empty else recent
    else:
        candidates = recent

    if candidates.empty:
        return False, None, 0.0

    similar = find_similar_complaints(new_text, candidates, top_k=1)
    if similar.empty:
        return False, None, 0.0

    top = similar.iloc[0]
    score = float(top["similarity_score"])
    if score >= DUPLICATE_SIMILARITY_THRESHOLD:
        return True, top["complaint_id"], round(score, 3)
    return False, None, round(score, 3)


def detect_recurring_issues(history_df: pd.DataFrame, min_count: int = 3) -> pd.DataFrame:
    """Group by (category, location) to surface recurring maintenance problems."""
    if history_df is None or history_df.empty:
        return pd.DataFrame()
    grouped = (
        history_df.groupby(["category", "location"])
        .size()
        .reset_index(name="occurrences")
        .sort_values("occurrences", ascending=False)
    )
    return grouped[grouped["occurrences"] >= min_count]
