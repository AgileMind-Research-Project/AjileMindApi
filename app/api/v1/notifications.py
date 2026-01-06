from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from app.utils.jwt import get_current_user_from_token
from app.db.database import db, Database
from app.schemas.notification_schemas import DowntimeNotificationRequest, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter()

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
            sender_email=current_user.get("email")
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
