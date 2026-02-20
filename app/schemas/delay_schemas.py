"""
Delay Analysis Schemas

Pydantic models for project delay analysis API responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class SprintBreakdownItem(BaseModel):
    """Sprint-level breakdown for delay analysis"""
    sprint_id: int
    sprint_name: str
    start_date: str
    end_date: str
    status: str
    planned_story_points: int
    completed_story_points: int
    completion_rate: float = Field(..., description="Percentage of story points completed")
    velocity: float = Field(..., description="Sprint velocity (story points completed)")
    total_hours: int
    leave_hours: int
    availability: float = Field(..., description="Developer availability percentage")


class DelayAnalysisResponse(BaseModel):
    """Comprehensive delay analysis response"""
    
    # Project identification
    project_id: int
    project_name: str
    project_key: str
    
    # Date information
    project_start_date: str
    planned_end_date: str
    current_date: str
    forecasted_end_date: str
    
    # Sprint configuration
    sprint_size_weeks: int = Field(..., description="Sprint size in weeks from project configuration")
    sprint_size_days: int = Field(..., description="Sprint size in days")
    
    # Sprint delay metrics (primary calculation)
    planned_total_sprints: float = Field(..., description="Total sprints planned for project")
    expected_sprints_by_now: float = Field(..., description="Expected sprints completed by current date")
    completed_sprints: int = Field(..., description="Actual completed sprints")
    sprint_delay: float = Field(..., description="Sprint delay (expected - actual)")
    
    # Delay metrics
    delay_days: float = Field(..., description="Adjusted delay in days")
    delay_percentage: float = Field(..., description="Delay as percentage of project duration")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, or CRITICAL")
    
    # Project metrics
    project_duration_days: int
    days_elapsed: int = Field(..., description="Days elapsed since project start")
    
    # Story points
    total_story_points: int
    completed_story_points: int
    remaining_story_points: int
    story_point_completion_rate: float = Field(..., description="Percentage of story points completed")
    
    # Velocity metrics
    expected_velocity: float = Field(..., description="Expected story points per sprint")
    actual_velocity: float = Field(..., description="Actual story points per sprint")
    velocity_variance: float = Field(..., description="Difference between actual and expected velocity")
    
    # Availability metrics
    total_planned_hours: int
    total_leave_hours: int
    availability_ratio: float = Field(..., description="Developer availability ratio (0-1)")
    
    # Sprint breakdown
    sprint_breakdown: List[SprintBreakdownItem]
    
    # Optional message
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 10001,
                "project_name": "E-Commerce Platform",
                "project_key": "ECOM",
                "project_start_date": "2026-01-01",
                "planned_end_date": "2026-06-30",
                "current_date": "2026-03-15",
                "forecasted_end_date": "2026-07-15",
                "sprint_size_weeks": 2,
                "sprint_size_days": 14,
                "planned_total_sprints": 12.93,
                "expected_sprints_by_now": 5.29,
                "completed_sprints": 4,
                "sprint_delay": 1.29,
                "delay_days": 18.5,
                "delay_percentage": 10.2,
                "risk_level": "MEDIUM",
                "project_duration_days": 181,
                "days_elapsed": 74,
                "total_story_points": 250,
                "completed_story_points": 95,
                "remaining_story_points": 155,
                "story_point_completion_rate": 38.0,
                "expected_velocity": 19.34,
                "actual_velocity": 23.75,
                "velocity_variance": 4.41,
                "total_planned_hours": 1600,
                "total_leave_hours": 80,
                "availability_ratio": 0.95,
                "sprint_breakdown": []
            }
        }


class DelayAnalysisErrorResponse(BaseModel):
    """Error response for delay analysis"""
    success: bool = False
    error: str
    project_id: Optional[int] = None
