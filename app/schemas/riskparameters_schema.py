from pydantic import BaseModel
from typing import Optional, List


class RiskParameters(BaseModel):
    project_id: int
    uncompleted_tasks: int = 0
    uncompleted_tasks_weight: int = 0

    detected_bugs: int = 0
    detected_bugs_weight: int = 0

    blockers_count: int = 0
    blockers_count_weight: int = 0

    developer_workload: int = 0
    developer_workload_weight: int = 0

    task_dependency: int = 0
    task_dependency_weight: int = 0

    timeline_conflict: int = 0
    timeline_conflict_weight: int = 0

    developer_availability: int = 0
    developer_availability_weight: int = 0

    task_progress: int = 0
    task_progress_weight: int = 0

    sprint_completion_level: int = 0
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