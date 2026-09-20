"""
nlp/classifier.py
------------------
Hybrid complaint classification: tries the trained ML model
(ml/classifier.py) first; if it's unavailable or low-confidence, falls
back to the explainable keyword rule engine in entity_extraction.py.

This hybrid design is a deliberate reliability choice: the project must
work even before `python ml/train_model.py` has ever been run.
"""

from ml.classifier import is_available as ml_available, predict_category as ml_predict
from nlp.entity_extraction import extract_category

ML_CONFIDENCE_THRESHOLD = 0.35


def classify(text: str) -> dict:
    """
    Returns a dict:
        category, subcategory, method ("ml" | "rule-based"),
        confidence, matched_keywords, explanation
    """
    rule_category, rule_sub, rule_hits = extract_category(text)

    if ml_available():
        ml_category, confidence = ml_predict(text)
        if ml_category and confidence >= ML_CONFIDENCE_THRESHOLD:
            # Use the ML category, but still surface the keyword-derived
            # subcategory when it agrees (nice detail for the "Why?" panel)
            subcategory = rule_sub if rule_category == ml_category else "General"
            return {
                "category": ml_category,
                "subcategory": subcategory,
                "method": "ml",
                "confidence": confidence,
                "matched_keywords": rule_hits,
                "explanation": (
                    f"Predicted by the trained TF-IDF + Logistic Regression model "
                    f"with {confidence*100:.1f}% confidence."
                ),
            }

    # Fallback: rule-based keyword classifier
    confidence = min(1.0, 0.4 + 0.15 * len(rule_hits)) if rule_hits else 0.2
    return {
        "category": rule_category,
        "subcategory": rule_sub,
        "method": "rule-based",
        "confidence": round(confidence, 3),
        "matched_keywords": rule_hits,
        "explanation": (
            f"Matched keyword(s) {rule_hits} for category '{rule_category}'."
            if rule_hits else
            "No strong keyword match found; defaulted to 'Other' for manual triage."
        ),
    }
