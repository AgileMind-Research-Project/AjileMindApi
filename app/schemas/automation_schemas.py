
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AutomationApprovalBase(BaseModel):
    project_id: int
    sprint_id: int
    backlog_prioritize: bool = False
    split_tasks: bool = False
    assign_tasks: bool = False

class AutomationApprovalCreate(AutomationApprovalBase):
    pass

class AutomationApprovalUpdate(BaseModel):
    backlog_prioritize: Optional[bool] = None
    split_tasks: Optional[bool] = None
    assign_tasks: Optional[bool] = None
    approved_by: Optional[str] = None

class AutomationApprovalResponse(AutomationApprovalBase):
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
