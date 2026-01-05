from datetime import date, time, datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class MeetingStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: Optional[int] = None
    date: date
    start_time: time
    end_time: time
    category: str = "Daily Meeting"
    attendees: Optional[List[str]] = [] # List of user emails or IDs

class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[MeetingStatus] = None
    category: Optional[str] = None
    meeting_transcript: Optional[str] = None
    recording_url: Optional[str] = None

class MeetingResponse(BaseModel):
    id: int
    meeting_id: str
    project_id: Optional[int]
    title: str
    description: Optional[str]
    date: date
    start_time: time
    end_time: time
    status: MeetingStatus
    category: str
    created_at: datetime
    created_by: Optional[str]
    
    class Config:
        from_attributes = True

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def parse_time(cls, v):
        if isinstance(v, timedelta):
            total_seconds = int(v.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return time(hour=hours, minute=minutes, second=seconds)
        return v
