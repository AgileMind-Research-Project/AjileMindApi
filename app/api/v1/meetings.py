"""
Meeting API - FastAPI Endpoints for Meeting Management

Provides REST API for:
- Meeting creation and management
- Join request handling
- Participant management
- Transcript storage
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from app.utils.jwt import get_current_user_from_token
from app.services.meeting_service import get_meeting_service
from app.schemas.meeting_schemas import (
    MeetingCreateRequest,
    MeetingResponse,
    MeetingStartRequest,
    MeetingEndRequest,
    MeetingListResponse,
    JoinRequestCreateRequest,
    JoinRequestResponse,
    JoinRequestActionRequest,
    JoinRequestListResponse,
    ParticipantAddRequest,
    ParticipantResponse,
    ParticipantListResponse,
    TranscriptCreateRequest,
    TranscriptResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Meeting Endpoints ====================

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    request: MeetingCreateRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Create an instant meeting (Meet Now)
    
    **Required Token Claims:**
    - user_id (from sub)
    - username (email or name)
    - tenant_name
    
    **Returns:**
    - Meeting data with ID and details
    """
    meeting_service = get_meeting_service()
    
    # Extract user info from JWT
    user_id = current_user.get('user_id') or current_user.get('sub')
    username = current_user.get('username') or current_user.get('email')
    tenant_name = current_user.get('tenant_name')
    
    if not all([user_id, username, tenant_name]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required user information in token"
        )
    
    # Create meeting
    meeting = meeting_service.create_meeting(
        channel_id=request.channel_id,
        tenant_name=tenant_name,
        created_by_user_id=user_id,
        created_by_username=username,
        title=request.title,
        description=request.description
    )
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create meeting"
        )
    
    return {
        "success": True,
        "message": "Meeting created successfully",
        "data": meeting
    }


@router.get("/{meeting_id}", response_model=dict)
async def get_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get meeting details
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Returns:**
    - Meeting data
    """
    meeting_service = get_meeting_service()
    
    meeting = meeting_service.get_meeting(meeting_id)
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    return {
        "success": True,
        "data": meeting
    }


@router.patch("/{meeting_id}/start", response_model=dict)
async def start_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Start a meeting (change status to live)
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Returns:**
    - Success status
    """
    meeting_service = get_meeting_service()
    
    # Get meeting to check permissions
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Only creator can start meeting
    if meeting.get('created_by_user_id') != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only meeting creator can start the meeting"
        )
    
    # Start meeting
    success = meeting_service.start_meeting(meeting_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start meeting"
        )
    
    return {
        "success": True,
        "message": "Meeting started successfully"
    }


@router.patch("/{meeting_id}/end", response_model=dict)
async def end_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    End a meeting
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Returns:**
    - Success status
    """
    meeting_service = get_meeting_service()
    
    # Get meeting to check permissions
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    tenant_name = current_user.get('tenant_name')
    
    # Only creator can end meeting
    if meeting.get('created_by_user_id') != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only meeting creator can end the meeting"
        )
    
    # End meeting
    success = meeting_service.end_meeting(meeting_id, tenant_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end meeting"
        )
    
    return {
        "success": True,
        "message": "Meeting ended successfully"
    }


# ==================== Channel Meeting Endpoints ====================

@router.get("/channels/{channel_id}/meetings", response_model=dict)
async def get_channel_meetings(
    channel_id: str,
    include_ended: bool = False,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get all meetings for a channel
    
    **Params:**
    - channel_id: Channel ID
    - include_ended: Include ended meetings (default: False)
    
    **Returns:**
    - List of meetings
    """
    meeting_service = get_meeting_service()
    
    meetings = meeting_service.get_channel_meetings(channel_id, include_ended)
    
    return {
        "success": True,
        "data": {
            "meetings": meetings,
            "total": len(meetings)
        }
    }


# ==================== Join Request Endpoints ====================

