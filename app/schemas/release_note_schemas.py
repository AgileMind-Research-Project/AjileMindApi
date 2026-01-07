from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum

class ReleaseType(str, Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    PATCH = "PATCH"
    HOTFIX = "HOTFIX"

class ReleaseStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class ReleaseNoteContent(BaseModel):
    features: List[str] = Field(default_factory=list, description="New features added in this release")
    bug_fixes: List[str] = Field(default_factory=list, description="Bugs fixed in this release")
    improvements: List[str] = Field(default_factory=list, description="Performance or UX improvements")
    breaking_changes: List[str] = Field(default_factory=list, description="Breaking changes that affect compatibility")
    known_issues: List[str] = Field(default_factory=list, description="Known issues in this release")

class CreateReleaseNoteRequest(BaseModel):
    project_id: int = Field(..., description="Project ID for this release note")
    version: str = Field(..., min_length=1, max_length=50, description="Semantic version (e.g., 1.0.0)")
    title: str = Field(..., min_length=1, max_length=255, description="Release title")
    release_date: Optional[date] = Field(None, description="Scheduled or actual release date")
    release_type: ReleaseType = Field(ReleaseType.MINOR, description="Type of release")
    content: ReleaseNoteContent = Field(..., description="Structured release content")
    summary: Optional[str] = Field(None, description="Executive summary of the release")

class UpdateReleaseNoteRequest(BaseModel):
    version: Optional[str] = Field(None, min_length=1, max_length=50)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    release_date: Optional[date] = None
    release_type: Optional[ReleaseType] = None
    content: Optional[ReleaseNoteContent] = None
    summary: Optional[str] = None

class ReleaseNoteResponse(BaseModel):
    id: int
    project_id: int
    version: str
    title: str
    release_date: Optional[date]
    release_type: str
    content: Dict[str, Any]
    summary: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    published_by: Optional[str]
    
    class Config:
        from_attributes = True

class GenerateReleaseNoteRequest(BaseModel):
    project_id: int = Field(..., description="Project ID to generate release notes for")
    version: str = Field(..., description="Version number for this release")
    include_tasks: bool = Field(True, description="Include project tasks in AI analysis")
    since_date: Optional[date] = Field(None, description="Only analyze items after this date")
