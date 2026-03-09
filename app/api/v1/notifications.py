"""
Notifications API Endpoints

Handles notification CRUD operations.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.db.database import db, Database
from app.core.logger import logger
from app.utils.jwt import get_current_user_from_token
from pydantic import BaseModel, Field


from app.schemas.notification_schemas import DowntimeNotificationRequest, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter()


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class CreateNotificationRequest(BaseModel):
    """Request model for creating a notification"""
    tenant_name: str = Field(..., description="Tenant database name")
    header: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    related_users: List[str] = Field(..., min_items=1, description="List of user emails")
    notification_type: str = Field(default="INFO", pattern="^(INFO|WARNING|SUCCESS|ERROR)$")


class NotificationResponse(BaseModel):
    """Response model for a notification"""
    id: int
    header: str
    description: str
    related_users: List[str]
    is_read: bool
    notification_type: str
    created_at: str
    updated_at: str


# ============================================
# DEPENDENCIES
# ============================================

async def get_database() -> Database:
    """Dependency to get database instance"""
    return db


# ============================================
# NOTIFICATION ENDPOINTS
# ============================================

@router.get(
    "",
    summary="Get User Notifications",
    description="Get all notifications for the current user"
)
async def get_user_notifications(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get all notifications for the current logged-in user.
    
    Notifications are filtered by the user's email in the related_users JSON array.
    """
    try:
        # Get tenant domain from JWT
        tenant_name = current_user.get("tenant_name")
        user_email = current_user.get("email")
        
        if not tenant_name or not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name or user email not found in token"
            )
        
        # Query notifications where user email is in related_users JSON array
        query = """
            SELECT 
                id,
                header,
                description,
                related_users,
                is_read,
                notification_type,
                created_at,
                updated_at
            FROM notifications
            WHERE JSON_CONTAINS(related_users, JSON_QUOTE(%s))
            ORDER BY created_at DESC
        """
        
        notifications = await database.execute_query(
            query,
            (user_email,),
            fetch_all=True,
            schema=tenant_name
        )
        
        # Parse JSON fields
        result = []
        if notifications:
            import json
            for notification in notifications:
                # Parse related_users JSON
                related_users = []
                if notification.get("related_users"):
                    try:
                        related_users = json.loads(notification["related_users"]) if isinstance(notification["related_users"], str) else notification["related_users"]
                    except:
                        related_users = []
                
                result.append({
                    "id": notification["id"],
                    "header": notification["header"],
                    "description": notification["description"],
                    "related_users": related_users,
                    "is_read": bool(notification["is_read"]),
                    "notification_type": notification["notification_type"],
                    "created_at": notification["created_at"].isoformat() if notification["created_at"] else "",
                    "updated_at": notification["updated_at"].isoformat() if notification["updated_at"] else ""
                })
        
        logger.info(f"Retrieved {len(result)} notifications for user {user_email}")
        
        return {
            "success": True,
            "message": f"Found {len(result)} notification(s)",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notifications: {str(e)}"
        )


