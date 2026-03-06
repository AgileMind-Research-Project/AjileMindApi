"""
Scheduled Meeting Service

Business logic layer for scheduled meeting operations.
"""

from typing import Optional, Dict, Any, List
from datetime import date

from app.db.database import Database, db
from app.db.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from app.core.logger import logger


class ScheduledMeetingService:
    """Service for scheduled meeting operations."""

    def __init__(self, database: Database):
        self.repo = ScheduledMeetingRepository(database)

    async def schedule_meeting(
        self,
        tenant_name: str,
        project_id: int,
        sprint_id: int,
        title: str,
        meeting_category: str,
        meeting_date: date,
        start_time: str,
        end_time: str,
        meeting_link: Optional[str],
        created_by: str,
        attendees: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new scheduled meeting. If link is absent, the system will generate one."""
        logger.info(
            f"Scheduling meeting '{title}' ({meeting_category}) "
            f"for project {project_id}, sprint {sprint_id} on {meeting_date}"
        )
        
        # 1. Create with placeholder link if not provided
        initial_link = meeting_link or "PENDING"
        
        meeting = await self.repo.create_meeting(
            tenant_name=tenant_name,
            project_id=project_id,
            sprint_id=sprint_id,
            title=title,
            meeting_category=meeting_category,
            meeting_date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            meeting_link=initial_link,
            created_by=created_by,
            attendees=attendees,
        )
        
        if not meeting:
            return None

        # 2. If it was a placeholder, update to the actual app meeting URL using the new meeting_id
        if initial_link == "PENDING":
            meeting_id = meeting["meeting_id"]
            # You can change the domain here as needed
            final_link = f"/meetings/{meeting_id}"
            await self.repo.update_meeting_link(tenant_name, meeting_id, final_link)
            meeting["meeting_link"] = final_link

        return meeting

    async def update_attendees(
        self, tenant_name: str, meeting_id: str, attendees: List[str]
    ) -> bool:
        """Update the list of attendees for a meeting."""
        return await self.repo.update_meeting_attendees(tenant_name, meeting_id, attendees)

    async def get_meeting(
        self, tenant_name: str, meeting_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single meeting by ID."""
        return await self.repo.get_meeting_by_id(tenant_name, meeting_id)

    async def get_meetings_by_project(
        self, tenant_name: str, project_id: int
    ) -> List[Dict[str, Any]]:
        """All meetings for a project."""
        return await self.repo.get_meetings_by_project(tenant_name, project_id)

    async def get_meetings_by_sprint(
        self, tenant_name: str, project_id: int, sprint_id: int
    ) -> List[Dict[str, Any]]:
        """All meetings for a sprint within a project."""
        return await self.repo.get_meetings_by_sprint(tenant_name, project_id, sprint_id)

    async def update_status(
        self, tenant_name: str, meeting_id: str, status: str
    ) -> bool:
        """Update meeting status."""
        return await self.repo.update_meeting_status(tenant_name, meeting_id, status)

    async def extend_meeting(
        self, tenant_name: str, meeting_id: str, new_end_time: str
    ) -> bool:
        """Update the meeting's scheduled end time."""
        return await self.repo.update_meeting_end_time(tenant_name, meeting_id, new_end_time)

    async def delete_meeting(self, tenant_name: str, meeting_id: str) -> bool:
        """Delete a meeting."""
        return await self.repo.delete_meeting(tenant_name, meeting_id)


# ── Singleton factory ─────────────────────────────────────────────────────────

def get_scheduled_meeting_service() -> ScheduledMeetingService:
    """Return a ScheduledMeetingService bound to the shared DB pool."""
    return ScheduledMeetingService(db)
