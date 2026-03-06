"""
Transcript Service

Service layer for transcript management operations.
"""

from app.db.database import Database
from app.schemas.transcript import (
    TranscriptCreate, TranscriptUpdate, TranscriptResponse,
    TranscriptListItem, TranscriptListResponse, TranscriptFilterParams
)
from app.core.logger import logger
from typing import List, Optional, Dict, Any
from datetime import date
import json


class TranscriptService:
    """Service for transcript operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_transcript(
        self,
        tenant_name: str,
        title: str,
        category: str,
        transcript_content: str,
        transcript_date: date,
        tags: List[str] = None,
        file_name: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        project_id: Optional[int] = 0,
        sprint_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new transcript record and update meeting attendance
        """
        try:
            import json
            import re
            
            # 1. Automatic categorisation if title contains common meeting keywords
            if category == 'other' or not category:
                lower_title = title.lower()
                if 'standup' in lower_title or 'daily' in lower_title:
                    category = 'daily_standup'
                elif 'retrospective' in lower_title or 'retro' in lower_title:
                    category = 'retrospective'
                elif 'planning' in lower_title:
                    category = 'sprint_planning'
                elif 'sprint' in lower_title:
                    category = 'sprint_meeting'

            # 2. Extract participants from transcript content
            speakers = re.findall(r'^([^:\n]+):', transcript_content, re.MULTILINE)
            participants_list = sorted(list(set(s.strip() for s in speakers)))
            
            # 3. Store Transcript
            query = """
                INSERT INTO transcripts (
                    title, category, transcript_content, transcript_date, 
                    tags, file_name, uploaded_by, tenant_schema, project_id, sprint_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            tags_json = json.dumps(tags) if tags else None
            
            await self.db.execute_query(
                query,
                (title, category, transcript_content, transcript_date, tags_json, file_name, uploaded_by, tenant_name, project_id, sprint_id),
                commit=True,
                schema=tenant_schema
            )
            
            # 4. Update Meeting Attendance
            # Try to find a matching meeting in MySQL for this project/sprint/date
            if participants_list:
                find_meeting_sql = """
                    SELECT meeting_id FROM meetings 
                    WHERE project_id = %s AND (sprint_id = %s OR %s IS NULL) AND meeting_date = %s
                    LIMIT 1
                """
                meeting_res = await self.db.execute_query(
                    find_meeting_sql, 
                    (project_id, sprint_id, sprint_id, transcript_date),
                    schema=tenant_name,
                    fetch_one=True
                )
                
                if meeting_res:
                    update_attendees_sql = "UPDATE meetings SET attendees = %s WHERE meeting_id = %s"
                    await self.db.execute_query(
                        update_attendees_sql,
                        (json.dumps(participants_list), meeting_res['meeting_id']),
                        schema=tenant_name,
                        commit=True
                    )
                    logger.info(f"Updated attendance for meeting {meeting_res['meeting_id']} based on transcript '{title}'")

            # Fetch created
            fetch_query = "SELECT * FROM transcripts WHERE tenant_schema = %s ORDER BY id DESC LIMIT 1"
            return await self.db.execute_query(fetch_query, (tenant_name,), fetch_one=True, schema=tenant_name)
            
        except Exception as e:
            logger.error(f"Error fetching transcript: {e}")
            raise
    
    async def list_transcripts(
        self,
        tenant_schema: str,
        filters: TranscriptFilterParams
    ) -> TranscriptListResponse:
        """List transcripts with filters"""
        try:
            # Build WHERE clause
            where_clauses = []
            params = []
            
            if filters.category:
                where_clauses.append("category = %s")
                params.append(filters.category.value)
            
            if filters.date_from:
                where_clauses.append("transcript_date >= %s")
                params.append(filters.date_from)
            
            if filters.date_to:
                where_clauses.append("transcript_date <= %s")
                params.append(filters.date_to)
            
            if filters.search:
                where_clauses.append("(title LIKE %s OR transcript_content LIKE %s)")
                search_term = f"%{filters.search}%"
                params.extend([search_term, search_term])
            
            if filters.report_generated:
                where_clauses.append("report_generated = %s")
                params.append(filters.report_generated.value)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Count total
            count_query = f"""
                SELECT COUNT(*) as total
                FROM {tenant_schema}.transcripts
                {where_sql}
            """
            count_result = await self.db.execute_query(count_query, tuple(params), fetch_one=True)
            total = count_result['total'] if count_result else 0
            
            # Fetch
            query = f"""
                SELECT t.id, t.title, t.category, t.transcript_date, t.tags, t.file_name, 
                       t.created_at, t.project_id, t.sprint_id, s.sprint_name
                FROM transcripts t
                LEFT JOIN sprint s ON t.sprint_id = s.sprint_id
                WHERE {where_str} 
                ORDER BY t.transcript_date DESC, t.created_at DESC 
                LIMIT %s OFFSET %s
            """
            params.extend([filters.page_size, offset])
            
            results = await self.db.execute_query(list_query, tuple(params), fetch_all=True)
            
            transcripts = []
            for row in results or []:
                tags = json.loads(row['tags']) if row.get('tags') else None
                transcripts.append(TranscriptListItem(
                    id=row['id'],
                    title=row['title'],
                    category=row['category'],
                    transcript_date=row['transcript_date'],
                    tags=tags,
                    file_name=row.get('file_name'),
                    project_id=row.get('project_id'),
                    report_generated=row.get('report_generated', 'pending'),
                    created_at=row['created_at']
                ))
            
            return TranscriptListResponse(
                transcripts=transcripts,
                total=total,
                page=filters.page,
                page_size=filters.page_size
            )
        
        except Exception as e:
            logger.error(f"Error listing transcripts: {e}")
            raise
    
    async def update_transcript(
        self,
        transcript_id: int,
        transcript_data: TranscriptUpdate,
        tenant_schema: str
    ) -> TranscriptResponse:
        """Update a transcript"""
        try:
            # Build UPDATE clause
            update_fields = []
            params = []
            
            if transcript_data.title is not None:
                update_fields.append("title = %s")
                params.append(transcript_data.title)
            
            if transcript_data.category is not None:
                update_fields.append("category = %s")
                params.append(transcript_data.category.value)
            
            if transcript_data.transcript_content is not None:
                update_fields.append("transcript_content = %s")
                params.append(transcript_data.transcript_content)
            
            if transcript_data.transcript_date is not None:
                update_fields.append("transcript_date = %s")
                params.append(transcript_data.transcript_date)
            
            if transcript_data.tags is not None:
                update_fields.append("tags = %s")
                params.append(json.dumps(transcript_data.tags))
            
            if not update_fields:
                raise ValueError("No fields to update")
            
            params.append(transcript_id)
            
            query = f"""
                UPDATE {tenant_schema}.transcripts
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            await self.db.execute_query(query, tuple(params), commit=True)
            
            return await self.get_transcript(transcript_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error updating transcript: {e}")
            raise
    
    async def delete_transcript(
        self,
        transcript_id: int,
        tenant_schema: str
    ) -> bool:
        """Delete a transcript"""
        try:
            query = f"""
                DELETE FROM {tenant_schema}.transcripts
                WHERE id = %s
            """
            
            await self.db.execute_query(query, (transcript_id,), commit=True)
            
            logger.info(f"Transcript {transcript_id} deleted successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting transcript: {e}")
            raise

    async def update_report_generated_status(
        self,
        transcript_id: int,
        tenant_schema: str,
        status: str = 'done'
    ) -> bool:
        """Update the report_generated status for a transcript"""
        try:
            query = f"""
                UPDATE {tenant_schema}.transcripts
                SET report_generated = %s
                WHERE id = %s
            """
            
            await self.db.execute_query(query, (status, transcript_id), commit=True)
            
            logger.info(f"Transcript {transcript_id} report_generated status updated to '{status}'")
            return True
        
        except Exception as e:
            logger.error(f"Error updating report_generated status: {e}")
            raise
