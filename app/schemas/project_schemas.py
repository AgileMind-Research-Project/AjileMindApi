"""
Project Schemas

Pydantic models for project creation and management.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from enum import Enum


class ProjectType(str, Enum):
    """Supported Jira project types"""
    SOFTWARE = "software"
    BUSINESS = "business"
    SERVICE_DESK = "service_desk"


class ProjectTemplate(str, Enum):
    """Jira project templates"""
    SCRUM = "com.pyxis.greenhopper.jira:gh-scrum-template"
    KANBAN = "com.pyxis.greenhopper.jira:gh-kanban-template"
    CLASSIC = "com.atlassian.jira-core-project-templates:jira-core-project-management"


class CreateProjectRequest(BaseModel):
    """Request model for creating a new project"""
    project_name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Name of the project"
    )
    key: str = Field(
        ..., 
        min_length=2, 
        max_length=10, 
        description="Project key (2-10 uppercase letters, manually entered)",
        pattern="^[A-Z][A-Z0-9]*$"
    )
    project_type: ProjectType = Field(
        default=ProjectType.SOFTWARE, 
        description="Type of project (software, business, service_desk)"
    )
    start_date: date = Field(..., description="Project start date")
    end_date: date = Field(..., description="Project end date")
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Project description"
    )
    template: ProjectTemplate = Field(
        default=ProjectTemplate.SCRUM,
        description="Project template (Scrum, Kanban, Classic)"
    )
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        """Validate that end date is after start date"""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('key')
    def validate_key_format(cls, v):
        """Validate project key format"""
        if not v.isupper():
            raise ValueError('Project key must be uppercase')
        if len(v) < 2 or len(v) > 10:
            raise ValueError('Project key must be 2-10 characters')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Agile Scrum Project 2025",
                "key": "ASP2025",
                "project_type": "software",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "description": "Scrum project for development team",
                "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
            }
        }


class ProjectResponse(BaseModel):
    """Response model for project data"""
    project_id: int
    project_name: str
    key: str
    project_type: str
    start_date: date
    end_date: date
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    jira_url: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class CreateProjectResponse(BaseModel):
    """Response model for project creation"""
    success: bool
    message: str
    data: Dict[str, Any]


class ProjectListResponse(BaseModel):
    """Response model for listing projects"""
    success: bool
    message: str
    data: List[ProjectResponse]
    total: int
    page: int
    limit: int


class UpdateProjectRequest(BaseModel):
    """Request model for updating project"""
    project_name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        """Validate that end date is after start date"""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v


class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
