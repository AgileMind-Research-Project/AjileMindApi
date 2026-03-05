"""
Transcript Service

Manages transcript storage, retrieval, and filtering.
"""

from typing import List, Dict, Any, Optional
from datetime import date
from app.db.database import Database
from app.core.logger import logger

class TranscriptService:
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
                schema=tenant_name
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
            logger.error(f"Failed to create transcript: {str(e)}")
            raise e

    async def get_transcripts(
        self,
        tenant_name: str,
        category: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None,
        project_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        try:
            offset = (page - 1) * page_size
            params = []
            where_clauses = ["1=1"] # tenant_schema check? Schema switching handles mostly.
            
            # If using single DB with schema column:
            # where_clauses.append("tenant_schema = %s") 
            # params.append(tenant_name)
            # But `execute_query` switches schema via `USE`, so we verify if `transcripts` is inside the tenant DB. 
            # The schema SQL earlier implies it IS inside the tenant DB. So no need for tenant_schema in WHERE if we USE schema.
            # However, the CREATE TABLE showed `tenant_schema` column, so let's populate it but rely on USE schema for isolation if that's the pattern.
            # Looking at `tenant_database_schema.sql`, it seems tables are per tenant.
            
            if category:
                where_clauses.append("category = %s")
                params.append(category)
            
            if project_id:
                where_clauses.append("project_id = %s")
                params.append(project_id)
                
            if date_from:
                where_clauses.append("transcript_date >= %s")
                params.append(date_from)
                
            if date_to:
                where_clauses.append("transcript_date <= %s")
                params.append(date_to)
                
            if search:
                where_clauses.append("(title LIKE %s OR transcript_content LIKE %s)")
                search_term = f"%{search}%"
                params.extend([search_term, search_term])

            where_str = " AND ".join(where_clauses)
            
            # Count
            count_query = f"SELECT COUNT(*) as total FROM transcripts WHERE {where_str}"
            count_res = await self.db.execute_query(count_query, tuple(params), fetch_one=True, schema=tenant_name)
            total = count_res['total'] if count_res else 0
            
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
            params.extend([page_size, offset])
            
            results = await self.db.execute_query(query, tuple(params), fetch_all=True, schema=tenant_name)
            
            # Parse tags
            import json
            for r in results:
                if r.get('tags') and isinstance(r['tags'], str):
                    try:
                        r['tags'] = json.loads(r['tags'])
                    except:
                        r['tags'] = []
            
            return {
                "transcripts": results,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"Failed to list transcripts: {str(e)}")
            raise e

    async def get_transcript_by_id(self, tenant_name: str, transcript_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM transcripts WHERE id = %s"
        return await self.db.execute_query(query, (transcript_id,), fetch_one=True, schema=tenant_name)

    async def delete_transcript(self, tenant_name: str, transcript_id: int) -> bool:
        query = "DELETE FROM transcripts WHERE id = %s"
        await self.db.execute_query(query, (transcript_id,), commit=True, schema=tenant_name)
        return True
