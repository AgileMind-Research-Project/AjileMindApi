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

    project_budget: int = 0
    project_budget_weight: int = 0


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
    # Task breakdown (task_type = 'Task')
    todo_tasks: int = 0
    inprogress_tasks: int = 0
    completed_tasks_only: int = 0
    overdue_tasks: int = 0
    max_overdue_days: int = 0  # Maximum days any task is overdue
    # Task risk percentages (for insights only)
    todo_tasks_risk: float = 0.0
    inprogress_tasks_risk: float = 0.0
    overdue_tasks_risk: float = 0.0
    # Bug breakdown
    total_bugs: int
    high_priority_bugs: int = 0
    medium_priority_bugs: int = 0
    low_priority_bugs: int = 0
    # Bug status breakdown
    todo_bugs: int = 0
    inprogress_bugs: int = 0
    completed_bugs: int = 0
    # Bug risk percentages (for insights only)
    todo_bugs_risk: float = 0.0
    inprogress_bugs_risk: float = 0.0
    high_priority_bugs_risk: float = 0.0
    # Blocker breakdown
    total_blockers: int = 0
    open_blockers: int = 0
    inprogress_blockers: int = 0
    resolved_blockers: int = 0
    # Blocker severity breakdown (unresolved only)
    critical_blockers: int = 0
    high_blockers: int = 0
    medium_blockers: int = 0
    low_blockers: int = 0
    # Blocker risk percentages (for insights only)
    open_blockers_risk: float = 0.0
    inprogress_blockers_risk: float = 0.0
    resolved_blockers_risk: float = 0.0
    critical_blockers_risk: float = 0.0
    high_blockers_risk: float = 0.0
    medium_blockers_risk: float = 0.0
    low_blockers_risk: float = 0.0
    # Developer breakdown (task_type='Task' only)
    developer_breakdown: dict = None
    # Timeline conflict insights
    timeline_conflicts: list = []
    # Developer availability insights
    developer_availability_breakdown: list = []
    # Task progress insights
    sprint_progress_breakdown: list = []
    avg_completion_rate: float = 1.0
    # Sprint completion level insights
    sprint_completion_breakdown: dict = {}
    # Sprint metrics
    completed_sprints: int
    total_sprints: int
    total_leave_hours: float
    total_sprint_hours: float
    # Available developers (low workload)
    available_developers_data: dict = {}


class RiskCalculationResponse(BaseModel):
    project_id: int
    total_risk_score: float
    risk_percentage: float  # Percentage format (0-100)
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    total_weight: int
    breakdown: List[ParameterBreakdown]
    metadata: RiskMetadata
    calculated_at: str