"""
Redis Chat API - FastAPI Endpoints

Provides REST API for channel and message management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from app.utils.jwt import get_current_user_from_token
from app.services.redis_chat_service import get_redis_chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class CreateChannelRequest(BaseModel):
    """Request to create a new channel"""
    name: str = Field(..., min_length=1, max_length=100, description="Channel name")
    description: str = Field(default="", max_length=500, description="Channel description")
    is_private: bool = Field(default=False, description="Whether channel is private")


class UpdateChannelRequest(BaseModel):
    """Request to update channel"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_private: Optional[bool] = None


class AddMembersRequest(BaseModel):
    """Request to add members to channel"""
    user_ids: List[str] = Field(..., description="List of user IDs to add")
    usernames: List[str] = Field(..., description="List of usernames corresponding to user IDs")


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    content: str = Field(..., min_length=1, max_length=5000, description="Message content")
    message_type: str = Field(default="text", description="Message type (text, file, image, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UpdateMessageRequest(BaseModel):
    """Request to update a message"""
    content: str = Field(..., min_length=1, max_length=5000, description="New message content")


# ==================== Channel Endpoints ====================

@router.post("/channels", status_code=status.HTTP_201_CREATED)
async def create_channel(
    request: CreateChannelRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Create a new channel
    
    **Required Token Claims:**
    - user_id (from sub)
    - username (email or name)
    - tenant_name
    
    **Returns:**
    - Channel data with ID
    """
    chat_service = get_redis_chat_service()
    
    # Extract user info from JWT
    user_id = current_user.get('user_id') or current_user.get('sub')
    username = current_user.get('username') or current_user.get('email')
    tenant_name = current_user.get('tenant_name')
    
    if not all([user_id, username, tenant_name]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required user information in token"
        )
    
    # Create channel
    channel = chat_service.create_channel(
        tenant_name=tenant_name,
        channel_name=request.name,
        created_by_user_id=user_id,
        created_by_username=username,
        description=request.description,
        is_private=request.is_private
    )
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create channel"
        )
    
    return {
        "success": True,
        "message": "Channel created successfully",
        "data": channel
    }


@router.get("/channels")
async def get_channels(
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get all channels for the current user's tenant
    
    **Returns:**
    - List of channels the user is a member of
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    tenant_name = current_user.get('tenant_name')
    
    if not tenant_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant information in token"
        )
    
    # Get user's channels
    channels = chat_service.get_tenant_channels(
        tenant_name=tenant_name,
        user_id=user_id
    )
    
    return {
        "success": True,
        "data": {
            "channels": channels,
            "total": len(channels)
        }
    }


@router.get("/channels/{channel_id}")
async def get_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get channel details
    
    **Params:**
    - channel_id: Channel ID
    
    **Returns:**
    - Channel data
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Get channel
    channel = chat_service.get_channel(channel_id)
    
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Check if user is member
    is_member = chat_service.is_user_in_channel(channel_id, user_id)
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this channel"
        )
    
    return {
        "success": True,
        "data": channel
    }


@router.patch("/channels/{channel_id}")
async def update_channel(
    channel_id: str,
    request: UpdateChannelRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Update channel details
    
    **Params:**
    - channel_id: Channel ID
    
    **Body:**
    - Fields to update
    
    **Returns:**
    - Success status
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Check if channel exists and user is member
    channel = chat_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Check if user is admin (simplified - check against creator for now)
    if channel.get('created_by_user_id') != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel admin can update channel"
        )
    
    # Prepare updates
    updates = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.description is not None:
        updates['description'] = request.description
    if request.is_private is not None:
        updates['is_private'] = request.is_private
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Update channel
    success = chat_service.update_channel(channel_id, updates)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update channel"
        )
    
    return {
        "success": True,
        "message": "Channel updated successfully"
    }


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Delete a channel
    
    **Params:**
    - channel_id: Channel ID
    
    **Returns:**
    - Success status
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    tenant_name = current_user.get('tenant_name')
    
    # Check if channel exists
    channel = chat_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Check if user is admin
    if channel.get('created_by_user_id') != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel admin can delete channel"
        )
    
    # Delete channel
    success = chat_service.delete_channel(tenant_name, channel_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete channel"
        )
    
    return {
        "success": True,
        "message": "Channel deleted successfully"
    }


# ==================== Member Endpoints ====================

@router.post("/channels/{channel_id}/members")
async def add_members(
    channel_id: str,
    request: AddMembersRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Add members to channel
    
    **Params:**
    - channel_id: Channel ID
    
    **Body:**
    - user_ids: List of user IDs to add
    - usernames: List of usernames
    
    **Returns:**
    - Success status
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    tenant_name = current_user.get('tenant_name')
    
    # Validate request
    if len(request.user_ids) != len(request.usernames):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_ids and usernames must have the same length"
        )
    
    # Check if channel exists
    channel = chat_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Check if requester is member
    is_member = chat_service.is_user_in_channel(channel_id, user_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel members can add other members"
        )
    
    # Add members
    added_count = 0
    for uid, uname in zip(request.user_ids, request.usernames):
        success = chat_service.add_user_to_channel(
            tenant_name=tenant_name,
            channel_id=channel_id,
            user_id=uid,
            username=uname,
            role="member"
        )
        if success:
            added_count += 1
    
    return {
        "success": True,
        "message": f"{added_count} member(s) added successfully",
        "data": {
            "added_count": added_count
        }
    }


@router.delete("/channels/{channel_id}/members/{member_user_id}")
async def remove_member(
    channel_id: str,
    member_user_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Remove member from channel
    
    **Params:**
    - channel_id: Channel ID
    - member_user_id: User ID to remove
    
    **Returns:**
    - Success status
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    tenant_name = current_user.get('tenant_name')
    
    # Check if channel exists
    channel = chat_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Check if requester is admin or removing themselves
    if channel.get('created_by_user_id') != user_id and member_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel admin can remove other members"
        )
    
    # Remove member
    success = chat_service.remove_user_from_channel(tenant_name, channel_id, member_user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )
    
    return {
        "success": True,
        "message": "Member removed successfully"
    }


@router.get("/channels/{channel_id}/members")
async def get_members(
    channel_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get all members of a channel
    
    **Params:**
    - channel_id: Channel ID
    
    **Returns:**
    - List of members
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Check if user is member
    is_member = chat_service.is_user_in_channel(channel_id, user_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this channel"
        )
    
    # Get members
    members = chat_service.get_channel_members(channel_id)
    
    return {
        "success": True,
        "data": {
            "members": members,
            "total": len(members)
        }
    }


# ==================== Message Endpoints ====================

@router.post("/channels/{channel_id}/messages")
async def send_message(
    channel_id: str,
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Send a message to channel
    
    **Params:**
    - channel_id: Channel ID
    
    **Body:**
    - content: Message content
    - message_type: Type of message (optional)
    - metadata: Additional metadata (optional)
    
    **Returns:**
    - Message data
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    username = current_user.get('username') or current_user.get('email')
    
    # Check if user is member
    is_member = chat_service.is_user_in_channel(channel_id, user_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this channel"
        )
    
    # Send message
    message = chat_service.send_message(
        channel_id=channel_id,
        user_id=user_id,
        username=username,
        content=request.content,
        message_type=request.message_type,
        metadata=request.metadata
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )
    
    return {
        "success": True,
        "message": "Message sent successfully",
        "data": message
    }


@router.get("/channels/{channel_id}/messages")
async def get_messages(
    channel_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get messages from channel
    
    **Params:**
    - channel_id: Channel ID
    - limit: Number of messages to retrieve (max 100)
    - offset: Offset from the end (for pagination)
    
    **Returns:**
    - List of messages (newest first)
    """
    chat_service = get_redis_chat_service()
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Validate params
    limit = min(limit, 100)  # Max 100 messages
    offset = max(offset, 0)  # Min 0 offset
    
    # Check if user is member
    is_member = chat_service.is_user_in_channel(channel_id, user_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this channel"
        )
    
    # Get messages
    messages = chat_service.get_messages(channel_id, limit=limit, offset=offset)
    
    return {
        "success": True,
        "data": {
            "messages": messages,
            "total": len(messages),
            "limit": limit,
            "offset": offset
        }
    }


@router.patch("/channels/{channel_id}/messages/{message_id}")
async def update_message(
    channel_id: str,
    message_id: str,
    request: UpdateMessageRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Update/edit a message
    
    **Params:**
    - channel_id: Channel ID
    - message_id: Message ID
    
    **Body:**
    - content: New message content
    
    **Returns:**
    - Success status
    """
    chat_service = get_redis_chat_service()
    
    # Note: In production, add check to ensure user owns the message
    
    # Update message
    success = chat_service.update_message(channel_id, message_id, request.content)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or failed to update"
        )
    
    return {
        "success": True,
        "message": "Message updated successfully"
    }


@router.delete("/channels/{channel_id}/messages/{message_id}")
async def delete_message(
    channel_id: str,
    message_id: str,
    soft_delete: bool = True,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Delete a message
    
    **Params:**
    - channel_id: Channel ID
    - message_id: Message ID
    - soft_delete: If true, mark as deleted; if false, remove completely
    
    **Returns:**
    - Success status
    """
    chat_service = get_redis_chat_service()
    
    # Note: In production, add check to ensure user owns the message or is admin
    
    # Delete message
    success = chat_service.delete_message(channel_id, message_id, soft_delete=soft_delete)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or failed to delete"
        )
    
    return {
        "success": True,
        "message": "Message deleted successfully"
    }
