-- schema.sql
-- Tenant Complaint AI Agent — SQLite schema

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    unit_number     TEXT,
    contact_email   TEXT,
    created_at      TEXT
);

CREATE TABLE IF NOT EXISTS departments (
    department_id   TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category_focus  TEXT
);

CREATE TABLE IF NOT EXISTS maintenance_staff (
    staff_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    department_id   TEXT,
    active_load     INTEGER DEFAULT 0,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id        TEXT PRIMARY KEY,
    tenant_id           TEXT,
    timestamp            TEXT,
    description          TEXT NOT NULL,
    category              TEXT,
    subcategory           TEXT,
    location               TEXT,
    sentiment               TEXT,
    severity                 TEXT,
    urgency                   TEXT,
    safety_risk               INTEGER DEFAULT 0,
    priority                    TEXT,
    priority_reason              TEXT,
    department                    TEXT,
    assigned_staff                  TEXT,
    status                            TEXT DEFAULT 'Submitted',
    sla_deadline                       TEXT,
    ai_summary                          TEXT,
    recommended_action                    TEXT,
    resolution                              TEXT,
    is_duplicate_of                          TEXT,
    last_updated                              TEXT,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
);

CREATE TABLE IF NOT EXISTS complaint_updates (
    update_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id    TEXT,
    old_status      TEXT,
    new_status      TEXT,
    note            TEXT,
    updated_at      TEXT,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
);

CREATE INDEX IF NOT EXISTS idx_complaints_tenant ON complaints(tenant_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints(category);
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority);
