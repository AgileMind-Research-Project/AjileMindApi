"""
Meeting API Routes
Handles meeting management operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import uuid

from app.schemas.meeting_schemas import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
    MeetingListResponse,
    MeetingActionResponse,
    MeetingStatus,
    MeetingType
)
from app.middleware.auth import get_current_user, get_tenant_db
from app.db.database import get_db_connection

router = APIRouter(prefix="/meetings", tags=["Meetings"])


def get_user_name(user_id: str, tenant_db: str) -> Optional[str]:
    """Get user name from user ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Extract domain from tenant_db (e.g., "visionexdigital_db" -> "visionexdigital")
        domain = tenant_db.replace("_db", "")
        
        cursor.execute(f"""
            SELECT first_name, last_name, email 
            FROM agilemind_db.`{domain}` 
            WHERE user_id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            return name if name else user.get('email')
        return None
    except Exception:
        return None


@router.post("/", response_model=MeetingActionResponse, status_code=201)
async def create_meeting(
    meeting_data: MeetingCreate,
    current_user: dict = Depends(get_current_user),
    tenant_db: str = Depends(get_tenant_db)
):
    """Create a new meeting"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        meeting_id = f"meeting-{uuid.uuid4()}"
        
        # Insert meeting
        cursor.execute(f"""
            INSERT INTO `{tenant_db}`.meetings (
                id, title, description, meeting_type, scheduled_date,
                duration_minutes, location, is_virtual, meeting_link,
                status, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            meeting_id,
            meeting_data.title,
            meeting_data.description,
            meeting_data.meeting_type.value,
            meeting_data.scheduled_date,
            meeting_data.duration_minutes,
            meeting_data.location,
            meeting_data.is_virtual,
            meeting_data.meeting_link,
            MeetingStatus.SCHEDULED.value,
            current_user['user_id']
        ))
        
        # Insert participants
        if meeting_data.participant_ids:
            participant_values = [
                (f"participant-{uuid.uuid4()}", meeting_id, user_id, False)
                for user_id in meeting_data.participant_ids
            ]
            cursor.executemany(f"""
                INSERT INTO `{tenant_db}`.meeting_participants (id, meeting_id, user_id, attended)
                VALUES (%s, %s, %s, %s)
            """, participant_values)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return MeetingActionResponse(
            success=True,
            message="Meeting created successfully",
            data={"id": meeting_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create meeting: {str(e)}")


@router.get("/", response_model=MeetingListResponse)
async def list_meetings(
    meeting_type: Optional[MeetingType] = None,
    status: Optional[MeetingStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    tenant_db: str = Depends(get_tenant_db)
):
    """List all meetings with optional filters"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Build query
        where_clauses = []
        params = []
        
        if meeting_type:
            where_clauses.append("meeting_type = %s")
            params.append(meeting_type.value)
        
        if status:
            where_clauses.append("status = %s")
            params.append(status.value)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Get total count
        cursor.execute(f"""
            SELECT COUNT(*) as total
            FROM `{tenant_db}`.meetings
            {where_sql}
        """, params)
        total = cursor.fetchone()['total']
        
        # Get paginated meetings
        offset = (page - 1) * page_size
        cursor.execute(f"""
            SELECT *
            FROM `{tenant_db}`.meetings
            {where_sql}
            ORDER BY scheduled_date DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        meetings = cursor.fetchall()
        
        # Get participants for each meeting
        meeting_responses = []
        for meeting in meetings:
            cursor.execute(f"""
                SELECT id, user_id, attended
                FROM `{tenant_db}`.meeting_participants
                WHERE meeting_id = %s
            """, (meeting['id'],))
            
            participants = cursor.fetchall()
            participant_list = [
                {
                    "id": p['id'],
                    "user_id": p['user_id'],
                    "attended": p['attended'],
                    "name": get_user_name(p['user_id'], tenant_db),
                    "email": None
                }
                for p in participants
            ]
            
            meeting_responses.append(MeetingResponse(
                id=meeting['id'],
                title=meeting['title'],
                description=meeting['description'],
                meeting_type=meeting['meeting_type'],
                scheduled_date=meeting['scheduled_date'],
                duration_minutes=meeting['duration_minutes'],
                location=meeting['location'],
                is_virtual=meeting['is_virtual'],
                meeting_link=meeting['meeting_link'],
                status=meeting['status'],
                participants=participant_list,
                created_by=meeting['created_by'],
                created_at=meeting['created_at'],
                updated_at=meeting['updated_at'],
                started_at=meeting.get('started_at'),
                ended_at=meeting.get('ended_at')
            ))
        
        cursor.close()
        conn.close()
        
        total_pages = (total + page_size - 1) // page_size
        
        return MeetingListResponse(
            meetings=meeting_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch meetings: {str(e)}")


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_db: str = Depends(get_tenant_db)
):
    """Get meeting by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"""
            SELECT *
            FROM `{tenant_db}`.meetings
            WHERE id = %s
        """, (meeting_id,))
        
        meeting = cursor.fetchone()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Get participants
        cursor.execute(f"""
            SELECT id, user_id, attended
            FROM `{tenant_db}`.meeting_participants
            WHERE meeting_id = %s
        """, (meeting_id,))
        
        participants = cursor.fetchall()
        participant_list = [
            {
                "id": p['id'],
                "user_id": p['user_id'],
                "attended": p['attended'],
                "name": get_user_name(p['user_id'], tenant_db),
                "email": None
            }
            for p in participants
        ]
        
        cursor.close()
        conn.close()
        
        return MeetingResponse(
            id=meeting['id'],
            title=meeting['title'],
            description=meeting['description'],
            meeting_type=meeting['meeting_type'],
            scheduled_date=meeting['scheduled_date'],
            duration_minutes=meeting['duration_minutes'],
            location=meeting['location'],
            is_virtual=meeting['is_virtual'],
            meeting_link=meeting['meeting_link'],
            status=meeting['status'],
            participants=participant_list,
            created_by=meeting['created_by'],
            created_at=meeting['created_at'],
            updated_at=meeting['updated_at'],
            started_at=meeting.get('started_at'),
            ended_at=meeting.get('ended_at')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch meeting: {str(e)}")


@router.put("/{meeting_id}", response_model=MeetingActionResponse)
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    current_user: dict = Depends(get_current_user),
    tenant_db: str = Depends(get_tenant_db)
):
    """Update meeting"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if meeting exists
        cursor.execute(f"""
            SELECT id FROM `{tenant_db}`.meetings WHERE id = %s
        """, (meeting_id,))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Build update query
        update_fields = []
        params = []
        
        if meeting_data.title is not None:
            update_fields.append("title = %s")
            params.append(meeting_data.title)
        
        if meeting_data.description is not None:
            update_fields.append("description = %s")
            params.append(meeting_data.description)
        
        if meeting_data.meeting_type is not None:
            update_fields.append("meeting_type = %s")
            params.append(meeting_data.meeting_type.value)
        
        if meeting_data.scheduled_date is not None:
            update_fields.append("scheduled_date = %s")
            params.append(meeting_data.scheduled_date)
        
        if meeting_data.duration_minutes is not None:
            update_fields.append("duration_minutes = %s")
            params.append(meeting_data.duration_minutes)
        
        if meeting_data.location is not None:
            update_fields.append("location = %s")
            params.append(meeting_data.location)
        
        if meeting_data.is_virtual is not None:
            update_fields.append("is_virtual = %s")
            params.append(meeting_data.is_virtual)
        
        if meeting_data.meeting_link is not None:
            update_fields.append("meeting_link = %s")
            params.append(meeting_data.meeting_link)
        
        if meeting_data.status is not None:
            update_fields.append("status = %s")
            params.append(meeting_data.status.value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append("updated_at = NOW()")
        params.append(meeting_id)
        
        cursor.execute(f"""
            UPDATE `{tenant_db}`.meetings
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return MeetingActionResponse(
            success=True,
            message="Meeting updated successfully",
            data={"id": meeting_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update meeting: {str(e)}")


@router.delete("/{meeting_id}", response_model=MeetingActionResponse)
async def delete_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_db: str = Depends(get_tenant_db)
):
    """Delete meeting"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if meeting exists
        cursor.execute(f"""
            SELECT id FROM `{tenant_db}`.meetings WHERE id = %s
        """, (meeting_id,))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Delete participants first
        cursor.execute(f"""
            DELETE FROM `{tenant_db}`.meeting_participants WHERE meeting_id = %s
        """, (meeting_id,))
        
        # Delete meeting
        cursor.execute(f"""
            DELETE FROM `{tenant_db}`.meetings WHERE id = %s
        """, (meeting_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return MeetingActionResponse(
            success=True,
            message="Meeting deleted successfully",
            data={"id": meeting_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete meeting: {str(e)}")


@router.post("/{meeting_id}/cancel", response_model=MeetingActionResponse)
async def cancel_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_db: str = Depends(get_tenant_db)
):
    """Cancel meeting"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"""
            UPDATE `{tenant_db}`.meetings
            SET status = %s, updated_at = NOW()
            WHERE id = %s
        """, (MeetingStatus.CANCELLED.value, meeting_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return MeetingActionResponse(
            success=True,
            message="Meeting cancelled successfully",
            data={"id": meeting_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel meeting: {str(e)}")
