"""
ml/classifier.py
-----------------
Loads the trained TF-IDF + Logistic Regression category model (if present)
and exposes a single predict_category() function.

Design rule from the project spec: the app must NEVER crash if the model
file doesn't exist (e.g., train_model.py hasn't been run yet). In that
case predict_category() returns None and the caller (nlp/classifier.py)
falls back to the keyword-based rule classifier.
"""

import os

from utils.config import MODEL_DIR

_vectorizer = None
_model = None
_load_attempted = False


def _lazy_load():
    global _vectorizer, _model, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    try:
        import joblib
        vec_path = os.path.join(MODEL_DIR, "category_vectorizer.joblib")
        model_path = os.path.join(MODEL_DIR, "category_model.joblib")
        if os.path.exists(vec_path) and os.path.exists(model_path):
            _vectorizer = joblib.load(vec_path)
            _model = joblib.load(model_path)
    except Exception:
        # Any failure (missing sklearn version mismatch, corrupt file, etc.)
        # simply means we fall back to the rule-based classifier upstream.
        _vectorizer, _model = None, None


def is_available() -> bool:
    _lazy_load()
    return _vectorizer is not None and _model is not None


def predict_category(text: str):
    """Returns (predicted_category, confidence) or (None, 0.0) if unavailable."""
    _lazy_load()
    if not is_available():
        return None, 0.0
    try:
        X = _vectorizer.transform([text])
        proba = _model.predict_proba(X)[0]
        idx = proba.argmax()
        label = _model.classes_[idx]
        confidence = float(proba[idx])
        return label, round(confidence, 3)
    except Exception:
        return None, 0.0
