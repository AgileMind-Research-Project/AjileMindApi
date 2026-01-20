"""
Project Service

Business logic for project creation and management.
"""

from typing import Optional, Dict, Any, List
from datetime import date
from fastapi import HTTPException, status

from app.db.database import Database
from app.db.repositories.project_repository import ProjectRepository
from app.services.jira_service import JiraService
from app.core.logger import logger


class ProjectService:
    """Service for project business logic"""
    
    def __init__(self, db: Database):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.jira_service = JiraService(db)
    
    async def create_project(
        self,
        tenant_name: str,
        project_name: str,
        key: str,
        project_type: str,
        start_date: date,
        end_date: date,
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
            
            logger.info(f"✅ Project created in Jira successfully: {jira_project}")
            
        except HTTPException as e:
            # Re-raise HTTP exceptions from Jira service
            logger.error(f"❌ Jira project creation failed: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to create project in Jira: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project in Jira: {str(e)}"
            )
        
        # Step 3: Save project to database ONLY after Jira success
        # If we reach this point, Jira project was created successfully
        try:
            project_id = jira_project.get("project_id")
            
            db_project = await self.project_repo.create_project(
                tenant_name=tenant_name,
                project_id=project_id,
                project_name=project_name,
                key=key,
                project_type=project_type,
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
            
            logger.info(f"✅ Project saved to database successfully: {db_project}")
            
            # Combine Jira and database information
            return {
                "id": project_id,
                "project_name": project_name,
                "key": key,
                "project_type": project_type,
                "start_date": str(start_date),
                "end_date": str(end_date),
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
