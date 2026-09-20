"""
agent/decision_engine.py
-------------------------
Deterministic, RULE-BASED decisions for the two things that must never be
left to an unpredictable LLM: emergency detection and priority assignment.

The project brief is explicit about this: "If an LLM is used, make sure
deterministic/business rules are also used for critical decisions such as
emergency detection and priority." This module is that safety net — it
runs identically in DEMO_MODE and LIVE_MODE.
"""

from nlp.entity_extraction import find_emergency_keywords, count_keyword_hits, NEGATIVE_WORDS

SEVERITY_HIGH_WORDS = [
    "flooding", "fire", "smoke", "gas", "exposed wire", "sparking", "sparks", "spark",
    "collapsing", "break-in", "intruder", "no water", "no power", "no heat", "force entry",
]
SEVERITY_MEDIUM_WORDS = [
    "leak", "broken", "not working", "blocked", "infestation", "mold",
]


def detect_emergency(text: str) -> dict:
    """
    Rule-based emergency / safety-risk detection.
    Returns dict: is_emergency (bool), matched_keywords (list), reason (str)
    """
    hits = find_emergency_keywords(text)
    is_emergency = len(hits) > 0
    if is_emergency:
        reason = (
            f"Detected high-risk keyword(s) {hits}, which indicate an active "
            f"safety hazard requiring immediate human intervention."
        )
    else:
        reason = "No emergency/safety-hazard keywords detected in the complaint text."
    return {"is_emergency": is_emergency, "matched_keywords": hits, "reason": reason}


def determine_severity(text: str) -> str:
    text_l = text.lower()
    if any(w in text_l for w in SEVERITY_HIGH_WORDS):
        return "High"
    if any(w in text_l for w in SEVERITY_MEDIUM_WORDS):
        return "Medium"
    return "Low"


def determine_priority(text: str, category: str, sentiment: dict, urgency: dict,
                        emergency: dict, severity: str) -> dict:
    """
    Deterministic priority scoring using a weighted rule system (fully
    explainable — no black-box LLM call in the critical path).

    Score components:
      +40  emergency keyword detected
      +20  severity High, +10 severity Medium
      +20  urgency label High, +10 Medium
      +10  strongly negative sentiment (score <= -0.4)
      +5   category is Security or Electrical (statistically higher-risk)
    Thresholds: >=60 Critical, >=35 High, >=15 Medium, else Low
    """
    score = 0
    reasons = []

    if emergency["is_emergency"]:
        score += 40
        reasons.append("active safety/emergency hazard detected (+40)")

    if severity == "High":
        score += 20
        reasons.append("severity assessed as High (+20)")
    elif severity == "Medium":
        score += 10
        reasons.append("severity assessed as Medium (+10)")

    if urgency["label"] == "High":
        score += 20
        reasons.append("urgency language assessed as High (+20)")
    elif urgency["label"] == "Medium":
        score += 10
        reasons.append("urgency language assessed as Medium (+10)")

    if sentiment["score"] <= -0.4:
        score += 10
        reasons.append("strongly negative tenant sentiment (+10)")

    if category in ("Security", "Electrical"):
        score += 5
        reasons.append(f"category '{category}' carries elevated baseline risk (+5)")

    if score >= 60:
        priority = "Critical"
    elif score >= 35:
        priority = "High"
    elif score >= 15:
        priority = "Medium"
    else:
        priority = "Low"

    explanation = (
        f"Priority score = {score}/100 → {priority}. Contributing factors: "
        + "; ".join(reasons) if reasons else
        f"Priority score = {score}/100 → {priority}. No elevated risk factors detected."
    )

    return {"priority": priority, "score": score, "reason": explanation}