@router.post(
    "",
    summary="Create Notification",
    description="Create a new notification for specified users (Public API for Lambda functions)"
)
async def create_notification(
    request: CreateNotificationRequest,
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """
    Create a new notification for one or more users.
    
    This endpoint is PUBLIC and designed to be called by Lambda functions.
    No authentication required.
    """
    try:
        tenant_name = request.tenant_name
        
        import json
        related_users_json = json.dumps(request.related_users)
        
        # Insert notification
        query = """
            INSERT INTO notifications (
                header,
                description,
                related_users,
                notification_type,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, NOW(), NOW())
        """
        
        await database.execute_query(
            query,
            (
                request.header,
                request.description,
                related_users_json,
                request.notification_type
            ),
            commit=True,
            schema=tenant_name
        )
        
        logger.info(f"Notification created for {len(request.related_users)} user(s) in {tenant_name}")
        
        return {
            "success": True,
            "message": "Notification created successfully",
            "data": {
                "header": request.header,
                "related_users": request.related_users,
                "notification_type": request.notification_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@router.put(
    "/{notification_id}/read",
    summary="Mark Notification as Read",
    description="Mark a notification as read"
)
async def mark_notification_read(
    notification_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Mark a notification as read."""
    try:
        tenant_name = current_user.get("tenant_name")
        user_email = current_user.get("email")
        
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Check if notification exists and user has access
        check_query = """
            SELECT id FROM notifications
            WHERE id = %s AND JSON_CONTAINS(related_users, JSON_QUOTE(%s))
        """
        
        notification = await database.execute_query(
            check_query,
            (notification_id, user_email),
            fetch_one=True,
            schema=tenant_name
        )
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied"
            )
        
        # Mark as read
        update_query = """
            UPDATE notifications
            SET is_read = TRUE, updated_at = NOW()
            WHERE id = %s
        """
        
        await database.execute_query(
            update_query,
            (notification_id,),
            commit=True,
            schema=tenant_name
        )
        
        logger.info(f"Notification {notification_id} marked as read by {user_email}")
        
        return {
            "success": True,
            "message": "Notification marked as read",
            "data": {"id": notification_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.delete(
    "/{notification_id}",
    summary="Delete Notification",
    description="Delete a notification"
)
async def delete_notification(
    notification_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    database: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Delete a notification (only if user has access to it)."""
    try:
        tenant_name = current_user.get("tenant_name")
        user_email = current_user.get("email")
        
        if not tenant_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant name not found in token"
            )
        
        # Check if notification exists and user has access
        check_query = """
            SELECT id FROM notifications
            WHERE id = %s AND JSON_CONTAINS(related_users, JSON_QUOTE(%s))
        """
        
        notification = await database.execute_query(
            check_query,
            (notification_id, user_email),
            fetch_one=True,
            schema=tenant_name
        )
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied"
            )
        
        # Delete notification
        delete_query = "DELETE FROM notifications WHERE id = %s"
        
        await database.execute_query(
            delete_query,
            (notification_id,),
            commit=True,
            schema=tenant_name
        )
        
        logger.info(f"Notification {notification_id} deleted by {user_email}")
        
        return {
            "success": True,
            "message": "Notification deleted successfully",
            "data": {"id": notification_id}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )


def get_notification_service(database: Database = Depends(lambda: db)) -> NotificationService:
    return NotificationService(database)

@router.post(
    "/downtime",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Send Downtime Notification",
    description="Send a downtime or maintenance notification to users"
)
async def send_downtime_notification(
    request: DowntimeNotificationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: NotificationService = Depends(get_notification_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name not found")
        
        # Verify admin permissions (optional, but good practice)
        # if current_user.get("role") not in ["ADMIN", "SUPER_ADMIN", "PROJECT_MANAGER"]:
        #     raise HTTPException(status_code=403, detail="Insufficient permissions")
            
        result = await service.send_downtime_notification(
            tenant_name=tenant_name,
            request=request,
            sender_email=current_user.get("email"),
            sender_id=current_user.get("user_id")
        )
        
        return NotificationResponse(
            success=True,
            message=f"Downtime notification sent successfully ({result.get('sent_count')} recipients)",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/downtime",
    status_code=status.HTTP_200_OK,
    summary="List Downtime Notifications",
    description="Get a paginated list of sent and scheduled downtime notifications"
)
async def list_downtime_notifications(
    page: int = 1,
    page_size: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    service: NotificationService = Depends(get_notification_service)
):
    try:
        tenant_name = current_user.get("tenant_name")
        if not tenant_name:
             raise HTTPException(status_code=400, detail="Tenant name not found")
             
        result = await service.list_downtime_notifications(
            tenant_name=tenant_name,
            page=page,
            page_size=page_size
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
