"""
app.py
------
TenantCare AI — Intelligent Tenant Complaint Management Agent.

Main Gradio entry point. Run with:
    python app.py

Layout note: navigation is a custom hover-expand sidebar (gr.HTML + CSS)
driving 6 real gr.Column sections via a hidden gr.Button per section
(clicked by JS through a stable, self-assigned elem_id) — this keeps all
actual state changes on real, testable Gradio events rather than fragile
internal Gradio Tabs CSS class names.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import gradio as gr
import pandas as pd

from agent import agent, tools
from analytics import analytics
from database import database as db
from ml.classifier import is_available as ml_model_available
from utils.config import CATEGORIES, DEPARTMENTS, PRIORITIES, STATUSES, status_banner
from utils.helpers import hours_until
from utils import ui_helpers as ui
from utils.icons import icon

# ---------------------------------------------------------------------------
# Startup: initialize DB and seed demo data if empty
# ---------------------------------------------------------------------------
db.init_db()
if db.is_empty():
    seed_path = os.path.join(BASE_DIR, "data", "sample_complaints.csv")
    if os.path.exists(seed_path):
        try:
            seed_df = pd.read_csv(seed_path)
            db.seed_from_dataframe(seed_df)
            print(f"Seeded database with {len(seed_df)} demo complaints.")
        except Exception as e:
            print(f"Warning: could not seed demo data ({e}).")

SECTIONS = [
    ("complaint", "Tenant Complaint"),
    ("agent", "AI Agent"),
    ("management", "Complaint Management"),
    ("dashboard", "Analytics Dashboard"),
    ("insights", "AI Insights"),
    ("history", "Complaint History"),
]


# ---------------------------------------------------------------------------
# Tab 1 — Tenant Complaint submission
# ---------------------------------------------------------------------------
def submit_complaint(tenant_name, unit_number, description, location, category):
    if not description or not description.strip():
        return (
            ui.placeholder_card("Please describe your issue before submitting."),
            "", "",
        )

    result = agent.analyze_new_complaint(
        tenant_name=tenant_name or "Anonymous Tenant",
        unit_number=unit_number or "N/A",
        description=description,
        provided_location=location or "",
        provided_category=category or "Auto-detect",
    )

    if not result.get("success"):
        return (
            ui.placeholder_card(result.get("error", "Something went wrong.")),
            "", "",
        )

    card_html = ui.complaint_card_html(result)
    tenant_html = ui.tenant_message_html(result["tenant_response"])
    actions_html = ui.actions_timeline_html(result["actions"])

    return card_html, tenant_html, actions_html


def clear_complaint_form():
    return "", "", "", "Auto-detect", "", ui.placeholder_card(), "", ""


# ---------------------------------------------------------------------------
# Tab 2 — AI Agent chat
# ---------------------------------------------------------------------------
def agent_chat_fn(message, history, tenant_id):
    history = history or []
    result = agent.chat(message, tenant_id=tenant_id.strip() if tenant_id else None)
    actions_block = ""
    if result["actions"]:
        actions_block = "\n\n**Agent actions:**\n" + "\n".join(f"- {a}" for a in result["actions"])
    reply = result["reply"] + actions_block
    history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
    return history, ""


# ---------------------------------------------------------------------------
# Tab 3 — Complaint Management
# ---------------------------------------------------------------------------
def load_complaints(priority_f, category_f, status_f, department_f, search_text):
    display_names = ["Complaint ID", "Tenant ID", "Timestamp", "Category", "Priority",
                      "Status", "Department", "Assigned Staff", "SLA Deadline", "Location"]
    df = db.get_all_complaints()
    if df.empty:
        return pd.DataFrame(columns=display_names)
    if priority_f and priority_f != "All":
        df = df[df["priority"] == priority_f]
    if category_f and category_f != "All":
        df = df[df["category"] == category_f]
    if status_f and status_f != "All":
        df = df[df["status"] == status_f]
    if department_f and department_f != "All":
        df = df[df["department"] == department_f]
    if search_text and search_text.strip():
        s = search_text.strip().lower()
        df = df[df["description"].str.lower().str.contains(s, na=False) |
                df["complaint_id"].str.lower().str.contains(s, na=False)]
    cols = ["complaint_id", "tenant_id", "timestamp", "category", "priority", "status",
            "department", "assigned_staff", "sla_deadline", "location"]
    if df.empty:
        return pd.DataFrame(columns=display_names)
    return df[cols].rename(columns=dict(zip(cols, display_names)))


def do_update_status(complaint_id, new_status, note, resolution):
    if not complaint_id or not complaint_id.strip():
        return "Please enter a complaint ID."
    result = tools.update_complaint_status(complaint_id.strip(), new_status, note, resolution)
    return result["message"]


# ---------------------------------------------------------------------------
# Tab 4 — Analytics Dashboard
# ---------------------------------------------------------------------------
def refresh_dashboard():
    m = analytics.get_summary_metrics()
    metrics_html = ui.stat_grid([
        ui.stat_card("Total Complaints", m["total"], "#6366F1"),
        ui.stat_card("Open", m["open"], "#FBBF24"),
        ui.stat_card("Resolved", m["resolved"], "#34D399"),
        ui.stat_card("Critical", m["critical"], "#F87171"),
        ui.stat_card("Avg Resolution", f"{m['avg_resolution_hours']}h", "#38BDF8"),
        ui.stat_card("SLA Breaches", m["sla_breaches"], "#FB923C"),
    ]) + ui.stat_grid([
        ui.stat_card("Top Category", m["top_category_count"], "#A78BFA", sublabel=m["top_category"] or "N/A"),
        ui.stat_card("Busiest Department", m["busiest_department_count"], "#A78BFA",
                     sublabel=m["busiest_department"] or "N/A"),
    ])
    return (
        metrics_html,
        analytics.chart_by_category(),
        analytics.chart_by_priority(),
        analytics.chart_by_status(),
        analytics.chart_over_time(),
        analytics.chart_department_workload(),
        analytics.chart_resolution_time(),
        analytics.chart_sentiment_distribution(),
    )


# ---------------------------------------------------------------------------
# Tab 5 — AI Insights
# ---------------------------------------------------------------------------
def generate_insights():
    stats = analytics.get_summary_metrics()
    report = tools.generate_management_insights(stats)

    recurring = tools.get_recurring_issues()
    recurring_md = "_No strongly recurring issues detected yet._"
    if not recurring.empty:
        lines = [f"- **{r['category']}** at **{r['location']}** — {r['occurrences']} occurrences"
                 for _, r in recurring.head(8).iterrows()]
        recurring_md = "\n".join(lines)

    df = db.get_all_complaints()
    breach_md = "_No complaints are approaching SLA breach._"
    if not df.empty:
        df = df[~df["status"].isin(["Resolved", "Closed"])].copy()
        if not df.empty:
            df["hours_left"] = df["sla_deadline"].apply(lambda d: hours_until(d) if pd.notna(d) else 999)
            approaching = df[df["hours_left"] <= 6].sort_values("hours_left")
            if not approaching.empty:
                lines = []
                for _, r in approaching.head(10).iterrows():
                    status_text = "BREACHED" if r["hours_left"] < 0 else f"{r['hours_left']:.1f}h left"
                    lines.append(f"- `{r['complaint_id']}` ({r['category']}, {r['priority']}) — {status_text}")
                breach_md = "\n".join(lines)

    return report, recurring_md, breach_md


# ---------------------------------------------------------------------------
# Tab 6 — Complaint History
# ---------------------------------------------------------------------------
def lookup_tenant_history(tenant_id):
    display_names = ["Complaint ID", "Timestamp", "Category", "Priority",
                      "Status", "Department", "SLA Deadline", "Resolution"]
    if not tenant_id or not tenant_id.strip():
        return pd.DataFrame(columns=display_names), "Enter a Tenant ID above and click Search."
    df = db.get_complaints_by_tenant(tenant_id.strip())
    cols = ["complaint_id", "timestamp", "category", "priority", "status",
            "department", "sla_deadline", "resolution"]
    if df.empty:
        return pd.DataFrame(columns=display_names), f"No complaints found for tenant `{tenant_id}`."
    return df[cols].rename(columns=dict(zip(cols, display_names))), f"Found {len(df)} complaint(s) for tenant `{tenant_id}`."


# ---------------------------------------------------------------------------
# Custom sidebar navigation (hover-expand) — CSS + HTML
# ---------------------------------------------------------------------------
def _build_sidebar_html() -> str:
    items = []
    for i, (icon_key, label) in enumerate(SECTIONS):
        active_class = " active" if i == 0 else ""
        items.append(f"""
        <div class="tc-nav-item{active_class}"
             onclick="
                document.querySelectorAll('.tc-nav-item').forEach(function(e){{e.classList.remove('active');}});
                this.classList.add('active');
                var el = document.getElementById('tc-navbtn-{i}');
                if (el) {{ var b = el.querySelector('button') || el; b.click(); }}
             ">
            <span class="tc-nav-icon">{icon(icon_key, 18)}</span>
            <span class="tc-nav-label">{label}</span>
        </div>""")
    return f"""
    <div id="tc-sidebar">
        <div class="tc-sidebar-brand">
            <span class="tc-brand-mark">T</span>
            <span class="tc-nav-label tc-brand-label">TenantCare AI</span>
        </div>
        <div class="tc-sidebar-items">
            {''.join(items)}
        </div>
    </div>
    """


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ---- Restrained professional dark theme ---- */
:root.dark, :root .dark {
    --body-background-fill: #131316;
    --background-fill-primary: #131316;
    --background-fill-secondary: #18181C;
    --block-background-fill: #1C1C21;
    --border-color-primary: #2A2A30;
    --border-color-accent: #34343C;
    --body-text-color: #E4E4E7;
    --body-text-color-subdued: #8B8B93;
    --color-accent: #6366F1;
    --color-accent-soft: rgba(99,102,241,0.08);
    --input-background-fill: #141417;
    --panel-background-fill: #18181C;
    --button-primary-background-fill: #6366F1;
    --button-primary-background-fill-hover: #7274F2;
    --button-primary-text-color: #FFFFFF;
    --button-secondary-background-fill: #202024;
    --button-secondary-text-color: #E4E4E7;
    --button-secondary-border-color: #2E2E34;
    --block-radius: 8px;
    --button-large-radius: 6px;
    --input-radius: 6px;

    /* Neutralize Gradio's default solid-color field labels (this is what was
       rendering every field label as a loud filled indigo block) */
    --block-label-background-fill: transparent;
    --block-label-text-color: #9A9AA2;
    --block-label-border-width: 0px;
    --block-label-text-weight: 600;
    --block-label-text-size: 0.8rem;
    --block-label-margin: 0px;
    --block-label-padding: 0px 0px 6px 0px;
    --block-title-background-fill: transparent;
    --block-title-text-color: #9A9AA2;

    /* Tighten overall spacing rhythm */
    --layout-gap: 10px;
    --block-padding: 12px 14px;
    --input-padding: 9px 12px;
    --form-gap-width: 0px;
}

html, body { margin: 0 !important; }
body, .gradio-container { background: #131316 !important; }

/* Reserve the collapsed sidebar's width at the document level, then let the
   content container center itself within whatever space remains — this way
   the whitespace is symmetric around the content instead of anchored to one
   side, regardless of screen width. */
body { padding-left: 64px !important; box-sizing: border-box !important; }

.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
    padding: 20px 24px !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    box-sizing: border-box !important;
}
footer {visibility: hidden}

.tc-icon svg { width: 100%; height: 100%; }

/* ---- Hover-expand sidebar ---- */
#tc-sidebar {
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: 64px;
    background: #17171B;
    border-right: 1px solid #26262C;
    z-index: 10000;
    overflow: hidden;
    transition: width 0.18s ease;
    display: flex;
    flex-direction: column;
    padding-top: 16px;
}
#tc-sidebar:hover { width: 220px; box-shadow: 8px 0 28px rgba(0,0,0,0.35); }

.tc-sidebar-brand {
    display: flex; align-items: center;
    padding: 4px 20px 16px 21px;
    margin-bottom: 6px;
    white-space: nowrap;
}
.tc-brand-mark {
    width: 22px; height: 22px; flex-shrink: 0;
    background: #6366F1; color: white; border-radius: 5px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.75rem;
}
.tc-brand-label { font-weight: 700; font-size: 0.92rem; color: #E4E4E7; letter-spacing: -0.01em; }

.tc-sidebar-items { display: flex; flex-direction: column; gap: 1px; padding: 4px 8px; }

.tc-nav-item {
    display: flex; align-items: center;
    padding: 9px 11px;
    border-radius: 6px;
    cursor: pointer;
    white-space: nowrap;
    color: #8B8B93;
    border-left: 2px solid transparent;
    transition: background 0.12s ease, color 0.12s ease;
}
.tc-nav-item:hover { background: #202024; color: #D4D4D8; }
.tc-nav-item.active { color: #C7CAFB; border-left: 2px solid #6366F1; background: rgba(99,102,241,0.08); }

.tc-nav-icon { width: 18px; height: 18px; flex-shrink: 0; opacity: 0.9; }
.tc-nav-label {
    margin-left: 13px; font-size: 0.85rem; font-weight: 500;
    max-width: 0; opacity: 0; overflow: hidden; transition: all 0.16s ease;
}
#tc-sidebar:hover .tc-nav-label { max-width: 160px; opacity: 1; }

.tc-hidden-trigger { display: none !important; }

/* ---- Slim top bar ---- */
#tc-topbar {
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid #26262C;
    padding: 0 0 14px 0; margin-bottom: 18px;
}
#tc-topbar h1 { margin: 0; font-size: 1.02rem; font-weight: 700; color: #E4E4E7; letter-spacing: -0.01em; }
#tc-topbar .tc-badges { display: flex; gap: 8px; }
#tc-topbar .tc-pill {
    background: #1C1C21; border: 1px solid #2A2A30;
    color: #A1A1AA; border-radius: 5px; padding: 4px 10px;
    font-size: 0.72rem; font-weight: 500;
}
#tc-topbar .tc-pill.on { color: #86EFAC; border-color: rgba(52,211,153,0.3); }

button.primary:hover { filter: brightness(1.08); }

.tc-section-title {
    font-weight: 700 !important;
    font-size: 0.96rem !important;
    color: #E4E4E7 !important;
    margin: 0 0 2px 0 !important;
}
.tc-section-sub {
    color: #8B8B93 !important;
    font-size: 0.81rem !important;
    margin-bottom: 12px !important;
}

.gr-group, .form { border-radius: 8px !important; }
.gap { gap: 8px !important; }
table { border-radius: 8px !important; overflow: hidden !important; }

/* Let the chat panel be dragged taller/shorter, like a resizable textarea,
   instead of sitting at a fixed height whether empty or full. */
.tc-chatbot { resize: vertical; overflow: auto !important; min-height: 160px; max-height: 720px; }
"""

