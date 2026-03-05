"""
Sprint Repository

Database operations for sprints in tenant-specific databases.

Real sprint table schema:
  sprint_id  bigint NOT NULL PRIMARY KEY  ← This IS the Jira sprint ID, supplied by caller.
  project_id bigint NOT NULL FK → projects(project_id)
  sprint_name, sprint_goal, start_date, end_date, sprint_status,
  total_estimated_hours, total_completed_hours, created_at, updated_at
"""

from typing import Optional, Dict, Any, List
from datetime import date
from app.db.database import Database
from app.core.logger import logger


class SprintRepository:
    """Repository for sprint database operations"""

    def __init__(self, db: Database):
        self.db = db

    async def create_sprint(
        self,
        tenant_name: str,
        sprint_id: int,           # Jira sprint ID — used as PK (required, no AUTO_INCREMENT)
        project_id: int,
        sprint_name: str,
        start_date: date,
        end_date: date,
        sprint_status: str = 'Future',
        sprint_goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new sprint row using the Jira sprint ID as the primary key.

        Because sprint_id is a plain bigint PK (no AUTO_INCREMENT), the caller
        MUST supply the Jira sprint ID before calling this method.

        Args:
            tenant_name:   Tenant database schema name
            sprint_id:     Jira sprint ID — becomes the PK sprint_id in the table
            project_id:    FK → projects.project_id
            sprint_name:   Human-readable sprint name (e.g. "Sprint 1")
            start_date:    Sprint start date
            end_date:      Sprint end date
            sprint_status: One of 'Not Started' | 'In Progress' | 'Completed' | 'Closed'
            sprint_goal:   Optional sprint goal text

        Returns:
            The full inserted sprint row as a dict.
        """
        try:
            query = """
                INSERT INTO sprint (
                    sprint_id, project_id, sprint_name, sprint_goal,
                    start_date, end_date, sprint_status,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """

            await self.db.execute_query(
                query,
                (
                    sprint_id, project_id, sprint_name, sprint_goal,
                    start_date, end_date, sprint_status
                ),
                commit=True,
                schema=tenant_name
            )

            # Fetch and return the inserted row
            fetch_query = """
                SELECT * FROM sprint
                WHERE sprint_id = %s
            """
            result = await self.db.execute_query(
                fetch_query,
                (sprint_id,),
                fetch_one=True,
                schema=tenant_name
            )

            logger.info(
                f"Sprint created in {tenant_name}: "
                f"sprint_id={sprint_id}, project_id={project_id}, name='{sprint_name}'"
            )
            return result

        except Exception as e:
            logger.error(f"Error creating sprint in database: {str(e)}")
            raise

    async def get_sprint_by_id(
        self,
        tenant_name: str,
        sprint_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a sprint by its ID (which is also the Jira sprint ID).

        Args:
            tenant_name: Tenant database schema name
            sprint_id:   PK sprint_id / Jira sprint ID

        Returns:
            Sprint row as dict, or None if not found.
        """
        try:
            query = "SELECT * FROM sprint WHERE sprint_id = %s"
            return await self.db.execute_query(
                query,
                (sprint_id,),
                fetch_one=True,
                schema=tenant_name
            )
        except Exception as e:
            logger.error(f"Error fetching sprint {sprint_id}: {e}")
            return None

    async def list_sprints_by_project(
        self,
        tenant_name: str,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """
        Return all sprints for a project ordered by sprint_id (= Jira sprint ID).

        Args:
            tenant_name: Tenant database schema name
            project_id:  FK project_id

        Returns:
            List of sprint row dicts (may be empty).
        """
        try:
            query = """
                SELECT * FROM sprint
                WHERE project_id = %s
                ORDER BY sprint_id ASC
            """
            result = await self.db.execute_query(
                query,
                (project_id,),
                fetch_all=True,
                schema=tenant_name
            )
            return result or []
        except Exception as e:
            logger.error(f"Error listing sprints for project {project_id}: {e}")
            return []
