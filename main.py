import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, HTTPException, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import json
from database import init_db, get_db_connection, get_default_form_fields
from models import (
    EventCreate, EventUpdate, AttendeeRegister, WalkinRegister,
    CheckinRequest, FollowupUpdate, FormFieldConfig, EventFormConfigUpdate
)
from services import (
    generate_ticket_code,
    generate_qr_base64,
    generate_whatsapp_link,
    generate_excel_report
)
import sample_data

# Ensure static directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)

app = FastAPI(title="Albirr Events - Event Operations Platform")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "P@$$word123"

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Initialize DB on start
@app.on_event("startup")
def startup_event():
    init_db()

# Helper to get event with stats
def get_event_by_id(event_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events WHERE id = ?;", (event_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

# Helper for event metrics
def calculate_event_metrics(event_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendees WHERE event_id = ?;", (event_id,))
    attendees = [dict(r) for r in cur.fetchall()]
    conn.close()

    total = len(attendees)
    attended = sum(1 for a in attendees if a.get("status") == "Attended")
    absent = sum(1 for a in attendees if a.get("status") == "Registered")
    walkin = sum(1 for a in attendees if a.get("is_walkin") == 1)
    rate = round((attended / total * 100), 1) if total > 0 else 0

    return {
        "total": total,
        "attended": attended,
        "absent": absent,
        "walkin": walkin,
        "rate": rate,
        "attendees": attendees
    }

def get_event_form_fields(event: dict) -> List[Dict[str, Any]]:
    """Get field definitions for an event, falling back to default schema."""
    if event and event.get("custom_fields_config"):
        try:
            fields = json.loads(event["custom_fields_config"])
            if isinstance(fields, list) and len(fields) > 0:
                return fields
        except Exception:
            pass
    return get_default_form_fields()

# -------------------------------------------------------------
# HTML PAGE ROUTES
# -------------------------------------------------------------

@app.get("/")
async def home_redirect():
    return RedirectResponse(url="/admin")


@app.get("/dashboard", response_class=HTMLResponse)
def index_page(request: Request):
    if request.cookies.get("admin_session") != "authenticated":
        return RedirectResponse (url="/admin")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY event_date DESC, id DESC;")
    events_raw = [dict(r) for r in cur.fetchall()]

    # Fetch stats for each event
    events = []
    total_reg = 0
    total_att = 0
    total_abs = 0

    for ev in events_raw:
        cur.execute("SELECT status, is_walkin FROM attendees WHERE event_id = ?;", (ev["id"],))
        rows = [dict(r) for r in cur.fetchall()]
        ev["registered_count"] = len(rows)
        ev["attended_count"] = sum(1 for r in rows if r["status"] == "Attended")
        ev["absent_count"] = sum(1 for r in rows if r["status"] == "Registered")
        
        total_reg += ev["registered_count"]
        total_att += ev["attended_count"]
        total_abs += ev["absent_count"]
        events.append(ev)

    conn.close()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "events": events,
            "total_registered": total_reg,
            "total_attended": total_att,
            "total_absent": total_abs,
            "active_tab": "dashboard"
        }
    )

