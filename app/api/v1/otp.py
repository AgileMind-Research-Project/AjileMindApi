"""
OTP API Endpoints

Handles passwordless email OTP verification for user registration.
Public endpoints that don't require authentication.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
import jwt
from datetime import datetime, timedelta

from app.schemas.otp_schemas import (
    SendOTPRequest,
    SendOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    CompleteRegistrationRequest,
    CompleteRegistrationResponse,
    ResendOTPRequest,
    OTPErrorResponse
)
from app.services.otp_service import otp_service
from app.services.auth_service import AuthService
from app.db.database import db
from app.core.logger import logger
from app.core.config import settings

router = APIRouter()


async def get_auth_service() -> AuthService:
    """Dependency to get auth service instance"""
    return AuthService(db)


def mask_email(email: str) -> str:
    """
    Mask email for privacy (e.g., u***@example.com).
    
    Args:
        email: Email address to mask
    
    Returns:
        Masked email
    """
    try:
        username, domain = email.split('@')
        if len(username) <= 2:
            masked_username = username[0] + '*' * (len(username) - 1)
        else:
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
        return f"{masked_username}@{domain}"
    except:
        return "***@***"


@router.post(
    "/send-otp",
    response_model=SendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Send OTP to Email",
    description="Send a 6-digit OTP to the user's email address for passwordless registration"
)
async def send_otp(request: SendOTPRequest) -> Dict[str, Any]:
    """
    Send OTP to user's email address.
    
    This endpoint:
    1. Generates a random 6-digit OTP
    2. Creates a JWT token containing the OTP and email
    3. Sends the OTP to the user's email
    4. Returns the JWT token (to be used for verification)
    
    **Request Body:**
    - email: Email address to send OTP to
    
    **Returns:**
    - token: JWT token containing encrypted OTP (pass to verify endpoint)
    - email: Masked email address
    - expires_in: OTP expiration time in seconds (300 = 5 minutes)
    
    **Error Responses:**
    - 400: Invalid email format
    - 500: Failed to send email
    """
    try:
        email = request.email.lower()
        
        # Generate OTP
        otp = otp_service.generate_otp()
        logger.info(f"Generated OTP for {email}: {otp}")  # For development/testing
        
        # Create JWT token with OTP
        token = otp_service.create_otp_token(email, otp)
        
        # Send OTP email
        email_sent = otp_service.send_otp_email(email, otp)
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )
        
        logger.info(f"OTP sent successfully to {email}")
        
        return {
            "success": True,
            "message": "OTP sent successfully to your email",
            "data": {
                "token": token,
                "email": mask_email(email),
                "expires_in": 300  # 5 minutes
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending OTP to {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP",
    description="Verify the OTP entered by the user"
)
async def verify_otp(request: VerifyOTPRequest) -> Dict[str, Any]:
    """
    Verify OTP entered by user.
    
    This endpoint:
    1. Decodes the JWT token
    2. Verifies the OTP matches
    3. Checks if the OTP hasn't expired
    4. Returns a verification token for password setup
    
    **Request Body:**
    - token: JWT token received from send-otp endpoint
    - otp: 6-digit OTP code entered by user
    
    **Returns:**
    - verification_token: Token to use for completing registration
    - email: User's email address
    
    **Error Responses:**
    - 400: Invalid or expired OTP
    - 401: OTP doesn't match
    """
    try:
        # Verify OTP
        is_valid, email, error_message = otp_service.verify_otp_token(
            request.token,
            request.otp
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message or "Invalid OTP"
            )
        
        # Create verification token (valid for 15 minutes to complete registration)
        verification_payload = {
            "email": email,
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "iat": datetime.utcnow(),
            "type": "email_verified"
        }
        
        verification_token = jwt.encode(
            verification_payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        logger.info(f"OTP verified successfully for {email}")
        
        return {
            "success": True,
            "message": "OTP verified successfully",
            "data": {
                "verification_token": verification_token,
                "email": email
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP. Please try again."
        )


@router.post(
    "/complete-registration",
    response_model=CompleteRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete Registration with Password",
    description="Complete the registration process by setting a password after OTP verification"
)
async def complete_registration(
    request: CompleteRegistrationRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Complete registration with password after OTP verification.
    
    This endpoint:
    1. Verifies the verification token
    2. Creates a new tenant and super admin user
    3. Sets the user's password
    4. Returns user and tenant information
    
    **Request Body:**
    - verification_token: Token received from verify-otp endpoint
    - company_name: Company name (3-100 characters)
    - password: Password (min 8 characters with policy requirements)
    - password_confirmation: Must match password
    
    **Returns:**
    - user_id: Created user ID
    - email: User email
    - tenant_name: Created tenant domain name
    - company_name: Company name
    - tokens: JWT access and refresh tokens for immediate login
    
    **Error Responses:**
    - 400: Invalid or expired verification token
    - 409: Email already registered
    - 422: Validation error (weak password, mismatched passwords)
    """
    try:
        # Decode verification token
        try:
            payload = jwt.decode(
                request.verification_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Verification token has expired. Please start again."
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification token"
            )
        
        # Verify token type
        if payload.get("type") != "email_verified":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Create tenant and user
        result = await auth_service.register_tenant(
            company_name=request.company_name,
            email=email,
            password=request.password
        )
        
        logger.info(f"Registration completed for {email} - Tenant: {result['tenant_name']}")
        
        return {
            "success": True,
            "message": "Registration completed successfully. Welcome to AgileMind!",
            "data": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete registration. Please try again."
        )


@router.post(
    "/resend-otp",
    response_model=SendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend OTP",
    description="Resend OTP to the email address"
)
async def resend_otp(request: ResendOTPRequest) -> Dict[str, Any]:
    """
    Resend OTP to user's email address.
    
    This endpoint:
    1. Decodes the previous token to get the email
    2. Generates a new OTP
    3. Creates a new JWT token
    4. Sends the new OTP to the email
    
    **Request Body:**
    - token: Previous JWT token (can be expired)
    
    **Returns:**
    - token: New JWT token
    - email: Masked email address
    - expires_in: OTP expiration time in seconds
    """
    try:
        # Decode token to get email (ignore expiration)
        try:
            payload = jwt.decode(
                request.token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": False}  # Don't verify expiration
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Generate new OTP
        otp = otp_service.generate_otp()
        logger.info(f"Regenerated OTP for {email}: {otp}")  # For development/testing
        
        # Create new JWT token
        token = otp_service.create_otp_token(email, otp)
        
        # Send OTP email
        email_sent = otp_service.send_otp_email(email, otp)
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )
        
        logger.info(f"OTP resent successfully to {email}")
        
        return {
            "success": True,
            "message": "OTP resent successfully to your email",
            "data": {
                "token": token,
                "email": mask_email(email),
                "expires_in": 300
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend OTP. Please try again."
        )
