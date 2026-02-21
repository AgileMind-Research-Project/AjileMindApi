"""
Transcript Schemas

Pydantic models for transcript management.
"""

from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


class TranscriptCategory(str, Enum):
    """Transcript category types"""
    DAILY_STANDUP = "daily_standup"
    SPRINT_MEETING = "sprint_meeting"
    SPRINT_PLANNING = "sprint_planning"
    RETROSPECTIVE = "retrospective"
    BRAINSTORMING = "brainstorming"


class TranscriptCreate(BaseModel):
    """Schema for creating a new transcript"""
    title: str = Field(..., min_length=1, max_length=255)
    category: TranscriptCategory
    transcript_content: str = Field(..., min_length=1)
    transcript_date: date
    tags: Optional[List[str]] = Field(default=None)
    file_name: Optional[str] = Field(default=None, max_length=255)
    project_id: Optional[int] = Field(default=None)


class TranscriptUpdate(BaseModel):
    """Schema for updating a transcript"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[TranscriptCategory] = None
    transcript_content: Optional[str] = Field(None, min_length=1)
    transcript_date: Optional[date] = None
    tags: Optional[List[str]] = None



class TranscriptResponse(BaseModel):
    """Schema for transcript response"""
    id: int
    title: str
    category: TranscriptCategory
    transcript_content: str
    transcript_date: date
    tags: Optional[List[str]] = None
    file_name: Optional[str] = None
    project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TranscriptListItem(BaseModel):
    """Schema for transcript list item (includes content for preview)"""
    id: int
    title: str
    category: TranscriptCategory
    transcript_content: Optional[str] = None
    transcript_date: date
    tags: Optional[List[str]] = None
    file_name: Optional[str] = None
    project_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptListResponse(BaseModel):
    """Schema for transcript list response"""
    transcripts: List[TranscriptListItem]
    total: int
    page: int = 1
    page_size: int = 20


class TranscriptFilterParams(BaseModel):
    """Schema for transcript filter parameters"""
    category: Optional[TranscriptCategory] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
