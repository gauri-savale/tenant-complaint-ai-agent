"""
analytics/analytics.py
------------------------
Computes dashboard metrics and generates INTERACTIVE Plotly charts from the
complaints table (hover tooltips, smooth rendering) rather than static
matplotlib images, so the dashboard reads as a real analytics product.
All functions are defensive against an empty database.
"""

import pandas as pd
import plotly.graph_objects as go

from database import database as db
from utils.helpers import is_sla_breached

# --- Restrained professional palette (kept in sync with app.py / ui_helpers.py) ---
PAPER_BG = "#1C1C21"
GRID_COLOR = "#2A2A30"
TEXT_MUTED = "#8B8B93"
TEXT_STRONG = "#E4E4E7"

ACCENT = "#6366F1"          # primary indigo — used for single-series charts
CATEGORICAL = ["#6366F1", "#38BDF8", "#34D399", "#FBBF24", "#F472B6",
               "#A78BFA", "#FB923C", "#94A3B8", "#22D3EE", "#4ADE80"]

PRIORITY_COLOR_MAP = {"Critical": "#F87171", "High": "#FB923C", "Medium": "#FBBF24", "Low": "#34D399"}
SENTIMENT_COLOR_MAP = {"Negative": "#F87171", "Neutral": "#71717A", "Positive": "#34D399"}
STATUS_COLOR_MAP = {
    "Submitted": "#818CF8", "AI Analyzed": "#6366F1", "Assigned": "#38BDF8",
    "In Progress": "#FBBF24", "Waiting for Tenant": "#FB923C",
    "Resolved": "#34D399", "Closed": "#71717A",
}


def _layout(fig: go.Figure, title: str, height: int = 320) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=TEXT_STRONG, family="Inter, sans-serif"), x=0.02, xanchor="left"),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PAPER_BG,
        font=dict(color=TEXT_MUTED, family="Inter, sans-serif", size=11),
        margin=dict(l=10, r=10, t=44, b=10),
        height=height,
        hoverlabel=dict(bgcolor="#232329", font_color=TEXT_STRONG, bordercolor=GRID_COLOR),
        showlegend=fig.layout.showlegend if fig.layout.showlegend is not None else False,
        legend=dict(font=dict(color=TEXT_MUTED, size=10), bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=GRID_COLOR, tickfont=dict(size=10))
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False, tickfont=dict(size=10))
    return fig


def _empty_fig(message: str = "No data yet") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(color=TEXT_MUTED, size=12))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(paper_bgcolor=PAPER_BG, plot_bgcolor=PAPER_BG, height=280,
                       margin=dict(l=10, r=10, t=10, b=10))
    return fig


def get_summary_metrics() -> dict:
    df = db.get_all_complaints()
    if df.empty:
        return {
            "total": 0, "open": 0, "resolved": 0, "critical": 0,
            "avg_resolution_hours": 0, "sla_breaches": 0,
            "top_category": None, "top_category_count": 0,
            "busiest_department": None, "busiest_department_count": 0,
            "critical_open": 0, "recurring_locations": "",
        }

    total = len(df)
    resolved_mask = df["status"].isin(["Resolved", "Closed"])
    resolved = int(resolved_mask.sum())
    open_count = total - resolved
    critical = int((df["priority"] == "Critical").sum())
    critical_open = int(((df["priority"] == "Critical") & (~resolved_mask)).sum())

    breaches = int(df.apply(
        lambda r: is_sla_breached(r["sla_deadline"], r["status"]) if pd.notna(r["sla_deadline"]) else False,
        axis=1,
    ).sum())

    avg_resolution_hours = 0
    if resolved > 0:
        try:
            resolved_df = df[resolved_mask].copy()
            resolved_df["t0"] = pd.to_datetime(resolved_df["timestamp"], errors="coerce")
            resolved_df["t1"] = pd.to_datetime(resolved_df["last_updated"], errors="coerce")
            deltas = (resolved_df["t1"] - resolved_df["t0"]).dt.total_seconds() / 3600
            avg_resolution_hours = round(deltas.dropna().mean(), 1) if not deltas.dropna().empty else 0
        except Exception:
            avg_resolution_hours = 0

    top_category, top_category_count = None, 0
    if not df["category"].dropna().empty:
        vc = df["category"].value_counts()
        top_category, top_category_count = vc.index[0], int(vc.iloc[0])

    busiest_department, busiest_department_count = None, 0
    open_df = df[~resolved_mask]
    if not open_df.empty and not open_df["department"].dropna().empty:
        vc = open_df["department"].value_counts()
        busiest_department, busiest_department_count = vc.index[0], int(vc.iloc[0])

    recurring = df.groupby(["category", "location"]).size().reset_index(name="n")
    recurring = recurring[recurring["n"] >= 3].sort_values("n", ascending=False)
    recurring_locations = ", ".join(
        f"{r['location']} ({r['category']}, x{r['n']})" for _, r in recurring.head(3).iterrows()
    )

    return {
        "total": total, "open": open_count, "resolved": resolved, "critical": critical,
        "avg_resolution_hours": avg_resolution_hours, "sla_breaches": breaches,
        "top_category": top_category, "top_category_count": top_category_count,
        "busiest_department": busiest_department, "busiest_department_count": busiest_department_count,
        "critical_open": critical_open, "recurring_locations": recurring_locations,
    }


