"""
database/database.py
---------------------
SQLite access layer for the Tenant Complaint AI Agent.

Every function here is defensive: an empty or missing database must
never crash the Gradio app. init_db() creates the schema and, on first
run, seeds realistic demo data so the dashboard/analytics tabs are
never empty.
"""

import os
import sqlite3
from contextlib import contextmanager

import pandas as pd

from utils.config import DB_PATH, DEPARTMENTS
from utils.helpers import now_iso

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist. Safe to call multiple times."""
    with get_conn() as conn:
        with open(SCHEMA_PATH, "r") as f:
            conn.executescript(f.read())
        _seed_departments(conn)


def _seed_departments(conn):
    cur = conn.execute("SELECT COUNT(*) AS c FROM departments")
    if cur.fetchone()["c"] > 0:
        return
    for i, dept in enumerate(DEPARTMENTS):
        conn.execute(
            "INSERT INTO departments (department_id, name, category_focus) VALUES (?, ?, ?)",
            (f"DEPT-{i+1:02d}", dept, dept),
        )
        for j in range(2):  # two staff per department for demo assignment
            conn.execute(
                "INSERT OR IGNORE INTO maintenance_staff (staff_id, name, department_id, active_load) "
                "VALUES (?, ?, ?, 0)",
                (f"STF-{i+1:02d}{j+1}", f"{dept.split()[0]} Tech {j+1}", f"DEPT-{i+1:02d}"),
            )


def is_empty() -> bool:
    with get_conn() as conn:
        cur = conn.execute("SELECT COUNT(*) AS c FROM complaints")
        return cur.fetchone()["c"] == 0


def upsert_tenant(tenant_id: str, name: str, unit_number: str, contact_email: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tenants (tenant_id, name, unit_number, contact_email, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(tenant_id) DO UPDATE SET name=excluded.name, unit_number=excluded.unit_number",
            (tenant_id, name, unit_number, contact_email, now_iso()),
        )


def insert_complaint(record: dict):
    cols = ", ".join(record.keys())
    placeholders = ", ".join("?" for _ in record)
    with get_conn() as conn:
        conn.execute(
            f"INSERT INTO complaints ({cols}) VALUES ({placeholders})",
            tuple(record.values()),
        )


def get_complaint(complaint_id: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id,))
        row = cur.fetchone()
        return dict(row) if row else {}


def get_all_complaints() -> pd.DataFrame:
    with get_conn() as conn:
        try:
            df = pd.read_sql_query("SELECT * FROM complaints ORDER BY timestamp DESC", conn)
        except Exception:
            df = pd.DataFrame()
    return df


def get_complaints_by_tenant(tenant_id: str) -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM complaints WHERE tenant_id = ? ORDER BY timestamp DESC",
            conn, params=(tenant_id,),
        )
    return df


def update_complaint_fields(complaint_id: str, fields: dict):
    if not fields:
        return
    fields = dict(fields)
    fields["last_updated"] = now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE complaints SET {set_clause} WHERE complaint_id = ?",
            (*fields.values(), complaint_id),
        )


def log_status_update(complaint_id: str, old_status: str, new_status: str, note: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO complaint_updates (complaint_id, old_status, new_status, note, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (complaint_id, old_status, new_status, note, now_iso()),
        )


def get_departments() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM departments", conn)


def get_staff_for_department(department_name: str) -> str:
    """Pick the least-loaded staff member for a department (round-robin-ish)."""
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT s.staff_id, s.name, s.active_load FROM maintenance_staff s "
            "JOIN departments d ON s.department_id = d.department_id "
            "WHERE d.name = ? ORDER BY s.active_load ASC LIMIT 1",
            (department_name,),
        )
        row = cur.fetchone()
        if not row:
            return "Unassigned"
        conn.execute(
            "UPDATE maintenance_staff SET active_load = active_load + 1 WHERE staff_id = ?",
            (row["staff_id"],),
        )
        return row["name"]


def seed_from_dataframe(df: pd.DataFrame):
    """Bulk-insert a demo dataset (already fully AI-analyzed) for a non-empty dashboard."""
    with get_conn() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, unit_number, created_at) "
                "VALUES (?, ?, ?, ?)",
                (row["tenant_id"], row["tenant_name"], row["unit_number"], row["timestamp"]),
            )
            conn.execute(
                """INSERT OR IGNORE INTO complaints (
                    complaint_id, tenant_id, timestamp, description, category, subcategory,
                    location, sentiment, severity, urgency, safety_risk, priority, priority_reason,
                    department, assigned_staff, status, sla_deadline, ai_summary,
                    recommended_action, resolution, is_duplicate_of, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["complaint_id"], row["tenant_id"], row["timestamp"], row["description"],
                    row["category"], row["subcategory"], row["location"], row["sentiment"],
                    row["severity"], row["urgency"], int(row["safety_risk"]), row["priority"],
                    row["priority_reason"], row["department"], row["assigned_staff"],
                    row["status"], row["sla_deadline"], row["ai_summary"],
                    row["recommended_action"], row["resolution"], row.get("is_duplicate_of", ""),
                    row.get("last_updated", row["timestamp"]),
                ),
            )
