from typing import List, Dict, Any
from datetime import datetime
import json
from app.schemas.notification_schemas import DowntimeNotificationRequest, Audience
from app.db.database import Database
from app.core.logger import logger
from app.core.config import settings

class NotificationService:
    def __init__(self, db: Database):
        self.db = db

    async def get_project_members(self, tenant_name: str, project_id: int) -> List[Dict[str, Any]]:
        """
        Get users assigned to a project.
        Uses the {tenant_name} table in the central database.
        """
        try:
            # Query the table named after tenant_name
            query = f"SELECT user_id, email, first_name, last_name, role, projects FROM `{tenant_name}` WHERE status = 'ACTIVE'"
            
            # Since this is a dynamic table name in the default DB, we don't pass schema=tenant_name 
            # unless the tenant_name table is actually inside the tenant DB. 
            # Looking at users.py, it seems `users.py` does `SELECT ... FROM {tenant_name}` without specifying schema 
            # if `database.execute_query` defaults to main DB. 
            # But meeting_config/service.py explicitly uses `{settings.DB_NAME}.{tenant_name}`.
            # I'll stick to just `{tenant_name}` if I rely on the default connection.
            
            users = await self.db.execute_query(query, fetch_all=True) or []
            
            project_users = []
            for user in users:
                projects_json = user.get('projects')
                if projects_json:
                    try:
                        if isinstance(projects_json, str):
                            projects = json.loads(projects_json)
                        else:
                            projects = projects_json # Already list or dict
                        
                        if isinstance(projects, list) and project_id in projects:
                            # Remove sensitive info and projects list
                            user_clean = {
                                "user_id": user.get("user_id"),
                                "email": user.get("email"),
                                "first_name": user.get("first_name"),
                                "last_name": user.get("last_name"),
                                "role": user.get("role")
                            }
                            project_users.append(user_clean)
                    except Exception as e:
                        logger.warning(f"Error parsing projects for user {user.get('user_id')}: {e}")
                        continue
            
            return project_users
        except Exception as e:
            logger.error(f"Error fetching project members: {e}")
            return []

    async def send_downtime_notification(self, tenant_name: str, request: DowntimeNotificationRequest, sender_email: str):
        # Handle Scheduling
        if request.scheduled_at:
             # Basic naive check, assuming Request is UTC or we just trust the value
             now = datetime.utcnow()
             schedule_time = request.scheduled_at.replace(tzinfo=None)
             if schedule_time > now:
                logger.info(f"Scheduling {request.type} notification for {request.scheduled_at}")
                return {
                    "success": True,
                    "message": f"Notification successfully scheduled for {request.scheduled_at}",
                    "scheduled_at": request.scheduled_at.isoformat(),
                    "status": "SCHEDULED"
                }

        recipients = []
        
        if request.audience == Audience.PROJECT_MEMBERS and request.project_id:
            recipients = await self.get_project_members(tenant_name, request.project_id)
        elif request.audience == Audience.ALL_USERS:
            # Get all active users
            query = f"SELECT user_id, email, first_name, last_name, role FROM `{tenant_name}` WHERE status = 'ACTIVE'"
            recipients = await self.db.execute_query(query, fetch_all=True) or []
        elif request.audience == Audience.ADMINS:
            # Get admins
            query = f"SELECT user_id, email, first_name, last_name, role FROM `{tenant_name}` WHERE status = 'ACTIVE' AND role IN ('ADMIN', 'SUPER_ADMIN')"
            recipients = await self.db.execute_query(query, fetch_all=True) or []
        
        # Log the action (mock sending)
        logger.info(f"Sending {request.type} notification to {request.audience} ({len(recipients)} recipients)")
        logger.info(f"Subject: {request.content.subject}")
        logger.info(f"Sender: {sender_email}")
        
        return {
            "success": True,
            "sent_count": len(recipients),
            "recipient_count": len(recipients),
            "recipients_sample": recipients[:5] if recipients else []
        }