def chart_by_category() -> go.Figure:
    df = db.get_all_complaints()
    if df.empty:
        return _empty_fig()
    counts = df["category"].value_counts()
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=ACCENT, marker_line_width=0,
        hovertemplate="%{x}: <b>%{y}</b><extra></extra>",
    ))
    return _layout(fig, "Complaints by Category")


def chart_by_priority() -> go.Figure:
    df = db.get_all_complaints()
    if df.empty:
        return _empty_fig()
    order = ["Critical", "High", "Medium", "Low"]
    counts = df["priority"].value_counts().reindex(order).fillna(0)
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=[PRIORITY_COLOR_MAP[p] for p in order], marker_line_width=0,
        hovertemplate="%{x}: <b>%{y}</b><extra></extra>",
    ))
    return _layout(fig, "Complaints by Priority")


def chart_by_status() -> go.Figure:
    df = db.get_all_complaints()
    if df.empty:
        return _empty_fig()
    counts = df["status"].value_counts()
    colors = [STATUS_COLOR_MAP.get(s, "#71717A") for s in counts.index]
    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values, hole=0.58,
        marker=dict(colors=colors, line=dict(color=PAPER_BG, width=2)),
        textfont=dict(size=10, color=TEXT_STRONG),
        hovertemplate="%{label}: <b>%{value}</b> (%{percent})<extra></extra>",
    ))
    fig.update_layout(showlegend=True)
    return _layout(fig, "Complaints by Status")


def chart_over_time() -> go.Figure:
    df = db.get_all_complaints()
    if df.empty:
        return _empty_fig()
    tmp = df.copy()
    tmp["date"] = pd.to_datetime(tmp["timestamp"], errors="coerce").dt.date
    counts = tmp.groupby("date").size().sort_index()
    fig = go.Figure(go.Scatter(
        x=[str(d) for d in counts.index], y=counts.values, mode="lines",
        line=dict(color=ACCENT, width=2, shape="spline"),
        fill="tozeroy", fillcolor="rgba(99,102,241,0.12)",
        hovertemplate="%{x}: <b>%{y}</b><extra></extra>",
    ))
    return _layout(fig, "Complaints Over Time")


def chart_department_workload() -> go.Figure:
    df = db.get_all_complaints()
    if df.empty:
        return _empty_fig()
    open_df = df[~df["status"].isin(["Resolved", "Closed"])]
    if open_df.empty:
        return _empty_fig("No open complaints")
    counts = open_df["department"].value_counts().sort_values()
    fig = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation="h",
        marker_color=ACCENT, marker_line_width=0,
        hovertemplate="%{y}: <b>%{x}</b><extra></extra>",
    ))
    return _layout(fig, "Open Workload by Department", height=340)


def chart_resolution_time() -> go.Figure:
    df = db.get_all_complaints()
    if df.empty:
        return _empty_fig()
    resolved = df[df["status"].isin(["Resolved", "Closed"])].copy()
    if resolved.empty:
        return _empty_fig("No resolved complaints yet")
    resolved["t0"] = pd.to_datetime(resolved["timestamp"], errors="coerce")
    resolved["t1"] = pd.to_datetime(resolved["last_updated"], errors="coerce")
    resolved["hours"] = (resolved["t1"] - resolved["t0"]).dt.total_seconds() / 3600
    grouped = resolved.groupby("category")["hours"].mean().dropna().sort_values()
    fig = go.Figure(go.Bar(
        x=grouped.values, y=grouped.index, orientation="h",
        marker_color="#34D399", marker_line_width=0,
        hovertemplate="%{y}: <b>%{x:.1f}h</b><extra></extra>",
    ))
    return _layout(fig, "Avg Resolution Time by Category (hrs)", height=340)


def chart_sentiment_distribution() -> go.Figure:
    df = db.get_all_complaints()
    if df.empty:
        return _empty_fig()
    counts = df["sentiment"].value_counts()
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=[SENTIMENT_COLOR_MAP.get(c, ACCENT) for c in counts.index],
        marker_line_width=0,
        hovertemplate="%{x}: <b>%{y}</b><extra></extra>",
    ))
    return _layout(fig, "Sentiment Distribution")
