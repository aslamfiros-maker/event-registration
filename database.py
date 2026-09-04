import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "events.db")

def get_db_connection():
    """Get a thread-safe connection to the SQLite database with dictionary rows."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys and WAL mode for better concurrency
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    """Initialize database tables and indexes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT DEFAULT 'General',
        event_date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        venue TEXT,
        location_type TEXT DEFAULT 'In-Person',
        banner_url TEXT,
        max_capacity INTEGER DEFAULT 100,
        status TEXT DEFAULT 'Upcoming', -- Upcoming, Active, Completed, Cancelled
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Attendees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        ticket_code TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        organization TEXT,
        role TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Registered', -- Registered, Attended, Cancelled
        is_walkin INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        checkin_at TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
    );
    """)

    # Follow-ups table for absentees / no-shows
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        attendee_id INTEGER NOT NULL UNIQUE,
        status TEXT DEFAULT 'Not Contacted', -- Not Contacted, Follow-up Sent, Responded, Excused
        channel TEXT DEFAULT 'WhatsApp', -- WhatsApp, Email, Phone, In-Person
        reason_category TEXT DEFAULT 'Not Specified', -- Work Conflict, Health/Medical, Travel Issue, Forgot, Other
        notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
        FOREIGN KEY (attendee_id) REFERENCES attendees (id) ON DELETE CASCADE
    );
    """)

    # Create indexes for speed
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendees_event ON attendees(event_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendees_ticket ON attendees(ticket_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendees_status ON attendees(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_followups_event ON followups(event_id);")

    # Safe Schema Evolution / Migrations:
    # 1. Ensure 'custom_fields_config' exists on events table
    cursor.execute("PRAGMA table_info(events);")
    event_cols = [r["name"] for r in cursor.fetchall()]
    if "custom_fields_config" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN custom_fields_config TEXT DEFAULT '[]';")

    # 2. Ensure 'custom_data' exists on attendees table
    cursor.execute("PRAGMA table_info(attendees);")
    attendee_cols = [r["name"] for r in cursor.fetchall()]
    if "custom_data" not in attendee_cols:
        cursor.execute("ALTER TABLE attendees ADD COLUMN custom_data TEXT DEFAULT '{}';")

    conn.commit()
    conn.close()

def get_default_form_fields() -> List[Dict[str, Any]]:
    """Default form configuration schema for events."""
    return [
        {
            "id": "full_name",
            "label": "Full Name",
            "type": "text",
            "required": True,
            "enabled": True,
            "is_standard": True,
            "placeholder": "e.g. Jane Doe"
        },
        {
            "id": "email",
            "label": "Email Address",
            "type": "email",
            "required": True,
            "enabled": True,
            "is_standard": True,
            "placeholder": "name@example.com"
        },
        {
            "id": "phone",
            "label": "Phone Number (WhatsApp)",
            "type": "tel",
            "required": True,
            "enabled": True,
            "is_standard": True,
            "placeholder": "+1 555-0199 or 9876543210"
        },
        {
            "id": "organization",
            "label": "Organization / Company / College",
            "type": "text",
            "required": False,
            "enabled": True,
            "is_standard": True,
            "placeholder": "e.g. Acme Corp or University"
        },
        {
            "id": "role",
            "label": "Designation / Role",
            "type": "text",
            "required": False,
            "enabled": True,
            "is_standard": True,
            "placeholder": "e.g. Lead Engineer / Student"
        },
        {
            "id": "notes",
            "label": "Special Requests / Dietary Notes",
            "type": "textarea",
            "required": False,
            "enabled": True,
            "is_standard": True,
            "placeholder": "Any dietary preferences or accessibility requirements..."
        }
    ]

if __name__ == "__main__":
    init_db()
    print("Database schema initialized successfully at:", DB_PATH)
