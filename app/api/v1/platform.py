"""
Platform API Endpoints

Handles public platform operations like tenant registration from Platform Home.
These endpoints are public and don't require authentication.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from app.schemas.auth_schemas import (
    TenantRegisterRequest,
    TenantRegisterResponse
)
from app.services.auth_service import AuthService
from app.db.database import db
from app.core.logger import logger

router = APIRouter()


async def get_auth_service() -> AuthService:
    """Dependency to get auth service instance"""
    return AuthService(db)


@router.post(
    "/register-tenant",
    response_model=TenantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Tenant from Platform Home",
    description="Public endpoint for tenant registration from the Platform Home page"
)
async def register_tenant(
    request: TenantRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Register new tenant (company) from Platform Home.
    
    This is a public endpoint that creates:
    - New tenant record
    - Super admin user for the tenant
    - JWT tokens for immediate login
    - Welcome email notification
    
    The user is automatically logged in after registration.
    
    **Request Body:**
    - company_name: Company name (3-100 characters)
    - email: Admin email address
    - password: Password (min 8 characters with policy requirements)
    - password_confirmation: Must match password
    
    **Returns:**
    - tenant_id: Unique tenant identifier
    - company_name: Registered company name
    - user: Super admin user profile
    - tokens: JWT access and refresh tokens
    - redirect_url: URL to redirect after successful registration
    
    **Error Responses:**
    - 409: Email already registered
    - 422: Validation error (weak password, mismatched passwords, etc.)
    - 500: Server error
    """
    try:
        result = await auth_service.register_tenant(
            company_name=request.company_name,
            email=request.email,
            password=request.password
        )
        
        logger.info(f"Tenant registered successfully: {request.company_name} ({result['tenant_id']})")
        
        return {
            "success": True,
            "message": "Tenant registered successfully. Welcome to AgileMind!",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tenant registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later."
        )


@router.get(
    "/health",
    summary="Platform Health Check",
    description="Public health check for platform services"
)
async def platform_health() -> Dict[str, Any]:
    """
    Public health check endpoint for platform services.
    
    Returns:
    - status: Service operational status
    - message: Status message
    """
    return {
        "status": "operational",
        "message": "AgileMind Platform is running",
        "service": "platform",
        "version": "1.0.0"
    }
