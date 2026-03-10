from typing import List, Dict, Any
from datetime import datetime
import json
import pytz
from app.schemas.notification_schemas import DowntimeNotificationRequest, Audience
from app.db.database import Database
from app.core.logger import logger
from app.core.config import settings

class NotificationService:
    def __init__(self, db: Database):
        self.db = db
        self.colombo_tz = pytz.timezone('Asia/Colombo')

    def _to_db_naive(self, dt: datetime) -> datetime:
        """Ensure datetime is naive and representing Colombo time for DB storage"""
        if dt is None:
            return None
        
        # If the datetime has timezone info, convert it to Colombo first
        if dt.tzinfo is not None:
            dt = dt.astimezone(self.colombo_tz)
        
        # Strip timezone to store as naive (which the user prefers)
        return dt.replace(tzinfo=None)
    
    def get_colombo_now(self) -> datetime:
        """Get current Colombo time as a naive datetime"""
        return datetime.now(self.colombo_tz).replace(tzinfo=None)

    async def get_project_members(self, tenant_name: str, project_id: int) -> List[Dict[str, Any]]:
        """
        Get users assigned to a project.
        Uses the {tenant_name} table in the central database.
        """
        try:
            query = f"SELECT user_id, email, first_name, last_name, role, projects FROM `{settings.DB_NAME}`.`{tenant_name}` WHERE status = 'ACTIVE'"
            
            users = await self.db.execute_query(query, fetch_all=True) or []
            
            project_users = []
            for user in users:
                projects_json = user.get('projects')
                if projects_json:
                    try:
                        if isinstance(projects_json, str):
                            projects = json.loads(projects_json)
                        else:
                            projects = projects_json
                        
                        if isinstance(projects, list):
                            project_id_str = str(project_id)
                            projects_str_list = [str(p) for p in projects]
                            
                            if project_id_str in projects_str_list:
                                project_users.append({
                                    "user_id": user.get("user_id"),
                                    "email": user.get("email"),
                                    "first_name": user.get("first_name"),
                                    "last_name": user.get("last_name"),
                                    "role": user.get("role")
                                })
                    except: continue
            return project_users
        except Exception as e:
            logger.error(f"Error fetching project members: {e}")
            return []

    async def send_downtime_notification(self, tenant_name: str, request: DowntimeNotificationRequest, sender_email: str, sender_id: str = None):
        # 1. Determine Status & Timing
        scheduled_time = self._to_db_naive(request.scheduled_at)
        is_scheduled = bool(scheduled_time)
        status = "SCHEDULED" if is_scheduled else "SENT"
        
        # 2. Persist Notification (Single-Row Model)
        try:
            affected_components_json = json.dumps(request.affected_components) if request.affected_components else "[]"
            target_emails_json = json.dumps(request.target_emails) if request.target_emails else "[]"
            
            release_note_status = "NONE"
            release_note_body = None
            if request.include_release_note and request.release_note_content:
                release_note_status = "SCHEDULED"
                release_note_body = request.release_note_content.message_body

            insert_query = f"""
                INSERT INTO `{tenant_name}`.downtime_notifications 
                (type, priority, affected_components, target_emails, start_time, end_time, timezone, 
                 subject, message_body, audience, project_id, scheduled_at, status, created_by, sent_by_user_id, 
                 release_note_status, release_note_content, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            params = (
                request.type.value if hasattr(request.type, 'value') else request.type,
                request.priority.value if hasattr(request.priority, 'value') else request.priority,
                affected_components_json,
                target_emails_json,
                self._to_db_naive(request.schedule.start_time),
                self._to_db_naive(request.schedule.end_time),
                request.schedule.timezone,
                request.content.subject,
                request.content.message_body,
                request.audience.value if hasattr(request.audience, 'value') else request.audience,
                request.project_id if request.project_id else None,
                scheduled_time,
                status,
                sender_email,
                sender_id,
                release_note_status,
                release_note_body
            )
            
            result = await self.db.execute_query(insert_query, params, commit=True)
            notification_id = int(result)
            
            if not is_scheduled:
                row = await self.db.execute_query(f"SELECT * FROM `{tenant_name}`.downtime_notifications WHERE id=%s", (notification_id,), fetch_one=True)
                if row: await self._send_alert(tenant_name, row)

            return {"success": True, "message": f"Notification {'scheduled' if is_scheduled else 'sent'}", "notification_id": notification_id}
        except Exception as e:
            logger.error(f"Failed send notification: {e}")
            raise

    async def update_downtime_notification(self, tenant_name: str, notification_id: int, request: DowntimeNotificationRequest):
        try:
            affected_components_json = json.dumps(request.affected_components) if request.affected_components else "[]"
            target_emails_json = json.dumps(request.target_emails) if request.target_emails else "[]"
            rn_status = "SCHEDULED" if request.include_release_note else "NONE"
            rn_body = request.release_note_content.message_body if request.release_note_content else None

            update_query = f"""
                UPDATE `{tenant_name}`.downtime_notifications 
                SET type=%s, priority=%s, affected_components=%s, target_emails=%s, 
                    start_time=%s, end_time=%s, timezone=%s, subject=%s, message_body=%s, 
                    audience=%s, project_id=%s, scheduled_at=%s, status=%s,
                    release_note_status=%s, release_note_content=%s
                WHERE id=%s
            """
            params = (
                request.type.value if hasattr(request.type, 'value') else request.type,
                request.priority.value if hasattr(request.priority, 'value') else request.priority,
                affected_components_json,
                target_emails_json,
                self._to_db_naive(request.schedule.start_time),
                self._to_db_naive(request.schedule.end_time),
                request.schedule.timezone,
                request.content.subject,
                request.content.message_body,
                request.audience.value if hasattr(request.audience, 'value') else request.audience,
                request.project_id if request.project_id else None,
                self._to_db_naive(request.scheduled_at),
                "SCHEDULED", rn_status, rn_body, notification_id
            )
            await self.db.execute_query(update_query, params, commit=True)
            return {"success": True, "message": "Updated successfully"}
        except Exception as e:
            logger.error(f"Error update: {e}")
            raise

    async def list_downtime_notifications(self, tenant_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        try:
            offset = (page - 1) * page_size
            query = f"""
                SELECT id, type, priority, subject, message_body as message, audience, project_id, 
                       scheduled_at, status, created_by, created_at, sent_at, start_time, end_time,
                       release_note_status, release_sent_at
                FROM `{tenant_name}`.downtime_notifications
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """
            rows = await self.db.execute_query(query, (page_size, offset), fetch_all=True) or []
            count = await self.db.execute_query(f"SELECT COUNT(*) as total FROM `{tenant_name}`.downtime_notifications", fetch_one=True)
            return {"items": rows, "total": count['total'] if count else 0, "page": page, "page_size": page_size}
        except Exception as e:
            logger.error(f"Error list: {e}")
            raise

    async def delete_downtime_notification(self, tenant_name: str, notification_id: int):
        try:
            await self.db.execute_query(f"DELETE FROM `{tenant_name}`.downtime_notifications WHERE id=%s", (notification_id,), commit=True)
            return {"success": True, "message": "Deleted"}
        except Exception as e:
            logger.error(f"Error delete: {e}")
            raise

    async def process_due_notifications(self):
        try:
            dbs = await self.db.execute_query("SHOW DATABASES", fetch_all=True)
            ignore_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys', 'railway', settings.DB_NAME}
            now = self.get_colombo_now()
            for db_row in dbs:
                tenant_name = list(db_row.values())[0]
                if tenant_name in ignore_dbs: continue
                try:
                    alert_query = f"SELECT * FROM `{tenant_name}`.downtime_notifications WHERE status='SCHEDULED' AND scheduled_at <= %s"
                    alerts = await self.db.execute_query(alert_query, (now,), fetch_all=True)
                    for row in (alerts or []): await self._send_alert(tenant_name, row)
                    
                    rn_query = f"SELECT * FROM `{tenant_name}`.downtime_notifications WHERE release_note_status='SCHEDULED' AND end_time <= %s"
                    notes = await self.db.execute_query(rn_query, (now,), fetch_all=True)
                    for row in (notes or []): await self._send_release_note(tenant_name, row)
                except: continue
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

    async def _send_alert(self, tenant_name: str, row: Dict[str, Any]):
        try:
            request = self._row_to_request(row)
            recipients = await self._get_recipients(tenant_name, row)
            from app.services.email_service import email_service
            await email_service.send_broadcast_template(request, recipients)
            await self.db.execute_query(f"UPDATE `{tenant_name}`.downtime_notifications SET status='SENT', sent_at=NOW() WHERE id=%s", (row['id'],), commit=True)
        except Exception as e:
            logger.error(f"Alert failed: {e}")

    async def _send_release_note(self, tenant_name: str, row: Dict[str, Any]):
        try:
            rn_req = self._row_to_request(row)
            rn_req.type = "FEATURE_UPGRADE"
            rn_req.content.message_body = row.get('release_note_content') or rn_req.content.message_body
            recipients = await self._get_recipients(tenant_name, row)
            from app.services.email_service import email_service
            await email_service.send_broadcast_template(rn_req, recipients)
            await self.db.execute_query(f"UPDATE `{tenant_name}`.downtime_notifications SET release_note_status='SENT', release_sent_at=NOW() WHERE id=%s", (row['id'],), commit=True)
        except Exception as e:
            logger.error(f"RN failed: {e}")

    def _row_to_request(self, row: Dict[str, Any]) -> DowntimeNotificationRequest:
        return DowntimeNotificationRequest(
            type=row['type'], priority=row['priority'],
            affected_components=json.loads(row['affected_components']) if row.get('affected_components') else [],
            schedule={"start_time": row['start_time'], "end_time": row['end_time'], "timezone": row['timezone']},
            audience=row['audience'], project_id=row['project_id'],
            content={"subject": row['subject'], "message_body": row.get('message_body') or row.get('message', '')},
            target_emails=json.loads(row['target_emails']) if row.get('target_emails') else [],
            scheduled_at=row['scheduled_at']
        )

    async def _get_recipients(self, tenant_name: str, row: Dict[str, Any]) -> List[Dict[str, Any]]:
        aud, pid = row['audience'], row.get('project_id')
        emails = json.loads(row['target_emails']) if row.get('target_emails') else []
        if emails: return [{"email": e} for e in emails]
        if aud == "ALL_USERS": return await self.db.execute_query(f"SELECT email FROM `{tenant_name}`.users WHERE status='ACTIVE'", fetch_all=True)
        if aud == "PROJECT_MEMBERS" and pid: return await self.get_project_members(tenant_name, int(pid))
        return []
