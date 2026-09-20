"""
data/generate_dataset.py
--------------------------
Builds the two CSV datasets used by the project:

  1. data/training_data.csv     — (text, category) pairs used to train the
                                   ML classifier in ml/train_model.py.
  2. data/sample_complaints.csv — a fully-analyzed demo dataset (~150 rows)
                                   used to seed the SQLite database on first
                                   run, so the dashboard/analytics tabs are
                                   never empty.

Both are synthetically generated from templates for this course project
(no real tenant data). Run standalone:

    python data/generate_dataset.py
"""

import csv
import os
import random
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

random.seed(42)

TEMPLATES = {
    "Plumbing": {
        "Leak": [
            "The water has been leaking from the ceiling in my {loc} since last night and the floor is getting wet.",
            "There is a slow drip coming from under the {loc} sink, it's been going on for two days.",
            "Water is leaking from the pipe behind the {loc} wall and it's starting to smell musty.",
            "My {loc} ceiling has a water stain that keeps spreading, I think there's a leak above it.",
        ],
        "Clog": [
            "The {loc} drain is completely clogged and water won't go down at all.",
            "My toilet in the {loc} keeps backing up whenever I flush it.",
            "The kitchen sink is blocked and dirty water is pooling in it.",
        ],
        "Fixture": [
            "The faucet in my {loc} won't turn off and keeps running.",
            "The shower in my {loc} has almost no water pressure anymore.",
        ],
        "No Water": [
            "There has been no water coming out of any tap in my unit since this morning.",
        ],
    },
    "Electrical": {
        "Power Outage": [
            "The power keeps tripping in my {loc} every time I turn on the microwave.",
            "I have had no electricity in half my apartment since yesterday evening.",
        ],
        "Wiring": [
            "There is smoke coming from the electrical socket in my {loc}, it smells like burning.",
            "I can see an exposed electrical wire hanging near the {loc} ceiling, it looks dangerous.",
            "There were sparks coming out of the outlet in the {loc} when I plugged in my charger.",
        ],
        "Outlet": [
            "The outlet in my {loc} is not working and the switch feels warm to touch.",
        ],
        "Lighting": [
            "The light in my {loc} keeps flickering constantly and won't stay on.",
        ],
    },
    "Internet": {
        "Outage": [
            "The Wi-Fi has been down since yesterday and I can't get any internet connection at all.",
            "My internet connection keeps dropping every few minutes, very frustrating for work calls.",
        ],
        "Speed": [
            "The internet is extremely slow and videos keep buffering nonstop.",
        ],
        "Router": [
            "The router in the hallway seems to be broken, none of the lights are on.",
        ],
    },
    "Security": {
        "Break-in Attempt": [
            "Someone tried to enter my apartment at night, I heard the door handle being forced.",
            "I found scratch marks around my front door lock this morning, it looks like a forced entry attempt.",
        ],
        "Lock Issue": [
            "My front door lock is broken and won't latch properly, anyone could just push it open.",
            "The key card for my building entrance stopped working since yesterday.",
        ],
        "Suspicious Activity": [
            "There was a stranger loitering near the parking lot for over an hour, very suspicious.",
        ],
        "Camera/Access": [
            "The security camera in the lobby has been pointed at the wall for a week, seems broken.",
        ],
    },
    "Noise": {
        "Neighbor Noise": [
            "My neighbor has extremely loud music every night and it goes on past midnight.",
            "There is constant shouting and loud parties coming from the unit next door.",
        ],
        "General Disturbance": [
            "There is a lot of noise coming from the {loc} above mine every night, hard to sleep.",
        ],
    },
    "Cleaning": {
        "Common Area": [
            "The hallway trash has not been collected in over a week and it's starting to smell.",
            "The lobby floor has been dirty and sticky for days now.",
        ],
        "Pest": [
            "I found cockroaches in my kitchen again, this is the third time this month.",
            "There are mice in my {loc}, I can hear them scratching at night.",
        ],
        "Unit Cleaning": [
            "There is mold growing in the {loc} corner near the window.",
        ],
    },
    "Heating/Cooling": {
        "AC Not Cooling": [
            "The AC is not cooling at all even though it's running constantly.",
            "My air conditioner in the {loc} is blowing warm air instead of cold.",
        ],
        "Heater Issue": [
            "The heater in my {loc} stopped working and it's freezing in here.",
        ],
        "Thermostat": [
            "The thermostat display is blank and I can't control the temperature anymore.",
        ],
    },
    "Appliance": {
        "Refrigerator": [
            "My refrigerator stopped cooling and all my food is starting to spoil.",
        ],
        "Washer/Dryer": [
            "The washing machine in the laundry room is leaking water everywhere.",
            "The dryer is not heating up so my clothes stay wet after a full cycle.",
        ],
        "Stove/Oven": [
            "The stove burners won't light no matter how many times I try.",
        ],
    },
    "Structural": {
        "Ceiling/Wall": [
            "There is a large crack running across my {loc} wall that seems to be getting bigger.",
            "Part of the ceiling in my {loc} looks like it's sagging and could collapse.",
        ],
        "Window/Door": [
            "My {loc} window is broken and won't close, letting in cold air and rain.",
        ],
        "Flooring": [
            "The floor tiles in my {loc} are cracked and coming loose.",
        ],
    },
    "Maintenance": {
        "General Repair": [
            "The cabinet door in my {loc} fell off its hinges and needs repair.",
            "The doorbell has not been working for weeks now.",
        ],
    },
}

LOCATIONS = ["bedroom", "bathroom", "kitchen", "living room", "hallway", "balcony", "laundry room"]

