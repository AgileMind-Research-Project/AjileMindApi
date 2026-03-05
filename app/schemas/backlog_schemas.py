"""
Backlog Schemas

Pydantic models for backlog item validation and serialization.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class IssueType(str, Enum):
    """Backlog issue types"""
    EPIC = "epic"
    STORY = "story"
    FEATURE = "feature"
    TASK = "task"
    CHANGE = "change"
    BUG = "bug"
    SUB_TASK = "sub_task"


class Priority(str, Enum):
    """Priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(str, Enum):
    """Backlog item status"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class BacklogItemBase(BaseModel):
    """Base backlog item fields"""
    summary: str = Field(..., max_length=255, description="Backlog item title")
    description: Optional[str] = Field(None, description="Detailed description")
    issue_type: IssueType = Field(..., description="Type: epic, story, feature, task, change, bug, or sub_task")
    priority: Optional[Priority] = Field(None, description="Priority level")
    assignee: Optional[str] = Field(None, max_length=255, description="Assigned person")
    tags: Optional[List[str]] = Field(None, description="Tags/labels")
    severity: Optional[str] = Field(None, max_length=100, description="Severity (required for bugs)")

    @validator('severity')
    def validate_severity(cls, v, values):
        """Severity is required for bugs"""
        if values.get('issue_type') == IssueType.BUG and not v:
            raise ValueError('Severity is required for bug type issues')
        return v


class BacklogItemCreate(BacklogItemBase):
    """Create backlog item request"""
    project_id: int = Field(..., description="Project ID this item belongs to")


class BacklogItemFromFile(BaseModel):
    """Backlog item parsed from Excel/CSV file"""
    summary: str
    description: Optional[str] = None
    issue_type: str  # Will be validated and converted to IssueType
    priority: Optional[str] = None
    assignee: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated string from file
    severity: Optional[str] = None

    def to_create_request(self, project_id: int) -> BacklogItemCreate:
        """Convert file data to create request"""
        # Parse tags from comma-separated string
        tags_list = None
        if self.tags:
            tags_list = [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        
        return BacklogItemCreate(
            project_id=project_id,
            summary=self.summary,
            description=self.description,
            issue_type=IssueType(self.issue_type.lower()),
            priority=Priority(self.priority.lower()) if self.priority else None,
            assignee=self.assignee,
            tags=tags_list,
            severity=self.severity
        )


class BacklogItemResponse(BacklogItemBase):
    """Backlog item response"""
    id: str = Field(..., description="Jira issue key (e.g., PROJ-123)")
    project_id: int
    parent_task_id: Optional[str] = Field(None, description="Parent task ID if this is a subtask")
    status: Status
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BulkUploadRequest(BaseModel):
    """Bulk upload request"""
    project_id: int = Field(..., description="Project to create backlog items for")
    items: List[BacklogItemFromFile] = Field(..., description="List of backlog items from file")


class BulkUploadResponse(BaseModel):
    """Bulk upload response"""
    success: bool
    message: str
    items_processed: int
    items_created: int
    jira_issues_created: List[str] = Field(default_factory=list)
    errors: Optional[List[str]] = None


class BacklogListResponse(BaseModel):
    """List backlog items response"""
    success: bool
    data: List[BacklogItemResponse]
    total: int


class BacklogItemUpdate(BaseModel):
    """Update backlog item request"""
    summary: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    assignee: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    severity: Optional[str] = Field(None, max_length=100)


class MergeBacklogItemsRequest(BaseModel):
    """Request to merge multiple backlog items into one"""
    target_item_id: str = Field(..., description="The ID of the item to keep and update")
    source_item_ids: List[str] = Field(..., description="List of item IDs to merge into the target and then delete")
    updates: BacklogItemUpdate = Field(..., description="The new data for the target item")


class SubtaskCreateRequest(BaseModel):
    """Request model for creating a subtask"""
    parent_item_id: str = Field(..., description="ID of the parent backlog item")
    summary: str = Field(..., max_length=255, description="Subtask title")
    description: Optional[str] = Field(None, description="Detailed description")
    priority: Optional[Priority] = Field(None, description="Priority level")
    assignee: Optional[str] = Field(None, max_length=255, description="Assigned person")
    tags: Optional[List[str]] = Field(None, description="Tags/labels")
    severity: Optional[str] = Field(None, max_length=100, description="Severity (optional)")
