"""
Project Management API Endpoints

Handles project creation, listing, and management.
Integrates with Jira Cloud for project creation.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List

from app.db.database import db, Database
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token
from app.services.project_service import ProjectService
from app.schemas.project_schemas import (
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectResponse,
    ProjectListResponse,
    UpdateProjectRequest,
    StandardResponse
)


router = APIRouter()


# ============================================
# DEPENDENCIES
# ============================================

async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


async def get_project_service(database: Database = Depends(get_database)) -> ProjectService:
    """Dependency to get Project service instance"""
    return ProjectService(database)


async def verify_project_creation_access(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """
    Verify that user has permission to create projects.
    Only SUPER_ADMIN, ADMIN, and PROJECT_MANAGER can create projects.
    """
    allowed_roles = ["SUPER_ADMIN", "ADMIN", "PROJECT_MANAGER"]
    user_roles = current_user.get("roles", [])
    # Fallback to single role for backward compatibility
    if not user_roles and current_user.get("role"):
        user_roles = [current_user.get("role")]
    
    if not any(role in allowed_roles for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Only {', '.join(allowed_roles)} can create projects."
        )
    return current_user


async def verify_admin_access(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """Verify that the user has admin access"""
    user_roles = current_user.get("roles", [])
    # Fallback to single role for backward compatibility
    if not user_roles and current_user.get("role"):
        user_roles = [current_user.get("role")]
    
    if not any(role in ["SUPER_ADMIN", "ADMIN"] for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================
# PROJECT ENDPOINTS
# ============================================

@router.post(
    "/",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Project",
    description="Create a new project in Jira and save to database"
)
async def create_project(
    request: CreateProjectRequest,
    current_user: Dict[str, Any] = Depends(verify_project_creation_access),
    project_service: ProjectService = Depends(get_project_service)
) -> Dict[str, Any]:
    """
    Create a new project in Jira Cloud and save to database.
    
    **Access:** SUPER_ADMIN, ADMIN, or PROJECT_MANAGER only
    
    **Process:**
    1. Validate request data
    2. Check if project already exists in database
    3. **Create project in Jira Cloud** using REST API
    4. **ONLY if Jira creation succeeds**, save project to database
    
    **Important**: The project key must be entered manually. Database storage 
    only occurs after successful Jira project creation.
    
    **Project Types:**
    - `software`: Software development project
    - `business`: Business project
    - `service_desk`: Service desk project
    
    **Templates:**
    - Scrum: `com.pyxis.greenhopper.jira:gh-scrum-template`
    - Kanban: `com.pyxis.greenhopper.jira:gh-kanban-template`
    - Classic: `com.atlassian.jira-core-project-templates:jira-core-project-management`
    
    **Example Request:**
    ```json
    {
        "project_name": "Agile Scrum Project 2025",
        "key": "ASP2025",
        "project_type": "software",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "description": "Scrum project for development team",
        "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
    }
    ```
    
    **Common Errors:**
    - `400`: Project name or key already exists (in Jira or database)
    - `403`: User doesn't have permission to create projects
    - `404`: Jira integration not configured
    - `500`: Failed to create project in Jira or save to database
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        user_id = current_user.get("user_id") or current_user.get("sub")
        username = current_user.get("username") or current_user.get("email")

        # Create project (Jira first, then database)
        result = await project_service.create_project(
            tenant_name=tenant_name,
            project_name=request.project_name,
            key=request.key,
            project_type=request.project_type.value,
            start_date=request.start_date,
            end_date=request.end_date,
            created_by_user_id=user_id,
            created_by_username=username,
            description=request.description,
            template=request.template.value,
            sprint_size=request.sprint_size,
            project_lead=request.project_lead,
            project_manager=request.project_manager,
            architecture_type=request.architecture_type.value if request.architecture_type else None,
            stack_type=request.stack_type.value if request.stack_type else None,
            frontend_technologies=request.frontend_technologies,
            backend_technologies=request.backend_technologies,
            cloud_host=request.cloud_host,
            budget=request.budget
        )
        
        logger.info(
            f"Project created by {current_user['email']}: "
            f"{result['key']} - {result['project_name']}"
        )
        
        return {
            "success": True,
            "message": "Project created successfully in Jira and database",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="List All Projects",
    description="Get list of all projects with pagination"
)
async def list_projects(
    page: int = 1,
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    project_service: ProjectService = Depends(get_project_service)
) -> Dict[str, Any]:
    """
    Get list of all projects for the tenant.
    
    **Access:** All authenticated users
    
    **Filtering:**
    - ADMIN and SUPER_ADMIN see all projects
    - PROJECT_MANAGER and other roles see only assigned projects (from user.projects field)
    
    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `limit`: Items per page (default: 20, max: 100)
    
    **Returns:**
    - List of projects with pagination metadata
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20
        
        result = await project_service.list_projects(
            tenant_name=tenant_name,
            page=page,
            limit=limit
        )
        
        # Get user roles and projects for filtering
        user_roles = current_user.get("roles", [])
        # Fallback to old single role for backward compatibility
        if not user_roles and current_user.get("role"):
            user_roles = [current_user.get("role")]
        user_projects = current_user.get("projects", [])
        
        # Filter projects based on user roles
        if any(role in ["ADMIN", "SUPER_ADMIN"] for role in user_roles):
            # ADMIN and SUPER_ADMIN see all projects
            filtered_projects = result["projects"]
        else:
            # PROJECT_MANAGER and other roles see only assigned projects
            filtered_projects = [
                project for project in result["projects"]
                if project.get("project_id") in user_projects
            ]
        
        # Recalculate total count after filtering
        filtered_total = len(filtered_projects)
        
        logger.info(
            f"User {current_user.get('email')} (roles: {user_roles}) "
            f"viewing {filtered_total} of {result['total']} projects"
        )
        
        return {
            "success": True,
            "message": f"Found {filtered_total} project(s)",
            "data": filtered_projects,
            "total": filtered_total,
            "page": result["page"],
            "limit": result["limit"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get(
    "/{project_id}",
    response_model=StandardResponse,
    summary="Get Project by ID",
    description="Get project details by ID"
)
async def get_project(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    project_service: ProjectService = Depends(get_project_service)
) -> Dict[str, Any]:
    """
    Get project details by ID.
    
    **Access:** All authenticated users (filtered by assigned projects)
    
    **Access Control:**
    - ADMIN and SUPER_ADMIN can access all projects
    - Other roles can only access projects they are assigned to
    
    **Path Parameters:**
    - `project_id`: Project ID
    
    **Returns:**
    - Project data
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        project = await project_service.get_project(
            tenant_name=tenant_name,
            project_id=project_id
        )
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Check if user has access to this project
        user_roles = current_user.get("roles", [])
        # Fallback to single role for backward compatibility
        if not user_roles and current_user.get("role"):
            user_roles = [current_user.get("role")]
        user_projects = current_user.get("projects", [])
        
        # ADMIN and SUPER_ADMIN can access all projects
        if not any(role in ["ADMIN", "SUPER_ADMIN"] for role in user_roles):
            # Other roles can only access assigned projects
            if project_id not in user_projects:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this project"
                )
        
        return {
            "success": True,
            "message": "Project retrieved successfully",
            "data": project
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put(
    "/{project_id}",
    response_model=StandardResponse,
    summary="Update Project",
    description="Update project details (database only, not Jira)"
)
async def update_project(
    project_id: int,
    request: UpdateProjectRequest,
    current_user: Dict[str, Any] = Depends(verify_project_creation_access),
    project_service: ProjectService = Depends(get_project_service)
) -> Dict[str, Any]:
    """
    Update project details in database.
    
    **Note:** This only updates the local database, not Jira.
    
    **Access:** SUPER_ADMIN, ADMIN, or PROJECT_MANAGER only
    
    **Path Parameters:**
    - `project_id`: Project ID
    
    **Request Body:**
    - Fields to update (all optional)
    
    **Returns:**
    - Updated project data
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        updated_project = await project_service.update_project(
            tenant_name=tenant_name,
            project_id=project_id,
            project_name=request.project_name,
            start_date=request.start_date,
            end_date=request.end_date,
            sprint_size=request.sprint_size,
            project_lead=request.project_lead,
            project_manager=request.project_manager,
            architecture_type=request.architecture_type.value if request.architecture_type else None,
            stack_type=request.stack_type.value if request.stack_type else None,
            frontend_technologies=request.frontend_technologies,
            backend_technologies=request.backend_technologies,
            cloud_host=request.cloud_host,
            budget=request.budget
        )
        
        logger.info(
            f"Project updated by {current_user['email']}: {project_id}"
        )
        
        return {
            "success": True,
            "message": "Project updated successfully",
            "data": updated_project
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete(
    "/{project_id}",
    response_model=StandardResponse,
    summary="Delete Project",
    description="Delete project from database (not from Jira)"
)
async def delete_project(
    project_id: int,
    current_user: Dict[str, Any] = Depends(verify_admin_access),
    project_service: ProjectService = Depends(get_project_service)
) -> Dict[str, Any]:
    """
    Delete project from database.
    
    **Note:** This does NOT delete the project from Jira, only from local database.
    
    **Access:** SUPER_ADMIN or ADMIN only
    
    **Path Parameters:**
    - `project_id`: Project ID
    
    **Returns:**
    - Success message
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        await project_service.delete_project(
            tenant_name=tenant_name,
            project_id=project_id
        )
        
        logger.info(
            f"Project deleted by {current_user['email']}: {project_id}"
        )
        
        return {
            "success": True,
            "message": "Project deleted from database successfully",
            "data": {
                "project_id": project_id,
                "deleted": True,
                "note": "Project still exists in Jira"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.get("/{project_id}/sprints", response_model=Dict[str, Any])
async def list_project_sprints(
    project_id: int,
    db: Database = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    List sprints for a specific project.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
             raise HTTPException(status_code=400, detail="Tenant not found in token")

        # Check if 'sprint' table exists effectively (simplified query)
        query = """
            SELECT sprint_id, sprint_name, sprint_status, start_date, end_date 
            FROM sprint 
            WHERE project_id = %s 
            ORDER BY start_date DESC
        """
        sprints = await db.execute_query(query, (project_id,), fetch_all=True, schema=tenant_name)
        
        return {
            "success": True,
            "data": {
                "sprints": sprints or []
            }
        }
    except Exception as e:
        logger.error(f"Error fetching sprints for project {project_id}: {str(e)}")
        # If table doesn't exist, return empty list gracefully or error?
        # For now, return error structure but code 200 so UI doesn't crash?
        # Or better 500.
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{project_id}/users",
    response_model=StandardResponse,
    summary="Get Project Users",
    description="Get of users assigned to this project"
)
async def get_project_users(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get users assigned to a specific project.
    
    **Access:** All authenticated users who have access to the project
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
            
        # Check access (reuse logic from get_project)
        user_roles = current_user.get("roles", [])
        if not user_roles and current_user.get("role"):
            user_roles = [current_user.get("role")]
        user_projects = current_user.get("projects", [])
        
        if not any(role in ["ADMIN", "SUPER_ADMIN"] for role in user_roles):
            if project_id not in user_projects:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this project"
                )
        
        # Query users who have this project_id in their projects JSON array
        # We handle both numeric and string representation in JSON for robustness
        query = f"""
            SELECT 
                user_id,
                email,
                first_name,
                last_name,
                roles,
                status,
                projects
            FROM `{tenant_name}`
            WHERE (
                JSON_CONTAINS(projects, %s) 
                OR JSON_CONTAINS(projects, %s)
            )
            AND status = 'ACTIVE'
            ORDER BY first_name, last_name
        """
        
        # Pass both integer and string version of ID to be safe
        import json
        
        users = await database.execute_query(
            query,
            (str(project_id), f'"{project_id}"'),
            fetch_all=True
        )
        
        # Format results
        result = []
        for user in users:
            # Parse roles
            u_roles = []
            if user.get("roles"):
                try:
                    u_roles = json.loads(user["roles"]) if isinstance(user["roles"], str) else user["roles"]
                except:
                    u_roles = []
            
            result.append({
                "user_id": user["user_id"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "roles": u_roles,
                "role": u_roles[0] if u_roles else "" # Backward compatibility
            })
            
        return {
            "success": True,
            "message": f"Found {len(result)} users assigned to project",
            "data": {
                "project_id": project_id,
                "users": result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project users: {str(e)}"
        )