FIRST_NAMES = ["Alex", "Jordan", "Priya", "Sam", "Maria", "Chen", "Fatima", "Daniel",
               "Aisha", "Liam", "Noor", "Ravi", "Emma", "Yuki", "Carlos", "Grace"]
LAST_INITIALS = list("ABCDEFGHJKLMNPQRSTUVWXYZ")

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
DEPT_MAP = {
    "Plumbing": "Plumbing Maintenance", "Electrical": "Electrical Maintenance",
    "Internet": "IT/Network Support", "Security": "Security Team",
    "Maintenance": "General Maintenance", "Cleaning": "Housekeeping",
    "Noise": "Resident Relations (Noise)", "Heating/Cooling": "HVAC Team",
    "Appliance": "Appliance Repair", "Structural": "Structural Engineering",
    "Other": "Front Office",
}
EMERGENCY_MARKERS = ["fire", "smoke", "gas", "exposed electrical wire", "sparks", "flooding",
                      "forced entry", "forced", "break", "collapse", "sagging"]


def build_training_rows():
    rows = []
    for category, subcats in TEMPLATES.items():
        for subcat, templates in subcats.items():
            for template in templates:
                for loc in LOCATIONS[:4]:
                    text = template.format(loc=loc) if "{loc}" in template else template
                    rows.append({"text": text, "category": category, "subcategory": subcat})
    random.shuffle(rows)
    return rows


def priority_from_text(text, category):
    text_l = text.lower()
    if any(m in text_l for m in EMERGENCY_MARKERS):
        return "Critical", "Emergency/safety keyword detected in description."
    if category in ("Security", "Electrical") or "leak" in text_l or "no water" in text_l or "no power" in text_l:
        return random.choice(["High", "Medium"]), "Elevated-risk category or active damage indicator."
    if category == "Noise":
        return "Low", "Non-hazardous disturbance complaint."
    return random.choice(["Medium", "Low"]), "Standard maintenance request."


def build_seed_rows(n_target=150):
    training_rows = build_training_rows()
    random.shuffle(training_rows)
    rows = []
    base_time = datetime.now() - timedelta(days=45)

    statuses_pool = (["Resolved"] * 5 + ["Closed"] * 2 + ["In Progress"] * 3 +
                      ["Assigned"] * 2 + ["AI Analyzed"] * 2 + ["Waiting for Tenant"] * 1)

    for i in range(n_target):
        template_row = training_rows[i % len(training_rows)]
        category, subcategory = template_row["category"], template_row["subcategory"]
        description = template_row["text"]
        loc_display = random.choice(LOCATIONS).title() if "{loc}" not in description else None
        location = loc_display or random.choice(LOCATIONS).title()

        tenant_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_INITIALS)}."
        tenant_id = f"{tenant_name[:3].upper()}-{1000+i}"
        unit_number = f"{random.randint(1,9)}{random.choice('ABCD')}{random.randint(1,20):02d}"

        submitted = base_time + timedelta(hours=random.randint(0, 45 * 24))
        priority, reason = priority_from_text(description, category)
        status = random.choice(statuses_pool)

        sla_hours = {"Critical": 2, "High": 24, "Medium": 72, "Low": 168}[priority]
        sla_deadline = submitted + timedelta(hours=sla_hours)

        if status in ("Resolved", "Closed"):
            resolved_offset = random.uniform(0.5, sla_hours * 1.3)
            last_updated = submitted + timedelta(hours=resolved_offset)
            resolution = f"{DEPT_MAP[category]} completed the repair and confirmed the issue was resolved."
        else:
            last_updated = submitted + timedelta(hours=random.uniform(0, sla_hours * 0.6))
            resolution = ""

        sentiment = "Negative" if any(w in description.lower() for w in
                    ["broken", "leak", "smoke", "forced", "mold", "cockroach"]) else random.choice(["Neutral", "Negative"])
        urgency = "High" if priority in ("Critical", "High") else random.choice(["Medium", "Low"])
        severity = "High" if priority == "Critical" else ("Medium" if priority == "High" else "Low")
        safety_risk = 1 if priority == "Critical" else 0

        complaint_id = f"CMP-{100000+i:06X}"
        summary = f"{category} issue reported at {location}: {description[:90]}"
        department = DEPT_MAP[category]
        assigned_staff = f"{department.split()[0]} Tech {(i % 2) + 1}"

        rows.append({
            "complaint_id": complaint_id,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "unit_number": unit_number,
            "timestamp": submitted.strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated": last_updated.strftime("%Y-%m-%d %H:%M:%S"),
            "description": description,
            "category": category,
            "subcategory": subcategory,
            "location": location,
            "sentiment": sentiment,
            "severity": severity,
            "urgency": urgency,
            "safety_risk": safety_risk,
            "priority": priority,
            "priority_reason": reason,
            "department": department,
            "assigned_staff": assigned_staff,
            "status": status,
            "sla_deadline": sla_deadline.strftime("%Y-%m-%d %H:%M:%S"),
            "ai_summary": summary,
            "recommended_action": f"Standard {category.lower()} resolution procedure followed by {department}.",
            "resolution": resolution,
            "is_duplicate_of": "",
        })
    return rows


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    training_rows = build_training_rows()
    training_path = os.path.join(out_dir, "training_data.csv")
    with open(training_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "category"])
        writer.writeheader()
        for r in training_rows:
            writer.writerow({"text": r["text"], "category": r["category"]})
    print(f"Wrote {len(training_rows)} rows to {training_path}")

    seed_rows = build_seed_rows(n_target=150)
    seed_path = os.path.join(out_dir, "sample_complaints.csv")
    with open(seed_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(seed_rows[0].keys()))
        writer.writeheader()
        writer.writerows(seed_rows)
    print(f"Wrote {len(seed_rows)} rows to {seed_path}")


if __name__ == "__main__":
    main()
