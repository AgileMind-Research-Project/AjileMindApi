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
from typing import List, Optional
from datetime import date
import json


class TranscriptService:
    """Service for transcript operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_transcript(
        self,
        transcript_data: TranscriptCreate,
        tenant_schema: str,
        uploaded_by: str
    ) -> TranscriptResponse:
        """Create a new transcript"""
        try:
            logger.info(f"Creating transcript in schema: {tenant_schema}, uploaded by: {uploaded_by}")
            
            # Validate schema exists
            check_query = "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s"
            schema_check = await self.db.execute_query(check_query, (tenant_schema,), fetch_one=True)
            
            if not schema_check:
                raise ValueError(f"Schema '{tenant_schema}' does not exist. Available schemas should include: sas, saas, visionexdigital")
            
            # Convert tags to JSON string
            tags_json = json.dumps(transcript_data.tags) if transcript_data.tags else None
            
            query = f"""
                INSERT INTO {tenant_schema}.transcripts 
                (title, category, transcript_content, transcript_date, tags, file_name, uploaded_by, tenant_schema, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            result = await self.db.execute_query(
                query,
                (
                    transcript_data.title,
                    transcript_data.category.value,
                    transcript_data.transcript_content,
                    transcript_data.transcript_date,
                    tags_json,
                    transcript_data.file_name,
                    uploaded_by,
                    tenant_schema,
                    transcript_data.project_id
                ),
                commit=True,
                schema=tenant_schema
            )
            
            # Get the inserted transcript ID from the cursor
            transcript_id = result.lastrowid
            
            if not transcript_id:
                raise Exception("Failed to get transcript ID after creation")
            
            logger.info(f"Transcript {transcript_id} created, verifying in {tenant_schema}.transcripts")
            
            # Verify record exists
            verify_query = f"SELECT COUNT(*) as cnt FROM {tenant_schema}.transcripts WHERE id = %s"
            verify_result = await self.db.execute_query(verify_query, (transcript_id,), fetch_one=True, schema=tenant_schema)
            
            if not verify_result or verify_result['cnt'] == 0:
                raise ValueError(f"Transcript {transcript_id} inserted but not found in {tenant_schema}.transcripts. This may indicate a schema mismatch.")
            
            logger.info(f"Transcript {transcript_id} verified, fetching full details")
            
            # Fetch the created transcript with explicit schema
            return await self.get_transcript(transcript_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error creating transcript: {e}")
            raise
    
    async def get_transcript(
        self,
        transcript_id: int,
        tenant_schema: str
    ) -> TranscriptResponse:
        """Get a transcript by ID"""
        try:
            query = f"""
                SELECT id, title, category, transcript_content, transcript_date, 
                       tags, file_name, project_id, created_at, updated_at
                FROM {tenant_schema}.transcripts
                WHERE id = %s
            """
            
            logger.info(f"Fetching transcript {transcript_id} from {tenant_schema}.transcripts")
            result = await self.db.execute_query(
                query, 
                (transcript_id,), 
                fetch_one=True,
                schema=tenant_schema
            )
            
            if not result:
                raise ValueError(f"Transcript with ID {transcript_id} not found in schema {tenant_schema}")
            
            # Parse tags JSON
            tags = json.loads(result['tags']) if result.get('tags') else None
            
            return TranscriptResponse(
                id=result['id'],
                title=result['title'],
                category=result['category'],
                transcript_content=result['transcript_content'],
                transcript_date=result['transcript_date'],
                tags=tags,
                file_name=result.get('file_name'),
                project_id=result.get('project_id'),
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        
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
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Count total
            count_query = f"""
                SELECT COUNT(*) as total
                FROM {tenant_schema}.transcripts
                {where_sql}
            """
            count_result = await self.db.execute_query(count_query, tuple(params), fetch_one=True)
            total = count_result['total'] if count_result else 0
            
            # Fetch transcripts
            offset = (filters.page - 1) * filters.page_size
            list_query = f"""
                SELECT id, title, category, transcript_content, transcript_date, tags, file_name, project_id, created_at
                FROM {tenant_schema}.transcripts
                {where_sql}
                ORDER BY transcript_date DESC, created_at DESC
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
                    transcript_content=row['transcript_content'],
                    transcript_date=row['transcript_date'],
                    tags=tags,
                    file_name=row.get('file_name'),
                    project_id=row.get('project_id'),
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
