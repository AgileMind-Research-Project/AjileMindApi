from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class DowntimeType(str, Enum):
    PLANNED_MAINTENANCE = "PLANNED_MAINTENANCE"
    EMERGENCY_OUTAGE = "EMERGENCY_OUTAGE"
    FEATURE_UPGRADE = "FEATURE_UPGRADE"
    SERVICE_DEGRADATION = "SERVICE_DEGRADATION"

class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Audience(str, Enum):
    ALL_USERS = "ALL_USERS"
    INTERNAL_TEAM = "INTERNAL_TEAM"
    PROJECT_MEMBERS = "PROJECT_MEMBERS"
    ADMINS = "ADMINS"

class Schedule(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str

class Content(BaseModel):
    subject: str
    message_body: str

class DowntimeNotificationRequest(BaseModel):
    type: DowntimeType
    priority: Priority
    affected_components: List[str]
    schedule: Schedule
    audience: Audience
    project_id: Optional[int] = None # Added based on requirements to select project
    content: Content
    scheduled_at: Optional[datetime] = None  # New field for scheduling send time
    sender_id: Optional[str] = None # Can be inferred from token

class NotificationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
