from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal


class ProjectBase(BaseModel):
    Project_Name: str
    Project_Description: Optional[str] = None
    Project_Owner: str
    Start_Date: date
    End_Date: date
    Budget: Decimal
    TeamMembers_Categories: Optional[str] = None
    Team_Members: Optional[str] = None
    Tech_Stack: Optional[str] = None
    Jira_ProjectId: Optional[str] = None
    GitHubRepoUrl: Optional[str] = None
    CI_CD_Tool: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class Project(ProjectBase):
    Project_Id: int

    class Config:
        from_attributes = True