@router.post("/{meeting_id}/join-requests", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_join_request(
    meeting_id: str,
    request: JoinRequestCreateRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Request to join a meeting
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Body:**
    - message: Optional message to host
    
    **Returns:**
    - Join request data
    """
    meeting_service = get_meeting_service()
    
    # Check if meeting exists
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    username = current_user.get('username') or current_user.get('email')
    
    # Create join request
    join_request = meeting_service.create_join_request(
        meeting_id=meeting_id,
        user_id=user_id,
        username=username,
        message=request.message
    )
    
    if not join_request:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create join request"
        )
    
    return {
        "success": True,
        "message": "Join request created successfully",
        "data": join_request
    }


@router.get("/{meeting_id}/join-requests", response_model=dict)
async def get_join_requests(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get pending join requests for a meeting
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Returns:**
    - List of pending join requests
    """
    meeting_service = get_meeting_service()
    
    # Check if meeting exists
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Only meeting creator can see join requests
    if meeting.get('created_by_user_id') != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only meeting creator can view join requests"
        )
    
    # Get pending requests
    requests = meeting_service.get_pending_requests(meeting_id)
    
    return {
        "success": True,
        "data": {
            "requests": requests,
            "total": len(requests)
        }
    }


@router.patch("/{meeting_id}/join-requests/{request_id}", response_model=dict)
async def process_join_request(
    meeting_id: str,
    request_id: str,
    action_request: JoinRequestActionRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Approve or reject a join request
    
    **Params:**
    - meeting_id: Meeting ID
    - request_id: Join request ID
    
    **Body:**
    - action: 'approve' or 'reject'
    
    **Returns:**
    - Success status
    """
    meeting_service = get_meeting_service()
    
    # Check if meeting exists
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Only meeting creator can process requests
    if meeting.get('created_by_user_id') != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only meeting creator can process join requests"
        )
    
    # Validate action
    if action_request.action not in ['approve', 'reject']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'"
        )
    
    # Process request
    success = meeting_service.process_join_request(
        meeting_id=meeting_id,
        request_id=request_id,
        action=action_request.action,
        processed_by=user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process join request"
        )
    
    action_message = "approved" if action_request.action == "approve" else "rejected"
    
    return {
        "success": True,
        "message": f"Join request {action_message} successfully"
    }


# ==================== Participant Endpoints ====================

@router.post("/{meeting_id}/participants", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_participant(
    meeting_id: str,
    participant_request: ParticipantAddRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Add participant to meeting (direct add, bypasses join request)
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Body:**
    - user_id: User ID to add
    - username: Username
    
    **Returns:**
    - Success status
    """
    meeting_service = get_meeting_service()
    
    # Check if meeting exists
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Add participant
    success = meeting_service.add_participant(
        meeting_id=meeting_id,
        user_id=participant_request.user_id,
        username=participant_request.username
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add participant"
        )
    
    return {
        "success": True,
        "message": "Participant added successfully"
    }


@router.delete("/{meeting_id}/participants/{user_id}", response_model=dict)
async def remove_participant(
    meeting_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Remove participant from meeting
    
    **Params:**
    - meeting_id: Meeting ID
    - user_id: User ID to remove
    
    **Returns:**
    - Success status
    """
    meeting_service = get_meeting_service()
    
    # Check if meeting exists
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    current_user_id = current_user.get('user_id') or current_user.get('sub')
    
    # Can remove self or meeting creator can remove anyone
    if user_id != current_user_id and meeting.get('created_by_user_id') != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove yourself or be the meeting creator"
        )
    
    # Remove participant
    success = meeting_service.remove_participant(meeting_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove participant"
        )
    
    return {
        "success": True,
        "message": "Participant removed successfully"
    }


@router.get("/{meeting_id}/participants", response_model=dict)
async def get_participants(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get all participants in a meeting
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Returns:**
    - List of participants
    """
    meeting_service = get_meeting_service()
    
    # Check if meeting exists
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Get participants
    participants = meeting_service.get_participants(meeting_id)
    
    return {
        "success": True,
        "data": {
            "participants": participants,
            "total": len(participants)
        }
    }


# ==================== Transcript Endpoints ====================

@router.post("/{meeting_id}/transcripts", response_model=dict, status_code=status.HTTP_201_CREATED)
async def store_transcript(
    meeting_id: str,
    transcript_request: TranscriptCreateRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Store meeting transcript
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Body:**
    - content: Transcript content
    - format: Transcript format (text, json, vtt)
    - metadata: Additional metadata
    
    **Returns:**
    - Transcript data
    """
    meeting_service = get_meeting_service()
    
    # Check if meeting exists
    meeting = meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Store transcript
    transcript = meeting_service.store_transcript(
        meeting_id=meeting_id,
        content=transcript_request.content,
        format=transcript_request.format,
        metadata=transcript_request.metadata
    )
    
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store transcript"
        )
    
    return {
        "success": True,
        "message": "Transcript stored successfully",
        "data": transcript
    }


@router.get("/{meeting_id}/transcripts", response_model=dict)
async def get_transcript(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get meeting transcript
    
    **Params:**
    - meeting_id: Meeting ID
    
    **Returns:**
    - Transcript data
    """
    meeting_service = get_meeting_service()
    
    # Get transcript
    transcript = meeting_service.get_transcript(meeting_id)
    
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found"
        )
    
    return {
        "success": True,
        "data": transcript
    }
