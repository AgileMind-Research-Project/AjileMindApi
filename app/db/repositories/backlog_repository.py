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
        severity: Optional[str],
        parent_task_id: Optional[str] = None
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
            parent_task_id: Parent task ID for subtasks
        
        Returns:
            Created backlog item data
        """
        try:
            # Serialize tags to JSON
            tags_json = json.dumps(tags) if tags else None
            
            query = """
                INSERT INTO project_backlog (
                    id, project_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity, parent_task_id,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    summary = VALUES(summary),
                    description = VALUES(description),
                    issue_type = VALUES(issue_type),
                    status = VALUES(status),
                    priority = VALUES(priority),
                    assignee = VALUES(assignee),
                    tags = VALUES(tags),
                    severity = VALUES(severity),
                    parent_task_id = VALUES(parent_task_id),
                    updated_at = NOW()
            """
            
            await self.db.execute_query(
                query,
                (item_id, project_id, summary, description, issue_type,
                 status, priority, assignee, tags_json, severity, parent_task_id),
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
                    id, project_id, sprint_id, summary, description, issue_type,
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
        project_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all backlog items for a project"""
        try:
            # Base query
            query = """
                SELECT 
                    id, project_id, sprint_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity, parent_task_id,
                    created_at, updated_at
                FROM project_backlog
                WHERE project_id = %s AND issue_type != 'release'
            """
            
            params = [project_id]
            
            # Add status filter if provided
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY created_at DESC"
            
            results = await self.db.execute_query(
                query,
                tuple(params),
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

    async def list_backlog_by_type(
        self,
        tenant_name: str,
        project_id: int,
        issue_type: str
    ) -> List[Dict[str, Any]]:
        """List backlog items filtered by type"""
        try:
            query = """
                SELECT 
                    id, project_id, sprint_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity, parent_task_id,
                    created_at, updated_at, start_date, end_date
                FROM project_backlog
                WHERE project_id = %s AND issue_type = %s
                ORDER BY created_at DESC
            """
            
            results = await self.db.execute_query(
                query,
                (project_id, issue_type),
                fetch_all=True,
                schema=tenant_name
            )
            
            if results:
                for item in results:
                    if item.get('tags'):
                        try:
                            item['tags'] = json.loads(item['tags'])
                        except:
                            item['tags'] = None
                    # Format dates for JSON
                    for d in ['created_at', 'updated_at', 'start_date', 'end_date']:
                        if item.get(d):
                            item[d] = str(item[d])

            return results or []
        except Exception as e:
            logger.error(f"Error listing backlog items by type: {str(e)}")
            raise

    async def list_all_by_type(
        self,
        tenant_name: str,
        issue_type: str
    ) -> List[Dict[str, Any]]:
        """List all backlog items of a given type across all projects"""
        try:
            query = """
                SELECT 
                    id, project_id, sprint_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity, parent_task_id,
                    created_at, updated_at, start_date, end_date
                FROM project_backlog
                WHERE issue_type = %s
                ORDER BY created_at DESC
            """
            results = await self.db.execute_query(
                query,
                (issue_type,),
                fetch_all=True,
                schema=tenant_name
            )
            if results:
                for item in results:
                    if item.get('tags'):
                        try:
                            item['tags'] = json.loads(item['tags'])
                        except:
                            item['tags'] = None
                    for d in ['created_at', 'updated_at', 'start_date', 'end_date']:
                        if item.get(d):
                            item[d] = str(item[d])
            return results or []
        except Exception as e:
            logger.error(f"Error listing all backlog items by type: {str(e)}")
            raise

    async def list_backlog_by_sprint(
        self,
        tenant_name: str,
        sprint_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all backlog items for a sprint"""
        try:
            # Base query
            query = """
                SELECT 
                    id, project_id, sprint_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity, parent_task_id,
                    estimated_hours, story_points, is_jira,
                    created_at, updated_at
                FROM project_backlog
                WHERE sprint_id = %s AND issue_type != 'release'
            """
            
            params = [sprint_id]
            
            # Add status filter if provided
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY created_at ASC"
            
            results = await self.db.execute_query(
                query,
                tuple(params),
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
            logger.error(f"Error listing sprint backlog items: {str(e)}")
            return []
    
    
    async def list_user_tasks(
        self,
        tenant_name: str,
        email: str
    ) -> List[Dict[str, Any]]:
        """List all backlog items assigned to a user across all projects"""
        try:
            query = """
                SELECT 
                    b.id, b.project_id, b.summary, b.description, b.issue_type,
                    b.status, b.priority, b.assignee, b.tags, b.severity, b.parent_task_id,
                    b.created_at, b.updated_at, b.estimated_hours, b.story_points, b.is_jira,
                    p.project_name, p.key as project_key,
                    parent.summary as parent_summary
                FROM project_backlog b
                JOIN projects p ON b.project_id = p.project_id
                LEFT JOIN project_backlog parent ON b.parent_task_id = parent.id
                WHERE b.assignee = %s
                ORDER BY p.project_name, b.created_at DESC
            """
            
            results = await self.db.execute_query(
                query,
                (email,),
                fetch_all=True,
                schema=tenant_name
            )
            
            # Normalize data for Pydantic validation
            if results:
                for item in results:
                    # Deserialize tags
                    if item.get('tags'):
                        try:
                            item['tags'] = json.loads(item['tags'])
                        except:
                            item['tags'] = None
                    
                    # Normalize Priority
                    if item.get('priority'):
                        try:
                            p = str(item['priority']).lower().strip()
                            if p in ['high', 'medium', 'low']:
                                item['priority'] = p
                            else:
                                item['priority'] = None
                        except:
                            item['priority'] = None
                    
                    # Normalize Issue Type
                    if item.get('issue_type'):
                        itype = str(item['issue_type']).lower().strip()
                        # Map 'task' or other variants to 'story' or keep if valid
                        if itype == 'task':
                            item['issue_type'] = 'story'
                        elif itype in ['story', 'feature', 'change', 'bug', 'sub_task']:
                            item['issue_type'] = itype
                        else:
                            # Default fallback if unknown
                            item['issue_type'] = 'story'
                    else:
                        item['issue_type'] = 'story' # Default if missing
            
            return results or []
            
        except Exception as e:
            logger.error(f"Error listing user tasks: {str(e)}")
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
    
    # ===== Task Split Methods =====
    
    async def get_task_with_subtasks(
        self,
        tenant_name: str,
        parent_id: str
    ) -> Dict[str, Any]:
        """Get parent task with all its subtasks"""
        try:
            # Get parent task
            parent_query = """
                SELECT 
                    id, project_id, summary, description, issue_type,
                    status, priority, assignee, tags, severity,
                    created_at, updated_at, is_jira
                FROM project_backlog
                WHERE id = %s
            """
            parent = await self.db.execute_query(
                parent_query,
                (parent_id,),
                fetch_one=True,
                schema=tenant_name
            )
            
            if not parent:
                return None
            
            # Deserialize parent tags
            if parent.get('tags'):
                try:
                    parent['tags'] = json.loads(parent['tags'])
                except:
                    parent['tags'] = None
            
            # Get subtasks
            subtasks_query = """
                SELECT 
                    id, project_id, summary, description, issue_type,
                    status, priority, assignee, tags, parent_task_id,
                    estimated_hours, story_points, is_jira,
                    created_at, updated_at
                FROM project_backlog
                WHERE parent_task_id = %s
                ORDER BY created_at ASC
            """
            subtasks = await self.db.execute_query(
                subtasks_query,
                (parent_id,),
                fetch_all=True,
                schema=tenant_name
            )
            
            # Deserialize subtask tags
            if subtasks:
                for subtask in subtasks:
                    if subtask.get('tags'):
                        try:
                            subtask['tags'] = json.loads(subtask['tags'])
                        except:
                            subtask['tags'] = None
            
            return {
                "parent": parent,
                "subtasks": subtasks or [],
                "total_subtasks": len(subtasks) if subtasks else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting task with subtasks: {str(e)}")
            raise
    
    async def get_next_temp_id(
        self,
        tenant_name: str,
        project_id: int
    ) -> str:
        """Generate next temporary task ID"""
        try:
            # Get project key
            project_query = "SELECT `key` FROM projects WHERE project_id = %s"
            project = await self.db.execute_query(
                project_query,
                (project_id,),
                fetch_one=True,
                schema=tenant_name
            )
            
            if not project:
                raise ValueError(f"Project with ID {project_id} not found")
            
            project_key = project.get("key")
            
            # Count existing temp IDs for this project
            count_query = """
                SELECT COUNT(*) as count
                FROM project_backlog
                WHERE project_id = %s AND id LIKE %s
            """
            result = await self.db.execute_query(
                count_query,
                (project_id, f"{project_key}-TEMP-%"),
                fetch_one=True,
                schema=tenant_name
            )
            
            count = result.get("count", 0) if result else 0
            next_num = count + 1
            
            # Generate temp ID: PROJECT_KEY-TEMP-001
            temp_id = f"{project_key}-TEMP-{next_num:03d}"
            
            return temp_id
            
        except Exception as e:
            logger.error(f"Error generating temp ID: {str(e)}")
            raise
    
    async def create_subtask_local(
        self,
        tenant_name: str,
        temp_id: str,
        parent_task_id: str,
        project_id: int,
        summary: str,
        description: Optional[str],
        priority: Optional[str],
        assignee: Optional[str],
        tags: Optional[List[str]],
        estimated_hours: int = 0,
        story_points: int = 0
    ) -> Dict[str, Any]:
        """Create a subtask locally with is_jira=false"""
        try:
            tags_json = json.dumps(tags) if tags else None
            
            query = """
                INSERT INTO project_backlog (
                    id, project_id, parent_task_id, summary, description,
                    issue_type, status, priority, assignee, tags,
                    estimated_hours, story_points, is_jira,
                    start_date, end_date, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY), NOW(), NOW())
            """
            
            await self.db.execute_query(
                query,
                (temp_id, project_id, parent_task_id, summary, description,
                 'sub_task', 'todo', priority, assignee, tags_json,
                 estimated_hours, story_points, False),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Subtask created locally: {temp_id}")
            
            # Return created subtask
            return await self.get_backlog_item(tenant_name, temp_id)
            
        except Exception as e:
            logger.error(f"Error creating subtask locally: {str(e)}")
            raise
    
    async def update_subtask(
        self,
        tenant_name: str,
        subtask_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update subtask fields"""
        try:
            # Build dynamic update query
            set_clauses = []
            params = []
            
            if 'summary' in updates and updates['summary'] is not None:
                set_clauses.append("summary = %s")
                params.append(updates['summary'])
            
            if 'description' in updates:
                set_clauses.append("description = %s")
                params.append(updates['description'])
            
            if 'priority' in updates:
                set_clauses.append("priority = %s")
                params.append(updates['priority'])
            
            if 'assignee' in updates:
                set_clauses.append("assignee = %s")
                params.append(updates['assignee'])
            
            if 'tags' in updates:
                tags_json = json.dumps(updates['tags']) if updates['tags'] else None
                set_clauses.append("tags = %s")
                params.append(tags_json)
            
            if 'estimated_hours' in updates:
                set_clauses.append("estimated_hours = %s")
                params.append(updates['estimated_hours'])
            
            if 'story_points' in updates:
                set_clauses.append("story_points = %s")
                params.append(updates['story_points'])
            
            if not set_clauses:
                return await self.get_backlog_item(tenant_name, subtask_id)
            
            set_clauses.append("updated_at = NOW()")
            params.append(subtask_id)
            
            query = f"""
                UPDATE project_backlog
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            
            await self.db.execute_query(
                query,
                tuple(params),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Subtask updated: {subtask_id}")
            
            # Return updated subtask
            return await self.get_backlog_item(tenant_name, subtask_id)
            
        except Exception as e:
            logger.error(f"Error updating subtask: {str(e)}")
            raise
    
    async def update_task_jira_info(
        self,
        tenant_name: str,
        old_id: str,
        new_jira_key: str
    ) -> bool:
        """Update task with Jira key and set is_jira=true"""
        try:
            # First, update any subtasks that reference this task as parent
            update_children_query = """
                UPDATE project_backlog
                SET parent_task_id = %s
                WHERE parent_task_id = %s
            """
            await self.db.execute_query(
                update_children_query,
                (new_jira_key, old_id),
                commit=True,
                schema=tenant_name
            )
            
            # Update the task itself
            update_query = """
                UPDATE project_backlog
                SET id = %s, is_jira = %s, updated_at = NOW()
                WHERE id = %s
            """
            await self.db.execute_query(
                update_query,
                (new_jira_key, True, old_id),
                commit=True,
                schema=tenant_name
            )
            
            logger.info(f"Task updated with Jira info: {old_id} -> {new_jira_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task Jira info: {str(e)}")
            raise

    async def rename_backlog_item(
        self,
        tenant_name: str,
        old_id: str,
        new_id: str
    ) -> bool:
        """
        Rename a backlog item (change its ID).
        Uses a single transaction block with FK checks disabled to ensure atomicity and success.
        """
        try:
            logger.info(f"Renaming {old_id} to {new_id} using transaction block")
            
            ops = [
                # 1. Disable FK checks
                {"query": "SET FOREIGN_KEY_CHECKS=0"},
                
                # 2. Update item ID and set is_jira to true
                {
                    "query": "UPDATE project_backlog SET id = %s, is_jira = 1, updated_at = NOW() WHERE id = %s",
                    "params": (new_id, old_id)
                },
                
                # 3. Update Priority Table References
                {
                    "query": "UPDATE project_backlog_priority SET backlog_id = %s WHERE backlog_id = %s",
                    "params": (new_id, old_id)
                },
                
                # 4. Update Child References
                {
                    "query": "UPDATE project_backlog SET parent_task_id = %s WHERE parent_task_id = %s",
                    "params": (new_id, old_id)
                },
                
                # 5. Re-enable FK checks
                {"query": "SET FOREIGN_KEY_CHECKS=1"}
            ]
            
            await self.db.execute_transaction_block(ops, schema=tenant_name)
            
            logger.info(f"Backlog item renamed successfully: {old_id} -> {new_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error renaming backlog item: {str(e)}")
            # Transaction block already handles rollback of the transaction, 
            # but we can't easily rollback SET FOREIGN_KEY_CHECKS=0 if the connection is closed.
            # However, since the connection is closed returned to pool, 
            # and autocommit is False, and we rolled back, the data is safe.
            # The next user of the connection should ideally reset session vars, but 
            # usually pools reset them or we assume default.
            raise
