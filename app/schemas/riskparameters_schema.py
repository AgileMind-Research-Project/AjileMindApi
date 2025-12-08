from pydantic import BaseModel
from typing import Optional, List


class RiskParameters(BaseModel):
    project_id: int
    uncompleted_tasks: bool = False
    uncompleted_tasks_weight: int = 0

    detected_bugs: bool = False
    detected_bugs_weight: int = 0

    blockers_count: bool = False
    blockers_count_weight: int = 0

    developer_workload: bool = False
    developer_workload_weight: int = 0

    task_dependency: bool = False
    task_dependency_weight: int = 0

    timeline_conflict: bool = False
    timeline_conflict_weight: int = 0

    developer_availability: bool = False
    developer_availability_weight: int = 0

    task_progress: bool = False
    task_progress_weight: int = 0

    sprint_completion_level: bool = False
    sprint_completion_level_weight: int = 0


class ParameterBreakdown(BaseModel):
    parameter: str
    enabled: bool
    risk_score: Optional[float] = None
    weight: int
    weighted_value: Optional[float] = None
    contribution: Optional[float] = None


class RiskMetadata(BaseModel):
    total_tasks: int
    uncompleted_tasks: int
    completed_tasks: int
    blocked_tasks: int
    total_bugs: int
    completed_sprints: int
    total_sprints: int
    total_leave_hours: float
    total_sprint_hours: float


class RiskCalculationResponse(BaseModel):
    project_id: int
    total_risk_score: float
    risk_percentage: float  # Percentage format (0-100)
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    total_weight: int
    breakdown: List[ParameterBreakdown]
    metadata: RiskMetadata
    calculated_at: str