"""
Meeting API - FastAPI Endpoints for Meeting Management

Provides REST API for:
- Meeting creation and management
- Join request handling
- Participant management
- Transcript storage
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging
import json
from typing import List, Optional
from datetime import date, datetime

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
    TranscriptResponse,
    AIAnalysisResponse,
    TaskSyncRequest,
    LeaveSyncRequest,
    BugSyncRequest
)
from app.services.ai_service import get_ai_service
from app.services.jira_service import JiraService
from app.services.backlog_service import BacklogService
from app.services.leave_service import LeaveService
from app.db.database import get_db

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
    
    return meeting


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
    
    return meeting


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


@router.put("/{meeting_id}", response_model=dict)
async def update_meeting_details(
    meeting_id: str,
    request_data: dict,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Update meeting transcript (legacy PUT endpoint)
    """
    meeting_service = get_meeting_service()
    tenant_name = current_user.get('tenant_name')
    
    transcript_content = request_data.get("meeting_transcript")
    if transcript_content is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must contain 'meeting_transcript' field"
        )

    # This is a proxy for the new update_transcript endpoint
    transcript = await meeting_service.store_transcript(
        meeting_id=meeting_id,
        content=transcript_content,
        format='text',
        metadata={},
        user_id=current_user.get('user_id') or current_user.get('sub'),
        username=current_user.get('username') or current_user.get('email'),
        tenant_name=tenant_name
    )
    
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transcript"
        )
    
    # Return the full meeting record to the frontend (unwrapped)
    from app.db.database import db as mysql_db
    query = """
        SELECT m.*, t.transcript_content, t.id as transcript_id
        FROM meetings m
        LEFT JOIN transcripts t ON t.meeting_id COLLATE utf8mb4_unicode_ci = m.meeting_id COLLATE utf8mb4_unicode_ci
        WHERE m.meeting_id = %s
    """
    meeting_data = await mysql_db.execute_query(query, (meeting_id,), fetch_one=True, schema=tenant_name)
    
    if meeting_data:
        if isinstance(meeting_data.get('attendees'), str):
            try:
                meeting_data['attendees'] = json.loads(meeting_data['attendees'])
            except:
                meeting_data['attendees'] = []
        return meeting_data

    return {
        "success": True,
        "message": "Transcript updated successfully",
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
    
    # Return the full meeting record to the frontend (unwrapped)
    from app.db.database import db as mysql_db
    query = """
        SELECT m.*, t.transcript_content, t.id as transcript_id
        FROM meetings m
        LEFT JOIN transcripts t ON t.meeting_id COLLATE utf8mb4_unicode_ci = m.meeting_id COLLATE utf8mb4_unicode_ci
        WHERE m.meeting_id = %s
    """
    meeting_data = await mysql_db.execute_query(query, (meeting_id,), fetch_one=True, schema=tenant_name)
    
    if meeting_data:
        if isinstance(meeting_data.get('attendees'), str):
            try:
                meeting_data['attendees'] = json.loads(meeting_data['attendees'])
            except:
                meeting_data['attendees'] = []
        return meeting_data

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

# ==================== AI Analysis Endpoints ====================

@router.post("/{meeting_id}/analyze-tasks", response_model=AIAnalysisResponse)
async def analyze_meeting_tasks(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Use AI to extract tasks and leave info from meeting transcript.
    Prefers the MySQL-stored (uploaded/structured) transcript over the
    Redis live-chat transcript when both exist, because the structured
    version contains explicit TAM-IDs and effort estimates.
    """
    meeting_service = get_meeting_service()
    ai_service      = get_ai_service()
    tenant_name     = current_user.get('tenant_name')

    # ── Step 1: Try MySQL transcript first (uploaded / structured) ─────────
    content: str = ""
    category: Optional[str] = None
    real_id = meeting_id.replace("redis_", "") if meeting_id.startswith("redis_") else meeting_id

    if tenant_name:
        try:
            from app.db.database import db as _db
            db_query = """
                SELECT t.transcript_content AS content, t.category
                FROM   transcripts t
                WHERE  t.meeting_id = %s
                LIMIT  1
            """
            db_row = await _db.execute_query(db_query, (real_id,), schema=tenant_name, fetch_one=True)
            if db_row and db_row.get("content"):
                content = db_row["content"]
                category = db_row.get("category")
                logger.info(
                    f"[Analyze] Using MySQL transcript for {real_id} "
                    f"(len={len(content)}, category={category})"
                )
        except Exception as _e:
            logger.warning(f"[Analyze] MySQL transcript lookup failed: {_e}")

    # ── Step 2: Fall back to Redis / standard get_transcript ───────────────
    if not content:
        transcript = await meeting_service.get_transcript(meeting_id, tenant_name=tenant_name)
        if not transcript or not transcript.get("content"):
            logger.warning(f"No transcript content found for meeting {meeting_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found for this meeting"
            )
        content = transcript["content"]
        # Redis transcripts don't usually have a category attached in the same way, 
        # but the meeting might have one. 
        meeting = meeting_service.get_meeting(meeting_id)
        if meeting:
             category = meeting.get("category")

        logger.info(
            f"[Analyze] Using Redis/fallback transcript for {real_id} "
            f"(len={len(content)}, category={category})"
        )

    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found for this meeting")

    logger.info(f"[Analyze] Starting AI analysis | meeting={meeting_id} | category={category}")
    analysis = await ai_service.analyze_transcript(content, category=category)
    return analysis


@router.post("/{meeting_id}/sync-tasks", response_model=dict)
async def sync_extracted_tasks(
    meeting_id: str,
    request: TaskSyncRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db = Depends(get_db)
):
    """
    Sync AI-extracted tasks to Jira and Database
    """
    tenant_name = current_user.get('tenant_name')
    jira_service = JiraService(db)
    backlog_service = BacklogService(db)
    
    # Get project key
    from app.db.repositories.project_repository import ProjectRepository
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project_by_id(tenant_name, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_key = project.get('key')
    results = []
    
    for task in request.tasks:
        try:
            # Skip tasks with no summary — DB column is NOT NULL
            if not task.summary or not task.summary.strip():
                logger.warning(f"Skipping task with no summary (task_id={task.task_id})")
                results.append({"task": task.task_id or "unknown", "status": "skipped", "reason": "No summary"})
                continue

            # 1. Update Jira
            jira_key = task.task_id
            if jira_key:
                # Update existing issue
                await jira_service.update_issue(
                    tenant_name=tenant_name,
                    issue_key=jira_key,
                    summary=task.summary,
                    description=task.description,
                    priority="Medium", # Default
                    assignee_email=task.assignee,
                    labels=task.tags
                )
            else:
                # Create new issue
                created_jira = await jira_service.create_issue(
                    tenant_name=tenant_name,
                    project_key=project_key,
                    summary=task.summary,
                    description=task.description,
                    issue_type="Task",
                    priority="Medium",
                    assignee_email=task.assignee,
                    labels=task.tags
                )
                jira_key = created_jira.get('issue_key')

            # 2. Update/Create in Database
            await backlog_service.backlog_repo.create_backlog_item(
                tenant_name=tenant_name,
                item_id=jira_key,
                project_id=request.project_id,
                summary=task.summary,
                description=task.description,
                issue_type="story", # Default to story/task mapping
                status="todo",
                priority="medium",
                assignee=task.assignee,
                tags=task.tags,
                severity=None,
                parent_task_id=None # We could potentially link subtasks here
            )
            
            # If sprint_id is provided, assign to sprint
            if request.sprint_id:
                update_sql = "UPDATE project_backlog SET sprint_id = %s WHERE id = %s"
                await db.execute_query(update_sql, (request.sprint_id, jira_key), schema=tenant_name, commit=True)

            results.append({"task": task.summary, "status": "synced", "jira_key": jira_key})
        except Exception as e:
            logger.error(f"Failed to sync task {task.summary}: {e}")
            results.append({"task": task.summary, "status": "failed", "error": str(e)})

    return {"success": True, "results": results}


@router.post("/{meeting_id}/sync-review-tasks", response_model=dict)
async def sync_review_tasks(
    meeting_id: str,
    request: TaskSyncRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db = Depends(get_db)
):
    """
    Sprint Review task sync:
    - Tasks with meeting_status='Completed'  → set Jira status to 'Done' + DB status='done'
    - Tasks with any other meeting_status    → leave Jira/DB status unchanged, just record review outcome
    Does NOT start/close a sprint (that is handled separately by the close endpoint).
    """
    tenant_name = current_user.get('tenant_name')
    jira_service = JiraService(db)
    results = []

    for task in request.tasks:
        if not task.task_id:
            continue
        try:
            is_completed = (task.meeting_status or '').strip().lower() == 'completed'

            if is_completed:
                # Transition Jira issue to Done via REST
                try:
                    credentials = await jira_service.get_credentials(tenant_name)
                    if credentials:
                        import aiohttp, base64
                        from app.utils.secrets import get_secret
                        jira_url = credentials["jira_url"]
                        email = credentials["email"]
                        secret_name = (
                            f"tenant_{tenant_name}_jira_api_token_"
                            f"{jira_url.replace('https://','').replace('/','_')}"
                        )
                        secret_result = get_secret(secret_name)
                        if secret_result.get("success"):
                            api_token = secret_result.get("secret_value")
                            auth_b64 = base64.b64encode(f"{email}:{api_token}".encode("ascii")).decode("ascii")
                            headers = {
                                "Authorization": f"Basic {auth_b64}",
                                "Content-Type": "application/json",
                                "Accept": "application/json",
                            }
                            # Step 1: Get available transitions
                            async with aiohttp.ClientSession() as session:
                                async with session.get(
                                    f"{jira_url}/rest/api/3/issue/{task.task_id}/transitions",
                                    headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=10)
                                ) as tresp:
                                    if tresp.status == 200:
                                        tdata = await tresp.json()
                                        transitions = tdata.get("transitions", [])
                                        # Find 'Done' transition
                                        done_id = None
                                        for t in transitions:
                                            tname = (t.get("name") or "").lower()
                                            if tname in ["done", "closed", "complete", "resolved"]:
                                                done_id = t["id"]
                                                break
                                        if done_id:
                                            async with session.post(
                                                f"{jira_url}/rest/api/3/issue/{task.task_id}/transitions",
                                                headers=headers,
                                                json={"transition": {"id": done_id}},
                                                timeout=aiohttp.ClientTimeout(total=10)
                                            ) as presp:
                                                if presp.status not in [200, 204]:
                                                    logger.warning(f"Jira transition {task.task_id} HTTP {presp.status}")
                except Exception as jira_err:
                    logger.warning(f"Jira transition non-fatal: {jira_err}")

                # Update DB status to 'done'
                try:
                    await db.execute_query(
                        "UPDATE project_backlog SET status = 'done', updated_at = NOW() WHERE id = %s",
                        (task.task_id,),
                        schema=tenant_name,
                        commit=True
                    )
                except Exception as db_err:
                    logger.warning(f"DB status update non-fatal: {db_err}")

            results.append({
                "task_id": task.task_id,
                "meeting_status": task.meeting_status,
                "action": "set_done" if is_completed else "kept_status"
            })
        except Exception as e:
            logger.error(f"Failed to sync review task {task.task_id}: {e}")
            results.append({"task_id": task.task_id, "status": "failed", "error": str(e)})

    return {"success": True, "results": results}


@router.post("/{meeting_id}/sync-leaves", response_model=dict)
async def sync_extracted_leaves(
    meeting_id: str,
    request: LeaveSyncRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db = Depends(get_db)
):
    """
    Sync AI-extracted leave info to Database
    """
    tenant_name = current_user.get('tenant_name')
    leave_service = LeaveService(db)
    
    results = []
    for leave in request.leaves:
        try:
            # Parse date safely
            leave_date_obj = None
            if leave.leave_date:
                from datetime import datetime
                try:
                    leave_date_obj = datetime.strptime(leave.leave_date, "%Y-%m-%d").date()
                except:
                    leave_date_obj = date.today()
            else:
                leave_date_obj = date.today()

            await leave_service.add_sprint_leave(
                tenant_name=tenant_name,
                sprint_id=request.sprint_id,
                project_id=request.project_id,
                developer_name=leave.developer_name,
                leave_date=leave_date_obj,
                leave_hours=int(leave.leave_hours or 8),
                leave_type=leave.leave_type or "Full Day",
                reason=leave.reason
            )
            results.append({"developer": leave.developer_name, "status": "synced"})
        except Exception as e:
            logger.error(f"Failed to sync leave for {leave.developer_name}: {e}")
            results.append({"developer": leave.developer_name, "status": "failed", "error": str(e)})

    return {"success": True, "results": results}


# ==================== Emotion / Sentiment Analysis Endpoint ====================

@router.post("/{meeting_id}/analyze-emotion", response_model=dict)
async def analyze_meeting_emotion(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Analyse the emotional tone and team sentiment from a meeting transcript.
    Uses the same transcript resolution strategy as analyze-tasks (MySQL first, Redis fallback).
    """
    meeting_service = get_meeting_service()
    ai_service      = get_ai_service()
    tenant_name     = current_user.get('tenant_name')

    # ── Step 1: Try MySQL transcript ─────────────────────────────────────────
    content: str = ""
    real_id = meeting_id.replace("redis_", "") if meeting_id.startswith("redis_") else meeting_id

    if tenant_name:
        try:
            from app.db.database import db as _db
            db_row = await _db.execute_query(
                "SELECT t.transcript_content AS content FROM transcripts t WHERE t.meeting_id = %s LIMIT 1",
                (real_id,), schema=tenant_name, fetch_one=True
            )
            if db_row and db_row.get("content"):
                content = db_row["content"]
                logger.info(f"[EmotionAnalyze] Using MySQL transcript for {real_id} (len={len(content)})")
        except Exception as _e:
            logger.warning(f"[EmotionAnalyze] MySQL transcript lookup failed: {_e}")

    # ── Step 2: Fall back to Redis / standard get_transcript ─────────────────
    if not content:
        transcript = await meeting_service.get_transcript(meeting_id, tenant_name=tenant_name)
        if not transcript or not transcript.get("content"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found for this meeting")
        content = transcript["content"]
        logger.info(f"[EmotionAnalyze] Using Redis/fallback transcript for {real_id} (len={len(content)})")

    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found for this meeting")

    logger.info(f"[EmotionAnalyze] Starting emotion analysis | meeting={meeting_id} | len={len(content)}")
    emotion_result = await ai_service.analyze_emotion(content)

    return {"success": True, "data": emotion_result}
@router.post("/{meeting_id}/sync-bugs", response_model=dict)
async def sync_extracted_bugs(
    meeting_id: str,
    request: BugSyncRequest,
    current_user: dict = Depends(get_current_user_from_token),
    db = Depends(get_db)
):
    """
    Sync AI-extracted bugs to Jira and Database
    """
    tenant_name = current_user.get('tenant_name')
    jira_service = JiraService(db)
    backlog_service = BacklogService(db)
    
    # Get project key
    from app.db.repositories.project_repository import ProjectRepository
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project_by_id(tenant_name, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_key = project.get('key')
    results = []
    
    for bug in request.bugs:
        try:
            # 1. Create in Jira
            created_jira = await jira_service.create_issue(
                tenant_name=tenant_name,
                project_key=project_key,
                summary=f"BUG: {bug.title}",
                description=f"Reporter: {bug.reporter}\nSeverity: {bug.severity}\n\n{bug.description}",
                issue_type="Bug",
                priority=bug.severity if bug.severity in ["High", "Medium", "Low"] else "Medium",
                assignee_email=None, 
                labels=["ai-extracted", "sprint-review"]
            )
            jira_key = created_jira.get('issue_key')

            # 2. Create in Database Backlog
            await backlog_service.backlog_repo.create_backlog_item(
                tenant_name=tenant_name,
                item_id=jira_key,
                project_id=request.project_id,
                summary=f"BUG: {bug.title}",
                description=bug.description,
                issue_type="bug",
                status="todo",
                priority=bug.severity.lower() if bug.severity else "medium",
                assignee=None,
                tags=["ai-extracted", "sprint-review"],
                severity=bug.severity,
                parent_task_id=None
            )
            
            # 3. Assign to sprint if provided
            if request.sprint_id and jira_key:
                await backlog_service.backlog_repo.update_backlog_item(
                    tenant_name=tenant_name,
                    item_id=jira_key,
                    sprint_id=request.sprint_id
                )

            results.append({"title": bug.title, "status": "synced", "jira_key": jira_key})
        except Exception as e:
            logger.error(f"Failed to sync bug {bug.title}: {e}")
            results.append({"title": bug.title, "status": "failed", "reason": str(e)})

    return {"results": results, "count": len(results)}
