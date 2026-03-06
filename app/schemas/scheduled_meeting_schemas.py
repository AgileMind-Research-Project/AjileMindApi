"""
Scheduled Meeting Schemas

Pydantic request/response models for the scheduled meetings API.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date, time, datetime

# ── Scrum Meeting Categories ──────────────────────────────────────────────────

SCRUM_MEETING_CATEGORIES: List[str] = [
    "Daily Standup",
    "Sprint Planning",
    "Sprint Review",
    "Sprint Retrospective",
    "Backlog Refinement / Grooming",
    "Release Planning",
    "Stakeholder Review",
    "Technical Design Meeting",
    "Incident / Post-Mortem",
    "One-on-One",
    "Other",
]

MEETING_STATUSES: List[str] = ["SCHEDULED", "ONGOING", "COMPLETED", "CANCELLED"]


# ── Request Models ────────────────────────────────────────────────────────────

class ScheduleMeetingRequest(BaseModel):
    """Request body for creating a scheduled meeting."""

    project_id: int = Field(..., description="Project the meeting belongs to")
    sprint_id: int = Field(..., description="Sprint the meeting belongs to")
    title: str = Field(..., min_length=1, max_length=255, description="Meeting title")
    meeting_category: str = Field(..., description="Scrum meeting category")
    meeting_date: date = Field(..., description="Date of the meeting (YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time (HH:MM or HH:MM:SS)")
    end_time: str = Field(..., description="End time (HH:MM or HH:MM:SS)")
    meeting_link: Optional[str] = Field(None, max_length=500, description="Video call or room link")
    attendees: Optional[List[str]] = Field(
        default=None, description="List of attendee emails"
    )

    @validator("meeting_category")
    def validate_category(cls, v: str) -> str:
        if v not in SCRUM_MEETING_CATEGORIES:
            raise ValueError(
                f"meeting_category must be one of: {', '.join(SCRUM_MEETING_CATEGORIES)}"
            )
        return v

    @validator("end_time")
    def validate_time_range(cls, end: str, values: dict) -> str:
        start = values.get("start_time")
        if start and end:
            if end <= start:
                raise ValueError("end_time must be after start_time")
        return end


class UpdateMeetingStatusRequest(BaseModel):
    """Request body to update meeting status."""

    status: str = Field(..., description="New status")

    @validator("status")
    def validate_status(cls, v: str) -> str:
        if v not in MEETING_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(MEETING_STATUSES)}"
            )
        return v


class UpdateMeetingAttendeesRequest(BaseModel):
    """Request body to update meeting attendees."""

    attendees: List[str] = Field(..., description="List of attendee emails")


class ExtendMeetingRequest(BaseModel):
    """Request body to extend meeting end time."""

    new_end_time: str = Field(..., description="New end time (HH:MM or HH:MM:SS)")


# ── Response Models ───────────────────────────────────────────────────────────

class ScheduledMeetingResponse(BaseModel):
    """Single meeting response."""

    meeting_id: str
    project_id: int
    sprint_id: int
    title: str
    meeting_category: str
    meeting_date: str
    start_time: str
    end_time: str
    meeting_link: str
    status: str
    created_by: Optional[str] = None
    attendees: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ScheduledMeetingListResponse(BaseModel):
    """List of scheduled meetings."""

    meetings: List[ScheduledMeetingResponse]
    total: int


class MeetingCategoriesResponse(BaseModel):
    """Available meeting categories."""

    categories: List[str]
