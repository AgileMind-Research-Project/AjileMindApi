"""
Backlog Repository

Database operations for backlog items.
"""

from typing import List, Dict, Any, Optional
from app.db.database import Database
from app.core.logger import logger
import json


class BacklogRepository:
    """Repository for backlog database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_backlog_item(
        self,
        tenant_name: str,
        item_id: str,
        project_id: int,
        summary: str,
        description: Optional[str],
        issue_type: str,
        status: str,
        priority: Optional[str],
        assignee: Optional[str],
        tags: Optional[List[str]],
        severity: Optional[str]
    ) -> Dict[str, Any]:
        """
        Create a backlog item in the database.
        
        Args:
            tenant_name: Tenant database name
            item_id: Jira issue key
            project_id: Project ID
            summary: Item summary
            description: Item description
            issue_type: Type (story, feature, change, bug)
            status: Current status
            priority: Priority level
            assignee: Assigned person
            tags: List of tags
            severity: Severity (for bugs)
        
        Returns:
            Created backlog item data
        """
        try:
            # Serialize tags to JSON
            tags_json = json.dumps(tags) if tags else None
            
            query = """
                INSERT INTO project_backlog (
                    id, project_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    summary = VALUES(summary),
                    description = VALUES(description),
                    issue_type = VALUES(issue_type),
                    status = VALUES(status),
                    priority = VALUES(priority),
                    assignee = VALUES(assignee),
                    tags = VALUES(tags),
                    severity = VALUES(severity),
                    updated_at = NOW()
            """
            
            await self.db.execute_query(
                query,
                (item_id, project_id, summary, description, issue_type,
                 status, priority, assignee, tags_json, severity),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Backlog item created: {item_id} in {tenant_name}")
            
            # Return created item
            return await self.get_backlog_item(tenant_name, item_id)
            
        except Exception as e:
            logger.error(f"Error creating backlog item: {str(e)}")
            raise
    
    async def get_backlog_item(
        self,
        tenant_name: str,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a single backlog item by ID"""
        try:
            query = """
                SELECT 
                    id, project_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity,
                    created_at, updated_at
                FROM project_backlog
                WHERE id = %s
            """
            
            result = await self.db.execute_query(
                query,
                (item_id,),
                fetch_one=True,
                schema=tenant_name
            )
            
            if result and result.get('tags'):
                try:
                    result['tags'] = json.loads(result['tags'])
                except:
                    result['tags'] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting backlog item: {str(e)}")
            raise
    
    async def list_backlog_by_project(
        self,
        tenant_name: str,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """List all backlog items for a project"""
        try:
            query = """
                SELECT 
                    id, project_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity,
                    created_at, updated_at
                FROM project_backlog
                WHERE project_id = %s
                ORDER BY created_at DESC
            """
            
            results = await self.db.execute_query(
                query,
                (project_id,),
                fetch_all=True,
                schema=tenant_name
            )
            
            # Deserialize tags for each item
            if results:
                for item in results:
                    if item.get('tags'):
                        try:
                            item['tags'] = json.loads(item['tags'])
                        except:
                            item['tags'] = None
            
            return results or []
            
        except Exception as e:
            logger.error(f"Error listing backlog items: {str(e)}")
            raise
    
    async def delete_backlog_item(
        self,
        tenant_name: str,
        item_id: str
    ) -> bool:
        """Delete a backlog item"""
        try:
            query = "DELETE FROM project_backlog WHERE id = %s"
            
            await self.db.execute_query(
                query,
                (item_id,),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Backlog item deleted: {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting backlog item: {str(e)}")
            raise