FORCE_DARK_JS = """
() => {
    document.documentElement.classList.add('dark');
}
"""


def top_bar_html() -> str:
    model_on = ml_model_available()
    mode_label = "Demo Mode" if not status_banner().startswith("🔌") else "Live Mode"
    return f"""
    <div id="tc-topbar">
        <h1>TenantCare AI</h1>
        <div class="tc-badges">
            <span class="tc-pill">{mode_label}</span>
            <span class="tc-pill {'on' if model_on else ''}">
                {"ML model loaded" if model_on else "ML model not trained"}
            </span>
        </div>
    </div>
    """


with gr.Blocks(title="TenantCare AI") as demo:
    gr.HTML(_build_sidebar_html())

    # Hidden real buttons the sidebar's JS clicks to switch sections
    nav_buttons = []
    with gr.Row(elem_classes=["tc-hidden-trigger"]):
        for i, _ in enumerate(SECTIONS):
            nav_buttons.append(gr.Button(str(i), elem_id=f"tc-navbtn-{i}"))

    gr.HTML(top_bar_html())

    sections = []

    # --- SECTION 0: Tenant Complaint ------------------------------------------
    with gr.Column(visible=True) as sec0:
        gr.Markdown(
            '<div class="tc-section-title">Submit a new complaint</div>'
            '<div class="tc-section-sub">Describe the issue in your own words — '
            'the AI agent handles the rest.</div>'
        )
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Group():
                    t_name = gr.Textbox(label="Tenant Name", placeholder="e.g. Priya Sharma")
                    t_unit = gr.Textbox(label="Apartment / Unit Number", placeholder="e.g. 4B")
                    t_location = gr.Textbox(label="Location (optional — auto-detected if left blank)",
                                             placeholder="e.g. Bedroom")
                    t_category = gr.Dropdown(
                        label="Category (optional — auto-detected if left as Auto-detect)",
                        choices=["Auto-detect"] + CATEGORIES, value="Auto-detect",
                    )
                    t_description = gr.Textbox(
                        label="Describe your issue", lines=5,
                        placeholder="e.g. The water has been leaking from the ceiling in my "
                                    "bedroom since last night and the floor is getting wet.",
                    )
                with gr.Row():
                    t_submit = gr.Button("Submit Complaint", variant="primary")
                    t_clear = gr.Button("Clear")
            with gr.Column(scale=1):
                t_card = gr.HTML(ui.placeholder_card())
                t_tenant_msg = gr.HTML()
                t_actions = gr.HTML()

        t_submit.click(
            submit_complaint,
            inputs=[t_name, t_unit, t_description, t_location, t_category],
            outputs=[t_card, t_tenant_msg, t_actions],
        )
        t_clear.click(
            clear_complaint_form,
            outputs=[t_name, t_unit, t_location, t_category, t_description,
                     t_card, t_tenant_msg, t_actions],
        )
    sections.append(sec0)

    # --- SECTION 1: AI Agent ---------------------------------------------------
    with gr.Column(visible=False) as sec1:
        gr.Markdown(
            '<div class="tc-section-title">Ask the agent about complaints, urgency, or resolutions</div>'
            '<div class="tc-section-sub">Try: "Is a leaking ceiling urgent?", '
            '"Show me similar complaints about noise", "What should I do about a broken AC?", '
            'or paste a complaint ID like <code>CMP-ABC123</code>.</div>'
        )
        chat_tenant_id = gr.Textbox(label="Your Tenant ID (optional, needed for 'my complaint history')",
                                     placeholder="e.g. PRI-1000")
        chat_input = gr.Textbox(label="Your message", placeholder="Type your question and press Enter...")
        chatbot = gr.Chatbot(height=260, show_label=False, elem_classes=["tc-chatbot"])
        chat_input.submit(agent_chat_fn, inputs=[chat_input, chatbot, chat_tenant_id],
                           outputs=[chatbot, chat_input])
    sections.append(sec1)

    # --- SECTION 2: Complaint Management ---------------------------------------
    with gr.Column(visible=False) as sec2:
        gr.Markdown('<div class="tc-section-title">Filter, search, and update complaints</div>')
        with gr.Group():
            with gr.Row():
                f_priority = gr.Dropdown(["All"] + PRIORITIES, value="All", label="Priority")
                f_category = gr.Dropdown(["All"] + CATEGORIES, value="All", label="Category")
                f_status = gr.Dropdown(["All"] + STATUSES, value="All", label="Status")
                f_department = gr.Dropdown(["All"] + DEPARTMENTS, value="All", label="Department")
            f_search = gr.Textbox(label="Search (description or complaint ID)")
            f_load = gr.Button("Load / Refresh", variant="primary")
        f_table = gr.Dataframe(
            interactive=False, wrap=True,
            headers=["Complaint ID", "Tenant ID", "Timestamp", "Category", "Priority",
                     "Status", "Department", "Assigned Staff", "SLA Deadline", "Location"],
            row_count=(0, "dynamic"),
        )

        f_load.click(load_complaints,
                      inputs=[f_priority, f_category, f_status, f_department, f_search],
                      outputs=f_table)

        gr.Markdown('<div class="tc-section-title" style="margin-top:24px;">Update a complaint</div>')
        with gr.Group():
            with gr.Row():
                u_id = gr.Textbox(label="Complaint ID", placeholder="e.g. CMP-ABC123")
                u_status = gr.Dropdown(STATUSES, value="In Progress", label="New Status")
            u_note = gr.Textbox(label="Update note (optional)")
            u_resolution = gr.Textbox(label="Resolution details (optional, shown if resolving)")
            u_button = gr.Button("Update Status", variant="primary")
        u_output = gr.Markdown()
        u_button.click(do_update_status, inputs=[u_id, u_status, u_note, u_resolution], outputs=u_output)
    sections.append(sec2)

    # --- SECTION 3: Analytics Dashboard -----------------------------------------
    with gr.Column(visible=False) as sec3:
        with gr.Row():
            gr.Markdown('<div class="tc-section-title">Live metrics</div>')
            d_refresh = gr.Button("Refresh", variant="primary", scale=0)
        d_metrics = gr.HTML()
        with gr.Row():
            d_cat_chart = gr.Plot(label="By Category")
            d_pri_chart = gr.Plot(label="By Priority")
        with gr.Row():
            d_status_chart = gr.Plot(label="By Status")
            d_time_chart = gr.Plot(label="Over Time")
        with gr.Row():
            d_dept_chart = gr.Plot(label="Department Workload")
            d_resolution_chart = gr.Plot(label="Avg Resolution Time")
        d_sentiment_chart = gr.Plot(label="Sentiment Distribution")

        d_refresh.click(
            refresh_dashboard,
            outputs=[d_metrics, d_cat_chart, d_pri_chart, d_status_chart,
                     d_time_chart, d_dept_chart, d_resolution_chart, d_sentiment_chart],
        )
        demo.load(
            refresh_dashboard,
            outputs=[d_metrics, d_cat_chart, d_pri_chart, d_status_chart,
                     d_time_chart, d_dept_chart, d_resolution_chart, d_sentiment_chart],
        )
    sections.append(sec3)

    # --- SECTION 4: AI Insights ---------------------------------------------------
    with gr.Column(visible=False) as sec4:
        gr.Markdown('<div class="tc-section-title">AI-generated management report</div>')
        i_button = gr.Button("Generate Management Insights", variant="primary")
        i_report = gr.Markdown()
        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Recurring Issues")
                i_recurring = gr.Markdown()
            with gr.Column():
                gr.Markdown("#### Approaching / Breached SLA")
                i_breach = gr.Markdown()
        i_button.click(generate_insights, outputs=[i_report, i_recurring, i_breach])
    sections.append(sec4)

    # --- SECTION 5: Complaint History -----------------------------------------------
    with gr.Column(visible=False) as sec5:
        gr.Markdown('<div class="tc-section-title">Look up your complaint history</div>')
        with gr.Row():
            h_tenant_id = gr.Textbox(label="Tenant ID", placeholder="e.g. PRI-1000", scale=3)
            h_button = gr.Button("Search", variant="primary", scale=1)
        h_status = gr.Markdown()
        h_table = gr.Dataframe(
            interactive=False, wrap=True,
            headers=["Complaint ID", "Timestamp", "Category", "Priority",
                     "Status", "Department", "SLA Deadline", "Resolution"],
            row_count=(0, "dynamic"),
        )
        h_button.click(lookup_tenant_history, inputs=h_tenant_id, outputs=[h_table, h_status])
    sections.append(sec5)

    gr.Markdown(
        "---\n*TenantCare AI — CSE Major Project: NLP + Machine Learning + Agentic AI + "
        "Database + Analytics, built with Gradio.*"
    )

    # Wire each hidden nav button to show only its section
    for idx, btn in enumerate(nav_buttons):
        def _make_switch(target_idx):
            def _switch():
                return [gr.update(visible=(j == target_idx)) for j in range(len(sections))]
            return _switch
        btn.click(_make_switch(idx), outputs=sections)


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="slate", neutral_hue="slate"),
        css=CUSTOM_CSS,
        js=FORCE_DARK_JS,
    )
