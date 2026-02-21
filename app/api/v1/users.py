"""
Users Management API Endpoints

Handles user CRUD operations and invitations.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime

from app.db.database import db, Database
from app.core.config import settings
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token
from app.utils.password import hash_password
from app.services.email_service import email_service
from pydantic import BaseModel, EmailStr, Field


router = APIRouter()


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class UserDataRequest(BaseModel):
    """User profile data"""
    stack: Optional[Union[str, List[str]]] = Field(None, description="Technology stack: 'backend', 'frontend', 'both', or array format")
    technologies: Optional[List[str]] = Field(None, description="Technologies/frameworks (e.g., java, spring, mysql)")
    experience_years: Optional[int] = Field(None, description="Years of experience")


class InviteUserRequest(BaseModel):
    """Request model for inviting a user"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    role: str = Field(..., min_length=1, max_length=50)
    project_ids: List[int] = Field(default=[], description="List of project IDs to assign user to")


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
        # Get tenant domain from JWT
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Check if user already exists in domain table
        check_query = f"""
            SELECT user_id FROM `{settings.DB_NAME}`.`{tenant_name}` 
            WHERE email = %s
        """
        existing_user = await database.execute_query(
            check_query,
            (request.email,),
            fetch_one=True
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Validate all roles exist (check against system roles table)
        for role_name in request.roles:
            role_query = f"""
                SELECT name FROM `{settings.DB_NAME}`.roles 
                WHERE name = %s
            """
            role = await database.execute_query(
                role_query,
                (role_name,),
                fetch_one=True
            )
            
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{role_name}' not found"
                )
        
        # Generate password: {FirstName}{EmailLocal}@123
        email_local = request.email.split('@')[0]
        auto_password = f"{request.first_name}{email_local}@123"
        
        # Hash the password
        password_hash = hash_password(auto_password)
        
        # Generate user ID
        user_id = f"usr-{uuid.uuid4().hex[:16]}"
        
        # Create user in domain table
        insert_query = f"""
            INSERT INTO `{settings.DB_NAME}`.`{tenant_name}` (
                user_id,
                email,
                password_hash,
                first_name,
                last_name,
                role,
                status,
                password_change_required,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        now = datetime.utcnow()
        
        await database.execute_query(
            insert_query,
            (
                user_id,
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
        
        # Assign user to projects if provided
        if request.project_ids:
            import json
            
            # Update the projects column with JSON array
            update_projects_query = f"""
                UPDATE `{settings.DB_NAME}`.`{tenant_name}` 
                SET projects = %s 
                WHERE user_id = %s
            """
            projects_json = json.dumps(request.project_ids)
            await database.execute_query(
                update_projects_query,
                (projects_json, user_id),
                commit=True
            )
            logger.info(f"Assigned user {user_id} to {len(request.project_ids)} project(s)")

        
        logger.info(f"User invited: {request.email} by {current_user['email']}")
        
        # Get company name from tenant_info table in tenant database
        try:
            tenant_info_query = f"""
                SELECT tenant_name FROM `{tenant_name}`.tenant_info 
                LIMIT 1
            """
            tenant_info = await database.execute_query(
                tenant_info_query,
                fetch_one=True
            )
            company_name = tenant_info.get("tenant_name", tenant_name.title()) if tenant_info else tenant_name.title()
        except Exception:
            # Fallback to domain name if tenant_info doesn't exist
            company_name = tenant_name.title()
        
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
                "project_ids": request.project_ids,
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
        # Get tenant domain from JWT
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        query = f"""
            SELECT 
                user_id,
                email,
                first_name,
                last_name,
                role,
                status,
                projects,
                password_change_required,
                created_at
            FROM `{settings.DB_NAME}`.`{tenant_name}`
            ORDER BY created_at DESC
        """
        
        users = await database.execute_query(
            query,
            fetch_all=True
        )
        
        # Convert to response format
        result = []
        for user in users:
            import json
            # Parse projects JSON
            user_projects = []
            if user.get("projects"):
                try:
                    user_projects = json.loads(user["projects"]) if isinstance(user["projects"], str) else user["projects"]
                except:
                    user_projects = []
            
            result.append({
                "user_id": user["user_id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "role": user["role"],
                "status": user["status"],
                "project_ids": user_projects,
                "password_change_required": bool(user["password_change_required"]),
                "created_at": user["created_at"].isoformat() if user["created_at"] else ""
            })
        
        logger.info(f"Retrieved {len(result)} users for tenant {tenant_name}")
        
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


@router.get(
    "/by-role/{role}",
    summary="Get Users by Role",
    description="Get all users with a specific role (for dropdowns, etc.)"
)
async def get_users_by_role(
    role: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get all users with a specific role.
    
    Useful for populating dropdowns with users of specific roles.
    For example: Get all PROJECT_MANAGER users for project assignment.
    
    **Access:** All authenticated users
    
    **Parameters:**
    - role: Role to filter by (e.g., PROJECT_MANAGER, ADMIN, DEVELOPER)
    
    **Returns:**
    - List of users with that role (email, name, user_id)
    """
    try:
        # Get tenant domain from JWT
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Query users with specific role
        query = f"""
            SELECT 
                user_id,
                email,
                first_name,
                last_name,
                role,
                status
            FROM `{settings.DB_NAME}`.`{tenant_name}`
            WHERE JSON_CONTAINS(roles, %s, '$') AND status = 'ACTIVE'
            ORDER BY first_name, last_name
        """
        
        users = await database.execute_query(
            query,
            (role,),
            fetch_all=True
        )
        
        # Convert to simple format for dropdown
        result = []
        for user in users:
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            result.append({
                "user_id": user["user_id"],
                "email": user["email"],
                "name": full_name or user["email"],  # Fallback to email if no name
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name")
            })
        
        logger.info(f"Retrieved {len(result)} users with role {role} for tenant {tenant_name}")
        
        return {
            "success": True,
            "message": f"Found {len(result)} user(s) with role {role}",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting users by role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users by role: {str(e)}"
        )


