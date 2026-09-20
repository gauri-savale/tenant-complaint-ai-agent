"""
agent/tools.py
---------------
The individual "tools" available to the AI Agent (agent/agent.py). Each
function here does ONE well-defined job, mirroring a real tool-calling
agent architecture (e.g. LangChain/OpenAI function-calling), but
implemented directly in Python so the whole project runs with zero
external agent-framework dependencies.

Tools:
    classify_complaint
    extract_complaint_information
    detect_emergency
    determine_priority
    assign_department
    estimate_sla
    generate_tenant_response
    search_similar_complaints
    check_duplicate
    recommend_resolution
    update_complaint_status
    generate_summary
    generate_management_insights
"""

import pandas as pd

from agent import prompts
from agent.decision_engine import detect_emergency as _detect_emergency
from agent.decision_engine import determine_priority as _determine_priority
from agent.decision_engine import determine_severity
from database import database as db
from nlp.classifier import classify as _classify
from nlp.entity_extraction import extract_all
from nlp.sentiment import analyze_sentiment, analyze_urgency
from nlp.similarity import detect_duplicate, find_similar_complaints, detect_recurring_issues
from utils.config import DEMO_MODE, OPENAI_API_KEY, OPENAI_MODEL
from utils.helpers import generate_complaint_id, now_iso, sla_deadline, hours_until, is_sla_breached

CATEGORY_TO_DEPARTMENT = {
    "Plumbing": "Plumbing Maintenance",
    "Electrical": "Electrical Maintenance",
    "Internet": "IT/Network Support",
    "Security": "Security Team",
    "Maintenance": "General Maintenance",
    "Cleaning": "Housekeeping",
    "Noise": "Resident Relations (Noise)",
    "Heating/Cooling": "HVAC Team",
    "Appliance": "Appliance Repair",
    "Structural": "Structural Engineering",
    "Other": "Front Office",
}

RESOLUTION_TEMPLATES = {
    "Plumbing": "Dispatch a licensed plumber to inspect and stop the source of the issue; "
                "shut off the local water valve if active leakage is present.",
    "Electrical": "Send a certified electrician immediately; advise tenant to avoid the "
                  "affected outlet/area and not attempt any DIY fix.",
    "Internet": "Have IT support remotely diagnose the router/modem, then dispatch a "
                "technician if the outage persists beyond a remote reset.",
    "Security": "Alert on-site security immediately, review access logs/camera footage, "
                "and arrange a lock/access-point inspection.",
    "Maintenance": "Assign a general maintenance technician to inspect and repair within "
                    "the standard maintenance window.",
    "Cleaning": "Schedule housekeeping/pest control for the affected area and, if pest-related, "
                "arrange a follow-up treatment in 2 weeks.",
    "Noise": "Send a courtesy notice to the source unit and log the incident; escalate to "
             "management if a repeat complaint is filed.",
    "Heating/Cooling": "Dispatch HVAC technician to inspect the unit; check filters, "
                        "refrigerant levels, and thermostat calibration.",
    "Appliance": "Schedule an appliance repair technician; check warranty status before "
                 "ordering replacement parts.",
    "Structural": "Escalate to structural engineering for an on-site safety assessment "
                  "before any cosmetic repair is attempted.",
    "Other": "Route to the front office for manual triage and department assignment.",
}


# ---------------------------------------------------------------------------
# Optional LLM enrichment (LIVE_MODE only) — every call is wrapped so a
# failed/missing API key NEVER crashes the app; callers always get a
# sensible template-based fallback string.
# ---------------------------------------------------------------------------
def _llm_generate(prompt: str, max_tokens: int = 120):
    if DEMO_MODE or not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None  # graceful fallback — caller uses template text instead


# ---------------------------------------------------------------------------
# Tool: classify_complaint
# ---------------------------------------------------------------------------
def classify_complaint(description: str) -> dict:
    return _classify(description)


