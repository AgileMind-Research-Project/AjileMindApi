"""
User Schemas

Pydantic models for user-related requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str


class UserCreate(UserBase):
    """User creation model"""
    password: str
    tenant_id: str
    status: str = "PENDING_ACTIVATION"
    password_change_required: bool = True


class UserUpdate(BaseModel):
    """User update model"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class UserInDB(UserBase):
    """User model from database"""
    user_id: str
    tenant_id: str
    password_hash: str
    status: str
    password_change_required: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserPublic(UserBase):
    """Public user model (no sensitive data)"""
    user_id: str
    tenant_id: str
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response"""
    success: bool = True
    data: dict
