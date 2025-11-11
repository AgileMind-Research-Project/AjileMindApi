"""
Audit Logs API Endpoints

Manage audit logs (Super Admin only).
"""

from fastapi import APIRouter, HTTPException, status, Request, Header, Depends
from typing import Dict, Any, Optional
from datetime import datetime

from app.schemas.audit_schemas import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditLogFilterRequest,
    AuditSettingsResponse,
    AuditSettingsUpdateRequest,
    ClearAuditLogsRequest,
    StandardResponse
)
from app.db.repositories.audit_repository import AuditRepository
from app.db.database import db
from app.core.logger import logger
from app.utils.jwt import get_user_from_token

router = APIRouter()


async def verify_super_admin(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Verify Super Admin access with JWT token.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    token = authorization.replace("Bearer ", "")
    
    # Decode and verify JWT token
    user = get_user_from_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Check if user is Super Admin
    if user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required"
        )
    
    return user


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="Get Audit Logs",
    description="Get audit logs with optional filters (Super Admin only)"
)
async def get_audit_logs(
    request: Request,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    user: Dict[str, Any] = Depends(verify_super_admin)
) -> Dict[str, Any]:
    """
    Get audit logs with filters and pagination.
    
    Query Parameters:
    - event_type: Filter by event type
    - user_id: Filter by user ID
    - start_date: Filter logs after this date (ISO format)
    - end_date: Filter logs before this date (ISO format)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 100)
    """
    try:
        # Get tenant_id from authenticated user
        tenant_id = user["tenant_id"]
        
        # Check if audit logging is enabled
        audit_repo = AuditRepository(db)
        settings = await audit_repo.get_audit_settings(tenant_id)
        
        if not settings["audit_logging_enabled"]:
            return {
                "success": True,
                "message": "Audit logging is disabled",
                "data": {
                    "logs": [],
                    "pagination": {
                        "page": 1,
                        "page_size": page_size,
                        "total": 0,
                        "total_pages": 0
                    }
                }
            }
        
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format"
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format"
                )
        
        # Validate page_size
        if page_size > 100:
            page_size = 100
        
        # Get logs
        result = await audit_repo.get_audit_logs(
            tenant_id=tenant_id,
            event_type=event_type,
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            page=page,
            page_size=page_size
        )
        
        return {
            "success": True,
            "message": "Audit logs retrieved successfully",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


@router.get(
    "/settings",
    response_model=StandardResponse,
    summary="Get Audit Settings",
    description="Get audit logging settings (Super Admin only)"
)
async def get_audit_settings(
    user: Dict[str, Any] = Depends(verify_super_admin)
) -> Dict[str, Any]:
    """Get audit logging settings for tenant"""
    try:
        tenant_id = user["tenant_id"]
        
        audit_repo = AuditRepository(db)
        settings = await audit_repo.get_audit_settings(tenant_id)
        
        return {
            "success": True,
            "message": "Audit settings retrieved successfully",
            "data": settings
        }
        
    except Exception as e:
        logger.error(f"Error getting audit settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit settings"
        )


@router.put(
    "/settings",
    response_model=StandardResponse,
    summary="Update Audit Settings",
    description="Update audit logging settings (Super Admin only)"
)
async def update_audit_settings(
    request: AuditSettingsUpdateRequest,
    user: Dict[str, Any] = Depends(verify_super_admin)
) -> Dict[str, Any]:
    """
    Update audit logging settings.
    
    Body:
    - audit_logging_enabled: Enable/disable audit logging
    - retention_days: Number of days to retain logs (1-365)
    """
    try:
        tenant_id = user["tenant_id"]
        user_id = user["user_id"]
        
        audit_repo = AuditRepository(db)
        
        # Update settings
        settings = await audit_repo.update_audit_settings(
            tenant_id=tenant_id,
            audit_logging_enabled=request.audit_logging_enabled,
            retention_days=request.retention_days or 90
        )
        
        # Log the settings change
        event_type = "audit_logging_enabled" if request.audit_logging_enabled else "audit_logging_disabled"
        await audit_repo.create_audit_log(
            tenant_id=tenant_id,
            event_type=event_type,
            user_id=user_id,
            event_data={
                "audit_logging_enabled": request.audit_logging_enabled,
                "retention_days": request.retention_days or 90
            }
        )
        
        return {
            "success": True,
            "message": "Audit settings updated successfully",
            "data": settings
        }
        
    except Exception as e:
        logger.error(f"Error updating audit settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update audit settings"
        )


@router.delete(
    "",
    response_model=StandardResponse,
    summary="Clear Audit Logs",
    description="Clear audit logs (all or selected) (Super Admin only)"
)
async def clear_audit_logs(
    request: ClearAuditLogsRequest,
    user: Dict[str, Any] = Depends(verify_super_admin)
) -> Dict[str, Any]:
    """
    Clear audit logs.
    
    Body:
    - log_ids: Array of log IDs to delete (optional, if not provided clears all)
    - before_date: Delete logs before this date (optional)
    """
    try:
        tenant_id = user["tenant_id"]
        user_id = user["user_id"]
        
        audit_repo = AuditRepository(db)
        
        deleted_count = 0
        
        if request.log_ids:
            # Delete specific logs
            deleted_count = await audit_repo.delete_audit_logs_by_ids(request.log_ids)
            message = f"Deleted {deleted_count} audit log(s)"
            
        elif request.before_date:
            # Delete logs before date
            deleted_count = await audit_repo.delete_audit_logs_before_date(
                tenant_id=tenant_id,
                before_date=request.before_date
            )
            message = f"Deleted audit logs before {request.before_date}"
            
        else:
            # Clear all logs
            await audit_repo.clear_all_audit_logs(tenant_id)
            message = "All audit logs cleared"
        
        # Log the clearing action
        await audit_repo.create_audit_log(
            tenant_id=tenant_id,
            event_type="audit_logs_cleared",
            user_id=user_id,
            event_data={
                "log_ids": request.log_ids,
                "before_date": request.before_date.isoformat() if request.before_date else None,
                "deleted_count": deleted_count
            }
        )
        
        return {
            "success": True,
            "message": message,
            "data": {
                "deleted_count": deleted_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error clearing audit logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear audit logs"
        )


@router.get(
    "/event-types",
    summary="Get Event Types",
    description="Get list of available audit event types"
)
async def get_event_types() -> Dict[str, Any]:
    """Get list of available audit event types for filtering"""
    from app.schemas.audit_schemas import EventType
    
    event_types = [
        {"value": event.value, "label": event.value.replace("_", " ").title()}
        for event in EventType
    ]
    
    return {
        "success": True,
        "message": "Event types retrieved successfully",
        "data": {
            "event_types": event_types
        }
    }


@router.post(
    "/cleanup",
    response_model=StandardResponse,
    summary="Cleanup Old Logs",
    description="Manually trigger cleanup of old audit logs based on retention policy"
)
async def cleanup_old_logs(
    user: Dict[str, Any] = Depends(verify_super_admin)
) -> Dict[str, Any]:
    """Manually trigger cleanup of old audit logs"""
    try:
        tenant_id = user["tenant_id"]
        
        audit_repo = AuditRepository(db)
        
        # Get retention settings
        settings = await audit_repo.get_audit_settings(tenant_id)
        retention_days = settings["retention_days"]
        
        # Cleanup old logs
        await audit_repo.cleanup_old_logs(tenant_id, retention_days)
        
        return {
            "success": True,
            "message": f"Cleaned up logs older than {retention_days} days",
            "data": {
                "retention_days": retention_days
            }
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup logs"
        )
