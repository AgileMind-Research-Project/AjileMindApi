"""
Meeting Schemas - Pydantic Models for Meeting Operations

Defines request/response schemas for:
- Meeting creation and management
- Join requests
- Meeting transcripts
- Participant management
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MeetingStatus(str, Enum):
    """Meeting status"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class JoinRequestStatus(str, Enum):
    """Join request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ==================== Meeting Schemas ====================

class MeetingCreateRequest(BaseModel):
    """Request to create a new meeting"""
    channel_id: str = Field(..., description="Channel ID for the meeting")
    title: Optional[str] = Field(None, description="Meeting title (defaults to channel name)")
    description: Optional[str] = Field(None, description="Meeting description")


class MeetingResponse(BaseModel):
    """Meeting details response"""
    id: str = Field(..., description="Meeting ID")
    channel_id: str = Field(..., description="Associated channel ID")
    title: str = Field(..., description="Meeting title")
    description: Optional[str] = Field(None, description="Meeting description")
    status: MeetingStatus = Field(..., description="Meeting status")
    created_by_user_id: str = Field(..., description="Creator user ID")
    created_by_username: str = Field(..., description="Creator username")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    ended_at: Optional[str] = Field(None, description="End timestamp")
    participant_count: int = Field(default=0, description="Number of active participants")
    participants: List[str] = Field(default_factory=list, description="List of participant user IDs")
    tenant_name: str = Field(..., description="Tenant name")


class MeetingStartRequest(BaseModel):
    """Request to start a meeting"""
    pass  # No additional fields needed, just triggers status change


class MeetingEndRequest(BaseModel):
    """Request to end a meeting"""
    pass  # No additional fields needed


# ==================== Join Request Schemas ====================

class JoinRequestCreateRequest(BaseModel):
    """Request to join a meeting"""
    message: Optional[str] = Field(None, description="Optional message to host")


class JoinRequestResponse(BaseModel):
    """Join request details"""
    id: str = Field(..., description="Request ID")
    meeting_id: str = Field(..., description="Meeting ID")
    user_id: str = Field(..., description="Requesting user ID")
    username: str = Field(..., description="Requesting username")
    message: Optional[str] = Field(None, description="Optional message")
    status: JoinRequestStatus = Field(..., description="Request status")
    created_at: str = Field(..., description="Request timestamp")
    processed_at: Optional[str] = Field(None, description="Processing timestamp")
    processed_by: Optional[str] = Field(None, description="Who processed the request")


class JoinRequestActionRequest(BaseModel):
    """Request to approve/reject join request"""
    action: str = Field(..., description="Action: 'approve' or 'reject'")


# ==================== Participant Schemas ====================

class ParticipantAddRequest(BaseModel):
    """Request to add participant"""
    user_id: str = Field(..., description="User ID to add")
    username: str = Field(..., description="Username")


class ParticipantResponse(BaseModel):
    """Participant details"""
    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    joined_at: str = Field(..., description="Join timestamp")


# ==================== Transcript Schemas ====================

class TranscriptCreateRequest(BaseModel):
    """Request to store meeting transcript"""
    content: str = Field(..., description="Transcript content")
    format: str = Field(default="text", description="Transcript format (text, json, vtt)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TranscriptResponse(BaseModel):
    """Meeting transcript response"""
    meeting_id: str = Field(..., description="Meeting ID")
    content: str = Field(..., description="Transcript content")
    format: str = Field(..., description="Transcript format")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    stored_at: str = Field(..., description="Storage timestamp")
    size_bytes: int = Field(..., description="Transcript size in bytes")


# ==================== List Response Schemas ====================

class MeetingListResponse(BaseModel):
    """List of meetings"""
    meetings: List[MeetingResponse] = Field(default_factory=list)
    total: int = Field(default=0)


class JoinRequestListResponse(BaseModel):
    """List of join requests"""
    requests: List[JoinRequestResponse] = Field(default_factory=list)
    total: int = Field(default=0)


class ParticipantListResponse(BaseModel):
    """List of participants"""
    participants: List[ParticipantResponse] = Field(default_factory=list)
    total: int = Field(default=0)
