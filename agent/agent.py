"""
agent/agent.py
---------------
The AI Agent orchestrator. Two entry points:

    analyze_new_complaint(...)  — runs the full tool pipeline on a freshly
                                   submitted complaint (Tab 1), logging every
                                   tool it invokes and why.

    chat(query, tenant_id=None) — a lightweight tool-calling chat agent
                                   (Tab 2) that inspects the user's natural-
                                   language question and DECIDES which
                                   subset of tools are relevant, rather than
                                   always running the whole pipeline. This is
                                   the part that makes it an "agent" rather
                                   than a single prompt-to-LLM chatbot.
"""

import re

import pandas as pd

from agent import tools
from database import database as db
from utils.helpers import generate_complaint_id, generate_tenant_id, now_iso


class AgentAction:
    """A single logged step, shown to the user as an 'Agent Actions' checklist."""
    def __init__(self, label: str, detail: str = ""):
        self.label = label
        self.detail = detail

    def __str__(self):
        return f"✓ {self.label}" + (f" — {self.detail}" if self.detail else "")


# ---------------------------------------------------------------------------
# Full pipeline for a NEW complaint (Tab 1: Tenant Complaint submission)
# ---------------------------------------------------------------------------
def analyze_new_complaint(tenant_name: str, unit_number: str, description: str,
                           provided_location: str = "", provided_category: str = "",
                           tenant_id: str = None) -> dict:
    actions = []
    description = (description or "").strip()

    if not description:
        return {"success": False, "error": "Please describe the issue before submitting."}

    tenant_id = tenant_id or generate_tenant_id(tenant_name or "Tenant")
    db.upsert_tenant(tenant_id, tenant_name or "Unknown Tenant", unit_number or "N/A")
    actions.append(AgentAction("Registered/looked up tenant record", tenant_id))

    # 1. Extract structured info (entities, sentiment, urgency, severity)
    info = tools.extract_complaint_information(description, provided_location)
    actions.append(AgentAction("Extracted complaint information",
                                f"location={info['location']}, sentiment={info['sentiment']['label']}, "
                                f"urgency={info['urgency']['label']}, severity={info['severity']}"))

    # 2. Classify category (unless the tenant explicitly picked one)
    if provided_category and provided_category != "Auto-detect":
        classification = {"category": provided_category, "subcategory": info["subcategory"],
                           "method": "tenant-selected", "confidence": 1.0,
                           "matched_keywords": info["category_keywords_matched"],
                           "explanation": "Category explicitly selected by tenant."}
    else:
        classification = tools.classify_complaint(description)
    actions.append(AgentAction("Classified complaint",
                                f"{classification['category']} / {classification['subcategory']} "
                                f"({classification['method']}, {classification['confidence']*100:.0f}% confidence)"))

    # 3. Emergency detection (always run — safety-critical)
    emergency = tools.detect_emergency(description)
    if emergency["is_emergency"]:
        actions.append(AgentAction("Detected safety/emergency risk", str(emergency["matched_keywords"])))
    else:
        actions.append(AgentAction("Checked for safety/emergency risk", "none detected"))

    # 4. Priority determination (deterministic rule engine)
    priority_result = tools.determine_priority(
        description, classification["category"], info["sentiment"], info["urgency"],
        emergency, info["severity"],
    )
    actions.append(AgentAction("Determined priority", priority_result["priority"]))

    # 5. Duplicate check
    dup = tools.check_duplicate(description, info["location"])
    if dup["is_duplicate"]:
        actions.append(AgentAction("Possible duplicate detected",
                                    f"matches {dup['matched_complaint_id']} "
                                    f"(similarity {dup['similarity_score']})"))
    else:
        actions.append(AgentAction("Checked for duplicate complaints", "none found"))

    # 6. Department + staff assignment
    routing = tools.assign_department(classification["category"])
    actions.append(AgentAction("Assigned department", f"{routing['department']} → {routing['assigned_staff']}"))

    # 7. SLA estimation
    submitted_at = now_iso()
    sla = tools.estimate_sla(priority_result["priority"], submitted_at)
    actions.append(AgentAction("Estimated SLA deadline", sla["sla_deadline"]))

    # 8. Resolution recommendation
    resolution = tools.recommend_resolution(classification["category"], classification["subcategory"], description)
    actions.append(AgentAction("Generated resolution recommendation", resolution["source"]))

    # 9. Summary generation
    summary = tools.generate_summary(description, classification["category"], info["location"])
    actions.append(AgentAction("Generated AI summary"))

    # 10. Tenant-facing response
    tenant_response = tools.generate_tenant_response(
        tenant_name or "there", summary, priority_result["priority"], routing["department"], sla["sla_deadline"]
    )
    actions.append(AgentAction("Generated tenant acknowledgement message"))

    complaint_id = generate_complaint_id()
    status = "AI Analyzed"

    record = {
        "complaint_id": complaint_id,
        "tenant_id": tenant_id,
        "timestamp": submitted_at,
        "description": description,
        "category": classification["category"],
        "subcategory": classification["subcategory"],
        "location": info["location"],
        "sentiment": info["sentiment"]["label"],
        "severity": info["severity"],
        "urgency": info["urgency"]["label"],
        "safety_risk": 1 if emergency["is_emergency"] else 0,
        "priority": priority_result["priority"],
        "priority_reason": priority_result["reason"],
        "department": routing["department"],
        "assigned_staff": routing["assigned_staff"],
        "status": status,
        "sla_deadline": sla["sla_deadline"],
        "ai_summary": summary,
        "recommended_action": resolution["recommended_action"],
        "resolution": "",
        "is_duplicate_of": dup["matched_complaint_id"] or "",
        "last_updated": submitted_at,
    }
    db.insert_complaint(record)
    db.log_status_update(complaint_id, "New", status, "Auto-analyzed by AI agent on submission")
    actions.append(AgentAction("Saved complaint to database", complaint_id))

    return {
        "success": True,
        "complaint_id": complaint_id,
        "tenant_id": tenant_id,
        "classification": classification,
        "info": info,
        "emergency": emergency,
        "priority": priority_result,
        "duplicate": dup,
        "routing": routing,
        "sla": sla,
        "resolution": resolution,
        "summary": summary,
        "tenant_response": tenant_response,
        "actions": [str(a) for a in actions],
    }


