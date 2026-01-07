"""
Pydantic models for Task Updates API
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class DetectedStatus(str, Enum):
    """AI-detected task statuses"""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class ApprovalStatus(str, Enum):
    """Approval workflow statuses"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class JiraSyncStatus(str, Enum):
    """Jira synchronization statuses"""
    NOT_SYNCED = "NOT_SYNCED"
    SYNCED = "SYNCED"
    FAILED = "FAILED"


class TaskUpdateExtract(BaseModel):
    """Single extracted task update from AI"""
    ticket_id: str
    detected_status: DetectedStatus
    blocker_description: Optional[str] = None
    ai_confidence_score: float = Field(ge=0.0, le=1.0)
    ai_reasoning: str
    extracted_context: str


class TaskUpdateCreate(BaseModel):
    """Create a task update"""
    meeting_id: str
    project_id: int
    task_id: Optional[int] = None
    ticket_id: str
    detected_status: DetectedStatus
    blocker_description: Optional[str] = None
    ai_confidence_score: float = 0.0
    ai_reasoning: Optional[str] = None
    extracted_context: Optional[str] = None


class TaskUpdateApproval(BaseModel):
    """Approve/reject a task update"""
    reviewer_remark:Optional[str] = None


class TaskUpdateResponse(BaseModel):
    """Response model for task update"""
    id: int
    meeting_id: str
    ticket_id: str
    task_id: Optional[int]
    project_id: int
    detected_status: DetectedStatus
    blocker_description: Optional[str]
    ai_confidence_score: float
    ai_reasoning: Optional[str]
    extracted_context: Optional[str]
    approval_status: ApprovalStatus
    reviewed_by: Optional[str]
    review_timestamp: Optional[datetime]
    reviewer_remark: Optional[str]
    jira_sync_status: JiraSyncStatus
    jira_sync_timestamp: Optional[datetime]
    jira_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExtractionResponse(BaseModel):
    """Response from AI extraction"""
    meeting_id: str
    total_extracted: int
    extractions: List[TaskUpdateExtract]
    processing_time_ms: float
