"""
Meeting Service - Redis-Based Meeting Management

Handles all meeting-related operations:
- Meeting creation and lifecycle management
- Join request handling
- Participant management
- Transcript storage
- Tenant isolation
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4
import json

from app.core.redis_chat_client import get_redis_chat
from app.services.redis_chat_service import get_redis_chat_service
from app.db.database import db

logger = logging.getLogger(__name__)


class MeetingService:
    """Service for managing meetings in Redis"""
    
    def __init__(self):
        """Initialize meeting service"""
        self.redis = get_redis_chat()
    
    # ==================== Helper Methods ====================
    
    def _meeting_key(self, meeting_id: str) -> str:
        """Generate meeting hash key"""
        return f"meeting:{meeting_id}"
    
    def _meeting_participants_key(self, meeting_id: str) -> str:
        """Generate participants set key"""
        return f"meeting:{meeting_id}:participants"
    
    def _meeting_join_requests_key(self, meeting_id: str) -> str:
        """Generate join requests list key"""
        return f"meeting:{meeting_id}:join_requests"
    
    def _meeting_transcript_key(self, meeting_id: str) -> str:
        """Generate transcript key"""
        return f"meeting:{meeting_id}:transcript"
    
    def _channel_meetings_key(self, channel_id: str) -> str:
        """Generate channel meetings set key"""
        return f"channel:{channel_id}:meetings"
    
    def _tenant_meetings_key(self, tenant_name: str) -> str:
        """Generate tenant active meetings set key"""
        return f"tenant:{tenant_name}:active_meetings"
    
    def _join_request_key(self, meeting_id: str, request_id: str) -> str:
        """Generate join request hash key"""
        return f"meeting:{meeting_id}:request:{request_id}"
    
    # ==================== Meeting CRUD ====================
    
    def create_meeting(
        self,
        channel_id: str,
        tenant_name: str,
        created_by_user_id: str,
        created_by_username: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new instant meeting
        
        Args:
            channel_id: Channel ID
            tenant_name: Tenant name
            created_by_user_id: Creator user ID
            created_by_username: Creator username
            title: Meeting title (optional)
            description: Meeting description (optional)
        
        Returns:
            Meeting data or None on failure
        """
        try:
            meeting_id = f"meet_{uuid4().hex[:12]}"
            now = datetime.utcnow().isoformat()
            
            meeting_data = {
                'id': meeting_id,
                'channel_id': channel_id,
                'title': title or f"Meeting in {channel_id}",
                'description': description or '',
                'status': 'scheduled',
                'created_by_user_id': created_by_user_id,
                'created_by_username': created_by_username,
                'created_at': now,
                'started_at': None,
                'ended_at': None,
                'participant_count': 0,
                'tenant_name': tenant_name
            }
            
            # Store meeting
            meeting_key = self._meeting_key(meeting_id)
            if not self.redis.set_hash(meeting_key, meeting_data):
                return None
            
            # Add to channel's meetings
            channel_meetings_key = self._channel_meetings_key(channel_id)
            self.redis.add_to_set(channel_meetings_key, meeting_id)
            
            # Add to tenant's active meetings
            tenant_meetings_key = self._tenant_meetings_key(tenant_name)
            self.redis.add_to_set(tenant_meetings_key, meeting_id)
            
            # Auto-add creator as first participant
            self.add_participant(meeting_id, created_by_user_id, created_by_username)
            
            logger.info(f"Created meeting {meeting_id} in channel {channel_id}")
            return self.get_meeting(meeting_id)
            
        except Exception as e:
            logger.error(f"Failed to create meeting: {e}")
            return None
    
    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Get meeting details"""
        try:
            meeting_key = self._meeting_key(meeting_id)
            meeting = self.redis.get_hash(meeting_key)
            
            if not meeting:
                return None
            
            # Get participant count
            participants_key = self._meeting_participants_key(meeting_id)
            participant_count = self.redis.get_set_size(participants_key)
            meeting['participant_count'] = participant_count
            
            # Get participant list
            participants = self.redis.get_set_members(participants_key)
            meeting['participants'] = participants
            
            return meeting
            
        except Exception as e:
            logger.error(f"Failed to get meeting {meeting_id}: {e}")
            return None
    
    def start_meeting(self, meeting_id: str) -> bool:
        """
        Start a meeting (change status to live)
        
        Args:
            meeting_id: Meeting ID
        
        Returns:
            True if successful
        """
        try:
            meeting_key = self._meeting_key(meeting_id)
            now = datetime.utcnow().isoformat()
            
            self.redis.update_hash(meeting_key, 'status', 'live')
            self.redis.update_hash(meeting_key, 'started_at', now)
            
            logger.info(f"Started meeting {meeting_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start meeting {meeting_id}: {e}")
            return False
    
    def end_meeting(self, meeting_id: str, tenant_name: str, user_id: Optional[str] = None, username: Optional[str] = None) -> bool:
        """
        End a meeting
        
        Args:
            meeting_id: Meeting ID
            tenant_name: Tenant name
            user_id: User ID ending the meeting
            username: Username ending the meeting
        
        Returns:
            True if successful
        """
        try:
            meeting_key = self._meeting_key(meeting_id)
            now = datetime.utcnow().isoformat()
            
            self.redis.update_hash(meeting_key, 'status', 'ended')
            self.redis.update_hash(meeting_key, 'ended_at', now)
            
            # Remove from tenant's active meetings
            tenant_meetings_key = self._tenant_meetings_key(tenant_name)
            self.redis.remove_from_set(tenant_meetings_key, meeting_id)
            
            logger.info(f"Ended meeting {meeting_id}")
            # Post to channel chat
            if user_id and username:
                try:
                    meeting = self.get_meeting(meeting_id)
                    chat_service = get_redis_chat_service()
                    channel_id = meeting.get('channel_id')
                    
                    if channel_id:
                        chat_message = f"🛑 **Meeting Ended**"
                        
                        chat_service.send_message(
                            channel_id=channel_id,
                            user_id=user_id,
                            username=username,
                            content=chat_message,
                            message_type="system",
                            metadata={
                                "type": "meeting_ended",
                                "meeting_id": meeting_id,
                                "meeting_title": meeting.get('title')
                            }
                        )
                        logger.info(f"Posted meeting ended message to channel {channel_id}")
                except Exception as chat_error:
                    logger.error(f"Failed to post end meeting message to chat: {chat_error}")

            return True
            
        except Exception as e:
            logger.error(f"Failed to end meeting {meeting_id}: {e}")
            return False
    
    def get_channel_meetings(
        self,
        channel_id: str,
        include_ended: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all meetings for a channel
        
        Args:
            channel_id: Channel ID
            include_ended: Include ended meetings
        
        Returns:
            List of meetings
        """
        try:
            channel_meetings_key = self._channel_meetings_key(channel_id)
            meeting_ids = self.redis.get_set_members(channel_meetings_key)
            
            meetings = []
            for meeting_id in meeting_ids:
                meeting = self.get_meeting(meeting_id)
                if meeting:
                    if include_ended or meeting.get('status') != 'ended':
                        meetings.append(meeting)
            
            # Sort by created_at (newest first)
            meetings.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return meetings
            
        except Exception as e:
            logger.error(f"Failed to get channel meetings: {e}")
            return []
    
    # ==================== Participant Management ====================
    
    def add_participant(
        self,
        meeting_id: str,
        user_id: str,
        username: str
    ) -> bool:
        """
        Add participant to meeting
        
        Args:
            meeting_id: Meeting ID
            user_id: User ID
            username: Username
        
        Returns:
            True if successful
        """
        try:
            participants_key = self._meeting_participants_key(meeting_id)
            
            # Store participant data as JSON
            participant_data = {
                'user_id': user_id,
                'username': username,
                'joined_at': datetime.utcnow().isoformat()
            }
            
            # Add to set (using user_id as member)
            self.redis.add_to_set(participants_key, user_id)
            
            # Store participant details
            participant_key = f"meeting:{meeting_id}:participant:{user_id}"
            self.redis.set_hash(participant_key, participant_data)
            
            logger.info(f"Added participant {user_id} to meeting {meeting_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add participant: {e}")
            return False
    
    def remove_participant(
        self,
        meeting_id: str,
        user_id: str
    ) -> bool:
        """
        Remove participant from meeting
        
        Args:
            meeting_id: Meeting ID
            user_id: User ID
        
        Returns:
            True if successful
        """
        try:
            participants_key = self._meeting_participants_key(meeting_id)
            self.redis.remove_from_set(participants_key, user_id)
            
            # Remove participant details
            participant_key = f"meeting:{meeting_id}:participant:{user_id}"
            self.redis.delete_key(participant_key)
            
            logger.info(f"Removed participant {user_id} from meeting {meeting_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove participant: {e}")
            return False
    
    def get_participants(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get all participants in a meeting
        
        Args:
            meeting_id: Meeting ID
        
        Returns:
            List of participant details
        """
        try:
            participants_key = self._meeting_participants_key(meeting_id)
            user_ids = self.redis.get_set_members(participants_key)
            
            participants = []
            for user_id in user_ids:
                participant_key = f"meeting:{meeting_id}:participant:{user_id}"
                participant_data = self.redis.get_hash(participant_key)
                if participant_data:
                    participants.append(participant_data)
            
            return participants
            
        except Exception as e:
            logger.error(f"Failed to get participants: {e}")
            return []
    
    # ==================== Join Request Management ====================
    
    def create_join_request(
        self,
        meeting_id: str,
        user_id: str,
        username: str,
        message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a join request
        
        Args:
            meeting_id: Meeting ID
            user_id: User ID
            username: Username
            message: Optional message to host
        
        Returns:
            Join request data or None
        """
        try:
            request_id = f"req_{uuid4().hex[:12]}"
            now = datetime.utcnow().isoformat()
            
            request_data = {
                'id': request_id,
                'meeting_id': meeting_id,
                'user_id': user_id,
                'username': username,
                'message': message or '',
                'status': 'pending',
                'created_at': now,
                'processed_at': None,
                'processed_by': None
            }
            
            # Store request
            request_key = self._join_request_key(meeting_id, request_id)
            self.redis.set_hash(request_key, request_data)
            
            # Add to meeting's join requests list
            join_requests_key = self._meeting_join_requests_key(meeting_id)
            self.redis.add_to_set(join_requests_key, request_id)
            
            logger.info(f"Created join request {request_id} for meeting {meeting_id}")
            return request_data
            
        except Exception as e:
            logger.error(f"Failed to create join request: {e}")
            return None
    
    def get_join_request(
        self,
        meeting_id: str,
        request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get join request details"""
        try:
            request_key = self._join_request_key(meeting_id, request_id)
            return self.redis.get_hash(request_key)
        except Exception as e:
            logger.error(f"Failed to get join request: {e}")
            return None
    
    def get_pending_requests(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get all pending join requests
        
        Args:
            meeting_id: Meeting ID
        
        Returns:
            List of pending requests
        """
        try:
            join_requests_key = self._meeting_join_requests_key(meeting_id)
            request_ids = self.redis.get_set_members(join_requests_key)
            
            requests = []
            for request_id in request_ids:
                request = self.get_join_request(meeting_id, request_id)
                if request and request.get('status') == 'pending':
                    requests.append(request)
            
            # Sort by created_at (oldest first)
            requests.sort(key=lambda x: x.get('created_at', ''))
            return requests
            
        except Exception as e:
            logger.error(f"Failed to get pending requests: {e}")
            return []
    
    def process_join_request(
        self,
        meeting_id: str,
        request_id: str,
        action: str,
        processed_by: str
    ) -> bool:
        """
        Approve or reject join request
        
        Args:
            meeting_id: Meeting ID
            request_id: Request ID
            action: 'approve' or 'reject'
            processed_by: User ID who processed
        
        Returns:
            True if successful
        """
        try:
            request_key = self._join_request_key(meeting_id, request_id)
            request = self.redis.get_hash(request_key)
            
            if not request:
                return False
            
            if request.get('status') != 'pending':
                return False
            
            now = datetime.utcnow().isoformat()
            
            if action == 'approve':
                self.redis.update_hash(request_key, 'status', 'approved')
                self.redis.update_hash(request_key, 'processed_at', now)
                self.redis.update_hash(request_key, 'processed_by', processed_by)
                
                # Add user to participants
                user_id = request.get('user_id')
                username = request.get('username')
                self.add_participant(meeting_id, user_id, username)
                
                logger.info(f"Approved join request {request_id}")
                
            elif action == 'reject':
                self.redis.update_hash(request_key, 'status', 'rejected')
                self.redis.update_hash(request_key, 'processed_at', now)
                self.redis.update_hash(request_key, 'processed_by', processed_by)
                
                logger.info(f"Rejected join request {request_id}")
            else:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process join request: {e}")
            return False
    
    # ==================== Transcript Management ====================
    
    async def store_transcript(
        self,
        meeting_id: str,
        content: str,
        format: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Store meeting transcript in Redis and post to channel
        
        Args:
            meeting_id: Meeting ID
            content: Transcript content
            format: Transcript format
            metadata: Additional metadata
            user_id: ID of user storing transcript (usually meeting ender)
            username: Username of user
        
        Returns:
            Transcript data or None
        """
        try:
            # Get meeting to find channel_id
            meeting = self.get_meeting(meeting_id)
            if not meeting:
                logger.error(f"Cannot store transcript: Meeting {meeting_id} not found")
                return None

            transcript_key = self._meeting_transcript_key(meeting_id)
            now = datetime.utcnow().isoformat()
            
            transcript_data = {
                'meeting_id': meeting_id,
                'content': content,
                'format': format,
                'metadata': metadata or {},
                'stored_at': now,
                'size_bytes': len(content.encode('utf-8')),
                'created_by': user_id
            }
            
            # Store transcript
            self.redis.set_hash(transcript_key, transcript_data)
            
            logger.info(f"Stored transcript for meeting {meeting_id} ({transcript_data['size_bytes']} bytes)")

            # Post to channel chat
            if user_id and username:
                try:
                    chat_service = get_redis_chat_service()
                    channel_id = meeting.get('channel_id')
                    
                    if channel_id:
                        chat_message = f"📝 **Meeting Summary**\n\n{content}"
                        
                        chat_service.send_message(
                            channel_id=channel_id,
                            user_id=user_id,
                            username=username,
                            content=chat_message,
                            message_type="system", # Use system type or text
                            metadata={
                                "type": "meeting_summary",
                                "meeting_id": meeting_id,
                                "meeting_title": meeting.get('title')
                            }
                        )
                        logger.info(f"Posted meeting transcript to channel {channel_id}")
                except Exception as chat_error:
                    logger.error(f"Failed to post transcript to chat: {chat_error}")

            # Store in MySQL Tenant DB
            await self.store_transcript_in_db(
                meeting_id=meeting_id,
                content=content,
                meeting_title=meeting.get('title', 'Untitled Meeting'),
                tenant_name=meeting.get('tenant_name'),
                user_id=user_id,
                created_at=now,
                project_id=metadata.get('project_id', 1) if metadata else 1
            )

            return transcript_data
            
        except Exception as e:
            logger.error(f"Failed to store transcript: {e}")
            return None

    async def store_transcript_in_db(
        self,
        meeting_id: str,
        content: str,
        meeting_title: str,
        tenant_name: str,
        user_id: Optional[str],
        created_at: str,
        project_id: int = 1  # Default to 1 as per implementation strategy
    ) -> bool:
        """
        Store transcript in tenant's MySQL database
        """
        if not tenant_name:
            logger.warning("No tenant_name provided, skipping MySQL transcript storage")
            return False

        try:
            # 1. Create table if not exists (Idempotent)
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS `transcripts` (
              `id` int NOT NULL AUTO_INCREMENT,
              `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Transcript title',
              `category` enum('daily_standup','sprint_meeting','retrospective') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Meeting type',
              `transcript_content` longtext COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Full transcript text',
              `transcript_date` date NOT NULL COMMENT 'Date of the meeting',
              `tags` json DEFAULT NULL COMMENT 'Tags for categorization',
              `file_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Original uploaded filename',
              `uploaded_by` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'User ID who uploaded',
              `tenant_schema` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant schema identifier',
              `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              `project_id` int NOT NULL DEFAULT 1,
              PRIMARY KEY (`id`),
              KEY `idx_category` (`category`),
              KEY `idx_date` (`transcript_date`),
              KEY `idx_tenant` (`tenant_schema`),
              FULLTEXT KEY `idx_content` (`transcript_content`),
              FULLTEXT KEY `idx_title` (`title`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Meeting transcripts for AI report generation';
            """
            
            # Execute create table in tenant schema
            await db.execute_query(create_table_sql, schema=tenant_name)

            # 2. Insert Transcript Record
            insert_sql = f"""
            INSERT INTO `transcripts` (
                title, 
                category, 
                transcript_content, 
                transcript_date, 
                uploaded_by, 
                tenant_schema, 
                project_id,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Determine category based on title (simple logic for now)
            category = 'sprint_meeting'
            if 'standup' in meeting_title.lower():
                category = 'daily_standup'
            elif 'retrospective' in meeting_title.lower():
                category = 'retrospective'
            
            transcript_date = created_at.split('T')[0]
            
            # Execute insert in tenant schema
            await db.execute_query(
                insert_sql, 
                (
                    meeting_title,
                    category,
                    content,
                    transcript_date,
                    user_id,
                    tenant_name,
                    project_id,
                    created_at
                ),
                schema=tenant_name,
                commit=True
            )
            
            logger.info(f"✅ Stored transcript in MySQL for tenant {tenant_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to store transcript in MySQL: {e}")
            return False
    
    def get_transcript(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Get meeting transcript
        
        Args:
            meeting_id: Meeting ID
        
        Returns:
            Transcript data or None
        """
        try:
            transcript_key = self._meeting_transcript_key(meeting_id)
            transcript = self.redis.get_hash(transcript_key)
            
            if not transcript:
                return None
            
            return transcript
            
        except Exception as e:
            logger.error(f"Failed to get transcript: {e}")
            return None

    def get_channel_transcripts(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get all transcripts for a channel
        
        Args:
            channel_id: Channel ID
        
        Returns:
            List of transcript data (metadata only)
        """
        try:
            meetings = self.get_channel_meetings(channel_id, include_ended=True)
            
            transcripts = []
            seen_ids = set()
            
            for meeting in meetings:
                meeting_id = meeting.get('id')
                
                # Skip if already processed
                if meeting_id in seen_ids:
                    continue
                seen_ids.add(meeting_id)

                # Check if transcript exists
                transcript = self.get_transcript(meeting_id)
                if transcript:
                    # Enrich with meeting title/date if not present in transcript metadata
                    if not transcript.get('title'):
                        transcript['title'] = meeting.get('title')
                    
                    transcripts.append(transcript)
            
            # Sort by stored_at (newest first)
            transcripts.sort(key=lambda x: x.get('stored_at', ''), reverse=True)
            return transcripts
            
        except Exception as e:
            logger.error(f"Failed to get channel transcripts: {e}")
            return []


# ==================== Singleton Instance ====================

_meeting_service: Optional[MeetingService] = None


def get_meeting_service() -> MeetingService:
    """Get meeting service instance"""
    global _meeting_service
    
    if _meeting_service is None:
        _meeting_service = MeetingService()
        logger.info("✅ Meeting Service initialized")
    
    return _meeting_service