@app.get("/events/{event_id}", response_class=HTMLResponse)
def event_overview_page(request: Request, event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    metrics = calculate_event_metrics(event_id)
    return templates.TemplateResponse(
        request=request,
        name="event_detail.html",
        context={
            "event": event,
            "attendees": metrics["attendees"],
            "total_registered": metrics["total"],
            "attended_count": metrics["attended"],
            "absent_count": metrics["absent"],
            "attendance_rate": metrics["rate"],
            "active_tab": "overview"
        }
    )

@app.get("/events/{event_id}/form-builder", response_class=HTMLResponse)
def form_builder_page(request: Request, event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    fields = get_event_form_fields(event)
    return templates.TemplateResponse(
        request=request,
        name="form_builder.html",
        context={
            "event": event,
            "current_fields": fields,
            "active_tab": "form-builder"
        }
    )

@app.get("/events/{event_id}/register", response_class=HTMLResponse)
def register_page(request: Request, event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    metrics = calculate_event_metrics(event_id)
    remaining = max(0, event["max_capacity"] - metrics["total"])
    fields = get_event_form_fields(event)
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "event": event,
            "remaining_seats": remaining,
            "fields": fields
        }
    )

@app.get("/tickets/{ticket_code}", response_class=HTMLResponse)
def ticket_page(request: Request, ticket_code: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendees WHERE ticket_code = ?;", (ticket_code,))
    attendee_row = cur.fetchone()
    if not attendee_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Ticket pass not found")

    attendee = dict(attendee_row)
    cur.execute("SELECT * FROM events WHERE id = ?;", (attendee["event_id"],))
    event_row = cur.fetchone()
    conn.close()
    if not event_row:
        raise HTTPException(status_code=404, detail="Event not found")

    event = dict(event_row)
    qr_data_uri = generate_qr_base64(ticket_code)

    return templates.TemplateResponse(
        request=request,
        name="ticket.html",
        context={
            "event": event,
            "attendee": attendee,
            "qr_code_uri": qr_data_uri
        }
    )

@app.get("/events/{event_id}/checkin", response_class=HTMLResponse)
def checkin_kiosk_page(request: Request, event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    metrics = calculate_event_metrics(event_id)
    return templates.TemplateResponse(
        request=request,
        name="checkin.html",
        context={
            "event": event,
            "attendees": metrics["attendees"],
            "total_count": metrics["total"],
            "attended_count": metrics["attended"],
            "absent_count": metrics["absent"],
            "attendance_rate": metrics["rate"],
            "active_tab": "checkin"
        }
    )

@app.get("/events/{event_id}/followup", response_class=HTMLResponse)
def followup_page(request: Request, event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get absent attendees
    cur.execute("SELECT * FROM attendees WHERE event_id = ? AND status = 'Registered' ORDER BY id ASC;", (event_id,))
    absentees_raw = [dict(r) for r in cur.fetchall()]

    # Get follow-up records
    cur.execute("SELECT * FROM followups WHERE event_id = ?;", (event_id,))
    fup_map = {r["attendee_id"]: dict(r) for r in cur.fetchall()}
    conn.close()

    absentees = []
    contacted_count = 0
    responded_count = 0

    for a in absentees_raw:
        fup = fup_map.get(a["id"], {
            "status": "Not Contacted",
            "channel": "WhatsApp",
            "reason_category": "Not Specified",
            "notes": ""
        })
        a["followup"] = fup
        a["whatsapp_link"] = generate_whatsapp_link(a.get("phone", ""), a["full_name"], event["title"])
        if fup["status"] in ["Follow-up Sent", "Responded", "Excused"]:
            contacted_count += 1
        if fup["status"] in ["Responded", "Excused"]:
            responded_count += 1
        absentees.append(a)

    pending_count = len(absentees) - contacted_count
    mail_subject = f"We missed you at {event['title']}"
    mail_body = f"Hello,\n\nWe noticed you couldn't attend {event['title']}. We hope everything is well!\n\nBest regards,\nEvent Team"

    return templates.TemplateResponse(
        request=request,
        name="followup.html",
        context={
            "event": event,
            "absentees": absentees,
            "pending_outreach_count": pending_count,
            "contacted_count": contacted_count,
            "responded_count": responded_count,
            "mail_subject": mail_subject,
            "mail_body": mail_body,
            "active_tab": "followup"
        }
    )

@app.get("/events/{event_id}/report", response_class=HTMLResponse)
def report_page(request: Request, event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendees WHERE event_id = ? ORDER BY id ASC;", (event_id,))
    attendees_raw = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM followups WHERE event_id = ?;", (event_id,))
    fup_map = {r["attendee_id"]: dict(r) for r in cur.fetchall()}
    conn.close()

    total = len(attendees_raw)
    attended = 0
    absent = 0
    walkin = 0
    arrival_counts_map = {}
    reason_counts = {
        "Work Conflict": 0,
        "Health/Medical": 0,
        "Travel Issue": 0,
        "Forgot Schedule": 0,
        "Personal Emergency": 0,
        "Not Specified / Other": 0
    }

    attendees = []
    for a in attendees_raw:
        fup = fup_map.get(a["id"], None)
        a["followup"] = fup
        if a["status"] == "Attended":
            attended += 1
            if a.get("checkin_at"):
                # extract hour, e.g. "09:00"
                try:
                    time_part = a["checkin_at"].split()[1] # "09:22:15"
                    hour_bucket = time_part[:2] + ":00"
                    arrival_counts_map[hour_bucket] = arrival_counts_map.get(hour_bucket, 0) + 1
                except Exception:
                    pass
        else:
            absent += 1
            if fup:
                r_cat = fup.get("reason_category", "Not Specified")
                if r_cat in reason_counts:
                    reason_counts[r_cat] += 1
                else:
                    reason_counts["Not Specified / Other"] += 1
            else:
                reason_counts["Not Specified / Other"] += 1

        if a.get("is_walkin") == 1:
            walkin += 1
        attendees.append(a)

    rate = round((attended / total * 100), 1) if total > 0 else 0

    sorted_hours = sorted(arrival_counts_map.keys())
    arrival_labels = sorted_hours if sorted_hours else ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]
    arrival_counts = [arrival_counts_map.get(h, 0) for h in arrival_labels]

    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "event": event,
            "attendees": attendees,
            "total_registered": total,
            "attended_count": attended,
            "absent_count": absent,
            "walkin_count": walkin,
            "attendance_rate": rate,
            "arrival_labels": arrival_labels,
            "arrival_counts": arrival_counts,
            "reason_counts": reason_counts,
            "report_generated_at": datetime.now().strftime("%B %d, %Y %I:%M %p"),
            "active_tab": "report"
        }
    )

# -------------------------------------------------------------
# REST API ENDPOINTS
# -------------------------------------------------------------

@app.post("/api/events")
def create_event(data: EventCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO events (title, description, category, event_date, start_time, end_time, venue, location_type, banner_url, max_capacity, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        data.title,
        data.description,
        data.category,
        data.event_date,
        data.start_time,
        data.end_time,
        data.venue,
        data.location_type,
        data.banner_url,
        data.max_capacity,
        data.status or "Upcoming"
    ))
    event_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"message": "Event created", "event_id": event_id}

@app.post("/api/events/{event_id}/form-config")
def save_event_form_config(event_id: int, config: EventFormConfigUpdate):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    fields_data = [f.dict() for f in config.fields]
    fields_json = json.dumps(fields_data)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE events SET custom_fields_config = ? WHERE id = ?;", (fields_json, event_id))
    conn.commit()
    conn.close()

    return {"message": "Form configuration saved successfully", "fields_count": len(fields_data)}

@app.post("/api/register")
def register_attendee(data: AttendeeRegister):
    event = get_event_by_id(data.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    metrics = calculate_event_metrics(data.event_id)
    if metrics["total"] >= event["max_capacity"]:
        raise HTTPException(status_code=400, detail="Event seat capacity has been reached.")

    # Validate custom fields against form config
    fields = get_event_form_fields(event)
    custom_data = data.custom_data or {}
    for f in fields:
        if f.get("enabled", True) and f.get("required", False) and not f.get("is_standard"):
            val = custom_data.get(f["id"])
            if val is None or str(val).strip() == "":
                raise HTTPException(status_code=400, detail=f"'{f['label']}' is required.")

    custom_data_json = json.dumps(custom_data)

    # Check if duplicate email for this event
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, ticket_code FROM attendees WHERE event_id = ? AND LOWER(email) = LOWER(?);", (data.event_id, data.email.strip()))
    existing = cur.fetchone()
    if existing:
        conn.close()
        # Return existing registration ticket
        return {"message": "Already registered", "ticket_code": existing["ticket_code"]}

    ticket_code = generate_ticket_code(data.event_id)
    cur.execute("""
    INSERT INTO attendees (event_id, ticket_code, full_name, email, phone, organization, role, notes, status, is_walkin, custom_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Registered', 0, ?);
    """, (
        data.event_id,
        ticket_code,
        data.full_name.strip(),
        data.email.strip().lower(),
        data.phone.strip() if data.phone else "",
        data.organization.strip() if data.organization else "",
        data.role.strip() if data.role else "",
        data.notes.strip() if data.notes else "",
        custom_data_json
    ))
    conn.commit()
    conn.close()

    return {"message": "Registration successful", "ticket_code": ticket_code}

@app.post("/api/walkin")
def register_walkin(data: WalkinRegister):
    event = get_event_by_id(data.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    ticket_code = generate_ticket_code(data.event_id)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_val = "Attended" if data.auto_checkin else "Registered"
    checkin_time = now_str if data.auto_checkin else None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO attendees (event_id, ticket_code, full_name, email, phone, organization, role, notes, status, checkin_at, is_walkin)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'On-the-spot walk-in', ?, ?, 1);
    """, (
        data.event_id,
        ticket_code,
        data.full_name.strip(),
        data.email.strip().lower(),
        data.phone.strip() if data.phone else "",
        data.organization.strip() if data.organization else "",
        data.role.strip() if data.role else "",
        status_val,
        checkin_time
    ))
    attendee_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "message": "Walk-in registered",
        "attendee_id": attendee_id,
        "full_name": data.full_name,
        "ticket_code": ticket_code,
        "status": status_val
    }

@app.post("/api/checkin")
def checkin_attendee(req: CheckinRequest):
    conn = get_db_connection()
    cur = conn.cursor()

    if req.ticket_code:
        clean_code = req.ticket_code.strip()
        cur.execute("SELECT * FROM attendees WHERE ticket_code = ? AND event_id = ?;", (clean_code, req.event_id))
    elif req.attendee_id:
        cur.execute("SELECT * FROM attendees WHERE id = ? AND event_id = ?;", (req.attendee_id, req.event_id))
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Missing ticket_code or attendee_id")

    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Attendee record not found for this event")

    attendee = dict(row)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if req.action == "checkout":
        # Undo check-in
        cur.execute("UPDATE attendees SET status = 'Registered', checkin_at = NULL WHERE id = ?;", (attendee["id"],))
        conn.commit()
        attendee["status"] = "Registered"
        attendee["checkin_at"] = None
        status_code = "checked_out"
    else:
        # Check in
        if attendee["status"] == "Attended":
            conn.close()
            metrics = calculate_event_metrics(req.event_id)
            return {
                "status": "already_checked_in",
                "attendee": attendee,
                "metrics": {
                    "total": metrics["total"],
                    "attended": metrics["attended"],
                    "absent": metrics["absent"],
                    "rate": metrics["rate"]
                }
            }

        cur.execute("UPDATE attendees SET status = 'Attended', checkin_at = ? WHERE id = ?;", (now_str, attendee["id"]))
        conn.commit()
        attendee["status"] = "Attended"
        attendee["checkin_at"] = now_str
        status_code = "checked_in"

    conn.close()
    metrics = calculate_event_metrics(req.event_id)
    return {
        "status": status_code,
        "attendee": attendee,
        "metrics": {
            "total": metrics["total"],
            "attended": metrics["attended"],
            "absent": metrics["absent"],
            "rate": metrics["rate"]
        }
    }

@app.post("/api/followup")
def update_followup(data: FollowupUpdate):
    conn = get_db_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO followups (event_id, attendee_id, status, channel, reason_category, notes, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(attendee_id) DO UPDATE SET
        status = excluded.status,
        channel = excluded.channel,
        reason_category = excluded.reason_category,
        notes = excluded.notes,
        updated_at = excluded.updated_at;
    """, (
        data.event_id,
        data.attendee_id,
        data.status,
        data.channel or "WhatsApp",
        data.reason_category or "Not Specified",
        data.notes or "",
        now_str
    ))
    conn.commit()
    conn.close()
    return {"message": "Follow-up saved"}

@app.get("/api/events/{event_id}/export/excel")
def export_event_excel(event_id: int):
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendees WHERE event_id = ? ORDER BY id ASC;", (event_id,))
    attendees = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT * FROM followups WHERE event_id = ?;", (event_id,))
    followups = [dict(r) for r in cur.fetchall()]
    conn.close()

    excel_buffer = generate_excel_report(event, attendees, followups)
    filename = f"Event_Report_{event['title'].replace(' ', '_')[:30]}_{event['event_date']}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/sample-data")
def populate_sample_data():
    res = sample_data.seed_sample_data()
    return res

if __name__ == "__main__":
    import uvicorn
    print("Starting EventPulse Server at http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

# --- ADMIN LOGIN ROUTES ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="admin_login.html", 
        context={"error": None}
    )

@app.post("/admin", response_class=HTMLResponse)
async def admin_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie("admin_session"), value="authenticated", httponly=True)
    else:
        return templates.TemplateResponse(
            request=request, 
            name="admin_login.html", 
            context={"error": "Invalid Username or Password!"}
        )
