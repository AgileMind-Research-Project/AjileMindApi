"""
Users Management API Endpoints

Handles user CRUD operations and invitations.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
import uuid
from datetime import datetime

from app.db.database import db, Database
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token
from app.utils.password import hash_password
from app.db.repositories.user_repository import UserRepository
from app.services.email_service import email_service
from pydantic import BaseModel, EmailStr, Field


router = APIRouter()


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class InviteUserRequest(BaseModel):
    """Request model for inviting a user"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    role: str = Field(..., min_length=1, max_length=50)


class InviteUserResponse(BaseModel):
    """Response model for user invitation"""
    success: bool
    message: str
    data: Dict[str, Any]


# ============================================
# AUTHENTICATION & AUTHORIZATION
# ============================================

async def verify_admin_or_super_admin(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """
    Verify that the user is an Admin or Super Admin.
    """
    if current_user.get("role") not in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Super Admin access required"
        )
    
    return current_user


async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


# ============================================
# USER ENDPOINTS
# ============================================

@router.post(
    "/invite",
    response_model=InviteUserResponse,
    summary="Invite New User",
    description="Invite a new user with auto-generated password (Admin/Super Admin only)"
)
async def invite_user(
    request: InviteUserRequest,
    current_user: Dict[str, Any] = Depends(verify_admin_or_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Invite a new user to the tenant.
    
    Auto-generates password using format: {FirstName}{EmailLocal}@123
    Example: John Doe (john.doe@company.com) → Johnjohn.doe@123
    
    The user will be required to change their password on first login.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        # Check if user already exists
        check_query = """
            SELECT user_id FROM users 
            WHERE email = %s AND tenant_id = %s
        """
        existing_user = await database.execute_query(
            check_query,
            (request.email, tenant_id),
            fetch_one=True
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Validate role exists (check against ROLES table which uses UPPERCASE)
        role_query = """
            SELECT NAME FROM ROLES 
            WHERE NAME = %s AND (TENANT_ID IS NULL OR TENANT_ID = %s)
        """
        role = await database.execute_query(
            role_query,
            (request.role, tenant_id),
            fetch_one=True
        )
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{request.role}' not found"
            )
        
        # Generate password: {FirstName}{EmailLocal}@123
        email_local = request.email.split('@')[0]
        auto_password = f"{request.first_name}{email_local}@123"
        
        # Hash the password
        password_hash = hash_password(auto_password)
        
        # Generate user ID
        user_id = f"usr-{uuid.uuid4().hex[:16]}"
        
        # Create user
        insert_query = """
            INSERT INTO users (
                user_id,
                tenant_id,
                email,
                password_hash,
                first_name,
                last_name,
                role,
                status,
                password_change_required,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        now = datetime.utcnow()
        
        await database.execute_query(
            insert_query,
            (
                user_id,
                tenant_id,
                request.email,
                password_hash,
                request.first_name,
                request.last_name,
                request.role,
                'ACTIVE',  # status
                1,  # password_change_required
                now,
                now
            ),
            commit=True
        )
        
        logger.info(f"User invited: {request.email} by {current_user['email']}")
        
        # Get tenant name for email
        tenant_query = """
            SELECT company_name FROM tenants 
            WHERE tenant_id = %s
        """
        tenant = await database.execute_query(
            tenant_query,
            (tenant_id,),
            fetch_one=True
        )
        company_name = tenant.get("company_name", "Your Company") if tenant else "Your Company"
        
        # Send welcome email with credentials
        email_sent = email_service.send_user_welcome_email(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            company_name=company_name,
            role=request.role,
            temporary_password=auto_password
        )
        
        if not email_sent:
            logger.warning(f"Failed to send welcome email to {request.email}")
        
        # Return success
        return {
            "success": True,
            "message": "User invited successfully. Welcome email sent with login credentials.",
            "data": {
                "user_id": user_id,
                "email": request.email,
                "first_name": request.first_name,
                "last_name": request.last_name,
                "role": request.role,
                "email_sent": email_sent,
                "password_change_required": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite user: {str(e)}"
        )


@router.get(
    "",
    summary="List Users",
    description="Get all users in the tenant (Admin/Super Admin only)"
)
async def list_users(
    current_user: Dict[str, Any] = Depends(verify_admin_or_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Get all users for the tenant"""
    try:
        tenant_id = current_user["tenant_id"]
        
        query = """
            SELECT 
                u.user_id,
                u.email,
                u.first_name,
                u.last_name,
                u.role,
                u.status,
                u.password_change_required,
                u.created_at
            FROM users u
            WHERE u.tenant_id = %s
            ORDER BY u.created_at DESC
        """
        
        users = await database.execute_query(
            query,
            (tenant_id,),
            fetch_all=True
        )
        
        # Convert to response format
        result = []
        for user in users:
            result.append({
                "user_id": user["user_id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "role": user["role"],
                "status": user["status"],
                "password_change_required": bool(user["password_change_required"]),
                "created_at": user["created_at"].isoformat() if user["created_at"] else ""
            })
        
        logger.info(f"Retrieved {len(result)} users for tenant {tenant_id}")
        
        return {
            "success": True,
            "message": "Users retrieved successfully",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )
