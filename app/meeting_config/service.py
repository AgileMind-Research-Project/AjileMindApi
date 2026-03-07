from typing import List, Dict, Any, Optional
from datetime import datetime, date
import json
from uuid import uuid4

from app.db.database import Database
from app.core.logger import logger
from app.core.config import settings
from app.meeting_config.models import MeetingCreate, MeetingUpdate, MeetingStatus


class MeetingService:
    def __init__(self, db: Database):
        self.db = db

    async def create_meeting(self, tenant_name: str, meeting_data: MeetingCreate, created_by: str) -> Dict[str, Any]:
        try:
            meeting_id = str(uuid4())
            
            query = """
                INSERT INTO meetings (
                    meeting_id, project_id, sprint_id, title,
                    meeting_category, meeting_date, start_time, end_time,
                    status, meeting_link, attendees, created_by,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            await self.db.execute_query(
                query,
                (
                    meeting_id,
                    meeting_data.project_id or 0,
                    0,  # default sprint_id
                    meeting_data.title,
                    meeting_data.category,
                    meeting_data.date,
                    meeting_data.start_time,
                    meeting_data.end_time,
                    MeetingStatus.SCHEDULED.value,
                    '',  # meeting_link
                    json.dumps(meeting_data.attendees) if meeting_data.attendees else None,
                    created_by
                ),
                commit=True,
                schema=tenant_name
            )
            
            # Fetch created meeting
            return await self.get_meeting_by_meeting_id(tenant_name, meeting_id)
            
        except Exception as e:
            logger.error(f"Error creating meeting: {str(e)}")
            raise

    async def get_meeting_by_meeting_id(self, tenant_name: str, meeting_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM meetings WHERE meeting_id = %s"
        result = await self.db.execute_query(query, (meeting_id,), fetch_one=True, schema=tenant_name)
        if result and isinstance(result.get('attendees'), str):
            try:
                result['attendees'] = json.loads(result['attendees'])
            except:
                result['attendees'] = []
        return result

    async def list_meetings(self, tenant_name: str, project_id: Optional[int] = None, date_filter: Optional[date] = None, meeting_category: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT m.*, t.transcript_content, t.id as transcript_id
            FROM meetings m
            LEFT JOIN transcripts t ON t.meeting_id COLLATE utf8mb4_unicode_ci = m.meeting_id COLLATE utf8mb4_unicode_ci
            WHERE 1=1
        """
        params = []
        
        if project_id:
            query += " AND m.project_id = %s"
            params.append(project_id)
            
        if date_filter:
            query += " AND m.meeting_date = %s"
            params.append(date_filter)

        if meeting_category:
            query += " AND m.meeting_category = %s"
            params.append(meeting_category)
            
        query += " ORDER BY m.meeting_date DESC, m.start_time DESC"
        
        results = await self.db.execute_query(query, tuple(params), fetch_all=True, schema=tenant_name) or []
        
        # Ensure attendees is a list
        for row in results:
            if isinstance(row.get('attendees'), str):
                try:
                    row['attendees'] = json.loads(row['attendees'])
                except:
                    row['attendees'] = []
        
        return results

    async def update_meeting(self, tenant_name: str, meeting_id: str, updates: MeetingUpdate) -> Optional[Dict[str, Any]]:
        # Check if meeting exists
        existing = await self.get_meeting_by_meeting_id(tenant_name, meeting_id)
        if not existing:
            return None
            
        update_fields = []
        params = []
        
        data = updates.dict(exclude_unset=True)
        if not data:
            return existing

        # Map model field names to DB column names
        field_mapping = {
            'date': 'meeting_date',
            'category': 'meeting_category',
        }

        transcript_to_update = data.pop('meeting_transcript', None)
        
        for field, value in data.items():
            db_field = field_mapping.get(field, field)
            update_fields.append(f"`{db_field}` = %s")
            # Serialize list/dict to JSON string for the DB
            if field == 'attendees' and value is not None:
                params.append(json.dumps(value))
            else:
                params.append(value)
            
        params.append(meeting_id)
        
        if update_fields:
            query = f"UPDATE meetings SET {', '.join(update_fields)}, updated_at = NOW() WHERE meeting_id = %s"
            await self.db.execute_query(query, tuple(params), commit=True, schema=tenant_name)
        
        # Handle transcript update
        if transcript_to_update is not None:
            # Check if transcript exists for this meeting
            check_transcript = "SELECT id FROM transcripts WHERE meeting_id = %s"
            transcript_res = await self.db.execute_query(check_transcript, (meeting_id,), fetch_one=True, schema=tenant_name)
            
            if transcript_res:
                update_transcript = "UPDATE transcripts SET transcript_content = %s, updated_at = NOW() WHERE meeting_id = %s"
                await self.db.execute_query(update_transcript, (transcript_to_update, meeting_id), commit=True, schema=tenant_name)
            else:
                # Create a new transcript if it doesn't exist
                insert_transcript = """
                    INSERT INTO transcripts (meeting_id, title, category, transcript_content, transcript_date, project_id, tenant_schema)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                await self.db.execute_query(
                    insert_transcript,
                    (meeting_id, existing['title'], existing['meeting_category'], transcript_to_update, existing['meeting_date'], existing['project_id'], tenant_name),
                    commit=True,
                    schema=tenant_name
                )
        
        return await self.get_meeting_by_meeting_id(tenant_name, meeting_id)

    async def delete_meeting(self, tenant_name: str, meeting_id: str) -> bool:
        existing = await self.get_meeting_by_meeting_id(tenant_name, meeting_id)
        if not existing:
            return False
            
        query = "DELETE FROM meetings WHERE meeting_id = %s"
        await self.db.execute_query(query, (meeting_id,), commit=True, schema=tenant_name)
        return True

    async def get_project_users(self, tenant_name: str, project_id: int) -> List[Dict[str, Any]]:
        """
        Get users assigned to a project.
        Uses the {tenant_name} table in the central database.
        """
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
                    
                    if isinstance(projects, list) and project_id in projects:
                        user_clean = {k: v for k, v in user.items() if k not in ['projects']}
                        project_users.append(user_clean)
                except Exception as e:
                    logger.warning(f"Error parsing projects for user {user.get('user_id')}: {e}")
                    continue
                    
        return project_users
