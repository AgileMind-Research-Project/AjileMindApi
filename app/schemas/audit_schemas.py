"""
Audit Log Schemas

Pydantic models for audit log requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Audit event types"""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    
    # User Management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_INVITED = "user_invited"
    USER_ROLE_CHANGED = "user_role_changed"
    
    # Tenant Management
    TENANT_CREATED = "tenant_created"
    TENANT_UPDATED = "tenant_updated"
    TENANT_DELETED = "tenant_deleted"
    
    # Role Management
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    
    # Settings
    SETTINGS_UPDATED = "settings_updated"
    AUDIT_LOGGING_ENABLED = "audit_logging_enabled"
    AUDIT_LOGGING_DISABLED = "audit_logging_disabled"
    AUDIT_LOGS_CLEARED = "audit_logs_cleared"
    
    # Data Operations
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
    
    # Security
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditLogResponse(BaseModel):
    """Audit log response model"""
    log_id: str
    tenant_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    event_type: str
    event_data: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Audit log list response"""
    success: bool
    message: str
    data: dict = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class AuditLogFilterRequest(BaseModel):
    """Audit log filter request"""
    event_type: Optional[str] = None
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class AuditSettingsResponse(BaseModel):
    """Audit settings response"""
    audit_logging_enabled: bool
    retention_days: int = 90
    
    class Config:
        from_attributes = True


class AuditSettingsUpdateRequest(BaseModel):
    """Update audit settings"""
    audit_logging_enabled: bool
    retention_days: Optional[int] = Field(default=90, ge=1, le=365)


class ClearAuditLogsRequest(BaseModel):
    """Clear audit logs request"""
    log_ids: Optional[List[str]] = None  # If None, clear all
    before_date: Optional[datetime] = None  # Clear logs before this date


class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[dict] = None
    
    class Config:
        from_attributes = True
