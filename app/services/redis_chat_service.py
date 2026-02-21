"""
Redis Chat Service - Channel and Message Management

Handles all chat-related operations:
- Channel creation and management
- User management within channels
- Message sending and retrieval
- Tenant isolation
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

from app.core.redis_chat_client import get_redis_chat

logger = logging.getLogger(__name__)


class RedisChatService:
    """Service for managing channels and messages in Redis"""
    
    def __init__(self):
        """Initialize chat service"""
        self.redis = get_redis_chat()
    
    # ==================== Channel Management ====================
    
    def create_channel(
        self,
        tenant_name: str,
        channel_name: str,
        created_by_user_id: str,
        created_by_username: str,
        description: str = "",
        is_private: bool = False,
        project_id: Optional[int] = None,
        team_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new channel
        
        Args:
            tenant_name: Tenant identifier
            channel_name: Name of the channel
            created_by_user_id: User ID creating the channel
            created_by_username: Username of creator
            description: Channel description
            is_private: Whether channel is private
            project_id: Associated project ID (optional, for project channels)
            team_name: Project/team name used for sidebar grouping (optional)
        
        Returns:
            Channel data or None if failed
        """
        try:
            channel_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            
            channel_data = {
                'id': channel_id,
                'name': channel_name,
                'description': description,
                'tenant_name': tenant_name,
                'created_by_user_id': created_by_user_id,
                'created_by_username': created_by_username,
                'created_at': now,
                'updated_at': now,
                'is_private': is_private,
                'member_count': 1
            }

            # Add project fields if provided (project channel)
            if project_id is not None:
                channel_data['project_id'] = project_id
            if team_name:
                channel_data['team_name'] = team_name
            
            # Store channel data
            channel_key = self.redis._channel_key(channel_id)
            if not self.redis.set_hash(channel_key, channel_data):
                logger.error(f"Failed to store channel {channel_id}")
                return None
            
            # Add to tenant's channels
            tenant_channels_key = self.redis._tenant_key(tenant_name, "channels")
            self.redis.add_to_set(tenant_channels_key, channel_id)
            
            # Add creator as admin member
            self.add_user_to_channel(
                tenant_name=tenant_name,
                channel_id=channel_id,
                user_id=created_by_user_id,
                username=created_by_username,
                role="admin"
            )
            
            # Add to user's channels
            user_channels_key = self.redis._user_key(tenant_name, created_by_user_id, "channels")
            self.redis.add_to_set(user_channels_key, channel_id)
            
            logger.info(f"✅ Channel created: {channel_id} ({channel_name}) by {created_by_username}")
            return channel_data
            
        except Exception as e:
            logger.error(f"Failed to create channel: {e}")
            return None
    
    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel details"""
        try:
            channel_key = self.redis._channel_key(channel_id)
            channel = self.redis.get_hash(channel_key)
            
            if channel:
                # Add real-time member count
                members_key = self.redis._channel_key(channel_id, "members")
                channel['member_count'] = self.redis.get_set_size(members_key)
                
                # Add unread count (optional - implement if needed)
                channel['unread_count'] = 0
            
            return channel
        except Exception as e:
            logger.error(f"Failed to get channel {channel_id}: {e}")
            return None
    
    def get_tenant_channels(
        self,
        tenant_name: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all channels for a tenant
        
        Args:
            tenant_name: Tenant identifier
            user_id: If provided, filter channels user is member of
        
        Returns:
            List of channels
        """
        try:
            if user_id:
                # Get user's channels
                user_channels_key = self.redis._user_key(tenant_name, user_id, "channels")
                channel_ids = self.redis.get_set_members(user_channels_key)
            else:
                # Get all tenant channels
                tenant_channels_key = self.redis._tenant_key(tenant_name, "channels")
                channel_ids = self.redis.get_set_members(tenant_channels_key)
            
            channels = []
            for channel_id in channel_ids:
                channel = self.get_channel(channel_id)
                if channel:
                    channels.append(channel)
            
            # Sort by name
            channels.sort(key=lambda x: x.get('name', '').lower())
            
            return channels
            
        except Exception as e:
            logger.error(f"Failed to get tenant channels: {e}")
            return []
    
    def update_channel(
        self,
        channel_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update channel details
        
        Args:
            channel_id: Channel ID
            updates: Fields to update
        
        Returns:
            True if successful
        """
        try:
            channel_key = self.redis._channel_key(channel_id)
            
            # Check if channel exists
            if not self.redis.key_exists(channel_key):
                logger.warning(f"Channel {channel_id} not found")
                return False
            
            # Update timestamp
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            # Update each field
            for field, value in updates.items():
                self.redis.update_hash(channel_key, field, value)
            
            logger.info(f"✅ Channel updated: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update channel {channel_id}: {e}")
            return False
    
    def delete_channel(
        self,
        tenant_name: str,
        channel_id: str
    ) -> bool:
        """
        Delete a channel
        
        Args:
            tenant_name: Tenant identifier
            channel_id: Channel ID
        
        Returns:
            True if successful
        """
        try:
            # Get channel members to clean up
            members_key = self.redis._channel_key(channel_id, "members")
            member_ids = self.redis.get_set_members(members_key)
            
            # Remove channel from each user's channel list
            for user_id in member_ids:
                user_channels_key = self.redis._user_key(tenant_name, user_id, "channels")
                self.redis.remove_from_set(user_channels_key, channel_id)
            
            # Delete channel data
            channel_key = self.redis._channel_key(channel_id)
            self.redis.delete_key(channel_key)
            
            # Delete members
            self.redis.delete_key(members_key)
            
            # Delete messages
            messages_key = self.redis._message_key(channel_id)
            self.redis.delete_key(messages_key)
            
            # Remove from tenant's channels
            tenant_channels_key = self.redis._tenant_key(tenant_name, "channels")
            self.redis.remove_from_set(tenant_channels_key, channel_id)
            
            logger.info(f"✅ Channel deleted: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete channel {channel_id}: {e}")
            return False
    
    # ==================== User/Member Management ====================
    
    def add_user_to_channel(
        self,
        tenant_name: str,
        channel_id: str,
        user_id: str,
        username: str,
        role: str = "member"
    ) -> bool:
        """
        Add user to channel
        
        Args:
            tenant_name: Tenant identifier
            channel_id: Channel ID
            user_id: User ID
            username: Username
            role: User role (admin, member)
        
        Returns:
            True if successful
        """
        try:
            # Add to channel members
            members_key = self.redis._channel_key(channel_id, "members")
            self.redis.add_to_set(members_key, user_id)
            
            # Store member details
            member_key = self.redis._channel_key(channel_id, f"member:{user_id}")
            member_data = {
                'user_id': user_id,
                'username': username,
                'tenant_name': tenant_name,
                'role': role,
                'joined_at': datetime.utcnow().isoformat()
            }
            self.redis.set_hash(member_key, member_data)
            
            # Add to user's channels
            user_channels_key = self.redis._user_key(tenant_name, user_id, "channels")
            self.redis.add_to_set(user_channels_key, channel_id)
            
            # Update member count
            channel_key = self.redis._channel_key(channel_id)
            member_count = self.redis.get_set_size(members_key)
            self.redis.update_hash(channel_key, 'member_count', member_count)
            
            logger.info(f"✅ User {username} added to channel {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add user to channel: {e}")
            return False
    
    def remove_user_from_channel(
        self,
        tenant_name: str,
        channel_id: str,
        user_id: str
    ) -> bool:
        """Remove user from channel"""
        try:
            # Remove from channel members
            members_key = self.redis._channel_key(channel_id, "members")
            self.redis.remove_from_set(members_key, user_id)
            
            # Delete member details
            member_key = self.redis._channel_key(channel_id, f"member:{user_id}")
            self.redis.delete_key(member_key)
            
            # Remove from user's channels
            user_channels_key = self.redis._user_key(tenant_name, user_id, "channels")
            self.redis.remove_from_set(user_channels_key, channel_id)
            
            # Update member count
            channel_key = self.redis._channel_key(channel_id)
            member_count = self.redis.get_set_size(members_key)
            self.redis.update_hash(channel_key, 'member_count', member_count)
            
            logger.info(f"✅ User {user_id} removed from channel {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove user from channel: {e}")
            return False
    
    def get_channel_members(
        self,
        channel_id: str
    ) -> List[Dict[str, Any]]:
        """Get all members of a channel"""
        try:
            members_key = self.redis._channel_key(channel_id, "members")
            member_ids = self.redis.get_set_members(members_key)
            
            members = []
            for user_id in member_ids:
                member_key = self.redis._channel_key(channel_id, f"member:{user_id}")
                member_data = self.redis.get_hash(member_key)
                if member_data:
                    members.append(member_data)
            
            return members
            
        except Exception as e:
            logger.error(f"Failed to get channel members: {e}")
            return []
    
    def is_user_in_channel(
        self,
        channel_id: str,
        user_id: str
    ) -> bool:
        """Check if user is member of channel"""
        try:
            members_key = self.redis._channel_key(channel_id, "members")
            return self.redis.is_set_member(members_key, user_id)
        except Exception as e:
            logger.error(f"Failed to check user membership: {e}")
            return False
    
    # ==================== Message Management ====================
    
    def send_message(
        self,
        channel_id: str,
        user_id: str,
        username: str,
        content: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send message to channel
        
        Args:
            channel_id: Channel ID
            user_id: Sender user ID
            username: Sender username
            content: Message content
            message_type: Type of message (text, file, image, etc.)
            metadata: Additional metadata (file info, etc.)
        
        Returns:
            Message data or None if failed
        """
        try:
            message_id = str(uuid4())
            now = datetime.utcnow().isoformat()
            
            message_data = {
                'id': message_id,
                'channel_id': channel_id,
                'user_id': user_id,
                'username': username,
                'content': content,
                'type': message_type,
                'created_at': now,
                'updated_at': now,
                'edited': False,
                'deleted': False
            }
            
            if metadata:
                message_data['metadata'] = metadata
            
            # Store message in channel's message list
            messages_key = self.redis._message_key(channel_id)
            import json
            message_json = json.dumps(message_data)
            self.redis.push_to_list(messages_key, message_json, left=False)
            
            # Keep only last 10000 messages (configurable)
            list_length = self.redis.get_list_length(messages_key)
            if list_length > 10000:
                self.redis.trim_list(messages_key, -10000, -1)
            
            # Publish to channel for real-time delivery
            self.redis.publish(f"channel:{channel_id}", {
                'type': 'new_message',
                'data': message_data
            })
            
            logger.info(f"✅ Message sent to channel {channel_id} by {username}")
            return message_data
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get messages from channel
        
        Args:
            channel_id: Channel ID
            limit: Number of messages to retrieve
            offset: Offset from the end (for pagination)
        
        Returns:
            List of messages (newest first)
        """
        try:
            messages_key = self.redis._message_key(channel_id)
            
            # Get total count
            total_count = self.redis.get_list_length(messages_key)
            
            if total_count == 0:
                return []
            
            # Calculate range (from end of list)
            start = max(0, total_count - offset - limit)
            end = total_count - offset - 1
            
            # Get messages
            import json
            message_strings = self.redis.get_list_range(messages_key, start, end)
            
            messages = []
            for msg_str in message_strings:
                try:
                    msg = json.loads(msg_str)
                    # Skip deleted messages
                    if not msg.get('deleted', False):
                        messages.append(msg)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse message: {e}")
                    continue
            
            # Reverse to get newest first
            messages.reverse()
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def update_message(
        self,
        channel_id: str,
        message_id: str,
        new_content: str
    ) -> bool:
        """
        Update/edit a message
        
        Note: This is inefficient with Redis lists. For production,
        consider using a different data structure or caching layer.
        """
        try:
            messages_key = self.redis._message_key(channel_id)
            messages = self.get_messages(channel_id, limit=10000)
            
            import json
            updated = False
            for i, msg in enumerate(messages):
                if msg['id'] == message_id:
                    msg['content'] = new_content
                    msg['edited'] = True
                    msg['updated_at'] = datetime.utcnow().isoformat()
                    updated = True
                    break
            
            if updated:
                # Rebuild the list (inefficient but simple)
                self.redis.delete_key(messages_key)
                messages.reverse()  # Back to oldest first
                for msg in messages:
                    msg_json = json.dumps(msg)
                    self.redis.push_to_list(messages_key, msg_json, left=False)
                
                logger.info(f"✅ Message {message_id} updated")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update message: {e}")
            return False
    
    def delete_message(
        self,
        channel_id: str,
        message_id: str,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete a message
        
        Args:
            channel_id: Channel ID
            message_id: Message ID
            soft_delete: If True, mark as deleted; if False, remove completely
        
        Returns:
            True if successful
        """
        try:
            messages_key = self.redis._message_key(channel_id)
            messages = self.get_messages(channel_id, limit=10000)
            
            import json
            deleted = False
            for msg in messages:
                if msg['id'] == message_id:
                    if soft_delete:
                        msg['deleted'] = True
                        msg['updated_at'] = datetime.utcnow().isoformat()
                    else:
                        messages.remove(msg)
                    deleted = True
                    break
            
            if deleted:
                # Rebuild the list
                self.redis.delete_key(messages_key)
                messages.reverse()  # Back to oldest first
                for msg in messages:
                    msg_json = json.dumps(msg)
                    self.redis.push_to_list(messages_key, msg_json, left=False)
                
                logger.info(f"✅ Message {message_id} deleted")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False


# ==================== Singleton Instance ====================

_redis_chat_service: Optional[RedisChatService] = None


def get_redis_chat_service() -> RedisChatService:
    """Get Redis chat service instance"""
    global _redis_chat_service
    
    if _redis_chat_service is None:
        _redis_chat_service = RedisChatService()
        logger.info("✅ Redis Chat Service initialized")
    
    return _redis_chat_service
