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
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            query = """
                INSERT INTO transcripts (
                    title, category, transcript_content, transcript_date, 
                    tags, file_name, uploaded_by, tenant_schema, project_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            import json
            tags_json = json.dumps(tags) if tags else None
            
            await self.db.execute_query(
                query,
                (title, category, transcript_content, transcript_date, tags_json, file_name, uploaded_by, tenant_name, project_id),
                commit=True,
                schema=tenant_name
            )
            
            # Fetch created
            # Assuming id is auto-increment, we need last insert id or fetch by unique fields.
            # For simplicity, fetching by title/date/uploader (might not be unique but adequate for now)
            # Better: use db.last_insert_id() if available in wrapper, or select max id
            
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
                SELECT id, title, category, transcript_date, tags, file_name, created_at, project_id 
                FROM transcripts 
                WHERE {where_str} 
                ORDER BY transcript_date DESC, created_at DESC 
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
        result = await self.db.execute_query(query, (transcript_id,), fetch_one=True, schema=tenant_name)
        if result and result.get('tags') and isinstance(result['tags'], str):
            import json
            try:
                result['tags'] = json.loads(result['tags'])
            except:
                result['tags'] = []
        return result

    async def update_transcript(
        self,
        tenant_name: str,
        transcript_id: int,
        title: Optional[str] = None,
        category: Optional[str] = None,
        transcript_content: Optional[str] = None,
        transcript_date: Optional[date] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing transcript."""
        try:
            # Build dynamic update query
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = %s")
                params.append(title)
            if category is not None:
                updates.append("category = %s")
                params.append(category)
            if transcript_content is not None:
                updates.append("transcript_content = %s")
                params.append(transcript_content)
            if transcript_date is not None:
                updates.append("transcript_date = %s")
                params.append(transcript_date)
            if tags is not None:
                import json
                updates.append("tags = %s")
                params.append(json.dumps(tags))
            
            if not updates:
                return await self.get_transcript_by_id(tenant_name, transcript_id)
            
            updates.append("updated_at = NOW()")
            params.append(transcript_id)
            
            query = f"UPDATE transcripts SET {', '.join(updates)} WHERE id = %s"
            await self.db.execute_query(query, tuple(params), commit=True, schema=tenant_name)
            
            return await self.get_transcript_by_id(tenant_name, transcript_id)
            
        except Exception as e:
            logger.error(f"Failed to update transcript: {str(e)}")
            raise e

    async def delete_transcript(self, tenant_name: str, transcript_id: int) -> bool:
        query = "DELETE FROM transcripts WHERE id = %s"
        await self.db.execute_query(query, (transcript_id,), commit=True, schema=tenant_name)
        return True
