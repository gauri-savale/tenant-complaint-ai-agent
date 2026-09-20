"""
agent/prompts.py
-----------------
Prompt templates used ONLY when LIVE_MODE is active (a valid OPENAI_API_KEY
is configured). These are used purely for natural-language *generation*
(summaries, tenant-facing responses, management insight narratives) —
never for the critical classification/priority/emergency decisions,
which always go through the deterministic rule engine.
"""

SUMMARY_PROMPT = """You are an assistant summarizing a tenant maintenance complaint for a
property manager. Write ONE concise sentence (max 25 words) summarizing the
core issue. Do not add commentary, do not repeat the tenant's exact wording
verbatim, and do not invent details that are not in the complaint.

Complaint: "{description}"
Category: {category}
Location: {location}

Summary:"""

TENANT_RESPONSE_PROMPT = """You are a friendly, professional property-management assistant writing a
short acknowledgement message directly to a tenant who just submitted a
maintenance complaint. Be warm but concise (2-3 sentences). Confirm you've
received it, mention the assigned department, and give the SLA timeframe.
Do not promise anything not provided below.

Tenant name: {tenant_name}
Complaint summary: {summary}
Priority: {priority}
Department: {department}
SLA deadline: {sla_deadline}

Message:"""

RESOLUTION_PROMPT = """You are a property-maintenance expert. Suggest a brief, practical
recommended first action (1-2 sentences) for the maintenance team handling
this complaint. Be specific to the category and description below.

Category: {category}
Subcategory: {subcategory}
Description: "{description}"

Recommended action:"""

MANAGEMENT_INSIGHTS_PROMPT = """You are a property-management analytics assistant. Given the aggregated
statistics below about recent tenant complaints, write a short (4-6 sentence)
management report in plain English highlighting the most important patterns,
risks, and one or two concrete preventive-maintenance recommendations.
Do not invent numbers not present in the data.

Stats:
{stats_block}

Management report:"""
