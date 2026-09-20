"""
tests/test_app.py
-------------------
Test suite for the Tenant Complaint AI Agent project.

Run with:
    python -m pytest tests/test_app.py -v
or:
    python -m unittest tests.test_app -v

These tests exercise the core pipeline directly (database, NLP, decision
engine, agent orchestration) rather than the Gradio UI layer, so they run
fast and don't require a browser or a running server.

Covers the required scenarios: normal complaint, emergency complaint,
high-priority complaint, low-priority complaint, duplicate complaint,
unknown/ambiguous complaint, empty input, very long complaint, multiple
issues in one complaint, angry-sentiment complaint, safety-risk complaint,
different-department routing, existing complaint lookup, status update,
and SLA breach detection.
"""

import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Use a throwaway database file for the whole test run so we never touch
# the real demo database.
os.environ["DB_PATH"] = os.path.join(tempfile.gettempdir(), "test_complaints.db")

from agent import agent, tools  # noqa: E402
from database import database as db  # noqa: E402
from utils.helpers import hours_until, is_sla_breached  # noqa: E402


class TenantComplaintAgentTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(os.environ["DB_PATH"]):
            os.remove(os.environ["DB_PATH"])
        db.init_db()

    # 1. Normal complaint -----------------------------------------------------
    def test_01_normal_complaint(self):
        r = agent.analyze_new_complaint(
            "Normal Tenant", "1A",
            "The kitchen sink is blocked and dirty water is pooling in it.",
        )
        self.assertTrue(r["success"])
        self.assertEqual(r["classification"]["category"], "Plumbing")
        self.assertIn(r["priority"]["priority"], ["Low", "Medium", "High", "Critical"])

    # 2. Emergency complaint ---------------------------------------------------
    def test_02_emergency_complaint(self):
        r = agent.analyze_new_complaint(
            "Emergency Tenant", "2B",
            "There is a gas leak smell in my kitchen and I hear hissing near the stove.",
        )
        self.assertTrue(r["emergency"]["is_emergency"])
        self.assertEqual(r["priority"]["priority"], "Critical")

    # 3. High priority complaint ------------------------------------------------
    def test_03_high_priority_complaint(self):
        r = agent.analyze_new_complaint(
            "High Tenant", "3C",
            "There were sparks coming out of the outlet in the bedroom when I plugged in my charger!",
        )
        self.assertIn(r["priority"]["priority"], ["High", "Critical"])

    # 4. Low priority complaint -------------------------------------------------
    def test_04_low_priority_complaint(self):
        r = agent.analyze_new_complaint(
            "Low Tenant", "4D",
            "The hallway trash has not been collected in a few days.",
        )
        self.assertIn(r["priority"]["priority"], ["Low", "Medium"])

    # 5. Duplicate complaint detection -------------------------------------------
    def test_05_duplicate_complaint(self):
        text = "Water is leaking from my bathroom ceiling and the floor is wet."
        first = agent.analyze_new_complaint("Dup Tenant", "5E", text, provided_location="Bathroom")
        second = agent.analyze_new_complaint("Dup Tenant", "5E", text, provided_location="Bathroom")
        self.assertFalse(first["duplicate"]["is_duplicate"])
        self.assertTrue(second["duplicate"]["is_duplicate"])
        self.assertEqual(second["duplicate"]["matched_complaint_id"], first["complaint_id"])

    # 6. Unknown / ambiguous complaint -------------------------------------------
    def test_06_unknown_complaint(self):
        r = agent.analyze_new_complaint("Vague Tenant", "6F", "Something is weird about my apartment today.")
        self.assertTrue(r["success"])
        self.assertIn(r["classification"]["category"], tools.CATEGORY_TO_DEPARTMENT.keys())

    # 7. Empty input --------------------------------------------------------------
    def test_07_empty_input(self):
        r = agent.analyze_new_complaint("Empty Tenant", "7G", "")
        self.assertFalse(r["success"])
        self.assertIn("error", r)

    # 8. Very long complaint -------------------------------------------------------
    def test_08_very_long_complaint(self):
        long_text = ("The bathroom faucet has been dripping constantly for weeks now and it "
                     "is getting worse every day, I have tried tightening it myself but nothing "
                     "seems to work, the sound keeps me up at night and I am worried about the "
                     "water bill going up, please send someone to fix it as soon as possible. ") * 5
        r = agent.analyze_new_complaint("Long Tenant", "8H", long_text)
        self.assertTrue(r["success"])
        self.assertLessEqual(len(r["summary"]), 200)

    # 9. Multiple issues in one complaint --------------------------------------------
    def test_09_multiple_issues(self):
        r = agent.analyze_new_complaint(
            "Multi Tenant", "9I",
            "The AC is not cooling and also the bathroom sink is leaking badly.",
        )
        self.assertTrue(r["success"])
        self.assertIn(r["classification"]["category"], ["Heating/Cooling", "Plumbing"])

    # 10. Angry sentiment complaint -----------------------------------------------------
    def test_10_angry_sentiment(self):
        r = agent.analyze_new_complaint(
            "Angry Tenant", "10J",
            "This is UNACCEPTABLE!!! The heater has been broken for a WEEK and nobody has "
            "helped me, I am extremely frustrated and this is the worst experience ever!",
        )
        self.assertEqual(r["info"]["sentiment"]["label"], "Negative")

    # 11. Safety risk complaint -----------------------------------------------------------
    def test_11_safety_risk(self):
        r = agent.analyze_new_complaint(
            "Safety Tenant", "11K",
            "Someone tried to force entry into my apartment last night, I'm really scared.",
        )
        self.assertTrue(r["emergency"]["is_emergency"])
        self.assertEqual(r["classification"]["category"], "Security")

    # 12. Different departments route correctly --------------------------------------------
    def test_12_department_routing(self):
        internet = agent.analyze_new_complaint("Dept Tenant", "12L", "The Wi-Fi has been down since yesterday.")
        noise = agent.analyze_new_complaint("Dept Tenant", "12L", "My neighbor has extremely loud music every night.")
        self.assertEqual(internet["routing"]["department"], "IT/Network Support")
        self.assertEqual(noise["routing"]["department"], "Resident Relations (Noise)")

    # 13. Existing complaint lookup -----------------------------------------------------------
    def test_13_existing_complaint_lookup(self):
        r = agent.analyze_new_complaint("Lookup Tenant", "13M", "The dryer is not heating up at all.")
        fetched = db.get_complaint(r["complaint_id"])
        self.assertEqual(fetched["complaint_id"], r["complaint_id"])
        self.assertEqual(fetched["category"], "Appliance")

    # 14. Status update -----------------------------------------------------------------------
    def test_14_status_update(self):
        r = agent.analyze_new_complaint("Status Tenant", "14N", "The stove burners won't light.")
        result = tools.update_complaint_status(r["complaint_id"], "Resolved", note="Fixed", resolution="Replaced igniter.")
        self.assertTrue(result["success"])
        fetched = db.get_complaint(r["complaint_id"])
        self.assertEqual(fetched["status"], "Resolved")
        self.assertEqual(fetched["resolution"], "Replaced igniter.")

    # 15. SLA breach detection ------------------------------------------------------------------
    def test_15_sla_breach_detection(self):
        # A deadline in the past, for an item that's still open, should be flagged as breached.
        past_deadline = "2000-01-01 00:00:00"
        self.assertTrue(is_sla_breached(past_deadline, "In Progress"))
        self.assertFalse(is_sla_breached(past_deadline, "Resolved"))
        self.assertLess(hours_until(past_deadline), 0)

    # --- Bonus: chat agent sanity check --------------------------------------------------------
    def test_16_chat_agent_basic(self):
        result = agent.chat("Is a leaking ceiling urgent?")
        self.assertIn("reply", result)
        self.assertTrue(len(result["reply"]) > 0)
        self.assertTrue(len(result["actions"]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
