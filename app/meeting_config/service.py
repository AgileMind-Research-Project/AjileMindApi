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
                    meeting_id, project_id, title, description,
                    date, start_time, end_time, status, category,
                    attendees, created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            await self.db.execute_query(
                query,
                (
                    meeting_id,
                    meeting_data.project_id,
                    meeting_data.title,
                    meeting_data.description,
                    meeting_data.date,
                    meeting_data.start_time,
                    meeting_data.end_time,
                    MeetingStatus.SCHEDULED.value,
                    meeting_data.category,
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
        return await self.db.execute_query(query, (meeting_id,), fetch_one=True, schema=tenant_name)

    async def get_meeting_by_id(self, tenant_name: str, id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM meetings WHERE id = %s"
        return await self.db.execute_query(query, (id,), fetch_one=True, schema=tenant_name)

    async def list_meetings(self, tenant_name: str, project_id: Optional[int] = None, date_filter: Optional[date] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM meetings WHERE 1=1"
        params = []
        
        if project_id:
            query += " AND project_id = %s"
            params.append(project_id)
            
        if date_filter:
            query += " AND date = %s"
            params.append(date_filter)
            
        query += " ORDER BY date, start_time"
        
        return await self.db.execute_query(query, tuple(params), fetch_all=True, schema=tenant_name) or []

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

        for field, value in data.items():
            update_fields.append(f"{field} = %s")
            params.append(value)
            
        params.append(meeting_id)
        
        query = f"UPDATE meetings SET {', '.join(update_fields)}, updated_at = NOW() WHERE meeting_id = %"
        # Fix: The above line has a typo '%'. It should be %s. 
        # Correcting logic below
        
        query = f"UPDATE meetings SET {', '.join(update_fields)}, updated_at = NOW() WHERE meeting_id = %s"
        
        await self.db.execute_query(query, tuple(params), commit=True, schema=tenant_name)
        
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
        # Note: We query the central DB, so we do NOT pass schema=tenant_name, but we query table `{tenant_name}`
        # Use fully qualified name to avoid issues if connection is in another schema
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
                        projects = projects_json # Already list or dict
                    
                    if isinstance(projects, list) and project_id in projects:
                        # Remove sensitive info
                        user_clean = {k: v for k, v in user.items() if k not in ['projects']}
                        project_users.append(user_clean)
                except Exception as e:
                    logger.warning(f"Error parsing projects for user {user.get('user_id')}: {e}")
                    continue
                    
        return project_users

