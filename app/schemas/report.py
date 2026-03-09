"""
Report Schemas

Pydantic models for AI-generated reports.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class ReportType(str, Enum):
    """Report type enumeration"""
    DAILY_STANDUP = "daily_standup"
    SPRINT_MEETING = "sprint_meeting"
    RETROSPECTIVE = "retrospective"
    BRAINSTORMING = "brainstorming"


class ReportStatus(str, Enum):
    """Report status enumeration"""
    DRAFT = "draft"
    PUBLISHED = "published"


class PersonUpdate(BaseModel):
    """A single person's update in a standup (legacy)"""
    name: str
    tasks: List[str] = Field(default_factory=list)


class DeveloperUpdate(BaseModel):
    """A single developer's full standup entry"""
    name: str
    role: Optional[str] = None
    yesterday_tasks: List[str] = Field(default_factory=list)
    today_tasks: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)


class BlockerSummary(BaseModel):
    """Summary of a shared blocker across multiple team members"""
    title: str
    description: str = ""
    reported_by: List[str] = Field(default_factory=list)
    impact: str = ""


class DailyStandupReport(BaseModel):
    """Daily Standup Report – developer-centric with per-person yesterday/today/blockers"""
    team_updates: List[DeveloperUpdate] = Field(default_factory=list)
    blockers_summary: List[BlockerSummary] = Field(default_factory=list)
    # Legacy fields kept for backward compatibility with old reports
    yesterday_work: Optional[List[PersonUpdate]] = None
    today_plan: Optional[List[PersonUpdate]] = None


class ActionItem(BaseModel):
    """Action item structure"""
    task: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None


class SprintMeetingReport(BaseModel):
    """Sprint Meeting Report structure"""
    sprint_goals: List[str] = Field(default_factory=list)
    progress_summary: str = ""
    issues_risks: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)


class RetrospectiveReport(BaseModel):
    """Retrospective Report structure"""
    what_went_well: List[str] = Field(default_factory=list)
    what_didnt_go_well: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    action_points: List[ActionItem] = Field(default_factory=list)


class BrainstormingIdea(BaseModel):
    """Brainstorming idea structure"""
    idea: str
    proposed_by: Optional[str] = None
    category: Optional[str] = None
    votes: int = 0


class Decision(BaseModel):
    """Decision structure for brainstorming meetings"""
    decision: str
    assignee: Optional[str] = None


class BrainstormingMeetingReport(BaseModel):
    """Brainstorming Meeting Summary Report structure"""
    meeting_topic: str = ""
    meeting_objective: str = ""
    participants: List[str] = Field(default_factory=list)
    ideas_generated: List[BrainstormingIdea] = Field(default_factory=list)
    top_ideas: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    key_themes: List[str] = Field(default_factory=list)
    decisions_made: List[Decision] = Field(default_factory=list)
    next_steps: List[ActionItem] = Field(default_factory=list)
    summary: str = ""


class ReportGenerateRequest(BaseModel):
    """Schema for generating a report"""
    transcript_id: int = Field(..., gt=0)
    template_id: Optional[int] = Field(default=None, gt=0)
    use_custom_prompt: bool = False
    custom_prompt: Optional[str] = None


class ReportUpdateRequest(BaseModel):
    """Schema for updating report content"""
    report_content: Dict[str, Any]
    status: Optional[ReportStatus] = None


class ReportResponse(BaseModel):
    """Schema for report response"""
    id: int
    transcript_id: int
    report_type: ReportType
    report_content: Dict[str, Any]
    template_id: Optional[int] = None
    version: int
    status: ReportStatus
    generated_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    """Schema for report list item"""
    id: int
    transcript_id: int
    transcript_title: Optional[str] = None
    report_type: ReportType
    version: int
    status: ReportStatus
    created_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Schema for report list response"""
    reports: List[ReportListItem]
    total: int
    page: int = 1
    page_size: int = 20


class ReportExportRequest(BaseModel):
    """Schema for report export"""
    format: str = Field(..., pattern="^(pdf|docx)$")
    include_header: bool = True
    include_footer: bool = True
    template_id: Optional[int] = None