class UpdateUserRequest(BaseModel):
    """Request model for updating user basic details"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[str] = Field(None, min_length=1, max_length=50)


@router.put(
    "/{user_id}",
    summary="Update User Details",
    description="Update user basic information (Admin/Super Admin only)"
)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: Dict[str, Any] = Depends(verify_admin_or_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Update user basic details (name, role)"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Check if user exists
        check_query = f"""
            SELECT user_id FROM `{settings.DB_NAME}`.`{tenant_name}` 
            WHERE user_id = %s
        """
        user = await database.execute_query(
            check_query,
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if request.first_name is not None:
            update_fields.append("first_name = %s")
            params.append(request.first_name)
        
        if request.last_name is not None:
            update_fields.append("last_name = %s")
            params.append(request.last_name)
        
        if request.roles is not None:
            # Validate all roles exist
            for role_name in request.roles:
                role_query = f"SELECT name FROM `{settings.DB_NAME}`.roles WHERE name = %s"
                role = await database.execute_query(
                    role_query,
                    (role_name,),
                    fetch_one=True
                )
                
                if not role:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Role '{role_name}' not found"
                    )
            
            update_fields.append("role = %s")
            params.append(request.role)
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Add updated_at timestamp
        update_fields.append("updated_at = NOW()")
        params.append(user_id)
        
        query = f"""
            UPDATE `{settings.DB_NAME}`.`{tenant_name}` 
            SET {', '.join(update_fields)}
            WHERE user_id = %s
        """
        
        await database.execute_query(query, tuple(params), commit=True)
        
        logger.info(f"User {user_id} updated by {current_user['email']}")
        
        return {
            "success": True,
            "message": "User updated successfully",
            "data": {
                "user_id": user_id,
                "first_name": request.first_name,
                "last_name": request.last_name,
                "role": request.role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.get(
    "/{user_id}/projects",
    summary="Get User Projects",
    description="Get project assignments for a specific user (Admin/Super Admin only)"
)
async def get_user_projects(
    user_id: str,
    current_user: Dict[str, Any] = Depends(verify_admin_or_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Get projects assigned to a specific user"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Get user's projects
        query = f"""
            SELECT projects 
            FROM `{settings.DB_NAME}`.`{tenant_name}` 
            WHERE user_id = %s
        """
        
        result = await database.execute_query(
            query,
            (user_id,),
            fetch_one=True
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        import json
        project_ids = []
        if result.get("projects"):
            try:
                project_ids = json.loads(result["projects"]) if isinstance(result["projects"], str) else result["projects"]
            except:
                project_ids = []
        
        return {
            "success": True,
            "message": "User projects retrieved successfully",
            "data": {
                "user_id": user_id,
                "project_ids": project_ids or []
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user projects: {str(e)}"
        )


class UpdateUserProjectsRequest(BaseModel):
    """Request model for updating user project assignments"""
    project_ids: List[int] = Field(..., description="List of project IDs to assign to user")


@router.put(
    "/{user_id}/projects",
    summary="Update User Projects",
    description="Update project assignments for a specific user (Admin/Super Admin only)"
)
async def update_user_projects(
    user_id: str,
    request: UpdateUserProjectsRequest,
    current_user: Dict[str, Any] = Depends(verify_admin_or_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Update projects assigned to a specific user"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Check if user exists
        check_query = f"""
            SELECT user_id FROM `{settings.DB_NAME}`.`{tenant_name}` 
            WHERE user_id = %s
        """
        user = await database.execute_query(
            check_query,
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        # Update user's projects
        import json
        update_query = f"""
            UPDATE `{settings.DB_NAME}`.`{tenant_name}` 
            SET projects = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        
        projects_json = json.dumps(request.project_ids)
        await database.execute_query(
            update_query,
            (projects_json, user_id),
            commit=True
        )
        
        logger.info(f"Updated user {user_id} projects by {current_user['email']}")
        
        return {
            "success": True,
            "message": "User project assignments updated successfully",
            "data": {
                "user_id": user_id,
                "project_ids": request.project_ids
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user projects: {str(e)}"
        )

