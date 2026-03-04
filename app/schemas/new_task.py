"""
New Tasks Schemas

Pydantic models for new tasks from brainstorming reports.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class NewTaskStatus(str, Enum):
    """New task status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REMOVED = "removed"


class NewTaskCreate(BaseModel):
    """Schema for creating a new task"""
    report_id: int
    transcript_id: int
    project_id: Optional[int] = None
    task_title: str = Field(..., max_length=500)
    assignee: Optional[str] = Field(default=None, max_length=255)
    due_date: Optional[str] = Field(default=None, max_length=50)
    priority: Optional[str] = Field(default=None, max_length=50)


class NewTaskUpdate(BaseModel):
    """Schema for updating a new task"""
    task_title: Optional[str] = Field(default=None, max_length=500)
    assignee: Optional[str] = Field(default=None, max_length=255)
    due_date: Optional[str] = Field(default=None, max_length=50)
    priority: Optional[str] = Field(default=None, max_length=50)
    status: Optional[NewTaskStatus] = None


class NewTaskResponse(BaseModel):
    """Schema for new task response"""
    id: int
    report_id: int
    transcript_id: int
    project_id: Optional[int] = None
    task_title: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: NewTaskStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NewTaskListResponse(BaseModel):
    """Schema for new task list response"""
    tasks: List[NewTaskResponse]
    total: int
    page: int = 1
    page_size: int = 20


class NewTaskFilterParams(BaseModel):
    """Schema for new task filter parameters"""
    status: Optional[NewTaskStatus] = None
    report_id: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
