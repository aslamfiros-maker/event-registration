import os
import sys
from database import init_db, get_db_connection
import sample_data
import services
from fastapi.testclient import TestClient
from main import app

def run_tests():
    print("--- 1. Testing Database & Schema Initialization ---")
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print("Detected DB Tables:", tables)
    assert "events" in tables
    assert "attendees" in tables
    assert "followups" in tables
    conn.close()
    print(" Database tables verified.")

    print("\n--- 2. Testing Sample Data Seeding ---")
    seed_res = sample_data.seed_sample_data()
    print("Seed result:", seed_res)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM events;")
    event_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM attendees;")
    attendee_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM followups;")
    followup_count = cur.fetchone()[0]
    conn.close()
    print(f"Total Events: {event_count}, Attendees: {attendee_count}, Follow-ups: {followup_count}")
    assert event_count >= 2
    assert attendee_count >= 10
    print(" Sample data seeded successfully.")

    print("\n--- 3. Testing QR Code & WhatsApp Generation ---")
    qr_uri = services.generate_qr_base64("REG-E1-TEST123")
    assert qr_uri.startswith("data:image/png;base64,")
    print(f"QR Code generated: {qr_uri[:40]}... (length: {len(qr_uri)})")
    wa_link = services.generate_whatsapp_link("+91 98765 43210", "Aarav Sharma", "Tech Summit 2026")
    assert "https://wa.me/919876543210?text=" in wa_link
    print("WhatsApp link generated:", wa_link[:60], "...")
    print(" Services verified.")

    print("\n--- 4. Testing Web Endpoints & API with FastAPI TestClient ---")
    client = TestClient(app)

    # 4.1 Dashboard
    res = client.get("/")
    assert res.status_code == 200
    assert "Event Operations Command Center" in res.text
    print(" GET / [Dashboard] passed.")

    # 4.2 Event Details
    res = client.get("/events/1")
    assert res.status_code == 200
    assert "Cloud Innovation Summit" in res.text
    print(" GET /events/1 [Event Detail] passed.")

    # 4.3 Pre-Registration Page
    res = client.get("/events/1/register")
    assert res.status_code == 200
    assert "Official Event Pre-Registration" in res.text
    print(" GET /events/1/register [Registration Page] passed.")

    # 4.4 Submit Pre-Registration
    unique_suffix = services.generate_ticket_code(99)[-4:]
    reg_payload = {
        "event_id": 1,
        "full_name": f"Test Attendee {unique_suffix}",
        "email": f"test.{unique_suffix}@example.com",
        "phone": "+1 555-0199",
        "organization": "Test Corp",
        "role": "QA Engineer",
        "notes": "Testing pre-registration"
    }
    res = client.post("/api/register", json=reg_payload)
    assert res.status_code == 200
    ticket_code = res.json()["ticket_code"]
    print(f" POST /api/register passed. Issued Ticket: {ticket_code}")

    # 4.5 Check Ticket Page
    res = client.get(f"/tickets/{ticket_code}")
    assert res.status_code == 200
    assert "Official Attendee Pass" in res.text
    assert ticket_code in res.text
    print(f" GET /tickets/{ticket_code} passed.")

    # 4.6 Check-In Kiosk Page
    res = client.get("/events/1/checkin")
    assert res.status_code == 200
    assert "Live Camera QR Scanner" in res.text
    print(" GET /events/1/checkin [Kiosk] passed.")

    # 4.7 Execute Check-In via API
    checkin_payload = {
        "ticket_code": ticket_code,
        "event_id": 1,
        "action": "checkin"
    }
    res = client.post("/api/checkin", json=checkin_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "checked_in"
    print(f" POST /api/checkin passed. Status: {res.json()['status']}")

    # 4.8 Test Duplicate Check-In Warning
    res = client.post("/api/checkin", json=checkin_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "already_checked_in"
    print(" POST /api/checkin duplicate detection passed.")

    # 4.9 Absentee Follow-Up Page
    res = client.get("/events/1/followup")
    assert res.status_code == 200
    assert "Not Attending Outreach Hub" in res.text
    print(" GET /events/1/followup [Follow-up Hub] passed.")

    # 4.10 Final Event Report Page
    res = client.get("/events/1/report")
    assert res.status_code == 200
    assert "Final Event Report" in res.text
    print(" GET /events/1/report [Report Page] passed.")

    # 4.11 Excel Export
    res = client.get("/api/events/1/export/excel")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(res.content) > 1000
    print(f" GET /api/events/1/export/excel passed ({len(res.content)} bytes generated).")

    # 4.12 Form Builder Page
    res = client.get("/events/1/form-builder")
    assert res.status_code == 200
    assert "Custom Form Builder" in res.text
    print(" GET /events/1/form-builder [Form Builder UI] passed.")

    # 4.13 Configure Custom Fields via API
    form_config_payload = {
        "fields": [
            {"id": "full_name", "label": "Full Name", "type": "text", "required": True, "enabled": True, "is_standard": True},
            {"id": "email", "label": "Email Address", "type": "email", "required": True, "enabled": True, "is_standard": True},
            {"id": "phone", "label": "Phone Number (WhatsApp)", "type": "tel", "required": True, "enabled": True, "is_standard": True},
            {"id": "organization", "label": "Organization", "type": "text", "required": False, "enabled": True, "is_standard": True},
            {"id": "tshirt_size", "label": "T-Shirt Size", "type": "select", "options": ["S", "M", "L", "XL"], "required": True, "enabled": True, "is_standard": False}
        ]
    }
    res = client.post("/api/events/1/form-config", json=form_config_payload)
    assert res.status_code == 200
    print(" POST /api/events/1/form-config [Save Config] passed.")

    # 4.14 Verify Dynamic Public Registration Form
    res = client.get("/events/1/register")
    assert res.status_code == 200
    assert "T-Shirt Size" in res.text
    print(" GET /events/1/register [Dynamic Custom Field Render] passed.")

    # 4.15 Custom Field Validation: Reject if required custom field missing
    invalid_reg_payload = {
        "event_id": 1,
        "full_name": "Custom Test User",
        "email": "custom.user@example.com",
        "phone": "+1 555-9988",
        "custom_data": {} # Missing required tshirt_size
    }
    res = client.post("/api/register", json=invalid_reg_payload)
    assert res.status_code == 400
    assert "T-Shirt Size" in res.json()["detail"]
    print(" POST /api/register [Missing Required Custom Field Rejection] passed.")

    # 4.16 Custom Field Validation: Accept when provided
    valid_reg_payload = {
        "event_id": 1,
        "full_name": "Custom Test User",
        "email": f"custom.{unique_suffix}@example.com",
        "phone": "+1 555-9988",
        "custom_data": {"tshirt_size": "L"}
    }
    res = client.post("/api/register", json=valid_reg_payload)
    assert res.status_code == 200
    print(" POST /api/register [Valid Custom Field Submission] passed.")

    print("\n=======================================================")
    print(" ALL 16 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
