from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Dict, Any, Optional
from datetime import date

from app.db.database import db, Database
from app.utils.jwt import get_current_user_from_token
from app.meeting_config.models import MeetingCreate, MeetingUpdate, MeetingResponse
from app.meeting_config.service import MeetingService
from app.core.logger import logger

router = APIRouter()

async def get_meeting_service() -> MeetingService:
    return MeetingService(db)

@router.post(
    "/",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Meeting",
    description="Create a new meeting"
)
async def create_meeting(
    meeting_data: MeetingCreate,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: MeetingService = Depends(get_meeting_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
            
        user_id = current_user.get("user_id") or current_user.get("email")
        
        result = await service.create_meeting(tenant_name, meeting_data, user_id)
        return result
        
    except Exception as e:
        logger.error(f"Error creating meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/",
    summary="List Meetings",
    description="List meetings with optional filters"
)
async def list_meetings(
    project_id: Optional[int] = None,
    date_filter: Optional[date] = Query(None, alias="date"),
    meeting_category: Optional[str] = Query(None, description="Filter by meeting category"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: MeetingService = Depends(get_meeting_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
            
        return await service.list_meetings(tenant_name, project_id, date_filter, meeting_category)
        
    except Exception as e:
        logger.error(f"Error listing meetings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="Get Meeting",
    description="Get meeting details by ID"
)
async def get_meeting(
    meeting_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: MeetingService = Depends(get_meeting_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
            
        meeting = await service.get_meeting_by_meeting_id(tenant_name, meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
            
        return meeting
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="Update Meeting",
    description="Update meeting details"
)
async def update_meeting(
    meeting_id: str,
    updates: MeetingUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: MeetingService = Depends(get_meeting_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
            
        result = await service.update_meeting(tenant_name, meeting_id, updates)
        if not result:
            raise HTTPException(status_code=404, detail="Meeting not found")
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/{meeting_id}",
    summary="Delete Meeting",
    description="Delete a meeting"
)
async def delete_meeting(
    meeting_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: MeetingService = Depends(get_meeting_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
            
        success = await service.delete_meeting(tenant_name, meeting_id)
        if not success:
            raise HTTPException(status_code=404, detail="Meeting not found")
            
        return {"success": True, "message": "Meeting deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/project/{project_id}/users",
    summary="Get Project Users",
    description="Get users assigned to a specific project"
)
async def get_project_users(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: MeetingService = Depends(get_meeting_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
            
        # Get users for the project
        users = await service.get_project_users(tenant_name, project_id)
        
        return {
            "success": True,
            "data": users
        }
        
    except Exception as e:
        logger.error(f"Error getting project users: {e}")
        raise HTTPException(status_code=500, detail=str(e))
