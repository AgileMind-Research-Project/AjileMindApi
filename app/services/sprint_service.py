from typing import Optional, Dict, Any, List
from datetime import date, datetime, timedelta
import logging
from app.db.database import Database
from app.db.repositories.sprint_repository import SprintRepository
from app.db.repositories.project_repository import ProjectRepository
from app.services.jira_service import JiraService
from app.core.logger import logger, get_logger
from app.utils.jwt import get_secret

# Dedicated logger for sprint transitions
sprint_event_logger = get_logger("sprint")

class SprintService:
    """Service for managing sprint lifecycles across Jira and local DB"""
    
    def __init__(self, db: Database):
        self.db = db
        self.sprint_repo = SprintRepository(db)
        self.project_repo = ProjectRepository(db)
        self.jira_service = JiraService(db)

    async def prepare_next_sprint(
        self,
        tenant_name: str,
        project_id: int,
        board_id: int
    ) -> Dict[str, Any]:
        """
        Ensures a future sprint exists in both Jira and the local DB.
        Identifies the next available sprint or creates one if necessary.
        """
        try:
            sprint_event_logger.info(f"[{tenant_name}] START: Preparing next sprint for project {project_id} (Board: {board_id})")
            
            # 1. Get Jira credentials and API token
            credentials = await self.jira_service.get_credentials(tenant_name)
            if not credentials:
                msg = f"Jira integration not configured for tenant '{tenant_name}'."
                sprint_event_logger.error(f"[{tenant_name}] FAILED: {msg}")
                raise Exception(msg)
            
            jira_url = credentials["jira_url"]
            secret_name = f"tenant_{tenant_name}_jira_api_token_{jira_url.replace('https://','').replace('/','_')}"
            secret_result = get_secret(secret_name)
            
            if not secret_result.get("success"):
                 msg = f"Failed to retrieve Jira API token for {tenant_name}."
                 sprint_event_logger.error(f"[{tenant_name}] FAILED: {msg}")
                 raise Exception(msg)
            
            api_token = secret_result.get("secret_value")

            # 2. Check Jira for future sprints
            sprints = await self.jira_service.get_jira_sprints_by_board(
                jira_url=jira_url,
                email=credentials["email"],
                api_token=api_token,
                board_id=board_id,
                state="future"
            )

            next_sprint = None
            if sprints:
                next_sprint = sprints[0]
                msg = f"Identified existing future Jira sprint: {next_sprint['name']} (ID: {next_sprint['id']})"
                sprint_event_logger.info(f"[{tenant_name}] {msg}")
                await self.sprint_repo.log_sprint_event(
                    tenant_name, project_id, "IDENTIFIED_EXISTING", msg, next_sprint["id"]
                )
            else:
                # No future sprint? Create one dynamically
                all_sprints = await self.jira_service.get_jira_sprints_by_board(
                    jira_url=jira_url,
                    email=credentials["email"],
                    api_token=api_token,
                    board_id=board_id,
                    state="future,active,closed"
                )
                
                sprint_num = len(all_sprints) + 1
                new_name = f"Sprint {sprint_num}"
                
                sprint_event_logger.info(f"[{tenant_name}] Creating new Jira sprint: {new_name}")
                created = await self.jira_service.create_jira_sprint(
                    tenant_name=tenant_name,
                    board_id=board_id,
                    sprint_name=new_name
                )
                if not created:
                    msg = "Jira API failed to create a new sprint."
                    sprint_event_logger.error(f"[{tenant_name}] FAILED: {msg}")
                    raise Exception(msg)
                
                next_sprint = created
                msg = f"Dynamically created new Jira sprint: {new_name} (ID: {next_sprint['id']})"
                sprint_event_logger.info(f"[{tenant_name}] {msg}")
                await self.sprint_repo.log_sprint_event(
                    tenant_name, project_id, "CREATED_NEW_SPRINT", msg, next_sprint["id"]
                )

            # 3. Synchronize to the local tenant database
            project = await self.project_repo.get_project_by_id(tenant_name, project_id)
            sprint_size = project.get("sprint_size", 2) if project else 2
            
            start_date_placeholder = date.today()
            end_date_placeholder = start_date_placeholder + timedelta(weeks=sprint_size)

            db_sprint = await self.sprint_repo.get_sprint_by_id(tenant_name, next_sprint["id"])
            if not db_sprint:
                await self.sprint_repo.create_sprint(
                    tenant_name=tenant_name,
                    sprint_id=next_sprint["id"],
                    project_id=project_id,
                    sprint_name=next_sprint["name"],
                    start_date=start_date_placeholder,
                    end_date=end_date_placeholder,
                    sprint_status="Future"
                )
                sprint_event_logger.info(f"[{tenant_name}] Synchronized new sprint {next_sprint['id']} to database.")
            else:
                await self.sprint_repo.update_sprint_status(
                    tenant_name=tenant_name,
                    sprint_id=next_sprint["id"],
                    new_status="Future"
                )
                sprint_event_logger.info(f"[{tenant_name}] Updated existing sprint {next_sprint['id']} in database.")

            return next_sprint

        except Exception as e:
            sprint_event_logger.error(f"[{tenant_name}] ERROR in prepare_next_sprint: {str(e)}")
            raise

    async def sync_and_start_sprint(
        self,
        tenant_name: str,
        project_id: int,
        sprint_id: int,
        board_id: int
    ) -> bool:
        """
        Starts the sprint in Jira and updates the local database state to 'Active'.
        """
        try:
            sprint_event_logger.info(f"[{tenant_name}] START: Activating sprint {sprint_id} for project {project_id}")
            
            project = await self.project_repo.get_project_by_id(tenant_name, project_id)
            if not project:
                raise Exception(f"Project {project_id} not found.")
            
            sprint_size = project.get("sprint_size", 2)
            now = datetime.now()
            end_time = now + timedelta(weeks=sprint_size)
            
            start_date_str = now.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
            end_date_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.000+0000')

            db_sprint = await self.sprint_repo.get_sprint_by_id(tenant_name, sprint_id)
            sprint_name = db_sprint["sprint_name"] if db_sprint else f"Sprint {sprint_id}"

            # 3. Activate in Jira Cloud
            success = await self.jira_service.start_jira_sprint(
                tenant_name=tenant_name,
                sprint_id=sprint_id,
                sprint_name=sprint_name,
                board_id=board_id,
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            if not success:
                msg = f"Jira API failure starting sprint {sprint_id}."
                sprint_event_logger.error(f"[{tenant_name}] FAILED: {msg}")
                await self.sprint_repo.log_sprint_event(
                    tenant_name, project_id, "START_FAILED", msg, sprint_id
                )
                return False

            # 4. Update the local database state
            await self.sprint_repo.start_sprint(
                tenant_name=tenant_name,
                sprint_id=sprint_id,
                sprint_size_weeks=sprint_size
            )
            
            msg = f"Successfully started sprint '{sprint_name}' (ID: {sprint_id})."
            sprint_event_logger.info(f"[{tenant_name}] {msg}")
            await self.sprint_repo.log_sprint_event(
                tenant_name, project_id, "STARTED", msg, sprint_id
            )
            
            return True

        except Exception as e:
            sprint_event_logger.error(f"[{tenant_name}] ERROR in sync_and_start_sprint: {str(e)}")
            return False

    async def close_active_sprint(self, tenant_name: str, project_id: int, sprint_id: int) -> bool:
        """
        Closes an active sprint in both Jira and the database.
        """
        try:
            sprint_event_logger.info(f"[{tenant_name}] START: Closing sprint {sprint_id} for project {project_id}")
            
            # 1. Close in Jira
            jira_closed = await self.jira_service.close_jira_sprint(tenant_name, sprint_id)
            if not jira_closed:
                msg = f"Failed to close sprint {sprint_id} in Jira."
                sprint_event_logger.warning(f"[{tenant_name}] {msg}")
            
            # 2. Update DB
            await self.sprint_repo.update_sprint_status(tenant_name, sprint_id, "Closed")
            
            msg = f"Sprint {sprint_id} closed successfully."
            sprint_event_logger.info(f"[{tenant_name}] {msg}")
            await self.sprint_repo.log_sprint_event(
                tenant_name, project_id, "CLOSED", msg, sprint_id
            )
            return True
        except Exception as e:
            sprint_event_logger.error(f"[{tenant_name}] ERROR in close_active_sprint: {str(e)}")
            return False
