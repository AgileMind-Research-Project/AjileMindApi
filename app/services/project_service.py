"""
Project Service

Business logic for project creation and management.
"""

from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from fastapi import HTTPException, status

from app.db.database import Database
from app.db.repositories.project_repository import ProjectRepository
from app.db.repositories.sprint_repository import SprintRepository
from app.services.jira_service import JiraService
from app.core.logger import logger


class ProjectService:
    """Service for project business logic"""
    
    def __init__(self, db: Database):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.sprint_repo = SprintRepository(db)
        self.jira_service = JiraService(db)
        from app.services.redis_chat_service import get_redis_chat_service
        self.chat_service = get_redis_chat_service()
    
    async def create_project(
        self,
        tenant_name: str,
        project_name: str,
        key: str,
        project_type: str,
        start_date: date,
        end_date: date,
        created_by_user_id: str,
        created_by_username: str,
        description: Optional[str] = None,
        template: str = "com.pyxis.greenhopper.jira:gh-scrum-template",
        sprint_size: Optional[int] = None,
        project_lead: Optional[str] = None,
        project_manager: Optional[List[str]] = None,
        architecture_type: Optional[str] = None,
        stack_type: Optional[str] = None,
        frontend_technologies: Optional[List[str]] = None,
        backend_technologies: Optional[List[str]] = None,
        cloud_host: Optional[str] = None,
        budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a project in Jira first, then save to database.
        
        **Important**: Database storage ONLY happens after successful Jira creation.
        
        This is a two-step process:
        1. Create project in Jira Cloud using REST API
        2. **ONLY IF Jira creation succeeds**, save project details to tenant database
        
        Args:
            tenant_name: Tenant database name
            project_name: Project name
            key: Project key (2-10 uppercase letters, manually entered)
            project_type: Project type (software, business, service_desk)
            start_date: Project start date
            end_date: Project end date
            description: Project description (optional)
            template: Jira project template
        
        Returns:
            Created project data including Jira ID and database info
            
        Raises:
            HTTPException: If project creation fails in Jira or database
        """
        # Step 1: Check if project already exists in local database (pre-validation)
        # This prevents duplicate attempts, but Jira is still the source of truth
        existing_by_key = await self.project_repo.project_exists(
            tenant_name=tenant_name,
            key=key
        )
        
        if existing_by_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with key '{key}' already exists in database"
            )
        
        existing_by_name = await self.project_repo.project_exists(
            tenant_name=tenant_name,
            project_name=project_name
        )
        
        if existing_by_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with name '{project_name}' already exists in database"
            )
        
        # Step 2: Create project in Jira Cloud FIRST
        # This is the critical step - if it fails, nothing is saved to database
        try:
            jira_project = await self.jira_service.create_project(
                tenant_name=tenant_name,
                project_name=project_name,
                key=key,
                project_type=project_type,
                template=template,
                description=description
            )
            
            logger.info(f"Project created in Jira successfully: {jira_project}")
            
        except HTTPException as e:
            # Re-raise HTTP exceptions from Jira service
            logger.error(f"Jira project creation failed: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"Failed to create project in Jira: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project in Jira: {str(e)}"
            )
        
        # Step 3: Save project to database ONLY after Jira success
        # If we reach this point, Jira project was created successfully
        try:
            project_id = jira_project.get("project_id")
            # board_id is fetched from Jira Agile API right after project creation.
            # It may be None for non-software project types that don't auto-create a board.
            board_id = jira_project.get("board_id")

            db_project = await self.project_repo.create_project(
                tenant_name=tenant_name,
                project_id=project_id,
                project_name=project_name,
                key=key,
                project_type=project_type,
                start_date=start_date,
                end_date=end_date,
                board_id=board_id,
                sprint_size=sprint_size,
                project_lead=project_lead,
                project_manager=project_manager,
                architecture_type=architecture_type,
                stack_type=stack_type,
                frontend_technologies=frontend_technologies,
                backend_technologies=backend_technologies,
                cloud_host=cloud_host,
                budget=budget
            )
            
            logger.info(f"Project saved to database successfully: {db_project}")
            
            # Step 4: Create the first sprint (Sprint 1)
            # The sprint table uses sprint_id (bigint, no AUTO_INCREMENT) as PK.
            # sprint_id IS the Jira sprint ID, so we MUST fetch it from Jira first.
            # We always attempt this for software projects (when board_id exists).
            # sprint_size only affects the sprint end_date; default to 2 weeks if not given.
            if board_id:
                try:
                    effective_sprint_size = sprint_size if sprint_size else 2
                    sprint_end_date = start_date + timedelta(weeks=effective_sprint_size)

                    # Step 4a: Resolve Jira credentials for the Agile API call
                    jira_sprint_id   = None
                    sprint_1_in_jira = None   # will hold the full sprint dict from Jira
                    try:
                        credentials = await self.jira_service.get_credentials(tenant_name)
                        if credentials:
                            from app.utils.jwt import get_secret
                            import asyncio
                            jira_url = credentials["jira_url"]
                            email    = credentials["email"]
                            secret_name = (
                                f"tenant_{tenant_name}_jira_api_token_"
                                f"{jira_url.replace('https://','').replace('/','_')}"
                            )
                            secret_result = get_secret(secret_name)
                            api_token = (
                                secret_result.get("secret_value")
                                if secret_result.get("success") else None
                            )

                            if api_token:
                                # Retry loop: Jira provisions Sprint 1 asynchronously,
                                # so it may not appear immediately after project creation.
                                max_sprint_retries = 4
                                sprint_retry_wait  = 3.0  # seconds

                                for sprint_attempt in range(1, max_sprint_retries + 1):
                                    jira_sprints = await self.jira_service.get_jira_sprints_by_board(
                                        jira_url=jira_url,
                                        email=email,
                                        api_token=api_token,
                                        board_id=board_id,
                                        state="future,active,closed"
                                    )

                                    if jira_sprints:
                                        # 1st priority: exact name match "Sprint 1"
                                        sprint_1_in_jira = next(
                                            (s for s in jira_sprints if s.get("name") == "Sprint 1"),
                                            None
                                        )
                                        # 2nd priority: take the first sprint on the board
                                        if not sprint_1_in_jira:
                                            sprint_1_in_jira = jira_sprints[0]
                                            logger.warning(
                                                f"'Sprint 1' not found by name on board {board_id}. "
                                                f"Using first sprint: {sprint_1_in_jira.get('name')} "
                                                f"(id={sprint_1_in_jira.get('id')})"
                                            )

                                        jira_sprint_id = sprint_1_in_jira["id"]
                                        logger.info(
                                            f"Fetched Jira sprint ID={jira_sprint_id} "
                                            f"('{sprint_1_in_jira.get('name')}') "
                                            f"on board {board_id} "
                                            f"(attempt {sprint_attempt}/{max_sprint_retries})"
                                        )
                                        break  # success – exit retry loop
                                    else:
                                        # Jira hasn't provisioned the sprint yet
                                        logger.warning(
                                            f"No sprints found on board {board_id} yet "
                                            f"(attempt {sprint_attempt}/{max_sprint_retries}). "
                                            f"Waiting {sprint_retry_wait}s..."
                                        )
                                        if sprint_attempt < max_sprint_retries:
                                            await asyncio.sleep(sprint_retry_wait)

                                if not jira_sprint_id:
                                    logger.error(
                                        f"Sprint not found on board {board_id} after "
                                        f"{max_sprint_retries} attempts. "
                                        f"Local sprint will be skipped."
                                    )
                    except Exception as jira_sprint_err:
                        logger.error(
                            f"Could not fetch Jira sprint ID for project "
                            f"{project_id}: {jira_sprint_err}"
                        )

                    # Step 4b: Insert the sprint row using real data from Jira
                    # sprint_id has no AUTO_INCREMENT — Jira ID is the PK.
                    if jira_sprint_id and sprint_1_in_jira:

                        # Map Jira state (lowercase) → our DB enum (title case)
                        jira_state_map = {
                            "future": "Future",
                            "active": "Active",
                            "closed": "Closed",
                        }
                        raw_state    = sprint_1_in_jira.get("state", "future").lower()
                        sprint_state = jira_state_map.get(raw_state, "Future")

                        # Use Jira's sprint name (e.g. "Sprint 1") — not hardcoded
                        real_sprint_name = sprint_1_in_jira.get("name", "Sprint 1")

                        # Use Jira's dates when set; fall back to our calculated values
                        from datetime import datetime as _dt

                        def _parse_jira_date(val):
                            """Parse ISO-8601 date string from Jira → date object, or None."""
                            if not val:
                                return None
                            try:
                                return _dt.fromisoformat(
                                    val.replace("Z", "+00:00")
                                ).date()
                            except Exception:
                                return None

                        jira_start = _parse_jira_date(sprint_1_in_jira.get("startDate"))
                        jira_end   = _parse_jira_date(sprint_1_in_jira.get("endDate"))

                        real_start = jira_start or start_date
                        real_end   = jira_end   or sprint_end_date

                        await self.sprint_repo.create_sprint(
                            tenant_name=tenant_name,
                            sprint_id=jira_sprint_id,     # Jira ID → PK (required)
                            project_id=project_id,
                            sprint_name=real_sprint_name, # real name from Jira
                            start_date=real_start,        # Jira start date (or fallback)
                            end_date=real_end,            # Jira end date   (or fallback)
                            sprint_status=sprint_state    # mapped from Jira state
                        )
                        logger.info(
                            f"Sprint '{real_sprint_name}' (id={jira_sprint_id}, "
                            f"state={sprint_state}) saved for project {project_id}"
                        )
                    else:
                        logger.warning(
                            f"Skipped local Sprint 1 creation for project {project_id} "
                            f"because Jira sprint ID could not be resolved."
                        )

                except Exception as sprint_err:
                    logger.error(f"Project created but failed to create first sprint: {str(sprint_err)}")
                    # Non-fatal – project itself is saved successfully

            # Step 5: Create a default chat channel for the project
            # This ensures that scheduler reminders have a place to post!
            try:
                channel_name = f"General-{key}"
                self.chat_service.create_channel(
                    tenant_name=tenant_name,
                    channel_name=channel_name,
                    created_by_user_id=created_by_user_id,
                    created_by_username=created_by_username,
                    description=f"Automated general channel for project {project_name}",
                    is_private=False,
                    project_id=project_id,
                    team_name=project_name
                )
                logger.info(f"Created default project channel for {key}: {channel_name}")
            except Exception as chat_err:
                logger.error(f"Failed to create default project channel: {chat_err}")
                # Also non-fatal
            
            # Combine Jira and database information
            return {
                "id": project_id,
                "project_name": project_name,
                "key": key,
                "project_type": project_type,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "board_id": board_id,
                "jira_url": jira_project.get("jira_url"),
                "jira_self": jira_project.get("self"),
                "created_at": db_project.get("created_at"),
                "message": "Project created successfully in Jira and database"
            }
            
        except Exception as e:
            logger.error(f"Failed to save project to database: {str(e)}")
            # Note: Project was created in Jira but failed to save to database
            # In production, you might want to implement compensation logic here
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Project created in Jira (ID: {project_id}) but failed to save to database: {str(e)}"
            )
    
    async def get_project(
        self,
        tenant_name: str,
        project_id: Optional[int] = None,
        key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get project by ID or key.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID (optional)
            key: Project key (optional)
        
        Returns:
            Project data or None if not found
        """
        if project_id:
            return await self.project_repo.get_project_by_id(tenant_name, project_id)
        elif key:
            return await self.project_repo.get_project_by_key(tenant_name, key)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either project_id or key must be provided"
            )
    
    async def list_projects(
        self,
        tenant_name: str,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        List all projects with pagination.
        
        Args:
            tenant_name: Tenant database name
            page: Page number
            limit: Items per page
        
        Returns:
            Dict with projects list, total count, page, and limit
        """
        print('Listing projects for tenant:',tenant_name)
        projects, total = await self.project_repo.list_projects(
            tenant_name=tenant_name,
            page=page,
            limit=limit
        )
        print('Projects found:',projects)
        return {
            "projects": projects,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0
        }
    
    async def update_project(
        self,
        tenant_name: str,
        project_id: int,
        project_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sprint_size: Optional[int] = None,
        project_lead: Optional[str] = None,
        project_manager: Optional[List[str]] = None,
        architecture_type: Optional[str] = None,
        stack_type: Optional[str] = None,
        frontend_technologies: Optional[List[str]] = None,
        backend_technologies: Optional[List[str]] = None,
        cloud_host: Optional[str] = None,
        budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update project details.
        Note: This only updates the local database, not Jira.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID
            project_name: New project name (optional)
            start_date: New start date (optional)
            end_date: New end date (optional)
        
        Returns:
            Updated project data
        """
        # Check if project exists
        existing = await self.project_repo.get_project_by_id(tenant_name, project_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Update project
        await self.project_repo.update_project(
            tenant_name=tenant_name,
            project_id=project_id,
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            sprint_size=sprint_size,
            project_lead=project_lead,
            project_manager=project_manager,
            architecture_type=architecture_type,
            stack_type=stack_type,
            frontend_technologies=frontend_technologies,
            backend_technologies=backend_technologies,
            cloud_host=cloud_host,
            budget=budget
        )
        
        # Return updated project
        updated_project = await self.project_repo.get_project_by_id(tenant_name, project_id)
        return updated_project
    
    async def delete_project(
        self,
        tenant_name: str,
        project_id: int
    ) -> bool:
        """
        Delete project from database.
        Note: This does NOT delete from Jira, only from local database.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID
        
        Returns:
            True if deleted successfully
        """
        # Check if project exists
        existing = await self.project_repo.get_project_by_id(tenant_name, project_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        return await self.project_repo.delete_project(tenant_name, project_id)
