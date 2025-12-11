"""
OTP Schemas

Pydantic models for OTP verification requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.utils.password import validate_password


class SendOTPRequest(BaseModel):
    """Request to send OTP to email"""
    email: EmailStr = Field(..., description="Email address to send OTP to")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class SendOTPResponse(BaseModel):
    """Response after sending OTP"""
    success: bool = True
    message: str = "OTP sent successfully"
    data: dict = Field(
        ..., 
        description="Contains token and masked email"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP sent successfully to your email",
                "data": {
                    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "email": "u***@example.com",
                    "expires_in": 300
                }
            }
        }


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP"""
    token: str = Field(..., description="JWT token received after sending OTP")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    
    @field_validator('otp')
    @classmethod
    def validate_otp_format(cls, v):
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        if len(v) != 6:
            raise ValueError('OTP must be exactly 6 digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "otp": "123456"
            }
        }


class VerifyOTPResponse(BaseModel):
    """Response after verifying OTP"""
    success: bool = True
    message: str = "OTP verified successfully"
    data: dict = Field(
        ...,
        description="Contains verification token for password setup"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "OTP verified successfully",
                "data": {
                    "verification_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "email": "user@example.com"
                }
            }
        }


class CompleteRegistrationRequest(BaseModel):
    """Request to complete registration with password"""
    verification_token: str = Field(..., description="Token received after OTP verification")
    company_name: str = Field(..., min_length=3, max_length=100, description="Company name")
    password: str = Field(..., min_length=8, description="User password")
    password_confirmation: str = Field(..., min_length=8, description="Password confirmation")
    
    @field_validator('password')
    @classmethod
    def validate_password_policy(cls, v):
        is_valid, errors = validate_password(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v
    
    @field_validator('password_confirmation')
    @classmethod
    def passwords_match(cls, v, values):
        if 'password' in values.data and v != values.data['password']:
            raise ValueError('Passwords do not match')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "verification_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "company_name": "Acme Corporation",
                "password": "SecurePass123!",
                "password_confirmation": "SecurePass123!"
            }
        }


class CompleteRegistrationResponse(BaseModel):
    """Response after completing registration"""
    success: bool = True
    message: str = "Registration completed successfully"
    data: dict = Field(
        ...,
        description="Contains user and tenant information"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Registration completed successfully",
                "data": {
                    "user_id": "usr_123456",
                    "email": "user@example.com",
                    "tenant_id": "tnt_123456",
                    "company_name": "Acme Corporation"
                }
            }
        }


class ResendOTPRequest(BaseModel):
    """Request to resend OTP"""
    token: str = Field(..., description="Previous JWT token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class OTPErrorResponse(BaseModel):
    """Error response for OTP operations"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "Invalid or expired OTP",
                "error_code": "OTP_INVALID"
            }
        }