# ---------------------------------------------------------------------------
# Chat agent (Tab 2) — decides which tools to run based on the question
# ---------------------------------------------------------------------------
def chat(query: str, tenant_id: str = None) -> dict:
    query = (query or "").strip()
    actions = []
    if not query:
        return {"reply": "Ask me about a complaint, e.g. 'Is a leaking ceiling urgent?' "
                          "or 'Show me similar complaints about noise.'", "actions": []}

    q_lower = query.lower()
    reply_parts = []

    looks_up_id = re.search(r"\b(CMP-[A-Z0-9]{4,8})\b", query.upper())
    wants_similar = any(p in q_lower for p in ["similar", "related complaints", "duplicate"])
    wants_status = any(p in q_lower for p in ["status of", "what is the status", "where is my complaint"])
    wants_history = any(p in q_lower for p in ["my complaints", "complaint history", "past complaints"])
    wants_insight = any(p in q_lower for p in ["overloaded", "most common", "trend", "insight", "recurring"])

    # --- Direct complaint ID lookup -----------------------------------------
    if looks_up_id:
        cid = looks_up_id.group(1)
        record = db.get_complaint(cid)
        actions.append(str(AgentAction("Looked up complaint by ID", cid)))
        if record:
            reply_parts.append(
                f"**{cid}** — {record['category']}/{record['subcategory']} at {record['location']}.\n"
                f"Status: **{record['status']}** | Priority: **{record['priority']}** | "
                f"SLA: {record['sla_deadline']}\n"
                f"Summary: {record['ai_summary']}\n"
                f"Recommended action: {record['recommended_action']}"
            )
        else:
            reply_parts.append(f"I couldn't find a complaint with ID {cid}.")
        return {"reply": "\n\n".join(reply_parts), "actions": actions}

    # --- Tenant history ------------------------------------------------------
    if wants_history and tenant_id:
        df = db.get_complaints_by_tenant(tenant_id)
        actions.append(str(AgentAction("Retrieved tenant complaint history", tenant_id)))
        if df.empty:
            reply_parts.append("You don't have any complaints on file yet.")
        else:
            lines = [f"- {r['complaint_id']}: {r['category']} ({r['status']}, {r['priority']})"
                     for _, r in df.head(10).iterrows()]
            reply_parts.append("Here's your recent complaint history:\n" + "\n".join(lines))
        return {"reply": "\n\n".join(reply_parts), "actions": actions}

    # --- Management-style insight questions -----------------------------------
    if wants_insight:
        recurring = tools.get_recurring_issues()
        actions.append(str(AgentAction("Checked complaint database for recurring issues")))
        if recurring.empty:
            reply_parts.append("No strongly recurring issues detected yet in the current data.")
        else:
            lines = [f"- {r['category']} at {r['location']}: {r['occurrences']} occurrences"
                     for _, r in recurring.head(5).iterrows()]
            reply_parts.append("Recurring issues worth management attention:\n" + "\n".join(lines))
        return {"reply": "\n\n".join(reply_parts), "actions": actions}

    # --- Default: treat the message as a NEW complaint-like question ---------
    # e.g. "What should I do about a leaking ceiling?" / "Is this urgent?"
    classification = tools.classify_complaint(query)
    actions.append(str(AgentAction("Classified complaint", classification["category"])))

    emergency = tools.detect_emergency(query)
    actions.append(str(AgentAction("Detected safety risk" if emergency["is_emergency"] else "Checked for safety risk")))

    info = tools.extract_complaint_information(query)

    priority_result = tools.determine_priority(
        query, classification["category"], info["sentiment"], info["urgency"], emergency, info["severity"]
    )
    actions.append(str(AgentAction("Assessed priority", priority_result["priority"])))

    routing = tools.assign_department(classification["category"])
    actions.append(str(AgentAction("Identified responsible department", routing["department"])))

    if wants_similar:
        similar = tools.search_similar_complaints(query, top_k=3)
        actions.append(str(AgentAction("Searched similar historical complaints", f"{len(similar)} found")))
        if not similar.empty:
            lines = [f"- {r['complaint_id']} ({r['category']}, similarity {r['similarity_score']:.2f})"
                     for _, r in similar.iterrows()]
            reply_parts.append("Similar past complaints:\n" + "\n".join(lines))
        else:
            reply_parts.append("I didn't find closely similar past complaints.")

    resolution = tools.recommend_resolution(classification["category"], classification["subcategory"], query)
    actions.append(str(AgentAction("Generated resolution recommendation")))

    urgency_word = "urgent" if priority_result["priority"] in ("Critical", "High") else "not especially urgent"
    reply_parts.insert(0,
        f"This looks like a **{classification['category']}** issue and is **{urgency_word}** "
        f"(priority: {priority_result['priority']}). It would typically be routed to "
        f"**{routing['department']}**.\n\n**Recommended action:** {resolution['recommended_action']}"
        + (f"\n\n⚠️ Safety concern detected: {emergency['reason']}" if emergency["is_emergency"] else "")
    )

    return {"reply": "\n\n".join(reply_parts), "actions": actions}
