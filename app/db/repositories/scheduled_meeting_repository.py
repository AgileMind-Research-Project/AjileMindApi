"""
Scheduled Meeting Repository

Database operations for scheduled meetings in the `meetings` table
of tenant-specific databases.
"""

import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import date, time
from app.db.database import Database
from app.core.logger import logger


class ScheduledMeetingRepository:
    """Repository for scheduled meeting database operations"""

    def __init__(self, db: Database):
        self.db = db

    async def create_meeting(
        self,
        tenant_name: str,
        project_id: int,
        sprint_id: int,
        title: str,
        meeting_category: str,
        meeting_date: date,
        start_time: time,
        end_time: time,
        meeting_link: str,
        created_by: str,
        attendees: Optional[List[str]] = None,
        status: str = "SCHEDULED",
    ) -> Optional[Dict[str, Any]]:
        """
        Insert a new scheduled meeting into the meetings table.

        Returns:
            Created meeting data or None on failure
        """
        try:
            attendees_json = json.dumps(attendees) if attendees else None
            meeting_id = str(uuid.uuid4())

            query = """
                INSERT INTO meetings (
                    meeting_id, project_id, sprint_id, title, meeting_category,
                    meeting_date, start_time, end_time,
                    meeting_link, status, created_by, attendees
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await self.db.execute_query(
                query,
                (
                    meeting_id, project_id, sprint_id, title, meeting_category,
                    meeting_date, str(start_time), str(end_time),
                    meeting_link, status, created_by, attendees_json,
                ),
                commit=True,
                schema=tenant_name,
            )

            # Fetch the row we just inserted using the meeting_id
            fetch_query = """
                SELECT *
                FROM meetings
                WHERE meeting_id = %s
            """
            result = await self.db.execute_query(
                fetch_query,
                (meeting_id,),
                fetch_one=True,
                schema=tenant_name,
            )

            return self._deserialize(result)

        except Exception as e:
            logger.error(f"Error creating scheduled meeting: {e}")
            return None

    async def get_meeting_by_id(
        self, tenant_name: str, meeting_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a single meeting by its UUID."""
        try:
            query = "SELECT * FROM meetings WHERE meeting_id = %s"
            result = await self.db.execute_query(
                query, (meeting_id,), fetch_one=True, schema=tenant_name
            )
            return self._deserialize(result)
        except Exception as e:
            logger.error(f"Error getting meeting {meeting_id}: {e}")
            return None

    async def get_meetings_by_project(
        self, tenant_name: str, project_id: int
    ) -> List[Dict[str, Any]]:
        """Get all meetings for a project, newest first."""
        try:
            query = """
                SELECT * FROM meetings
                WHERE project_id = %s
                ORDER BY meeting_date ASC, start_time ASC
            """
            rows = await self.db.execute_query(
                query, (project_id,), fetch_all=True, schema=tenant_name
            )
            return [self._deserialize(r) for r in (rows or [])]
        except Exception as e:
            logger.error(f"Error getting meetings for project {project_id}: {e}")
            return []

    async def get_meetings_by_sprint(
        self, tenant_name: str, project_id: int, sprint_id: int
    ) -> List[Dict[str, Any]]:
        """Get all meetings for a specific sprint."""
        try:
            query = """
                SELECT * FROM meetings
                WHERE project_id = %s AND sprint_id = %s
                ORDER BY meeting_date ASC, start_time ASC
            """
            rows = await self.db.execute_query(
                query, (project_id, sprint_id), fetch_all=True, schema=tenant_name
            )
            return [self._deserialize(r) for r in (rows or [])]
        except Exception as e:
            logger.error(f"Error getting meetings for sprint {sprint_id}: {e}")
            return []

    async def update_meeting_status(
        self, tenant_name: str, meeting_id: str, status: str
    ) -> bool:
        """Update the status of a meeting (SCHEDULED / ONGOING / COMPLETED / CANCELLED)."""
        try:
            query = "UPDATE meetings SET status = %s WHERE meeting_id = %s"
            await self.db.execute_query(
                query, (status, meeting_id), commit=True, schema=tenant_name
            )
            return True
        except Exception as e:
            logger.error(f"Error updating meeting status {meeting_id}: {e}")
            return False

    async def update_meeting_attendees(
        self, tenant_name: str, meeting_id: str, attendees: List[str]
    ) -> bool:
        """Set the attendees list for a meeting (stored as JSON)."""
        try:
            attendees_json = json.dumps(attendees)
            query = "UPDATE meetings SET attendees = %s WHERE meeting_id = %s"
            await self.db.execute_query(
                query, (attendees_json, meeting_id), commit=True, schema=tenant_name
            )
            return True
        except Exception as e:
            logger.error(f"Error updating meeting attendees {meeting_id}: {e}")
            return False

    async def update_meeting_end_time(
        self, tenant_name: str, meeting_id: str, new_end_time: str
    ) -> bool:
        """Update the meeting's scheduled end time."""
        try:
            query = "UPDATE meetings SET end_time = %s WHERE meeting_id = %s"
            await self.db.execute_query(
                query, (new_end_time, meeting_id), commit=True, schema=tenant_name
            )
            return True
        except Exception as e:
            logger.error(f"Error updating meeting end time {meeting_id}: {e}")
            return False

    async def update_meeting_link(
        self, tenant_name: str, meeting_id: str, link: str
    ) -> bool:
        """Set or update the meeting link."""
        try:
            query = "UPDATE meetings SET meeting_link = %s WHERE meeting_id = %s"
            await self.db.execute_query(
                query, (link, meeting_id), commit=True, schema=tenant_name
            )
            return True
        except Exception as e:
            logger.error(f"Error updating meeting link {meeting_id}: {e}")
            return False

    async def delete_meeting(self, tenant_name: str, meeting_id: str) -> bool:
        """Hard-delete a meeting by UUID."""
        try:
            query = "DELETE FROM meetings WHERE meeting_id = %s"
            await self.db.execute_query(
                query, (meeting_id,), commit=True, schema=tenant_name
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting meeting {meeting_id}: {e}")
            return False

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _deserialize(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse JSON attendees field and coerce date/time to strings."""
        if not row:
            return None
        row = dict(row)
        # attendees stored as JSON string
        if isinstance(row.get("attendees"), str):
            try:
                row["attendees"] = json.loads(row["attendees"])
            except Exception:
                row["attendees"] = []
        # Convert date/time/datetime objects to ISO strings for JSON serialisation
        for key in ("meeting_date", "start_time", "end_time", "created_at", "updated_at"):
            val = row.get(key)
            if val is not None and not isinstance(val, str):
                row[key] = str(val)
        return row
