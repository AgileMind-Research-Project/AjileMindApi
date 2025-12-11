"""
Project Repository

Database operations for projects in tenant-specific databases.
"""

from typing import Optional, Dict, Any, List
from datetime import date
from app.db.database import Database
from app.core.logger import logger


class ProjectRepository:
    """Repository for project database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_project(
        self,
        tenant_name: str,
        project_id: int,
        project_name: str,
        key: str,
        project_type: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Create a new project in tenant database.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID from Jira
            project_name: Project name
            key: Project key
            project_type: Project type (software, business, service_desk)
            start_date: Project start date
            end_date: Project end date
        
        Returns:
            Created project data
        """
        try:
            query = """
                INSERT INTO projects (
                    project_id, project_name, `key`, project_type, 
                    start_date, end_date, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            await self.db.execute_query(
                query,
                (project_id, project_name, key, project_type, start_date, end_date),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Project created in {tenant_name}: {key} - {project_name} (ID: {project_id})")
            
            # Return created project
            return await self.get_project_by_id(tenant_name, project_id)
            
        except Exception as e:
            logger.error(f"Error creating project in database: {str(e)}")
            raise
    
    async def get_project_by_id(
        self,
        tenant_name: str,
        project_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get project by ID.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID
        
        Returns:
            Project data or None if not found
        """
        try:
            query = """
                SELECT 
                    project_id, project_name, `key`, project_type,
                    start_date, end_date, created_at, updated_at
                FROM projects
                WHERE project_id = %s
            """
            
            result = await self.db.execute_query(
                query,
                (project_id,),
                fetch_one=True,
                schema=tenant_name
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching project by ID: {str(e)}")
            return None
    
    async def get_project_by_key(
        self,
        tenant_name: str,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get project by key.
        
        Args:
            tenant_name: Tenant database name
            key: Project key
        
        Returns:
            Project data or None if not found
        """
        try:
            query = """
                SELECT 
                    project_id, project_name, `key`, project_type,
                    start_date, end_date, created_at, updated_at
                FROM projects
                WHERE `key` = %s
            """
            
            result = await self.db.execute_query(
                query,
                (key,),
                fetch_one=True,
                schema=tenant_name
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching project by key: {str(e)}")
            return None
    
    async def get_project_by_name(
        self,
        tenant_name: str,
        project_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get project by name.
        
        Args:
            tenant_name: Tenant database name
            project_name: Project name
        
        Returns:
            Project data or None if not found
        """
        try:
            query = """
                SELECT 
                    project_id, project_name, `key`, project_type,
                    start_date, end_date, created_at, updated_at
                FROM projects
                WHERE project_name = %s
            """
            
            result = await self.db.execute_query(
                query,
                (project_name,),
                fetch_one=True,
                schema=tenant_name
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching project by name: {str(e)}")
            return None
    
    async def list_projects(
        self,
        tenant_name: str,
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        List all projects with pagination.
        
        Args:
            tenant_name: Tenant database name
            page: Page number
            limit: Items per page
        
        Returns:
            Tuple of (projects list, total count)
        """
        try:
            offset = (page - 1) * limit
            
            # Get projects
            query = """
                SELECT 
                    project_id, project_name, `key`, project_type,
                    start_date, end_date, created_at, updated_at
                FROM projects
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            
            projects = await self.db.execute_query(
                query,
                (limit, offset),
                fetch_all=True,
                schema=tenant_name
            )
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM projects"
            count_result = await self.db.execute_query(
                count_query,
                fetch_one=True,
                schema=tenant_name
            )
            
            total = count_result['total'] if count_result else 0
            
            return projects or [], total
            
        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            return [], 0
    
    async def update_project(
        self,
        tenant_name: str,
        project_id: int,
        project_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> bool:
        """
        Update project details.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID
            project_name: New project name (optional)
            start_date: New start date (optional)
            end_date: New end date (optional)
        
        Returns:
            True if updated successfully
        """
        try:
            # Build update fields dynamically
            update_fields = []
            params = []
            
            if project_name:
                update_fields.append("project_name = %s")
                params.append(project_name)
            
            if start_date:
                update_fields.append("start_date = %s")
                params.append(start_date)
            
            if end_date:
                update_fields.append("end_date = %s")
                params.append(end_date)
            
            if not update_fields:
                return True  # Nothing to update
            
            update_fields.append("updated_at = NOW()")
            params.append(project_id)
            
            query = f"""
                UPDATE projects
                SET {', '.join(update_fields)}
                WHERE project_id = %s
            """
            
            await self.db.execute_query(
                query,
                tuple(params),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Project updated in {tenant_name}: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating project: {str(e)}")
            raise
    
    async def delete_project(
        self,
        tenant_name: str,
        project_id: int
    ) -> bool:
        """
        Delete a project from database.
        Note: This does not delete from Jira, only from local database.
        
        Args:
            tenant_name: Tenant database name
            project_id: Project ID
        
        Returns:
            True if deleted successfully
        """
        try:
            query = "DELETE FROM projects WHERE project_id = %s"
            
            await self.db.execute_query(
                query,
                (project_id,),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Project deleted from {tenant_name}: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting project: {str(e)}")
            raise
    
    async def project_exists(
        self,
        tenant_name: str,
        key: Optional[str] = None,
        project_name: Optional[str] = None
    ) -> bool:
        """
        Check if a project exists by key or name.
        
        Args:
            tenant_name: Tenant database name
            key: Project key (optional)
            project_name: Project name (optional)
        
        Returns:
            True if exists
        """
        try:
            if key:
                query = "SELECT COUNT(*) as count FROM projects WHERE `key` = %s"
                result = await self.db.execute_query(
                    query,
                    (key,),
                    fetch_one=True,
                    schema=tenant_name
                )
                return result and result['count'] > 0
            
            if project_name:
                query = "SELECT COUNT(*) as count FROM projects WHERE project_name = %s"
                result = await self.db.execute_query(
                    query,
                    (project_name,),
                    fetch_one=True,
                    schema=tenant_name
                )
                return result and result['count'] > 0
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking project existence: {str(e)}")
            return False
