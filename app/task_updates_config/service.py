"""
Task Updates Service Layer - Business Logic
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db.database import Database
from app.core.logger import logger
from app.task_updates_config.models import (
    TaskUpdateCreate, TaskUpdateResponse,
    ApprovalStatus, JiraSyncStatus
)
from app.ai.task_extractor.extractor import get_task_extractor
from app.meeting_config.service import MeetingService


class TaskUpdatesService:
    """Service for managing task updates"""
    
    def __init__(self, db: Database):
        self.db = db
        self.meeting_service = MeetingService(db)
        self.extractor = get_task_extractor()
    
    async def extract_from_meeting(
        self, 
        tenant_name: str, 
        meeting_id: str,
        force_reextract: bool = False
    ) -> Dict[str, Any]:
        """
        Extract task updates from a meeting transcript using AI
        
        Args:
            tenant_name: Tenant schema name
            meeting_id: Meeting ID
            force_reextract: Re-extract even if already processed
            
        Returns:
            Extraction results dict
        """
        try:
            # Get meeting
            meeting = await self.meeting_service.get_meeting_by_meeting_id(tenant_name, meeting_id)
            if not meeting:
                raise ValueError(f"Meeting {meeting_id} not found")
            
            transcript = meeting.get('meeting_transcript')
            if not transcript:
                raise ValueError("Meeting has no transcript")
            
            project_id = meeting.get('project_id')
            if not project_id:
                raise ValueError("Meeting has no project_id")
            
            # Check if already extracted
            if not force_reextract:
                existing = await self.list_by_meeting(tenant_name, meeting_id)
                if existing:
                    logger.info(f"Meeting {meeting_id} already has {len(existing)} extractions")
                    return {
                        "meeting_id": meeting_id,
                        "total_extracted": len(existing),
                        "already_processed": True
                    }
            
            # If forcing re-extraction, delete existing ones first
            if force_reextract:
                await self.delete_for_meeting(tenant_name, meeting_id)
            
            # Extract using AI
            extractions, processing_time = self.extractor.extract_from_transcript(transcript, meeting_id)
            
            # Save extractions to database
            saved_count = 0
            for extraction in extractions:
                update_data = TaskUpdateCreate(
                    meeting_id=meeting_id,
                    project_id=project_id,
                    ticket_id=extraction.ticket_id,
                    detected_status=extraction.detected_status,
                    blocker_description=extraction.blocker_description,
                    ai_confidence_score=extraction.ai_confidence_score,
                    ai_reasoning=extraction.ai_reasoning,
                    extracted_context=extraction.extracted_context
                )
                
                await self.create_update(tenant_name, update_data)
                saved_count += 1
            
            logger.info(f"Saved {saved_count} task updates from meeting {meeting_id}")
            
            return {
                "meeting_id": meeting_id,
                "total_extracted": saved_count,
                "processing_time_ms": processing_time,
                "already_processed": False
            }
        
        except Exception as e:
            logger.error(f"Error extracting from meeting: {e}")
            raise
    
    async def create_update(
        self, 
        tenant_name: str, 
        update_data: TaskUpdateCreate
    ) -> Dict[str, Any]:
        """Create a task update"""
        try:
            query = """
                INSERT INTO task_updates (
                    meeting_id, project_id, task_id, ticket_id,
                    detected_status, blocker_description,
                    ai_confidence_score, ai_reasoning, extracted_context,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            await self.db.execute_query(
                query,
                (
                    update_data.meeting_id,
                    update_data.project_id,
                    update_data.task_id,
                    update_data.ticket_id,
                    update_data.detected_status.value,
                    update_data.blocker_description,
                    update_data.ai_confidence_score,
                    update_data.ai_reasoning,
                    update_data.extracted_context
                ),
                commit=True,
                schema=tenant_name
            )
            
            # Get created record
            fetch_query = """
                SELECT * FROM task_updates 
                WHERE meeting_id = %s AND ticket_id = %s 
                ORDER BY id DESC LIMIT 1
            """
            
            return await self.db.execute_query(
                fetch_query, 
                (update_data.meeting_id, update_data.ticket_id),
                fetch_one=True,
                schema=tenant_name
            )
        
        except Exception as e:
            logger.error(f"Error creating task update: {e}")
            raise
    
    async def list_by_meeting(
        self, 
        tenant_name: str, 
        meeting_id: str
    ) -> List[Dict[str, Any]]:
        """List task updates for a meeting"""
        query = "SELECT * FROM task_updates WHERE meeting_id = %s ORDER BY created_at DESC"
        return await self.db.execute_query(query, (meeting_id,), fetch_all=True, schema=tenant_name) or []
    
    async def list_pending(
        self, 
        tenant_name: str,
        project_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List pending task updates"""
        return await self.list_updates(tenant_name, project_id, 'PENDING')

    async def list_updates(
        self,
        tenant_name: str,
        project_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List task updates with optional status filter"""
        query = "SELECT * FROM task_updates WHERE 1=1"
        params = []

        if status:
            query += " AND approval_status = %s"
            params.append(status)
        
        if project_id:
            query += " AND project_id = %s"
            params.append(project_id)
        
        query += " ORDER BY created_at DESC"
        
        return await self.db.execute_query(
            query, 
            tuple(params) if params else None,
            fetch_all=True, 
            schema=tenant_name
        ) or []
    
    async def approve_update(
        self, 
        tenant_name: str,
        update_id: int,
        reviewed_by: str,
        remark: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Approve a task update"""
        query = """
            UPDATE task_updates 
            SET approval_status = 'APPROVED',
                reviewed_by = %s,
                review_timestamp = NOW(),
                reviewer_remark = %s
            WHERE id = %s
        """
        
        await self.db.execute_query(
            query, 
            (reviewed_by, remark, update_id),
            commit=True, 
            schema=tenant_name
        )
        
        # Helper to update backlog
        await self._sync_to_backlog(tenant_name, update_id)
        
        return await self.get_by_id(tenant_name, update_id)

    async def _sync_to_backlog(self, tenant_name: str, update_id: int):
        """Sync approved task status to project_backlog"""
        try:
            # Get the update details
            task_update = await self.get_by_id(tenant_name, update_id)
            if not task_update or not task_update.get('ticket_id'):
                return

            ticket_id = task_update['ticket_id']
            detected_status = task_update['detected_status'] # e.g. DONE, IN_PROGRESS
            
            # Map to backlog status
            status_map = {
                'TODO': 'todo',
                'IN_PROGRESS': 'in_progress',
                'DONE': 'done'
            }
            
            new_status = status_map.get(detected_status)
            
            if new_status:
                logger.info(f"Syncing task update {update_id} to backlog item {ticket_id}: {new_status}")
                query = "UPDATE project_backlog SET status = %s, updated_at = NOW() WHERE id = %s"
                await self.db.execute_query(
                    query,
                    (new_status, ticket_id),
                    commit=True,
                    schema=tenant_name
                )
        except Exception as e:
            logger.error(f"Failed to sync backlog for update {update_id}: {e}")
            # Don't fail the approval if sync fails

    
    async def reject_update(
        self, 
        tenant_name: str,
        update_id: int,
        reviewed_by: str,
        remark: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Reject a task update"""
        query = """
            UPDATE task_updates 
            SET approval_status = 'REJECTED',
                reviewed_by = %s,
                review_timestamp = NOW(),
                reviewer_remark = %s
            WHERE id = %s
        """
        
        await self.db.execute_query(
            query, 
            (reviewed_by, remark, update_id),
            commit=True, 
            schema=tenant_name
        )
        
        return await self.get_by_id(tenant_name, update_id)
    
    async def get_by_id(
        self, 
        tenant_name: str, 
        update_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get task update by ID"""
        query = "SELECT * FROM task_updates WHERE id = %s"
        return await self.db.execute_query(query, (update_id,), fetch_one=True, schema=tenant_name)

    async def delete_for_meeting(self, tenant_name: str, meeting_id: str):
        """Delete all task updates for a meeting"""
        query = "DELETE FROM task_updates WHERE meeting_id = %s"
        await self.db.execute_query(query, (meeting_id,), commit=True, schema=tenant_name)
