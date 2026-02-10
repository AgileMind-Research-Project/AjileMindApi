"""
Authentication API Endpoints

Handles user authentication, registration, and password management.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    TenantRegisterRequest,
    TenantRegisterResponse,
    ChangePasswordRequest,
    VerifyPasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    InviteUserRequest,
    InviteUserResponse,
    StandardResponse,
    ErrorResponse
)
from app.services.auth_service import AuthService
from app.db.database import db
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token

router = APIRouter()


async def get_auth_service() -> AuthService:
    """Dependency to get auth service instance"""
    return AuthService(db)


@router.post(
    "/register",
    response_model=TenantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Tenant",
    description="Register a new tenant (company) with super admin user from Platform Home"
)
async def register_tenant(
    request: TenantRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Register new tenant and create super admin user.
    
    This endpoint is called from the Platform Home registration form.
    It creates:
    - New tenant record
    - Super admin user
    - JWT tokens for immediate login
    
    Returns:
    - Tenant information
    - User profile
    - JWT tokens
    - Redirect URL to dashboard
    """
    try:
        result = await auth_service.register_tenant(
            company_name=request.company_name,
            email=request.email,
            password=request.password
        )
        
        return {
            "success": True,
            "message": "Tenant registered successfully",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User Login",
    description="Authenticate user and return JWT tokens"
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Authenticate user with email and password.
    
    Returns:
    - User profile
    - JWT access token
    - JWT refresh token
    - Password change requirement flag
    """
    try:
        result = await auth_service.login(
            email=request.email,
            password=request.password
        )
        
        return {
            "success": True,
            "message": "Login successful",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh Access Token",
    description="Get new access token using refresh token"
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.
    
    Returns:
    - New JWT access token
    - New JWT refresh token
    """
    try:
        # TODO: Implement refresh token logic
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Refresh token endpoint not yet implemented"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post(
    "/change-password",
    response_model=StandardResponse,
    summary="Change Password",
    description="Change user password (requires current password)"
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Change user password.
    
    Requires:
    - JWT authentication
    - Current password
    - New password
    - New password confirmation
    
    Returns:
    - Success status
    - Password change requirement cleared
    """
    try:
        # Validate new passwords match
        if request.new_password != request.new_password_confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match"
            )
        
        # Get tenant_name from JWT token
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: missing tenant information"
            )
        
        # Change password
        await auth_service.change_password(
            user_id=current_user["user_id"],
            current_password=request.current_password,
            new_password=request.new_password,
            tenant_name=tenant_name
        )
        
        return {
            "success": True,
            "message": "Password changed successfully",
            "data": {
                "password_change_required": False
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post(
    "/verify-current-password",
    response_model=StandardResponse,
    summary="Verify Current Password",
    description="Verify if the provided password matches the current user's password"
)
async def verify_current_password(
    request: VerifyPasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Verify current password.
    
    Requires:
    - JWT authentication
    - current_password in request body
    
    Returns:
    - is_valid: boolean indicating if password is correct
    """
    try:
        from app.utils.password import verify_password
        from app.db.repositories.tenant_user_repository import TenantUserRepository
        
        if not request.current_password:
            return {
                "success": True,
                "message": "Password verification",
                "data": {
                    "is_valid": False
                }
            }
        
        # Get tenant_name from JWT token
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            return {
                "success": True,
                "message": "Password verification",
                "data": {
                    "is_valid": False
                }
            }
        
        # Get user from tenant-specific repository
        tenant_user_repo = TenantUserRepository(db)
        user = await tenant_user_repo.get_user_by_id(tenant_name, current_user["user_id"])
        
        if not user:
            return {
                "success": True,
                "message": "Password verification",
                "data": {
                    "is_valid": False
                }
            }
        
        # Verify password
        is_valid = verify_password(request.current_password, user["password_hash"])
        
        logger.info(f"Password verification for user {current_user['user_id']}: {is_valid}")
        
        return {
            "success": True,
            "message": "Password verification",
            "data": {
                "is_valid": is_valid
            }
        }
    except Exception as e:
        logger.error(f"Verify password error: {str(e)}")
        return {
            "success": True,
            "message": "Password verification",
            "data": {
                "is_valid": False
            }
        }


@router.post(
    "/forgot-password",
    response_model=StandardResponse,
    summary="Forgot Password",
    description="Initiate password reset process"
)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Initiate password reset process.
    
    Sends password reset email with token.
    Always returns success (security - don't reveal if email exists).
    """
    try:
        await auth_service.forgot_password(email=request.email)
        
        return {
            "success": True,
            "message": "If the email exists, a password reset link has been sent",
            "data": None
        }
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        # Always return success for security
        return {
            "success": True,
            "message": "If the email exists, a password reset link has been sent",
            "data": None
        }


@router.post(
    "/reset-password",
    response_model=StandardResponse,
    summary="Reset Password",
    description="Reset password using token from email"
)
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Reset password using token.
    
    Requires:
    - Reset token (from email)
    - New password
    - New password confirmation
    """
    try:
        await auth_service.reset_password(
            token=request.token,
            new_password=request.new_password
        )
        
        return {
            "success": True,
            "message": "Password reset successful. Please login with your new password.",
            "data": None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post(
    "/invite",
    response_model=InviteUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite User",
    description="Invite new user to tenant"
)
async def invite_user(
    request: InviteUserRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Invite new user to tenant.
    
    Creates user with temporary password and sends welcome email.
    Requires authentication and SUPER_ADMIN or ADMIN role.
    """
    try:
        # Get tenant_name from JWT token
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: missing tenant information"
            )
        
        # Check user roles
        user_roles = current_user.get("roles", [])
        # Fallback to single role for backward compatibility
        if not user_roles and current_user.get("role"):
            user_roles = [current_user.get("role")]
        
        if not any(role in ["SUPER_ADMIN", "ADMIN"] for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can invite users"
            )
        
        # Invite user
        result = await auth_service.invite_user(
            tenant_name=tenant_name,
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
            role=request.role,
            company_name=tenant_name  # Use domain as company name fallback
        )
        
        return {
            "success": True,
            "message": "User invited successfully",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invite user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User invitation failed"
        )


@router.get(
    "/me",
    summary="Get Current User",
    description="Get current user profile from JWT token"
)
async def get_current_user_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """
    Get current user profile.
    
    Requires valid JWT token in Authorization header.
    Returns user information from JWT token.
    """
    try:
        return {
            "success": True,
            "message": "User retrieved successfully",
            "data": current_user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


@router.post(
    "/logout",
    response_model=StandardResponse,
    summary="Logout",
    description="Logout user (client-side token removal)"
)
async def logout() -> Dict[str, Any]:
    """
    Logout user.
    
    Since JWT is stateless, logout is handled client-side by removing tokens.
    This endpoint is provided for consistency but doesn't perform server-side action.
    """
    return {
        "success": True,
        "message": "Logout successful. Please remove tokens from client.",
        "data": None
    }
