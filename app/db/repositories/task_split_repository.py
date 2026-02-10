"""
Task Split Repository

Database operations for task splitting and subtask management.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import date
from app.db.database import Database
from app.core.logger import logger


class TaskSplitRepository:
    """Repository for task split operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_parent_tasks_for_project(
        self,
        project_id: int,
        tenant_name: str
    ) -> List[Dict[str, Any]]:
        """Get all parent tasks for a project (is_jira=false, parent_task_id IS NULL)"""
        try:
            query = """
                SELECT 
                    id, project_id, summary, description, issue_type,
                    status, priority, severity, assignee, tags,
                    estimated_hours, logged_hours, story_points,
                    sprint_id, parent_task_id, start_date, actual_start_date,
                    end_date, actual_end_date, created_at, updated_at, is_jira
                FROM project_backlog
                WHERE project_id = %s 
                    AND is_jira = 0 
                    AND parent_task_id IS NULL
                ORDER BY created_at DESC
            """
            
            tasks = await self.db.execute_query(
                query,
                (project_id,),
                fetch_all=True,
                schema=tenant_name
            )
            
            # Deserialize tags
            if tasks:
                for task in tasks:
                    if task.get('tags'):
                        try:
                            task['tags'] = json.loads(task['tags'])
                        except:
                            task['tags'] = None
            
            return tasks or []
            
        except Exception as e:
            logger.error(f"Error getting parent tasks for project: {str(e)}")
            raise
    
    async def get_task_with_subtasks(
        self,
        task_id: str,
        tenant_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get parent task with all its subtasks"""
        try:
            # Get parent task
            parent_query = """
                SELECT 
                    id, project_id, summary, description, issue_type,
                    status, priority, severity, assignee, tags,
                    estimated_hours, logged_hours, story_points,
                    sprint_id, parent_task_id, start_date, actual_start_date,
                    end_date, actual_end_date, created_at, updated_at, is_jira
                FROM project_backlog
                WHERE id = %s
            """
            
            parent_task = await self.db.execute_query(
                parent_query,
                (task_id,),
                fetch_one=True,
                schema=tenant_name
            )
            
            if not parent_task:
                return None
            
            # Deserialize parent task tags
            if parent_task.get('tags'):
                try:
                    parent_task['tags'] = json.loads(parent_task['tags'])
                except:
                    parent_task['tags'] = None
            
            # Get subtasks
            subtasks_query = """
                SELECT 
                    id, project_id, summary, description, issue_type,
                    status, priority, severity, assignee, tags,
                    estimated_hours, logged_hours, story_points,
                    sprint_id, parent_task_id, start_date, actual_start_date,
                    end_date, actual_end_date, created_at, updated_at, is_jira
                FROM project_backlog
                WHERE parent_task_id = %s
                ORDER BY created_at ASC
            """
            
            subtasks = await self.db.execute_query(
                subtasks_query,
                (task_id,),
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
                **parent_task,
                "subtasks": subtasks or [],
                "total_subtasks": len(subtasks) if subtasks else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting task with subtasks: {str(e)}")
            raise
    
    async def create_subtask(
        self,
        subtask_data: Dict[str, Any],
        tenant_name: str
    ) -> str:
        """Create a new subtask (local, not yet in Jira)"""
        try:
            # Generate temporary local ID
            import uuid
            local_id = f"LOCAL-{uuid.uuid4().hex[:8].upper()}"
            
            # Serialize tags to JSON
            tags_json = None
            if subtask_data.get('tags'):
                tags_json = json.dumps(subtask_data['tags'])
            
            insert_query = """
                INSERT INTO project_backlog (
                    id, project_id, summary, description, issue_type,
                    status, priority, assignee, tags, estimated_hours,
                    story_points, parent_task_id, start_date, end_date,
                    is_jira, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, NOW(), NOW()
                )
            """
            
            await self.db.execute_query(
                insert_query,
                (
                    local_id,
                    subtask_data['project_id'],
                    subtask_data['summary'],
                    subtask_data.get('description'),
                    'Sub-task',
                    subtask_data.get('status', 'todo'),
                    subtask_data.get('priority'),
                    subtask_data.get('assignee'),
                    tags_json,
                    subtask_data.get('estimated_hours', 0),
                    subtask_data.get('story_points', 0),
                    subtask_data['parent_task_id'],
                    subtask_data.get('start_date'),
                    subtask_data.get('end_date'),
                    False  # is_jira = False for local tasks
                ),
                schema=tenant_name
            )
            
            logger.info(f"Created local subtask: {local_id}")
            return local_id
            
        except Exception as e:
            logger.error(f"Error creating subtask: {str(e)}")
            raise
    
    async def update_subtask(
        self,
        subtask_id: str,
        update_data: Dict[str, Any],
        tenant_name: str
    ) -> bool:
        """Update subtask details"""
        try:
            # Build dynamic update query
            update_fields = []
            params = []
            
            if 'summary' in update_data:
                update_fields.append("summary = %s")
                params.append(update_data['summary'])
            
            if 'description' in update_data:
                update_fields.append("description = %s")
                params.append(update_data['description'])
            
            if 'status' in update_data:
                update_fields.append("status = %s")
                params.append(update_data['status'])
            
            if 'priority' in update_data:
                update_fields.append("priority = %s")
                params.append(update_data['priority'])
            
            if 'assignee' in update_data:
                update_fields.append("assignee = %s")
                params.append(update_data['assignee'])
            
            if 'tags' in update_data:
                update_fields.append("tags = %s")
                params.append(json.dumps(update_data['tags']) if update_data['tags'] else None)
            
            if 'estimated_hours' in update_data:
                update_fields.append("estimated_hours = %s")
                params.append(update_data['estimated_hours'])
            
            if 'story_points' in update_data:
                update_fields.append("story_points = %s")
                params.append(update_data['story_points'])
            
            if 'start_date' in update_data:
                update_fields.append("start_date = %s")
                params.append(update_data['start_date'])
            
            if 'end_date' in update_data:
                update_fields.append("end_date = %s")
                params.append(update_data['end_date'])
            
            if not update_fields:
                return True  # Nothing to update
            
            update_fields.append("updated_at = NOW()")
            params.append(subtask_id)
            
            update_query = f"""
                UPDATE project_backlog
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            await self.db.execute_query(
                update_query,
                tuple(params),
                schema=tenant_name
            )
            
            logger.info(f"Updated subtask: {subtask_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subtask: {str(e)}")
            raise
    
    async def delete_subtask(
        self,
        subtask_id: str,
        tenant_name: str
    ) -> bool:
        """Delete a subtask"""
        try:
            delete_query = "DELETE FROM project_backlog WHERE id = %s"
            
            await self.db.execute_query(
                delete_query,
                (subtask_id,),
                schema=tenant_name
            )
            
            logger.info(f"Deleted subtask: {subtask_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting subtask: {str(e)}")
            raise
    
    async def combine_subtasks(
        self,
        subtask_ids: List[str],
        combined_data: Dict[str, Any],
        parent_task_id: str,
        tenant_name: str
    ) -> str:
        """Combine multiple subtasks into one new subtask"""
        try:
            # Get all subtasks to combine
            placeholders = ', '.join(['%s'] * len(subtask_ids))
            query = f"""
                SELECT id, summary, description, estimated_hours, story_points
                FROM project_backlog
                WHERE id IN ({placeholders}) AND parent_task_id = %s
            """
            
            subtasks = await self.db.execute_query(
                query,
                (*subtask_ids, parent_task_id),
                fetch_all=True,
                schema=tenant_name
            )
            
            if not subtasks or len(subtasks) != len(subtask_ids):
                raise ValueError("Some subtasks not found or don't belong to parent")
            
            # Concatenate descriptions
            descriptions = [s['description'] for s in subtasks if s.get('description')]
            combined_description = combined_data.get('description', '')
            if descriptions:
                combined_description = combined_description + "\n\n" + "\n---\n".join(descriptions) if combined_description else "\n---\n".join(descriptions)
            
            # Sum estimated hours and story points
            total_hours = sum(s.get('estimated_hours', 0) for s in subtasks)
            total_points = sum(s.get('story_points', 0) for s in subtasks)
            
            # Create new combined subtask
            combined_subtask_data = {
                **combined_data,
                'description': combined_description,
                'estimated_hours': total_hours,
                'story_points': total_points,
                'parent_task_id': parent_task_id,
                'project_id': subtasks[0]['project_id']  # Use project_id from first subtask
            }
            
            # Get project_id from parent task
            parent_query = "SELECT project_id FROM project_backlog WHERE id = %s"
            parent = await self.db.execute_query(
                parent_query,
                (parent_task_id,),
                fetch_one=True,
                schema=tenant_name
            )
            
            if parent:
                combined_subtask_data['project_id'] = parent['project_id']
            
            new_subtask_id = await self.create_subtask(combined_subtask_data, tenant_name)
            
            # Delete old subtasks
            for subtask_id in subtask_ids:
                await self.delete_subtask(subtask_id, tenant_name)
            
            logger.info(f"Combined {len(subtask_ids)} subtasks into {new_subtask_id}")
            return new_subtask_id
            
        except Exception as e:
            logger.error(f"Error combining subtasks: {str(e)}")
            raise
    
    async def update_subtask_jira_id(
        self,
        local_id: str,
        jira_key: str,
        tenant_name: str
    ) -> bool:
        """Update subtask ID with Jira key after creation"""
        try:
            # Update the ID and set is_jira to true
            update_query = """
                UPDATE project_backlog
                SET id = %s, is_jira = TRUE, updated_at = NOW()
                WHERE id = %s
            """
            
            await self.db.execute_query(
                update_query,
                (jira_key, local_id),
                schema=tenant_name
            )
            
            logger.info(f"Updated subtask ID from {local_id} to {jira_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subtask Jira ID: {str(e)}")
            raise
