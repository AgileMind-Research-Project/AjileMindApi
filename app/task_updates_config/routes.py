"""
Task Updates API Routes
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Dict, Any, Optional

from app.db.database import db, Database
from app.utils.jwt import get_current_user_from_token
from app.task_updates_config.models import (
    TaskUpdateResponse, TaskUpdateApproval,
    ExtractionResponse
)
from app.task_updates_config.service import TaskUpdatesService
from app.core.logger import logger

router = APIRouter()


async def get_service() -> TaskUpdatesService:
    """Dependency to get service instance"""
    return TaskUpdatesService(db)


@router.post(
    "/extract/{meeting_id}",
    response_model=ExtractionResponse,
    summary="Extract Task Updates from Meeting",
    description="Use AI to extract task updates from meeting transcript"
)
async def extract_from_meeting(
    meeting_id: str,
    force_reextract: bool = Query(False, description="Re-extract even if already processed"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: TaskUpdatesService = Depends(get_service)
):
    """Extract task updates using Mistral-7B AI"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        result = await service.extract_from_meeting(tenant_name, meeting_id, force_reextract)
        
       # Get extractions to return
        updates = await service.list_by_meeting(tenant_name, meeting_id)
        
        from app.task_updates_config.models import TaskUpdateExtract, DetectedStatus
        extractions = [
            TaskUpdateExtract(
                ticket_id=u['ticket_id'],
                detected_status=DetectedStatus(u['detected_status']),
                blocker_description=u.get('blocker_description'),
                ai_confidence_score=float(u.get('ai_confidence_score', 0)),
                ai_reasoning=u.get('ai_reasoning', ''),
                extracted_context=u.get('extracted_context', '')
            )
            for u in updates
        ]
        
        return ExtractionResponse(
            meeting_id=meeting_id,
            total_extracted=result['total_extracted'],
            extractions=extractions,
            processing_time_ms=result.get('processing_time_ms', 0)
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error extracting updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/meeting/{meeting_id}",
    response_model=List[TaskUpdateResponse],
    summary="Get Task Updates for Meeting",
    description="List all task updates extracted from a specific meeting"
)
async def get_meeting_updates(
    meeting_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: TaskUpdatesService = Depends(get_service)
):
    """Get all task updates for a meeting"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        updates = await service.list_by_meeting(tenant_name, meeting_id)
        return updates
    
    except Exception as e:
        logger.error(f"Error fetching updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pending",
    response_model=List[TaskUpdateResponse],
    summary="List Pending Approvals",
    description="Get all task updates awaiting human approval"
)
async def list_pending_approvals(
    project_id: Optional[int] = Query(None, description="Filter by project"),
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: TaskUpdatesService = Depends(get_service)
):
    """List pending task updates"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        updates = await service.list_pending(tenant_name, project_id)
        return updates
    
    except Exception as e:
        logger.error(f"Error listing pending: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{update_id}/approve",
    response_model=TaskUpdateResponse,
    summary="Approve Task Update",
    description="Approve a task update for Jira sync"
)
async def approve_update(
    update_id: int,
    approval: TaskUpdateApproval,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: TaskUpdatesService = Depends(get_service)
):
    """Approve task update"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        user_id = current_user.get("user_id") or current_user.get("email")
        
        result = await service.approve_update(
            tenant_name, 
            update_id, 
            user_id, 
            approval.reviewer_remark
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Task update not found")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{update_id}/reject",
    response_model=TaskUpdateResponse,
    summary="Reject Task Update",
    description="Reject a task update"
)
async def reject_update(
    update_id: int,
    approval: TaskUpdateApproval,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: TaskUpdatesService = Depends(get_service)
):
    """Reject task update"""
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        user_id = current_user.get("user_id") or current_user.get("email")
        
        result = await service.reject_update(
            tenant_name, 
            update_id, 
            user_id, 
            approval.reviewer_remark
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Task update not found")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/debug/model-status",
    summary="Get AI Model Status",
    description="Debug endpoint to check Mistral-7B model status"
)
async def get_model_status(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
):
    """Get current AI model status for debugging"""
    try:
        from app.ai.task_extractor.extractor import get_task_extractor
        
        extractor = get_task_extractor()
        status = extractor.get_status()
        
        return {
            "status": "ok",
            "model_info": status,
            "timestamp": logger.info("Model status checked")
        }
    
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
