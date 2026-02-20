"""
Backlog API Endpoints

REST API for backlog management including file upload and Jira integration.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form
from typing import Dict, Any
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


@router.get(
    "/project/{project_id}",
    response_model=BacklogListResponse,
    summary="List Backlog Items",
    description="Get all backlog items for a project"
)
async def list_project_backlog(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    backlog_service: BacklogService = Depends(get_backlog_service)
) -> BacklogListResponse:
    """
    List all backlog items for a specific project.
    
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
        
        items = await backlog_service.list_backlog(tenant_name, project_id)
        
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
