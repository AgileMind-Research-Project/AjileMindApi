"""
Meeting Schemas
Pydantic models for meeting management
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MeetingType(str, Enum):
    """Meeting type enumeration"""
    STANDUP = "standup"
    PLANNING = "planning"
    RETROSPECTIVE = "retrospective"
    REVIEW = "review"
    GENERAL = "general"


class MeetingStatus(str, Enum):
    """Meeting status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ParticipantBase(BaseModel):
    """Base participant model"""
    user_id: str = Field(..., description="User ID")
    attended: bool = Field(default=False, description="Whether user attended")


class MeetingBase(BaseModel):
    """Base meeting model"""
    title: str = Field(..., min_length=1, max_length=255, description="Meeting title")
    description: Optional[str] = Field(None, max_length=1000, description="Meeting description")
    meeting_type: MeetingType = Field(..., description="Type of meeting")
    scheduled_date: datetime = Field(..., description="Scheduled date and time")
    duration_minutes: int = Field(..., ge=1, le=480, description="Duration in minutes (1-480)")
    location: Optional[str] = Field(None, max_length=255, description="Meeting location")
    is_virtual: bool = Field(default=False, description="Whether meeting is virtual")
    meeting_link: Optional[str] = Field(None, max_length=500, description="Virtual meeting link")


class MeetingCreate(MeetingBase):
    """Schema for creating a meeting"""
    participant_ids: List[str] = Field(default=[], description="List of participant user IDs")


class MeetingUpdate(BaseModel):
    """Schema for updating a meeting"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    meeting_type: Optional[MeetingType] = None
    scheduled_date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    location: Optional[str] = Field(None, max_length=255)
    is_virtual: Optional[bool] = None
    meeting_link: Optional[str] = Field(None, max_length=500)
    status: Optional[MeetingStatus] = None


class ParticipantResponse(ParticipantBase):
    """Participant response model"""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None


class MeetingResponse(MeetingBase):
    """Meeting response model"""
    id: str
    status: MeetingStatus
    participants: List[ParticipantResponse] = []
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """Meeting list response with pagination"""
    meetings: List[MeetingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MeetingActionResponse(BaseModel):
    """Response for meeting actions"""
    success: bool
    message: str
    data: Optional[dict] = None
