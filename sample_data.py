from datetime import datetime, timedelta
import random
from database import get_db_connection, init_db
from services import generate_ticket_code

def seed_sample_data():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if sample events already exist
    cursor.execute("SELECT COUNT(*) as count FROM events;")
    row = cursor.fetchone()
    if row["count"] > 0:
        conn.close()
        return {"message": "Data already exists. Skipping seed."}

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # Sample Event 1: AI & Cloud Innovation Summit 2026
    cursor.execute("""
    INSERT INTO events (title, description, category, event_date, start_time, end_time, venue, location_type, max_capacity, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "AI & Cloud Innovation Summit 2026",
        "A premier tech conference showcasing advancements in Agentic AI, Autonomous Workflows, and Cloud Architecture. Featuring keynote sessions, interactive tech tracks, and hands-on workshops.",
        "Conference",
        today_str,
        "09:30",
        "17:30",
        "Grand Tech Auditorium, Floor 3",
        "In-Person",
        150,
        "Active"
    ))
    event1_id = cursor.lastrowid

    # Sample Event 2: Full-Stack Web & API Masterclass
    cursor.execute("""
    INSERT INTO events (title, description, category, event_date, start_time, end_time, venue, location_type, max_capacity, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "Next-Gen Python & Web API Masterclass",
        "Hands-on architectural deep-dive into building high-throughput asynchronous services and real-time interactive user interfaces.",
        "Workshop",
        tomorrow_str,
        "10:00",
        "16:00",
        "Silicon Innovation Lab / Online Zoom",
        "Hybrid",
        75,
        "Upcoming"
    ))
    event2_id = cursor.lastrowid

    # Attendees for Event 1
    sample_attendees = [
        ("Aarav Sharma", "aarav.sharma@techcorp.com", "+91 98765 43210", "TechCorp Global", "Lead AI Architect", "Vegan lunch preference", "Attended", "09:22:15"),
        ("Sophia Williams", "sophia.w@cloudscale.io", "+1 415 555 0192", "CloudScale Labs", "Principal DevOps Engineer", "", "Attended", "09:35:40"),
        ("Rohan Patel", "rohan.patel@innovate.in", "+91 91234 56789", "Innovate Systems", "Senior Full-Stack Developer", "Requires parking pass", "Attended", "09:41:10"),
        ("Elena Rostova", "elena.r@datastack.com", "+44 7700 900123", "DataStack Analytics", "Data Engineering Lead", "", "Attended", "09:55:04"),
        ("David Miller", "david.m@cybersec.org", "+1 312 555 0144", "CyberSec Dynamics", "Solutions Architect", "", "Attended", "10:12:30"),
        ("Priya Nair", "priya.nair@quantum.co", "+91 94455 66778", "Quantum Solutions", "Product Manager", "", "Attended", "10:28:19"),
        
        # Absent attendees for follow-up demo
        ("Michael Chang", "m.chang@enterprise.com", "+1 650 555 0188", "Enterprise Digital", "VP of Engineering", "Interested in AI roadmap slides", "Registered", None),
        ("Ananya Iyer", "ananya.iyer@fintechhub.in", "+91 99887 76655", "FinTech Hub", "Security Specialist", "", "Registered", None),
        ("Liam O'Connor", "liam.oc@greenenergy.ie", "+353 87 123 4567", "Green Energy Tech", "CTO", "Late travel arrival", "Registered", None),
        ("Kavita Deshmukh", "kavita.d@edulearn.org", "+91 97654 32198", "EduLearn Academy", "Dean of Computing", "Request recordings", "Registered", None),
        ("James Wilson", "j.wilson@nexusai.com", "+1 206 555 0166", "Nexus AI Research", "Research Scientist", "", "Registered", None),
    ]

    for name, email, phone, org, role, notes, status, chk_time in sample_attendees:
        code = generate_ticket_code(event1_id)
        chk_at = f"{today_str} {chk_time}" if chk_time else None
        cursor.execute("""
        INSERT INTO attendees (event_id, ticket_code, full_name, email, phone, organization, role, notes, status, checkin_at, is_walkin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (event1_id, code, name, email, phone, org, role, notes, status, chk_at, 0))
        att_id = cursor.lastrowid

        # If absent, add initial follow-up state
        if status == "Registered":
            if name == "Michael Chang":
                fup_status = "Responded"
                reason = "Work Conflict"
                fup_notes = "Sent slide deck; had an urgent client release meeting."
            elif name == "Liam O'Connor":
                fup_status = "Follow-up Sent"
                reason = "Travel Issue"
                fup_notes = "Flight delayed; requested session recording."
            else:
                fup_status = "Not Contacted"
                reason = "Not Specified"
                fup_notes = ""

            cursor.execute("""
            INSERT INTO followups (event_id, attendee_id, status, channel, reason_category, notes)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (event1_id, att_id, fup_status, "WhatsApp", reason, fup_notes))

    # Add 1 Walk-in for event 1
    walkin_code = generate_ticket_code(event1_id)
    cursor.execute("""
    INSERT INTO attendees (event_id, ticket_code, full_name, email, phone, organization, role, notes, status, checkin_at, is_walkin)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (event1_id, walkin_code, "Vikram Malhotra (Walk-in)", "vikram.m@investments.in", "+91 98111 22334", "Malhotra Capital", "Managing Partner", "On-spot badge issued", "Attended", f"{today_str} 10:45:00", 1))

    conn.commit()
    conn.close()
    return {"message": "Sample events and attendees seeded successfully!"}

if __name__ == "__main__":
    res = seed_sample_data()
    print(res)
