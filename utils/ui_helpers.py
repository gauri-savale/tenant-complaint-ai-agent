"""
utils/ui_helpers.py
--------------------
HTML-rendering helpers for a restrained, professional dark UI: small
colored status TAGS (not bubbly emoji pills) and clean cards. Colors are
used sparingly and consistently — kept in sync with analytics.py's chart
palette and app.py's CSS tokens.
"""

from utils.icons import icon

# Surface tokens — keep in sync with app.py's CUSTOM_CSS and analytics.py's PAPER_BG
SURFACE = "#1C1C21"
SURFACE_ALT = "#18181C"
BORDER = "#2A2A30"
TEXT = "#E4E4E7"
TEXT_MUTED = "#8B8B93"
ACCENT = "#6366F1"
ACCENT_TEXT = "#A5A9F5"

# (bg, text, dot) — flat, low-saturation tags rather than glowing pastel pills
PRIORITY_COLORS = {
    "Critical": ("rgba(248,113,113,0.10)", "#F87171"),
    "High":     ("rgba(251,146,60,0.10)",  "#FB923C"),
    "Medium":   ("rgba(251,191,36,0.10)",  "#FBBF24"),
    "Low":      ("rgba(52,211,153,0.10)",  "#34D399"),
}

STATUS_COLORS = {
    "Submitted":          ("rgba(129,140,248,0.10)", "#818CF8"),
    "AI Analyzed":        ("rgba(99,102,241,0.10)",  "#8B8FEA"),
    "Assigned":           ("rgba(56,189,248,0.10)",  "#38BDF8"),
    "In Progress":        ("rgba(251,191,36,0.10)",  "#FBBF24"),
    "Waiting for Tenant":  ("rgba(251,146,60,0.10)",  "#FB923C"),
    "Resolved":           ("rgba(52,211,153,0.10)",  "#34D399"),
    "Closed":             ("rgba(139,139,147,0.10)", "#8B8B93"),
}

SENTIMENT_COLORS = {
    "Negative": ("rgba(248,113,113,0.10)", "#F87171"),
    "Neutral":  ("rgba(139,139,147,0.10)", "#A1A1AA"),
    "Positive": ("rgba(52,211,153,0.10)",  "#34D399"),
}


def _tag(label: str, bg: str, fg: str) -> str:
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;padding:3px 9px;'
        f'border-radius:5px;background:{bg};color:{fg};font-weight:600;'
        f'font-size:0.78rem;white-space:nowrap;letter-spacing:0.01em;">'
        f'<span style="width:6px;height:6px;border-radius:50%;background:{fg};flex-shrink:0;"></span>'
        f'{label}</span>'
    )


def priority_badge(priority: str) -> str:
    bg, fg = PRIORITY_COLORS.get(priority, ("rgba(139,139,147,0.10)", "#A1A1AA"))
    return _tag(priority, bg, fg)


def status_badge(status: str) -> str:
    bg, fg = STATUS_COLORS.get(status, ("rgba(139,139,147,0.10)", "#A1A1AA"))
    return _tag(status, bg, fg)


def sentiment_badge(sentiment: str) -> str:
    bg, fg = SENTIMENT_COLORS.get(sentiment, ("rgba(139,139,147,0.10)", "#A1A1AA"))
    return _tag(sentiment, bg, fg)


def safety_badge(is_risk: bool) -> str:
    if is_risk:
        return _tag("Safety risk", "rgba(248,113,113,0.10)", "#F87171")
    return _tag("No safety risk", "rgba(52,211,153,0.10)", "#34D399")


def stat_card(label: str, value, accent: str = ACCENT, sublabel: str = "") -> str:
    sub_html = f'<div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:3px;">{sublabel}</div>' if sublabel else ""
    return f"""
    <div style="flex:1;min-width:150px;background:{SURFACE};border:1px solid {BORDER};
                border-top:2px solid {accent};border-radius:8px;padding:14px 16px;">
        <div style="font-size:0.72rem;font-weight:600;color:{TEXT_MUTED};text-transform:uppercase;
                    letter-spacing:0.05em;">{label}</div>
        <div style="font-size:1.65rem;font-weight:700;color:{TEXT};margin-top:6px;line-height:1;">{value}</div>
        {sub_html}
    </div>
    """


def stat_grid(cards: list) -> str:
    return f'<div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px;">{"".join(cards)}</div>'


