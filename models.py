from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class FormFieldConfig(BaseModel):
    id: str
    label: str
    type: str = "text" # text, number, tel, email, select, textarea, checkbox
    required: bool = False
    enabled: bool = True
    options: Optional[List[str]] = []
    placeholder: Optional[str] = ""
    is_standard: bool = False

class EventFormConfigUpdate(BaseModel):
    fields: List[FormFieldConfig]

class EventCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = ""
    category: Optional[str] = "Conference"
    event_date: str = Field(..., description="YYYY-MM-DD")
    start_time: Optional[str] = "09:00"
    end_time: Optional[str] = "17:00"
    venue: Optional[str] = "Main Auditorium"
    location_type: Optional[str] = "In-Person"
    banner_url: Optional[str] = ""
    max_capacity: Optional[int] = 100
    status: Optional[str] = "Upcoming"

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue: Optional[str] = None
    location_type: Optional[str] = None
    banner_url: Optional[str] = None
    max_capacity: Optional[int] = None
    status: Optional[str] = None

class AttendeeRegister(BaseModel):
    event_id: int
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., max_length=150)
    phone: Optional[str] = ""
    organization: Optional[str] = ""
    role: Optional[str] = ""
    notes: Optional[str] = ""
    custom_data: Optional[Dict[str, Any]] = {}

class WalkinRegister(BaseModel):
    event_id: int
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., max_length=150)
    phone: Optional[str] = ""
    organization: Optional[str] = ""
    role: Optional[str] = ""
    auto_checkin: bool = True

class CheckinRequest(BaseModel):
    ticket_code: Optional[str] = None
    attendee_id: Optional[int] = None
    event_id: int
    action: str = "checkin" # checkin or checkout

class FollowupUpdate(BaseModel):
    attendee_id: int
    event_id: int
    status: str # Not Contacted, Follow-up Sent, Responded, Excused
    channel: Optional[str] = "WhatsApp"
    reason_category: Optional[str] = "Not Specified"
    notes: Optional[str] = ""
