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
            # Use fully qualified table name like MeetingService
            query = f"SELECT user_id, email, first_name, last_name, role, projects FROM `{settings.DB_NAME}`.`{tenant_name}` WHERE status = 'ACTIVE'"
            
            users = await self.db.execute_query(query, fetch_all=True) or []
            logger.info(f"DEBUG: Fetched {len(users)} users from table {settings.DB_NAME}.{tenant_name}. Searching for project_id {project_id}...")
            
            project_users = []
            for user in users:
                projects_json = user.get('projects')
                if projects_json:
                    try:
                        if isinstance(projects_json, str):
                            projects = json.loads(projects_json)
                        else:
                            projects = projects_json # Already list or dict
                        
                        if isinstance(projects, list):
                            # Handle potential string/int mismatch
                            project_id_str = str(project_id)
                            projects_str_list = [str(p) for p in projects]
                            
                            if project_id_str in projects_str_list:
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
            
            logger.info(f"DEBUG: Found {len(project_users)} members for project {project_id}")
            return project_users
        except Exception as e:
            logger.error(f"Error fetching project members: {e}")
            return []

    async def send_downtime_notification(self, tenant_name: str, request: DowntimeNotificationRequest, sender_email: str, sender_id: str = None):
        from app.services.email_service import email_service

        # 1. Determine Status & Timing
        # ... existing logic ...
        now = datetime.utcnow()
        scheduled_time = None
        if request.scheduled_at:
             scheduled_time = request.scheduled_at.replace(tzinfo=None)
        
        is_scheduled = bool(scheduled_time)
        status = "SCHEDULED" if is_scheduled else "SENT"
        
        # 2. Persist Notification to DB
        try:
            # Convert lists to JSON strings
            import json
            affected_components_json = json.dumps(request.affected_components) if request.affected_components else json.dumps([])
            target_emails_json = json.dumps(request.target_emails) if request.target_emails else json.dumps([])
            
            insert_query = f"""
                INSERT INTO `{tenant_name}`.downtime_notifications 
                (type, priority, affected_components, target_emails, start_time, end_time, timezone, 
                 subject, message_body, audience, project_id, scheduled_at, status, created_by, sent_by_user_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            # Map enum values to strings
            # If project_id is None, store as NULL (None in Python)
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
                status,
                sender_email,
                sender_id
            )
            
            # Execute insert
            result = await self.db.execute_query(insert_query, params, commit=True)
            notification_id = result
            logger.info(f"Notification persisted ID: {notification_id} Status: {status}")
            
        except Exception as e:
            logger.error(f"Failed to persist notification: {e}")
            # If persistence fails, maybe just log and continue for immediate sending? 
            # Or fail? Better to fail or log error. 
            # For now, we proceed but logging is critical.
            notification_id = None

        # 3. If Scheduled, Return early
        if is_scheduled:
            logger.info(f"Scheduling {request.type} notification for {scheduled_time}")
            return {
                "success": True,
                "message": f"Notification successfully scheduled for {request.scheduled_at}",
                "scheduled_at": request.scheduled_at.isoformat(),
                "status": "SCHEDULED",
                "notification_id": notification_id
            }

        # 4. If Immediate: Fetch Recipients
        recipients = []
        
        # Priority 1: Specific target emails if provided
        if request.target_emails and len(request.target_emails) > 0:
            # We need to build recipient objects from emails
            if request.audience == Audience.PROJECT_MEMBERS and request.project_id:
                # Get names from project members for better greeting
                all_members = await self.get_project_members(tenant_name, request.project_id)
                member_map = {m['email']: m for m in all_members}
                for email in request.target_emails:
                    if email in member_map:
                        recipients.append(member_map[email])
                    else:
                        recipients.append({"email": email, "first_name": "User", "last_name": ""})
            else:
                # Just use emails directly
                recipients = [{"email": email, "first_name": "User", "last_name": ""} for email in request.target_emails]
            logger.info(f"Using {len(recipients)} specific target emails as recipients")
            
        elif request.audience == Audience.PROJECT_MEMBERS and request.project_id:
            all_members = await self.get_project_members(tenant_name, request.project_id)
            if request.target_roles and len(request.target_roles) > 0:
                recipients = [m for m in all_members if m.get('role') in request.target_roles]
                logger.info(f"Filtered recipients by roles {request.target_roles}: {len(recipients)} remaining")
            else:
                recipients = all_members
        elif request.audience == Audience.ALL_USERS:
            # Get all active users
            query = f"SELECT user_id, email, first_name, last_name, role FROM `{tenant_name}` WHERE status = 'ACTIVE'"
            recipients = await self.db.execute_query(query, fetch_all=True) or []
        elif request.audience == Audience.ADMINS:
            # Get admins
            query = f"SELECT user_id, email, first_name, last_name, role FROM `{tenant_name}` WHERE status = 'ACTIVE' AND role IN ('ADMIN', 'SUPER_ADMIN')"
            recipients = await self.db.execute_query(query, fetch_all=True) or []
        
        # 5. Send Emails
        logger.info(f"Sending {request.type} notification to {request.audience} ({len(recipients)} recipients)")
        sent_count = 0
        
        email_subject = f"[{request.priority.value}] {request.content.subject}"
        # Construct simple HTML body if no template
        # Define styling based on Type/Priority
        header_bg = "#3B82F6" # Default Blue
        header_text_color = "#ffffff"
        accent_color = "#EFF6FF"
        border_color = "#BFDBFE"
        text_color = "#1F2937"
        icon = "🔧"
        
        display_type = request.type.value.replace('_', ' ').title()
        
        if request.type == "FEATURE_UPGRADE":
            # Premium Official Release Report Template
            features_html = ""
            improvements_html = ""
            fixes_html = ""
            summary_info = ""
            
            # Try to parse structured content if body is JSON or has markers
            try:
                content_data = None
                if request.content.message_body.strip().startswith('{'):
                    content_data = json.loads(request.content.message_body)
                
                if content_data and isinstance(content_data, dict):
                    # Features
                    if content_data.get('features'):
                        items = "".join([f'<div style="display:flex; gap:15px; margin-bottom:12px;"><span style="color:#cbd5e1; font-weight:900; font-size:12px;">{i+1:02d}</span><p style="margin:0; font-size:14px; font-weight:600; color:#0f172a;">{item}</p></div>' for i, item in enumerate(content_data['features'])])
                        features_html = f'<section style="margin-top:30px; border-top:1px solid #f1f5f9; padding-top:15px;"><h3 style="font-size:10px; font-weight:800; color:#64748b; margin-bottom:15px;">03. NEW FEATURES</h3>{items}</section>'
                    
                    # Improvements
                    if content_data.get('improvements'):
                        items = "".join([f'<div style="background:#f8fafc; border:1px solid #f1f5f9; padding:12px; border-radius:4px; margin-bottom:8px; font-size:13px; color:#475569;">{item}</div>' for item in content_data['improvements']])
                        improvements_html = f'<section style="margin-top:30px; border-top:1px solid #f1f5f9; padding-top:15px;"><h3 style="font-size:10px; font-weight:800; color:#64748b; margin-bottom:15px;">04. ENHANCEMENTS</h3>{items}</section>'
                    
                    # Fixes
                    if content_data.get('bug_fixes'):
                        items = "".join([f'<div style="display:flex; align-items:center; gap:10px; padding:8px; margin-bottom:4px;"><div style="width:4px; height:4px; background:#f59e0b; border-radius:50%;"></div><p style="margin:0; font-size:13px; font-weight:500; color:#64748b;">{item}</p></div>' for item in content_data['bug_fixes']])
                        fixes_html = f'<section style="margin-top:30px; border-top:1px solid #f1f5f9; padding-top:15px;"><h3 style="font-size:10px; font-weight:800; color:#64748b; margin-bottom:15px;">05. FIXED BUGS</h3>{items}</section>'
                    
                    summary_info = content_data.get('summary', request.content.message_body if not content_data else "")
                else:
                    summary_info = request.content.message_body
            except:
                summary_info = request.content.message_body

            email_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
                    body {{ font-family: 'Inter', -apple-system, sans-serif; margin: 0; padding: 0; background-color: #f8fafc; color: #0f172a; }}
                    .doc-container {{ max-width: 650px; margin: 30px auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 4px; box-shadow: 0 10px 40px rgba(0,0,0,0.05); overflow: hidden; }}
                    .top-stripe {{ height: 4px; background-color: #0f172a; }}
                    .header-p {{ padding: 40px 40px 20px 40px; }}
                    .label-sm {{ font-size: 10px; font-weight: 800; color: #1e293b; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }}
                    .title-h1 {{ font-size: 32px; font-weight: 800; tracking-tight: -0.025em; margin: 0 0 25px 0; line-height: 1.1; }}
                    .meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 8px; margin-bottom: 30px; }}
                    .meta-cell {{ padding: 15px; border-right: 1px solid #e2e8f0; }}
                    .meta-cell:last-child {{ border-right: none; }}
                    .meta-label {{ font-size: 9px; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 4px; display: block; }}
                    .meta-value {{ font-size: 13px; font-weight: 700; color: #0f172a; }}
                    .summary-box {{ border-left: 2px solid #0f172a; padding-left: 24px; margin-bottom: 30px; }}
                    .summary-p {{ font-size: 16px; font-weight: 500; color: #475569; font-style: italic; line-height: 1.5; }}
                    .main-content {{ padding: 0 40px 40px 40px; }}
                    .footer-p {{ background-color: #0f172a; padding: 30px 40px; color: #ffffff; }}
                    .footer-brand {{ display: flex; align-items: center; gap: 12px; margin-bottom: 15px; }}
                    .brand-box {{ width: 24px; height: 24px; border: 1.5px solid #ffffff; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 14px; transform: rotate(-2deg); }}
                    .footer-note {{ font-size: 9px; color: #94a3b8; line-height: 1.6; max-width: 350px; opacity: 0.7; }}
                </style>
            </head>
            <body>
                <div class="doc-container">
                    <div class="top-stripe"></div>
                    <div class="header-p">
                        <div class="label-sm"><span style="width:20px; height:2px; background:#1e293b; display:inline-block;"></span> RELEASE DOCUMENTATION</div>
                        <h1 class="title-h1">{request.content.subject}</h1>
                        
                        <div class="meta-grid">
                            <div class="meta-cell">
                                <span class="meta-label">ID Reference</span>
                                <span class="meta-value">RN-PROTOCOL-{datetime.now().strftime('%y%m')}</span>
                            </div>
                            <div class="meta-cell">
                                <span class="meta-label">Version</span>
                                <span class="meta-value">System Sync</span>
                            </div>
                            <div class="meta-cell">
                                <span class="meta-label">Type</span>
                                <span class="meta-value">Security Verified</span>
                            </div>
                        </div>

                        {f'<div class="summary-box"><p class="summary-p">"{summary_info}"</p></div>' if summary_info else ''}
                    </div>

                    <div class="main-content">
                        {features_html}
                        {improvements_html}
                        {fixes_html}
                        
                        <div style="background:#f8fafc; border:1px solid #e2e8f0; padding:20px; border-radius:4px; margin-top:40px;">
                            <h4 style="font-size:10px; font-weight:800; color:#64748b; margin:0 0 10px 0;">07. SUPPORT ENQUIRIES</h4>
                            <p style="font-size:13px; color:#475569; margin-bottom:15px;">For deeper insights or support requests, please contact the product synthesis group.</p>
                            <a href="mailto:support@ajilemind.com" style="background:#0f172a; color:#ffffff; padding:10px 20px; border-radius:4px; font-size:11px; font-weight:700; text-decoration:none; display:inline-block;">Email Support</a>
                        </div>
                    </div>

                    <div class="footer-p">
                        <div class="footer-brand">
                            <div class="brand-box">A</div>
                            <div style="line-height:1">
                                <div style="font-size:11px; font-weight:800;">AgileMind Enterprise</div>
                                <div style="font-size:9px; color:#94a3b8; font-weight:500;">Intelligence Synthesis Group</div>
                            </div>
                        </div>
                        <p class="footer-note">This document is electronically verified and authorized for public distribution. Any unauthorized modification of the synthesis content is strictly prohibited by AI security protocols.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            email_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f4f5; }}
                    .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e4e4e7; }}
                    .header {{ background-color: {header_bg}; color: #ffffff; padding: 20px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px; }}
                    .header .icon {{ font-size: 32px; display: block; margin-bottom: 8px; }}
                    .content {{ padding: 30px; color: #374151; line-height: 1.6; font-size: 15px; }}
                    .meta-badge {{ display: inline-block; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 600; background-color: {accent_color}; color: {text_color}; border: 1px solid {border_color}; margin-bottom: 20px; }}
                    .message-box {{ margin-bottom: 25px; white-space: pre-wrap; }}
                    .details-box {{ background-color: {accent_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 16px; font-size: 13px; }}
                    .detail-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px dashed {border_color}; padding-bottom: 8px; }}
                    .detail-row:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
                    .label {{ font-weight: 600; color: #6b7280; width: 30%; }}
                    .value {{ font-weight: 500; color: #111827; width: 70%; }}
                    .footer {{ background-color: #f8fafc; padding: 15px; text-align: center; color: #9ca3af; font-size: 12px; border-top: 1px solid #e2e8f0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="icon">{icon}</div>
                        <h1>{request.content.subject}</h1>
                    </div>
                    <div class="content">
                        <div class="meta-badge">
                            {display_type} • {request.priority.value} Priority
                        </div>
                        
                        <div class="message-box">
                            <p><strong>Dear {request.audience.value.replace('_', ' ').title().replace('All Users', 'User')},</strong></p>
                            <p>{request.content.message_body}</p>
                        </div>
    
                        <div class="details-box">
                            <div class="detail-row">
                                <span class="label">📅 Start:</span>
                                <span class="value">{request.schedule.start_time.strftime('%Y-%m-%d %H:%M') if hasattr(request.schedule.start_time, 'strftime') else request.schedule.start_time}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">⏳ End:</span>
                                <span class="value">{request.schedule.end_time.strftime('%Y-%m-%d %H:%M') if hasattr(request.schedule.end_time, 'strftime') else request.schedule.end_time}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">📉 Impact:</span>
                                <span class="value">{', '.join(request.affected_components)}</span>
                            </div>
                             <div class="detail-row">
                                <span class="label">🌍 Timezone:</span>
                                <span class="value">{request.schedule.timezone}</span>
                            </div>
                        </div>
                    </div>
                    <div class="footer">
                        &copy; {datetime.now().year} AgileMind Platform. All rights reserved.<br/>
                        This is an automated system notification.
                    </div>
                </div>
            </body>
            </html>
            """
        
        for recipient in recipients:
            email = recipient.get('email')
            if email:
                try:
                    # Use existing email_service.send_email
                    # We pass the constructed HTML body
                    success = email_service.send_email(
                        to_email=email,
                        subject=email_subject,
                        html_body=email_body
                    )
                    if success:
                        sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send email to {email}: {e}")

        # Update DB with sent_at if persisted
        if notification_id:
            try:
                update_query = f"UPDATE `{tenant_name}`.downtime_notifications SET sent_at = NOW() WHERE id = %s"
                await self.db.execute_query(update_query, (notification_id,), commit=True)
            except Exception as e:
                logger.error(f"Failed to update sent_at for notification {notification_id}: {e}")

        return {
            "success": True,
            "sent_count": sent_count,
            "recipient_count": len(recipients),
            "recipients_sample": recipients[:5] if recipients else [],
            "notification_id": notification_id
        }

    async def list_downtime_notifications(self, tenant_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        List downtime notifications with pagination.
        """
        try:
            offset = (page - 1) * page_size
            
            # Count total
            count_query = f"SELECT COUNT(*) as total FROM `{tenant_name}`.downtime_notifications"
            count_result = await self.db.execute_query(count_query, fetch_one=True)
            total = count_result['total'] if count_result else 0
            
            # Fetch records
            query = f"""
                SELECT id, type, priority, subject, message_body as message, audience, project_id, scheduled_at, status, created_by, created_at, sent_at, start_time, end_time
                FROM `{tenant_name}`.downtime_notifications
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            
            rows = await self.db.execute_query(query, (page_size, offset), fetch_all=True) or []
            
            return {
                "items": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

        except Exception as e:
            logger.error(f"Error listing downtime notifications: {e}")
            raise

    async def process_due_notifications(self):
        """
        Check all tenants for scheduled notifications that are due.
        """
        try:
            # 1. Discover Tenants
            dbs = await self.db.execute_query("SHOW DATABASES", fetch_all=True)
            if not dbs: return

            ignore_dbs = {'information_schema', 'mysql', 'performance_schema', 'sys', 'railway', settings.DB_NAME}
            
            for db_row in dbs:
                # dbs is list of dicts, e.g. [{'Database': 'sliit'}, ...]
                tenant_name = list(db_row.values())[0]
                if tenant_name in ignore_dbs: continue

                # 2. Check for Table Existence (Silent Try)
                try:
                    # Quick verify if table exists
                    check = await self.db.execute_query(f"SHOW TABLES FROM `{tenant_name}` LIKE 'downtime_notifications'", fetch_one=True)
                    if not check: continue

                    # 3. Fetch Due Notifications
                    # status='SCHEDULED' AND scheduled_at <= NOW() (in Colombo time)
                    query = f"SELECT * FROM `{tenant_name}`.downtime_notifications WHERE status='SCHEDULED' AND scheduled_at <= %s"
                    rows = await self.db.execute_query(query, (self.get_colombo_now(),), fetch_all=True)

                    if rows:
                        logger.info(f"Scheduler: Found {len(rows)} due notifications in tenant '{tenant_name}'")
                        for row in rows:
                            await self._send_notification_from_row(tenant_name, row)
                
                except Exception as inner_e:
                    # Log but continue to next tenant
                    # logger.warning(f"Skipping tenant {tenant_name}: {inner_e}")
                    continue

        except Exception as e:
            logger.error(f"Error in process_due_notifications: {e}")

    async def _send_notification_from_row(self, tenant_name: str, row: Dict[str, Any]):
        from app.services.email_service import email_service
        
        try:
            notification_id = row['id']
            # Parse fields
            audience_val = row['audience']
            project_id = row.get('project_id')
            
            # Fetch Recipients
            recipients = []
            
            # Priority 1: Specific target emails if stored in DB
            target_emails = []
            if row.get('target_emails'):
                try:
                    target_emails = json.loads(row['target_emails'])
                    if isinstance(target_emails, str): target_emails = json.loads(target_emails)
                except:
                    target_emails = []

            if target_emails and len(target_emails) > 0:
                if audience_val == Audience.PROJECT_MEMBERS.value and project_id:
                     all_members = await self.get_project_members(tenant_name, int(project_id))
                     member_map = {m['email']: m for m in all_members}
                     for email in target_emails:
                         if email in member_map:
                             recipients.append(member_map[email])
                         else:
                             recipients.append({"email": email, "first_name": "User", "last_name": ""})
                else:
                     recipients = [{"email": email, "first_name": "User", "last_name": ""} for email in target_emails]
                logger.info(f"Scheduler: Using {len(recipients)} specific target emails for notification {notification_id}")
                
            elif audience_val == Audience.PROJECT_MEMBERS.value and project_id:
                # We need to fetch project members. 
                # Note: get_project_members expects project_id as int
                all_members = await self.get_project_members(tenant_name, int(project_id))
                recipients = all_members # Assuming no complex role filtering stored in DB for now (or need to parse columns if I add them)
            elif audience_val == Audience.ALL_USERS.value:
                query = f"SELECT user_id, email, first_name, last_name, role FROM `{tenant_name}` WHERE status = 'ACTIVE'"
                recipients = await self.db.execute_query(query, fetch_all=True) or []
            elif audience_val == Audience.ADMINS.value:
                query = f"SELECT user_id, email, first_name, last_name, role FROM `{tenant_name}` WHERE status = 'ACTIVE' AND role IN ('ADMIN', 'SUPER_ADMIN')"
                recipients = await self.db.execute_query(query, fetch_all=True) or []

            if not recipients:
                logger.info(f"No recipients found for notification {notification_id}")
                # Still mark as SENT effectively? Or FAILED. Let's mark SENT with 0 count.
            
            # Construct Email Body
            # Parse JSON affected components
            try:
                affected = json.loads(row['affected_components']) if row.get('affected_components') else []
                if isinstance(affected, str): affected = json.loads(affected) # Handle double encoding if any
            except:
                affected = []

            # Format Dates
            start_str = str(row.get('start_time'))
            end_str = str(row.get('end_time'))
            if row.get('start_time') and hasattr(row['start_time'], 'strftime'):
                start_str = row['start_time'].strftime('%Y-%m-%d %H:%M')
            if row.get('end_time') and hasattr(row['end_time'], 'strftime'):
                end_str = row['end_time'].strftime('%Y-%m-%d %H:%M')

            # Styling
            prio = row['priority']
            typ = row['type']
            
            header_bg = "#3B82F6" 
            text_color = "#1F2937"
            icon = "🔧"
            accent_color = "#EFF6FF"
            border_color = "#BFDBFE"

            if typ == "EMERGENCY_OUTAGE" or prio == "HIGH":
                header_bg = "#DC2626"
                accent_color = "#FEF2F2"
                border_color = "#FECACA"
                text_color = "#991B1B"
                icon = "🚨"
            elif typ == "FEATURE_UPGRADE":
                header_bg = "#16A34A"
                accent_color = "#F0FDF4"
                border_color = "#BBF7D0"
                text_color = "#166534"
                icon = "🚀"
            elif typ == "PLANNED_MAINTENANCE":
                header_bg = "#F59E0B"
                accent_color = "#FFFBEB"
                border_color = "#FDE68A"
                text_color = "#92400E"
                icon = "🛠️"

            display_type = typ.replace('_', ' ').title()
            user_greeting = audience_val.replace('_', ' ').title().replace('All Users', 'User')

            email_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f4f5; }}
                    .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e4e4e7; }}
                    .header {{ background-color: {header_bg}; color: #ffffff; padding: 20px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px; }}
                    .header .icon {{ font-size: 32px; display: block; margin-bottom: 8px; }}
                    .content {{ padding: 30px; color: #374151; line-height: 1.6; font-size: 15px; }}
                    .meta-badge {{ display: inline-block; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 600; background-color: {accent_color}; color: {text_color}; border: 1px solid {border_color}; margin-bottom: 20px; }}
                    .message-box {{ margin-bottom: 25px; white-space: pre-wrap; }}
                    .details-box {{ background-color: {accent_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 16px; font-size: 13px; }}
                    .detail-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px dashed {border_color}; padding-bottom: 8px; }}
                    .detail-row:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
                    .label {{ font-weight: 600; color: #6b7280; width: 30%; }}
                    .value {{ font-weight: 500; color: #111827; width: 70%; }}
                    .footer {{ background-color: #f8fafc; padding: 15px; text-align: center; color: #9ca3af; font-size: 12px; border-top: 1px solid #e2e8f0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="icon">{icon}</div>
                        <h1>{row['subject']}</h1>
                    </div>
                    <div class="content">
                        <div class="meta-badge">
                            {display_type} • {prio} Priority
                        </div>
                        
                        <div class="message-box">
                            <p><strong>Dear {user_greeting},</strong></p>
                            <p>{row['message_body']}</p>
                        </div>

                        <div class="details-box">
                            <div class="detail-row">
                                <span class="label">📅 Start:</span>
                                <span class="value">{start_str}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">⏳ End:</span>
                                <span class="value">{end_str}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">📉 Impact:</span>
                                <span class="value">{', '.join(affected)}</span>
                            </div>
                             <div class="detail-row">
                                <span class="label">🌍 Timezone:</span>
                                <span class="value">{row.get('timezone', 'UTC')}</span>
                            </div>
                        </div>
                    </div>
                    <div class="footer">
                        &copy; {datetime.now().year} AgileMind Platform. All rights reserved.<br/>
                        This is an automated system notification.
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send Emails
            email_subject = f"[{prio}] {row['subject']}"
            sent_count = 0
            for recipient in recipients:
                email = recipient.get('email')
                if email:
                    try:
                        success = email_service.send_email(
                            to_email=email,
                            subject=email_subject,
                            html_body=email_body
                        )
                        if success: sent_count += 1
                    except Exception:
                        pass
            
            # Update Status
            update_query = f"UPDATE `{tenant_name}`.downtime_notifications SET status='SENT', sent_at=NOW() WHERE id=%s"
            await self.db.execute_query(update_query, (notification_id,), commit=True)
            
            logger.info(f"Processed scheduled notification {notification_id}: Sent {sent_count} emails.")
            
        except Exception as e:
            logger.error(f"Failed to process scheduled notification {row.get('id')}: {e}")

    async def update_downtime_notification(self, tenant_name: str, notification_id: int, request: DowntimeNotificationRequest):
        """Update a scheduled downtime notification"""
        try:
            # Check if exists and is scheduled
            check_query = f"SELECT status FROM `{tenant_name}`.downtime_notifications WHERE id = %s"
            existing = await self.db.execute_query(check_query, (notification_id,), fetch_one=True)
            
            if not existing:
                return {"success": False, "message": "Notification not found"}
            
            if existing['status'] != 'SCHEDULED':
                return {"success": False, "message": "Only scheduled notifications can be updated"}

            # Update notification
            affected_components_json = json.dumps(request.affected_components) if request.affected_components else json.dumps([])
            target_emails_json = json.dumps(request.target_emails) if request.target_emails else json.dumps([])

            update_query = f"""
                UPDATE `{tenant_name}`.downtime_notifications 
                SET type = %s, priority = %s, affected_components = %s, target_emails = %s, 
                    start_time = %s, end_time = %s, timezone = %s, subject = %s, 
                    message_body = %s, audience = %s, project_id = %s, scheduled_at = %s
                WHERE id = %s
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
                notification_id
            )
            
            await self.db.execute_query(update_query, params, commit=True)
            
            return {"success": True, "message": "Notification updated successfully"}
            
        except Exception as e:
            logger.error(f"Error updating notification: {e}")
            raise

    async def delete_downtime_notification(self, tenant_name: str, notification_id: int):
        """Delete a downtime notification record"""
        try:
            query = f"DELETE FROM `{tenant_name}`.downtime_notifications WHERE id = %s"
            result = await self.db.execute_query(query, (notification_id,), commit=True)
            
            if result.rowcount == 0:
                return {"success": False, "message": "Notification not found"}
                
            return {"success": True, "message": "Notification deleted successfully"}
            
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            raise
