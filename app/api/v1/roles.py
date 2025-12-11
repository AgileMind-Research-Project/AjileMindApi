"""
Roles Management API Endpoints

Handles role CRUD operations and user role assignments (Super Admin only).
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import json

from app.db.database import db, Database
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token
from pydantic import BaseModel, Field


router = APIRouter()


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class RoleCreate(BaseModel):
    """Request model for creating a role"""
    role_name: str = Field(..., min_length=1, max_length=50, description="Role name")
    description: str = Field(..., min_length=1, description="Role description")


class RoleUpdate(BaseModel):
    """Request model for updating a role"""
    description: str = Field(..., min_length=1, description="Role description")


class RoleResponse(BaseModel):
    """Response model for a role"""
    role_id: str
    role_name: str
    description: str
    created_at: str


class UpdateUserRoleRequest(BaseModel):
    """Request model for updating user role"""
    role_id: str = Field(..., description="New role ID to assign")


# ============================================
# AUTHENTICATION & AUTHORIZATION
# ============================================

async def verify_super_admin(current_user: Dict[str, Any] = Depends(get_current_user_from_token)) -> Dict[str, Any]:
    """
    Verify that the user is a Super Admin.
    Uses the JWT dependency to extract and validate user.
    """
    # Check if user is Super Admin
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required"
        )
    
    return current_user


async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


# ============================================
# UTILITY FUNCTIONS
# ============================================

def convert_permission_level_to_json(permission_level: str) -> str:
    """Convert permission level to JSON array of permissions - Default to READ"""
    return json.dumps(["*.read"])  # Default permission


def get_permission_level_from_json(permissions_json: str) -> str:
    """Extract permission level from JSON permissions array - Not used anymore"""
    return "READ"  # Default


# ============================================
# ROLE ENDPOINTS
# ============================================

@router.get(
    "",
    response_model=List[RoleResponse],
    summary="Get All Roles",
    description="Retrieve all system roles - Super Admin only"
)
async def get_roles(
    current_user: Dict = Depends(verify_super_admin),
    database: Database = Depends(get_database)
) -> List[Dict[str, Any]]:
    """Get all system roles (shared across all tenants)"""
    try:
        query = """
            SELECT 
                ROLE_ID as role_id,
                NAME as role_name,
                DESCRIPTION as description,
                CREATED_AT as created_at
            FROM roles
            WHERE is_system_role = TRUE
            ORDER BY CREATED_AT DESC
        """
        
        roles = await database.execute_query(
            query,
            fetch_all=True
        )
        
        # Convert to response format
        result = []
        for role in roles:
            result.append({
                "role_id": role["role_id"],
                "role_name": role["role_name"],
                "description": role["description"],
                "created_at": role["created_at"].isoformat() if role["created_at"] else ""
            })
        
        logger.info(f"Retrieved {len(result)} roles for user {current_user['user_id']}")
        return result
        
    except Exception as e:
        logger.exception(f"Failed to get roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles"
        )


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Role",
    description="Create a new custom role - Super Admin only"
)
async def create_role(
    role_data: RoleCreate,
    current_user: Dict = Depends(verify_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Create a new custom role"""
    try:
        # Generate role ID and format name
        role_id = f"role-{uuid.uuid4()}"
        role_name = role_data.role_name
        
        # Check if role name already exists
        check_query = """
            SELECT ROLE_ID as role_id 
            FROM roles 
            WHERE NAME = %s
        """
        existing = await database.execute_query(
            check_query,
            (role_name,),
            fetch_one=True
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_name}' already exists"
            )
        
        # Insert new role (system-wide, no tenant_id)
        insert_query = """
            INSERT INTO roles (
                ROLE_ID, NAME, DESCRIPTION, is_system_role
            ) VALUES (%s, %s, %s, %s)
        """
        
        await database.execute_query(
            insert_query,
            (
                role_id,
                role_name,
                role_data.description,
                False
            ),
            commit=True
        )
        
        # Fetch created role
        created_role = await database.execute_query(
            """SELECT 
                ROLE_ID as role_id,
                NAME as role_name,
                DESCRIPTION as description,
                CREATED_AT as created_at 
            FROM roles 
            WHERE ROLE_ID = %s""",
            (role_id,),
            fetch_one=True
        )
        
        result = {
            "role_id": created_role["role_id"],
            "role_name": created_role["role_name"],
            "description": created_role["description"],
            "created_at": created_role["created_at"].isoformat() if created_role["created_at"] else ""
        }
        
        logger.info(f"Created role {role_id} by user {current_user['user_id']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role"
        )


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update Role",
    description="Update a custom role - Super Admin only"
)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: Dict = Depends(verify_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Update an existing custom role"""
    try:
        # Check if role exists
        check_query = """
            SELECT ROLE_ID as role_id, NAME as name, is_system_role
            FROM roles 
            WHERE ROLE_ID = %s
        """
        existing_role = await database.execute_query(
            check_query,
            (role_id,),
            fetch_one=True
        )
        
        # Prevent editing system roles
        if existing_role and existing_role.get("is_system_role"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot edit system roles"
            )
        
        if not existing_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Update role (only description, no permission level)
        update_query = """
            UPDATE roles 
            SET DESCRIPTION = %s, UPDATED_AT = %s
            WHERE ROLE_ID = %s
        """
        
        await database.execute_query(
            update_query,
            (
                role_data.description,
                datetime.utcnow(),
                role_id
            ),
            commit=True
        )
        
        # Fetch updated role
        updated_role = await database.execute_query(
            """SELECT 
                ROLE_ID as role_id,
                NAME as role_name,
                DESCRIPTION as description,
                CREATED_AT as created_at 
            FROM roles 
            WHERE ROLE_ID = %s""",
            (role_id,),
            fetch_one=True
        )
        
        result = {
            "role_id": updated_role["role_id"],
            "role_name": updated_role["role_name"],
            "description": updated_role["description"],
            "created_at": updated_role["created_at"].isoformat() if updated_role["created_at"] else ""
        }
        
        logger.info(f"Updated role {role_id} by user {current_user['user_id']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role"
        )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Role",
    description="Delete a custom role - Super Admin only"
)
async def delete_role(
    role_id: str,
    current_user: Dict = Depends(verify_super_admin),
    database: Database = Depends(get_database)
):
    """Delete a custom role"""
    try:
        # Check if role exists
        check_query = """
            SELECT ROLE_ID as role_id, is_system_role
            FROM roles 
            WHERE ROLE_ID = %s
        """
        existing_role = await database.execute_query(
            check_query,
            (role_id,),
            fetch_one=True
        )
        
        # Prevent deleting system roles
        if existing_role and existing_role.get("is_system_role"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system roles"
            )
        
        if not existing_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Check if any users have this role
        users_count_query = "SELECT COUNT(*) as count FROM users WHERE ROLE_ID = %s"
        users_count = await database.execute_query(
            users_count_query,
            (role_id,),
            fetch_one=True
        )
        
        if users_count["count"] > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete role. {users_count['count']} user(s) currently have this role."
            )
        
        # Delete role
        delete_query = "DELETE FROM roles WHERE ROLE_ID = %s"
        await database.execute_query(delete_query, (role_id,), commit=True)
        
        logger.info(f"Deleted role {role_id} by user {current_user['user_id']}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete role"
        )


# ============================================
# USER ROLE ASSIGNMENT ENDPOINTS
# ============================================

@router.get(
    "/users/{user_id}/role",
    summary="Get User Role",
    description="Get the current role of a user - Super Admin only"
)
async def get_user_role(
    user_id: str,
    current_user: Dict = Depends(verify_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Get user's current role"""
    try:
        # Get tenant domain from JWT
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Query domain-based user table
        query = f"""
            SELECT 
                user_id,
                email,
                first_name,
                last_name,
                role
            FROM `{tenant_name}`
            WHERE user_id = %s
        """
        
        user = await database.execute_query(
            query,
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": f"{user['first_name']} {user['last_name']}",
            "current_role": {
                "role_name": user["role"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user role"
        )


@router.put(
    "/users/{user_id}/role",
    summary="Update User Role",
    description="Change a user's role - Super Admin only"
)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_user: Dict = Depends(verify_super_admin),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Update user's role"""
    try:
        # Get tenant domain from JWT
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Check if user exists in domain table
        user_query = f"SELECT user_id, email FROM `{tenant_name}` WHERE user_id = %s"
        user = await database.execute_query(
            user_query,
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if role exists (role_id is actually the role name in new architecture)
        role_query = """
            SELECT role_id, name 
            FROM roles 
            WHERE name = %s
        """
        role = await database.execute_query(
            role_query,
            (request.role_id,),
            fetch_one=True
        )
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Update user role in domain table (role stored as name, not ID)
        update_query = f"""
            UPDATE `{tenant_name}` 
            SET role = %s, updated_at = %s
            WHERE user_id = %s
        """
        
        await database.execute_query(
            update_query,
            (request.role_id, datetime.utcnow(), user_id),
            commit=True
        )
        
        logger.info(f"Updated user {user_id} role to {request.role_id} by {current_user['user_id']}")
        
        return {
            "message": "User role updated successfully",
            "user_id": user_id,
            "new_role_name": request.role_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )
