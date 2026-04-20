"""
Backlog API Endpoints

REST API for backlog management including file upload and Jira integration.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form, Query
from typing import Dict, Any, Optional
from app.schemas.backlog_schemas import BulkUploadResponse, BacklogListResponse, BacklogItemUpdate, MergeBacklogItemsRequest, SubtaskCreateRequest
from app.services.backlog_service import BacklogService
from app.db.database import db, Database
from app.utils.jwt import get_current_user_from_token, get_secret
from app.core.logger import logger


router = APIRouter()


async def get_backlog_service() -> BacklogService:
    """Dependency to get backlog service instance"""
    return BacklogService(db)


@router.post(
    "/upload",
    response_model=BulkUploadResponse,
    summary="Upload Excel/CSV to Create Backlog in Jira",
    description="Upload Excel or CSV file to create backlog items in Jira and store in database"
)
async def upload_backlog_file(
    project_id: int = Form(..., description="Project ID to create backlog for"),
    file: UploadFile = File(..., description="Excel or CSV file with backlog items"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service),
    database: Database = Depends(lambda: db)
) -> BulkUploadResponse:
    """
    Upload Excel/CSV file to create backlog items.
    
    The file should contain the following columns:
    - **summary** (required): Backlog item title
    - **description**: Detailed description
    - **issue_type** (required): story, feature, change, or bug
    - **priority**: high, medium, or low
    - **assignee**: Email or name
    - **tags**: Comma-separated tags
    - **severity**: Required if issue_type is 'bug'
    
    Process:
    1. Parse Excel/CSV file
    2. Validate data
    3. Create issues in Jira
    4. Store in database with Jira issue keys
    
    Returns:
    - Number of items processed
    - Number of items created
    - List of Jira issue keys
    - Any errors encountered
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Get Jira credentials from database
        # Query jira_integrations table
        jira_query = "SELECT jira_url, email FROM jira_integrations LIMIT 1"
        jira_result = await database.execute_query(
            jira_query,
            fetch_one=True,
            schema=tenant_name
        )
        
        if not jira_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured. Please configure Jira first."
            )
        
        jira_url = jira_result.get("jira_url")
        jira_email = jira_result.get("email")
        
        # Get API token from AWS Secrets Manager
        secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
        secret_result = get_secret(secret_name)
        
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token from secure storage. Please reconnect Jira integration."
            )
        
        jira_api_token = secret_result.get("secret_value")
        
        # Get project key
        project_query = "SELECT `key` FROM projects WHERE project_id = %s"
        project_result = await database.execute_query(
            project_query,
            (project_id,),
            fetch_one=True,
            schema=tenant_name
        )
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        project_key = project_result.get("key")
        
        # Process file and create backlog
        result = await backlog_service.create_backlog_from_file(
            tenant_name=tenant_name,
            project_id=project_id,
            project_key=project_key,
            file=file,
            jira_url=jira_url,
            jira_email=jira_email,
            jira_api_token=jira_api_token
        )
        
        logger.info(
            f"Backlog upload completed for project {project_id}: "
            f"{result.items_created}/{result.items_processed} items created"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_backlog_file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload backlog: {str(e)}"
        )


@router.post(
    "/upload-bugs",
    response_model=BulkUploadResponse,
    summary="Upload Excel/CSV to Create Bugs in Jira and Bugs Table",
    description="Upload Excel or CSV file to create bug items in Jira and store in database"
)
async def upload_bugs_file(
    project_id: int = Form(..., description="Project ID to create bugs for"),
    sprint_id: int = Form(..., description="Sprint ID to link the bugs to"),
    file: UploadFile = File(..., description="Excel or CSV file with bug items"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service),
    database: Database = Depends(lambda: db)
) -> BulkUploadResponse:
    """
    Upload Excel/CSV file to create bug items.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Get Jira credentials from database
        jira_query = "SELECT jira_url, email FROM jira_integrations LIMIT 1"
        jira_result = await database.execute_query(
            jira_query,
            fetch_one=True,
            schema=tenant_name
        )
        
        if not jira_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jira integration not configured. Please configure Jira first."
            )
        
        jira_url = jira_result.get("jira_url")
        jira_email = jira_result.get("email")
        
        # Get API token from AWS Secrets Manager
        secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
        secret_result = get_secret(secret_name)
        
        if not secret_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve Jira API token from secure storage. Please reconnect Jira integration."
            )
        
        jira_api_token = secret_result.get("secret_value")
        
        # Get project key
        project_query = "SELECT `key` FROM projects WHERE project_id = %s"
        project_result = await database.execute_query(
            project_query,
            (project_id,),
            fetch_one=True,
            schema=tenant_name
        )
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        project_key = project_result.get("key")
        
        # Process file and create bugs
        result = await backlog_service.create_bugs_from_file(
            tenant_name=tenant_name,
            project_id=project_id,
            project_key=project_key,
            sprint_id=sprint_id,
            file=file,
            jira_url=jira_url,
            jira_email=jira_email,
            jira_api_token=jira_api_token
        )
        
        logger.info(
            f"Bugs upload completed for project {project_id}: "
            f"{result.items_created}/{result.items_processed} items created"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_bugs_file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload bugs: {str(e)}"
        )



@router.get(
    "/project/{project_id}",
    response_model=BacklogListResponse,
    summary="List Backlog Items",
    description="Get all backlog items for a project, optionally filtered by sprint and status"
)
async def list_project_backlog(
    project_id: int,
    sprint_id: Optional[int] = Query(None, description="Optional sprint ID to filter by"),
    status: Optional[str] = Query(None, description="Optional status to filter by (e.g., 'done', 'in_progress')"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> BacklogListResponse:
    """
    List all backlog items for a specific project.
    
    Args:
        project_id: The project ID to get backlog for
        sprint_id: Optional sprint ID to filter items by specific sprint
        status: Optional status to filter items by (e.g., 'done', 'in_progress')
    
    Returns:
        - List of backlog items with Jira issue keys
        - Total count
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        if sprint_id is not None:
            # Filter by sprint
            items = await backlog_service.list_sprint_backlog(tenant_name, sprint_id, status)
        else:
            # Get all project backlog items
            items = await backlog_service.list_backlog(tenant_name, project_id, status)
        
        return BacklogListResponse(
            success=True,
            data=items,
            total=len(items)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing backlog: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backlog: {str(e)}"
        )


@router.get(
    "/project/{project_id}/subtask",
    summary="Get Project Subtasks",
    description="Get all subtasks for a project grouped by their parent task name"
)
async def get_project_subtasks(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> Dict[str, Any]:
    """
    Retrieve all subtasks for a project, grouped by parent task.

    Each group contains the parent task ID, the parent summary (name),
    and the list of child subtask rows from the backlog table.

    URL: GET /api/v1/backlog/project/{project_id}/subtask
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )

        query = """
            SELECT
                pb.id,
                pb.summary,
                pb.description,
                pb.issue_type,
                pb.status,
                pb.priority,
                pb.severity,
                pb.assignee,
                pb.tags,
                pb.estimated_hours,
                pb.logged_hours,
                pb.story_points,
                pb.story_point_estimate,
                pb.sprint_id,
                pb.parent_task_id,
                pb.start_date,
                pb.end_date,
                pb.created_at,
                pb.updated_at,
                parent.summary AS parent_summary
            FROM project_backlog pb

            LEFT JOIN project_backlog parent
                ON pb.parent_task_id = parent.id

            WHERE pb.project_id = %s
            AND (
                    pb.id IN (
                        SELECT backlog_id
                        FROM project_backlog_priority
                        WHERE project_id = %s
                        AND sprint_id IS NULL
                    )
                OR
                    pb.parent_task_id IN (
                        SELECT backlog_id
                        FROM project_backlog_priority
                        WHERE project_id = %s
                        AND sprint_id IS NULL
                    )
            )

            ORDER BY
                COALESCE(pb.parent_task_id, pb.id),
                pb.parent_task_id,
                pb.id;
        """

        rows = await backlog_service.db.execute_query(
            query,
            (project_id, project_id, project_id),
            fetch_all=True,
            schema=tenant_name
        )

        if not rows:
            return {
                "success": True,
                "message": "No subtasks found for this project",
                "data": {
                    "project_id": project_id,
                    "total_subtasks": 0,
                    "groups": []
                }
            }

        # Group subtasks by parent task
        groups: Dict[str, Any] = {}
        for row in rows:
            parent_id = row["parent_task_id"]
            if parent_id not in groups:
                groups[parent_id] = {
                    "parent_task_id": parent_id,
                    "parent_summary": row.get("parent_summary") or parent_id,
                    "subtasks": []
                }
            groups[parent_id]["subtasks"].append({
                "id": row["id"],
                "summary": row["summary"],
                "description": row.get("description"),
                "issue_type": row["issue_type"],
                "status": row["status"],
                "priority": row.get("priority"),
                "severity": row.get("severity"),
                "assignee": row.get("assignee"),
                "tags": row.get("tags"),
                "estimated_hours": row.get("estimated_hours", 0),
                "logged_hours": row.get("logged_hours", 0),
                "story_points": row.get("story_points", 0),
                "story_point_estimate": row.get("story_point_estimate", 0),
                "sprint_id": row.get("sprint_id"),
                "parent_task_id": parent_id,
                "start_date": str(row["start_date"]) if row.get("start_date") else None,
                "end_date": str(row["end_date"]) if row.get("end_date") else None,
                "created_at": str(row["created_at"]) if row.get("created_at") else None,
                "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
            })

        group_list = list(groups.values())
        total_subtasks = sum(len(g["subtasks"]) for g in group_list)

        logger.info(f"Retrieved {total_subtasks} subtasks in {len(group_list)} group(s) for project {project_id}")

        return {
            "success": True,
            "message": f"Found {total_subtasks} subtask(s) in {len(group_list)} parent task(s)",
            "data": {
                "project_id": project_id,
                "total_subtasks": total_subtasks,
                "groups": group_list
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subtasks for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch subtasks: {str(e)}"
        )


@router.get(
    "/my-tasks",
    response_model=BacklogListResponse,
    summary="List My Tasks",
    description="Get all backlog items assigned to the current user"
)
async def list_my_tasks(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> BacklogListResponse:
    """
    List all backlog items assigned to the current user.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        email = current_user.get("email")
        if not tenant_name or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name or email not found in token"
            )

        items = await backlog_service.list_user_tasks(tenant_name, email)

        return BacklogListResponse(
            success=True,
            data=items,
            total=len(items)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing my tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list my tasks: {str(e)}"
        )


