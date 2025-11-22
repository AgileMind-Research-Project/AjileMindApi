"""
Jira Integration Schemas

Request/Response models for Jira Cloud integration.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List
from datetime import datetime


class JiraCredentialsRequest(BaseModel):
    """Request model for storing Jira credentials"""
    jira_url: HttpUrl = Field(..., description="Jira Cloud URL (e.g., https://company.atlassian.net)")
    email: str = Field(..., description="Jira account email")
    api_token: str = Field(..., description="Jira API token")


class JiraCredentialsResponse(BaseModel):
    """Response model for Jira credentials"""
    success: bool
    message: str
    data: Dict[str, Any]


class JiraIssueRequest(BaseModel):
    """Request model for creating Jira issue"""
    project_key: str = Field(..., description="Jira project key")
    summary: str = Field(..., min_length=1, max_length=255, description="Issue summary")
    description: Optional[str] = Field(None, description="Issue description")
    issue_type: str = Field(default="Task", description="Issue type (Task, Story, Bug, etc.)")
    priority: Optional[str] = Field(default="Medium", description="Priority (Highest, High, Medium, Low, Lowest)")
    assignee_email: Optional[str] = Field(None, description="Assignee email")
    labels: Optional[List[str]] = Field(default=[], description="Issue labels")
    sprint_id: Optional[str] = Field(None, description="Sprint ID to add issue to")


class JiraIssueResponse(BaseModel):
    """Response model for Jira issue operations"""
    success: bool
    message: str
    data: Dict[str, Any]


class JiraSyncRequest(BaseModel):
    """Request model for syncing Jira issues"""
    project_key: str = Field(..., description="Jira project key to sync")
    jql: Optional[str] = Field(None, description="Custom JQL query")
    max_results: Optional[int] = Field(default=50, ge=1, le=100, description="Maximum results to fetch")


class JiraSyncResponse(BaseModel):
    """Response model for Jira sync"""
    success: bool
    message: str
    data: Dict[str, Any]


class JiraWebhookRequest(BaseModel):
    """Request model for Jira webhook events"""
    webhookEvent: str
    issue: Optional[Dict[str, Any]] = None
    changelog: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None


class JiraProjectsResponse(BaseModel):
    """Response model for listing Jira projects"""
    success: bool
    message: str
    data: List[Dict[str, Any]]