def complaint_card_html(result: dict) -> str:
    """Renders the post-submission analysis card — one clean sectioned panel."""
    cls = result["classification"]
    info = result["info"]
    emergency = result["emergency"]
    priority = result["priority"]
    routing = result["routing"]
    sla = result["sla"]

    banners = ""
    if emergency["is_emergency"]:
        banners += f"""
        <div style="display:flex;gap:8px;align-items:flex-start;background:rgba(248,113,113,0.08);
                    border:1px solid rgba(248,113,113,0.25);border-radius:6px;
                    padding:9px 12px;margin-bottom:10px;color:#F87171;font-size:0.83rem;">
            {icon('alert', 15)}<span><b>Safety risk detected —</b> {emergency['reason']}</span>
        </div>"""
    if result["duplicate"]["is_duplicate"]:
        banners += f"""
        <div style="display:flex;gap:8px;align-items:flex-start;background:rgba(251,191,36,0.08);
                    border:1px solid rgba(251,191,36,0.25);border-radius:6px;
                    padding:9px 12px;margin-bottom:10px;color:#FBBF24;font-size:0.83rem;">
            {icon('alert', 15)}<span><b>Possible duplicate —</b> similar to
            <code style="color:#FBBF24;">{result['duplicate']['matched_complaint_id']}</code>
            (similarity {result['duplicate']['similarity_score']})</span>
        </div>"""

    def row(label, value_html):
        return f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:8px 0;border-bottom:1px solid {BORDER};">
            <span style="color:{TEXT_MUTED};font-size:0.82rem;">{label}</span>
            <span style="font-weight:600;color:{TEXT};font-size:0.86rem;text-align:right;">{value_html}</span>
        </div>"""

    rows = "".join([
        row("Complaint ID", f"<code style='color:{TEXT};'>{result['complaint_id']}</code>"),
        row("Category", f"{cls['category']} <span style='color:{TEXT_MUTED};'>/ {cls['subcategory']}</span>"),
        row("Priority", priority_badge(priority["priority"])),
        row("Urgency / Severity", f"{info['urgency']['label']} / {info['severity']}"),
        row("Sentiment", sentiment_badge(info["sentiment"]["label"])),
        row("Safety Risk", safety_badge(emergency["is_emergency"])),
        row("Department", f"{routing['department']} <span style='color:{TEXT_MUTED};'>({routing['assigned_staff']})</span>"),
        row("SLA Deadline", sla["sla_deadline"]),
    ])

    def section(title_icon, title, text, accent):
        return f"""
        <div style="margin-top:10px;padding:11px 13px;background:{SURFACE_ALT};
                    border:1px solid {BORDER};border-left:2px solid {accent};border-radius:6px;">
            <div style="display:flex;align-items:center;gap:6px;font-size:0.72rem;font-weight:700;
                        color:{accent};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">
                {icon(title_icon, 13)}{title}
            </div>
            <div style="font-size:0.87rem;color:{TEXT};line-height:1.5;">{text}</div>
        </div>"""

    return f"""
    <div style="background:{SURFACE};border:1px solid {BORDER};border-radius:10px;padding:18px 20px;">
        <div style="display:flex;align-items:center;gap:8px;font-size:0.98rem;font-weight:700;color:{TEXT};margin-bottom:10px;">
            {icon('check', 17)}Complaint received
        </div>
        {banners}
        <div>{rows}</div>
        {section('insights', 'AI Summary', result['summary'], '#A5A9F5')}
        {section('management', 'Recommended Action', result['resolution']['recommended_action'], '#34D399')}
        {section('alert', 'Why this priority?', priority['reason'], '#FBBF24')}
    </div>
    """


def tenant_message_html(message: str) -> str:
    return f"""
    <div style="background:{SURFACE_ALT};border:1px solid {BORDER};border-left:2px solid #38BDF8;
                border-radius:6px;padding:13px 15px;margin-top:12px;">
        <div style="display:flex;align-items:center;gap:6px;font-size:0.72rem;font-weight:700;color:#7DD3FC;
                    text-transform:uppercase;letter-spacing:0.05em;margin-bottom:5px;">
            {icon('agent', 13)}Message to tenant
        </div>
        <div style="font-size:0.87rem;color:{TEXT};line-height:1.5;">{message}</div>
    </div>
    """


def actions_timeline_html(actions: list) -> str:
    items = "".join(
        f'<div style="display:flex;gap:8px;padding:4px 0;font-size:0.82rem;color:{TEXT_MUTED};">'
        f'<span style="color:#34D399;margin-top:2px;">{icon("check", 12)}</span>'
        f'<span>{a[2:] if a.startswith("✓ ") else a}</span></div>'
        for a in actions
    )
    return f"""
    <div style="background:{SURFACE_ALT};border:1px solid {BORDER};border-radius:6px;
                padding:13px 15px;margin-top:12px;">
        <div style="font-size:0.72rem;font-weight:700;color:{TEXT_MUTED};text-transform:uppercase;
                    letter-spacing:0.05em;margin-bottom:6px;">Agent actions</div>
        {items}
    </div>
    """


def placeholder_card(message: str = "Your AI analysis will appear here after submission.") -> str:
    return f"""
    <div style="border:1px dashed {BORDER};border-radius:10px;padding:26px 20px;
                text-align:center;color:{TEXT_MUTED};font-size:0.87rem;background:{SURFACE_ALT};">
        {message}
    </div>
    """
