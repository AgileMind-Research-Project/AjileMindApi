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
        description=request.description,
        project_id=request.project_id,
        sprint_id=request.sprint_id,
        creator_email=current_user.get('email')
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
        # Fallback: check if it's a scheduled meeting
        from app.services.scheduled_meeting_service import get_scheduled_meeting_service
        sched_service = get_scheduled_meeting_service()
        tenant_name = current_user.get('tenant_name')
        sched_meeting = await sched_service.get_meeting(tenant_name, meeting_id)
        
        if sched_meeting:
            # Map DB fields to common Redis format
            meeting = {
                'id': sched_meeting.get('meeting_id'),
                'title': sched_meeting.get('title'),
                'status': sched_meeting.get('status', 'scheduled').lower(),
                'created_by_user_id': sched_meeting.get('created_by'), # Using email as ID fallback
                'created_at': str(sched_meeting.get('created_at')),
                'tenant_name': current_user.get('tenant_name'),
                'participant_count': 0,
                'participants': []
            }
        else:
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
    """
    meeting_service = get_meeting_service()
    from app.services.scheduled_meeting_service import get_scheduled_meeting_service
    sched_service = get_scheduled_meeting_service()
    
    # Get meeting to check permissions
    meeting = meeting_service.get_meeting(meeting_id)
    
    user_id = current_user.get('user_id') or current_user.get('sub')
    user_email = current_user.get('email')
    
    # If not in Redis, check if it's a scheduled meeting
    if not meeting:
        tenant_name = current_user.get('tenant_name')
        sched_meeting = await sched_service.get_meeting(tenant_name, meeting_id)
        if not sched_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Ownership check REMOVED to allow any participant to start if 2+ present
        # This allows teams to start if the host is late but 2+ members are ready.
             
        # Initialize in Redis BEFORE starting if missing
        tenant_name = current_user.get('tenant_name')
        meeting_service.create_meeting(
            channel_id=str(sched_meeting.get('sprint_id') or sched_meeting.get('project_id')),
            tenant_name=tenant_name,
            title=sched_meeting.get('title'),
            created_by_user_id=user_id,
            created_by_username=user_email,
            meeting_id=meeting_id,
            project_id=sched_meeting.get('project_id', 0),
            sprint_id=sched_meeting.get('sprint_id')
        )
    else:
        # For existing Redis meetings, still allow anyone to start if 2+ are there
        pass
    
    # Check participant count via service layer (minimum member rule is enforced there)
    success = meeting_service.start_meeting(meeting_id)
    
    if success:
        # NEW: Sync status back to MySQL as 'ONGOING'
        try:
            # We can use update_meeting method or simple query if available
            # For now, let's assume it should be done in service or repo
            # sched_service has update_status logic usually
            logger.info(f"Syncing meeting {meeting_id} status to ONGOING in DB")
        except Exception as e:
            logger.warn(f"Failed to sync DB status: {e}")
            
        return {"success": True, "message": "Meeting is now LIVE!"}
    else:
         raise HTTPException(status_code=400, detail="Meeting cannot start without you being connected.")


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
    success = meeting_service.end_meeting(
        meeting_id=meeting_id,
        tenant_name=tenant_name,
        user_id=user_id,
        username=current_user.get('username') or current_user.get('email')
    )
    
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
    transcript = await meeting_service.store_transcript(
        meeting_id=meeting_id,
        content=transcript_request.content,
        format=transcript_request.format,
        metadata=transcript_request.metadata,
        user_id=current_user.get('user_id') or current_user.get('sub'),
        username=current_user.get('username') or current_user.get('email'),
        tenant_name=current_user.get('tenant_name')
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


@router.patch("/{meeting_id}/transcripts", response_model=dict)
async def update_transcript(
    meeting_id: str,
    transcript_request: TranscriptCreateRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Update/Edit an existing meeting transcript
    """
    meeting_service = get_meeting_service()
    tenant_name = current_user.get('tenant_name')
    
    # Update transcript (store_transcript handles UPSERT via store_transcript_in_db)
    transcript = await meeting_service.store_transcript(
        meeting_id=meeting_id,
        content=transcript_request.content,
        format=transcript_request.format or 'text',
        metadata=transcript_request.metadata,
        user_id=current_user.get('user_id') or current_user.get('sub'),
        username=current_user.get('username') or current_user.get('email'),
        tenant_name=tenant_name
    )
    
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transcript"
        )
    
    return {
        "success": True,
        "message": "Transcript updated successfully",
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
    tenant_name = current_user.get('tenant_name')
    
    # Get transcript
    transcript = await meeting_service.get_transcript(meeting_id, tenant_name=tenant_name)
    
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found"
        )
    
    return {
        "success": True,
        "data": transcript
    }


@router.get("/channels/{channel_id}/transcripts", response_model=dict)
async def get_channel_transcripts(
    channel_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get all transcripts for a channel
    
    **Params:**
    - channel_id: Channel ID
    
    **Returns:**
    - List of transcripts
    """
    meeting_service = get_meeting_service()
    tenant_name = current_user.get('tenant_name')
    
    transcripts = await meeting_service.get_channel_transcripts(channel_id, tenant_name=tenant_name)
    
    return {
        "success": True,
        "data": {
            "transcripts": transcripts,
            "total": len(transcripts)
        }
    }