@router.get(
    "/{item_id}",
    summary="Get Backlog Item",
    description="Fetch a single backlog item by its ID (e.g. TAM-123)"
)
async def get_backlog_item(
    item_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> Dict[str, Any]:
    """
    Get details for a single backlog item.
    Returns description, tags, story_points, status, priority, assignee etc.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )

        item = await backlog_service.backlog_repo.get_backlog_item(tenant_name, item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backlog item '{item_id}' not found"
            )

        return {"success": True, "data": item}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching backlog item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch backlog item: {str(e)}"
        )


@router.patch(
    "/{item_id}",
    summary="Update Backlog Item",
    description="Update backlog item details (subtask or main task)"
)
async def update_backlog_item(
    item_id: str,
    updates: BacklogItemUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> Dict[str, Any]:
    """
    Update a backlog item.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Convert updates to dict, excluding None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
            
        result = await backlog_service.update_backlog_item(tenant_name, item_id, update_data)
        
        return {
            "success": True,
            "message": "Item updated successfully",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update item: {str(e)}"
        )


@router.post(
    "/merge",
    summary="Merge Backlog Items",
    description="Merge multiple backlog items into one: update target and delete sources"
)
async def merge_backlog_items(
    request: MergeBacklogItemsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> Dict[str, Any]:
    """
    Merge backlog items.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Convert updates to dict, excluding None values
        update_data = {k: v for k, v in request.updates.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided for merged item"
            )
            
        result = await backlog_service.merge_backlog_items(
            tenant_name=tenant_name,
            target_id=request.target_item_id,
            source_ids=request.source_item_ids,
            updates=update_data
        )
        
        return {
            "success": True,
            "message": "Items merged successfully",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge items: {str(e)}"
        )


@router.delete(
    "/{item_id}",
    summary="Delete Backlog Item",
    description="Delete a backlog item. If it is a subtask, it reorders subsequent subtasks to fill the ID gap."
)
async def delete_backlog_item(
    item_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> Dict[str, Any]:
    """
    Delete a backlog item.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
            
        success = await backlog_service.delete_backlog_item(tenant_name, item_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} not found"
            )
            
        return {
            "success": True,
            "message": "Item deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(e)}"
        )


@router.post(
    "/subtask",
    summary="Create Subtask",
    description="Create a subtask for a given parent task, with sequential ID generation (e.g. PARENT-1, PARENT-2)"
)
async def create_subtask(
    request: SubtaskCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> Dict[str, Any]:
    """
    Create a new subtask.
    """
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
            
        result = await backlog_service.create_subtask(tenant_name, request)
        
        return {
            "success": True,
            "message": "Subtask created successfully",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subtask: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subtask: {str(e)}"
        )


