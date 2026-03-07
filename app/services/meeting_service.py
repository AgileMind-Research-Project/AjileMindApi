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
        description: Optional[str] = None,
        meeting_id: Optional[str] = None,
        project_id: Optional[int] = 0,
        sprint_id: Optional[int] = None,
        creator_email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new instant meeting or activate a scheduled one
        """
        try:
            if not meeting_id:
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
                'tenant_name': tenant_name,
                'project_id': project_id,
                'sprint_id': sprint_id or '' # Redis hashes don't like None
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
            self.add_participant(meeting_id, created_by_user_id, created_by_username, creator_email)
            
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
            
            # Check participant count - at least 2 members required to start
            participants_key = self._meeting_participants_key(meeting_id)
            participant_count = self.redis.get_set_size(participants_key)
            
            if participant_count < 1:
                logger.warning(f"Meeting {meeting_id} cannot start: at least 1 participant required (currently {participant_count})")
                return False

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
        username: str,
        email: Optional[str] = None
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
                'email': email or '',
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
        username: Optional[str] = None,
        tenant_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Store meeting transcript in Redis and post to channel
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
            
            # Store transcript in Redis
            self.redis.set_hash(transcript_key, transcript_data)
            
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
                            message_type="system", 
                            metadata={
                                "type": "meeting_summary",
                                "meeting_id": meeting_id,
                                "meeting_title": meeting.get('title')
                            }
                        )
                except Exception as chat_error:
                    logger.error(f"Failed to post transcript to chat: {chat_error}")

            # Get participants for attendance update
            participants_list = meeting.get('participants', [])
            if not participants_list:
                import re
                speakers = re.findall(r'^([^:\n]+):', content, re.MULTILINE)
                participants_list = sorted(list(set(s.strip() for s in speakers)))

            # Fallback IDs from meeting if not in metadata
            p_id = metadata.get('project_id') if metadata else None
            if p_id is None: 
                p_id = meeting.get('project_id')
            
            # If still None, try to get from channel
            if p_id is None or p_id == 0 or p_id == '':
                channel_id = meeting.get('channel_id')
                if channel_id:
                    try:
                        # 1. Try to get channel metadata
                        chat_service = get_redis_chat_service()
                        channel = chat_service.get_channel(channel_id)
                        if channel and channel.get('project_id'):
                            p_id = channel.get('project_id')
                        # 2. If channel_id itself is numeric, it might be the project_id (fallback for some legacy setups)
                        elif str(channel_id).isdigit():
                            p_id = channel_id
                    except Exception as channel_err:
                        logger.debug(f"Could not get project_id from channel {channel_id}: {channel_err}")

            # Coerce p_id for FK safety
            try:
                if p_id and int(p_id) > 0: p_id = int(p_id)
                else: p_id = None
            except: p_id = None

            # Fetch full participant info (including emails) from Redis if not provided
            participants_info = []
            redis_participants = self.get_participants(meeting_id)
            if redis_participants:
                participants_info = [{
                    'username': p.get('username'),
                    'email': p.get('email', '')
                } for p in redis_participants]
                
            # Fallback if no participants in Redis (extract from text)
            if not participants_info:
                import re
                speakers = list(set(re.findall(r'^([^:\n]+):', content, re.MULTILINE)))
                participants_info = [{'username': s.strip(), 'email': ''} for s in speakers if s.strip()]

            s_id = metadata.get('sprint_id') if metadata else None
            if s_id is None:
                s_id = meeting.get('sprint_id')
                if not s_id or s_id == '': s_id = None
                else: 
                    try: s_id = int(s_id)
                    except: s_id = None

            # Store in MySQL Tenant DB
            db_transcript_id = await self.store_transcript_in_db(
                meeting_id=meeting_id,
                content=content,
                meeting_title=meeting.get('title', 'Untitled Meeting'),
                tenant_name=tenant_name or meeting.get('tenant_name'),
                user_id=user_id,
                created_at=now,
                project_id=p_id,
                sprint_id=s_id,
                participants=participants_info
            )

            if db_transcript_id:
                transcript_data['id'] = db_transcript_id
                # Update Redis with the ID
                self.redis.set_hash(transcript_key, transcript_data)
            else:
                logger.warning(f"Transcript for {meeting_id} saved to Redis but failed for MySQL")

            return transcript_data
            
        except Exception as e:
            logger.error(f"Failed to store transcript: {e}")
            return None

    async def get_db_channel_transcripts(self, tenant_name: str, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get all transcripts for a channel from MySQL DB with meeting type distinction
        """
        try:
            # Query MySQL transcripts table join with sprint and meetings
            # Using subquery to deduplicate by meeting_id (keeping latest per meeting)
            query = """
                SELECT t.id, t.meeting_id, t.title, t.category, t.transcript_date, t.tags, 
                       t.file_name, t.created_at, t.project_id, t.sprint_id, 
                       s.sprint_name, m.attendees,
                       CASE WHEN m.meeting_id IS NOT NULL THEN 'scheduled' ELSE 'meeting_now' END as meeting_type
                FROM transcripts t
                LEFT JOIN sprint s ON t.sprint_id = s.sprint_id
                LEFT JOIN meetings m ON t.meeting_id = m.meeting_id
                WHERE (t.project_id = %s OR t.sprint_id = %s)
                AND (t.meeting_id IS NULL OR t.id IN (
                    SELECT MAX(id) FROM transcripts GROUP BY meeting_id
                ))
                ORDER BY t.created_at DESC
            """
            results = await db.execute_query(query, (channel_id, channel_id), schema=tenant_name, fetch_all=True)
            
            import json
            for r in results:
                # Calculate participant count from attendees
                participants = []
                if r.get('attendees'):
                    try: participants = json.loads(r['attendees'])
                    except: participants = []
                r['participant_count'] = len(participants)
                
                if r.get('tags') and isinstance(r['tags'], str):
                    try: r['tags'] = json.loads(r['tags'])
                    except: r['tags'] = []
                
                # Coerce dates for JSON
                for key in ('transcript_date', 'created_at'):
                    if r.get(key): 
                        r[key] = str(r[key])
                    elif key == 'transcript_date':
                        # Fallback for missing date
                        r[key] = str(date.today())

            return results
        except Exception as e:
            logger.error(f"Failed to fetch transcripts from DB for channel {channel_id}: {e}")
            return []

    async def get_channel_transcripts(self, channel_id: str, tenant_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all transcripts for a channel (Historical DB + Previous Redis records)
        """
        db_transcripts = []
        try:
            if tenant_name:
                db_transcripts = await self.get_db_channel_transcripts(tenant_name, channel_id)
        except Exception as e:
            logger.error(f"Failed to fetch DB transcripts: {e}")
        
        # Also check Redis for any recent ones or historical Redis-only transcripts
        redis_transcripts = []
        try:
            meetings = self.get_channel_meetings(channel_id, include_ended=True)
            for m in meetings:
                try:
                    m_id = m.get('id')
                    t_redis = self.get_transcript(m_id)
                    if t_redis:
                        # Extract date or use current as fallback to prevent 'Invalid Date'
                        stored_at = t_redis.get('stored_at') or ''
                        transcript_date = stored_at.split('T')[0] if 'T' in stored_at else ''
                        
                        formatted = {
                            'id': f"redis_{m_id}", 
                            'meeting_id': m_id,
                            'title': t_redis.get('title') or m.get('title', 'Untitled Meeting'),
                            'category': 'other', 
                            'transcript_date': transcript_date or datetime.utcnow().strftime('%Y-%m-%d'),
                            'created_at': stored_at,
                            'meeting_type': 'meeting_now',
                            'source': 'redis',
                            'participant_count': m.get('participant_count', 0)
                        }
                        redis_transcripts.append(formatted)
                except:
                    continue
        except Exception as e:
            logger.debug(f"Redis transcript fetch skipped (connection issue?): {e}")

        # Combine transcripts
        # Use a map to prevent duplicates, preferring DB records
        combined = {t.get('meeting_id'): t for t in db_transcripts if t.get('meeting_id')}
        
        for t in redis_transcripts:
            m_id = t.get('meeting_id')
            if m_id not in combined:
                combined[m_id] = t
        
        results = list(combined.values())
        results.extend([t for t in db_transcripts if not t.get('meeting_id')])
        
        # Sort by creation time (newest first)
        results.sort(key=lambda x: str(x.get('created_at', '') or ''), reverse=True)
        return results

    async def store_transcript_in_db(
        self,
        meeting_id: str,
        content: str,
        meeting_title: str,
        tenant_name: str,
        user_id: Optional[str],
        created_at: str,
        project_id: int = 0,
        sprint_id: Optional[int] = None,
        participants: Optional[List[str]] = None
    ) -> Optional[int]:
        """
        Store transcript in tenant's MySQL database and update meeting attendance
        """
        if not tenant_name:
            logger.warning("No tenant_name provided, skipping MySQL transcript storage")
            return None

        try:
            # 1. Create table if not exists (Updated to include meeting_id)
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS `transcripts` (
                `id` int NOT NULL AUTO_INCREMENT,
                `meeting_id` varchar(50) DEFAULT NULL,
                `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Transcript title',
                `category` enum('daily_standup','sprint_meeting','retrospective','sprint_planning','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Meeting type',
                `transcript_content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Full transcript text',
                `transcript_date` date NOT NULL COMMENT 'Date of the meeting',
                `tags` json DEFAULT NULL COMMENT 'Tags for categorization',
                `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Original uploaded filename',
                `uploaded_by` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'User ID who uploaded',
                `tenant_schema` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Tenant schema identifier',
                `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                `project_id` BIGINT DEFAULT 0 COMMENT 'Reference to projects.project_id',
                `sprint_id` BIGINT DEFAULT NULL COMMENT 'Reference to sprint.sprint_id',
                PRIMARY KEY (`id`),
                KEY `idx_category` (`category`),
                KEY `idx_date` (`transcript_date`),
                KEY `idx_tenant` (`tenant_schema`),
                KEY `idx_project_id` (`project_id`),
                KEY `idx_sprint_id` (`sprint_id`),
                FULLTEXT KEY `idx_content` (`transcript_content`),
                FULLTEXT KEY `idx_title` (`title`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Meeting transcripts for AI report generation';
            """
            
            # Execute create table in tenant schema
            await db.execute_query(create_table_sql, schema=tenant_name)
            
            # 1.5 Ensure columns exist (for older tables)
            # We fetch existing columns first to avoid Duplicate Column errors in logs
            try:
                check_cols_sql = "SHOW COLUMNS FROM `transcripts`"
                existing_cols_raw = await db.execute_query(check_cols_sql, schema=tenant_name, fetch_all=True)
                existing_cols = [c['Field'].lower() for c in existing_cols_raw] if existing_cols_raw else []
                
                migration_sqls = []
                if 'meeting_id' not in existing_cols:
                    migration_sqls.append("ALTER TABLE `transcripts` ADD COLUMN `meeting_id` varchar(50) DEFAULT NULL AFTER `id`")
                
                # Ensure meeting_id has a UNIQUE index to prevent double-insertions from race conditions
                try:
                    check_index_sql = "SHOW INDEX FROM `transcripts` WHERE Key_name = 'uk_meeting_id'"
                    index_exists = await db.execute_query(check_index_sql, schema=tenant_name, fetch_one=True)
                    if not index_exists:
                        migration_sqls.append("ALTER TABLE `transcripts` ADD UNIQUE KEY `uk_meeting_id` (`meeting_id`)")
                except: pass

                if 'project_id' not in existing_cols:
                    migration_sqls.append("ALTER TABLE `transcripts` ADD COLUMN `project_id` BIGINT DEFAULT NULL AFTER `tenant_schema`")
                if 'sprint_id' not in existing_cols:
                    migration_sqls.append("ALTER TABLE `transcripts` ADD COLUMN `sprint_id` BIGINT DEFAULT NULL AFTER `project_id`")
                
                for sql in migration_sqls:
                    try: await db.execute_query(sql, schema=tenant_name, commit=True)
                    except Exception as inner_e:
                        logger.debug(f"Migration step skipped: {inner_e}")
            except Exception as e:
                logger.warning(f"Could not verify/migrate transcript table structure: {e}")

            # 2. Determine category based on title
            category = 'sprint_meeting'
            lower_title = meeting_title.lower()
            if 'standup' in lower_title or 'daily' in lower_title:
                category = 'daily_standup'
            elif 'retrospective' in lower_title or 'retro' in lower_title:
                category = 'retrospective'
            elif 'planning' in lower_title:
                category = 'sprint_planning'
            elif 'sprint' in lower_title:
                category = 'sprint_meeting'
            else:
                category = 'other'
            
            transcript_date = created_at.split('T')[0]
            
            # 3. Check for existing transcript with this meeting_id to prevent duplicates
            if meeting_id:
                check_existing_sql = "SELECT id FROM `transcripts` WHERE meeting_id = %s LIMIT 1"
                existing = await db.execute_query(check_existing_sql, (meeting_id,), schema=tenant_name, fetch_one=True)
                
                if existing:
                    # Update existing record
                    update_sql = """
                    UPDATE `transcripts` 
                    SET transcript_content = %s, title = %s, category = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """
                    await db.execute_query(
                        update_sql, 
                        (content, meeting_title, category, existing['id']),
                        schema=tenant_name,
                        commit=True
                    )
                    logger.info(f"Updated existing transcript for meeting {meeting_id}")
                    # Update attendees too
                    if meeting_id and participants:
                        try:
                            import json
                            attendees_json = json.dumps(participants)
                            await db.execute_query("UPDATE `meetings` SET attendees = %s WHERE meeting_id = %s", (attendees_json, meeting_id), schema=tenant_name, commit=True)
                        except: pass
                    return existing['id']

            # 4. Insert new Transcript Record if not exists
            insert_sql = """
            INSERT INTO `transcripts` (
                meeting_id, title, category, transcript_content, transcript_date, 
                uploaded_by, tenant_schema, project_id, sprint_id, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            await db.execute_query(
                insert_sql, 
                (
                    meeting_id, meeting_title, category, content, transcript_date,
                    user_id, tenant_name, project_id, sprint_id, created_at
                ),
                schema=tenant_name,
                commit=True
            )
            
            # Fetch last insert ID
            last_id_res = await db.execute_query("SELECT LAST_INSERT_ID() as id", schema=tenant_name, fetch_one=True)
            transcript_id = last_id_res['id'] if last_id_res else None
            
            # 4. Update Meeting Attendance (attendees field)
            if meeting_id and participants:
                import json
                # Ensure each participant is consistently formatted (string or dict)
                # But we prefer dicts with emails if available
                attendees_json = json.dumps(participants)
                update_meeting_sql = "UPDATE `meetings` SET attendees = %s WHERE meeting_id = %s"
                try:
                    await db.execute_query(
                        update_meeting_sql,
                        (attendees_json, meeting_id),
                        schema=tenant_name,
                        commit=True
                    )
                except Exception as am_err:
                    logger.warning(f"Could not update meeting attendance for {meeting_id}: {am_err}")

            logger.info(f"Stored transcript in MySQL for tenant {tenant_name} with ID {transcript_id}")
            return transcript_id

        except Exception as e:
            logger.error(f"Failed to store transcript in MySQL: {e}")
            return None
    
    async def get_transcript(self, meeting_id: str, tenant_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get meeting transcript (Redis or MySQL)
        """
        try:
            # 1. Try Redis first
            real_m_id = meeting_id
            if real_m_id.startswith("redis_"):
                real_m_id = real_m_id.replace("redis_", "")

            transcript_key = self._meeting_transcript_key(real_m_id)
            transcript = self.redis.get_hash(transcript_key)
            
            if transcript:
                logger.info(f"Found transcript for {real_m_id} in Redis")
                
                # Enrich with ID from MySQL if missing
                if not transcript.get('id') and tenant_name:
                    try:
                        id_query = "SELECT id FROM `transcripts` WHERE meeting_id = %s LIMIT 1"
                        id_res = await db.execute_query(id_query, (real_m_id,), schema=tenant_name, fetch_one=True)
                        if id_res:
                            transcript['id'] = id_res['id']
                            # Update Redis cache with the ID
                            self.redis.set_hash(transcript_key, transcript)
                            logger.info(f"Enriched Redis transcript with MySQL ID {transcript['id']}")
                    except Exception as e:
                        logger.debug(f"Could not enrich Redis transcript with ID: {e}")

                # Format dates for frontend
                if transcript.get('stored_at'):
                    transcript['stored_at'] = str(transcript['stored_at'])
                return transcript

            # 2. Try MySQL if tenant is known
            if tenant_name:
                logger.info(f"Searching transcript for {real_m_id} in MySQL (Tenant: {tenant_name})")
                
                # Try by meeting_id first
                query = """
                    SELECT t.id, t.meeting_id, t.transcript_content as content, t.title, t.category, 
                           t.created_at as stored_at, t.uploaded_by as created_by,
                           m.attendees, t.project_id, t.sprint_id
                    FROM transcripts t
                    LEFT JOIN meetings m ON t.meeting_id = m.meeting_id
                    WHERE t.meeting_id = %s
                    LIMIT 1
                """
                db_res = await db.execute_query(query, (real_m_id,), schema=tenant_name, fetch_one=True)
                
                if not db_res:
                    # FALLBACK: Try lookup by project_id and sprint_id if meeting exists but no link yet
                    # This helps with historical data or legacy records
                    logger.debug(f"No direct meeting_id match for {real_m_id}, trying fallback...")
                    
                    # Get meeting details to find project/sprint if possible
                    meeting_query = "SELECT project_id, sprint_id, title FROM meetings WHERE meeting_id = %s"
                    m_details = await db.execute_query(meeting_query, (real_m_id,), schema=tenant_name, fetch_one=True)
                    
                    if m_details:
                        fallback_query = """
                            SELECT DISTINCT t.meeting_id, t.id, t.transcript_content as content, t.title, t.category, 
                                   t.created_at as stored_at, t.uploaded_by as created_by,
                                   t.project_id, t.sprint_id
                            FROM transcripts t
                            WHERE t.project_id = %s AND t.sprint_id = %s AND t.title = %s
                        """
                        db_res = await db.execute_query(
                            fallback_query, 
                            (m_details['project_id'], m_details['sprint_id'], m_details['title']), 
                            schema=tenant_name, 
                            fetch_one=True
                        )
                
                if db_res:
                    logger.info(f"Found transcript for {real_m_id} in MySQL")
                    # Format dates
                    if db_res.get('stored_at'):
                        db_res['stored_at'] = str(db_res['stored_at'])
                    
                    db_res['format'] = 'text'
                    
                    # Map attendees to participants for frontend
                    import json
                    participants = []
                    if db_res.get('attendees'):
                        try:
                            participants = json.loads(db_res['attendees'])
                        except:
                            participants = []
                    
                    db_res['participants'] = participants
                    db_res['metadata'] = {
                        'category': db_res.get('category'),
                        'participant_count': len(participants)
                    }
                    return db_res

            return None
        except Exception as e:
            logger.error(f"Failed to get transcript for {meeting_id}: {e}")
            return None




# ==================== Singleton Instance ====================

_meeting_service: Optional[MeetingService] = None


def get_meeting_service() -> MeetingService:
    """Get meeting service instance"""
    global _meeting_service
    
    if _meeting_service is None:
        _meeting_service = MeetingService()
        logger.info("Meeting Service initialized")
    
    return _meeting_service