# ---------------------------------------------------------------------------
# Tool: extract_complaint_information
# ---------------------------------------------------------------------------
def extract_complaint_information(description: str, provided_location: str = "") -> dict:
    entities = extract_all(description, provided_location)
    sentiment = analyze_sentiment(description)
    urgency = analyze_urgency(description)
    severity = determine_severity(description)
    return {
        **entities,
        "sentiment": sentiment,
        "urgency": urgency,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# Tool: detect_emergency
# ---------------------------------------------------------------------------
def detect_emergency(description: str) -> dict:
    return _detect_emergency(description)


# ---------------------------------------------------------------------------
# Tool: determine_priority
# ---------------------------------------------------------------------------
def determine_priority(description: str, category: str, sentiment: dict,
                        urgency: dict, emergency: dict, severity: str) -> dict:
    return _determine_priority(description, category, sentiment, urgency, emergency, severity)


# ---------------------------------------------------------------------------
# Tool: assign_department
# ---------------------------------------------------------------------------
def assign_department(category: str) -> dict:
    department = CATEGORY_TO_DEPARTMENT.get(category, "Front Office")
    try:
        staff = db.get_staff_for_department(department)
    except Exception:
        staff = "Unassigned"
    return {"department": department, "assigned_staff": staff}


# ---------------------------------------------------------------------------
# Tool: estimate_sla
# ---------------------------------------------------------------------------
def estimate_sla(priority: str, submitted_at: str = None) -> dict:
    submitted_at = submitted_at or now_iso()
    deadline = sla_deadline(priority, submitted_at)
    return {"sla_deadline": deadline, "hours_remaining": hours_until(deadline)}


# ---------------------------------------------------------------------------
# Tool: check_duplicate
# ---------------------------------------------------------------------------
def check_duplicate(description: str, location: str) -> dict:
    try:
        history = db.get_all_complaints()
    except Exception:
        history = pd.DataFrame()
    is_dup, match_id, score = detect_duplicate(description, location, history)
    return {"is_duplicate": is_dup, "matched_complaint_id": match_id, "similarity_score": score}


# ---------------------------------------------------------------------------
# Tool: search_similar_complaints
# ---------------------------------------------------------------------------
def search_similar_complaints(description: str, top_k: int = 5) -> pd.DataFrame:
    try:
        history = db.get_all_complaints()
    except Exception:
        history = pd.DataFrame()
    return find_similar_complaints(description, history, top_k=top_k)


# ---------------------------------------------------------------------------
# Tool: recommend_resolution
# ---------------------------------------------------------------------------
def recommend_resolution(category: str, subcategory: str, description: str) -> dict:
    template = RESOLUTION_TEMPLATES.get(category, RESOLUTION_TEMPLATES["Other"])
    llm_text = _llm_generate(
        prompts.RESOLUTION_PROMPT.format(
            category=category, subcategory=subcategory, description=description
        )
    )
    action = llm_text if llm_text else template
    return {"recommended_action": action, "source": "llm" if llm_text else "template"}


# ---------------------------------------------------------------------------
# Tool: generate_summary
# ---------------------------------------------------------------------------
def generate_summary(description: str, category: str, location: str) -> str:
    llm_text = _llm_generate(
        prompts.SUMMARY_PROMPT.format(description=description, category=category, location=location)
    )
    if llm_text:
        return llm_text
    # Template fallback: trim + structure
    trimmed = description.strip()
    if len(trimmed) > 140:
        trimmed = trimmed[:137].rsplit(" ", 1)[0] + "..."
    return f"{category} issue reported at {location}: {trimmed}"


# ---------------------------------------------------------------------------
# Tool: generate_tenant_response
# ---------------------------------------------------------------------------
def generate_tenant_response(tenant_name: str, summary: str, priority: str,
                              department: str, sla_deadline_value: str) -> str:
    llm_text = _llm_generate(
        prompts.TENANT_RESPONSE_PROMPT.format(
            tenant_name=tenant_name, summary=summary, priority=priority,
            department=department, sla_deadline=sla_deadline_value,
        )
    )
    if llm_text:
        return llm_text
    urgency_note = (
        "This has been flagged as a top priority and our team is being notified immediately."
        if priority in ("Critical", "High")
        else "Our team will look into this within the standard service window."
    )
    return (
        f"Hi {tenant_name}, thanks for letting us know. We've logged your complaint and "
        f"routed it to {department}. {urgency_note} Expected resolution by {sla_deadline_value}. "
        f"We'll keep you posted!"
    )


# ---------------------------------------------------------------------------
# Tool: update_complaint_status
# ---------------------------------------------------------------------------
def update_complaint_status(complaint_id: str, new_status: str, note: str = "",
                             resolution: str = None) -> dict:
    record = db.get_complaint(complaint_id)
    if not record:
        return {"success": False, "message": f"Complaint {complaint_id} not found."}

    old_status = record.get("status", "Submitted")
    fields = {"status": new_status}
    if resolution:
        fields["resolution"] = resolution
    db.update_complaint_fields(complaint_id, fields)
    db.log_status_update(complaint_id, old_status, new_status, note)
    return {
        "success": True,
        "message": f"Status updated: {old_status} → {new_status}",
        "complaint_id": complaint_id,
    }


# ---------------------------------------------------------------------------
# Tool: generate_management_insights
# ---------------------------------------------------------------------------
def generate_management_insights(stats: dict) -> str:
    stats_block = "\n".join(f"- {k}: {v}" for k, v in stats.items())
    llm_text = _llm_generate(
        prompts.MANAGEMENT_INSIGHTS_PROMPT.format(stats_block=stats_block), max_tokens=220
    )
    if llm_text:
        return llm_text

    # Template-based management narrative (DEMO_MODE default)
    lines = ["📋 **AI Management Insights (rule-based summary)**\n"]
    if stats.get("top_category"):
        lines.append(
            f"- The most common issue category is **{stats['top_category']}** "
            f"({stats.get('top_category_count', 0)} complaints), suggesting it deserves "
            f"proactive preventive maintenance attention."
        )
    if stats.get("busiest_department"):
        lines.append(
            f"- **{stats['busiest_department']}** currently has the heaviest workload "
            f"({stats.get('busiest_department_count', 0)} open items) and may need "
            f"additional staffing support this week."
        )
    if stats.get("sla_breaches", 0) > 0:
        lines.append(
            f"- ⚠️ {stats['sla_breaches']} complaint(s) have breached their SLA deadline "
            f"and need immediate escalation."
        )
    if stats.get("critical_open", 0) > 0:
        lines.append(
            f"- 🚨 {stats['critical_open']} Critical-priority complaint(s) are still open — "
            f"these should be management's top focus today."
        )
    if stats.get("recurring_locations"):
        lines.append(
            f"- Recurring issues detected at: {stats['recurring_locations']}. Consider a "
            f"targeted preventive maintenance inspection there."
        )
    if len(lines) == 1:
        lines.append("- No significant risk patterns detected in the current data.")
    return "\n".join(lines)


def get_recurring_issues() -> pd.DataFrame:
    try:
        history = db.get_all_complaints()
    except Exception:
        history = pd.DataFrame()
    return detect_recurring_issues(history)
