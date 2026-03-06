"""
Project Management API Endpoints

Handles project creation, listing, and management.
Integrates with Jira Cloud for project creation.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
import json

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
    StandardResponse,
    SprintListResponse,
    SprintFilterRequest
)
from app.schemas.delay_schemas import (
    DelayAnalysisResponse,
    DelayAnalysisErrorResponse
)


router = APIRouter()


async def _resolve_user_role(database: Database, tenant_name: str, email: str):
    """
    Look up a user's role and projects directly from the centralized DB.
    Used as a fallback when the JWT token is missing the role claim.
    Returns (role, projects) or (None, []).
    """
    try:
        table_result = await database.execute_query(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE %s LIMIT 1",
            (f"%{tenant_name}",),
            fetch_one=True
        )
        if not table_result:
            return None, []
        user_row = await database.execute_query(
            f"SELECT role, projects FROM `{table_result['TABLE_NAME']}` WHERE email = %s",
            (email,),
            fetch_one=True
        )
        if not user_row:
            return None, []
        role = user_row.get("role")
        projects = user_row.get("projects") or []
        if isinstance(projects, str):
            try:
                projects = json.loads(projects)
            except Exception:
                projects = []
        return role, projects
    except Exception as e:
        logger.warning(f"DB role fallback failed: {e}")
        return None, []


# ============================================
# DEPENDENCIES
# ============================================

async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


async def get_project_service(database: Database = Depends(get_database)) -> ProjectService:
    """Dependency to get Project service instance"""
    return ProjectService(database)


async def get_delay_service(database: Database = Depends(get_database)) -> DelayCalculationService:
    """Dependency to get Delay Calculation service instance"""
    return DelayCalculationService(database)


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
    project_service: ProjectService = Depends(get_project_service),
    database: Database = Depends(get_database)
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
        
        # Get user role and projects for filtering
        user_role = current_user.get("role")
        user_projects = current_user.get("projects", [])

        # Fallback: token is missing role — look it up from the centralized user table
        if not user_role:
            user_role, db_projects = await _resolve_user_role(
                database, tenant_name, current_user.get("email", "")
            )
            if not user_projects:
                user_projects = db_projects
            logger.info(
                f"Role resolved from DB for {current_user.get('email')}: {user_role}"
            )

        # Filter projects based on user role
        if user_role in ["ADMIN", "SUPER_ADMIN"]:
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
            f"User {current_user.get('email')} (role: {user_role}) "
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
        user_role = current_user.get("role")
        user_projects = current_user.get("projects", [])
        
        # ADMIN and SUPER_ADMIN can access all projects
        if user_role not in ["ADMIN", "SUPER_ADMIN"]:
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


@router.get(
    "/{project_id}/delay-analysis",
    response_model=DelayAnalysisResponse,
    summary="Calculate Project Delay",
    description="Calculate comprehensive project delay analysis using Agile metrics"
)
async def get_project_delay_analysis(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    delay_service: DelayCalculationService = Depends(get_delay_service)
) -> Dict[str, Any]:
    """
    Calculate comprehensive project delay analysis.
    
    **Algorithm Steps:**
    1. Calculate project duration
    2. Calculate planned number of sprints
    3. Calculate story point completion rate
    4. Calculate expected velocity
    5. Calculate actual velocity
    6. Calculate remaining story points
    7. Forecast remaining sprints
    8. Calculate total forecasted sprints
    9. Calculate sprint delay
    10. Convert sprint delay to days
    11. Calculate developer availability factor (aggregated sprint-wise)
    12. Adjust delay using availability
    13. Calculate delay percentage
    14. Determine delay risk level (LOW/MEDIUM/HIGH/CRITICAL)
    
    **Access:** All authenticated users
    
    **Returns:**
    - Planned end date (PED)
    - Forecasted end date (PED + Adjusted Delay Days)
    - Delay in days
    - Delay percentage
    - Risk level
    - Velocity metrics (expected vs actual)
    - Sprint-wise breakdown
    - Developer availability metrics
    
    **Risk Levels:**
    - **LOW**: < 10% delay
    - **MEDIUM**: 10-25% delay
    - **HIGH**: 25-40% delay
    - **CRITICAL**: ≥ 40% delay
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Calculate delay analysis
        delay_result = await delay_service.calculate_project_delay(
            project_id=project_id,
            tenant_db=tenant_name
        )
        
        logger.info(
            f"Delay analysis calculated for project {project_id} by {current_user['email']}: "
            f"{delay_result['delay_days']} days delay, {delay_result['risk_level']} risk"
        )
        
        return delay_result
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in delay analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating delay analysis for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate delay analysis: {str(e)}"
        )


@router.get(
    "/{project_id}/sprints",
    response_model=SprintListResponse,
    summary="Get Project Sprints",
    description="Get list of sprints for a project"
)
async def get_project_sprints(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    project_service: ProjectService = Depends(get_project_service)
) -> Dict[str, Any]:
    """
    Get list of sprints for a project.
    
    **Access:** All authenticated users
    
    **Path Parameters:**
    - `project_id`: Project ID
    
    **Returns:**
    - List of sprints
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
            
        sprints = await project_service.get_project_sprints(
            tenant_name=tenant_name,
            project_id=project_id
        )
        
        return {
            "success": True,
            "message": f"Found {len(sprints)} sprint(s)",
            "data": sprints,
            "total": len(sprints)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project sprints: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project sprints: {str(e)}"
        )

@router.post(
    "/{project_id}/sprints/active",
    response_model=StandardResponse,
    summary="Get Active Sprints with Tasks",
    description="Get sprints active on the given date, including their backlog tasks"
)
async def get_active_sprints_with_tasks(
    project_id: int,
    request: SprintFilterRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    project_service: ProjectService = Depends(get_project_service)
) -> Dict[str, Any]:
    """
    Get active sprints with tasks.
    
    Payload:
    ```json
    {
        "date": "2026-01-06"
    }
    ```
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
            
        result = await project_service.get_active_sprints_with_tasks(
            tenant_name=tenant_name,
            project_id=project_id,
            date_filter=request.date
        )
        
        return {
            "success": True,
            "message": f"Found {len(result)} active sprint(s)",
            "data": {
                "sprints": result,
                "total": len(result)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active sprints: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active sprints: {str(e)}"
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

