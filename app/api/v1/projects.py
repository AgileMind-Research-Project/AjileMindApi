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
from app.services.delay_calculation_service import DelayCalculationService
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
            budget=request.budget,
            trust_index_threshold=request.trust_index_threshold,
            prioritize_task_count=request.prioritize_task_count,
            working_hours_for_day=request.working_hours_for_day
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
            budget=request.budget,
            trust_index_threshold=request.trust_index_threshold,
            prioritize_task_count=request.prioritize_task_count,
            working_hours_for_day=request.working_hours_for_day
        )
        
        logger.info(f"Project updated by {current_user['email']}: {project_id}")
        
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
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}/sprints/{sprint_id}/status", response_model=Dict[str, Any])
async def update_sprint_status(
    project_id: int,
    sprint_id: int,
    body: Dict[str, Any],
    db: Database = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Update the status of a sprint (e.g. set to 'Active' when a Sprint Planning meeting tasks are synced).
    Body: { "sprint_status": "Active" }
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant not found in token")

        new_status = body.get("sprint_status")
        if not new_status:
            raise HTTPException(status_code=422, detail="sprint_status is required")

        from app.db.repositories.sprint_repository import SprintRepository
        repo = SprintRepository(db)
        updated = await repo.update_sprint_status(tenant_name, sprint_id, new_status)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Sprint {sprint_id} not found")

        return {"success": True, "data": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating sprint status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/sprints/{sprint_id}/start", response_model=Dict[str, Any])
async def start_sprint(
    project_id: int,
    sprint_id: int,
    body: Dict[str, Any],
    db: Database = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Start a sprint end-to-end:
      1. Reads project.sprint_size (weeks) → computes start_date=today, end_date=today+N weeks.
      2. Adds task_ids (Jira issue keys) to the Jira sprint via Agile API.
      3. Activates the sprint in Jira (PUT /rest/agile/1.0/sprint/{id}).
      4. Updates the DB sprint row: status='Active', start_date, end_date.

    Body: { "task_ids": ["TAM-1", "TAM-2", ...] }  (task_ids optional)
    Returns: { "success": true, "data": <updated_sprint_row>, "jira_started": bool }
    """
    import datetime as dt
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant not found in token")

        from app.db.repositories.project_repository import ProjectRepository
        from app.db.repositories.sprint_repository import SprintRepository
        from app.services.jira_service import JiraService

        # ── 1. Load project (sprint_size, board_id, sprint_name) ──────────────
        project_repo = ProjectRepository(db)
        project = await project_repo.get_project_by_id(tenant_name, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        sprint_size_weeks = project.get("sprint_size")
        if not sprint_size_weeks or int(sprint_size_weeks) <= 0:
            raise HTTPException(
                status_code=422,
                detail="Project sprint_size is not set or invalid. Set it before starting a sprint."
            )
        sprint_size_weeks = int(sprint_size_weeks)
        board_id = project.get("board_id")

        # ── 2. Compute dates ────────────────────────────────────────────────────
        today = dt.date.today()
        end_date_obj = today + dt.timedelta(weeks=sprint_size_weeks)
        # Jira Agile API expects ISO-8601 with time component
        jira_start = f"{today.isoformat()}T09:00:00.000+0000"
        jira_end   = f"{end_date_obj.isoformat()}T18:00:00.000+0000"

        # ── 3. Load the sprint row to get sprint_name ───────────────────────────
        sprint_repo = SprintRepository(db)
        sprint_row = await sprint_repo.get_sprint_by_id(tenant_name, sprint_id)
        if not sprint_row:
            raise HTTPException(status_code=404, detail=f"Sprint {sprint_id} not found")
        sprint_name = sprint_row.get("sprint_name", f"Sprint {sprint_id}")

        # ── 3b. Sync prioritized items to Jira first (creates missing issues & subtasks) ──
        # This ensures that local item IDs like "AFV-262-SUB-1" are created in Jira
        # and the database is updated with the actual Jira keys before we try to add them to the sprint
        from app.services.backlog_service import BacklogService
        try:
            backlog_service = BacklogService(db)
            project_key = project.get("key")  # Jira project key (e.g. "AFV")
            
            logger.info(f"Syncing prioritized items to Jira for project {project_id} before sprint start")
            sync_result = await backlog_service.sync_priority_items_to_jira(
                tenant_name=tenant_name,
                project_id=project_id,
                project_key=project_key,
                jira_service=JiraService(db)
            )
            logger.info(f"Sync completed: {sync_result.get('synced_count', 0)} items synced")
        except Exception as sync_err:
            # Non-fatal: sync errors should not prevent sprint start
            logger.warning(f"Non-fatal: Could not sync prioritized items to Jira: {sync_err}")

        # ── 4. Add issues to the Jira sprint ───────────────────────────────────
        task_ids: list = body.get("task_ids", []) or []
        jira_svc = JiraService(db)
        issues_added = False
        jira_started = False
        try:
            if task_ids:
                issues_added = await jira_svc.add_issues_to_sprint(
                    tenant_name, sprint_id, task_ids
                )

            # ── 5. Activate the sprint in Jira ─────────────────────────────────
            if board_id:
                jira_started = await jira_svc.start_jira_sprint(
                    tenant_name=tenant_name,
                    sprint_id=sprint_id,
                    sprint_name=sprint_name,
                    board_id=board_id,
                    start_date=jira_start,
                    end_date=jira_end,
                )
            else:
                logger.warning(
                    f"Project {project_id} has no board_id — skipping Jira sprint activation."
                )
        except Exception as jira_err:
            # Jira errors are non-fatal; still update the DB
            logger.warning(f"Jira sprint start non-fatal error: {jira_err}")

        # ── 6. Update DB sprint row ─────────────────────────────────────────────
        updated = await sprint_repo.start_sprint(tenant_name, sprint_id, sprint_size_weeks)

        logger.info(
            f"Sprint {sprint_id} started: project={project_id}, "
            f"sprint_size={sprint_size_weeks}w, start={today}, end={end_date_obj}, "
            f"jira_started={jira_started}, issues_added={issues_added}"
        )
        return {"success": True, "data": updated, "jira_started": jira_started}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting sprint {sprint_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/sprints/{sprint_id}/close", response_model=Dict[str, Any])
async def close_sprint(
    project_id: int,
    sprint_id: int,
    db: Database = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """
    Close a sprint end-to-end (called after Sprint Review sync):
      1. Closes the sprint in Jira (state = 'closed') via PUT /rest/agile/1.0/sprint/{id}.
      2. Updates the DB sprint row: status='Closed'.
    Returns: { "success": true, "data": <updated_sprint_row>, "jira_closed": bool }
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant not found in token")

        from app.db.repositories.sprint_repository import SprintRepository
        from app.services.jira_service import JiraService

        sprint_repo = SprintRepository(db)
        sprint_row = await sprint_repo.get_sprint_by_id(tenant_name, sprint_id)
        if not sprint_row:
            raise HTTPException(status_code=404, detail=f"Sprint {sprint_id} not found")

        sprint_name = sprint_row.get("sprint_name", f"Sprint {sprint_id}")
        jira_svc = JiraService(db)
        jira_closed = False

        try:
            credentials = await jira_svc.get_credentials(tenant_name)
            if credentials:
                import aiohttp, base64
                from app.utils.secrets import get_secret
                jira_url = credentials["jira_url"]
                email = credentials["email"]
                secret_name = (
                    f"tenant_{tenant_name}_jira_api_token_"
                    f"{jira_url.replace('https://','').replace('/','_')}"
                )
                secret_result = get_secret(secret_name)
                if secret_result.get("success"):
                    api_token = secret_result.get("secret_value")
                    auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
                    headers = {
                        "Authorization": f"Basic {auth_b64}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    }
                    payload = {
                        "id": sprint_id,
                        "name": sprint_name,
                        "state": "closed",
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.put(
                            f"{jira_url}/rest/agile/1.0/sprint/{sprint_id}",
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as resp:
                            jira_closed = resp.status == 200
                            if not jira_closed:
                                body_txt = await resp.text()
                                logger.warning(f"Jira close sprint {sprint_id} HTTP {resp.status}: {body_txt}")
        except Exception as jira_err:
            logger.warning(f"Jira close sprint non-fatal error: {jira_err}")

        # Update DB status to Closed (enum: Future, Active, Closed, On Hold, Cancelled)
        updated = await sprint_repo.update_sprint_status(tenant_name, sprint_id, "Closed")
        logger.info(f"Sprint {sprint_id} closed: project={project_id}, jira_closed={jira_closed}")
        return {"success": True, "data": updated, "jira_closed": jira_closed}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing sprint {sprint_id}: {str(e)}")
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


@router.get(
    "/{project_id}/delay-analysis",
    response_model=StandardResponse,
    summary="Get Project Delay Analysis",
    description="Calculate and retrieve delay analysis for a project"
)
async def get_delay_analysis(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Calculate delay analysis for a project.
    
    **Access:** All authenticated users who have access to the project
    
    **Returns:**
    - Delay level (NO_DELAY, LOW, MEDIUM, HIGH, CRITICAL)
    - Delay percentage
    - Detailed breakdown and metrics
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
            
        # Check access
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
        
        # Calculate delay analysis
        delay_service = DelayCalculationService(database)
        delay_data = await delay_service.calculate_project_delay(project_id, tenant_name)
        
        return {
            "success": True,
            "message": "Delay analysis calculated successfully",
            "data": delay_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating delay analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate delay analysis: {str(e)}"
        )


@router.post(
    "/{project_id}/delay-suggestions",
    response_model=StandardResponse,
    summary="Generate AI Delay Recovery Suggestions",
    description="Use local LLM to generate actionable recovery suggestions based on current delay analysis"
)
async def get_delay_suggestions(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Generate AI-powered recovery suggestions for a delayed project.
    Calls local Ollama LLM (llama3.2) with detailed delay metrics.
    """
    from app.services.llm_service import llm_service

    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )

        # Check access
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

        # Check LLM availability
        if not llm_service.llm:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service unavailable. Ensure Ollama is running locally."
            )

        # Fetch fresh delay data
        delay_service = DelayCalculationService(database)
        delay_data = await delay_service.calculate_project_delay(project_id, tenant_name)

        # Generate LLM suggestions
        suggestions = await llm_service.generate_delay_suggestions(delay_data)

        return {
            "success": True,
            "message": f"Generated {len(suggestions)} AI recovery suggestions",
            "data": {
                "project_id": project_id,
                "project_name": delay_data.get("project_name"),
                "risk_level": delay_data.get("risk_level"),
                "suggestions": suggestions
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating delay suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestions: {str(e)}"
        )
