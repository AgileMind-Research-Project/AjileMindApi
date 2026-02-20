"""
Authentication Schemas

Pydantic models for authentication requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from app.utils.password import validate_password


class TenantRegisterRequest(BaseModel):
    """Tenant registration request from Platform Home"""
    company_name: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    password_confirmation: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password_policy(cls, v):
        is_valid, errors = validate_password(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v
    
    @validator('password_confirmation')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User data response"""
    user_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    tenant_id: str
    tenant_name: Optional[str] = None
    status: str = "ACTIVE"


class LoginResponse(BaseModel):
    """Login response"""
    success: bool = True
    message: str = "Login successful"
    data: dict


class TenantRegisterResponse(BaseModel):
    """Tenant registration response"""
    success: bool = True
    message: str = "Tenant created successfully"
    data: dict


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response"""
    success: bool = True
    data: dict


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    new_password_confirmation: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        is_valid, errors = validate_password(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v
    
    @validator('new_password_confirmation')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class VerifyPasswordRequest(BaseModel):
    """Verify current password request"""
    current_password: str = Field(..., min_length=1, description="Current password to verify")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "MySecurePassword123!"
            }
        }


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str
    new_password: str = Field(..., min_length=8)
    new_password_confirmation: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        is_valid, errors = validate_password(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v
    
    @validator('new_password_confirmation')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class InviteUserRequest(BaseModel):
    """Invite user request"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: str = Field(..., min_length=1, max_length=50)


class InviteUserResponse(BaseModel):
    """Invite user response"""
    success: bool = True
    message: str = "User invited successfully"
    data: dict


class ValidatePasswordRequest(BaseModel):
    """Validate password request"""
    password: str


class ValidatePasswordResponse(BaseModel):
    """Validate password response"""
    success: bool = True
    data: dict


class StandardResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    errors: Optional[dict] = None
