"""
Scheduled Meetings API — FastAPI Endpoints

Saves structured meetings to the `meetings` MySQL table.
Meeting category is validated against the Scrum ceremony list.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.utils.jwt import get_current_user_from_token
from app.services.scheduled_meeting_service import get_scheduled_meeting_service
from app.schemas.scheduled_meeting_schemas import (
    ScheduleMeetingRequest,
    UpdateMeetingStatusRequest,
    UpdateMeetingAttendeesRequest,
    ExtendMeetingRequest,
    SCRUM_MEETING_CATEGORIES,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Utility endpoint ──────────────────────────────────────────────────────────

@router.get("/categories", response_model=dict)
async def get_meeting_categories(
    current_user: dict = Depends(get_current_user_from_token),
):
    """Return all available Scrum meeting category options for the UI dropdown."""
    return {
        "success": True,
        "data": {"categories": SCRUM_MEETING_CATEGORIES},
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_scheduled_meeting(
    request: ScheduleMeetingRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Schedule a new meeting and persist it to the `meetings` table.

    **Required Token Claims:** tenant_name, username/email
    """
    svc = get_scheduled_meeting_service()

    tenant_name = current_user.get("tenant_name")
    created_by = current_user.get("username") or current_user.get("email")

    if not tenant_name or not created_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant_name or user identity in token",
        )

    meeting = await svc.schedule_meeting(
        tenant_name=tenant_name,
        project_id=request.project_id,
        sprint_id=request.sprint_id,
        title=request.title,
        meeting_category=request.meeting_category,
        meeting_date=request.meeting_date,
        start_time=request.start_time,
        end_time=request.end_time,
        meeting_link=request.meeting_link,
        created_by=created_by,
        attendees=request.attendees,
    )

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule meeting",
        )

    return {
        "success": True,
        "message": "Meeting scheduled successfully",
        "data": meeting,
    }


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/project/{project_id}", response_model=dict)
async def get_meetings_by_project(
    project_id: int,
    current_user: dict = Depends(get_current_user_from_token),
):
    """List all scheduled meetings for a project."""
    svc = get_scheduled_meeting_service()
    tenant_name = current_user.get("tenant_name")

    if not tenant_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant information in token",
        )

    meetings = await svc.get_meetings_by_project(tenant_name, project_id)

    return {
        "success": True,
        "data": {"meetings": meetings, "total": len(meetings)},
    }


@router.get("/sprint/{project_id}/{sprint_id}", response_model=dict)
async def get_meetings_by_sprint(
    project_id: int,
    sprint_id: int,
    current_user: dict = Depends(get_current_user_from_token),
):
    """List all scheduled meetings for a sprint."""
    svc = get_scheduled_meeting_service()
    tenant_name = current_user.get("tenant_name")

    if not tenant_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant information in token",
        )

    meetings = await svc.get_meetings_by_sprint(tenant_name, project_id, sprint_id)

    return {
        "success": True,
        "data": {"meetings": meetings, "total": len(meetings)},
    }


@router.get("/{meeting_id}", response_model=dict)
async def get_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Get a single scheduled meeting by ID."""
    svc = get_scheduled_meeting_service()
    tenant_name = current_user.get("tenant_name")

    meeting = await svc.get_meeting(tenant_name, meeting_id)

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    return {"success": True, "data": meeting}


# ── Update status ─────────────────────────────────────────────────────────────

@router.patch("/{meeting_id}/status", response_model=dict)
async def update_meeting_status(
    meeting_id: str,
    body: UpdateMeetingStatusRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Update the status of a scheduled meeting."""
    svc = get_scheduled_meeting_service()
    tenant_name = current_user.get("tenant_name")

    # Verify meeting exists
    meeting = await svc.get_meeting(tenant_name, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    success = await svc.update_status(tenant_name, meeting_id, body.status)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update meeting status",
        )

    return {"success": True, "message": f"Meeting status updated to {body.status}"}


@router.patch("/{meeting_id}/attendees", response_model=dict)
async def update_meeting_attendees(
    meeting_id: str,
    body: UpdateMeetingAttendeesRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Update the attendee list for a scheduled meeting."""
    svc = get_scheduled_meeting_service()
    tenant_name = current_user.get("tenant_name")

    # Verify meeting exists
    meeting = await svc.get_meeting(tenant_name, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    success = await svc.update_attendees(tenant_name, meeting_id, body.attendees)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update meeting attendees",
        )

    return {"success": True, "message": "Meeting attendees updated successfully"}


@router.patch("/{meeting_id}/extend", response_model=dict)
async def extend_meeting(
    meeting_id: str,
    body: ExtendMeetingRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Extend the end time of a scheduled meeting."""
    svc = get_scheduled_meeting_service()
    tenant_name = current_user.get("tenant_name")

    # Verify meeting exists
    meeting = await svc.get_meeting(tenant_name, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    success = await svc.extend_meeting(tenant_name, meeting_id, body.new_end_time)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend meeting time",
        )

    return {"success": True, "message": f"Meeting extended until {body.new_end_time}"}


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{meeting_id}", response_model=dict)
async def delete_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Delete a scheduled meeting. Only the creator can delete."""
    svc = get_scheduled_meeting_service()
    tenant_name = current_user.get("tenant_name")
    current_email = current_user.get("username") or current_user.get("email")

    meeting = await svc.get_meeting(tenant_name, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    # Only creator or admin can delete
    roles = current_user.get("roles", [])
    is_admin = any(r in roles for r in ("SUPER_ADMIN", "ADMIN", "PROJECT_MANAGER"))
    if meeting.get("created_by") != current_email and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the meeting creator can delete this meeting",
        )

    success = await svc.delete_meeting(tenant_name, meeting_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete meeting",
        )

    return {"success": True, "message": "Meeting deleted successfully"}
