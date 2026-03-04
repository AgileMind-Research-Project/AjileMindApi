"""
New Tasks API Endpoints

Handles new tasks from brainstorming reports.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from app.db.database import Database, get_db
from app.utils.jwt import get_current_user_from_token
from app.schemas.new_task import (
    NewTaskUpdate, NewTaskResponse, NewTaskListResponse,
    NewTaskFilterParams, NewTaskStatus
)
from app.services.new_task_service import NewTaskService
from app.core.logger import logger
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ApproveTaskRequest(BaseModel):
    """Optional request body for approving task"""
    project_id: Optional[int] = None


router = APIRouter()


@router.get("/", response_model=NewTaskListResponse)
async def list_new_tasks(
    status: Optional[str] = Query(None),
    report_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    List new tasks with optional filters.
    
    - **status**: Filter by status (pending, approved, removed)
    - **report_id**: Filter by report ID
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    try:
        # Parse status
        status_enum = None
        if status:
            try:
                status_enum = NewTaskStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status. Use 'pending', 'approved', or 'removed'")
        
        filters = NewTaskFilterParams(
            status=status_enum,
            report_id=report_id,
            page=page,
            page_size=page_size
        )
        
        service = NewTaskService(db)
        result = await service.list_tasks(
            tenant_schema=current_user.get('tenant_schema'),
            filters=filters
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing new tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list new tasks")


@router.get("/{task_id}", response_model=NewTaskResponse)
async def get_new_task(
    task_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Get a specific new task by ID"""
    try:
        service = NewTaskService(db)
        return await service.get_task(task_id, current_user.get('tenant_schema'))
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting new task: {e}")
        raise HTTPException(status_code=500, detail="Failed to get new task")


@router.put("/{task_id}", response_model=NewTaskResponse)
async def update_new_task(
    task_id: int,
    task_data: NewTaskUpdate,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Update a new task"""
    try:
        service = NewTaskService(db)
        return await service.update_task(task_id, task_data, current_user.get('tenant_schema'))
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating new task: {e}")
        raise HTTPException(status_code=500, detail="Failed to update new task")


@router.post("/{task_id}/approve", response_model=NewTaskResponse)
async def approve_new_task(
    task_id: int,
    request: ApproveTaskRequest = Body(default=ApproveTaskRequest()),
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Approve a new task and add to project backlog.
    
    If the task already has a project_id, it will use that.
    Otherwise, you can provide a project_id in the request body.
    """
    try:
        service = NewTaskService(db)
        return await service.approve_task(
            task_id, 
            current_user.get('tenant_schema'),
            project_id_override=request.project_id
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving new task: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve new task")


@router.post("/{task_id}/remove", response_model=NewTaskResponse)
async def remove_new_task(
    task_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Remove/reject a new task"""
    try:
        service = NewTaskService(db)
        return await service.remove_task(task_id, current_user.get('tenant_schema'))
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing new task: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove new task")


@router.delete("/{task_id}")
async def delete_new_task(
    task_id: int,
    current_user: dict = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """Delete a new task"""
    try:
        service = NewTaskService(db)
        await service.delete_task(task_id, current_user.get('tenant_schema'))
        return {"message": "Task deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting new task: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete new task")
