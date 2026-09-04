# EventPulse - Modern Event Management & Operations Software

A comprehensive, full-stack event operations platform built for event managers, organizers, and volunteers.

---

## 🌟 Key Capabilities

### 1. 🎟️ Pre-Registration & Digital QR Tickets
- **Public Pre-Registration Portal**: Clean, mobile-friendly landing page with live seat capacity tracking (`/events/{id}/register`).
- **Instant Digital QR Pass**: Automatically generates a unique QR code ticket pass (`/tickets/{code}`) with high-definition QR rendering and print/save options.
- **Capacity Management**: Automatic countdown of remaining seats and waitlist/sold-out notice.

### 2. 📱 Live Attendance Marking Kiosk
- **Instant Camera QR Scanner**: Organizers and gate staff can use any webcam, tablet, or smartphone camera to scan tickets in milliseconds (`/events/{id}/checkin`).
- **Live Sound Feedback**: Built-in Web Audio API synthesizers provide instant chime feedback (success chime, warning sound on duplicate check-in, alert sound on invalid code).
- **Fast Search & 1-Click Check-In**: Instant filter by Name, Email, or Pass Code with one-click Check-In and Undo Check-In.
- **On-the-Spot Walk-In Registration**: Register unexpected attendees on-the-fly and immediately mark them present.
- **Real-Time KPIs**: Dynamic live counter for Total Registered, Checked In, Pending, and Turnout Rate %.

### 3. 💬 "Not Attending" (No-Show) Follow-Up Hub
- **Automated Absentee Filter**: Instantly detects and lists all registered participants who did not check in.
- **1-Click WhatsApp Direct Chat**: Opens pre-filled WhatsApp chats (`https://wa.me/...`) with customizable outreach templates:
  - *Template 1*: "Sorry We Missed You" (warm check-in).
  - *Template 2*: "Post-Event Presentation & Materials Sharing".
  - *Template 3*: "Reason Survey & Future Event Check".
- **Reason Categorization**: Track why attendees missed the event (Work Emergency, Medical/Health, Travel Issue, Forgot, etc.) with custom organizer notes.
- **Outreach Status Tracking**: Monitor status (`Not Contacted`, `Follow-up Sent`, `Responded`, `Excused`).

### 4. 📊 Event Final Report & Analytics
- **Executive Turnout Dashboard**: View overall attendance rate, registered vs attended ratio, and walk-in counts.
- **Interactive Visualizations**:
  - Turnout Breakdown Donut Chart.
  - Check-in Rush Curve / Arrival Hour distribution.
  - Absence Reason Breakdown Bar Chart.
- **Export to Excel (`.xlsx`)**: Generates a professional multi-sheet Excel workbook with:
  1. *Executive Summary*: Event info, capacity, and KPI metrics.
  2. *Attended Participants*: Complete list with check-in timestamps and walk-in markers.
  3. *Absentee Follow-Ups*: Contact info, follow-up status, channel, reason category, and notes.
- **Printable Executive Summary**: Clean print CSS layout ready for stakeholders or PDF saving.

---

## 🚀 Getting Started

### Option A: Quick Launch (Windows)
Double-click `run.bat` in this folder.

### Option B: Command Line
```powershell
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Seed realistic demo data (optional, but recommended for immediate testing)
python -c "import sample_data; sample_data.seed_sample_data()"

# 3. Launch application server
python main.py
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:8000`**

---

## 🛠️ Tech Architecture

- **Backend**: Python 3.14 + FastAPI + Uvicorn
- **Database**: SQLite (`events.db`) with WAL mode and indexing
- **Frontend**: Tailwind CSS + Lucide Icons + Chart.js + HTML5 QR Code Scanner
- **Ticket Generation**: `qrcode` + `Pillow` (in-memory Base64 Data URI)
- **Reporting**: `openpyxl` (styled multi-tab spreadsheets)
