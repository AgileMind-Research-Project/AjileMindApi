"""
Recurring Bugs Schemas

Pydantic models for recurring bugs with cross-meeting detection.
Tracks bugs mentioned across retrospectives, daily standups, and sprint meetings.
"""

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Any
from enum import Enum


class RecurringBugStatus(str, Enum):
    """Recurring bug status enumeration"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    WONT_FIX = "wont_fix"


class RecurringBugSeverity(str, Enum):
    """Bug severity levels - auto-escalates with mention count"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecurringBugCategory(str, Enum):
    """Bug categories based on keyword detection"""
    PERFORMANCE = "performance"
    UI = "ui"
    API = "api"
    DATABASE = "database"
    INTEGRATION = "integration"
    SECURITY = "security"
    OTHER = "other"


class BugSource(BaseModel):
    """A source where the bug was mentioned"""
    report_id: int
    transcript_id: int
    meeting_date: str
    source_type: str  # e.g., 'retrospective_issues', 'daily_standup_blocker'


class RecurringBugUpdate(BaseModel):
    """Schema for updating a recurring bug"""
    status: Optional[RecurringBugStatus] = None
    severity: Optional[RecurringBugSeverity] = None
    resolution_notes: Optional[str] = Field(default=None, max_length=2000)
    impact_description: Optional[str] = Field(default=None, max_length=500)


class RecurringBugResponse(BaseModel):
    """Schema for recurring bug response"""
    id: int
    project_id: int
    project_name: Optional[str] = None
    bug_hash: str
    bug_description: str
    bug_category: Optional[RecurringBugCategory] = None
    first_reported_date: Any  # Can be date or string
    last_reported_date: Any  # Can be date or string
    mention_count: int = 1
    sources: List[BugSource] = []
    severity: Optional[RecurringBugSeverity] = None
    status: RecurringBugStatus = RecurringBugStatus.OPEN
    impact_description: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_date: Optional[Any] = None
    resolved_by: Optional[str] = None
    backlog_item_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecurringBugListResponse(BaseModel):
    """Schema for recurring bug list response"""
    bugs: List[RecurringBugResponse]
    total: int
    page: int = 1
    page_size: int = 20


class RecurringBugFilterParams(BaseModel):
    """Schema for recurring bug filter parameters"""
    status: Optional[RecurringBugStatus] = None
    project_id: Optional[int] = None
    min_mentions: int = Field(default=1, ge=1)
    severity: Optional[RecurringBugSeverity] = None
    category: Optional[RecurringBugCategory] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CreateBacklogFromBugRequest(BaseModel):
    """Request to create a backlog item from a recurring bug"""
    bug_id: int
    created_by: Optional[str] = None
