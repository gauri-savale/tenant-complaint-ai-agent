"""
nlp/entity_extraction.py
-------------------------
Lightweight, dependency-free information extraction for tenant complaints.

Uses keyword/regex heuristics (a classic, explainable NLP technique) to pull
structured fields out of free-text complaints:
    - category / subcategory keyword hits
    - location mentions (room/area names)
    - emergency keyword hits (used by decision_engine for safety-risk flags)

Keeping this rule-based (rather than another LLM call) is intentional: it
guarantees the system works fully offline and gives explainable "Why?"
reasoning for the evaluator/viva.
"""

import re

# category -> (subcategory, [keywords])
CATEGORY_KEYWORDS = {
    "Plumbing": {
        "Leak": ["leak", "leaking", "dripping", "burst pipe", "water damage"],
        "Clog": ["clogged", "blocked drain", "won't flush", "backed up"],
        "No Water": ["no water", "water not working", "water supply"],
        "Fixture": ["faucet", "tap", "toilet", "shower", "sink"],
    },
    "Electrical": {
        "Power Outage": ["no power", "power outage", "electricity out", "tripping", "trips"],
        "Wiring": ["exposed wire", "sparking", "wire", "wiring", "shock"],
        "Outlet": ["outlet", "socket", "switch not working"],
        "Lighting": ["light not working", "bulb", "flickering light"],
    },
    "Internet": {
        "Outage": ["wifi", "wi-fi", "internet down", "no internet", "connection down"],
        "Speed": ["slow internet", "buffering", "lagging"],
        "Router": ["router", "modem"],
    },
    "Security": {
        "Break-in Attempt": ["break in", "break-in", "intruder", "forced entry", "trying to enter",
                              "force entry", "trying to force", "force his way", "force her way"],
        "Lock Issue": ["lock broken", "key not working", "door won't lock", "lock jammed"],
        "Camera/Access": ["camera", "keypad", "access card", "fob not working"],
        "Suspicious Activity": ["suspicious", "stranger", "trespass"],
    },
    "Noise": {
        "Neighbor Noise": ["loud music", "loud neighbor", "party", "noisy neighbor", "shouting"],
        "Construction Noise": ["construction noise", "drilling noise"],
        "General Disturbance": ["noise", "noisy", "loud"],
    },
    "Cleaning": {
        "Common Area": ["hallway dirty", "trash", "garbage", "common area", "lobby dirty"],
        "Pest": ["cockroach", "roach", "rodent", "mice", "pest", "bugs", "infestation"],
        "Unit Cleaning": ["dirty carpet", "mold", "mildew"],
    },
    "Heating/Cooling": {
        "AC Not Cooling": ["ac not cooling", "ac not working", "air conditioner", "not cooling"],
        "Heater Issue": ["heater", "heating not working", "no heat", "radiator"],
        "Thermostat": ["thermostat"],
    },
    "Appliance": {
        "Refrigerator": ["fridge", "refrigerator"],
        "Washer/Dryer": ["washer", "dryer", "washing machine"],
        "Stove/Oven": ["stove", "oven", "microwave", "dishwasher"],
    },
    "Structural": {
        "Ceiling/Wall": ["ceiling", "crack in wall", "wall crack", "collapsing"],
        "Window/Door": ["window broken", "door broken", "window won't close"],
        "Flooring": ["floor damage", "floor is wet", "tile broken"],
    },
    "Maintenance": {
        "General Repair": ["broken", "not working", "repair needed", "maintenance"],
    },
}

EMERGENCY_KEYWORDS = [
    "fire", "smoke", "gas leak", "gas smell", "exposed electrical wire",
    "exposed wire", "sparking wire", "sparking", "sparks", "spark",
    "major flooding", "flooding", "security breach",
    "break-in", "break in", "intruder", "carbon monoxide", "explosion",
    "electrical fire", "burning smell", "forced entry", "force entry",
    "force his way", "force her way", "trying to force",
]

LOCATION_KEYWORDS = [
    "bedroom", "bathroom", "kitchen", "living room", "ceiling", "hallway",
    "balcony", "garage", "basement", "parking lot", "lobby", "laundry room",
    "closet", "dining room", "entrance", "stairwell", "elevator", "rooftop",
]

NEGATIVE_WORDS = [
    "leak", "broken", "not working", "urgent", "emergency", "unsafe", "danger",
    "angry", "frustrated", "worst", "terrible", "unacceptable", "disgusting",
    "infestation", "no water", "no power", "no heat", "flooding", "smoke",
    "fire", "scared", "worried", "immediately", "asap", "never", "again",
]

POSITIVE_WORDS = [
    "thank", "thanks", "appreciate", "great", "good", "resolved", "fixed",
    "please", "kindly",
]

INTENSITY_WORDS = ["very", "extremely", "severely", "completely", "totally", "immediately", "asap"]


def extract_location(text: str, fallback: str = "") -> str:
    text_l = text.lower()
    for loc in LOCATION_KEYWORDS:
        if loc in text_l:
            return loc.title()
    return fallback or "Unspecified"


def extract_category(text: str):
    """Return (category, subcategory, matched_keywords) using keyword scoring."""
    text_l = text.lower()
    best_category, best_sub, best_score, best_hits = "Other", "General", 0, []

    for category, subcats in CATEGORY_KEYWORDS.items():
        for subcat, keywords in subcats.items():
            hits = [kw for kw in keywords if kw in text_l]
            score = len(hits)
            if score > best_score:
                best_category, best_sub, best_score, best_hits = category, subcat, score, hits

    return best_category, best_sub, best_hits


def find_emergency_keywords(text: str):
    text_l = text.lower()
    return [kw for kw in EMERGENCY_KEYWORDS if kw in text_l]


def count_keyword_hits(text: str, words: list) -> int:
    text_l = text.lower()
    return sum(1 for w in words if w in text_l)


def extract_all(text: str, provided_location: str = "") -> dict:
    category, subcategory, cat_hits = extract_category(text)
    emergency_hits = find_emergency_keywords(text)
    location = extract_location(text, provided_location)
    return {
        "category": category,
        "subcategory": subcategory,
        "category_keywords_matched": cat_hits,
        "emergency_keywords_matched": emergency_hits,
        "location": location,
    }
