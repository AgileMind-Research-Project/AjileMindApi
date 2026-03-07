"""
New Task Service

Service layer for new task management operations.
"""

from app.db.database import Database
from app.schemas.new_task import (
    NewTaskCreate, NewTaskUpdate, NewTaskResponse,
    NewTaskListResponse, NewTaskFilterParams, NewTaskStatus
)
from app.core.logger import logger
from typing import List, Optional, Dict, Any
from datetime import datetime


class NewTaskService:
    """Service for new task operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_task(
        self,
        task_data: NewTaskCreate,
        tenant_schema: str
    ) -> NewTaskResponse:
        """Create a new task"""
        try:
            insert_query = f"""
                INSERT INTO {tenant_schema}.new_tasks
                (report_id, transcript_id, project_id, task_title, assignee, due_date, priority, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            result = await self.db.execute_query(
                insert_query,
                (
                    task_data.report_id,
                    task_data.transcript_id,
                    task_data.project_id,
                    task_data.task_title,
                    task_data.assignee,
                    task_data.due_date,
                    task_data.priority,
                    NewTaskStatus.PENDING.value
                ),
                commit=True,
                schema=tenant_schema
            )
            
            task_id = result.lastrowid
            return await self.get_task(task_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    async def create_tasks_from_report(
        self,
        report_id: int,
        transcript_id: int,
        project_id: Optional[int],
        next_steps: List[Dict[str, Any]],
        tenant_schema: str
    ) -> List[NewTaskResponse]:
        """Create multiple tasks from report next_steps"""
        try:
            created_tasks = []
            
            for step in next_steps:
                # Handle both dict and ActionItem-like objects
                if isinstance(step, dict):
                    task_title = step.get('task', step.get('action', ''))
                    assignee = step.get('assignee')
                    due_date = step.get('due_date')
                    priority = step.get('priority')
                else:
                    task_title = getattr(step, 'task', getattr(step, 'action', ''))
                    assignee = getattr(step, 'assignee', None)
                    due_date = getattr(step, 'due_date', None)
                    priority = getattr(step, 'priority', None)
                
                if not task_title:
                    continue
                
                task_data = NewTaskCreate(
                    report_id=report_id,
                    transcript_id=transcript_id,
                    project_id=project_id,
                    task_title=task_title,
                    assignee=assignee,
                    due_date=due_date,
                    priority=priority
                )
                
                task = await self.create_task(task_data, tenant_schema)
                created_tasks.append(task)
            
            logger.info(f"Created {len(created_tasks)} tasks from report {report_id}")
            return created_tasks
        
        except Exception as e:
            logger.error(f"Error creating tasks from report: {e}")
            raise
    
    async def get_task(
        self,
        task_id: int,
        tenant_schema: str
    ) -> NewTaskResponse:
        """Get a task by ID"""
        try:
            query = f"""
                SELECT id, report_id, transcript_id, project_id, task_title, assignee,
                       due_date, priority, status, created_at, updated_at
                FROM {tenant_schema}.new_tasks
                WHERE id = %s
            """
            
            result = await self.db.execute_query(query, (task_id,), fetch_one=True, schema=tenant_schema)
            
            if not result:
                raise ValueError(f"Task with ID {task_id} not found")
            
            return NewTaskResponse(
                id=result['id'],
                report_id=result['report_id'],
                transcript_id=result['transcript_id'],
                project_id=result.get('project_id'),
                task_title=result['task_title'],
                assignee=result.get('assignee'),
                due_date=result.get('due_date'),
                priority=result.get('priority'),
                status=result['status'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        
        except Exception as e:
            logger.error(f"Error fetching task: {e}")
            raise
    
    async def list_tasks(
        self,
        tenant_schema: str,
        filters: NewTaskFilterParams
    ) -> NewTaskListResponse:
        """List tasks with filters"""
        try:
            where_clauses = []
            params = []
            
            if filters.status:
                where_clauses.append("status = %s")
                params.append(filters.status.value)
            
            if filters.report_id:
                where_clauses.append("report_id = %s")
                params.append(filters.report_id)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Count total
            count_query = f"""
                SELECT COUNT(*) as total
                FROM {tenant_schema}.new_tasks
                {where_sql}
            """
            count_result = await self.db.execute_query(count_query, tuple(params), fetch_one=True)
            total = count_result['total'] if count_result else 0
            
            # Fetch tasks
            offset = (filters.page - 1) * filters.page_size
            list_query = f"""
                SELECT id, report_id, transcript_id, project_id, task_title, assignee,
                       due_date, priority, status, created_at, updated_at
                FROM {tenant_schema}.new_tasks
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([filters.page_size, offset])
            
            results = await self.db.execute_query(list_query, tuple(params), fetch_all=True)
            
            tasks = []
            for row in results or []:
                tasks.append(NewTaskResponse(
                    id=row['id'],
                    report_id=row['report_id'],
                    transcript_id=row['transcript_id'],
                    project_id=row.get('project_id'),
                    task_title=row['task_title'],
                    assignee=row.get('assignee'),
                    due_date=row.get('due_date'),
                    priority=row.get('priority'),
                    status=row['status'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            
            return NewTaskListResponse(
                tasks=tasks,
                total=total,
                page=filters.page,
                page_size=filters.page_size
            )
        
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            raise
    
    async def update_task(
        self,
        task_id: int,
        task_data: NewTaskUpdate,
        tenant_schema: str
    ) -> NewTaskResponse:
        """Update a task"""
        try:
            # Build update query dynamically
            update_fields = []
            params = []
            
            if task_data.task_title is not None:
                update_fields.append("task_title = %s")
                params.append(task_data.task_title)
            
            if task_data.assignee is not None:
                update_fields.append("assignee = %s")
                params.append(task_data.assignee)
            
            if task_data.due_date is not None:
                update_fields.append("due_date = %s")
                params.append(task_data.due_date)
            
            if task_data.priority is not None:
                update_fields.append("priority = %s")
                params.append(task_data.priority)
            
            if task_data.status is not None:
                update_fields.append("status = %s")
                params.append(task_data.status.value)
            
            if not update_fields:
                return await self.get_task(task_id, tenant_schema)
            
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            params.append(task_id)
            
            update_query = f"""
                UPDATE {tenant_schema}.new_tasks
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            await self.db.execute_query(update_query, tuple(params), commit=True, schema=tenant_schema)
            
            return await self.get_task(task_id, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            raise
    
    async def approve_task(
        self,
        task_id: int,
        tenant_schema: str,
        project_id_override: Optional[int] = None
    ) -> NewTaskResponse:
        """Approve a task and add to project backlog"""
        try:
            # Get the task first
            task = await self.get_task(task_id, tenant_schema)
            
            # Determine project_id (use override if provided, otherwise use task's project_id)
            project_id = project_id_override or task.project_id
            
            if not project_id:
                raise ValueError("No project_id found. Task must be associated with a project to be approved.")
            
            # Generate unique backlog ID
            import uuid
            backlog_id = f"IDEA-{uuid.uuid4().hex[:8].upper()}"
            
            # Parse due_date if available
            end_date = None
            if task.due_date:
                try:
                    from datetime import datetime as dt
                    for fmt in ['%Y-%m-%d', '%b %d', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            parsed = dt.strptime(task.due_date, fmt)
                            if fmt == '%b %d':
                                parsed = parsed.replace(year=dt.now().year)
                            end_date = parsed.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            
            # Insert into project_backlog
            backlog_query = f"""
                INSERT INTO {tenant_schema}.project_backlog
                (id, project_id, summary, description, issue_type, status, priority, assignee, end_date, is_jira, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            await self.db.execute_query(
                backlog_query,
                (
                    backlog_id,
                    project_id,
                    task.task_title,
                    f"Approved from brainstorming session (Task ID: {task_id})",
                    'story',
                    'todo',
                    task.priority or 'medium',
                    task.assignee,
                    end_date,
                    0  # Not from Jira
                ),
                commit=True,
                schema=tenant_schema
            )
            
            logger.info(f"Task {task_id} added to project_backlog as {backlog_id}")
            
            # Update task status to approved
            update_data = NewTaskUpdate(status=NewTaskStatus.APPROVED)
            return await self.update_task(task_id, update_data, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error approving task: {e}")
            raise
    
    async def remove_task(
        self,
        task_id: int,
        tenant_schema: str
    ) -> NewTaskResponse:
        """Remove/reject a task"""
        try:
            update_data = NewTaskUpdate(status=NewTaskStatus.REMOVED)
            return await self.update_task(task_id, update_data, tenant_schema)
        
        except Exception as e:
            logger.error(f"Error removing task: {e}")
            raise
    
    async def delete_task(
        self,
        task_id: int,
        tenant_schema: str
    ) -> bool:
        """Delete a task"""
        try:
            delete_query = f"""
                DELETE FROM {tenant_schema}.new_tasks
                WHERE id = %s
            """
            
            await self.db.execute_query(delete_query, (task_id,), commit=True, schema=tenant_schema)
            return True
        
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise
