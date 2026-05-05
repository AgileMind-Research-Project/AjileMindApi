"""
Redis Chat Client - Connection and Helper Methods

Provides Redis connection management and helper methods for chat operations.
Includes tenant isolation for multi-tenant chat system.
"""

import redis
import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


class RedisChatClient:
    """Redis client for chat operations with tenant isolation"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        password: str = None,
        username: str = None,
        db: int = None,
        decode_responses: bool = True
    ):
        """
        Initialize Redis client for chat
        
        Args:
            host: Redis host (defaults to REDIS_HOST env var)
            port: Redis port (defaults to REDIS_PORT env var)
            password: Redis password (defaults to REDIS_PASSWORD env var)
            username: Redis username (defaults to REDIS_USERNAME env var)
            db: Redis database number (defaults to REDIS_DB env var)
            decode_responses: Auto-decode responses to strings
        """
        # Use environment variables with fallbacks
        host = host or os.getenv('REDIS_HOST', 'localhost')
        port = port or int(os.getenv('REDIS_PORT', 6379))
        password = password or os.getenv('REDIS_PASSWORD', '')
        username = username or os.getenv('REDIS_USERNAME', 'default')
        db = db if db is not None else int(os.getenv('REDIS_DB', 0))
        
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                username=username,
                db=db,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_keepalive=True,
                max_connections=50
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis connected successfully to {host}:{port}")
            
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Redis initialization error: {e}")
            raise
    
    # ==================== Health & Utility ====================
    
    def ping(self) -> bool:
        """Check if Redis is connected"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis server information"""
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}
    
    # ==================== Key Helpers ====================
    
    def _tenant_key(self, tenant_name: str, suffix: str) -> str:
        """Generate tenant-scoped key"""
        return f"tenant:{tenant_name}:{suffix}"
    
    def _channel_key(self, channel_id: str, suffix: str = "") -> str:
        """Generate channel key"""
        if suffix:
            return f"channel:{channel_id}:{suffix}"
        return f"channel:{channel_id}"
    
    def _user_key(self, tenant_name: str, user_id: str, suffix: str = "") -> str:
        """Generate user key"""
        if suffix:
            return f"user:{tenant_name}:{user_id}:{suffix}"
        return f"user:{tenant_name}:{user_id}"
    
    def _message_key(self, channel_id: str) -> str:
        """Generate message list key"""
        return f"messages:{channel_id}"
    
    # ==================== Hash Operations ====================
    
    def set_hash(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Set hash data
        
        Args:
            key: Redis key
            data: Dictionary to store
        
        Returns:
            True if successful
        """
        try:
            # Convert dict values to strings
            str_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                       for k, v in data.items()}
            self.client.hset(key, mapping=str_data)
            return True
        except Exception as e:
            logger.error(f"Failed to set hash {key}: {e}")
            return False
    
    def get_hash(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get hash data
        
        Args:
            key: Redis key
        
        Returns:
            Dictionary or None
        """
        try:
            data = self.client.hgetall(key)
            if not data:
                return None
            
            # Try to parse JSON values
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            
            return result
        except Exception as e:
            logger.error(f"Failed to get hash {key}: {e}")
            return None
    
    def update_hash(self, key: str, field: str, value: Any) -> bool:
        """Update single field in hash"""
        try:
            str_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            self.client.hset(key, field, str_value)
            return True
        except Exception as e:
            logger.error(f"Failed to update hash {key}.{field}: {e}")
            return False
    
    def delete_hash_field(self, key: str, field: str) -> bool:
        """Delete field from hash"""
        try:
            self.client.hdel(key, field)
            return True
        except Exception as e:
            logger.error(f"Failed to delete hash field {key}.{field}: {e}")
            return False
    
    # ==================== Set Operations ====================
    
    def add_to_set(self, key: str, *values: str) -> int:
        """
        Add values to set
        
        Returns:
            Number of elements added
        """
        try:
            return self.client.sadd(key, *values)
        except Exception as e:
            logger.error(f"Failed to add to set {key}: {e}")
            return 0
    
    def remove_from_set(self, key: str, *values: str) -> int:
        """Remove values from set"""
        try:
            return self.client.srem(key, *values)
        except Exception as e:
            logger.error(f"Failed to remove from set {key}: {e}")
            return 0
    
    def get_set_members(self, key: str) -> List[str]:
        """Get all members of a set"""
        try:
            members = self.client.smembers(key)
            return list(members) if members else []
        except Exception as e:
            logger.error(f"Failed to get set members {key}: {e}")
            return []
    
    def is_set_member(self, key: str, value: str) -> bool:
        """Check if value exists in set"""
        try:
            return self.client.sismember(key, value)
        except Exception as e:
            logger.error(f"Failed to check set membership {key}: {e}")
            return False
    
    def get_set_size(self, key: str) -> int:
        """Get size of set"""
        try:
            return self.client.scard(key)
        except Exception as e:
            logger.error(f"Failed to get set size {key}: {e}")
            return 0
    
    # ==================== List Operations ====================
    
    def push_to_list(self, key: str, *values: str, left: bool = False) -> int:
        """
        Push values to list
        
        Args:
            key: Redis key
            values: Values to push
            left: If True, push to left (LPUSH), else right (RPUSH)
        
        Returns:
            Length of list after push
        """
        try:
            if left:
                return self.client.lpush(key, *values)
            else:
                return self.client.rpush(key, *values)
        except Exception as e:
            logger.error(f"Failed to push to list {key}: {e}")
            return 0
    
    def get_list_range(
        self,
        key: str,
        start: int = 0,
        end: int = -1
    ) -> List[str]:
        """Get range of list elements"""
        try:
            return self.client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Failed to get list range {key}: {e}")
            return []
    
    def get_list_length(self, key: str) -> int:
        """Get length of list"""
        try:
            return self.client.llen(key)
        except Exception as e:
            logger.error(f"Failed to get list length {key}: {e}")
            return 0
    
    def trim_list(self, key: str, start: int, end: int) -> bool:
        """Trim list to specified range"""
        try:
            self.client.ltrim(key, start, end)
            return True
        except Exception as e:
            logger.error(f"Failed to trim list {key}: {e}")
            return False
    
    # ==================== String Operations ====================
    
    def set_value(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set simple key-value
        
        Args:
            key: Redis key
            value: Value to store
            expire: Expiration in seconds (optional)
        
        Returns:
            True if successful
        """
        try:
            str_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            self.client.set(key, str_value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"Failed to set value {key}: {e}")
            return False
    
    def get_value(self, key: str) -> Optional[Any]:
        """Get value"""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Failed to get value {key}: {e}")
            return None
    
    def delete_key(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys: {e}")
            return 0
    
    def key_exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check key existence {key}: {e}")
            return False
    
    def set_expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Failed to set expire on {key}: {e}")
            return False
    
    # ==================== Pub/Sub Operations ====================
    
    def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Publish message to channel
        
        Returns:
            Number of subscribers that received the message
        """
        try:
            msg_str = json.dumps(message)
            return self.client.publish(channel, msg_str)
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return 0
    
    # ==================== Atomic Operations ====================
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment value atomically"""
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Failed to increment {key}: {e}")
            return 0
    
    def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement value atomically"""
        try:
            return self.client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Failed to decrement {key}: {e}")
            return 0


# ==================== Singleton Instance ====================

_redis_chat_client: Optional[RedisChatClient] = None


def init_redis_chat() -> RedisChatClient:
    """Initialize Redis chat client (call on app startup)"""
    global _redis_chat_client
    
    if _redis_chat_client is None:
        _redis_chat_client = RedisChatClient()
        logger.info("Redis Chat Client initialized")
    
    return _redis_chat_client


def get_redis_chat() -> RedisChatClient:
    """Get Redis chat client instance"""
    global _redis_chat_client
    
    if _redis_chat_client is None:
        _redis_chat_client = init_redis_chat()
    
    return _redis_chat_client
