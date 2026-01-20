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
    
    def end_meeting(self, meeting_id: str, tenant_name: str) -> bool:
        """
        End a meeting
        
        Args:
            meeting_id: Meeting ID
            tenant_name: Tenant name
        
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
    
    def store_transcript(
        self,
        meeting_id: str,
        content: str,
        format: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Store meeting transcript in Redis
        
        Args:
            meeting_id: Meeting ID
            content: Transcript content
            format: Transcript format
            metadata: Additional metadata
        
        Returns:
            Transcript data or None
        """
        try:
            transcript_key = self._meeting_transcript_key(meeting_id)
            now = datetime.utcnow().isoformat()
            
            transcript_data = {
                'meeting_id': meeting_id,
                'content': content,
                'format': format,
                'metadata': metadata or {},
                'stored_at': now,
                'size_bytes': len(content.encode('utf-8'))
            }
            
            # Store transcript
            self.redis.set_hash(transcript_key, transcript_data)
            
            logger.info(f"Stored transcript for meeting {meeting_id} ({transcript_data['size_bytes']} bytes)")
            return transcript_data
            
        except Exception as e:
            logger.error(f"Failed to store transcript: {e}")
            return None
    
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


# ==================== Singleton Instance ====================

_meeting_service: Optional[MeetingService] = None


def get_meeting_service() -> MeetingService:
    """Get meeting service instance"""
    global _meeting_service
    
    if _meeting_service is None:
        _meeting_service = MeetingService()
        logger.info("✅ Meeting Service initialized")
    
    return _meeting_service
