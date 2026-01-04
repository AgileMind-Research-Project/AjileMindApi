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
    user_role = current_user.get("role")
    
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Only {', '.join(allowed_roles)} can create projects."
        )
    return current_user


async def verify_admin_access(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """Verify that the user has admin access"""
    if current_user.get("role") not in ["SUPER_ADMIN", "ADMIN"]:
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
        
        # Create project (Jira first, then database)
        result = await project_service.create_project(
            tenant_name=tenant_name,
            project_name=request.project_name,
            key=request.key,
            project_type=request.project_type.value,
            start_date=request.start_date,
            end_date=request.end_date,
            description=request.description,
            template=request.template.value,
            sprint_size=request.sprint_size,
            project_lead=request.project_lead,
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
        
        return {
            "success": True,
            "message": f"Found {result['total']} project(s)",
            "data": result["projects"],
            "total": result["total"],
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
    
    **Access:** All authenticated users
    
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
